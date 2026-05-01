from flask import Flask, jsonify, render_template, Response, request, abort
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
import re
import copy
import secrets
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text      import MIMEText
import requests
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from blog_content import ARTICLES, ARTICLES_BY_SLUG, CATEGORIES

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", secrets.token_hex(32))

# ── Rate Limiter ──────────────────────────────────────────────────────────────
limiter = Limiter(
    app=app,
    key_func=get_remote_address,
    default_limits=["300 per minute"],
    storage_uri="memory://",
)

# ── Admin endpoint koruması ───────────────────────────────────────────────────
ADMIN_SECRET = os.environ.get("ADMIN_SECRET", "")

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


def compute_rsi(close, period=14):
    """RSI (Relative Strength Index) — EWM yöntemi."""
    delta    = close.diff()
    gain     = delta.clip(lower=0)
    loss     = -delta.clip(upper=0)
    avg_gain = gain.ewm(com=period - 1, min_periods=period).mean()
    avg_loss = loss.ewm(com=period - 1, min_periods=period).mean()
    rs  = avg_gain / avg_loss.replace(0, np.nan)
    rsi = 100 - (100 / (1 + rs))
    return rsi.fillna(50)


def compute_atr(high, low, close, period=14):
    """ATR(14) — Wilder smoothing. Bağımsız helper; giriş optimizasyonu için kullanılır."""
    hi = high.values; lo = low.values; cl = close.values
    n  = len(cl)
    tr      = np.empty(n)
    tr[0]   = hi[0] - lo[0]
    tr[1:]  = np.maximum(hi[1:] - lo[1:],
              np.maximum(np.abs(hi[1:] - cl[:-1]),
                         np.abs(lo[1:] - cl[:-1])))
    atr = np.full(n, np.nan)
    if n >= period:
        atr[period - 1] = np.mean(tr[:period])
        for i in range(period, n):
            atr[i] = (atr[i - 1] * (period - 1) + tr[i]) / period
    return pd.Series(atr, index=close.index)


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

        volume = df["Volume"].squeeze() if "Volume" in df.columns else pd.Series([0]*len(close), index=close.index)

        ema12                  = compute_ema(close, 12)
        ema99                  = compute_ema(close, 99)
        adx, di_plus, di_minus = compute_adx(high, low, close)
        supertrend, st_line    = compute_supertrend(high, low, close)
        rsi_series             = compute_rsi(close, 14)

        rsi_val   = round(float(rsi_series.iloc[-1]), 1)
        _vol_avg  = float(volume.rolling(20).mean().iloc[-1])
        vol_ratio = round(float(volume.iloc[-1]) / _vol_avg, 2) if _vol_avg > 0 else 1.0

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

        # is_new_signal: yalnızca AL/SAT sinyalleri için geçerli.
        # BEKLE sinyali bugün başladıysa (eski sinyal sona erdi) "Bugün" gösterme —
        # kullanıcıya "Belirsiz + Bugün" kombinasyonu çelişkili ve yanıltıcı görünüyor.
        is_new_signal = (signal_date == today_str and signal != "BEKLE")
        confirmed     = signal != "BEKLE" and signal_bars >= 3

        # ── ATR(14) — giriş optimizasyonu için ────────────────────────────────
        atr14_series = compute_atr(high, low, close, 14)
        atr_now      = float(atr14_series.iloc[-1])
        atr_now      = atr_now if not np.isnan(atr_now) else 0.0

        # ── Volume Teyidi — SİNYAL ÇIKAN BARDAKI hacim / önceki 20 bar ort ───
        # (Bugünkü hacim değil — sinyal breakout'undaki hacim kalitesi ölçülüyor)
        vol_confirmed    = None
        signal_vol_ratio = None
        if signal != "BEKLE" and signal_start < len(volume):
            svol      = float(volume.iloc[signal_start])
            _slice    = volume.iloc[max(0, signal_start - 20):signal_start]
            svol_avg  = float(_slice.mean()) if len(_slice) > 0 else svol
            signal_vol_ratio = round(svol / svol_avg, 2) if svol_avg > 0 else 1.0
            vol_confirmed    = signal_vol_ratio >= 1.5

        # ── Giriş Optimizasyonu (Entry Quality) ───────────────────────────────
        # Ölçüt: Fiyat sinyal gününden bu yana kaç ATR hareket etti?
        # < 1 ATR → IDEAL  |  1-2 ATR → IYI  |  2-3.5 ATR → DIKKATLI  |  >3.5 → UZAK
        entry_quality = None
        entry_note    = None
        optimal_entry = None
        tp1 = tp2     = None
        rr_ratio      = None

        if signal == "AL" and signal_price and sl_val and c > sl_val and atr_now > 0:
            risk         = c - sl_val                            # mevcut fiyattan SL'ye mesafe
            sl_dist_pct  = round(risk / c * 100, 1)             # SL uzaklığı %
            pct_moved    = (c - signal_price) / signal_price * 100  # sinyalden bu yana %
            atr_pct      = atr_now / c * 100                    # ATR = fiyatın kaç %'i
            atrs_moved   = round(pct_moved / atr_pct, 1) if atr_pct > 0 else 0.0

            tp1      = round(c + risk * 2, 2)    # 2R hedef
            tp2      = round(c + risk * 3, 2)    # 3R hedef
            rr_ratio = 2.0                        # standart 2R TP hedefleniyor

            if atrs_moved < 1.0:
                entry_quality = "IDEAL"
                entry_note    = (f"Sinyal taze ({signal_bars} bar), "
                                 f"fiyat SL'ye yakın — R/R en avantajlı bölge")
            elif atrs_moved < 2.0:
                entry_quality = "IYI"
                entry_note    = (f"Trend onaylandı ({signal_bars} bar, "
                                 f"+{pct_moved:.1f}%), makul giriş bölgesi")
            elif atrs_moved < 3.5:
                entry_quality = "DIKKATLI"
                entry_note    = (f"Fiyat +{pct_moved:.1f}% yükseldi "
                                 f"({atrs_moved:.1f} ATR) — küçük pullback beklenmesi daha sağlıklı")
                # Optimal giriş: SL + 0.8 ATR veya mevcut -3%, hangisi yüksekse
                optimal_entry = round(max(sl_val + atr_now * 0.8, c * 0.97), 2)
            else:
                entry_quality = "UZAK"
                entry_note    = (f"Fiyat +{pct_moved:.1f}% yükseldi "
                                 f"({atrs_moved:.1f} ATR) — kovalama riski yüksek, pullback bekle")
                optimal_entry = round(max(sl_val + atr_now * 0.8, c * 0.95), 2)

        elif signal == "SAT" and signal_price and sl_val and c < sl_val and atr_now > 0:
            risk        = sl_val - c
            sl_dist_pct = round(risk / c * 100, 1)
            pct_moved   = (signal_price - c) / signal_price * 100
            atr_pct     = atr_now / c * 100
            atrs_moved  = round(pct_moved / atr_pct, 1) if atr_pct > 0 else 0.0

            tp1      = round(c - risk * 2, 2)
            tp2      = round(c - risk * 3, 2)
            rr_ratio = 2.0

            if atrs_moved < 1.0:
                entry_quality = "IDEAL"
                entry_note    = (f"Zayıf trend taze ({signal_bars} bar), "
                                 f"SL yakın — kısa pozisyon için avantajlı bölge")
            elif atrs_moved < 2.0:
                entry_quality = "IYI"
                entry_note    = (f"Düşüş trendi onaylandı "
                                 f"({signal_bars} bar, -{pct_moved:.1f}%)")
            elif atrs_moved < 3.5:
                entry_quality = "DIKKATLI"
                entry_note    = (f"Fiyat -{pct_moved:.1f}% düştü "
                                 f"({atrs_moved:.1f} ATR) — kısa dönem teknik geri tepme riski")
                optimal_entry = round(min(sl_val - atr_now * 0.8, c * 1.03), 2)
            else:
                entry_quality = "UZAK"
                entry_note    = (f"Fiyat -{pct_moved:.1f}% düştü "
                                 f"({atrs_moved:.1f} ATR) — aşırı satım bölgesi, riski yüksek")
                optimal_entry = round(min(sl_val - atr_now * 0.8, c * 1.05), 2)

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
            "rsi":             rsi_val,
            "vol_ratio":       vol_ratio,
            "vol_confirmed":   vol_confirmed,
            "signal_vol_ratio": signal_vol_ratio,
            "atr14":           round(atr_now, 2) if atr_now else None,
            "entry_quality":   entry_quality,
            "entry_note":      entry_note,
            "optimal_entry":   optimal_entry,
            "tp1":             tp1,
            "tp2":             tp2,
            "rr_ratio":        rr_ratio,
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

    if changes:
        _notify_email_signal_changes(changes)

    _prev_signals = new_sig_map


# ── E-posta Bildirim Sistemi ──────────────────────────────────────────────────
SMTP_HOST = os.environ.get("SMTP_HOST", "")
SMTP_PORT = int(os.environ.get("SMTP_PORT", "587"))
SMTP_USER = os.environ.get("SMTP_USER", "")
SMTP_PASS = os.environ.get("SMTP_PASS", "")
SMTP_FROM = os.environ.get("SMTP_FROM", "BorsaPusula <noreply@borsapusula.com>")

SUBSCRIBERS_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "subscribers.json")
_sub_lock = threading.Lock()


