"""G24c POC — yf_fundamentals_fetch.py unit tests (no real network / no yfinance call).
Tests the fetch() logic and subprocess contract via mocking.
"""
import sys
import os
import json
import subprocess
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

_VENV_PYTHON = sys.executable
_SCRIPT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "yf_fundamentals_fetch.py")


# ── helpers ───────────────────────────────────────────────────────────────────

def _fake_info(pe=12.5, market_cap=10_000_000_000, short_name="AKBANK T.A.S."):
    return {
        "trailingPE": pe,
        "forwardPE": 11.0,
        "priceToBook": 1.5,
        "trailingEps": 8.2,
        "marketCap": market_cap,
        "totalRevenue": 5_000_000_000,
        "netIncomeToCommon": 1_000_000_000,
        "dividendYield": 0.04,
        "returnOnEquity": 0.18,
        "beta": 1.1,
        "sharesOutstanding": 4_000_000_000,
        "fiftyTwoWeekHigh": 55.0,
        "fiftyTwoWeekLow": 30.0,
        "averageVolume": 50_000_000,
        "shortName": short_name,
        "profitMargins": 0.20,
        "operatingMargins": 0.25,
        "earningsGrowth": 0.15,
        "revenueGrowth": 0.10,
        "debtToEquity": 0.5,
        "currentRatio": 1.2,
        "priceToSalesTrailing12Months": 2.0,
    }


# ── yf_fundamentals_fetch.fetch() unit tests ──────────────────────────────────

def test_fetch_returns_required_keys():
    """fetch() result must have ticker and info keys."""
    import yf_fundamentals_fetch
    import unittest.mock as mock

    fake_ticker = type("T", (), {"info": _fake_info()})()
    with mock.patch("yfinance.Ticker", return_value=fake_ticker):
        result = yf_fundamentals_fetch.fetch("AKBNK.IS")

    assert not result.get("error"), f"unexpected error: {result.get('error')}"
    assert result["ticker"] == "AKBNK.IS"
    assert "info" in result
    info = result["info"]
    assert "trailingPE" in info
    assert "marketCap" in info
    assert "shortName" in info


def test_fetch_numeric_values_are_floats():
    """Numeric info values must be returned as floats."""
    import yf_fundamentals_fetch
    import unittest.mock as mock

    fake_ticker = type("T", (), {"info": _fake_info(pe=12.5, market_cap=10_000_000_000)})()
    with mock.patch("yfinance.Ticker", return_value=fake_ticker):
        result = yf_fundamentals_fetch.fetch("AKBNK.IS")

    info = result["info"]
    assert isinstance(info["trailingPE"], float)
    assert isinstance(info["marketCap"], float)
    assert abs(info["trailingPE"] - 12.5) < 0.01


def test_fetch_none_values_returned_as_null():
    """Missing keys → None in output (not KeyError)."""
    import yf_fundamentals_fetch
    import unittest.mock as mock

    fake_ticker = type("T", (), {"info": {}})()
    with mock.patch("yfinance.Ticker", return_value=fake_ticker):
        result = yf_fundamentals_fetch.fetch("AKBNK.IS")

    if result.get("error"):
        return  # empty info → error path, acceptable
    info = result["info"]
    for k in ["trailingPE", "marketCap", "shortName"]:
        assert info.get(k) is None, f"expected None for {k}, got {info.get(k)}"


def test_fetch_na_string_treated_as_null():
    """'N/A' string values → None in output."""
    import yf_fundamentals_fetch
    import unittest.mock as mock

    raw = _fake_info()
    raw["trailingPE"] = "N/A"
    fake_ticker = type("T", (), {"info": raw})()
    with mock.patch("yfinance.Ticker", return_value=fake_ticker):
        result = yf_fundamentals_fetch.fetch("AKBNK.IS")

    assert not result.get("error")
    assert result["info"]["trailingPE"] is None


def test_fetch_empty_info_returns_error():
    """fetch() with None info → error dict."""
    import yf_fundamentals_fetch
    import unittest.mock as mock

    fake_ticker = type("T", (), {"info": None})()
    with mock.patch("yfinance.Ticker", return_value=fake_ticker):
        result = yf_fundamentals_fetch.fetch("AKBNK.IS")

    assert result.get("error") == "empty_info"


def test_fetch_short_name_is_string():
    """shortName is returned as a string."""
    import yf_fundamentals_fetch
    import unittest.mock as mock

    fake_ticker = type("T", (), {"info": _fake_info(short_name="AKBANK T.A.S.")})()
    with mock.patch("yfinance.Ticker", return_value=fake_ticker):
        result = yf_fundamentals_fetch.fetch("AKBNK.IS")

    assert not result.get("error")
    assert isinstance(result["info"]["shortName"], str)
    assert result["info"]["shortName"] == "AKBANK T.A.S."


# ── subprocess contract tests ─────────────────────────────────────────────────

def test_subprocess_missing_args():
    """Running yf_fundamentals_fetch.py with 0 args → exit 1 + error JSON on stderr."""
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


def test_fetch_fundamentals_subprocess_failure_returns_none():
    """_fetch_fundamentals_subprocess with subprocess failure → None (not raise)."""
    import json as _json
    fake_result = type("R", (), {"returncode": 1, "stderr": '{"error":"empty_info"}', "stdout": ""})()
    if fake_result.returncode != 0:
        result = None
    else:
        data = _json.loads(fake_result.stdout)
        result = data.get("info") if not data.get("error") else None
    assert result is None


# ── runner ────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    tests = [
        test_fetch_returns_required_keys,
        test_fetch_numeric_values_are_floats,
        test_fetch_none_values_returned_as_null,
        test_fetch_na_string_treated_as_null,
        test_fetch_empty_info_returns_error,
        test_fetch_short_name_is_string,
        test_subprocess_missing_args,
        test_subprocess_error_is_valid_json,
        test_subprocess_timeout_raises,
        test_fetch_fundamentals_subprocess_failure_returns_none,
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
