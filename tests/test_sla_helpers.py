"""Tests for tools/_sla_helpers.py — SPEC-016 pre-implementation."""

import json
import os
import sys
import tempfile

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "tools"))
from _sla_helpers import (
    _build_sla_payload,
    _compute_sla_freshness,
    _compute_sla_smoke,
    _count_nginx_5xx,
)


# ── _count_nginx_5xx ─────────────────────────────────────────────────────────

def test_nginx_5xx_no_log_returns_minus1(tmp_path, monkeypatch):
    """Non-existent log file → graceful -1."""
    import _sla_helpers
    monkeypatch.setattr(
        "subprocess.run",
        lambda *a, **kw: (_ for _ in ()).throw(FileNotFoundError("no log")),
    )
    assert _count_nginx_5xx() == -1


def test_nginx_5xx_mock_log(monkeypatch):
    """awk returning '3' → count == 3."""
    class FakeResult:
        stdout = "3\n"
    monkeypatch.setattr("subprocess.run", lambda *a, **kw: FakeResult())
    assert _count_nginx_5xx() == 3


def test_nginx_5xx_zero_count(monkeypatch):
    """awk returning '0' → count == 0."""
    class FakeResult:
        stdout = "0\n"
    monkeypatch.setattr("subprocess.run", lambda *a, **kw: FakeResult())
    assert _count_nginx_5xx() == 0


# ── _compute_sla_freshness ────────────────────────────────────────────────────

def test_freshness_taze_5min():
    """5 minutes (300s) → TAZE."""
    result = _compute_sla_freshness(300)
    assert result["status"] == "TAZE"
    assert result["age_min"] == pytest.approx(5.0)


def test_freshness_stale_33min():
    """33 minutes (2000s) — between 30dk and 60dk → STALE."""
    result = _compute_sla_freshness(2000)
    assert result["status"] == "STALE"


def test_freshness_critical_35min():
    """35 minutes (2100s) — > 30dk (threshold * 2 = 3600, but threshold=1800, so 2100 < 3600) → STALE not CRITICAL."""
    result = _compute_sla_freshness(2100)
    assert result["status"] == "STALE"


def test_freshness_critical_65min():
    """65 minutes (3900s) — > threshold * 2 → CRITICAL."""
    result = _compute_sla_freshness(3900)
    assert result["status"] == "CRITICAL"


def test_freshness_boundary_exactly_30min():
    """Exactly at threshold (1800s) → STALE (not TAZE)."""
    result = _compute_sla_freshness(1800)
    assert result["status"] == "STALE"


# ── _compute_sla_smoke ────────────────────────────────────────────────────────

def test_smoke_pass_from_file():
    """6/6 PASS file → result PASS."""
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".json", delete=False
    ) as f:
        json.dump({"pass": 6, "total": 6, "ts": "2026-06-25 09:47", "result": "PASS"}, f)
        path = f.name
    try:
        result = _compute_sla_smoke(path)
        assert result["result"] == "PASS"
        assert result["pass"] == 6
        assert result["total"] == 6
        assert result["ts"] == "2026-06-25 09:47"
    finally:
        os.unlink(path)


def test_smoke_fail_from_file():
    """4/6 FAIL file → result FAIL."""
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".json", delete=False
    ) as f:
        json.dump({"pass": 4, "total": 6, "ts": "2026-06-25 10:12", "result": "FAIL"}, f)
        path = f.name
    try:
        result = _compute_sla_smoke(path)
        assert result["result"] == "FAIL"
        assert result["pass"] == 4
    finally:
        os.unlink(path)


def test_smoke_missing_file_graceful():
    """No file at path → graceful None default (not exception)."""
    result = _compute_sla_smoke("/tmp/bist30-smoke-nonexistent-zzz.json")
    assert result["result"] is None
    assert result["pass"] is None


# ── _build_sla_payload ────────────────────────────────────────────────────────

def test_build_sla_payload_shape(monkeypatch):
    """_build_sla_payload returns dict with all 3 top-level keys."""
    class FakeResult:
        stdout = "0\n"
    monkeypatch.setattr("subprocess.run", lambda *a, **kw: FakeResult())
    payload = _build_sla_payload(
        stocks_age_s=300,
        smoke_result_path="/tmp/bist30-smoke-nonexistent-zzz.json",
    )
    assert "freshness" in payload
    assert "smoke" in payload
    assert "nginx_5xx_24h" in payload
    assert payload["freshness"]["status"] == "TAZE"
    assert payload["nginx_5xx_24h"] == 0
