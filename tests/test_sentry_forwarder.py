"""Tests for tools/sentry-forwarder.py — pure unit tests, no sentry_sdk install needed."""
import os
import sys
import types
import unittest
from unittest.mock import MagicMock, patch

import importlib.util

_tools_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "tools")
_spec = importlib.util.spec_from_file_location(
    "sentry_forwarder", os.path.join(_tools_dir, "sentry-forwarder.py")
)
sf = importlib.util.module_from_spec(_spec)
sys.modules["sentry_forwarder"] = sf
_spec.loader.exec_module(sf)


class TestParseJournalLine(unittest.TestCase):
    def test_standard_systemd_format(self):
        line = "Jun 25 09:00:00 myhost bist30[123]: ERROR fetch failed"
        parsed = sf.parse_journal_line(line)
        assert parsed["severity"] == "error"
        assert "ERROR fetch failed" in parsed["message"]
        assert parsed["timestamp"] is not None

    def test_critical_maps_to_fatal(self):
        line = "Jun 25 09:01:00 myhost bist30[1]: CRITICAL disk full"
        parsed = sf.parse_journal_line(line)
        assert parsed["severity"] == "fatal"

    def test_info_maps_to_info(self):
        line = "Jun 25 09:02:00 myhost bist30[1]: INFO startup complete"
        parsed = sf.parse_journal_line(line)
        assert parsed["severity"] == "info"

    def test_bare_line_no_crash(self):
        parsed = sf.parse_journal_line("some random line without systemd header")
        assert isinstance(parsed["severity"], str)
        assert isinstance(parsed["message"], str)
        assert parsed["timestamp"] is None


class TestShouldCapture(unittest.TestCase):
    def test_error_captured(self):
        assert sf.should_capture("Jun 25 10:00:00 h bist30[1]: ERROR boom") is True

    def test_critical_captured(self):
        assert sf.should_capture("CRITICAL system failure") is True

    def test_unhandled_exception_captured(self):
        assert sf.should_capture("UnhandledException in worker thread") is True

    def test_retry_exhausted_captured(self):
        assert sf.should_capture("RetryExhausted after 5 attempts") is True

    def test_subprocess_timeout_captured(self):
        assert sf.should_capture("SubprocessTimeout: yf fetch timed out") is True

    def test_info_not_captured(self):
        assert sf.should_capture("INFO cache refreshed") is False

    def test_debug_not_captured(self):
        assert sf.should_capture("DEBUG loop tick") is False


class TestCaptureToSentry(unittest.TestCase):
    def test_none_dsn_is_noop(self):
        # Must not raise even if sentry_sdk not installed
        sf.capture_to_sentry("ERROR something", None)  # no-op

    def test_empty_dsn_is_noop(self):
        sf.capture_to_sentry("CRITICAL boom", "")  # no-op

    def test_valid_dsn_calls_capture_message(self):
        mock_sdk = types.ModuleType("sentry_sdk")
        captured = {}

        def fake_init(**kwargs):
            captured["dsn"] = kwargs.get("dsn")

        def fake_capture_message(msg, level=None):
            captured["msg"] = msg
            captured["level"] = level

        mock_sdk.init = fake_init
        mock_sdk.capture_message = fake_capture_message

        with patch.dict(sys.modules, {"sentry_sdk": mock_sdk}):
            sf.capture_to_sentry("Jun 25 09:00:00 h bist30[1]: ERROR fetch failed", "https://fake@sentry.io/1")

        assert captured.get("level") == "error"
        assert "ERROR fetch failed" in captured.get("msg", "")


class TestForwardRecent(unittest.TestCase):
    def test_returns_count_of_matching_lines(self):
        fake_output = "\n".join([
            "Jun 25 09:00:00 h bist30[1]: ERROR fetch failed",
            "Jun 25 09:00:01 h bist30[1]: INFO startup",
            "Jun 25 09:00:02 h bist30[1]: CRITICAL disk full",
        ])
        with patch("sentry_forwarder.subprocess.run") as mock_run, \
             patch("sentry_forwarder.capture_to_sentry") as mock_cap:
            mock_run.return_value = MagicMock(stdout=fake_output, returncode=0)
            count = sf.forward_recent(dsn="https://fake@sentry.io/1", since_min=5)
        assert count == 2  # ERROR + CRITICAL, INFO skipped
        assert mock_cap.call_count == 2

    def test_journalctl_missing_returns_zero(self):
        with patch("sentry_forwarder.subprocess.run", side_effect=FileNotFoundError):
            count = sf.forward_recent(dsn="https://fake@sentry.io/1")
        assert count == 0


if __name__ == "__main__":
    unittest.main()
