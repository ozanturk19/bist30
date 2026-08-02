"""CPO-1206 §7 / SEO9 #6 — nginx 5xx-oranı monitor test suite.

Kök neden: 12 restart / 0 alarm (CPO-1206 §8) — restart/deploy kaynaklı 5xx
patlamaları görünmezdi. Bu test tools/nginx_5xx_monitor.py'nin saf
fonksiyonlarını (parse_line, parse_window, should_alert, run) doğrular:
timestamp/offset ayrıştırma, trailing pencere filtresi, eşik kararı, ve
uçtan-uca run() dosya I/O'su (ALERT.md'ye yalnız eşik aşılınca yazma).
"""

import datetime
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tools import nginx_5xx_monitor as mon


def _line(time_str, status, path="/api/data"):
    return (
        f'2a01:4f9:c013:41f2::1 - - [{time_str}] "GET {path} HTTP/2.0" {status} '
        f'36648 "-" "Mozilla/5.0" borsapusula.com {status} 0.031 0.031\n'
    )


# ── parse_line ───────────────────────────────────────────────────────────

def test_parse_line_extracts_utc_datetime_and_status():
    parsed = mon.parse_line(_line("02/Aug/2026:06:02:30 +0000", 502))
    assert parsed is not None
    ts, status = parsed
    assert status == 502
    assert ts == datetime.datetime(2026, 8, 2, 6, 2, 30, tzinfo=datetime.timezone.utc)


def test_parse_line_converts_non_utc_offset():
    parsed = mon.parse_line(_line("02/Aug/2026:09:02:30 +0300", 200))
    ts, status = parsed
    assert ts == datetime.datetime(2026, 8, 2, 6, 2, 30, tzinfo=datetime.timezone.utc)


def test_parse_line_returns_none_for_garbage():
    assert mon.parse_line("not a log line\n") is None


# ── parse_window ─────────────────────────────────────────────────────────

def test_parse_window_counts_5xx_within_trailing_window():
    now = datetime.datetime(2026, 8, 2, 6, 5, 0, tzinfo=datetime.timezone.utc)
    lines = [
        _line("02/Aug/2026:06:04:00 +0000", 502),
        _line("02/Aug/2026:06:04:10 +0000", 200),
        _line("02/Aug/2026:06:04:20 +0000", 503),
        _line("02/Aug/2026:06:04:30 +0000", 404),
    ]
    total, five_xx, by_status = mon.parse_window(lines, now, window_minutes=5)
    assert total == 4
    assert five_xx == 2
    assert by_status == {502: 1, 503: 1}


def test_parse_window_excludes_lines_outside_window():
    now = datetime.datetime(2026, 8, 2, 6, 10, 0, tzinfo=datetime.timezone.utc)
    lines = [
        _line("02/Aug/2026:06:03:00 +0000", 500),  # 7dk önce — pencere dışı
        _line("02/Aug/2026:06:08:00 +0000", 500),  # 2dk önce — pencere içi
    ]
    total, five_xx, _ = mon.parse_window(lines, now, window_minutes=5)
    assert total == 1
    assert five_xx == 1


def test_parse_window_ignores_unparseable_lines():
    now = datetime.datetime(2026, 8, 2, 6, 5, 0, tzinfo=datetime.timezone.utc)
    lines = ["garbage\n", _line("02/Aug/2026:06:04:00 +0000", 200)]
    total, five_xx, _ = mon.parse_window(lines, now, window_minutes=5)
    assert total == 1
    assert five_xx == 0


# ── should_alert ─────────────────────────────────────────────────────────

def test_should_alert_below_threshold_is_false():
    assert mon.should_alert(2, threshold_abs=3) is False


def test_should_alert_at_threshold_is_true():
    assert mon.should_alert(3, threshold_abs=3) is True


def test_should_alert_single_incidental_5xx_does_not_trigger():
    # CPO-1206 §8'in tam karşıtı olmasın diye: 1 istek 1 hata (%100 oran)
    # ama mutlak sayım eşiğin altında — spam alarm doğurmamalı.
    assert mon.should_alert(1, threshold_abs=3) is False


# ── run (uçtan-uca dosya I/O) ────────────────────────────────────────────

def test_run_writes_alert_md_when_threshold_exceeded(tmp_path):
    log_path = tmp_path / "access.log"
    log_path.write_text(
        _line("02/Aug/2026:06:04:00 +0000", 502)
        + _line("02/Aug/2026:06:04:05 +0000", 502)
        + _line("02/Aug/2026:06:04:10 +0000", 503)
    )
    alert_md = tmp_path / "ALERT.md"
    alert_md.write_text("")
    state_log = tmp_path / "state.log"

    now = datetime.datetime(2026, 8, 2, 6, 5, 0, tzinfo=datetime.timezone.utc)
    total, five_xx, alerted = mon.run(
        log_path=str(log_path),
        alert_md_path=str(alert_md),
        state_log_path=str(state_log),
        window_minutes=5,
        threshold_abs=3,
        now_utc=now,
    )

    assert (total, five_xx, alerted) == (3, 3, True)
    content = alert_md.read_text()
    assert "P1 NGINX_5XX" in content
    assert "5xx=3/3" in content
    assert state_log.read_text().strip() != ""


def test_run_does_not_write_alert_md_when_below_threshold(tmp_path):
    log_path = tmp_path / "access.log"
    log_path.write_text(_line("02/Aug/2026:06:04:00 +0000", 502))
    alert_md = tmp_path / "ALERT.md"
    alert_md.write_text("")
    state_log = tmp_path / "state.log"

    now = datetime.datetime(2026, 8, 2, 6, 5, 0, tzinfo=datetime.timezone.utc)
    total, five_xx, alerted = mon.run(
        log_path=str(log_path),
        alert_md_path=str(alert_md),
        state_log_path=str(state_log),
        window_minutes=5,
        threshold_abs=3,
        now_utc=now,
    )

    assert (total, five_xx, alerted) == (1, 1, False)
    assert alert_md.read_text() == ""


def test_run_missing_log_file_does_not_crash(tmp_path):
    alert_md = tmp_path / "ALERT.md"
    alert_md.write_text("")
    state_log = tmp_path / "state.log"

    total, five_xx, alerted = mon.run(
        log_path=str(tmp_path / "does-not-exist.log"),
        alert_md_path=str(alert_md),
        state_log_path=str(state_log),
    )

    assert (total, five_xx, alerted) == (0, 0, False)
