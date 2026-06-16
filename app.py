# ─── CRITICAL: gevent monkey-patch + socket timeout (worker hang prevention) ───
import sys as _sys
if 'gevent' in _sys.modules or any('gunicorn' in arg for arg in _sys.argv):
    try:
        from gevent import monkey
        if not monkey.is_module_patched('socket'):
            monkey.patch_all()
    except ImportError:
        pass
import socket as _socket
_socket.setdefaulttimeout(8)   # CPO-505: 20→8s (uzun yfinance hang -w4 satürasyon yapıyordu)

from flask import Flask, jsonify, render_template, Response, request, abort, redirect
import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime, date, timedelta, timezone

# Türkiye saati: UTC+3, DST yok (2016'dan beri sabit)
_TZ_TR = timezone(timedelta(hours=3))
import threading
import collections
import logging
import time
import json
import os
import tempfile
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

# ── Web Push (VAPID) — opsiyonel; eksikse özellik devre dışı ──────────────────
try:
    from pywebpush import webpush, WebPushException
    _PUSH_ENABLED = True
except ImportError:
    _PUSH_ENABLED = False

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
ADMIN_SECRET = os.environ.get("ADMIN_SECRET", "").strip()
# MSG-019B: admin endpoint token (mail credential ile decoupled — least privilege)
ADMIN_TOKEN  = os.environ.get("ADMIN_TOKEN",  "")

def require_admin():
    """Bulgu 5 (danışman audit) fix: ADMIN_SECRET boşsa endpoint KAPALI (503).
    Eski 'if ADMIN_SECRET and ...' pattern secret boşken endpoint'i korumasız bırakıyordu."""
    from flask import abort as _abort
    if not ADMIN_SECRET:
        _abort(503)  # secret yapılandırılmamış → endpoint devre dışı (fail-closed)
    if request.headers.get("X-Admin-Secret", "") != ADMIN_SECRET:
        _abort(403)

# ── VAPID Web Push Bildirimleri ───────────────────────────────────────────────
_APP_DIR        = os.path.dirname(os.path.abspath(__file__))
VAPID_PUBLIC    = os.environ.get("VAPID_PUBLIC", "")
VAPID_PRIV_PATH = os.environ.get(
    "VAPID_PRIVATE_PATH",
    os.path.join(_APP_DIR, "vapid_private.pem")
)
VAPID_CLAIMS    = {"sub": "mailto:hello@borsapusula.com"}

# Auto-load VAPID public key from file if env var not set
if not VAPID_PUBLIC and os.path.exists(os.path.join(_APP_DIR, "vapid_public.txt")):
    try:
        with open(os.path.join(_APP_DIR, "vapid_public.txt")) as _f:
            VAPID_PUBLIC = _f.read().strip()
    except Exception:
        pass

# Push subscriber storage
_PUSH_SUBS_FILE = os.path.join(_APP_DIR, "push_subs.json")
_push_subs: list = []
_push_lock = threading.Lock()
_YF_GLOBAL_LOCK = threading.Lock()  # CPO-592: tüm yf.download/Ticker çağrılarını serialize — global state contamination fix


def _load_push_subs():
    global _push_subs
    try:
        if os.path.exists(_PUSH_SUBS_FILE):
            with open(_PUSH_SUBS_FILE, encoding="utf-8") as f:
                _push_subs = json.load(f)
            logger = logging.getLogger(__name__)
            logger.info("Push subscribers yüklendi: %d", len(_push_subs))
    except Exception as e:
        pass  # logger not yet set up at import time


def _save_push_subs_locked():
    """Must be called while holding _push_lock."""
    try:
        with open(_PUSH_SUBS_FILE, "w", encoding="utf-8") as f:
            json.dump(_push_subs, f)
    except Exception:
        pass


def _send_one_push(sub_info: dict, payload: str) -> bool | None:
    """Tek subscriber'a push gönder. False=expired, True=ok, None=error."""
    if not _PUSH_ENABLED:
        return None
    try:
        webpush(
            subscription_info=sub_info,
            data=payload,
            vapid_private_key=VAPID_PRIV_PATH,
            vapid_claims=VAPID_CLAIMS,
        )
        return True
    except Exception as exc:
        s = str(exc)
        if "410" in s or "404" in s or "unsubscribed" in s.lower():
            return False     # Expired subscription
        return None          # Transient error


_PUSH_RATELIMIT_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "push_state.json")

def _can_send_push(endpoint_key, ticker):
    """SPEC-006 Faz 3 (CPO MSG-106): Push rate limit.
    - Hisse başına 24h içinde max 1 push
    - Kullanıcı başına saatlik max 3 push
    File-based state (push_state.json) + fcntl lock. True → gönderilebilir (state tüketilir).
    Hata durumunda fail-open (True) — rate limit dosya sorunu push'u tamamen kesmesin."""
    import fcntl
    try:
        now  = time.time()
        hour = int(now / 3600)
        with open(_PUSH_RATELIMIT_PATH, "a+") as f:
            fcntl.flock(f, fcntl.LOCK_EX)
            f.seek(0)
            raw   = f.read()
            state = json.loads(raw) if raw.strip() else {}

            tkey = f"{endpoint_key}:{ticker}"
            if now - state.get(tkey, 0) < 86400:
                return False   # aynı hisse 24h içinde zaten gönderilmiş
            hkey = f"{endpoint_key}:h:{hour}"
            if state.get(hkey, 0) >= 3:
                return False   # saatlik global limit (3) doldu

            state[tkey] = now
            state[hkey] = state.get(hkey, 0) + 1
            # Eski saat anahtarlarını temizle (dosya şişmesini önle)
            state = {k: v for k, v in state.items()
                     if not (":h:" in k and k.rsplit(":", 1)[-1].isdigit()
                             and int(k.rsplit(":", 1)[-1]) < hour - 1)}
            f.seek(0); f.truncate()
            json.dump(state, f)
        return True
    except Exception:
        return True   # fail-open


def _broadcast_push_changes(changes):
    """SPEC-006 Faz 2 (CPO MSG-095): Watchlist-aware push.
    Her subscriber'a SADECE izlediği ticker'ların sinyal değişimi gönderilir.
    watchlist boş/eksik subscriber → tüm değişimleri alır (backward compat — eski user).
    changes: [(ticker, old_sig, new_sig, stock_data), ...]"""
    if not _PUSH_ENABLED or not VAPID_PUBLIC or not os.path.exists(VAPID_PRIV_PATH):
        return
    with _push_lock:
        subs_snap = list(_push_subs)
    if not subs_snap or not changes:
        return

    keep = []
    sent = 0
    for sub in subs_snap:
        wl = sub.get("watchlist") or []
        # watchlist varsa filtrele, yoksa tüm değişimler (backward compat)
        relevant = [c for c in changes if c[0] in wl] if wl else list(changes)
        if not relevant:
            keep.append(sub)
            continue

        # SPEC-006 Faz 3: rate limit — hisse başına 24h max 1, saatlik global max 3
        _ep_key  = (sub.get("endpoint") or "")[-40:]
        relevant = [c for c in relevant if _can_send_push(_ep_key, c[0])]
        if not relevant:
            keep.append(sub)
            continue

        if len(relevant) == 1:
            t, old, new, _stock = relevant[0]
            name = STOCK_NAMES.get(t, t)
            lbl  = "AL ▲ Güçlü Trend" if new == "AL" else "SAT ▼ Zayıf Trend"
            title = f"{t} — {lbl}"
            body  = f"{name} sinyali değişti: {old} → {new}"
            url   = f"/hisse/{t}"
        else:
            tickers_str = ", ".join(c[0] for c in relevant[:3])
            title = f"Sinyal Değişimi: {tickers_str}"
            body  = f"{len(relevant)} hissede sinyal değişti"
            url   = "/"

        payload = json.dumps({
            "title": title,
            "body": body,
            "url": url,
            "tag": "borsapusula-signal",
            "icon": "/static/icon-192.png",
        })
        result = _send_one_push(sub, payload)
        if result is not False:
            keep.append(sub)
        if result is True:
            sent += 1

    removed = len(subs_snap) - len(keep)
    if removed > 0:
        with _push_lock:
            _push_subs[:] = keep
            _save_push_subs_locked()

    logging.getLogger(__name__).info(
        "Push broadcast (watchlist-aware): %d sent, %d expired removed", sent, removed
    )

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

# Delisted/merged BIST hisseleri - 410 Gone
DELISTED_TICKERS = {
    "ANACM",  # Anadolu Cam - 2020 Sisecam birlesmesi
}

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
    "AYCES", "BIOEN", "BOSSA", "CEMTS",
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
    # ── Faz 2: Yıldız Pazar genişlemesi (>=200M TL/gün, 2026-05-07) ─
    "ASTOR", "PEKGY", "PASEU", "MIATK", "CANTE",
    "KLRHO", "PSGYO", "QUAGR", "IZENR", "EUREN",
    "ALKLC", "YEOTK", "BINHO", "FZLGY", "SKBNK",
    "MAGEN", "SURGY", "ESEN", "REEDR", "ALTNY",
    "ENERY", "BTCIM", "SDTTR", "BURCE", "TUKAS",
    "MARTI", "FONET", "AGROT", "MRGYO", "TUREX",
    "LILAK", "TCKRC", "PENGD", "PAPIL", "AYGAZ",
    "TSKB", "FORTE", "AKFYE", "TEKTU", "LMKDC",
    "ECZYT", "ARENA", "USAK", "MARKA", "BERA",
    "LINK", "MERCN", "ARDYZ", "KZBGY", "GMTAS",
    "AHGAZ",
    # ── 125M cutoff genişleme (2026-05-07) ──
    "KAREL", "ARZUM", "AKCNS", "MERKO", "KARSN",
    "POLHO", "TABGD", "GENTS", "ANELE", "HATSN",
    "SMART", "PKART", "AYEN", "EDATA", "TMSN",
    "AYDEM", "SNGYO", "YESIL", "LRSHO", "DERHL",
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
    "AYCES": "Altınyunus Çeşme Turistik",
    "BASGZ": "Başkent Doğalgaz GMYO",
    "BIOEN": "Biotrend Çevre",
    "BOSSA": "Bossa Ticaret ve Sanayi",
    "CEMTS": "Çemtaş Çelik Makine",
    "CEMAS": "Çemaş Döküm Sanayi",
    "CLEBI": "Çelebi Hava Servisi",
    "CRDFA": "Creditwest Faktoring",
    "DENGE": "Denge Yatırım Holding",
    "DNISI": "Dinamik Isı Makina",
    "DOBUR": "Doğuş Otomotiv Servis",
    "DOGUB": "Doğusan Boru",
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
    "FMIZP": "Federal-Mogul İzmit Piston",
    "FORMT": "Formet Metal ve Cam",
    "GESAN": "Gersan Elektrik Ticaret",
    "GSDHO": "GSD Holding",
    "GSRAY": "Galatasaray Sportif",
    "GOKNR": "Göknur Gıda",
    "HDFGS": "Hedef Girişim Sermayesi",
    "HLGYO": "Halk GYO",
    "HTTBT": "Hitit Bilgisayar",
    "IEYHO": "İEYHO İnşaat",
    "IPMAT": "İpek Matbaacılık",
    "ISKPL": "Işık Plastik",
    "ISFIN": "İş Finansal Kiralama",
    "KAPLM": "Kaplamin Ambalaj",
    "KATMR": "Katmerciler Araç Üstü",
    "KERVT": "Kervansaray Yatırım",
    "KMPUR": "Kimteks Poliüretan",
    "KONYA": "Konya Çimento",
    "KRSTL": "Kristal Kola",
    "LKMNH": "Lokman Hekim",
    "LUKSK": "Lüks Kadife",
    "MAKTK": "Makina Takım Endüstrisi",
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
    # Faz 2 genişleme
    "ASTOR":  "Astor Enerji",
    "PEKGY":  "Peker GMYO",
    "PASEU":  "Paşabahçe Cam",
    "MIATK":  "Mia Teknoloji",
    "CANTE":  "Çan2 Termik",
    "KLRHO":  "Kiler Holding",
    "PSGYO":  "Pera GMYO",
    "QUAGR":  "Qua Granite",
    "IZENR":  "İzdemir Enerji",
    "EUREN":  "Eurasia Eurobond",
    "ALKLC":  "Alkaloid Sağlık",
    "YEOTK":  "YEO Teknoloji",
    "BINHO":  "Binbir Holding",
    "FZLGY":  "Fuzul GMYO",
    "SKBNK":  "Şekerbank",
    "MAGEN":  "Margün Enerji",
    "SURGY":  "Sur GMYO",
    "ESEN":  "Esenboğa Elektrik",
    "REEDR":  "Reeder Teknoloji",
    "ALTNY":  "Altınay Savunma",
    "ENERY":  "Enerya Enerji",
    "BTCIM":  "Batıçim Çimento",
    "SDTTR":  "SDT Uzay ve Savunma",
    "BURCE":  "Burçelik Vana",
    "TUKAS":  "Tukaş Gıda",
    "MARTI":  "Martı Otel",
    "FONET":  "Fonet Bilgi Tek.",
    "AGROT":  "Agrotech Yüksek Tek.",
    "MRGYO":  "Marbaş GMYO",
    "TUREX":  "Türk Tuborg",
    "LILAK":  "Lila Kağıt",
    "TCKRC":  "Türk Tuborg Cyt.",
    "PENGD":  "Penguen Gıda",
    "PAPIL":  "Papilon Savunma",
    "AYGAZ":  "Aygaz",
    "TSKB":  "Türkiye Sınai Kalkınma Bankası",
    "FORTE":  "Forte Bilgi İletişim",
    "AKFYE":  "Akfen Yenilenebilir Enerji",
    "TEKTU":  "Tek-Art İnşaat",
    "LMKDC":  "Limak Doğu Anadolu Çimento",
    "ECZYT":  "Eczacıbaşı Yatırım",
    "ARENA":  "Arena Bilgisayar",
    "USAK":  "Uşak Seramik",
    "MARKA":  "Marka Yatırım",
    "BERA":  "Bera Holding",
    "LINK":  "Link Bilgisayar",
    "MERCN":  "Mercan Kimya",
    "ARDYZ":  "Ard Bilgi Tek.",
    "KZBGY":  "Kızılbük GMYO",
    "GMTAS":  "Gümüş Madencilik",
    "AHGAZ":  "Ahlatcı Doğal Gaz",
    # 125M cutoff genişleme
    "KAREL":  "Karel Elektronik",
    "ARZUM":  "Arzum Küçük Ev Aletleri",
    "AKCNS":  "Akçansa Çimento",
    "MERKO":  "Merko Gıda",
    "KARSN":  "Karsan Otomotiv",
    "POLHO":  "Polisan Holding",
    "TABGD":  "Taze Beyaz Gıda",
    "GENTS":  "Genel Mobilya",
    "ANELE":  "Anel Elektrik",
    "HATSN":  "Hateks",
    "SMART":  "Smart Solar Tek.",
    "PKART":  "Plastikkart",
    "AYEN":  "Ayen Enerji",
    "EDATA":  "E-Data Teknoloji",
    "TMSN":  "Tümosan Motor",
    "AYDEM":  "Aydem Enerji",
    "SNGYO":  "Sinpaş GMYO",
    "YESIL":  "Yeşil GMYO",
    "LRSHO":  "Liderfarma Holding",
    "DERHL":  "Derindere Holding",
}

# ── KAP (Kamuyu Aydınlatma Platformu) UUID OID eşleştirme ───────────────────
# Gerçek UUID'ler — KAP /tr/api/search/combined endpoint'inden alındı
KAP_UUID_OIDS = {
    "AKBNK": "4028e4a240e8d1830140e905edcd0006",
    "ARCLK": "4028e4a240e95dc90140ed55b43900cf",
    "ASELS": "4028e4a1413b7ef401413bc2251e0047",
    "BIMAS": "4028e4a140e95be70140ee1b7b030119",
    "EKGYO": "4028e4a2422d9a780142513cda5b232e",
    "EREGL": "4028e4a240e95dc90140ede4c12a0133",
    "FROTO": "4028e4a140f2ed71014106890fae0138",
    "GARAN": "4028e4a140f2ed720140f37cb2a601b7",
    "HEKTS": "4028e4a140ee35c00140ee5d194a0055",
    "ISCTR": "4028e4a140f2ed7201411682b0cb05c6",
    "KCHOL": "4028e4a140f2ed710140f2f4d6c70039",
    "KRDMD": "4028e4a140f2ed7201412ace3ada0707",
    "MGROS": "4028e4a141462df2014150162e1c3424",
    "ODAS":  "4028e4a2416e696c01416edd70713183",
    "OYAKC": "4028e4a140f2ed720140f32377aa016c",
    "PGSUS": "4028e4a2422d9a78014232e751bc22a4",
    "SAHOL": "4028e4a240ee37a90140ee50087e000b",
    "SASA":  "4028e4a240ee866c0140f20abd9500cc",
    "SISE":  "4028e4a140f2ed710140f385d5690102",
    "SOKM":  "4028e4a14184e9c9014198095f4442bf",
    "TAVHL": "4028e4a140f2ed720140f31195ef010e",
    "TCELL": "4028e4a1486ec80a0148c55510d71d31",
    "THYAO": "4028e4a140f2ed720140f376bebb01a7",
    "TKFEN": "4028e4a140f2ed720140f31367840112",
    "TOASO": "4028e4a140f2ed710140f328bed700a5",
    "TUPRS": "4028e4a140f2ed720140f37f139c01bc",
    "VAKBN": "4028e4a1415f4d9b01415fe3340f36e4",
    "YKBNK": "4028e4a240f2ef4c01412ae6d6630538",
    # BIST100 ek hisseler
    "HALKB": "1DE05DAA82C3073AE0530A4A622A2EBD",
    "ALBRK": "4028e4a240f2ef4c014106a1c5ef016d",
    "TTRAK": "4028e4a140f2ed720140f3790d6a01ad",
    "DOAS":  "4028e4a240e8d16e0140e951bf04007b",
    "ENKAI": "4028e4a240e95dc90140ed3883fe0093",
    "ULKER": "4028e4a14184e9c901419801438a422b",
    "CCOLA": "4028e4a140ee35c00140ee586bdd0034",
    "PETKM": "4028e4a240f2ef470141165c566a03e4",
    "LOGO":  "4028e4a14158e41e01415b41210a6e8c",
    "NETAS": "4028e4a240f2ef47014111d7df220232",
    "CIMSA": "4028e4a240ee866c0140f1f64bdb0014",
    "ALARK": "4028e4a241462fd80141500c738e36be",
    "AEFES": "4028e4a140e95bea0140ed2fde10009d",
    "VESTL": "4028e4a140f2ed7201412c2000c507db",
    "VESBE": "4028e4a140f2ed7201412c223c9707e6",
    "AKSA":  "4028e4a240f2ef470141175e189f0453",
    "AKSEN": "4028e4a241733d42014179341a147ddb",
    "DOHOL": "4028e4a141462df201414ff732983087",
    "OYAKC": "4028e4a140f2ed720140f32377aa016c",
    "BRSAN": "4028e4a140f2ed7201412ac9ca5d06e6",
    "KONTR": "8acae2c5745d76320174c4879b101cb2",
    "SARKY": "4028e4a140f2ed7101410294f924012d",
    "KCAER": "4028e4a2416f888d01416f9ea04a058f",
    "ISDMR": "4028e4a2416e696c01416ee8eb7b3770",
    "IZMDC": "4028e4a140f275550140f27e319401ca",
    "ISGYO": "4028e4a140f2ed7201412acbeb8b06f7",
    "MAVI":  "4028e4a141733b5101417ea9aae11fec",
    "OTKAR": "4028e4a140ee35c70140ee4316b3001d",
    "NTHOL": "4028e4a140f2ed7101412ba0829f034d",
    "GLYHO": "4028e4a140e95bea0140ee24416e0197",
    "PRKAB": "4028e4a240f2ef470141167b777b0437",
    "JANTS": "4028e4a240f2ef4c01413b1b57300719",
    "TATGD": "4028e4a140f2ed720140f31089aa010a",
    "ANSGR": "4028e4a140e95bea0140ed21b5c10078",
    "BUCIM": "4028e4a140ee35c00140ee41a5e4000f",
    "NUHCM": "4028e4a141558bdd014156053d9f04b2",
    "ECILC": "4028e4a1415f4d99014160034b683108",
}

# Runtime'da API'den çekilen UUID'ler için cache (disk'e yazılmaz)
_kap_uuid_runtime: dict = {}

def kap_url_for(ticker: str) -> str:
    """KAP şirket sayfası URL'si — doğrudan bildirimleri sayfasına yönlendirir."""
    uuid = KAP_UUID_OIDS.get(ticker) or _kap_uuid_runtime.get(ticker)
    if uuid:
        return f"https://www.kap.org.tr/tr/bildirim-sorgu?company={uuid}&year=&dcType=&isLate=&orderBy=date&orderDir=desc"
    return f"https://www.kap.org.tr/tr/bildirim-sorgu?q={ticker}"


def _get_kap_uuid(ticker: str) -> str | None:
    """Ticker için KAP UUID OID döner. Cache'de yoksa API'den çeker."""
    uuid = KAP_UUID_OIDS.get(ticker) or _kap_uuid_runtime.get(ticker)
    if uuid:
        return uuid
    # Bilinmeyen ticker — search API'den çek
    try:
        r = requests.post(
            "https://www.kap.org.tr/tr/api/search/combined",
            json={"keyword": ticker},
            headers={"User-Agent": "Mozilla/5.0", "Content-Type": "application/json"},
            timeout=8
        )
        for cat in r.json():
            if cat.get("category") == "companyOrFunds":
                items = cat.get("results", [])
                if items:
                    uuid = items[0]["memberOrFundOid"]
                    _kap_uuid_runtime[ticker] = uuid
                    return uuid
    except Exception:
        pass
    return None


# ── KAP bildirim cache ────────────────────────────────────────────────────────
_kap_cache: dict = {}          # {ticker: {"data": [...], "ts": float}}
_KAP_CACHE_TTL = 1800          # 30 dakika


def fetch_kap_disclosures(ticker: str, days: int = 90) -> list:
    """Ticker için son N günlük KAP bildirimlerini çeker (ODA + FR)."""
    uuid = _get_kap_uuid(ticker)
    if not uuid:
        return []

    H = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Content-Type": "application/json",
    }
    from_date = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
    to_date   = datetime.now(_TZ_TR).strftime("%Y-%m-%d")

    results = []
    for disc_class in ("ODA", "FR"):
        try:
            payload = {
                "fromDate": from_date,
                "toDate":   to_date,
                "disclosureClass": disc_class,
                "subjectList": [],
                "mkkMemberOidList": [uuid],
                "inactiveMkkMemberOidList": [],
                "bdkMemberOidList": [],
                "fromSrc": False,
                "disclosureIndexList": [],
            }
            r = requests.post(
                "https://www.kap.org.tr/tr/api/disclosure/members/byCriteria",
                json=payload, headers=H, timeout=12
            )
            if r.status_code == 200:
                items = r.json() or []
                for item in items:
                    results.append({
                        "date":    item.get("publishDate", ""),
                        "summary": item.get("summary", ""),
                        "subject": item.get("subject", ""),
                        "class":   disc_class,
                        "type":    item.get("disclosureType", ""),
                        "index":   item.get("disclosureIndex"),
                        "url":     f"https://www.kap.org.tr/tr/Bildirim/{item.get('disclosureIndex')}",
                        "late":    item.get("isLate", False),
                    })
        except Exception as e:
            logger.warning("fetch_kap_disclosures(%s, %s): %s", ticker, disc_class, e)

    # En yeni tarihe göre sırala
    def _parse_date(d):
        try:
            return datetime.strptime(d, "%d.%m.%Y %H:%M:%S")
        except Exception:
            return datetime.min
    results.sort(key=lambda x: _parse_date(x["date"]), reverse=True)
    return results

# ── Sektör sınıflandırması ────────────────────────────────────────────────────
SECTORS = {
    "Bankacılık":    ["AKBNK", "GARAN", "HALKB", "ISCTR", "VAKBN", "YKBNK",
                      "ALBRK", "KLNMA", "ISMEN", "ISFIN", "CRDFA", "SKBNK", "TSKB"],
    "Holding":       ["KCHOL", "SAHOL", "AGHOL", "ALARK", "DOHOL", "GLYHO",
                      "NTHOL", "TKFEN", "BRYAT", "GSDHO", "DENGE", "HDFGS",
                      "DOGUB", "DOBUR", "KLRHO", "BINHO", "ECZYT", "MARKA", "BERA", "POLHO", "LRSHO", "DERHL"],
    "Sanayi":        ["ARCLK", "ASELS", "EREGL", "FROTO", "KRDMD", "TOASO",
                      "ASUZU", "BRSAN", "DOAS",  "ISDMR", "IZMDC", "JANTS",
                      "KCAER", "KORDS", "OTKAR", "PARSN", "SARKY", "TTRAK",
                      "VESTL", "VESBE", "YATAS", "ARSAN", "BOSSA", "CEMTS",
                      "CEMAS", "EDIP",  "EMKEL", "ERBOS", "EGGUB", "EGPRO",
                      "GESAN", "KAPLM", "KATMR", "LKMNH", "LUKSK", "MAKTK",
                      "MUTLU", "NIBAS", "NUHCM", "PASEU", "QUAGR", "EUREN", "BURCE", "LILAK", "USAK", "GMTAS", "ALTNY", "SDTTR", "PAPIL", "BTCIM", "LMKDC", "TEKTU", "ARZUM", "AKCNS", "KARSN", "GENTS", "ANELE", "HATSN", "PKART", "TMSN"],
    "Enerji":        ["AKSEN", "ALFAS", "CWENE", "ENJSA", "ENKAI",
                      "EUPWR", "ODAS",  "PRKAB", "SMRTG", "TUPRS", "ZOREN",
                      "BASGZ", "BIOEN", "NATEN", "ORGE", "ASTOR", "CANTE", "IZENR", "MAGEN", "ESEN", "ENERY", "AYGAZ", "AKFYE", "AHGAZ", "SMART", "AYEN", "AYDEM"],
    "Perakende":     ["BIMAS", "MGROS", "SOKM",  "MAVI",  "SELEC", "ULKER",
                      "KRSTL", "TUKAS", "TUREX", "PENGD", "TCKRC", "MERKO", "TABGD"],
    "Teknoloji":     ["INDES", "LOGO",  "NETAS", "KONTR", "ESCOM", "MTRKS",
                      "HTTBT", "MPARK", "MIATK", "YEOTK", "REEDR", "FONET", "FORTE", "ARENA", "LINK", "ARDYZ", "KAREL", "EDATA"],
    "Telekom":       ["TCELL", "TTKOM"],
    "Ulaşım":        ["PGSUS", "TAVHL", "THYAO", "RYSAS", "CLEBI"],
    "GYO":           ["EKGYO", "ALGYO", "ISGYO", "AKMGY", "HLGYO", "BASGZ", "PEKGY", "PSGYO", "FZLGY", "SURGY", "MRGYO", "KZBGY", "SNGYO", "YESIL"],
    "Kimya/Malzeme": ["AKSA", "ALKIM", "ANACM", "ISKPL", "BUCIM", "CIMSA", "GUBRF", "HEKTS",
                      "OYAKC", "PETKM", "SASA",  "SISE",  "TATGD", "AEFES",
                      "CCOLA", "EGEEN", "DYOBY", "ERSU",  "KMPUR", "KONYA",
                      "MEGAP", "MIPAZ", "MRDIN", "NUHCM", "MERCN"],
    "Sigorta":       ["ANHYT", "ANSGR", "TURSG", "AKGRT"],
    "Diğer":         ["BJKAS", "FENER", "GENIL", "KARTN", "ADEL",  "DURDO",
                      "ECILC", "FMIZP", "FORMT", "GSRAY", "IEYHO", "IPMAT",
                      "KERVT", "LKMNH", "MEDTR", "PARSN", "AGROT", "MARTI"],
}

def _get_sector(ticker: str) -> str:
    """Ticker için sektör adını döndürür. Bulunamazsa 'Diğer'."""
    for sector, tickers in SECTORS.items():
        if ticker in tickers:
            return sector
    return "Diğer"


def _enrich_stock(s: dict) -> dict:
    """Stock dict'ine sector ve name alanlarını ekler (in-place + return)."""
    if "sector" not in s:
        s["sector"] = _get_sector(s.get("ticker", ""))
    if "name" not in s:
        s["name"] = STOCK_NAMES.get(s.get("ticker", ""), "")
    return s


_cache       = {"data": [], "updated_at": None, "last_refresh_ts": 0.0}  # SPEC-008 v1.2 #39
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
    """Gunluk data eksik gunleri 1m data'dan OHLC sentezleyerek doldur.
    yfinance bazen son 1-2 gunun daily barini geciktiriyor."""
    try:
        if not _YF_GLOBAL_LOCK.acquire(timeout=30):  # CPO-596: deadlock koruması
            return df
        try:
            df5d = yf.download(ticker, period="5d", interval="1m",
                               progress=False, auto_adjust=True, timeout=20, threads=False)
        finally:
            _YF_GLOBAL_LOCK.release()
        if df5d is None or df5d.empty:
            return df
        if isinstance(df5d.columns, pd.MultiIndex):
            df5d.columns = df5d.columns.get_level_values(0)
            df5d = df5d.loc[:, ~df5d.columns.duplicated()]

        last_daily = df.index[-1].date()
        last_close = float(df["Close"].iloc[-1])
        added = False
        for day in sorted(set(df5d.index.date)):
            if day <= last_daily:
                continue
            day_bars = df5d[df5d.index.map(lambda x: x.date()) == day].dropna()
            if len(day_bars) < 30:
                continue
            synth_close = float(day_bars["Close"].iloc[-1])
            # Skala koruma: intraday veri gunluk kapanistan >%25 sapiyorsa yoksay
            if last_close > 0 and abs(synth_close / last_close - 1) > 0.25:
                logger.warning(
                    "_fill_intraday_gaps(%s): skala uyusmazligi (%.2f vs %.2f), bar atlandi",
                    ticker, synth_close, last_close,
                )
                continue
            ts = pd.Timestamp(day, tz=df.index.tz)
            synth = pd.DataFrame({
                "Open":   float(day_bars["Open"].iloc[0]),
                "High":   float(day_bars["High"].max()),
                "Low":    float(day_bars["Low"].min()),
                "Close":  synth_close,
                "Volume": float(day_bars["Volume"].sum()) if "Volume" in day_bars else 0,
            }, index=pd.DatetimeIndex([ts]))
            df = pd.concat([df, synth[df.columns]])
            added = True
            last_close = synth_close
        if added:
            logger.info("_fill_intraday_gaps(%s): eksik gun(ler) 1m'den eklendi", ticker)
        return df
    except Exception as e:
        logger.warning("_fill_intraday_gaps(%s): %s", ticker, e)
        return df


def _weekly_trend(ticker: str) -> int:
    """Haftalık EMA20 yönü: +1 yükselen, -1 düşen, 0 belirsiz/hata."""
    try:
        if not _YF_GLOBAL_LOCK.acquire(timeout=30):  # CPO-596: deadlock koruması
            return 0
        try:
            wdf = yf.download(ticker, period="1y", interval="1wk",
                              progress=False, auto_adjust=True, timeout=20, threads=False)
        finally:
            _YF_GLOBAL_LOCK.release()
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


def compose_score(adx: float, vol_ratio: float, bull_score: int,
                  confirmed: bool, rsi: float) -> int:
    """Tek skor kaynağı — 0-100 aralığı. CPO-535 spec.

    Güçlü Trend listesi (_mscore) ve hisse detay sayfası (signal_strength)
    için aynı formül → tutarlı sayı. gucu_yuksek() momentum_score() ve
    analyze() AUDIT-004 tier_score'un yerine geçer (CPO-531 #36).

    Bileşenler:
        ADX       : min(adx, 50) / 50 * 30   → max 30
        Hacim     : min(vol_ratio, 5) / 5 * 25 → max 25
        Yön gücü  : bull_or_bear_score / 3 * 25 → max 25  (AL → bull, SAT → bear)
        Teyit     : +10 (signal_bars >= 3)
        RSI bölge : +10 (50-75) | +5 (>75)   → max 10

    Tier eşikleri (hisse detay badge):
        75+ → 🏆 PREMIUM | 60-74 → ✅ İYİ | 40-59 → ⚪ ORTA | <40 → ⚠️ ZAYIF
    """
    s = 0.0
    s += min(float(adx or 0), 50) / 50 * 30
    s += min(float(vol_ratio or 1.0), 5) / 5 * 25
    s += int(bull_score or 0) / 3 * 25
    s += 10 if confirmed else 0
    rsi = float(rsi or 50)
    if 50 <= rsi <= 75:
        s += 10
    elif rsi > 75:
        s += 5
    return int(round(s))


