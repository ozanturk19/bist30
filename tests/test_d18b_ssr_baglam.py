"""D-18b — hisse rotası SSR bağlamı: initial_tab + closes_30; /lite'a sayısal di_plus/di_minus/adx.

VPS (py3.10+). Şablon bağlamı `template_rendered` sinyaliyle okunur.
"""
import os
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
PY310 = pytest.mark.skipif(sys.version_info < (3, 10), reason="app.py 3.10+ ister")


def _ctx(app, url):
    from flask import template_rendered
    seen = []

    def _rec(sender, template, context, **kw):
        if template.name == "hisse.html":
            seen.append(context)

    template_rendered.connect(_rec, app.app)
    try:
        assert app.app.test_client().get(url).status_code == 200
    finally:
        template_rendered.disconnect(_rec, app.app)
    return seen[0]


def _chart(n=40):
    import datetime as dt
    d0 = dt.date(2026, 8, 3)
    return {"ohlc": [{"time": (d0 + dt.timedelta(days=i)).isoformat(), "open": 1, "high": 2, "low": 1,
                      "close": 10.0 + i} for i in range(n)]}


@PY310
def test_initial_tab_dogrulanir():
    import app
    assert app._hisse_initial_tab(None) == "ozet"
    assert app._hisse_initial_tab("temel") == "temel"
    assert app._hisse_initial_tab("grafik") == "grafik"
    assert app._hisse_initial_tab("ai") == "ozet"          # C-19 eski ad
    assert app._hisse_initial_tab("<script>") == "ozet"    # geçersiz → varsayılan


@PY310
def test_closes_30_son_30_gun_ve_resmi_kapanis_eki(monkeypatch):
    import app
    monkeypatch.setattr(app, "_load_chart_from_disk_per_ticker", lambda t: (_chart(40), "x"))
    rows = app._closes_30("THYAO", None)
    assert len(rows) == 30 and rows[-1] == ["2026-09-11", 49.0] and rows[0][0] == "2026-08-13"
    # grafik ucu geride + ana sinyal resmi kapanış → son nokta eklenir (30'da kalır)
    st = {"bar_date": "14.09.2026", "price": 55.5, "close_status": "resmi"}
    rows = app._closes_30("THYAO", st)
    assert len(rows) == 30 and rows[-1] == ["2026-09-14", 55.5]
    # geçici kapanışta eklenmez
    assert app._closes_30("THYAO", dict(st, close_status="gecici"))[-1][0] == "2026-09-11"
    # grafik verisi yoksa None
    monkeypatch.setattr(app, "_load_chart_from_disk_per_ticker", lambda t: (None, None))
    assert app._closes_30("THYAO", st) is None


@PY310
def test_hisse_sayfasi_baglami(monkeypatch):
    import app
    monkeypatch.setattr(app, "_load_chart_from_disk_per_ticker", lambda t: (_chart(40), "x"))
    ctx = _ctx(app, "/hisse/THYAO?tab=temel")
    assert ctx["initial_tab"] == "temel" and len(ctx["closes_30"]) == 30
    assert _ctx(app, "/hisse/THYAO")["initial_tab"] == "ozet"
    assert _ctx(app, "/hisse/THYAO?tab=zzz")["initial_tab"] == "ozet"


@PY310
def test_lite_sayisal_di_alanlari():
    import app
    row = app._enrich_stock({"ticker": "THYAO", "price": 1.0, "change_pct": 0.0})
    row.update({"di_plus": 27.5, "di_minus": 12.1, "adx": 31.2})
    with app._lock:
        _old = list(app._cache["data"])
        app._cache["data"] = [row]
    try:
        st = app.app.test_client().get("/api/hisse/THYAO/lite").get_json()["stock"]
    finally:
        with app._lock:
            app._cache["data"] = _old
    assert st["di_plus"] == 27.5 and st["di_minus"] == 12.1 and st["adx"] == 31.2
