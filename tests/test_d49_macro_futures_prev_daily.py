"""D-49: vadeli (=F) makro sembollerde değişim günlük barın önceki kapanışından
(fast_info.previous_close Brent -1,3 / gümüş +0,24 gibi yanlış seans değeri veriyordu)."""
import json
import subprocess
import unittest.mock as mock

import pandas as pd

import yf_macro_fetch


def _proc(payload):
    return subprocess.CompletedProcess(args=[], returncode=0, stdout=json.dumps(payload), stderr="")


def test_fetch_daily_prev_uses_second_last_bar():
    fi = type("FI", (), {"last_price": 104.32, "previous_close": 105.69, "regularMarketPrice": 104.32})()
    hist = pd.DataFrame({"Close": [103.08, 106.6, 104.32]})
    tk = type("T", (), {"fast_info": fi, "history": lambda self, **kw: hist})()
    with mock.patch("yfinance.Ticker", return_value=tk):
        r = yf_macro_fetch.fetch("BZ=F", daily_prev=True)
        r0 = yf_macro_fetch.fetch("BZ=F")
    assert r["prev_daily"] == 106.6
    assert "prev_daily" not in r0


def test_macro_one_futures_change_from_daily_bar(app_module):
    app = app_module
    app._MACRO_PREV_DAILY.clear()
    out = {"sym": "BZ=F", "price": 104.32, "prev_close": 105.69, "prev_daily": 106.6}
    with mock.patch.object(app, "_yahoo_cb_blocked", return_value=False), \
         mock.patch.object(app.subprocess, "run", return_value=_proc(out)) as run:
        r = app._fetch_macro_one_subprocess("PETROL", "BZ=F")
        assert run.call_args[0][0][-1] == "daily"          # ilk çağrı günlük barı ister
        assert r["change"] == -2.14                        # 104.32/106.6-1
        out2 = {"sym": "BZ=F", "price": 104.32, "prev_close": 105.69}
        run.return_value = _proc(out2)
        r2 = app._fetch_macro_one_subprocess("PETROL", "BZ=F")
        assert run.call_args[0][0][-1] == "BZ=F"           # TTL içinde ek Yahoo çağrısı yok
        assert r2["change"] == -2.14
    app._MACRO_PREV_DAILY.clear()


def test_macro_one_non_futures_unchanged(app_module):
    app = app_module
    app._MACRO_PREV_DAILY.clear()
    out = {"sym": "USDTRY=X", "price": 48.92, "prev_close": 48.878}
    with mock.patch.object(app, "_yahoo_cb_blocked", return_value=False), \
         mock.patch.object(app.subprocess, "run", return_value=_proc(out)) as run:
        r = app._fetch_macro_one_subprocess("USDTRY", "USDTRY=X")
    assert run.call_args[0][0][-1] == "USDTRY=X"
    assert r["change"] == round((48.92 - 48.878) / 48.878 * 100, 2)


def test_macro_one_bist_index_uses_daily_bar(app_module):
    app = app_module
    app._MACRO_PREV_DAILY.clear()
    out = {"sym": "XU100.IS", "price": 12899.4, "prev_close": 12892.79, "prev_daily": 12888.3}
    with mock.patch.object(app, "_yahoo_cb_blocked", return_value=False), \
         mock.patch.object(app.subprocess, "run", return_value=_proc(out)) as run:
        r = app._fetch_macro_one_subprocess("XU100", "XU100.IS")
    assert run.call_args[0][0][-1] == "daily"
    assert r["change"] == 0.09          # /api/data xu100_change_pct ile ayni taban
    app._MACRO_PREV_DAILY.clear()
