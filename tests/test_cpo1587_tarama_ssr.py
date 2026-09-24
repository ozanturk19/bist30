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
import sys
from datetime import datetime

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_APP_PY = os.path.join(_ROOT, "app.py")
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)
import tarama_fields  # noqa: E402

_SECTORS = {"AKBNK": "Bankacılık", "THYAO": "Ulaştırma", "ASELS": "Savunma"}

_STOCKS = [
    {"ticker": "XU030", "signal": "AL", "price": 1, "signal_strength": 999},
    {"ticker": "AKBNK", "signal": "AL", "price": 50.0, "change_pct": 1.2,
     "adx": 30.4, "indicators": {"adx": {"label": "ADX 30"}}, "signal_bars": 2,
     "signal_date": "10.09.2026", "entry_quality": "IDEAL", "vol_ratio": 1.5,
     "is_premium": True, "tier": "guclu_sinyal", "signal_strength": 80,
     "bull_score": 70, "sl_level": 45.0},
    {"ticker": "THYAO", "signal": "SAT", "price": 300.0, "change_pct": -2.1,
     "adx": 39.6, "indicators": {"adx": {"label": "ADX 40"}}, "signal_bars": 1,
     "signal_date": "11.09.2026", "entry_quality": "DIKKATLI", "vol_ratio": 0.8,
     "is_premium": False, "tier": None, "signal_strength": 55,
     "bull_score": 10, "sl_level": None},
    {"ticker": "ASELS", "signal": "BEKLE", "price": 90.0, "change_pct": 0.0,
     "adx": 15.4, "indicators": {"adx": {"label": "ADX 15"}}, "signal_bars": 5,
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


def _fresh_compute(stocks=None, updated_at="11.09.2026 18:00", health=None, fund=None):
    """Her cagrida kaynaktan yeniden exec eder — testler arasi mutasyona kapali."""
    with open(_APP_PY, encoding="utf-8") as f:
        src = f.read()
    m = re.search(r"def _compute_tarama_results\(.*?\n\n\n", src, re.DOTALL)
    assert m
    m_d51 = re.search(r"def _tarama_d51_fields\(.*?\n\n\n", src, re.DOTALL)
    assert m_d51
    cache = {"data": _STOCKS if stocks is None else stocks, "updated_at": updated_at}
    ns = {
        "_lock": _FakeLockCtx(),
        "_cache": cache,
        "_get_sector": lambda ticker: _SECTORS.get(ticker, "Diğer"),
        "STOCK_NAMES": {},
        "derive_adx_label": lambda adx: f"ADX {adx:.0f}",
        "datetime": datetime,
        # CPO-1783: _compute_tarama_results artık INDEX_TICKERS kanonuna
        # bağlı (önceden inline `("XU030", "XU100")` idi).
        "INDEX_TICKERS": {"XU030", "XU100"},
        # D-51: temel skor / oran kaynaklari (varsayilan bos) + turetme modulu
        "_financial_health_cache": health if health is not None else {},
        "_fundamentals_cache": fund if fund is not None else {},
        "tarama_fields": tarama_fields,
    }
    exec(m_d51.group(0), ns)
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


def test_min_adx_filter_uses_raw_adx_not_rounded_label():
    """CPO-1751/K-BU dersi: `indicators.adx.label` insan-okur YUVARLANMIS
    metindir ("ADX 26"). ISDMR canli ornegi (22.09): raw adx=25.9, label
    "ADX 26"ya yuvarlanir. min_adx=26 filtresi HAM degere gore calismali --
    25.9 esigi GECMEDI, sonucta olmamali. Eski kod label'i geri parse edip
    26.0 >= 26 ile yanlislikla iceri alirdi."""
    stocks = [
        {"ticker": "ISDMR", "signal": "AL", "price": 10.0, "change_pct": 0.5,
         "adx": 25.9, "indicators": {"adx": {"label": "ADX 26"}},
         "signal_bars": 1, "signal_date": "20.09.2026", "entry_quality": "IDEAL",
         "vol_ratio": 1.0, "is_premium": False, "tier": None,
         "signal_strength": 40, "bull_score": 20, "sl_level": None},
    ]
    fn = _fresh_compute(stocks=stocks)
    results, _, _ = fn(min_adx=26)
    assert results == []


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


def test_cpo1794_stale_fields_passthrough():
    """CPO-1794: donuk hisse satirinda stale_reason/data_quality/last_fresh_ts
    tasinir, taze hissede None kalir."""
    stale = {"ticker": "MARKA", "signal": "BEKLE", "price": 73.45,
             "change_pct": -2.39, "adx": 23.2, "data_quality": "stale",
             "stale_reason": "son seans verisi gelmedi",
             "last_fresh_ts": 1789139651.47}
    fn = _fresh_compute(stocks=[stale, _STOCKS[1]])
    results, _, _ = fn()
    by = {r["ticker"]: r for r in results}
    assert by["MARKA"]["data_quality"] == "stale"
    assert by["MARKA"]["stale_reason"] == "son seans verisi gelmedi"
    assert by["MARKA"]["last_fresh_ts"] == 1789139651.47
    assert by["AKBNK"]["stale_reason"] is None
    assert by["AKBNK"]["data_quality"] is None
    assert by["AKBNK"]["last_fresh_ts"] is None


# ── D-51: satir alanlari ─────────────────────────────────────────────────────
_HEALTH = {
    "AKBNK": {"data": {"temel_analiz_skoru": 72, "borsapusula_skoru": 68, "data_completeness": 0.95,
                       "categories": {"karlilik": 80, "nakit_akisi": 60, "kaldirac": 70, "degerleme_buyume": 75},
                       "categories_na": []}},
    "THYAO": {"data": {"temel_analiz_skoru": None, "borsapusula_skoru": 40}},
}
_FUND = {
    "AKBNK": {"data": {"pe_ratio": 4.0, "pb_ratio": 0.9, "roe": 30.5}},
    "THYAO": {"data": {"pe_ratio": 8.0, "pb_ratio": 1.0, "roe": 12.0}},
}


def test_d51_fields_present_on_every_row_even_without_sources():
    fn = _fresh_compute()
    results, _, _ = fn()
    for r in results:
        for k in ("temel_analiz_skoru", "borsapusula_skoru", "data_completeness", "categories",
                  "categories_na", "va", "pe", "pb", "roe", "ema_diff", "lim"):
            assert k in r
        assert r["temel_analiz_skoru"] is None and r["categories"] is None and r["categories_na"] == []


def test_d51_health_and_ratios_join():
    fn = _fresh_compute(health=_HEALTH, fund=_FUND)
    by = {r["ticker"]: r for r in fn()[0]}
    a = by["AKBNK"]
    assert a["temel_analiz_skoru"] == 72 and a["borsapusula_skoru"] == 68
    assert a["categories"]["karlilik"] == 80 and a["data_completeness"] == 0.95
    assert (a["pe"], a["pb"], a["roe"]) == (4.0, 0.9, 30.5)
    # skoru bastirilmis kayit: hicbir temel alan yok (BP dahil) -- /api/tarama/temel ile ayni
    t = by["THYAO"]
    assert t["temel_analiz_skoru"] is None and t["borsapusula_skoru"] is None and t["categories"] is None
    assert by["ASELS"]["pe"] is None and by["ASELS"]["va"] is None


def test_d51_valuation_band_thresholds_and_mixed():
    med = {"sector": {"S": {"pe": (10.0, 5), "pb": (2.0, 5)}}, "market": {"pe": 12.0, "pb": 1.5}}
    f = tarama_fields.derive_valuation_band
    assert f(7.9, 1.5, "S", med) == "u"        # 0,79 ucuz + 0,75 ucuz
    assert f(8.0, 2.0, "S", med) == "m"        # 0,80 makul sinir
    assert f(12.5, 2.5, "S", med) == "m"       # 1,25 makul sinir
    assert f(12.6, 2.6, "S", med) == "p"
    assert f(5.0, 3.0, "S", med) == "k"        # biri ucuz biri pahali
    assert f(5.0, 2.0, "S", med) == "u"        # ucuz + makul -> ucuz tarafta
    assert f(-3.0, None, "S", med) is None     # zarar: F/K tanimsiz, PD/DD yok
    assert f(None, 1.0, "S", med) == "u"       # yalniz PD/DD 0,5


def test_d51_valuation_uses_market_median_when_peers_lt_3():
    med = {"sector": {"S": {"pe": (10.0, 2), "pb": (None, 0)}}, "market": {"pe": 20.0, "pb": 2.0}}
    assert tarama_fields.derive_valuation_band(12.0, None, "S", med) == "u"   # 12/20 = 0,6 (sektor n=2 sayilmaz)
    assert tarama_fields.derive_valuation_band(12.0, None, "YOK", med) == "u"


def test_d51_valuation_medians_positive_only():
    fund = {"A": {"pe_ratio": 5.0, "pb_ratio": 1.0}, "B": {"pe_ratio": -4.0, "pb_ratio": 2.0},
            "C": {"pe_ratio": 15.0, "pb_ratio": None}, "D": {"pe_ratio": 25.0, "pb_ratio": 3.0}}
    m = tarama_fields.valuation_medians(fund, lambda tk: "S")
    assert m["sector"]["S"]["pe"] == (15.0, 3)   # 5, 15, 25 (negatif atildi)
    assert m["sector"]["S"]["pb"] == (2.0, 3)
    assert m["market"]["pe"] == 15.0


def test_d51_ema_diff_signed():
    f = tarama_fields.ema_diff_pct
    assert f({"ema1299": {"diff_pct": 3.456, "bull": True, "bear": False}}) == 3.46
    assert f({"ema1299": {"diff_pct": 3.456, "bull": False, "bear": True}}) == -3.46
    assert f({"ema1299": {"diff_pct": None}}) is None
    assert f({}) is None and f(None) is None


def test_d51_limit_flag_from_change():
    f = tarama_fields.limit_flag_from_change
    assert f(110.0, 10.0) == "tavan"                 # prev 100 -> tavan 110
    assert f(90.0, -10.0) == "taban"
    assert f(109.9, 9.9) is None
    assert f(None, 10.0) is None and f(50.0, None) is None and f(50.0, 3.0) is None
    # fiyat adimi: prev 13,50 (tick 0,01) -> tavan 14,85
    assert f(14.85, 10.0) == "tavan"


def test_d51_lim_blank_for_stale_row():
    stale = [{"ticker": "AKBNK", "signal": "AL", "price": 110.0, "change_pct": 10.0, "adx": 20.0,
              "stale_reason": "son seans verisi gelmedi"}]
    fresh = [dict(stale[0], stale_reason=None)]
    assert _fresh_compute(stocks=stale)()[0][0]["lim"] is None
    assert _fresh_compute(stocks=fresh)()[0][0]["lim"] == "tavan"
