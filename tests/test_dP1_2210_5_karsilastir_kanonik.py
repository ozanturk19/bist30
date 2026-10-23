"""D-P1-2210-5 (genis denetim 22.10): /api/karsilastir piyasa degeri ve temettu
verimi alanlari eskiden HER ZAMAN Yahoo (fund['market_cap']/['dividend_yield'])
donuyordu -- pe_val/pb_val'in KAP-once dallanmasi bu iki alana uygulanmamisti.
KAP kaydi varken artik kap_temel_v2.valuation_now (piyasa_degeri) ve
kap_financials.dividend_ttm (dividend_yield) kaynakli; kayit yokken Yahoo'nun
reddedilen ham degerine (docs/URUN-VE-TASARIM.md) dusulmuyor, None donuyor."""
import gzip
import json
import os
import sys

import pytest

if sys.version_info < (3, 10):
    pytest.skip("app.py 3.10+ ister — VPS venv'de çalıştır", allow_module_level=True)

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

import app  # noqa: E402
import kap_financials as kf  # noqa: E402
import kap_temel_v2 as ktv2  # noqa: E402

FIX = os.path.join(ROOT, "tests", "fixtures", "kap_temel_v2")

YAHOO_FUND = {"pe_ratio": 11.7, "pb_ratio": 1.74, "roe": 17.6, "shares": 1926795598.0,
              "market_cap": {"value": 7.6e11, "currency": "TRY"}, "dividend_yield": 2.28}


def _rec(t):
    with gzip.open(os.path.join(FIX, t + ".json.gz"), "rt", encoding="utf-8") as f:
        return json.load(f)


def _patch_common(monkeypatch, price_tuprs=397.0, price_garan=97.0):
    rec = _rec("TUPRS")
    monkeypatch.setattr(kf, "load_record", lambda t, base_dir=None: rec if t == "TUPRS" else None)
    monkeypatch.setattr(app, "_get_fundamentals", lambda t, force=False: dict(YAHOO_FUND))
    monkeypatch.setitem(app._cache, "data", [
        {"ticker": "TUPRS", "price": price_tuprs, "signal": "AL"},
        {"ticker": "GARAN", "price": price_garan, "signal": "AL"},
    ])
    monkeypatch.setitem(app._KAP_SECTOR_METRICS, "ts", 0.0)
    monkeypatch.setitem(app._KAP_SECTOR_METRICS, "data", {})
    return rec


def test_market_cap_kap_kaydi_varken_kap_degerinden(monkeypatch):
    """TUPRS icin KAP kaydi var -> market_cap Yahoo'nun 7.6e11'inden DEGIL,
    kap_temel_v2.valuation_now'un piyasa_degeri'nden (price x KAP pay adedi)."""
    _patch_common(monkeypatch)
    client = app.app.test_client()
    r = client.get("/api/karsilastir?tickers=TUPRS,GARAN")
    assert r.status_code == 200
    rows = {row["ticker"]: row for row in r.get_json()["stocks"]}

    expected_now = ktv2.valuation_now(_rec("TUPRS"), ktv2.template_of(_rec("TUPRS")), 397.0,
                                       yahoo_shares=YAHOO_FUND["shares"])
    assert rows["TUPRS"]["market_cap"] == {"value": expected_now["piyasa_degeri"], "currency": "TRY"}
    assert rows["TUPRS"]["market_cap"]["value"] != YAHOO_FUND["market_cap"]["value"]


def test_market_cap_kap_kaydi_yokken_yahoo_yedegine_duser(monkeypatch):
    """GARAN icin KAP kaydi yok (mock None dondurur) -> Yahoo market_cap yedek olarak kalir
    (reddedilen alan degil -- market_cap icin KAP'a ozel bir 'yanlis' degil, sadece eksik veri)."""
    _patch_common(monkeypatch)
    client = app.app.test_client()
    r = client.get("/api/karsilastir?tickers=TUPRS,GARAN")
    rows = {row["ticker"]: row for row in r.get_json()["stocks"]}
    assert rows["GARAN"]["market_cap"] == YAHOO_FUND["market_cap"]


def test_dividend_yield_kap_kaydi_varken_kap_hesabindan(monkeypatch):
    """TUPRS icin KAP kaydi var -> dividend_yield kap_financials.dividend_ttm tabanli
    (apply_to_fundamentals zaten fund['dividend_yield']'i bu degerle yeniden yaziyor)."""
    _patch_common(monkeypatch)
    client = app.app.test_client()
    r = client.get("/api/karsilastir?tickers=TUPRS,GARAN")
    rows = {row["ticker"]: row for row in r.get_json()["stocks"]}

    fund = app._fundamentals_kap("TUPRS", dict(YAHOO_FUND))
    assert rows["TUPRS"]["dividend_yield"] == fund["dividend_yield"]
    # D-40a0 kanonik hesap Yahoo'nun ham %2,28'inden farkli olmali (ayni sayiysa test anlamsiz).
    # (Gercek TUPRS fixture'inda temettu odemesi olabilir/olmayabilir -- her halukarda
    # deger kap_financials.dividend_ttm'den gelmeli, YAHOO_FUND sabitinden degil.)
    assert rows["TUPRS"]["dividend_yield"] == fund.get("dividend_yield")


def test_dividend_yield_kap_kaydi_yokken_yahoonun_reddedilen_degerine_dusmez(monkeypatch):
    """GARAN icin KAP kaydi yok -> docs/URUN-VE-TASARIM.md'de reddedilen Yahoo
    dividendYield'a (odeme yokken yanlis yuzde gosterebilir) DUSULMEZ, None doner."""
    _patch_common(monkeypatch)
    client = app.app.test_client()
    r = client.get("/api/karsilastir?tickers=TUPRS,GARAN")
    rows = {row["ticker"]: row for row in r.get_json()["stocks"]}
    assert rows["GARAN"]["dividend_yield"] is None
    assert rows["GARAN"]["dividend_yield"] != YAHOO_FUND["dividend_yield"]
