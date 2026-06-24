"""G24d POC — yf_live_fetch.py unit tests (no real network / no yfinance call).
Tests fetch_bist/fetch_global logic and subprocess contract via mocking.
G24e verification: _YF_GLOBAL_LOCK definition removed from app.py.
"""
import sys
import os
import json
import subprocess
import re

import pandas as pd
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

_VENV_PYTHON = sys.executable
_SCRIPT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "yf_live_fetch.py")
_APP_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "app.py")


# ── helpers ───────────────────────────────────────────────────────────────────

def _fake_multiticker_df(tickers, rows=120):
    """yf.download group_by='ticker' MultiIndex DataFrame simülasyonu.
    Level 0 = ticker, Level 1 = column (yfinance orijinal format).
    """
    today = pd.Timestamp.now().normalize()
    yesterday = today - pd.Timedelta(days=1)
    idx_y = pd.date_range(yesterday, periods=rows // 2, freq="1min")
    idx_t = pd.date_range(today, periods=rows - rows // 2, freq="1min")
    idx = idx_y.append(idx_t)

    arrays = [
        [t for t in tickers for _ in ["Close", "High", "Low", "Open", "Volume"]],
        [col for _ in tickers for col in ["Close", "High", "Low", "Open", "Volume"]],
    ]
    cols = pd.MultiIndex.from_arrays(arrays)
    data = np.random.uniform(10, 50, (len(idx), len(tickers) * 5))
    df = pd.DataFrame(data, index=idx, columns=cols)
    return df


def _fake_single_df(rows=120):
    today = pd.Timestamp.now().normalize()
    yesterday = today - pd.Timedelta(days=1)
    idx_y = pd.date_range(yesterday, periods=rows // 2, freq="1min")
    idx_t = pd.date_range(today, periods=rows - rows // 2, freq="1min")
    idx = idx_y.append(idx_t)
    return pd.DataFrame({
        "Close": np.random.uniform(10, 50, len(idx)),
        "High":  np.random.uniform(50, 60, len(idx)),
        "Low":   np.random.uniform(8, 10, len(idx)),
        "Open":  np.random.uniform(10, 50, len(idx)),
        "Volume": np.random.randint(1_000, 50_000, len(idx)).astype(float),
    }, index=idx)


# ── yf_live_fetch.fetch_bist() unit tests ────────────────────────────────────

def test_fetch_bist_returns_payload_structure():
    """fetch_bist() must return dict with 'mode' and 'payload' keys."""
    import yf_live_fetch
    import unittest.mock as mock

    syms = ["AKBNK.IS", "THYAO.IS", "GARAN.IS"]
    tickers_str = " ".join(syms)

    with mock.patch("yfinance.download") as mock_dl:
        mock_dl.return_value = _fake_multiticker_df(syms)
        result = yf_live_fetch.fetch_bist(tickers_str)

    assert not result.get("error"), f"unexpected error: {result.get('error')}"
    assert result.get("mode") == "bist"
    assert isinstance(result.get("payload"), dict)
    assert len(result["payload"]) > 0


def test_fetch_bist_strips_is_suffix():
    """fetch_bist() payload keys must not have .IS suffix."""
    import yf_live_fetch
    import unittest.mock as mock

    syms = ["AKBNK.IS", "THYAO.IS"]
    with mock.patch("yfinance.download") as mock_dl:
        mock_dl.return_value = _fake_multiticker_df(syms)
        result = yf_live_fetch.fetch_bist(" ".join(syms))

    assert not result.get("error")
    for key in result["payload"]:
        assert not key.endswith(".IS"), f"Key {key!r} still has .IS suffix"


def test_fetch_bist_payload_has_price_and_change():
    """Each ticker in fetch_bist() payload must have price and change_pct."""
    import yf_live_fetch
    import unittest.mock as mock

    syms = ["AKBNK.IS", "THYAO.IS"]
    with mock.patch("yfinance.download") as mock_dl:
        mock_dl.return_value = _fake_multiticker_df(syms)
        result = yf_live_fetch.fetch_bist(" ".join(syms))

    assert not result.get("error")
    for ticker, entry in result["payload"].items():
        assert "price" in entry, f"{ticker} missing price"
        assert "change_pct" in entry, f"{ticker} missing change_pct"
        assert isinstance(entry["price"], float)
        assert isinstance(entry["change_pct"], float)


def test_fetch_bist_empty_df_returns_error():
    """Empty DataFrame → error dict, not crash."""
    import yf_live_fetch
    import unittest.mock as mock

    with mock.patch("yfinance.download") as mock_dl:
        mock_dl.return_value = pd.DataFrame()
        result = yf_live_fetch.fetch_bist("AKBNK.IS THYAO.IS")

    assert result.get("error") == "empty_df"


def test_fetch_global_returns_payload_structure():
    """fetch_global() must return dict with 'mode' and 'payload' keys."""
    import yf_live_fetch
    import unittest.mock as mock

    syms = ["BTC-USD", "GC=F"]
    with mock.patch("yfinance.download") as mock_dl:
        mock_dl.return_value = _fake_multiticker_df(syms)
        result = yf_live_fetch.fetch_global(json.dumps(syms))

    assert not result.get("error"), f"unexpected error: {result.get('error')}"
    assert result.get("mode") == "global"
    assert isinstance(result.get("payload"), dict)


def test_fetch_global_preserves_yf_sym_as_key():
    """fetch_global() payload keys must be original yf symbols (no stripping)."""
    import yf_live_fetch
    import unittest.mock as mock

    syms = ["BTC-USD", "GC=F"]
    with mock.patch("yfinance.download") as mock_dl:
        mock_dl.return_value = _fake_multiticker_df(syms)
        result = yf_live_fetch.fetch_global(json.dumps(syms))

    assert not result.get("error")
    for sym in syms:
        if sym in result["payload"]:
            assert "price" in result["payload"][sym]


# ── subprocess contract tests ─────────────────────────────────────────────────

def test_subprocess_missing_args_exits_1():
    """Running yf_live_fetch.py with 0 args → exit 1 + error JSON on stderr."""
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


def test_subprocess_unknown_mode_exits_1():
    """Unknown mode → exit 1."""
    result = subprocess.run(
        [_VENV_PYTHON, _SCRIPT, "invalid_mode", "[]"],
        capture_output=True, text=True, timeout=10,
    )
    assert result.returncode == 1
    err = json.loads(result.stderr)
    assert "error" in err


# ── G24d AST verification ─────────────────────────────────────────────────────

def test_fetch_live_prices_uses_subprocess():
    """fetch_live_prices() must call _fetch_live_subprocess, not _YF_GLOBAL_LOCK."""
    import ast

    with open(_APP_PATH, encoding="utf-8") as f:
        src = f.read()

    tree = ast.parse(src)
    func_src = None
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == "fetch_live_prices":
            lines = src.splitlines()
            func_src = "\n".join(lines[node.lineno - 1: node.end_lineno])
            break

    assert func_src is not None, "fetch_live_prices not found in app.py"
    assert "_fetch_live_subprocess" in func_src, \
        "fetch_live_prices() must call _fetch_live_subprocess (G24d)"
    assert "_YF_GLOBAL_LOCK" not in func_src, \
        "_YF_GLOBAL_LOCK must not be used in fetch_live_prices() after G24d"


def test_fetch_global_prices_uses_subprocess():
    """fetch_global_prices() must call _fetch_global_subprocess, not _YF_GLOBAL_LOCK."""
    import ast

    with open(_APP_PATH, encoding="utf-8") as f:
        src = f.read()

    tree = ast.parse(src)
    func_src = None
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == "fetch_global_prices":
            lines = src.splitlines()
            func_src = "\n".join(lines[node.lineno - 1: node.end_lineno])
            break

    assert func_src is not None, "fetch_global_prices not found in app.py"
    assert "_fetch_global_subprocess" in func_src, \
        "fetch_global_prices() must call _fetch_global_subprocess (G24d)"
    assert "_YF_GLOBAL_LOCK" not in func_src, \
        "_YF_GLOBAL_LOCK must not be used in fetch_global_prices() after G24d"


# ── G24e AST verification ─────────────────────────────────────────────────────

def test_yf_global_lock_definition_removed():
    """_YF_GLOBAL_LOCK = threading.Lock() must not exist in app.py after G24e."""
    with open(_APP_PATH, encoding="utf-8") as f:
        src = f.read()
    assert not re.search(r"_YF_GLOBAL_LOCK\s*=\s*threading\.Lock\(\)", src), \
        "_YF_GLOBAL_LOCK definition still present in app.py (G24e not done)"


# ── runner ────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    tests = [
        test_fetch_bist_returns_payload_structure,
        test_fetch_bist_strips_is_suffix,
        test_fetch_bist_payload_has_price_and_change,
        test_fetch_bist_empty_df_returns_error,
        test_fetch_global_returns_payload_structure,
        test_fetch_global_preserves_yf_sym_as_key,
        test_subprocess_missing_args_exits_1,
        test_subprocess_error_is_valid_json,
        test_subprocess_unknown_mode_exits_1,
        test_fetch_live_prices_uses_subprocess,
        test_fetch_global_prices_uses_subprocess,
        test_yf_global_lock_definition_removed,
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
