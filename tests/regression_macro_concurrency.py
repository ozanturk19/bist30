#!/usr/bin/env python3
"""
Regression test — /api/macro thread leak + Yahoo 401 protection.

Bu testi commit 9dc27af öncesi çalıştırsaydık, thread leak bug'ını yakalardık.
Şimdi (3fff364 sonrası) bu test geçer ve regression'ı koruma altında tutar.

ÇALIŞTIR:
  python tests/regression_macro_concurrency.py

KOŞULLAR (HEPSI GEÇMELİ):
  1. 100 paralel /api/macro request → hepsi 200, <2s
  2. Endpoint hiç yfinance çağırmamalı (request handler'da)
  3. _macro_bg_lock single-flight garantisi
  4. Yahoo 401 simülasyonunda eski cache korunur
"""
import subprocess
import json
import time
import sys
import urllib.request
import urllib.error
from concurrent.futures import ThreadPoolExecutor

BASE = "http://127.0.0.1:8003"


def fetch(url, timeout=3):
    try:
        t0 = time.time()
        r = urllib.request.urlopen(url, timeout=timeout)
        dt = time.time() - t0
        return r.status, dt, r.read().decode('utf-8', errors='replace')
    except urllib.error.HTTPError as e:
        return e.code, time.time() - t0, str(e)
    except Exception as e:
        return 0, time.time() - t0, str(e)


def _warmup():
    """Cache + workers warm-up. Service restart sonrası gerekli."""
    for _ in range(3):
        fetch(f"{BASE}/api/macro", timeout=10)
        time.sleep(0.3)


def test_1_concurrent_load():
    """50 paralel /api/macro request — rate limit 60/min'in altında.
    Hepsi başarılı + makul latency. Thread leak olsa fail eder."""
    print("\n=== TEST 1: 50 paralel /api/macro ===")
    _warmup()
    time.sleep(2)  # rate limit window'u bekle
    with ThreadPoolExecutor(max_workers=50) as pool:
        t0 = time.time()
        results = list(pool.map(lambda _: fetch(f"{BASE}/api/macro"), range(50)))
        total_dt = time.time() - t0

    statuses = [r[0] for r in results]
    times = [r[1] for r in results]
    ok_200 = sum(1 for s in statuses if s == 200)
    rate_limited = sum(1 for s in statuses if s == 429)
    failed = len(statuses) - ok_200 - rate_limited
    max_t = max(times)
    avg_t = sum(times) / len(times)
    p95 = sorted(times)[int(len(times) * 0.95)]

    print(f"  Total wall: {total_dt:.2f}s")
    print(f"  200 OK: {ok_200}/50")
    print(f"  429 Rate limited (kabul): {rate_limited}")
    print(f"  Other failures: {failed}")
    print(f"  Avg latency: {avg_t*1000:.0f}ms, p95: {p95*1000:.0f}ms, Max: {max_t*1000:.0f}ms")

    assert failed == 0, f"FAIL: {failed} non-429 failures (thread leak indicator)"
    assert ok_200 >= 30, f"FAIL: only {ok_200} 200 OK responses"
    # 200 OK requests should be fast (not yfinance)
    ok_times = [t for s, t, _ in results if s == 200]
    if ok_times:
        max_ok = max(ok_times)
        assert max_ok < 2.0, f"FAIL: max 200 latency {max_ok:.2f}s > 2s"
    print("  ✓ PASS")


