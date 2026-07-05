"""CPO-1008 — signal-explanation cache-or-queue regression test.

Root cause: request path senkron Gemini call yapıyordu, _gemini_rate_acquire
thundering herd'de saniyelerce sleep döndürünce gunicorn worker o süre boyunca
bloke oluyordu (12-25s response, DEV-1005 log kanıtı). Fix /news'teki
cache-or-queue pattern'e taşındı: cache-miss → commentary anında dön, Gemini
zenginleştirme bg thread kuyruğunda (_on_demand_signal_explain_worker).

Bu test import app.py gerektirir — local Mac python3.9 ile ÇALIŞMAZ
(app.py 3.10+ bağımlılık ister, bkz. feedback_local_mac_no_python310).
VPS'te /root/bist30/venv/bin/python3 ile çalıştırılmalı.
"""

import os
import sys
import time

import pytest

if sys.version_info < (3, 10):
    # app.py `bool | None` gibi 3.10+ union syntax kullanıyor — local Mac (python3.9)
    # collection sırasında import hatası verir. P2.5 pre-push gate'i bu ortamda
    # çalışır, bu yüzden burada skip zorunlu (VPS Python 3.12'de gerçek çalışır).
    pytest.skip("app.py 3.10+ ister (bool | None syntax) — VPS venv'de (3.12) çalıştır", allow_module_level=True)

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import app


def _reset_state(ticker):
    with app._lock:
        app._signal_explain_cache.pop(ticker, None)
    with app._signal_explain_queue_lock:
        app._signal_explain_queue.pop(ticker, None)


def _fake_signal_data(sig="AL"):
    return {
        "signal": sig, "adx": 30.0, "di_plus": 28.0, "di_minus": 12.0,
        "e12": 105.0, "e99": 98.0, "st_bull": True,
        "price": 100.0, "sl_level": 95.0, "signal_bars": 3,
    }


def test_cache_miss_returns_immediately_without_gemini_call(monkeypatch):
    ticker = "TESTX1"
    _reset_state(ticker)

    monkeypatch.setattr(app, "GEMINI_API_KEY", "fake-key-for-test")
    monkeypatch.setattr(app, "_is_gemini_leader", lambda: True)

    gemini_calls = []

    def _fake_gemini_call(*args, **kwargs):
        gemini_calls.append(1)
        return "gemini-2.5-flash", "AI metni"

    monkeypatch.setattr(app, "_gemini_call", _fake_gemini_call)

    start = time.time()
    text = app.get_ai_signal_explanation(ticker, _fake_signal_data())
    elapsed = time.time() - start

    assert text is not None and "Yatırım tavsiyesi değildir." in text
    assert gemini_calls == [], "request path Gemini çağırmamalı (bg kuyruğa taşınmalı)"
    assert elapsed < 1.0, "cache-miss request path 1sn altında dönmeli (senkron Gemini yok)"

    with app._signal_explain_queue_lock:
        assert ticker in app._signal_explain_queue, "cache-miss ticker'ı bg kuyruğuna eklemeli"

    _reset_state(ticker)


def test_non_leader_never_queues(monkeypatch):
    ticker = "TESTX2"
    _reset_state(ticker)

    monkeypatch.setattr(app, "GEMINI_API_KEY", "fake-key-for-test")
    monkeypatch.setattr(app, "_is_gemini_leader", lambda: False)

    text = app.get_ai_signal_explanation(ticker, _fake_signal_data())

    assert text is not None
    with app._signal_explain_queue_lock:
        assert ticker not in app._signal_explain_queue, "non-leader kuyruğa eklememeli"

    _reset_state(ticker)


def test_enrich_writes_jittered_ttl_and_clears_via_worker_pattern(monkeypatch):
    ticker = "TESTX3"
    _reset_state(ticker)

    monkeypatch.setattr(app, "GEMINI_API_KEY", "fake-key-for-test")
    monkeypatch.setattr(app, "_is_gemini_leader", lambda: True)
    monkeypatch.setattr(app, "_save_explain_cache_to_disk", lambda: None)

    def _fake_gemini_call(*args, **kwargs):
        return "gemini-2.5-flash", "Güçlü trend devam ediyor, göstergeler yükseliş yönünde."

    monkeypatch.setattr(app, "_gemini_call", _fake_gemini_call)

    signal_data = _fake_signal_data()
    fallback = app.get_ai_signal_explanation(ticker, signal_data)
    assert fallback is not None

    app._enrich_signal_explanation(ticker, signal_data)

    with app._lock:
        cached = app._signal_explain_cache.get(ticker)
    assert cached is not None
    assert cached["failed"] is False
    lo = app._SIG_EXPLAIN_TTL - app._SIG_EXPLAIN_TTL_JITTER
    hi = app._SIG_EXPLAIN_TTL + app._SIG_EXPLAIN_TTL_JITTER
    assert lo <= cached["ttl"] <= hi, "TTL jitter aralık dışında"

    _reset_state(ticker)


def test_validation_rejects_contradicting_ai_text(monkeypatch):
    ticker = "TESTX4"
    _reset_state(ticker)

    monkeypatch.setattr(app, "GEMINI_API_KEY", "fake-key-for-test")
    monkeypatch.setattr(app, "_is_gemini_leader", lambda: True)
    monkeypatch.setattr(app, "_save_explain_cache_to_disk", lambda: None)

    def _fake_gemini_call(*args, **kwargs):
        return "gemini-2.5-flash", "Bu hissede düşüş beklenir, satış baskısı var."

    monkeypatch.setattr(app, "_gemini_call", _fake_gemini_call)

    signal_data = _fake_signal_data(sig="AL")
    app.get_ai_signal_explanation(ticker, signal_data)
    app._enrich_signal_explanation(ticker, signal_data)

    with app._lock:
        cached = app._signal_explain_cache.get(ticker)
    assert cached["failed"] is True, "AI sinyalle çelişince commentary fallback + failed=True olmalı"
    assert "Yatırım tavsiyesi değildir." in cached["text"]

    _reset_state(ticker)
