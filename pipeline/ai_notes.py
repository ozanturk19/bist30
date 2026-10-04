"""D-44a — AI Analist Notu pilotu (iki model yan yana).

Kalite tarifi: ~/ops/plans/2026-09-23-denetim/ai-not-tarifi.md (CPO, 23.09).
Bu modül app.py'yi İMPORT ETMEZ (pipeline/intraday.py deseni) — girdi yalnız
sitenin kendi yayınladığı public API'si (/api/hisse/<T>/lite, /fundamentals).
Sayıları model YAZMAZ: kod olgu listesi üretir, model olgu kimliğiyle yazar,
kod {Fn} yerleştirir, doğrulayıcı geçmeyeni reddeder (önceki not korunur —
pilotta "önceki not" yok, reddedilen örnek ayrıca raporda işaretlenir).

Kullanım: python3 -m pipeline.ai_notes --out plans/2026-09-23-denetim/ai-pilot.md
Ortam: GEMINI_API_KEY zorunlu (yoksa çıkar, hiçbir çağrı atılmaz).
Bütçe: --budget-usd (varsayılan 1.0) — kümülatif harcama bu değere ulaşınca
kalan çağrılar atılmaz (gemini_budget.cost_usd ile ölçülür, PROD sayaç dosyasına
dokunulmaz — ayrı, yalnız bellek-içi bir pilot sayacı).
"""
import argparse
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import gemini_budget  # noqa: E402  (fiyat tablosu + cost_usd — bağımsız modül, app.py'siz)

DEFAULT_BASE_URL = "https://borsapusula.com"
MODELS = ["gemini-2.5-flash-lite", "gemini-2.5-flash"]
SIGNAL_LABELS = {"AL": "Güçlü Trend", "SAT": "Trend Bozuldu", "BEKLE": "Yatay"}  # app.py:152 ile aynı sabit

SYSTEM_PROMPT = """Rolün: BorsaPusula için betimleyici şirket notu yazan editör. Okur orta-uzun vadeli bireysel yatırımcı.
Yalnız verilen olgulara dayan; olguda olmayan hiçbir iddia, tahmin, beklenti yazma. Metinde çıplak rakam YAZMA, \
yalnız olgu kimliği ({F1} gibi, SÜSLÜ PARANTEZLİ) kullan — tarih ve "üç yıl" gibi göreli-olmayan zaman sözcükleri hariç.
ZORUNLU ÖRNEK (olgu: F1=Hasılat 2025 yıllık değişim=−%21,7): DOĞRU → "Hasılat geriledi ({F1})." \
YANLIŞ → "Hasılat %21,7 geriledi." (rakam metne çıplak yazılmış, {F1} kullanılmamış — bu metin REDDEDİLİR).
Her sayısal olguyu mutlaka {Fn} kimliğiyle ver; olgu listesindeki hiçbir sayıyı kendi kelimelerinle yazma.
Yasak: AL / SAT / BEKLE kelimeleri ve "al", "sat", "almalı", "satmalı", "fırsat", "tavsiye", "önerilir"; \
teknik hedef dili (hedef fiyat, TP, kâr al, potansiyel, yükseliş beklentisi, "hedefe ulaştı"); \
göreli zaman ("bugün", "dün", "yarın", "günün"); kaynak adı ("KAP'a göre", "Reuters"); \
şirkete yargı ("zayıf şirket", "sağlam değil", "riskli hisse").
İzinli: güçlü/zayıf KALEM betimi ("nakit akışı güçlü, kârlılık zayıf"), ucuz/makul/pahalı DEĞERLEME betimi \
(sektöre göre, olguyla), trend durumu adı (Güçlü Trend / Yatay / Trend Bozuldu).
Sıra: (1) son finansal tablonun ana hareketi, (2) bilanço/nakit, (3) değerleme bağlamı, (4) trend durumu tek cümle.
3-5 cümle, toplam en fazla 420 karakter. Çıktı YALNIZ JSON: {"note": "...", "facts_used": ["F1","F4"], "lang": "tr"}
"""

