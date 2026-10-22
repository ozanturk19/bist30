"""D-18b — hisse rotası SSR bağlamı: initial_tab + closes_30.

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
def test_closes_30_dondurulmus_sinyalden_ileri_grafik_kirpilir(monkeypatch):
    """D-P1-2210-1 (SKBNK): %10,5 tavan guard sinyali önceki günde dondururken
    (örn. bedelli hak kullanım günü) grafik önbelleği guard'sız bugünü yazmış olabilir —
    liste bu durumda bar_date'i geçen barları kırpmalı, aksi halde şablon fiyat+tarih
    uyuşmazlığı (yanlış gün etiketi) üretir."""
    import app
    monkeypatch.setattr(app, "_load_chart_from_disk_per_ticker", lambda t: (_chart(40), "x"))
    # grafik sinyalden ileride (bugünün barını zaten yazmış) — dondurulmuş sinyal 3 gün geride.
    # bar_date grafikte zaten var olan bir tarih → kırpılır, grafiğin KENDİ kapanışı korunur
    # (sinyal fiyatıyla ezilmez — aynı gün için iki farklı kaynak varsa grafik otoriter kalır).
    st = {"bar_date": "08.09.2026", "price": 42.0, "close_status": "resmi"}
    rows = app._closes_30("THYAO", st)
    assert rows[-1] == ["2026-09-08", 46.0]
    assert all(r[0] <= "2026-09-08" for r in rows)
    # bar_date grafik penceresinden bile geride (örn. uzun süredir donmuş sinyal) →
    # kırpma hepsini siler, dondurulmuş fiyat son nokta olarak eklenir
    st_disi = {"bar_date": "01.08.2026", "price": 42.0, "close_status": "resmi"}
    assert app._closes_30("THYAO", st_disi) == [["2026-08-01", 42.0]]
    # grafik tam bar_date'te bitiyorsa (fark yok) dokunulmaz
    st2 = {"bar_date": "11.09.2026", "price": 49.0, "close_status": "resmi"}
    assert app._closes_30("THYAO", st2)[-1] == ["2026-09-11", 49.0]


@PY310
def test_hisse_sayfasi_baglami(monkeypatch):
    import app
    monkeypatch.setattr(app, "_load_chart_from_disk_per_ticker", lambda t: (_chart(40), "x"))
    ctx = _ctx(app, "/hisse/THYAO?tab=temel")
    assert ctx["initial_tab"] == "temel" and len(ctx["closes_30"]) == 30
    assert _ctx(app, "/hisse/THYAO")["initial_tab"] == "ozet"
    assert _ctx(app, "/hisse/THYAO?tab=zzz")["initial_tab"] == "ozet"


