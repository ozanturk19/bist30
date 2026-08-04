"""CPO-1269 §6/§7 (04.08) — `_lock` staleness probe + /api/health.lock_probe alanı.

Canlı P0 forensic: `_lock` (app.py:1300) bir route'ta süresiz tutuluyor ama
/api/health bunu hiç göremiyor (SPEC-016 K4 tasarımı gereği lock-free). CPO'nun
kendi önerisi: `_lock`'u sahiplenen tarafı ölçmek yerine (SIGUSR2 dump gerektirir,
deploy bekliyor), sadece "_lock ne kadardır sürekli meşgul" — non-blocking probe.

Bu testler kod tabanını statik olarak inceler (regex) + probe'un TEK iterasyon
mantığını izole exec ile gerçek `threading.Lock` üzerinde davranış olarak
doğrular — sunucu/3.10+ import gerektirmez (feedback_local_mac_no_python310).
"""
import os
import re
import threading
import time

_APP_PY = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "app.py")


def _read_app():
    with open(_APP_PY, encoding="utf-8") as f:
        return f.read()


def _extract_function_body(src, func_name):
    pattern = rf"def {func_name}\(.*?(?=\ndef |\Z)"
    m = re.search(pattern, src, re.DOTALL)
    return m.group(0) if m else None


def test_probe_loop_never_uses_blocking_acquire():
    src = _read_app()
    body = _extract_function_body(src, "_lock_probe_loop")
    assert body, "_lock_probe_loop() bulunamadı"
    assert "_lock.acquire(blocking=False)" in body, (
        "probe SADECE non-blocking acquire kullanmalı — aksi halde probe'un "
        "kendisi de _lock asılı kalırsa tıkanır, tüm gözlemlenebilirliği götürür"
    )
    assert "_lock.acquire()" not in body.replace("_lock.acquire(blocking=False)", ""), (
        "gizli bir blocking acquire() sızmış olmamalı"
    )


def test_probe_runs_independently_of_health_snapshot_loop():
    """CPO-1269'un asıl talebi: _compute_health() kendisi _lock alıyor (8582) —
    _lock asılı kalırsa o thread de tıkanır. Probe AYRI bir thread/fonksiyon
    olmalı, _health_snapshot_loop'un İÇİNE gömülmemeli."""
    src = _read_app()
    health_loop_body = _extract_function_body(src, "_health_snapshot_loop")
    assert health_loop_body, "_health_snapshot_loop() bulunamadı"
    assert "_lock_probe_loop" not in health_loop_body, (
        "probe _health_snapshot_loop içine gömülmemeli — o thread _compute_health() "
        "üzerinden _lock'a bağımlı, tıkanırsa probe da onunla birlikte gömülür"
    )
    assert re.search(r'threading\.Thread\(target=_lock_probe_loop,\s*daemon=True', src), (
        "_lock_probe_loop kendi bağımsız daemon thread'inde başlatılmalı"
    )


def test_health_endpoint_merges_lock_probe_without_touching_lock():
    src = _read_app()
    body = _extract_function_body(src, "api_health")
    assert body, "api_health() bulunamadı"
    assert "resp[\"lock_probe\"] = _lock_probe_state" in body
    assert "with _lock" not in body, (
        "/api/health endpoint'i (request path) HİÇBİR koşulda _lock almamalı — "
        "SPEC-016 K4'ün tüm amacı bu, lock_probe eklemek bu invariantı bozmamalı"
    )


def _load_probe_iteration_isolated():
    """`_lock_probe_loop`'un `while True:` gövdesini (tek iterasyon) izole exec
    ile yükler — gerçek threading.Lock üzerinde davranışını doğrular."""
    src = _read_app()
    body = _extract_function_body(src, "_lock_probe_loop")
    assert body, "_lock_probe_loop() bulunamadı"
    m = re.search(r"while True:\n(.*?)\n(?=        time\.sleep\(3\))", body, re.DOTALL)
    assert m, "while True: gövdesi çıkarılamadı"
    iteration_src = m.group(1)
    # Girinti düzelt (while-body 8 boşluk → def-body 4 boşluk) + fonksiyona sar
    dedented = "\n".join(line[4:] if line.startswith("    ") else line for line in iteration_src.split("\n"))
    fn_src = "def _one_iteration():\n    global _lock_probe_state\n" + dedented
    ns = {"time": time, "logger": __import__("logging").getLogger("test_cpo1269_isolated")}
    exec(fn_src, ns)
    return ns["_one_iteration"], ns


def test_probe_reports_free_when_lock_available():
    fn, ns = _load_probe_iteration_isolated()
    ns["_lock"] = threading.Lock()
    ns["_lock_probe_state"] = {"last_free_ts": time.time() - 100, "stuck_s": 100.0}  # stale başlangıç
    fn()
    assert ns["_lock_probe_state"]["stuck_s"] == 0.0, "lock boşken stuck_s sıfırlanmalı"


def test_probe_reports_growing_stuck_s_when_lock_held_elsewhere():
    """Asıl regresyon senaryosu: _lock BAŞKA bir thread tarafından tutuluyor
    (CPO-1269'un canlı gözlemlediği durumun simülasyonu) — probe bunu HEMEN
    (non-blocking) tespit etmeli, kendisi asılı kalmamalı."""
    fn, ns = _load_probe_iteration_isolated()
    real_lock = threading.Lock()
    real_lock.acquire()  # başka bir "greenlet/thread" tutuyormuş gibi — asla release edilmiyor
    try:
        ns["_lock"] = real_lock
        _t0 = time.time() - 45  # 45s önce son kez boştu
        ns["_lock_probe_state"] = {"last_free_ts": _t0, "stuck_s": 45.0}

        _call_t0 = time.time()
        fn()
        _elapsed = time.time() - _call_t0

        assert _elapsed < 0.5, f"probe non-blocking olmalı, {_elapsed:.2f}s sürdü"
        assert ns["_lock_probe_state"]["stuck_s"] >= 45.0, (
            f"lock hâlâ meşgulken stuck_s ARTMALI (en az başlangıç kadar), "
            f"gerçek={ns['_lock_probe_state']['stuck_s']}"
        )
        assert ns["_lock_probe_state"]["last_free_ts"] == _t0, (
            "lock meşgulken last_free_ts DEĞİŞMEMELİ — asıl 'ne zamandır meşgul' ölçütü bu"
        )
    finally:
        real_lock.release()
