from flask import Flask, jsonify, render_template, Response, request
import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime, date
import threading
import collections
import logging
import time
import json
import os
import requests
from blog_content import ARTICLES, ARTICLES_BY_SLUG, CATEGORIES

app = Flask(__name__)

# ── Sinyal görünen ad eşlemesi (iç değer AL/SAT/BEKLE değişmez) ───────────────
_SIGNAL_LABELS = {'AL': 'Güçlü Trend', 'SAT': 'Zayıf Trend', 'BEKLE': 'Belirsiz'}

@app.template_filter('signal_label')
def signal_label_filter(signal):
    return _SIGNAL_LABELS.get(signal, signal)


def _clean(obj):
    """NaN/Inf değerlerini None'a çevir — JSON'da NaN geçersiz, JS crash yapar."""
    import math
    if isinstance(obj, float):
        return None if (math.isnan(obj) or math.isinf(obj)) else obj
    if isinstance(obj, dict):
        return {k: _clean(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_clean(v) for v in obj]
    return obj


def safe_json(data):
    """NaN-temizlenmiş JSON Response döner."""
    return Response(
        json.dumps(_clean(data)),
        mimetype="application/json",
    )

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("bist30")

# BIST100 hisse listesi (XU030 endeks dahil)
BIST100 = [
    # ── BIST30 ──────────────────────────────────────────
    "AKBNK", "ARCLK", "ASELS", "BIMAS", "EKGYO",
    "EREGL", "FROTO", "GARAN", "HEKTS", "ISCTR",
    "KCHOL", "KRDMD", "MGROS", "ODAS", "OYAKC",
    "PGSUS", "SAHOL", "SASA", "SISE", "SOKM",
    "TAVHL", "TCELL", "THYAO", "TKFEN", "TOASO",
    "TUPRS", "VAKBN", "YKBNK",
    # ── BIST100 ek hisseler ─────────────────────────────
    "AEFES", "AGHOL", "AKSA",  "AKSEN", "ALARK",
    "ALBRK", "ALFAS", "ALGYO", "ALKIM",
    "ANHYT", "ANSGR", "ASUZU", "BJKAS", "BRSAN",
    "BRYAT", "BUCIM", "CCOLA", "CIMSA", "CWENE",
    "DOAS",  "DOHOL", "EGEEN", "ENJSA", "ENKAI",
    "EUPWR", "FENER", "GENIL", "GLYHO", "GUBRF",
    "HALKB", "INDES", "ISDMR", "ISGYO",
    "ISMEN", "IZMDC", "JANTS", "KARTN", "KCAER",
    "KLNMA", "KONTR", "KORDS",
    "LOGO",  "MAVI",  "NETAS", "NTHOL",
    "OTKAR", "PARSN", "PETKM", "PRKAB", "RYSAS",
    "SARKY", "SELEC", "SMRTG", "TATGD", "TTKOM",
    "TTRAK", "TURSG", "ULKER", "VESBE", "VESTL",
    "YATAS", "ZOREN",
    # ── BIST100+ genişleme ──────────────────────────────
    "ADEL",  "ADESE", "AKMGY", "AKGRT", "ARSAN",
    "AYCES", "BASGZ", "BIOEN", "BOSSA", "CEMTS",
    "CEMAS", "CLEBI", "CRDFA", "DENGE", "DNISI",
    "DOGUB", "DURDO", "DYOBY", "ECILC",
    "EDIP",  "EGGUB", "EGPRO", "EMKEL", "ERBOS",
    "ERSU",  "ESCOM", "FMIZP", "FORMT", "GESAN",
    "GSDHO", "GSRAY", "GOKNR", "HDFGS", "HLGYO",
    "HTTBT", "IEYHO", "ISKPL", "ISFIN",
    "KAPLM", "KATMR", "KMPUR", "KONYA",
    "KRSTL", "LKMNH", "LUKSK", "MAKTK", "MPARK",
    "MEDTR", "MEGAP", "MTRKS",
    "NATEN", "NIBAS", "NUHCM", "ORGE",
    # ── Endeks ──────────────────────────────────────────
    "XU030",
]
# Geriye dönük uyumluluk için alias
BIST30 = BIST100

STOCK_NAMES = {
    # ── BIST30 ──────────────────────────────────────────
    "AKBNK": "Akbank T.A.Ş.",
    "ARCLK": "Arçelik A.Ş.",
    "ASELS": "Aselsan Elektronik Sanayi",
    "BIMAS": "BİM Birleşik Mağazalar",
    "EKGYO": "Emlak Konut GYO",
    "EREGL": "Ereğli Demir ve Çelik",
    "FROTO": "Ford Otomotiv Sanayi",
    "GARAN": "Garanti BBVA",
    "HEKTS": "Hektaş Ticaret T.A.Ş.",
    "ISCTR": "İş Bankası (C)",
    "KCHOL": "Koç Holding A.Ş.",
    "KRDMD": "Kardemir Karabük Demir Çelik",
    "MGROS": "Migros Ticaret A.Ş.",
    "ODAS":  "Odaş Elektrik Üretim",
    "OYAKC": "Oyak Çimento Fabrikaları",
    "PGSUS": "Pegasus Hava Taşımacılığı",
    "SAHOL": "Sabancı Holding",
    "SASA":  "Sasa Polyester Sanayi",
    "SISE":  "Türkiye Şişe ve Cam Fabrikaları",
    "SOKM":  "Şok Marketler Ticaret",
    "TAVHL": "TAV Havalimanları Holding",
    "TCELL": "Turkcell İletişim Hizmetleri",
    "THYAO": "Türk Hava Yolları",
    "TKFEN": "Tekfen Holding A.Ş.",
    "TOASO": "Tofaş Türk Otomobil Fabrikası",
    "TUPRS": "Tüpraş Türkiye Petrol Rafinerileri",
    "VAKBN": "Vakıfbank",
    "YKBNK": "Yapı ve Kredi Bankası",
    # ── BIST100 ek hisseler ─────────────────────────────
    "AEFES": "Anadolu Efes Biracılık",
    "AGHOL": "AG Anadolu Grubu Holding",
    "AKSA":  "Aksa Akrilik Kimya Sanayii",
    "AKSEN": "Aksen Enerji",
    "ALARK": "Alarko Holding",
    "ALBRK": "Albaraka Türk",
    "ALFAS": "Alfa Solar Enerji",
    "ALGYO": "Alarko GYO",
    "ALKIM": "Alkim Kimya Sanayii",
    "ANACM": "Anadolu Cam Sanayii",
    "ANHYT": "Anadolu Hayat Emeklilik",
    "ANSGR": "Anadolu Sigorta",
    "ASUZU": "Anadolu Isuzu",
    "BJKAS": "Beşiktaş JK",
    "BRSAN": "Borçelik Çelik Sanayii",
    "BRYAT": "BR Yatırım Holding",
    "BUCIM": "Bursa Çimento",
    "CCOLA": "Coca-Cola İçecek A.Ş.",
    "CIMSA": "Çimsa Çimento",
    "CWENE": "CW Enerji",
    "DOAS":  "Doğuş Otomotiv",
    "DOHOL": "Doğan Holding",
    "EGEEN": "Ege Endüstri",
    "ENJSA": "Enerjisa Enerji",
    "ENKAI": "Enka İnşaat",
    "EUPWR": "Europower Enerji",
    "FENER": "Fenerbahçe SK",
    "GENIL": "Gen İlaç",
    "GLYHO": "Global Yatırım Holding",
    "GUBRF": "Gübre Fabrikaları T.A.Ş.",
    "HALKB": "Halk Bankası",
    "INDES": "İndeks Bilgisayar",
    "ISDMR": "İskenderun Demir ve Çelik",
    "ISGYO": "İş GYO",
    "ISMEN": "İş Yatırım Menkul Değerler",
    "IZMDC": "İzmir Demir Çelik",
    "JANTS": "Jantsa Jant Sanayii",
    "KARTN": "Kartonsan Karton Sanayii",
    "KCAER": "Kocaer Çelik",
    "KLNMA": "Türkiye Kalkınma ve Yatırım Bankası",
    "KONTR": "Kontrolmatik Teknoloji",
    "KORDS": "Kordsa Teknik Tekstil",
    "LOGO":  "Logo Yazılım",
    "MAVI":  "Mavi Giyim",
    "NETAS": "NetAş Telekomünikasyon",
    "NTHOL": "Net Holding",
    "OTKAR": "Otokar Otomotiv",
    "PARSN": "Parsan Makina Parçaları",
    "PETKM": "Petkim Petrokimya",
    "PRKAB": "Park Elektrik Üretim",
    "RYSAS": "Reysaş Gayrimenkul",
    "SARKY": "Sarkuysan Elektrolitik Bakır",
    "SELEC": "Selçuk Ecza Deposu",
    "SMRTG": "Smart Güneş Enerjisi",
    "TATGD": "Tat Gıda Sanayi",
    "TTKOM": "Türk Telekom",
    "TTRAK": "Türk Traktör",
    "TURSG": "Türkiye Sigorta",
    "ULKER": "Ülker Bisküvi",
    "VESBE": "Vestel Beyaz Eşya",
    "VESTL": "Vestel Elektronik",
    "YATAS": "Yataş Yatak ve Yorgan",
    "ZOREN": "Zorlu Enerji",
    # ── BIST100+ genişleme ───────────────────────────────
    "ADEL":  "Adel Kalemcilik",
    "ADESE": "Adese Alışveriş Merkezleri",
    "AKMGY": "Akmerkez GYO",
    "AKGRT": "Aksigorta A.Ş.",
    "ARSAN": "Arsan Tekstil",
    "AYCES": "Ayces Turizm",
    "BASGZ": "Başgüç Enerji",
    "BIOEN": "Biotrend Çevre",
    "BOSSA": "Bossa Ticaret ve Sanayi",
    "CEMTS": "Çemtaş Çelik Makine",
    "CEMAS": "Çemaş Döküm Sanayi",
    "CLEBI": "Çelebi Hava Servisi",
    "CRDFA": "Creditwest Faktoring",
    "DENGE": "Denge Yatırım Holding",
    "DNISI": "Deniz İnşaat",
    "DOBUR": "Doğuş Otomotiv Servis",
    "DOGUB": "Doğuş Holding",
    "DURDO": "Duran Doğan Basım",
    "DYOBY": "DYO Boya Fabrikaları",
    "ECILC": "Eczacıbaşı İlaç",
    "EDIP":  "Edip İplik Sanayi",
    "EGGUB": "Ege Gübre Sanayi",
    "EGPRO": "Ege Profil Ticaret",
    "EMKEL": "Emkel Elektrik Malzemeleri",
    "ERBOS": "Erbosan Erciyas Boru",
    "ERSU":  "Ersu Meyve ve Gıda",
    "ESCOM": "Escort Teknoloji",
    "FMIZP": "Formateks Tekstil",
    "FORMT": "Formosa Asya Holding",
    "GESAN": "Gersan Elektrik Ticaret",
    "GSDHO": "GSD Holding",
    "GSRAY": "Galatasaray Sportif",
    "GOKNR": "Göknel Holding",
    "HDFGS": "Hedef Girişim Sermayesi",
    "HLGYO": "Halk GYO",
    "HTTBT": "Hat Teknoloji",
    "IEYHO": "İEYHO İnşaat",
    "IPMAT": "İpek Matbaacılık",
    "ISKPL": "İş Yapı GYO",
    "ISFIN": "İş Finansal Kiralama",
    "KAPLM": "Kaplamin Ambalaj",
    "KATMR": "Katmerciler Araç Üstü",
    "KERVT": "Kervansaray Yatırım",
    "KMPUR": "Kâmpur Enerji",
    "KONYA": "Konya Çimento",
    "KRSTL": "Kristal Kola",
    "LKMNH": "Lokman Hekim",
    "LUKSK": "Lüks Kadife",
    "MAKTK": "Maktek Makine",
    "MPARK": "Mia Teknoloji (MParKEY)",
    "MEDTR": "Meditera Tıbbi Malzeme",
    "MEGAP": "Mega Polietilen",
    "MIPAZ": "Mipaz Petrol",
    "MRDIN": "Mardin Çimento",
    "MTRKS": "Matriks Bilgi Dağıtım",
    "MUTLU": "Mutlu Akü ve Malzemeleri",
    "NATEN": "Naturel Enerji",
    "NIBAS": "Niğbaş Niğde Beton",
    "NUHCM": "Nuh Çimento",
    "ORGE":  "Orge Enerji Elektrik",
    # ── Endeks ──────────────────────────────────────────
    "XU030": "BIST 30 Endeksi",
}

# ── Sektör sınıflandırması ────────────────────────────────────────────────────
SECTORS = {
    "Bankacılık":    ["AKBNK", "GARAN", "HALKB", "ISCTR", "VAKBN", "YKBNK",
                      "ALBRK", "KLNMA", "ISMEN", "ISFIN", "CRDFA"],
    "Holding":       ["KCHOL", "SAHOL", "AGHOL", "ALARK", "DOHOL", "GLYHO",
                      "NTHOL", "TKFEN", "BRYAT", "GSDHO", "DENGE", "HDFGS",
                      "DOGUB", "DOBUR", "GOKNR"],
    "Sanayi":        ["ARCLK", "ASELS", "EREGL", "FROTO", "KRDMD", "TOASO",
                      "ASUZU", "BRSAN", "DOAS",  "ISDMR", "IZMDC", "JANTS",
                      "KCAER", "KORDS", "OTKAR", "PARSN", "SARKY", "TTRAK",
                      "VESTL", "VESBE", "YATAS", "ARSAN", "BOSSA", "CEMTS",
                      "CEMAS", "EDIP",  "EMKEL", "ERBOS", "EGGUB", "EGPRO",
                      "GESAN", "KAPLM", "KATMR", "LKMNH", "LUKSK", "MAKTK",
                      "MUTLU", "NIBAS", "NUHCM"],
    "Enerji":        ["AKSA",  "AKSEN", "ALFAS", "CWENE", "ENJSA", "ENKAI",
                      "EUPWR", "ODAS",  "PRKAB", "SMRTG", "TUPRS", "ZOREN",
                      "BASGZ", "BIOEN", "NATEN", "ORGE"],
    "Perakende":     ["BIMAS", "MGROS", "SOKM",  "MAVI",  "SELEC", "ULKER",
                      "ADESE", "KRSTL"],
    "Teknoloji":     ["INDES", "LOGO",  "NETAS", "KONTR", "ESCOM", "MTRKS",
                      "HTTBT", "MPARK"],
    "Telekom":       ["TCELL", "TTKOM"],
    "Ulaşım":        ["PGSUS", "TAVHL", "THYAO", "RYSAS", "CLEBI", "AYCES"],
    "GYO":           ["EKGYO", "ALGYO", "ISGYO", "AKMGY", "HLGYO", "ISKPL"],
    "Kimya/Malzeme": ["ALKIM", "ANACM", "BUCIM", "CIMSA", "GUBRF", "HEKTS",
                      "OYAKC", "PETKM", "SASA",  "SISE",  "TATGD", "AEFES",
                      "CCOLA", "EGEEN", "DYOBY", "ERSU",  "KMPUR", "KONYA",
                      "MEGAP", "MIPAZ", "MRDIN", "NUHCM"],
    "Sigorta":       ["ANHYT", "ANSGR", "TURSG", "AKGRT"],
    "Diğer":         ["BJKAS", "FENER", "GENIL", "KARTN", "ADEL",  "DURDO",
                      "ECILC", "FMIZP", "FORMT", "GSRAY", "IEYHO", "IPMAT",
                      "KERVT", "LKMNH", "MEDTR", "PARSN"],
}

_cache       = {"data": [], "updated_at": None}
_live_prices = {}
_lock        = threading.Lock()
_sse_clients = []
_sse_lock    = threading.Lock()
_bt_cache    = {"data": None, "computed_at": None}   # backtest cache


def _push_sse(payload: dict):
    msg = f"data: {json.dumps(payload)}\n\n"
    with _sse_lock:
        dead = []
        for q in _sse_clients:
            try:
                q.append(msg)
            except Exception:
                dead.append(q)
        for q in dead:
            _sse_clients.remove(q)


def compute_ema(series, period):
    return series.ewm(span=period, adjust=False).mean()


def compute_adx(high, low, close, period=14):
    tr1 = high - low
    tr2 = (high - close.shift()).abs()
    tr3 = (low - close.shift()).abs()
    tr  = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)

    plus_dm  = high.diff()
    minus_dm = -low.diff()
    plus_dm  = plus_dm.where((plus_dm > minus_dm) & (plus_dm > 0), 0)
    minus_dm = minus_dm.where((minus_dm > plus_dm) & (minus_dm > 0), 0)

    atr      = tr.ewm(com=period - 1, adjust=False).mean()
    plus_di  = 100 * plus_dm.ewm(com=period - 1, adjust=False).mean() / atr
    minus_di = 100 * minus_dm.ewm(com=period - 1, adjust=False).mean() / atr

    dx  = 100 * (plus_di - minus_di).abs() / (plus_di + minus_di).replace(0, np.nan)
    adx = dx.ewm(com=period - 1, adjust=False).mean()
    return adx, plus_di, minus_di