def analyze(ticker_base):
    ticker = ticker_base + ".IS" if ticker_base != "XU030" else "XU030.IS"

    try:
        weekly_dir = _weekly_trend(ticker)

        # CPO-596: timeout ile acquire — eski thread lock'u tutuyorsa sonsuz bekleme yerine skip
        if not _YF_GLOBAL_LOCK.acquire(timeout=45):
            logger.error("analyze(%s): _YF_GLOBAL_LOCK 45s timeout — skip", ticker_base)
            return None
        try:
            df = yf.download(ticker, period="2y", interval="1d",
                             progress=False, auto_adjust=True, timeout=30, threads=False)
        finally:
            _YF_GLOBAL_LOCK.release()
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

        today_str   = datetime.now(_TZ_TR).strftime("%d.%m.%Y")
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
            vol_confirmed    = signal_vol_ratio >= 1.7

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

        # ── RVOL (Relative Volume) — kalite sinyali ────────────────────────
        # Son 5 gün ortalama hacmi / Son 20 gün ortalama hacmi.
        # >= 1.20 → premium sinyal (backtest: Sharpe 1.62 → 2.97, Win Rate 36.7% → 51.5%)
        rvol = None
        is_premium = False
        try:
            if len(volume) >= 20:
                v5  = float(volume.iloc[-5:].mean())
                v20 = float(volume.iloc[-20:].mean())
                if v20 > 0 and not pd.isna(v20):
                    rvol = round(v5 / v20, 2)
                    is_premium = (signal == "AL" and rvol >= 1.20)
        except Exception:
            pass

        # ── Bilanço Yakın Riski (Faz 1 #5) — spec Bölüm 6 Filtre C ───────────
        # Sinyal aktif AL/SAT + 7 gün içinde KESİN bilanço tarihi → uyarı
        earnings_warning = None
        if signal != "BEKLE":
            _e = get_upcoming_earnings_for(ticker_base)
            if _e:
                earnings_warning = {
                    "date": _e["date"],
                    "days_ahead": _e["days_ahead"],
                    "message": f"Bilanço {_e['days_ahead']} gün sonra ({_e['date']}) — pozisyon riski yüksek"
                }

        # ── Sinyal Yaşı Yorumu (Faz 1 #4) — spec Bölüm 4.3 ──────────────────
        # 1-3 gün → Taze | 4-7 gün → Gelişiyor | 8-15 gün → Olgunlaşıyor | 15+ → Olgun
        if signal == "BEKLE" or signal_bars is None:
            signal_age_label = None
            signal_age_color = None
        elif signal_bars <= 3:
            signal_age_label = "Taze"
            signal_age_color = "green"      # 🟢 İdeal pencere
        elif signal_bars <= 7:
            signal_age_label = "Gelişiyor"
            signal_age_color = "yellow"     # 🟡 Hâlâ değerlendirilebilir
        elif signal_bars <= 15:
            signal_age_label = "Olgunlaşıyor"
            signal_age_color = "orange"     # 🟠 Dikkatli değerlendir
        else:
            signal_age_label = "Olgun"
            signal_age_color = "red"        # 🔴 Yeni giriş için geç

        # ── RSI Bölge Rozeti (Faz 1 #3) — spec Bölüm 3.3 ────────────────────
        # 30-45: Dip Toparlanması | 45-60: İdeal Giriş ✅ | 60-70: Trend Güçleniyor
        # 70-80: Dikkatli ⚠️ | 80+: Aşırı Alım 🔴 | <30: Aşırı Satım
        if rsi_val is None:
            rsi_zone = None
        elif rsi_val < 30:
            rsi_zone = "Aşırı Satım"
        elif rsi_val < 45:
            rsi_zone = "Dip Toparlanması"
        elif rsi_val < 60:
            rsi_zone = "İdeal Giriş Penceresi"
        elif rsi_val < 70:
            rsi_zone = "Trend Güçleniyor"
        elif rsi_val < 80:
            rsi_zone = "Dikkatli"
        else:
            rsi_zone = "Aşırı Alım"

        # ── R/R Çift Oran (Faz 1 #2) — bug fix ─────────────────────────────
        # Önceki kod hard-coded rr_ratio=2.0 veriyordu (anlamsız).
        # Doğru hesap: TP1 fix bir hedef, iki farklı giriş için R/R farklı:
        #  - Sinyal başından: entry=signal_price, ideal koşullar (en yüksek R/R)
        #  - Şu an girersen: entry=current, fiyat yükseldikçe R/R düşer (kovalama riski)
        rr_signal = None
        rr_now    = None
        if tp1 is not None and signal_price is not None and sl_val is not None:
            if signal == "AL":
                _risk_sig = signal_price - sl_val
                _risk_now = c - sl_val
                if _risk_sig > 0:
                    rr_signal = round((tp1 - signal_price) / _risk_sig, 2)
                if _risk_now > 0:
                    rr_now = round((tp1 - c) / _risk_now, 2)
            elif signal == "SAT":
                _risk_sig = sl_val - signal_price
                _risk_now = sl_val - c
                if _risk_sig > 0:
                    rr_signal = round((signal_price - tp1) / _risk_sig, 2)
                if _risk_now > 0:
                    rr_now = round((c - tp1) / _risk_now, 2)

        # ── Likidite Filtresi (Faz 1) — Günlük TL hacim 20 gün ortalaması ─────
        # < 5M TL → "Düşük Likidite" uyarısı (slippage + manipülasyon riski)
        # Hesap: close × volume 20 gün hareketli ortalama (lots/değer dalgalanması düzleştirilir)
        # NOT: tier_score bloğundan ÖNCE hesaplanmalı — tier penalty low_liquidity'ye bağlı.
        volume_tl_avg20 = None
        low_liquidity   = False
        try:
            if len(volume) >= 20:
                tl_series = (close * volume).rolling(20).mean()
                _avg = float(tl_series.iloc[-1])
                if not pd.isna(_avg):
                    volume_tl_avg20 = round(_avg, 0)
                    low_liquidity   = volume_tl_avg20 < 5_000_000
        except Exception:
            pass

        # ── SPEC-001 Faz 1: 3-Katmanlı Tier (Standart / Plus / Premium) ─────
        # AUDIT-004 formülü — kompozit skor 0-100
        # Standart 35-49 | Plus 50-69 | Premium 70+ (CPO MSG-076 rebalance)
        tier = None
        tier_score = 0
        if signal != "BEKLE":
            try:
                # Trend force (max 30)
                if bull_score == 3 or bear_score == 3: tier_score += 30
                elif bull_score >= 2 or bear_score >= 2: tier_score += 15
                # ADX strength (max 20)
                if adx_val >= 35: tier_score += 20
                elif adx_val >= 25: tier_score += 12
                # RVOL (max 20)
                if rvol is not None:
                    if rvol >= 2.0: tier_score += 20
                    elif rvol >= 1.5: tier_score += 15
                    elif rvol >= 1.2: tier_score += 10
                # RSI zone (max 15)
                if rsi_zone == "İdeal Giriş Penceresi": tier_score += 15
                elif rsi_zone in ("Trend Güçleniyor", "Dip Toparlanması"): tier_score += 8
                # Sinyal yaşı (max 10)
                if signal_age_label == "Taze": tier_score += 10
                elif signal_age_label == "Gelişiyor": tier_score += 6
                # Penalty: düşük likidite (-10)
                if low_liquidity: tier_score = max(0, tier_score - 10)
                # Penalty: yakın bilanço (-5)
                if earnings_warning: tier_score = max(0, tier_score - 5)
                tier_score = max(0, min(100, tier_score))
                # Eşikler
                if tier_score >= 70: tier = "premium"
                elif tier_score >= 50: tier = "plus"
                elif tier_score >= 35: tier = "standart"
            except Exception:
                tier = None
                tier_score = 0

        # ── compose_score → signal_strength (CPO-535, #36) ──────────────────
        # Tek ve tutarlı skor. hisse detay ↔ Güçlü Trend listesi aynı sayıyı gösterir.
        # tier_score (AUDIT-004) geriye uyumluluk için korunuyor — DEPRECATED.
        signal_strength = 0
        if signal != "BEKLE":
            _bs = bull_score if signal == "AL" else (bear_score or 0)
            signal_strength = compose_score(
                adx=float(adx_val or 0),
                vol_ratio=float(vol_ratio or 1.0),
                bull_score=int(_bs or 0),
                confirmed=bool(confirmed),
                rsi=float(rsi_val or 50),
            )

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
            "rvol":          rvol,
            "is_premium":    is_premium,
            "signal_strength": signal_strength,  # compose_score 0-100 (CPO-535 #36) — PRIMARY display
            "tier":          tier,        # SPEC-001 Faz 1: 'standart' | 'plus' | 'premium' | None (BEKLE) — DEPRECATED
            "tier_score":    tier_score,  # AUDIT-004 0-100 — backward compat — DEPRECATED (use signal_strength)
            "volume_tl_avg20": volume_tl_avg20,
            "low_liquidity": low_liquidity,
            "adx":           round(adx_val, 1),  # top-level for SSR/SEO
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
            "rsi_zone":        rsi_zone,  # Faz 1 #3: yorumlanmış bölge etiketi
            "signal_age_label": signal_age_label,  # Faz 1 #4: Taze/Gelişiyor/Olgunlaşıyor/Olgun
            "signal_age_color": signal_age_color,  # green/yellow/orange/red
            "earnings_warning": earnings_warning,  # Faz 1 #5: 7 gün içinde bilanço uyarısı
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
            "rr_signal":       rr_signal,  # Faz 1 #2: sinyal başından R/R
            "rr_now":          rr_now,     # Faz 1 #2: şu an girersen R/R
        }
    except Exception as e:
        logger.error("analyze(%s): %s", ticker_base, e, exc_info=True)
        return None


# ── Telegram Bildirim ─────────────────────────────────────────────────────────
TELEGRAM_BOT_TOKEN  = os.environ.get("TELEGRAM_BOT_TOKEN",  "")
TELEGRAM_CHANNEL_ID = os.environ.get("TELEGRAM_CHANNEL_ID", "")
_prev_signals       = {}   # {ticker: signal}  — bir önceki döngü sinyalleri

# MSG-019B Adım 3: _prev_signals diske persist (worker restart sonrası state korunsun)
_PREV_SIGNALS_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "prev_signals.json")
_prev_signals_lock = threading.Lock()  # disk write atomik

# SPEC-006 Faz 1 (CPO MSG-095): Notify-leader lock — gunicorn -w 4 worker'ın
# her biri background_refresh çalıştırıyor. Bildirim (Telegram/Email/Push) 4×
# duplikasyonunu önlemek için fcntl.flock ile tek worker "notify leader" olur.
# refresh_data tüm worker'larda devam eder (in-memory _cache her worker'da güncel kalmalı).
import fcntl as _fcntl
_NOTIFY_LOCK_PATH = "/tmp/bp_notify_leader.lock"
_notify_lock_fh = None

def _is_notify_leader():
    """Bu worker bildirim gönderme yetkisine sahip mi? fcntl.flock atomik —
    4 worker'dan yalnızca biri lock'u tutar, diğerleri False alır."""
    global _notify_lock_fh
    try:
        if _notify_lock_fh is None:
            _notify_lock_fh = open(_NOTIFY_LOCK_PATH, "w")
        _fcntl.flock(_notify_lock_fh, _fcntl.LOCK_EX | _fcntl.LOCK_NB)
        return True
    except (BlockingIOError, OSError):
        return False

# MSG-140 (notify-leader genişletme): background_refresh tek worker'da çalışsın.
# 4 worker × yfinance/pandas ağır iş → gevent worker bloke → %40 504 timeout.
# Leader worker bg çalıştırır + cache'i diske yazar; non-leader 3 worker hafif
# disk-reload yapar (gevent bloke etmez) → temiz HTTP handler.
_BG_LOCK_PATH = os.environ.get("BG_LOCK_PATH", "/tmp/bp_bg_leader.lock")  # staging-prod izolasyon (CPO-505)
_bg_lock_fh = None

def _is_bg_leader():
    """Bu worker background_refresh (yfinance ağır iş) yetkisine sahip mi?
    fcntl.flock — 4 worker'dan yalnızca biri leader."""
    global _bg_lock_fh
    try:
        if _bg_lock_fh is None:
            _bg_lock_fh = open(_BG_LOCK_PATH, "w")
        _fcntl.flock(_bg_lock_fh, _fcntl.LOCK_EX | _fcntl.LOCK_NB)
        return True
    except (BlockingIOError, OSError):
        return False

# SPEC-009 Faz D2 (digest mail leader-lock): _digest_cron_loop her 4 worker'da
# çalışıyordu → 19:00'da eşzamanlı first-fire (last_digest.txt yazılmadan) → 4×
# aynı digest mail → Brevo kotası 4× tükeniyor. Ayrı lock — yalnız leader gönderir.
_DIGEST_LOCK_PATH = os.environ.get("DIGEST_LOCK_PATH", "/tmp/bp_digest_leader.lock")  # staging-prod izolasyon
_digest_lock_fh = None

def _is_digest_leader():
    """Bu worker digest mail gönderme yetkisine sahip mi? fcntl.flock —
    4 worker'dan yalnızca biri leader → digest 4× yerine 1× gönderilir."""
    global _digest_lock_fh
    try:
        if _digest_lock_fh is None:
            _digest_lock_fh = open(_DIGEST_LOCK_PATH, "w")
        _fcntl.flock(_digest_lock_fh, _fcntl.LOCK_EX | _fcntl.LOCK_NB)
        return True
    except (BlockingIOError, OSError):
        return False

# SPEC-009 Gemini Faz 1: _prefetch_thread her 4 worker'da çalışıyordu → Gemini
# çağrıları 4× → maliyet patlaması (~60 TL/gün). Ayrı leader-lock — yalnız 1
# worker bg prefetch yapar (multi-worker cost multiplier fix).
_GEMINI_LOCK_PATH = os.environ.get("GEMINI_LOCK_PATH", "/tmp/bp_gemini_leader.lock")  # staging-prod izolasyon
_gemini_lock_fh = None

def _is_gemini_leader():
    """Bu worker Gemini bg prefetch yetkisine sahip mi? fcntl.flock —
    4 worker'dan yalnızca biri leader → prefetch 4× yerine 1×."""
    global _gemini_lock_fh
    try:
        if _gemini_lock_fh is None:
            _gemini_lock_fh = open(_GEMINI_LOCK_PATH, "w")
        _fcntl.flock(_gemini_lock_fh, _fcntl.LOCK_EX | _fcntl.LOCK_NB)
        return True
    except (BlockingIOError, OSError):
        return False

# CPO-520 KÖK NEDEN P0 (07.06.2026): _macro_bg_loop her worker'da çalışıyordu →
# 4 worker × 10 ticker × 3dk = 40 paralel yfinance.Ticker.fast_info call →
# gevent monkey_patch + threading hybrid corruption → /hisse deadlock 20s.
# Fix: fcntl leader-lock — yalnız 1 worker macro fetch yapar (40× → 10× her 3dk).
_MACRO_LOCK_PATH = os.environ.get("MACRO_LOCK_PATH", "/tmp/bp_macro_leader.lock")  # staging-prod izolasyon
_macro_leader_fh = None

def _is_macro_leader():
    """Bu worker macro bg fetch yetkisine sahip mi? fcntl.flock —
    4 worker'dan yalnızca biri leader → fast_info 4× yerine 1×."""
    global _macro_leader_fh
    try:
        if _macro_leader_fh is None:
            _macro_leader_fh = open(_MACRO_LOCK_PATH, "w")
        _fcntl.flock(_macro_leader_fh, _fcntl.LOCK_EX | _fcntl.LOCK_NB)
        return True
    except (BlockingIOError, OSError):
        return False

def _load_prev_signals():
    """App start'ta disk'ten _prev_signals'i yükler."""
    global _prev_signals
    try:
        if os.path.exists(_PREV_SIGNALS_PATH):
            with open(_PREV_SIGNALS_PATH) as f:
                import json as _j
                _prev_signals = _j.load(f) or {}
                logger.info("_prev_signals diskten yüklendi: %d ticker", len(_prev_signals))
    except Exception as e:
        logger.warning("_load_prev_signals: %s — boş dict ile başlanıyor", e)
        _prev_signals = {}

def _save_prev_signals(sig_map):
    """_prev_signals'i atomik olarak disk'e yaz (tempfile + rename)."""
    try:
        import json as _j
        tmp = _PREV_SIGNALS_PATH + ".tmp"
        with open(tmp, "w") as f:
            _j.dump(sig_map, f)
        os.replace(tmp, _PREV_SIGNALS_PATH)
    except Exception as e:
        logger.warning("_save_prev_signals: %s", e)

# Module load anında disk'ten yükle (her worker bunu yapacak — race condition yok, hep aynı içeriği okur)
_load_prev_signals()


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
    """Önceki döngüye göre sinyal değişimlerini tespit et;
    Telegram (seans saati + token varsa), Email (her zaman, abone varsa), Web Push (her zaman) — bağımsız rotalar.

    MSG-019B Adım 3 düzeltmesi:
    - Bug 1 fix: Telegram disable olsa bile email/push çalışsın (önce 'return' vardı)
    - Bug 2 fix: Seans dışı değişimler de pending buffer'a yazılır (digest sonraki gün gönderir)
    - State persist: _prev_signals diske yazılır → worker restart sonrası state korunur
    """
    global _prev_signals

    new_data_map = {r["ticker"]: r for r in new_results if r["ticker"] != "XU030"}
    new_sig_map  = {t: d["signal"] for t, d in new_data_map.items()}

    # SPEC-006 Faz 1 (CPO MSG-095): Sadece notify-leader worker bildirim gönderir.
    # Non-leader worker'lar state'i günceller (kendi karşılaştırması taze kalsın) ama
    # Telegram/Email/Push duplikasyonu yapmaz.
    if not _is_notify_leader():
        with _prev_signals_lock:
            _prev_signals = new_sig_map
            _save_prev_signals(new_sig_map)
        return

    # MSG-019B diag: state durumu
    if not _prev_signals:
        logger.info("_notify_signal_changes: _prev_signals boş (first run veya disk yükleme miss); değişim tespiti atlanacak, snapshot kaydediliyor")
    else:
        logger.debug("_notify_signal_changes: %d previous + %d new ticker karşılaştırılıyor", len(_prev_signals), len(new_sig_map))

    changes = []
    for t, new_sig in new_sig_map.items():
        old_sig = _prev_signals.get(t)
        if old_sig and old_sig != new_sig and new_sig in ("AL", "SAT"):
            changes.append((t, old_sig, new_sig, new_data_map[t]))

    if changes:
        logger.info("_notify_signal_changes: %d sinyal değişimi tespit edildi [%s]",
                    len(changes), ", ".join(f"{c[0]}({c[1]}→{c[2]})" for c in changes[:5]))

    # Rota 1: Telegram — sadece seans saatinde + token varsa
    now_utc  = datetime.utcnow()
    now_tr_min = now_utc.hour * 60 + now_utc.minute + 180  # UTC+3 dakika
    in_session = 600 <= now_tr_min <= 1110  # 10:00–18:30 TR

    if changes and TELEGRAM_BOT_TOKEN and TELEGRAM_CHANNEL_ID and in_session:
        sig_emoji = {"AL": "🟢", "SAT": "🔴", "BEKLE": "⚪"}
        lines = [f"<b>📊 BorsaPusula — Sinyal Değişimi</b>\n"]
        for t, old, new, stock in changes[:10]:
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

    # Rota 2: Email — her zaman (seans dışı değişimler de digest'e yazılır)
    if changes:
        _notify_email_signal_changes(changes)

    # Rota 3: Web push — seans saatinde, watchlist-aware (SPEC-006 Faz 2)
    # Her subscriber kendi watchlist'indeki ticker'ların değişimini alır.
    if changes and in_session:
        threading.Thread(
            target=_broadcast_push_changes,
            args=(changes,),
            daemon=True
        ).start()

    # State güncelle + diske persist (worker restart-safe)
    with _prev_signals_lock:
        _prev_signals = new_sig_map
        _save_prev_signals(new_sig_map)


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


def _email_base(content_html, unsubscribe_url, preheader=""):
    """Ortak e-posta şablonu — site dark teması, pusula logo, modern footer."""
    preheader_html = f'''<div style="display:none;max-height:0;overflow:hidden;font-size:1px;line-height:1px;color:#0e0e12;opacity:0">{preheader}</div>''' if preheader else ""
    return f"""<!DOCTYPE html>
<html lang="tr">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1.0">
<meta name="color-scheme" content="dark">
<meta name="supported-color-schemes" content="dark">
<title>BorsaPusula</title>
</head>
<body style="margin:0;padding:0;background:#0e0e12;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI','Inter',Arial,sans-serif;color:#e5e1e4;-webkit-font-smoothing:antialiased">
{preheader_html}
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="background:#0e0e12">
  <tr><td align="center" style="padding:32px 16px">
    <table role="presentation" width="600" cellpadding="0" cellspacing="0" border="0" style="max-width:600px;width:100%">

      <!-- Logo header -->
      <tr><td align="center" style="padding-bottom:24px">
        <a href="https://borsapusula.com" style="text-decoration:none;display:inline-block">
          <svg width="220" height="58" viewBox="0 0 460 120" xmlns="http://www.w3.org/2000/svg">
            <defs>
              <linearGradient id="bpEmailNeedle" x1="60" y1="22" x2="60" y2="60" gradientUnits="userSpaceOnUse">
                <stop offset="0" stop-color="#b8c3ff"/>
                <stop offset="1" stop-color="#00e2a1"/>
              </linearGradient>
            </defs>
            <rect x="14" y="20" width="80" height="80" rx="18" fill="#0f1218" stroke="#28303f"/>
            <line x1="22" y1="46" x2="86" y2="46" stroke="#222a37" stroke-width="1"/>
            <line x1="22" y1="74" x2="86" y2="74" stroke="#222a37" stroke-width="1"/>
            <line x1="40" y1="28" x2="40" y2="92" stroke="#222a37" stroke-width="1"/>
            <line x1="68" y1="28" x2="68" y2="92" stroke="#222a37" stroke-width="1"/>
            <path d="M54 33 L62 60 L54 55 L46 60 Z" fill="url(#bpEmailNeedle)"/>
            <path d="M54 87 L60 61 L54 64 L48 61 Z" fill="#2c3445"/>
            <circle cx="54" cy="60" r="3.5" fill="#eef3f8"/>
            <circle cx="54" cy="60" r="1.4" fill="#00e2a1"/>
            <text x="116" y="66" fill="#eef3f8" font-family="'Sora','Manrope',Arial,sans-serif" font-size="34" font-weight="800" letter-spacing="-0.5">Borsa<tspan fill="#00e2a1">Pusula</tspan></text>
            <line x1="118" y1="78" x2="430" y2="78" stroke="#1e2532" stroke-width="1"/>
            <text x="118" y="94" fill="#8f98a8" font-family="'Manrope',Arial,sans-serif" font-size="10" font-weight="700" letter-spacing="2.4">PİYASANIN YÖNÜ</text>
          </svg>
        </a>
      </td></tr>

      <!-- Body content -->
      <tr><td>{content_html}</td></tr>

      <!-- Footer -->
      <tr><td style="padding-top:32px">
        <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0">
          <tr><td style="border-top:1px solid #2a2a2c;padding-top:18px;text-align:center;font-size:11px;color:#5a5a62;line-height:1.6">
            ⚠️ Bu bildirim <strong style="color:#909097">yatırım tavsiyesi değildir</strong>. Algoritmik sinyal bilgilendirmesidir.<br>
            Geçmiş performans gelecekteki sonuçların garantisi değildir.
          </td></tr>
          <tr><td align="center" style="padding-top:12px">
            <a href="https://borsapusula.com" style="font-size:11px;color:#909097;text-decoration:none;margin:0 10px">borsapusula.com</a>
            <span style="color:#3a3a42">·</span>
            <a href="https://borsapusula.com/iletisim" style="font-size:11px;color:#909097;text-decoration:none;margin:0 10px">iletişim</a>
            <span style="color:#3a3a42">·</span>
            <a href="{unsubscribe_url}" style="font-size:11px;color:#909097;text-decoration:underline;margin:0 10px">aboneliği sonlandır</a>
          </td></tr>
        </table>
      </td></tr>

    </table>
  </td></tr>
</table>
</body></html>"""


def _build_welcome_email(email, unsubscribe_url, name=None, profile_token=""):
    """Hoş geldin maili — kişisel, motivasyonel, CTA güçlü."""
    preheader = f"Aboneliğin onaylandı. Premium sinyaller hacim onaylı olarak işaretli."
    content = f'''
    <!-- Hero -->
    <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="background:linear-gradient(135deg,rgba(0,226,144,0.08),rgba(184,195,255,0.04));border:1px solid rgba(0,226,144,0.25);border-radius:12px;margin-bottom:20px">
      <tr><td style="padding:28px 24px;text-align:center">
        <div style="font-size:32px;margin-bottom:8px">🎯</div>
        <div style="font-size:22px;font-weight:800;color:#e5e1e4;margin-bottom:8px;letter-spacing:-0.3px">{("Hoş geldin, " + name.split()[0] + "!") if name else "Hoş geldin!"}</div>
        <div style="font-size:13px;color:#909097;line-height:1.6">
          BorsaPusula sinyal bildirimlerine başarıyla abone oldun.<br>
          <span style="color:#c7c5cd;font-weight:600">{email}</span>
        </div>
      </td></tr>
    </table>

    <!-- Ne alacaksın? -->
    <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="background:#161618;border:1px solid #2a2a2c;border-radius:10px;margin-bottom:16px">
      <tr><td style="padding:20px 22px">
        <div style="font-size:11px;color:#909097;text-transform:uppercase;letter-spacing:1.4px;font-weight:700;margin-bottom:14px">📬 Ne tür mailler alacaksın</div>

        <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0">
          <tr><td style="padding:8px 0;vertical-align:top;width:30px;font-size:18px">🟢</td>
            <td style="padding:8px 0;vertical-align:top;font-size:13.5px;color:#c7c5cd;line-height:1.55">
              <strong style="color:#e5e1e4">Güçlü Trend sinyali</strong> oluştuğunda — algoritmamız 3 testten geçen yükseliş onayı verdiğinde
            </td></tr>
          <tr><td style="padding:8px 0;vertical-align:top;font-size:18px">🔴</td>
            <td style="padding:8px 0;vertical-align:top;font-size:13.5px;color:#c7c5cd;line-height:1.55">
              <strong style="color:#e5e1e4">Zayıf Trend sinyali</strong> oluştuğunda — kısa pozisyon fırsatı
            </td></tr>
          <tr><td style="padding:8px 0;vertical-align:top;font-size:18px">💎</td>
            <td style="padding:8px 0;vertical-align:top;font-size:13.5px;color:#c7c5cd;line-height:1.55">
              <strong style="color:#ffc850">Premium işaretli</strong> sinyaller — hacim onaylı (RVOL ≥ 1.20). Backtest&apos;te %51 win rate, Sharpe 2.97.
            </td></tr>
        </table>
      </td></tr>
    </table>

    <!-- Şu an sitede neler var -->
    <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="background:#161618;border:1px solid #2a2a2c;border-radius:10px;margin-bottom:24px">
      <tr><td style="padding:20px 22px">
        <div style="font-size:11px;color:#909097;text-transform:uppercase;letter-spacing:1.4px;font-weight:700;margin-bottom:12px">🎯 Site&apos;de neler var</div>
        <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0">
          <tr><td style="padding:5px 0;font-size:13px;color:#c7c5cd">📊 215 BIST hissesi günlük analiz</td></tr>
          <tr><td style="padding:5px 0;font-size:13px;color:#c7c5cd">💎 Premium hacim filtreli sinyaller</td></tr>
          <tr><td style="padding:5px 0;font-size:13px;color:#c7c5cd">🗺️ Sektör ısı haritası</td></tr>
          <tr><td style="padding:5px 0;font-size:13px;color:#c7c5cd">📅 Bilanço takvimi</td></tr>
          <tr><td style="padding:5px 0;font-size:13px;color:#c7c5cd">📈 2-yıllık backtest performans raporu</td></tr>
          <tr><td style="padding:5px 0;font-size:13px;color:#c7c5cd">⚖️ Hisse karşılaştırma</td></tr>
        </table>
      </td></tr>
    </table>

    <!-- Profil tamamla davet -->
    <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="background:rgba(184,195,255,0.06);border:1px solid rgba(184,195,255,0.20);border-radius:10px;margin-bottom:18px">
      <tr><td style="padding:18px 22px">
        <div style="font-size:14px;font-weight:700;color:#b8c3ff;margin-bottom:6px">🎯 Sinyalleri sana özelleştir</div>
        <div style="font-size:12.5px;color:#c7c5cd;line-height:1.55;margin-bottom:12px">
          30 saniye ayır, yatırım profilini doldur. Sana en uygun sinyal türleri ve mail sıklığını ayarla.
        </div>
        <a href="https://borsapusula.com/profil?t={profile_token}" style="display:inline-block;background:rgba(184,195,255,0.14);color:#b8c3ff;border:1px solid rgba(184,195,255,0.45);padding:8px 18px;border-radius:6px;text-decoration:none;font-size:12.5px;font-weight:700;letter-spacing:0.3px">
          Profili Tamamla →
        </a>
      </td></tr>
    </table>

    <!-- CTA -->
    <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0">
      <tr><td align="center">
        <a href="https://borsapusula.com" style="display:inline-block;background:#00e290;color:#0e0e12;padding:14px 40px;border-radius:8px;text-decoration:none;font-size:14px;font-weight:700;letter-spacing:0.3px">
          Sinyal Panelini Aç →
        </a>
      </td></tr>
    </table>

    <p style="text-align:center;font-size:12px;color:#909097;margin-top:18px;line-height:1.5">
      İlk sinyal mailini sinyal değişimi olduğunda alacaksın.<br>
      Bekleme süresi yok — site sürekli güncel.
    </p>
    '''
    return _email_base(content, unsubscribe_url, preheader=preheader)


def _build_signal_email(changes, unsubscribe_url):
    """Sinyal değişim maili — premium-aware, modern card layout."""
    sig_color  = {"AL": "#00e290", "SAT": "#f85149", "BEKLE": "#909097"}
    sig_bg     = {"AL": "rgba(0,226,144,0.10)", "SAT": "rgba(248,81,73,0.10)", "BEKLE": "rgba(144,144,151,0.08)"}
    sig_border = {"AL": "rgba(0,226,144,0.30)", "SAT": "rgba(248,81,73,0.30)", "BEKLE": "rgba(144,144,151,0.20)"}
    sig_lbl    = {"AL": "▲ Güçlü Trend", "SAT": "▼ Zayıf Trend", "BEKLE": "● Belirsiz"}

    # Premium ve sayım analizi
    al_count   = sum(1 for c in changes if c[2] == "AL")
    sat_count  = sum(1 for c in changes if c[2] == "SAT")
    prem_count = sum(1 for c in changes if c[3].get("is_premium"))
    tickers_str = ", ".join(c[0] for c in changes[:4])
    if len(changes) > 4: tickers_str += f" +{len(changes)-4}"

    preheader = f"{al_count} Güçlü Trend · {sat_count} Zayıf Trend · {prem_count} Premium 💎 — {tickers_str}"

    # Sinyal kartları
    cards = ""
    for t, old, new, stock in changes[:10]:
        name      = STOCK_NAMES.get(t, t)
        price     = stock.get("price") or 0
        sl_level  = stock.get("sl_level")
        adx       = stock.get("adx") or 0
        rvol      = stock.get("rvol")
        is_prem   = stock.get("is_premium", False)
        col       = sig_color.get(new, "#909097")
        bg        = sig_bg.get(new, "rgba(144,144,151,0.08)")
        bd        = sig_border.get(new, "rgba(144,144,151,0.2)")
        lbl       = sig_lbl.get(new, new)

        prem_badge = ""
        if is_prem:
            prem_badge = '''<span style="display:inline-block;background:rgba(255,200,80,0.12);border:1px solid rgba(255,200,80,0.45);color:#ffc850;font-size:10px;font-weight:700;padding:2px 7px;border-radius:6px;letter-spacing:0.4px;margin-left:6px;vertical-align:middle">💎 PREMIUM</span>'''

        sl_html = f'<span style="color:#909097">SL <strong style="color:#c7c5cd">{sl_level:.2f}₺</strong></span>' if sl_level else ''
        rvol_html = f'<span style="color:#909097">·  RVOL <strong style="color:{"#ffc850" if is_prem else "#c7c5cd"}">{rvol:.2f}×</strong></span>' if rvol is not None else ''

        cards += f'''
        <tr><td style="padding:0 0 12px 0">
          <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="background:{bg};border:1px solid {bd};border-radius:10px">
            <tr><td style="padding:14px 16px">
              <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0">
                <tr>
                  <td style="vertical-align:top">
                    <a href="https://borsapusula.com/hisse/{t}" style="color:#e5e1e4;text-decoration:none;font-size:18px;font-weight:800;letter-spacing:-0.3px">{t}</a>{prem_badge}
                    <div style="font-size:11.5px;color:#909097;margin-top:3px">{name}</div>
                  </td>
                  <td align="right" style="vertical-align:top">
                    <div style="font-size:15px;font-weight:700;color:#e5e1e4;font-variant-numeric:tabular-nums">{price:.2f} ₺</div>
                    <div style="background:{bg};color:{col};border:1px solid {bd};border-radius:6px;padding:3px 9px;font-size:11px;font-weight:700;display:inline-block;margin-top:4px">{lbl}</div>
                  </td>
                </tr>
                <tr><td colspan="2" style="padding-top:10px;border-top:1px solid rgba(255,255,255,0.04);margin-top:10px">
                  <div style="font-size:11.5px;color:#909097;line-height:1.7;padding-top:8px">
                    <span style="color:#909097">Momentum <strong style="color:#c7c5cd">{adx:.0f}</strong></span>
                    {f"  ·  {sl_html}" if sl_html else ""}
                    {rvol_html}
                  </div>
                  <div style="margin-top:10px">
                    <a href="https://borsapusula.com/hisse/{t}" style="color:#b8c3ff;font-size:12px;font-weight:600;text-decoration:none">Detay ve grafik →</a>
                  </div>
                </td></tr>
              </table>
            </td></tr>
          </table>
        </td></tr>'''

    # Header summary
    summary_chips = ""
    if al_count > 0:
        summary_chips += f'<span style="display:inline-block;background:rgba(0,226,144,0.10);border:1px solid rgba(0,226,144,0.30);color:#00e290;font-size:11px;font-weight:700;padding:4px 10px;border-radius:8px;margin:0 4px">▲ {al_count} Güçlü Trend</span>'
    if sat_count > 0:
        summary_chips += f'<span style="display:inline-block;background:rgba(248,81,73,0.10);border:1px solid rgba(248,81,73,0.30);color:#f85149;font-size:11px;font-weight:700;padding:4px 10px;border-radius:8px;margin:0 4px">▼ {sat_count} Zayıf Trend</span>'
    if prem_count > 0:
        summary_chips += f'<span style="display:inline-block;background:rgba(255,200,80,0.10);border:1px solid rgba(255,200,80,0.40);color:#ffc850;font-size:11px;font-weight:700;padding:4px 10px;border-radius:8px;margin:0 4px">💎 {prem_count} Premium</span>'

    content = f'''
    <!-- Header -->
    <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="background:#161618;border:1px solid #2a2a2c;border-radius:10px;margin-bottom:20px">
      <tr><td style="padding:18px 22px;text-align:center">
        <div style="font-size:11px;color:#909097;text-transform:uppercase;letter-spacing:1.4px;font-weight:700;margin-bottom:8px">📊 Yeni Sinyal Değişimleri</div>
        <div style="font-size:13px;color:#c7c5cd;margin-bottom:14px">{datetime.now(_TZ_TR).strftime("%d %B %Y · %H:%M")}</div>
        <div>{summary_chips}</div>
      </td></tr>
    </table>

    <!-- Signal cards -->
    <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0">
      {cards}
    </table>

    <!-- CTA -->
    <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="margin-top:16px">
      <tr><td align="center">
        <a href="https://borsapusula.com" style="display:inline-block;background:#00e290;color:#0e0e12;padding:14px 36px;border-radius:8px;text-decoration:none;font-size:14px;font-weight:700;letter-spacing:0.3px">
          Tüm Sinyalleri Gör →
        </a>
      </td></tr>
      <tr><td align="center" style="padding-top:10px">
        <a href="https://borsapusula.com/sinyal-performans" style="display:inline-block;color:#909097;font-size:12px;text-decoration:none;border-bottom:1px solid #3a3a42;padding-bottom:1px">
          Backtest performansını gör →
        </a>
      </td></tr>
    </table>
    '''
    return _email_base(content, unsubscribe_url, preheader=preheader)


# Pending changes buffer — günlük/haftalık digest için biriktirir
_pending_changes_lock = threading.Lock()
_pending_changes_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "pending_changes.json")


