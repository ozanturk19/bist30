"""D-44a — AI Analist Notu pilotu (iki model yan yana) + D-44b ilk adım (üretim şirket notu).

Üretim (BIST30, gün sonu): olgu kurucu build_company_facts (yalnız KAP bloğu, trend ve koşullar, sektör
ortancası/sırası, son bildirimler), istem SYSTEM_PROMPT, cümle denetimi validate_sentences; iş ve okuma
yolu pipeline/ai_not_job.py. Pilot raporları (aşağıdaki run_* işlevleri) aynı olgu kurucuyu kullanır.

Kalite tarifi: ~/ops/plans/2026-09-23-denetim/ai-not-tarifi.md (CPO, 23.09).
Bu modül app.py'yi İMPORT ETMEZ (pipeline/intraday.py deseni) — girdi yalnız
sitenin kendi yayınladığı public API'si (/api/data, /api/hisse/<T>/fundamentals, /kap).
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
Her cümlede en az bir {Fn} olsun: olgu kimliği taşımayan cümle yayımlanmaz.
Şirketin ne iş yaptığını, ürününü, pazarını, yatırımını, yöneticisini yazma; olgu listesinde olmayan hiçbir \
şirket bilgisi yazma.
Neden-sonuç kurma ("nedeniyle", "sayesinde", "sağladı", "destekledi", "işaret ediyor" yok). Yorum sıfatı ve derece \
zarfı kullanma ("makul", "yeterli", "güçlü", "zayıf", "yüksek", "önemli ölçüde", "oldukça"); böyle bir sözcük \
yalnız ilgili olgunun değerinde geçiyorsa yazılır (ör. değerleme olgusunun değeri "pahalı tarafta" ise).
Sektör karşılaştırmasında "ortanca" de, "ortalama" deme; karşılaştırmayı iki olguyla birlikte ver \
("F/K {F7}, sektör ortancası {F8}"). Yıl ve dönemi yalnız olgu etiketindeki gibi yaz ("2025", "2026 2. çeyrek").
Yasak: AL / SAT / BEKLE kelimeleri ve "al", "sat", "almalı", "satmalı", "fırsat", "tavsiye", "önerilir"; \
teknik hedef dili (hedef fiyat, TP, kâr al, potansiyel, yükseliş beklentisi, "hedefe ulaştı"); \
göreli zaman ("bugün", "dün", "yarın", "günün"); kaynak adı ("KAP'a göre", "Reuters"); \
şirkete yargı ("zayıf şirket", "sağlam değil", "riskli hisse").
İzinli: ucuz/makul/pahalı DEĞERLEME betimi yalnız değerleme olgusunun değeriyle; trend durumu adı \
(Güçlü Trend / Yatay / Trend Bozuldu).
Her değişim olgusunu ({Fn} değeri +% ya da −% ile başlayan) kullandığın cümlede dönemini de yaz ("2025" ya da \
"2026 2. çeyrek" gibi, olgunun kendi etiketindeki gibi) — dönemsiz değişim cümlesi yayımlanmaz.
Bir parantezde en çok bir {Fn} olsun; aynı değeri cümlede iki kez yazma (ne aynı {Fn}'i tekrar, ne de kelimeyle \
yazıp parantezle tekrarlama — "Değerleme makul (makul)" YANLIŞ, "Trend durumu {F17}" DOĞRU, parantezsiz).
Bir cümle "ise", "ancak", "ama", "fakat", "da/de" ile BAŞLAMAZ (önceki cümleye bağımlı, tek başına anlamsız kalır).
Sıra: (1) son finansal tablonun ana hareketi, (2) bilanço/nakit, (3) değerleme bağlamı, (4) trend durumu tek cümle. \
KAP bildirimi olgusu varsa en çok bir kısa cümle (isteğe bağlı).
3-5 cümle, toplam en fazla 420 karakter. Çıktı YALNIZ JSON: {"note": "...", "facts_used": ["F1","F4"], "lang": "tr"}
"""

_BANNED_PATTERNS = [
    r"\b(AL|SAT|BEKLE)\b",
    r"(?i)\b(al(ın|malı)?|sat(ın|malı)?|fırsat|tavsiye|öneril|hedef|potansiyel|kâr al|beklenti)\b",
    r"(?i)\b(bugün|dün|yarın|günün)\b",
    r"(?i)(KAP'a göre|kaynak\s*:|reuters|bloomberg|anadolu ajansı)",
]
# BIST100/BIST30 (ve XU100/XU030): endeks adının kendisi rakam taşıyor (bülten modu), olgu değil.
_DATE_OK = re.compile(
    r"\b(19|20)\d{2}\b|\b\d{1,2}\s+(Ocak|Şubat|Mart|Nisan|Mayıs|Haziran|Temmuz|Ağustos|Eylül|Ekim|Kasım|Aralık)\b"
    r"|\bBIST\s?(100|30)\b|\bXU0?(100|30)\b")

# D-44a kalan #1 — bildirim özeti (tarifi §1: 1 cümle, ≤180 karakter). Girdi: bildirimin kendi
# KAP metni (/api/bildirim/<id>) + varsa onem (tutar/oran) olguları — web araması yok.
SYSTEM_PROMPT_BILDIRIM = """Rolün: BorsaPusula için KAP bildirimini TEK CÜMLEYLE özetleyen editör.
Sana bildirimin ham metni (KAP'ın kendi ifadeleriyle) ve varsa sayısal olgular ({Fn} kimlikli) verilir.
Metinden kimin ne yaptığını (taraf, işlem türü, konu) kendi cümlenle anlat; HİÇBİR sayıyı kendi kelimelerinle \
YAZMA — sayı gerekiyorsa yalnız verilen {Fn} kimliğini kullan (olgu yoksa sayı hiç verme, nitel anlat).
Yasak: AL / SAT / BEKLE ve "al", "sat", "almalı", "satmalı", "fırsat", "tavsiye", "önerilir"; \
teknik hedef dili (hedef fiyat, TP, kâr al, potansiyel, yükseliş beklentisi); \
göreli zaman ("bugün", "dün", "yarın", "günün"); kaynak adı ("KAP'a göre", "Reuters"); şirkete yargı.
Tek cümle, en fazla 180 karakter. Çıktı YALNIZ JSON: {"note": "...", "facts_used": ["F1"], "lang": "tr"}
"""

# D-44a kalan #2 — bülten metni (tarifi §1 ürün 4: 3-4 cümle, EOD sonrası, `/bulten/<tarih>`).
# Girdi: D-45'in zaten dondurduğu `data/bulten/<gün>.json` (bist100, sayim, hareketliler,
# durum_degisimleri, isi_haritasi_ozet, onemli_bildirimler) — web araması yok, yeni veri yok.
# Not: Gündem maddesi (tarifi §1 ürün 3) zaten D-57/gundem_haber.py'de üretim kodu + kendi
# doğrulayıcısıyla (BASLIK_MAX=70, OZET_MAX=260, yasak dil dahil) canlıdır — burada tekrar
# edilmez (bkz. ~/ops plan D-57); bu modül yalnız tarifinin henüz karşılığı olmayan 4. ürününü
# (bülten metni) kapsar.
SYSTEM_PROMPT_BULTEN = """Rolün: BorsaPusula için günün BIST100 bültenini 3-4 cümleyle özetleyen editör.
Sana günün kapanış olguları ({Fn} kimlikli) verilir. HİÇBİR sayıyı kendi kelimelerinle YAZMA — \
sayı gerekiyorsa yalnız verilen {Fn} kimliğini kullan; tarih ve gün adı hariç çıplak rakam yazma.
Yasak: AL / SAT / BEKLE ve "al", "sat", "almalı", "satmalı", "fırsat", "tavsiye", "önerilir"; \
teknik hedef dili (hedef fiyat, TP, kâr al, potansiyel, yükseliş beklentisi); \
göreli zaman ("bugün", "dün", "yarın", "günün"); kaynak adı ("KAP'a göre", "Reuters"); yargı.
Sıra: (1) BIST100'ün günü nasıl kapattığı, (2) yükselen/düşen hisse dengesi ya da öne çıkan sektör, \
(3) öne çıkan bir KAP bildirimi ya da trend durumu değişimi varsa tek cümle, (4) kapanış tek cümle.
3-4 cümle, toplam en fazla 500 karakter. Çıktı YALNIZ JSON: {"note": "...", "facts_used": ["F1","F3"], "lang": "tr"}
"""


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


