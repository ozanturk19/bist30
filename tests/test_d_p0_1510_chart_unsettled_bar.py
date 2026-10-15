"""D-P0-1510 (15.10) — grafik verisinde bar_date'ten sonraki (oturmamış/yarım)
bar diske yazılmaz: EOD tetiğinden önce "bugün"ün tek-fiyat (O=H=L=C eşit)
barı _compute_chart_data() çıktısına girmemeli.

app.py 3.10+ ister; VPS venv'de (3.12) çalıştır.
"""
import os
import sys

import pytest

if sys.version_info < (3, 10):
    pytest.skip("app.py 3.10+ ister — VPS venv'de çalıştır", allow_module_level=True)

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import datetime as dt

import numpy as np
import pandas as pd

import app

FIXED_LAST = dt.date(2026, 10, 8)      # gerçek, oturmuş son seans günü (Perşembe)
UNSETTLED_DAY = dt.date(2026, 10, 9)   # EOD tetiğinden önce gelen yarım bar (Cuma)


def _synthetic_chart_df():
    idx = pd.bdate_range(end=pd.Timestamp(FIXED_LAST, tz="Europe/Istanbul"), periods=170)
    n = len(idx)
    base = 100 + np.arange(n) * 0.05 + 2 * np.sin(np.arange(n) / 5)
    df = pd.DataFrame({
        "Open":   base - 0.2,
        "High":   base + 0.4,
        "Low":    base - 0.4,
        "Close":  base,
        "Volume": 1_000_000.0,
    }, index=idx)
    # Yahoo'nun seans içinde döndürdüğü oturmamış "bugün" barı: tek anlık fiyat,
    # O=H=L=C eşit (bkz. plan D-P0-1510 kök neden, 2026-10-15 07:1x UTC örneği).
    unsettled_price = float(df["Close"].iloc[-1])
    unsettled = pd.DataFrame({
        "Open": unsettled_price, "High": unsettled_price,
        "Low": unsettled_price, "Close": unsettled_price, "Volume": 0.0,
    }, index=pd.DatetimeIndex([pd.Timestamp(UNSETTLED_DAY, tz="Europe/Istanbul")]))
    return pd.concat([df, unsettled]).sort_index()


def test_unsettled_today_bar_is_dropped_before_eod(monkeypatch):
    monkeypatch.setattr(app, "_fetch_chart_subprocess", lambda ticker, period: _synthetic_chart_df())
    monkeypatch.setattr(app, "_fetch_intraday_subprocess", lambda ticker: None)
    # EOD tetiği henüz gelmedi → beklenen seans günü hâlâ FIXED_LAST (dünkü kapanış).
    monkeypatch.setattr(app, "_expected_bar_date", lambda *a, **k: FIXED_LAST)

    data = app._compute_chart_data("TESTX", "2y")

    assert data is not None and not data.get("insufficient_history")
    ohlc_dates = [row["time"] for row in data["ohlc"]]
    assert UNSETTLED_DAY.isoformat() not in ohlc_dates
    assert ohlc_dates[-1] == FIXED_LAST.isoformat()
    assert data["summary"]["updated_at"].startswith(FIXED_LAST.strftime("%d.%m.%Y"))


def test_bar_kept_once_eod_trigger_confirms_today(monkeypatch):
    monkeypatch.setattr(app, "_fetch_chart_subprocess", lambda ticker, period: _synthetic_chart_df())
    monkeypatch.setattr(app, "_fetch_intraday_subprocess", lambda ticker: None)
    # EOD tetiği geçti → beklenen seans günü artık UNSETTLED_DAY (settled kapanış).
    monkeypatch.setattr(app, "_expected_bar_date", lambda *a, **k: UNSETTLED_DAY)

    data = app._compute_chart_data("TESTX", "2y")

    assert data is not None and not data.get("insufficient_history")
    ohlc_dates = [row["time"] for row in data["ohlc"]]
    assert ohlc_dates[-1] == UNSETTLED_DAY.isoformat()
