"""D-44b ilk adım — AI Analist Notu (şirket notu): gün sonu üretim işi + sitenin okuma yolu.

Ne yapar: resmi kapanış ve donmuş bülten/ısı haritası yazıldıktan sonra, BIST30 hisselerinden olgu
imzası değişenlere bir kez not yazdırır (Gemini flash-lite, grounding yok; istem ve doğrulayıcı
pipeline/ai_notes.py), notu cümle cümle denetler (ai_notes.validate_sentences) ve geçeni
data/ai_not/<T>.json'a atomik yazar. Denetimden geçmeyen not saklanmaz; önceki sürüm kalır ve
MAX_AGE_DAYS sonra gösterilmez. Olgular değişmediyse çağrı yok, notun kapanış tarihi ilerletilir.

Harcama: (1) gemini_budget paylaşımlı tavanları (GEMINI_ENABLED, 200 çağrı/gün, 5 $/ay) her çağrıdan
önce reserve(), sonra record(); diğer AI özelliklerine her gün DAILY_RESERVE çağrı bırakılır.
(2) Paylaşımlı kota sigortası dosyası okunur: manual_hold ya da açık sigorta → çağrı yok.
(3) Pilot tavanı: toplam ≤ AI_NOT_PILOT_USD (varsayılan 1 $), kendi sayacı data/ai_not/butce.json.
Her çağrıdan önce kalan ≥ CALL_RESERVE_USD şartı aranır (bir çağrının en kötü maliyeti bunun altında),
ölçülemeyen çağrı CALL_RESERVE_USD sayılır → tavan aşılmaz. Tavan dolunca notlar gizlenir.

Bayrak: AI_NOT_ENABLED=1 olmadan iş çağrı atmaz ve site notu göstermez (varsayılan KAPALI).
Kuru koşu (--kuru): bayraktan bağımsız; seçilen hisselere not yazdırır (gerçek çağrı, aynı tavanlar ve
pilot sayacı) ama yayımlamaz: data/ai_not/kuru/<T>.json + ozet.md (Ozan'a örnek sayfası için).
--olgular: model çağrısı yok, olgu listesi ve imza (maliyet 0). --ozet: sayaç ve durum.

Girdi yalnız sitenin kendi uçları (AI_NOT_BASE_URL, varsayılan http://127.0.0.1:8003): /api/data,
/api/hisse/<T>/fundamentals, /api/hisse/<T>/kap. app.py import edilmez; app.py yalnız public_note()
okur. Python 3.9 uyumlu. Zamanlama: pipeline/systemd/bp-ai-not.timer (hafta içi 20:00–22:30 TR, yarım
saatte bir); iş gün sonu hazır mı, bu gün yapıldı mı diye kendisi bakar (idempotent, kilitli).
"""
import argparse
import json
import os
import re
import sys
import tempfile
import time
import urllib.error
import urllib.request
from datetime import date, datetime, timedelta, timezone

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)
import gemini_budget  # noqa: E402  (paylaşımlı tavan; app.py'siz)
from pipeline import ai_notes as an  # noqa: E402  (olgu, istem, doğrulayıcı — tek kaynak)

LABEL = "Yapay zekâ ile derlendi"
MODEL = an.URETIM_MODEL


def _env_float(name, default):
    try:
        return float(os.environ.get(name, default))
    except (TypeError, ValueError):
        return float(default)