def _load_pending_changes():
    if not os.path.exists(_pending_changes_path):
        return []
    try:
        with open(_pending_changes_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []


def _save_pending_changes(items):
    try:
        with open(_pending_changes_path, "w", encoding="utf-8") as f:
            json.dump(items, f, ensure_ascii=False, default=str)
    except Exception as e:
        logger.warning("pending_changes.json yazma hatası: %s", e)


def _serialize_change(c):
    """changes tuple → JSON-serializable dict."""
    t, old, new, stock = c
    return {
        "ticker":    t,
        "old":       old,
        "new":       new,
        "stock":     {
            "price":      stock.get("price"),
            "change_pct": stock.get("change_pct"),
            "sl_level":   stock.get("sl_level"),
            "adx":        stock.get("adx"),
            "rvol":       stock.get("rvol"),
            "is_premium": stock.get("is_premium", False),
            "name":       STOCK_NAMES.get(t, t),
        },
        "ts":        datetime.now().isoformat(),
    }


def _deserialize_change(d):
    """pending JSON dict → changes tuple."""
    return (d["ticker"], d["old"], d["new"], d["stock"])


def _notify_email_signal_changes(changes):
    """Aktif abonelere sinyal değişim e-postası — mail tercihine göre rota."""
    if not SMTP_HOST or not changes:
        if not changes:
            logger.debug("_notify_email_signal_changes: changes boş, skip")
        return

    # MSG-019B diag: değişen sinyal sayısı
    logger.info("_notify_email_signal_changes: %d değişim alındı [%s]",
                len(changes), ", ".join(c[0] for c in changes[:5]) + ("..." if len(changes) > 5 else ""))

    # 1) Pending buffer'a ekle (günlük/haftalık digest için)
    with _pending_changes_lock:
        pending = _load_pending_changes()
        prev_len = len(pending)
        pending.extend(_serialize_change(c) for c in changes)
        _save_pending_changes(pending)
        logger.info("Pending buffer: %d → %d (+%d) (file=pending_changes.json)",
                    prev_len, len(pending), len(changes))

    # 2) Anında gönderim — mail_pref=instant olan kullanıcılara
    def _send_instant():
        with _sub_lock:
            subs = _load_subscribers()
        active = {e: d for e, d in subs.items() if d.get("active", True)}
        if not active:
            return
        sent = 0
        for email, data in active.items():
            mail_pref = data.get("mail_pref") or "daily"
            # Sadece instant ya da premium-isteyen abonelere anlık
            if mail_pref not in ("instant", "premium"):
                continue
            token    = data.get("token", "")
            name     = data.get("name", "")
            tickers  = data.get("tickers", [])
            # Filter changes by user prefs
            relevant = list(changes)
            # Premium-only filter
            if mail_pref == "premium":
                relevant = [c for c in relevant if c[3].get("is_premium")]
            # Watchlist filter
            if tickers:
                relevant = [c for c in relevant if c[0] in tickers]
            if not relevant:
                continue
            unsub_url = f"https://borsapusula.com/unsubscribe/{token}"
            subject_prefix = "💎 Premium" if mail_pref == "premium" else "🔔 BorsaPusula —"
            subject = subject_prefix + " Sinyal Değişimi: " + ", ".join(c[0] for c in relevant[:3])
            if len(relevant) > 3:
                subject += f" +{len(relevant) - 3}"
            if send_email(email, subject, _build_signal_email(relevant, unsub_url)):
                sent += 1
            time.sleep(0.3)
        if sent:
            logger.info("Anında sinyal e-postası gönderildi: %d abone", sent)

    threading.Thread(target=_send_instant, daemon=True).start()


# SPEC-009 Aksiyon 3 (Trading Day Guard): resmi tatil + hafta sonu digest
# atlanır — veri oluşmadan mail anlamsız + spam algısı. holidays paketi yoksa
# defansif: yalnız hafta sonu kontrolü (digest crash etmez, sadece tatil atlamaz).
try:
    import holidays as _holidays_lib
    _tr_holidays = _holidays_lib.Turkey()
except Exception:
    _tr_holidays = None
    logger.warning("holidays paketi yüklü değil — is_trading_day yalnız hafta sonu kontrolü")

def is_trading_day(d=None):
    """BIST işlem günü mü? Hafta sonu (Cmt/Pzr) veya TR resmi tatil → False."""
    d = d or datetime.now(_TZ_TR).date()
    if d.weekday() >= 5:
        return False
    if _tr_holidays is not None and d in _tr_holidays:
        return False
    return True


# ── SPEC-014 Faz B — Data Freshness SLA ───────────────────────────────────────
def _market_open(now_tr=None):
    """BIST seansı açık mı? Hafta içi 10:00-18:00 TR + işlem günü."""
    now_tr = now_tr or datetime.now(_TZ_TR)
    if not is_trading_day(now_tr.date()):
        return False
    return 10 <= now_tr.hour < 18


def build_data_freshness():
    """SPEC-014 B1 — veri tazeliği meta objesi.

    /api/data ve /api/health response'larına eklenir.
    is_stale = market_open ve stocks yaşı > 900s (15dk).
    """
    now = time.time()
    with _lock:
        last_ts    = _cache.get("last_refresh_ts", 0.0) or 0.0
        updated_at = _cache.get("updated_at")
    macro_ts = _macro_cache.get("ts", 0) if "_macro_cache" in globals() else 0

    stocks_age = int(now - last_ts) if last_ts else None
    macro_age  = int(now - macro_ts) if macro_ts else None
    mkt_open   = _market_open()
    is_stale   = bool(stocks_age is not None and stocks_age > 1800)  # CPO-596: market_open'a bağlama, 30dk absolute threshold

    return {
        "stocks_updated_at":  updated_at,
        "stocks_age_seconds": stocks_age,
        "macro_updated_at":   datetime.fromtimestamp(macro_ts, _TZ_TR).isoformat() if macro_ts else None,
        "macro_age_seconds":  macro_age,
        "is_stale":           is_stale,
        "market_open":        mkt_open,
    }


def _send_digest_emails(timeframe="daily", force=False):
    """Günlük (19:00) veya haftalık (Cuma 19:00) digest gönder.
    timeframe: 'daily' | 'weekly'
    force: True ise pending boş bile olsa devam (MSG-019B manuel test için)"""
    if not SMTP_HOST:
        logger.warning("_send_digest_emails: SMTP_HOST yok, atlandı (timeframe=%s)", timeframe)
        return {"status": "no_smtp", "sent": 0}

    # SPEC-009 Aksiyon 3: tatil/hafta sonu daily digest atla (force manuel hariç).
    if timeframe == "daily" and not force and not is_trading_day():
        logger.info("digest skipped: işlem günü değil (%s)", datetime.now(_TZ_TR).date())
        return {"status": "not_trading_day", "sent": 0}

    with _pending_changes_lock:
        pending = _load_pending_changes()

    # MSG-019B diag: pending durumu
    logger.info("_send_digest_emails(%s, force=%s): pending=%d items", timeframe, force, len(pending))

    if not pending and not force:
        logger.info("Digest skip: pending değişim yok (timeframe=%s)", timeframe)
        return {"status": "empty_pending", "sent": 0}

    # Reconstruct changes
    changes = [_deserialize_change(d) for d in pending] if pending else []

    with _sub_lock:
        subs = _load_subscribers()
    active = {e: d for e, d in subs.items() if d.get("active", True)}
    logger.info("Digest: %d aktif abone, %d toplam abone", len(active), len(subs))
    if not active:
        return {"status": "no_active_subs", "sent": 0}

    target_pref = timeframe  # 'daily' or 'weekly'
    sent = 0
    # MSG-019B diag: skip nedenleri sayacı
    skip_reasons = {"pref_mismatch": 0, "watchlist_empty": 0, "send_fail": 0}
    for email, data in active.items():
        mail_pref = data.get("mail_pref") or "daily"
        if mail_pref != target_pref:
            skip_reasons["pref_mismatch"] += 1
            continue
        token   = data.get("token", "")
        name    = data.get("name", "")
        tickers = data.get("tickers", [])
        # Watchlist filter
        relevant = list(changes)
        if tickers:
            relevant = [c for c in relevant if c[0] in tickers]
        if not relevant:
            skip_reasons["watchlist_empty"] += 1
            continue
        unsub_url = f"https://borsapusula.com/unsubscribe/{token}"

        if timeframe == "daily":
            today_str = datetime.now(_TZ_TR).strftime("%-d %B")
            subject = f"📊 {today_str} BIST Sinyalleri"
        else:
            subject = f"📊 Haftalık BIST Özeti — {datetime.now(_TZ_TR).strftime('%-d %B')}"

        # Premium count for subject hint
        prem_count = sum(1 for c in relevant if c[3].get("is_premium"))
        if prem_count > 0:
            subject += f" — {prem_count} Premium 💎"

        if send_email(email, subject, _build_signal_email(relevant, unsub_url)):
            sent += 1
        else:
            skip_reasons["send_fail"] += 1
        time.sleep(0.3)

    logger.info("%s digest sonuc: sent=%d, skip_pref=%d, skip_watchlist=%d, skip_sendfail=%d (active=%d, changes=%d)",
                timeframe, sent, skip_reasons["pref_mismatch"],
                skip_reasons["watchlist_empty"], skip_reasons["send_fail"],
                len(active), len(changes))

    # Daily digest gönderildiyse buffer temizle (force run'da temizleme)
    if timeframe == "daily" and not force:
        with _pending_changes_lock:
            _save_pending_changes([])
        logger.info("Pending changes buffer temizlendi (daily digest sonrası)")

    return {
        "status": "ok",
        "sent": sent,
        "active": len(active),
        "changes": len(changes),
        "skipped": skip_reasons,
    }


def _digest_cron_loop():
    """Günde bir kez 19:00'da digest gönder. Cuma 19:00'da haftalık."""
    while True:
        try:
            now = datetime.now(_TZ_TR)
            # 19:00–19:05 arasında ve son 6 saatte gönderilmediyse tetikle
            if 19 <= now.hour < 20 and now.minute < 10:
                # Leader-lock — yalnız 1 worker digest gönderir. 4 worker eşzamanlı
                # tetiklenince last_digest.txt yazılmadan 4× mail gidiyordu (Faz D2).
                if not _is_digest_leader():
                    time.sleep(300)
                    continue
                last_sent_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "last_digest.txt")
                today_str = now.strftime("%Y-%m-%d")
                already_sent = False
                if os.path.exists(last_sent_path):
                    try:
                        with open(last_sent_path) as f:
                            last_date = f.read().strip()
                        if last_date == today_str:
                            already_sent = True
                    except Exception:
                        pass
                if not already_sent:
                    logger.info("Daily digest cron tetiklendi: %s", today_str)
                    _send_digest_emails("daily")
                    # Cuma ise haftalık da gönder
                    if now.weekday() == 4:  # Friday
                        logger.info("Weekly digest cron (Cuma)")
                        _send_digest_emails("weekly")
                    try:
                        with open(last_sent_path, "w") as f:
                            f.write(today_str)
                    except Exception as e:
                        logger.warning("last_digest.txt yazma: %s", e)
        except Exception as e:
            logger.error("digest_cron_loop: %s", e, exc_info=True)
        time.sleep(300)  # 5 dakikada bir kontrol


threading.Thread(target=_digest_cron_loop, daemon=True, name="digest-cron").start()
logger.info("Digest cron başlatıldı (her 5 dakikada kontrol, 19:00'da tetikler)")


# ── SPEC-014 B4 — Freshness monitor (market saatinde veri yaşı > 25dk → Telegram) ──
_freshness_alert_state = {"last_alert_ts": 0.0}

def _freshness_monitor_loop():
    """Market seansında veri yaşı > 25dk ise Telegram uyarısı gönderir.

    #22 trading-day + market-hours guard ile false positive önlenir
    (gece/tatil veri yaşı zaten yüksek olur — alarm yalnız seans içinde).
    Anti-spam: aynı stale durumda en fazla saatte 1 mesaj.
    """
    while True:
        try:
            if _market_open():
                fresh = build_data_freshness()
                age = fresh.get("stocks_age_seconds")
                if age is not None and age > 1500:  # 25 dk
                    now = time.time()
                    if now - _freshness_alert_state["last_alert_ts"] > 3600:
                        _freshness_alert_state["last_alert_ts"] = now
                        mins = age // 60
                        _send_telegram(
                            f"⚠️ <b>BorsaPusula veri tazeliği uyarısı</b>\n"
                            f"BIST seansında hisse verisi <b>{mins} dakikadır</b> "
                            f"güncellenmedi (eşik 25 dk).\n"
                            f"Son güncelleme: {fresh.get('stocks_updated_at') or '—'}"
                        )
                        logger.warning("Freshness alarm: stocks_age=%ss (>25dk), Telegram gönderildi", age)
        except Exception as e:
            logger.error("freshness_monitor_loop: %s", e, exc_info=True)
        time.sleep(300)  # 5 dakikada bir kontrol


# Leader-only — #30 maliyet/spam multiplier fix: 4 worker yerine 1 worker
# Telegram alarmı gönderir (anti-spam state worker-local olduğu için gate şart).
if _is_notify_leader():
    threading.Thread(target=_freshness_monitor_loop, daemon=True, name="freshness-monitor").start()
    logger.info("Freshness monitor başlatıldı (LEADER — 5dk kontrol, seansda >25dk → Telegram)")
else:
    logger.info("Freshness monitor: non-leader worker — atlandı (spam fix)")


# SPEC-008 L5 — Modül-load-time tanımlama (alarm thread'inden ÖNCE).
_chart_integrity_errors = {}                   # {ticker: float ts}
_CHART_INTEGRITY_ALARM_THRESHOLD = 5           # 214 hisseden >N → alarm
_CHART_INTEGRITY_ALARM_WINDOW_S  = 600         # son 10 dakika


def _chart_integrity_count_recent(now=None):
    """Son ALARM_WINDOW içindeki integrity_error ticker sayısı. Pruning dahil."""
    now = now or time.time()
    win = _CHART_INTEGRITY_ALARM_WINDOW_S
    with _lock:
        # Eski kayıtları temizle (in-place)
        stale = [t for t, ts in _chart_integrity_errors.items() if (now - ts) > win]
        for t in stale:
            _chart_integrity_errors.pop(t, None)
        return len(_chart_integrity_errors)


def _chart_integrity_alarm_loop():
    """SPEC-008 L5 — Son 10dk içindeki chart integrity_error ticker sayısı eşiği
    aşarsa journalctl'e ALARM düşürür. Anti-spam: aynı durumda 30dk'da 1 mesaj."""
    last_alarm = 0.0
    while True:
        try:
            n = _chart_integrity_count_recent()
            if n > _CHART_INTEGRITY_ALARM_THRESHOLD:
                now = time.time()
                if now - last_alarm > 1800:   # 30dk anti-spam
                    last_alarm = now
                    logger.error("CHART-INTEGRITY-ALARM: son %ddk içinde %d/%d hisse integrity_error "
                                 "(eşik %d). Watchdog/manuel inceleme gerekli.",
                                 _CHART_INTEGRITY_ALARM_WINDOW_S // 60, n, len(BIST100) - 1,
                                 _CHART_INTEGRITY_ALARM_THRESHOLD)
        except Exception as e:
            logger.error("chart_integrity_alarm_loop hatası: %s", e)
        time.sleep(300)  # 5 dakikada bir kontrol


# Leader-only — anti-spam state worker-local; 4× duplicate alarm engellenir.
if _is_notify_leader():
    threading.Thread(target=_chart_integrity_alarm_loop, daemon=True,
                     name="chart-integrity-alarm").start()
    logger.info("Chart-integrity alarm başlatıldı (LEADER — SPEC-008 L5)")


_DISK_CACHE_PATH       = os.path.join(os.path.dirname(os.path.abspath(__file__)), "last_cache.json")
_LIVE_PRICES_DISK_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "last_live_prices.json")
_BT_DISK_PATH          = os.path.join(os.path.dirname(os.path.abspath(__file__)), "backtest_cache.json")
_SNAPSHOTS_DIR   = os.path.join(os.path.dirname(os.path.abspath(__file__)), "snapshots")
os.makedirs(_SNAPSHOTS_DIR, exist_ok=True)


def _save_daily_snapshot(data: list):
    """Seans kapandıktan sonra (14:00 UTC = 17:00 TR) günlük snapshot yazar.
    Her gün için bir kez; dosya varsa üzerine yazmaz."""
    now = datetime.now()
    # Sadece seans saati sonrası yaz (14:00 UTC → 17:00 TR)
    if now.hour < 14:
        return
    fname = os.path.join(_SNAPSHOTS_DIR, f"{now.strftime('%Y-%m-%d')}.json")
    if os.path.exists(fname):
        return  # Bugün zaten yazıldı
    try:
        with open(fname, "w", encoding="utf-8") as f:
            json.dump({
                "date":     now.strftime("%Y-%m-%d"),
                "date_tr":  now.strftime("%d.%m.%Y"),
                "stocks":   data,
                "saved_at": now.isoformat(),
                "al_count":    sum(1 for s in data if s.get("signal") == "AL"),
                "sat_count":   sum(1 for s in data if s.get("signal") == "SAT"),
                "bekle_count": sum(1 for s in data if s.get("signal") == "BEKLE"),
            }, f, ensure_ascii=False, default=str)
        logger.info("Günlük snapshot yazıldı: %s (%d hisse)", fname, len(data))
    except Exception as e:
        logger.warning("Snapshot yazma hatası: %s", e)


def _save_cache_to_disk(data):
    """Son başarılı sinyal datasını diske yazar — restart sonrası hızlı yükleme için.
    Madde 1: atomic — non-leader worker yarım dosya okumamalı."""
    try:
        _atomic_write_json(_DISK_CACHE_PATH, data)
        logger.debug("Disk cache yazıldı: %d hisse", len(data))
    except Exception as e:
        logger.warning("Disk cache yazma hatası: %s", e)


# H3 (#60) — Disk cache mtime guard (26 May 2026, INCIDENT-3/5/6/7 root cause fix)
# Module-level state: aynı mtime → reload SKIP, gevent hub blocking I/O önlenir.
# Önceki: background_refresh non-leader 3 worker × 90s döngü = 95 reload/saat (24h 2280).
# Yeni: file mtime aynıysa hemen return; sadece refresh_data yazımı sonrası reload.
_disk_cache_mtime = None  # type: Optional[float]


def _load_cache_from_disk():
    """Disk cache'i yükler — mtime değişmediyse SKIP (H3 fix, #60).

    Cold start: _disk_cache_mtime=None → ilk mtime ile compare, mismatch → load.
    İlk yüklemeden sonra: file değişmedikçe in-memory dön, blocking I/O yok.
    Thread-safety: float/None atomic primitive (Python GIL), ek lock gerekmez.
    """
    global _disk_cache_mtime
    try:
        if not os.path.exists(_DISK_CACHE_PATH):
            return
        current_mtime = os.path.getmtime(_DISK_CACHE_PATH)
        # H3 guard: mtime aynı + in-memory veri var → SKIP (1.6 reload/dakika sızıntısı kapanır)
        if _disk_cache_mtime == current_mtime and _cache.get("data"):
            return
        with open(_DISK_CACHE_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        if data and isinstance(data, list) and len(data) > 0:
            for s in data:
                _enrich_stock(s)
            # updated_at = disk dosyasının mtime'ı (refresh_data yazımı sonrası).
            # Non-leader worker refresh_data çalıştırmaz → placeholder string
            # /api/data updated_at'i parse edilemez bırakıyordu. mtime her zaman parse edilebilir.
            disk_ts = datetime.fromtimestamp(current_mtime, _TZ_TR).strftime("%d.%m.%Y %H:%M:%S")
            with _lock:
                _cache["data"] = data
                _cache["updated_at"] = disk_ts
                # SPEC-008 v1.2 #39 — disk mtime = son refresh_data zamanı.
                # background_refresh tamamlanana kadar grace penceresi açık (>300s ise).
                _cache["last_refresh_ts"] = current_mtime
            _disk_cache_mtime = current_mtime  # H3: state update sadece load sonrası
            logger.info("Disk cache yüklendi: %d hisse (updated_at=%s)", len(data), disk_ts)
    except Exception as e:
        logger.warning("Disk cache okuma hatası: %s", e)


# CPO-506 P0 (Pzt 10:00 öncesi): analyze() per-ticker hard-timeout + negatif cache.
# Watchdog deadlock'u önlüyor ama yfinance yavaşlığını çözmüyor (CPO-501/502 önerisi).
# Yaklaşım: her ticker için ThreadPoolExecutor + 8s timeout. Timeout'ta skip + 60s negatif cache
# (sonraki iterasyonda tekrar dene, ardarda hang'i önler). 30 ticker × 8s = max ~240s soft cap.
import concurrent.futures as _cf_analyze
_ANALYZE_EXECUTOR    = _cf_analyze.ThreadPoolExecutor(max_workers=2, thread_name_prefix="analyze_wd")  # CPO-583: 4→2 CPU throttle
_ANALYZE_TIMEOUT     = 40    # saniye, CPO-592v3: fetch_live(12s)+fetch_global(8s)+3_download(11s) = ~31s worst-case
_ANALYZE_NEG_CACHE   = {}    # {ticker: timeout_until_ts} — 60s skip after timeout
_ANALYZE_NEG_TTL     = 60    # saniye

def _analyze_with_timeout(ticker):
    """analyze(ticker) çağrısını 8s timeout ile sar. Timeout'ta None döner + 60s negatif cache."""
    # Negatif cache kontrolü — son 60s içinde timeout aldıysa skip
    until = _ANALYZE_NEG_CACHE.get(ticker, 0)
    if until > time.time():
        return None  # negatif cache geçerli, skip

    future = _ANALYZE_EXECUTOR.submit(analyze, ticker)
    try:
        return future.result(timeout=_ANALYZE_TIMEOUT)
    except _cf_analyze.TimeoutError:
        _ANALYZE_NEG_CACHE[ticker] = time.time() + _ANALYZE_NEG_TTL
        logger.warning("ANALYZE_TIMEOUT: %s %ds — neg cache %ds, skip", ticker, _ANALYZE_TIMEOUT, _ANALYZE_NEG_TTL)
        future.cancel()
        return None
    except Exception as e:
        logger.error("analyze(%s) hatası: %s", ticker, e)
        return None


def refresh_data():
    # CPO-507 P0 refining (Cmt 17:45): SIRALI for loop yerine PARALEL ThreadPoolExecutor.
    # Önceki: 30 ticker × 8s socket timeout = 240s watchdog timeout (Cmt yfinance throttle ağırlaştı)
    # Yeni: 4 paralel as_completed → 30/4 ≈ 8 batch × 8s = max ~64s
    # Per-ticker hard-timeout korunuyor (_analyze_with_timeout içinde)
    # Toplam timeout 180s soft cap (240s watchdog'un altında)
    results = []
    # CPO-596: `with executor` kullanma — __exit__ shutdown(wait=True) çağırır ve hung thread'de
    # 66 saat bloke kalır. Explicit shutdown(wait=False) ile hung thread'leri bırak, devam et.
    ex = _cf_analyze.ThreadPoolExecutor(max_workers=2, thread_name_prefix="refresh_par")  # CPO-583: 4→2 CPU throttle
    try:
        future_map = {ex.submit(_analyze_with_timeout, t): t for t in BIST30}
        try:
            for future in _cf_analyze.as_completed(future_map, timeout=180):
                try:
                    r = future.result(timeout=1)  # _analyze_with_timeout zaten 8s döner
                    if r:
                        results.append(r)
                except Exception as e:
                    logger.warning("refresh_data future hatası (%s): %s", future_map[future], e)
        except _cf_analyze.TimeoutError:
            # 180s'de bitmediyse iptal et — gelen sonuçlarla devam (degraded ama YAZAR)
            done_count = sum(1 for f in future_map if f.done())
            logger.warning("refresh_data 180s soft cap → %d/30 ticker tamamlandı, degraded yaz", done_count)
            for f in future_map:
                if not f.done():
                    f.cancel()
    finally:
        ex.shutdown(wait=False)  # CPO-596: hung thread'leri bekleme — deadlock önleme

    results.sort(key=lambda x: (
        0 if x.get("is_new_signal") else 1,
        0 if x["signal"] == "AL" else 1 if x["signal"] == "SAT" else 2,
        -x["bull_score"] if x["signal"] == "AL" else -x["bear_score"]
    ))

    _notify_signal_changes(results)

    for s in results:
        _enrich_stock(s)

    # ── prev_cache fallback (CPO-550/551): yfinance no-data/timeout tickerlar ────────
    # Seans dışında bazı tickerlar yfinance'tan veri gelmez → analyze() None →
    # results'a girmez → cache kısmi yazılır (örn: 193/215).
    # Fix: önceki cache'deki eksik tickerları "stale" flag ile koru → 215/215 sustained.
    with _lock:
        _prev_data = list(_cache.get("data") or [])
    _fresh_tickers = {r["ticker"] for r in results}
    _stale_count = 0
    for _ps in _prev_data:
        _pt = _ps.get("ticker")
        if _pt and _pt not in _fresh_tickers:
            _fallback = dict(_ps)
            _fallback["data_quality"] = "stale"
            results.append(_fallback)
            _stale_count += 1
    if _stale_count:
        logger.info("prev_cache fallback: %d ticker stale ile korundu (toplam %d)", _stale_count, len(results))
    # ── /prev_cache fallback ─────────────────────────────────────────────────────────

    with _lock:
        _cache["data"] = results
        _cache["updated_at"] = datetime.now(_TZ_TR).strftime("%d.%m.%Y %H:%M:%S")
        _cache["last_refresh_ts"] = time.time()  # SPEC-008 v1.2 #39 — grace pencere kapanır

    # Başarılı güncellemeden sonra diske yaz
    _save_cache_to_disk(results)
    _save_daily_snapshot(results)   # T2-6: Günlük snapshot (seans sonrası)


def fetch_live_prices():
    tickers_str = " ".join(t + ".IS" for t in BIST30)
    try:
        with _YF_GLOBAL_LOCK:  # CPO-592v3: batch da lock altında — slow_chart_refresh contamination fix
            df = yf.download(
                tickers_str, period="2d", interval="1m",
                progress=False, auto_adjust=True, group_by="ticker", timeout=30, threads=False
            )
        if df is None or df.empty:
            return

        payload = {}
        now_str  = datetime.now(_TZ_TR).strftime("%H:%M:%S")

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
            _save_live_prices_to_disk()
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
        with _YF_GLOBAL_LOCK:  # CPO-592v3: batch da lock altında
            df = yf.download(
                " ".join(syms), period="2d", interval="1m",
                progress=False, auto_adjust=True, group_by="ticker", timeout=30, threads=False
            )
        if df is None or df.empty:
            return

        payload = {}
        now_str  = datetime.now(_TZ_TR).strftime("%H:%M:%S")
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
            _save_live_prices_to_disk()
            _push_sse({"type": "global_prices", "data": payload, "ts": now_str})

    except Exception as e:
        logger.error("fetch_global_prices: %s", e, exc_info=True)


def _save_live_prices_to_disk():
    """Refresh service: _live_prices'ı diske yazar; web workerlar okusun.
    Boş dict'i yazmaz — startup'ta var olan disk verisini silmesin."""
    try:
        with _lock:
            snapshot = dict(_live_prices)
        if not snapshot:
            return
        _atomic_write_json(_LIVE_PRICES_DISK_PATH, snapshot)
    except Exception as e:
        logger.warning("_save_live_prices_to_disk hatası: %s", e)


def _load_live_prices_from_disk():
    """Web worker: _live_prices'ı diskten yükler (yfinance yapmadan)."""
    try:
        if not os.path.exists(_LIVE_PRICES_DISK_PATH):
            return
        with open(_LIVE_PRICES_DISK_PATH, "r", encoding="utf-8") as f:
            d = json.load(f)
        if isinstance(d, dict) and d:
            with _lock:
                _live_prices.update(d)
            logger.debug("_load_live_prices_from_disk: %d fiyat yüklendi", len(d))
    except Exception as e:
        logger.warning("_load_live_prices_from_disk hatası: %s", e)


def background_global_prices():
    # CPO-558 (11.06.2026): REFRESH_WORKER guard — web worker'da yfinance yasak
    _rw = os.environ.get("REFRESH_WORKER", "")
    if _rw == "web":
        logger.info("background_global_prices: REFRESH_WORKER=web — global fiyatlar background_live_prices disk-reload ile güncellenir")
        return
    elif _rw == "1":
        logger.info("background_global_prices: REFRESH_WORKER=1 — bist30-refresh.service lider modu")
    # CPO-520 P0 (07.06.2026): _is_macro_leader fcntl ile multi-worker fan-out önlendi
    # (4 worker × kripto+emtia+ABD multi yfinance download = 25 ticker × 4 = 100 paralel call → deadlock)
    if not _is_macro_leader():
        logger.info("background_global_prices: non-leader worker — atlandı")
        return
    logger.info("background_global_prices: LEADER worker — fetch modu (60s)")
    time.sleep(60)  # CPO-592v3: startup delay — refresh_data() ilk analyze batch'ini tamamlasın
    while True:
        try:
            fetch_global_prices()
        except Exception as e:
            logger.error("background_global_prices hatası: %s", e, exc_info=True)
        time.sleep(60)


def background_live_prices():
    # CPO-558 (11.06.2026): REFRESH_WORKER guard — web worker'da yfinance yasak
    _rw = os.environ.get("REFRESH_WORKER", "")
    if _rw == "web":
        logger.info("background_live_prices: REFRESH_WORKER=web — disk-reload only modu (30s)")
        while True:
            try:
                _load_live_prices_from_disk()
            except Exception as e:
                logger.error("background_live_prices disk-reload hatası: %s", e)
            time.sleep(30)
        return  # ulaşılmaz
    elif _rw == "1":
        logger.info("background_live_prices: REFRESH_WORKER=1 — bist30-refresh.service lider modu")
    # CPO-520 P0 (07.06.2026): _is_macro_leader fcntl ile multi-worker fan-out önlendi
    # (4 worker × BIST30 multi yfinance.download = 30 ticker × 4 = 120 paralel call → deadlock)
    if not _is_macro_leader():
        logger.info("background_live_prices: non-leader worker — atlandı")
        return
    logger.info("background_live_prices: LEADER worker — fetch modu (30s)")
    time.sleep(30)  # CPO-592v3: startup delay — refresh_data() ilk analyze batch'ini tamamlasın
    while True:
        try:
            fetch_live_prices()
        except Exception as e:
            logger.error("background_live_prices hatası: %s", e, exc_info=True)
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
    # CPO-551 Aşama 4: REFRESH_WORKER env ile web/refresh service ayrımı.
    # REFRESH_WORKER=web  → sadece disk-reload (bist30.service web workers)
    # REFRESH_WORKER=1    → her zaman lider, yfinance yapar (bist30-refresh.service)
    # REFRESH_WORKER unset → eski davranış: lider seçimi + yfinance (geriye dönük uyumluluk)
    _rw = os.environ.get("REFRESH_WORKER", "")
    if _rw == "web":
        logger.info("background_refresh: REFRESH_WORKER=web — disk-reload only modu")
        # CPO-591: PID*7%90 → sequential PID'ler 7s arayla stagger alır (0-89s).
        # Önceki PID%4*23: iki worker aynı stagger (0) alabiliyordu → eş zamanlı reload.
        _stagger = (os.getpid() * 7) % 90
        logger.info("background_refresh: worker stagger %ds (pid=%d)", _stagger, os.getpid())
        if _stagger:
            time.sleep(_stagger)
        while True:
            try:
                _load_cache_from_disk()
                _load_macro_from_disk()
            except Exception as e:
                logger.error("web disk-reload hatası: %s", e)
            time.sleep(90)
        return  # ulaşılmaz
    if _rw == "1":
        logger.info("background_refresh: REFRESH_WORKER=1 — bist30-refresh.service lider modu")
        # lider seçimi bypass: refresh.service tek process, her zaman lider
    # MSG-140: Sadece leader worker yfinance ağır işi yapar (504 worker hang fix).
    # Non-leader 3 worker hafif disk-reload — cache leader'dan tazelenir, gevent bloke olmaz.
    if _rw != "1" and not _is_bg_leader():
        logger.info("background_refresh: non-leader worker — hafif disk-reload modu (90s)")
        while True:
            try:
                _load_cache_from_disk()
                _load_macro_from_disk()
            except Exception as e:
                logger.error("background_refresh non-leader reload hatası: %s", e)
            time.sleep(90)
        return  # ulaşılmaz

    logger.info("background_refresh: LEADER worker — yfinance refresh modu (900s)")
    # CPO-495 FIX (06.06.2026): refresh_data() ÖNCE — chart hang BIST30 sinyal akışını engellemesin.
    # Önceki sıra: 11 chart refresh → refresh_data — biri hang olunca refresh_data() ASLA çağrılmıyordu
    # (kanıt: 04.06 21:24'ten beri updated_at donmuş, 5+ saat seans içinde stale veri).
    # Yeni sıra: refresh_data ÖNCE, sonra her chart refresh AYRI try/except (biri hang diğerlerini bozmaz).
    _CHART_REFRESH_TASKS = [
        ("refresh_chart",                  refresh_chart,         ()),
        ("refresh_xu100_chart",            refresh_xu100_chart,   ()),
        ("varlik_chart_BTC",      _refresh_varlik_chart, ("BTC",      _btc_chart_cache)),
        ("varlik_chart_ALTIN",    _refresh_varlik_chart, ("ALTIN",    _altin_chart_cache)),
        ("varlik_chart_GUMUS",    _refresh_varlik_chart, ("GUMUS",    _gumus_chart_cache)),
        ("varlik_chart_ETH",      _refresh_varlik_chart, ("ETH",      _eth_chart_cache)),
        ("varlik_chart_SP500",    _refresh_varlik_chart, ("SP500",    _sp500_chart_cache)),
        ("varlik_chart_NASDAQ",   _refresh_varlik_chart, ("NASDAQ",   _nasdaq_chart_cache)),
        ("varlik_chart_SOL",      _refresh_varlik_chart, ("SOL",      _sol_chart_cache)),
        ("varlik_chart_BNB",      _refresh_varlik_chart, ("BNB",      _bnb_chart_cache)),
        ("varlik_chart_PETROL",   _refresh_varlik_chart, ("PETROL",   _petrol_chart_cache)),
        ("varlik_chart_DOGALGAZ", _refresh_varlik_chart, ("DOGALGAZ", _dogalgaz_chart_cache)),
    ]
    # CPO-505 FIX (06.06.2026 P0): refresh_data() ve chart refresh'leri WATCHDOG ile sarıldı.
    # 06.06 06:28'de leader thread dondu → updated_at 4h sabit, /hisse flapping DOWN (worker hang).
    # Watchdog: her ağır iş ThreadPoolExecutor ile timeout-bounded — N dk geçerse skip + sonraki cycle.
    import concurrent.futures as _cf
    _REFRESH_DATA_TIMEOUT = 240   # 4 dakika (30 ticker × ~8s yfinance soft-cap)
    _CHART_TASK_TIMEOUT   = 60    # 1 dakika per chart refresh
    _executor = _cf.ThreadPoolExecutor(max_workers=2, thread_name_prefix="bg_refresh_wd")

    def _run_with_timeout(name, fn, args=(), timeout=60):
        """Watchdog wrapper: fn'i ayrı thread'de çalıştır, timeout'ta cancel + log + devam."""
        future = _executor.submit(fn, *args)
        try:
            future.result(timeout=timeout)
            return True
        except _cf.TimeoutError:
            logger.error("WATCHDOG: %s %ds timeout — skip (worker bloke olmasın)", name, timeout)
            # Future'ı cancel et (zaten çalışıyor ama future referansını bırak)
            future.cancel()
            return False
        except Exception as e:
            logger.error("%s hatası: %s", name, e, exc_info=True)
            return False

    # CPO-596: Loop-level watchdog — eğer 30dk'da döngü tamamlanmazsa process çık, systemd restart etsin.
    _bg_loop_last_ts = [time.time()]

    def _bg_loop_watchdog():
        while True:
            time.sleep(120)
            age = time.time() - _bg_loop_last_ts[0]
            if age > 1800:  # 30 dakika
                logger.critical("background_refresh watchdog: loop %ds dondu — process çıkıyor (restart bekleniyor)", int(age))
                import os as _os; _os._exit(2)

    import threading as _thr
    _thr.Thread(target=_bg_loop_watchdog, daemon=True, name="bg_refresh_watchdog").start()

    while True:
        _bg_loop_last_ts[0] = time.time()
        # 1) BIST30 ana refresh — watchdog'lu (4dk timeout)
        logger.info("background_refresh: refresh_data() başlıyor")
        ok = _run_with_timeout("refresh_data", refresh_data, (), _REFRESH_DATA_TIMEOUT)
        if ok:
            logger.info("background_refresh: refresh_data() tamamlandı")

        # 2) Stale chart cache purge — kısa, watchdog'suz (lock-swap only)
        try:
            _purge_stale_chart_caches()
        except Exception as e:
            logger.error("_purge_stale_chart_caches() hatası: %s", e, exc_info=True)

        # 3) Chart refresh'leri — her biri watchdog'lu (1dk timeout) + isolated
        for task_name, fn, args in _CHART_REFRESH_TASKS:
            _run_with_timeout(task_name, fn, args, _CHART_TASK_TIMEOUT)
            time.sleep(5)  # CPO-583: inter-chart throttle — pandas spike aralarında CPU soğutur

        time.sleep(900)


# ── Güvenlik Headerları ───────────────────────────────────────────────────────
@app.after_request
def set_security_headers(response):
    """Security headers — Cloudflare zaten X-Frame/X-CTO/Referrer/Permissions/HSTS ekliyor.
    Biz sadece CF'in eklemediği header'ları + CSP'yi (CF eklemiyor) ekliyoruz."""
    # CSP — GA4 + Google Fonts + Cloudflare Insights (HTML only)
    if response.content_type and "text/html" in response.content_type:
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline' https://www.googletagmanager.com https://static.cloudflareinsights.com; "
            "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
            "connect-src 'self' https://fonts.googleapis.com https://www.google-analytics.com https://analytics.google.com https://stats.g.doubleclick.net https://cloudflareinsights.com; "
            "img-src 'self' data: https://www.google-analytics.com; "
            "font-src 'self' https://fonts.gstatic.com; "
            "frame-ancestors 'none'; "
            "form-action 'self'; "
            "base-uri 'self'; "
            "object-src 'none'; "
            "upgrade-insecure-requests;"
        )
    # CF'in EKLEMEDİĞİ header'lar (modern security):
    response.headers["X-DNS-Prefetch-Control"] = "on"
    response.headers["Cross-Origin-Opener-Policy"] = "same-origin-allow-popups"
    response.headers["Cross-Origin-Resource-Policy"] = "same-site"
    response.headers["X-Permitted-Cross-Domain-Policies"] = "none"
    # Server header'ı temizle (info leak)
    response.headers.pop("Server", None)
    # NOT: HSTS, X-Frame-Options, X-Content-Type-Options, Referrer-Policy, Permissions-Policy
    # Cloudflare tarafından ekleniyor — duplicate olmaması için biz eklemiyoruz.
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
    # ADX null fix (BUG-C1) — sector/name artık cache yazılırken ekleniyor
    for s in stocks:
        # Parse ADX from nested indicators if top-level is null
        if s.get("adx") is None:
            _adx_lbl = (s.get("indicators") or {}).get("adx", {}).get("label", "")
            try:
                s["adx"] = float(_adx_lbl.replace("ADX", "").strip()) if _adx_lbl else 0.0
            except (ValueError, TypeError):
                s["adx"] = 0.0
            _adx_val = (s.get("indicators") or {}).get("adx", {}).get("value", "")
            _parts = re.findall(r"[0-9]+", _adx_val)
            if len(_parts) >= 2:
                s["di_plus"]  = float(_parts[0])
                s["di_minus"] = float(_parts[1])
    # ── Stale-safe fields (CPO-551 Aşama 2) ─────────────────────────────────────
    with _lock:
        _lr_ts  = _cache.get("last_refresh_ts", 0) or 0
        _loading = _cache.get("loading", False)
    _now      = time.time()
    _age_s    = int(_now - _lr_ts) if _lr_ts else None
    _mkt_open = _market_open()
    if not _mkt_open:
        _dq = "fresh"
    elif _age_s is None or _age_s > 1800:
        _dq = "critical"
    elif _age_s > 900:
        _dq = "stale"
    else:
        _dq = "fresh"
    # ── /stale-safe fields ───────────────────────────────────────────────────────
    return safe_json({
        "stocks":       stocks,
        "updated_at":   _cache["updated_at"],
        "loading":      len(stocks) == 0,
        "sectors":      list(SECTORS.keys()),
        "data_quality": _dq,        # "fresh" | "stale" | "critical" (CPO-551)
        "stocks_age_s": _age_s,     # seconds since last refresh
        "refreshing":   _loading,   # True = background refresh aktif
        "data_freshness": build_data_freshness(),  # SPEC-014 B1
    })


