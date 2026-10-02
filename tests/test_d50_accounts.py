"""D-50 — hesap çekirdeği (accounts.py) yerel testleri (py3.9, Flask'sız).

Kabul: çerezsiz akış e-posta → kod → oturum → listeye ekle → başka tarayıcıda aynı
e-postayla giriş → liste aynı; yanlış kod 5 denemede kilit; süre dolumu; KVKK yoksa 400;
kayıtlı/kayıtsız adres yanıtı aynı; içe aktarma birleşimi; oturum iptali; hız sınırı.
Sentetik veriyle çalışır (gerçek abone dosyası okunmaz).
"""
import json
import os
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

import accounts as A  # noqa: E402

UNIVERSE = {"THYAO", "ASELS", "TKFEN", "ULKER", "KARSN", "MGROS", "AKBNK", "SASA"}


class Clock:
    def __init__(self, t=1790000000.0):
        self.t = t

    def __call__(self):
        return self.t


class Rate:
    """app._mail_route_allowed ile aynı anlam: pencere içinde max_count'a kadar izin."""

    def __init__(self, clock):
        self.clock, self.hits = clock, {}

    def __call__(self, bucket, key, max_count, window):
        now = self.clock()
        k = (bucket, key)
        xs = [t for t in self.hits.get(k, []) if now - t < window]
        if len(xs) >= max_count:
            self.hits[k] = xs
            return False
        xs.append(now)
        self.hits[k] = xs
        return True


@pytest.fixture
def env(tmp_path):
    clock = Clock()
    subs = A.FileStore(str(tmp_path / "subscribers.json"))
    sess = A.FileStore(str(tmp_path / "sessions.json"))
    codes = A.FileStore(str(tmp_path / "login_codes.json"))
    svc = A.AccountService(subs, sess, codes, b"t" * 32, lambda t: t in UNIVERSE,
                           rate_allow=Rate(clock), clock=clock)
    svc._tmp, svc._clock = tmp_path, clock
    return svc


def _login(svc, email="ayse.demir@ornek.com", ip="10.0.0.1", imp=None):
    r = svc.request_code(email, True, ip)
    assert r.status == 200 and r.code and len(r.code) == 6
    v = svc.verify_code(email, r.code, ip, imp)
    assert v.status == 200, v.body
    return v


# 1 — tam akış + ikinci tarayıcıda aynı liste
def test_full_flow_code_session_watchlist_second_browser(env):
    v1 = _login(env)
    tok1 = v1.token
    email = env.session_email(tok1)
    assert email == "ayse.demir@ornek.com"
    assert v1.body["me"]["logged_in"] and v1.body["me"]["email_masked"] == "ay•••@ornek.com"
    assert env.watch_add(email, "thyao").body["added"] is True
    assert env.position_set(email, "TKFEN", "80", "210,80").status == 200
    # ikinci "tarayıcı": çerez yok, aynı e-postayla yeni kod
    v2 = _login(env)
    assert v2.token != tok1
    rec = env.account(env.session_email(v2.token))
    assert A.account_fields(rec)["watchlist"] == ["THYAO", "TKFEN"]
    assert env.portfolio_view(rec) == [{"ticker": "TKFEN", "qty": 80, "cost": 210.8}]
    # iki oturum da geçerli (cihaz başına ayrı)
    assert env.session_email(tok1) == env.session_email(v2.token)


# 2 — 5 yanlış denemede kilit
def test_wrong_code_five_times_locks(env):
    r = env.request_code("a@ornek.com", True, "1.1.1.1")
    wrong = "%06d" % ((int(r.code) + 1) % 1000000)
    for i in range(4):
        v = env.verify_code("a@ornek.com", wrong, "1.1.1.1")
        assert v.status == 400 and v.body["error"] == "code_invalid"
        assert v.body["attempts_left"] == 4 - i
    v = env.verify_code("a@ornek.com", wrong, "1.1.1.1")
    assert v.status == 429 and v.body["error"] == "locked"
    # kilitliyken doğru kod da geçmez, yeni kod da istenemez
    assert env.verify_code("a@ornek.com", r.code, "1.1.1.1").status == 429
    assert env.request_code("a@ornek.com", True, "1.1.1.2").body["error"] == "locked"
    # 15 dk sonra yeni kod istenebilir ve çalışır
    env._clock.t += A.LOCK_SECONDS + 1
    r2 = env.request_code("a@ornek.com", True, "1.1.1.3")
    assert r2.status == 200
    assert env.verify_code("a@ornek.com", r2.code, "1.1.1.3").status == 200


