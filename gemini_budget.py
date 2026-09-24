"""D-P0-2409 — Gemini harcama tavanı (günlük çağrı + aylık USD).

Ozan 24.09: "çok tasarruflu, büyük harcama olmasın". Faturalandırma açıkken kodda
hız sınırından başka fren yoktu. Sayaç dosyası tüm worker'lar ve refresh servisi
arasında paylaşımlıdır (repo dizininde, /tmp değil — reboot'ta aylık toplam
kaybolmasın); yazım atomiktir (tmp + os.replace). Gerçek çağrılar zaten
`_gemini_rate_acquire` ile ≥6,5 sn aralıklı serileştiği için eşzamanlı yazım
pratikte yok; süreç içi threading.Lock yine de araya girmeyi keser.

Bütçe dolunca `reserve()` (False, sebep) döner ve çağıran HTTP isteği atmaz.
"""
import json
import os
import threading
import time
from datetime import datetime, timedelta, timezone

_TZ_TR = timezone(timedelta(hours=3))

# Fiyat tablosu ($ / 1M token): (giriş, çıkış). Bilinmeyen model → en pahalı satır.
PRICES = {
    "gemini-2.5-flash-lite": (0.10, 0.40),
    "gemini-2.5-flash": (0.30, 2.50),
}
_FALLBACK_PRICE = (0.30, 2.50)


def _env_num(name, default, cast):
    try:
        return cast(os.environ.get(name, default))
    except (TypeError, ValueError):
        return cast(default)


ENABLED = os.environ.get("GEMINI_ENABLED", "1").strip() != "0"
DAILY_CALLS = _env_num("GEMINI_DAILY_CALLS", "200", int)
MONTHLY_USD = _env_num("GEMINI_MONTHLY_USD", "5", float)
# Google Search grounding tavana dahil edilmiyor (1.500/gün sonrası $35/1.000) → varsayılan kapalı.
GROUNDING = os.environ.get("GEMINI_GROUNDING", "0").strip() == "1"
USAGE_PATH = os.environ.get(
    "GEMINI_USAGE_PATH",
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "gemini_usage.json"),
)

_lock = threading.Lock()


def _now_tr(now=None):
    return datetime.fromtimestamp(now if now is not None else time.time(), _TZ_TR)


def _blank(day, month):
    return {"day": day, "month": month, "calls_today": 0, "usd_today": 0.0,
            "usd_month": 0.0, "calls_month": 0, "month_capped_alerted": False}


def _load(path=None, now=None):
    """Sayaç dosyasını okur; gün/ay değişmişse ilgili sayaçları sıfırlar (yazmaz)."""
    path = path or USAGE_PATH
    t = _now_tr(now)
    day, month = t.strftime("%Y-%m-%d"), t.strftime("%Y-%m")
    try:
        with open(path, encoding="utf-8") as f:
            d = json.load(f)
        if not isinstance(d, dict):
            raise ValueError("dict değil")
    except (OSError, ValueError):
        return _blank(day, month)
    base = _blank(day, month)
    base.update({k: d[k] for k in base if k in d})
    if base["month"] != month:
        return _blank(day, month)
    if base["day"] != day:
        base["day"], base["calls_today"], base["usd_today"] = day, 0, 0.0
    return base


def _save(d, path=None):
    path = path or USAGE_PATH
    tmp = f"{path}.tmp.{os.getpid()}.{threading.get_ident()}"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(d, f)
    os.replace(tmp, path)


def cost_usd(model, prompt_tokens, output_tokens):
    pin, pout = PRICES.get(model, _FALLBACK_PRICE)
    return (max(0, prompt_tokens) * pin + max(0, output_tokens) * pout) / 1_000_000


def status(path=None, now=None):
    """/api/health ve günlük log için salt-okunur özet."""
    d = _load(path, now)
    return {
        "enabled": ENABLED,
        "calls_today": d["calls_today"], "daily_cap": DAILY_CALLS,
        "usd_month": round(d["usd_month"], 4), "monthly_cap_usd": MONTHLY_USD,
    }


def reserve(path=None, now=None):
    """Çağrıdan ÖNCE. (True, None) → devam; (False, sebep) → HTTP isteği atma.
    İzin verilirse çağrı sayacı hemen artar (başarısız çağrı da sayılır).
    Aylık tavan ilk kez dolduğunda sebep 'monthly_cap_new' döner (tek uyarı için)."""
    if not ENABLED:
        return False, "disabled"
    with _lock:
        try:
            d = _load(path, now)
            if d["usd_month"] >= MONTHLY_USD:
                if not d["month_capped_alerted"]:
                    d["month_capped_alerted"] = True
                    _save(d, path)
                    return False, "monthly_cap_new"
                return False, "monthly_cap"
            if d["calls_today"] >= DAILY_CALLS:
                return False, "daily_cap"
            d["calls_today"] += 1
            d["calls_month"] += 1
            _save(d, path)
            return True, None
        except OSError:
            # Sayaç yazılamıyorsa fail-CLOSED: maliyeti ölçemediğimiz çağrı atılmaz.
            return False, "usage_file_error"


def record(model, prompt_tokens, output_tokens, path=None, now=None):
    """Yanıttan sonra: usageMetadata token sayısıyla harcamayı ekler."""
    c = cost_usd(model, prompt_tokens, output_tokens)
    with _lock:
        try:
            d = _load(path, now)
            d["usd_today"] += c
            d["usd_month"] += c
            _save(d, path)
        except OSError:
            pass
    return c


def summary_line(path=None, now=None):
    s = status(path, now)
    return (f"gemini gün: {s['calls_today']} çağrı, "
            f"${_load(path, now)['usd_today']:.4f}; ay: ${s['usd_month']:.4f} / ${s['monthly_cap_usd']:g}")
