"""Görev 10 — ThreadPoolExecutor(4) birim testleri (CPO-740).
Doğrular:
  - _ANALYZE_EXECUTOR max_workers == 4
  - refresh_data() içinde max_workers=4 ThreadPool kullanılıyor
  - 4 eş zamanlı _analyze_with_timeout benzeri çağrı çalışabilir
"""
import re
import os
import time
import threading
import concurrent.futures as cf

_APP_PY = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "app.py")


# ── Dosya içeriği kontrolleri ─────────────────────────────────────────────────

def test_analyze_executor_max_workers_is_4():
    """app.py: _ANALYZE_EXECUTOR max_workers=4 olmalı."""
    with open(_APP_PY, encoding="utf-8") as f:
        src = f.read()
    m = re.search(r"_ANALYZE_EXECUTOR\s*=.*ThreadPoolExecutor\(max_workers=(\d+)", src)
    assert m, "_ANALYZE_EXECUTOR satırı bulunamadı"
    assert m.group(1) == "4", f"_ANALYZE_EXECUTOR max_workers beklenen 4, gerçek: {m.group(1)}"


def test_refresh_par_max_workers_is_4():
    """app.py: refresh_par ThreadPoolExecutor max_workers=4 olmalı."""
    with open(_APP_PY, encoding="utf-8") as f:
        src = f.read()
    m = re.search(r'thread_name_prefix="refresh_par"', src)
    assert m, "refresh_par satırı bulunamadı"
    # İki satırlı kontrol: max_workers=4 ve refresh_par aynı satırda
    line_re = re.search(r"ThreadPoolExecutor\(max_workers=(\d+)[^)]*\)\s*#.*refresh_par|ThreadPoolExecutor\(max_workers=(\d+),\s*thread_name_prefix=\"refresh_par\"", src)
    assert line_re, "refresh_par ile max_workers aynı satırda bulunamadı"
    val = line_re.group(1) or line_re.group(2)
    assert val == "4", f"refresh_par max_workers beklenen 4, gerçek: {val}"


def test_cpo583_comment_removed():
    """CPO-583 (4→2) yorumu artık 4 olan satırlarda bulunmamalı."""
    with open(_APP_PY, encoding="utf-8") as f:
        src = f.read()
    for line in src.splitlines():
        if "CPO-583: 4→2" in line:
            if "_ANALYZE_EXECUTOR" in line or "refresh_par" in line:
                assert False, f"CPO-583 yorumu Görev 10 satırında hâlâ var: {line.strip()}"


# ── Eş zamanlılık davranış testleri ──────────────────────────────────────────

def test_four_concurrent_workers_run_simultaneously():
    """4 worker ThreadPool, 4 görevi gerçekten eş zamanlı çalıştırabilmeli."""
    max_concurrent = 4
    barrier = threading.Barrier(max_concurrent)
    results = []

    def task(i):
        barrier.wait(timeout=3)  # 4 iş parçacığı aynı anda buluşmalı
        results.append(i)
        return i

    with cf.ThreadPoolExecutor(max_workers=max_concurrent) as ex:
        futures = [ex.submit(task, i) for i in range(max_concurrent)]
        cf.wait(futures, timeout=5)

    assert len(results) == max_concurrent, f"Beklenen {max_concurrent} sonuç, gerçek: {len(results)}"


def test_analyze_timeout_wrapper_pattern():
    """_analyze_with_timeout benzeri timeout wrapper: 40s limit içinde döner."""
    inner_pool = cf.ThreadPoolExecutor(max_workers=4)
    TIMEOUT = 40

    def fast_analyze(ticker):
        time.sleep(0.01)  # 10ms simulate
        return {"ticker": ticker, "signal": "AL"}

    tickers = ["AKBNK", "THYAO", "GARAN", "ASELS"]
    futures = {inner_pool.submit(fast_analyze, t): t for t in tickers}
    results = []
    for f in cf.as_completed(futures, timeout=TIMEOUT):
        r = f.result(timeout=1)
        if r:
            results.append(r)

    inner_pool.shutdown(wait=False)
    assert len(results) == 4, f"4 ticker beklendi, {len(results)} geldi"


def test_throughput_improvement_vs_2workers():
    """4 worker, 2 worker'a göre en az 1.5x hızlı olmalı (8 paralel görev)."""
    TASK_COUNT = 8
    SLEEP = 0.05  # 50ms per task

    def timed_run(workers):
        pool = cf.ThreadPoolExecutor(max_workers=workers)
        start = time.time()
        futures = [pool.submit(time.sleep, SLEEP) for _ in range(TASK_COUNT)]
        cf.wait(futures, timeout=10)
        pool.shutdown(wait=False)
        return time.time() - start

    t2 = timed_run(2)
    t4 = timed_run(4)

    speedup = t2 / t4
    assert speedup >= 1.5, f"4 worker speedup beklenen ≥1.5x, gerçek: {speedup:.2f}x (t2={t2:.3f}s, t4={t4:.3f}s)"


# ── Runner ────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    tests = [
        test_analyze_executor_max_workers_is_4,
        test_refresh_par_max_workers_is_4,
        test_cpo583_comment_removed,
        test_four_concurrent_workers_run_simultaneously,
        test_analyze_timeout_wrapper_pattern,
        test_throughput_improvement_vs_2workers,
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
    print(f"\n{'='*60}")
    print(f"Result: {passed}/{len(tests)} passed")
    if fail_names:
        print(f"FAILED: {', '.join(fail_names)}")
        raise SystemExit(1)
    print("ALL TESTS PASSED ✅")