def fetch_company_inputs(ticker, base_url, data_rows=None, get_json=None):
    """Şirket notunun girdisi — yalnız sitenin kendi uçları: /api/data satırı (trend durumu ve 5 koşul),
    /fundamentals (KAP bloğu, sektör ortancası ve sırası), /kap (son bildirimler). data_rows verilirse
    /api/data yeniden çekilmez (üretim işi tek kez çeker). Dönüş: (stock, fund, kap_rows)."""
    get = get_json or (lambda path: _get_json(path, base_url))
    if data_rows is None:
        data_rows = {r.get("ticker"): r for r in ((get("/api/data") or {}).get("stocks") or [])}
    stock = data_rows.get(ticker) or {}
    fund = (get(f"/api/hisse/{ticker}/fundamentals") or {}).get("fundamentals") or {}
    kap_rows = (get(f"/api/hisse/{ticker}/kap") or {}).get("disclosures") or []
    return stock, fund, kap_rows


def build_facts(ticker, base_url):
    """Olgu listesi: [{"id","t","v"}] (D-44b: yalnız KAP bloğu + trend + sektör sırası + bildirim;
    Yahoo alanları ve analist hedefi artık yok). Pilot raporu bu fonksiyonu kullanır."""
    stock, fund, kap_rows = fetch_company_inputs(ticker, base_url)
    if not stock or not fund:
        return None, stock, fund
    return build_company_facts(ticker, stock, fund, kap_rows), stock, fund


def facts_block(facts):
    """Modele giden olgu satırları: yalnız id/t/v (iç alanlar `_k/_g/_n` gitmez); json.dumps → KAP
    başlığındaki tırnak da satırı bozmaz."""
    return "\n".join(json.dumps({"id": f["id"], "t": f["t"], "v": f["v"]}, ensure_ascii=False,
                                separators=(",", ":")) for f in facts)


def build_bildirim_facts(idx, base_url):
    """Bildirim özeti olguları: tutar + oran (varsa, `onem`'den — kural tabanlı, AI üretmez).
    Ham KAP metni ayrıca döner (model narratifi oradan kurar, sayıyı oradan KOPYALAMAZ)."""
    payload = _get_json(f"/api/bildirim/{idx}", base_url)
    item = (payload or {}).get("item") or {}
    if not item:
        return None, None, None
    facts = []
    n = [0]

    def add(t, v):
        if v is None:
            return None
        n[0] += 1
        fid = f"F{n[0]}"
        facts.append({"id": fid, "t": t, "v": v})
        return fid

    onem = item.get("onem") or {}
    if onem.get("amount_txt"):
        add("Bildirilen tutar", onem["amount_txt"])
    if onem.get("txt") and onem.get("rev_year"):
        ratio = onem["txt"].replace("~", "yaklaşık ")
        add(f"Tutarın {onem['rev_year']} hasılatına oranı", ratio)
    text_block = (payload.get("text") or {}).get("text") or ""
    fields = (payload.get("text") or {}).get("fields") or []
    raw_context = {
        "company": item.get("company"), "class": item.get("class"), "subject": item.get("subject"),
        "title": item.get("title"), "text": text_block[:1500],
        "fields": [f"{lbl}: {val}" for lbl, val in fields[:15]],
    }
    return facts, item, raw_context


def build_bulten_facts(tarih, base_url):
    """Bülten olguları (D-45 dondurmuş JSON'dan — yeni veri çekilmez)."""
    path = f"/api/bulten/{tarih}" if tarih else "/api/bulten/latest"
    payload = _get_json(path, base_url)
    if not payload or not payload.get("bist100"):
        return None, None
    facts = []
    n = [0]

    def add(t, v):
        if v is None:
            return None
        n[0] += 1
        fid = f"F{n[0]}"
        facts.append({"id": fid, "t": t, "v": v})
        return fid

    b100 = payload.get("bist100") or {}
    add("BIST100 kapanış", _tr_num(b100.get("kapanis"), 2))
    add("BIST100 günlük değişim", _tr_pct(b100.get("degisim_pct")))
    sayim = payload.get("sayim") or {}
    if sayim.get("up") is not None and sayim.get("down") is not None:
        add("Yükselen hisse sayısı", str(sayim["up"]))
        add("Düşen hisse sayısı", str(sayim["down"]))
    isi = payload.get("isi_haritasi_ozet") or []
    if isi:
        en_guclu = isi[0]
        add("En güçlü sektör", en_guclu.get("sektor"))
        add("En güçlü sektör ortalama değişim", _tr_pct(en_guclu.get("ortalama_degisim_pct")))
    onemli = payload.get("onemli_bildirimler") or []
    if onemli:
        add("Öne çıkan KAP bildirimi sayısı", str(len(onemli)))
        ilk = onemli[0]
        add("En önemli bildirim", f"{ilk.get('company')} ({ilk.get('onem')})")
    durum = payload.get("durum_degisimleri") or []
    if durum:
        add("Trend durumu değişen hisse sayısı", str(len(durum)))
    return facts, payload


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


def validate_note(raw_text, facts, max_len=420):
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
    if len(rendered) > max_len:
        return False, None, f"uzunluk {len(rendered)} > {max_len}"
    return True, rendered, None


# ============================================================================================
# D-44b ilk adım (üretim, şirket notu) — KAP olguları + cümle cümle denetim.
# Model: flash-lite (O5c teknik karar, CPO 12.10: pilotta 10/10 geçti, en ucuz). Olgu listesi yalnız
# sitenin kendi verisinden: KAP bloğu (açıklanan rakamlar), trend durumu ve 5 koşul, sektör ortancası
# ve sırası, son rutin dışı bildirimler. Yahoo alanları ve analist hedefi girmez.
# Denetim cümle düzeyinde: eşlenemeyen (olgu kimliği yok / olgu dışı söz / yanlış sayı-tarih / yön ya da
# karşılaştırma çelişkisi / yasak dil / yargı / neden-sonuç / tahmin) cümle atılır; kalan ≥3 cümle
# değilse not yayımlanmaz. validate_note() (pilot: bildirim ve bülten) değişmedi.
# ============================================================================================
URETIM_MODEL = "gemini-2.5-flash-lite"
NOTE_MAX_LEN = 420
NOTE_MIN_SENT = 3
NOTE_MAX_SENT = 5
MAX_NOVEL = 1            # cümlede olgu, şirket adı ve nötr sözlük dışında en çok 1 sözcük
KAP_DAYS = 30
KAP_MAX = 2

_TR_MONTHS = ("Ocak", "Şubat", "Mart", "Nisan", "Mayıs", "Haziran", "Temmuz", "Ağustos", "Eylül",
              "Ekim", "Kasım", "Aralık")
_POSS = {0: "'ı", 1: "'i", 2: "'si", 3: "'ü", 4: "'ü", 5: "'i", 6: "'sı", 7: "'si", 8: "'i", 9: "'u"}
_BASIS_TXT = {"tms29": "enflasyon düzeltmeli", "banka": "nominal", "nominal": "nominal"}
_VERDICT_TXT = {"ucuz": "ucuz tarafta", "makul": "makul", "pahali": "pahalı tarafta", "karisik": "karışık"}
PAIRS = (("fk", "fk_ort"), ("pddd", "pddd_ort"), ("ozk", "ozk_ort"))


def _lower_tr(s):
    return (s or "").replace("I", "ı").replace("İ", "i").lower()


