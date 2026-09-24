"""D-04: resmi kapanış — Borsa İstanbul günlük pay bülteni (kaynak notu:
plans/2026-09-23-denetim/d04-resmi-kapanis-kaynagi.md).

Yahoo'nun günlük barı akşam 17:59 fiyatını taşıyor, resmi kapanış (18:10 kapanış
seansı) 1-1,5 gün sonra oturuyor. Bülten 18:25-18:30'da çıkar; fiyat, önceki
kapanış ve son mum bu dosyadan alınır. Saf fonksiyonlar + tek ağ çağrısı
(fetch_bulletin); import yan etkisizdir.
"""
import csv
import io
import json
import os
import zipfile
from datetime import date, datetime

_HERE = os.path.dirname(os.path.abspath(__file__))
ARCHIVE_DIR = os.path.join(_HERE, "resmi_kapanis")
BULLETIN_URL = "https://www.borsaistanbul.com/data/thb/{y}/{m}/thb{y}{m}{d}1.zip"
INDEX_URL = "https://www.borsaistanbul.com/datum/PayEndeksleri.zip"
INDEX_CODES = ("XU100", "XU030")
MIN_EQUITY_ROWS = 600        # bülten ~631 pay satırı içerir
MIN_UNIVERSE_COVERAGE = 0.98  # evrenin en az %98'i bültende olmalı
SOURCE_LABEL = "BIST bülteni"

# Başlık adıyla okunur (sütun sırası değişebilir; başlıkta çift boşluk var).
_COLS = {
    "date": "TARIH", "code": "ISLEM KODU", "group": "ENSTRUMAN GRUBU",
    "sub": "YAPISAL BAZDA PIYASA ALT BOLUMU", "prev": "ONCEKI KAPANIS FIYATI",
    "open": "ACILIS FIYATI", "low": "EN DUSUK FIYAT", "high": "EN YUKSEK FIYAT",
    "close": "KAPANIS FIYATI", "chg": "DEGISIM (%)", "vol": "TOPLAM ISLEM ADEDI",
}


def bulletin_url(d):
    return BULLETIN_URL.format(y=d.strftime("%Y"), m=d.strftime("%m"), d=d.strftime("%d"))


def _norm(s):
    return " ".join((s or "").split())


def _num(x):
    try:
        return float(str(x).replace(",", ".").strip())
    except (TypeError, ValueError):
        return None


def parse_bulletin(zip_bytes):
    """ZIP → {"date": "YYYY-MM-DD", "stocks": {TICKER: {...}}}. Pay = ISLEM KODU
    `.E` ile biten, ENSTRUMAN GRUBU=EQT, alt bölüm=MSPOT. KAPANIS FIYATI ≤ 0 olan
    satır atlanır (işlem görmeyen). Bozuk dosyada ValueError."""
    with zipfile.ZipFile(io.BytesIO(zip_bytes)) as zf:
        names = [n for n in zf.namelist() if n.lower().endswith(".csv")]
        if not names:
            raise ValueError("bülten ZIP'inde csv yok")
        text = zf.read(names[0]).decode("utf-8-sig", errors="replace")
    rows = csv.reader(io.StringIO(text), delimiter=";")
    header = next(rows, None)
    if not header:
        raise ValueError("bülten boş")
    idx = {_norm(h): i for i, h in enumerate(header)}
    missing = [v for v in _COLS.values() if v not in idx]
    if missing:
        raise ValueError("bülten başlığı beklenenden farklı, eksik: %s" % missing)
    g = {k: idx[v] for k, v in _COLS.items()}
    stocks, dates = {}, set()
    for r in rows:
        if len(r) <= max(g.values()):
            continue
        code = _norm(r[g["code"]])
        if not code.endswith(".E") or _norm(r[g["group"]]) != "EQT" or _norm(r[g["sub"]]) != "MSPOT":
            continue
        close, prev = _num(r[g["close"]]), _num(r[g["prev"]])
        if not close or close <= 0 or not prev or prev <= 0:
            continue
        o, h, l = _num(r[g["open"]]), _num(r[g["high"]]), _num(r[g["low"]])
        d = _norm(r[g["date"]])
        dates.add(d)
        stocks[code[:-2]] = {
            "close": close, "prev_close": prev,
            "open": o if o else close, "high": h if h else close, "low": l if l else close,
            "volume": _num(r[g["vol"]]) or 0.0,
            "change_pct": _num(r[g["chg"]]),
        }
    if len(dates) != 1:
        raise ValueError("bültende tek tarih beklenirdi: %s" % sorted(dates))
    return {"date": dates.pop(), "stocks": stocks}


