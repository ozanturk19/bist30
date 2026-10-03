"""D-57 app.py ince bağlantı testleri.

Kaynak denetimi bölümü yerelde de koşar (app.py import edilmez). Flask istemcisi bölümü app.py 3.10+
ister: yerelde atlanır, VPS venv'de koşar. Ağ yok, Gemini yok: `_gemini_call` ve `requests.post`
sahteyle değiştirilir; üretim sayaç/sigorta dosyalarına dokunulmaz.
"""
from __future__ import annotations

import json
import os
import sys
from datetime import datetime

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
FX = os.path.join(ROOT, "tests", "fixtures", "gundem_haber")
APP_SRC = open(os.path.join(ROOT, "app.py"), encoding="utf-8").read()


def _block(start, end):
    return APP_SRC[APP_SRC.index(start):APP_SRC.index(end)]


# ----------------------------------------------------------------------------- kaynak denetimi (yerel)

def test_gemini_call_json_mode_and_timeout_cap_are_opt_in():
    call = _block("def _gemini_call(", "def _compute_signal_commentary(")
    assert "json_mode=False, timeout_cap=None" in call
    assert "_GEMINI_TIMEOUT_CAP if timeout_cap is None else timeout_cap" in call
    i = call.index('"responseMimeType"')
    assert call.rfind("elif json_mode:", 0, i) > call.rfind("if use_search:", 0, i)   # grounding ile birlikte değil
    assert call.index("gemini_budget.reserve()") < call.index("requests.post(")


def test_d57_block_uses_capped_path_without_grounding():
    blk = _block("# ── D-57 Gündem haber derlemesi", '@app.route("/api/hisse/<ticker>/signal-explanation")')
    assert "_gemini_call(prompt, [(gundem_haber.MODEL, False)]" in blk    # use_search=False
    assert "requests." not in blk and "generativelanguage" not in blk     # tek çağrı yolu _gemini_call
    assert "budget_status=gemini_budget.status()" in blk
    assert "read_cb_state(_GEMINI_QUOTA_CB_PATH)" in blk                 # manual_hold / sigorta
    assert 'os.environ.get("BP_ROLE") == "macro" and gundem_haber.ENABLED' in blk
    assert '@app.route("/api/gundem-haber")' in blk
    assert 'p == "/" or p == "/haberler" or p.startswith("/haberler/")' in blk


def test_module_default_model_is_flash_lite():
    import gundem_haber
    assert gundem_haber.MODEL == "gemini-2.5-flash-lite"
    assert gundem_haber.MAX_CALLS == 4


# ----------------------------------------------------------------------------- Flask (VPS)

needs_app = pytest.mark.skipif(sys.version_info < (3, 10), reason="app.py 3.10+ ister — VPS venv'de çalıştır")


@pytest.fixture()
def appmod(tmp_path, monkeypatch):
    if sys.version_info < (3, 10):
        pytest.skip("app.py 3.10+ ister")
    import app as appmod  # noqa: E402
    import gundem_haber
    monkeypatch.setattr(gundem_haber, "OUT_DIR", str(tmp_path / "gundem_haber"))
    monkeypatch.setattr(gundem_haber, "INPUT_DIR", os.path.join(FX, "girdi"))
    monkeypatch.setattr(gundem_haber, "ENABLED", True)
    gundem_haber._CACHE.clear()
    appmod.app.config["TESTING"] = True
    return appmod


@needs_app
def test_api_empty_then_latest(appmod, tmp_path):
    import gundem_haber
    c = appmod.app.test_client()
    r = c.get("/api/gundem-haber")
    assert r.status_code == 200 and r.get_json() == {"baski": None, "baski_label": None, "maddeler": []}
    doc = {"baski": "2026-10-01T19:30:00+03:00", "baski_label": "1 Ekim 2026 · 19:30",
           "maddeler": [{"id": "g-20261001-11", "kategori": "Türkiye", "baslik": "b", "ozet": "o", "hisseler": [],
                         "kaynaklar": [{"ad": "AA", "url": "https://www.aa.com.tr/x", "tarih": "2026-10-01"}],
                         "ai": True, "onemli": False}]}
    gundem_haber._atomic_write(os.path.join(gundem_haber.OUT_DIR, "latest.json"), doc)
    assert c.get("/api/gundem-haber").get_json() == doc


@needs_app
def test_ssr_context_only_on_home_and_haberler(appmod):
    import gundem_haber
    gundem_haber._atomic_write(os.path.join(gundem_haber.OUT_DIR, "latest.json"),
                               {"baski": "x", "baski_label": "y", "maddeler": [{"id": "g"}]})
    for path, has in (("/", True), ("/haberler", True), ("/haberler/bildirimler", True), ("/hisse/THYAO", False)):
        with appmod.app.test_request_context(path):
            ctx = appmod._inject_gundem_haber()
            assert ("gundem_haber" in ctx) is has, path
            if has:
                assert ctx["gundem_haber"]["baski"] == "x"


