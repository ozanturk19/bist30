"""D-44b ilk adım — app.py ince bağlantı (AI Analist Notu okuma yolu).

Kaynak denetimi yerelde koşar (app.py import edilmez). Flask istemcisi bölümü app.py 3.10+ ister: yerelde
atlanır, VPS venv'de koşar (93d01dc deseni). Ağ yok, Gemini yok; not dosyaları tmp dizinde.
"""
import json
import os
import sys
from datetime import datetime, timedelta, timezone

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
APP_SRC = open(os.path.join(ROOT, "app.py"), encoding="utf-8").read()


def _block(start, end):
    return APP_SRC[APP_SRC.index(start):APP_SRC.index(end)]


# ----------------------------------------------------------------------------- kaynak denetimi (yerel)

def test_app_only_reads_notes_never_generates():
    blk = _block("# ── D-44b ilk adım: AI Analist Notu", "_mtf_cache     = {}")
    assert "ai_not_job.public_note(ticker)" in blk
    assert '@app.route("/api/hisse/<ticker>/ai-not")' in blk
    assert 'safe_json({"ai_not": _ai_not_ctx(ticker)})' in blk
    for banned in ("_gemini_call", "requests.", "generativelanguage", "ai_not_job.run", "threading", "_bg_start"):
        assert banned not in blk, banned
    assert "ticker in INDEX_TICKERS or ticker not in BIST100" in blk


def test_stock_page_passes_ssr_context():
    page = _block("def stock_page(ticker):", "_fundamentals_cache = {}")
    assert "ai_not=_ai_not_ctx(ticker))" in page
    assert "from pipeline import ai_not_job" in APP_SRC


def test_job_module_import_has_no_side_effects():
    import threading
    before = threading.active_count()
    from pipeline import ai_not_job  # noqa: F401
    assert threading.active_count() == before
    assert ai_not_job.enabled() is (os.environ.get("AI_NOT_ENABLED", "0").strip() == "1")


# ----------------------------------------------------------------------------- Flask (VPS)

needs_app = pytest.mark.skipif(sys.version_info < (3, 10), reason="app.py 3.10+ ister — VPS venv'de çalıştır")


@pytest.fixture()
def appmod(tmp_path, monkeypatch):
    if sys.version_info < (3, 10):
        pytest.skip("app.py 3.10+ ister")
    import app as appmod  # noqa: E402
    from pipeline import ai_not_job
    monkeypatch.setattr(ai_not_job, "OUT_DIR", str(tmp_path / "ai_not"))
    monkeypatch.setenv("AI_NOT_ENABLED", "1")
    appmod.app.config["TESTING"] = True
    return appmod


def _write_note(ticker, kapanis=None):
    from pipeline import ai_not_job
    day = kapanis or datetime.now(timezone(timedelta(hours=3))).date().isoformat()
    ai_not_job._atomic_write(ai_not_job.note_path(ticker), {
        "ticker": ticker, "not": "Trend durumu Yatay; 5 koşuldan 4'ü sağlanıyor.", "kapanis": day,
        "kapanis_label": "x", "etiket": ai_not_job.LABEL, "model": ai_not_job.MODEL})
    return day


@needs_app
def test_api_null_until_note_then_note(appmod, monkeypatch):
    c = appmod.app.test_client()
    r = c.get("/api/hisse/THYAO/ai-not")
    assert r.status_code == 200 and r.get_json() == {"ai_not": None}
    day = _write_note("THYAO")
    doc = c.get("/api/hisse/thyao/ai-not").get_json()["ai_not"]
    assert doc == {"ticker": "THYAO", "not": "Trend durumu Yatay; 5 koşuldan 4'ü sağlanıyor.", "kapanis": day,
                   "kapanis_label": "x", "etiket": "Yapay zekâ ile derlendi"}
    monkeypatch.setenv("AI_NOT_ENABLED", "0")
    assert c.get("/api/hisse/THYAO/ai-not").get_json() == {"ai_not": None}


@needs_app
def test_api_rejects_index_and_unknown(appmod):
    c = appmod.app.test_client()
    assert c.get("/api/hisse/XU030/ai-not").status_code == 404
    assert c.get("/api/hisse/YOKBOYLE/ai-not").status_code == 404


@needs_app
def test_stock_page_context_has_ai_not(appmod):
    from flask import template_rendered
    _write_note("THYAO")
    seen = []

    def rec(sender, template, context, **extra):
        seen.append(context)

    template_rendered.connect(rec, appmod.app)
    try:
        r = appmod.app.test_client().get("/hisse/THYAO")
    finally:
        template_rendered.disconnect(rec, appmod.app)
    assert r.status_code == 200
    ctx = next(c for c in seen if c.get("ticker") == "THYAO")
    assert ctx["ai_not"]["etiket"] == "Yapay zekâ ile derlendi"


@needs_app
def test_ctx_swallows_errors(appmod, monkeypatch):
    from pipeline import ai_not_job

    def boom(t):
        raise RuntimeError("x")

    monkeypatch.setattr(ai_not_job, "public_note", boom)
    assert appmod._ai_not_ctx("THYAO") is None