# ── SPEC-018 BIST Heatmap MVP (Çar 27 May 2026, Ozan-direktif) ──────────────
# Vanilla squarified treemap için minimal JSON. Boyut = tier_score (market_cap
# v2'de fundamentals'tan eklenir). Renk = tier (Bronz/Gümüş/Altın) + signal.
@app.route("/api/heatmap")
def api_heatmap():
    with _lock:
        stocks_raw = list(_cache["data"])
    out = []
    for s in stocks_raw:
        out.append({
            "ticker":     s.get("ticker"),
            "name":       s.get("name") or s.get("ticker"),
            "sector":     s.get("sector") or "Diğer",
            "signal":     s.get("signal"),       # AL/SAT/BEKLE
            "tier":       s.get("tier"),         # standart/plus/premium/None
            "tier_score": s.get("tier_score", 0),
            "price":      s.get("price"),
            "change_pct": s.get("change_pct"),
        })
    return safe_json({
        "stocks":     out,
        "updated_at": _cache["updated_at"],
        "loading":    len(out) == 0,
        "sectors":    list(SECTORS.keys()),
        "data_freshness": build_data_freshness(),
    })


@app.route("/heatmap")
def heatmap_page():
    return render_template("heatmap.html")



# ── Makro Haber RSS ──────────────────────────────────────────────────────────
import feedparser as _feedparser

_MACRO_RSS_SOURCES = [
    ("Reuters TR",  "https://tr.reuters.com/rssFeed/businessNews"),
    ("Bloomberg HT", "https://www.bloomberght.com/rss"),
    ("Dünya",        "https://www.dunya.com/rss/ekonomi.xml"),
    ("Haberler.com", "https://www.haberler.com/ekonomi/rss/"),
    ("AA Ekonomi",   "https://www.aa.com.tr/tr/rss/default?cat=ekonomi"),
]

_macro_news_cache: list = []
_macro_news_ts: float   = 0.0
_MACRO_NEWS_TTL         = 1800  # 30 dk

def _fetch_macro_rss_once() -> list:
    results = []
    cutoff  = datetime.now() - timedelta(hours=24)
    for source_name, url in _MACRO_RSS_SOURCES:
        try:
            feed = _feedparser.parse(url)
            for entry in (feed.entries or [])[:6]:
                try:
                    parsed = entry.get("published_parsed") or entry.get("updated_parsed")
                    if parsed:
                        pub = datetime(*parsed[:6])
                    else:
                        pub = datetime.now()
                    if pub < cutoff:
                        continue
                    title = (entry.get("title") or "").strip()
                    link  = (entry.get("link")  or "").strip()
                    if not title:
                        continue
                    results.append({
                        "title":     title,
                        "url":       link,
                        "source":    source_name,
                        "published": pub.strftime("%H:%M"),
                        "date_str":  pub.strftime("%d.%m"),
                        "pub_ts":    pub.timestamp(),   # gerçek timestamp → doğru sıralama
                        "category":  "makro",
                    })
                except Exception:
                    continue
        except Exception as e:
            logger.debug("RSS fetch [%s]: %s", source_name, e)
    # pub_ts ile sırala — sadece saat string'i değil, tam tarih+saat kullanılır
    results.sort(key=lambda x: x.get("pub_ts", 0), reverse=True)
    return results[:20]

def _macro_news_bg_loop():
    global _macro_news_cache, _macro_news_ts
    while True:
        try:
            news = _fetch_macro_rss_once()
            if news:
                _macro_news_cache = news
                _macro_news_ts    = time.time()
                logger.info("Makro RSS: %d haber", len(news))
        except Exception as e:
            logger.debug("Makro RSS loop: %s", e)
        time.sleep(_MACRO_NEWS_TTL)

threading.Thread(target=_macro_news_bg_loop, daemon=True, name="macro-rss").start()


# ── Ekonomik Takvim ───────────────────────────────────────────────────────────
ECONOMIC_CALENDAR_2026 = [
    # TCMB Para Politikası Kurulu Toplantıları
    {"date": "2026-05-22", "event": "TCMB Para Politikası Kurulu", "importance": "HIGH", "source": "TCMB", "icon": "🏦"},
    {"date": "2026-06-26", "event": "TCMB Para Politikası Kurulu", "importance": "HIGH", "source": "TCMB", "icon": "🏦"},
    {"date": "2026-07-23", "event": "TCMB Para Politikası Kurulu", "importance": "HIGH", "source": "TCMB", "icon": "🏦"},
    # TUIK Enflasyon Verileri
    {"date": "2026-05-05", "event": "TÜFE Nisan 2026", "importance": "HIGH", "source": "TUIK", "icon": "📊"},
    {"date": "2026-06-03", "event": "TÜFE Mayıs 2026", "importance": "HIGH", "source": "TUIK", "icon": "📊"},
    {"date": "2026-07-03", "event": "TÜFE Haziran 2026", "importance": "HIGH", "source": "TUIK", "icon": "📊"},
    # Fed Faiz Kararları
    {"date": "2026-05-07", "event": "Fed Faiz Kararı", "importance": "HIGH", "source": "FED", "icon": "🇺🇸"},
    {"date": "2026-06-18", "event": "Fed Faiz Kararı", "importance": "HIGH", "source": "FED", "icon": "🇺🇸"},
    {"date": "2026-07-30", "event": "Fed Faiz Kararı", "importance": "HIGH", "source": "FED", "icon": "🇺🇸"},
    # Bilanço Dönemleri
    {"date": "2026-05-15", "event": "1Ç 2026 Bilanço Son Günü (ilk açıklamalar)", "importance": "MED", "source": "KAP", "icon": "📋"},
    {"date": "2026-08-14", "event": "2Ç 2026 Bilanço Son Günü", "importance": "MED", "source": "KAP", "icon": "📋"},
    # Türkiye büyüme verisi
    {"date": "2026-05-30", "event": "1Ç 2026 GSYH Büyüme", "importance": "HIGH", "source": "TUIK", "icon": "📈"},
    # BIST genel
    {"date": "2026-06-01", "event": "BIST Aylık İşlem İstatistikleri", "importance": "LOW", "source": "BIST", "icon": "📉"},
]

@app.route("/api/economic-calendar")
@limiter.limit("60 per minute")
def api_economic_calendar():
    """Ekonomik takvim — yaklaşan ve son 7 günün önemli olayları."""
    today = datetime.now().date()
    all_events = []
    for e in ECONOMIC_CALENDAR_2026:
        try:
            ev_date = datetime.strptime(e["date"], "%Y-%m-%d").date()
            delta   = (ev_date - today).days
            e2 = dict(e)
            e2["days_until"] = delta
            e2["date_fmt"]   = ev_date.strftime("%d.%m.%Y")
            e2["is_today"]   = (delta == 0)
            e2["is_past"]    = (delta < 0)
            all_events.append(e2)
        except Exception:
            continue
    upcoming = sorted([e for e in all_events if not e["is_past"]], key=lambda x: x["days_until"])
    recent   = sorted([e for e in all_events if e["is_past"] and e["days_until"] >= -7],
                       key=lambda x: x["days_until"], reverse=True)
    return safe_json({
        "upcoming": upcoming[:6],
        "recent":   recent[:3],
        "today":    [e for e in upcoming if e["is_today"]],
    })

@app.route("/api/macro-news")
@limiter.limit("60 per minute")
def api_macro_news():
    """Makro ekonomi haberleri — RSS tabanlı."""
    return safe_json({
        "items":      _macro_news_cache,
        "updated_at": datetime.fromtimestamp(_macro_news_ts).strftime("%H:%M")
                        if _macro_news_ts else "—",
        "count":      len(_macro_news_cache),
    })

@app.route("/api/refresh", methods=["POST"])
@limiter.limit("1 per 5 minutes")
def api_refresh():
    require_admin()
    threading.Thread(target=refresh_data, daemon=True).start()
    return jsonify({"status": "refreshing"})


# MSG-019B: Daily digest manuel tetikleyici (token korumalı)
# Pending boş olsa bile force=true ile test mail göndermek için.
# Auth: Authorization: Bearer <ADMIN_TOKEN> + localhost-only.
@app.route("/admin/send-digest-now", methods=["POST"])
@limiter.limit("3 per hour")
def admin_send_digest_now():
    # Layer 1: ADMIN_TOKEN header zorunlu (Bearer auth)
    if not ADMIN_TOKEN:
        return jsonify({"error": "ADMIN_TOKEN configured değil (env eksik)"}), 503
    auth_header = request.headers.get("Authorization", "")
    expected = f"Bearer {ADMIN_TOKEN}"
    if auth_header != expected:
        logger.warning("admin_send_digest_now: invalid auth header (token mismatch)")
        abort(401)

    # Layer 2: sadece localhost erişebilir (nginx X-Forwarded-For kontrolü)
    # Production'da nginx 127.0.0.1 → app, public requests'te remote_addr farklı olur.
    # Yine de defense-in-depth için kontrol.
    remote = request.headers.get("X-Forwarded-For", request.remote_addr or "")
    remote_first = remote.split(",")[0].strip()
    if remote_first not in ("127.0.0.1", "::1", "localhost"):
        logger.warning("admin_send_digest_now: non-localhost erişim engellendi (remote=%s)", remote_first)
        return jsonify({"error": "Sadece localhost'tan erişilebilir"}), 403

    # Params
    timeframe = (request.args.get("timeframe") or "daily").strip()
    if timeframe not in ("daily", "weekly"):
        return jsonify({"error": "timeframe daily|weekly olmalı"}), 400
    force = (request.args.get("force") or "false").strip().lower() in ("1", "true", "yes")

    logger.info("admin_send_digest_now: timeframe=%s, force=%s tetiklendi", timeframe, force)
    result = _send_digest_emails(timeframe=timeframe, force=force)
    return jsonify({
        "triggered": True,
        "timeframe": timeframe,
        "force": force,
        "result": result,
    })


# ── Makro Veri Bandı ─────────────────────────────────────────────────────────
_macro_cache = {"data": None, "ts": 0}
_MACRO_DISK_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "last_macro.json")

def _save_macro_to_disk(data, ts):
    """Macro cache'i diske yaz — restart sonrası cold start'tan kurtarır."""
    try:
        with open(_MACRO_DISK_PATH, "w") as f:
            import json as _j
            _j.dump({"data": data, "ts": ts}, f)
    except Exception as e:
        logger.debug("_save_macro_to_disk: %s", e)

def _load_macro_from_disk():
    """Startup'ta diskten macro cache'i yükle — soğuk başlangıç süresini sıfırlar."""
    try:
        if os.path.exists(_MACRO_DISK_PATH):
            with open(_MACRO_DISK_PATH) as f:
                import json as _j
                d = _j.load(f)
            if isinstance(d, dict) and d.get("data"):
                _macro_cache["data"] = d["data"]
                _macro_cache["ts"]   = d.get("ts", 0)
                logger.info("_load_macro_from_disk: %d items loaded", len(d["data"]))
    except Exception as e:
        logger.warning("_load_macro_from_disk: %s", e)


_macro_bg_lock = threading.Lock()   # Tek seferde 1 _fetch_macro garantisi
_macro_bg_stats = {"cycles": 0, "successes": 0, "empty_results": 0, "exceptions": 0, "last_success_ts": 0, "last_error": None, "startup_ts": time.time()}

def _macro_bg_loop():
    """Background macro refresh thread — her 3 dakika.

    CPO-520 FIX (07.06.2026): fcntl leader-lock eklendi.
    CPO-558 FIX (11.06.2026): REFRESH_WORKER guard eklendi — web worker yfinance yasak.
    Önceki: 4 worker × _macro_bg_lock (proses-içi, paylaşımsız) → her worker 10 ticker fast_info
    → 40 paralel yfinance call → gevent+threading hybrid corruption → /hisse 20s deadlock.
    Yeni: _is_macro_leader() fcntl.flock — yalnız 1 worker macro fetch yapar.
    Non-leader worker'lar hafif disk-reload modunda (90s aralık).
    """
    _rw = os.environ.get("REFRESH_WORKER", "")
    if _rw == "web":
        # CPO-591: PID*7%90 stagger — 4 worker aynı anda reload yapmasın (anti-storm).
        # Önceki: stagger yoktu → tüm worker'lar eş zamanlı json.load() → GIL burst → 15s blok.
        _mac_stagger = (os.getpid() * 7) % 90
        logger.info("_macro_bg_loop: REFRESH_WORKER=web — disk-reload only modu (90s), stagger %ds (pid=%d)", _mac_stagger, os.getpid())
        if _mac_stagger:
            time.sleep(_mac_stagger)
        while True:
            try:
                _load_macro_from_disk()
            except Exception as e:
                logger.error("_macro_bg_loop disk-reload hatası: %s", e)
            time.sleep(90)
        return  # ulaşılmaz
    elif _rw == "1":
        logger.info("_macro_bg_loop: REFRESH_WORKER=1 — bist30-refresh.service lider modu")
    if not _is_macro_leader():
        logger.info("_macro_bg_loop: non-leader worker — hafif disk-reload modu (90s)")
        while True:
            try:
                _load_macro_from_disk()
            except Exception as e:
                logger.error("_macro_bg_loop non-leader reload hatası: %s", e)
            time.sleep(90)
        return  # ulaşılmaz

    logger.info("_macro_bg_loop: LEADER worker — yfinance fetch modu (180s)")
    # İlk run hemen (cache cold ise warm yapsın)
    while True:
        # acquire(blocking=False): kilit alınmazsa skip — bir önceki cycle hâlâ devam ediyor
        if _macro_bg_lock.acquire(blocking=False):
            _macro_bg_stats["cycles"] += 1
            try:
                items = _fetch_macro()
                if items:
                    with _lock:
                        _macro_cache["data"] = items
                        _macro_cache["ts"]   = time.time()
                    _save_macro_to_disk(items, _macro_cache["ts"])
                    _macro_bg_stats["successes"] += 1
                    _macro_bg_stats["last_success_ts"] = time.time()
                    logger.info("_macro_bg_loop heartbeat: cycle=%d items=%d uptime=%ds",
                                _macro_bg_stats["cycles"], len(items),
                                int(time.time() - _macro_bg_stats.get("startup_ts", time.time())))
                else:
                    _macro_bg_stats["empty_results"] += 1
                    logger.warning("_macro_bg_loop: empty result, eski cache korunur (empty_count=%d)",
                                   _macro_bg_stats["empty_results"])
            except Exception as e:
                _macro_bg_stats["exceptions"] += 1
                _macro_bg_stats["last_error"] = str(e)[:200]
                logger.warning("_macro_bg_loop exception: %s (total=%d)", e, _macro_bg_stats["exceptions"])
            finally:
                _macro_bg_lock.release()
        else:
            logger.debug("_macro_bg_loop: previous cycle still running, skip")
        time.sleep(180)   # 3 dakika

# Disk load — _fetch_macro tanımlandıktan sonra thread başlatılır (aşağıda)
_load_macro_from_disk()

_MACRO_TTL   = 300   # 5 dakika cache (stale-while-revalidate)

_MACRO_TICKERS = [
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

def _fetch_macro_one(label, sym):
    """Tek bir ticker için fast_info çağrısı — timeout korumalı."""
    try:
        with _YF_GLOBAL_LOCK:
            tk  = yf.Ticker(sym)
            fi  = tk.fast_info
            price  = getattr(fi, "last_price", None) or getattr(fi, "regularMarketPrice", None)
            prev   = getattr(fi, "previous_close", None)
        if price is None or prev is None or prev == 0:
            return None
        change = round((float(price) - float(prev)) / float(prev) * 100, 2)
        return {"label": label, "price": round(float(price), 2), "change": change}
    except Exception as e:
        logger.debug("_fetch_macro_one %s: %s", label, e)
        return None


def _fetch_macro():
    """XU100, XU030, BTC, ALTIN, GUMUS, PETROL, USD/TRY, EUR/TRY, S&P500, NASDAQ anlık veri.

    Her ticker bağımsız try/except — biri hata verse bile diğerleri devam eder.
    """
    result = []
    for label, sym in _MACRO_TICKERS:
        item = _fetch_macro_one(label, sym)
        if item:
            result.append(item)
    return result


# Background macro refresh — _fetch_macro DEFINED olduktan SONRA başlat
threading.Thread(target=_macro_bg_loop, daemon=True, name="macro-bg-loop").start()


# Macro refresh — ARTIK SADECE bg loop (request-spawned thread leak'ini önle)
# _macro_refreshing global flag kaldırıldı (race condition kaynağıydı).
# Tek refresh path: _macro_bg_loop (module-level, 3dk periyodik).


@app.route("/api/macro")
@limiter.limit("60 per minute")
def api_macro():
    """Macro endpoint — SADECE cache döner, thread spawn YOK.

    Cache her zaman var (disk persistence + _macro_bg_loop her 3dk yeniler).
    İlk başlatmada cache boş ise _macro_bg_loop'un ilk run'ını bekler (max 3dk).
    O sırada [] döner (frontend graceful degrade).

    ARTITEKTÜR: yfinance çağrıları SADECE _macro_bg_loop (module-level thread).
    Request handler'lar yfinance ÇAĞRMAZ → infinite hang riski sıfır.
    """
    with _lock:
        cached_items = _macro_cache.get("data") or []
        cached_ts    = _macro_cache.get("ts", 0)
    stale = (time.time() - cached_ts) > _MACRO_TTL
    return safe_json({
        "items": cached_items,
        "cached": True,
        "stale": stale,
    })


# ── Günlük Makro AI Özeti ────────────────────────────────────────────────────
_macro_ai_cache: dict = {}   # {"text": str, "ts": float, "date": str}
_MACRO_AI_TTL   = 21600      # SPEC-009 Faz 2 B3: 4h→12h; SPEC-011 paketi: 12h→6h
                             # (makro hızlı değişir — freshness; KPI 245 req/gün stabil)
_macro_ai_refreshing = False  # arka plan yenileme kilidi

# SPEC-009 Faz 2 B2: macro-ai shared disk cache — leader Gemini çağrısını yapıp
# diske yazar, non-leader worker'lar diskten okur → 4× Gemini çağrısı yerine 1×.
_MACRO_AI_DISK_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "last_macro_ai.json")

def _atomic_write_json(path, data):
    """JSON'u atomic yazar — tempfile + fsync + os.replace (POSIX rename).
    Ozan/Madde 1: leader yazarken non-leader yarım dosya okumamalı (bozuk JSON
    / crash riski). os.replace aynı dosya sisteminde atomik."""
    dir_ = os.path.dirname(os.path.abspath(path))
    fd, tmp = tempfile.mkstemp(dir=dir_, suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, path)   # atomic
    except Exception:
        if os.path.exists(tmp):
            os.unlink(tmp)
        raise


def _save_macro_ai_to_disk():
    """Leader: macro-ai cache'i diske yazar (non-leader worker'lar okusun).
    Boş cache'i diske YAZMAZ — restart sonrası startup-load yarışı diskteki
    veriyi silmesin (empty-overwrite guard)."""
    try:
        if not _macro_ai_cache:
            return
        _atomic_write_json(_MACRO_AI_DISK_PATH, _macro_ai_cache)
    except Exception as e:
        logger.warning("_save_macro_ai_to_disk hatası: %s", e)

def _load_macro_ai_from_disk():
    """Non-leader: diskten macro-ai cache yükler (leader yazmış olabilir)."""
    try:
        if not os.path.exists(_MACRO_AI_DISK_PATH):
            return
        with open(_MACRO_AI_DISK_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, dict) and data.get("text"):
            _macro_ai_cache.update(data)
    except Exception as e:
        logger.warning("_load_macro_ai_from_disk hatası: %s", e)


def _do_macro_ai_refresh():
    """Makro özet Gemini çağrısını arka planda yapar — endpoint'i bloklamaz."""
    global _macro_ai_refreshing
    if _macro_ai_refreshing:
        return
    _macro_ai_refreshing = True
    try:
        with _lock:
            macro_items = _macro_cache.get("data") or []
        if not macro_items:
            macro_items = _fetch_macro()

        def _lbl(label):
            return next((m["price"] for m in macro_items if m.get("label") == label), None)

        xu100  = _lbl("XU100")
        xu100c = next((m.get("change") for m in macro_items if m.get("label") == "XU100"), None)
        usdtry = _lbl("USDTRY")
        gold   = _lbl("ALTIN")
        oil    = _lbl("PETROL")
        btc    = _lbl("BTC")

        today_str = datetime.now(_TZ_TR).strftime("%d %B %Y")
        lines = []
        if xu100:
            chg_str = ('%+.2f' % xu100c + '%') if xu100c is not None else '—'
            lines.append(f"BIST100: {xu100:,.0f} ({chg_str})")
        if usdtry: lines.append(f"USD/TRY: {usdtry:.4f}")
        if gold:   lines.append(f"Altın: {gold:,.0f} ₺/gr")
        if oil:    lines.append(f"Brent Petrol: {oil:.2f} USD")
        if btc:    lines.append(f"BTC: {btc:,.0f} USD")

        if not lines:
            return

        prompt = (
            f"Bugün {today_str}. Türk piyasaları anlık verileri:\n"
            + "\n".join(f"• {ln}" for ln in lines)
            + "\n\nKURAL: Sadece bu verileri yorumla. Spekülasyon yapma. Tahmin yapma.\n"
            "GÖREV: Bireysel yatırımcı için 2 cümlelik Türkçe piyasa özeti. "
            "Yatırım tavsiyesi verme. Giriş/kapanış cümlesi ekleme."
        )
        _, text = _gemini_call(prompt, _GEMINI_NEWS_ATTEMPTS, timeout=12, max_tokens=600, temperature=0.3)
        if text:
            now = time.time()
            today_s = datetime.now(_TZ_TR).strftime("%Y-%m-%d")
            _macro_ai_cache.update({"text": text, "ts": now, "date": today_s,
                                    "generated_at": datetime.now(_TZ_TR).strftime("%H:%M")})
            logger.info("_do_macro_ai_refresh: tamamlandi")
    except Exception as e:
        logger.warning("_do_macro_ai_refresh: hata — %s", e)
    finally:
        _macro_ai_refreshing = False


@app.route("/api/macro-summary")
@limiter.limit("30 per minute")
def api_macro_summary():
    """Günlük makro ekonomi özeti — Gemini ile üretilir, 4 saat cache'lenir.
    Stale-while-revalidate: cache varsa anında döner, arka planda yeniler."""
    now     = time.time()
    today_s = datetime.now(_TZ_TR).strftime("%Y-%m-%d")
    cached  = _macro_ai_cache

    cache_fresh = (cached.get("date") == today_s
                   and (now - cached.get("ts", 0)) < _MACRO_AI_TTL)

    # Stale + bu worker gemini-leader ise → arka planda yenile (4× çağrı fix).
    # Non-leader yenilemez; gemini-cache-sync timer thread'i diskteki leader
    # cache'ini periyodik (90s) yükler → in-memory'den serve eder (inline I/O YOK, #38).
    if not cache_fresh and not _macro_ai_refreshing and _is_gemini_leader():
        threading.Thread(target=_do_macro_ai_refresh, daemon=True,
                         name="macro-ai-refresh").start()

    if cached.get("text"):
        return safe_json({"summary": cached["text"], "cached": cache_fresh,
                          "generated_at": cached.get("generated_at", "")})
    return safe_json({"summary": "", "cached": False})


@app.route("/api/market-summary")
@limiter.limit("60 per minute")
def api_market_summary():
    """Feature 1 #1A — Bugünün Özeti hero card data (CPO MSG-054 onayı).

    Sabit 3-cümle şablon için backend compute:
      Cümle 1: BIST'de bugün N hisse güçlü trende geçti (topTickers)
      Cümle 2: <hottestSector> sektörü en güçlü ivmesinde, ortalama %X
      Cümle 3: Genel sinyal dağılımı dünden +N güçlü/zayıf

    Snapshot pattern: _SNAPSHOTS_DIR/<YYYY-MM-DD>.json (mevcut, _save_daily_snapshot kullanılır)
    """
    with _lock:
        stocks = list(_cache.get("data") or [])
    if not stocks:
        return jsonify({"loading": True}), 200

    # BIST hisseleri (XU030 hariç)
    bist = [s for s in stocks if s.get("ticker") != "XU030"]
    new_bull = [s for s in bist if s.get("is_new_signal") and s.get("signal") == "AL"]
    new_bear = [s for s in bist if s.get("is_new_signal") and s.get("signal") == "SAT"]
    all_bull = [s for s in bist if s.get("signal") == "AL"]

    # Top tickers (en taze 4 AL)
    top_tickers = [s.get("ticker") for s in new_bull[:8] if s.get("ticker")]

    # Hottest sector — change_pct avg max (en az 2 hisse, mock güvenilirlik)
    sector_agg = {}
    for s in bist:
        sec = s.get("sector")
        if not sec or sec == "Diğer":
            continue
        agg = sector_agg.setdefault(sec, {"sum": 0.0, "count": 0})
        try:
            agg["sum"] += float(s.get("change_pct") or 0)
            agg["count"] += 1
        except Exception:
            pass

    hottest_sector = None
    sector_change = 0.0
    max_avg = float("-inf")
    for name, agg in sector_agg.items():
        if agg["count"] < 2:
            continue
        avg = agg["sum"] / agg["count"]
        if avg > max_avg:
            max_avg = avg
            hottest_sector = name
            sector_change = round(avg, 1)

    # Dün snapshot ile delta (al_count fark)
    delta = 0
    try:
        from datetime import timedelta as _td
        ydate = (datetime.now(_TZ_TR) - _td(days=1)).strftime("%Y-%m-%d")
        yfile = os.path.join(_SNAPSHOTS_DIR, f"{ydate}.json")
        if os.path.exists(yfile):
            with open(yfile, encoding="utf-8") as f:
                ysnap = json.load(f)
            delta = len(all_bull) - int(ysnap.get("al_count") or 0)
    except Exception as e:
        logger.debug("market-summary delta hesabı: %s", e)

    # Market status (TR saatine göre)
    now_tr = datetime.now(_TZ_TR)
    weekday = now_tr.weekday()  # 0=Pzt, 6=Pzr
    hour = now_tr.hour
    is_weekend = weekday >= 5
    market_open_hours = (10 <= hour < 18) and not is_weekend
    market_status = "open" if market_open_hours else "closed"

    closed_msg = None
    if not market_open_hours:
        if is_weekend:
            closed_msg = "Borsa hafta sonu kapalı. Pazartesi 10:00'da tekrar görüşelim."
        elif hour < 10:
            closed_msg = "BIST henüz açılmadı. 10:00'da seans başlar."
        else:
            closed_msg = "BIST seansı kapandı. Yarın 10:00'da tekrar görüşelim."

    return jsonify({
        "asOfTime": now_tr.strftime("%H:%M"),
        "marketStatus": market_status,
        "closedMessage": closed_msg,
        "newBullCount": len(new_bull),
        "newBearCount": len(new_bear),
        "topTickers": top_tickers,
        "hottestSector": hottest_sector,
        "sectorChange": sector_change,
        "delta": delta,
        "totalBullCount": len(all_bull),
        # watchlistMoved: client-side hesaplanır (watchlist localStorage)
    })


@app.route("/api/stream")
def api_stream():
    client_queue = collections.deque()
    with _sse_lock:
        _sse_clients.append(client_queue)

    with _lock:
        initial = dict(_live_prices)
    initial_msg = (
        f"data: {json.dumps({'type': 'prices', 'data': initial, 'ts': datetime.now(_TZ_TR).strftime('%H:%M:%S')})}\n\n"
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
        with _YF_GLOBAL_LOCK:
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
_stock_chart_cache = {}          # {ticker: {"data": ..., "ts": float, "updated_at": str, "v": str}}

# SPEC-DECOUPLING-v2-PHASE3 (CPO-437): Per-ticker chart cache disk path.
# Staging: BIST_STAGING=1 ENV → data-staging/charts/, prod → data/charts/ (Phase-3 sonrası).
_PHASE3_CHART_DIR = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "data-staging" if os.getenv("BIST_STAGING") == "1" else "data",
    "charts"
)
_phase3_chart_mtimes = {}  # {ticker: mtime} — per-ticker mtime guard


def _load_chart_from_disk_per_ticker(ticker):
    """Phase-3: Per-ticker chart_<T>.json disk-read (lazy, mtime guard).

    Returns (data, updated_at) or (None, None) if no cache.
    """
    path = os.path.join(_PHASE3_CHART_DIR, f"chart_{ticker}.json")
    try:
        if not os.path.exists(path):
            return None, None
        mt = os.path.getmtime(path)
        # In-memory cache hit + mtime aynı → SKIP disk read (mtime guard)
        cached = _stock_chart_cache.get(ticker)
        if cached and _phase3_chart_mtimes.get(ticker) == mt:
            return cached.get("data"), cached.get("updated_at")
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        if not data:
            return None, None
        upd = (data.get("summary") or {}).get("updated_at") or datetime.fromtimestamp(mt, _TZ_TR).strftime("%d.%m.%Y %H:%M:%S")
        with _lock:
            _stock_chart_cache[ticker] = {
                "data": data, "ts": mt, "updated_at": upd, "v": _CHART_CACHE_VERSION
            }
            _phase3_chart_mtimes[ticker] = mt
        return data, upd
    except Exception as e:
        logger.debug("_load_chart_from_disk_per_ticker %s: %s", ticker, e)
        return None, None
_STOCK_CACHE_TTL   = 900         # 15 dakika
_CHART_CACHE_VERSION = "1.0"     # SPEC-008 L4a — schema bumpu temiz invalidation
                                 # için. Entry "v" alanı uyuşmuyorsa cache miss say
                                 # (deploy-zamanı şema değişiminde eski cache yok sayılır).

# SPEC-008 L5 — Sayaçlar yukarıda (modül-load sırası) tanımlandı.
# Detay: api_stock_chart integrity_error döndüğünde {ticker: ts} yazılır.
# Alarm loop 5dk'da bir son 10dk içindeki ticker sayısını kontrol eder;
# eşiği aşarsa logger.error ile journalctl alarm pattern düşürür.


# ── Gemini API — AI haber özeti & sinyal açıklaması ─────────────────────────
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")

# Cache yapıları
# failed=True → negatif cache (başarısız istek, kısa TTL)
_news_cache           = {}   # {ticker: {"text": str|None, "ts": float, "failed": bool}}
_NEWS_CACHE_TTL       = 3600 * 6   # 6 saat — başarılı yanıt
_NEWS_FAIL_TTL        = 300        # 5 dakika — başarısız yanıt (negatif cache)

# SPEC-009 Faz 2 B2: news cache shared disk — herhangi worker Gemini'den haber
# çekince diske yazar; başka worker aynı ticker'ı çekmeden önce diskten okur →
# 4× Gemini çağrısı yerine ~1× (cross-worker dedup). Leader-gate gerekmez:
# dedup get_ai_news içindeki disk-check ile olur (her worker kendi isteğini servis eder).
_NEWS_CACHE_DISK_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "last_news_cache.json")

def _save_news_cache_to_disk():
    """News cache'i diske yazar (cross-worker dedup). _lock DIŞINDA çağrılmalı."""
    try:
        with _lock:
            snapshot = dict(_news_cache)
        if not snapshot:
            return   # empty-overwrite guard — diskteki veriyi silme
        _atomic_write_json(_NEWS_CACHE_DISK_PATH, snapshot)
    except Exception as e:
        logger.warning("_save_news_cache_to_disk hatası: %s", e)

def _load_news_cache_from_disk():
    """Diskten news cache merge — ticker başına en taze (ts) kazanır. _lock DIŞINDA."""
    try:
        if not os.path.exists(_NEWS_CACHE_DISK_PATH):
            return
        with open(_NEWS_CACHE_DISK_PATH, "r", encoding="utf-8") as f:
            disk = json.load(f)
        if not isinstance(disk, dict):
            return
        with _lock:
            for tk, dentry in disk.items():
                if not isinstance(dentry, dict):
                    continue
                mem = _news_cache.get(tk)
                if not mem or dentry.get("ts", 0) > mem.get("ts", 0):
                    _news_cache[tk] = dentry
    except Exception as e:
        logger.warning("_load_news_cache_from_disk hatası: %s", e)

# ── SPEC-011 L4 / SPEC-013 — Şirket AI özeti (LLM referral + bounce reduction) ──
# Hisse detay sayfasına özgün metin: Gemini ile 2 paragraf şirket özeti.
# TTL 30 gün (şirket profili nadiren değişir) → ayda ~215 çağrı, marjinal maliyet.
# Üretim leader-only bg prefetch'te (#30 maliyet pattern); request path'te asla.
_company_summary_cache = {}              # {ticker: {"text": str, "ts": float}}
_COMPANY_SUMMARY_TTL   = 30 * 86400      # 30 gün
_COMPANY_SUMMARY_PATH  = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "last_company_summary.json")