def test_new_code_does_not_reset_attempts(env):
    r = env.request_code("b@ornek.com", True, "1.1.1.1")
    wrong = "%06d" % ((int(r.code) + 7) % 1000000)
    for _ in range(3):
        env.verify_code("b@ornek.com", wrong, "1.1.1.1")
    r2 = env.request_code("b@ornek.com", True, "1.1.1.1")
    wrong2 = "%06d" % ((int(r2.code) + 7) % 1000000)
    assert env.verify_code("b@ornek.com", wrong2, "1.1.1.1").body["attempts_left"] == 1
    assert env.verify_code("b@ornek.com", wrong2, "1.1.1.1").body["error"] == "locked"


# 3 — süre dolumu + tek kullanım
def test_code_expires_after_10_minutes_and_is_single_use(env):
    r = env.request_code("c@ornek.com", True, "1.1.1.1")
    env._clock.t += A.CODE_TTL + 1
    v = env.verify_code("c@ornek.com", r.code, "1.1.1.1")
    assert v.status == 400 and v.body["error"] == "code_expired"
    r2 = env.request_code("c@ornek.com", True, "1.1.1.1")
    assert env.verify_code("c@ornek.com", r2.code, "1.1.1.1").status == 200
    again = env.verify_code("c@ornek.com", r2.code, "1.1.1.1")
    assert again.status == 400 and again.body["error"] == "code_expired"


# 4 — KVKK yoksa 400
@pytest.mark.parametrize("kvkk", [None, False, "true", 1, "on"])
def test_kvkk_missing_is_400(env, kvkk):
    r = env.request_code("d@ornek.com", kvkk, "1.1.1.1")
    assert r.status == 400 and r.body["error"] == "kvkk_required" and r.code is None


def test_invalid_email_is_400(env):
    for bad in ("", "x", "a@b", "a b@c.de", None, 5, "a@" + "b" * 260 + ".com"):
        assert env.request_code(bad, True, "1.1.1.1").body["error"] == "email_invalid"


# 5 — kayıt var/yok ayrımı sızmaz
def test_enumeration_safe_responses(env):
    _login(env, "kayitli@ornek.com")
    a = env.request_code("kayitli@ornek.com", True, "2.2.2.2")
    b = env.request_code("yeni@ornek.com", True, "2.2.2.3")
    assert (a.status, a.body) == (b.status, b.body)
    # hiç istenmemiş kod ile süresi dolmuş kod aynı yanıt
    x = env.verify_code("hic@ornek.com", "123456", "2.2.2.4")
    env._clock.t += A.CODE_TTL + 1
    y = env.verify_code("kayitli@ornek.com", a.code, "2.2.2.5")
    assert (x.status, x.body) == (y.status, y.body)


