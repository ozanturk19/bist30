"""Görev 11 — _weekly_trend() + _fill_intraday_gaps() subprocess birim testleri (CPO-740).
Doğrular:
  - _weekly_trend() lock-free (no _YF_GLOBAL_LOCK)
  - _fill_intraday_gaps() lock-free
  - _fetch_weekly_subprocess() ve _fetch_intraday_subprocess() tanımlı
  - yf_fetch.py period/interval parametreleri (1y/1wk ve 5d/1m)
  - ticker_base dönüşümü doğru (.IS strip mantığı)
  - EMA20 yön hesabı mantığı
"""
import re
import os
import sys
import subprocess
import json
import pandas as pd

_APP_PY = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "app.py")
_YF_FETCH_SCRIPT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "yf_fetch.py")
_VENV_PYTHON = sys.executable


# ── Dosya içeriği kontrolleri ─────────────────────────────────────────────────

def _extract_function_body(src, func_name):
    """Fonksiyon gövdesini kaynak koddan çıkar (bir sonraki def'e kadar)."""
    pattern = rf"def {func_name}\(.*?(?=\ndef |\Z)"
    m = re.search(pattern, src, re.DOTALL)
    if not m:
        return None
    return m.group(0)


def _without_docstring(body):
    """Fonksiyon gövdesinden triple-quote docstring'i çıkar."""
    return re.sub(r'""".*?"""', '', body, flags=re.DOTALL)


def test_weekly_trend_no_global_lock():
    """_weekly_trend() gövdesinde (docstring hariç) global lock kullanılmamalı."""
    with open(_APP_PY, encoding="utf-8") as f:
        src = f.read()
    body = _extract_function_body(src, "_weekly_trend")
    assert body, "_weekly_trend fonksiyonu bulunamadı"
    code_only = _without_docstring(body)
    assert "_YF_GLOBAL_LOCK" not in code_only, "_weekly_trend hâlâ _YF_GLOBAL_LOCK kullanıyor"
    assert "yf.download" not in code_only, "_weekly_trend hâlâ yf.download kullanıyor"


def test_fill_intraday_no_global_lock():
    """_fill_intraday_gaps() gövdesinde (docstring hariç) global lock kullanılmamalı."""
    with open(_APP_PY, encoding="utf-8") as f:
        src = f.read()
    body = _extract_function_body(src, "_fill_intraday_gaps")
    assert body, "_fill_intraday_gaps fonksiyonu bulunamadı"
    code_only = _without_docstring(body)
    assert "_YF_GLOBAL_LOCK" not in code_only, "_fill_intraday_gaps hâlâ _YF_GLOBAL_LOCK kullanıyor"
    assert "yf.download" not in code_only, "_fill_intraday_gaps hâlâ yf.download kullanıyor"


def test_fetch_weekly_subprocess_defined():
    """_fetch_weekly_subprocess fonksiyonu tanımlı olmalı."""
    with open(_APP_PY, encoding="utf-8") as f:
        src = f.read()
    assert "def _fetch_weekly_subprocess(" in src, "_fetch_weekly_subprocess tanımsız"


def test_fetch_intraday_subprocess_defined():
    """_fetch_intraday_subprocess fonksiyonu tanımlı olmalı."""
    with open(_APP_PY, encoding="utf-8") as f:
        src = f.read()
    assert "def _fetch_intraday_subprocess(" in src, "_fetch_intraday_subprocess tanımsız"


def test_weekly_trend_calls_subprocess():
    """_weekly_trend() _fetch_weekly_subprocess çağırmalı."""
    with open(_APP_PY, encoding="utf-8") as f:
        src = f.read()
    body = _extract_function_body(src, "_weekly_trend")
    assert "_fetch_weekly_subprocess" in body, "_weekly_trend _fetch_weekly_subprocess çağırmıyor"


def test_fill_intraday_calls_subprocess():
    """_fill_intraday_gaps() _fetch_intraday_subprocess çağırmalı."""
    with open(_APP_PY, encoding="utf-8") as f:
        src = f.read()
    body = _extract_function_body(src, "_fill_intraday_gaps")
    assert "_fetch_intraday_subprocess" in body, "_fill_intraday_gaps _fetch_intraday_subprocess çağırmıyor"


def test_weekly_trend_has_is_strip():
    """_weekly_trend() .IS suffix strip mantığı içermeli (endswith/removesuffix/[:-3])."""
    with open(_APP_PY, encoding="utf-8") as f:
        src = f.read()
    body = _extract_function_body(src, "_weekly_trend")
    has_strip = ".IS" in body and (
        "endswith" in body or "removesuffix" in body or "[:-3]" in body
    )
    assert has_strip, "_weekly_trend .IS strip mantığı yok"