OUT_DIR = os.environ.get("AI_NOT_DIR") or os.path.join(ROOT, "data", "ai_not")
BASE_URL = os.environ.get("AI_NOT_BASE_URL", "http://127.0.0.1:8003")
QUOTA_CB_PATH = os.environ.get("GEMINI_QUOTA_CB_PATH", "/tmp/bp_gemini_quota_cb.json")
PILOT_USD = _env_float("AI_NOT_PILOT_USD", "1")
CALL_RESERVE_USD = 0.002      # flash-lite tek çağrı tavanı: ~4k giriş + 1k çıkış token ≈ 0,0008 $
DAILY_RESERVE = 60            # 200/gün tavanından Gündem, açıklama vb. için bırakılan çağrı
MAX_CALLS_PER_TICKER = 2      # ilk yazım + ret sebepleriyle bir deneme
CALL_GAP_S = 7.0              # app.py _gemini_rate_acquire aralığından (6,5 sn) geniş
FETCH_GAP_S = 2.2             # /fundamentals 30/dk sınırının altında
MAX_AGE_DAYS = 10             # kapanış tarihi bundan eski not gösterilmez
MIN_FACTS = 4
READY_RATIO = 0.8             # BIST30 satırlarının en az %80'i o günün resmi kapanışında olmalı
AUDIT_KEEP_DAYS = 30
_TZ_TR = timezone(timedelta(hours=3))
_TICKER_RE = re.compile(r"^[A-Z0-9]{2,8}$")
_DAY_FILE = re.compile(r"^(\d{4}-\d{2}-\d{2})\.json$")


def enabled():
    """Site gösterimi ve zamanlanmış üretim için bayrak (varsayılan kapalı)."""
    return os.environ.get("AI_NOT_ENABLED", "0").strip() == "1"


class Stop(Exception):
    """Tur durur (tavan, sigorta, Gemini hatası); kalan hisseler sonraki turda."""


# ----------------------------------------------------------------------------- dosya

def _read_json(path):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return None


def _atomic_write(path, obj):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=os.path.dirname(path), prefix=".tmp_")
    try:
        with os.fdopen(fd, "wb") as f:
            f.write(json.dumps(obj, ensure_ascii=False, indent=1).encode("utf-8"))
        os.replace(tmp, path)
    except BaseException:
        try:
            os.remove(tmp)
        except OSError:
            pass
        raise


def note_path(ticker, base=None):
    return os.path.join(base or OUT_DIR, "%s.json" % ticker)


def _state_path(base):
    return os.path.join(base, "durum.json")


def _audit_path(base, day):
    return os.path.join(base, "audit", "%s.json" % day)


# ----------------------------------------------------------------------------- pilot bütçesi

def budget_state(base=None):
    d = _read_json(os.path.join(base or OUT_DIR, "butce.json")) or {}
    return {"tavan_usd": PILOT_USD, "usd": float(d.get("usd") or 0.0), "cagri": int(d.get("cagri") or 0),
            "ilk": d.get("ilk"), "son": d.get("son")}


def budget_exhausted(base=None):
    st = budget_state(base)
    return st["tavan_usd"] - st["usd"] < CALL_RESERVE_USD


def _budget_add(base, usd, now_iso):
    st = budget_state(base)
    st["usd"] = round(st["usd"] + max(0.0, float(usd)), 6)
    st["cagri"] += 1
    st["ilk"] = st["ilk"] or now_iso
    st["son"] = now_iso
    _atomic_write(os.path.join(base, "butce.json"), st)
    return st


# ----------------------------------------------------------------------------- kapı

def read_cb_state(path):
    d = _read_json(path) if path else None
    return d if isinstance(d, dict) else {}


def gate(budget_status=None, cb_state=None, base=None, now_ts=None, need_flag=True):
    """Tur başında: (True, None) | (False, sebep). Hiçbir durumda istem kurulmaz/çağrı atılmaz."""
    if need_flag and not enabled():
        return False, "AI_NOT_ENABLED=0"
    st = budget_status or {}
    if not st.get("enabled", True):
        return False, "GEMINI_ENABLED=0"
    cb = cb_state or {}
    if cb.get("manual_hold"):
        return False, "manual_hold"
    if (cb.get("open_until") or 0) > (now_ts if now_ts is not None else time.time()):
        return False, "kota_sigortasi"
    if (st.get("usd_month") or 0) >= (st.get("monthly_cap_usd") or gemini_budget.MONTHLY_USD):
        return False, "aylik_tavan"
    if (st.get("daily_cap") or gemini_budget.DAILY_CALLS) - (st.get("calls_today") or 0) <= DAILY_RESERVE:
        return False, "gunluk_tavan"
    if budget_exhausted(base):
        return False, "pilot_butce"
    return True, None