# 6 — içe aktarma birleşimi
def test_import_merge_aggregates_lots_and_server_wins(env):
    v = _login(env, imp={"watchlist": ["THYAO", "asels", "XU030", "ZZZZ", 7],
                         "portfolio": [{"ticker": "THYAO", "lot": 60, "price": 300},
                                       {"ticker": "THYAO", "lot": 40, "price": 342.5},
                                       {"ticker": "KARSN", "lot": 1500, "price": 9.86},
                                       {"ticker": "SASA", "lot": 1.5, "price": 3},
                                       {"ticker": "MGROS", "lot": 10, "price": 0}]})
    imp = v.body["imported"]
    assert imp["watchlist_added"] == 3 and imp["portfolio_added"] == 2   # THYAO, ASELS + KARSN (pozisyondan)
    email = env.session_email(v.token)
    rec = env.account(email)
    assert A.account_fields(rec)["watchlist"] == ["THYAO", "ASELS", "KARSN"]
    pv = {p["ticker"]: p for p in env.portfolio_view(rec)}
    assert pv["THYAO"]["qty"] == 100 and pv["THYAO"]["cost"] == pytest.approx(317.0)
    # ikinci içe aktarma: aynı hisse için sunucudaki pozisyon korunur, liste birleşir
    r = env.import_merge(email, {"watchlist": ["ULKER", "THYAO"],
                                 "portfolio": [{"ticker": "THYAO", "qty": 1, "cost": 1}]})
    assert r.body["imported"] == {"watchlist_added": 1, "portfolio_added": 0, "skipped": []}
    rec = env.account(email)
    assert {p["ticker"]: p["qty"] for p in env.portfolio_view(rec)}["THYAO"] == 100


# 7 — oturum iptali
def test_logout_revokes_session_and_revoke_all(env):
    t1 = _login(env, "e@ornek.com").token
    t2 = _login(env, "e@ornek.com").token
    assert env.revoke_session(t1) is True
    assert env.session_email(t1) is None and env.session_email(t2) == "e@ornek.com"
    assert env.revoke_all("e@ornek.com") == 1
    assert env.session_email(t2) is None
    assert env.session_email("kisa") is None and env.session_email(None) is None


def test_session_expires_after_90_days(env):
    t = _login(env, "f@ornek.com").token
    env._clock.t += A.SESSION_TTL - 10
    assert env.session_email(t) == "f@ornek.com"
    env._clock.t += 20
    assert env.session_email(t) is None


# 8 — hız sınırı (IP ve e-posta)
def test_rate_limits_per_ip_and_per_email(env):
    for i in range(3):
        assert env.request_code("g@ornek.com", True, "3.3.3.%d" % i).status == 200
    r = env.request_code("g@ornek.com", True, "3.3.3.9")
    assert r.status == 429 and r.body["error"] == "rate_limited"
    for i in range(10):
        assert env.request_code("ip%d@ornek.com" % i, True, "4.4.4.4").status == 200
    assert env.request_code("ip99@ornek.com", True, "4.4.4.4").status == 429
    for i in range(30):
        env.verify_code("v%d@ornek.com" % i, "000000", "5.5.5.5")
    assert env.verify_code("v@ornek.com", "000000", "5.5.5.5").body["error"] == "rate_limited"


# 9 — diskte kod/belirteç düz metin yok; karşılaştırma sabit zamanlı
def test_only_hashes_on_disk_and_constant_time_compare(env, monkeypatch):
    calls = []
    real = A.hmac.compare_digest
    monkeypatch.setattr(A.hmac, "compare_digest", lambda a, b: calls.append(1) or real(a, b))
    r = env.request_code("h@ornek.com", True, "1.1.1.1")
    raw_codes = open(env._tmp / "login_codes.json", encoding="utf-8").read()
    assert r.code not in raw_codes and "h@ornek.com" not in raw_codes
    v = env.verify_code("h@ornek.com", r.code, "1.1.1.1")
    assert calls, "hmac.compare_digest kullanılmadı"
    raw_sess = open(env._tmp / "sessions.json", encoding="utf-8").read()
    assert v.token not in raw_sess
    assert oct(os.stat(env._tmp / "sessions.json").st_mode & 0o777) == "0o600"