def _load_subscribers():
    if not os.path.exists(SUBSCRIBERS_FILE):
        return {}
    try:
        with open(SUBSCRIBERS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def _save_subscribers(subs):
    try:
        with open(SUBSCRIBERS_FILE, "w", encoding="utf-8") as f:
            json.dump(subs, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.error("subscribers.json kaydetme hatası: %s", e)


def send_email(to_email, subject, html_body):
    """SMTP üzerinden HTML e-posta gönderir. Config eksikse sessizce atlar."""
    if not SMTP_HOST or not SMTP_USER or not SMTP_PASS:
        return False
    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"]    = SMTP_FROM
        msg["To"]      = to_email
        msg.attach(MIMEText(html_body, "html", "utf-8"))
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=15) as srv:
            srv.ehlo()
            srv.starttls()
            srv.login(SMTP_USER, SMTP_PASS)
            srv.sendmail(SMTP_USER, [to_email], msg.as_string())
        return True
    except Exception as e:
        logger.error("E-posta gönderilemedi (%s): %s", to_email, e)
        return False


def _email_base(content_html, unsubscribe_url):
    """Ortak e-posta şablonu."""
    return f"""<!DOCTYPE html>
<html lang="tr">
<head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>BorsaPusula</title></head>
<body style="margin:0;padding:0;background:#0b111f;font-family:-apple-system,BlinkMacSystemFont,'Inter',Arial,sans-serif;color:#e2e8f0">
<div style="max-width:600px;margin:0 auto;padding:32px 16px">
  <div style="text-align:center;margin-bottom:28px">
    <a href="https://borsapusula.com" style="text-decoration:none">
      <span style="font-size:22px;font-weight:800;color:#e2e8f0">Borsa<span style="color:#3b82f6">Pusula</span></span>
    </a>
  </div>
  {content_html}
  <div style="border-top:1px solid #1e2d45;padding-top:14px;text-align:center;margin-top:28px">
    <div style="font-size:11px;color:#374151;margin-bottom:6px">
      ⚠️ Bu bildirim yatırım tavsiyesi değildir. Algoritmik sinyal bilgilendirmesidir.
    </div>
    <a href="{unsubscribe_url}" style="font-size:11px;color:#4b5563;text-decoration:underline">
      Abonelikten çık
    </a>
  </div>
</div>
</body></html>"""


def _build_welcome_email(email, unsubscribe_url):
    content = f"""
    <div style="background:#111827;border:1px solid #1e2d45;border-radius:12px;padding:24px;margin-bottom:20px;text-align:center">
      <div style="font-size:36px;margin-bottom:12px">✅</div>
      <div style="font-size:18px;font-weight:700;margin-bottom:8px">Abonelik Onaylandı!</div>
      <div style="font-size:13px;color:#94a3b8;line-height:1.6">
        <strong style="color:#e2e8f0">{email}</strong> adresi için BIST sinyal bildirimleri aktif edildi.<br>
        BIST100 hisselerinde Güçlü Trend veya Zayıf Trend sinyali oluştuğunda e-posta alacaksınız.
      </div>
    </div>
    <div style="text-align:center">
      <a href="https://borsapusula.com" style="display:inline-block;background:#1f6feb;color:#fff;padding:10px 28px;border-radius:8px;text-decoration:none;font-size:13px;font-weight:600">
        Sinyalleri İncele →
      </a>
    </div>"""
    return _email_base(content, unsubscribe_url)


def _build_signal_email(changes, unsubscribe_url):
    """Sinyal değişim e-postası HTML içeriği."""
    sig_color = {"AL": "#3fb950", "SAT": "#f85149", "BEKLE": "#8b949e"}
    sig_bg    = {"AL": "#1a4731", "SAT": "#3d0f0f", "BEKLE": "#21262d"}
    sig_lbl   = {"AL": "Güçlü Trend ▲", "SAT": "Zayıf Trend ▼", "BEKLE": "Belirsiz"}

    rows = ""
    for t, old, new, stock in changes[:8]:
        name  = STOCK_NAMES.get(t, t)
        price = stock.get("price") or 0
        col   = sig_color.get(new, "#8b949e")
        bg    = sig_bg.get(new, "#21262d")
        lbl   = sig_lbl.get(new, new)
        rows += f"""
        <tr>
          <td style="padding:10px 16px;border-bottom:1px solid #1e2d45">
            <a href="https://borsapusula.com/hisse/{t}" style="color:#e2e8f0;text-decoration:none;font-weight:700">{t}</a>
            <div style="font-size:11px;color:#64748b;margin-top:2px">{name}</div>
          </td>
          <td style="padding:10px 16px;border-bottom:1px solid #1e2d45;font-size:13px;color:#94a3b8">{price:.2f} ₺</td>
          <td style="padding:10px 16px;border-bottom:1px solid #1e2d45">
            <span style="background:{bg};color:{col};border-radius:6px;padding:4px 10px;font-size:12px;font-weight:700">{lbl}</span>
          </td>
          <td style="padding:10px 16px;border-bottom:1px solid #1e2d45">
            <a href="https://borsapusula.com/hisse/{t}" style="color:#3b82f6;font-size:12px">Detay →</a>
          </td>
        </tr>"""

    content = f"""
    <div style="background:#111827;border:1px solid #1e2d45;border-radius:12px;overflow:hidden;margin-bottom:20px">
      <div style="background:#1a2438;padding:10px 16px;font-size:11px;font-weight:700;color:#64748b;text-transform:uppercase;letter-spacing:.5px">
        📊 Sinyal Değişimleri — {datetime.now().strftime('%d.%m.%Y %H:%M')}
      </div>
      <table style="width:100%;border-collapse:collapse">
        <thead><tr style="background:#0d1117">
          <th style="padding:8px 16px;text-align:left;font-size:10px;color:#64748b;font-weight:600;letter-spacing:.5px">HİSSE</th>
          <th style="padding:8px 16px;text-align:left;font-size:10px;color:#64748b;font-weight:600;letter-spacing:.5px">FİYAT</th>
          <th style="padding:8px 16px;text-align:left;font-size:10px;color:#64748b;font-weight:600;letter-spacing:.5px">SİNYAL</th>
          <th style="padding:8px 16px"></th>
        </tr></thead>
        <tbody>{rows}</tbody>
      </table>
    </div>
    <div style="text-align:center">
      <a href="https://borsapusula.com" style="display:inline-block;background:#1f6feb;color:#fff;padding:10px 24px;border-radius:8px;text-decoration:none;font-size:13px;font-weight:600">
        Tüm Sinyalleri Görüntüle →
      </a>
    </div>"""
    return _email_base(content, unsubscribe_url)


def _notify_email_signal_changes(changes):
    """Aktif abonelere sinyal değişim e-postası gönderir — arka planda çalışır."""
    if not SMTP_HOST or not changes:
        return

    def _send_batch():
        with _sub_lock:
            subs = _load_subscribers()
        active = {e: d for e, d in subs.items() if d.get("active", True)}
        if not active:
            return
        sent = 0
        for email, data in active.items():
            token    = data.get("token", "")
            tickers  = data.get("tickers", [])
            relevant = [c for c in changes if not tickers or c[0] in tickers]
            if not relevant:
                continue
            unsub_url = f"https://borsapusula.com/unsubscribe/{token}"
            subject   = "🔔 BorsaPusula — Sinyal Değişimi: " + ", ".join(c[0] for c in relevant[:3])
            if len(relevant) > 3:
                subject += f" +{len(relevant) - 3}"
            if send_email(email, subject, _build_signal_email(relevant, unsub_url)):
                sent += 1
            time.sleep(0.3)
        if sent:
            logger.info("E-posta bildirim gönderildi: %d abone", sent)

    threading.Thread(target=_send_batch, daemon=True).start()


_DISK_CACHE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "last_cache.json")


def _save_cache_to_disk(data):
    """Son başarılı sinyal datasını diske yazar — restart sonrası hızlı yükleme için."""
    try:
        with open(_DISK_CACHE_PATH, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False)
        logger.debug("Disk cache yazıldı: %d hisse", len(data))
    except Exception as e:
        logger.warning("Disk cache yazma hatası: %s", e)


