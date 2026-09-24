"""D-39 (Ozan O10, kanon §2.2) — teknik hedef alanları ve metinleri üretilmez.

API'lerden kalkan alanlar: tp1, tp2, tp_level, rr_signal, rr_ratio, rr_now,
entry_note ("SL yakın — R/R"), optimal_entry. Supertrend "LONG/SHORT" değeri
"Yukarı/Aşağı" olur. Sinyal/digest e-postası, market-news yedek metni, AI
açıklama istemi ve Sinyal Özeti "SL / Hedef / giriş bölgesi / stop-loss"
dilini üretmez. Analist hedef fiyatı (temel analiz) KALIR.

Python 3.9 app.py'yi import edemez: kaynak AST ile taranır, küçük fonksiyonlar
izole exec edilir. Son test yalnız VPS'te (py3.12) app'i import eder.
"""
import ast
import os
import re
import sys
from datetime import datetime
from zoneinfo import ZoneInfo

import pytest

import business_rules as br

_APP_PY = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "app.py")
with open(_APP_PY, encoding="utf-8") as _f:
    _SRC = _f.read()
_TREE = ast.parse(_SRC)


def _func_src(name):
    for node in ast.walk(_TREE):
        if isinstance(node, ast.FunctionDef) and node.name == name:
            lines = _SRC.splitlines()
            return "\n".join(lines[node.lineno - 1:node.end_lineno]) + "\n"
    raise AssertionError(f"{name} bulunamadı")


def _strings(name):
    """Fonksiyondaki string sabitleri (yorumlar hariç — render edilmezler)."""
    return [n.value for n in ast.walk(ast.parse(_func_src(name)))
            if isinstance(n, ast.Constant) and isinstance(n.value, str)]


# ── Kanonik liste + dil deseni (business_rules) ─────────────────────────────

def test_retired_keys_cover_plan_fields():
    for k in ("tp1", "tp2", "tp_level", "rr_signal", "rr_ratio", "entry_note", "optimal_entry"):
        assert k in br.RETIRED_TRADE_KEYS
    assert "sl_level" not in br.RETIRED_TRADE_KEYS        # Supertrend seviyesi (trend dönüş) kalır
    assert "entry_quality" not in br.RETIRED_TRADE_KEYS   # kod değeri; tarama/karsilastir/gundem/hisse tüketiyor


@pytest.mark.parametrize("text", [
    "Sinyal taze (2 bar), fiyat SL'ye yakın — R/R en avantajlı bölge",
    "Stop-Loss seviyesi: 30,12 ₺", "stop loss", "Stop bölgesi", "KÂR AL", "kar al",
    "ideal giriş bölgesi", "Giriş Fiyatı", "giriş kalitesi", "ST: LONG", "SHORT",
    "TP1: 12,50", "hedefe ulaştı", "zarar durdurma seviyesi", "Kazanma oranı %50",
    "Hedef seviye 40 ₺",
])
def test_trade_lang_regex_catches_variants(text):
    assert br.TRADE_LANG_RE.search(text)


@pytest.mark.parametrize("text", [
    "Trend dönüş seviyesi (Supertrend): 30,12 ₺ · fiyatın %4,2 altında",
    "Analist hedef ortalaması 12 ₺ · fiyatın %5 üstünde · 8 analist",
    "Güçlü Trend sinyali aktif.", "Hedef kitlen bireysel yatırımcılardır",
    "https://www.aa.com.tr/tr/rss/default?cat=ekonomi",
])
def test_trade_lang_regex_leaves_allowed_text(text):
    assert not br.TRADE_LANG_RE.search(text)


# ── app.py: alanlar üretilmiyor ──────────────────────────────────────────────

def test_app_py_never_names_a_retired_field():
    # analyze() dönüşü, /api/karsilastir satırı, market-news tp_val okuması —
    # hiçbir yerde emekli alan adı string olarak geçmiyor (liste business_rules'ta).
    hits = sorted({(n.lineno, n.value) for n in ast.walk(_TREE)
                   if isinstance(n, ast.Constant) and n.value in br.RETIRED_TRADE_KEYS})
    assert hits == []
    analyze_keys = {k.value for n in ast.walk(ast.parse(_func_src("analyze")))
                    if isinstance(n, ast.Dict) for k in n.keys if isinstance(k, ast.Constant)}
    assert {"entry_quality", "sl_level", "signal_date", "bar_date"} <= analyze_keys
    assert not {"LONG", "SHORT"} & set(_strings("analyze"))


