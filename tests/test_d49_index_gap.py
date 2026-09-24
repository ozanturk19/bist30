"""D-49 — endeks/makro doğruluğu: eksik günlük bar (Yahoo XU100.IS 22.09) yanlış
değişim üretmez; ara boşluk 1m'den dolar; petrol sembolü Brent.
"""
import os
import re
from datetime import date, timedelta

import pandas as pd

_APP_PY = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "app.py")


def _extract(name):
    src = open(_APP_PY, encoding="utf-8").read()
    m = re.search(rf"^def {name}\(.*?(?=^def |^@app\.|\Z)", src, re.DOTALL | re.MULTILINE)
    assert m, name
    return m.group(0)


class _Lock:
    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


class _Log:
    def warning(self, *a, **k):
        pass

    info = warning


def _trading(d=None):
    return d.weekday() < 5


def _last_trading_day_on_or_before(d):
    while not _trading(d):
        d -= timedelta(days=1)
    return d


def _level(ohlc):
    ns = {
        "_lock": _Lock(),
        "_load_xu100_chart_from_disk": lambda: None,
        "_xu100_chart_cache": {"data": {"ohlc": ohlc}},
        "date": date, "timedelta": timedelta, "logger": _Log(),
        "last_trading_day_on_or_before": _last_trading_day_on_or_before,
    }
    exec(_extract("_get_xu100_level"), ns)
    return ns["_get_xu100_level"]()


def test_change_none_when_previous_bar_is_not_previous_trading_day():
    # 22.09 barı yok: 23.09'un değişimi 21.09'a göre hesaplanmamalı
    lvl = _level([
        {"time": "2026-09-21", "close": 13337.7},
        {"time": "2026-09-23", "close": 13251.9},
    ])
    assert lvl["close"] == 13251.9
    assert lvl["change_pct"] is None


def test_change_present_when_bars_consecutive():
    lvl = _level([
        {"time": "2026-09-22", "close": 13220.49},
        {"time": "2026-09-23", "close": 13251.9},
    ])
    assert lvl["change_pct"] == round((13251.9 - 13220.49) / 13220.49 * 100, 2)


def test_change_across_weekend_ok():
    lvl = _level([
        {"time": "2026-09-18", "close": 100.0},
        {"time": "2026-09-21", "close": 101.0},
    ])
    assert lvl["change_pct"] == 1.0


def _fill(df, df5d):
    ns = {
        "pd": pd, "logger": _Log(), "is_trading_day": _trading,
        "_fetch_intraday_subprocess": lambda base: df5d,
    }
    exec(_extract("_fill_intraday_gaps"), ns)
    return ns["_fill_intraday_gaps"](df, "XU100.IS")


def _daily(days_closes):
    idx = pd.DatetimeIndex([pd.Timestamp(d, tz="Europe/Istanbul") for d, _ in days_closes])
    c = [x for _, x in days_closes]
    return pd.DataFrame({"Open": c, "High": c, "Low": c, "Close": c, "Volume": [0.0] * len(c)}, index=idx)


def _intraday(day, last_close, n=40):
    idx = pd.date_range(f"{day} 10:00", periods=n, freq="1min", tz="Europe/Istanbul")
    c = [last_close - (n - 1 - i) * 0.1 for i in range(n)]
    return pd.DataFrame({"Open": c, "High": c, "Low": c, "Close": c, "Volume": [1.0] * n}, index=idx)


def test_fill_interior_gap_from_intraday():
    df = _daily([("2026-09-21", 13337.7), ("2026-09-23", 13251.9)])
    df5d = pd.concat([_intraday("2026-09-21", 13312.4), _intraday("2026-09-22", 13220.49), _intraday("2026-09-23", 13252.5)])
    out = _fill(df, df5d)
    days = [str(i.date()) for i in out.index]
    assert days == ["2026-09-21", "2026-09-22", "2026-09-23"]
    assert abs(out["Close"].iloc[1] - 13220.49) < 1e-6
    # mevcut günlük barlar (21.09, 23.09) 1m ile ezilmez
    assert out["Close"].iloc[0] == 13337.7 and out["Close"].iloc[2] == 13251.9


def test_fill_interior_gap_scale_guard():
    df = _daily([("2026-09-21", 13337.7), ("2026-09-23", 13251.9)])
    out = _fill(df, _intraday("2026-09-22", 1000.0))
    assert len(out) == 2


def test_fill_no_change_when_no_gap():
    df = _daily([("2026-09-22", 13220.0), ("2026-09-23", 13251.9)])
    out = _fill(df, _intraday("2026-09-23", 13252.5))
    assert len(out) == 2


def test_petrol_is_brent():
    src = open(_APP_PY, encoding="utf-8").read()
    assert '("PETROL", "BZ=F")' in src
    assert '"PETROL":   "BZ=F"' in src
    assert "Ham Petrol (WTI)" not in src
