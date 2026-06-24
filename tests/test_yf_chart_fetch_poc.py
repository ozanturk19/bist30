"""G24b POC — yf_chart_fetch.py unit tests (no real network / no yfinance call).
Tests the fetch() logic, Volume inclusion, and subprocess contract via mocking.
"""
import sys
import os
import json
import subprocess
import tempfile

import pandas as pd
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

_VENV_PYTHON = sys.executable
_SCRIPT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "yf_chart_fetch.py")


# ── helpers ───────────────────────────────────────────────────────────────────

def _fake_df(rows=300, include_volume=True):
    idx = pd.date_range("2023-01-01", periods=rows, freq="B")
    data = {
        "Open":  np.random.uniform(10, 20, rows),
        "High":  np.random.uniform(20, 25, rows),
        "Low":   np.random.uniform(8,  12, rows),
        "Close": np.random.uniform(10, 22, rows),
    }
    if include_volume:
        data["Volume"] = np.random.randint(1_000_000, 50_000_000, rows).astype(float)
    return pd.DataFrame(data, index=idx)


# ── yf_chart_fetch.fetch() unit tests ────────────────────────────────────────

def test_fetch_returns_required_keys():
    """fetch() result must have ticker, rows, columns, index, data keys."""
    import yf_chart_fetch
    import unittest.mock as mock

    with mock.patch("yfinance.Ticker") as MockTicker:
        MockTicker.return_value.history.return_value = _fake_df()
        result = yf_chart_fetch.fetch("THYAO.IS", "2y")

    assert not result.get("error"), f"unexpected error: {result.get('error')}"
    assert result["ticker"] == "THYAO.IS"
    assert result["rows"] > 0
    assert "columns" in result
    assert "index" in result
    assert "data" in result


def test_fetch_includes_volume():
    """fetch() must include Volume column when available in DataFrame."""
    import yf_chart_fetch
    import unittest.mock as mock

    with mock.patch("yfinance.Ticker") as MockTicker:
        MockTicker.return_value.history.return_value = _fake_df(include_volume=True)
        result = yf_chart_fetch.fetch("THYAO.IS", "2y")

    assert not result.get("error")
    assert "Volume" in result["columns"]
    assert "Volume" in result["data"]
    assert len(result["data"]["Volume"]) > 0


def test_fetch_values_are_floats():
    """OHLC values in data must be floats (not strings or ints)."""
    import yf_chart_fetch
    import unittest.mock as mock

    with mock.patch("yfinance.Ticker") as MockTicker:
        MockTicker.return_value.history.return_value = _fake_df()
        result = yf_chart_fetch.fetch("AKBNK.IS", "2y")

    assert not result.get("error")
    for col in ["Open", "High", "Low", "Close"]:
        sample = [v for v in result["data"][col] if v is not None]
        assert len(sample) > 0
        assert isinstance(sample[0], float), f"{col} value not float: {type(sample[0])}"


def test_fetch_nan_becomes_null():
    """NaN values in DataFrame → None (JSON null) in output."""
    import yf_chart_fetch
    import unittest.mock as mock

    df = _fake_df(rows=200)
    df.iloc[5, df.columns.get_loc("Close")] = float("nan")
    with mock.patch("yfinance.Ticker") as MockTicker:
        MockTicker.return_value.history.return_value = df
        result = yf_chart_fetch.fetch("GARAN.IS", "2y")

    assert not result.get("error")
    close_vals = result["data"]["Close"]
    assert None in close_vals, "NaN was not converted to None"


def test_fetch_empty_dataframe_returns_error():
    """Empty DataFrame from yfinance → error dict (not crash)."""
    import yf_chart_fetch
    import unittest.mock as mock

    with mock.patch("yfinance.Ticker") as MockTicker:
        MockTicker.return_value.history.return_value = pd.DataFrame()
        result = yf_chart_fetch.fetch("UNKNOWN.IS", "2y")

    assert result.get("error") == "empty"


def test_fetch_index_is_string_list():
    """index field must be a list of strings (ISO date format)."""
    import yf_chart_fetch
    import unittest.mock as mock

    with mock.patch("yfinance.Ticker") as MockTicker:
        MockTicker.return_value.history.return_value = _fake_df(rows=100)
        result = yf_chart_fetch.fetch("EREGL.IS", "1y")

    assert not result.get("error")
    assert isinstance(result["index"], list)
    assert len(result["index"]) == result["rows"]
    assert isinstance(result["index"][0], str)


# ── subprocess contract tests ─────────────────────────────────────────────────

def test_subprocess_missing_args_exits_1():
    """Running yf_chart_fetch.py with 0 args → exit 1 + error JSON on stderr."""
    result = subprocess.run(
        [_VENV_PYTHON, _SCRIPT],
        capture_output=True, text=True, timeout=10,
    )
    assert result.returncode == 1
    err = json.loads(result.stderr)
    assert "error" in err


def test_subprocess_error_is_valid_json():
    """Error output must always be parseable JSON."""
    result = subprocess.run(
        [_VENV_PYTHON, _SCRIPT],
        capture_output=True, text=True, timeout=10,
    )
    err = json.loads(result.stderr)
    assert isinstance(err, dict)


def test_subprocess_timeout_raises():
    """subprocess.run(timeout=X) raises TimeoutExpired if script hangs."""
    sleepy = tempfile.NamedTemporaryFile(suffix=".py", mode="w", delete=False)
    sleepy.write("import time; time.sleep(10)\n")
    sleepy.close()
    try:
        raised = False
        try:
            subprocess.run(
                [_VENV_PYTHON, sleepy.name],
                capture_output=True, timeout=0.5,
            )
        except subprocess.TimeoutExpired:
            raised = True
        assert raised, "TimeoutExpired was NOT raised — subprocess timeout broken"
    finally:
        os.unlink(sleepy.name)


def test_compute_chart_calls_subprocess():
    """_compute_chart_data() source must use _fetch_chart_subprocess (G24b), not _YF_GLOBAL_LOCK."""
    import ast

    app_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "app.py")
    with open(app_path, encoding="utf-8") as f:
        src = f.read()

    tree = ast.parse(src)
    func_src = None
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == "_compute_chart_data":
            # extract lines for this function
            lines = src.splitlines()
            func_src = "\n".join(lines[node.lineno - 1: node.end_lineno])
            break

    assert func_src is not None, "_compute_chart_data not found in app.py"
    assert "_fetch_chart_subprocess" in func_src, "_compute_chart_data must call _fetch_chart_subprocess (G24b)"
    assert "_YF_GLOBAL_LOCK" not in func_src, "_YF_GLOBAL_LOCK must not be used in _compute_chart_data after G24b"


# ── runner ────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    tests = [
        test_fetch_returns_required_keys,
        test_fetch_includes_volume,
        test_fetch_values_are_floats,
        test_fetch_nan_becomes_null,
        test_fetch_empty_dataframe_returns_error,
        test_fetch_index_is_string_list,
        test_subprocess_missing_args_exits_1,
        test_subprocess_error_is_valid_json,
        test_subprocess_timeout_raises,
        test_compute_chart_calls_subprocess,
    ]
    passed = 0
    fail_names = []
    for t in tests:
        try:
            t()
            passed += 1
            print(f"  OK {t.__name__}")
        except Exception as e:
            fail_names.append(t.__name__)
            print(f"  FAIL {t.__name__}: {e}")
    print(f"\n{'='*60}")
    print(f"Result: {passed}/{len(tests)} passed")
    if fail_names:
        print(f"FAILED: {', '.join(fail_names)}")
        raise SystemExit(1)
    print("ALL TESTS PASSED")
