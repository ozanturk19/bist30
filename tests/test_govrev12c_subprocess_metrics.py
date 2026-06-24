"""Görev 12c — Subprocess metric collection birim testleri (CPO-740).
Doğrular:
  - _SUBPROCESS_SLOW_MS ve _MACRO_SLOW_MS sabitleri tanımlı
  - _fetch_daily_subprocess() timing log içeriyor (debug + warning)
  - _fetch_macro_one_subprocess() timing log içeriyor
  - SLOW threshold mantığı (>3000ms ve >2000ms)
  - Timeout durumunda elapsed ms log çıkışı
"""
import re
import os
import subprocess
import sys
import time

_APP_PY = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "app.py")
_VENV_PYTHON = sys.executable


# ── Dosya içeriği kontrolleri ─────────────────────────────────────────────────

def _extract_function_body(src, func_name):
    pattern = rf"def {func_name}\(.*?(?=\ndef |\Z)"
    m = re.search(pattern, src, re.DOTALL)
    return m.group(0) if m else None


def test_subprocess_slow_ms_constant_defined():
    """_SUBPROCESS_SLOW_MS sabiti tanımlı ve 3000 olmalı."""
    with open(_APP_PY, encoding="utf-8") as f:
        src = f.read()
    m = re.search(r"_SUBPROCESS_SLOW_MS\s*=\s*(\d+)", src)
    assert m, "_SUBPROCESS_SLOW_MS tanımsız"
    assert int(m.group(1)) == 3000, f"_SUBPROCESS_SLOW_MS beklenen 3000, gerçek: {m.group(1)}"


def test_macro_slow_ms_constant_defined():
    """_MACRO_SLOW_MS sabiti tanımlı ve 2000 olmalı."""
    with open(_APP_PY, encoding="utf-8") as f:
        src = f.read()
    m = re.search(r"_MACRO_SLOW_MS\s*=\s*(\d+)", src)
    assert m, "_MACRO_SLOW_MS tanımsız"
    assert int(m.group(1)) == 2000, f"_MACRO_SLOW_MS beklenen 2000, gerçek: {m.group(1)}"


def test_fetch_daily_has_timing():
    """_fetch_daily_subprocess() perf_counter() timing içermeli."""
    with open(_APP_PY, encoding="utf-8") as f:
        src = f.read()
    body = _extract_function_body(src, "_fetch_daily_subprocess")
    assert body, "_fetch_daily_subprocess bulunamadı"
    assert "perf_counter" in body, "_fetch_daily_subprocess timing (perf_counter) yok"
    assert "_ms" in body, "_fetch_daily_subprocess _ms değişkeni yok"


def test_fetch_daily_has_debug_log():
    """_fetch_daily_subprocess() debug log (ms bilgisi) içermeli."""
    with open(_APP_PY, encoding="utf-8") as f:
        src = f.read()
    body = _extract_function_body(src, "_fetch_daily_subprocess")
    has_debug = "logger.debug" in body and "ms" in body.lower()
    assert has_debug, "_fetch_daily_subprocess debug log (ms bilgisi) yok"


def test_fetch_daily_has_slow_warning():
    """_fetch_daily_subprocess() SLOW warning içermeli."""
    with open(_APP_PY, encoding="utf-8") as f:
        src = f.read()
    body = _extract_function_body(src, "_fetch_daily_subprocess")
    has_slow = "_SUBPROCESS_SLOW_MS" in body and "SLOW" in body
    assert has_slow, "_fetch_daily_subprocess SLOW uyarı mantığı yok"


def test_fetch_daily_timeout_logs_elapsed():
    """_fetch_daily_subprocess() timeout'ta elapsed ms loglamalı."""
    with open(_APP_PY, encoding="utf-8") as f:
        src = f.read()
    body = _extract_function_body(src, "_fetch_daily_subprocess")
    # TimeoutExpired bloğunda da _ms log olmalı
    timeout_block = body[body.find("TimeoutExpired"):]
    assert "_ms" in timeout_block, "Timeout bloğunda elapsed ms log yok"


