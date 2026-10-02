"""D-50 — app.py'deki GERÇEK hesap rotaları, yerelde (py3.9) mini Flask uygulamasında.

app.py yerelde içe aktarılamıyor (3.10+ sözdizimi); D-50 bağlantı kodu AST ile app.py'den
çıkarılır ve saplarla çalıştırılır: çerez bayrakları, CSRF (JSON + köken), 401/403/415,
tam akış (kod -> oturum -> liste -> ikinci tarayıcı), çıkış/iptal, hesap silme, /api/me,
/takip şablon yoksa 404, eski uçların (bp_sub / oturum) kimlik kabulü. VPS'te de koşar.
"""
import ast
import json
import os
import re
import sys
import threading

import pytest

flask = pytest.importorskip("flask")

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
import accounts  # noqa: E402

WANT_FUNCS = {
    "_clean", "safe_json", "_private_json", "_acct_store", "_acct_valid_ticker", "_acct_email",
    "_acct_set_cookies", "_acct_clear_cookies", "_acct_json", "_acct_result", "_acct_api", "_acct_body",
    "_build_code_email", "_acct_code_request", "api_auth_code", "api_recognize", "api_auth_verify",
    "api_auth_logout", "api_me", "api_me_delete", "_acct_market_snapshot", "api_me_watchlist",
    "api_me_watchlist_add", "api_me_watchlist_replace", "api_me_watchlist_remove", "api_me_portfolio",
    "api_me_position_set", "api_me_position_remove", "api_me_import", "api_me_prefs", "takip_page",
    "_get_sub_by_cookie", "api_user_alerts_get",
}
WANT_ASSIGN = {"_ACCT_COOKIE", "_ACCT_HINT"}
UNIVERSE = {"THYAO", "ASELS", "TKFEN", "SASA"}


class _Limiter:
    def limit(self, *a, **k):
        return lambda f: f


def _extract():
    src = open(os.path.join(ROOT, "app.py"), encoding="utf-8").read()
    tree = ast.parse(src)
    body = []
    for n in tree.body:
        if isinstance(n, ast.FunctionDef) and n.name in WANT_FUNCS:
            body.append(n)
        elif isinstance(n, ast.Assign) and any(isinstance(t, ast.Name) and t.id in WANT_ASSIGN for t in n.targets):
            body.append(n)
    got = {n.name for n in body if isinstance(n, ast.FunctionDef)}
    assert got == WANT_FUNCS, WANT_FUNCS - got
    return ast.Module(body=body, type_ignores=[])


@pytest.fixture
def env(tmp_path, monkeypatch):
    app = flask.Flask(__name__, template_folder=str(tmp_path / "tpl"))
    (tmp_path / "tpl").mkdir()
    sent = []
    hits = {}

    def rate(bucket, key, n, w):
        xs = hits.setdefault((bucket, key), [])
        if len(xs) >= n:
            return False
        xs.append(1)
        return True

    subs_path = str(tmp_path / "subscribers.json")

    def load_subs():
        return accounts.read_json(subs_path)

    def save_subs(d):
        accounts.atomic_write_json(subs_path, d)

    ns = {
        "__name__": "app_d50", "app": app, "limiter": _Limiter(), "request": flask.request,
        "redirect": flask.redirect, "abort": flask.abort, "render_template": flask.render_template,
        "Response": flask.Response, "json": json, "os": os, "re": re, "secrets": __import__("secrets"),
        "time": __import__("time"), "_html": __import__("html"), "logger": __import__("logging").getLogger("t"),
        "_accounts": accounts, "get_remote_address": lambda: "127.0.0.1", "_mail_route_allowed": rate,
        "send_email": lambda to, subj, html, unsubscribe_url=None, reply_to=None: sent.append((to, subj, html)) or True,
        "_email_base": lambda content, unsub, preheader="": content + ("UNSUB:%s" % unsub if unsub else ""),
        "_PF_VALID_TICKERS": UNIVERSE, "INDEX_TICKERS": {"XU030", "XU100"},
        "_lock": threading.Lock(), "_cache": {"data": [
            {"ticker": "THYAO", "name": "Türk Hava Yolları", "price": 288.5, "change_pct": -3.35,
             "signal": "BEKLE", "signal_bars": 1, "signal_date": "24.09.2026", "sector": "Ulaştırma"},
            {"ticker": "ASELS", "name": "Aselsan", "price": 380.25, "change_pct": 1.54, "signal": "AL",
             "signal_bars": 18, "signal_date": "01.09.2026"}]},
        "_financial_health_cache": {"THYAO": {"data": {"borsapusula_skoru": 63}}},
        "_data_quality_snapshot": lambda stocks: {"updated_at": "24.09.2026 19:11:25"},
        "_load_pending_changes_weekly": lambda: [{"ticker": "THYAO", "old": "AL", "new": "BEKLE", "ts": "2026-09-24T18:40:00+03:00"}],
        "_load_pending_changes": lambda: [], "STOCK_NAMES": {},
        "_sub_lock": threading.Lock(), "_load_subscribers": load_subs, "_save_subscribers": save_subs,
        "SUBSCRIBERS_FILE": subs_path,
    }
    exec(compile(_extract(), "app_d50", "exec"), ns)
    # app.py'de _acct'ın modül düzeyinde kurulduğu gibi: aynı abone dosyası + yan dosyalar
    ns["_acct"] = accounts.AccountService(
        accounts.FileStore(subs_path, ns["_sub_lock"], load=load_subs, save=save_subs),
        accounts.FileStore(str(tmp_path / "sessions.json")),
        accounts.FileStore(str(tmp_path / "login_codes.json")),
        b"p" * 32, lambda t: t in UNIVERSE, rate_allow=rate)
    c = app.test_client()
    c.ns, c.sent, c.tmp = ns, sent, tmp_path
    return c


