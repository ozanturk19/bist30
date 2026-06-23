"""Faz 12 P1 — playwright_checks.py test suite (CPO-693) — logic tests (no browser)"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import tempfile

from playwright_checks import (
    check_canvas_height,
    check_hareketliler_change_pct,
    check_signal_count_consistency,
    run_page_checks,
    check_visual_diff,
    MAX_HAREKETLILER_CHANGE_PCT,
    DEFAULT_VISUAL_DIFF_THRESHOLD,
)


# ── helpers for visual diff tests ─────────────────────────────────────────────

def _make_solid_png(color, size=(100, 100)):
    """Create a temp PNG filled with a solid RGB color. Caller must os.unlink()."""
    from PIL import Image
    img = Image.new("RGB", size, color=color)
    tmp = tempfile.NamedTemporaryFile(suffix=".png", delete=False)
    img.save(tmp.name)
    tmp.close()
    return tmp.name


def _make_patched_png(base_color, patch_color, patch_count, size=(100, 100)):
    """Solid PNG with `patch_count` pixels changed to patch_color."""
    from PIL import Image
    img = Image.new("RGB", size, color=base_color)
    pixels = img.load()
    changed = 0
    for y in range(size[1]):
        for x in range(size[0]):
            if changed >= patch_count:
                break
            pixels[x, y] = patch_color
            changed += 1
        if changed >= patch_count:
            break
    tmp = tempfile.NamedTemporaryFile(suffix=".png", delete=False)
    img.save(tmp.name)
    tmp.close()
    return tmp.name


# ── check_canvas_height ───────────────────────────────────────────────────────

def test_canvas_height_normal():
    r = check_canvas_height(400)
    assert r["ok"] is True and r["canvas_height"] == 400

def test_canvas_height_zero_fail():
    r = check_canvas_height(0)
    assert r["ok"] is False and r["flag"] == "CANVAS_HEIGHT_ZERO"

def test_canvas_height_none_fail():
    r = check_canvas_height(None)
    assert r["ok"] is False and r["flag"] == "CANVAS_HEIGHT_NONE"

def test_canvas_height_one_ok():
    r = check_canvas_height(1)
    assert r["ok"] is True

def test_canvas_height_negative_fail():
    r = check_canvas_height(-10)
    assert r["ok"] is False and r["flag"] == "CANVAS_HEIGHT_ZERO"


# ── check_hareketliler_change_pct ─────────────────────────────────────────────

def test_hareketliler_normal():
    r = check_hareketliler_change_pct([1.5, -2.3, 3.1, -4.0])
    assert r["ok"] is True

def test_hareketliler_glyho_selec_anomaly():
    r = check_hareketliler_change_pct([1.5, 28.4, -15.2])
    assert r["ok"] is False and r["flag"] == "EXCESSIVE_CHANGE_IN_HAREKETLILER"

def test_hareketliler_at_threshold_fail():
    # exactly 11.0 → >= threshold → fail
    r = check_hareketliler_change_pct([11.0])
    assert r["ok"] is False

def test_hareketliler_just_under_ok():
    r = check_hareketliler_change_pct([10.99])
    assert r["ok"] is True

def test_hareketliler_negative_anomaly():
    r = check_hareketliler_change_pct([-12.0, 5.0])
    assert r["ok"] is False and r["flag"] == "EXCESSIVE_CHANGE_IN_HAREKETLILER"

def test_hareketliler_empty_ok():
    r = check_hareketliler_change_pct([])
    assert r["ok"] is True

def test_hareketliler_all_none_ok():
    r = check_hareketliler_change_pct([None, None])
    assert r["ok"] is True

def test_hareketliler_custom_threshold():
    r = check_hareketliler_change_pct([5.0], max_pct=4.0)
    assert r["ok"] is False

def test_hareketliler_max_reported():
    r = check_hareketliler_change_pct([2.5, -7.3, 4.1])
    assert r["ok"] is True and r["max_pct"] == 7.3


# ── check_signal_count_consistency ───────────────────────────────────────────

def test_signal_count_consistent():
    r = check_signal_count_consistency(15, 5, 10, 30)
    assert r["ok"] is True and r["total"] == 30

def test_signal_count_mismatch():
    r = check_signal_count_consistency(15, 5, 10, 29)  # reported=29, computed=30
    assert r["ok"] is False and r["flag"] == "SIGNAL_COUNT_MISMATCH"

def test_signal_count_mismatch_fields():
    r = check_signal_count_consistency(5, 3, 2, 9)  # 10 computed, 9 reported
    assert r["computed"] == 10 and r["reported"] == 9

def test_signal_count_all_zero_ok():
    r = check_signal_count_consistency(0, 0, 0, 0)
    assert r["ok"] is True


# ── run_page_checks ───────────────────────────────────────────────────────────

GOOD_DATA = {
    "canvas_height": 400,
    "hareketliler_change_pcts": [2.5, -3.1, 1.8],
    "signal_counts": {"guclu": 15, "zayif": 5, "belirsiz": 10, "total": 30},
}

def test_run_page_checks_all_pass():
    r = run_page_checks(GOOD_DATA)
    assert r["errors"] == [] and r["failed_checks"] == []

def test_run_page_checks_canvas_fail():
    data = {**GOOD_DATA, "canvas_height": 0}
    r = run_page_checks(data)
    assert "CANVAS_HEIGHT_ZERO" in r["failed_checks"]

def test_run_page_checks_hareketliler_fail():
    data = {**GOOD_DATA, "hareketliler_change_pcts": [28.4, 2.0]}
    r = run_page_checks(data)
    assert "EXCESSIVE_CHANGE_IN_HAREKETLILER" in r["failed_checks"]

def test_run_page_checks_signal_count_fail():
    data = {**GOOD_DATA, "signal_counts": {"guclu": 15, "zayif": 5, "belirsiz": 10, "total": 29}}
    r = run_page_checks(data)
    assert "SIGNAL_COUNT_MISMATCH" in r["failed_checks"]

def test_run_page_checks_total_is_3():
    r = run_page_checks(GOOD_DATA)
    assert r["total_checks"] == 3

def test_run_page_checks_no_signal_counts():
    data = {"canvas_height": 300, "hareketliler_change_pcts": [2.0]}
    r = run_page_checks(data)
    assert r["errors"] == []  # no signal_counts key → skip check


# ── check_visual_diff ────────────────────────────────────────────────────────
# 100×100 = 10 000 pixels. fuzz=5% → channel diff must be > 12.75 to count as AE.
# All tests use (255,0,0) base and (0,255,0) patch so channel_diff=255 >> fuzz.

def test_visual_diff_identical():
    p = _make_solid_png((255, 0, 0))
    try:
        r = check_visual_diff(p, p)
        assert r["ok"] is True and r["diff_ratio"] == 0.0
    finally:
        import os; os.unlink(p)


def test_visual_diff_completely_different():
    before = _make_solid_png((255, 0, 0))
    after = _make_solid_png((0, 255, 0))
    try:
        r = check_visual_diff(before, after, threshold=0.02)
        assert r["ok"] is False and r["flag"] == "VISUAL_DIFF_EXCEEDED"
        assert r["diff_ratio"] > 0.99
    finally:
        import os; os.unlink(before); os.unlink(after)


def test_visual_diff_below_threshold():
    # 1% diff → below default 2% threshold
    before = _make_solid_png((255, 0, 0))
    after = _make_patched_png((255, 0, 0), (0, 255, 0), patch_count=100)  # 100/10000=1%
    try:
        r = check_visual_diff(before, after, threshold=0.02)
        assert r["ok"] is True and r["diff_ratio"] <= 0.01
    finally:
        import os; os.unlink(before); os.unlink(after)


def test_visual_diff_above_threshold():
    # 3% diff → exceeds default 2% threshold
    before = _make_solid_png((255, 0, 0))
    after = _make_patched_png((255, 0, 0), (0, 255, 0), patch_count=300)  # 300/10000=3%
    try:
        r = check_visual_diff(before, after, threshold=0.02)
        assert r["ok"] is False and r["flag"] == "VISUAL_DIFF_EXCEEDED"
    finally:
        import os; os.unlink(before); os.unlink(after)


def test_visual_diff_missing_before():
    after = _make_solid_png((0, 255, 0))
    try:
        r = check_visual_diff("/nonexistent/before.png", after)
        assert r["ok"] is False and r["flag"] == "VISUAL_DIFF_FILE_MISSING"
    finally:
        import os; os.unlink(after)


def test_visual_diff_missing_after():
    before = _make_solid_png((255, 0, 0))
    try:
        r = check_visual_diff(before, "/nonexistent/after.png")
        assert r["ok"] is False and r["flag"] == "VISUAL_DIFF_FILE_MISSING"
    finally:
        import os; os.unlink(before)


def test_visual_diff_saves_diff_image():
    before = _make_solid_png((255, 0, 0))
    after = _make_solid_png((0, 255, 0))
    diff_tmp = tempfile.NamedTemporaryFile(suffix=".png", delete=False)
    diff_tmp.close()
    try:
        r = check_visual_diff(before, after, threshold=0.02, diff_path=diff_tmp.name)
        assert r["ok"] is False
        assert import_os().path.isfile(diff_tmp.name)
    finally:
        import os
        os.unlink(before); os.unlink(after)
        if os.path.isfile(diff_tmp.name):
            os.unlink(diff_tmp.name)


def import_os():
    import os
    return os


def test_visual_diff_custom_threshold_tight():
    # With threshold=0.001 (0.1%), even 1% diff should fail
    before = _make_solid_png((255, 0, 0))
    after = _make_patched_png((255, 0, 0), (0, 255, 0), patch_count=100)
    try:
        r = check_visual_diff(before, after, threshold=0.001)
        assert r["ok"] is False and r["flag"] == "VISUAL_DIFF_EXCEEDED"
    finally:
        import os; os.unlink(before); os.unlink(after)


def test_visual_diff_default_threshold_constant():
    assert DEFAULT_VISUAL_DIFF_THRESHOLD == 0.02


# ── runner ───────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    tests = [
        test_canvas_height_normal, test_canvas_height_zero_fail,
        test_canvas_height_none_fail, test_canvas_height_one_ok,
        test_canvas_height_negative_fail,
        test_hareketliler_normal, test_hareketliler_glyho_selec_anomaly,
        test_hareketliler_at_threshold_fail, test_hareketliler_just_under_ok,
        test_hareketliler_negative_anomaly, test_hareketliler_empty_ok,
        test_hareketliler_all_none_ok, test_hareketliler_custom_threshold,
        test_hareketliler_max_reported,
        test_signal_count_consistent, test_signal_count_mismatch,
        test_signal_count_mismatch_fields, test_signal_count_all_zero_ok,
        test_run_page_checks_all_pass, test_run_page_checks_canvas_fail,
        test_run_page_checks_hareketliler_fail, test_run_page_checks_signal_count_fail,
        test_run_page_checks_total_is_3, test_run_page_checks_no_signal_counts,
        # P2.10 visual diff tests
        test_visual_diff_identical, test_visual_diff_completely_different,
        test_visual_diff_below_threshold, test_visual_diff_above_threshold,
        test_visual_diff_missing_before, test_visual_diff_missing_after,
        test_visual_diff_saves_diff_image, test_visual_diff_custom_threshold_tight,
        test_visual_diff_default_threshold_constant,
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
