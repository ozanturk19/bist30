"""D-P1-2509 — hisse sayfasından takip: /api/subscribe `ticker`, çerez sahipliği, onay bağlantısı.

Saf yardımcılar AST ile (py3.9 yerel); route'lar VPS'te (py3.10+, test_client).
"""
import ast
import os
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
PY310 = pytest.mark.skipif(sys.version_info < (3, 10), reason="app.py 3.10+ ister")


def _helpers():
    src = open(os.path.join(ROOT, "app.py"), encoding="utf-8").read()
    tree = ast.parse(src)
    want = {"_follow_ticker", "_sub_follow_set", "_add_follow"}
    body = [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name in want]
    assert {n.name for n in body} == want
    ns = {"re": __import__("re"), "INDEX_TICKERS": {"XU030", "XU100"}, "BIST100": ["THYAO", "AHGAZ", "XU030"]}
    exec(compile(ast.Module(body=body, type_ignores=[]), "app_helpers", "exec"), ns)
    return ns


def test_follow_ticker_normalizes_and_rejects():
    h = _helpers()
    assert h["_follow_ticker"](" ahgaz ") == "AHGAZ"
    assert h["_follow_ticker"]("XU030") is None       # endeks
    assert h["_follow_ticker"]("ZZZZ") is None        # evren dışı
    assert h["_follow_ticker"]("A;B") is None
    assert h["_follow_ticker"](None) is None


def test_add_follow_idempotent_and_leaves_tickers_filter_alone():
    h = _helpers()
    rec = {"tickers": []}
    assert h["_add_follow"](rec, "THYAO") is True
    assert h["_add_follow"](rec, "THYAO") is False
    assert rec["follow"] == ["THYAO"] and rec["tickers"] == []   # filtre (boş = hepsi) daralmaz
    assert h["_sub_follow_set"](rec) == {"THYAO"}


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


def _sub(c, **kw):
    return c.post("/api/subscribe", json=kw).get_json()


@PY310
def test_new_subscriber_gets_follow(client):
    r = _sub(client, email="a@example.com", ticker="AHGAZ")
    assert r["ok"] and "AHGAZ bildirimleri açıldı" in r["message"]
    rec = client.mod._load_subscribers()["a@example.com"]
    assert rec["follow"] == ["AHGAZ"] and rec["tickers"] == []


@PY310
def test_registered_with_cookie_adds_directly_then_already(client):
    r = _sub(client, email="a@example.com")
    client.set_cookie("bp_sub", r["token"])   # werkzeug>=2.3 imzası (domain'siz)
    r2 = _sub(client, email="a@example.com", ticker="AHGAZ")
    assert r2["status"] == "added"
    r3 = _sub(client, email="a@example.com", ticker="AHGAZ")
    assert r3["status"] == "already" and "zaten takip" in r3["message"]


@PY310
def test_registered_without_cookie_sends_confirm_then_confirms(client):
    _sub(client, email="a@example.com")
    client.delete_cookie("bp_sub")
    n = len(client.sent)
    r = _sub(client, email="a@example.com", ticker="THYAO")
    assert r["status"] == "confirm_sent" and len(client.sent) == n + 1
    assert not client.mod._load_subscribers()["a@example.com"].get("follow")   # onaya kadar eklenmez
    tok = client.mod._load_subscribers()["a@example.com"]["follow_pending"]["token"]
    resp = client.get(f"/api/follow/confirm?t={tok}")
    assert resp.status_code == 302 and "/hisse/THYAO" in resp.headers["Location"]
    assert client.mod._load_subscribers()["a@example.com"]["follow"] == ["THYAO"]
    assert client.get(f"/api/follow/confirm?t={tok}").headers["Location"].endswith("takip=expired")  # tek kullanım


@PY310
def test_inactive_reactivated_with_follow(client):
    r = _sub(client, email="a@example.com")
    subs = client.mod._load_subscribers()
    subs["a@example.com"]["active"] = False
    client.mod._save_subscribers(subs)
    r2 = _sub(client, email="a@example.com", ticker="THYAO")
    assert r2["ok"] and "THYAO" in r2["message"]
    rec = client.mod._load_subscribers()["a@example.com"]
    assert rec["active"] and rec["follow"] == ["THYAO"]


@PY310
def test_invalid_ticker_400_and_plain_subscribe_unchanged(client):
    assert client.post("/api/subscribe", json={"email": "a@example.com", "ticker": "XU030"}).status_code == 400
    _sub(client, email="a@example.com")
    r = _sub(client, email="a@example.com")           # ticker'sız: eski davranış
    assert r["ok"] is False and "zaten kayıtlı" in r["error"]


@PY310
def test_digest_email_marks_followed_first(client):
    stock = {"price": 10.0, "adx": 20, "sl_level": None, "rvol": None, "is_premium": False}
    html = client.mod._build_signal_email([("THYAO", "BEKLE", "AL", stock), ("AHGAZ", "BEKLE", "SAT", stock)],
                                          "https://x/u", follow={"AHGAZ"})
    assert "TAKİPTE" in html and html.index("AHGAZ") < html.index("THYAO")
