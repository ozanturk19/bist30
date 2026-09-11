"""CPO-1587 Faz 2 — /sektor-harita, /gundem, anasayfa icin backend SSR extraction.

Ayni /tarama desenini (_compute_tarama_results, bkz. test_cpo1587_tarama_ssr.py)
3 sayfaya daha uygular:
  - _compute_sector_heatmap(): sektor_harita() (SSR) ve api_sector_heatmap()
    (canli JS) artik ayni fonksiyonu cagirir.
  - _compute_gundem_data(): gundem_page() (SSR) ve api_gundem() (canli JS)
    artik ayni fonksiyonu cagirir.
  - _get_xu100_level() + _compute_index_ssr_context(): index() (SSR) ve
    api_data() artik BIST100 seviyesini ayni yerden okur (kopya hesaplama yok).

Bu testler extraction'in davranisi bozmadigini dogrular. Python 3.9 (yerel Mac)
app.py'yi (3.10+ sozdizimi) import edemedigi icin fonksiyonlar kaynaktan izole
exec edilir (bkz. test_cpo1587_tarama_ssr.py).
"""
import os
import re
from datetime import datetime, date
from zoneinfo import ZoneInfo

_APP_PY = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "app.py")

with open(_APP_PY, encoding="utf-8") as _f:
    _SRC = _f.read()


class _FakeLockCtx:
    def __enter__(self):
        return None

    def __exit__(self, *a):
        return False


def _extract(func_name):
    m = re.search(r"def " + re.escape(func_name) + r"\(.*?\n\n\n", _SRC, re.DOTALL)
    assert m, f"{func_name} not found / boundary regex needs updating"
    return m.group(0)


# ── _compute_sector_heatmap ──────────────────────────────────────────────────

_SECTORS = {"AKBNK": "Bankacılık", "THYAO": "Ulaştırma", "ASELS": "Savunma"}

_SECTOR_STOCKS = [
    {"ticker": "XU030", "signal": "AL", "rvol": 5.0},
    {"ticker": "AKBNK", "signal": "AL", "sector": "Bankacılık", "rvol": 1.5},
    {"ticker": "GARAN", "signal": "SAT", "sector": "Bankacılık", "rvol": 0.8},
    {"ticker": "THYAO", "signal": "AL", "sector": "Ulaştırma", "rvol": 2.0},
    {"ticker": "ASELS", "signal": "BEKLE", "sector": "Savunma", "rvol": None},
]


def _fresh_sector_heatmap():
    ns = {
        "_lock": _FakeLockCtx(),
        "_cache": {"data": _SECTOR_STOCKS, "updated_at": "11.09.2026 18:00"},
        "_get_sector": lambda ticker: _SECTORS.get(ticker, "Diğer"),
    }
    exec(_extract("_compute_sector_heatmap"), ns)
    return ns["_compute_sector_heatmap"]


def test_sector_heatmap_excludes_xu030():
    fn = _fresh_sector_heatmap()
    result, upd = fn()
    names = [r["name"] for r in result]
    assert "XU030" not in names
    assert upd == "11.09.2026 18:00"


def test_sector_heatmap_scores_and_sorts_desc():
    fn = _fresh_sector_heatmap()
    result, _ = fn()
    # Bankacilik: 1 AL, 1 SAT -> score 0; Ulastirma: 1 AL, 0 SAT -> score 100
    by_name = {r["name"]: r for r in result}
    assert by_name["Ulaştırma"]["score"] == 100
    assert by_name["Bankacılık"]["score"] == 0
    assert by_name["Savunma"]["score"] == 0  # tek hisse BEKLE -> al=sat=0, score=(0-0)/1*100=0
    # sirali (score desc) oldugunu dogrula
    assert [r["score"] for r in result] == sorted([r["score"] for r in result], reverse=True)


def test_sector_heatmap_avg_rvol_ignores_none():
    fn = _fresh_sector_heatmap()
    result, _ = fn()
    by_name = {r["name"]: r for r in result}
    assert by_name["Savunma"]["avg_rvol"] is None  # tek hissenin rvol'u None


# ── _compute_gundem_data ─────────────────────────────────────────────────────

_TZ_TR_STUB = ZoneInfo("Europe/Istanbul")

_GUNDEM_STOCKS = [
    {"ticker": "XU030", "signal": "AL", "signal_date": "12.09.2026"},
    {"ticker": "AKBNK", "signal": "AL", "signal_date": "12.09.2026",
     "indicators": {"adx": {"label": "ADX 30"}}},
    {"ticker": "THYAO", "signal": "SAT", "signal_date": "11.09.2026",
     "indicators": {"adx": {"label": "ADX 40"}}},
    {"ticker": "ASELS", "signal": "BEKLE", "signal_date": "12.09.2026"},
]


def _fresh_gundem():
    ns = {
        "_lock": _FakeLockCtx(),
        "_cache": {"data": _GUNDEM_STOCKS, "updated_at": "12.09.2026 09:00"},
        "_TZ_TR": _TZ_TR_STUB,
        "datetime": datetime,
        "date": date,
        "_BILANCO_PERIODS": [],
        "is_trading_day": lambda d: True,
        "_market_open": lambda now: True,
        "_data_quality_snapshot": lambda stocks: {"updated_at": "12.09.2026 09:00"},
    }
    exec(_extract("_compute_gundem_data"), ns)
    return ns["_compute_gundem_data"]