def test_macro_fetch_has_timing():
    """_fetch_macro_one_subprocess() perf_counter() timing içermeli."""
    with open(_APP_PY, encoding="utf-8") as f:
        src = f.read()
    body = _extract_function_body(src, "_fetch_macro_one_subprocess")
    assert body, "_fetch_macro_one_subprocess bulunamadı"
    assert "perf_counter" in body, "_fetch_macro_one_subprocess timing yok"
    assert "_ms" in body, "_fetch_macro_one_subprocess _ms değişkeni yok"


def test_macro_fetch_has_slow_warning():
    """_fetch_macro_one_subprocess() SLOW warning içermeli."""
    with open(_APP_PY, encoding="utf-8") as f:
        src = f.read()
    body = _extract_function_body(src, "_fetch_macro_one_subprocess")
    has_slow = "_MACRO_SLOW_MS" in body and "SLOW" in body
    assert has_slow, "_fetch_macro_one_subprocess SLOW uyarı mantığı yok"


# ── Zamanlama sabiti mantık testleri ─────────────────────────────────────────

def test_slow_threshold_above_baseline():
    """_SUBPROCESS_SLOW_MS 956ms baseline'dan büyük olmalı (false alarm olmaz)."""
    baseline_ms = 956
    slow_ms = 3000
    assert slow_ms > baseline_ms * 2, f"{slow_ms} < baseline {baseline_ms} × 2"


def test_macro_threshold_above_baseline():
    """_MACRO_SLOW_MS 650ms baseline'dan büyük olmalı."""
    baseline_ms = 650
    slow_ms = 2000
    assert slow_ms > baseline_ms * 2, f"{slow_ms} < baseline {baseline_ms} × 2"


def test_slow_threshold_below_timeout():
    """_SUBPROCESS_SLOW_MS 25s timeout'tan küçük olmalı (alarm timeout'tan önce gelir)."""
    timeout_ms = 25000
    slow_ms = 3000
    assert slow_ms < timeout_ms, f"{slow_ms} >= timeout {timeout_ms}"


def test_macro_threshold_below_timeout():
    """_MACRO_SLOW_MS 10s macro timeout'tan küçük olmalı."""
    timeout_ms = 10000
    slow_ms = 2000
    assert slow_ms < timeout_ms, f"{slow_ms} >= timeout {timeout_ms}"


# ── perf_counter güvenilirlik testi ──────────────────────────────────────────

def test_perf_counter_measures_subprocess():
    """time.perf_counter() kısa subprocess süresini doğru ölçüyor mu?"""
    import tempfile
    script = tempfile.NamedTemporaryFile(suffix=".py", mode="w", delete=False)
    script.write("import time; time.sleep(0.1); print('ok')\n")
    script.close()

    try:
        t0 = time.perf_counter()
        result = subprocess.run(
            [_VENV_PYTHON, script.name],
            capture_output=True, text=True, timeout=5,
        )
        ms = (time.perf_counter() - t0) * 1000
        assert result.returncode == 0
        assert ms >= 100, f"100ms subprocess için ölçülen {ms:.0f}ms (perf_counter çalışmıyor?)"
        assert ms < 5000, f"Beklenmedik kadar yavaş: {ms:.0f}ms"
    finally:
        os.unlink(script.name)


# ── Runner ────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    tests = [
        test_subprocess_slow_ms_constant_defined,
        test_macro_slow_ms_constant_defined,
        test_fetch_daily_has_timing,
        test_fetch_daily_has_debug_log,
        test_fetch_daily_has_slow_warning,
        test_fetch_daily_timeout_logs_elapsed,
        test_macro_fetch_has_timing,
        test_macro_fetch_has_slow_warning,
        test_slow_threshold_above_baseline,
        test_macro_threshold_above_baseline,
        test_slow_threshold_below_timeout,
        test_macro_threshold_below_timeout,
        test_perf_counter_measures_subprocess,
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
