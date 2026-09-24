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


def save_archive(parsed, last_modified=None, source=SOURCE_LABEL):
    os.makedirs(ARCHIVE_DIR, exist_ok=True)
    payload = {"date": parsed["date"], "source": source, "last_modified": last_modified,
               "saved_at": datetime.now().isoformat(timespec="seconds"), "stocks": parsed["stocks"]}
    p = archive_path(date.fromisoformat(parsed["date"]))
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
    t = (rec or {}).get("stocks", {}).get(ticker_base)
    if not t or df is None or len(df) < 2:
        return df, False
    want = pd.Timestamp(rec["date"])
    last_ts = df.index[-1]
    last_day = pd.Timestamp(last_ts.date())
    if last_day > want:
        return df, False
    prev_pos = -2 if last_day == want else -1
    prev_series_close = float(df["Close"].iloc[prev_pos])
    if prev_series_close > 0 and abs(t["prev_close"] / prev_series_close - 1) > 0.12:
        return df, False   # bölünme/bedelsiz benzeri seri kırılması: resmi bar seriye yazılmaz
    row = {"Open": t["open"], "High": t["high"], "Low": t["low"], "Close": t["close"]}
    if "Volume" in df.columns:
        row["Volume"] = t["volume"]
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
