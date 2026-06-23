"""
Faz 12 P1 — Data Quality Validator: Playwright Smart Visual Checks
CPO-693: Visual integrity checks — canvas height, hareketliler anomaly, signal count
"""

import logging

logger = logging.getLogger(__name__)

MAX_HAREKETLILER_CHANGE_PCT = 11.0


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