@needs_app
def test_print_end_to_end_with_fake_gemini(appmod, monkeypatch):
    import gundem_haber
    with open(os.path.join(FX, "yanit_1.json"), encoding="utf-8") as f:
        answer = f.read()
    with open(os.path.join(FX, "v1_baski.json"), encoding="utf-8") as f:
        v1 = json.load(f)
    with open(os.path.join(FX, "kap_items.json"), encoding="utf-8") as f:
        kap = json.load(f)
    calls = []

    def fake_call(prompt, attempts, **kw):
        calls.append((attempts, kw))
        return attempts[0][0], answer

    class Store(object):
        def available(self):
            return True

        def all_items(self):
            return kap

    monkeypatch.setattr(appmod, "_gemini_call", fake_call)
    monkeypatch.setattr(appmod, "_KAP_STORE", Store())
    monkeypatch.setattr(appmod.haber_gundem, "load_latest", lambda: v1)
    monkeypatch.setattr(appmod.gemini_budget, "status", lambda: {"enabled": True, "calls_today": 0, "daily_cap": 200,
                                                                 "usd_month": 0.0, "monthly_cap_usd": 5})
    monkeypatch.setattr(gundem_haber, "read_cb_state", lambda p: {})
    res = appmod._gundem_haber_print(datetime(2026, 10, 1, 21, 45), "aksam")
    assert res["durum"] == "basildi" and res["madde"] >= 5
    assert len(calls) == 1
    attempts, kw = calls[0]
    assert attempts == [("gemini-2.5-flash-lite", False)] and kw["json_mode"] is True and kw["timeout_cap"] == 45
    doc = appmod.app.test_client().get("/api/gundem-haber").get_json()
    assert doc["maddeler"] and all(m["ai"] for m in doc["maddeler"])


@needs_app
def test_weekend_print_uses_last_business_day_v1(appmod, monkeypatch):
    # CPO-1815 (03.10): hafta sonu baskısı v1'in son iş günü (≤3 gün önce) kapanışını kullanır;
    # hafta içi beklenmedik kaçırılmış baskıda (>3 gün ya da hafta içi "bugün" eşleşmiyor) bayat sayılır.
    with open(os.path.join(FX, "v1_baski.json"), encoding="utf-8") as f:
        v1 = json.load(f)   # date=2026-10-01 (Perşembe), close_day=2026-10-01
    captured = {}

    def fake_run_edition(now, slot, call_model, v1_doc=None, close_day=None, **kw):
        captured["v1"] = v1_doc
        captured["close_day"] = close_day
        return {"durum": "aday_yetersiz", "madde": 0}

    monkeypatch.setattr(appmod.haber_gundem, "load_latest", lambda: v1)
    monkeypatch.setattr(appmod.gundem_haber, "run_edition", fake_run_edition)
    monkeypatch.setattr(appmod, "_KAP_STORE", type("S", (), {"available": lambda s: False})())
    monkeypatch.setattr(appmod.gemini_budget, "status", lambda: {})
    monkeypatch.setattr(appmod.gundem_haber, "read_cb_state", lambda p: {})

    appmod._gundem_haber_print(datetime(2026, 10, 3, 10, 31), "hafta_sonu")   # Cmt, v1 2 gün önce
    assert captured["v1"] is v1 and captured["close_day"] == v1_date("2026-10-01")

    appmod._gundem_haber_print(datetime(2026, 10, 7, 8, 35), "sabah")        # Çar, hafta içi kaçırılmış baskı
    assert captured["v1"] is None and captured["close_day"] is None


def v1_date(s):
    from datetime import datetime as _dt
    return _dt.strptime(s, "%Y-%m-%d").date()


@needs_app
def test_gemini_call_body_json_mode(appmod, monkeypatch):
    sent = {}

    class R(object):
        status_code = 200

        def raise_for_status(self):
            pass

        def json(self):
            return {"candidates": [{"content": {"parts": [{"text": "{\"maddeler\": []}"}]}}],
                    "usageMetadata": {"promptTokenCount": 10, "candidatesTokenCount": 5}}

    def fake_post(url, json=None, timeout=None):
        sent.update(body=json, timeout=timeout)
        return R()

    monkeypatch.setattr(appmod, "GEMINI_API_KEY", "test")
    monkeypatch.setattr(appmod, "_gemini_rate_acquire", lambda: 0)
    monkeypatch.setattr(appmod, "_gemini_quota_cb_sync", lambda: {"open_until": 0})
    monkeypatch.setattr(appmod, "_gemini_quota_cb_persist", lambda: None)
    monkeypatch.setattr(appmod, "_gemini_cb", {"open_until": 0, "fails": 0})
    monkeypatch.setattr(appmod, "_gemini_quota_cb", {"open_until": 0, "consecutive_429": 0, "quota_exhausted_total": 0})
    monkeypatch.setattr(appmod.gemini_budget, "reserve", lambda: (True, None))
    monkeypatch.setattr(appmod.gemini_budget, "record", lambda *a, **k: 0.0)
    monkeypatch.setattr(appmod.requests, "post", fake_post)
    m, text = appmod._gemini_call("x", [("gemini-2.5-flash-lite", False)], timeout=45, json_mode=True, timeout_cap=45)
    assert text == "{\"maddeler\": []}"
    assert sent["body"]["generationConfig"]["responseMimeType"] == "application/json"
    assert "tools" not in sent["body"] and sent["timeout"] == 45
    appmod._gemini_call("x", [("gemini-2.5-flash-lite", False)], timeout=45)
    assert "responseMimeType" not in sent["body"]["generationConfig"] and sent["timeout"] == appmod._GEMINI_TIMEOUT_CAP