def _tr_chg(v, decimals=1):
    """Değişim: işaretli (+%28,2 / −%21,7), kanon §2.10."""
    if v is None:
        return None
    r = round(float(v), decimals)
    if r == 0:
        return "%" + _tr_num(0.0, decimals)
    return ("+" if r > 0 else "−") + "%" + _tr_num(abs(r), decimals)


_DON_METIN = {"kara_gecti": "kâra geçti", "zarara_dondu": "zarara döndü"}


def _tr_date(s):
    """'22.09.2026' | '2026-09-22' | '02.10.2026 18:24:08' → '22 Eylül 2026'."""
    s = (s or "").strip()
    m = re.match(r"^(\d{2})\.(\d{2})\.(\d{4})", s) or None
    if m:
        d, mo, y = int(m.group(1)), int(m.group(2)), int(m.group(3))
    else:
        m = re.match(r"^(\d{4})-(\d{2})-(\d{2})", s)
        if not m:
            return None
        y, mo, d = int(m.group(1)), int(m.group(2)), int(m.group(3))
    if not 1 <= mo <= 12:
        return None
    return "%d %s %d" % (d, _TR_MONTHS[mo - 1], y)


def _iso_of(s):
    m = re.match(r"^(\d{2})\.(\d{2})\.(\d{4})", (s or "").strip())
    if m:
        return "%s-%s-%s" % (m.group(3), m.group(2), m.group(1))
    m = re.match(r"^(\d{4}-\d{2}-\d{2})", (s or "").strip())
    return m.group(1) if m else None