_COMPANY_SUMMARY_PROMPT = (
    "Sen finansal yazılım için içerik üreticisin. Türkçe BIST hissesi {ticker} "
    "({name}) hakkında 2 paragraf özet yaz.\n\n"
    "KURAL:\n"
    "1. İlk paragraf 2-3 cümle: Şirket ne yapıyor, hangi sektörde, ana iş kolu.\n"
    "2. İkinci paragraf 2-3 cümle: Pazardaki konumu, yatırımcı için önemli faktörler.\n"
    "3. Yatırım tavsiyesi YOK, sadece bilgi.\n"
    "4. Maksimum 150 kelime toplam. Net, kısa cümleler.\n"
    "5. Sadece düz metin — başlık yok, markdown yok, madde işareti yok.\n\n"
    "Çıktı: sadece 2 paragraf."
)

def _save_company_summary_to_disk():
    """Şirket özeti cache'i diske yazar (atomic). _lock DIŞINDA çağrılmalı."""
    try:
        with _lock:
            snapshot = dict(_company_summary_cache)
        if not snapshot:
            return   # empty-overwrite guard — restart sonrası 30g cache'i koru
        _atomic_write_json(_COMPANY_SUMMARY_PATH, snapshot)
    except Exception as e:
        logger.warning("_save_company_summary_to_disk hatası: %s", e)

def _load_company_summary_from_disk():
    """Diskten şirket özeti merge — ticker başına en taze kazanır. _lock DIŞINDA."""
    try:
        if not os.path.exists(_COMPANY_SUMMARY_PATH):
            return
        with open(_COMPANY_SUMMARY_PATH, "r", encoding="utf-8") as f:
            disk = json.load(f)
        if not isinstance(disk, dict):
            return
        with _lock:
            for tk, dentry in disk.items():
                if not isinstance(dentry, dict):
                    continue
                mem = _company_summary_cache.get(tk)
                if not mem or dentry.get("ts", 0) > mem.get("ts", 0):
                    _company_summary_cache[tk] = dentry
    except Exception as e:
        logger.warning("_load_company_summary_from_disk hatası: %s", e)

def get_company_summary(ticker):
    """Şirket AI özeti — in-memory cache okur; yoksa/bayatsa None (graceful)."""
    now = time.time()
    with _lock:
        cached = _company_summary_cache.get(ticker)
    if cached and (now - cached.get("ts", 0)) < _COMPANY_SUMMARY_TTL:
        return cached.get("text") or None
    return None

def _generate_company_summary(ticker):
    """Gemini ile şirket özeti üretir + cache'ler. Yalnız bg thread'den çağrılmalı."""
    if not GEMINI_API_KEY:
        return None
    name = STOCK_NAMES.get(ticker, ticker)
    prompt = _COMPANY_SUMMARY_PROMPT.format(ticker=ticker, name=name)
    model, text = _gemini_call(prompt, _GEMINI_EXPLAIN_ATTEMPTS,
                               timeout=20, max_tokens=400, temperature=0.4)
    if text:
        with _lock:
            _company_summary_cache[ticker] = {"text": text.strip(), "ts": time.time()}
        logger.info("company-summary [%s]: OK [model=%s]", ticker, model)
        return text.strip()
    return None


def _news_ttl_for(ticker: str) -> int:
    """Dinamik TTL: aktif sinyalli/hacimli hisseler kısa TTL, durgun hisseler uzun TTL.

    - AL/SAT sinyalli: 6h (aktif iş, sık güncelle)
    - vol_ratio >= 1.0: 6h (hacimli)
    - vol_ratio 0.5-1.0: 12h (orta)
    - vol_ratio < 0.5: 24h (durgun, gemini çağrısını azalt)
    """
    with _lock:
        for s in _cache.get("data", []):
            if s.get("ticker") == ticker:
                if s.get("signal") in ("AL", "SAT"):
                    return _NEWS_CACHE_TTL
                vr = s.get("vol_ratio") or 1.0
                if vr < 0.5:
                    return 3600 * 24
                if vr < 1.0:
                    return 3600 * 12
                return _NEWS_CACHE_TTL
    return _NEWS_CACHE_TTL



# On-demand news fetch kuyruğu (market-news endpoint'i tarafından doldurulur)
_news_fetch_queue     = set()      # tickers waiting for background fetch
_news_queue_lock      = threading.Lock()

_signal_explain_cache = {}   # {ticker: {"text": str|None, "sig": str, "ts": float, "failed": bool}}
_SIG_EXPLAIN_TTL      = 3600 * 12  # SPEC-009 Faz 2 B3: 4h → 12h (Gemini maliyet)
_SIG_FAIL_TTL         = 300        # 5 dakika

# SPEC-020 Faz 1 — Gemini AI Queue (27 May 2026, INCIDENT-8/10 katalizör fix)
# Worker-local cache 4 worker × paralel Gemini call sorun: 10 ticker × 4 worker
# burst = gevent hub 40-50s donar → K6 v2 quorum tetik. Çözüm:
#   1. Leader-only Gemini call (_is_gemini_leader mevcut)
#   2. Disk cache shared (workers arası senkron)
#   3. Non-leader: cache miss → commentary fallback (Gemini call YOK)
_SIG_EXPLAIN_DISK_PATH = "/root/bist30/_signal_explain_cache.json"
_sig_disk_mtime = None  # H3 pattern: file mtime guard
_sig_disk_lock = threading.Lock()


def _save_explain_cache_to_disk():
    """Leader-only — _signal_explain_cache'i atomic disk'e yazar."""
    try:
        # In-memory cache snapshot (concurrent mutation güvenli)
        with _lock:
            snap = dict(_signal_explain_cache)
        # Atomic write: tempfile + os.replace
        tmp = _SIG_EXPLAIN_DISK_PATH + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(snap, f, ensure_ascii=False)
        os.replace(tmp, _SIG_EXPLAIN_DISK_PATH)
    except Exception as e:
        logger.debug("explain cache disk yazma hatası: %s", e)


def _load_explain_cache_from_disk():
    """Non-leader workers — disk cache'i memory'e merge eder (H3 pattern, mtime guard)."""
    global _sig_disk_mtime
    try:
        if not os.path.exists(_SIG_EXPLAIN_DISK_PATH):
            return
        current_mtime = os.path.getmtime(_SIG_EXPLAIN_DISK_PATH)
        # Mtime guard: file değişmemişse skip (gevent hub bloke etme)
        if _sig_disk_mtime == current_mtime:
            return
        with open(_SIG_EXPLAIN_DISK_PATH, "r", encoding="utf-8") as f:
            disk_data = json.load(f)
        if not isinstance(disk_data, dict):
            return
        # Merge: disk daha taze TS varsa al
        with _lock:
            for tk, dv in disk_data.items():
                mv = _signal_explain_cache.get(tk)
                if not mv or (dv.get("ts", 0) > mv.get("ts", 0)):
                    _signal_explain_cache[tk] = dv
        _sig_disk_mtime = current_mtime
    except Exception as e:
        logger.debug("explain cache disk okuma hatası: %s", e)

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

# ─── Gemini timeout-guard + circuit breaker (SPEC-009 Faz D, 18 May 2026) ───
# 17:15 watchdog auto-restart kök neden: Gemini 503/ReadTimeout 30s+ → 2 fallback
# denemesi toplam gunicorn --timeout 45'i aşıyor → worker SIGKILL → /api/health
# fail → watchdog restart. Sert per-istek timeout cap + circuit breaker zinciri kırar.
_GEMINI_TIMEOUT_CAP  = 5      # saniye — _gemini_call istek başına sert üst sınır
# SPEC-016 K3 — storm-aware: devreyi daha erken aç (3→2), daha uzun kapalı tut
# (300→600s). Gemini 503/ReadTimeout storm'unda gevent maruziyeti minimize edilir.
_GEMINI_CB_THRESHOLD = 2      # ardışık fail eşiği — devre açılır
_GEMINI_CB_COOLDOWN  = 600    # saniye — devre açık kalır (10dk Gemini'siz fallback)
_gemini_cb = {"fails": 0, "open_until": 0.0}   # circuit breaker durumu (worker-local)




# ═══════════════════════════════════════════════════════════════════════════
# IMPLICIT CACHING — Gemini 2.5 sabit prefix sistem prompt'ları (1024+ token)
# Aynı prefix tekrar gönderildiğinde input token maliyeti %75 düşer.
# Bu prompt'lar değişmemeli — her değişiklik cache invalidate eder.
# ═══════════════════════════════════════════════════════════════════════════

_SYS_NEWS = """KIMLIK: Sen BorsaPusula adlı Türk borsa analiz platformunun haber özet asistanısın. Borsa İstanbul'da işlem gören şirketler hakkındaki resmi açıklamaları, finansal sonuçları, KAP bildirimlerini ve önemli kurumsal gelişmeleri bireysel yatırımcılar için sade Türkçe ile özetlersin. Hedef kitlen finans uzmanı değil, sıradan birikim sahibi bireylerdir. Aşağıdaki kurallara KESİNLİKLE uyacaksın.

═══ KESİN KURALLAR ═══

KURAL 1 — TARİH KISITI:
YALNIZCA görev mesajında belirtilen tarih aralığındaki olayları yaz. Bu tarih aralığı dışındaki herhangi bir gelişmeyi DAHIL ETME. Bugünün tarihinden sonraki tarihler için ASLA "olacak, planlanıyor, açıklanacak" gibi ifadeler kullanma — gelecek bilinmez.

KURAL 2 — GELECEK YASAĞI:
Bugünden sonraki tarihlerde olacak olaylar HAKKINDA SPEKÜLASYON YAPMA. Eğer arama sonuçlarında "X şirket yarın bilanço açıklayacak" gibi bir haber bulursan, bunu özete DAHIL ETME. Sadece zaten gerçekleşmiş olayları rapor et. Tahminler, beklentiler ve "olabilir" denenen şeyler de yasaktır.

KURAL 3 — BOŞ KAYNAK YANITI:
Eğer belirtilen tarih aralığında doğrulanmış bir gelişme bulamadıysan, SADECE şunu yaz: "Son 7 günde kayda değer bir gelişme bulunmuyor." Başka bir ek metin yazma, "bilgim sınırlı" gibi bahane sunma, alternatif öneri sunma.

KURAL 4 — UYDURMA YASAĞI:
Tarih uydurma, rakam uydurma, isim uydurma, KAP referans numarası uydurma. Spekülasyon yapma. "Olabilir, muhtemelen, görünüyor, sanırım" gibi belirsiz ifadeler kullanma. Sadece arama kaynaklarında doğrulayabildiğin bilgileri yaz. Emin değilsen yazma.

KURAL 5 — GİRİŞ/KAPANIŞ YASAĞI:
"Aşağıda X şirketinin özetlerini bulabilirsiniz" gibi giriş cümlesi YAZMA. "Umarım faydalı olmuştur, başka sorunuz olursa..." gibi kapanış cümlesi YAZMA. Yalnızca madde madde özet sun, gereksiz dolgu metni ekleme.

═══ FORMAT ═══

• Her madde "•" (madde imi) ile başlasın.
• Her madde tek konuya odaklansın (1-2 cümle, 30-40 kelimeyi geçmesin).
• Sayıları Türkçe formatla yaz: 1.234,56 TL (binlik ayraç nokta, ondalık virgül).
• Yüzdeleri Türkçe formatla yaz: %12,5 büyüme.
• Tarihleri "DD MMMM YYYY" formatında yaz (örn: 8 Mayıs 2026).
• En önemli haberi en üste koy (KAP açıklamalarında genelde en yeni tarihli).
• Teknik finansal jargonu sade dile çevir:
  - "tahvil itfası" yerine "tahvil geri ödemesi"
  - "ihraç" yerine "satış / çıkarma"
  - "iştirak" yerine "bağlı şirket"
  - "konsolide gelir" yerine "şirket grubunun toplam geliri"
  - "FAVÖK" yerine "esas faaliyet kârı (FAVÖK)"
  - "esas faaliyet" yerine "ana iş kolu"
  - "sermaye artırımı" → açıklayarak yaz: "şirket yeni hisse çıkararak sermayesini artırdı"

═══ İYİ ÖRNEK (referans çıktı) ═══

• 8 Mayıs 2026: Akbank, 2025 yılına ait sürdürülebilirlik raporunu yayınladı. Çevresel ve sosyal hedeflerine ilişkin performansı paylaştı.

• 7 Mayıs 2026: Akbank, vadesi gelen 250 milyon dolarlık tahvilin geri ödemesini tamamladı. Yatırımcılara anapara ve son faiz ödendi.

═══ KÖTÜ ÖRNEKLER (yapma) ═══

❌ "Bilgi sahibi olduğum kadarıyla..." — bilgi yetersizse Kural 3'teki boş kaynak yanıtı kullan.
❌ "Akbank yarın bilanço açıklayacak" — Kural 2 gelecek yasağı.
❌ "Hisse fiyatı yükselebilir" — spekülasyon yasağı, sen analist değil özetçisin.
❌ "Aşağıdaki özetler size yardımcı olacaktır" — Kural 5 giriş yasağı.

═══ DEĞIŞKEN GÖREV AŞAĞIDA ═══
"""


_SYS_EXPLAIN = """KIMLIK: Sen BorsaPusula platformunun teknik sinyal açıklama asistanısın. Algoritmik olarak üretilmiş hisse sinyal yorumlarını sade Türkçe ile yeniden ifade edersin. Görevini "bilgili bir borsa abisi" tonunda, anlaşılır ama profesyonel bir üslupla yaparsın. Hedef kitlen finans uzmanı değil, sıradan birikim sahibi bireylerdir.

═══ KESİN KURALLAR ═══

KURAL 1 — ALGORİTMİK METİN KESINLIKLE DOĞRUDUR:
Sana verilen "DOĞRU ALGORİTMİK ANALİZ" bölümündeki bilgiler matematiksel olarak hesaplanmıştır ve doğrudur. Bu analize ASLA itiraz ETME, "ama bir yandan da" diyerek ters yön belirtme, "fakat dikkat edilmeli" gibi şüphe ekleme. Görevin bu analizi desteklemek ve sade dille açıklamak — yorumlamak değil.

KURAL 2 — SİNYALİN YÖNÜNE SADIK KAL:
Eğer sinyal "Güçlü Trend" ise yorum YÜKSELİŞ yönünde olsun. "Zayıf Trend" ise DÜŞÜŞ yönünde. "Yatay/Belirsiz" ise kararsız/yan yatay tonu. Sinyalle çelişen kelimeler (yükselişte 'düşüş', düşüşte 'yükseliş') KULLANMA.

KURAL 3 — ÜÇ CÜMLE KURALI:
Yorumun TAM olarak 3 cümle olsun. Birinci cümle teknik durumu özetlesin, ikinci cümle bu durumun ne anlama geldiğini söylesin, üçüncü cümle MUTLAKA "Yatırım tavsiyesi değildir." şeklinde bitsin. Daha fazla veya daha az cümle yazma.

KURAL 4 — SADE DİL ZORUNLU:
Teknik göstergeleri sıradan yatırımcı diline çevir:
  - Supertrend → fiyat trendi göstergesi / trend yönü
  - ADX → trend gücü
  - EMA → hareketli ortalama
  - DI+ / DI- → yön göstergeleri
  - Stop-Loss → zarar durdurma seviyesi
  - RSI → momentum göstergesi
  - Hacim oranı → işlem hacmi karşılaştırması

KURAL 5 — SAYI YAZIM KURALI:
- Fiyat: TL cinsinden, virgülle ondalık (örn: 32,45 ₺).
- ADX: tam sayı + parantezle açıklama (örn: "28 - güçlü trend").
- Yön: net ifade ("yukarı yönlü", "aşağı yönlü", "kararsız").
- Süre: "X gündür", "yeni başladı".
- Yüzde: virgülle ondalık (%5,3).

KURAL 6 — YASAKLI İFADELER:
- ❌ "Bence", "düşünüyorum", "tahminim" → algoritmik metni anlat, kendi görüşünü ekleme.
- ❌ "Kesin", "mutlaka", "yüzde yüz" → finansta kesinlik yok.
- ❌ "Al/sat tavsiyesi", "almalısınız", "satın" → tavsiye yasağı.
- ❌ Başlık, alt başlık (## veya **bold**) → düz paragraf yaz.
- ❌ Madde işaretleri (- veya •) → düz paragraf, virgüllerle bağla.
- ❌ 1. çoğul fiil ("belirtelim", "ifade edelim", "söyleyebiliriz", "anlayalım") →
     3. tekil / nesnel kullan ("görünüyor", "durumunda", "seviyesinde",
     "olarak hesaplanmış"). Mesafeli + bilgilendirici ton (SPEC-014 polish #1).
- ❌ "Bu durumda yatırımcılar..." → genel tavsiye yok.

═══ İYİ ÖRNEK ═══

"AKBNK için Güçlü Trend sinyali aktif: hisse fiyatı 32,45 ₺ seviyesinde işlem görüyor, trend göstergesi yukarı yönü işaret ediyor ve trend gücü 28 ile güçlü seviyede. Bu üç koşulun aynı anda oluşması, hissenin son 5 gündür istikrarlı bir yükseliş eğiliminde olduğunu gösteriyor; zarar durdurma seviyesi 30,12 ₺ olarak hesaplanmış durumda. Yatırım tavsiyesi değildir."

═══ KÖTÜ ÖRNEKLER ═══

❌ "Akbank hissesinde yükseliş trendi var, ancak dikkatli olunmalı..." (Kural 1 — itiraz yasağı)
❌ "Bence şu an alım fırsatı olabilir" (Kural 6 — kişisel görüş)
❌ "**AKBNK Analizi**" başlık (Kural 6 — formatlama yok)
❌ "- Trend: Güçlü\n- Yön: Yukarı" (Kural 6 — düz paragraf)

═══ EK BAĞLAM ═══

Algoritmik sinyal motoru üç gösterge kombinasyonu kullanır:
1. Supertrend — fiyatın trend bandının üstünde mi altında mı?
2. ADX (Average Directional Index) — trend ne kadar güçlü?
3. EMA12 vs EMA99 — kısa vade uzun vade hareketli ortalamasının üstünde mi?

Üç koşul da AYNI yönde olursa sinyal aktif olur. Bu nedenle açıklamalar
çelişkisiz, tek yönde olmalı. Yatırımcıya "bu üç gösterge nedir?" sorusunun
cevabını sade dille verebilirsin.

Premium sinyal: Eğer hisse "Premium" olarak işaretliyse, bu AL sinyali +
hacim teyidinin de olduğu anlamına gelir (RVOL ≥ 1.20). Bunu yorumda
"hacimle desteklenmiş güçlü sinyal" şeklinde belirtmek serbest ama zorunlu değil.

═══ DEĞIŞKEN GÖREV AŞAĞIDA ═══
"""


_SYS_KAP = """KIMLIK: Sen BorsaPusula adlı Türk borsa analiz platformunun KAP (Kamuyu Aydınlatma Platformu) bildirim özet asistanısın. Borsa İstanbul'da işlem gören şirketlerin KAP'a yaptıkları resmi bildirimleri bireysel yatırımcılar için sade Türkçe ile özetlersin. Hedef kitlen finans uzmanı değil, sıradan birikim sahibi bireylerdir. Aşağıdaki kurallara KESİNLİKLE uyacaksın.

═══ KESİN KURALLAR ═══

KURAL 1 — SADECE VERİLEN BİLDİRİMLER:
Sana ham veri olarak verilen KAP bildirimlerinden BAŞKA bilgi katma. Ek araştırma yapma, dış kaynak kullanma, kendi yorumunu ekleme. Görevin sadece verilen bildirimleri Türkçe sadeleştirmek.

KURAL 2 — UYDURMA YASAĞI:
Tarih uydurma, rakam uydurma, kontrat numarası uydurma. Bildirim metninde olmayan bilgileri YAZMA. "Bu bildirimin anlamı muhtemelen..." gibi yorum kullanma.

KURAL 3 — GİRİŞ/KAPANIŞ YASAĞI:
"Aşağıda X şirketinin KAP bildirimlerini bulabilirsiniz" gibi giriş cümlesi YAZMA. "Umarım faydalı olmuştur" gibi kapanış cümlesi YAZMA. Yalnızca madde madde özet sun.

KURAL 4 — SADE DİL ZORUNLU:
KAP'ta kullanılan teknik finansal terimleri sıradan dile çevir:
  - "tahvil itfası" → "tahvil geri ödemesi" (vade sona erdi)
  - "ihraç" → "satış / çıkarma"
  - "iştirak" → "bağlı şirket"
  - "konsolide finansal sonuçlar" → "şirket grubunun toplam finansal sonuçları"
  - "FAVÖK" → "esas faaliyet kârı (FAVÖK)"
  - "ana ortaklığa ait net kâr" → "ana şirkete düşen net kâr"
  - "yönetim kurulu kararı" → "yönetim kurulu kararı"
  - "kar payı dağıtımı" → "temettü ödemesi"
  - "MKK" → "Merkezi Kayıt Kuruluşu (MKK)"
  - "SPK" → "Sermaye Piyasası Kurulu (SPK)"

═══ FORMAT ═══

• Her madde "•" (madde imi) ile başlasın.
• Her madde 1-2 cümle olsun, gereksiz uzatma.
• Tarihi başta yaz: "8 Mayıs 2026: ..."
• Önemli sayıları belirgin yap: 250 milyon TL, %5 oranında, vb.
• Yatırımcı için "ne anlama geliyor" kısmını parantezle ekleyebilirsin (kısa, max 5 kelime).
• Birden fazla bildirim varsa kronolojik (yeni → eski) sırala.
• Sayıları Türkçe formatla: 1.234,56 TL, %12,5.

═══ İYİ ÖRNEK ═══

• 8 Mayıs 2026: Şirket, 2025 yılı sürdürülebilirlik raporunu yayınladı (çevresel ve sosyal performans verisi).

• 7 Mayıs 2026: 250 milyon TL nominal değerli tahvilin geri ödemesi tamamlandı (vadesi gelen borçlanma kapatıldı).

• 6 Mayıs 2026: Yönetim kurulu, %15 temettü dağıtım kararı aldı; ödeme 15 Mayıs'ta yapılacak.

═══ KÖTÜ ÖRNEKLER ═══

❌ "Aşağıda X şirketinin bildirimlerini bulabilirsiniz" (Kural 3 — giriş yasağı)
❌ "Bu temettü artışı hissenin yükselmesine neden olabilir" (Kural 2 — yorum yasağı)
❌ "Sektör genelinde benzer trendler görülüyor" (Kural 1 — ek bilgi yasağı)
❌ "**KAP Bildirimleri**" başlık (Kural 3 — formatlama yok)

═══ KAP BİLDİRİM TÜRLERİ REFERANSI ═══

Yatırımcılar için en önemli KAP bildirim kategorileri (sadeleştirilmiş açıklama):

• "Finansal Rapor" → çeyrek bilanço açıklaması (3 ayda bir).
  Yatırımcıya etkisi: net kâr/zarar, satış büyümesi → hisse fiyatına yansır.

• "Esas Sözleşme Değişikliği" → şirket tüzüğünde değişiklik.
  Yatırımcıya etkisi: yönetişim/oy hakları değişimi olabilir.

• "Genel Kurul Toplantısı" → ortaklar yıllık toplantısı.
  Yatırımcıya etkisi: temettü dağıtım kararı, yönetim kurulu seçimi.

• "Pay Geri Alımı" (buyback) → şirket kendi hissesini satın alıyor.
  Yatırımcıya etkisi: hisse arzı azalır → fiyat desteği oluşur.

• "Önemli Olaylar" → satın alma, satış, ortaklık değişikliği, davalar.
  Yatırımcıya etkisi: olayın boyutuna göre büyük fiyat etkisi olabilir.

• "İhraç Tavanı" → şirket yeni borçlanma izni almış.
  Yatırımcıya etkisi: borç yükü artabilir, faiz gideri yükselir.

• "Bağımsız Denetim" → yıllık dış denetim sonuçları.
  Yatırımcıya etkisi: muhasebe doğruluğu teyidi.

═══ DEĞIŞKEN GÖREV AŞAĞIDA ═══
"""

def _gemini_call(prompt, attempts, timeout=20, max_tokens=500, temperature=0.3):
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

    # Circuit breaker — devre açıksa Gemini'yi hiç çağırma, anında fallback dön.
    # Worker'ı bloke eden tekrarlı hang çağrılarını önler (17:15 watchdog restart fix).
    now = time.time()
    if now < _gemini_cb["open_until"]:
        logger.debug("_gemini_call: circuit breaker açık (%.0fs kaldı) — fallback",
                     _gemini_cb["open_until"] - now)
        return None, None

    # Sert timeout cap — caller ne geçerse geçsin per-istek üst sınır.
    eff_timeout = min(timeout, _GEMINI_TIMEOUT_CAP)

    for model_id, use_search in attempts:
        body = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {
                "maxOutputTokens": int(max_tokens),
                "temperature": float(temperature),
                "topP": 0.8,
                # Gemini 2.5 Flash thinking mode default ON → output budget'i yiyor.
                # Bizim use-case (özet/çeviri) reasoning gerektirmiyor → kapattık.
                "thinkingConfig": {"thinkingBudget": 0},
            },
        }
        if use_search:
            body["tools"] = [{"google_search": {}}]
        url = (f"https://generativelanguage.googleapis.com/v1beta/"
               f"models/{model_id}:generateContent?key={GEMINI_API_KEY}")
        try:
            r = requests.post(url, json=body, timeout=eff_timeout)
            r.raise_for_status()
            text = (r.json().get("candidates", [{}])[0]
                            .get("content", {})
                            .get("parts", [{}])[0]
                            .get("text", "")).strip()
            if text:
                _gemini_cb["fails"] = 0   # başarı → circuit breaker sayacı sıfırla
                return model_id, text
            # Model yanıt verdi ama boş metin — fallback'e geç
            logger.debug("_gemini_call [%s]: boş yanıt, fallback deneniyor", model_id)
        except Exception as e:
            status = getattr(getattr(e, "response", None), "status_code", None)
            if status == 429:
                logger.debug("_gemini_call [%s]: rate-limited (429)", model_id)  # sessiz — log dolmasın
            else:
                logger.warning("_gemini_call [%s]: %s (HTTP %s)", model_id, type(e).__name__, status)
            # Circuit breaker — ardışık fail say, eşikte devreyi aç
            _gemini_cb["fails"] += 1
            if _gemini_cb["fails"] >= _GEMINI_CB_THRESHOLD:
                _gemini_cb["open_until"] = time.time() + _GEMINI_CB_COOLDOWN
                _gemini_cb["fails"] = 0
                logger.warning("_gemini_call: circuit breaker AÇILDI — %d ardışık fail, "
                               "%ds boyunca Gemini'siz fallback", _GEMINI_CB_THRESHOLD, _GEMINI_CB_COOLDOWN)
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
            ttl = _NEWS_FAIL_TTL if cached.get("failed") else _news_ttl_for(ticker)
            if (now - cached["ts"]) < ttl:
                return cached.get("text")   # başarısız cache → None döner

    name       = STOCK_NAMES.get(ticker, ticker)
    today_str  = datetime.now(_TZ_TR).strftime("%d %B %Y")   # ör: "01 Mayıs 2026"
    today_iso  = datetime.now(_TZ_TR).strftime("%Y-%m-%d")   # ör: "2026-05-01"
    week_ago   = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")
    prompt = _SYS_NEWS + (
        f"\nHisse: {ticker} ({name})\n"
        f"Tarih aralığı: {week_ago} → {today_iso} (son 7 gün)\n"
        f"Bugün: {today_str}\n\n"
        f"Yukarıdaki kurallara göre bu hisse için belirtilen tarih aralığındaki "
        f"gerçek KAP bildirimleri, finansal sonuçlar veya önemli şirket açıklamalarını "
        f"madde madde özetle."
    )

    model_used, text = _gemini_call(prompt, _GEMINI_NEWS_ATTEMPTS, timeout=25, max_tokens=400, temperature=0.2)

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

    # SPEC-020 Faz 1 — Memory miss → DISK cache lazy-load (H3 pattern mtime guard)
    # Workers arası senkron: leader Gemini yazdığında non-leader buradan okur
    _load_explain_cache_from_disk()
    with _lock:
        cached = _signal_explain_cache.get(ticker)
        if cached:
            ttl = _SIG_FAIL_TTL if cached.get("failed") else _SIG_EXPLAIN_TTL
            if (now - cached["ts"]) < ttl and cached.get("sig") == sig:
                return cached.get("text")

    # SPEC-AI-EXPLANATION-FIX (CPO-428): Indikatör extraction'ı non-leader check'ten
    # YUKARI taşı — non-leader path'i de kural-tabanlı commentary üretmek için ihtiyaç.
    # Graceful fallback: AI tab ASLA boş/takılı kalmasın, Gemini gelince üzerine yazar.

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

    # ── Algoritmik temel metin (her zaman doğru, AI'dan bağımsız) ────────────
    commentary = _generate_commentary(ticker, sig, bars, None, adx, di_plus, di_minus, e12, e99, st_bull)

    # SPEC-AI-EXPLANATION-FIX (CPO-428): Non-leader path → kural-tabanlı commentary DÖN.
    # ÖNCEKİ DAVRANIŞ: "Sinyal açıklaması hazırlanıyor…" placeholder (~%50 hissede kalıcı).
    # YENİ DAVRANIŞ: AI tab ASLA boş/takılı kalmaz; Gemini cache gelince üzerine yazar.
    # Glass-box + K8 data-trust prensibi.
    if not _is_gemini_leader():
        return commentary + " Yatırım tavsiyesi değildir."

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
    prompt = _SYS_EXPLAIN + (
        f"\n=== DOĞRU ALGORİTMİK ANALİZ ===\n"
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
        f"Yukarıdaki kurallara göre bu sinyali 3 cümlede sade Türkçe ile yeniden ifade et."
    )

    model_used, text = _gemini_call(prompt, _GEMINI_EXPLAIN_ATTEMPTS, timeout=20, max_tokens=250, temperature=0.3)

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

    # SPEC-020 Faz 1 — Leader yazımı sonrası disk cache senkronu
    # Non-leader workers _load_explain_cache_from_disk ile mtime guard'a göre
    # bu güncellemeyi okur, ikinci Gemini call yapmaz.
    if ai_ok:  # Sadece gerçek AI başarısı disk'e (fallback noise olmaz)
        _save_explain_cache_to_disk()

    return final_text


# ── Arka plan: BIST30 haber ön-yüklemesi ─────────────────────────────────────
_PREFETCH_MAX    = 8    # Aynı anda en fazla bu kadar hisse prefetch edilir
_PREFETCH_DELAY  = 30   # İstekler arası bekleme (saniye) — Gemini rate-limit koruması
_PREFETCH_STARTUP_GRACE_S = 300  # SPEC-016 K1 — restart sonrası prefetch bekleme (soğuk-start storm fix)


def _prefetch_news_worker():
    """AL sinyalli hisselerin haberlerini cache'e önceden yükler; her 6 saatte bir çalışır.

    Sunucu yeniden başlatıldıktan sonra kullanıcılar soğuk cache'e düşmeden
    içerik görür. Yalnızca AL sinyalli hisseler için çalışır (max 8) ve istekler
    arası 30 saniye bekler — Gemini ücretsiz tier rate-limit koruması.
    """
    # SPEC-016 K1 — restart-grace: soğuk-start thundering herd fix (#48).
    # Site oturmadan prefetch Gemini'ye yüklenmesin → 120s → 300s.
    time.sleep(_PREFETCH_STARTUP_GRACE_S)
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
                elif (now - cached["ts"]) > _news_ttl_for(ticker) * 0.9:
                    to_fetch.append(ticker)          # cache sona ermek üzere

        logger.info("Prefetch: %d/%d AL hisse için haber yüklenecek", len(to_fetch), len(al_tickers))
        fetched = 0
        for ticker in to_fetch:
            # SPEC-016 K2 — sıralı + leader teyidi: storm sırasında leader
            # değişirse prefetch'i durdur (çift worker Gemini yükü engellenir).
            if not _is_gemini_leader():
                logger.info("Prefetch: leader değil — tur durduruldu")
                break
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
# SPEC-009 Gemini Faz 1: yalnız leader worker prefetch çalıştırır — 4× Gemini
# maliyet multiplier fix. Non-leader 3 worker prefetch yapmaz (on-demand cache'ten okur).
if _is_gemini_leader():
    _prefetch_thread.start()
    logger.info("gemini-prefetch: LEADER worker — bg prefetch aktif")
else:
    logger.info("gemini-prefetch: non-leader worker — prefetch atlandı (maliyet fix)")


def _company_summary_prefetch_worker():
    """SPEC-011 L4 — Şirket AI özetlerini yavaşça doldurur (leader-only).
    Eksik/bayat özetleri 35s arayla üretir → Gemini rate-limit dostu.
    Tur sonunda 12h uyur (TTL 30 gün, acele yok)."""
    time.sleep(_PREFETCH_STARTUP_GRACE_S)   # SPEC-016 K1 — restart-grace (soğuk-start storm fix)
    while True:
        try:
            now = time.time()
            with _lock:
                have = set(_company_summary_cache.keys())
            to_gen = [t for t in BIST100
                      if t != "XU030" and t not in have]
            # Bayatları da yenile
            with _lock:
                for tk, e in list(_company_summary_cache.items()):
                    if (now - e.get("ts", 0)) > _COMPANY_SUMMARY_TTL:
                        to_gen.append(tk)
            if to_gen:
                logger.info("company-summary prefetch: %d hisse üretilecek", len(to_gen))
            done = 0
            for tk in to_gen:
                try:
                    if _generate_company_summary(tk):
                        done += 1
                except Exception as e:
                    logger.error("company-summary prefetch hatası [%s]: %s", tk, e)
                time.sleep(35)   # rate-limit koruması
            if to_gen:
                logger.info("company-summary prefetch tamamlandı: %d/%d", done, len(to_gen))
        except Exception as e:
            logger.error("company-summary prefetch worker hatası: %s", e)
        time.sleep(12 * 3600)   # 12h sonra yeni tur (eksik/bayat kontrolü)


_company_summary_thread = threading.Thread(
    target=_company_summary_prefetch_worker,
    daemon=True,
    name="gemini-company-summary"
)
# Leader-only — #30 maliyet multiplier fix (4 worker yerine 1)
if _is_gemini_leader():
    _company_summary_thread.start()
    logger.info("gemini-company-summary: LEADER worker — bg prefetch aktif")
else:
    logger.info("gemini-company-summary: non-leader worker — prefetch atlandı")


# SPEC-009 Faz 2 (redesign) — gemini-cache-sync: timer-tabanlı disk senkron.
# #38: disk I/O request/hot-path'te YAPILMAZ (gevent hub kilitler). Bunun yerine
# 90s'lik bg timer thread — background_refresh non-leader pattern'i birebir.
# Leader: in-memory cache'i diske yazar. Non-leader: diskten okur. Inline I/O YOK.
def _gemini_cache_sync_loop():
    is_leader = _is_gemini_leader()
    mode = "LEADER (disk yazar)" if is_leader else "non-leader (disk okur)"
    logger.info("gemini-cache-sync: %s", mode)
    while True:
        try:
            if is_leader:
                _save_news_cache_to_disk()
                _save_macro_ai_to_disk()
                _save_company_summary_to_disk()
            else:
                _load_news_cache_from_disk()
                _load_macro_ai_from_disk()
                _load_company_summary_from_disk()
        except Exception as e:
            logger.error("gemini-cache-sync hatası: %s", e)
        time.sleep(90)

