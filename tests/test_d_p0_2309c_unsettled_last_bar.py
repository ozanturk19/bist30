"""D-P0-2309c — oturmamış son seans barı: %0,00 ile önceki kapanış gösterilmez.

app.py 3.10+ ister; VPS venv'de (3.12) çalıştır.
"""
import os
import sys
from datetime import datetime, timedelta, timezone

import pytest

if sys.version_info < (3, 10):
    pytest.skip("app.py 3.10+ ister — VPS venv'de çalıştır", allow_module_level=True)

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd

import app

TR = timezone(timedelta(hours=3))


def _df(rows):
    idx = pd.DatetimeIndex([pd.Timestamp(d, tz="Europe/Istanbul") for d, *_ in rows])
    return pd.DataFrame([r[1:] for r in rows], index=idx,
                        columns=["Open", "High", "Low", "Close", "Volume"])


def test_placeholder_copy_of_previous_bar_is_dropped():
    df = _df([("2026-09-21", 97.2, 99.9, 95.7, 99.9, 1),
              ("2026-09-22", 99.45, 102.0, 99.45, 100.3, 1),
              ("2026-09-23", 99.45, 102.0, 99.45, 100.3, 1)])
    out = app._drop_placeholder_last_bar(df, "TCELL")
    assert len(out) == 2 and out.index[-1].date().isoformat() == "2026-09-22"


def test_real_bar_and_flat_bar_are_kept():
    real = _df([("2026-09-21", 1, 2, 1, 1.5, 1), ("2026-09-22", 1, 2, 1, 1.6, 1),
                ("2026-09-23", 1.1, 2, 1, 1.7, 1)])
    assert len(app._drop_placeholder_last_bar(real, "X")) == 3
    flat = _df([("2026-09-21", 5, 5, 5, 5, 1), ("2026-09-22", 5, 5, 5, 5, 1), ("2026-09-23", 5, 5, 5, 5, 1)])
    assert len(app._drop_placeholder_last_bar(flat, "X")) == 3


def test_expected_bar_date_after_eod_trigger_is_today():
    wed_1815 = datetime(2026, 9, 23, 18, 15, tzinfo=TR)
    wed_1000 = datetime(2026, 9, 23, 10, 0, tzinfo=TR)
    thu_0050 = datetime(2026, 9, 24, 0, 50, tzinfo=TR)
    assert app._expected_bar_date(wed_1815).isoformat() == "2026-09-23"
    assert app._expected_bar_date(wed_1000).isoformat() == "2026-09-22"
    assert app._expected_bar_date(thu_0050).isoformat() == "2026-09-23"


def test_old_last_bar_after_eod_is_unsettled():
    df = _df([("2026-09-21", 1, 2, 1, 1.5, 1), ("2026-09-22", 1, 2, 1, 1.6, 1)])
    now = datetime(2026, 9, 23, 18, 15, tzinfo=TR)
    assert app._last_bar_unsettled("X", df, cb_skip=True, now_tr=now) is True
    # aynı seri seans içinde (10:00) beklenen 22.09'a uyar
    assert app._last_bar_unsettled("X", df, cb_skip=True,
                                    now_tr=datetime(2026, 9, 23, 10, 0, tzinfo=TR)) is False


def test_zero_change_with_different_1m_price_is_unsettled(monkeypatch):
    df = _df([("2026-09-22", 1, 2, 1, 91.15, 1), ("2026-09-23", 1, 2, 1, 91.15, 1)])
    idx = pd.date_range("2026-09-23 10:00", periods=40, freq="1min", tz="Europe/Istanbul")
    m = pd.DataFrame({"Open": 91.1, "High": 91.2, "Low": 91.0, "Close": 91.10, "Volume": 10}, index=idx)
    monkeypatch.setattr(app, "_fetch_intraday_subprocess", lambda t: m)
    now = datetime(2026, 9, 23, 18, 15, tzinfo=TR)
    assert app._last_bar_unsettled("SAHOL", df, now_tr=now) is True
    m2 = m.assign(Close=91.15)
    monkeypatch.setattr(app, "_fetch_intraday_subprocess", lambda t: m2)
    assert app._last_bar_unsettled("SAHOL", df, now_tr=now) is False


def test_unsettled_reason_string_is_canonical():
    assert app._STALE_REASON_UNSETTLED == "son seans verisi gelmedi"