H = {"Origin": "https://localhost"}
B = "https://localhost"


def _code_from_mail(c):
    return re.search(r">(\d{6})<", c.sent[-1][2]).group(1)


def _post(c, url, body, method="post", headers=H):
    return getattr(c, method)(url, json=body, headers=headers, base_url=B)


def _login(c, email="ayse.demir@ornek.com", imp=None):
    r = _post(c, "/api/auth/code", {"email": email, "kvkk": True})
    assert r.status_code == 200, r.get_json()
    body = {"email": email, "code": _code_from_mail(c)}
    if imp:
        body["import"] = imp
    return _post(c, "/api/auth/verify", body)


def test_full_flow_cookies_and_second_browser(env):
    r = _login(env, imp={"watchlist": ["THYAO"], "portfolio": [{"ticker": "ASELS", "lot": 10, "price": 300}]})
    assert r.status_code == 200 and r.get_json()["imported"]["watchlist_added"] == 2
    sc = r.headers.getlist("Set-Cookie")
    sess = [h for h in sc if h.startswith("bp_session=")][0]
    hint = [h for h in sc if h.startswith("bp_li=")][0]
    for flag in ("HttpOnly", "Secure", "SameSite=Lax", "Path=/", "Max-Age=7776000"):
        assert flag in sess, (flag, sess)
    assert "HttpOnly" not in hint and "Secure" in hint and hint.startswith("bp_li=1;")
    me = env.get("/api/me", base_url=B).get_json()
    assert me["logged_in"] and me["email_masked"] == "ay•••@ornek.com" and me["counts"] == {"watchlist": 2, "portfolio": 1}
    wl = env.get("/api/me/watchlist", base_url=B).get_json()
    assert [i["ticker"] for i in wl["items"]] == ["THYAO", "ASELS"]
    th = wl["items"][0]
    assert th["prev_signal"] == "AL" and th["bp"] == 63 and wl["asof"] == "24.09.2026 19:11:25"
    assert wl["items"][1]["qty"] == 10 and wl["items"][1]["prev_signal"] is None
    assert _post(env, "/api/me/watchlist", {"ticker": "TKFEN"}).get_json()["added"] is True
    # ikinci tarayıcı (çerezsiz istemci): aynı e-posta -> aynı liste
    c2 = env.application.test_client()
    c2.sent = env.sent
    _login(c2)
    assert c2.get("/api/me/watchlist", base_url=B).get_json()["watchlist"] == ["THYAO", "ASELS", "TKFEN"]


def test_kvkk_missing_400_and_enumeration_safe(env):
    r = _post(env, "/api/auth/code", {"email": "a@ornek.com"})
    assert r.status_code == 400 and r.get_json()["error"] == "kvkk_required" and not env.sent
    _login(env, "kayitli@ornek.com")
    a = _post(env, "/api/auth/code", {"email": "kayitli@ornek.com", "kvkk": True})
    b = _post(env, "/api/auth/code", {"email": "yok@ornek.com", "kvkk": True})
    assert (a.status_code, a.get_json()) == (b.status_code, b.get_json())
    assert env.sent[-2][2].count(">") and "UNSUB:" in env.sent[-2][2] and "UNSUB:" not in env.sent[-1][2]


