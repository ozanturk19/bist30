"""Görev 12b — yf_fetch.py HTTP retry logic birim testleri (CPO-740).
Doğrular:
  - fetch_with_retry() tanımlı
  - Başarılı ilk deneme → direkt döner (retry gecikme yok)
  - İlk denemede error dict → 1 retry
  - İlk denemede exception → 1 retry
  - İkinci deneme de başarısız → son hata döner, exit 1
  - max_attempts parametresi çalışıyor
  - main() artık fetch_with_retry() çağırıyor
"""
import sys
import os
import json
import subprocess
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

_VENV_PYTHON = sys.executable
_SCRIPT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "yf_fetch.py")


# ── fetch_with_retry() birim testleri ────────────────────────────────────────

def test_fetch_with_retry_defined():
    """fetch_with_retry fonksiyonu yf_fetch'te tanımlı olmalı."""
    import yf_fetch
    assert hasattr(yf_fetch, "fetch_with_retry"), "fetch_with_retry tanımsız"


def test_retry_success_on_first_attempt():
    """İlk denemede başarılı → hemen döner, 2. deneme olmaz."""
    import yf_fetch
    import unittest.mock as mock

    call_count = [0]
    def mock_fetch(ticker, period, interval):
        call_count[0] += 1
        return {"ticker": ticker, "rows": 5, "columns": ["Close"], "index": [], "data": {}}

    with mock.patch.object(yf_fetch, "fetch", side_effect=mock_fetch):
        result = yf_fetch.fetch_with_retry("AKBNK", "2y", "1d", retry_delay=0)

    assert call_count[0] == 1, f"1 attempt bekleniyor, {call_count[0]} oldu"
    assert not result.get("error"), f"Hata dönmemeli: {result}"


def test_retry_on_error_dict():
    """İlk denemede error dict → 1 retry daha."""
    import yf_fetch
    import unittest.mock as mock

    call_count = [0]
    def mock_fetch(ticker, period, interval):
        call_count[0] += 1
        if call_count[0] == 1:
            return {"error": "empty", "ticker": ticker}
        return {"ticker": ticker, "rows": 5, "columns": [], "index": [], "data": {}}

    with mock.patch.object(yf_fetch, "fetch", side_effect=mock_fetch):
        result = yf_fetch.fetch_with_retry("AKBNK", "2y", "1d", retry_delay=0)

    assert call_count[0] == 2, f"2 attempt bekleniyor (1 fail + 1 retry), {call_count[0]} oldu"
    assert not result.get("error"), f"2. deneme başarılı olmalı: {result}"


def test_retry_on_exception():
    """İlk denemede exception → 1 retry."""
    import yf_fetch
    import unittest.mock as mock

    call_count = [0]
    def mock_fetch(ticker, period, interval):
        call_count[0] += 1
        if call_count[0] == 1:
            raise ConnectionError("network jitter")
        return {"ticker": ticker, "rows": 10, "columns": [], "index": [], "data": {}}

    with mock.patch.object(yf_fetch, "fetch", side_effect=mock_fetch):
        result = yf_fetch.fetch_with_retry("AKBNK", "2y", "1d", retry_delay=0)

    assert call_count[0] == 2, f"2 attempt bekleniyor, {call_count[0]} oldu"
    assert not result.get("error"), f"2. deneme başarılı olmalı: {result}"


def test_retry_both_fail_returns_last_error():
    """Her iki deneme de başarısız → son error dict döner."""
    import yf_fetch
    import unittest.mock as mock

    def mock_fetch(ticker, period, interval):
        return {"error": "empty", "ticker": ticker}

    with mock.patch.object(yf_fetch, "fetch", side_effect=mock_fetch):
        result = yf_fetch.fetch_with_retry("AKBNK", "2y", "1d", max_attempts=2, retry_delay=0)

    assert result.get("error"), "Her iki deneme başarısız → error döner"


def test_retry_exception_both_fail():
    """Her iki denemede exception → son hata dict döner."""
    import yf_fetch
    import unittest.mock as mock

    def mock_fetch(ticker, period, interval):
        raise RuntimeError("persistent network error")

    with mock.patch.object(yf_fetch, "fetch", side_effect=mock_fetch):
        result = yf_fetch.fetch_with_retry("AKBNK", "2y", "1d", max_attempts=2, retry_delay=0)

    assert result.get("error"), "Exception → error dict döner"
    assert "ticker" in result, "Error dict ticker içermeli"