def test_account_record_fields_and_prefs(env):
    v = _login(env, "k@ornek.com")
    rec = json.load(open(env._tmp / "subscribers.json", encoding="utf-8"))["k@ornek.com"]
    assert rec["account_v"] == 1 and rec["confirmed_at"] and rec["kvkk_consent_ts"]
    assert rec["notify"] == {"trend": True, "bulten": False} and rec["token"] and rec["active"]
    email = env.session_email(v.token)
    assert env.set_prefs(email, {"bulten": True, "trend": "x"}).body["notify"] == {"trend": True, "bulten": True}
    assert env.watch_add(email, "XU030").status == 400
    assert env.position_set(email, "ASELS", 0, 10).body["error"] == "position_invalid"
    assert env.position_set(email, "ASELS", 2.5, 10).body["error"] == "position_invalid"
    assert env.watch_remove(email, "ASELS").body["removed"] is False
    env.position_set(email, "ASELS", 3, 10)
    assert env.watch_remove(email, "ASELS").body["removed"] is True
    assert env.portfolio_view(env.account(email)) == []


def test_replace_supports_clear_and_undo(env):
    email = env.session_email(_login(env, "m@ornek.com").token)
    env.watch_add(email, "THYAO")
    env.position_set(email, "TKFEN", 80, 210.8)
    old_w = A.account_fields(env.account(email))["watchlist"]
    old_p = env.portfolio_view(env.account(email))
    assert env.watch_replace(email, [], []).body["watchlist"] == []
    r = env.watch_replace(email, old_w, old_p)
    assert r.body["watchlist"] == ["THYAO", "TKFEN"] and r.body["portfolio"] == old_p


def test_delete_account_forgets_sessions_and_codes(env):
    t = _login(env, "n@ornek.com").token
    env.request_code("n@ornek.com", True, "1.1.1.1")
    assert env.delete_account("n@ornek.com") is True
    assert env.session_email(t) is None
    assert env.codes.load() == {}
    assert "n@ornek.com" not in env.subs.load()


def test_inactive_record_login_keeps_mail_off(env):
    env.subs._save({"p@ornek.com": {"token": "x" * 48, "active": False, "tickers": [], "mail_pref": "daily"}})
    email = env.session_email(_login(env, "p@ornek.com").token)
    rec = env.account(email)
    assert rec["active"] is True and rec["notify"] == {"trend": False, "bulten": False}


# Göç + e-posta filtresi eşdeğerliği
def _legacy_filter(rec, changes, premium_only=False):
    """D-P1-2509 sonrası app.py'deki eski filtre (karşılaştırma için)."""
    tickers = rec.get("tickers", [])
    follow = {str(t).upper() for t in (rec.get("follow") or []) if t}
    rel = list(changes)
    if premium_only:
        rel = [c for c in rel if c[3].get("is_premium") or c[0] in follow]
    if tickers:
        rel = [c for c in rel if c[0] in tickers or c[0] in follow]
    return rel


CH = [("THYAO", "BEKLE", "AL", {"is_premium": False}), ("ASELS", "AL", "BEKLE", {"is_premium": True}),
      ("SASA", "SAT", "BEKLE", {"is_premium": False})]


def test_migration_keeps_mail_behaviour_and_is_idempotent():
    subs = {
        "u1@ornek.com": {"token": "a" * 48, "tickers": [], "follow": ["THYAO"], "active": True, "mail_pref": "daily"},
        "u2@ornek.com": {"token": "b" * 48, "tickers": ["ASELS"], "active": True, "mail_pref": "instant"},
        "u3@ornek.com": {"token": "c" * 48, "tickers": [], "alerts": {"SASA": {"signal_change": True}}, "active": False},
        "u4@ornek.com": {"token": "d" * 48, "active": True},
    }
    before = {e: _legacy_filter(r, CH) for e, r in subs.items()}
    rep = A.migrate_all(subs, ts=1790000000)
    assert rep["migrated"] == 4 and rep["already"] == 0 and rep["watchlist_nonempty"] == 3
    assert rep["from_follow"] == 1 and rep["from_tickers"] == 1 and rep["from_alerts"] == 1
    assert subs["u1@ornek.com"]["watchlist"] == ["THYAO"] and "follow" not in subs["u1@ornek.com"]
    assert subs["u2@ornek.com"]["notify"] == {"trend": True, "bulten": False}
    for e in ("u1@ornek.com", "u2@ornek.com", "u4@ornek.com"):
        assert [c[0] for c in A.relevant_changes(subs[e], CH)] == [c[0] for c in before[e]], e
    assert A.watch_set(subs["u1@ornek.com"]) == {"THYAO"}
    assert "@" not in json.dumps(rep)
    assert A.migrate_all(subs)["already"] == 4