def _load_cache_from_disk():
    """Disk cache'i yükler — servis başlarken ~3 dakikalık boş sayfayı önler."""
    try:
        if not os.path.exists(_DISK_CACHE_PATH):
            return
        with open(_DISK_CACHE_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        if data and isinstance(data, list) and len(data) > 0:
            with _lock:
                _cache["data"] = data
                _cache["updated_at"] = "disk cache (başlatılıyor…)"
            logger.info("Disk cache yüklendi: %d hisse (anlık veri bekleniyor)", len(data))
    except Exception as e:
        logger.warning("Disk cache okuma hatası: %s", e)


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

    # Başarılı güncellemeden sonra diske yaz
    _save_cache_to_disk(results)


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


_GLOBAL_TICKERS_YF = {
    "BTC":      "BTC-USD",
    "ETH":      "ETH-USD",
    "SOL":      "SOL-USD",
    "BNB":      "BNB-USD",
    "ALTIN":    "GC=F",
    "GUMUS":    "SI=F",
    "PETROL":   "CL=F",
    "DOGALGAZ": "NG=F",
    "SP500":    "^GSPC",
    "NASDAQ":   "^IXIC",
    # US Stocks
    "AAPL": "AAPL", "MSFT": "MSFT", "NVDA": "NVDA", "GOOGL": "GOOGL",
    "AMZN": "AMZN", "META": "META", "TSLA": "TSLA", "NFLX": "NFLX",
    "JPM":  "JPM",  "BRKB": "BRK-B","WMT":  "WMT",  "V":    "V",
    "MA":   "MA",   "UNH":  "UNH",  "XOM":  "XOM",
}

def fetch_global_prices():
    """Kripto, emtia ve ABD hisselerinin fiyatlarını çeker, SSE'ye push eder."""
    try:
        syms = list(set(_GLOBAL_TICKERS_YF.values()))
        df = yf.download(
            " ".join(syms), period="2d", interval="1m",
            progress=False, auto_adjust=True, group_by="ticker", timeout=30
        )
        if df is None or df.empty:
            return

        payload = {}
        now_str  = datetime.now().strftime("%H:%M:%S")
        # ters harita: yf sembol -> key listesi
        yf_to_keys = {}
        for k, v in _GLOBAL_TICKERS_YF.items():
            yf_to_keys.setdefault(v, []).append(k)

        for yf_sym, keys in yf_to_keys.items():
            try:
                if isinstance(df.columns, pd.MultiIndex):
                    lvls = df.columns.get_level_values(0)
                    if yf_sym not in lvls:
                        continue
                    closes = df[yf_sym]["Close"].dropna()
                else:
                    closes = df["Close"].dropna()

                if closes is None or len(closes) < 2:
                    continue

                price      = float(closes.iloc[-1])
                today_date = closes.index[-1].date()
                prev_bars  = closes[closes.index.map(lambda x: x.date()) < today_date]
                prev       = float(prev_bars.iloc[-1]) if len(prev_bars) > 0 else float(closes.iloc[-2])
                chg        = ((price - prev) / prev * 100) if prev else 0

                entry = {"price": round(price, 6), "change_pct": round(chg, 2), "updated": now_str}
                for k in keys:
                    payload[k] = entry
            except Exception:
                continue

        if payload:
            with _lock:
                _live_prices.update(payload)
            _push_sse({"type": "global_prices", "data": payload, "ts": now_str})

    except Exception as e:
        logger.error("fetch_global_prices: %s", e, exc_info=True)


def background_global_prices():
    while True:
        fetch_global_prices()
        time.sleep(60)


def background_live_prices():
    while True:
        fetch_live_prices()
        time.sleep(30)


def _purge_stale_chart_caches():
    """Fiyat uyuşmazlığı olan BIST hisse chart cache'lerini temizler.

    background_refresh() içinde her döngüde çağrılır. Ana cache (analyze())
    güncellendikten sonra, chart cache'inde eski bölünme/split verisi kalmış
    hisseleri tespit edip cache'i sıfırlar — böylece bir sonraki ziyarette
    taze data çekilir.
    """
    with _lock:
        stocks = list(_cache["data"])
    purged = 0
    for s in stocks:
        t = s.get("ticker")
        if not t or t in ("XU030", "XU100"):
            continue
        main_price = s.get("price", 0)
        if not main_price:
            continue
        with _lock:
            cached = _stock_chart_cache.get(t)
        if not cached:
            continue
        chart_price = (cached.get("data") or {}).get("summary", {}).get("price", 0)
        if chart_price > 0 and main_price > 0:
            ratio = max(chart_price, main_price) / min(chart_price, main_price)
            if ratio > 1.15:
                logger.warning(
                    "Watchdog: fiyat uyuşmazlığı [%s] chart=%.2f main=%.2f "
                    "oran=%.2fx — chart cache temizlendi",
                    t, chart_price, main_price, ratio
                )
                with _lock:
                    _stock_chart_cache.pop(t, None)
                purged += 1
    if purged:
        logger.info("Watchdog: %d hisse chart cache temizlendi (split/veri hatası)", purged)


def background_refresh():
    while True:
        refresh_chart()
        refresh_xu100_chart()
        _refresh_varlik_chart("BTC",   _btc_chart_cache)
        _refresh_varlik_chart("ALTIN", _altin_chart_cache)
        _refresh_varlik_chart("GUMUS", _gumus_chart_cache)
        _refresh_varlik_chart("ETH",    _eth_chart_cache)
        _refresh_varlik_chart("SP500",  _sp500_chart_cache)
        _refresh_varlik_chart("NASDAQ", _nasdaq_chart_cache)
        _refresh_varlik_chart("SOL",      _sol_chart_cache)
        _refresh_varlik_chart("BNB",      _bnb_chart_cache)
        _refresh_varlik_chart("PETROL",   _petrol_chart_cache)
        _refresh_varlik_chart("DOGALGAZ", _dogalgaz_chart_cache)
        refresh_data()
        _purge_stale_chart_caches()   # Split/split sonrası uyuşmazlık taraması
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
    resp = app.make_response(render_template("index.html"))
    resp.headers["Cache-Control"] = "no-store, no-cache, must-revalidate"
    resp.headers["Pragma"] = "no-cache"
    return resp


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
@limiter.limit("1 per 5 minutes")
def api_refresh():
    if ADMIN_SECRET and request.headers.get("X-Admin-Secret") != ADMIN_SECRET:
        abort(403)
    threading.Thread(target=refresh_data, daemon=True).start()
    return jsonify({"status": "refreshing"})


# ── Makro Veri Bandı ─────────────────────────────────────────────────────────
_macro_cache = {"data": None, "ts": 0}
_MACRO_TTL   = 60   # 60 saniye cache

def _fetch_macro():
    """XU100, XU030, BTC, ALTIN, GUMUS, PETROL, USD/TRY, EUR/TRY, S&P500, NASDAQ anlık veri."""
    tickers = [
        ("XU100",  "XU100.IS"),
        ("XU030",  "XU030.IS"),
        ("USDTRY", "USDTRY=X"),
        ("EURTRY", "EURTRY=X"),
        ("BTC",    "BTC-USD"),
        ("ALTIN",  "GC=F"),
        ("GUMUS",  "SI=F"),
        ("PETROL", "CL=F"),
        ("SP500",  "^GSPC"),
        ("NASDAQ", "^IXIC"),
    ]
    result = []
    for label, sym in tickers:
        try:
            tk  = yf.Ticker(sym)
            fi  = tk.fast_info
            price  = getattr(fi, "last_price", None) or getattr(fi, "regularMarketPrice", None)
            prev   = getattr(fi, "previous_close", None)
            if price is None or prev is None or prev == 0:
                continue
            change = round((float(price) - float(prev)) / float(prev) * 100, 2)
            result.append({"label": label, "price": round(float(price), 2), "change": change})
        except Exception as e:
            logger.debug("_fetch_macro %s: %s", label, e)
    return result

@app.route("/api/macro")
@limiter.limit("60 per minute")
def api_macro():
    now = time.time()
    with _lock:
        if _macro_cache["data"] and (now - _macro_cache["ts"]) < _MACRO_TTL:
            return safe_json({"items": _macro_cache["data"], "cached": True})
    items = _fetch_macro()
    with _lock:
        _macro_cache["data"] = items
        _macro_cache["ts"]   = now
    return safe_json({"items": items, "cached": False})


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
                        "text":     "▲"        if sig == "AL" else "▼",
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
_xu100_chart_cache = {"data": None, "updated_at": None}
_btc_chart_cache   = {"data": None, "updated_at": None}
_altin_chart_cache = {"data": None, "updated_at": None}
_gumus_chart_cache = {"data": None, "updated_at": None}
_eth_chart_cache    = {"data": None, "updated_at": None}
_sp500_chart_cache  = {"data": None, "updated_at": None}
_nasdaq_chart_cache  = {"data": None, "updated_at": None}
_sol_chart_cache     = {"data": None, "updated_at": None}
_bnb_chart_cache     = {"data": None, "updated_at": None}
_petrol_chart_cache  = {"data": None, "updated_at": None}
_dogalgaz_chart_cache= {"data": None, "updated_at": None}
_stock_chart_cache = {}          # {ticker: {"data": ..., "ts": float, "updated_at": str}}
_STOCK_CACHE_TTL   = 900         # 15 dakika


# ── Gemini API — AI haber özeti & sinyal açıklaması ─────────────────────────
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")

# Cache yapıları
# failed=True → negatif cache (başarısız istek, kısa TTL)
_news_cache           = {}   # {ticker: {"text": str|None, "ts": float, "failed": bool}}
_NEWS_CACHE_TTL       = 3600 * 6   # 6 saat — başarılı yanıt
_NEWS_FAIL_TTL        = 300        # 5 dakika — başarısız yanıt (negatif cache)

# On-demand news fetch kuyruğu (market-news endpoint'i tarafından doldurulur)
_news_fetch_queue     = set()      # tickers waiting for background fetch
_news_queue_lock      = threading.Lock()

_signal_explain_cache = {}   # {ticker: {"text": str|None, "sig": str, "ts": float, "failed": bool}}
_SIG_EXPLAIN_TTL      = 3600 * 4   # 4 saat
_SIG_FAIL_TTL         = 300        # 5 dakika

# Model fallback zinciri: birincil 2.5-flash, yedek 1.5-flash
# (use_search=False olan denemeler grounding olmadan gider → daha stabil)
_GEMINI_NEWS_ATTEMPTS = [
    ("gemini-2.5-flash",      True),   # 1. tercih: Flash 2.5 + Google Search grounding
    ("gemini-2.5-flash-lite", False),  # fallback: Flash 2.5 Lite, stabil, grounding yok
]
_GEMINI_EXPLAIN_ATTEMPTS = [
    ("gemini-2.5-flash",      False),  # 1. tercih: Flash 2.5
    ("gemini-2.5-flash-lite", False),  # fallback: Flash 2.5 Lite, stabil
]


def _gemini_call(prompt, attempts, timeout=20):
    """Model fallback zinciri ile Gemini API çağrısı yapar.

    Args:
        prompt: Gönderilecek metin
        attempts: [(model_id, use_google_search), ...] listesi
        timeout: İstek zaman aşımı (saniye)

    Returns:
        (model_id, text) — başarılı ise; (None, None) — tüm modeller başarısızsa
    """
    if not GEMINI_API_KEY:
        return None, None

    for model_id, use_search in attempts:
        body = {"contents": [{"parts": [{"text": prompt}]}]}
        if use_search:
            body["tools"] = [{"google_search": {}}]
        url = (f"https://generativelanguage.googleapis.com/v1beta/"
               f"models/{model_id}:generateContent?key={GEMINI_API_KEY}")
        try:
            r = requests.post(url, json=body, timeout=timeout)
            r.raise_for_status()
            text = (r.json().get("candidates", [{}])[0]
                            .get("content", {})
                            .get("parts", [{}])[0]
                            .get("text", "")).strip()
            if text:
                return model_id, text
            # Model yanıt verdi ama boş metin — fallback'e geç
            logger.debug("_gemini_call [%s]: boş yanıt, fallback deneniyor", model_id)
        except Exception as e:
            status = getattr(getattr(e, "response", None), "status_code", None)
            logger.warning("_gemini_call [%s]: %s (HTTP %s)", model_id, type(e).__name__, status)
            # 5xx ve 429 → geçici sorun, bir sonraki modeli dene
            # 4xx (400, 403 vb.) → API/key sorunu, fallback da aynı hatayı verir
            if status and 400 <= status < 500 and status != 429:
                break   # Fallback fayda vermez, dur

    return None, None


def get_ai_news(ticker):
    """Gemini + Google Search grounding ile Türkçe haber özeti üretir.

    Model fallback: gemini-2.5-flash → gemini-1.5-flash
    Negatif cache: tüm modeller başarısız olursa 5 dk boyunca yeniden deneme yapılmaz.
    """
    if not GEMINI_API_KEY:
        return None
    now = time.time()
    with _lock:
        cached = _news_cache.get(ticker)
        if cached:
            ttl = _NEWS_FAIL_TTL if cached.get("failed") else _NEWS_CACHE_TTL
            if (now - cached["ts"]) < ttl:
                return cached.get("text")   # başarısız cache → None döner

    name       = STOCK_NAMES.get(ticker, ticker)
    today_str  = datetime.now().strftime("%d %B %Y")   # ör: "24 Nisan 2026"
    cutoff_str = datetime.now().strftime("%Y-%m-%d")    # ör: "2026-04-17" (7 gün öncesi referans)
    prompt = (
        f"Bugünün tarihi: {today_str}.\n"
        f"Borsa İstanbul'da işlem gören {ticker} ({name}) hissesi hakkında "
        f"YALNIZCA son 7 gün ({cutoff_str} sonrası) içindeki gelişmeleri, haberleri ve "
        f"şirket açıklamalarını Türkçe olarak 3-5 madde halinde kısaca özetle. "
        f"Daha eski (1 aydan eski) haberleri kesinlikle ekleme. "
        f"Her madde 1-2 cümle olsun ve tarihi belirt. "
        f"Son 7 günde kayda değer haber yoksa bunu açıkça belirt. "
        f"Sadece maddeleri yaz, giriş/kapanış cümlesi ekleme."
    )

    model_used, text = _gemini_call(prompt, _GEMINI_NEWS_ATTEMPTS, timeout=25)

    with _lock:
        if text:
            logger.info("get_ai_news(%s): OK [model=%s]", ticker, model_used)
            _news_cache[ticker] = {"text": text, "ts": now, "failed": False}
        else:
            logger.warning("get_ai_news(%s): tüm modeller başarısız → negatif cache 5dk", ticker)
            _news_cache[ticker] = {"text": None, "ts": now, "failed": True}
    return text


def get_ai_signal_explanation(ticker, signal_data):
    """Gemini ile teknik sinyal açıklaması üretir.

    Strateji:
    - _generate_commentary() algoritmik metin GERÇEK DOĞRU olarak AI'ya verilir
    - AI sadece bu metni daha akıcı/anlaşılır dile çevirir, kendi yorumunu YAPAMAZ
    - Validation: AI sinyalin yönüyle çelişen anahtar kelimeler üretirse commentary fallback
    - AI tümüyle başarısız olursa commentary direkt döner (null yerine)

    Model fallback: gemini-2.5-flash → gemini-2.5-flash-lite
    Negatif cache: yalnızca GERÇEK API hatalarında (commentary her zaman var)
    """
    now = time.time()
    sig = signal_data.get("signal", "BEKLE")

    # Önce cache'i kontrol et
    with _lock:
        cached = _signal_explain_cache.get(ticker)
        if cached:
            ttl = _SIG_FAIL_TTL if cached.get("failed") else _SIG_EXPLAIN_TTL
            if (now - cached["ts"]) < ttl and cached.get("sig") == sig:
                return cached.get("text")

    name     = STOCK_NAMES.get(ticker, ticker)
    sig_lbl  = {"AL": "Güçlü Trend", "SAT": "Zayıf Trend", "BEKLE": "Belirsiz"}.get(sig, sig)

    # ── İndikatör değerlerini çıkar: US hisseleri (düz alan) + BIST (iç içe indicators) ──
    inds = signal_data.get("indicators") or {}

    # ADX: US hisseleri → düz "adx" alanı; BIST → indicators.adx.label ("ADX 25")
    adx_raw = signal_data.get("adx")
    if adx_raw is None:
        adx_label = (inds.get("adx") or {}).get("label", "ADX 0")
        try:
            adx = float(adx_label.replace("ADX", "").strip())
        except (ValueError, AttributeError):
            adx = 0.0
    else:
        adx = float(adx_raw or 0)

    # DI+/DI-: US hisseleri → düz "di_plus"/"di_minus"; BIST → indicators.adx.value ("DI+27/DI-15")
    di_plus  = signal_data.get("di_plus")
    di_minus = signal_data.get("di_minus")
    if di_plus is None or di_minus is None:
        di_val = (inds.get("adx") or {}).get("value", "")
        try:
            parts    = di_val.replace("DI+", "").split("/DI-")
            di_plus  = float(parts[0]) if len(parts) >= 1 else 0.0
            di_minus = float(parts[1]) if len(parts) >= 2 else 0.0
        except (ValueError, IndexError, AttributeError):
            di_plus, di_minus = 0.0, 0.0
    else:
        di_plus, di_minus = float(di_plus or 0), float(di_minus or 0)

    # EMA12/EMA99: US hisseleri → düz "e12"/"e99"; BIST → indicators.ema1299.value ("121/104")
    e12 = signal_data.get("e12")
    e99 = signal_data.get("e99")
    if e12 is None or e99 is None:
        ema_val = (inds.get("ema1299") or {}).get("value", "")
        try:
            parts = ema_val.split("/")
            e12 = float(parts[0]) if len(parts) >= 1 else 0.0
            e99 = float(parts[1]) if len(parts) >= 2 else 0.0
        except (ValueError, IndexError, AttributeError):
            e12, e99 = 0.0, 0.0
    else:
        e12, e99 = float(e12 or 0), float(e99 or 0)

    # Supertrend: US hisseleri → düz "st_bull"; BIST → indicators.supertrend.bull
    st_bull_raw = signal_data.get("st_bull")
    if st_bull_raw is None:
        st_bull = bool((inds.get("supertrend") or {}).get("bull", False))
    else:
        st_bull = bool(st_bull_raw)
    price    = signal_data.get("price", 0) or 0
    sl       = signal_data.get("sl_level")
    bars     = signal_data.get("signal_bars", 1) or 1

    # ── Algoritmik temel metin (her zaman doğru) ─────────────────────────────
    commentary = _generate_commentary(ticker, sig, bars, None, adx, di_plus, di_minus, e12, e99, st_bull)

    # AI yoksa direkt algoritmik metni döndür
    if not GEMINI_API_KEY:
        return commentary + " Yatırım tavsiyesi değildir."

    # ── Sinyalin yönü (validation için) ──────────────────────────────────────
    if sig == "AL":
        direction_tr   = "yükseliş"
        opposite_words = ["düşüş", "satış", "negatif", "aşağı", "zayıf trend", "bear", "sat ", "kayıp"]
    elif sig == "SAT":
        direction_tr   = "düşüş"
        opposite_words = ["yükseliş", "alım", "pozitif", "yukarı", "güçlü trend", "bull", "al ", "kazanç"]
    else:
        direction_tr   = "belirsiz"
        opposite_words = []

    # ── Stop-loss satırı ─────────────────────────────────────────────────────
    sl_line = f"\n- Stop-Loss seviyesi: {sl:.2f} ₺ (Supertrend alt/üst bandı)" if sl else ""

    # ── Directive prompt: AI sadece çeviri/stilize yapıyor ───────────────────
    prompt = (
        f"Aşağıdaki algoritmik borsa analizi KESINLIKLE DOĞRUDUR. "
        f"Görevin bunu olduğu gibi kabul edip sıradan bir yatırımcının anlayacağı, "
        f"sade ve akıcı Türkçe ile 3 cümleye yeniden yazmak.\n\n"
        f"=== DOĞRU ALGORİTMİK ANALİZ ===\n"
        f"{commentary}\n\n"
        f"=== ARKA PLAN ===\n"
        f"Hisse: {ticker} ({name})\n"
        f"Sinyal: {sig_lbl} — 3 göstergenin TAMAMI {direction_tr} yönünü işaret ediyor\n"
        f"Göstergeler:\n"
        f"  • Supertrend: {'YUKARI ✓' if st_bull else 'AŞAĞI ✓'}\n"
        f"  • ADX: {adx:.0f} {'(güçlü trend ✓)' if adx >= 25 else '(orta)'}, "
        f"DI+: {di_plus:.0f}, DI-: {di_minus:.0f}\n"
        f"  • EMA12 {e12:.0f} {'>' if e12 > e99 else '<'} EMA99 {e99:.0f} ✓\n"
        f"  • Fiyat: {price:.2f} ₺ | Sinyal süresi: {bars} gün{sl_line}\n\n"
        f"=== KURALLAR ===\n"
        f"1. Yukarıdaki algoritmik analizi destekle — ASLA çelişme veya 'ama' ile başlayan cümleler kurma\n"
        f"2. Sinyali '{sig_lbl}' olarak sun, düşünce belirtme\n"
        f"3. Teknik terimleri sıradan dile çevir (örn. Supertrend→fiyat trendi, ADX→trend gücü)\n"
        f"4. Son cümle mutlaka: 'Yatırım tavsiyesi değildir.'\n"
        f"5. Başlık ekleme, yalnızca paragraf yaz\n"
    )

    model_used, text = _gemini_call(prompt, _GEMINI_EXPLAIN_ATTEMPTS, timeout=20)

    # ── Validation: sinyalle çelişen metin ürettiyse commentary'ye fall back ─
    if text and opposite_words:
        text_lower = text.lower()
        if any(w in text_lower for w in opposite_words):
            logger.warning(
                "get_ai_signal_explanation(%s): AI sinyalle çelişti [%s→%s], commentary kullanılıyor",
                ticker, sig, text[:60]
            )
            text = None

    final_text = text if text else (commentary + " Yatırım tavsiyesi değildir.")

    with _lock:
        # AI başarılıysa uzun TTL, commentary fallback ise kısa TTL (AI tekrar denensin)
        ai_ok = bool(text)
        _signal_explain_cache[ticker] = {
            "text":   final_text,
            "sig":    sig,
            "ts":     now,
            "failed": not ai_ok,
        }
        if ai_ok:
            logger.info("get_ai_signal_explanation(%s): OK [model=%s]", ticker, model_used)
        else:
            logger.info("get_ai_signal_explanation(%s): commentary fallback kullanıldı", ticker)

    return final_text


# ── Arka plan: BIST30 haber ön-yüklemesi ─────────────────────────────────────
_PREFETCH_MAX    = 8    # Aynı anda en fazla bu kadar hisse prefetch edilir
_PREFETCH_DELAY  = 30   # İstekler arası bekleme (saniye) — Gemini rate-limit koruması


def _prefetch_news_worker():
    """AL sinyalli hisselerin haberlerini cache'e önceden yükler; her 6 saatte bir çalışır.

    Sunucu yeniden başlatıldıktan sonra kullanıcılar soğuk cache'e düşmeden
    içerik görür. Yalnızca AL sinyalli hisseler için çalışır (max 8) ve istekler
    arası 30 saniye bekler — Gemini ücretsiz tier rate-limit koruması.
    """
    time.sleep(120)   # Servis startup'ı ve veri yüklemesi tamamlanana kadar bekle
    while True:
        now = time.time()

        # Güncel cache'den AL sinyalli hisseleri seç (en fazla _PREFETCH_MAX adet)
        with _lock:
            stocks = list(_cache.get("data") or [])
        al_tickers = [
            s["ticker"] for s in stocks
            if s.get("signal") == "AL" and s.get("ticker") not in ("XU030", "XU100")
        ][:_PREFETCH_MAX]

        if not al_tickers:
            # Henüz veri yüklenmemiş — tekrar dene
            time.sleep(300)
            continue

        to_fetch = []
        with _lock:
            for ticker in al_tickers:
                cached = _news_cache.get(ticker)
                if not cached:
                    to_fetch.append(ticker)          # hiç denenmemiş
                elif cached.get("failed"):
                    to_fetch.append(ticker)          # başarısız cache süresi dolmuş
                elif (now - cached["ts"]) > _NEWS_CACHE_TTL * 0.9:
                    to_fetch.append(ticker)          # cache sona ermek üzere

        logger.info("Prefetch: %d/%d AL hisse için haber yüklenecek", len(to_fetch), len(al_tickers))
        fetched = 0
        for ticker in to_fetch:
            try:
                result = get_ai_news(ticker)
                if result:
                    fetched += 1
            except Exception as e:
                logger.error("Prefetch hatası [%s]: %s", ticker, e)
            time.sleep(_PREFETCH_DELAY)   # İstekler arası 30 saniye — rate-limit koruması

        logger.info("Prefetch tamamlandı: %d/%d başarılı", fetched, len(to_fetch))
        time.sleep(_NEWS_CACHE_TTL)   # Bir sonraki tur 6 saat sonra


_prefetch_thread = threading.Thread(
    target=_prefetch_news_worker,
    daemon=True,
    name="gemini-prefetch"
)
_prefetch_thread.start()


def _on_demand_news_worker():
    """market-news endpoint'inden gelen talep üzerine haber cache'i arka planda doldurur.

    Kuyrukta bekleyen her ticker için get_ai_news() çağırır; istekler arası
    15 saniye bekler (Gemini rate-limit koruması). Kuyruk boşsa 5s polling.
    """
    while True:
        ticker = None
        with _news_queue_lock:
            if _news_fetch_queue:
                ticker = _news_fetch_queue.pop()
        if ticker:
            try:
                result = get_ai_news(ticker)
                logger.info("On-demand news [%s]: %s", ticker, "OK" if result else "FAIL")
            except Exception as exc:
                logger.error("On-demand news hatası [%s]: %s", ticker, exc)
            time.sleep(15)   # İstekler arası 15s — rate-limit koruması
        else:
            time.sleep(5)    # Kuyruk boşsa 5s bekle


_on_demand_thread = threading.Thread(
    target=_on_demand_news_worker,
    daemon=True,
    name="news-ondemand"
)
_on_demand_thread.start()


def _generate_commentary(ticker, signal, signal_bars, signal_date, adx, di_p, di_m, e12, e99, st_bull):
    """Algoritmik teknik yorum metni üretir (SEO + kullanıcı için)."""
    _varlik_names = {
        "BTC":"Bitcoin","ETH":"Ethereum",
        "ALTIN":"Altın","GUMUS":"Gümüş",
        "SP500":"S&P 500","NASDAQ":"NASDAQ Composite",
        "SOL":"Solana","BNB":"BNB (Binance)",
        "PETROL":"Ham Petrol","DOGALGAZ":"Doğal Gaz",
        "XU030":"BIST30 Endeksi","XU100":"BIST100 Endeksi",
        **{k: v for k,v in US_STOCK_NAMES.items()},
    }
    name = STOCK_NAMES.get(ticker) or _varlik_names.get(ticker, ticker)
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
            f"{ticker} ({name}) hissesi şu anda net bir Güçlü/Zayıf Trend sinyali üretmiyor. "
            f"{mixed} "
            f"ADX {adx:.0f} ({adx_quality}), EMA12 {e12:.0f} / EMA99 {e99:.0f}."
        )


