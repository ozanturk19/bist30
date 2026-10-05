"""D-38 — anonim bülten aboneliği: KVKK zorunlu + çift onay (CPO-1823 karar b: grandfather).

Saf yardımcı (grandfather) AST'siz doğrudan import (py3.9'da da koşar); route'lar ve
digest filtresi VPS'te (py3.10+, test_client).
"""
import os
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
PY310 = pytest.mark.skipif(sys.version_info < (3, 10), reason="app.py 3.10+ ister")


def test_grandfather_sets_confirmed_at_for_active_unconfirmed_only():
    sys.path.insert(0, os.path.join(ROOT, "tools"))
    import migrate_confirm_grandfather as mig

    subs = {
        "a@example.com": {"active": True,  "subscribed_at": "2026-01-01T00:00:00+03:00", "confirmed_at": None},
        "b@example.com": {"active": True,  "subscribed_at": "2026-02-01T00:00:00+03:00", "confirmed_at": "2026-02-01T00:00:00+03:00"},
        "c@example.com": {"active": False, "subscribed_at": "2026-03-01T00:00:00+03:00", "confirmed_at": None},
    }
    n = mig.grandfather(subs)
    assert n == 1
    assert subs["a@example.com"]["confirmed_at"] == "2026-01-01T00:00:00+03:00"   # grandfathered
    assert subs["b@example.com"]["confirmed_at"] == "2026-02-01T00:00:00+03:00"   # değişmedi
    assert subs["c@example.com"]["confirmed_at"] is None                          # pasif, dokunulmadı
    assert mig.grandfather(subs) == 0   # tekrar koşmak zararsız (idempotent)


@pytest.fixture
def client(tmp_path, monkeypatch):
    import app
    monkeypatch.setattr(app, "SUBSCRIBERS_FILE", str(tmp_path / "subscribers.json"))
    monkeypatch.setattr(app, "_MAIL_ROUTE_SENDS_PATH", str(tmp_path / "mrs.json"))
    sent = []
    monkeypatch.setattr(app, "send_email", lambda to, subj, html, unsubscribe_url=None, reply_to=None: sent.append((to, subj, html)) or True)
    app.limiter.enabled = False
    c = app.app.test_client()
    c.sent = sent
    c.mod = app
    return c


@PY310
def test_kvkk_missing_400_no_record_created(client):
    r = client.post("/api/subscribe", json={"email": "a@example.com"})
    assert r.status_code == 400
    assert "KVKK" in r.get_json()["error"]
    assert client.mod._load_subscribers() == {}


@PY310
def test_new_subscriber_unconfirmed_no_cookie_until_confirm_link(client):
    r = client.post("/api/subscribe", json={"email": "a@example.com", "kvkk": True})
    body = r.get_json()
    assert r.status_code == 200 and body["ok"]
    assert "set-cookie" not in {k.lower() for k in r.headers.keys()}   # D-38: sahiplik onaya kadar verilmez
    rec = client.mod._load_subscribers()["a@example.com"]
    assert rec["confirmed_at"] is None
    assert rec.get("login_token") and rec.get("login_used") is False

    confirm = client.get(f"/api/recognize/confirm?t={rec['login_token']}")
    assert confirm.status_code == 302
    rec2 = client.mod._load_subscribers()["a@example.com"]
    assert rec2["confirmed_at"]   # artık onaylı
    assert rec2["login_used"] is True


@PY310
def test_digest_skips_unconfirmed_active_subscriber(client):
    from datetime import datetime
    client.mod.SMTP_HOST = "smtp.test"
    client.post("/api/subscribe", json={"email": "confirmed@example.com", "kvkk": True})
    client.post("/api/subscribe", json={"email": "pending@example.com", "kvkk": True})
    subs = client.mod._load_subscribers()
    subs["confirmed@example.com"]["confirmed_at"] = client.mod._accounts.now_iso()
    client.mod._save_subscribers(subs)
    client.sent.clear()

    today_iso = datetime.now(client.mod._TZ_TR).isoformat()
    stock = {"price": 10.0, "change_pct": 1.0, "sl_level": None, "adx": 30, "rvol": None, "is_premium": False}
    client.mod._load_pending_changes = lambda: [
        {"ticker": "THYAO", "old": "BEKLE", "new": "AL", "stock": stock, "ts": today_iso}
    ]
    rep = client.mod._send_digest_emails(timeframe="daily", force=True)

    recipients = {to for to, _subj, _html in client.sent}
    assert "confirmed@example.com" in recipients
    assert "pending@example.com" not in recipients
    assert rep["sent"] == 1
