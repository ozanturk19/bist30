"""
Faz 12 P1 — Data Quality Validator: Playwright Smart Visual Checks
CPO-693: Visual integrity checks — canvas height, hareketliler anomaly, signal count
P2.10: check_visual_diff — pre-deploy pixel-level regression (threshold 2%)
"""

import logging
import os

logger = logging.getLogger(__name__)

MAX_HAREKETLILER_CHANGE_PCT = 11.0
DEFAULT_VISUAL_DIFF_THRESHOLD = 0.02  # 2% pixel diff ratio


def check_canvas_height(canvas_height):
    """
    BIST100 chart canvas must be rendered (height > 0).
    canvas_height: int or None (extracted from page)
    """
    if canvas_height is None:
        logger.warning("VISUAL: canvas_height is None (page extract failed?)")
        return {"ok": False, "flag": "CANVAS_HEIGHT_NONE", "value": None}
    if canvas_height <= 0:
        logger.warning("VISUAL: canvas_height=%s (chart not rendered)", canvas_height)
        return {"ok": False, "flag": "CANVAS_HEIGHT_ZERO", "value": canvas_height}
    return {"ok": True, "canvas_height": canvas_height}


def check_hareketliler_change_pct(change_pct_list, max_pct=MAX_HAREKETLILER_CHANGE_PCT):
    """
    Hareketliler section: max abs(change_pct) must be < 11%.
    Detects GLYHO/SELEC-style anomalies showing in the page.
    change_pct_list: list[float] — change_pct values visible in hareketliler
    """
    if not change_pct_list:
        return {"ok": True, "note": "empty_list"}
    clean = [p for p in change_pct_list if p is not None]
    if not clean:
        return {"ok": True, "note": "all_none"}
    max_val = max(abs(p) for p in clean)
    if max_val >= max_pct:
        logger.warning("VISUAL: hareketliler max_pct=%.2f >= threshold %.2f", max_val, max_pct)
        return {
            "ok": False, "flag": "EXCESSIVE_CHANGE_IN_HAREKETLILER",
            "max_pct": round(max_val, 2), "threshold": max_pct,
        }
    return {"ok": True, "max_pct": round(max_val, 2)}


def check_signal_count_consistency(guclu, zayif, belirsiz, reported_total):
    """
    Signal count must be internally consistent:
    sum(güçlü + zayıf + belirsiz) == reported total in page header.
    """
    computed = guclu + zayif + belirsiz
    if computed != reported_total:
        logger.warning(
            "VISUAL: signal_count mismatch: computed=%d reported=%d (g=%d z=%d b=%d)",
            computed, reported_total, guclu, zayif, belirsiz,
        )
        return {
            "ok": False, "flag": "SIGNAL_COUNT_MISMATCH",
            "computed": computed, "reported": reported_total,
            "guclu": guclu, "zayif": zayif, "belirsiz": belirsiz,
        }
    return {"ok": True, "total": computed}


def run_page_checks(data):
    """
    Run all visual checks against data extracted from page.

    data: {
        "canvas_height": int | None,
        "hareketliler_change_pcts": list[float],
        "signal_counts": {
            "guclu": int, "zayif": int, "belirsiz": int, "total": int
        }
    }
    Returns: {"total_checks": N, "errors": [...], "failed_checks": [...]}
    """
    errors = []

    r = check_canvas_height(data.get("canvas_height"))
    if not r["ok"]:
        errors.append(r)

    r = check_hareketliler_change_pct(data.get("hareketliler_change_pcts", []))
    if not r["ok"]:
        errors.append(r)

    sc = data.get("signal_counts", {})
    if sc:
        r = check_signal_count_consistency(
            sc.get("guclu", 0), sc.get("zayif", 0),
            sc.get("belirsiz", 0), sc.get("total", 0),
        )
        if not r["ok"]:
            errors.append(r)

    failed = [e["flag"] for e in errors]
    if errors:
        logger.warning("VISUAL: %d check(s) failed: %s", len(errors), failed)
    return {"total_checks": 3, "errors": errors, "failed_checks": failed}


def extract_and_check(url, headless=True, timeout_ms=15000):
    """
    Run visual checks against a live URL using Playwright.
    Requires: playwright installed + playwright install chromium

    Returns run_page_checks() result dict, or {"ok": False, "flag": "PLAYWRIGHT_ERROR", "error": ...}
    """
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        return {"ok": False, "flag": "PLAYWRIGHT_NOT_INSTALLED"}

    try:
        with sync_playwright() as pw:
            browser = pw.chromium.launch(headless=headless)
            page = browser.new_page()
            page.goto(url, timeout=timeout_ms, wait_until="networkidle")

            canvas_height = page.evaluate(
                "() => { const c = document.querySelector('canvas'); return c ? c.clientHeight : 0; }"
            )

            change_pcts = page.evaluate("""
                () => {
                    const els = document.querySelectorAll('[data-change-pct]');
                    return Array.from(els).map(el => parseFloat(el.getAttribute('data-change-pct'))).filter(n => !isNaN(n));
                }
            """)

            signal_counts = page.evaluate("""
                () => {
                    const get = (sel) => {
                        const el = document.querySelector(sel);
                        return el ? parseInt(el.textContent.replace(/\\D/g, '')) || 0 : 0;
                    };
                    return {
                        guclu: get('[data-count="guclu"]'),
                        zayif: get('[data-count="zayif"]'),
                        belirsiz: get('[data-count="belirsiz"]'),
                        total: get('[data-count="total"]'),
                    };
                }
            """)

            browser.close()

        return run_page_checks({
            "canvas_height": canvas_height,
            "hareketliler_change_pcts": change_pcts,
            "signal_counts": signal_counts,
        })

    except Exception as e:
        logger.error("VISUAL: extract_and_check failed: %s", e)
        return {"ok": False, "flag": "PLAYWRIGHT_ERROR", "error": str(e)}