# ── Makro varlık tanımları (BTC / Altın / Gümüş) ──────────────────────────────
_VARLIK_META = {
    "BTC": {
        "name":       "Bitcoin",
        "ticker_yf":  "BTC-USD",
        "unit":       "USD",
        "emoji":      "₿",
        "color":      "#f7931a",
        "desc":       "Bitcoin (BTC) teknik analizi — Supertrend, ADX ve EMA sinyalleri",
        "period":     "2y",
    },
    "ALTIN": {
        "name":       "Altın (XAU/USD)",
        "ticker_yf":  "GC=F",
        "unit":       "USD/oz",
        "emoji":      "🥇",
        "color":      "#e3b341",
        "desc":       "Altın (XAU/USD) teknik analizi — Supertrend, ADX ve EMA sinyalleri",
        "period":     "2y",
    },
    "GUMUS": {
        "name":       "Gümüş (XAG/USD)",
        "ticker_yf":  "SI=F",
        "unit":       "USD/oz",
        "emoji":      "🥈",
        "color":      "#8b949e",
        "desc":       "Gümüş (XAG/USD) teknik analizi — Supertrend, ADX ve EMA sinyalleri",
        "period":     "2y",
    },
    "ETH": {
        "name": "Ethereum", "ticker_yf": "ETH-USD", "unit": "USD",
        "emoji": "⟠", "color": "#627eea",
        "desc": "Ethereum (ETH) teknik analizi — Supertrend, ADX ve EMA sinyalleri",
        "period": "2y",
    },
    "SP500": {
        "name": "S&P 500", "ticker_yf": "^GSPC", "unit": "USD",
        "emoji": "📈", "color": "#3fb950",
        "desc": "S&P 500 endeksi teknik analizi — Supertrend, ADX ve EMA sinyalleri",
        "period": "2y",
    },
    "NASDAQ": {
        "name": "NASDAQ Composite", "ticker_yf": "^IXIC", "unit": "USD",
        "emoji": "💹", "color": "#58a6ff",
        "desc": "NASDAQ Composite endeksi teknik analizi",
        "period": "2y",
    },
    "SOL": {
        "name": "Solana", "ticker_yf": "SOL-USD", "unit": "USD",
        "emoji": "◎", "color": "#9945ff",
        "desc": "Solana (SOL) teknik analizi — Supertrend, ADX ve EMA sinyalleri",
        "period": "2y",
    },
    "BNB": {
        "name": "BNB (Binance)", "ticker_yf": "BNB-USD", "unit": "USD",
        "emoji": "⬡", "color": "#f3ba2f",
        "desc": "BNB (Binance Coin) teknik analizi — Supertrend, ADX ve EMA sinyalleri",
        "period": "2y",
    },
    "PETROL": {
        "name": "Ham Petrol (WTI)", "ticker_yf": "CL=F", "unit": "USD/bbl",
        "emoji": "🛢️", "color": "#d4870b",
        "desc": "Ham Petrol (WTI) vadeli işlem teknik analizi — Supertrend, ADX ve EMA sinyalleri",
        "period": "2y",
    },
    "DOGALGAZ": {
        "name": "Doğal Gaz", "ticker_yf": "NG=F", "unit": "USD/MMBtu",
        "emoji": "🔥", "color": "#ef5a2a",
        "desc": "Doğal Gaz vadeli işlem teknik analizi — Supertrend, ADX ve EMA sinyalleri",
        "period": "2y",
    },
}

# yfinance sembol eşleme tablosu
_TICKER_SYMBOL_MAP = {
    "XU030": "XU030.IS",
    "XU100": "XU100.IS",
    "BTC":   "BTC-USD",
    "ALTIN": "GC=F",
    "GUMUS": "SI=F",
    "ETH":      "ETH-USD",
    "SP500":    "^GSPC",
    "NASDAQ":   "^IXIC",
    "SOL":      "SOL-USD",
    "BNB":      "BNB-USD",
    "PETROL":   "CL=F",
    "DOGALGAZ": "NG=F",
}

# ── ABD Hisseleri ─────────────────────────────────────────────────────────────
US_STOCKS = [
    "AAPL","MSFT","NVDA","GOOGL","AMZN","META","TSLA",
    "NFLX","JPM","BRKB","WMT","V","MA","UNH","XOM",
]
US_STOCK_NAMES = {
    "AAPL":"Apple","MSFT":"Microsoft","NVDA":"NVIDIA",
    "GOOGL":"Alphabet (Google)","AMZN":"Amazon","META":"Meta Platforms",
    "TSLA":"Tesla","NFLX":"Netflix","JPM":"JPMorgan Chase",
    "BRKB":"Berkshire Hathaway","WMT":"Walmart","V":"Visa",
    "MA":"Mastercard","UNH":"UnitedHealth","XOM":"ExxonMobil",
}
US_SECTORS = {
    "Teknoloji":    ["AAPL","MSFT","NVDA","GOOGL","META"],
    "E-Ticaret":    ["AMZN"],
    "Otomotiv":     ["TSLA"],
    "Medya":        ["NFLX"],
    "Finans":       ["JPM","BRKB","V","MA"],
    "Perakende":    ["WMT"],
    "Sağlık":       ["UNH"],
    "Enerji":       ["XOM"],
}

