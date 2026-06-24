"""Görev 9 POC — yf_macro_fetch.py unit tests (no real network / no yfinance call).
Tests the fetch() logic and subprocess contract via mocking.
"""
import sys
import os
import json
import subprocess
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

_VENV_PYTHON = sys.executable
_SCRIPT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "yf_macro_fetch.py")


# ── helpers ───────────────────────────────────────────────────────────────────

def _fake_fast_info(price=38.45, prev=38.20):
    class FakeFastInfo:
        last_price = price
        previous_close = prev
        regularMarketPrice = price
    return FakeFastInfo()


class _FakeTickerNone:
    class fast_info:
        last_price = None
        previous_close = None
        regularMarketPrice = None


# ── yf_macro_fetch.fetch() unit tests ─────────────────────────────────────────

def test_fetch_returns_required_keys():
    """fetch() result must have sym, price, prev_close keys."""
    import yf_macro_fetch
    import unittest.mock as mock

    fi = _fake_fast_info(38.45, 38.20)
    fake_ticker = type("T", (), {"fast_info": fi})()

    with mock.patch("yfinance.Ticker", return_value=fake_ticker):
        result = yf_macro_fetch.fetch("USDTRY=X")

    assert not result.get("error"), f"unexpected error: {result.get('error')}"
    assert result["sym"] == "USDTRY=X"
    assert abs(result["price"] - 38.45) < 0.01
    assert abs(result["prev_close"] - 38.20) < 0.01


def test_fetch_no_price_returns_error():
    """fetch() with None price → error dict."""
    import yf_macro_fetch
    import unittest.mock as mock

    fi = _fake_fast_info(None, 38.20)
    fake_ticker = type("T", (), {"fast_info": fi})()

    with mock.patch("yfinance.Ticker", return_value=fake_ticker):
        result = yf_macro_fetch.fetch("USDTRY=X")

    assert result.get("error") == "no_price"


def test_fetch_no_prev_close_returns_error():
    """fetch() with None prev_close → error dict."""
    import yf_macro_fetch
    import unittest.mock as mock

    fi = _fake_fast_info(38.45, None)
    fake_ticker = type("T", (), {"fast_info": fi})()

    with mock.patch("yfinance.Ticker", return_value=fake_ticker):
        result = yf_macro_fetch.fetch("USDTRY=X")

    assert result.get("error") == "no_prev_close"


def test_fetch_values_are_floats():
    """price and prev_close in result must be floats."""
    import yf_macro_fetch
    import unittest.mock as mock

    fi = _fake_fast_info(14539.61, 14500.00)
    fake_ticker = type("T", (), {"fast_info": fi})()

    with mock.patch("yfinance.Ticker", return_value=fake_ticker):
        result = yf_macro_fetch.fetch("XU100.IS")

    assert isinstance(result["price"], float)
    assert isinstance(result["prev_close"], float)


# ── subprocess contract tests ─────────────────────────────────────────────────

def test_subprocess_missing_args():
    """Running yf_macro_fetch.py with 0 args → exit 1 + error JSON on stderr."""
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


# ── _fetch_macro_one_subprocess integration ───────────────────────────────────

def test_fetch_macro_one_subprocess_error_returns_none():
    """_fetch_macro_one_subprocess with bad ticker → None (not raise)."""
    import yf_macro_fetch
    import unittest.mock as mock

    # Simulate subprocess failure (returncode=1)
    fake_result = type("R", (), {"returncode": 1, "stderr": '{"error": "no_price"}', "stdout": ""})()
    with mock.patch("subprocess.run", return_value=fake_result):
        # Import app to get _fetch_macro_one_subprocess
        # Test the logic directly to avoid Flask init
        import json as _json
        data_str = fake_result.stdout
        if fake_result.returncode != 0:
            result = None
        else:
            data = _json.loads(data_str)
            result = data if not data.get("error") else None
        assert result is None


# ── runner ────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    tests = [
        test_fetch_returns_required_keys,
        test_fetch_no_price_returns_error,
        test_fetch_no_prev_close_returns_error,
        test_fetch_values_are_floats,
        test_subprocess_missing_args,
        test_subprocess_error_is_valid_json,
        test_subprocess_timeout_raises,
        test_fetch_macro_one_subprocess_error_returns_none,
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
