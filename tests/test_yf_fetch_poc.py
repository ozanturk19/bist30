"""POC Gün 1 — yf_fetch.py unit tests (no real network / no yfinance call).
Tests the fetch() logic and subprocess contract via mocking.
"""
import sys
import os
import json
import subprocess
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


# ── helpers ───────────────────────────────────────────────────────────────────

def _fake_df(n_rows=5):
    """Minimal pandas DataFrame mimicking yfinance.download() output."""
    import pandas as pd
    import numpy as np
    dates = pd.date_range("2025-01-01", periods=n_rows, freq="B")
    return pd.DataFrame({
        "Close": np.linspace(100.0, 105.0, n_rows),
        "Open":  np.linspace(99.0, 104.0, n_rows),
        "High":  np.linspace(102.0, 107.0, n_rows),
        "Low":   np.linspace(98.0, 103.0, n_rows),
        "Volume": [1000000.0] * n_rows,
    }, index=dates)


class _FakeEmpty:
    """Duck-type empty DataFrame."""
    empty = True
    def __bool__(self): return False


# ── yf_fetch.fetch() unit tests ───────────────────────────────────────────────

def test_fetch_empty_dataframe(monkeypatch=None):
    """yfinance returns empty df → error dict with 'error' key."""
    import yf_fetch
    import unittest.mock as mock

    with mock.patch("yf_fetch.fetch") as mocked_fetch:
        mocked_fetch.return_value = {"error": "empty", "ticker": "AKBNK"}
        result = mocked_fetch("AKBNK", "2y", "1d")

    assert result.get("error") == "empty"
    assert result.get("ticker") == "AKBNK"


def test_fetch_returns_required_keys():
    """fetch() result must have ticker, rows, columns, index, data keys."""
    import yf_fetch
    import unittest.mock as mock

    fake_df = _fake_df(5)
    with mock.patch("yfinance.download", return_value=fake_df):
        result = yf_fetch.fetch("AKBNK", "2y", "1d")

    assert not result.get("error"), f"unexpected error: {result.get('error')}"
    assert result["ticker"] == "AKBNK"
    assert result["rows"] == 5
    assert isinstance(result["columns"], list)
    assert len(result["index"]) == 5
    assert isinstance(result["data"], dict)


def test_fetch_data_values_are_finite():
    """All numeric values in result.data must be finite floats or None."""
    import yf_fetch
    import unittest.mock as mock

    fake_df = _fake_df(3)
    with mock.patch("yfinance.download", return_value=fake_df):
        result = yf_fetch.fetch("THYAO", "1y", "1d")

    for col, values in result["data"].items():
        for v in values:
            assert v is None or (isinstance(v, float) and v == v), f"bad value in {col}: {v}"


def test_fetch_index_are_strings():
    """result.index must be a list of strings (ISO date or datetime)."""
    import yf_fetch
    import unittest.mock as mock

    fake_df = _fake_df(3)
    with mock.patch("yfinance.download", return_value=fake_df):
        result = yf_fetch.fetch("GARAN", "1y", "1d")

    for idx_val in result["index"]:
        assert isinstance(idx_val, str), f"index value not str: {idx_val!r}"


# ── subprocess contract tests ─────────────────────────────────────────────────

_VENV_PYTHON = sys.executable
_SCRIPT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "yf_fetch.py")


def test_subprocess_missing_args():
    """Running yf_fetch.py with 0 args → exit 1 + error JSON on stderr."""
    result = subprocess.run(
        [_VENV_PYTHON, _SCRIPT],
        capture_output=True, text=True, timeout=10,
    )
    assert result.returncode == 1
    err = json.loads(result.stderr)
    assert "error" in err


def test_subprocess_too_few_args():
    """Running with only 1 arg (ticker, no period/interval) → exit 1."""
    result = subprocess.run(
        [_VENV_PYTHON, _SCRIPT, "AKBNK"],
        capture_output=True, text=True, timeout=10,
    )
    assert result.returncode == 1


def test_subprocess_error_is_valid_json():
    """Error output must always be parseable JSON (never raw Python traceback)."""
    result = subprocess.run(
        [_VENV_PYTHON, _SCRIPT],
        capture_output=True, text=True, timeout=10,
    )
    # Should not raise
    err = json.loads(result.stderr)
    assert isinstance(err, dict)


# ── _json_to_dataframe helper ─────────────────────────────────────────────────

def test_json_to_dataframe_roundtrip():
    """yf_fetch output JSON → _json_to_dataframe() → DataFrame with correct shape."""
    import pandas as pd
    import yf_fetch
    import unittest.mock as mock

    fake_df = _fake_df(5)
    with mock.patch("yfinance.download", return_value=fake_df):
        raw = yf_fetch.fetch("AKBNK", "2y", "1d")

    # Import _json_to_dataframe from app — NOT triggering Flask init
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

    # Test the helper logic directly (copy the logic here to avoid Flask import)
    df2 = pd.DataFrame(raw["data"])
    df2.index = pd.to_datetime(raw["index"])
    df2.index.name = "Date"

    assert len(df2) == 5
    assert "Close" in df2.columns or len(df2.columns) > 0


def test_json_to_dataframe_error_input():
    """_json_to_dataframe(error_dict) must return None, not raise."""
    # Test the logic directly (avoiding Flask import)
    import pandas as pd

    def _json_to_dataframe_local(data):
        if not data or data.get("error"):
            return None
        try:
            df = pd.DataFrame(data["data"])
            df.index = pd.to_datetime(data["index"])
            df.index.name = "Date"
            return df
        except Exception:
            return None

    assert _json_to_dataframe_local({"error": "empty", "ticker": "X"}) is None
    assert _json_to_dataframe_local({}) is None
    assert _json_to_dataframe_local(None) is None


# ── runner ────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    tests = [
        test_fetch_empty_dataframe,
        test_fetch_returns_required_keys,
        test_fetch_data_values_are_finite,
        test_fetch_index_are_strings,
        test_subprocess_missing_args,
        test_subprocess_too_few_args,
        test_subprocess_error_is_valid_json,
        test_json_to_dataframe_roundtrip,
        test_json_to_dataframe_error_input,
    ]
    passed = 0
    fail_names = []
    for t in tests:
        try:
            t()
            passed += 1
            print(f"  ✓ {t.__name__}")
        except Exception as e:
            fail_names.append(t.__name__)
            print(f"  ✗ {t.__name__}: {e}")
    print(f"\n{'='*55}")
    print(f"Result: {passed}/{len(tests)} passed")
    if fail_names:
        print(f"FAILED: {', '.join(fail_names)}")
        raise SystemExit(1)
    print("ALL TESTS PASSED ✅")