def compute_supertrend(high, low, close, period=10, multiplier=3):
    """ATR(10,3) — numpy tabanlı.
    Returns (direction Series, st_line Series); warmup barları NaN."""
    hl2 = (high.values + low.values) / 2
    cl  = close.values
    hi  = high.values
    lo  = low.values
    n   = len(cl)

    # True Range
    tr_arr      = np.empty(n)
    tr_arr[0]   = hi[0] - lo[0]
    tr_arr[1:]  = np.maximum(hi[1:] - lo[1:],
                  np.maximum(np.abs(hi[1:] - cl[:-1]),
                             np.abs(lo[1:] - cl[:-1])))

    # ATR — Wilder smoothing (SMA seed)
    atr         = np.full(n, np.nan)
    if n >= period:
        atr[period - 1] = np.mean(tr_arr[:period])
        for i in range(period, n):
            atr[i] = (atr[i - 1] * (period - 1) + tr_arr[i]) / period

    basic_upper = hl2 + multiplier * atr   # NaN where atr is NaN
    basic_lower = hl2 - multiplier * atr

    final_upper = basic_upper.copy()
    final_lower = basic_lower.copy()
    direction   = np.ones(n, dtype=int)
    st_line     = np.full(n, np.nan)

    # Geçerli ilk index (ATR warmup sonrası)
    start = period  # atr[period-1] geçerli, ama final band için period'dan başla

    for i in range(start, n):
        pu = final_upper[i - 1]
        pl = final_lower[i - 1]

        # NaN warmup koruması
        if np.isnan(pu):
            pu = basic_upper[i]
        if np.isnan(pl):
            pl = basic_lower[i]

        bu = basic_upper[i]
        bl = basic_lower[i]

        final_upper[i] = bu if (np.isnan(bu) or bu < pu or cl[i - 1] > pu) else pu
        final_lower[i] = bl if (np.isnan(bl) or bl > pl or cl[i - 1] < pl) else pl

        if direction[i - 1] == 1:
            direction[i] = 1 if cl[i] >= final_lower[i] else -1
        else:
            direction[i] = -1 if cl[i] <= final_upper[i] else 1

        st_line[i] = final_lower[i] if direction[i] == 1 else final_upper[i]

    dir_series = pd.Series(direction, index=close.index)
    stl_series = pd.Series(st_line,   index=close.index)
    return dir_series, stl_series


def _fill_intraday_gaps(df, ticker):
    """Günlük data'da eksik günleri 1m data'dan OHLC sentezleyerek doldur.
    yfinance bazen son 1-2 günün daily barını geciktiriyor."""
    try:
        df5d = yf.download(ticker, period="5d", interval="1m",
                           progress=False, auto_adjust=True, timeout=20)
        if df5d is None or df5d.empty:
            return df
        if isinstance(df5d.columns, pd.MultiIndex):
            df5d.columns = df5d.columns.get_level_values(0)
            df5d = df5d.loc[:, ~df5d.columns.duplicated()]

        last_daily = df.index[-1].date()
        added = False
        for day in sorted(set(df5d.index.date)):
            if day <= last_daily:
                continue
            day_bars = df5d[df5d.index.map(lambda x: x.date()) == day].dropna()
            if len(day_bars) < 30:   # kısmen gelen gün, geç
                continue
            ts = pd.Timestamp(day, tz=df.index.tz)
            synth = pd.DataFrame({
                "Open":   float(day_bars["Open"].iloc[0]),
                "High":   float(day_bars["High"].max()),
                "Low":    float(day_bars["Low"].min()),
                "Close":  float(day_bars["Close"].iloc[-1]),
                "Volume": float(day_bars["Volume"].sum()) if "Volume" in day_bars else 0,
            }, index=pd.DatetimeIndex([ts]))
            df = pd.concat([df, synth[df.columns]])
            added = True
        if added:
            logger.info("_fill_intraday_gaps(%s): eksik gun(ler) 1m'den eklendi", ticker)
        return df
    except Exception as e:
        logger.warning("_fill_intraday_gaps(%s): %s", ticker, e)
        return df


def _weekly_trend(ticker: str) -> int:
    """Haftalık EMA20 yönü: +1 yükselen, -1 düşen, 0 belirsiz/hata."""
    try:
        wdf = yf.download(ticker, period="1y", interval="1wk",
                          progress=False, auto_adjust=True, timeout=20)
        if wdf is None or len(wdf) < 25:
            return 0
        if isinstance(wdf.columns, pd.MultiIndex):
            wdf.columns = wdf.columns.get_level_values(0)
            wdf = wdf.loc[:, ~wdf.columns.duplicated()]
        wdf    = wdf.dropna()
        wclose = wdf["Close"].squeeze()
        wema20 = compute_ema(wclose, 20)
        if len(wema20) < 2:
            return 0
        return 1 if float(wema20.iloc[-1]) > float(wema20.iloc[-2]) else -1
    except Exception:
        return 0