def test_retry_max_attempts_1_no_retry():
    """max_attempts=1 → retry yok, ilk hata direkt döner."""
    import yf_fetch
    import unittest.mock as mock

    call_count = [0]
    def mock_fetch(ticker, period, interval):
        call_count[0] += 1
        return {"error": "empty", "ticker": ticker}

    with mock.patch.object(yf_fetch, "fetch", side_effect=mock_fetch):
        result = yf_fetch.fetch_with_retry("AKBNK", "2y", "1d", max_attempts=1, retry_delay=0)

    assert call_count[0] == 1, f"max_attempts=1 → sadece 1 deneme, {call_count[0]} oldu"
    assert result.get("error"), "Başarısız fetch error döner"


def test_retry_no_delay_on_success():
    """Başarılı ilk deneme → retry_delay kadar bekleme olmaz."""
    import yf_fetch
    import unittest.mock as mock

    def mock_fetch(ticker, period, interval):
        return {"ticker": ticker, "rows": 1, "columns": [], "index": [], "data": {}}

    t0 = time.monotonic()
    with mock.patch.object(yf_fetch, "fetch", side_effect=mock_fetch):
        yf_fetch.fetch_with_retry("AKBNK", "2y", "1d", retry_delay=1.0)
    elapsed = time.monotonic() - t0

    assert elapsed < 0.5, f"Başarılı fetch 1s beklememeli, {elapsed:.2f}s geçti"


def test_retry_delay_on_failure():
    """İlk denemede hata → retry_delay kadar bekler."""
    import yf_fetch
    import unittest.mock as mock

    call_count = [0]
    def mock_fetch(ticker, period, interval):
        call_count[0] += 1
        if call_count[0] == 1:
            return {"error": "empty", "ticker": ticker}
        return {"ticker": ticker, "rows": 1, "columns": [], "index": [], "data": {}}

    t0 = time.monotonic()
    with mock.patch.object(yf_fetch, "fetch", side_effect=mock_fetch):
        yf_fetch.fetch_with_retry("AKBNK", "2y", "1d", retry_delay=0.1)
    elapsed = time.monotonic() - t0

    assert elapsed >= 0.1, f"Retry delay (0.1s) uygulanmadı, {elapsed:.3f}s geçti"


# ── main() retry kullanım kontrolü ───────────────────────────────────────────

def test_main_uses_fetch_with_retry():
    """yf_fetch.py main() fetch_with_retry() çağırıyor olmalı."""
    import re
    yf_fetch_path = _SCRIPT
    with open(yf_fetch_path, encoding="utf-8") as f:
        src = f.read()
    main_body = re.search(r"def main\(.*?\Z", src, re.DOTALL)
    assert main_body, "main() bulunamadı"
    assert "fetch_with_retry" in main_body.group(0), "main() fetch_with_retry çağırmıyor"


# ── subprocess kontrat (main → retry) ────────────────────────────────────────

def test_subprocess_contract_unchanged():
    """Retry eklenmesi subprocess kontratını bozmamalı: eksik args → exit 1 + JSON."""
    result = subprocess.run(
        [_VENV_PYTHON, _SCRIPT],
        capture_output=True, text=True, timeout=5,
    )
    assert result.returncode == 1, "Argümansız exit 1 bekleniyor"
    err = json.loads(result.stderr)
    assert "error" in err


# ── Runner ────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    tests = [
        test_fetch_with_retry_defined,
        test_retry_success_on_first_attempt,
        test_retry_on_error_dict,
        test_retry_on_exception,
        test_retry_both_fail_returns_last_error,
        test_retry_exception_both_fail,
        test_retry_max_attempts_1_no_retry,
        test_retry_no_delay_on_success,
        test_retry_delay_on_failure,
        test_main_uses_fetch_with_retry,
        test_subprocess_contract_unchanged,
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
    print(f"\n{'='*65}")
    print(f"Result: {passed}/{len(tests)} passed")
    if fail_names:
        print(f"FAILED: {', '.join(fail_names)}")
        raise SystemExit(1)
    print("ALL TESTS PASSED ✅")
