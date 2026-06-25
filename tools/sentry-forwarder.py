#!/usr/bin/env python3
"""
Standalone Sentry forwarder: journalctl pattern matching -> Sentry capture.
Usage (crontab): */5 * * * * /root/bist30/tools/sentry-forwarder.py
Requires: SENTRY_DSN env var or pass dsn explicitly.
"""
import os
import re
import subprocess
import sys
from datetime import datetime, timezone

CAPTURE_PATTERN = re.compile(
    r"ERROR|CRITICAL|UnhandledException|RetryExhausted|SubprocessTimeout"
)

# systemd journal line: "May 21 12:34:56 hostname unit[pid]: LEVEL message"
JOURNAL_RE = re.compile(
    r"^(?P<month>\w+)\s+(?P<day>\d+)\s+(?P<time>\S+)\s+\S+\s+\S+:\s+(?P<body>.+)$"
)

SEVERITY_MAP = {
    "CRITICAL": "fatal",
    "ERROR": "error",
    "WARNING": "warning",
    "INFO": "info",
    "DEBUG": "debug",
}


def parse_journal_line(line: str) -> dict:
    """Extract severity, message, and timestamp from a systemd journal line."""
    m = JOURNAL_RE.match(line.strip())
    body = m.group("body") if m else line.strip()
    timestamp = None
    if m:
        try:
            year = datetime.now(timezone.utc).year
            ts_str = f"{m.group('month')} {m.group('day')} {m.group('time')} {year}"
            timestamp = datetime.strptime(ts_str, "%b %d %H:%M:%S %Y")
        except ValueError:
            pass

    severity = "info"
    for key, sentry_level in SEVERITY_MAP.items():
        if key in body:
            severity = sentry_level
            break

    return {"severity": severity, "message": body, "timestamp": timestamp}


def should_capture(line: str) -> bool:
    """Return True if the line matches patterns that warrant Sentry capture."""
    return bool(CAPTURE_PATTERN.search(line))


def capture_to_sentry(line: str, dsn: str) -> None:
    """Send a parsed journal line to Sentry. No-op if dsn is None/empty."""
    if not dsn:
        return
    try:
        import sentry_sdk  # type: ignore
    except ImportError:
        print("sentry_sdk not installed; skipping capture", file=sys.stderr)
        return

    sentry_sdk.init(dsn=dsn, traces_sample_rate=0.0)
    parsed = parse_journal_line(line)
    sentry_sdk.capture_message(parsed["message"], level=parsed["severity"])


def forward_recent(dsn: str, since_min: int = 5) -> int:
    """
    Read journalctl output for the last `since_min` minutes and forward
    matching lines to Sentry. Returns count of captured events.
    """
    since = f"{since_min} min ago"
    try:
        result = subprocess.run(
            ["journalctl", "-u", "bist30", "--since", since, "--no-pager", "-o", "short"],
            capture_output=True,
            text=True,
            timeout=15,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired) as exc:
        print(f"journalctl error: {exc}", file=sys.stderr)
        return 0

    count = 0
    for line in result.stdout.splitlines():
        if should_capture(line):
            capture_to_sentry(line, dsn)
            count += 1
    return count


if __name__ == "__main__":
    dsn = os.environ.get("SENTRY_DSN", "")
    if not dsn:
        print("SENTRY_DSN not set; exiting", file=sys.stderr)
        sys.exit(0)
    captured = forward_recent(dsn)
    print(f"sentry-forwarder: {captured} events forwarded")
