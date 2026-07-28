"""CPO-1155 §2 — alerting.py flag-bazlı şiddet + dedup/rate-limit test suite.

Kök neden: DQV_SV_DATA/MACRO/CHART her zaman sabit P0'dı, aynı kronik hata
tekrarlandığında (ör. CPO-1152/1153'teki updated_at=None drift'i) ALERT.md'ye
saatlerce her request'te bir satır düşüyordu (704 kayıt/gün). Bu test iki
düzeltmeyi doğrular: (1) yalnızca leaf-level "is not of type" hataları P1'e
düşer, yapısal (required/container) hatalar P0'da kalır — (2) aynı
(event, ticker, tier) DEDUP_WINDOW_S içinde bastırılır, ilk görülüşte ve
pencere kapanınca "+N suppressed" ile geçer.
"""

import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import alerting


def _reset():
    """Her testten önce process-local dedup state'i temizle."""
    with alerting._dedup_lock:
        alerting._last_emit.clear()


def _capture(monkeypatch):
    lines = []
    monkeypatch.setattr(alerting, "_append_alert_md", lambda line: lines.append(line))
    return lines


# ── _classify_severity ──────────────────────────────────────────────────────

def test_classify_severity_downgrades_pure_type_drift():
    errors = [{"path": ["updated_at"], "message": "None is not of type 'string'"}]
    assert alerting._classify_severity("P0", errors) == "P1"


def test_classify_severity_keeps_structural_required_error():
    errors = [{"path": [], "message": "'stocks' is a required property"}]
    assert alerting._classify_severity("P0", errors) == "P0"


def test_classify_severity_keeps_non_null_type_error_p0():
    # "None is not of type" değil (gerçek veri bozulması, null-drift değil)
    # -> P0'da kalmalı, yanlışlıkla P1'e düşmemeli.
    errors = [{"path": ["stocks"], "message": "'not-an-array' is not of type 'array'"}]
    assert alerting._classify_severity("P0", errors) == "P0"


def test_classify_severity_no_errors_keeps_default():
    assert alerting._classify_severity("P0", None) == "P0"
    assert alerting._classify_severity("P0", []) == "P0"


def test_classify_severity_p1_event_untouched():
    errors = [{"path": [], "message": "'x' is a required property"}]
    assert alerting._classify_severity("P1", errors) == "P1"


def test_classify_severity_mixed_errors_stays_p0():
    errors = [
        {"path": ["updated_at"], "message": "None is not of type 'string'"},
        {"path": [], "message": "'stocks' is a required property"},
    ]
    assert alerting._classify_severity("P0", errors) == "P0"


# ── emit_alert dedup/rate-limit ─────────────────────────────────────────────

def test_emit_alert_first_call_not_suppressed(monkeypatch):
    _reset()
    lines = _capture(monkeypatch)
    alerting.emit_alert("DQV_BR", "detail-1", ticker="AKBNK")
    assert len(lines) == 1
    assert "suppressed" not in lines[0]


def test_emit_alert_repeat_within_window_suppressed(monkeypatch):
    _reset()
    lines = _capture(monkeypatch)
    alerting.emit_alert("DQV_BR", "detail-1", ticker="AKBNK")
    alerting.emit_alert("DQV_BR", "detail-2", ticker="AKBNK")
    alerting.emit_alert("DQV_BR", "detail-3", ticker="AKBNK")
    assert len(lines) == 1  # yalnız ilki yazıldı


def test_emit_alert_different_ticker_not_deduped(monkeypatch):
    _reset()
    lines = _capture(monkeypatch)
    alerting.emit_alert("DQV_BR", "detail", ticker="AKBNK")
    alerting.emit_alert("DQV_BR", "detail", ticker="GARAN")
    assert len(lines) == 2  # farklı fingerprint


def test_emit_alert_window_expiry_flushes_with_suppressed_count(monkeypatch):
    _reset()
    lines = _capture(monkeypatch)
    monkeypatch.setattr(alerting, "DEDUP_WINDOW_S", 0.05)
    alerting.emit_alert("DQV_BR", "detail-1", ticker="AKBNK")
    alerting.emit_alert("DQV_BR", "detail-2", ticker="AKBNK")  # suppressed
    time.sleep(0.1)
    alerting.emit_alert("DQV_BR", "detail-3", ticker="AKBNK")  # pencere kapandı, flush
    assert len(lines) == 2
    assert "+1 suppressed" in lines[1]


def test_emit_alert_never_raises_on_sentry_exception(monkeypatch):
    _reset()
    _capture(monkeypatch)

    class _BadSentry:
        def capture_message(self, *a, **kw):
            raise RuntimeError("boom")

    # P0 tier + sentry hatası -> exception yutulmalı
    alerting.emit_alert("DQV_SV_DATA", "detail", _sentry=_BadSentry())


# ── runner ───────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import unittest.mock as mock

    tests = [
        test_classify_severity_downgrades_pure_type_drift,
        test_classify_severity_keeps_structural_required_error,
        test_classify_severity_keeps_non_null_type_error_p0,
        test_classify_severity_no_errors_keeps_default,
        test_classify_severity_p1_event_untouched,
        test_classify_severity_mixed_errors_stays_p0,
    ]
    passed = 0
    fail_names = []
    for t in tests:
        try:
            t()
            passed += 1
            print(f"  ✓ {t.__name__}")
        except AssertionError as e:
            fail_names.append(t.__name__)
            print(f"  ✗ {t.__name__}: {e}")

    # monkeypatch gerektiren testler pytest.MonkeyPatch ile manuel çalıştırılır
    from _pytest.monkeypatch import MonkeyPatch
    mp_tests = [
        test_emit_alert_first_call_not_suppressed,
        test_emit_alert_repeat_within_window_suppressed,
        test_emit_alert_different_ticker_not_deduped,
        test_emit_alert_window_expiry_flushes_with_suppressed_count,
        test_emit_alert_never_raises_on_sentry_exception,
    ]
    for t in mp_tests:
        mp = MonkeyPatch()
        try:
            t(mp)
            passed += 1
            print(f"  ✓ {t.__name__}")
        except AssertionError as e:
            fail_names.append(t.__name__)
            print(f"  ✗ {t.__name__}: {e}")
        finally:
            mp.undo()

    total = len(tests) + len(mp_tests)
    print(f"\n{'='*55}")
    print(f"Result: {passed}/{total} passed")
    if fail_names:
        print(f"FAILED: {', '.join(fail_names)}")
        raise SystemExit(1)
    print("ALL TESTS PASSED ✅")