def parse_indices(zip_bytes):
    """PayEndeksleri.zip → {"date": "YYYY-MM-DD", "indices": {"XU100": {close, open, low, high}, ...}}.
    Dosyada yalnız son gün var (her akşam üzerine yazılır). Satır biçimi:
    id;kod;ad_tr;ad_en;para;GG/AA/YYYY;kapanış;açılış;en düşük;en yüksek. Bozuk dosyada ValueError."""
    with zipfile.ZipFile(io.BytesIO(zip_bytes)) as zf:
        names = [n for n in zf.namelist() if n.lower().startswith("fiyatendeksleri")]
        if not names:
            raise ValueError("endeks ZIP'inde FiyatEndeksleri csv yok")
        text = zf.read(names[0]).decode("utf-8-sig", errors="replace")
    out, dates = {}, set()
    for r in csv.reader(io.StringIO(text), delimiter=";"):
        if len(r) < 10 or _norm(r[1]) not in INDEX_CODES:
            continue
        close, o, l, h = (_num(r[6]), _num(r[7]), _num(r[8]), _num(r[9]))
        if not close or close <= 0:
            continue
        try:
            d = datetime.strptime(_norm(r[5]), "%d/%m/%Y").date().isoformat()
        except ValueError:
            raise ValueError("endeks tarihi okunamadı: %r" % r[5])
        dates.add(d)
        out[_norm(r[1])] = {"close": close, "open": o or close, "low": l or close, "high": h or close}
    if not out or len(dates) != 1:
        raise ValueError("endeks dosyasında tek tarihli XU100/XU030 beklenirdi: %s %s" % (sorted(out), sorted(dates)))
    return {"date": dates.pop(), "indices": out}


def fetch_indices(timeout=30):
    """Endeks dosyasını indirir (yok → None). Ağ hatası fırlatır."""
    import requests
    r = requests.get(INDEX_URL, timeout=timeout, headers={"User-Agent": "Mozilla/5.0"})
    if r.status_code != 200 or not r.content:
        return None
    return {"raw": r.content, "last_modified": r.headers.get("Last-Modified")}


def check_gates(parsed, want_date, universe):
    """(ok, neden). Kapılar: tarih o gün mü; ≥600 pay; evrenin ≥%98'i bültende."""
    if parsed.get("date") != want_date.isoformat():
        return False, "tarih %s != beklenen %s" % (parsed.get("date"), want_date)
    n = len(parsed["stocks"])
    if n < MIN_EQUITY_ROWS:
        return False, "%d pay satırı < %d" % (n, MIN_EQUITY_ROWS)
    uni = [t for t in universe if t]
    if uni:
        cov = sum(1 for t in uni if t in parsed["stocks"]) / float(len(uni))
        if cov < MIN_UNIVERSE_COVERAGE:
            return False, "evren kapsaması %.1f%% < %.0f%%" % (cov * 100, MIN_UNIVERSE_COVERAGE * 100)
    return True, "ok"


def fetch_bulletin(d, timeout=30):
    """Bülteni indirir (indirme yok/404 → None). Ağ hatası fırlatır."""
    import requests
    r = requests.get(bulletin_url(d), timeout=timeout, headers={"User-Agent": "Mozilla/5.0"})
    if r.status_code != 200 or not r.content:
        return None
    return {"raw": r.content, "last_modified": r.headers.get("Last-Modified")}


def archive_path(d):
    return os.path.join(ARCHIVE_DIR, "%s.json" % d.isoformat())


def previous_archive(d):
    """d gününden ÖNCEKİ en yakın arşiv kaydı (endeks önceki kapanışı için) ya da None."""
    try:
        days = sorted(n[:-5] for n in os.listdir(ARCHIVE_DIR)
                      if n.endswith(".json") and len(n) == 15 and n[:-5] < d.isoformat())
    except OSError:
        return None
    for day in reversed(days):
        try:
            with open(os.path.join(ARCHIVE_DIR, day + ".json"), encoding="utf-8") as f:
                rec = json.load(f)
        except (OSError, ValueError):
            continue
        if rec.get("indices"):
            return rec
    return None