# ── P2.10 Visual Regression ───────────────────────────────────────────────────

def check_visual_diff(before_img, after_img, threshold=DEFAULT_VISUAL_DIFF_THRESHOLD,
                      diff_path=None, fuzz=0.05):
    """
    Pixel-level image diff between two PNG files. Primary: Pillow; fallback: ImageMagick.

    Mirrors visual-diff.sh behaviour (-fuzz 5% / AE metric).
    threshold: float ratio (0.02 = 2%).
    diff_path: optional path to write highlighted diff PNG on failure.
    fuzz: channel tolerance as fraction of 255 (0.05 = 5%, matches shell script).

    Returns dict with keys: ok, diff_ratio, threshold. On failure also: flag, ae, total_pixels.
    """
    if not os.path.isfile(before_img):
        return {"ok": False, "flag": "VISUAL_DIFF_FILE_MISSING", "missing": before_img}
    if not os.path.isfile(after_img):
        return {"ok": False, "flag": "VISUAL_DIFF_FILE_MISSING", "missing": after_img}

    try:
        from PIL import Image
        import numpy as np

        img_a = Image.open(before_img).convert("RGB")
        img_b = Image.open(after_img).convert("RGB")
        if img_a.size != img_b.size:
            img_b = img_b.resize(img_a.size, Image.LANCZOS)

        arr_a = np.array(img_a, dtype=np.int32)
        arr_b = np.array(img_b, dtype=np.int32)

        channel_diff = np.max(np.abs(arr_a - arr_b), axis=2)
        fuzz_px = int(fuzz * 255)
        ae = int(np.sum(channel_diff > fuzz_px))

        total_pixels = arr_a.shape[0] * arr_a.shape[1]
        diff_ratio = ae / total_pixels if total_pixels > 0 else 0.0

        if diff_ratio > threshold and diff_path:
            diff_arr = np.zeros((*arr_a.shape[:2], 3), dtype=np.uint8)
            diff_arr[channel_diff > fuzz_px] = [255, 0, 0]
            diff_dir = os.path.dirname(diff_path)
            if diff_dir:
                os.makedirs(diff_dir, exist_ok=True)
            Image.fromarray(diff_arr).save(diff_path)

        if diff_ratio > threshold:
            logger.warning(
                "VISUAL_DIFF: %s ratio=%.4f > threshold=%.4f (ae=%d/%d)",
                os.path.basename(before_img), diff_ratio, threshold, ae, total_pixels,
            )
            return {
                "ok": False, "flag": "VISUAL_DIFF_EXCEEDED",
                "diff_ratio": round(diff_ratio, 4), "threshold": threshold,
                "ae": ae, "total_pixels": total_pixels,
                "diff_path": diff_path,
            }

        return {
            "ok": True, "diff_ratio": round(diff_ratio, 4),
            "threshold": threshold, "ae": ae, "total_pixels": total_pixels,
        }

    except ImportError:
        return _check_visual_diff_imagemagick(before_img, after_img, threshold, diff_path, fuzz)
    except Exception as e:
        logger.error("VISUAL_DIFF: %s", e)
        return {"ok": False, "flag": "VISUAL_DIFF_ERROR", "error": str(e)}


def _check_visual_diff_imagemagick(before_img, after_img, threshold, diff_path, fuzz):
    """Fallback to ImageMagick compare (used when Pillow not available)."""
    import subprocess
    try:
        pixels_out = subprocess.run(
            ["identify", "-format", "%[fx:w*h]", before_img],
            capture_output=True, text=True, timeout=10,
        )
        total_pixels = int(pixels_out.stdout.strip()) if pixels_out.returncode == 0 else 1

        fuzz_pct = f"{int(fuzz * 100)}%"
        out_arg = diff_path if diff_path else "/dev/null"
        result = subprocess.run(
            ["compare", "-metric", "AE", "-fuzz", fuzz_pct, before_img, after_img, out_arg],
            capture_output=True, text=True, timeout=30,
        )
        raw = (result.stderr or result.stdout).strip()
        try:
            ae = int(raw.split()[0])
        except (ValueError, IndexError):
            ae = 0

        diff_ratio = ae / total_pixels if total_pixels > 0 else 0.0
        if diff_ratio > threshold:
            return {
                "ok": False, "flag": "VISUAL_DIFF_EXCEEDED",
                "diff_ratio": round(diff_ratio, 4), "threshold": threshold,
                "ae": ae, "total_pixels": total_pixels,
            }
        return {"ok": True, "diff_ratio": round(diff_ratio, 4), "threshold": threshold}

    except FileNotFoundError:
        return {"ok": False, "flag": "VISUAL_DIFF_NO_BACKEND"}
    except Exception as e:
        logger.error("VISUAL_DIFF (imagemagick): %s", e)
        return {"ok": False, "flag": "VISUAL_DIFF_ERROR", "error": str(e)}