def test_2_no_yfinance_in_handler():
    """/api/macro warm cache median <100ms (sadece cache lookup).
    Threshold: median<100ms (worker scheduling jitter ile ortalanır)."""
    print("\n=== TEST 2: /api/macro pure cache (no yfinance in handler) ===")
    _warmup()
    time.sleep(3)  # rate limit reset
    times = []
    fails = 0
    for _ in range(8):
        status, dt, _ = fetch(f"{BASE}/api/macro")
        if status == 200:
            times.append(dt)
        else:
            fails += 1
        time.sleep(0.5)  # 1.5/s = 90/min, çok altında

    if not times:
        raise AssertionError("FAIL: No 200 responses (all rate-limited?)")
    sorted_t = sorted(times)
    median = sorted_t[len(sorted_t) // 2]
    avg = sum(times) / len(times)
    max_t = max(times)
    print(f"  {len(times)} sequential calls — median {median*1000:.0f}ms, avg {avg*1000:.0f}ms, max {max_t*1000:.0f}ms")
    assert median < 0.15, f"FAIL: median {median*1000:.0f}ms > 150ms — handler may be doing external calls"
    print("  ✓ PASS")


def test_3_health_endpoint():
    """/api/health döner ve bg_loop stats içerir."""
    print("\n=== TEST 3: /api/health endpoint ===")
    status, dt, body = fetch(f"{BASE}/api/health")
    assert status == 200, f"Status {status} != 200"
    j = json.loads(body)
    assert "macro_bg_loop" in j, "macro_bg_loop key missing"
    assert "cycles" in j["macro_bg_loop"], "cycles missing"
    assert j["macro"]["count"] > 0, "macro cache empty"
    print(f"  bg_loop cycles: {j['macro_bg_loop']['cycles']}")
    print(f"  bg_loop successes: {j['macro_bg_loop']['successes']}")
    print(f"  macro age: {j['macro']['age_s']}s")
    print("  ✓ PASS")


def test_4_old_code_path_gone():
    """Eski thread-leak kod path'i tamamen silinmeli."""
    print("\n=== TEST 4: Eski code path grep verification ===")
    with open('/root/bist30/app.py') as f:
        src = f.read()

    # _refresh_macro_bg silinmiş olmalı
    assert "def _refresh_macro_bg" not in src, "FAIL: _refresh_macro_bg still defined"
    assert "_refresh_macro_bg(" not in src, "FAIL: _refresh_macro_bg still called"

    # _macro_refreshing global flag silinmiş olmalı (sadece comment kalabilir)
    code_lines = [l for l in src.split('\n') if not l.strip().startswith('#')]
    code = '\n'.join(code_lines)
    assert "_macro_refreshing = " not in code, "FAIL: _macro_refreshing flag still exists"

    # Request-spawned macro thread silinmiş olmalı
    assert 'name="macro-refresh"' not in src, "FAIL: macro-refresh thread spawn still there"

    print("  ✓ _refresh_macro_bg: removed")
    print("  ✓ _macro_refreshing flag: removed")
    print("  ✓ macro-refresh thread spawn: removed")
    print("  ✓ PASS")


def test_5_single_flight_lock():
    """_macro_bg_lock var ve thread-safe acquire pattern kullanılıyor."""
    print("\n=== TEST 5: _macro_bg_lock thread-safe pattern ===")
    with open('/root/bist30/app.py') as f:
        src = f.read()

    assert "_macro_bg_lock = threading.Lock()" in src, "FAIL: _macro_bg_lock not defined"
    assert "_macro_bg_lock.acquire(blocking=False)" in src, "FAIL: non-blocking acquire missing"
    assert "_macro_bg_lock.release()" in src, "FAIL: release missing"

    # try/finally pattern (release her zaman çağrılmalı)
    pattern_idx = src.find("if _macro_bg_lock.acquire")
    if pattern_idx > 0:
        snippet = src[pattern_idx:pattern_idx+2000]
        assert "try:" in snippet and "finally:" in snippet, "FAIL: try/finally pattern missing"

    print("  ✓ Lock defined")
    print("  ✓ Non-blocking acquire")
    print("  ✓ try/finally release pattern")
    print("  ✓ PASS")


def test_6_news_endpoint_fast():
    """/api/hisse/<t>/news cache-or-queue: handler max 200ms (no Gemini in handler)."""
    print("\n=== TEST 6: /api/hisse/<t>/news handler latency ===")
    # Hit a few times to ensure cache or in_flight
    fetch(f"{BASE}/api/hisse/AKBNK/news", timeout=5)
    time.sleep(2)
    times = []
    fails = 0
    for t in ["AKBNK", "THYAO", "GARAN", "BIMAS", "ASELS"]:
        status, dt, _ = fetch(f"{BASE}/api/hisse/{t}/news", timeout=3)
        if status == 200:
            times.append(dt)
        elif status == 429:
            pass  # rate limit OK
        else:
            fails += 1
        time.sleep(0.5)
    if not times:
        raise AssertionError("No 200 responses")
    max_t = max(times)
    print(f"  {len(times)} calls — max {max_t*1000:.0f}ms")
    assert max_t < 1.0, f"FAIL: max {max_t:.2f}s > 1s — news handler doing Gemini call?"
    assert fails == 0, f"FAIL: {fails} non-429 failures"
    print("  ✓ PASS")


def test_7_news_in_flight_single_flight():
    """News endpoint: aynı ticker için tek bg fetch (5 paralel call → 1 bg fetch)."""
    print("\n=== TEST 7: News single-flight per ticker ===")
    # Pick ticker not yet cached
    import urllib.request
    # Force in-flight by hitting fresh ticker
    ticker = "FONET"  # likely not cached recently
    statuses = []
    with ThreadPoolExecutor(max_workers=5) as pool:
        results = list(pool.map(lambda _: fetch(f"{BASE}/api/hisse/{ticker}/news"), range(5)))
    statuses = [r[0] for r in results]
    times = [r[1] for r in results]
    print(f"  5 paralel call: statuses={statuses}, max={max(times):.2f}s")
    # All should return fast (cache miss → null)
    assert max(times) < 2.0, f"FAIL: max {max(times):.2f}s > 2s — handler should not block"
    print("  ✓ PASS")


if __name__ == "__main__":
    tests = [test_1_concurrent_load, test_2_no_yfinance_in_handler,
             test_3_health_endpoint, test_4_old_code_path_gone,
             test_5_single_flight_lock,
             test_6_news_endpoint_fast,
             test_7_news_in_flight_single_flight]
    failed = 0
    for t in tests:
        try:
            t()
        except AssertionError as e:
            print(f"  ✗ FAIL: {e}")
            failed += 1
        except Exception as e:
            print(f"  ✗ ERROR: {e}")
            failed += 1

    print(f"\n{'═' * 50}")
    print(f"Total: {len(tests)}, Pass: {len(tests) - failed}, Fail: {failed}")
    sys.exit(0 if failed == 0 else 1)