# ----------------------------------------------------------------------------- gün ve evren

def latest_close_day(root=None):
    """Donmuş bülten ya da ısı haritası görüntüsü olan en son gün (resmi kapanış turu bitmiş demek)."""
    root = root or ROOT
    days = []
    for sub in ("bulten", "heatmap"):
        try:
            days += [m.group(1) for m in (_DAY_FILE.match(n) for n in os.listdir(os.path.join(root, "data", sub)))
                     if m]
        except OSError:
            continue
    return max(days) if days else None


def bist30(root=None):
    root = root or ROOT
    for rel in ("data/universe.json", "universe_seed.json"):
        d = _read_json(os.path.join(root, rel)) or {}
        lst = (d.get("indices") or {}).get("XU030") or []
        if lst:
            return sorted(t for t in lst if _TICKER_RE.match(t or ""))
    return []


def _day_label(iso):
    return an._tr_date(iso) or iso


# ----------------------------------------------------------------------------- çağrı ve getirme

def make_fetch(base_url=None, sleep=time.sleep):
    base_url = (base_url or BASE_URL).rstrip("/")
    last = [0.0]

    def fetch(path):
        wait = FETCH_GAP_S - (time.time() - last[0])
        if path != "/api/data" and wait > 0:
            sleep(wait)
        req = urllib.request.Request(base_url + path, headers={"User-Agent": "bp-ai-not/1"})
        try:
            with urllib.request.urlopen(req, timeout=30) as r:
                return json.loads(r.read().decode("utf-8"))
        finally:
            last[0] = time.time()
    return fetch


def make_gemini_call(api_key, base, sleep=time.sleep, budget=gemini_budget, now_fn=None):
    """Gerçek çağrı: reserve() → ai_notes.call_gemini → record() + pilot sayacı. Dönüş (metin|None, maliyet, hata)."""
    n = [0]
    now_fn = now_fn or (lambda: datetime.now(_TZ_TR).isoformat(timespec="seconds"))

    def call(system, user):
        if n[0]:
            sleep(CALL_GAP_S)
        st = budget.status()
        if not st.get("enabled", True):
            raise Stop("GEMINI_ENABLED=0")
        if (st.get("daily_cap") or 0) - (st.get("calls_today") or 0) <= DAILY_RESERVE:
            raise Stop("gunluk_tavan")
        if budget_exhausted(base):
            raise Stop("pilot_butce")
        ok, why = budget.reserve()
        if not ok:
            raise Stop(why or "gemini_tavan")
        n[0] += 1
        try:
            text, usage, err = an.call_gemini(MODEL, system, user, api_key, timeout=30)
        except Exception as e:   # zaman aşımı / ağ: anahtar içeren adres loglanmaz, yalnız tür
            text, usage, err = None, None, type(e).__name__
        if usage:
            pt = int(usage.get("promptTokenCount") or 0)
            ot = int(usage.get("candidatesTokenCount") or 0) + int(usage.get("thoughtsTokenCount") or 0)
            cost = budget.record(MODEL, pt, ot)
        else:
            cost = CALL_RESERVE_USD   # ölçülemeyen çağrı pilot tavanından en kötü maliyetle düşülür
        _budget_add(base, cost, now_fn())
        return text, round(cost, 6), err
    return call