# US stocks için yfinance sembol eşleme (_TICKER_SYMBOL_MAP'a ekle)
_TICKER_SYMBOL_MAP.update({
    "AAPL":"AAPL","MSFT":"MSFT","NVDA":"NVDA","GOOGL":"GOOGL","AMZN":"AMZN",
    "META":"META","TSLA":"TSLA","NFLX":"NFLX","JPM":"JPM","BRKB":"BRK-B",
    "WMT":"WMT","V":"V","MA":"MA","UNH":"UNH","XOM":"XOM",
})

# ── Varlık eş grupları (kategori sayfaları için) ──────────────────────────────
_KRIPTO_PEERS = [
    {"key":"BTC",  "name":"Bitcoin",  "href":"/btc",  "emoji":"₿"},
    {"key":"ETH",  "name":"Ethereum", "href":"/eth",  "emoji":"⟠"},
    {"key":"SOL",  "name":"Solana",   "href":"/sol",  "emoji":"◎"},
    {"key":"BNB",  "name":"BNB",      "href":"/bnb",  "emoji":"⬡"},
]
_EMTIA_PEERS = [
    {"key":"ALTIN",    "name":"Altın",     "href":"/altin",    "emoji":"🥇"},
    {"key":"GUMUS",    "name":"Gümüş",     "href":"/gumus",    "emoji":"🥈"},
    {"key":"PETROL",   "name":"Petrol",    "href":"/petrol",   "emoji":"🛢️"},
    {"key":"DOGALGAZ", "name":"Doğal Gaz", "href":"/dogalgaz", "emoji":"🔥"},
]
_ABD_INDEX_PEERS = [
    {"key":"SP500", "name":"S&P 500","href":"/abd/sp500", "emoji":"📈"},
    {"key":"NASDAQ","name":"NASDAQ", "href":"/abd/nasdaq","emoji":"💹"},
]

# ── Ortak grafik verisi hesaplama (XU030 + bireysel hisseler + makro varlıklar) ─
def _compute_chart_data(ticker_base, period="2y"):
    """Herhangi bir hisse / varlık için grafik verisi hesaplar (OHLC, EMA, ST, sinyal geçmişi)."""
    ticker = _TICKER_SYMBOL_MAP.get(ticker_base, ticker_base + ".IS")
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
                        "text":     "▲" if sig == "AL" else "▼",
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

        # ── Haftalık trend kapısı — analyze() ile tam senkron ───────────
        # Mevcut günlük veriyi yeniden örnekleyerek haftalık EMA20 hesaplar;
        # ekstra yfinance çağrısı gerekmez, analyze() ile aynı mantık.
        wkly_dir = 0
        try:
            wkly_close = close.resample("W-FRI").last().dropna()
            if len(wkly_close) >= 20:
                wk_ema = compute_ema(wkly_close, 20)
                wkly_dir = 1 if float(wk_ema.iloc[-1]) > float(wk_ema.iloc[-2]) else -1
        except Exception:
            wkly_dir = 0

        if bull_score >= 3 and wkly_dir != -1:
            signal = "AL"
        elif bear_score >= 3 and wkly_dir != 1:
            signal = "SAT"
        else:
            signal = "BEKLE"

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


def refresh_xu100_chart():
    """XU100 grafik verisini günceller — _compute_chart_data wrapper."""
    try:
        d = _compute_chart_data("XU100", "5y")
        if d:
            with _lock:
                _xu100_chart_cache["data"] = d
                _xu100_chart_cache["updated_at"] = datetime.now().strftime("%d.%m.%Y %H:%M:%S")
            logger.info("XU100 chart cache güncellendi")
    except Exception as e:
        logger.error("refresh_xu100_chart: %s", e, exc_info=True)


@app.route("/api/chart")
def api_chart():
    with _lock:
        return safe_json({
            "chart":      _chart_cache["data"],
            "updated_at": _chart_cache["updated_at"],
            "loading":    _chart_cache["data"] is None,
        })


@app.route("/api/chart/XU100")
def api_chart_xu100():
    with _lock:
        return safe_json({
            "chart":      _xu100_chart_cache["data"],
            "updated_at": _xu100_chart_cache["updated_at"],
            "loading":    _xu100_chart_cache["data"] is None,
        })


def _refresh_varlik_chart(varlik_key, cache_obj):
    """BTC / ALTIN / GUMUS grafik verisini günceller."""
    meta = _VARLIK_META.get(varlik_key, {})
    try:
        d = _compute_chart_data(varlik_key, meta.get("period", "2y"))
        if d:
            with _lock:
                cache_obj["data"] = d
                cache_obj["updated_at"] = datetime.now().strftime("%d.%m.%Y %H:%M:%S")
            logger.info("%s chart cache güncellendi", varlik_key)
    except Exception as e:
        logger.error("_refresh_varlik_chart(%s): %s", varlik_key, e, exc_info=True)


@app.route("/api/chart/BTC")
def api_chart_btc():
    with _lock:
        return safe_json({
            "chart":      _btc_chart_cache["data"],
            "updated_at": _btc_chart_cache["updated_at"],
            "loading":    _btc_chart_cache["data"] is None,
        })


@app.route("/api/chart/ALTIN")
def api_chart_altin():
    with _lock:
        return safe_json({
            "chart":      _altin_chart_cache["data"],
            "updated_at": _altin_chart_cache["updated_at"],
            "loading":    _altin_chart_cache["data"] is None,
        })


@app.route("/api/chart/GUMUS")
def api_chart_gumus():
    with _lock:
        return safe_json({
            "chart":      _gumus_chart_cache["data"],
            "updated_at": _gumus_chart_cache["updated_at"],
            "loading":    _gumus_chart_cache["data"] is None,
        })


@app.route("/api/chart/ETH")
def api_chart_eth():
    with _lock:
        return safe_json({"chart": _eth_chart_cache["data"],
                          "updated_at": _eth_chart_cache["updated_at"],
                          "loading": _eth_chart_cache["data"] is None})

@app.route("/api/chart/SP500")
def api_chart_sp500():
    with _lock:
        return safe_json({"chart": _sp500_chart_cache["data"],
                          "updated_at": _sp500_chart_cache["updated_at"],
                          "loading": _sp500_chart_cache["data"] is None})

@app.route("/api/chart/NASDAQ")
def api_chart_nasdaq():
    with _lock:
        return safe_json({"chart": _nasdaq_chart_cache["data"],
                          "updated_at": _nasdaq_chart_cache["updated_at"],
                          "loading": _nasdaq_chart_cache["data"] is None})

@app.route("/api/chart/SOL")
def api_chart_sol():
    with _lock:
        return safe_json({"chart": _sol_chart_cache["data"],
                          "updated_at": _sol_chart_cache["updated_at"],
                          "loading": _sol_chart_cache["data"] is None})

@app.route("/api/chart/BNB")
def api_chart_bnb():
    with _lock:
        return safe_json({"chart": _bnb_chart_cache["data"],
                          "updated_at": _bnb_chart_cache["updated_at"],
                          "loading": _bnb_chart_cache["data"] is None})

@app.route("/api/chart/PETROL")
def api_chart_petrol():
    with _lock:
        return safe_json({"chart": _petrol_chart_cache["data"],
                          "updated_at": _petrol_chart_cache["updated_at"],
                          "loading": _petrol_chart_cache["data"] is None})

@app.route("/api/chart/DOGALGAZ")
def api_chart_dogalgaz():
    with _lock:
        return safe_json({"chart": _dogalgaz_chart_cache["data"],
                          "updated_at": _dogalgaz_chart_cache["updated_at"],
                          "loading": _dogalgaz_chart_cache["data"] is None})


@app.route("/api/chart/us/<ticker>")
def api_chart_us_stock(ticker):
    """ABD hissesi grafik verisi — lazy cache (15 dakika TTL).
    Fiyat uyuşmazlığı tespit edilirse (split vb.) cache otomatik iptal edilir.
    """
    ticker = ticker.upper()
    if ticker not in US_STOCKS and ticker not in ("SP500","NASDAQ","SOL","BNB","PETROL","DOGALGAZ"):
        return safe_json({"error": "Hisse bulunamadı"}), 404
    now  = time.time()
    with _lock:
        cached = _stock_chart_cache.get(f"US_{ticker}")

    # US stock cache için global_prices ile fiyat karşılaştır
    if cached:
        chart_price = (cached.get("data") or {}).get("summary", {}).get("price", 0)
        with _lock:
            gp = _global_prices_cache.get("prices", {})
        main_price = gp.get(ticker, {}).get("price", 0) if gp else 0
        if chart_price > 0 and main_price > 0:
            ratio = max(chart_price, main_price) / min(chart_price, main_price)
            if ratio > 1.15:
                logger.warning(
                    "Fiyat uyuşmazlığı [US_%s]: chart=%.2f main=%.2f oran=%.2fx — cache iptal",
                    ticker, chart_price, main_price, ratio
                )
                cached = None

    if cached and (now - cached["ts"]) < _STOCK_CACHE_TTL:
        return safe_json({"chart": cached["data"], "updated_at": cached["updated_at"], "loading": False})

    data = _compute_chart_data(ticker, "2y")
    upd  = datetime.now().strftime("%d.%m.%Y %H:%M:%S")
    if data:
        with _lock:
            _stock_chart_cache[f"US_{ticker}"] = {"data": data, "ts": now, "updated_at": upd}
        return safe_json({"chart": data, "updated_at": upd, "loading": False})
    return safe_json({"chart": None, "loading": True})


# ── Makro Varlık Sayfaları (BTC / ETH / Altın / Gümüş) ──────────────────────
@app.route("/btc")
def btc_page():
    peers = [p for p in _KRIPTO_PEERS if p["key"] != "BTC"]
    return render_template("varlik.html", varlik_key="BTC", meta=_VARLIK_META["BTC"],
                           peers=peers, category_url="/kripto", category_label="Kripto")


@app.route("/eth")
def eth_page():
    peers = [p for p in _KRIPTO_PEERS if p["key"] != "ETH"]
    return render_template("varlik.html", varlik_key="ETH", meta=_VARLIK_META["ETH"],
                           peers=peers, category_url="/kripto", category_label="Kripto")


@app.route("/sol")
def sol_page():
    peers = [p for p in _KRIPTO_PEERS if p["key"] != "SOL"]
    return render_template("varlik.html", varlik_key="SOL", meta=_VARLIK_META["SOL"],
                           peers=peers, category_url="/kripto", category_label="Kripto")

@app.route("/bnb")
def bnb_page():
    peers = [p for p in _KRIPTO_PEERS if p["key"] != "BNB"]
    return render_template("varlik.html", varlik_key="BNB", meta=_VARLIK_META["BNB"],
                           peers=peers, category_url="/kripto", category_label="Kripto")


@app.route("/altin")
def altin_page():
    peers = [p for p in _EMTIA_PEERS if p["key"] != "ALTIN"]
    return render_template("varlik.html", varlik_key="ALTIN", meta=_VARLIK_META["ALTIN"],
                           peers=peers, category_url="/emtialar", category_label="Emtialar")


@app.route("/gumus")
def gumus_page():
    peers = [p for p in _EMTIA_PEERS if p["key"] != "GUMUS"]
    return render_template("varlik.html", varlik_key="GUMUS", meta=_VARLIK_META["GUMUS"],
                           peers=peers, category_url="/emtialar", category_label="Emtialar")


@app.route("/petrol")
def petrol_page():
    peers = [p for p in _EMTIA_PEERS if p["key"] != "PETROL"]
    return render_template("varlik.html", varlik_key="PETROL", meta=_VARLIK_META["PETROL"],
                           peers=peers, category_url="/emtialar", category_label="Emtialar")

@app.route("/dogalgaz")
def dogalgaz_page():
    peers = [p for p in _EMTIA_PEERS if p["key"] != "DOGALGAZ"]
    return render_template("varlik.html", varlik_key="DOGALGAZ", meta=_VARLIK_META["DOGALGAZ"],
                           peers=peers, category_url="/emtialar", category_label="Emtialar")


