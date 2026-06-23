"""
Faz 12 P1 — Data Quality Validator: Email QA Pre-Send Check
CPO-693: Validate signal changes before building/sending email
"""

import logging

logger = logging.getLogger(__name__)

MAX_DAILY_CHANGES = 100


def validate_email_pre_send(changes, max_count=MAX_DAILY_CHANGES, context=""):
    """
    Pre-send guard: validate changes list before building signal email.

    changes: list of (ticker, old_signal, new_signal, stock_dict) tuples
    max_count: BIST30 has 30 stocks — >100 in one send = likely buffer contamination

    Returns: {"ok": True, "count": N}
          or {"ok": False, "flag": "...", ...}
    """
    n = len(changes)

    if n == 0:
        logger.warning("EMAIL_QA: empty changes list (context=%s)", context)
        return {"ok": False, "flag": "EMAIL_EMPTY_CHANGES", "count": 0, "context": context}

    if n > max_count:
        logger.warning(
            "EMAIL_QA: %d changes > %d daily limit — possible buffer contamination (context=%s)",
            n, max_count, context,
        )
        return {
            "ok": False, "flag": "EMAIL_EXCESSIVE_CHANGES",
            "count": n, "max_count": max_count, "context": context,
            "msg": f"{n} changes > {max_count} daily limit",
        }

    malformed = [
        i for i, c in enumerate(changes)
        if not (isinstance(c, (tuple, list)) and len(c) >= 3)
    ]
    if malformed:
        logger.warning("EMAIL_QA: malformed change tuples at indices %s", malformed)
        return {
            "ok": False, "flag": "EMAIL_MALFORMED_CHANGES",
            "count": n, "indices": malformed,
        }

    tickers = [c[0] for c in changes]
    seen = set()
    dupes = [t for t in tickers if t in seen or seen.add(t)]  # type: ignore[func-returns-value]
    if dupes:
        logger.warning("EMAIL_QA: duplicate tickers in changes: %s", dupes)
        return {
            "ok": False, "flag": "EMAIL_DUPLICATE_TICKERS",
            "count": n, "duplicates": list(set(dupes)),
        }

    return {"ok": True, "count": n, "context": context}