def test_relevant_changes_by_prefs():
    rec = {"account_v": 1, "watchlist": ["THYAO"], "portfolio": {}, "notify": {"trend": True, "bulten": False}}
    assert [c[0] for c in A.relevant_changes(rec, CH)] == ["THYAO"]
    rec["notify"] = {"trend": False, "bulten": True}
    assert [c[0] for c in A.relevant_changes(rec, CH)] == ["THYAO", "ASELS", "SASA"]
    assert [c[0] for c in A.relevant_changes(rec, CH, premium_only=True)] == ["THYAO", "ASELS"]
    rec["notify"] = {"trend": False, "bulten": False}
    assert A.relevant_changes(rec, CH) == []


def test_origin_check():
    host = "https://borsapusula.com/"
    assert A.origin_allowed("https://borsapusula.com", None, host)
    assert A.origin_allowed(None, "https://borsapusula.com/takip", host)
    assert A.origin_allowed("http://127.0.0.1:5000", None, "http://127.0.0.1:5000/")
    assert not A.origin_allowed("https://evil.example", "https://borsapusula.com/", host)
    assert not A.origin_allowed("https://borsapusula.com.evil.example", None, host)
    assert not A.origin_allowed(None, None, host)


def test_store_error_never_overwrites(tmp_path):
    p = tmp_path / "subscribers.json"
    p.write_text("{bozuk", encoding="utf-8")
    st = A.FileStore(str(p))
    with pytest.raises(A.StoreError):
        with st.update() as d:
            d["x"] = 1
    assert p.read_text(encoding="utf-8") == "{bozuk"


def test_pepper_file_created_once(tmp_path):
    path = str(tmp_path / "auth_pepper.key")
    a = A.load_or_create_pepper("", path)
    b = A.load_or_create_pepper(None, path)
    assert a == b and len(a) >= 32
    assert oct(os.stat(path).st_mode & 0o777) == "0o600"
    assert A.load_or_create_pepper("x" * 20, path) == b"x" * 20


def test_pepper_concurrent_workers_agree(tmp_path):
    """4 gunicorn işçisi aynı anda açılır: hepsi aynı pepper'ı görmeli (yarım dosya okunmaz)."""
    import threading as th
    path = str(tmp_path / "auth_pepper.key")
    got, errs = [], []

    def run():
        try:
            got.append(A.load_or_create_pepper("", path))
        except Exception as e:  # pragma: no cover
            errs.append(e)
    ts = [th.Thread(target=run) for _ in range(8)]
    for t in ts:
        t.start()
    for t in ts:
        t.join()
    assert not errs and len(set(got)) == 1 and len(got[0]) >= 32
    assert [f for f in os.listdir(tmp_path) if f.endswith(".tmp")] == []
    (tmp_path / "kisa.key").write_bytes(b"abc")
    with pytest.raises(ValueError):
        A.load_or_create_pepper("", str(tmp_path / "kisa.key"))


def test_tr_number_parsing_matches_client_canon():
    """accounts._num = static/bp-format.js bpParseTrNumber (K-BA) — aynı girdi, aynı sayı."""
    cases = {"210,80": 210.8, "1.234,56": 1234.56, "1.500.000": 1500000.0, "9.86": 9.86, "1500": 1500.0,
             " 12 ": 12.0, "abc": None, "1,2,3": None, "": None, "1e5": None, "-3": -3.0}
    for raw, want in cases.items():
        got = A._num(raw)
        assert (got is None and want is None) or got == pytest.approx(want), (raw, got)
    assert A.clean_position("1.500.000", "0,5") == (1500000, 0.5)
    assert A.clean_position("1.5", "10") is None and A.clean_position(True, 1) is None