@app.route("/kripto")
def kripto_page():
    return render_template("kategori.html",
        category_key="kripto",
        title="Kripto Varlıklar", emoji="🔐",
        desc="Bitcoin ve Ethereum Supertrend + ADX + EMA12/99 teknik analizi",
        assets=_KRIPTO_PEERS,
        us_stocks=None)

@app.route("/emtialar")
def emtialar_page():
    return render_template("kategori.html",
        category_key="emtialar",
        title="Emtialar", emoji="🥇",
        desc="Altın ve Gümüş Supertrend + ADX + EMA12/99 teknik analizi",
        assets=_EMTIA_PEERS,
        us_stocks=None)

@app.route("/abd")
def abd_page():
    us_list = [{"key": t, "name": US_STOCK_NAMES.get(t,t),
                "sector": next((s for s,tl in US_SECTORS.items() if t in tl),"Diğer"),
                "href": f"/abd/{t}"}
               for t in US_STOCKS]
    return render_template("kategori.html",
        category_key="abd",
        title="ABD Piyasaları", emoji="🇺🇸",
        desc="S&P 500, NASDAQ ve ABD büyük şirketleri teknik analizi",
        assets=_ABD_INDEX_PEERS,
        us_stocks=us_list)

@app.route("/abd/tarama")
def abd_tarama_page():
    """ABD hisseleri tarama sayfası."""
    all_assets = []
    # Önce endeksler
    for p in _ABD_INDEX_PEERS:
        all_assets.append({**p, "sector": "Endeks", "api": f"/api/chart/{p['key']}"})
    # Sonra hisseler
    for t in US_STOCKS:
        sector = next((s for s,tl in US_SECTORS.items() if t in tl), "Diğer")
        all_assets.append({
            "key": t, "name": US_STOCK_NAMES.get(t, t),
            "href": f"/abd/{t}", "emoji": "🇺🇸",
            "sector": sector, "api": f"/api/chart/us/{t}"
        })
    return render_template("abd_tarama.html",
        title="ABD Tarama", emoji="🔍",
        desc="ABD hisseleri ve endeksleri — Supertrend + ADX + EMA sinyal tarayıcısı",
        assets=all_assets)

@app.route("/abd/sp500")
def abd_sp500_page():
    peers = [p for p in _ABD_INDEX_PEERS if p["key"] != "SP500"]
    return render_template("varlik.html", varlik_key="SP500", meta=_VARLIK_META["SP500"],
                           peers=peers, category_url="/abd", category_label="ABD")

@app.route("/abd/nasdaq")
def abd_nasdaq_page():
    peers = [p for p in _ABD_INDEX_PEERS if p["key"] != "NASDAQ"]
    return render_template("varlik.html", varlik_key="NASDAQ", meta=_VARLIK_META["NASDAQ"],
                           peers=peers, category_url="/abd", category_label="ABD")

@app.route("/abd/<ticker>")
def abd_stock_page(ticker):
    ticker = ticker.upper()
    if ticker in ("SP500",): return abd_sp500_page()
    if ticker in ("NASDAQ",): return abd_nasdaq_page()
    if ticker not in US_STOCKS:
        return render_template("index.html"), 404
    name   = US_STOCK_NAMES.get(ticker, ticker)
    sector = next((s for s,tl in US_SECTORS.items() if ticker in tl), "Diğer")
    meta = {
        "name": f"{ticker} — {name}", "ticker_yf": _TICKER_SYMBOL_MAP.get(ticker, ticker),
        "unit": "USD", "emoji": "🇺🇸", "color": "#1f6feb",
        "desc": f"{name} ({ticker}) teknik analizi — Supertrend, ADX ve EMA sinyalleri",
        "period": "2y",
    }
    peers = [{"key":t,"name":US_STOCK_NAMES.get(t,t),"href":f"/abd/{t}","emoji":"🇺🇸"}
             for t in US_STOCKS if t != ticker][:4]
    return render_template("varlik.html", varlik_key=ticker, meta=meta,
                           peers=peers, category_url="/abd", category_label="ABD",
                           chart_api=f"/api/chart/us/{ticker}")


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

    # SEO: mevcut cache'ten temel sinyal verisini SSR için çek
    ssr_signal = None
    with _lock:
        for s in _cache["data"]:
            if s.get("ticker") == ticker:
                ssr_signal = s
                break

    return render_template("hisse.html",
                           ticker=ticker,
                           name=name,
                           sector=sector,
                           others=others,
                           stock_names=STOCK_NAMES,
                           ssr_signal=ssr_signal)


_fundamentals_cache = {}
_FUND_TTL = 3600 * 4  # 4 saat

# ── Temel analiz sanity sınırları (yfinance Türk hisselerinde bozuk değer üretir) ──
_FUND_SANITY = {
    "pe_ratio":       (0.0, 150.0),   # P/E > 150 → muhtemelen dolar/lira karışıklığı
    "dividend_yield": (0.0, 50.0),    # %50 üstü → imkânsız (zaten *100 çarpılmış)
    "beta":           (0.10, 5.0),    # 0.06-0.09 beta havacılık için saçma
    "pb_ratio":       (0.0, 50.0),    # P/B > 50 → bozuk
    "roe":            (-100.0, 200.0),# ROE > 200% → bozuk
}