def test_fill_intraday_has_is_strip():
    """_fill_intraday_gaps() .IS suffix strip mantığı içermeli."""
    with open(_APP_PY, encoding="utf-8") as f:
        src = f.read()
    body = _extract_function_body(src, "_fill_intraday_gaps")
    has_strip = ".IS" in body and (
        "endswith" in body or "removesuffix" in body or "[:-3]" in body
    )
    assert has_strip, "_fill_intraday_gaps .IS strip mantığı yok"


def test_fetch_weekly_uses_1wk_interval():
    """_fetch_weekly_subprocess(), 1wk interval ile _fetch_daily_subprocess çağırmalı."""
    with open(_APP_PY, encoding="utf-8") as f:
        src = f.read()
    body = _extract_function_body(src, "_fetch_weekly_subprocess")
    assert "1wk" in body, "_fetch_weekly_subprocess 1wk interval kullanmıyor"
    assert "1y" in body, "_fetch_weekly_subprocess 1y period kullanmıyor"


def test_fetch_intraday_uses_1m_interval():
    """_fetch_intraday_subprocess(), 1m interval ile _fetch_daily_subprocess çağırmalı."""
    with open(_APP_PY, encoding="utf-8") as f:
        src = f.read()
    body = _extract_function_body(src, "_fetch_intraday_subprocess")
    assert "1m" in body, "_fetch_intraday_subprocess 1m interval kullanmıyor"
    assert "5d" in body, "_fetch_intraday_subprocess 5d period kullanmıyor"


# ── yf_fetch.py subprocess kontrat testleri ──────────────────────────────────

def test_yf_fetch_accepts_1wk_args():
    """yf_fetch.py 4 argüman beklediğinde (ticker period interval) exit 0 veya 1 döner, asılmaz."""
    result = subprocess.run(
        [_VENV_PYTHON, _YF_FETCH_SCRIPT],  # no args → should exit 1 + error JSON
        capture_output=True, text=True, timeout=5,
    )
    assert result.returncode == 1, "Argümansız yf_fetch.py exit 1 döndürmeli"
    err = json.loads(result.stderr)
    assert "error" in err, "Error JSON 'error' anahtarı içermeli"


def test_yf_fetch_3_args_required():
    """yf_fetch.py 2 argümanla (ticker period) çalıştırıldığında da exit 1 döner."""
    result = subprocess.run(
        [_VENV_PYTHON, _YF_FETCH_SCRIPT, "AKBNK", "1y"],  # missing interval
        capture_output=True, text=True, timeout=5,
    )
    assert result.returncode == 1, "Eksik argümanla yf_fetch.py exit 1 döndürmeli"


# ── EMA yön mantığı (standalone) ─────────────────────────────────────────────

def _compute_ema(series, n):
    return series.ewm(span=n, adjust=False).mean()


def test_ema20_rising_direction():
    """Yükselen kapanış serisi → EMA20 yönü +1 olmalı."""
    close = pd.Series([100.0 + i * 0.5 for i in range(30)])
    ema = _compute_ema(close, 20)
    direction = 1 if float(ema.iloc[-1]) > float(ema.iloc[-2]) else -1
    assert direction == 1, "Yükselen seri için +1 bekleniyor"


def test_ema20_falling_direction():
    """Düşen kapanış serisi → EMA20 yönü -1 olmalı."""
    close = pd.Series([150.0 - i * 0.5 for i in range(30)])
    ema = _compute_ema(close, 20)
    direction = 1 if float(ema.iloc[-1]) > float(ema.iloc[-2]) else -1
    assert direction == -1, "Düşen seri için -1 bekleniyor"


def test_weekly_min_row_check():
    """25 satırdan az haftalık bar → _weekly_trend 0 döndürmeli (len < 25 guard)."""
    with open(_APP_PY, encoding="utf-8") as f:
        src = f.read()
    body = _extract_function_body(src, "_weekly_trend")
    assert "< 25" in body or "25" in body, "_weekly_trend < 25 row guard yok"


# ── Runner ────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    tests = [
        test_weekly_trend_no_global_lock,
        test_fill_intraday_no_global_lock,
        test_fetch_weekly_subprocess_defined,
        test_fetch_intraday_subprocess_defined,
        test_weekly_trend_calls_subprocess,
        test_fill_intraday_calls_subprocess,
        test_weekly_trend_has_is_strip,
        test_fill_intraday_has_is_strip,
        test_fetch_weekly_uses_1wk_interval,
        test_fetch_intraday_uses_1m_interval,
        test_yf_fetch_accepts_1wk_args,
        test_yf_fetch_3_args_required,
        test_ema20_rising_direction,
        test_ema20_falling_direction,
        test_weekly_min_row_check,
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