def _with_index_prev(idx_parsed, d):
    """Endeks kayıtlarına önceki resmi kapanışı (varsa) yazar; dosyada önceki kapanış alanı yok."""
    prev = previous_archive(d)
    out = {}
    for code, v in (idx_parsed or {}).get("indices", {}).items():
        v = dict(v)
        pc = ((prev or {}).get("indices") or {}).get(code, {}).get("close")
        if pc:
            v["prev_close"] = pc
        out[code] = v
    return out


def save_archive(parsed, last_modified=None, source=SOURCE_LABEL, indices=None):
    os.makedirs(ARCHIVE_DIR, exist_ok=True)
    d = date.fromisoformat(parsed["date"])
    payload = {"date": parsed["date"], "source": source, "last_modified": last_modified,
               "saved_at": datetime.now().isoformat(timespec="seconds"), "stocks": parsed["stocks"]}
    if indices and indices.get("date") == parsed["date"]:
        payload["indices"] = _with_index_prev(indices, d)
    p = archive_path(d)
    tmp = p + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, separators=(",", ":"))
    os.replace(tmp, p)
    return p


_MEM = {}   # {iso_date: payload | None}  (analyze() 215× çağırır; dosyayı bir kez oku)


def load_archive(d):
    """d gününün resmi kaydı ya da None. Bulunamayan tarih önbelleğe alınmaz
    (kesinleştirme koşusu dosyayı sonradan yazar)."""
    key = d.isoformat()
    if key in _MEM:
        return _MEM[key]
    try:
        with open(archive_path(d), encoding="utf-8") as f:
            rec = json.load(f)
    except (OSError, ValueError):
        return None
    _MEM[key] = rec
    return rec


def reset_memory():
    _MEM.clear()


def overlay_official_bar(df, rec, ticker_base):
    """Günlük df'nin son barını resmi OHLCV ile değiştirir; son bar tarihi resmi
    tarihten eskiyse ekler; önceki barın kapanışı bültendeki önceki kapanışa
    eşitlenir. (df, uygulandı_mı) döner. Resmi tarihten SONRAKİ bar varsa
    dokunmaz. Bülten önceki kapanışı seriyle %12'den fazla ayrışıyorsa
    (bölünme/bedelsiz) hiçbir şey yazılmaz."""
    import pandas as pd
    t = (rec or {}).get("stocks", {}).get(ticker_base) or (rec or {}).get("indices", {}).get(ticker_base)
    if not t or df is None or len(df) < 2:
        return df, False
    want = pd.Timestamp(rec["date"])
    last_ts = df.index[-1]
    last_day = pd.Timestamp(last_ts.date())
    if last_day > want:
        return df, False
    prev_pos = -2 if last_day == want else -1
    prev_series_close = float(df["Close"].iloc[prev_pos])
    # Endeks kaydında önceki resmi kapanış yoksa (arşivin ilk günü) seri önceki barı kalır.
    t = dict(t, prev_close=t.get("prev_close") or prev_series_close)
    if prev_series_close > 0 and abs(t["prev_close"] / prev_series_close - 1) > 0.12:
        return df, False   # bölünme/bedelsiz benzeri seri kırılması: resmi bar seriye yazılmaz
    row = {"Open": t["open"], "High": t["high"], "Low": t["low"], "Close": t["close"]}
    if "Volume" in df.columns:
        # Endeks kayıtlarında hacim yok (D-04c P2-1): serinin son barının hacmi kalır.
        row["Volume"] = t["volume"] if "volume" in t else float(df["Volume"].iloc[-1])
    out = df.copy()
    # Önceki bar Yahoo'da oturmamış olabilir: değişim bülten değişimiyle eşleşsin.
    out.iloc[prev_pos if last_day == want else -1, out.columns.get_loc("Close")] = t["prev_close"]
    if last_day == want:
        for c, v in row.items():
            out.iloc[-1, out.columns.get_loc(c)] = v
    else:
        new_idx = pd.Timestamp(want)
        if getattr(last_ts, "tzinfo", None) is not None:
            new_idx = new_idx.tz_localize(last_ts.tzinfo)
        add = pd.DataFrame([row], index=[new_idx], columns=out.columns).astype(out.dtypes.to_dict(), errors="ignore")
        out = pd.concat([out, add])
    return out, True