def analyze(ticker_base):
    ticker = ticker_base + ".IS" if ticker_base != "XU030" else "XU030.IS"

    try:
        weekly_dir = _weekly_trend(ticker)

        df = yf.download(ticker, period="2y", interval="1d",
                         progress=False, auto_adjust=True, timeout=30)
        if df is None or len(df) < 120:
            return None

        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
            df = df.loc[:, ~df.columns.duplicated()]

        df    = df.dropna()
        df    = _fill_intraday_gaps(df, ticker)   # yfinance gecikmeli günleri 1m'den tamamla
        df    = df.sort_index()
        close = df["Close"].squeeze()
        high  = df["High"].squeeze()
        low   = df["Low"].squeeze()

        ema12                  = compute_ema(close, 12)
        ema99                  = compute_ema(close, 99)
        adx, di_plus, di_minus = compute_adx(high, low, close)
        supertrend, st_line    = compute_supertrend(high, low, close)

        def v(s):  return float(s.iloc[-1])
        def v2(s): return float(s.iloc[-2])

        c       = v(close)
        e12     = v(ema12);   e99 = v(ema99)
        adx_val = v(adx)
        di_p    = v(di_plus); di_m = v(di_minus)
        st_val  = int(v(supertrend))
        _sl_raw = float(st_line.iloc[-1])
        sl_val  = round(_sl_raw, 2) if not np.isnan(_sl_raw) else None

        prev_c     = v2(close)
        change_pct = ((c - prev_c) / prev_c) * 100 if prev_c != 0 else 0

        # ── 3-Kriter Sinyal Motoru: ST + ADX≥25 + EMA12/99 ─────────────
        st_bull  = st_val == 1
        st_bear  = st_val == -1
        adx_bull = adx_val >= 25 and di_p > di_m
        adx_bear = adx_val >= 25 and di_m > di_p
        e12_bull = e12 > e99
        e12_bear = e12 < e99

        bull_score = int(st_bull) + int(adx_bull) + int(e12_bull)  # max 3
        bear_score = int(st_bear) + int(adx_bear) + int(e12_bear)  # max 3

        # Haftalık gate: büyük ters trendde sinyal üretme
        if bull_score >= 3 and weekly_dir != -1:
            signal = "AL"
        elif bear_score >= 3 and weekly_dir != 1:
            signal = "SAT"
        else:
            signal = "BEKLE"

        # ── Sinyal tarihi & süre ─────────────────────────────────────────
        def bar_signal(i):
            ei12  = float(ema12.iloc[i]);  ei99  = float(ema99.iloc[i])
            ai    = float(adx.iloc[i])
            dip_i = float(di_plus.iloc[i]); dim_i = float(di_minus.iloc[i])
            sti   = int(supertrend.iloc[i])
            bs  = int(sti == 1)  + int(ai >= 25 and dip_i > dim_i) + int(ei12 > ei99)
            brs = int(sti == -1) + int(ai >= 25 and dim_i > dip_i) + int(ei12 < ei99)
            return "AL" if bs >= 3 else "SAT" if brs >= 3 else "BEKLE"

        today_str   = datetime.now().strftime("%d.%m.%Y")
        signal_date = today_str
        signal_bars = 1
        n = len(close)
        try:
            for i in range(n - 2, max(n - 120, 0), -1):
                if bar_signal(i) != signal:
                    signal_date = close.index[i + 1].strftime("%d.%m.%Y")
                    signal_bars = (n - 1) - (i + 1) + 1
                    break
            else:
                signal_date = close.index[max(n - 120, 0)].strftime("%d.%m.%Y")
                signal_bars = n - max(n - 120, 0)
        except Exception:
            pass

        # Sinyal başındaki kapanış fiyatı
        signal_start = max(0, (n - 1) - (signal_bars - 1))
        signal_price = round(float(close.iloc[signal_start]), 2) if signal != "BEKLE" else None

        is_new_signal = (signal_date == today_str)
        confirmed     = signal != "BEKLE" and signal_bars >= 3

        return {
            "ticker":        ticker_base,
            "price":         round(c, 2),
            "change_pct":    round(change_pct, 2),
            "signal":        signal,
            "signal_date":   signal_date,
            "signal_bars":   signal_bars,
            "signal_price":  signal_price,
            "sl_level":      sl_val,
            "is_new_signal": is_new_signal,
            "confirmed":     confirmed,
            "bull_score":    bull_score,
            "bear_score":    bear_score,
            "weekly_trend":  weekly_dir,
            "indicators": {
                "supertrend": {
                    "label": "ST",
                    "value": "LONG" if st_bull else "SHORT",
                    "bull":  st_bull,  "bear": st_bear,
                },
                "adx": {
                    "label": f"ADX {adx_val:.0f}",
                    "value": f"DI+{di_p:.0f}/DI-{di_m:.0f}",
                    "bull":  adx_bull, "bear": adx_bear,
                },
                "ema1299": {
                    "label": "EMA12/99",
                    "value": f"{e12:.0f}/{e99:.0f}",
                    "bull":  e12_bull, "bear": e12_bear,
                },
            },
        }
    except Exception as e:
        logger.error("analyze(%s): %s", ticker_base, e, exc_info=True)
        return None


# ── Telegram Bildirim ─────────────────────────────────────────────────────────
TELEGRAM_BOT_TOKEN  = os.environ.get("TELEGRAM_BOT_TOKEN",  "")
TELEGRAM_CHANNEL_ID = os.environ.get("TELEGRAM_CHANNEL_ID", "")
_prev_signals       = {}   # {ticker: signal}  — bir önceki döngü sinyalleri


def _send_telegram(text):
    """Telegram kanalına/gruba mesaj gönderir."""
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHANNEL_ID:
        return
    try:
        url  = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        resp = requests.post(url, json={
            "chat_id":    TELEGRAM_CHANNEL_ID,
            "text":       text,
            "parse_mode": "HTML",
            "disable_web_page_preview": True,
        }, timeout=10)
        if not resp.ok:
            logger.warning("Telegram gönderimi başarısız: %s", resp.text)
    except Exception as e:
        logger.warning("Telegram hatası: %s", e)


def _notify_signal_changes(new_results):
    """Önceki döngüye göre sinyal değişimlerini tespit et ve Telegram'a bildir."""
    global _prev_signals
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHANNEL_ID:
        return
    # Borsa saatleri dışında bildirim gönderme (UTC+3: 10:00-18:30)
    now_utc  = datetime.utcnow()
    now_tr   = now_utc.hour * 60 + now_utc.minute + 180  # UTC+3 dakika
    if not (600 <= now_tr <= 1110):  # 10:00–18:30
        return

    new_data_map = {r["ticker"]: r for r in new_results if r["ticker"] != "XU030"}
    new_sig_map  = {t: d["signal"] for t, d in new_data_map.items()}
    changes = []
    for t, new_sig in new_sig_map.items():
        old_sig = _prev_signals.get(t)
        if old_sig and old_sig != new_sig and new_sig in ("AL", "SAT"):
            changes.append((t, old_sig, new_sig, new_data_map[t]))

    if changes:
        sig_emoji = {"AL": "🟢", "SAT": "🔴", "BEKLE": "⚪"}
        lines = [f"<b>📊 BorsaPusula — Sinyal Değişimi</b>\n"]
        for t, old, new, stock in changes[:10]:   # max 10 aynı mesajda
            e    = sig_emoji.get(new, "")
            name = STOCK_NAMES.get(t, t)
            lbl  = "Güçlü Trend ▲" if new == "AL" else "Zayıf Trend ▼"
            price = stock.get("price") or ""
            price_str = f" — {price:.2f} ₺" if price else ""
            lines.append(f"{e} <b>{t}</b> ({name}){price_str}")
            lines.append(f"   <i>{old} → {lbl}</i>")
        lines.append(f"\n<a href='https://borsapusula.com'>borsapusula.com</a>")
        lines.append("<i>⚠️ Yatırım tavsiyesi değildir.</i>")
        _send_telegram("\n".join(lines))

    _prev_signals = new_sig_map


def refresh_data():
    results = []
    for t in BIST30:
        r = analyze(t)
        if r:
            results.append(r)
        time.sleep(0.3)

    results.sort(key=lambda x: (
        0 if x.get("is_new_signal") else 1,
        0 if x["signal"] == "AL" else 1 if x["signal"] == "SAT" else 2,
        -x["bull_score"] if x["signal"] == "AL" else -x["bear_score"]
    ))

    _notify_signal_changes(results)

    with _lock:
        _cache["data"] = results
        _cache["updated_at"] = datetime.now().strftime("%d.%m.%Y %H:%M:%S")


def fetch_live_prices():
    tickers_str = " ".join(t + ".IS" for t in BIST30)
    try:
        df = yf.download(
            tickers_str, period="2d", interval="1m",
            progress=False, auto_adjust=True, group_by="ticker", timeout=30
        )
        if df is None or df.empty:
            return

        payload = {}
        now_str  = datetime.now().strftime("%H:%M:%S")

        for t in BIST30:
            try:
                sym = t + ".IS"
                if isinstance(df.columns, pd.MultiIndex):
                    lvls = df.columns.get_level_values(0)
                    if sym in lvls:
                        closes = df[sym]["Close"].dropna()
                    else:
                        continue
                else:
                    closes = df["Close"].dropna()

                if closes is None or len(closes) < 2:
                    continue

                price      = float(closes.iloc[-1])
                today_date = closes.index[-1].date()
                prev_bars  = closes[closes.index.map(lambda x: x.date()) < today_date]
                prev       = float(prev_bars.iloc[-1]) if len(prev_bars) > 0 else float(closes.iloc[-2])
                chg        = ((price - prev) / prev * 100) if prev else 0

                payload[t] = {
                    "price":      round(price, 2),
                    "change_pct": round(chg, 2),
                    "updated":    now_str,
                }
            except Exception:
                continue

        if payload:
            with _lock:
                _live_prices.update(payload)
            _push_sse({"type": "prices", "data": payload, "ts": now_str})

    except Exception as e:
        logger.error("fetch_live_prices: %s", e, exc_info=True)


def background_live_prices():
    while True:
        fetch_live_prices()
        time.sleep(30)


def background_refresh():
    while True:
        refresh_chart()
        refresh_data()
        time.sleep(900)


# ── Güvenlik Headerları ───────────────────────────────────────────────────────
@app.after_request
def set_security_headers(response):
    # X-Frame-Options — clickjacking koruması
    response.headers["X-Frame-Options"] = "SAMEORIGIN"
    # X-Content-Type-Options — MIME sniffing koruması
    response.headers["X-Content-Type-Options"] = "nosniff"
    # Referrer-Policy
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    # Permissions-Policy
    response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"
    # CSP — SSE, Google Fonts ve self-hosted JS/CSS izni
    if response.content_type and "text/html" in response.content_type:
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline'; "
            "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
            "connect-src 'self'; "
            "img-src 'self' data:; "
            "font-src 'self' https://fonts.gstatic.com; "
            "frame-ancestors 'none';"
        )
    return response


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/data")
def api_data():
    with _lock:
        stocks = list(_cache["data"])
    # Sektör bilgisini ekle
    for s in stocks:
        s["sector"] = _get_sector(s["ticker"])
    return safe_json({
        "stocks":     stocks,
        "updated_at": _cache["updated_at"],
        "loading":    len(stocks) == 0,
        "sectors":    list(SECTORS.keys()),
    })