def _clean_fundamentals(data: dict) -> dict:
    """yfinance bozuk Türk hisse değerlerini sanity sınırlarına göre None'a çeker."""
    cleaned = {}
    for k, v in data.items():
        if k in _FUND_SANITY and v is not None:
            lo, hi = _FUND_SANITY[k]
            if not (lo <= v <= hi):
                logger.debug("_clean_fundamentals: %s=%s sınır dışı → None", k, v)
                cleaned[k] = None
            else:
                cleaned[k] = v
        else:
            cleaned[k] = v
    return cleaned


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

        raw = {
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
        data = _clean_fundamentals(raw)
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
@limiter.limit("20 per minute")
def api_stock_news(ticker):
    """Gemini AI haber özeti — 6 saatlik cache."""
    ticker = ticker.upper()
    if ticker not in BIST100:
        return safe_json({"error": "Hisse bulunamadı"}), 404
    text = get_ai_news(ticker)
    if text:
        return safe_json({"news": text, "source": "gemini"})
    return safe_json({"news": ""})


@app.route("/api/hisse/<ticker>/signal-explanation")
@limiter.limit("20 per minute")
def api_signal_explanation(ticker):
    """Sinyal açıklaması — AI varsa AI, yoksa algoritmik metin döner. Her zaman dolu.
    BIST hisseleri için _cache["data"] kullanılır.
    US hisseleri için _stock_chart_cache["US_{ticker}"]["data"]["summary"] kullanılır.
    """
    ticker = ticker.upper()
    is_bist = ticker in BIST100
    is_us   = ticker in US_STOCKS

    if not is_bist and not is_us:
        return safe_json({"error": "Hisse bulunamadı"}), 404

    if is_bist:
        # BIST hissesi — anlık sinyal datasını cache'den al
        with _lock:
            stocks = list(_cache.get("data") or _cache.get("stocks") or [])
        stock = next((s for s in stocks if s.get("ticker") == ticker), None)
        if not stock:
            return safe_json({"explanation": None, "reason": "no_data"})
    else:
        # US hissesi — chart cache'inden "summary" al (lazy hesapla)
        now = time.time()
        with _lock:
            cached = _stock_chart_cache.get(f"US_{ticker}")
        if cached and cached.get("data") and cached.get("data", {}).get("summary"):
            stock = cached["data"]["summary"]
        else:
            # Cache yok — hesapla (ilk açılış gecikir ama sonrası cache'den gelir)
            data = _compute_chart_data(ticker, "2y")
            upd  = datetime.now().strftime("%d.%m.%Y %H:%M:%S")
            if data and data.get("summary"):
                with _lock:
                    _stock_chart_cache[f"US_{ticker}"] = {"data": data, "ts": now, "updated_at": upd}
                stock = data["summary"]
            else:
                return safe_json({"explanation": None, "reason": "no_data"})

    text = get_ai_signal_explanation(ticker, stock)
    source = "gemini" if GEMINI_API_KEY else "algorithmic"
    return safe_json({"explanation": text, "signal": stock.get("signal"), "source": source})


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

    def _tf_signal_4h(sym):
        try:
            df = yf.download(sym, period="60d", interval="1h",
                             progress=False, auto_adjust=True, timeout=25)
            if df is None or df.empty:
                return None
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = df.columns.get_level_values(0)
                df = df.loc[:, ~df.columns.duplicated()]
            df = df.dropna().sort_index()
            df_4h = df.resample("4h").agg({
                "Open":  "first", "High": "max",
                "Low":   "min",   "Close": "last",
                "Volume":"sum",
            }).dropna(subset=["Close"])
            if len(df_4h) < 40:
                return None
            close = df_4h["Close"].squeeze()
            high  = df_4h["High"].squeeze()
            low   = df_4h["Low"].squeeze()
            ema12, ema99      = compute_ema(close, 12), compute_ema(close, 99)
            adx_s, dip_s, dim_s = compute_adx(high, low, close)
            st_s, st_ln       = compute_supertrend(high, low, close)
            c    = float(close.iloc[-1])
            e12  = float(ema12.iloc[-1]); e99_ = float(ema99.iloc[-1])
            adxv = float(adx_s.iloc[-1])
            dipv = float(dip_s.iloc[-1]); dimv = float(dim_s.iloc[-1])
            stv  = int(st_s.iloc[-1])
            bs   = int(stv == 1)  + int(adxv >= 25 and dipv > dimv) + int(e12 > e99_)
            brs  = int(stv == -1) + int(adxv >= 25 and dimv > dipv) + int(e12 < e99_)
            sig  = "AL" if bs >= 3 else "SAT" if brs >= 3 else "BEKLE"
            return {
                "signal":     sig,
                "price":      round(c, 2),
                "adx":        round(adxv, 1),
                "sl":         round(float(st_ln.iloc[-1]), 2),
                "bull_score": bs,
                "bear_score": brs,
            }
        except Exception as e:
            logger.debug("_tf_signal_4h(%s): %s", sym, e)
            return None

    return {
        "ticker":  ticker,
        "h4":      _tf_signal_4h(sym),
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

    # ── Otoritelif sinyal kaynağı: ana cache ──────────────────────────────
    with _lock:
        stocks     = list(_cache["data"])
        cached     = _stock_chart_cache.get(ticker)
    main_stock = next((s for s in stocks if s.get("ticker") == ticker), None)
    main_price = main_stock.get("price", 0) if main_stock else 0

    # ── Fiyat uyuşmazlık tespiti: bölünme/split sonrası eski cache'i iptal et ─
    if cached and main_price > 0:
        chart_price = (cached.get("data") or {}).get("summary", {}).get("price", 0)
        if chart_price > 0:
            ratio = max(chart_price, main_price) / min(chart_price, main_price)
            if ratio > 1.15:   # %15 üstü fiyat sapması → hisse bölünmesi veya veri hatası
                logger.warning(
                    "Fiyat uyuşmazlığı [%s]: chart=%.2f main=%.2f oran=%.2fx — "
                    "chart cache iptal ediliyor (bölünme veya veri hatası)",
                    ticker, chart_price, main_price, ratio
                )
                cached = None   # Taze hesaplamaya zorla

    if cached and (now - cached["ts"]) < _STOCK_CACHE_TTL:
        data = cached["data"]
        upd  = cached["updated_at"]
    else:
        # Cache yok, bayat veya fiyat uyuşmazlığı → taze hesapla
        data = _compute_chart_data(ticker, period="2y")
        upd  = datetime.now().strftime("%d.%m.%Y %H:%M:%S")
        if data:
            with _lock:
                _stock_chart_cache[ticker] = {"data": data, "ts": now, "updated_at": upd}

    if not data:
        return safe_json({"chart": None, "loading": True})

    # ── Sinyal senkronizasyonu: ana cache otoritelif kaynaktır ───────────────
    # _compute_chart_data() ve analyze() farklı zamanlarda çalışabilir;
    # ana cache'in sinyali her zaman önceliklidir.
    if main_stock:
        chart_sig = (data.get("summary") or {}).get("signal")
        main_sig  = main_stock.get("signal")
        if chart_sig != main_sig:
            logger.warning(
                "Sinyal uyuşmazlığı [%s]: chart=%s main=%s → ana cache sinyali kullanılıyor",
                ticker, chart_sig, main_sig
            )
        # Derin kopya — cache'de saklanan dict'i değiştirmemek için
        data = copy.deepcopy(data)
        if data.get("summary") is None:
            data["summary"] = {}
        data["summary"]["signal"]      = main_sig or chart_sig
        data["summary"]["bull_score"]  = main_stock.get("bull_score",  data["summary"].get("bull_score"))
        data["summary"]["bear_score"]  = main_stock.get("bear_score",  data["summary"].get("bear_score"))
        data["summary"]["sl_level"]    = main_stock.get("sl_level",    data["summary"].get("sl_level"))
        data["summary"]["signal_bars"] = main_stock.get("signal_bars", data["summary"].get("signal_bars", 1))

    return safe_json({"chart": data, "updated_at": upd, "loading": False})


# ── Strateji Tarayıcısı ──────────────────────────────────────────────────────
@app.route("/tarama")
def tarama():
    return render_template("tarama.html")


@app.route("/api/tarama")
@limiter.limit("60 per minute")
def api_tarama():
    """Hisse tarayıcısı — sinyal, ADX, fiyat, hacim, sektör filtresi."""
    sig      = request.args.get("signal",    "")
    min_adx  = float(request.args.get("min_adx",   0))
    min_p    = float(request.args.get("min_price", 0))
    max_p    = float(request.args.get("max_price", 999999))
    sector   = request.args.get("sector",    "")
    eq       = request.args.get("eq",        "")   # IDEAL | IYI | DIKKATLI | UZAK
    sort_by  = request.args.get("sort",      "adx")

    with _lock:
        stocks = list(_cache["data"])
        upd    = _cache.get("updated_at", "")

    def _parse_adx(s):
        """ADX değerini indicators.adx.label'dan çıkar ('ADX 26' → 26.0)."""
        inds = s.get("indicators") or {}
        adx_ind = inds.get("adx") or {}
        label = adx_ind.get("label", "")  # "ADX 26"
        try:
            return float(label.split()[-1])
        except (ValueError, IndexError):
            return 0.0

    results = []
    for s in stocks:
        if s.get("ticker") in ("XU030", "XU100"): continue
        if sig    and s.get("signal")              != sig:    continue
        if sector and _get_sector(s.get("ticker","")) != sector: continue
        if eq     and s.get("entry_quality")       != eq:    continue
        price = s.get("price")  or 0
        adx   = _parse_adx(s)
        if price < min_p or price > max_p: continue
        if adx < min_adx: continue
        results.append({
            "ticker":        s.get("ticker"),
            "name":          STOCK_NAMES.get(s.get("ticker",""), s.get("ticker","")),
            "sector":        _get_sector(s.get("ticker","")),
            "signal":        s.get("signal",""),
            "price":         price,
            "change_pct":    s.get("change_pct") or 0,
            "adx":           adx,
            "signal_bars":   s.get("signal_bars") or 1,
            "entry_quality": s.get("entry_quality",""),
            "vol_ratio":     s.get("vol_ratio") or 1.0,
            "bull_score":    s.get("bull_score") or 0,
            "sl_level":      s.get("sl_level"),
        })

    rev = sort_by in ("adx","price","signal_bars","vol_ratio","bull_score","change_pct")
    results.sort(key=lambda x: (x.get(sort_by) or 0), reverse=rev)

    with _lock:
        sectors = sorted(set(_get_sector(s.get("ticker","")) for s in _cache["data"]
                             if s.get("ticker") not in ("XU030","XU100")))

    return jsonify({"results": results, "sectors": sectors,
                    "count": len(results), "updated_at": upd})


# ── SEO: sitemap, robots, favicon ────────────────────────────────────────────
@app.route("/sitemap.xml")
def sitemap():
    pages = [
        {"loc": "/",            "priority": "1.0", "changefreq": "hourly"},
        {"loc": "/ozet",        "priority": "0.9", "changefreq": "daily"},
        {"loc": "/tarama",      "priority": "0.8", "changefreq": "daily"},
        {"loc": "/gucu-yuksek", "priority": "0.8", "changefreq": "daily"},
        {"loc": "/metodoloji",  "priority": "0.7", "changefreq": "monthly"},
        {"loc": "/hakkinda",    "priority": "0.6", "changefreq": "monthly"},
        {"loc": "/gizlilik",    "priority": "0.3", "changefreq": "yearly"},
        {"loc": "/iletisim",    "priority": "0.4", "changefreq": "yearly"},
        {"loc": "/btc",         "priority": "0.8", "changefreq": "daily"},
        {"loc": "/altin",       "priority": "0.8", "changefreq": "daily"},
        {"loc": "/gumus",       "priority": "0.7", "changefreq": "daily"},
        {"loc": "/eth",             "priority": "0.8", "changefreq": "daily"},
        {"loc": "/kripto",          "priority": "0.8", "changefreq": "daily"},
        {"loc": "/emtialar",        "priority": "0.8", "changefreq": "daily"},
        {"loc": "/abd",             "priority": "0.8", "changefreq": "daily"},
        {"loc": "/abd/sp500",       "priority": "0.8", "changefreq": "daily"},
        {"loc": "/abd/nasdaq",      "priority": "0.8", "changefreq": "daily"},
        {"loc": "/sol",             "priority": "0.8", "changefreq": "daily"},
        {"loc": "/bnb",             "priority": "0.8", "changefreq": "daily"},
        {"loc": "/petrol",          "priority": "0.8", "changefreq": "daily"},
        {"loc": "/dogalgaz",        "priority": "0.7", "changefreq": "daily"},
        {"loc": "/abd/tarama",      "priority": "0.7", "changefreq": "daily"},
    ]
    for t in US_STOCKS:
        pages.append({"loc": f"/abd/{t}", "priority": "0.7", "changefreq": "daily"})
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
  <text x="60" y="165" font-size="26" fill="#8b949e">borsapusula.com · Algoritmik Trend Sinyalleri · {today_s}</text>
  <!-- Ayırıcı çizgi -->
  <line x1="60" y1="195" x2="1140" y2="195" stroke="#30363d" stroke-width="1"/>
  <!-- İstatistik kutular -->
  <rect x="60"  y="230" width="280" height="160" rx="12" fill="#161b22" stroke="#30363d" stroke-width="1"/>
  <text x="200" y="305" font-size="72" font-weight="800" fill="#3fb950" text-anchor="middle">{al_count}</text>
  <text x="200" y="355" font-size="22" fill="#8b949e" text-anchor="middle">▲ GÜÇLÜ TREND</text>
  <rect x="380" y="230" width="280" height="160" rx="12" fill="#161b22" stroke="#30363d" stroke-width="1"/>
  <text x="520" y="305" font-size="72" font-weight="800" fill="#f85149" text-anchor="middle">{sat_count}</text>
  <text x="520" y="355" font-size="22" fill="#8b949e" text-anchor="middle">▼ ZAYIF TREND</text>
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


# ── Güçlü Momentum Listesi ────────────────────────────────────────────────────
@app.route("/gucu-yuksek")
def gucu_yuksek():
    """En güçlü momentum sinyallerini göster (ADX + hacim + bull_score kompozit skoru)."""
    with _lock:
        stocks = list(_cache["data"])
        updated_at = _cache.get("updated_at", "")
        loading = len(stocks) == 0

    # Sadece AL/SAT sinyallerini al; kompozit skor hesapla
    def momentum_score(s):
        adx = s.get("adx") or 0
        try:
            adx = float(str(adx).replace(",", "."))
        except Exception:
            adx = 0
        vr   = s.get("vol_ratio") or 1.0
        bs   = s.get("bull_score") if s.get("signal") == "AL" else (s.get("bear_score") or 0)
        bs   = bs or 0
        conf = 10 if s.get("confirmed") else 0
        rsi  = s.get("rsi") or 50
        rsi_pts = 10 if 50 <= rsi <= 75 else (5 if rsi > 75 else 0)
        return round(
            min(adx, 50) / 50 * 30 +
            min(vr, 5) / 5 * 25 +
            bs / 3 * 25 +
            conf +
            rsi_pts
        )

    active = [s for s in stocks if s.get("signal") in ("AL", "SAT") and s.get("ticker") != "XU030"]
    for s in active:
        s["_mscore"] = momentum_score(s)
    active.sort(key=lambda s: s["_mscore"], reverse=True)

    today_str = date.today().strftime("%d.%m.%Y")
    return render_template("gucu_yuksek.html",
        stocks=active, loading=loading, updated_at=updated_at,
        today_str=today_str, stock_names=STOCK_NAMES)


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


@app.route("/api/contact", methods=["POST"])
@limiter.limit("3 per hour")
def api_contact():
    data    = request.get_json(silent=True) or {}
    name    = str(data.get("name",    "")).strip()[:100]
    email   = str(data.get("email",   "")).strip()[:200]
    subject = str(data.get("subject", "")).strip()[:200]
    message = str(data.get("message", "")).strip()[:2000]

    if not all([name, email, message]):
        return jsonify({"ok": False, "error": "Eksik alan"}), 400
    if "@" not in email or "." not in email:
        return jsonify({"ok": False, "error": "Geçersiz e-posta"}), 400

    SMTP_HOST  = os.environ.get("SMTP_HOST", "")
    SMTP_USER  = os.environ.get("SMTP_USER", "")
    SMTP_PASS  = os.environ.get("SMTP_PASS", "")
    ADMIN_MAIL = os.environ.get("ADMIN_MAIL", "iletisim@borsapusula.com")

    if SMTP_HOST and SMTP_USER:
        try:
            msg = MIMEMultipart()
            msg["From"]    = SMTP_USER
            msg["To"]      = ADMIN_MAIL
            msg["Subject"] = f"[BorsaPusula İletişim] {subject}"
            body = f"Gönderen: {name} <{email}>\nKonu: {subject}\n\n{message}"
            msg.attach(MIMEText(body, "plain", "utf-8"))
            with smtplib.SMTP_SSL(SMTP_HOST, 465) as s:
                s.login(SMTP_USER, SMTP_PASS)
                s.sendmail(SMTP_USER, ADMIN_MAIL, msg.as_string())
            logger.info("Contact mail gönderildi: %s <%s>", name, email)
        except Exception as ex:
            logger.error("Contact mail hatası: %s", ex)
            return jsonify({"ok": False, "error": "Mail gönderilemedi"}), 500

    return jsonify({"ok": True})


@app.route("/yasal")
def yasal():
    return render_template("yasal.html")


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
                duration_bars = exit_i - entry_i
                episodes.append({
                    "sig":           sig,
                    "date":          close.index[entry_i].strftime("%d.%m.%Y"),
                    "entry_price":   round(entry_price, 2),
                    "exit_price":    round(exit_price, 2),
                    "bars":          duration_bars,
                    "duration_days": duration_bars,  # günlük bar = işlem günü
                    "ret_pct":       round(ret_pct, 2),
                    "win":           (ret_pct > 0 and sig == "AL") or (ret_pct < 0 and sig == "SAT"),
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
        if not eps: return {
            "count": 0, "win_rate": 0, "avg_ret": 0, "best": 0, "worst": 0,
            "sharpe": None, "max_drawdown": None, "profit_factor": None,
            "avg_duration_days": None,
        }
        wins = [e for e in eps if e["win"]]
        rets = [e["ret_pct"] for e in eps]
        avg  = sum(rets) / len(rets)
        std  = (sum((r - avg) ** 2 for r in rets) / len(rets)) ** 0.5

        # Sharpe (günlük getiri % → yıllık ölçekle; her işlem ~bağımsız)
        sharpe = round(avg / std * (len(rets) ** 0.5), 2) if std > 0 else None

        # Kümülatif max drawdown
        cum   = 100.0
        peak  = 100.0
        max_dd = 0.0
        for r in rets:
            cum  *= (1 + r / 100)
            peak  = max(peak, cum)
            dd    = (cum - peak) / peak * 100
            max_dd = min(max_dd, dd)

        # Profit factor = brüt kazanç / brüt kayıp
        gross_win  = sum(r for r in rets if r > 0)
        gross_loss = abs(sum(r for r in rets if r < 0))
        pf = round(gross_win / gross_loss, 2) if gross_loss > 0 else None

        # Ortalama işlem süresi
        durations = [e.get("duration_days") for e in eps if e.get("duration_days") is not None]
        avg_dur   = round(sum(durations) / len(durations), 1) if durations else None

        return {
            "count":             len(eps),
            "win_rate":          round(len(wins) / len(eps) * 100, 1),
            "avg_ret":           round(avg, 2),
            "best":              round(max(rets), 2),
            "worst":             round(min(rets), 2),
            "sharpe":            sharpe,
            "max_drawdown":      round(max_dd, 2),
            "profit_factor":     pf,
            "avg_duration_days": avg_dur,
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
@limiter.limit("1 per 30 minutes")
def api_backtest_run():
    if ADMIN_SECRET and request.headers.get("X-Admin-Secret") != ADMIN_SECRET:
        abort(403)
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


@app.route("/api/bilanco-mini")
@limiter.limit("60 per minute")
def api_bilanco_mini():
    """Ana sayfa mini bilanço widget — yfinance çağrısı yok, sadece dönem bilgisi."""
    today_dt  = date.today()
    today_str = today_dt.isoformat()
    items     = []
    for qlabel, start, end, desc in _BILANCO_PERIODS:
        if end < today_str:
            continue
        start_dt      = date.fromisoformat(start)
        end_dt        = date.fromisoformat(end)
        days_to_end   = (end_dt   - today_dt).days
        days_to_start = (start_dt - today_dt).days
        if today_dt >= start_dt:
            status     = "active"
            days_label = f"{days_to_end} gün kaldı"
        else:
            status     = "upcoming"
            days_label = f"{days_to_start} gün sonra"
        items.append({
            "label":      qlabel,
            "start":      start,
            "end":        end,
            "desc":       desc,
            "status":     status,
            "days_label": days_label,
        })
        if len(items) >= 3:
            break
    return safe_json({"periods": items})


@app.route("/api/market-news")
@limiter.limit("30 per minute")
def api_market_news():
    """Ana sayfa Gündem kutusu için öne çıkan hisse haberleri.

    Sadece mevcut cache'leri okur — Gemini'ye yeni çağrı yapmaz.
    AL sinyalli top hisseler için news veya sinyal açıklamasını döner.
    Haber yoksa algoritmik fallback metin kullanılır.
    """
    with _lock:
        stocks = list(_cache["data"])

    # Top 5 AL + top 2 SAT (endeks hisseleri hariç)
    al_stocks  = [s for s in stocks
                  if s.get("signal") == "AL"
                  and s.get("ticker") not in ("XU030", "XU100")][:5]
    sat_stocks = [s for s in stocks
                  if s.get("signal") == "SAT"
                  and s.get("ticker") not in ("XU030", "XU100")][:2]
    candidates = al_stocks + sat_stocks

    results = []
    for s in candidates:
        t      = s["ticker"]
        name   = STOCK_NAMES.get(t, t)
        sig    = s.get("signal", "BEKLE")
        price  = s.get("price", 0) or 0
        chg    = s.get("change_pct", 0) or 0
        bars   = s.get("signal_bars", 1) or 1

        # ── Metin kaynağı önceliği: haber > sinyal açıklaması > algoritma ──
        with _lock:
            news_c = _news_cache.get(t)
            expl_c = _signal_explain_cache.get(t)

        text   = None
        source = "algorithmic"

        if news_c and not news_c.get("failed") and news_c.get("text"):
            text   = news_c["text"]
            source = "news"
        elif expl_c and expl_c.get("text") and not expl_c.get("failed"):
            text   = expl_c["text"]
            source = "explanation"

        if not text:
            # Haber cache yok → on-demand kuyruğuna ekle (eğer başarısız cache yoksa)
            failed_recently = news_c and news_c.get("failed") and \
                              (time.time() - news_c.get("ts", 0)) < _NEWS_FAIL_TTL
            if not failed_recently:
                with _news_queue_lock:
                    _news_fetch_queue.add(t)

            # Algoritmik fallback metin (kaynak = "loading" — frontend polling tetikler)
            dur = "bugün" if bars <= 1 else f"son {bars} gündür"
            if sig == "AL":
                text = (f"{name} hissesinde {dur} Güçlü Trend sinyali aktif. "
                        "Supertrend, ADX ve EMA göstergelerinin tamamı yükseliş yönünü destekliyor.")
                source = "loading"
            elif sig == "SAT":
                text = (f"{name} hissesinde {dur} Zayıf Trend sinyali aktif. "
                        "Teknik göstergeler düşüş yönünü işaret ediyor.")
                source = "loading"
            else:
                continue   # BEKLE hisselerini listeye alma

        # Snippet: gereksiz giriş cümlelerini temizle, 200 karakter kes
        _skip_prefixes = (
            "aşağıda", "işte", "here are", "here is", "below are",
            "son 7 gün", "son yedi gün", "belirtmek gerekir",
        )
        lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
        # İlk satır boş veya haber maddesine benzemeyen giriş ise atla
        if lines and any(lines[0].lower().startswith(p) for p in _skip_prefixes):
            lines = lines[1:]
        clean = " ".join(lines).strip()
        snippet = clean if len(clean) <= 220 else clean[:220].rsplit(" ", 1)[0] + "…"

        results.append({
            "ticker":      t,
            "name":        name,
            "signal":      sig,
            "price":       round(price, 2),
            "change_pct":  round(chg, 2),
            "snippet":     snippet,
            "source":      source,
            "signal_date": s.get("signal_date", ""),
            "signal_bars": bars,
            "sector":      _get_sector(t),
            "sl_level":    s.get("sl_level"),
        })

        if len(results) >= 5:
            break

    has_loading = any(r.get("source") == "loading" for r in results)
    now = datetime.now()
    return safe_json({
        "items":       results,
        "updated_at":  now.strftime("%d.%m.%Y %H:%M"),
        "count":       len(results),
        "has_loading": has_loading,   # True → frontend 30s sonra yenile
    })


@app.route("/api/subscribe", methods=["POST"])
@limiter.limit("5 per hour")
def api_subscribe():
    """E-posta abonelik kaydı."""
    data  = request.get_json(silent=True) or {}
    email = (data.get("email") or "").strip().lower()
    # Basit e-posta doğrulama
    if not email or "@" not in email or not re.match(r'^[^@]+@[^@]+\.[^@]+$', email):
        return safe_json({"ok": False, "error": "Geçersiz e-posta adresi"}), 400

    with _sub_lock:
        subs = _load_subscribers()
        if email in subs:
            if subs[email].get("active", True):
                return safe_json({"ok": False, "message": "Bu e-posta zaten kayıtlı."})
            # Pasif abonenin kaydını yeniden aktif et
            subs[email]["active"] = True
            subs[email]["subscribed_at"] = datetime.now().isoformat()
            _save_subscribers(subs)
            token = subs[email].get("token", "")
            unsub = f"https://borsapusula.com/unsubscribe/{token}"
            threading.Thread(target=send_email, args=(
                email, "✅ BorsaPusula — Abonelik Yenilendi",
                _build_welcome_email(email, unsub)
            ), daemon=True).start()
            return safe_json({"ok": True, "message": "Aboneliğiniz yeniden aktif edildi!"})

        token = secrets.token_hex(24)
        subs[email] = {
            "token":         token,
            "subscribed_at": datetime.now().isoformat(),
            "tickers":       [],
            "active":        True,
        }
        _save_subscribers(subs)

    unsub = f"https://borsapusula.com/unsubscribe/{token}"
    threading.Thread(target=send_email, args=(
        email, "✅ BorsaPusula — Abonelik Onayı",
        _build_welcome_email(email, unsub)
    ), daemon=True).start()

    logger.info("Yeni e-posta abonesi: %s", email)
    return safe_json({"ok": True, "message": "Abonelik başarılı! Onay e-postası gönderildi."})


@app.route("/unsubscribe/<token>")
def unsubscribe_page(token):
    """Tek tıkla abonelik iptali."""
    with _sub_lock:
        subs = _load_subscribers()
        for email, data in subs.items():
            if data.get("token") == token:
                subs[email]["active"] = False
                _save_subscribers(subs)
                logger.info("E-posta abonelik iptal: %s", email)
                return f"""<!DOCTYPE html>
<html lang="tr">
<head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>Abonelik İptal — BorsaPusula</title>
<style>body{{margin:0;padding:0;background:#0b111f;color:#e2e8f0;
font-family:-apple-system,BlinkMacSystemFont,'Inter',Arial,sans-serif;
display:flex;align-items:center;justify-content:center;min-height:100vh}}
.box{{background:#111827;border:1px solid #1e2d45;border-radius:12px;
padding:32px 40px;text-align:center;max-width:420px}}</style>
</head>
<body>
<div class="box">
  <div style="font-size:40px;margin-bottom:16px">✅</div>
  <h2 style="font-size:18px;margin:0 0 8px;font-weight:700">Abonelik İptal Edildi</h2>
  <p style="font-size:13px;color:#94a3b8;margin:0 0 20px;line-height:1.6">
    <strong style="color:#e2e8f0">{email}</strong> adresi için bildirimler durduruldu.
  </p>
  <a href="https://borsapusula.com" style="display:inline-block;background:#1f6feb;
  color:#fff;padding:9px 22px;border-radius:8px;text-decoration:none;font-size:13px;font-weight:600">
    Ana Sayfaya Dön
  </a>
</div>
</body></html>"""
    return "<p style='font-family:sans-serif;color:#888;padding:40px'>Geçersiz veya süresi dolmuş bağlantı.</p>", 404


@app.route("/api/telegram/test", methods=["POST"])
@limiter.limit("5 per hour")
def api_telegram_test():
    """Admin: Telegram bağlantısını test et."""
    if ADMIN_SECRET and request.headers.get("X-Admin-Secret") != ADMIN_SECRET:
        abort(403)
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


# Eski / kısa slug'lar → doğru slug 301 yönlendirme tablosu
_BLOG_SLUG_REDIRECTS = {
    "supertrend-nedir":              "supertrend-indikatoru-nedir",
    "supertrend":                    "supertrend-indikatoru-nedir",
    "adx-nedir":                     "adx-indikatoru-nedir",
    "ema-nedir":                     "ema-nedir-nasil-hesaplanir",
    "rsi-nedir":                     "rsi-gosterge-analizi",
    "bist30-nedir":                  "bist100-nedir",
    "supertrend-vs-macd-karsilastirma": "supertrend-vs-macd",
}

@app.route("/blog/<slug>")
def blog_article(slug):
    from flask import abort, redirect, url_for
    # Bilinen eski slug → doğru slug 301 yönlendirme
    if slug in _BLOG_SLUG_REDIRECTS:
        return redirect(url_for("blog_article", slug=_BLOG_SLUG_REDIRECTS[slug]), code=301)
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
    # Disk cache'i yükle — anlık veri gelene kadar siteyi hemen dolduran eski veri
    _load_cache_from_disk()
    refresh_chart()
    # XU100 + makro varlıkları arka planda paralel yükle
    threading.Thread(target=refresh_xu100_chart, daemon=True).start()
    threading.Thread(target=_refresh_varlik_chart, args=("BTC",   _btc_chart_cache),   daemon=True).start()
    threading.Thread(target=_refresh_varlik_chart, args=("ALTIN", _altin_chart_cache), daemon=True).start()
    threading.Thread(target=_refresh_varlik_chart, args=("GUMUS", _gumus_chart_cache), daemon=True).start()
    threading.Thread(target=_refresh_varlik_chart, args=("ETH",    _eth_chart_cache),    daemon=True).start()
    threading.Thread(target=_refresh_varlik_chart, args=("SP500",  _sp500_chart_cache),  daemon=True).start()
    threading.Thread(target=_refresh_varlik_chart, args=("NASDAQ", _nasdaq_chart_cache), daemon=True).start()
    threading.Thread(target=_refresh_varlik_chart, args=("SOL",      _sol_chart_cache),      daemon=True).start()
    threading.Thread(target=_refresh_varlik_chart, args=("BNB",      _bnb_chart_cache),      daemon=True).start()
    threading.Thread(target=_refresh_varlik_chart, args=("PETROL",   _petrol_chart_cache),   daemon=True).start()
    threading.Thread(target=_refresh_varlik_chart, args=("DOGALGAZ", _dogalgaz_chart_cache), daemon=True).start()
    time.sleep(3)
    threading.Thread(target=background_refresh,        daemon=True).start()
    threading.Thread(target=background_live_prices,    daemon=True).start()
    threading.Thread(target=background_global_prices,  daemon=True).start()
    # Makro ticker'ları servis başlar başlamaz ilk kez çek (arka planda)
    def _warm_macro():
        items = _fetch_macro()
        with _lock:
            _macro_cache["data"] = items
            _macro_cache["ts"]   = time.time()
        logger.info("_warm_macro: %d sembol hazır", len(items))
    threading.Thread(target=_warm_macro, daemon=True).start()
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