threading.Thread(target=_gemini_cache_sync_loop, daemon=True, name="gemini-cache-sync").start()


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
                _news_queue_stats["last_processed_ts"] = time.time()
                _news_queue_stats["total_processed"] += 1
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
        # gevent altinda yf.download bazi semboller icin yanlis scale donerebiliyor.
        # Endeks ve emtia sembolleri icin Ticker.history daha guvenilir.
        df = None
        if ticker_base in ("XU100", "XU030"):
            try:
                with _YF_GLOBAL_LOCK:
                    df = yf.Ticker(ticker).history(period=period, interval="1d", auto_adjust=True)
                if df is not None and len(df) > 0:
                    df.index = df.index.tz_localize(None) if df.index.tz else df.index
            except Exception as _e:
                logger.warning("%s: Ticker.history fallback (%s)", ticker_base, _e)
                df = None
        if df is None or len(df) == 0:
            with _YF_GLOBAL_LOCK:
                df = yf.download(ticker, period=period, interval="1d",
                                 progress=False, auto_adjust=True, timeout=30, threads=False)
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
                entry_price = round(float(close.iloc[i]), 2)
                if d_str in show_set:
                    markers.append({
                        "time":     d_str,
                        "position": "belowBar" if sig == "AL" else "aboveBar",
                        "color":    "#3fb950"  if sig == "AL" else "#f85149",
                        "shape":    "arrowUp"  if sig == "AL" else "arrowDown",
                        "text":     "▲" if sig == "AL" else "▼",
                        "signal":   sig,
                        "price":    entry_price,
                        "date_tr":  close.index[i].strftime("%d.%m.%Y"),
                    })
                signal_history.append({
                    "date":   close.index[i].strftime("%d.%m.%Y"),
                    "signal": sig,
                    "price":  entry_price,
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
            _chart_cache["updated_at"] = datetime.now(_TZ_TR).strftime("%d.%m.%Y %H:%M:%S")


def refresh_xu100_chart():
    """XU100 grafik verisini günceller — sanity guard ile (BIST 100 ≥ 5000)."""
    try:
        d = _compute_chart_data("XU100", "5y")
        if not d: return
        s = d.get("summary", {}) or {}
        price = s.get("price", 0) or 0
        if price < 5000:
            logger.warning("XU100 chart REJECTED: price=%.2f (yfinance scale glitch); cache korunuyor", price)
            return
        ohlc = d.get("ohlc", []) or []
        if ohlc and (ohlc[-1].get("close", 0) or 0) < 5000:
            logger.warning("XU100 chart REJECTED: last close=%.2f scale invalid", ohlc[-1].get("close"))
            return
        with _lock:
            _xu100_chart_cache["data"] = d
            _xu100_chart_cache["updated_at"] = datetime.now(_TZ_TR).strftime("%d.%m.%Y %H:%M:%S")
        logger.info("XU100 chart cache güncellendi (price=%.2f)", price)
    except Exception as e:
        logger.error("refresh_xu100_chart: %s", e, exc_info=True)


@app.route("/api/chart")
def api_chart():
    # XU030 (BIST30) — MSG-006 macro summary inject
    return _chart_response_with_macro_summary("XU030", _chart_cache)


def _chart_response_with_macro_summary(ticker_base, cache_obj):
    """MSG-006: Single Source of Truth — chart summary fiyatını _macro_cache ile override.

    Drift fix: chart cache 1h+ stale, macro 90s'de güncel.
    Macro cold/missing ise chart cache değeri korunur (graceful fallback).
    Cache mutate edilmez (response için shallow copy + yeni summary dict).
    """
    with _lock:
        data = cache_obj.get("data")
        updated_at = cache_obj.get("updated_at")
    if not data or "summary" not in data:
        return safe_json({"chart": data, "updated_at": updated_at, "loading": data is None})
    # Shallow copy + yeni summary dict (cache mutate olmasın)
    data = dict(data)
    data["summary"] = dict(data.get("summary", {}))
    # Macro lookup
    macro_items = _macro_cache.get("data") or []
    for item in macro_items:
        if item.get("label") == ticker_base:
            price = item.get("price")
            change = item.get("change")
            if price is not None:
                data["summary"]["price"] = price
            if change is not None:
                data["summary"]["change_pct"] = change
            break
    return safe_json({"chart": data, "updated_at": updated_at, "loading": data is None})


@app.route("/api/chart/XU100")
def api_chart_xu100():
    return _chart_response_with_macro_summary("XU100", _xu100_chart_cache)


def _refresh_varlik_chart(varlik_key, cache_obj):
    """BTC / ALTIN / GUMUS grafik verisini günceller."""
    meta = _VARLIK_META.get(varlik_key, {})
    try:
        d = _compute_chart_data(varlik_key, meta.get("period", "2y"))
        if d:
            with _lock:
                cache_obj["data"] = d
                cache_obj["updated_at"] = datetime.now(_TZ_TR).strftime("%d.%m.%Y %H:%M:%S")
            logger.info("%s chart cache güncellendi", varlik_key)
    except Exception as e:
        logger.error("_refresh_varlik_chart(%s): %s", varlik_key, e, exc_info=True)


@app.route("/api/chart/BTC")
def api_chart_btc():
    return _chart_response_with_macro_summary("BTC", _btc_chart_cache)


@app.route("/api/chart/ALTIN")
def api_chart_altin():
    return _chart_response_with_macro_summary("ALTIN", _altin_chart_cache)


@app.route("/api/chart/GUMUS")
def api_chart_gumus():
    return _chart_response_with_macro_summary("GUMUS", _gumus_chart_cache)


@app.route("/api/chart/ETH")
def api_chart_eth():
    # ETH macro cache'de yok — sadece chart cache (helper fallback OK)
    return _chart_response_with_macro_summary("ETH", _eth_chart_cache)

@app.route("/api/chart/SP500")
def api_chart_sp500():
    return _chart_response_with_macro_summary("SP500", _sp500_chart_cache)

@app.route("/api/chart/NASDAQ")
def api_chart_nasdaq():
    return _chart_response_with_macro_summary("NASDAQ", _nasdaq_chart_cache)

@app.route("/api/chart/SOL")
def api_chart_sol():
    return _chart_response_with_macro_summary("SOL", _sol_chart_cache)

@app.route("/api/chart/BNB")
def api_chart_bnb():
    return _chart_response_with_macro_summary("BNB", _bnb_chart_cache)

@app.route("/api/chart/PETROL")
def api_chart_petrol():
    return _chart_response_with_macro_summary("PETROL", _petrol_chart_cache)

@app.route("/api/chart/DOGALGAZ")
def api_chart_dogalgaz():
    # DOGALGAZ macro cache'de yok, fallback chart cache
    return _chart_response_with_macro_summary("DOGALGAZ", _dogalgaz_chart_cache)


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

    # US stock cache için _live_prices ile fiyat karşılaştır (split tespiti)
    if cached:
        try:
            chart_price = (cached.get("data") or {}).get("summary", {}).get("price", 0)
            with _lock:
                gp = dict(_live_prices)  # _global_prices_cache yerine _live_prices kullan
            main_price = (gp.get(ticker) or {}).get("price", 0) if gp else 0
            if chart_price > 0 and main_price > 0:
                ratio = max(chart_price, main_price) / min(chart_price, main_price)
                if ratio > 1.15:
                    logger.warning(
                        "Fiyat uyuşmazlığı [US_%s]: chart=%.2f main=%.2f oran=%.2fx — cache iptal",
                        ticker, chart_price, main_price, ratio
                    )
                    cached = None
        except Exception as _e:
            logger.debug("US chart price compare skipped: %s", _e)

    if cached and (now - cached["ts"]) < _STOCK_CACHE_TTL:
        return safe_json({"chart": cached["data"], "updated_at": cached["updated_at"], "loading": False})

    data = _compute_chart_data(ticker, "2y")
    upd  = datetime.now(_TZ_TR).strftime("%d.%m.%Y %H:%M:%S")
    if data:
        with _lock:
            _stock_chart_cache[f"US_{ticker}"] = {"data": data, "ts": now, "updated_at": upd}
        return safe_json({"chart": data, "updated_at": upd, "loading": False})
    return safe_json({"chart": None, "loading": True})


# ── Makro Varlık Sayfaları (BTC / ETH / Altın / Gümüş) ──────────────────────
# SPEC-MOBILE-UI-AUDIT-2026-06-04 task #28 (CPO-484/485): Kripto modülü GATE.
# Veri doğruluğu sorunu (OHLC close 1000x yanlış, BTC $17) — sayfa "Yakında" placeholder.
# Fix #34 (kök neden + yfinance symbol test) sonrası gate kaldırılacak.
@app.route("/btc")
def btc_page():
    return render_template("kripto_gate.html")


@app.route("/eth")
def eth_page():
    return render_template("kripto_gate.html")


@app.route("/sol")
def sol_page():
    return render_template("kripto_gate.html")

@app.route("/bnb")
def bnb_page():
    return render_template("kripto_gate.html")


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
    # CPO-484/485 GATE: veri doğruluğu sorunu, "Yakında" placeholder
    return render_template("kripto_gate.html")

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


# ── SPEC-014 A1 — Sinyal Özeti (deterministik, kural-tabanlı) ─────────────────
def _fmt_tl(v):
    """Sayıyı TR formatında TL string'e çevirir."""
    try:
        return f"{float(v):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".") + " TL"
    except (ValueError, TypeError):
        return "—"


def build_signal_summary(stock):
    """SPEC-014 A1 — Sinyal Özeti.

    Deterministik (Gemini DEĞİL), kural-tabanlı durum matrisi.
    3 katman döner:
      verdict — tek cümle, teknik terimsiz kullanıcı sonucu
      points  — 3 madde "neden böyle söylüyoruz" (trend / giriş riski / risk seviyesi)
    Tüm AL/SAT/BEKLE durumlarını kapsar.
    """
    if not stock:
        return None

    signal  = (stock.get("signal") or "BEKLE").upper()
    entry   = stock.get("signal_price")
    current = stock.get("price")
    bars    = stock.get("signal_bars") or 0
    rsi     = stock.get("rsi")
    adx     = stock.get("adx")
    sl      = stock.get("sl_level")
    weekly  = stock.get("weekly_trend")   # int: 1 = haftalık yukarı, -1 = aşağı
    eq      = stock.get("entry_quality")
    opt     = stock.get("optimal_entry")

    try:
        gain_pct = ((float(current) - float(entry)) / float(entry) * 100.0) if (entry and current) else 0.0
    except (ValueError, TypeError, ZeroDivisionError):
        gain_pct = 0.0

    rsi_hot  = isinstance(rsi, (int, float)) and rsi > 70
    rsi_cold = isinstance(rsi, (int, float)) and rsi < 30

    # ── Katman A — tek cümle (durum matrisi) ──────────────────────────────────
    if signal == "AL":
        if gain_pct > 50 and rsi_hot:
            verdict = ("Trend güçlü kalmaya devam ediyor; ancak fiyat sinyal "
                       "başlangıcına göre ciddi yükseldiği için yeni girişte kovalamak "
                       "yerine geri çekilme beklemek daha sağlıklı görünüyor.")
        elif gain_pct > 50:
            verdict = ("Trend güçlü; fiyat sinyal başından bu yana belirgin yükseldi — "
                       "mevcut pozisyon için trend korunuyor, yeni giriş için ideal bölge "
                       "takibi önerilir.")
        elif gain_pct > 20 and rsi_hot:
            verdict = ("Trend yukarı yönlü ama fiyat kısa vadede ısınmış; yeni girişte "
                       "acele etmeden geri çekilmeyi beklemek daha mantıklı görünüyor.")
        elif bars <= 5:
            verdict = ("Trend yeni güçlenmiş; sinyal taze ve giriş için nispeten erken "
                       "bir aşamada görünüyor.")
        else:
            verdict = "Trend güçlü ve alış sinyali aktif kalmaya devam ediyor."
    elif signal == "SAT":
        if gain_pct < -20 and rsi_cold:
            verdict = ("Düşüş trendi sürüyor; fiyat sinyal başlangıcına göre belirgin "
                       "geriledi ve kısa vadede aşırı satım bölgesine yaklaştı — yeni satış "
                       "için acele etmek yerine tepki ihtimalini izlemek daha sağlıklı.")
        elif gain_pct < -20:
            verdict = ("Düşüş trendi güçlü; fiyat sinyal başından bu yana belirgin geriledi, "
                       "satış baskısı sürüyor görünüyor.")
        elif bars <= 5:
            verdict = ("Satış sinyali yeni oluşmuş; trend aşağı yönlü dönmeye başlamış "
                       "görünüyor.")
        else:
            verdict = "Trend zayıf ve satış sinyali aktif kalmaya devam ediyor."
    else:  # BEKLE
        if weekly == 1:
            verdict = ("Net bir alım/satım sinyali yok; göstergeler kararsız ancak "
                       "orta vadeli görünüm hâlâ yukarı yönlü — beklemek şu an daha "
                       "temkinli bir tercih.")
        elif weekly == -1:
            verdict = ("Net bir sinyal yok ve orta vadeli görünüm zayıf — yeni pozisyon "
                       "için acele etmemek, netleşmeyi beklemek daha sağlıklı görünüyor.")
        else:
            verdict = ("Şu an net bir alım/satım sinyali yok; göstergeler kararsız, "
                       "yön belirginleşene kadar beklemek daha mantıklı görünüyor.")

    # ── Katman B — 3 madde ────────────────────────────────────────────────────
    points = []

    # 1) Trend maddesi
    adx_txt = ""
    if isinstance(adx, (int, float)) and adx:
        if adx >= 25:
            adx_txt = " (trend gücü belirgin)"
        elif adx >= 20:
            adx_txt = " (trend gücü orta)"
        else:
            adx_txt = " (trend gücü zayıf)"
    if signal == "AL":
        points.append({
            "text": "Trend yukarı yönlü: orta/uzun vadeli göstergeler alım tarafında" + adx_txt + ".",
            "tip":  "ADX, EMA ve Supertrend gibi göstergelerin ortak yönü değerlendirilir.",
        })
    elif signal == "SAT":
        points.append({
            "text": "Trend aşağı yönlü: orta/uzun vadeli göstergeler satış tarafında" + adx_txt + ".",
            "tip":  "ADX, EMA ve Supertrend gibi göstergelerin ortak yönü değerlendirilir.",
        })
    else:
        points.append({
            "text": "Trend kararsız: göstergeler net bir yön vermiyor" + adx_txt + ".",
            "tip":  "ADX, EMA ve Supertrend gibi göstergeler bir arada değerlendirilir.",
        })

    # 2) Giriş riski maddesi
    if signal == "AL":
        if gain_pct > 50:
            risk_txt = f"Giriş riski yüksek: fiyat sinyal başlangıcına göre ~%{gain_pct:.0f} yukarıda."
        elif gain_pct > 15:
            risk_txt = f"Giriş riski arttı: fiyat sinyal başlangıcına göre ~%{gain_pct:.0f} yukarıda."
        elif gain_pct >= 0:
            risk_txt = f"Giriş riski sınırlı: fiyat sinyal başlangıcına yakın (~%{gain_pct:.0f})."
        else:
            risk_txt = f"Fiyat sinyal başlangıcının ~%{abs(gain_pct):.0f} altında — giriş bölgesine yakın."
    elif signal == "SAT":
        risk_txt = (f"Fiyat sinyal başlangıcına göre %{gain_pct:.0f} seviyesinde — "
                    "satış sinyali bu hareketle uyumlu.")
    else:
        risk_txt = "Net sinyal olmadığı için tanımlı bir giriş bölgesi yok."
    rsi_tip = ""
    if isinstance(rsi, (int, float)):
        rsi_tip = f" RSI {rsi:.0f} — 70 üstü aşırı alım, 30 altı aşırı satım bölgesi."
    points.append({
        "text": risk_txt,
        "tip":  "Sinyal başlangıç fiyatı ile güncel fiyat arasındaki fark." + rsi_tip,
    })

    # 3) Risk seviyesi maddesi
    if sl:
        risk_lvl = f"Risk seviyesi: stop bölgesi {_fmt_tl(sl)}."
    else:
        risk_lvl = "Risk seviyesi: bu sinyal için tanımlı stop bölgesi bulunmuyor."
    if opt:
        risk_lvl += f" İdeal giriş bölgesi {_fmt_tl(opt)} civarı."
    elif isinstance(eq, str) and eq:
        risk_lvl += f" Giriş kalitesi: {eq}."
    points.append({
        "text": risk_lvl,
        "tip":  "Stop bölgesi, sinyal geçersiz sayılabilecek fiyat seviyesidir.",
    })

    return {
        "signal":   signal,
        "verdict":  verdict,
        "points":   points,
        "gain_pct": round(gain_pct, 1),
    }


# ── Bireysel Hisse Sayfaları ──────────────────────────────────────────────────
@app.route("/hisse/<ticker>")
def stock_page(ticker):
    ticker = ticker.upper()
    if ticker not in BIST100:
        if ticker in DELISTED_TICKERS:
            from flask import make_response
            html = (
                "<!doctype html><html lang='tr'><head><meta charset='utf-8'>"
                f"<title>{ticker} — Borsadan çekildi | BorsaPusula</title>"
                "<meta name='robots' content='noindex'>"
                "<meta http-equiv='refresh' content='5;url=/hisseler'>"
                "<style>body{background:#0e0e12;color:#e5e1e4;font-family:system-ui;padding:60px 20px;text-align:center}"
                "a{color:#70b1ff;text-decoration:none;font-weight:600}h1{font-size:24px;margin-bottom:10px}"
                "p{color:#909097;line-height:1.6}</style></head><body>"
                f"<h1>{ticker} hissesi artık işlem görmüyor</h1>"
                "<p>Bu hisse Borsa İstanbul'dan çekildi veya başka bir şirketle birleşti.</p>"
                "<p><a href='/hisseler'>Tüm aktif BIST hisselerini görüntüle →</a></p>"
                "<p style='font-size:11px;margin-top:20px'>5 saniye içinde otomatik yönlendirme…</p>"
                "</body></html>"
            )
            r = make_response(html, 410)
            r.headers['Content-Type'] = 'text/html; charset=utf-8'
            return r
        return render_template("index.html"), 404
    name   = STOCK_NAMES.get(ticker, ticker)
    sector = _get_sector(ticker)
    others = [t for t in BIST100 if t != ticker and t != "XU030"]

    # Sektör karşılaştırma URL'i — aynı sektördeki ilk 2 peer ile
    _sector_peers = [t for t in SECTORS.get(sector, []) if t != ticker and t in BIST100][:2]
    compare_url = "/karsilastir?tickers=" + ",".join([ticker] + _sector_peers)

    # SEO: mevcut cache'ten temel sinyal verisini SSR için çek
    ssr_signal = None
    with _lock:
        for s in _cache["data"]:
            if s.get("ticker") == ticker:
                ssr_signal = s
                break

    # T3-4: İlgili blog makaleleri — bu ticker'ı related_tickers olarak işaretleyenler
    related_blog = [
        {"slug": a["slug"], "title": a["title"], "cat": a["cat"], "mins": a.get("mins") or a.get("read_min", 5)}
        for a in ARTICLES
        if ticker in a.get("related_tickers", [])
    ][:4]  # max 4 makale

    # Backtest — bu ticker için geçmiş başarı istatistikleri
    ticker_bt = None
    try:
        bt_data = _bt_cache.get("data") or {}
        per_ticker = bt_data.get("per_ticker", [])
        for entry in per_ticker:
            if entry.get("ticker") == ticker:
                al_cnt  = entry.get("al_count", 0)
                al_wins = entry.get("al_wins", 0)
                ticker_bt = {
                    "al_count":    al_cnt,
                    "al_wins":     al_wins,
                    "al_win_rate": round(al_wins / al_cnt * 100) if al_cnt > 0 else None,
                    "al_avg":      round(entry.get("al_avg", 0) * 100, 1),
                    "computed_at": bt_data.get("computed_at", ""),
                }
                break
    except Exception:
        pass

    # SPEC-007: Premium hisse detay paywall — anonim user'a grafik/geçmiş/indikatör blur
    premium_locked = bool(
        ssr_signal and ssr_signal.get("tier") == "premium" and not has_premium_access()
    )

    # ── SPEC-011 L4 + SPEC-013 — İçerik zenginleştirme + AI-optimized data ──────
    company_summary = get_company_summary(ticker)   # None olabilir → template fallback

    # İlgili hisseler — aynı sektörden 5 hisse (internal linking)
    related_stocks = [
        {"ticker": t, "name": STOCK_NAMES.get(t, t)}
        for t in SECTORS.get(sector, [])
        if t != ticker and t in BIST100 and t != "XU030"
    ][:5]

    # Sinyal/skor verileri — JSON-LD schema + SSS için
    sig      = (ssr_signal or {}).get("signal") or "BEKLE"
    price    = (ssr_signal or {}).get("price")
    chg      = (ssr_signal or {}).get("change_pct")
    rsi_val  = (ssr_signal or {}).get("rsi")
    rr_val   = (ssr_signal or {}).get("rr_ratio")
    # SPEC-017 Faz 3 batch v2 B2: hero card tier_score (0-100) vs SSS score (bull/bear 0-3) tutarsızlığı.
    # SSS de tier_score kullanmalı (hero ile aynı kaynak) — kullanıcı "skor 3/100 düşük" sanmaz.
    score = (ssr_signal or {}).get("tier_score")
    if score is None and sig in ("AL", "SAT"):
        # Fallback: tier_score yoksa bull/bear x 33 ~ 0-100 normalize
        raw = (ssr_signal or {}).get("bull_score" if sig == "AL" else "bear_score")
        score = int(raw * 33) if isinstance(raw, (int, float)) else None
    _inds    = (ssr_signal or {}).get("indicators") or {}
    _adx_lbl = (_inds.get("adx") or {}).get("label", "")
    try:
        adx_val = float(_adx_lbl.replace("ADX", "").strip()) if _adx_lbl else None
    except (ValueError, TypeError):
        adx_val = None
    # SPEC-017 Faz 3 batch v2 B1: SSS cevabında AL/SAT parantez yasak (K3 wording disiplin)
    sig_label = {"AL": "Güçlü Trend", "SAT": "Zayıf Trend",
                 "BEKLE": "Belirsiz"}.get(sig, sig)

    # Yatırımcı SSS — deterministik, veri-tabanlı (ekstra Gemini çağrısı YOK)
    # SPEC-017 Faz B K3: AL/SAT wording yasak — "al mı sat mı" → "güncel teknik sinyali nedir"
    seo_faq = []
    seo_faq.append({
        "q": f"{ticker} hissesinin güncel teknik sinyali nedir?",
        "a": (f"{ticker} için güncel algoritmik sinyal: {sig_label}. "
              f"BorsaPusula teknik göstergeleri (Supertrend, EMA, ADX, MACD) baz alır. "
              f"Yatırım tavsiyesi değildir."),
    })
    if price:
        _chg_txt = f", günlük değişim %{chg:.2f}" if isinstance(chg, (int, float)) else ""
        seo_faq.append({
            "q": f"{ticker} hisse fiyatı ne kadar?",
            "a": f"{ticker} güncel fiyatı {price} TL{_chg_txt}.",
        })
    if adx_val is not None or score is not None:
        _parts = []
        if adx_val is not None:
            _parts.append(f"ADX {adx_val:.0f} (trend gücü)")
        if score is not None:
            _parts.append(f"sinyal skoru {score}/100")
        if isinstance(rr_val, (int, float)) and rr_val:
            _parts.append(f"R/R oranı {rr_val}")
        seo_faq.append({
            "q": f"{ticker} hissesi prim potansiyeli nedir?",
            "a": "Teknik göstergeler: " + ", ".join(_parts) + ". Yatırım tavsiyesi değildir.",
        })
    if company_summary:
        _first = company_summary.split(".")[0].strip()
        if _first:
            seo_faq.append({
                "q": f"{ticker} ne yapan şirket?",
                "a": _first + ".",
            })

    # SPEC-014 A1 — Sinyal Özeti (deterministik konsolide kutu)
    signal_summary = build_signal_summary(ssr_signal)

    return render_template("hisse.html",
                           ticker=ticker,
                           name=name,
                           sector=sector,
                           others=others,
                           signal_summary=signal_summary,
                           stock_names=STOCK_NAMES,
                           ssr_signal=ssr_signal,
                           kap_url=kap_url_for(ticker),
                           related_blog=related_blog,
                           compare_url=compare_url,
                           ticker_bt=ticker_bt,
                           premium_locked=premium_locked,
                           company_summary=company_summary,
                           related_stocks=related_stocks,
                           seo_faq=seo_faq,
                           seo_signal=sig,
                           seo_signal_label=sig_label,
                           seo_price=price,
                           seo_change=chg,
                           seo_score=score,
                           seo_adx=adx_val,
                           seo_rsi=rsi_val)


_fundamentals_cache = {}
_FUND_TTL = 3600 * 4  # 4 saat

# ── Temel analiz sanity sınırları (yfinance Türk hisselerinde bozuk değer üretir) ──
_FUND_SANITY = {
    "pe_ratio":       (0.0, 150.0),   # P/E > 150 → muhtemelen dolar/lira karışıklığı
    "forward_pe":     (0.0, 150.0),
    "dividend_yield": (0.0, 50.0),    # %50 üstü → imkânsız (zaten *100 çarpılmış)
    "beta":           (0.10, 5.0),    # 0.06-0.09 beta havacılık için saçma
    "pb_ratio":       (0.0, 50.0),    # P/B > 50 → bozuk
    "roe":            (-100.0, 200.0),# ROE > 200% → bozuk
    "profit_margin":  (-200.0, 100.0),
    "operating_margin":(-200.0, 100.0),
    "earnings_growth":(-500.0, 1000.0),
    "revenue_growth": (-100.0, 500.0),
    "debt_to_equity": (0.0, 2000.0),
    "current_ratio":  (0.0, 50.0),
    "price_to_sales": (0.0, 100.0),
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
    # CPO-558G: web worker'da synchronous yfinance yasak — stale/empty cache dön
    if os.environ.get("REFRESH_WORKER") == "web":
        logger.debug("_get_fundamentals(%s): REFRESH_WORKER=web — cache-only", ticker_base)
        return cached["data"] if cached else {}
    try:
        yf_ticker = ticker_base + ".IS" if ticker_base != "XU030" else "XU030.IS"
        with _YF_GLOBAL_LOCK:
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
            "pe_ratio":          round(safe("trailingPE", 0), 1) if safe("trailingPE") else None,
            "forward_pe":        round(safe("forwardPE", 0), 1) if safe("forwardPE") else None,
            "pb_ratio":          round(safe("priceToBook", 0), 2) if safe("priceToBook") else None,
            "eps":               safe("trailingEps"),
            "market_cap":        fmt_billion(safe("marketCap")),
            "revenue":           fmt_billion(safe("totalRevenue")),
            "net_income":        fmt_billion(safe("netIncomeToCommon")),
            "dividend_yield":    round(safe("dividendYield", 0), 2) if safe("dividendYield") else None,
            "roe":               round(safe("returnOnEquity", 0) * 100, 1) if safe("returnOnEquity") else None,
            "beta":              round(safe("beta", 0), 2) if safe("beta") else None,
            "shares":            fmt_billion(safe("sharesOutstanding")),
            "52w_high":          safe("fiftyTwoWeekHigh"),
            "52w_low":           safe("fiftyTwoWeekLow"),
            "avg_volume":        safe("averageVolume"),
            "short_name":        safe("shortName"),
            "profit_margin":     round(safe("profitMargins", 0) * 100, 1) if safe("profitMargins") else None,
            "operating_margin":  round(safe("operatingMargins", 0) * 100, 1) if safe("operatingMargins") else None,
            "earnings_growth":   round(safe("earningsGrowth", 0) * 100, 1) if safe("earningsGrowth") else None,
            "revenue_growth":    round(safe("revenueGrowth", 0) * 100, 1) if safe("revenueGrowth") else None,
            "debt_to_equity":    round(safe("debtToEquity", 0), 2) if safe("debtToEquity") else None,
            "current_ratio":     round(safe("currentRatio", 0), 2) if safe("currentRatio") else None,
            "price_to_sales":    round(safe("priceToSalesTrailing12Months", 0), 2) if safe("priceToSalesTrailing12Months") else None,
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



# ─── News endpoint queue pattern ───
# Pattern: cache hit → return. Miss → push to _news_fetch_queue → return null.
# _on_demand_news_worker (mevcut, 15s rate-limited) kuyruğu işler.
# THREAD SPAWN YOK → worker capacity korunur.
_news_queue_stats = {"last_added_ts": 0, "last_processed_ts": 0, "total_added": 0, "total_processed": 0}


@app.route("/api/hisse/<ticker>/news")
@limiter.limit("20 per minute")
def api_stock_news(ticker):
    """News endpoint — ARCHITECTURAL FIX: cache-or-queue pattern.

    Cache hit → return. Cache miss → bg fetch trigger (single-flight per ticker),
    return {"news": null}. Frontend zaten 8s sonra retry yapar (loadNews retry pattern).

    Request handler İÇİNDE yfinance/Gemini ÇAĞRILMAZ → worker hang riski sıfır.
    """
    ticker = ticker.upper()
    if ticker not in BIST100:
        return safe_json({"error": "Hisse bulunamadı"}), 404

    kap_url = kap_url_for(ticker)
    now_ts  = time.time()

    # 1. KAP cache check (no scrape in handler)
    with _lock:
        kap_hit = _kap_cache.get(ticker)
    kap_discs = kap_hit["data"] if (kap_hit and (now_ts - kap_hit["ts"]) < _KAP_CACHE_TTL) else None

    # 2. KAP-based news cache check
    if kap_discs:
        cache_key = f"{ticker}_kap_{kap_discs[0]['date'][:10] if kap_discs else 'none'}"
        with _lock:
            cached = _news_cache.get(cache_key)
        if cached and not cached.get("failed"):
            ttl = _NEWS_FAIL_TTL if cached.get("failed") else _news_ttl_for(ticker)
            if (now_ts - cached["ts"]) < ttl:
                return safe_json({
                    "news": cached["text"], "source": "kap_ai",
                    "kap_url": kap_url, "kap_count": len(kap_discs)
                })

    # 3. Search-grounded cache check (get_ai_news uses _news_cache[ticker])
    with _lock:
        gen_cached = _news_cache.get(ticker)
    if gen_cached and not gen_cached.get("failed"):
        ttl = _NEWS_FAIL_TTL if gen_cached.get("failed") else _news_ttl_for(ticker)
        if (now_ts - gen_cached["ts"]) < ttl and gen_cached.get("text"):
            return safe_json({"news": gen_cached["text"], "source": "gemini", "kap_url": kap_url})

    # 4. CACHE MISS — queue bg fetch (existing _on_demand_news_worker handles it)
    with _news_queue_lock:
        _news_fetch_queue.add(ticker)
    _news_queue_stats["last_added_ts"] = time.time()
    _news_queue_stats["total_added"] += 1

    # Return placeholder — frontend zaten retry yapacak (loadNews 8s sonra)
    return safe_json({"news": None, "loading": True, "kap_url": kap_url})


def get_signal_story(ticker: str, signal_date: str) -> dict:
    """Sinyal tarihi etrafındaki (-20/+5 gün) KAP bildirimleri.
    AL/SAT sinyalinin hangi haber ortamında oluştuğunu gösterir.
    """
    try:
        sig_dt = datetime.strptime(signal_date, "%d.%m.%Y")
    except ValueError:
        return {"events": [], "window_start": "", "window_end": ""}

    window_start = sig_dt - timedelta(days=20)
    window_end   = sig_dt + timedelta(days=5)

    # Son 90 günlük KAP cache'ini kullan
    now_ts = time.time()
    with _lock:
        kap_hit = _kap_cache.get(ticker)
    if kap_hit and (now_ts - kap_hit["ts"]) < _KAP_CACHE_TTL:
        all_discs = kap_hit["data"]
    else:
        all_discs = fetch_kap_disclosures(ticker, days=90)
        with _lock:
            _kap_cache[ticker] = {"data": all_discs, "ts": now_ts}

    events = []
    for d in all_discs:
        try:
            d_date = datetime.strptime(d["date"][:10], "%d.%m.%Y")
        except ValueError:
            continue
        if window_start <= d_date <= window_end:
            # Sinyal öncesi/sonrası etiketleme
            if d_date < sig_dt - timedelta(days=1):
                timing = "before"
            elif d_date > sig_dt + timedelta(days=1):
                timing = "after"
            else:
                timing = "at"
            events.append({
                **d,
                "timing": timing,
                "days_delta": (d_date - sig_dt).days,
            })

    return {
        "events": events[:10],  # En fazla 10 olay
        "window_start": window_start.strftime("%d.%m.%Y"),
        "window_end":   window_end.strftime("%d.%m.%Y"),
        "signal_date":  signal_date,
    }


@app.route("/api/hisse/<ticker>/signal-story")
@limiter.limit("20 per minute")
def api_signal_story(ticker):
    """Sinyal tarihindeki KAP bağlamı — sinyal neden oluştu?"""
    ticker = ticker.upper()
    if ticker not in BIST100:
        return safe_json({"error": "Hisse bulunamadı"}), 404

    # Signal date'i cache'den al
    with _lock:
        stocks = list(_cache.get("data") or [])
    stock = next((s for s in stocks if s.get("ticker") == ticker), None)
    if not stock:
        return safe_json({"error": "Veri yok", "events": []})

    signal_date = stock.get("signal_date", "")
    if not signal_date:
        return safe_json({"error": "Sinyal tarihi yok", "events": []})

    story = get_signal_story(ticker, signal_date)
    story["signal"]      = stock.get("signal", "BEKLE")
    story["signal_bars"] = stock.get("signal_bars", 0)
    story["ticker"]      = ticker
    return safe_json(story)


@app.route("/api/hisse/<ticker>/kap")
@limiter.limit("30 per minute")
def api_stock_kap(ticker):
    """KAP bildirimleri — 30 dakikalık cache. Son 90 günlük ODA + FR."""
    ticker = ticker.upper()
    if ticker not in BIST100:
        return safe_json({"error": "Hisse bulunamadı"}), 404

    now = time.time()
    with _lock:
        cached = _kap_cache.get(ticker)
        if cached and (now - cached["ts"]) < _KAP_CACHE_TTL:
            return safe_json({"disclosures": cached["data"], "cached": True})

    disclosures = fetch_kap_disclosures(ticker, days=90)
    with _lock:
        _kap_cache[ticker] = {"data": disclosures, "ts": now}

    return safe_json({
        "disclosures": disclosures,
        "ticker": ticker,
        "kap_search_url": f"https://www.kap.org.tr/tr/bildirim-sorgu?q={ticker}",
        "cached": False,
    })


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
            # CPO-586: web worker'da synchronous yfinance yasak — stale cache yok, no_data
            if os.environ.get("REFRESH_WORKER") == "web":
                return safe_json({"explanation": None, "reason": "no_data"})
            # Cache yok — hesapla (ilk açılış gecikir ama sonrası cache'den gelir)
            data = _compute_chart_data(ticker, "2y")
            upd  = datetime.now(_TZ_TR).strftime("%d.%m.%Y %H:%M:%S")
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
                             progress=False, auto_adjust=True, timeout=25, threads=False)
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
                             progress=False, auto_adjust=True, timeout=25, threads=False)
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

    # CPO-585: web worker'da synchronous yfinance yasak — stale veya boş döner, warmup daemon dolduracak
    if os.environ.get("REFRESH_WORKER") == "web":
        with _lock:
            stale = _mtf_cache.get(ticker)
        return safe_json(stale["data"] if stale else {})

    data = _compute_mtf(ticker)
    with _lock:
        _mtf_cache[ticker] = {"data": data, "ts": now}
    return safe_json(data)


# SPEC-008 L1 — Chart Integrity Guard. Bozuk/stale chart fiyatı ana fiyattan
# saparsa kullanıcıya ASLA bozuk grafik render edilmez (GSDHO 3.08× bug fix).
# SPEC-008 v1.2 #39 — Post-restart grace: main_price referansı henüz fresh
# değilse (>300s eski veya bilinmiyor) guard graceful skip yapar — restart
# sonrası FP penceresini elimine eder (AKBNK/THYAO 14:44 FP olayı).
_CHART_SUMMARY_TOL_PCT  = 3    # summary.price — intraday dalga toleransı
_CHART_OHLC_TOL_PCT     = 20   # last ohlc close — split tolere
_CHART_MAIN_GRACE_S     = 300  # main_price 5dk+ eski ise guard ATLA (#39)

def validate_chart_integrity(ticker, chart_data, main_price, main_price_age_s=None):
    """Chart fiyatı ana cache fiyatıyla tutarlı mı? (valid, reason).
    main_price/veri yoksa True (graceful — engelleme yok).
    main_price_age_s None veya > 300 → grace skip (referans stale, FP riski)."""
    if not chart_data or not main_price or main_price <= 0:
        return True, None
    # #39 — referans tazelik kontrolü
    if main_price_age_s is None or main_price_age_s > _CHART_MAIN_GRACE_S:
        return True, None
    summary_price = (chart_data.get("summary") or {}).get("price")
    ohlc = chart_data.get("ohlc") or []
    last_close = ohlc[-1].get("close") if (ohlc and isinstance(ohlc[-1], dict)) else None
    if summary_price and abs(summary_price - main_price) / main_price * 100 > _CHART_SUMMARY_TOL_PCT:
        return False, f"summary.price {summary_price} vs main {main_price} (>%{_CHART_SUMMARY_TOL_PCT})"
    if last_close and abs(last_close - main_price) / main_price * 100 > _CHART_OHLC_TOL_PCT:
        return False, f"last_ohlc.close {last_close} vs main {main_price} (>%{_CHART_OHLC_TOL_PCT})"
    return True, None


@app.route("/api/hisse/<ticker>/chart")
def api_stock_chart(ticker):
    ticker = ticker.upper()
    if ticker not in BIST30:
        return safe_json({"error": "Hisse bulunamadı"}), 404

    now = time.time()

    # ── Otoritelif sinyal kaynağı: ana cache ──────────────────────────────
    with _lock:
        stocks          = list(_cache["data"])
        cached          = _stock_chart_cache.get(ticker)
        main_refresh_ts = _cache.get("last_refresh_ts", 0.0)  # SPEC-008 v1.2 #39
    main_stock = next((s for s in stocks if s.get("ticker") == ticker), None)
    main_price = main_stock.get("price", 0) if main_stock else 0
    # main_price yaşı (saniye) — grace penceresi için (>300s → guard atlar)
    main_price_age_s = (now - main_refresh_ts) if main_refresh_ts > 0 else None

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

    # SPEC-008 L4a — cache version guard: entry "v" sabite uymuyorsa miss say.
    if cached and cached.get("v") != _CHART_CACHE_VERSION:
        logger.info("Chart cache version mismatch [%s]: %r != %r — invalidate",
                    ticker, cached.get("v"), _CHART_CACHE_VERSION)
        cached = None

    if cached and (now - cached["ts"]) < _STOCK_CACHE_TTL:
        data = cached["data"]
        upd  = cached["updated_at"]
    else:
        # SPEC-DECOUPLING-v2-PHASE3 M3 (CPO-449): Worker SADECE per-ticker disk cache okur.
        # _compute_chart_data ÇAĞRILMAZ — ASLA senkron fetch, ASLA blok (gevent hub temiz).
        # Cache miss → stale veri yok → loading:true döner (frontend skeleton).
        data, upd = _load_chart_from_disk_per_ticker(ticker)
        # Cache miss durumunda fetch YOK — fetcher daemon arkada cache'i doldurur,
        # frontend retry/refresh ile alacak. Worker render path TAMAMEN BLOK-FREE.

    if not data:
        return safe_json({"chart": None, "loading": True, "reason": "cache_miss_read_only_mode"})

    # ── SPEC-008 L1: Chart Integrity Guard ───────────────────────────────────
    # FINAL doğrulama — bozuk chart ASLA render edilmez. Sapma varsa cache iptal
    # + recompute; recompute de bozuksa integrity_error döner (frontend skeleton).
    if main_price > 0:
        ok, reason = validate_chart_integrity(ticker, data, main_price, main_price_age_s)
        if not ok:
            logger.warning("SPEC-008 chart integrity FAIL [%s]: %s — recompute", ticker, reason)
            # CPO-565 Bug 2: web worker'da yfinance yasak — fetcher daemon dolduracak
            if os.environ.get("REFRESH_WORKER") == "web":
                logger.warning("SPEC-008 integrity recompute [%s]: REFRESH_WORKER=web — loading döner", ticker)
                return safe_json({"chart": None, "loading": True, "reason": "integrity_fail_web_worker"})
            with _lock:
                _stock_chart_cache.pop(ticker, None)
            fresh = _compute_chart_data(ticker, period="2y")
            if fresh:
                data = fresh
                upd  = datetime.now(_TZ_TR).strftime("%d.%m.%Y %H:%M:%S")
                with _lock:
                    _stock_chart_cache[ticker] = {"data": data, "ts": now,
                                                  "updated_at": upd, "v": _CHART_CACHE_VERSION}
                ok2, reason2 = validate_chart_integrity(ticker, data, main_price, main_price_age_s)
            else:
                ok2, reason2 = False, "recompute başarısız (veri yok)"
            if not ok2:
                logger.error("SPEC-008 chart integrity recompute de FAIL [%s]: %s → integrity_error",
                             ticker, reason2)
                # SPEC-008 L5 — recent integrity-error tracker (alarm loop tarafından okunur)
                with _lock:
                    _chart_integrity_errors[ticker] = time.time()
                return safe_json({"chart": None, "loading": True, "integrity_error": reason2})

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
            "rvol":          s.get("rvol"),
            "is_premium":    s.get("is_premium", False),
            "tier":          s.get("tier"),   # SPEC-007: paywall için (premium/plus/standart/None)
            "bull_score":    s.get("bull_score") or 0,
            "sl_level":      s.get("sl_level"),
        })

    sort_dir = request.args.get("sort_dir", "")  # asc | desc | (default desc)
    only_premium = request.args.get("only_premium", "") == "1"
    if only_premium:
        results = [r for r in results if r.get("is_premium")]
    if sort_dir in ("asc", "desc"):
        rev = sort_dir == "desc"
    else:
        rev = sort_by in ("adx","price","signal_bars","vol_ratio","bull_score","change_pct")
    results.sort(key=lambda x: (x.get(sort_by) or 0), reverse=rev)

    with _lock:
        sectors = sorted(set(_get_sector(s.get("ticker","")) for s in _cache["data"]
                             if s.get("ticker") not in ("XU030","XU100")))

    return jsonify({"results": results, "sectors": sectors,
                    "count": len(results), "updated_at": upd})