@app.route("/api/refresh", methods=["POST"])
def api_refresh():
    threading.Thread(target=refresh_data, daemon=True).start()
    return jsonify({"status": "refreshing"})


@app.route("/api/stream")
def api_stream():
    client_queue = collections.deque()
    with _sse_lock:
        _sse_clients.append(client_queue)

    with _lock:
        initial = dict(_live_prices)
    initial_msg = (
        f"data: {json.dumps({'type': 'prices', 'data': initial, 'ts': datetime.now().strftime('%H:%M:%S')})}\n\n"
        if initial else ""
    )

    def generate():
        try:
            if initial_msg:
                yield initial_msg
            while True:
                while client_queue:
                    yield client_queue.popleft()
                time.sleep(0.5)
        finally:
            with _sse_lock:
                if client_queue in _sse_clients:
                    _sse_clients.remove(client_queue)

    return Response(
        generate(),
        mimetype="text/event-stream",
        headers={
            "Cache-Control":     "no-cache",
            "X-Accel-Buffering": "no",
            "Connection":        "keep-alive",
        },
    )


def _safe_float(val):
    if hasattr(val, "iloc"):
        return float(val.iloc[0])
    if hasattr(val, "item"):
        return float(val.item())
    return float(val)


def get_chart_data():
    """XU030 grafik verisi — _compute_chart_data wrapper (5y period)."""
    DISPLAY_BARS = 500
    WARMUP_MIN   = 200

    try:
        df = yf.Ticker("XU030.IS").history(period="5y", interval="1d", auto_adjust=True)
        if df is None or len(df) < WARMUP_MIN + 50:
            return None

        df    = df[["Open", "High", "Low", "Close"]].dropna()
        df    = _fill_intraday_gaps(df, "XU030.IS")   # eksik günleri tamamla
        df    = df.sort_index()
        close = df["Close"]
        high  = df["High"]
        low   = df["Low"]
        open_ = df["Open"]

        # ── İndikatörleri FULL veri üzerinde hesapla (warmup) ────────────
        ema12                      = compute_ema(close, 12)
        ema99                      = compute_ema(close, 99)
        adx, di_plus_s, di_minus_s = compute_adx(high, low, close)
        supertrend, st_line_s      = compute_supertrend(high, low, close)

        # ── Gösterim için son DISPLAY_BARS barı kes ───────────────────────
        show_idx = df.index[-DISPLAY_BARS:]
        show_set = set(show_idx.strftime("%Y-%m-%d"))

        def series(s):
            out = []
            for ts, val in s.items():
                if pd.isna(val): continue
                d = ts.strftime("%Y-%m-%d")
                if d not in show_set: continue
                out.append({"time": d, "value": round(float(val), 4)})
            return out

        # OHLC
        ohlc = []
        for ts in show_idx:
            try:
                ohlc.append({
                    "time":  ts.strftime("%Y-%m-%d"),
                    "open":  round(_safe_float(open_[ts]),  2),
                    "high":  round(_safe_float(high[ts]),   2),
                    "low":   round(_safe_float(low[ts]),    2),
                    "close": round(_safe_float(close[ts]),  2),
                })
            except Exception:
                continue

        # Supertrend çizgisi — iloc ile eriş (loc/label indexing sorununu önler)
        st_line_data = []
        stl_arr = st_line_s.values
        std_arr = supertrend.values
        all_dates = [ts.strftime("%Y-%m-%d") for ts in df.index]
        for i, d_str in enumerate(all_dates):
            if d_str not in show_set: continue
            stl = stl_arr[i]
            if np.isnan(stl): continue
            st_line_data.append({
                "time":  d_str,
                "value": round(float(stl), 2),
                "bull":  int(std_arr[i]) == 1,
            })

        # ── Sinyal değişim işaretçileri (grafik okleri) ──────────────────
        def bar_sig(i):
            ei12  = float(ema12.iloc[i]);  ei99  = float(ema99.iloc[i])
            ai    = float(adx.iloc[i])
            dip_i = float(di_plus_s.iloc[i]); dim_i = float(di_minus_s.iloc[i])
            sti   = int(supertrend.iloc[i])
            bs  = int(sti == 1)  + int(ai >= 25 and dip_i > dim_i) + int(ei12 > ei99)
            brs = int(sti == -1) + int(ai >= 25 and dim_i > dip_i) + int(ei12 < ei99)
            return "AL" if bs >= 3 else "SAT" if brs >= 3 else "BEKLE"

        markers   = []
        prev_bsig = "BEKLE"
        for i in range(200, len(close)):
            sig = bar_sig(i)
            if sig != prev_bsig and sig != "BEKLE":
                d_str = close.index[i].strftime("%Y-%m-%d")
                if d_str in show_set:
                    markers.append({
                        "time":     d_str,
                        "position": "belowBar" if sig == "AL" else "aboveBar",
                        "color":    "#3fb950"  if sig == "AL" else "#f85149",
                        "shape":    "arrowUp"  if sig == "AL" else "arrowDown",
                        "text":     "AL"       if sig == "AL" else "SAT",
                    })
            prev_bsig = sig

        # ── Son bar değerleri ────────────────────────────────────────────
        c       = float(close.iloc[-1])
        prev_c  = float(close.iloc[-2])
        chg     = ((c - prev_c) / prev_c) * 100 if prev_c else 0
        adx_val = float(adx.iloc[-1])
        di_p    = float(di_plus_s.iloc[-1]); di_m = float(di_minus_s.iloc[-1])
        e12_val = float(ema12.iloc[-1])
        e99_val = float(ema99.iloc[-1])
        st_val   = int(supertrend.iloc[-1])
        _sl_raw  = float(st_line_s.iloc[-1])
        sl_val   = round(_sl_raw, 2) if not np.isnan(_sl_raw) else None

        st_bull  = st_val == 1;   st_bear  = st_val == -1
        adx_bull = adx_val >= 25 and di_p > di_m
        adx_bear = adx_val >= 25 and di_m > di_p
        e12_bull = e12_val > e99_val; e12_bear = e12_val < e99_val

        bull_score = int(st_bull) + int(adx_bull) + int(e12_bull)
        bear_score = int(st_bear) + int(adx_bear) + int(e12_bear)
        signal = "AL" if bull_score >= 3 else "SAT" if bear_score >= 3 else "BEKLE"

        return {
            "ohlc":      ohlc,
            "ema12":     series(ema12),
            "ema99":     series(ema99),
            "st_line":   st_line_data,
            "markers":   markers,
            "summary": {
                "price":      round(c, 2),
                "change_pct": round(chg, 2),
                "signal":     signal,
                "bull_score": bull_score,
                "bear_score": bear_score,
                "sl_level":   sl_val,
                "adx":        round(adx_val, 1),
                "e12":        round(e12_val, 1),
                "e99":        round(e99_val, 1),
                "st_bull":    st_bull,  "st_bear":  st_bear,
                "adx_bull":   adx_bull, "adx_bear": adx_bear,
                "e12_bull":   e12_bull, "e12_bear": e12_bear,
            }
        }
    except Exception as e:
        logger.error("chart error: %s", e, exc_info=True)
        return None


_chart_cache       = {"data": None, "updated_at": None}
_stock_chart_cache = {}          # {ticker: {"data": ..., "ts": float, "updated_at": str}}
_STOCK_CACHE_TTL   = 900         # 15 dakika


# ── Gemini API — AI haber özeti ──────────────────────────────────────────────
GEMINI_API_KEY  = os.environ.get("GEMINI_API_KEY", "")
_news_cache     = {}          # {ticker: {"text": str, "ts": float}}
_NEWS_CACHE_TTL = 3600 * 6   # 6 saat

def get_ai_news(ticker):
    """Gemini Flash + Google Search grounding ile Türkçe haber özeti üretir."""
    if not GEMINI_API_KEY:
        return None
    now = time.time()
    with _lock:
        cached = _news_cache.get(ticker)
        if cached and (now - cached["ts"]) < _NEWS_CACHE_TTL:
            return cached["text"]

    name    = STOCK_NAMES.get(ticker, ticker)
    prompt  = (
        f"Borsa İstanbul'da işlem gören {ticker} ({name}) hissesi hakkında "
        f"son 7 günün en önemli gelişmelerini, haberlerini ve şirket açıklamalarını "
        f"Türkçe olarak 3-5 madde halinde kısaca özetle. "
        f"Her madde 1-2 cümle olsun. Tarih belirt. Sadece maddeleri yaz, giriş/kapanış cümlesi ekleme."
    )
    try:
        url  = (f"https://generativelanguage.googleapis.com/v1beta/"
                f"models/gemini-2.5-flash:generateContent?key={GEMINI_API_KEY}")
        body = {
            "contents": [{"parts": [{"text": prompt}]}],
            "tools":    [{"google_search": {}}],
        }
        r    = requests.post(url, json=body, timeout=20)
        r.raise_for_status()
        data = r.json()
        text = (data.get("candidates", [{}])[0]
                    .get("content", {})
                    .get("parts", [{}])[0]
                    .get("text", "")).strip()
        if text:
            with _lock:
                _news_cache[ticker] = {"text": text, "ts": now}
        return text or None
    except Exception as e:
        logger.warning("get_ai_news(%s): %s", ticker, e)
        return None


_signal_explain_cache = {}           # {ticker: {"text": str, "sig": str, "ts": float}}
_SIG_EXPLAIN_TTL      = 3600 * 4    # 4 saat