def generate(ticker, name, facts, call):
    """En çok MAX_CALLS_PER_TICKER çağrı; ikincisi ret sebepleriyle.
    Dönüş (geçen sonuç | None, denemeler, durma sebebi | None). Stop yükselirse o ana kadarki denemeler döner."""
    attempts, feedback = [], None
    for k in range(MAX_CALLS_PER_TICKER):
        try:
            text, cost, err = call(an.SYSTEM_PROMPT, an.company_user_content(ticker, name, facts, feedback))
        except Stop as e:
            return None, attempts, str(e)
        rec = {"cagri": k + 1, "maliyet_usd": cost, "hata": err, "yanit": text}
        attempts.append(rec)
        if text is None:
            return None, attempts, "gemini_hata:%s" % (err or "?")[:60]
        try:
            res = an.validate_sentences(text, facts, name=name, ticker=ticker)
        except Exception as e:   # doğrulayıcıda beklenmedik hata: not yayımlanmaz, tur sürer
            res = {"ok": False, "not": None, "cumleler": [], "sebep": "dogrulayici:%s" % type(e).__name__,
                   "facts_used": []}
        rec["sonuc"] = res
        if res["ok"]:
            return res, attempts, None
        feedback = an.feedback_for(res)
    return None, attempts, None


# ----------------------------------------------------------------------------- tur

