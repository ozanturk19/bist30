"""DEV-1441 / CPO-1068 — health snapshot loop stall-detection regression test.

_health_snapshot_loop (app.py) her tick'te _check_health_loop_stall()
çağırır (_health_extras.py, pure/stateless). Bu test app.py import etmez
(3.10+ gerektirir, bkz. feedback_local_mac_no_python310) — sadece pure
helper'ı doğrudan test eder, local Mac python3.9'da da çalışır.

CPO-1068 (b) şartı: (i) normal çalışmada SIFIR WARNING, (ii) >15s stall'da
TAM 1 uyarı + doğru gap değeri.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from _health_extras import _check_health_loop_stall


def test_normal_cadence_never_stalls():
    """8s loop cadence — hiçbir tick 15s eşiğini geçmemeli."""
    last_tick = 0.0
    for _ in range(50):
        now = last_tick + 8.0
        assert _check_health_loop_stall(now, last_tick) is None
        last_tick = now


def test_stall_over_threshold_returns_gap():
    result = _check_health_loop_stall(now=122.0, last_tick_ts=100.0)  # gap=22
    assert result == 22.0


def test_gap_exactly_at_threshold_is_not_a_stall():
    assert _check_health_loop_stall(now=115.0, last_tick_ts=100.0) is None  # gap=15


def test_gap_just_over_threshold_is_a_stall():
    result = _check_health_loop_stall(now=115.1, last_tick_ts=100.0)  # gap=15.1
    assert result is not None
    assert round(result, 1) == 15.1


def test_first_tick_after_init_is_not_a_false_positive():
    """Loop init'te last_tick_ts=now olduğundan ilk tick gap~0, stall değil."""
    t0 = 1000.0
    assert _check_health_loop_stall(t0, t0) is None