def get_ai_signal_explanation(ticker, signal_data):
    """Mevcut teknik sinyal için Gemini ile kullanıcı dostu Türkçe açıklama üretir."""
    if not GEMINI_API_KEY:
        return None
    now   = time.time()
    sig   = signal_data.get("signal", "BEKLE")
    with _lock:
        cached = _signal_explain_cache.get(ticker)
        if cached and (now - cached["ts"]) < _SIG_EXPLAIN_TTL and cached.get("sig") == sig:
            return cached["text"]

    name     = STOCK_NAMES.get(ticker, ticker)
    sig_lbl  = {"AL": "Güçlü Trend (AL)", "SAT": "Zayıf Trend (SAT)", "BEKLE": "Belirsiz (BEKLE)"}.get(sig, sig)
    adx      = signal_data.get("adx", 0)
    e12      = signal_data.get("e12", 0)
    e99      = signal_data.get("e99", 0)
    di_plus  = signal_data.get("di_plus", 0)
    di_minus = signal_data.get("di_minus", 0)
    st_bull  = signal_data.get("st_bull", False)
    price    = signal_data.get("price", 0)
    sl       = signal_data.get("sl_level")
    bars     = signal_data.get("signal_bars", 1)

    sl_line = f"- Stop-Loss seviyesi: {sl:.2f} ₺\n" if sl else ""
    prompt = (
        f"Sen bir borsa analistinin yardımcısısın. "
        f"{ticker} ({name}) hissesi için şu an '{sig_lbl}' sinyali var.\n\n"
        f"Teknik gösterge değerleri:\n"
        f"- Fiyat: {price:.2f} ₺\n"
        f"- Supertrend: {'YUKARI (boğa)' if st_bull else 'AŞAĞI (ayı)'}\n"
        f"- ADX: {adx:.1f} (25 üzeri güçlü trend, 40 üzeri çok güçlü)\n"
        f"- DI+: {di_plus:.1f}, DI-: {di_minus:.1f}\n"
        f"- EMA12: {e12:.1f}, EMA99: {e99:.1f}\n"
        f"{sl_line}"
        f"- Sinyal süresi: {bars} gün\n\n"
        f"Lütfen bu sinyali yatırımcıya yönelik, sade ve anlaşılır Türkçe ile 3-4 cümle açıkla. "
        f"Teknik jargonu minimize et, herkesin anlayabileceği bir dil kullan. "
        f"Neden bu sinyal oluştu ve ne anlama geliyor kısaca anlat. "
        f"'Yatırım tavsiyesi değildir' ibaresini sonuna ekle. Başlık ekleme, sadece paragraf yaz."
    )
    try:
        url  = (f"https://generativelanguage.googleapis.com/v1beta/"
                f"models/gemini-2.5-flash:generateContent?key={GEMINI_API_KEY}")
        body = {"contents": [{"parts": [{"text": prompt}]}]}
        r    = requests.post(url, json=body, timeout=15)
        r.raise_for_status()
        data = r.json()
        text = (data.get("candidates", [{}])[0]
                    .get("content", {})
                    .get("parts", [{}])[0]
                    .get("text", "")).strip()
        if text:
            with _lock:
                _signal_explain_cache[ticker] = {"text": text, "sig": sig, "ts": now}
        return text or None
    except Exception as e:
        logger.warning("get_ai_signal_explanation(%s): %s", ticker, e)
        return None


def _generate_commentary(ticker, signal, signal_bars, signal_date, adx, di_p, di_m, e12, e99, st_bull):
    """Algoritmik teknik yorum metni üretir (SEO + kullanıcı için)."""
    name = STOCK_NAMES.get(ticker, ticker)
    adx_quality = "çok güçlü" if adx >= 40 else "güçlü" if adx >= 30 else "orta güçte" if adx >= 25 else "zayıf"

    if signal == "AL":
        trend_dir  = "yükseliş"
        st_text    = "yükseliş yönünde"
        ema_text   = f"EMA12 ({e12:.0f} ₺), EMA99 ({e99:.0f} ₺) üzerinde seyrediyor"
        di_text    = f"DI+ {di_p:.0f} DI- {di_m:.0f}'i geçmiş durumda"
        dur_text   = f"Son {signal_bars} gündür Güçlü Trend sinyali aktif" if signal_bars > 1 else "Bugün Güçlü Trend sinyali oluştu"
        if signal_date:
            dur_text += f" ({signal_date} tarihinden itibaren)" if signal_bars > 1 else ""
        return (
            f"{ticker} ({name}) hissesi {dur_text}. "
            f"Supertrend göstergesi {st_text}, ADX {adx:.0f} ile {adx_quality} bir {trend_dir} trendi işaret ediyor. "
            f"{ema_text}. {di_text}."
        )
    elif signal == "SAT":
        trend_dir  = "düşüş"
        st_text    = "düşüş yönünde"
        ema_text   = f"EMA12 ({e12:.0f} ₺), EMA99 ({e99:.0f} ₺) altında seyrediyor"
        di_text    = f"DI- {di_m:.0f} DI+ {di_p:.0f}'ün üzerinde"
        dur_text   = f"Son {signal_bars} gündür Zayıf Trend sinyali aktif" if signal_bars > 1 else "Bugün Zayıf Trend sinyali oluştu"
        if signal_date:
            dur_text += f" ({signal_date} tarihinden itibaren)" if signal_bars > 1 else ""
        return (
            f"{ticker} ({name}) hissesi {dur_text}. "
            f"Supertrend göstergesi {st_text}, ADX {adx:.0f} ile {adx_quality} bir {trend_dir} trendi işaret ediyor. "
            f"{ema_text}. {di_text}."
        )
    else:
        mixed = ""
        if st_bull and e12 > e99:
            mixed = "Supertrend ve EMA yükselen ancak ADX trend gücü henüz yetersiz."
        elif not st_bull and e12 < e99:
            mixed = "Supertrend ve EMA düşen ancak ADX trend gücü yetersiz."
        else:
            mixed = "İndikatörler birbirini teyit etmiyor, karmaşık bir görünüm var."
        return (
            f"{ticker} ({name}) hissesi şu anda net bir AL/SAT sinyali üretmiyor. "
            f"{mixed} "
            f"ADX {adx:.0f} ({adx_quality}), EMA12 {e12:.0f} / EMA99 {e99:.0f}."
        )


# ── Ortak grafik verisi hesaplama (XU030 + bireysel hisseler) ─────────────────
def _compute_chart_data(ticker_base, period="2y"):
    """Herhangi bir hisse için grafik verisi hesaplar (OHLC, EMA, ST, sinyal geçmişi)."""
    ticker      = ticker_base + ".IS" if ticker_base != "XU030" else "XU030.IS"
    DISPLAY_BARS = 500
    WARMUP_MIN   = 150

    try:
        df = yf.download(ticker, period=period, interval="1d",
                         progress=False, auto_adjust=True, timeout=30)
        if df is None or len(df) < WARMUP_MIN:
            return None

        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
            df = df.loc[:, ~df.columns.duplicated()]

        has_volume = "Volume" in df.columns
        cols = ["Open", "High", "Low", "Close"] + (["Volume"] if has_volume else [])
        df    = df[cols].dropna(subset=["Open", "High", "Low", "Close"])
        df    = _fill_intraday_gaps(df, ticker)
        df    = df.sort_index()

        close  = df["Close"]
        high   = df["High"]
        low    = df["Low"]
        open_  = df["Open"]
        volume = df["Volume"] if has_volume else None

        ema12                      = compute_ema(close, 12)
        ema99                      = compute_ema(close, 99)
        adx, di_plus_s, di_minus_s = compute_adx(high, low, close)
        supertrend, st_line_s      = compute_supertrend(high, low, close)

        show_idx = df.index[-DISPLAY_BARS:]
        show_set = set(show_idx.strftime("%Y-%m-%d"))

        def series(s):
            out = []
            for ts, val in s.items():
                if pd.isna(val): continue
                d = ts.strftime("%Y-%m-%d")
                if d not in show_set: continue
                out.append({"time": d, "value": round(float(val), 4)})
            return out

        # OHLC
        ohlc = []
        for ts in show_idx:
            try:
                ohlc.append({
                    "time":  ts.strftime("%Y-%m-%d"),
                    "open":  round(_safe_float(open_[ts]),  2),
                    "high":  round(_safe_float(high[ts]),   2),
                    "low":   round(_safe_float(low[ts]),    2),
                    "close": round(_safe_float(close[ts]),  2),
                })
            except Exception:
                continue

        # Supertrend çizgisi
        st_line_data = []
        stl_arr  = st_line_s.values
        std_arr  = supertrend.values
        all_dates = [ts.strftime("%Y-%m-%d") for ts in df.index]
        for i, d_str in enumerate(all_dates):
            if d_str not in show_set: continue
            stl = stl_arr[i]
            if np.isnan(stl): continue
            st_line_data.append({
                "time":  d_str,
                "value": round(float(stl), 2),
                "bull":  int(std_arr[i]) == 1,
            })

        # Sinyal fonksiyonu (tek bar)
        def bar_sig(i):
            ei12  = float(ema12.iloc[i]);   ei99  = float(ema99.iloc[i])
            ai    = float(adx.iloc[i])
            dip_i = float(di_plus_s.iloc[i]); dim_i = float(di_minus_s.iloc[i])
            sti   = int(supertrend.iloc[i])
            bs  = int(sti == 1)  + int(ai >= 25 and dip_i > dim_i) + int(ei12 > ei99)
            brs = int(sti == -1) + int(ai >= 25 and dim_i > dip_i) + int(ei12 < ei99)
            return "AL" if bs >= 3 else "SAT" if brs >= 3 else "BEKLE"

        # Grafik marker'ları ve sinyal geçmişi
        markers        = []
        signal_history = []
        prev_sig       = "BEKLE"
        for i in range(200, len(close)):
            sig = bar_sig(i)
            if sig != prev_sig and sig != "BEKLE":
                d_str = close.index[i].strftime("%Y-%m-%d")
                if d_str in show_set:
                    markers.append({
                        "time":     d_str,
                        "position": "belowBar" if sig == "AL" else "aboveBar",
                        "color":    "#3fb950"  if sig == "AL" else "#f85149",
                        "shape":    "arrowUp"  if sig == "AL" else "arrowDown",
                        "text":     sig,
                    })
                signal_history.append({
                    "date":   close.index[i].strftime("%d.%m.%Y"),
                    "signal": sig,
                    "price":  round(float(close.iloc[i]), 2),
                })
            prev_sig = sig
        signal_history = list(reversed(signal_history[-15:]))   # en yeni başta, max 15

        # Özet (son bar)
        c       = float(close.iloc[-1])
        prev_c  = float(close.iloc[-2])
        chg     = ((c - prev_c) / prev_c) * 100 if prev_c else 0
        adx_val = float(adx.iloc[-1])
        di_p    = float(di_plus_s.iloc[-1]); di_m = float(di_minus_s.iloc[-1])
        e12_val = float(ema12.iloc[-1])
        e99_val = float(ema99.iloc[-1])
        st_val  = int(supertrend.iloc[-1])
        _sl_raw = float(st_line_s.iloc[-1])
        sl_val  = round(_sl_raw, 2) if not np.isnan(_sl_raw) else None

        st_bull  = st_val == 1;   st_bear  = st_val == -1
        adx_bull = adx_val >= 25 and di_p > di_m
        adx_bear = adx_val >= 25 and di_m > di_p
        e12_bull = e12_val > e99_val; e12_bear = e12_val < e99_val
        bull_score = int(st_bull) + int(adx_bull) + int(e12_bull)
        bear_score = int(st_bear) + int(adx_bear) + int(e12_bear)
        signal     = "AL" if bull_score >= 3 else "SAT" if bear_score >= 3 else "BEKLE"

        # ── Volume histogram (gösterim barları) ──────────────────────────
        vol_data = []
        if volume is not None:
            avg_vol = float(volume.iloc[-60:].mean()) if len(volume) >= 60 else float(volume.mean())
            for ts in show_idx:
                try:
                    v = float(volume[ts]) if not pd.isna(volume[ts]) else 0
                    cl_ = float(close[ts]); op_ = float(open_[ts])
                    color = "#3fb950" if cl_ >= op_ else "#f85149"
                    # yüksek hacim biraz daha parlak
                    if avg_vol > 0 and v > avg_vol * 2:
                        color = "#3fb950cc" if cl_ >= op_ else "#f85149cc"
                    vol_data.append({"time": ts.strftime("%Y-%m-%d"), "value": v, "color": color})
                except Exception:
                    continue

        # ── 52 haftalık yüksek / düşük (yaklaşık 252 işlem günü) ─────────
        week52_bars = min(252, len(close))
        w52_close   = close.iloc[-week52_bars:]
        w52_high    = round(float(w52_close.max()), 2)
        w52_low     = round(float(w52_close.min()), 2)

        # ── Güncel sinyal süresi (son sinyal değişiminden beri) ───────────
        signal_bars = 1
        signal_date_str = signal_history[0]["date"] if signal_history else ""
        if signal_history:
            # son al/sat değişimi
            signal_bars = 1
            for idx2 in range(len(close) - 1, -1, -1):
                if bar_sig(idx2) != signal:
                    signal_bars = (len(close) - 1) - idx2
                    break

        # ── Otomatik teknik yorum metni ───────────────────────────────────
        commentary = _generate_commentary(
            ticker_base, signal, signal_bars, signal_date_str,
            adx_val, di_p, di_m, e12_val, e99_val, st_bull
        )

        return {
            "ohlc":           ohlc,
            "ema12":          series(ema12),
            "ema99":          series(ema99),
            "st_line":        st_line_data,
            "markers":        markers,
            "signal_history": signal_history,
            "volume":         vol_data,
            "week52":         {"high": w52_high, "low": w52_low},
            "commentary":     commentary,
            "summary": {
                "price":      round(c, 2),
                "change_pct": round(chg, 2),
                "signal":     signal,
                "bull_score": bull_score,
                "bear_score": bear_score,
                "sl_level":   sl_val,
                "adx":        round(adx_val, 1),
                "di_plus":    round(di_p, 1),
                "di_minus":   round(di_m, 1),
                "e12":        round(e12_val, 1),
                "e99":        round(e99_val, 1),
                "st_bull":    st_bull,  "st_bear":  st_bear,
                "adx_bull":   adx_bull, "adx_bear": adx_bear,
                "e12_bull":   e12_bull, "e12_bear": e12_bear,
            }
        }
    except Exception as e:
        logger.error("_compute_chart_data(%s): %s", ticker_base, e, exc_info=True)
        return None