def _lock(base):
    """Aynı anda tek tur (zamanlayıcı + elle kuru koşu). Kilit alınamazsa None."""
    import fcntl
    os.makedirs(base, exist_ok=True)
    fh = open(os.path.join(base, ".kilit"), "w")
    try:
        fcntl.flock(fh, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError:
        fh.close()
        return None
    return fh


def _prune_audit(base, today_iso):
    d = os.path.join(base, "audit")
    try:
        cutoff = (date.fromisoformat(today_iso) - timedelta(days=AUDIT_KEEP_DAYS)).isoformat()
        for n in os.listdir(d):
            m = _DAY_FILE.match(n)
            if m and m.group(1) < cutoff:
                os.remove(os.path.join(d, n))
    except (OSError, ValueError):
        pass


def _public_facts(facts, ids):
    keep = set(ids)
    return [{"id": f["id"], "t": f["t"], "v": f["v"]} for f in facts if f["id"] in keep]


def run(now=None, call=None, fetch=None, base=None, root=None, tickers=None, kuru=False, log=None,
        budget_status=None, cb_state=None, api_key=None):
    """Bir tur. Dönüş özeti {durum, gun, ...}. Testler call/fetch/base/root/budget_status/cb_state verir."""
    base, root = base or OUT_DIR, root or ROOT
    log = log or (lambda s: print(s, flush=True))
    now = now or datetime.now(_TZ_TR)
    if not kuru and not enabled():
        return {"durum": "kapali"}
    day = latest_close_day(root)
    if not day:
        return {"durum": "gun_sonu_yok"}
    lock = _lock(base)
    if lock is None:
        return {"durum": "calisiyor", "gun": day}
    try:
        return _run_locked(now, day, call, fetch, base, root, tickers, kuru, log, budget_status, cb_state, api_key)
    finally:
        lock.close()


def _run_locked(now, day, call, fetch, base, root, tickers, kuru, log, budget_status, cb_state, api_key):
    state = _read_json(_state_path(base)) or {}
    hs = state.get("hisseler") or {}
    universe = [t.upper() for t in tickers] if tickers else bist30(root)
    todo = list(universe) if kuru else [t for t in universe if (hs.get(t) or {}).get("gun") != day]
    if not todo:
        return {"durum": "yapildi", "gun": day}
    ok, why = gate(budget_status if budget_status is not None else gemini_budget.status(),
                   cb_state if cb_state is not None else read_cb_state(QUOTA_CB_PATH),
                   base, now.timestamp(), need_flag=not kuru)
    if not ok:
        log("ai-not %s: atlandı (%s)" % (day, why))
        return {"durum": "atlandi", "sebep": why, "gun": day}
    if call is None:
        key = api_key if api_key is not None else os.environ.get("GEMINI_API_KEY", "")
        if not key:
            return {"durum": "anahtar_yok", "gun": day}
        call = make_gemini_call(key, base)
    fetch = fetch or make_fetch()
    try:
        rows = {r.get("ticker"): r for r in ((fetch("/api/data") or {}).get("stocks") or [])}
    except (urllib.error.URLError, OSError, ValueError) as e:
        log("ai-not %s: /api/data alınamadı (%s)" % (day, type(e).__name__))
        return {"durum": "girdi_yok", "gun": day}
    ready = sum(1 for t in universe if an._iso_of((rows.get(t) or {}).get("bar_date")) == day
                and (rows.get(t) or {}).get("close_status") == "resmi")
    if ready < READY_RATIO * len(universe):
        log("ai-not %s: veri hazır değil (%d/%d resmi kapanış)" % (day, ready, len(universe)))
        return {"durum": "veri_hazir_degil", "gun": day, "hazir": ready}
    audit = _read_json(_audit_path(base, day)) or {"gun": day, "hisseler": {}}
    out = {"durum": "tamam", "gun": day, "yayin": 0, "ret": 0, "degismedi": 0, "atlanan": 0, "cagri": 0,
           "maliyet_usd": 0.0}
    kuru_rows = []
    stop = None
    for t in todo:
        row = rows.get(t) or {}
        name = row.get("name") or t
        if an._iso_of(row.get("bar_date")) != day:
            out["atlanan"] += 1
            continue
        try:
            stock, fund, kap_rows = an.fetch_company_inputs(t, None, data_rows=rows, get_json=fetch)
        except (urllib.error.URLError, OSError, ValueError) as e:
            log("ai-not %s %s: girdi alınamadı (%s)" % (day, t, type(e).__name__))
            out["atlanan"] += 1
            continue
        facts = an.build_company_facts(t, stock, fund, kap_rows, today=day)
        prev = hs.get(t) or {}
        if len(facts) < MIN_FACTS:
            if not kuru:
                hs[t] = dict(prev, gun=day, sonuc="olgu_yetersiz")
                _atomic_write(_state_path(base), dict(state, hisseler=hs))
            out["atlanan"] += 1
            continue
        imza = an.facts_signature(facts)
        if not kuru and prev.get("imza") == imza:
            doc = _read_json(note_path(t, base))
            if isinstance(doc, dict) and doc.get("not"):
                # olgular aynı: not bu kapanış için de geçerli → çağrı yok, kapanış tarihi ilerler
                doc.update(kapanis=day, kapanis_label=_day_label(day))
                _atomic_write(note_path(t, base), doc)
            hs[t] = dict(prev, gun=day, sonuc="degismedi")
            _atomic_write(_state_path(base), dict(state, hisseler=hs))
            out["degismedi"] += 1
            continue
        if not kuru:
            # çağrıdan ÖNCE iz: süreç ölse de bu hisse bu kapanış için yeniden çağrılmaz
            hs[t] = {"gun": day, "imza": imza, "sonuc": "basliyor"}
            _atomic_write(_state_path(base), dict(state, hisseler=hs))
        best, attempts, stop = generate(t, name, facts, call)
        if stop and not best:
            # tur durdu (tavan, sigorta, Gemini hatası): bu hissenin izi geri alınır, sonraki turda yeniden
            out["cagri"] += len(attempts)
            out["maliyet_usd"] += sum(a["maliyet_usd"] for a in attempts)
            if not kuru:
                if prev:
                    hs[t] = prev
                else:
                    hs.pop(t, None)
                _atomic_write(_state_path(base), dict(state, hisseler=hs))
            break
        cost = round(sum(a["maliyet_usd"] for a in attempts), 6)
        out["cagri"] += len(attempts)
        out["maliyet_usd"] += cost
        rec = {"ticker": t, "ad": name, "imza": imza, "olgular": [{"id": f["id"], "t": f["t"], "v": f["v"]}
                                                                   for f in facts],
               "denemeler": attempts, "maliyet_usd": cost, "sonuc": "yayin" if best else "ret"}
        if best:
            doc = {"ticker": t, "not": best["not"], "kapanis": day, "kapanis_label": _day_label(day),
                   "etiket": LABEL, "model": MODEL, "olusturma": now.isoformat(timespec="seconds"), "imza": imza,
                   "cumle": sum(1 for c in best["cumleler"] if not c["ret"]),
                   "olgular": _public_facts(facts, best["facts_used"])}
            if kuru:
                _atomic_write(os.path.join(base, "kuru", "%s.json" % t), dict(rec, yayin=doc))
            else:
                _atomic_write(note_path(t, base), doc)
            out["yayin"] += 1
        else:
            if kuru:
                _atomic_write(os.path.join(base, "kuru", "%s.json" % t), rec)
            out["ret"] += 1
        if kuru:
            kuru_rows.append(dict(rec, yayin=doc if best else None))
        else:
            hs[t] = {"gun": day, "imza": imza, "sonuc": rec["sonuc"], "cagri": len(attempts), "maliyet_usd": cost}
            audit["hisseler"][t] = rec
            _atomic_write(_audit_path(base, day), audit)
            _atomic_write(_state_path(base), dict(state, hisseler=hs))
    out["maliyet_usd"] = round(out["maliyet_usd"], 6)
    if stop:
        out.update(durum="durdu", sebep=stop)
    pilot = budget_state(base)
    if kuru:
        write_kuru_report(kuru_rows, out, pilot, os.path.join(base, "kuru", "ozet.md"))
    else:
        state.update(hisseler=hs, son_gun=day, son_tur=now.isoformat(timespec="seconds"))
        _atomic_write(_state_path(base), state)
        _prune_audit(base, day)
    log("ai-not %s%s: %s — yayın %d, ret %d, değişmedi %d, atlanan %d, %d çağrı, $%.4f; pilot $%.4f / $%g%s"
        % (day, " (kuru)" if kuru else "", out["durum"], out["yayin"], out["ret"], out["degismedi"],
           out["atlanan"], out["cagri"], out["maliyet_usd"], pilot["usd"], pilot["tavan_usd"],
           (" (%s)" % stop) if stop else ""))
    return out


# ----------------------------------------------------------------------------- kuru koşu raporu

def write_kuru_report(rows, out, pilot, path):
    lines = ["# AI Analist Notu — kuru koşu örnekleri (yayımlanmadı)", "",
             "Model %s · kapanış %s · %d hisse · yayına uygun %d, ret %d · bu koşu %d çağrı, $%.4f · "
             "pilot sayacı $%.4f / $%g" % (MODEL, _day_label(out.get("gun") or ""), len(rows), out["yayin"],
                                           out["ret"], out["cagri"], out["maliyet_usd"], pilot["usd"],
                                           pilot["tavan_usd"]), ""]
    for r in rows:
        lines.append("## %s · %s" % (r["ticker"], r["ad"]))
        lines.append("")
        if r.get("yayin"):
            lines += ["**%s** · %s kapanışı" % (LABEL, r["yayin"]["kapanis_label"]), "",
                      "> " + r["yayin"]["not"], ""]
        else:
            last = (r["denemeler"][-1].get("sonuc") or {}) if r.get("denemeler") else {}
            lines += ["**Yayımlanmadı** (%s)" % (last.get("sebep") or "yanıt yok"), ""]
        dropped = [(d["cagri"], c) for d in r.get("denemeler") or [] for c in (d.get("sonuc") or {}).get("cumleler", [])
                   if c.get("ret")]
        if dropped:
            lines.append("Atılan cümleler:")
            lines += ["- (deneme %d) %s — `%s`" % (k, c["metin"], ", ".join(c["ret"])) for k, c in dropped]
            lines.append("")
        lines.append("<details><summary>Olgular (%d)</summary>" % len(r["olgular"]))
        lines.append("")
        lines += ["- %s · %s = %s" % (f["id"], f["t"], f["v"]) for f in r["olgular"]]
        lines += ["", "</details>", ""]
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))