def patch_chart_last_bar(data, rec, ticker_base):
    """Grafik yanıtının (derin kopya) son mumunu resmi OHLC ile eşitler; resmi tarih
    seride yoksa sona ekler. Grafik önbelleği günde bir/oturmamış çekilir; sunum anında
    yama yapmak `summary.close == ohlc[-1].close` sözünü önbellek tazeliğinden bağımsız
    tutar. Uygulandıysa True. Resmi tarihten sonraki mumlar ve %12'den büyük kırılmalar
    (bölünme/bedelsiz) için dokunmaz."""
    t = (rec or {}).get("stocks", {}).get(ticker_base) or (rec or {}).get("indices", {}).get(ticker_base)
    ohlc = (data or {}).get("ohlc")
    if not t or not ohlc:
        return False
    day = rec["date"]
    last = ohlc[-1]
    if last.get("time", "") > day:
        return False
    ref = ohlc[-2]["close"] if last.get("time") == day and len(ohlc) >= 2 else last.get("close")
    if ref and abs(t["close"] / ref - 1) > 0.12 and abs((t.get("prev_close") or ref) / ref - 1) > 0.12:
        return False
    bar = {"time": day, "open": round(t["open"], 2), "high": round(t["high"], 2),
           "low": round(t["low"], 2), "close": round(t["close"], 2)}
    if last.get("time") == day:
        ohlc[-1] = bar
    else:
        ohlc.append(bar)
    s = data.setdefault("summary", {})
    s["close"] = bar["close"]
    s["close_status"] = "resmi"
    return True


def collapse_pending(entries, day_iso, tickers=None):
    """Digest bufferindeki (bir günün) aynı hisse değişim zincirini tek girdiye indirir.
    18:10 geçici sinyali X→Y, resmi bar Y→X'e döndürürse ikisi de silinir (digest'te
    "değişim" görünmez); X→Y→Z ise tek X→Z girdisi kalır. Yalnız `ts` tarihi day_iso
    olan girdiler ve (verildiyse) `tickers` içindeki hisseler etkilenir; sıra korunur.
    (yeni_liste, silinen_sayısı) döner."""
    groups = {}
    for i, e in enumerate(entries):
        if str(e.get("ts", ""))[:10] != day_iso or (tickers is not None and e.get("ticker") not in tickers):
            continue
        groups.setdefault(e.get("ticker"), []).append(i)
    drop, repl = set(), {}
    for tk, idxs in groups.items():
        first, last = entries[idxs[0]], entries[idxs[-1]]
        if len(idxs) < 2:
            continue
        if first.get("old") == last.get("new"):
            drop.update(idxs)
        else:
            merged = dict(last)
            merged["old"] = first.get("old")
            repl[idxs[0]] = merged
            drop.update(idxs[1:])
    out = [repl.get(i, e) for i, e in enumerate(entries) if i not in drop or i in repl]
    return out, len(entries) - len(out)


def rebuild_pending(entries, day_iso, tickers, pre_sig, official, make_entry):
    """D-04c P1-1: `tickers` için day_iso günlük digest girdilerini resmi sinyalden YENİDEN kurar.
    18:10 geçici sinyalinin bıraktığı zincir (BEKLE→SAT gibi resmi bar tarafından geri
    alınan ya da AL→BEKLE→AL ile sahte "yeni sinyal" doğuran) silinir; girdi yalnız
    EOD öncesi sinyal (`pre_sig`) ile resmi sinyal (`official`) farklı ve resmi ∈ {AL,SAT}
    ise, resmi fiyat/değişimle (make_entry(ticker, old, new)) yazılır. `pre_sig`'te
    olmayan hisse dokunulmadan kalır. (yeni_liste, silinen, eklenen) döner."""
    base = [t for t in tickers if t in pre_sig and t in official]
    tset = set(base)
    kept = [e for e in entries
            if not (str(e.get("ts", ""))[:10] == day_iso and e.get("ticker") in tset)]
    added = 0
    for t in base:
        if official[t] in ("AL", "SAT") and pre_sig[t] != official[t]:
            kept.append(make_entry(t, pre_sig[t], official[t]))
            added += 1
    return kept, len(entries) - (len(kept) - added), added