def refresh_chart():
    d = get_chart_data()
    if d:
        with _lock:
            _chart_cache["data"] = d
            _chart_cache["updated_at"] = datetime.now().strftime("%d.%m.%Y %H:%M:%S")


@app.route("/api/chart")
def api_chart():
    with _lock:
        return safe_json({
            "chart":      _chart_cache["data"],
            "updated_at": _chart_cache["updated_at"],
            "loading":    _chart_cache["data"] is None,
        })


# ── Bireysel Hisse Sayfaları ──────────────────────────────────────────────────
def _get_sector(ticker):
    for sector, tickers in SECTORS.items():
        if ticker in tickers:
            return sector
    return "Diğer"

@app.route("/hisse/<ticker>")
def stock_page(ticker):
    ticker = ticker.upper()
    if ticker not in BIST100:
        return render_template("index.html"), 404
    name   = STOCK_NAMES.get(ticker, ticker)
    sector = _get_sector(ticker)
    others = [t for t in BIST100 if t != ticker and t != "XU030"]
    return render_template("hisse.html",
                           ticker=ticker,
                           name=name,
                           sector=sector,
                           others=others,
                           stock_names=STOCK_NAMES)


_fundamentals_cache = {}
_FUND_TTL = 3600 * 4  # 4 saat

def _get_fundamentals(ticker_base):
    """yfinance ile temel analiz verilerini döndürür."""
    now = time.time()
    with _lock:
        cached = _fundamentals_cache.get(ticker_base)
        if cached and (now - cached["ts"]) < _FUND_TTL:
            return cached["data"]
    try:
        yf_ticker = ticker_base + ".IS" if ticker_base != "XU030" else "XU030.IS"
        info = yf.Ticker(yf_ticker).info
        def safe(key, default=None):
            v = info.get(key)
            return v if v not in (None, "N/A", 0) else default

        def fmt_billion(v):
            if v is None: return None
            if v >= 1e12: return f"{v/1e12:.2f} T₺"
            if v >= 1e9:  return f"{v/1e9:.2f} Mrd₺"
            if v >= 1e6:  return f"{v/1e6:.1f} Mn₺"
            return f"{v:,.0f} ₺"

        data = {
            "pe_ratio":       round(safe("trailingPE", 0), 1) if safe("trailingPE") else None,
            "pb_ratio":       round(safe("priceToBook", 0), 2) if safe("priceToBook") else None,
            "eps":            safe("trailingEps"),
            "market_cap":     fmt_billion(safe("marketCap")),
            "revenue":        fmt_billion(safe("totalRevenue")),
            "dividend_yield": round(safe("dividendYield", 0) * 100, 2) if safe("dividendYield") else None,
            "roe":            round(safe("returnOnEquity", 0) * 100, 1) if safe("returnOnEquity") else None,
            "beta":           round(safe("beta", 0), 2) if safe("beta") else None,
            "shares":         fmt_billion(safe("sharesOutstanding")),
            "52w_high":       safe("fiftyTwoWeekHigh"),
            "52w_low":        safe("fiftyTwoWeekLow"),
            "avg_volume":     safe("averageVolume"),
            "short_name":     safe("shortName"),
        }
        with _lock:
            _fundamentals_cache[ticker_base] = {"data": data, "ts": now}
        return data
    except Exception as e:
        logger.warning("_get_fundamentals(%s): %s", ticker_base, e)
        return {}


@app.route("/api/hisse/<ticker>/fundamentals")
def api_stock_fundamentals(ticker):
    """Temel analiz verileri — 4 saatlik cache."""
    ticker = ticker.upper()
    if ticker not in BIST100:
        return safe_json({"error": "Hisse bulunamadı"}), 404
    data = _get_fundamentals(ticker)
    return safe_json({"fundamentals": data})


@app.route("/api/hisse/<ticker>/news")
def api_stock_news(ticker):
    """Gemini AI haber özeti — 6 saatlik cache."""
    ticker = ticker.upper()
    if ticker not in BIST100:
        return safe_json({"error": "Hisse bulunamadı"}), 404
    text = get_ai_news(ticker)
    if text:
        return safe_json({"news": text, "source": "gemini"})
    return safe_json({"news": None})


@app.route("/api/hisse/<ticker>/signal-explanation")
def api_signal_explanation(ticker):
    """Gemini AI sinyal açıklaması — 4 saatlik cache (sinyal değişince yenilenir)."""
    ticker = ticker.upper()
    if ticker not in BIST100:
        return safe_json({"error": "Hisse bulunamadı"}), 404
    if not GEMINI_API_KEY:
        return safe_json({"explanation": None, "reason": "no_api_key"})

    # Anlık sinyal datasını cache'den al
    with _lock:
        stocks = list(_cache["data"])
    stock = next((s for s in stocks if s["ticker"] == ticker), None)
    if not stock:
        return safe_json({"explanation": None, "reason": "no_data"})

    text = get_ai_signal_explanation(ticker, stock)
    if text:
        return safe_json({"explanation": text, "signal": stock.get("signal"), "source": "gemini"})
    return safe_json({"explanation": None})


_mtf_cache     = {}        # {ticker: {"data": {...}, "ts": float}}
_MTF_CACHE_TTL = 1800      # 30 dakika (MTF günlük/haftalık/aylık — sık değişmez)


def _compute_mtf(ticker):
    """Tek hisse için çoklu zaman dilimi sinyal hesaplar — cache tarafından çağrılır."""
    sym = ticker + ".IS"

    def _tf_signal(interval, period, min_bars):
        try:
            df = yf.download(sym, period=period, interval=interval,
                             progress=False, auto_adjust=True, timeout=25)
            if df is None or len(df) < min_bars:
                return None
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = df.columns.get_level_values(0)
                df = df.loc[:, ~df.columns.duplicated()]
            df    = df.dropna().sort_index()
            close = df["Close"].squeeze()
            high  = df["High"].squeeze()
            low   = df["Low"].squeeze()
            if len(close) < min_bars:
                return None

            ema12, ema99       = compute_ema(close, 12), compute_ema(close, 99)
            adx, dip, dim      = compute_adx(high, low, close)
            supertrend, st_ln  = compute_supertrend(high, low, close)

            c     = float(close.iloc[-1])
            e12   = float(ema12.iloc[-1]); e99   = float(ema99.iloc[-1])
            adxv  = float(adx.iloc[-1]);   dipv  = float(dip.iloc[-1]); dimv = float(dim.iloc[-1])
            stv   = int(supertrend.iloc[-1])

            bs    = int(stv == 1)  + int(adxv >= 25 and dipv > dimv) + int(e12 > e99)
            brs   = int(stv == -1) + int(adxv >= 25 and dimv > dipv) + int(e12 < e99)
            sig   = "AL" if bs >= 3 else "SAT" if brs >= 3 else "BEKLE"
            sl    = round(float(st_ln.iloc[-1]), 2)
            return {
                "signal": sig,
                "price":  round(c, 2),
                "adx":    round(adxv, 1),
                "sl":     sl,
                "bull_score": bs,
                "bear_score": brs,
            }
        except Exception as e:
            logger.debug("_tf_signal(%s, %s): %s", ticker, interval, e)
            return None

    return {
        "ticker":  ticker,
        "daily":   _tf_signal("1d",  "2y",  80),
        "weekly":  _tf_signal("1wk", "5y",  40),
        "monthly": _tf_signal("1mo", "10y", 12),
    }


@app.route("/api/hisse/<ticker>/mtf")
def api_stock_mtf(ticker):
    """Hisse için çoklu zaman dilimi sinyal analizi (Günlük / Haftalık / Aylık) — 30 dk cache."""
    ticker = ticker.upper()
    if ticker not in BIST30:
        return safe_json({"error": "Hisse bulunamadı"}), 404

    now = time.time()
    with _lock:
        cached = _mtf_cache.get(ticker)
        if cached and (now - cached["ts"]) < _MTF_CACHE_TTL:
            return safe_json(cached["data"])

    data = _compute_mtf(ticker)
    with _lock:
        _mtf_cache[ticker] = {"data": data, "ts": now}
    return safe_json(data)


