"""CPO-1587 Faz 2 — /tarama SSR icin _compute_tarama_results() extraction.

tarama() (SSR, /tarama sayfasi) ve api_tarama() (/api/tarama) artik ayni
_compute_tarama_results() yardimci fonksiyonunu cagiriyor (onceden mantik
sadece api_tarama() icindeydi, tarama() cıplak render_template idi — AI
crawler'lar JS calistirmiyorsa /tarama'da hicbir hisse/sinyal verisi
gormuyordu). Bu test extraction'in davranisi bozmadigini (varsayilan
parametrelerle eski api_tarama() ile ayni filtre/sirala sonucunu urettigini)
dogrular. Python 3.9 (yerel Mac) app.py'yi (3.10+ sözdizimi) import edemediği
icin fonksiyon kaynaktan izole exec edilir (bkz. test_cpo1137_canonical_freshness.py).
"""
import os
import re
from datetime import datetime

_APP_PY = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "app.py")

_SECTORS = {"AKBNK": "Bankacılık", "THYAO": "Ulaştırma", "ASELS": "Savunma"}

_STOCKS = [
    {"ticker": "XU030", "signal": "AL", "price": 1, "signal_strength": 999},
    {"ticker": "AKBNK", "signal": "AL", "price": 50.0, "change_pct": 1.2,
     "indicators": {"adx": {"label": "ADX 30"}}, "signal_bars": 2,
     "signal_date": "10.09.2026", "entry_quality": "IDEAL", "vol_ratio": 1.5,
     "is_premium": True, "tier": "guclu_sinyal", "signal_strength": 80,
     "bull_score": 70, "sl_level": 45.0},
    {"ticker": "THYAO", "signal": "SAT", "price": 300.0, "change_pct": -2.1,
     "indicators": {"adx": {"label": "ADX 40"}}, "signal_bars": 1,
     "signal_date": "11.09.2026", "entry_quality": "DIKKATLI", "vol_ratio": 0.8,
     "is_premium": False, "tier": None, "signal_strength": 55,
     "bull_score": 10, "sl_level": None},
    {"ticker": "ASELS", "signal": "BEKLE", "price": 90.0, "change_pct": 0.0,
     "indicators": {"adx": {"label": "ADX 15"}}, "signal_bars": 5,
     "signal_date": "05.09.2026", "entry_quality": "UZAK", "vol_ratio": 1.0,
     "is_premium": False, "tier": None, "signal_strength": 20,
     "bull_score": 5, "sl_level": None},
]

_cache = {"data": _STOCKS, "updated_at": "11.09.2026 18:00"}


class _FakeLockCtx:
    def __enter__(self):
        return None

    def __exit__(self, *a):
        return False


def _fresh_compute():
    """Her cagrida kaynaktan yeniden exec eder — testler arasi mutasyona kapali."""
    with open(_APP_PY, encoding="utf-8") as f:
        src = f.read()
    m = re.search(r"def _compute_tarama_results\(.*?\n\n\n", src, re.DOTALL)
    assert m
    ns = {
        "_lock": _FakeLockCtx(),
        "_cache": _cache,
        "_get_sector": lambda ticker: _SECTORS.get(ticker, "Diğer"),
        "STOCK_NAMES": {},
        "derive_adx_label": lambda adx: f"ADX {adx:.0f}",
        "datetime": datetime,
    }
    exec(m.group(0), ns)
    return ns["_compute_tarama_results"]


def test_xu030_xu100_excluded():
    fn = _fresh_compute()
    results, sectors, upd = fn()
    tickers = [r["ticker"] for r in results]
    assert "XU030" not in tickers
    assert len(results) == 3


def test_default_call_returns_all_three_sorted_by_signal_strength_bucket():
    """Varsayilan sort='signal_strength': AL bucket once, SAT sonra, BEKLE ortada
    (bucket = AL:0, BEKLE:1, SAT:2), bucket icinde signal_strength desc."""
    fn = _fresh_compute()
    results, sectors, upd = fn()
    assert [r["ticker"] for r in results] == ["AKBNK", "ASELS", "THYAO"]
    assert sectors == ["Bankacılık", "Savunma", "Ulaştırma"]
    assert upd == "11.09.2026 18:00"


def test_signal_filter():
    fn = _fresh_compute()
    results, _, _ = fn(sig="SAT")
    assert [r["ticker"] for r in results] == ["THYAO"]


def test_price_range_filter():
    fn = _fresh_compute()
    results, _, _ = fn(min_p=60, max_p=500)
    # AKBNK (50) disarida kalir; ASELS (BEKLE, bucket 1) THYAO'dan (SAT, bucket 2) once gelir
    assert sorted(r["ticker"] for r in results) == ["ASELS", "THYAO"]


def test_min_adx_filter():
    fn = _fresh_compute()
    results, _, _ = fn(min_adx=35)
    assert [r["ticker"] for r in results] == ["THYAO"]


def test_only_premium_filter():
    fn = _fresh_compute()
    results, _, _ = fn(only_premium=True)
    assert [r["ticker"] for r in results] == ["AKBNK"]


def test_sector_filter_case_insensitive():
    fn = _fresh_compute()
    results, _, _ = fn(sector="bankacılık")
    assert [r["ticker"] for r in results] == ["AKBNK"]


def test_sort_by_price_desc_default():
    fn = _fresh_compute()
    results, _, _ = fn(sort_by="price")
    assert [r["ticker"] for r in results] == ["THYAO", "ASELS", "AKBNK"]


def test_sort_dir_explicit_asc_overrides_default():
    fn = _fresh_compute()
    results, _, _ = fn(sort_by="price", sort_dir="asc")
    assert [r["ticker"] for r in results] == ["AKBNK", "ASELS", "THYAO"]


def test_ssr_default_call_matches_first_n_semantics():
    """tarama() SSR yolu _compute_tarama_results() sonucunu [:30] ile kullanir --
    burada 3 hisse oldugundan tumu donmeli, XU030/XU100 haric."""
    fn = _fresh_compute()
    results, _, _ = fn()
    ssr_rows = results[:30]
    assert len(ssr_rows) == 3
    assert all(r["ticker"] != "XU030" for r in ssr_rows)
