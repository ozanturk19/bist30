"""D-50 — gerçek app.py ile duman testi (VPS venv, py3.10+). Yerelde atlanır (93d01dc deseni)."""
import os
import sys

import pytest

if sys.version_info < (3, 10):
    pytest.skip("app.py 3.10+ ister — VPS venv'de çalıştır", allow_module_level=True)

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import app  # noqa: E402


def test_routes_and_service_registered():
    have = set()
    for r in app.app.url_map.iter_rules():
        for m in r.methods - {"HEAD", "OPTIONS"}:
            have.add("%s %s" % (m, r.rule))
    need = {"POST /api/auth/code", "POST /api/auth/verify", "POST /api/auth/logout", "POST /api/recognize",
            "GET /api/me", "DELETE /api/me", "GET /api/me/watchlist", "POST /api/me/watchlist",
            "PUT /api/me/watchlist", "DELETE /api/me/watchlist/<ticker>", "GET /api/me/portfolio",
            "PUT /api/me/portfolio/<ticker>", "DELETE /api/me/portfolio/<ticker>", "POST /api/me/import",
            "POST /api/me/prefs", "GET /takip"}
    assert need <= have, need - have
    assert app._acct is not None, "pepper kurulamadı -> hesap uçları kapalı"
    assert app._acct.subs.lock is app._sub_lock        # abone dosyasıyla AYNI kilit nesnesi


def test_new_subscriber_record_is_account_shaped(tmp_path, monkeypatch):
    monkeypatch.setattr(app, "SUBSCRIBERS_FILE", str(tmp_path / "subscribers.json"))
    monkeypatch.setattr(app, "_MAIL_ROUTE_SENDS_PATH", str(tmp_path / "mrs.json"))
    monkeypatch.setattr(app, "send_email", lambda *a, **k: True)
    app.limiter.enabled = False
    c = app.app.test_client()
    r = c.post("/api/subscribe", json={"email": "yeni@ornek.com", "kvkk": True})
    assert r.get_json()["ok"]
    rec = app._load_subscribers()["yeni@ornek.com"]
    assert rec["account_v"] == 1 and rec["notify"] == {"trend": True, "bulten": True}
    assert rec["kvkk_consent_ts"] and rec["confirmed_at"] is None and rec["watchlist"] == []


def test_takip_route_without_template_is_404_or_page():
    c = app.app.test_client()
    code = c.get("/takip").status_code
    exists = os.path.exists(os.path.join(os.path.dirname(app.__file__), "templates", "takip.html"))
    assert code == (200 if exists else 404)