@app.route("/api/hisse/<ticker>/chart")
def api_stock_chart(ticker):
    ticker = ticker.upper()
    if ticker not in BIST30:
        return safe_json({"error": "Hisse bulunamadı"}), 404

    now = time.time()
    with _lock:
        cached = _stock_chart_cache.get(ticker)
        if cached and (now - cached["ts"]) < _STOCK_CACHE_TTL:
            return safe_json({
                "chart":      cached["data"],
                "updated_at": cached["updated_at"],
                "loading":    False,
            })

    # Cache yok veya bayat → taze hesapla
    data = _compute_chart_data(ticker, period="2y")
    if data:
        upd = datetime.now().strftime("%d.%m.%Y %H:%M:%S")
        with _lock:
            _stock_chart_cache[ticker] = {"data": data, "ts": now, "updated_at": upd}
        return safe_json({"chart": data, "updated_at": upd, "loading": False})

    return safe_json({"chart": None, "loading": True})


# ── SEO: sitemap, robots, favicon ────────────────────────────────────────────
@app.route("/sitemap.xml")
def sitemap():
    pages = [
        {"loc": "/",            "priority": "1.0", "changefreq": "hourly"},
        {"loc": "/ozet",        "priority": "0.9", "changefreq": "daily"},
        {"loc": "/metodoloji",  "priority": "0.7", "changefreq": "monthly"},
        {"loc": "/hakkinda",    "priority": "0.6", "changefreq": "monthly"},
        {"loc": "/gizlilik",    "priority": "0.3", "changefreq": "yearly"},
        {"loc": "/iletisim",    "priority": "0.4", "changefreq": "yearly"},
    ]
    for t in BIST30:
        if t != "XU030":
            pages.append({"loc": f"/hisse/{t}", "priority": "0.85", "changefreq": "daily"})
    pages.append({"loc": "/blog",               "priority": "0.8", "changefreq": "weekly"})
    pages.append({"loc": "/portfolio",          "priority": "0.6", "changefreq": "monthly"})
    pages.append({"loc": "/sinyal-performans",  "priority": "0.7", "changefreq": "weekly"})
    pages.append({"loc": "/sektor-harita",      "priority": "0.7", "changefreq": "daily"})
    pages.append({"loc": "/bilanco-takvimi",    "priority": "0.8", "changefreq": "weekly"})
    for a in ARTICLES:
        pages.append({"loc": f"/blog/{a['slug']}", "priority": "0.7", "changefreq": "monthly"})
    today = date.today().isoformat()
    xml   = ['<?xml version="1.0" encoding="UTF-8"?>',
             '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
    base  = "https://borsapusula.com"   # Domain eklenince burası güncellenir
    for p in pages:
        xml.append(f"  <url><loc>{base}{p['loc']}</loc>"
                   f"<lastmod>{today}</lastmod>"
                   f"<changefreq>{p['changefreq']}</changefreq>"
                   f"<priority>{p['priority']}</priority></url>")
    xml.append("</urlset>")
    return Response("\n".join(xml), mimetype="application/xml")


@app.route("/robots.txt")
def robots():
    body = (
        "User-agent: *\n"
        "Allow: /\n"
        "Disallow: /api/\n"
        "\n"
        "Sitemap: https://borsapusula.com/sitemap.xml\n"
    )
    return Response(body, mimetype="text/plain")


@app.route("/sw.js")
def service_worker():
    """Service worker kök scope'tan sunulmalı."""
    import os
    fpath = os.path.join(app.root_path, "static", "sw.js")
    with open(fpath, "rb") as f:
        return Response(f.read(), mimetype="application/javascript",
                        headers={"Service-Worker-Allowed": "/"})


@app.route("/favicon.ico")
def favicon():
    import os
    fpath = os.path.join(app.root_path, "static", "favicon.svg")
    if os.path.exists(fpath):
        with open(fpath, "rb") as f:
            return Response(f.read(), mimetype="image/svg+xml")
    return "", 404


@app.route("/og-image.svg")
def og_image():
    """Dinamik OG image — 1200×630 SVG (sosyal medya önizlemesi)."""
    with _lock:
        stocks = list(_cache["data"])
    al_count  = sum(1 for s in stocks if s["signal"] == "AL" and s["ticker"] != "XU030")
    sat_count = sum(1 for s in stocks if s["signal"] == "SAT" and s["ticker"] != "XU030")
    total     = sum(1 for s in stocks if s["ticker"] != "XU030")
    today_s   = date.today().strftime("%d.%m.%Y")

    svg = f'''<svg width="1200" height="630" viewBox="0 0 1200 630"
     xmlns="http://www.w3.org/2000/svg" font-family="Arial,sans-serif">
  <rect width="1200" height="630" fill="#0d1117"/>
  <rect x="0" y="0" width="6" height="630" fill="#58a6ff"/>
  <!-- Logo / başlık -->
  <text x="60" y="120" font-size="64" font-weight="700" fill="#f0f6fc">BIST</text>
  <text x="194" y="120" font-size="64" font-weight="700" fill="#58a6ff">100</text>
  <text x="310" y="120" font-size="64" font-weight="700" fill="#f0f6fc"> Sinyal Paneli</text>
  <text x="60" y="165" font-size="26" fill="#8b949e">borsapusula.com · Algoritmik AL/SAT Sinyalleri · {today_s}</text>
  <!-- Ayırıcı çizgi -->
  <line x1="60" y1="195" x2="1140" y2="195" stroke="#30363d" stroke-width="1"/>
  <!-- İstatistik kutular -->
  <rect x="60"  y="230" width="280" height="160" rx="12" fill="#161b22" stroke="#30363d" stroke-width="1"/>
  <text x="200" y="305" font-size="72" font-weight="800" fill="#3fb950" text-anchor="middle">{al_count}</text>
  <text x="200" y="355" font-size="22" fill="#8b949e" text-anchor="middle">▲ AL SİNYALİ</text>
  <rect x="380" y="230" width="280" height="160" rx="12" fill="#161b22" stroke="#30363d" stroke-width="1"/>
  <text x="520" y="305" font-size="72" font-weight="800" fill="#f85149" text-anchor="middle">{sat_count}</text>
  <text x="520" y="355" font-size="22" fill="#8b949e" text-anchor="middle">▼ SAT SİNYALİ</text>
  <rect x="700" y="230" width="280" height="160" rx="12" fill="#161b22" stroke="#30363d" stroke-width="1"/>
  <text x="840" y="305" font-size="72" font-weight="800" fill="#58a6ff" text-anchor="middle">{total}</text>
  <text x="840" y="355" font-size="22" fill="#8b949e" text-anchor="middle">BIST100 HİSSE</text>
  <!-- Alt slogan -->
  <text x="60" y="480" font-size="30" fill="#c9d1d9">Supertrend · ADX · EMA12/99</text>
  <text x="60" y="525" font-size="22" fill="#484f58">Algoritmik, ücretsiz, canlı güncelleme · Yatırım tavsiyesi değildir.</text>
  <!-- Sağ ikon -->
  <rect x="1020" y="230" width="120" height="160" rx="12" fill="#1c2b3a" stroke="#1f6feb44" stroke-width="1"/>
  <text x="1080" y="335" font-size="56" text-anchor="middle">📊</text>
</svg>'''
    return Response(svg, mimetype="image/svg+xml",
                    headers={"Cache-Control": "public, max-age=3600"})


# ── Günlük Özet Sayfası ───────────────────────────────────────────────────────
@app.route("/ozet")
def ozet_page():
    with _lock:
        stocks = list(_cache["data"])
        updated_at = _cache.get("updated_at", "")
        loading = len(stocks) == 0

    al_list    = [s for s in stocks if s["signal"] == "AL"]
    sat_list   = [s for s in stocks if s["signal"] == "SAT"]
    bekle_list = [s for s in stocks if s["signal"] == "BEKLE"]
    new_signals = [s for s in stocks if s.get("is_new_signal")]

    today_str = date.today().strftime("%d.%m.%Y")
    return render_template("ozet.html",
        stocks=stocks, loading=loading, updated_at=updated_at,
        al_list=al_list, sat_list=sat_list, bekle_list=bekle_list,
        new_signals=new_signals, today_str=today_str,
        stock_names=STOCK_NAMES)


# ── Eğitim Sayfaları ──────────────────────────────────────────────────────────
@app.route("/metodoloji")
def metodoloji():
    return render_template("metodoloji.html")


@app.route("/hakkinda")
def hakkinda():
    return render_template("hakkinda.html")


@app.route("/gizlilik")
def gizlilik():
    return render_template("gizlilik.html")


@app.route("/iletisim")
def iletisim():
    return render_template("iletisim.html")


# ── Blog ──────────────────────────────────────────────────────────────────────
@app.route("/portfolio")
def portfolio():
    return render_template("portfolio.html")


# ── Backtest / Sinyal Performansı ─────────────────────────────────────────────
def _bar_signal_fast(ema12, ema99, adx, di_plus, di_minus, supertrend, i):
    """i. bar için sinyal hesapla."""
    ei12  = float(ema12.iloc[i]);   ei99  = float(ema99.iloc[i])
    ai    = float(adx.iloc[i])
    dip   = float(di_plus.iloc[i]); dim   = float(di_minus.iloc[i])
    sti   = int(supertrend.iloc[i])
    bs    = int(sti == 1)  + int(ai >= 25 and dip > dim) + int(ei12 > ei99)
    brs   = int(sti == -1) + int(ai >= 25 and dim > dip) + int(ei12 < ei99)
    return "AL" if bs >= 3 else "SAT" if brs >= 3 else "BEKLE"


def backtest_ticker(ticker_base, fwd_days=20):
    """Bir hisse için son 2 yıl AL/SAT sinyal performansını hesapla."""
    ticker = ticker_base + ".IS" if ticker_base != "XU030" else "XU030.IS"
    try:
        df = yf.download(ticker, period="2y", interval="1d",
                         progress=False, auto_adjust=True, timeout=30)
        if df is None or len(df) < 120:
            return None
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
            df = df.loc[:, ~df.columns.duplicated()]
        df    = df.dropna().sort_index()
        close = df["Close"].squeeze()
        high  = df["High"].squeeze()
        low   = df["Low"].squeeze()
        n     = len(close)
        if n < 120:
            return None

        ema12                  = compute_ema(close, 12)
        ema99                  = compute_ema(close, 99)
        adx, di_plus, di_minus = compute_adx(high, low, close)
        supertrend, _          = compute_supertrend(high, low, close)

        # Her bar için sinyal
        signals = [_bar_signal_fast(ema12, ema99, adx, di_plus, di_minus, supertrend, i)
                   for i in range(n)]

        episodes = []   # {"sig", "entry_i", "entry_price", "exit_i", "exit_price", "ret_pct"}
        i = 0
        while i < n:
            sig = signals[i]
            if sig in ("AL", "SAT"):
                entry_i     = i
                entry_price = float(close.iloc[i])
                # Sinyal bitmesini bekle (max fwd_days bar)
                j = i + 1
                while j < n and j < i + fwd_days + 1 and signals[j] == sig:
                    j += 1
                exit_i     = min(j, n - 1)
                exit_price = float(close.iloc[exit_i])
                ret_pct    = (exit_price - entry_price) / entry_price * 100
                episodes.append({
                    "sig":         sig,
                    "date":        close.index[entry_i].strftime("%d.%m.%Y"),
                    "entry_price": round(entry_price, 2),
                    "exit_price":  round(exit_price, 2),
                    "bars":        exit_i - entry_i,
                    "ret_pct":     round(ret_pct, 2),
                    "win":         (ret_pct > 0 and sig == "AL") or (ret_pct < 0 and sig == "SAT"),
                })
                i = j
            else:
                i += 1
        return {"ticker": ticker_base, "episodes": episodes}
    except Exception as e:
        logger.warning("backtest_ticker(%s): %s", ticker_base, e)
        return None


def run_backtest():
    """BIST30 hisseleri için backtest yürüt ve cache'e kaydet."""
    # Sadece BIST30 (ilk 28 hisse) – 130 hisse çok yavaş olur
    bt_tickers = BIST100[:28]
    all_episodes = {"AL": [], "SAT": []}
    per_ticker   = []

    for t in bt_tickers:
        res = backtest_ticker(t)
        time.sleep(0.3)
        if not res:
            continue
        t_al = [e for e in res["episodes"] if e["sig"] == "AL"]
        t_sa = [e for e in res["episodes"] if e["sig"] == "SAT"]
        all_episodes["AL"] += t_al
        all_episodes["SAT"] += t_sa
        if t_al or t_sa:
            per_ticker.append({
                "ticker":   t,
                "al_count": len(t_al),
                "al_wins":  sum(1 for e in t_al if e["win"]),
                "al_avg":   round(sum(e["ret_pct"] for e in t_al) / len(t_al), 2) if t_al else None,
                "sat_count":len(t_sa),
                "sat_wins": sum(1 for e in t_sa if e["win"]),
                "sat_avg":  round(sum(e["ret_pct"] for e in t_sa) / len(t_sa), 2) if t_sa else None,
            })

    def stats(eps):
        if not eps: return {"count": 0, "win_rate": 0, "avg_ret": 0, "best": 0, "worst": 0}
        wins = [e for e in eps if e["win"]]
        rets = [e["ret_pct"] for e in eps]
        return {
            "count":    len(eps),
            "win_rate": round(len(wins) / len(eps) * 100, 1),
            "avg_ret":  round(sum(rets) / len(rets), 2),
            "best":     round(max(rets), 2),
            "worst":    round(min(rets), 2),
        }

    result = {
        "al":          stats(all_episodes["AL"]),
        "sat":         stats(all_episodes["SAT"]),
        "per_ticker":  sorted(per_ticker, key=lambda x: -(x["al_count"] + x["sat_count"])),
        "computed_at": datetime.now().strftime("%d.%m.%Y %H:%M"),
        "tickers_used": len(bt_tickers),
    }
    with _lock:
        _bt_cache["data"]        = result
        _bt_cache["computed_at"] = result["computed_at"]
    logger.info("Backtest tamamlandı: %d AL, %d SAT episod",
                result["al"]["count"], result["sat"]["count"])


@app.route("/sinyal-performans")
def sinyal_performans():
    with _lock:
        bt = _bt_cache.get("data")
    # Aktif sinyallerden anlık performans tablosu
    with _lock:
        stocks = list(_cache["data"])
    aktif = [s for s in stocks if s["signal"] in ("AL", "SAT") and s.get("signal_price")]
    for s in aktif:
        if s.get("signal_price") and s.get("price"):
            s["aktif_ret"] = round((s["price"] - s["signal_price"]) / s["signal_price"] * 100, 2)
        else:
            s["aktif_ret"] = None
    return render_template("sinyal_performans.html", bt=bt, aktif=aktif)


@app.route("/api/backtest")
def api_backtest():
    with _lock:
        bt = _bt_cache.get("data")
    if not bt:
        return safe_json({"status": "computing", "message": "Backtest hesaplanıyor..."})
    return safe_json(bt)


@app.route("/api/backtest/run", methods=["POST"])
def api_backtest_run():
    threading.Thread(target=run_backtest, daemon=True).start()
    return jsonify({"status": "started"})


@app.route("/sektor-harita")
def sektor_harita():
    return render_template("sektor_harita.html")


# ── Bilanço Takvimi ───────────────────────────────────────────────────────────
_earnings_cache   = {"data": None, "ts": 0}
_EARNINGS_TTL     = 3600 * 12   # 12 saat

# BIST'te finansal sonuçlar genellikle şu dönemlerde açıklanır:
# Q4 (Ekim-Aralık bilanços): Mart-Nisan
# Q1 (Ocak-Mart bilanços):   Mayıs ortası
# Q2/H1 (Nisan-Haziran):     Ağustos-Eylül
# Q3 (Temmuz-Eylül):         Ekim-Kasım
_BILANCO_PERIODS = [
    # (quarter_label, est_start_mm_dd, est_end_mm_dd, description)
    ("Q4 2025 (Yıllık)", "2026-03-01", "2026-04-30", "2025 yıl sonu bilanço açıklamaları"),
    ("Q1 2026",          "2026-05-15", "2026-06-15", "2026 1. çeyrek sonuçları"),
    ("Q2 2026 (H1)",     "2026-08-01", "2026-09-15", "2026 ilk yarıyıl sonuçları"),
    ("Q3 2026",          "2026-10-15", "2026-11-30", "2026 3. çeyrek sonuçları"),
    ("Q4 2026 (Yıllık)", "2027-03-01", "2027-04-30", "2026 yıl sonu bilanço açıklamaları"),
]

def get_earnings_data():
    """Yaklaşan finansal sonuç dönemlerini sinyallerle birleştirerek döner."""
    now = time.time()
    with _lock:
        if _earnings_cache["data"] and (now - _earnings_cache["ts"]) < _EARNINGS_TTL:
            return _earnings_cache["data"]

    # Mevcut sinyal datasını al
    with _lock:
        stocks = list(_cache["data"])
    sig_map = {s["ticker"]: s for s in stocks}

    # Her hisse için yfinance calendar dene (bazı hisseler için gerçek tarih döner)
    yf_dates = {}   # ticker → date_str
    sample_tickers = BIST100[:28]   # Sadece BIST30 için hız kazanımı
    for t in sample_tickers:
        try:
            cal = yf.Ticker(t + ".IS").calendar
            if cal is not None and isinstance(cal, dict):
                # yfinance v0.2+: cal.get('Earnings Date') list olabilir
                ed = cal.get("Earnings Date")
                if ed is not None:
                    if hasattr(ed, "iloc"):
                        ed = ed.iloc[0] if len(ed) > 0 else None
                    if ed is not None:
                        yf_dates[t] = str(ed)[:10]
        except Exception:
            pass
        time.sleep(0.1)

    # Dönemleri bugüne göre filtrele (geçmiş dönemler hariç)
    today_str = date.today().isoformat()
    result_periods = []
    for qlabel, start, end, desc in _BILANCO_PERIODS:
        if end < today_str:   # Tamamen geçmiş dönem
            continue
        # Bu döneme giren hisseleri al (yfinance tarih varsa + yaklaşık olarak hepsini)
        stocks_in_period = []
        for t in BIST100:
            if t == "XU030":
                continue
            sig_data = sig_map.get(t, {})
            yf_date  = yf_dates.get(t)
            # yfinance tarihi bu döneme giriyorsa → kesin; girmiyor/yoksa → yaklaşık
            in_period = False
            date_label = "yaklaşık"
            if yf_date and start <= yf_date <= end:
                in_period  = True
                date_label = yf_date
            elif not yf_date:
                # Yaklaşık — dönem içinde göster
                in_period  = True
                date_label = "yaklaşık"

            if in_period:
                stocks_in_period.append({
                    "ticker":   t,
                    "name":     STOCK_NAMES.get(t, t),
                    "signal":   sig_data.get("signal", "BEKLE"),
                    "price":    sig_data.get("price"),
                    "date":     date_label,
                    "kap_url":  f"https://www.kap.org.tr/tr/Bildirim/Ara?ara={t}&tip=MAL&kategori=2",
                })
        # Sinyal önceliği: AL → SAT → BEKLE, içinde alfabetik
        stocks_in_period.sort(key=lambda x: (
            0 if x["signal"] == "AL" else 1 if x["signal"] == "SAT" else 2,
            x["ticker"]
        ))
        result_periods.append({
            "label":       qlabel,
            "start":       start,
            "end":         end,
            "description": desc,
            "stocks":      stocks_in_period,
            "is_current":  start <= today_str <= end,
        })

    data = {
        "periods":    result_periods,
        "updated_at": datetime.now().strftime("%d.%m.%Y %H:%M"),
    }
    with _lock:
        _earnings_cache["data"] = data
        _earnings_cache["ts"]   = now
    return data


@app.route("/bilanco-takvimi")
def bilanco_takvimi():
    return render_template("bilanco_takvimi.html")


@app.route("/api/bilanco-takvimi")
def api_bilanco_takvimi():
    data = get_earnings_data()
    return safe_json(data)


@app.route("/api/telegram/test", methods=["POST"])
def api_telegram_test():
    """Admin: Telegram bağlantısını test et."""
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHANNEL_ID:
        return safe_json({"ok": False, "error": "Telegram env vars eksik (TELEGRAM_BOT_TOKEN, TELEGRAM_CHANNEL_ID)"})
    _send_telegram(
        "🔔 <b>BorsaPusula Test Mesajı</b>\n"
        "Telegram entegrasyonu başarıyla yapılandırıldı!\n"
        f"<i>Sunucu: {datetime.now().strftime('%d.%m.%Y %H:%M:%S')}</i>"
    )
    return safe_json({"ok": True, "channel": TELEGRAM_CHANNEL_ID})


@app.route("/blog")
def blog_index():
    from collections import Counter
    counts = Counter(a["cat"] for a in ARTICLES)
    cat_counts = sorted(counts.items())
    return render_template("blog.html", articles=ARTICLES, cat_counts=cat_counts)


@app.route("/blog/<slug>")
def blog_article(slug):
    from flask import abort
    article = ARTICLES_BY_SLUG.get(slug)
    if not article:
        abort(404)
    # İlgili makaleler: aynı kategori, max 3
    related = [a for a in ARTICLES if a["cat"] == article["cat"] and a["slug"] != slug][:3]
    if len(related) < 3:
        extras = [a for a in ARTICLES if a["cat"] != article["cat"] and a["slug"] != slug]
        related += extras[:3 - len(related)]
    return render_template("blog_article.html", article=article, related=related)


# ── Startup ───────────────────────────────────────────────────────────────────
def _startup():
    refresh_chart()
    time.sleep(3)
    threading.Thread(target=background_refresh,     daemon=True).start()
    threading.Thread(target=background_live_prices, daemon=True).start()
    # Backtest'i arka planda başlat (30 dakika gecikme ile — önce ana veri yüklensin)
    def _delayed_backtest():
        time.sleep(1800)   # 30 dakika sonra
        run_backtest()
    threading.Thread(target=_delayed_backtest, daemon=True).start()

threading.Thread(target=_startup, daemon=True).start()

logger.info("=" * 50)
logger.info("  BIST30 Sinyal Paneli başlatıldı")
logger.info("  http://localhost:8003")
logger.info("=" * 50)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8003, debug=False)