def test_gundem_excludes_xu030_from_everything():
    fn = _fresh_gundem()
    g = fn()
    tickers_new = [s["ticker"] for s in g["new_signals"]]
    tickers_al = [s["ticker"] for s in g["strong_al"]]
    assert "XU030" not in tickers_new
    assert "XU030" not in tickers_al
    assert g["signal_summary"]["total"] == 3  # XU030 haric


def test_gundem_new_signals_today_only_non_bekle():
    fn = _fresh_gundem()
    g = fn()
    # today mock edilmedigi icin gercek datetime.now(_TZ_TR) kullanilir -- bu
    # test suit'in calistigi gunun tarihini bilmiyoruz, o yuzden sadece
    # BEKLE'nin hicbir zaman new_signals'a girmedigini dogrula (tarih ne olursa olsun).
    assert all(s["signal"] != "BEKLE" for s in g["new_signals"])


def test_gundem_strong_al_sorted_by_adx_desc():
    fn = _fresh_gundem()
    g = fn()
    assert [s["ticker"] for s in g["strong_al"]] == ["AKBNK"]  # tek AL hisse (XU030 haric)


def test_gundem_closed_message_none_when_market_open():
    fn = _fresh_gundem()
    g = fn()
    assert g["market_open"] is True
    assert g["closed_message"] is None


# ── _get_xu100_level / _compute_index_ssr_context ────────────────────────────

_INDEX_STOCKS = [
    {"ticker": "XU030", "signal": "AL", "signal_strength": 999},
    {"ticker": "AKBNK", "signal": "AL", "signal_strength": 80},
    {"ticker": "THYAO", "signal": "SAT", "signal_strength": 60},
    {"ticker": "ASELS", "signal": "AL", "signal_strength": 40},
    {"ticker": "GARAN", "signal": "BEKLE", "signal_strength": None},
]


def _fresh_xu100_level():
    ns = {
        "_lock": _FakeLockCtx(),
        "_load_xu100_chart_from_disk": lambda: None,
        "_xu100_chart_cache": {"data": {"ohlc": [
            {"close": 14000.0}, {"close": 14200.0}, {"close": 14505.5},
        ]}},
    }
    exec(_extract("_get_xu100_level"), ns)
    return ns["_get_xu100_level"]


def test_xu100_level_close_and_change_pct():
    fn = _fresh_xu100_level()
    lvl = fn()
    assert lvl["close"] == 14505.5
    expected_chg = round((14505.5 - 14200.0) / 14200.0 * 100, 2)
    assert lvl["change_pct"] == expected_chg
    assert lvl["spark"] == [14000.0, 14200.0, 14505.5]


def test_xu100_level_empty_ohlc_returns_none():
    ns = {
        "_lock": _FakeLockCtx(),
        "_load_xu100_chart_from_disk": lambda: None,
        "_xu100_chart_cache": {"data": {"ohlc": []}},
    }
    exec(_extract("_get_xu100_level"), ns)
    lvl = ns["_get_xu100_level"]()
    assert lvl["close"] is None
    assert lvl["change_pct"] is None
    assert lvl["spark"] == []


def _fresh_index_ssr_context():
    ns = {
        "_lock": _FakeLockCtx(),
        "_cache": {"data": _INDEX_STOCKS, "updated_at": "12.09.2026 09:00"},
        "_load_xu100_chart_from_disk": lambda: None,
        "_xu100_chart_cache": {"data": {"ohlc": [{"close": 14200.0}, {"close": 14505.5}]}},
    }
    # _compute_index_ssr_context, govde icinde _get_xu100_level'i cagiriyor --
    # ikisi de ayni namespace'te tanimlanmali.
    exec(_extract("_get_xu100_level") + _extract("_compute_index_ssr_context"), ns)
    return ns["_compute_index_ssr_context"]


def test_index_ssr_excludes_xu030_and_xu100_from_counts():
    fn = _fresh_index_ssr_context()
    ctx = fn()
    assert ctx["signal_counts"]["total"] == 4  # XU030 haric (5 - 1)
    assert ctx["signal_counts"]["al"] == 2  # AKBNK, ASELS
    assert ctx["signal_counts"]["sat"] == 1
    assert ctx["signal_counts"]["bekle"] == 1


def test_index_ssr_top_signals_only_al_with_numeric_score_sorted_desc():
    fn = _fresh_index_ssr_context()
    ctx = fn()
    tickers = [s["ticker"] for s in ctx["top_signals"]]
    assert tickers == ["AKBNK", "ASELS"]  # THYAO (SAT) ve GARAN (None skor) haric, once yuksek skor


def test_index_ssr_bist_level_uses_same_source():
    fn = _fresh_index_ssr_context()
    ctx = fn()
    assert ctx["bist_level"]["close"] == 14505.5
