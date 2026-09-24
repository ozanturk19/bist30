"""D-P0-2409 — Gemini günlük çağrı + aylık USD tavanı (gemini_budget.py)."""
import calendar
import os

import pytest

import gemini_budget as gb

_APP_PY = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "app.py")


@pytest.fixture
def path(tmp_path, monkeypatch):
    monkeypatch.setattr(gb, "ENABLED", True)
    monkeypatch.setattr(gb, "DAILY_CALLS", 3)
    monkeypatch.setattr(gb, "MONTHLY_USD", 1.0)
    return str(tmp_path / "usage.json")


def _ts(y, m, d, h=12):
    return calendar.timegm((y, m, d, h - 3, 0, 0))  # TR = UTC+3


def test_daily_cap_blocks_after_n_calls(path):
    now = _ts(2026, 9, 24)
    assert [gb.reserve(path, now)[0] for _ in range(4)] == [True, True, True, False]
    assert gb.reserve(path, now)[1] == "daily_cap"
    assert gb.status(path, now)["calls_today"] == 3


def test_daily_counter_resets_at_tr_midnight(path):
    for _ in range(3):
        gb.reserve(path, _ts(2026, 9, 24, 23))
    assert gb.reserve(path, _ts(2026, 9, 24, 23))[0] is False
    assert gb.reserve(path, _ts(2026, 9, 25, 0))[0] is True


def test_cost_uses_price_table():
    assert gb.cost_usd("gemini-2.5-flash-lite", 1_000_000, 1_000_000) == pytest.approx(0.50)
    assert gb.cost_usd("gemini-2.5-flash", 1_000_000, 1_000_000) == pytest.approx(2.80)
    # bilinmeyen model en pahalı satırdan fiyatlanır
    assert gb.cost_usd("gemini-x", 1_000_000, 0) == pytest.approx(0.30)


def test_monthly_cap_blocks_and_alerts_once(path):
    now = _ts(2026, 9, 24)
    assert gb.reserve(path, now)[0] is True
    gb.record("gemini-2.5-flash", 0, 500_000, path, now)  # 1,25 $ > 1 $ tavan
    assert gb.reserve(path, now) == (False, "monthly_cap_new")
    assert gb.reserve(path, now) == (False, "monthly_cap")   # uyarı ikinci kez tetiklenmez
    assert gb.status(path, now)["usd_month"] == pytest.approx(1.25)


def test_month_rollover_clears_cap(path):
    gb.record("gemini-2.5-flash", 0, 500_000, path, _ts(2026, 9, 30))
    assert gb.reserve(path, _ts(2026, 9, 30))[0] is False
    assert gb.reserve(path, _ts(2026, 10, 1))[0] is True
    assert gb.status(path, _ts(2026, 10, 1))["usd_month"] == 0


def test_disabled_switch_blocks_everything(path, monkeypatch):
    monkeypatch.setattr(gb, "ENABLED", False)
    assert gb.reserve(path, _ts(2026, 9, 24)) == (False, "disabled")


def test_unwritable_usage_file_fails_closed(tmp_path):
    bad = str(tmp_path / "yok-dizin" / "usage.json")
    assert gb.reserve(bad, _ts(2026, 9, 24)) == (False, "usage_file_error")


def test_corrupt_usage_file_starts_blank(path):
    with open(path, "w") as f:
        f.write("{bozuk")
    assert gb.reserve(path, _ts(2026, 9, 24))[0] is True


def test_app_wiring_grounding_off_reserve_before_request_health_fields():
    src = open(_APP_PY, encoding="utf-8").read()
    call = src[src.index("def _gemini_call("):src.index("def get_ai_news(")]
    assert call.index("gemini_budget.reserve()") < call.index("requests.post(")
    assert "use_search and gemini_budget.GROUNDING" in call
    assert "gemini_budget.record(" in call
    news = src[src.index("_GEMINI_NEWS_ATTEMPTS = ["):src.index("_GEMINI_EXPLAIN_ATTEMPTS = [")]
    assert "True" not in news, "haber denemelerinde grounding açık kalmamalı"
    assert news.index("flash-lite") < news.index('"gemini-2.5-flash"')
    for k in ("gemini_calls_today", "gemini_usd_month"):
        assert f'resp["{k}"]' in src
    assert "gemini_call=no (grounding kapalı)" in src