def test_csrf_json_and_origin_required(env):
    _login(env)
    assert env.post("/api/me/watchlist", data="ticker=THYAO", headers=H, base_url=B,
                    content_type="application/x-www-form-urlencoded").status_code == 415
    assert _post(env, "/api/me/watchlist", {"ticker": "THYAO"}, headers={"Origin": "https://evil.example"}).status_code == 403
    assert _post(env, "/api/me/watchlist", {"ticker": "THYAO"}, headers={}).status_code == 403
    assert _post(env, "/api/me/watchlist", {"ticker": "THYAO"},
                 headers={"Referer": "https://localhost/takip"}).status_code == 200


def test_login_required_and_wrong_code_lock(env):
    assert env.get("/api/me/watchlist", base_url=B).status_code == 401
    assert env.get("/api/me", base_url=B).get_json() == {"ok": False, "logged_in": False, "subscribed": False}
    _post(env, "/api/auth/code", {"email": "k@ornek.com", "kvkk": True})
    good = _code_from_mail(env)
    bad = "%06d" % ((int(good) + 1) % 1000000)
    codes = [_post(env, "/api/auth/verify", {"email": "k@ornek.com", "code": bad}).status_code for _ in range(5)]
    assert codes == [400, 400, 400, 400, 429]
    r = _post(env, "/api/auth/verify", {"email": "k@ornek.com", "code": good})
    assert r.status_code == 429 and not [h for h in r.headers.getlist("Set-Cookie") if h.startswith("bp_session=")]


def test_logout_revokes_server_side(env):
    _login(env)
    assert env.get("/api/me", base_url=B).get_json()["logged_in"]
    sid_before = json.load(open(env.tmp / "sessions.json"))
    r = _post(env, "/api/auth/logout", {})
    assert r.status_code == 200
    cleared = " ".join(r.headers.getlist("Set-Cookie"))
    assert "bp_session=;" in cleared and "bp_li=;" in cleared and "bp_sub=;" in cleared
    assert json.load(open(env.tmp / "sessions.json")) == {} and sid_before
    assert env.get("/api/me/watchlist", base_url=B).status_code == 401


def test_positions_prefs_delete_account(env):
    _login(env)
    r = _post(env, "/api/me/portfolio/TKFEN", {"qty": 80, "cost": "210,80"}, method="put")
    assert r.status_code == 200 and r.get_json()["position"] == {"ticker": "TKFEN", "qty": 80, "cost": 210.8}
    assert _post(env, "/api/me/portfolio/TKFEN", {"qty": 0, "cost": 1}, method="put").status_code == 400
    assert env.get("/api/me/portfolio", base_url=B).get_json()["portfolio"][0]["qty"] == 80
    assert _post(env, "/api/me/portfolio/TKFEN", {}, method="delete").get_json()["removed"] is True
    assert _post(env, "/api/me/prefs", {"bulten": True}).get_json()["notify"] == {"trend": True, "bulten": True}
    assert _post(env, "/api/me/watchlist", {"watchlist": [], "portfolio": []}, method="put").status_code == 200
    r = _post(env, "/api/me", {}, method="delete")
    assert r.status_code == 200 and "ayse.demir@ornek.com" not in json.load(open(env.tmp / "subscribers.json"))
    assert env.get("/api/me/watchlist", base_url=B).status_code == 401


def test_takip_page_404_until_template_exists(env):
    assert env.get("/takip").status_code == 404
    (env.tmp / "tpl" / "takip.html").write_text("<h1>Takip</h1>", encoding="utf-8")
    env.ns["_nocache_html"] = lambda html: html
    assert env.get("/takip").status_code == 200


def test_legacy_endpoints_accept_session_and_bp_sub(env):
    _login(env)
    assert env.get("/api/user-alerts", base_url=B).status_code == 200      # oturumla
    c2 = env.application.test_client()
    tok = json.load(open(env.tmp / "subscribers.json"))["ayse.demir@ornek.com"]["token"]
    c2.set_cookie("bp_sub", tok, domain="localhost")
    assert c2.get("/api/user-alerts", base_url=B).status_code == 200       # eski bp_sub hâlâ çalışır
    assert c2.get("/api/me", base_url=B).get_json()["logged_in"] is False  # yeni API bp_sub'ı kabul etmez


def test_recognize_is_code_flow(env):
    r = _post(env, "/api/recognize", {"email": "r@ornek.com", "kvkk": True})
    assert r.status_code == 200 and re.search(r">(\d{6})<", env.sent[-1][2])