# ── SEO: sitemap, robots, favicon ────────────────────────────────────────────
_sitemap_cache: dict = {}  # {"xml": str, "date": str}

def _compute_health():
    """Health verisini hesaplar — _lock alır. SPEC-016 K4: yalnız bg thread çağırır,
    request path'te DEĞİL → /api/health _lock contention'da bloke olmaz.

    CPO-551 Aşama 2: OK/DEGRADED/CRITICAL semantics + components + message.
    Seans dışında (market_open=False) stocks/macro stale DEGRADED/CRITICAL tetiklemez.
    Eşikler: stocks 900s=DEGRADED 1800s=CRITICAL; macro 1800s=DEGRADED 3600s=CRITICAL.
    """
    now = time.time()
    with _lock:
        stocks_count    = len(_cache.get("data") or [])
        cache_loading   = _cache.get("loading", True)
        cache_updated   = _cache.get("updated_at", "—")
        last_refresh_ts = _cache.get("last_refresh_ts", 0) or 0
        macro_count     = len(_macro_cache.get("data") or [])
        macro_ts        = _macro_cache.get("ts", 0)

    mkt_open    = _market_open()
    stocks_age_s = int(now - last_refresh_ts) if last_refresh_ts else None
    macro_age_s  = int(now - macro_ts) if macro_ts else None
    macro_stale  = macro_age_s is None or macro_age_s > _MACRO_TTL

    # ── Component durumları ── (seans dışında stale OK — normal davranış)
    if stocks_count == 0:
        stocks_status = "critical"
    elif not mkt_open:
        stocks_status = "ok"
    elif stocks_age_s is None or stocks_age_s > 1800:
        stocks_status = "critical"
    elif stocks_age_s > 900:
        stocks_status = "degraded"
    else:
        stocks_status = "ok"

    if macro_count == 0:
        macro_status = "critical"
    elif not mkt_open:
        macro_status = "ok"
    elif macro_age_s is None or macro_age_s > 3600:
        macro_status = "critical"
    elif macro_age_s > 1800:
        macro_status = "degraded"
    else:
        macro_status = "ok"

    # ── Genel status: en kötü component ──
    if "critical" in (stocks_status, macro_status):
        status = "CRITICAL"
    elif "degraded" in (stocks_status, macro_status):
        status = "DEGRADED"
    else:
        status = "OK"

    # ── Mesaj ──
    msg_parts = []
    if stocks_status == "critical":
        msg_parts.append(f"stocks {stocks_age_s}s stale" if stocks_age_s else "stocks data yok")
    elif stocks_status == "degraded":
        msg_parts.append(f"stocks {stocks_age_s}s stale")
    if macro_status == "critical":
        msg_parts.append(f"macro {macro_age_s}s stale" if macro_age_s else "macro data yok")
    elif macro_status == "degraded":
        msg_parts.append(f"macro {macro_age_s}s stale")
    if not msg_parts:
        message = "seans dışı" if not mkt_open else "tüm sistemler normal"
    else:
        message = "; ".join(msg_parts)

    macro_last_ts = _macro_bg_stats.get("last_success_ts", 0)
    news_last_ts  = _news_queue_stats.get("last_processed_ts", 0)
    return {
        "ok":          status == "OK",
        "status":      status,
        "message":     message,
        "market_open": mkt_open,
        "components": {
            "stocks": stocks_status,
            "macro":  macro_status,
        },
        "stocks": {
            "count":   stocks_count,
            "loading": cache_loading,
            "updated": cache_updated,
            "age_s":   stocks_age_s,
        },
        "macro": {
            "count": macro_count,
            "age_s": macro_age_s,
            "stale": macro_stale,
        },
        "macro_bg_loop":            _macro_bg_stats,
        "last_macro_refresh_ts":    macro_last_ts,
        "last_macro_refresh_age_s": int(now - macro_last_ts) if macro_last_ts else None,
        "news_queue":               _news_queue_stats,
        "last_news_queue_ts":       news_last_ts,
        "last_news_queue_age_s":    int(now - news_last_ts) if news_last_ts else None,
        "data_freshness":           build_data_freshness(),  # SPEC-014 B1
        "market_data_age_s":         stocks_age_s,                           # CPO-590 madde 4
        "chart_integrity_recent":   _chart_integrity_count_recent(now),  # SPEC-008 L5
        "ts": now,
    }


# SPEC-016 K4 — /api/health lock-free decouple.
# Health hesabı (_lock alır) bg thread'de yapılır; endpoint snapshot'ı lock-free
# okur. _lock contention / gevent yavaşlamasında bile /api/health anında 200 döner
# → watchdog yanlış HTTP=000 görmez → restart churn döngüsü kırılır (#48 ailesi).
_health_snapshot = {"ok": True, "status": "STARTING", "ts": 0.0, "note": "warming up"}

def _health_snapshot_loop():
    global _health_snapshot
    while True:
        try:
            _health_snapshot = _compute_health()   # atomic rebind (GIL)
        except Exception as e:
            logger.error("health snapshot loop: %s", e)
        time.sleep(8)

threading.Thread(target=_health_snapshot_loop, daemon=True, name="health-snapshot").start()
logger.info("Health snapshot loop başlatıldı (SPEC-016 K4 — /api/health lock-free)")


@app.route("/api/health")
def api_health():
    """Health + observability endpoint — SPEC-016 K4 lock-free.

    Production monitoring (UptimeRobot, watchdog) için 1dk poll edilebilir.
    Snapshot bg thread'de güncellenir (8s) → endpoint hiç _lock almaz,
    contention/gevent yavaşlamasında bile anında yanıt verir."""
    return safe_json(_health_snapshot)


@app.route("/sitemap.xml")
def sitemap():
    today = date.today().isoformat()
    if _sitemap_cache.get("date") == today and _sitemap_cache.get("xml"):
        return Response(_sitemap_cache["xml"], mimetype="application/xml")
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
    pages.append({"loc": "/hisseler",          "priority": "0.85", "changefreq": "daily"})
    pages.append({"loc": "/bilanco-takvimi",    "priority": "0.8", "changefreq": "weekly"})
    pages.append({"loc": "/gundem",             "priority": "0.8", "changefreq": "daily"})
    pages.append({"loc": "/karsilastir",        "priority": "0.6", "changefreq": "monthly"})
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
    xml_str = "\n".join(xml)
    _sitemap_cache.update({"xml": xml_str, "date": today})
    return Response(xml_str, mimetype="application/xml")


@app.route("/robots.txt")
def robots():
    body = """# borsapusula.com — robots.txt
# Allow major search engines + reputation crawlers explicitly

User-agent: Googlebot
Allow: /
Disallow: /api/

User-agent: Bingbot
Allow: /
Disallow: /api/

User-agent: Yandex
Allow: /
Disallow: /api/

User-agent: DuckDuckBot
Allow: /
Disallow: /api/

User-agent: Slurp
Allow: /
Disallow: /api/

# Reputation/security scanners — explicit allow
User-agent: facebookexternalhit
Allow: /

User-agent: Twitterbot
Allow: /

User-agent: LinkedInBot
Allow: /

User-agent: WhatsApp
Allow: /

User-agent: Applebot
Allow: /

# AI crawlers — allow (we want indexing)
User-agent: GPTBot
Allow: /
Disallow: /api/

User-agent: ClaudeBot
Allow: /
Disallow: /api/

User-agent: PerplexityBot
Allow: /
Disallow: /api/

# Default rule
User-agent: *
Allow: /
Disallow: /api/
Disallow: /admin/

# Aggressive scrapers — explicit deny
User-agent: SemrushBot
Disallow: /

User-agent: AhrefsBot
Disallow: /

User-agent: MJ12bot
Disallow: /

User-agent: DotBot
Disallow: /

# Crawl-delay for politeness
Crawl-delay: 5

# Sitemaps
Sitemap: https://borsapusula.com/sitemap.xml
"""
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


@app.route("/.well-known/security.txt")
def security_txt():
    """RFC 9116 — Security Researchers contact channel."""
    body = """# borsapusula.com — Security Policy (RFC 9116)
Contact: mailto:security@borsapusula.com
Contact: mailto:iletisim@borsapusula.com
Expires: 2027-12-31T23:59:59.000Z
Preferred-Languages: tr, en
Canonical: https://borsapusula.com/.well-known/security.txt
Policy: https://borsapusula.com/yasal
Acknowledgments: https://borsapusula.com/hakkinda

# We welcome responsible disclosure of security vulnerabilities.
# Please email us with details and we will respond within 5 business days.
# Out of scope: DoS, social engineering, missing CSP headers, version disclosure.
"""
    return Response(body, mimetype="text/plain", headers={
        "Cache-Control": "public, max-age=86400",
        "X-Robots-Tag": "noindex, nofollow",
    })


@app.route("/security.txt")
def security_txt_alias():
    """Alias for /.well-known/security.txt"""
    return security_txt()


@app.route("/humans.txt")
def humans_txt():
    """humanstxt.org — site arkasındaki insanlar."""
    body = """/* borsapusula.com — humans.txt */
/* https://humanstxt.org */

/* TEAM */
    Founder & Product: BorsaPusula Ekibi
    Site: https://borsapusula.com
    Contact: iletisim [at] borsapusula.com
    Location: Istanbul, Türkiye

/* THANKS */
    Topluluğumuza, geri bildirim veren tüm yatırımcılara teşekkürler.

/* SITE */
    Last update: 2026/05/08
    Language: Türkçe (TR)
    Doctype: HTML5
    Standards: HTML5, CSS3, ECMAScript 2022
    Components: Lightweight Charts, Chart.js
    Software: Python (Flask), JavaScript (Vanilla), Cloudflare CDN
    Methodology: Algoritmik teknik analiz — Supertrend(10,3) + ADX(14) + EMA12/99

/* MISSION */
    Türk yatırımcılarına şeffaf, ücretsiz, algoritmik BIST sinyal aracı sunmak.
    Backtest ile her zaman doğrulanan, açık kaynaklı metodoloji.
"""
    return Response(body, mimetype="text/plain; charset=utf-8", headers={
        "Cache-Control": "public, max-age=86400",
    })


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


# ── Hisse Karşılaştırma ──────────────────────────────────────────────────────
@app.route("/karsilastir")
def karsilastir():
    """SPEC-011 L1+L2 — Query-param normalize + self-canonical + dinamik meta.
    `?tickers=` farklı varyasyonları (case/sıra/duplicate) tek canonical URL'e
    301 ile yönlendirir → Google duplicate dropluyor sorununu çözer (#40)."""
    raw = request.args.get("tickers", "").strip()
    base = "https://borsapusula.com"
    canonical_url    = f"{base}/karsilastir"
    page_title       = "Hisse Karşılaştırma — BorsaPusula"
    page_description = ("BIST hisselerini teknik sinyal, temel analiz ve yatırım skoru ile "
                        "yan yana karşılaştırın. F/K, ROE, ADX, RSI, R/R ve daha fazlası.")
    tickers_param    = raw

    if raw:
        # Normalize: trim + upper + dedup + alfabetik sırala (max 4 — API ile uyumlu)
        tickers = sorted({t.strip().upper() for t in raw.split(",") if t.strip()})[:4]
        if tickers:
            norm = ",".join(tickers)
            if raw != norm:
                # Case/sıra/duplicate farkı → 301 canonical'a
                return redirect(f"/karsilastir?tickers={norm}", code=301)
            canonical_url = f"{base}/karsilastir?tickers={norm}"
            tickers_param = norm
            # Title: 3'e kadar listele, daha fazlası → "X, Y, Z +N daha"
            if len(tickers) > 3:
                title_list = ", ".join(tickers[:3]) + f" +{len(tickers)-3} daha"
            else:
                title_list = ", ".join(tickers)
            page_title = f"{title_list} Karşılaştırma — BorsaPusula"
            page_description = (f"{', '.join(tickers)} hisselerini teknik sinyal, "
                                f"F/K, ROE, ADX, RSI ve yatırım skoru ile yan yana karşılaştırın.")
    return render_template("karsilastir.html",
                           tickers_param=tickers_param,
                           canonical_url=canonical_url,
                           page_title=page_title,
                           page_description=page_description,
                           today_iso=date.today().isoformat())


@app.route("/api/karsilastir")
@limiter.limit("30 per minute")
def api_karsilastir():
    """2-4 hisseyi yan yana karşılaştır — tüm sinyal metrikleri."""
    tickers = [t.strip().upper() for t in
               request.args.get("tickers", "").split(",")
               if t.strip()][:4]
    if not tickers:
        return safe_json({"error": "tickers parametresi gerekli"}), 400

    with _lock:
        data_map = {s["ticker"]: s for s in _cache["data"]}

    results = []
    for ticker in tickers:
        s = data_map.get(ticker, {})
        inds      = s.get("indicators") or {}
        adx_label = (inds.get("adx") or {}).get("label", "")
        try:
            adx_val = float(adx_label.replace("ADX", "").strip()) if adx_label else None
        except (ValueError, TypeError):
            adx_val = None
        # Temel analiz verileri (sadece BIST hisseleri ve veri varsa)
        fund = _get_fundamentals(ticker) if ticker in BIST100 and bool(s) else {}
        results.append({
            "ticker":         ticker,
            "name":           STOCK_NAMES.get(ticker, US_STOCK_NAMES.get(ticker, ticker)),
            "signal":         s.get("signal"),
            "price":          s.get("price"),
            "change_pct":     s.get("change_pct"),
            "adx":            adx_val,
            "rsi":            s.get("rsi"),
            "signal_bars":    s.get("signal_bars"),
            "signal_date":    s.get("signal_date"),
            "entry_quality":  s.get("entry_quality"),
            "sl_level":       s.get("sl_level"),
            "tp1":            s.get("tp1"),
            "tp2":            s.get("tp2"),
            "rr_ratio":       s.get("rr_ratio"),
            "bull_score":     s.get("bull_score"),
            "bear_score":     s.get("bear_score"),
            "sector":         _get_sector(ticker),
            "kap_url":        kap_url_for(ticker),
            # ── Temel analiz ───────────────────────────────
            "pe_ratio":       fund.get("pe_ratio"),
            "pb_ratio":       fund.get("pb_ratio"),
            "market_cap":     fund.get("market_cap"),
            "roe":            fund.get("roe"),
            "dividend_yield": fund.get("dividend_yield"),
            "eps":            fund.get("eps"),
            "profit_margin":  fund.get("profit_margin"),
            "found":          bool(s),
        })
    return safe_json({"stocks": results, "count": len(results)})


@app.route("/api/stocks/list")
@limiter.limit("60 per minute")
def api_stocks_list():
    """Autocomplete için tüm hisseler: ticker + isim listesi"""
    result = [{"ticker": t, "name": STOCK_NAMES.get(t, t)}
              for t in BIST100 if t != "XU030"]
    return safe_json({"stocks": result})


# ── Piyasa Gündem Merkezi ────────────────────────────────────────────────────
@app.route("/gundem")
def gundem_page():
    return render_template("gundem.html")


@app.route("/api/gundem")
@limiter.limit("30 per minute")
def api_gundem():
    """Piyasa Gündem API — bugün değişen sinyaller, güçlü trendler, sinyal özeti."""
    with _lock:
        stocks = list(_cache["data"])

    today = date.today().strftime("%d.%m.%Y")

    # Bugün sinyal alan hisseler
    new_signals = [s for s in stocks
                   if s.get("signal_date") == today and s.get("signal") != "BEKLE"]

    # ADX sıralamalı en güçlü AL hisseler
    def _adx_val(s):
        inds = s.get("indicators") or {}
        lbl  = (inds.get("adx") or {}).get("label", "")
        try:
            return float(lbl.replace("ADX", "").strip())
        except Exception:
            return 0.0

    strong_al = sorted(
        [s for s in stocks if s.get("signal") == "AL"],
        key=_adx_val, reverse=True
    )[:8]

    # Yaklaşan bilanço dönemleri (gündem için)
    today_dt  = date.today()
    today_iso = today_dt.isoformat()
    bilanco_upcoming = []
    for qlabel, start, end, desc in _BILANCO_PERIODS:
        if end < today_iso:
            continue
        start_dt      = date.fromisoformat(start)
        end_dt        = date.fromisoformat(end)
        days_to_end   = (end_dt   - today_dt).days
        days_to_start = (start_dt - today_dt).days
        bilanco_upcoming.append({
            "label":      qlabel,
            "desc":       desc,
            "start":      start,
            "end":        end,
            "status":     "active" if today_dt >= start_dt else "upcoming",
            "days_label": f"{days_to_end} gün kaldı" if today_dt >= start_dt else f"{days_to_start} gün sonra",
        })
        if len(bilanco_upcoming) >= 2:
            break

    return safe_json({
        "new_signals": new_signals,
        "strong_al":   strong_al,
        "updated_at":  datetime.now(_TZ_TR).strftime("%d.%m.%Y %H:%M"),
        "signal_summary": {
            "al":    sum(1 for s in stocks if s.get("signal") == "AL"),
            "sat":   sum(1 for s in stocks if s.get("signal") == "SAT"),
            "bekle": sum(1 for s in stocks if s.get("signal") == "BEKLE"),
            "total": len(stocks),
        },
        "bilanco_upcoming": bilanco_upcoming,
    })


# ── Geçmiş Günlük Snapshot API ───────────────────────────────────────────────
@app.route("/api/snapshots")
@limiter.limit("30 per minute")
def api_snapshots():
    """Mevcut günlük snapshot tarihlerini listele."""
    try:
        files = sorted([
            f.replace(".json", "")
            for f in os.listdir(_SNAPSHOTS_DIR)
            if re.match(r"^\d{4}-\d{2}-\d{2}\.json$", f)
        ], reverse=True)
        return safe_json({"dates": files[:30]})  # son 30 gün
    except Exception as e:
        return safe_json({"dates": [], "error": str(e)})


@app.route("/ozet/<tarih>")
def ozet_gecmis(tarih):
    """Geçmiş tarihli sinyal özeti."""
    if not re.match(r"^\d{4}-\d{2}-\d{2}$", tarih):
        abort(404)
    fname = os.path.join(_SNAPSHOTS_DIR, f"{tarih}.json")
    if not os.path.exists(fname):
        abort(404)
    try:
        with open(fname, encoding="utf-8") as f:
            snap = json.load(f)
    except Exception:
        abort(404)

    stocks     = snap.get("stocks", [])
    # Add sector field (not stored in snapshot) — fixes groupby error
    for s in stocks:
        if "sector" not in s:
            s["sector"] = _get_sector(s["ticker"])
    al_list    = [s for s in stocks if s.get("signal") == "AL"]
    sat_list   = [s for s in stocks if s.get("signal") == "SAT"]
    bekle_list = [s for s in stocks if s.get("signal") == "BEKLE"]
    new_signals = [s for s in stocks if s.get("is_new_signal")]
    return render_template("ozet.html",
        stocks=stocks, loading=False,
        updated_at=snap.get("date_tr", tarih),
        al_list=al_list, sat_list=sat_list, bekle_list=bekle_list,
        new_signals=new_signals, today_str=snap.get("date_tr", tarih),
        stock_names=STOCK_NAMES,
        historical_date=tarih)


@app.route("/api/ozet/snapshots")
def api_ozet_snapshots():
    """Mevcut geçmiş özet tarihlerini listele."""
    try:
        files = sorted([
            f.replace(".json", "")
            for f in os.listdir(_SNAPSHOTS_DIR)
            if re.match(r"^\d{4}-\d{2}-\d{2}\.json$", f)
        ], reverse=True)
        return safe_json({"dates": files[:90]})  # Son 90 gün max
    except Exception as e:
        logger.error("Snapshot list: %s", e)
        return safe_json({"dates": []})


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

    # Sadece AL/SAT sinyallerini al; compose_score ile sırala (CPO-535 #36)
    # momentum_score() kaldırıldı → compose_score() top-level (tutarlılık: hisse detay ↔ liste)
    active = [s for s in stocks if s.get("signal") in ("AL", "SAT") and s.get("ticker") != "XU030"]
    for s in active:
        _bs = s.get("bull_score") if s.get("signal") == "AL" else (s.get("bear_score") or 0)
        try:
            _adx = float(str(s.get("adx") or 0).replace(",", "."))
        except Exception:
            _adx = 0.0
        s["_mscore"] = compose_score(
            adx=_adx,
            vol_ratio=float(s.get("vol_ratio") or 1.0),
            bull_score=int(_bs or 0),
            confirmed=bool(s.get("confirmed")),
            rsi=float(s.get("rsi") or 50),
        )
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


# ── Sunucu Taraflı Portföy (UUID Token Bazlı) ─────────────────────────────────
_PF_DIR = os.path.join(_APP_DIR, "portfolios")
os.makedirs(_PF_DIR, exist_ok=True)

_PF_MAX_ENTRIES  = 100     # Token başına maksimum pozisyon
_PF_MAX_BYTES    = 65536   # 64KB — saldırı hafifletme
_PF_LOCK         = threading.Lock()


def _pf_path(token: str) -> str | None:
    """Token güvenlik kontrolü — path traversal koruma."""
    if not re.match(r'^[0-9a-f\-]{36}$', token):  # UUID4 formatı
        return None
    return os.path.join(_PF_DIR, f"{token}.json")


@app.route("/api/portfolio/new", methods=["POST"])
@limiter.limit("10 per hour")
def api_portfolio_new():
    """Yeni UUID token oluştur."""
    token = str(__import__('uuid').uuid4())
    path  = _pf_path(token)
    with _PF_LOCK:
        with open(path, "w", encoding="utf-8") as f:
            json.dump({"positions": [], "created_at": datetime.now().isoformat()}, f)
    return safe_json({"token": token})


@app.route("/api/portfolio/<token>", methods=["GET"])
@limiter.limit("60 per minute")
def api_portfolio_get(token):
    """Token'a ait portföyü getir."""
    path = _pf_path(token)
    if not path:
        return safe_json({"error": "Geçersiz token"}), 400
    if not os.path.exists(path):
        return safe_json({"error": "Portföy bulunamadı"}), 404
    try:
        with _PF_LOCK:
            with open(path, encoding="utf-8") as f:
                data = json.load(f)
        return safe_json(data)
    except Exception as e:
        logger.error("Portfolio get [%s]: %s", token, e)
        return safe_json({"error": "Sunucu hatası"}), 500


@app.route("/api/portfolio/<token>", methods=["POST"])
@limiter.limit("30 per minute")
def api_portfolio_save(token):
    """Token'a ait portföyü kaydet."""
    path = _pf_path(token)
    if not path:
        return safe_json({"error": "Geçersiz token"}), 400

    # Content-Length kontrolü — büyük payload'ları reddet
    cl = request.content_length
    if cl and cl > _PF_MAX_BYTES:
        return safe_json({"error": "Veri çok büyük"}), 413
    raw = request.get_data()
    if len(raw) > _PF_MAX_BYTES:
        return safe_json({"error": "Veri çok büyük"}), 413

    try:
        body = json.loads(raw)
    except (ValueError, TypeError):
        return safe_json({"error": "Geçersiz JSON"}), 400

    positions = body.get("positions", [])
    if not isinstance(positions, list):
        return safe_json({"error": "positions listesi gerekli"}), 400
    if len(positions) > _PF_MAX_ENTRIES:
        return safe_json({"error": f"Maksimum {_PF_MAX_ENTRIES} pozisyon izin verilir"}), 400

    # Sadece izin verilen alanları kaydet (injection güvenliği)
    ALLOWED = {"id","ticker","name","buy_price","quantity","date","note","sector"}
    clean = []
    for p in positions:
        if not isinstance(p, dict):
            continue
        entry = {k: v for k, v in p.items() if k in ALLOWED}
        # Tip güvenliği: fiyat ve miktar sayısal olmalı
        if "buy_price" in entry:
            try: entry["buy_price"] = float(entry["buy_price"])
            except (ValueError, TypeError): entry["buy_price"] = 0.0
        if "quantity" in entry:
            try: entry["quantity"] = float(entry["quantity"])
            except (ValueError, TypeError): entry["quantity"] = 0.0
        # String alanları kırp
        for k in ("ticker","name","date","note","sector"):
            if k in entry and isinstance(entry[k], str):
                entry[k] = entry[k][:200]
        clean.append(entry)

    payload = {
        "positions":   clean,
        "updated_at":  datetime.now().isoformat(),
        "count":       len(clean),
    }

    try:
        with _PF_LOCK:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(payload, f, ensure_ascii=False)
        return safe_json({"ok": True, "count": len(clean)})
    except Exception as e:
        logger.error("Portfolio save [%s]: %s", token, e)
        return safe_json({"error": "Sunucu hatası"}), 500


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
                         progress=False, auto_adjust=True, timeout=30, threads=False)
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
        "per_ticker":  sorted(per_ticker, key=lambda x: (-x["al_count"], -x["sat_count"])),
        "computed_at": datetime.now(_TZ_TR).strftime("%d.%m.%Y %H:%M"),
        "tickers_used": len(bt_tickers),
    }
    with _lock:
        _bt_cache["data"]        = result
        _bt_cache["computed_at"] = result["computed_at"]
    logger.info("Backtest tamamlandı: %d AL, %d SAT episod",
                result["al"]["count"], result["sat"]["count"])
    # Diske kaydet — restart sonrası anında yüklenir
    try:
        with open(_BT_DISK_PATH, "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False)
        logger.info("Backtest diske kaydedildi: %s", _BT_DISK_PATH)
    except Exception as e:
        logger.warning("Backtest disk yazma hatası: %s", e)


# ── SPEC-007: Site-wide Premium Paywall — has_premium_access helper ──────────
def has_premium_access():
    """Kullanıcının Premium erişimi var mı? bp_premium_trial cookie (email submit sonrası)."""
    try:
        return request.cookies.get("bp_premium_trial") == "1"
    except Exception:
        return False

@app.context_processor
def _inject_premium_status():
    """SPEC-007: Tüm Jinja template'lerinde has_premium_access + premium_count."""
    try:
        with _lock:
            _stocks = list(_cache.get("data") or [])
        pc = sum(1 for s in _stocks if s.get("tier") == "premium")
    except Exception:
        pc = 0
    return dict(has_premium_access=has_premium_access(), premium_count=pc)


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
    require_admin()
    threading.Thread(target=run_backtest, daemon=True).start()
    return jsonify({"status": "started"})


@app.route("/nasdaq")
def _redir_nasdaq():
    return redirect("/abd/nasdaq", code=301)

@app.route("/sp500")
def _redir_sp500():
    return redirect("/abd/sp500", code=301)

@app.route("/dow")
@app.route("/djia")
def _redir_dow():
    return redirect("/abd", code=301)


@app.route("/hisseler")
def hisseler_hub():
    """SEO hub — Tüm BIST hisseleri sektör + alfabetik. SSR ile 215 internal link."""
    # Sektörlere göre grupla (sadece BIST100 içinde olanlar)
    bist_set = set(BIST100) - {"XU030", "XU100"}
    by_sector = {}
    for sector, tickers in SECTORS.items():
        active = [t for t in tickers if t in bist_set]
        if active:
            # Her sektörde ticker → name çiftleri, alfabetik
            items = sorted(
                [(t, STOCK_NAMES.get(t, t)) for t in active],
                key=lambda x: x[0]
            )
            by_sector[sector] = items
    # Sektörsüz/Diğer
    in_any = set()
    for items in by_sector.values():
        for t, _ in items:
            in_any.add(t)
    others = sorted([t for t in bist_set if t not in in_any])
    if others:
        by_sector["Diğer"] = [(t, STOCK_NAMES.get(t, t)) for t in others]

    # Alfabetik tam liste (her harf grubu)
    all_pairs = sorted(
        [(t, STOCK_NAMES.get(t, t)) for t in bist_set],
        key=lambda x: x[0]
    )
    by_letter = {}
    for t, n in all_pairs:
        first = t[0].upper()
        by_letter.setdefault(first, []).append((t, n))
    letters_sorted = sorted(by_letter.keys())

    # Sektörler alfabetik
    sectors_sorted = sorted(by_sector.keys())

    return render_template(
        "hisseler.html",
        by_sector=by_sector,
        sectors_sorted=sectors_sorted,
        by_letter=by_letter,
        letters_sorted=letters_sorted,
        total_count=len(all_pairs),
    )


@app.route("/sektor-harita")
def sektor_harita():
    return render_template("sektor_harita.html")


# ── Bilanço Takvimi ───────────────────────────────────────────────────────────
_earnings_cache      = {"data": None, "ts": 0}
_EARNINGS_TTL        = 3600 * 12   # 12 saat
_earnings_refreshing = False         # arka plan yenileme kilidi

# BIST'te finansal sonuçlar genellikle şu dönemlerde açıklanır:
# Q4 (Ekim-Aralık bilanços): Mart-Nisan
# Q1 (Ocak-Mart bilanços):   Mayıs ortası
# Q2/H1 (Nisan-Haziran):     Ağustos-Eylül
# Q3 (Temmuz-Eylül):         Ekim-Kasım
_BILANCO_PERIODS = [
    # (quarter_label, est_start_mm_dd, est_end_mm_dd, description)
    ("Q4 2025 (Yıllık)", "2026-03-01", "2026-05-31", "2025 yıl sonu bilanço açıklamaları"),
    ("Q1 2026",          "2026-04-15", "2026-06-15", "2026 1. çeyrek sonuçları"),
    ("Q2 2026 (H1)",     "2026-08-01", "2026-09-15", "2026 ilk yarıyıl sonuçları"),
    ("Q3 2026",          "2026-10-15", "2026-11-30", "2026 3. çeyrek sonuçları"),
    ("Q4 2026 (Yıllık)", "2027-03-01", "2027-04-30", "2026 yıl sonu bilanço açıklamaları"),
]

def _do_earnings_refresh():
    """Bilanço takvimi yfinance verilerini arka planda yeniler — endpoint'i bloklamaz."""
    global _earnings_refreshing
    if _earnings_refreshing:
        return
    _earnings_refreshing = True
    try:
        _earnings_refresh_impl()
    except Exception as e:
        logger.warning("_do_earnings_refresh: hata — %s", e)
    finally:
        _earnings_refreshing = False


def _earnings_refresh_impl():
    """Gerçek yfinance çağrılarını yapar, cache'i günceller."""
    now = time.time()

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
        "updated_at": datetime.now(_TZ_TR).strftime("%d.%m.%Y %H:%M"),
    }
    with _lock:
        _earnings_cache["data"] = data
        _earnings_cache["ts"]   = now
    # Faz 1 #5: flat lookup rebuild (O(1) erişim için)
    _rebuild_earnings_warning_lookup()
    logger.info("_earnings_refresh_impl: tamamlandi (%d donem)", len(result_periods))