_BANNED_PATTERNS = [
    r"\b(AL|SAT|BEKLE)\b",
    r"(?i)\b(al(ın|malı)?|sat(ın|malı)?|fırsat|tavsiye|öneril|hedef|potansiyel|kâr al|beklenti)\b",
    r"(?i)\b(bugün|dün|yarın|günün)\b",
    r"(?i)(KAP'a göre|kaynak\s*:|reuters|bloomberg|anadolu ajansı)",
]
_DATE_OK = re.compile(r"\b(19|20)\d{2}\b|\b\d{1,2}\s+(Ocak|Şubat|Mart|Nisan|Mayıs|Haziran|Temmuz|Ağustos|Eylül|Ekim|Kasım|Aralık)\b")


def _tr_num(v, decimals=1):
    if v is None:
        return None
    s = f"{v:,.{decimals}f}"
    s = s.replace(",", "§").replace(".", ",").replace("§", ".")
    return s


def _tr_pct(v, decimals=1):
    """Türkçe yazım: işaret % işaretinden önce (−%21,7), app.py _tr1 deseniyle uyumlu."""
    if v is None:
        return None
    sign = "−" if v < 0 else ""
    return f"{sign}%{_tr_num(abs(v), decimals)}"


def _get_json(path, base_url, timeout=15):
    url = base_url.rstrip("/") + path
    req = urllib.request.Request(url, headers={"User-Agent": "bp-ai-notes-pilot/1"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode("utf-8"))


def build_facts(ticker, base_url):
    """Olgu listesi: [{"id","t","v"}]. Girdi yalnız sitenin kendi /api/hisse/<T>/* JSON'u."""
    lite = (_get_json(f"/api/hisse/{ticker}/lite", base_url) or {}).get("stock") or {}
    fund = (_get_json(f"/api/hisse/{ticker}/fundamentals", base_url) or {}).get("fundamentals") or {}
    if not lite or not fund:
        return None, lite, fund
    kap = fund.get("kap") or {}
    facts = []
    n = [0]

    def add(t, v):
        if v is None:
            return None
        n[0] += 1
        fid = f"F{n[0]}"
        facts.append({"id": fid, "t": t, "v": v})
        return fid

    yd = kap.get("yillik_degisim") or {}
    years = sorted(yd.keys())
    if years:
        last_y = years[-1]
        is_bank = (kap.get("flags") or {}).get("banka")
        rev_key = "net_interest_income" if is_bank else "revenue"
        rev_label = "Net faiz geliri" if is_bank else "Hasılat"
        pct = (yd.get(last_y) or {}).get(rev_key)
        if pct is not None:
            add(f"{rev_label} {last_y} yıllık değişim", _tr_pct(pct))
        ni_pct = (yd.get(last_y) or {}).get("net_income_parent")
        if ni_pct is not None:
            add(f"Net kâr {last_y} yıllık değişim", _tr_pct(ni_pct))
    nb = kap.get("net_borc") or {}
    if nb.get("net_borc_favok") is not None:
        add("Net borç/FAVÖK", _tr_num(nb["net_borc_favok"], 2))
    elif nb.get("net_borc_tl") is not None and nb["net_borc_tl"] < 0:
        add("Net nakit (TL)", _tr_num(-nb["net_borc_tl"] / 1e9, 1) + " milyar")
    cr = fund.get("current_ratio")
    if cr is not None:
        add("Cari oran", _tr_num(cr, 2))
    ds = kap.get("degerleme_simdi") or {}
    sek = fund.get("sektor_ortanca") or {}
    fk_simdi, fk_sek = ds.get("fk"), (sek.get("fk") or {}).get("deger")
    if fk_simdi is not None:
        add("F/K (son 12 ay)", _tr_num(fk_simdi, 1))
    if fk_sek is not None:
        add("Sektör ortanca F/K", _tr_num(fk_sek, 1))
    roe = fund.get("roe")
    roe_sek = (sek.get("ozsermaye_karliligi") or {}).get("deger")
    if roe is not None:
        add("Özsermaye kârlılığı (son 12 ay)", _tr_pct(roe, 1))
    if roe_sek is not None:
        add("Sektör ortanca özsermaye kârlılığı", _tr_pct(roe_sek, 1))
    hukum = None
    if fk_simdi and fk_sek:
        if fk_simdi < fk_sek * 0.9:
            hukum = "ucuz"
        elif fk_simdi > fk_sek * 1.1:
            hukum = "pahalı"
        else:
            hukum = "makul"
        add("Değerleme (F/K, sektöre göre)", hukum)
    trend = SIGNAL_LABELS.get(lite.get("signal"), lite.get("signal"))
    if trend:
        add("Trend durumu", trend)
    at = fund.get("analyst_target")
    price = lite.get("price")
    if at and price:
        add("Analist hedef ortalaması fiyatın üstünde oranı", _tr_pct((at / price - 1) * 100, 1))
        add("Analist sayısı", str(fund.get("analyst_count") or ""))
    return facts, lite, fund


def facts_block(facts):
    return "\n".join(f'{{"id":"{f["id"]}","t":"{f["t"]}","v":"{f["v"]}"}}' for f in facts)


def call_gemini(model, system_prompt, user_content, api_key, timeout=25):
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
    body = {
        "systemInstruction": {"parts": [{"text": system_prompt}]},
        "contents": [{"role": "user", "parts": [{"text": user_content}]}],
        # thinkingBudget=0: 2.5 serisi "thinking" moduyla maxOutputTokens'ı rasyoner ("thought")
        # token'larla tüketip metni kesiyordu (pilotta canlı ölçüldü: thoughtsTokenCount >100,
        # finishReason=MAX_TOKENS) — bu not boyutunda muhakemeye gerek yok, kapatınca STOP+tam JSON.
        "generationConfig": {"temperature": 0.3, "maxOutputTokens": 1000,
                              "responseMimeType": "application/json",
                              "thinkingConfig": {"thinkingBudget": 0}},
    }
    req = urllib.request.Request(url, data=json.dumps(body).encode("utf-8"),
                                  headers={"Content-Type": "application/json"}, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            d = json.loads(r.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        return None, None, f"HTTP {e.code}: {e.read()[:300]}"
    usage = d.get("usageMetadata") or {}
    try:
        cand = d["candidates"][0]
        text = cand["content"]["parts"][0]["text"]
    except (KeyError, IndexError):
        finish = (d.get("candidates") or [{}])[0].get("finishReason", "?")
        return None, usage, f"yanıt şekli beklenmedik (finishReason={finish}): {str(d)[:300]}"
    return text, usage, None


def validate_note(raw_text, facts):
    """Yayından önce doğrulayıcı (tarifi §4). (ok, rendered_text|None, reason|None) döner."""
    try:
        parsed = json.loads(raw_text)
        note = parsed.get("note", "")
        facts_used = parsed.get("facts_used", [])
    except (json.JSONDecodeError, AttributeError):
        return False, None, "JSON ayrıştırılamadı"
    fact_ids = {f["id"] for f in facts}
    fact_map = {f["id"]: f["v"] for f in facts}
    if not isinstance(facts_used, list) or not set(facts_used) <= fact_ids:
        return False, None, f"facts_used olgu kümesinin dışında: {facts_used}"
    placeholders = set(re.findall(r"\{(F\d+)\}", note))
    if not placeholders <= fact_ids:
        return False, None, f"metinde tanımsız olgu kimliği: {placeholders - fact_ids}"
    pre_text = re.sub(r"\{F\d+\}", "", note)
    bare_digits = re.sub(_DATE_OK, "", pre_text)
    if re.search(r"\d", bare_digits):
        return False, None, "çıplak rakam (tarih/yıl dışı)"
    for pat in _BANNED_PATTERNS:
        if re.search(pat, note):
            return False, None, f"yasak dil: {pat}"
    rendered = note
    for fid, val in fact_map.items():
        rendered = rendered.replace("{" + fid + "}", val)
    if len(rendered) > 420:
        return False, None, f"uzunluk {len(rendered)} > 420"
    return True, rendered, None


def run_pilot(tickers, base_url, api_key, budget_usd, out_path):
    spent = [0.0]
    rows = []
    for ticker in tickers:
        try:
            facts, lite, fund = build_facts(ticker, base_url)
        except (urllib.error.URLError, OSError, json.JSONDecodeError) as e:
            rows.append({"ticker": ticker, "error": f"veri çekilemedi: {e}"})
            continue
        if not facts:
            rows.append({"ticker": ticker, "error": "hisse bulunamadı / veri boş"})
            continue
        user_content = f"Olgular ({ticker}):\n{facts_block(facts)}"
        model_results = {}
        for model in MODELS:
            if spent[0] >= budget_usd:
                model_results[model] = {"skipped": "pilot bütçesi doldu"}
                continue
            text, usage, err = call_gemini(model, SYSTEM_PROMPT, user_content, api_key)
            if err:
                model_results[model] = {"error": err}
                continue
            cost = gemini_budget.cost_usd(model, usage.get("promptTokenCount", 0) or 0,
                                           usage.get("candidatesTokenCount", 0) or 0)
            spent[0] += cost
            ok, rendered, reason = validate_note(text, facts)
            model_results[model] = {"ok": ok, "raw": text, "rendered": rendered,
                                     "reason": reason, "cost_usd": round(cost, 6)}
            time.sleep(1)  # nazik aralık, pilot ölçeğinde rate-limit riski yok
        rows.append({"ticker": ticker, "facts": facts, "lite": lite, "models": model_results})
    write_report(rows, spent[0], out_path)
    return rows, spent[0]


def write_report(rows, spent, out_path):
    lines = ["# D-44a — AI Analist Notu pilotu (şirket notu, yan yana)", "",
              f"Modeller: {', '.join(MODELS)} (Claude anahtarı yok → Gemini varyant kıyası). "
              f"Toplam ölçülen maliyet: ${spent:.4f}", ""]
    for row in rows:
        lines.append(f"## {row['ticker']}")
        if row.get("error"):
            lines.append(f"- HATA: {row['error']}")
            lines.append("")
            continue
        lines.append("**Olgular:** " + "; ".join(f"{f['id']}={f['t']}={f['v']}" for f in row["facts"]))
        lines.append("")
        for model, res in row["models"].items():
            lines.append(f"**{model}:**")
            if res.get("skipped"):
                lines.append(f"- atlandı: {res['skipped']}")
            elif res.get("error"):
                lines.append(f"- hata: {res['error']}")
            elif res["ok"]:
                lines.append(f"- ✅ geçti (${res['cost_usd']}): {res['rendered']}")
            else:
                lines.append(f"- ❌ reddedildi ({res['reason']}): ham çıktı: {res['raw']!r}")
            lines.append("")
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))


def main(argv=None):
    p = argparse.ArgumentParser()
    p.add_argument("--tickers", default="THYAO,GARAN,TUPRS,BIMAS,ASELS")
    p.add_argument("--base-url", default=DEFAULT_BASE_URL)
    p.add_argument("--budget-usd", type=float, default=1.0)
    p.add_argument("--out", default="plans/2026-09-23-denetim/ai-pilot.md")
    args = p.parse_args(argv)
    api_key = os.environ.get("GEMINI_API_KEY", "")
    if not api_key:
        print("GEMINI_API_KEY yok, çağrı atılmadı.", file=sys.stderr)
        return 1
    tickers = [t.strip().upper() for t in args.tickers.split(",") if t.strip()]
    out_path = args.out if os.path.isabs(args.out) else os.path.join(
        os.path.expanduser("~/ops"), args.out)
    rows, spent = run_pilot(tickers, args.base_url, api_key, args.budget_usd, out_path)
    print(f"Bitti. {len(rows)} hisse, toplam ${spent:.4f}. Rapor: {out_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