# ----------------------------------------------------------------------------- sitenin okuma yolu

def public_note(ticker, base=None, today=None):
    """app.py SSR bağlamı ve /api/hisse/<T>/ai-not. Bayrak kapalı, pilot bütçesi bitmiş, not yok, bozuk ya
    da kapanışı MAX_AGE_DAYS'ten eski → None (kart hiç çizilmez; gri ifade yok)."""
    if not enabled() or not _TICKER_RE.match(ticker or ""):
        return None
    base = base or OUT_DIR
    if budget_exhausted(base):
        return None
    d = _read_json(note_path(ticker, base))
    if not isinstance(d, dict) or d.get("ticker") != ticker or not isinstance(d.get("not"), str) or not d["not"]:
        return None
    try:
        kapanis = date.fromisoformat(d.get("kapanis") or "")
    except ValueError:
        return None
    today = today or datetime.now(_TZ_TR).date()
    if (today - kapanis).days > MAX_AGE_DAYS:
        return None
    return {"ticker": ticker, "not": d["not"], "kapanis": kapanis.isoformat(),
            "kapanis_label": d.get("kapanis_label") or _day_label(kapanis.isoformat()), "etiket": LABEL}


# ----------------------------------------------------------------------------- komut satırı

def _print_facts(tickers, fetch, base):
    rows = {r.get("ticker"): r for r in ((fetch("/api/data") or {}).get("stocks") or [])}
    dump = {}
    for t in tickers:
        stock, fund, kap_rows = an.fetch_company_inputs(t, None, data_rows=rows, get_json=fetch)
        facts = an.build_company_facts(t, stock, fund, kap_rows, today=an._iso_of(stock.get("bar_date")))
        dump[t] = {"imza": an.facts_signature(facts), "olgular": [{"id": f["id"], "t": f["t"], "v": f["v"]}
                                                                  for f in facts]}
        print("== %s (%d olgu) %s" % (t, len(facts), dump[t]["imza"][:12]))
        for f in facts:
            print("   %s %s = %s" % (f["id"], f["t"], f["v"]))
    _atomic_write(os.path.join(base, "kuru", "olgular.json"), dump)


