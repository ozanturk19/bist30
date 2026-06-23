"""Faz 12 P1 — email_qa.py test suite (CPO-693)"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from email_qa import validate_email_pre_send, MAX_DAILY_CHANGES


def _make_changes(tickers, signal="AL"):
    """Helper: build (ticker, old, new, stock) tuples."""
    return [(t, "BEKLE", signal, {"price": 45.0}) for t in tickers]


# ── Normal cases ─────────────────────────────────────────────────────────────

def test_valid_single_change():
    r = validate_email_pre_send(_make_changes(["AKBNK"]))
    assert r["ok"] is True and r["count"] == 1

def test_valid_multiple_changes():
    tickers = ["AKBNK", "THYAO", "SISE", "KCHOL"]
    r = validate_email_pre_send(_make_changes(tickers))
    assert r["ok"] is True and r["count"] == 4

def test_at_max_count_ok():
    tickers = [f"TICK{i:02d}" for i in range(MAX_DAILY_CHANGES)]
    r = validate_email_pre_send(_make_changes(tickers))
    assert r["ok"] is True

def test_result_has_count():
    r = validate_email_pre_send(_make_changes(["AKBNK", "THYAO"]))
    assert r["count"] == 2


# ── Empty changes ─────────────────────────────────────────────────────────────

def test_empty_changes_fail():
    r = validate_email_pre_send([])
    assert r["ok"] is False and r["flag"] == "EMAIL_EMPTY_CHANGES"

def test_empty_changes_count_zero():
    r = validate_email_pre_send([])
    assert r["count"] == 0


# ── Excessive changes ─────────────────────────────────────────────────────────

def test_just_over_max_fail():
    tickers = [f"TICK{i:03d}" for i in range(MAX_DAILY_CHANGES + 1)]
    r = validate_email_pre_send(_make_changes(tickers))
    assert r["ok"] is False and r["flag"] == "EMAIL_EXCESSIVE_CHANGES"

def test_excessive_has_count():
    tickers = [f"X{i:04d}" for i in range(150)]
    r = validate_email_pre_send(_make_changes(tickers))
    assert r["count"] == 150 and r["max_count"] == MAX_DAILY_CHANGES

def test_custom_max_count():
    changes = _make_changes(["A", "B", "C"])  # 3 items
    r = validate_email_pre_send(changes, max_count=2)
    assert r["ok"] is False and r["flag"] == "EMAIL_EXCESSIVE_CHANGES"

def test_custom_max_exactly_ok():
    changes = _make_changes(["A", "B"])  # 2 items
    r = validate_email_pre_send(changes, max_count=2)
    assert r["ok"] is True


# ── Malformed changes ─────────────────────────────────────────────────────────

def test_malformed_too_short_fail():
    changes = [("AKBNK", "BEKLE")]  # only 2 elements, need >= 3
    r = validate_email_pre_send(changes)
    assert r["ok"] is False and r["flag"] == "EMAIL_MALFORMED_CHANGES"

def test_malformed_not_tuple_fail():
    changes = ["not-a-tuple"]
    r = validate_email_pre_send(changes)
    assert r["ok"] is False and r["flag"] == "EMAIL_MALFORMED_CHANGES"

def test_malformed_indices_reported():
    good = ("AKBNK", "BEKLE", "AL", {})
    bad = ("THYAO", "BEKLE")  # too short
    r = validate_email_pre_send([good, bad])
    assert r["ok"] is False
    assert 1 in r["indices"]  # index 1 is the bad one


# ── Duplicate tickers ─────────────────────────────────────────────────────────

def test_duplicate_ticker_fail():
    changes = _make_changes(["AKBNK", "THYAO", "AKBNK"])  # AKBNK twice
    r = validate_email_pre_send(changes)
    assert r["ok"] is False and r["flag"] == "EMAIL_DUPLICATE_TICKERS"

def test_duplicate_ticker_reported():
    changes = _make_changes(["AKBNK", "AKBNK"])
    r = validate_email_pre_send(changes)
    assert "AKBNK" in r["duplicates"]

def test_no_duplicates_ok():
    changes = _make_changes(["AKBNK", "THYAO", "SISE"])
    r = validate_email_pre_send(changes)
    assert r["ok"] is True


# ── Context field ────────────────────────────────────────────────────────────

def test_context_propagated():
    r = validate_email_pre_send([], context="daily_digest")
    assert r["context"] == "daily_digest"


# ── runner ───────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    tests = [
        test_valid_single_change, test_valid_multiple_changes,
        test_at_max_count_ok, test_result_has_count,
        test_empty_changes_fail, test_empty_changes_count_zero,
        test_just_over_max_fail, test_excessive_has_count,
        test_custom_max_count, test_custom_max_exactly_ok,
        test_malformed_too_short_fail, test_malformed_not_tuple_fail,
        test_malformed_indices_reported,
        test_duplicate_ticker_fail, test_duplicate_ticker_reported,
        test_no_duplicates_ok,
        test_context_propagated,
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
    print(f"\n{'='*55}")
    print(f"Result: {passed}/{len(tests)} passed")
    if fail_names:
        print(f"FAILED: {', '.join(fail_names)}")
        raise SystemExit(1)
    print("ALL TESTS PASSED ✅")