def test_enrich_stock_drops_legacy_disk_cache_fields():
    ns = {"_get_sector": lambda t: "Ulaştırma", "STOCK_NAMES": {"THYAO": "Türk Hava Yolları"},
          "_RETIRED_TRADE_KEYS": br.RETIRED_TRADE_KEYS}
    exec(_func_src("_enrich_stock"), ns)
    old = {"ticker": "THYAO", "tp1": 320.0, "tp2": 330.0, "rr_signal": 2.1, "entry_note": "SL yakın — R/R",
           "optimal_entry": 290.0, "sl_level": 280.0, "entry_quality": "IDEAL",
           "indicators": {"supertrend": {"value": "SHORT", "bull": False, "bear": True}}}
    s = ns["_enrich_stock"](old)
    assert not set(br.RETIRED_TRADE_KEYS) & set(s)
    assert s["sl_level"] == 280.0 and s["entry_quality"] == "IDEAL"
    assert s["indicators"]["supertrend"]["value"] == "Aşağı"
    s2 = ns["_enrich_stock"]({"ticker": "X", "indicators": {"supertrend": None}})
    assert s2["indicators"]["supertrend"] is None


def test_signal_email_uses_trend_donus_seviyesi():
    ns = {"_SIGNAL_LABELS": br.SIGNAL_LABELS, "STOCK_NAMES": {"SAHOL": "Sabancı Holding"},
          "tr_price_filter": lambda v: f"{v:.2f}".replace(".", ","), "datetime": datetime,
          "_TZ_TR": ZoneInfo("Europe/Istanbul"), "_tr_month": lambda d: "Eylül",
          "_email_base": lambda content, unsub, preheader="": preheader + content}
    exec(_func_src("_build_signal_email"), ns)
    stock = {"price": 91.1, "sl_level": 95.4, "adx": 31.0, "rvol": 1.3, "is_premium": False}
    html = ns["_build_signal_email"]([("SAHOL", "BEKLE", "SAT", stock)], "https://x/unsub")
    text = re.sub(r"<[^>]+>", " ", html)
    assert "Trend dönüş seviyesi (Supertrend):" in text and "95,40 ₺" in text
    assert not br.TRADE_LANG_RE.search(text)


# ── Üretilen metin taraması ──────────────────────────────────────────────────

_ALLOWED = {
    "sl",               # iç sözlük anahtarı (Supertrend seviyesi), metin değil
    "--short",          # git rev-parse argümanı
    "LONG", "SHORT",    # _enrich_stock: eski disk cache değerini Yukarı/Aşağı'ya çevirir
    "stop-loss-nedir",  # Borsa Okulu blog yazısı adresi (blog kalır)
}


def _is_prompt(text):
    # Gemini istemleri: işlem dili yalnız YASAK listesi olarak geçer, üretilmez.
    return text.startswith("KIMLIK:") or "KURAL" in text


def test_app_generated_strings_have_no_trade_language():
    skip = set()
    for node in ast.walk(_TREE):
        body = getattr(node, "body", None)
        if isinstance(body, list) and body and isinstance(body[0], ast.Expr) \
                and isinstance(body[0].value, ast.Constant):
            skip.add(id(body[0].value))                      # docstring
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) \
                and isinstance(node.func.value, ast.Name) and node.func.value.id == "logger":
            skip.update(id(n) for n in ast.walk(node))       # log satırı
        if isinstance(node, ast.Call) and getattr(node.func, "attr", "") == "compile":
            skip.update(id(n) for n in ast.walk(node))       # regex desenleri
    hits = sorted({(n.lineno, n.value[:90]) for n in ast.walk(_TREE)
                   if isinstance(n, ast.Constant) and isinstance(n.value, str)
                   and id(n) not in skip and n.value not in _ALLOWED
                   and not _is_prompt(n.value) and br.TRADE_LANG_RE.search(n.value)})
    assert hits == [], f"hedef/işlem yönetimi dili üreten metin: {hits}"


def test_explain_prompt_and_validation():
    strings = " ".join(_strings("_enrich_signal_explanation"))
    assert "Stop-Loss" not in strings and "Trend dönüş seviyesi (Supertrend): " in strings
    # AI yine de üretirse commentary'ye düşer
    assert "_TRADE_LANG_RE.search(text)" in _func_src("_enrich_signal_explanation")


# ── VPS (py3.12): gerçek import — DQV import bloğu yedeğe düşmemiş olmalı ────

@pytest.mark.skipif(sys.version_info < (3, 10), reason="app.py 3.10+ ister — VPS venv'de çalıştır")
def test_app_wiring_on_vps():
    sys.path.insert(0, os.path.dirname(_APP_PY))
    import app
    assert app._RETIRED_TRADE_KEYS == br.RETIRED_TRADE_KEYS
    assert app._TRADE_LANG_RE.pattern == br.TRADE_LANG_RE.pattern
    s = app._enrich_stock({"ticker": "THYAO", "tp1": 1.0, "rr_signal": 2.0, "entry_note": "SL yakın — R/R"})
    assert not set(br.RETIRED_TRADE_KEYS) & set(s)
