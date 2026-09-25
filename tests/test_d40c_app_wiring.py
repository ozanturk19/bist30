"""D-40c: app.py ince baglanti -- TEMEL_V2 bayragi, gun sonu kaydi, /fundamentals ortancasi, /api/tarama."""
import gzip
import json
import os
import sys

import pytest

if sys.version_info < (3, 10):
    pytest.skip("app.py 3.10+ ister — VPS venv'de çalıştır", allow_module_level=True)

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

import app  # noqa: E402
import kap_financials as kf  # noqa: E402

FIX = os.path.join(ROOT, "tests", "fixtures", "kap_temel_v2")


def _rec(t):
    with gzip.open(os.path.join(FIX, t + ".json.gz"), "rt", encoding="utf-8") as f:
        return json.load(f)


def _swf():
    base = {"shares": 1926795598.0, "pe_ratio": 11.7, "roe": 17.6, "profit_margin": 3.0, "current_ratio": 1.4}
    return [dict(base, ticker=t, sector="Kimya, Petrol ve Plastik") for t in ("TUPRS", "A1", "A2", "A3", "A4")]


def test_bayrak_kapaliyken_hicbir_sey_eklenmez(monkeypatch):
    monkeypatch.delenv("TEMEL_V2", raising=False)
    swf = _swf()
    app._temel_v2_attach(swf, [{"ticker": "TUPRS", "price": 410.75}])
    assert all("_temel_v2" not in fd for fd in swf)
    h = app._fhs.compute_health_score(swf[0], swf[0]["sector"], swf)
    assert set(h["categories"]) <= set(app._fhs.CATEGORIES)


def test_bayrak_acikken_v2_skoru_ve_kaydi(monkeypatch):
    monkeypatch.setenv("TEMEL_V2", "1")
    rec = _rec("TUPRS")
    monkeypatch.setattr(kf, "load_record", lambda t, base_dir=None: rec)   # 5 sirket ayni kayit: grup >= 5
    swf = _swf()
    app._temel_v2_attach(swf, [{"ticker": t, "price": 410.75} for t in ("TUPRS", "A1", "A2", "A3", "A4")])
    v2 = swf[0]["_temel_v2"]
    assert v2["detay"]["surum"] == 2 and v2["detay"]["sablon"] == "sanayi" and v2["detay"]["veri_notu"] == "A"
    h = app._fhs.compute_health_score(swf[0], swf[0]["sector"], swf)
    assert h["temel_analiz_skoru"] == v2["detay"]["temel"] and set(h["categories"]) <= {
        "kalite", "degerleme", "buyume", "bilanco", "temettu"}
    json.dumps(v2["detay"], allow_nan=False)


def test_fundamentals_ve_tarama_v2_kaydindan(monkeypatch):
    rec = _rec("TUPRS")
    monkeypatch.setattr(kf, "load_record", lambda t, base_dir=None: rec if t == "TUPRS" else None)
    monkeypatch.setitem(app._cache, "data", [{"ticker": "TUPRS", "price": 410.75}])
    detay = {"surum": 2, "sebep": None, "roe": 14.8, "ortanca": {"fk": {"deger": 12.24, "n": 7}, "pd_dd": None,
             "ozsermaye_karliligi": {"deger": 3.0, "n": 13}},
             "degerleme": {"hukum": "makul", "fk": 11.73, "pd_dd": 1.74, "oran": {"fk": 0.96}}}
    monkeypatch.setitem(app._financial_health_cache, "TUPRS",
                        {"data": {"temel_analiz_skoru": 59, "temel_v2": detay}, "ts": 1.0})
    yahoo = {"pe_ratio": 11.7, "pb_ratio": 1.74, "roe": 17.6, "shares": 1926795598.0,
             "market_cap": {"value": 7.6e11, "currency": "TRY"}}
    out = app._fundamentals_temel_v2("TUPRS", app._fundamentals_kap("TUPRS", yahoo))
    assert out["sektor_ortanca"]["fk"] == {"deger": 12.24, "n": 7, "kapsam": "sektor"}
    assert out["sektor_ortanca"]["pd_dd"] is None
    row = app._tarama_d51_fields({"ticker": "TUPRS"}, dict(app._financial_health_cache),
                                 {"TUPRS": yahoo}, {"sector": {}, "market": {}})
    assert (row["va"], row["pe"], row["pb"], row["roe"]) == ("m", 11.73, 1.74, 14.8)