# Faz 1 #5: ticker → upcoming earnings flat lookup (O(1) erişim)
# _earnings_refresh_impl her çalıştığında güncellenir.
_earnings_warning_lookup = {}  # {ticker: {"date": "YYYY-MM-DD", "days_ahead": int}}
_earnings_warning_lock = threading.Lock()

def _rebuild_earnings_warning_lookup():
    """Faz 1 #5: _earnings_cache'ten flat ticker → upcoming earnings dict çıkar.
    Sadece 7 gün içinde KESİN tarih olanlar dahil ('yaklaşık' atlanır)."""
    try:
        cached = _earnings_cache.get("data")
        if not cached:
            return
        today = date.today()
        new_lookup = {}
        for period in cached.get("periods", []):
            for s in period.get("stocks", []):
                d = s.get("date")
                t = s.get("ticker")
                if not t or not d or d == "yaklaşık":
                    continue
                try:
                    e_date = datetime.strptime(d, "%Y-%m-%d").date()
                    delta = (e_date - today).days
                    if 0 <= delta <= 7:
                        new_lookup[t] = {"date": d, "days_ahead": delta}
                except Exception:
                    continue
        with _earnings_warning_lock:
            _earnings_warning_lookup.clear()
            _earnings_warning_lookup.update(new_lookup)
        logger.info("Earnings warning lookup rebuilt: %d ticker", len(new_lookup))
    except Exception as e:
        logger.warning("_rebuild_earnings_warning_lookup: %s", e)


def get_upcoming_earnings_for(ticker, days=7):
    """Faz 1 #5: O(1) ticker lookup. days=7 default (parameter ignored, lookup hep 7d)."""
    return _earnings_warning_lookup.get(ticker)


def get_earnings_data():
    """Bilanço takvimi verisi — cache'den döner, stale ise arka planda yeniler."""
    now = time.time()
    # GIL sayesinde dict key read thread-safe; _lock yerine direkt oku (lock contention önleme)
    cached = _earnings_cache.get("data")
    ts     = _earnings_cache.get("ts", 0)

    # Cache taze ise anında dön
    if cached and (now - ts) < _EARNINGS_TTL:
        return cached

    # Stale veya yok — arka planda yenile (CPO-558F: web worker'da yfinance thread yasak)
    if not _earnings_refreshing and os.environ.get("REFRESH_WORKER") != "web":
        threading.Thread(target=_do_earnings_refresh, daemon=True,
                         name="earnings-refresh").start()

    # Stale cache varsa onu dön; yoksa boş döndür (loading state)
    if cached:
        return cached
    return {"periods": [], "updated_at": "—"}


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

        # ── Metin kaynağı önceliği: kap_cache > haber_cache > sinyal_açıklama > algoritma ──
        with _lock:
            news_c = _news_cache.get(t)
            expl_c = _signal_explain_cache.get(t)

        text   = None
        source = "algorithmic"

        # 1. KAP cache'den doğrudan bildirim konularını snippet olarak kullan (hallucination yok)
        kap_cached = _kap_cache.get(t, {})
        kap_discs  = kap_cached.get("data", []) if kap_cached else []
        if kap_discs:
            lines = [f"{d['date'][:10]}: {d['subject']}"
                     for d in kap_discs[:3] if d.get("subject")]
            if lines:
                text   = " | ".join(lines)
                source = "kap"

        # 2. AI haber cache (Google Search grounding)
        if not text and news_c and not news_c.get("failed") and news_c.get("text"):
            text   = news_c["text"]
            source = "news"

        # 3. Sinyal açıklama cache
        if not text and expl_c and expl_c.get("text") and not expl_c.get("failed"):
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

        # Snippet: gereksiz giriş/kapanış cümlelerini temizle, ilk ~220 karakter
        _skip_prefixes = (
            "aşağıda", "işte", "here are", "here is", "below are",
            "son 7 gün", "son yedi gün", "belirtmek gerekir",
            "bugünün tarihi", "bu tarihe", "01 mayıs", "belirtilen tarih",
            "kayda değer", "son 7 günde kayda", "son yedi günde kayda",
            "not:", "note:", "önemli not",
        )
        lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
        # Başındaki giriş cümlelerini atla (maksimum 2 satır)
        for _ in range(2):
            if lines and any(lines[0].lower().startswith(p) for p in _skip_prefixes):
                lines = lines[1:]
            else:
                break
        # Madde işareti olan satırlarla başlıyorsa, sadece ilk 3 maddeyi al
        bullet_lines = [ln for ln in lines if ln.startswith(("•", "-", "*", "–", "1.", "2.", "3."))]
        if bullet_lines:
            lines = bullet_lines[:3]
        # Markdown temizle: bullet prefix, bold markers, italic markers
        _MD_STRIP_RE = re.compile(r'^\s*[\*\-•–]\s+|\*\*([^*]+)\*\*|\*([^*]+)\*')
        def _clean_md(ln):
            ln = re.sub(r'^\s*[\*\-•–]\s+', '', ln)  # bullet prefix
            ln = re.sub(r'\*\*([^*]+)\*\*', r'\1', ln)  # **bold**
            ln = re.sub(r'\*([^*]+)\*', r'\1', ln)   # *italic*
            ln = re.sub(r'^\d+\.\s+', '', ln)         # 1. numbered
            return ln.strip()
        lines = [_clean_md(ln) for ln in lines if ln.strip()]
        clean = " ".join(ln for ln in lines if ln).strip()
        snippet = clean if len(clean) <= 220 else clean[:220].rsplit(" ", 1)[0] + "…"

        # "Kayda değer gelişme yok" → boş kart yerine algoritmik sinyal bilgisi göster
        _EMPTY_PATTERNS = (
            "kayda değer bir gelişme",
            "kayda değer gelişme bulunmuyor",
            "kayda değer bir haber",
            "herhangi bir haber bulunamadı",
            "son 7 günde kayda değer",
        )
        if source == "news" and len(snippet) < 160 and \
                any(pat in snippet.lower() for pat in _EMPTY_PATTERNS):
            dur = "bugün" if bars <= 1 else f"son {bars} gündür"
            entry_q = s.get("entry_quality", "")
            sl_val  = s.get("sl_level") or 0
            tp_val  = s.get("tp1") or 0
            snippet = (
                f"{dur.capitalize()} {sig} sinyali aktif"
                f"{', ' + entry_q.lower() + ' giriş bölgesi' if entry_q else ''}. "
                f"SL: {sl_val:.2f}₺ | Hedef: {tp_val:.2f}₺"
            )
            source = "algorithmic"

        # Guard: _skip_prefixes tüm satırları silmişse (ör. "kayda değer" yanıtı) → algoritmik fallback
        if not snippet.strip():
            dur = "bugün" if bars <= 1 else f"son {bars} gündür"
            entry_q = s.get("entry_quality", "")
            sl_val  = s.get("sl_level") or 0
            tp_val  = s.get("tp1") or 0
            snippet = (
                f"{dur.capitalize()} {sig} sinyali aktif"
                f"{', ' + entry_q.lower() + ' giriş bölgesi' if entry_q else ''}. "
                f"SL: {sl_val:.2f}₺ | Hedef: {tp_val:.2f}₺"
            )
            source = "algorithmic"

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
            "kap_url":     kap_url_for(t),
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


@app.route("/api/recognize", methods=["POST"])
@limiter.limit("10 per hour")
def api_recognize():
    """MSG-098 soft auth: Eski abone re-recognize — email ile kaydı bul, bp_sub cookie set.
    Yeni kayıt OLUŞTURMAZ — sadece mevcut aboneyi tanır."""
    data  = request.get_json(silent=True) or {}
    email = (data.get("email") or "").strip().lower()
    if not email or "@" not in email or not re.match(r'^[^@]+@[^@]+\.[^@]+$', email):
        return safe_json({"ok": False, "error": "Geçersiz e-posta adresi"}), 400

    with _sub_lock:
        subs = _load_subscribers()
        rec  = subs.get(email)

    if not rec or not rec.get("active", True):
        return safe_json({"ok": False, "reason": "not_found"}), 404

    token = rec.get("token", "")
    resp  = safe_json({
        "ok":               True,
        "name":             rec.get("name", ""),
        "subscribed_at":    rec.get("subscribed_at", ""),
        "premium_unlocked": True,   # MSG-116 Bug E: üye girişi → premium 30 gün retention bonus
    })
    resp.set_cookie("bp_sub", token, max_age=31536000, samesite="Lax", secure=True, httponly=False)
    # MSG-116 Bug E: "Üye Girişi" eski aboneye Premium 30 gün açar (retention bonus).
    # recognize AÇIK aksiyon (buton + email) — pasif bypass değil, MSG-073 kuralıyla uyumlu.
    resp.set_cookie("bp_premium_trial", "1", max_age=30 * 86400, samesite="Lax", secure=True, httponly=False)
    return resp


@app.route("/api/subscribe", methods=["POST"])
@limiter.limit("5 per hour")
def api_subscribe():
    """E-posta abonelik kaydı (name + email)."""
    data  = request.get_json(silent=True) or {}
    email = (data.get("email") or "").strip().lower()
    name  = (data.get("name") or "").strip()[:80]  # max 80 chars

    # Basit e-posta doğrulama
    if not email or "@" not in email or not re.match(r'^[^@]+@[^@]+\.[^@]+$', email):
        return safe_json({"ok": False, "error": "Geçersiz e-posta adresi"}), 400
    # İsim isteğe bağlı; varsa minimum 2 karakter
    if name and len(name) < 2:
        return safe_json({"ok": False, "error": "Ad çok kısa"}), 400

    with _sub_lock:
        subs = _load_subscribers()
        if email in subs:
            if subs[email].get("active", True):
                return safe_json({"ok": False, "message": "Bu e-posta zaten kayıtlı."})
            # Pasif abonenin kaydını yeniden aktif et
            subs[email]["active"] = True
            subs[email]["subscribed_at"] = datetime.now().isoformat()
            if name and not subs[email].get("name"):
                subs[email]["name"] = name
            _save_subscribers(subs)
            token = subs[email].get("token", "")
            unsub = f"https://borsapusula.com/unsubscribe/{token}"
            threading.Thread(target=send_email, args=(
                email, "✅ BorsaPusula — Abonelik Yenilendi",
                _build_welcome_email(email, unsub, name=subs[email].get("name"), profile_token=subs[email].get("token", ""))
            ), daemon=True).start()
            react_resp = safe_json({"ok": True, "message": "Aboneliğiniz yeniden aktif edildi!", "token": token, "name": subs[email].get("name", ""), "email": email})
            react_resp.set_cookie("bp_sub", token, max_age=31536000, samesite="Lax", secure=True, httponly=False)
            return react_resp

        token = secrets.token_hex(24)
        subs[email] = {
            "token":         token,
            "subscribed_at": datetime.now().isoformat(),
            "name":          name,            # FAZ 3: kullanıcı adı
            "tickers":       [],
            "active":        True,
            "level":         None,            # FAZ 4: yatırım deneyimi
            "freq":          None,            # FAZ 4: işlem sıklığı
            "segments":      [],              # FAZ 4: ilgi alanları
            "mail_pref":     "daily",         # FAZ 4: mail tercihi (daily|instant|premium|weekly)
            "profile_done":  False,           # FAZ 4: profil tamamlandı mı
        }
        _save_subscribers(subs)

    unsub = f"https://borsapusula.com/unsubscribe/{token}"
    threading.Thread(target=send_email, args=(
        email, "✅ BorsaPusula — Abonelik Onayı",
        _build_welcome_email(email, unsub, name=subs[email].get("name"), profile_token=subs[email].get("token", ""))
    ), daemon=True).start()

    logger.info("Yeni e-posta abonesi: %s", email)
    resp = safe_json({
        "ok":      True,
        "message": "Abonelik başarılı! Onay e-postası gönderildi.",
        "token":   token,
        "name":    name,
        "email":   email,
    })
    # Cookie set — 1 yıl, SameSite=Lax (CSRF korumalı)
    resp.set_cookie("bp_sub", token, max_age=31536000, samesite="Lax", secure=True, httponly=False)
    return resp


@app.route("/profil")
def profil_page():
    """Profil tamamla sayfası — token ile kullanıcıyı tanı."""
    token = request.args.get("t", "")
    if not token:
        return Response("Geçersiz bağlantı", status=400)
    with _sub_lock:
        subs = _load_subscribers()
        target_email = None
        for em, info in subs.items():
            if info.get("token") == token and info.get("active"):
                target_email = em
                break
    if not target_email:
        return render_template("profil.html", error="Aboneliğiniz bulunamadı veya pasif", email=None, name="", profile=None, token="")

    info = subs[target_email]
    profile = {
        "level":     info.get("level"),
        "freq":      info.get("freq"),
        "size":      info.get("size"),
        "segments":  info.get("segments", []),
        "mail_pref": info.get("mail_pref", "daily"),
    }
    return render_template("profil.html",
                           email=target_email,
                           name=info.get("name", ""),
                           profile=profile,
                           token=token,
                           done=info.get("profile_done", False))


@app.route("/api/profile", methods=["POST"])
@limiter.limit("10 per hour")
def api_profile():
    """Profil verilerini kaydet."""
    data = request.get_json(silent=True) or {}
    token = (data.get("token") or "").strip()
    if not token:
        return safe_json({"ok": False, "error": "Token eksik"}), 400

    level     = (data.get("level") or "").strip()[:20]
    freq      = (data.get("freq") or "").strip()[:20]
    size      = (data.get("size") or "").strip()[:30]
    segments  = data.get("segments") or []
    if not isinstance(segments, list): segments = []
    segments = [str(s).strip()[:30] for s in segments][:10]
    mail_pref = (data.get("mail_pref") or "daily").strip()[:20]
    if mail_pref not in ("daily", "instant", "premium", "weekly"):
        mail_pref = "daily"

    with _sub_lock:
        subs = _load_subscribers()
        target = None
        for em, info in subs.items():
            if info.get("token") == token and info.get("active"):
                target = em; break
        if not target:
            return safe_json({"ok": False, "error": "Geçersiz token"}), 404

        subs[target]["level"]        = level
        subs[target]["freq"]         = freq
        subs[target]["size"]         = size
        subs[target]["segments"]     = segments
        subs[target]["mail_pref"]    = mail_pref
        subs[target]["profile_done"] = True
        subs[target]["profile_updated_at"] = datetime.now().isoformat()
        _save_subscribers(subs)

    logger.info("Profil tamamlandı: %s (level=%s, freq=%s, mail=%s)", target, level, freq, mail_pref)
    return safe_json({"ok": True, "message": "Profil kaydedildi! Sinyaller artık size özel."})


@app.route("/api/me")
def api_me():
    """Kullanıcı tanıma — token ile abonelik durumu sorgular."""
    token = request.args.get("t") or request.cookies.get("bp_sub")
    if not token:
        return safe_json({"ok": False, "subscribed": False})
    with _sub_lock:
        subs = _load_subscribers()
        for em, info in subs.items():
            if info.get("token") == token and info.get("active"):
                return safe_json({
                    "ok":            True,
                    "subscribed":    True,
                    "email":         em,
                    "name":          info.get("name", ""),
                    "first_name":    (info.get("name", "").split()[0] if info.get("name") else ""),
                    "profile_done":  bool(info.get("profile_done")),
                    "mail_pref":     info.get("mail_pref", "daily"),
                })
    return safe_json({"ok": False, "subscribed": False})


# In-memory rate limit + dedup for client error reports
_client_errors_recent = {}   # key: (msg_hash, page), val: timestamp
_CLIENT_ERROR_DEDUP_WINDOW = 60.0   # aynı hatayı 60s'de bir logla
_CLIENT_ERROR_RATE_LIMIT  = 50      # tüm IP'ler toplam 50 error/dk üst sınır
_client_error_count_this_min = {"count": 0, "minute": 0}


@app.route("/api/log-error", methods=["POST"])
@limiter.limit("30 per minute")
def api_log_error():
    """Client-side JS hatalarını logger'a yazar. Stealth bug detection."""
    data = request.get_json(silent=True) or {}
    msg  = (data.get("msg") or "").strip()[:500]
    src  = (data.get("src") or "").strip()[:200]
    line = data.get("line")
    col  = data.get("col")
    page = (data.get("page") or "").strip()[:120]
    stack = (data.get("stack") or "").strip()[:1000]
    ua   = (request.headers.get("User-Agent") or "")[:200]

    if not msg:
        return safe_json({"ok": False}), 400

    # Dedup
    key = (hash(msg) % 1_000_000, page)
    now_ts = time.time()
    if key in _client_errors_recent and (now_ts - _client_errors_recent[key]) < _CLIENT_ERROR_DEDUP_WINDOW:
        return safe_json({"ok": True, "deduped": True})
    _client_errors_recent[key] = now_ts

    # Rate guard (toplam)
    cur_min = int(now_ts // 60)
    if _client_error_count_this_min["minute"] != cur_min:
        _client_error_count_this_min["minute"] = cur_min
        _client_error_count_this_min["count"]  = 0
    _client_error_count_this_min["count"] += 1
    if _client_error_count_this_min["count"] > _CLIENT_ERROR_RATE_LIMIT:
        return safe_json({"ok": True, "throttled": True})

    logger.warning(
        "🐛 CLIENT-JS-ERROR | page=%s | msg=%s | %s:%s:%s | UA=%s | stack=%s",
        page, msg, src, line, col, ua[:80], stack[:200]
    )
    return safe_json({"ok": True})


# ── Web Push API ─────────────────────────────────────────────────────────────

@app.route("/api/push/vapid-public-key")
def api_push_vapid_key():
    """Frontend'in subscription için ihtiyaç duyduğu VAPID public key."""
    return safe_json({"publicKey": VAPID_PUBLIC})


@app.route("/api/push/subscribe", methods=["POST"])
@limiter.limit("20 per hour")
def api_push_subscribe():
    """Browser push subscription'ı kaydet."""
    sub = request.get_json(silent=True)
    if not sub or "endpoint" not in sub:
        return safe_json({"error": "Geçersiz subscription"}), 400

    with _push_lock:
        # SPEC-006 Faz 2: existing varsa REPLACE — watchlist değişimi yansısın
        existing_idx = next(
            (i for i, s in enumerate(_push_subs) if s.get("endpoint") == sub["endpoint"]),
            None,
        )
        if existing_idx is not None:
            _push_subs[existing_idx] = sub
        else:
            _push_subs.append(sub)
        _save_push_subs_locked()
        count = len(_push_subs)

    logger.info("Push sub kaydedildi/güncellendi (toplam %d)", count)
    return safe_json({"ok": True, "subscribed": existing_idx is None, "count": count})


@app.route("/api/push/unsubscribe", methods=["POST"])
@limiter.limit("20 per hour")
def api_push_unsubscribe():
    """Push subscription'ı iptal et."""
    data     = request.get_json(silent=True) or {}
    endpoint = data.get("endpoint", "")
    with _push_lock:
        before = len(_push_subs)
        _push_subs[:] = [s for s in _push_subs if s.get("endpoint") != endpoint]
        removed = before - len(_push_subs)
        if removed:
            _save_push_subs_locked()
    return safe_json({"ok": True, "removed": removed})


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
    require_admin()
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHANNEL_ID:
        return safe_json({"ok": False, "error": "Telegram env vars eksik (TELEGRAM_BOT_TOKEN, TELEGRAM_CHANNEL_ID)"})
    _send_telegram(
        "🔔 <b>BorsaPusula Test Mesajı</b>\n"
        "Telegram entegrasyonu başarıyla yapılandırıldı!\n"
        f"<i>Sunucu: {datetime.now(_TZ_TR).strftime('%d.%m.%Y %H:%M:%S')}</i>"
    )
    return safe_json({"ok": True, "channel": TELEGRAM_CHANNEL_ID})


# ── Blog önbelleği: startup'ta bir kez normalize et, her request'te yeniden hesaplama yok ──
_BLOG_NORMALIZED_CACHE: list | None = None
_BLOG_CAT_COUNTS_CACHE: list | None = None

def _get_blog_cache():
    global _BLOG_NORMALIZED_CACHE, _BLOG_CAT_COUNTS_CACHE
    if _BLOG_NORMALIZED_CACHE is None:
        from collections import Counter
        _counts = Counter(a["cat"] for a in ARTICLES)
        _BLOG_CAT_COUNTS_CACHE = sorted(_counts.items())
        _BLOG_NORMALIZED_CACHE = [_normalize_article(a) for a in ARTICLES]
        logger.info("Blog önbelleği hazırlandı: %d makale", len(_BLOG_NORMALIZED_CACHE))
    return _BLOG_NORMALIZED_CACHE, _BLOG_CAT_COUNTS_CACHE

@app.route("/blog")
def blog_index():
    normalized, cat_counts = _get_blog_cache()
    return render_template("blog.html", articles=normalized, cat_counts=cat_counts)


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

def _normalize_article(a):
    """Eski ve yeni makale formatını ortak template formatına normalize et."""
    import copy
    art = copy.copy(a)
    # desc: 'desc' yoksa 'summary' kullan
    if not art.get("desc") and art.get("summary"):
        art["desc"] = art["summary"]
    # mins: 'mins' yoksa 'read_min' kullan
    if not art.get("mins") and art.get("read_min"):
        art["mins"] = art["read_min"]
    # date: yoksa varsayılan
    if not art.get("date"):
        art["date"] = "2026-05-01"
    # body: markdown ise HTML'e çevir
    body = art.get("body", "")
    if body and not body.strip().startswith("<"):
        try:
            import markdown as md_lib
            # markdown tabloları ve kod blokları için extras
            art["body"] = md_lib.markdown(
                body,
                extensions=["tables", "fenced_code"],
                output_format="html"
            )
        except Exception:
            # Fallback: basit satır kırma dönüşümü
            art["body"] = "<p>" + "</p><p>".join(p for p in body.split("\n\n") if p.strip()) + "</p>"
    return art


@app.route("/blog/<slug>")
def blog_article(slug):
    from flask import abort, redirect, url_for
    # Bilinen eski slug → doğru slug 301 yönlendirme
    if slug in _BLOG_SLUG_REDIRECTS:
        return redirect(url_for("blog_article", slug=_BLOG_SLUG_REDIRECTS[slug]), code=301)
    raw_article = ARTICLES_BY_SLUG.get(slug)
    if not raw_article:
        abort(404)
    article = _normalize_article(raw_article)
    # İlgili makaleler: aynı kategori, max 3
    related = [_normalize_article(a) for a in ARTICLES if a["cat"] == article["cat"] and a["slug"] != slug][:3]
    if len(related) < 3:
        extras = [_normalize_article(a) for a in ARTICLES if a["cat"] != article["cat"] and a["slug"] != slug]
        related += extras[:3 - len(related)]
    return render_template("blog_article.html", article=article, related=related)


# ── Startup ───────────────────────────────────────────────────────────────────
def _startup():
    # Disk cache'i yükle — anlık veri gelene kadar siteyi hemen dolduran eski veri
    _load_cache_from_disk()
    # SPEC-011 L4 — şirket özeti cache'i diskten yükle (restart sonrası anında dolu)
    try:
        _load_company_summary_from_disk()
    except Exception as e:
        logger.warning("Şirket özeti disk yükleme hatası: %s", e)
    # Backtest disk cache'i yükle — restart sonrası hemen sinyal-performans sayfasına veri verir
    try:
        if os.path.exists(_BT_DISK_PATH):
            with open(_BT_DISK_PATH, encoding="utf-8") as f:
                bt_data = json.load(f)
            if bt_data and bt_data.get("al"):
                _bt_cache["data"]        = bt_data
                _bt_cache["computed_at"] = bt_data.get("computed_at", "")
                logger.info("Backtest disk cache yüklendi: AL=%s, computed=%s",
                            bt_data["al"].get("count"), bt_data.get("computed_at"))
    except Exception as e:
        logger.warning("Backtest disk cache yükleme hatası: %s", e)
    # Push subscribers'ı yükle
    _load_push_subs()
    refresh_chart()
    # XU100 + makro varliklari sirali sekilde yukle
    # Paralel yfinance calisi veri bozulmasina neden olur — sirali calis zorunlu
    def _serial_chart_refresh():
        time.sleep(1)
        refresh_xu100_chart()
        time.sleep(1)
        varlik_list = [
            ("BTC",      _btc_chart_cache),
            ("ALTIN",    _altin_chart_cache),
            ("GUMUS",    _gumus_chart_cache),
            ("ETH",      _eth_chart_cache),
            ("SP500",    _sp500_chart_cache),
            ("NASDAQ",   _nasdaq_chart_cache),
            ("SOL",      _sol_chart_cache),
            ("BNB",      _bnb_chart_cache),
            ("PETROL",   _petrol_chart_cache),
            ("DOGALGAZ", _dogalgaz_chart_cache),
        ]
        for key, cache in varlik_list:
            try:
                _refresh_varlik_chart(key, cache)
                time.sleep(0.5)
            except Exception as exc:
                logger.warning("serial_chart_refresh %s: %s", key, exc)
    _serial_done = threading.Event()

    _orig_serial = _serial_chart_refresh
    def _serial_chart_refresh_with_event():
        # CPO-558D: web worker'da yfinance chart download yasak — serial_done hemen set et
        if os.environ.get("REFRESH_WORKER") == "web":
            logger.info("_serial_chart_refresh_with_event: REFRESH_WORKER=web — atlandı, serial_done set")
            _serial_done.set()
            return
        _orig_serial()
        _serial_done.set()
        logger.info("serial_chart_refresh tamamlandi, background_refresh baslayabilir")

    def _background_refresh_after_serial():
        # Baslatma suresince paralel yfinance cagrisi olmasin: serial bitince basla
        _serial_done.wait(timeout=120)
        # CPO-558B: web worker'da yfinance prewarm yasak
        if os.environ.get("REFRESH_WORKER") != "web":
            # En çok ziyaret edilen BIST30 hisselerinin chart cache'ini ısıt
            _warm_tickers = ["THYAO", "AKBNK", "GARAN", "ASELS", "EREGL"]
            for _t in _warm_tickers:
                try:
                    _compute_chart_data(_t, "2y")
                    time.sleep(0.5)
                except Exception as _e:
                    logger.warning("prewarm chart [%s]: %s", _t, _e)
            # Temel analiz verilerini ısıt (yfinance - hisse başına ~1s)
            for _t in _warm_tickers[:3]:
                try:
                    _get_fundamentals(_t)
                    time.sleep(0.3)
                except Exception as _e:
                    logger.warning("prewarm fundamentals [%s]: %s", _t, _e)
        # CPO-572: REFRESH_WORKER=1 → refresh_worker.py zaten background_refresh() çağırıyor.
        # Burada da çağırmak iki eş-zamanlı refresh_data() döngüsü yaratır → double cache write
        # → web worker reload flood → cascade (root cause: 2026-06-12 07:55:41 + 07:56:04 çift yazı).
        if os.environ.get("REFRESH_WORKER") == "1":
            logger.info("_background_refresh_after_serial: REFRESH_WORKER=1 — background_refresh() atlandı (refresh_worker.py başlatıyor)")
            return
        background_refresh()

    threading.Thread(target=_serial_chart_refresh_with_event, daemon=True).start()
    threading.Thread(target=_background_refresh_after_serial,  daemon=True).start()
    threading.Thread(target=background_live_prices,    daemon=True).start()
    threading.Thread(target=background_global_prices,  daemon=True).start()
    # Makro ticker'ları servis başlar başlamaz ilk kez çek (arka planda)
    def _warm_macro():
        # CPO-558B: web worker'da yfinance yasak — disk-reload yeterli
        if os.environ.get("REFRESH_WORKER") == "web":
            logger.info("_warm_macro: REFRESH_WORKER=web — disk-reload only, yfinance atlandı")
            _load_macro_from_disk()
            return
        items = _fetch_macro()
        with _lock:
            _macro_cache["data"] = items
            _macro_cache["ts"]   = time.time()
        logger.info("_warm_macro: %d sembol hazır", len(items))
    threading.Thread(target=_warm_macro, daemon=True).start()
    # Makro AI özetini başlangıçta ısıt (arka planda — _warm_macro bittikten sonra)
    def _warm_macro_summary():
        # CPO-558E: web worker'da Gemini/yfinance yasak
        if os.environ.get("REFRESH_WORKER") == "web":
            logger.info("_warm_macro_summary: REFRESH_WORKER=web — atlandı")
            return
        time.sleep(10)   # macro fiyatlarının gelmesini bekle
        _do_macro_ai_refresh()
    threading.Thread(target=_warm_macro_summary, daemon=True).start()
    # Bilanço takvimini arka planda yükle (yfinance çağrıları — ana veri hazır olunca)
    def _warm_earnings():
        # CPO-558B: web worker'da yfinance yasak — refresh service günceller, disk-reload yeter
        if os.environ.get("REFRESH_WORKER") == "web":
            logger.info("_warm_earnings: REFRESH_WORKER=web — yfinance atlandı")
            return
        time.sleep(30)   # ana sinyal datasının gelmesini bekle
        _do_earnings_refresh()
    threading.Thread(target=_warm_earnings, daemon=True).start()
    # Backtest'i arka planda başlat (30 dakika gecikme ile — önce ana veri yüklensin)
    def _delayed_backtest():
        # CPO-558H: web worker'da backtest (28 × yfinance.download) yasak
        if os.environ.get("REFRESH_WORKER") == "web":
            logger.info("_delayed_backtest: REFRESH_WORKER=web — atlandı")
            return
        time.sleep(1800)   # 30 dakika sonra
        run_backtest()
    threading.Thread(target=_delayed_backtest, daemon=True).start()
    # Bilanco takvimi ilk yuklemesini arkaplanda hazirla (yfinance cagrilari yuzunden yavastir)
    def _warm_earnings_2():
        # CPO-558B: web worker'da yfinance yasak
        if os.environ.get("REFRESH_WORKER") == "web":
            logger.info("_warm_earnings_2: REFRESH_WORKER=web — yfinance atlandı")
            return
        time.sleep(60)    # Ana veri yüklendikten 60s sonra başla
        try:
            get_earnings_data()
            logger.info("_warm_earnings: bilanço takvimi ön yüklendi")
        except Exception as e:
            logger.warning("_warm_earnings: %s", e)
    threading.Thread(target=_warm_earnings_2, daemon=True).start()

    def _slow_chart_refresh_daemon():
        # CPO-565 Bug 1: Per-ticker chart dosyalarını diske yazar.
        # REFRESH_WORKER=1 (leader) ortamında çalışır; web worker'da atlanır.
        if os.environ.get("REFRESH_WORKER") == "web":
            logger.info("_slow_chart_refresh: REFRESH_WORKER=web — atlandı")
            return
        time.sleep(300)  # Startup'ta 5dk bekle (refresh_data bitmesini bekle)
        while True:
            try:
                with _lock:
                    tickers = [s.get("ticker") for s in _cache.get("data", []) if s.get("ticker")]
                if not tickers:
                    logger.warning("_slow_chart_refresh: _cache boş, 60s bekle")
                    time.sleep(60)
                    continue
                logger.info("_slow_chart_refresh başladı: %d ticker", len(tickers))
                done = 0
                for ticker in tickers:
                    try:
                        data = _compute_chart_data(ticker, "2y")
                        if data:
                            path = os.path.join(_PHASE3_CHART_DIR, f"chart_{ticker}.json")
                            _atomic_write_json(path, data)
                            done += 1
                    except Exception as e:
                        logger.warning("_slow_chart_refresh [%s]: %s", ticker, e)
                    time.sleep(3)
                logger.info("_slow_chart_refresh tamamlandı: %d/%d ticker diske yazıldı", done, len(tickers))
            except Exception as e:
                logger.error("_slow_chart_refresh outer: %s", e)
            time.sleep(6 * 3600)  # 6 saatte bir tam cycle

    threading.Thread(target=_slow_chart_refresh_daemon, daemon=True).start()

# CPO-576: systemd watchdog heartbeat — pure Python, python-systemd gerekmez.
# NotifyAccess=all + WatchdogSec>0 → systemd NOTIFY_SOCKET'i sağlar.
# READY=1 (startup), ardından her 30s WATCHDOG=1 → WatchdogSec=120 ile 4x margin.
def _sd_notify(msg):
    sock_path = os.environ.get("NOTIFY_SOCKET", "")
    if not sock_path:
        return False
    if sock_path.startswith("@"):
        sock_path = "\0" + sock_path[1:]
    try:
        s = _socket.socket(_socket.AF_UNIX, _socket.SOCK_DGRAM)
        s.sendto(msg.encode(), sock_path)
        s.close()
        return True
    except Exception:
        return False

def _systemd_watchdog_thread():
    _sd_notify("READY=1")
    while True:
        time.sleep(30)
        _sd_notify("WATCHDOG=1")

if os.environ.get("NOTIFY_SOCKET"):
    _wd_thread = threading.Thread(target=_systemd_watchdog_thread, daemon=True, name="systemd-watchdog")
    _wd_thread.start()
    logger.info("CPO-576: systemd watchdog heartbeat başlatıldı (30s ping, WatchdogSec=120)")

threading.Thread(target=_startup, daemon=True).start()

# CPO-585: MTF warmup daemon — REFRESH_WORKER=1 only, web worker hang önlenir
# /api/hisse/<ticker>/mtf cache miss → web worker artık blocking call yapmaz (guard var)
# Bu daemon 30dk'lık MTF cache'ini proaktif doldurur, cold window kalmaz.
def _mtf_warmup_daemon():
    time.sleep(90)  # ilk cycle'dan sonra başla — startup I/O ile çakışma önlenir
    while True:
        now = time.time()
        for _t in BIST30:
            with _lock:
                _mc = _mtf_cache.get(_t)
            if not _mc or (now - _mc["ts"]) > 1500:  # 25dk → 30dk TTL'den önce tazele
                try:
                    _compute_mtf(_t)
                    time.sleep(3)  # yfinance throttle
                except Exception:
                    pass
        time.sleep(1800)

if os.environ.get("REFRESH_WORKER") == "1":
    threading.Thread(target=_mtf_warmup_daemon, daemon=True, name="mtf-warmup").start()
    logger.info("CPO-585: MTF warmup daemon başlatıldı (REFRESH_WORKER=1, 30dk interval)")

logger.info("=" * 50)
logger.info("  BIST30 Sinyal Paneli başlatıldı")
logger.info("  http://localhost:8003")
logger.info("=" * 50)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8003, debug=False)