def _quarter_label(donem):
    """'2026/06' → '2026 2. çeyrek' (12. ay yıllık rapordur → None)."""
    m = re.match(r"^(\d{4})/(\d{2})$", donem or "")
    if not m or m.group(2) not in ("03", "06", "09"):
        return None
    return "%s %d. çeyrek" % (m.group(1), int(m.group(2)) // 3)


_POSS_TENS = {1: "'u", 2: "'si", 3: "'u", 4: "'ı", 5: "'si", 6: "'ı", 7: "'i", 8: "'i", 9: "'ı"}


def _poss(n):
    """Sayının iyelik eki (4'ü, 7'si, 10'u) — 'beş koşuldan 4'ü', '9 maddenin 7'si'."""
    n = abs(int(n))
    if n % 10:
        return _POSS[n % 10]
    return _POSS_TENS.get((n // 10) % 10, "'ü") if n else _POSS[0]


_COND_COUNT_TXT = "{n} koşuldan {k}{s}"


def build_company_facts(ticker, stock, fund, kap_rows=None, today=None):
    """Saf olgu kurucu (ağ yok). stock: /api/data satırı; fund: /fundamentals 'fundamentals'; kap_rows:
    /kap 'disclosures'. Olgu: {"id","t","v"} + iç alanlar _k (tür), _g (grup), _n (sayısal değer,
    gösterilen yuvarlamayla). Sayılar sitenin gösterdiği biçimde (kanon §2.10)."""
    import temel_skor_v2   # kanon §5.6 değerleme hükmü (hisse sayfası "Fiyatı makul mu?" ile aynı kural)
    stock, fund = stock or {}, fund or {}
    facts = []

    def add(t, v, kind, grup=None, n=None):
        if v in (None, ""):
            return None
        fid = "F%d" % (len(facts) + 1)
        facts.append({"id": fid, "t": t, "v": v, "_k": kind, "_g": grup, "_n": n})
        return fid

    kap = (fund.get("kap") or {}) if fund.get("kap_durum") == "var" else {}
    flags = kap.get("flags") or {}
    bank = bool(flags.get("banka")) or kap.get("sablon") == "banka"
    basis = kap.get("basis")
    cur = fund.get("financial_currency") or fund.get("statement_currency")
    if basis == "yabanci_para":
        basis_txt = "%s cinsinden rapor" % cur if cur and cur != "TRY" else None
    else:
        basis_txt = _BASIS_TXT.get(basis)
    suffix = " (%s)" % basis_txt if basis_txt else ""
    money_ok = basis in ("tms29", "nominal", "banka")

    # (1) son finansal tablonun ana hareketi — şirketin kendi raporundaki karşılaştırma
    rev_key, rev_lbl = ("net_interest_income", "Net faiz geliri") if bank else ("revenue", "Hasılat")
    yd = kap.get("yillik_degisim") or {}
    years = sorted(y for y in yd if isinstance(yd.get(y), dict) and yd.get(y))
    if years:
        y, row = years[-1], yd[years[-1]]
        if row.get(rev_key) is not None:
            add("%s, %s yıllık değişim%s" % (rev_lbl, y, suffix), _tr_chg(row[rev_key]["pct"]), "degisim", "gelir",
                round(row[rev_key]["pct"], 1))
        ni = row.get("net_income_parent")
        if ni is not None:
            metin = _DON_METIN.get(ni.get("don"))
            if metin:
                # işaret dönüşü (CPO 13.10 madde 4): kardan zarara/zarardan kara geçişte yüzde
                # yanıltıcı olur (|değişim| hep >%100) — metin olgusu kullanılır, yüzde verilmez.
                add("Net kâr, %s karşılaştırması%s" % (y, suffix), metin, "durum", "kar")
            else:
                add("Net kâr, %s yıllık değişim%s" % (y, suffix), _tr_chg(ni["pct"]), "degisim", "kar",
                    round(ni["pct"], 1))
    son = (kap.get("son_rapor") or {}).get("donem")
    q = _quarter_label(son) if son and son != kap.get("son_yillik") else None
    cd = ((kap.get("ceyreklik_degisim") or {}).get(son) or {}) if q else {}
    if cd.get(rev_key) is not None:
        add("%s değişimi, %s (önceki yılın aynı çeyreğine göre)" % (rev_lbl, q), _tr_chg(cd[rev_key]["pct"]),
            "degisim", "gelir_q", round(cd[rev_key]["pct"], 1))
    ni_q = cd.get("net_income_parent")
    if ni_q is not None:
        metin_q = _DON_METIN.get(ni_q.get("don"))
        if metin_q:
            add("Net kâr karşılaştırması, %s (önceki yılın aynı çeyreğine göre)" % q, metin_q, "durum", "kar_q")
        else:
            add("Net kâr değişimi, %s (önceki yılın aynı çeyreğine göre)" % q, _tr_chg(ni_q["pct"]),
                "degisim", "kar_q", round(ni_q["pct"], 1))

    # (2) bilanço / nakit
    bil = kap.get("bilanco") or {}
    bcur, by = bil.get("cur") or {}, bil.get("yil")
    if by:
        if bank:
            km = bcur.get("kredi_mevduat")
            if km is not None:
                add("Kredi/mevduat oranı, %s sonu" % by, _tr_pct(km, 1), "oran", "km", round(km, 1))
            gg = ((kap.get("oranlar") or {}).get(str(by)) or {}).get("gider_gelir")
            if gg is not None:
                add("Gider/gelir oranı, %s" % by, _tr_pct(gg, 1), "oran", "gg", round(gg, 1))
        else:
            nb, fv, nbf = bcur.get("net_borc"), bcur.get("favok"), bcur.get("net_borc_favok")
            if nb is not None and nb < 0:
                if money_ok:
                    add("Net nakit, %s sonu" % by, _tr_num(-nb / 1e9, 1) + " Mrd ₺", "tutar", "net_nakit",
                        round(-nb / 1e9, 1))
                else:
                    add("Net borç durumu, %s sonu" % by, "net nakit", "durum", "net_nakit")
            elif nb is not None and nbf is not None and (fv or 0) > 0:
                add("Net borç/FAVÖK, %s" % by, _tr_num(nbf, 2), "oran", "nb_favok", round(nbf, 2))
            cr = bcur.get("cari_oran")
            if cr is not None:
                add("Cari oran (dönen varlıklar / kısa vadeli borçlar), %s sonu" % by, _tr_num(cr, 2), "oran",
                    "cari", round(cr, 2))
    sg = kap.get("saglamlik") or {}
    if sg.get("puan") is not None and sg.get("toplam"):
        add("Sağlamlık kontrolü, %s (geçen madde)" % sg.get("yil"),
            "%d maddenin %d%s" % (sg["toplam"], sg["puan"], _poss(sg["puan"])), "sayim", "saglamlik", sg["puan"])

    # (3) değerleme — hisse sayfası Q2 ile aynı sayılar ve aynı kural (kanon §5.6)
    ds = kap.get("degerleme_simdi") or {}
    med = fund.get("sektor_ortanca") or {}
    sira = fund.get("sektor_sira") or {}
    pay_ok = not ds.get("pay_uyumsuz")

    def med_lbl(m):
        return "Sektör ortancası" if (m or {}).get("kapsam") == "sektor" else "BIST ortancası"

    ratios, used = [], []
    for key, grup, lbl, dec in (("fk", "fk", "F/K (son 12 ay kârıyla)", 1),
                                ("pd_dd", "pddd", "PD/DD (son açıklanan özkaynakla)", 2)):
        v = ds.get(key) if pay_ok else None
        if v is None or v <= 0:
            continue
        add(lbl, _tr_num(v, dec), "oran", grup, round(v, dec))
        m = med.get(key) or {}
        if (m.get("deger") or 0) > 0:
            add("%s %s" % (med_lbl(m), "F/K" if key == "fk" else "PD/DD"), _tr_num(m["deger"], dec), "oran",
                grup + "_ort", round(m["deger"], dec))
            ratios.append(v / m["deger"])
            used.append("F/K" if key == "fk" else "PD/DD")
    roe = ds.get("ozsermaye_karliligi")
    if roe is not None:
        add("Özsermaye kârlılığı (son 12 ay)", _tr_pct(roe, 1), "oran", "ozk", round(roe, 1))
        m = med.get("ozsermaye_karliligi") or {}
        if m.get("deger") is not None:
            add("%s özsermaye kârlılığı" % med_lbl(m), _tr_pct(m["deger"], 1), "oran", "ozk_ort",
                round(m["deger"], 1))
    for key, lbl in (("fk", "F/K'da sektör sırası (en düşük F/K birinci)"),
                     ("ozsermaye_karliligi", "Özsermaye kârlılığında sektör sırası (en yüksek birinci)")):
        s = sira.get(key) if (pay_ok or key != "fk") else None
        if s and s.get("sira") and s.get("toplam"):
            add(lbl, "%d şirket arasında %d. sırada" % (s["toplam"], s["sira"]), "sira", key + "_sira", s["sira"])
    verdict = temel_skor_v2.valuation_verdict(ratios) if ratios else None
    if verdict:
        add("Değerleme (%s, ortancaya göre)" % " ve ".join(used), _VERDICT_TXT[verdict], "hukum", "degerleme")

    # (4) trend durumu ve koşullar (motorun kendi kaydı, D-47)
    trend = SIGNAL_LABELS.get(stock.get("signal"))
    if trend:
        add("Trend durumu", trend, "durum", "trend")
        add("Trend durumunun başladığı tarih", _tr_date(stock.get("signal_date")), "tarih", "trend_tarih")
        conds = stock.get("conditions") or []
        if conds:
            k = sum(1 for c in conds if c.get("ok"))
            add("Sağlanan trend koşulu", _COND_COUNT_TXT.format(n=len(conds), k=k, s=_poss(k)), "sayim", "kosul", k)

    # (5) son rutin dışı şirket bildirimleri (isteğe bağlı; finansal rapor duyurusu (1)'de zaten var)
    ref = today or _iso_of(stock.get("bar_date"))
    picked = []
    for r in kap_rows or []:
        iso = _iso_of(r.get("date"))
        title = re.sub(r"\s+", " ", (r.get("summary") or "")).strip()
        if not iso or not title or r.get("rutin") or (r.get("class") or r.get("type")) != "ODA":
            continue
        if ref and iso < _days_before(ref, KAP_DAYS):
            continue
        if re.search(r"(?i)finansal (tablo|rapor)", title) or any(re.search(p, title) for p in _BANNED_ALL):
            continue
        letters = [c for c in title if c.isalpha()]
        if letters and sum(c.isupper() for c in letters) > 0.7 * len(letters):
            continue   # TAMAMI BÜYÜK HARF başlık nota olduğu gibi girmez (Türkçe küçültme riski almıyoruz)
        if any(_lower_tr(title) == _lower_tr(t) for _, t in picked):
            continue   # aynı başlık iki kez (büyük/küçük harf farkıyla da) girmez
        picked.append((iso, title[:120]))
    for iso, title in sorted(picked, reverse=True)[:KAP_MAX]:
        add("Şirket bildirimi, %s" % _tr_date(iso), title, "bildirim", "kap")
    return facts


def _days_before(iso, days):
    from datetime import date, timedelta
    try:
        y, m, d = (int(x) for x in iso.split("-"))
        return (date(y, m, d) - timedelta(days=days)).isoformat()
    except (ValueError, AttributeError):
        return "0000-00-00"


def facts_signature(facts, model=URETIM_MODEL, prompt=None):
    """Girdi imzası: olgular (id/t/v) + model + istem. Aynı imza → yeni çağrı yok (veri değişmedi)."""
    import hashlib
    body = json.dumps([{"id": f["id"], "t": f["t"], "v": f["v"]} for f in facts], ensure_ascii=False,
                      sort_keys=True, separators=(",", ":"))
    h = hashlib.sha256()
    for part in (body, model, prompt if prompt is not None else SYSTEM_PROMPT):
        h.update(part.encode("utf-8"))
        h.update(b"\x00")
    return h.hexdigest()


def company_user_content(ticker, name, facts, feedback=None):
    s = "Şirket: %s (%s)\nOlgular:\n%s" % (name or ticker, ticker, facts_block(facts))
    if feedback:
        s += "\n\n" + feedback
    return s


# ---- cümle denetimi ---------------------------------------------------------------------------
# Tarifi §4'ün dört kalıbı aynen (_BANNED_PATTERNS) + üretim genişletmesi: çekimli göreli zaman,
# işlem/hedef dili, şirkete yargı ve üstünlük iddiası, gri dil, kaynak adı.
_BANNED_EXTRA = [
    r"(?i)\b(?:öneri\w*|önerir\w*|önerilir\w*|tavsiye\w*|fırsat\w*|hedef\w*|potansiyel\w*|beklenti\w*)",
    r"(?i)\b(?:almalı\w*|satmalı\w*|alım fırsat\w*|kâr al\w*|kar al\w*|zarar kes\w*|stop\w*|TP\d|R/R|risk/ödül)",
    r"(?i)\bgiriş (?:fiyat|bölge|seviye|nokta)\w*|\bdirenç\w*|\bdestek seviye\w*|\bprim yap\w*",
    r"(?i)\b(?:bugün\w*|yarın\w*|dün(?:kü|den|de|e|ü|ün)?|günün|şimdi\w*|haftaya|yakında|son günlerde)\b",
    r"(?i)\b(?:bu|geçen|gelecek|önümüzdeki|geçtiğimiz)\s+(?:gün|hafta|ay|yıl|sene|çeyrek|dönem)\w*",
    r"(?i)\b(?:zayıf|güçlü|sağlam|riskli|kötü|iyi|cazip|değerli|değersiz)\s+(?:bir\s+)?(?:şirket|hisse|firma|banka|holding)\w*",
    r"(?i)\b(?:şirket|hisse|firma)\w*\s+(?:zayıf|güçlü|sağlam|riskli|cazip|kötü)\b",
    r"(?i)\ben büyük\w*|\ben iyi\w*|\blider\w*|\böncü\w*|pazar pay\w*|\bdev\b",
    r"(?i)\b(?:kısmi\w*|ücretsiz\w*)|verisi\s*%",
    r"(?i)(?:yahoo|finnet|matriks|kap'a göre|kap’a göre|kaynağa göre)",
]
_BANNED_ALL = list(_BANNED_PATTERNS) + _BANNED_EXTRA
_CAUSAL_RE = re.compile(
    r"(?i)\b(?:nedeniyle|yüzünden|sayesinde|etkisiyle|dolayı\w*|kaynakl\w*|bağlı olarak|sonucunda|"
    r"yol aç\w*|katkı\w*|destekle\w*|sağladı\w*|sağlamış\w*|sağlayarak|yansı\w*|işaret\w*|anlamına|"
    r"böylece|dolayısıyla|bu nedenle|bu da\b|bunun sonucu\w*)")
_FUTURE_RE = re.compile(
    r"(?i)\b(?!(?:içecek|yiyecek|giyecek)\b)\w+(?:acak|ecek|acağ|eceğ)\w*|\b(?:beklen\w*|öngör\w*|tahmin\w*|"
    r"muhtemel\w*|olası\w*|olabilir\w*|edebilir\w*|sürebilir\w*|gelecek\w*)")
_AVG_RE = re.compile(r"(?i)\bortalama\w*")
# yargı/derece sözcükleri: yalnız cümlenin dayandığı olgunun metninde geçiyorsa (ör. "pahalı tarafta")
_JUDGE_RE = re.compile(
    r"(?i)\b(makul\w*|ucuz\w*|pahal\w*|karışık\w*|güçlü\w*|zayıf\w*|sağlam\w*|sağlıklı\w*|yeterli\w*|"
    r"yetersiz\w*|iyi|kötü\w*|olumlu\w*|olumsuz\w*|önemli\w*|ciddi\w*|belirgin\w*|dikkat çek\w*|sınırlı\w*|"
    r"oldukça|çok|yönetilebilir\w*|uyumlu\w*|riskl\w*|risk|cazip\w*|başarı\w*|istikrar\w*|rekor\w*|sert\w*|"
    r"keskin\w*|hızl[ıa]\w*|yavaş\w*|kayda değer|zirve\w*|güvenl\w*|endişe\w*|kaygı\w*|yüksek\w*|düşük\w*|"
    r"fazla\w*|az|negatif\w*|pozitif\w*)\b")
_UP_CMP = re.compile(r"(?i)\b(?:üstünde\w*|üzerinde\w*|yüksek\w*|fazla\w*|aşıyor|aştı)\b")
_DN_CMP = re.compile(r"(?i)\b(?:altında\w*|gerisinde\w*|düşük\w*|az)\b")
_EQ_CMP = re.compile(r"(?i)\b(?:yakın\w*|eşit\w*|benzer\w*|paralel\w*)\b|\baynı (?:seviye|düzey)\w*")
_UP_DIR = re.compile(r"(?i)\b(?:art(?:tı|ış\w*|arak|mış\w*|an|ıyor)|artır\w*|yüksel\w*|büyü(?:dü|me\w*|yerek|"
                     r"müş\w*|yen|yor)|iyileş\w*|toparlan\w*|güçlen\w*)\b")
_DN_DIR = re.compile(r"(?i)\b(?:azal\w*|geril\w*|düş(?:tü|üş\w*|erek|müş\w*|en|üyor)|daral\w*|kötüleş\w*|"
                     r"zayıfla\w*|küçül\w*|kayb\w*)\b")
_NEG_SIGN = re.compile(r"(?i)\b(?:negatif\w*|eksi\w*|zarar\w*)\b")
_POS_SIGN = re.compile(r"(?i)\b(?:pozitif\w*|kâra geç\w*|kara geç\w*)\b")
_CLAUSE_SPLIT = re.compile(r";|,\s|\s(?:ve|ancak|ama|fakat|ise|buna karşılık|öte yandan)\s")
_SENT_SPLIT = re.compile(r"(?<=[.!?])\s+(?=[A-ZÇĞİÖŞÜ{(\"'“]|\d)")   # "2. çeyrek" küçük harfle sürer
_PERIOD_RE = re.compile(r"(?:19|20)\d{2}(?:\s+\d\.\s*çeyrek)?")
_DANGLING_START_RE = re.compile(r"(?i)^(ise|ancak|ama|fakat|da|de|dahi|üstelik|öte yandan|buna karşılık)\b")
_PH = re.compile(r"\{(F\d+)\}")
_WORD = re.compile(r"[A-Za-zÇĞİÖŞÜÂÎÛçğıöşüâîû]+")
_NUM_TOK = re.compile(r"\d+(?:[.,]\d+)*")
_MONTHS_RE = "|".join(_TR_MONTHS)
_BARE_OK = re.compile(
    r"\b\d{1,2}\s+(?:%s)(?:\s+(?:19|20)\d{2})?|\b[1-4]\.\s*çeyre\w*|\bson\s+12\s+ay\w*|\b(?:19|20)\d{2}\b"
    % _MONTHS_RE)
_STOP = set("""ve ile da de ki bu şu o bir en mi mı mu mü ise için gibi daha olarak kadar göre ya veya hem ne
ama fakat ancak ayrıca yanı sıra""".split())
_NEUTRAL_WORDS = """şirket şirketin şirketi şirketinin hisse hissenin hissesi bilanço bilançoda bilançosu finansal tablo
tablolar tablosunda rapor raporda raporu raporunda dönem dönemde döneminde yıl yılı yılında yıllık çeyrek çeyrekte
çeyreğinde ilk yarı yarısında son aynı oranla oran oranı oranında değer değeri değerinde düzey düzeyinde seviye
seviyesinde durum durumu durumda durumunda var yok oldu olan olup olmuş olduğu olarak birlikte öte yandan buna
karşılık kendi açıkladığı açıklanan açıkladı karşılaştırma kaydetti kaydedildi gösterdi gösteriyor izliyor izledi
seyrediyor sürüyor bulunuyor devam ediyor yer alıyor başladı başlayan beri itibarıyla tarihinden tarihinde tarihli
tarihte kapanış kapanışı toplam değişim değişimi değişti koşul koşulu koşuldan koşulun koşulları sağlanıyor
sağlanmıyor sağlandı madde maddesi maddeden geçti geçen sırada sırası sıralamada arasında içinde üstünde üzerinde
altında gerisinde yakın eşit benzer paralel aşıyor arttı artış artışı artarak artırdı yükseldi yükseliş yükselişi
büyüdü büyüme büyümesi geriledi gerileme gerilemesi azaldı azalış düştü düşüş düşüşü daraldı daralma iyileşti
kötüleşti toparlandı yön döndü dönüş ise yönünde bildirim bildirimi yayımladı yayımlanan duyurdu açıklama başlıklı
konulu hakkında ilişkin ilgili mevcut buna bunun""".split()


def _stem(w):
    return w[:5] if len(w) > 5 else w


_NEUTRAL = set(_stem(_lower_tr(w)) for w in _NEUTRAL_WORDS)


def _vocab(texts):
    words = set()
    for t in texts:
        for w in _WORD.findall(t or ""):
            lw = _lower_tr(w)
            if len(lw) >= 3:
                words.add(lw)
    return words


def _grounded(lw, vocab, vocab_stems):
    if _stem(lw) in vocab_stems:
        return True
    for fw in vocab:
        if len(fw) >= 4 and (lw.startswith(fw) or (len(lw) >= 4 and fw.startswith(lw))):
            return True
        if len(fw) == 3 and lw.startswith(fw) and len(lw) - 3 <= 4:   # kâr → kârı, kârında (yalnız ek)
            return True
    return False


def _split_sentences(note):
    return [s.strip() for s in _SENT_SPLIT.split((note or "").strip()) if s.strip()]


def _render(text, fmap):
    return _PH.sub(lambda m: fmap[m.group(1)]["v"] if m.group(1) in fmap else m.group(0), text)


def _rounded_pair(fmap, ids, ga, gb):
    a = next((fmap[i] for i in ids if fmap[i].get("_g") == ga), None)
    b = next((fmap[i] for i in ids if fmap[i].get("_g") == gb), None)
    return (a, b) if a and b and a.get("_n") is not None and b.get("_n") is not None else (None, None)


_KEY_GENERIC = set("""yıllık değişim değişimi son sonu önceki yılın aynı çeyreğine göre birinci geçen madde
olarak ile oranı""".split())


def _period_phrase(label):
    """Olgu etiketindeki dönem ifadesi ('2025' ya da '2026 2. çeyrek') — değişim cümlesinin aynı dönemi
    taşıması zorunlu (tarifi §madde-3, dönemsiz değişim cümlesi atılır)."""
    m = _PERIOD_RE.search(label or "")
    return m.group(0) if m else None


def _fact_keys(f):
    """Olgu etiketinin ayırt edici sözcükleri (kök) + F/K, PD/DD, FAVÖK gibi kısaltmalar."""
    low = _lower_tr(f["t"])
    keys = set(k for k in ("f/k", "pd/dd", "favök") if k in low)
    for w in _WORD.findall(low):
        if len(w) >= 3 and w not in _KEY_GENERIC and w not in _STOP and not w.isdigit():
            keys.add(_stem(w))
    return keys


def _split_outside_parens(s):
    """';' ve ', ' ile böl; parantez içindeki virgül ('(%22,9, %19,9)') bölmez."""
    out, depth, cur, i = [], 0, [], 0
    while i < len(s):
        c = s[i]
        depth += (c == "(") - (c == ")")
        if depth <= 0 and (c == ";" or (c == "," and s[i + 1:i + 2] == " ")):
            out.append("".join(cur))
            cur = []
        else:
            cur.append(c)
        i += 1
    out.append("".join(cur))
    return [x for x in out if x.strip()]


def check_sentence(sent, fmap, vocab, vocab_stems, name_words=()):
    """Tek cümle → ret kodları listesi (boş = geçer). fmap: {id: olgu}. Ağ yok."""
    ret = []
    ids = _PH.findall(sent)
    if not ids:
        return ["olgu_yok"]
    unknown = [i for i in ids if i not in fmap]
    if unknown:
        return ["tanimsiz_olgu:" + ",".join(unknown)]
    refs = [fmap[i] for i in dict.fromkeys(ids)]
    ref_text = _lower_tr(" ".join("%s %s" % (f["t"], f["v"]) for f in refs))
    ref_words = _vocab([ref_text])
    pre = _PH.sub(" ", sent)
    # biçim: % ya da ₺ ya da işaret olgu kimliğine yapışık ("%{F1}" → "%−%21,7"), iki kimlik bitişik
    if re.search(r"[%₺+−-]\s*\{F\d+\}|\d\{F\d+\}|\{F\d+\}\s*[%₺]|\{F\d+\}\d|\{F\d+\}\{F\d+\}", sent):
        ret.append("bicim")
    # yankı parantezi + değer yığını: metin olgusu (durum/hukum) parantezde hiç basılmaz (zaten cümlede
    # çıplak ya da {Fn} ile var — parantezdeki tekrarı okunabilirliği bozar); bir parantezde en çok bir {Fn}
    for grp in re.findall(r"\(([^()]*)\)", sent):
        grp_ids = _PH.findall(grp)
        if len(grp_ids) > 1:
            ret.append("deger_yigini")
        for gid in grp_ids:
            if fmap.get(gid, {}).get("_k") in ("hukum", "durum"):
                ret.append("yanki_parantez")
                break
    # çıplak rakam: yalnız tarih/yıl/çeyrek kalıbı ve yalnız dayandığı olgunun metninde geçiyorsa
    rest = pre
    for m in _BARE_OK.finditer(pre):
        core = _lower_tr(re.sub(r"\s+", " ", m.group(0)))
        core = re.sub(r"\.\s*çeyre\w*", ". çeyrek", core)
        core = re.sub(r"\bay\w*$", "ay", core)
        if core in ref_text:
            rest = rest.replace(m.group(0), " ", 1)
    if re.search(r"\d", rest):
        ret.append("ciplak_rakam")
    # dönemsiz cümle: değişim olgusu kullanan cümle kendi dönemini (olgu etiketindeki yıl/çeyrek) de taşır
    if "ciplak_rakam" not in ret:
        low_pre = _lower_tr(pre)
        for i in dict.fromkeys(ids):
            f = fmap.get(i, {})
            if f.get("_k") != "degisim":
                continue
            phrase = _period_phrase(f.get("t"))
            if phrase and _lower_tr(phrase) not in low_pre:
                ret.append("donem_yok")
                break
    for pat in _BANNED_ALL:
        if re.search(pat, pre):
            ret.append("yasak_dil")
            break
    if _CAUSAL_RE.search(pre):
        ret.append("neden_sonuc")
    if _FUTURE_RE.search(pre):
        ret.append("tahmin")
    if _AVG_RE.search(pre):
        ret.append("ortalama")
    # karşılaştırma (F/K ↔ ortanca vb.): sözcüğün yönü gösterilen sayılarla tutarlı olmalı; çifti olmayan
    # karşılaştırma sözcüğü ("borçluluk yüksek") yargıdır — dayandığı olgunun metninde yoksa atılır
    sent_pairs = [(a, b) for a, b in (_rounded_pair(fmap, ids, ga, gb) for ga, gb in PAIRS) if a is not None]
    checked = set()
    for cl in (c for c in _CLAUSE_SPLIT.split(sent) if c and c.strip()):
        body = _PH.sub(" ", cl)
        found = [(k, _lower_tr(m.group(0))) for rx, k in ((_UP_CMP, ">"), (_DN_CMP, "<"), (_EQ_CMP, "="))
                 for m in rx.finditer(body)]
        if not found:
            continue
        cl_ids = _PH.findall(cl)
        pair = next(((a, b) for a, b in sent_pairs if a["id"] in cl_ids or b["id"] in cl_ids), None)
        if pair is None and len(sent_pairs) == 1:
            pair = sent_pairs[0]
        for k, w in found:
            checked.add(w)
            if pair is None:
                if not (w in ref_text or _stem(w) in ref_text):
                    ret.append("yargi:" + w)
                continue
            x, y = pair[0]["_n"], pair[1]["_n"]
            if (k == ">" and not x > y) or (k == "<" and not x < y) or \
                    (k == "=" and not (y != 0 and abs(x / y - 1) <= 0.10)):
                ret.append("karsilastirma:%s/%s" % (pair[0]["id"], pair[1]["id"]))
    # eşleşme: her {Fn} kendi yan cümlesinde olgunun konusuyla birlikte anılır ("değerleme {F17}" ama F17 trend
    # durumuysa → yanlış olguya bağlanmış cümle). Parantez içindeki virgül yan cümle bölmez.
    for cl in _split_outside_parens(sent):
        low = _lower_tr(_PH.sub(" ", cl))
        for i in dict.fromkeys(_PH.findall(cl)):
            keys = _fact_keys(fmap[i])
            if keys and not any(k in low for k in keys):
                ret.append("eslesme:" + i)
    # yön (arttı/geriledi) ve işaret (negatif) — değişim olgusunun işaretiyle çelişmemeli
    deg_all = [i for i in dict.fromkeys(ids) if fmap[i].get("_k") == "degisim"]
    for cl in re.split(r";|,\s", sent):
        body = _PH.sub(" ", cl)
        up, dn = bool(_UP_DIR.search(body)), bool(_DN_DIR.search(body))
        parts = [cl] if up != dn else re.split(r"\s(?:ve|ancak|ama|fakat|ise|buna karşılık)\s", cl)
        for p in parts:
            pb = _PH.sub(" ", p)
            pu, pd = bool(_UP_DIR.search(pb)), bool(_DN_DIR.search(pb))
            if pu == pd:
                continue
            cl_deg = [i for i in _PH.findall(p) if fmap.get(i, {}).get("_k") == "degisim"]
            for i in cl_deg or (deg_all if len(deg_all) == 1 else []):
                n = fmap[i].get("_n")
                if n is not None and ((pu and not n > 0) or (pd and not n < 0)):
                    ret.append("yon:" + i)
        neg, pos = bool(_NEG_SIGN.search(body)), bool(_POS_SIGN.search(body))
        if neg or pos:
            nums = [fmap[i] for i in _PH.findall(cl) if fmap.get(i, {}).get("_n") is not None] or \
                   [f for f in refs if f.get("_n") is not None][:1]
            if not nums:
                ret.append("isaret")
            for f in nums:
                if (neg and not f["_n"] < 0) or (pos and not f["_n"] > 0):
                    ret.append("isaret:" + f["id"])
    # cari oran "karşılıyor" ancak oran ≥1 ise
    if re.search(r"(?i)karşıla", pre):
        cari = next((f for f in refs if f.get("_g") == "cari"), None)
        negated = bool(re.search(r"(?i)karşıla(?:mıyor|mamakta|yamıyor|madı)", pre))
        if cari is None or (negated and not cari["_n"] < 1) or (not negated and not cari["_n"] >= 1):
            ret.append("karsilama")
    # yargı/derece sözcüğü: dayandığı olgunun metninde yoksa (karşılaştırma çiftiyle denetlenenler hariç)
    for m in _JUDGE_RE.finditer(pre):
        w = _lower_tr(m.group(0))
        if w in checked or _NEG_SIGN.fullmatch(w) or _POS_SIGN.fullmatch(w):
            continue
        if not (_stem(w) in ref_text or any(rw.startswith(_stem(w)) for rw in ref_words)):
            ret.append("yargi:" + w)
    # dayanak: sözcükler olguda, şirket adında ya da nötr sözlükte; büyük harfli (özel ad) sözcükte tolerans yok
    novel, proper = [], []
    for raw in _WORD.findall(re.sub(r"[’'][A-Za-zÇĞİÖŞÜçğıöşü]+", "", pre)):
        lw = _lower_tr(raw)
        if len(lw) < 3 or lw in _STOP or _stem(lw) in _NEUTRAL:
            continue
        if _JUDGE_RE.fullmatch(lw) or _UP_DIR.fullmatch(lw) or _DN_DIR.fullmatch(lw):
            continue
        if lw in name_words or _grounded(lw, vocab, vocab_stems):
            continue
        (proper if raw[:1].isupper() else novel).append(lw)
    if proper:
        ret.append("ad:" + ",".join(proper[:3]))
    if len(novel) > MAX_NOVEL:
        ret.append("dayanak:" + ",".join(novel[:4]))
    # yerleştirme sonrası: yasak dil (olgu değerleri dahil) ve her sayı dayandığı olgularda
    rendered = _render(sent, fmap)
    if not any(r == "yasak_dil" for r in ret) and any(re.search(p, _PH.sub(" ", rendered)) for p in _BANNED_ALL):
        ret.append("yasak_dil_olgu")
    ok_nums = set(_NUM_TOK.findall(" ".join("%s %s" % (f["t"], f["v"]) for f in refs)))
    if any(n not in ok_nums for n in _NUM_TOK.findall(rendered)) and "ciplak_rakam" not in ret:
        ret.append("sayi")
    return list(dict.fromkeys(ret))


def validate_sentences(raw_text, facts, name="", ticker="", max_len=NOTE_MAX_LEN, min_sent=NOTE_MIN_SENT,
                       max_sent=NOTE_MAX_SENT, extra_words=()):
    """Üretim doğrulayıcısı (tarifi §4 + cümle düzeyi). Dönüş sözlüğü:
    {ok, not (yerleştirilmiş metin | None), cumleler: [{ham, metin, olgular, ret}], sebep, facts_used}.
    Geçemeyen cümle atılır; kalan cümle sayısı min_sent altındaysa not yayımlanmaz (ok=False)."""
    out = {"ok": False, "not": None, "cumleler": [], "sebep": None, "facts_used": []}
    try:
        parsed = json.loads(raw_text)
        note = parsed.get("note", "")
        facts_used = parsed.get("facts_used", [])
    except (json.JSONDecodeError, AttributeError, TypeError):
        out["sebep"] = "json"
        return out
    if not isinstance(note, str) or not note.strip():
        out["sebep"] = "bos_not"
        return out
    fmap = {f["id"]: f for f in facts}
    if not isinstance(facts_used, list) or not set(map(str, facts_used)) <= set(fmap):
        out["sebep"] = "facts_used"   # tarifi §4: facts_used ⊆ verilen olgular
        return out
    name_words = set(_lower_tr(w) for w in _WORD.findall("%s %s" % (name or "", ticker or "")) if len(w) >= 3)
    vocab = _vocab(["%s %s" % (f["t"], f["v"]) for f in facts] + [name or "", ticker or ""] + list(extra_words))
    vocab_stems = set(_stem(w) for w in vocab)
    kept = []
    prev_idx = -1
    for idx, s in enumerate(_split_sentences(note)):
        ret = check_sentence(s, fmap, vocab, vocab_stems, name_words)
        rec = {"ham": s, "metin": _render(s, fmap), "olgular": list(dict.fromkeys(_PH.findall(s))), "ret": ret}
        out["cumleler"].append(rec)
        if not ret:
            # kopuk bağlaç: öncesindeki cümle(ler) atıldıysa ve bu cümle "ise/ancak/..." ile başlıyorsa
            # (önceki cümleye bağımlı, tek başına anlamsız kalır) o da yayımlanmaz (tarifi §madde-5)
            if idx - prev_idx > 1 and _DANGLING_START_RE.match(rec["metin"].strip()):
                rec["ret"] = ["kopuk_baglac"]
            else:
                kept.append(rec)
                prev_idx = idx
    for rec in kept[max_sent:]:
        rec["ret"] = ["fazla_cumle"]
    kept = kept[:max_sent]
    while kept and len(" ".join(r["metin"] for r in kept)) > max_len:
        kept[-1]["ret"] = ["uzunluk"]
        kept.pop()
    if len(kept) < min_sent:
        out["sebep"] = "cumle_az:%d" % len(kept)
        return out
    text = " ".join(r["metin"] for r in kept)
    out.update(ok=True, **{"not": text})
    out["facts_used"] = sorted(set(i for r in kept for i in r["olgular"]), key=lambda x: int(x[1:]))
    return out


_RET_TXT = (("olgu_yok", "cümlede olgu kimliği yok"), ("tanimsiz_olgu", "listede olmayan olgu kimliği"),
            ("ciplak_rakam", "sayı ya da tarih {Fn} yerine çıplak yazılmış"), ("yasak_dil", "yasak sözcük"),
            ("neden_sonuc", "olguda olmayan neden-sonuç"), ("tahmin", "tahmin/gelecek ifadesi"),
            ("ortalama", "'ortalama' yerine 'ortanca' yazılmalı"), ("karsilastirma", "karşılaştırma sayılarla çelişiyor"),
            ("yon", "artış/düşüş olgunun işaretiyle çelişiyor"), ("isaret", "negatif/pozitif olguyla çelişiyor"),
            ("yargi", "olguda olmayan yorum sıfatı"), ("dayanak", "olgu listesinde olmayan bilgi"),
            ("ad", "olgu listesinde olmayan özel ad"), ("bicim", "% ya da ₺ olgu kimliğine yapışık"),
            ("karsilama", "cari oran ifadesi olguyla çelişiyor"), ("sayi", "olguda olmayan sayı"),
            ("eslesme", "olgu kimliği konusuyla birlikte anılmamış"),
            ("deger_yigini", "bir parantezde birden çok değer"),
            ("yanki_parantez", "aynı değer parantezle tekrar edilmiş"),
            ("donem_yok", "değişim cümlesi dönemini (yıl/çeyrek) taşımıyor"),
            ("kopuk_baglac", "önceki cümle atıldığı için bağlaçla başlıyor"))


def feedback_for(result):
    """Yeniden deneme için kısa ret özeti (model istemine eklenir)."""
    why = []
    for c in result.get("cumleler") or []:
        for r in c.get("ret") or []:
            head = r.split(":")[0]
            txt = next((t for k, t in _RET_TXT if head == k), None)
            if txt and txt not in why:
                why.append(txt)
    return ("Önceki taslakta bazı cümleler kurallara uymadığı için atıldı (%s). Yalnız olgulara dayanan, her "
            "cümlesinde {Fn} bulunan 3-5 cümle yaz; sayı ve tarihi kendin yazma, yorum sıfatı ve neden-sonuç "
            "kullanma." % ("; ".join(why[:6]) or "cümle sayısı yetersiz"))


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


def run_bildirim_pilot(ids, base_url, api_key, budget_usd, out_path):
    """D-44a kalan #1 — bildirim özeti (tarifi §1/§5: 20 bildirim, 2 model yan yana)."""
    spent = [0.0]
    rows = []
    for idx in ids:
        try:
            facts, item, ctx = build_bildirim_facts(idx, base_url)
        except (urllib.error.URLError, OSError, json.JSONDecodeError) as e:
            rows.append({"idx": idx, "error": f"veri çekilemedi: {e}"})
            continue
        if not item:
            rows.append({"idx": idx, "error": "bildirim bulunamadı"})
            continue
        facts = facts or []
        olgu_block = facts_block(facts) if facts else "(olgu yok — sayı YAZMA, nitel anlat)"
        field_block = "\n".join(ctx["fields"]) if ctx["fields"] else ""
        user_content = (
            f"Şirket: {ctx['company']} · Bildirim türü: {ctx['class']} ({ctx['subject']})\n"
            f"Başlık: {ctx['title']}\n"
            f"Olgular:\n{olgu_block}\n"
            f"Yapılandırılmış alanlar:\n{field_block}\n"
            f"Ham metin (ilk 1500 karakter):\n{ctx['text']}"
        )
        model_results = {}
        for model in MODELS:
            if spent[0] >= budget_usd:
                model_results[model] = {"skipped": "pilot bütçesi doldu"}
                continue
            text, usage, err = call_gemini(model, SYSTEM_PROMPT_BILDIRIM, user_content, api_key)
            if err:
                model_results[model] = {"error": err}
                continue
            cost = gemini_budget.cost_usd(model, usage.get("promptTokenCount", 0) or 0,
                                           usage.get("candidatesTokenCount", 0) or 0)
            spent[0] += cost
            ok, rendered, reason = validate_note(text, facts, max_len=180)
            model_results[model] = {"ok": ok, "raw": text, "rendered": rendered,
                                     "reason": reason, "cost_usd": round(cost, 6)}
            time.sleep(1)
        rows.append({"idx": idx, "item": item, "facts": facts, "models": model_results})
    write_bildirim_report(rows, spent[0], out_path)
    return rows, spent[0]


def write_bildirim_report(rows, spent, out_path):
    lines = ["# D-44a kalan #1 — AI bildirim özeti pilotu (yan yana)", "",
              f"Modeller: {', '.join(MODELS)}. Toplam ölçülen maliyet: ${spent:.4f}", ""]
    for row in rows:
        item = row.get("item") or {}
        head = f"## {row['idx']} — {item.get('company', '?')} ({item.get('class', '?')})"
        lines.append(head)
        if row.get("error"):
            lines.append(f"- HATA: {row['error']}")
            lines.append("")
            continue
        lines.append("**Kural tabanlı (canlı) özet:** " + (item.get("summary") or "(yok)"))
        if row["facts"]:
            lines.append("**Olgular:** " + "; ".join(f"{f['id']}={f['t']}={f['v']}" for f in row["facts"]))
        else:
            lines.append("**Olgular:** (yok — tutar/oran çıkarılamadı)")
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


def run_bulten_pilot(tarihler, base_url, api_key, budget_usd, out_path):
    """D-44a kalan #2 — bülten metni (tarifi §1/§5: 1 bülten, 2 model yan yana)."""
    spent = [0.0]
    rows = []
    for tarih in tarihler:
        try:
            facts, payload = build_bulten_facts(tarih, base_url)
        except (urllib.error.URLError, OSError, json.JSONDecodeError) as e:
            rows.append({"tarih": tarih or "latest", "error": f"veri çekilemedi: {e}"})
            continue
        if not facts:
            rows.append({"tarih": tarih or "latest", "error": "bülten bulunamadı / boş (503?)"})
            continue
        gercek_tarih = payload.get("tarih", tarih or "latest")
        user_content = f"Olgular (bülten {gercek_tarih}):\n{facts_block(facts)}"
        model_results = {}
        for model in MODELS:
            if spent[0] >= budget_usd:
                model_results[model] = {"skipped": "pilot bütçesi doldu"}
                continue
            text, usage, err = call_gemini(model, SYSTEM_PROMPT_BULTEN, user_content, api_key)
            if err:
                model_results[model] = {"error": err}
                continue
            cost = gemini_budget.cost_usd(model, usage.get("promptTokenCount", 0) or 0,
                                           usage.get("candidatesTokenCount", 0) or 0)
            spent[0] += cost
            ok, rendered, reason = validate_note(text, facts, max_len=500)
            model_results[model] = {"ok": ok, "raw": text, "rendered": rendered,
                                     "reason": reason, "cost_usd": round(cost, 6)}
            time.sleep(1)
        rows.append({"tarih": gercek_tarih, "facts": facts, "models": model_results})
    write_bulten_report(rows, spent[0], out_path)
    return rows, spent[0]


def write_bulten_report(rows, spent, out_path):
    lines = ["# D-44a kalan #2 — AI bülten metni pilotu (yan yana)", "",
              f"Modeller: {', '.join(MODELS)}. Toplam ölçülen maliyet: ${spent:.4f}", ""]
    for row in rows:
        lines.append(f"## Bülten {row['tarih']}")
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
    p.add_argument("--mode", choices=["sirket", "bildirim", "bulten"], default="sirket")
    p.add_argument("--tickers", default="THYAO,GARAN,TUPRS,BIMAS,ASELS")
    p.add_argument("--ids", default="", help="bildirim modu: virgülle ayrılmış KAP bildirim id'leri")
    p.add_argument("--tarihler", default="", help="bulten modu: virgülle ayrılmış YYYY-AA-GG (boş=latest)")
    p.add_argument("--base-url", default=DEFAULT_BASE_URL)
    p.add_argument("--budget-usd", type=float, default=1.0)
    p.add_argument("--out", default="plans/2026-09-23-denetim/ai-pilot.md")
    args = p.parse_args(argv)
    api_key = os.environ.get("GEMINI_API_KEY", "")
    if not api_key:
        print("GEMINI_API_KEY yok, çağrı atılmadı.", file=sys.stderr)
        return 1
    out_path = args.out if os.path.isabs(args.out) else os.path.join(
        os.path.expanduser("~/ops"), args.out)
    if args.mode == "bildirim":
        ids = [int(x) for x in args.ids.split(",") if x.strip()]
        rows, spent = run_bildirim_pilot(ids, args.base_url, api_key, args.budget_usd, out_path)
        print(f"Bitti. {len(rows)} bildirim, toplam ${spent:.4f}. Rapor: {out_path}")
        return 0
    if args.mode == "bulten":
        tarihler = [t.strip() for t in args.tarihler.split(",") if t.strip()] or [None]
        rows, spent = run_bulten_pilot(tarihler, args.base_url, api_key, args.budget_usd, out_path)
        print(f"Bitti. {len(rows)} bülten, toplam ${spent:.4f}. Rapor: {out_path}")
        return 0
    tickers = [t.strip().upper() for t in args.tickers.split(",") if t.strip()]
    rows, spent = run_pilot(tickers, args.base_url, api_key, args.budget_usd, out_path)
    print(f"Bitti. {len(rows)} hisse, toplam ${spent:.4f}. Rapor: {out_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