def _print_summary(base):
    st = _read_json(_state_path(base)) or {}
    counts = {}
    for v in (st.get("hisseler") or {}).values():
        counts[v.get("sonuc")] = counts.get(v.get("sonuc"), 0) + 1
    pilot = budget_state(base)
    notes = sorted(n[:-5] for n in os.listdir(base) if re.match(r"^[A-Z0-9]{2,8}\.json$", n)) \
        if os.path.isdir(base) else []
    print("bayrak AI_NOT_ENABLED=%s · son gün %s · son tur %s" % ("1" if enabled() else "0", st.get("son_gun"),
                                                                 st.get("son_tur")))
    print("hisse durumu: %s" % (", ".join("%s %d" % kv for kv in sorted(counts.items(), key=str)) or "yok"))
    print("pilot: $%.4f / $%g, %d çağrı%s" % (pilot["usd"], pilot["tavan_usd"], pilot["cagri"],
                                            " — TÜKENDİ (notlar gizli)" if budget_exhausted(base) else ""))
    print("diskte not: %d (%s)" % (len(notes), ", ".join(notes[:30])))
    print(gemini_budget.summary_line())


def main(argv=None):
    p = argparse.ArgumentParser(description="AI Analist Notu (şirket notu) gün sonu işi")
    p.add_argument("--kuru", action="store_true", help="yayımlamadan örnek üret (gerçek çağrı, aynı tavanlar)")
    p.add_argument("--olgular", action="store_true", help="çağrı yok: olgu listesi ve imza")
    p.add_argument("--ozet", action="store_true", help="sayaç ve durum")
    p.add_argument("--tickers", default="", help="virgüllü (varsayılan BIST30)")
    p.add_argument("--base-url", default=None)
    args = p.parse_args(argv)
    if args.ozet:
        _print_summary(OUT_DIR)
        return 0
    tickers = [t.strip().upper() for t in args.tickers.split(",") if t.strip()] or None
    if args.olgular:
        _print_facts(tickers or bist30(), make_fetch(args.base_url), OUT_DIR)
        return 0
    res = run(tickers=tickers, kuru=args.kuru, fetch=make_fetch(args.base_url))
    print(json.dumps(res, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
