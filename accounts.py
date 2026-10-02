"""D-50 — hesap çekirdeği: şifresiz e-posta kodu, oturum, izleme listesi, portföy.

O16g=B (liste/portföy hesaba bağlı), O24=A (şifresiz e-posta kodu), O25=A (önce PWA,
sonra aynı API). Saf modül: Flask'a bağlı değil, Python 3.9 ile çalışır; app.py yalnız
ince rota bağlantısıdır. Yerel testler: tests/test_d50_accounts.py.

İKİNCİ SİSTEM YOK. Hesap = subscribers.json'daki abone kaydı (aynı dosya, aynı kilit,
aynı atomik yazım). Kayıt genişler:
    account_v:1, watchlist:[T..], portfolio:{T:{qty,cost,ts}}, notify:{trend,bulten},
    confirmed_at (kodla e-posta sahipliği kanıtlandı), kvkk_consent_ts, last_login_at
Eski alanlar (token, tickers, follow, alerts, mail_pref, ...) yerinde kalır; eski kayıt
okunurken `account_fields()` aynı görünümü türetir (göç koşmadan da doğru çalışır).

Yan dosyalar (kişisel veri; .gitignore'da):
    sessions.json     sha256(oturum belirteci) -> {e, c, x}   (belirtecin kendisi saklanmaz)
    login_codes.json  hmac(e-posta) -> {h, s, c, x, n, k} | {lu}  (kodun kendisi saklanmaz)

Güvenlik kuralları (D-50 kabulü):
- Kod 6 hane, 10 dk geçerli, tek kullanımlık; yalnız HMAC-SHA256(pepper, tuz:e-posta:kod) saklanır.
- 5 yanlış denemede kod silinir ve e-posta 15 dk kilitlenir. Karşılaştırma sabit zamanlı.
- Kod isteği: e-posta başına 3/15 dk ve 10/24 sa; IP başına 10/sa. Doğrulama: IP başına 30/sa.
- Yanıtlar e-postanın kayıtlı olup olmadığını sızdırmaz (kod her adrese aynı biçimde gider:
  kayıtlıysa giriş, değilse hesap açılışı).
- KVKK kutusu işaretsizse istek 400; onay zamanı hesaba yazılır.
- Oturum 90 gün, sunucu tarafında iptal edilebilir (sessions.json kaydı silinir).
- Log satırlarında e-posta maskelidir (email_mask.mask_email).
"""
from __future__ import annotations

import hashlib
import hmac
import json
import logging
import math
import os
import re
import secrets
import tempfile
import threading
import time
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone

from email_mask import mask_email

logger = logging.getLogger("bist30")

TZ_TR = timezone(timedelta(hours=3))

CODE_TTL = 600                    # 10 dk
CODE_MAX_ATTEMPTS = 5
LOCK_SECONDS = 900                # 5 yanlış -> 15 dk kilit
SESSION_TTL = 90 * 86400          # 90 gün
CODE_REQ_EMAIL = ((3, 900), (10, 86400))
CODE_REQ_IP = (10, 3600)
VERIFY_IP = (30, 3600)
MAX_WATCH = 100
MAX_POSITIONS = 100
MAX_IMPORT_ITEMS = 500
MAX_QTY = 1e9
MAX_COST = 1e9

EMAIL_RE = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")
TICKER_RE = re.compile(r"^[A-Z0-9]{2,10}$")
CODE_RE = re.compile(r"^\d{6}$")
TOKEN_RE = re.compile(r"^[A-Za-z0-9_-]{20,128}$")

MSG = {
    "email_invalid": "Geçerli bir e-posta adresi yaz.",
    "kvkk_required": "Devam etmek için KVKK aydınlatma metnini onayla.",
    "rate_limited": "Çok fazla istek geldi. Biraz sonra yeniden dene.",
    "locked": "Çok fazla yanlış deneme. 15 dakika sonra yeni kod iste.",
    "mail_failed": "Kod e-postası şu an gönderilemedi. Biraz sonra yeniden dene.",
    "code_sent": "Kodu e-postana gönderdik. 10 dakika geçerli.",
    "code_format": "Kod 6 haneli bir sayı olmalı.",
    "code_invalid": "Kod yanlış.",
    "code_expired": "Kod geçersiz ya da süresi doldu. Yeni kod iste.",
    "login_required": "Bu işlem için giriş yap.",
    "ticker_invalid": "Bu hisse kodu takip edilemiyor.",
    "limit": "Listede en fazla 100 hisse olabilir.",
    "position_invalid": "Adet tam sayı, maliyet sıfırdan büyük olmalı.",
    "store_error": "Kayıt şu an okunamadı. Biraz sonra yeniden dene.",
}


class StoreError(Exception):
    """Kalıcı dosya okunamadı/yazılamadı — yazma iptal edilir (boş sözlükle ezilmez)."""


# ── Depolama ────────────────────────────────────────────────────────────────

def read_json(path):
    if not os.path.exists(path):
        return {}
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def atomic_write_json(path, data):
    """tempfile + fsync + os.replace (app._atomic_write_json ile aynı desen)."""
    d = os.path.dirname(os.path.abspath(path))
    fd, tmp = tempfile.mkstemp(dir=d, suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=1)
            f.flush()
            os.fsync(f.fileno())
        os.chmod(tmp, 0o600)
        os.replace(tmp, path)
    except Exception:
        if os.path.exists(tmp):
            os.unlink(tmp)
        raise


class FileStore:
    """JSON dosyası + dışarıdan verilen kilit (app: _CrossProcessLock).

    Aynı dosyaya giden HER yazar aynı kilit nesnesini paylaşmalı: gevent altında ayrı
    bir flock tanımlayıcısı aynı süreçte kilitlenir (bkz. app._CrossProcessLock notu).
    """

    def __init__(self, path, lock=None, load=None, save=None):
        self.path = path
        self.lock = lock if lock is not None else threading.Lock()
        self._load = load or (lambda: read_json(self.path))
        self._save = save or (lambda data: atomic_write_json(self.path, data))

    def load(self):
        try:
            data = self._load()
        except Exception as e:  # bozuk JSON / G/Ç
            raise StoreError("%s okunamadı: %s" % (os.path.basename(self.path), type(e).__name__))
        if data is None:   # app: threadpool zaman aşımı -> "bilinmiyor", boş değil
            raise StoreError("%s okunamadı (zaman aşımı)" % os.path.basename(self.path))
        if not isinstance(data, dict):
            raise StoreError("%s beklenmeyen biçim" % os.path.basename(self.path))
        return data

    @contextmanager
    def update(self):
        with self.lock:
            data = self.load()
            yield data
            self._save(data)


# ── Saf yardımcılar ─────────────────────────────────────────────────────────

def now_iso(ts=None):
    return datetime.fromtimestamp(ts if ts is not None else time.time(), TZ_TR).isoformat(timespec="seconds")


def normalize_email(raw):
    e = (raw or "").strip().lower() if isinstance(raw, str) else ""
    if not e or len(e) > 254 or not EMAIL_RE.match(e):
        return None
    return e


def normalize_ticker(raw):
    if not isinstance(raw, str):
        return None
    t = raw.strip().upper()
    return t if TICKER_RE.match(t) else None


def mask_ui(email):
    """Arayüz maskesi (taslak: "ay•••@ornek.com")."""
    local, sep, domain = (email or "").rpartition("@")
    if not sep:
        return ""
    return local[:2] + "•••@" + domain


def _num(v):
    if isinstance(v, bool):
        return None
    if isinstance(v, (int, float)):
        f = float(v)
    elif isinstance(v, str):
        # static/bp-format.js bpParseTrNumber (K-BA) ile birebir: virgül varsa noktalar binlik
        # ve virgül ondalık ("1.234,56"); virgül yok ama birden çok nokta varsa hepsi binlik
        # ("1.500.000"); tek nokta ondalıktır ("9.86").
        s = v.strip().replace(" ", "")
        if "," in s:
            s = s.replace(".", "").replace(",", ".", 1)
        elif s.count(".") > 1:
            s = s.replace(".", "")
        if not re.match(r"^[+-]?\d*\.?\d+$", s):
            return None
        f = float(s)
    else:
        return None
    return f if math.isfinite(f) else None


def clean_position(qty, cost):
    """(adet, maliyet) doğrula -> (int, float) ya da None. Adet tam sayı >= 1."""
    q, c = _num(qty), _num(cost)
    if q is None or c is None or q < 1 or q > MAX_QTY or q != int(q) or c <= 0 or c > MAX_COST:
        return None
    return int(q), round(c, 4)


def _dedupe_upper(seq):
    out = []
    for x in seq or []:
        t = normalize_ticker(x) if isinstance(x, str) else None
        if t and t not in out:
            out.append(t)
    return out


def account_fields(rec):
    """Kaydın hesap görünümü: {watchlist, portfolio, notify}. Göç edilmemiş eski kayıtta
    türetilir: izleme listesi = tickers ∪ follow ∪ alerts anahtarları; `tickers` bir FİLTREDİR
    (boş = hepsi) -> boşsa bülten açık (eski davranış: tüm değişimler), doluysa yalnız liste."""
    rec = rec or {}
    if rec.get("account_v") == 1:
        wl = _dedupe_upper(rec.get("watchlist"))
        pf = {}
        for t, p in (rec.get("portfolio") or {}).items():
            if isinstance(p, dict) and normalize_ticker(t):
                cp = clean_position(p.get("qty"), p.get("cost"))
                if cp:
                    pf[t] = {"qty": cp[0], "cost": cp[1]}
        n = rec.get("notify") if isinstance(rec.get("notify"), dict) else {}
        notify = {"trend": bool(n.get("trend", True)), "bulten": bool(n.get("bulten", False))}
        return {"watchlist": wl, "portfolio": pf, "notify": notify}
    tickers = _dedupe_upper(rec.get("tickers"))
    alerts = list((rec.get("alerts") or {}).keys()) if isinstance(rec.get("alerts"), dict) else []
    wl = _dedupe_upper(list(tickers) + list(rec.get("follow") or []) + alerts)
    return {"watchlist": wl, "portfolio": {}, "notify": {"trend": True, "bulten": not tickers}}


def watch_set(rec):
    """Özet/anlık e-postadaki "TAKİPTE" kümesi = hesabın izleme listesi (D-P1-2509 `follow` yerine)."""
    return set(account_fields(rec)["watchlist"])


def migrate_record(rec, ts=None):
    """Eski abone kaydını yerinde hesap biçimine çevirir. Zaten hesapsa False (idempotent)."""
    if rec.get("account_v") == 1:
        return False
    f = account_fields(rec)
    rec["watchlist"] = f["watchlist"]
    rec["portfolio"] = {}
    rec["notify"] = f["notify"]
    rec.pop("follow", None)                  # izleme listesine taşındı (tek kaynak)
    rec.setdefault("confirmed_at", None)     # e-posta sahipliği henüz kodla kanıtlanmadı
    rec.setdefault("kvkk_consent_ts", None)  # onay zamanı bilinmiyor: ilk kodlu girişte yazılır
    rec["account_v"] = 1
    rec["migrated_at"] = now_iso(ts)
    return True


def migrate_all(subs, ts=None):
    """subscribers sözlüğünü yerinde göç ettirir; e-posta içermeyen sayım raporu döner."""
    rep = {"records": 0, "migrated": 0, "already": 0, "active": 0, "watchlist_nonempty": 0,
           "watchlist_items": 0, "from_tickers": 0, "from_follow": 0, "from_alerts": 0,
           "bulten_on": 0, "bulten_off_filter": 0, "skipped_bad": 0}
    for _email, rec in subs.items():
        rep["records"] += 1
        if not isinstance(rec, dict):
            rep["skipped_bad"] += 1
            continue
        if rec.get("account_v") == 1:
            rep["already"] += 1
            continue
        rep["from_tickers"] += len(_dedupe_upper(rec.get("tickers")))
        rep["from_follow"] += len(_dedupe_upper(rec.get("follow")))
        rep["from_alerts"] += len(rec.get("alerts") or {}) if isinstance(rec.get("alerts"), dict) else 0
        migrate_record(rec, ts)
        rep["migrated"] += 1
        if rec.get("active", True):
            rep["active"] += 1
        if rec["watchlist"]:
            rep["watchlist_nonempty"] += 1
            rep["watchlist_items"] += len(rec["watchlist"])
        if rec["notify"]["bulten"]:
            rep["bulten_on"] += 1
        else:
            rep["bulten_off_filter"] += 1
    return rep


def relevant_changes(rec, changes, premium_only=False):
    """Özet/anlık e-posta için bu hesaba giden değişimler. changes: (ticker, eski, yeni, stock).
    notify.trend  = izlenen hissenin durumu değişince (yalnız liste);
    notify.bulten = akşam bülteni (tüm değişimler, liste başta — sıralama _build_signal_email'de).
    İkisi kapalıysa boş. Eski kayıtta account_fields() eski filtreyi birebir üretir."""
    f = account_fields(rec)
    n, wl = f["notify"], set(f["watchlist"])
    if not (n["trend"] or n["bulten"]):
        return []
    rel = list(changes)
    if premium_only:
        rel = [c for c in rel if (c[3] or {}).get("is_premium") or c[0] in wl]
    if not n["bulten"]:
        rel = [c for c in rel if c[0] in wl]
    return rel


def merge_import(rec, payload, valid_ticker):
    """Tarayıcı listesini hesaba birleştirir (yerinde). İzleme listesi birleşim; pozisyon
    yalnız hesapta o hisse için pozisyon YOKSA eklenir (sunucu kazanır). Aynı hissenin
    birden çok yerel lotu tek pozisyona toplanır: adet toplam, maliyet ağırlıklı ortalama."""
    payload = payload if isinstance(payload, dict) else {}
    migrate_record(rec)
    wl, pf = rec["watchlist"], rec.setdefault("portfolio", {})
    added_w = added_p = 0
    skipped = []

    def _skip(x):
        if len(skipped) < 20:
            skipped.append(str(x)[:12])

    raw_w = payload.get("watchlist") if isinstance(payload.get("watchlist"), list) else []
    for raw in raw_w[:MAX_IMPORT_ITEMS]:
        t = normalize_ticker(raw.get("ticker") if isinstance(raw, dict) else raw)
        if not t or not valid_ticker(t):
            _skip(raw if not isinstance(raw, dict) else raw.get("ticker"))
            continue
        if t in wl:
            continue
        if len(wl) >= MAX_WATCH:
            _skip(t)
            continue
        wl.append(t)
        added_w += 1

    agg = {}
    raw_p = payload.get("portfolio") if isinstance(payload.get("portfolio"), list) else []
    for p in raw_p[:MAX_IMPORT_ITEMS]:
        if not isinstance(p, dict):
            continue
        t = normalize_ticker(p.get("ticker"))
        qty = p.get("qty", p.get("lot", p.get("quantity")))
        cost = p.get("cost", p.get("price", p.get("buy_price")))
        cp = clean_position(qty, cost)
        if not t or not valid_ticker(t) or not cp:
            _skip(p.get("ticker"))
            continue
        a = agg.setdefault(t, [0, 0.0])
        a[0] += cp[0]
        a[1] += cp[0] * cp[1]
    for t, (q, total) in agg.items():
        if t in pf:
            continue
        if len(pf) >= MAX_POSITIONS or (t not in wl and len(wl) >= MAX_WATCH):
            _skip(t)
            continue
        cp = clean_position(q, total / q)
        if not cp:
            _skip(t)
            continue
        pf[t] = {"qty": cp[0], "cost": cp[1], "ts": int(time.time())}
        if t not in wl:
            wl.append(t)
            added_w += 1
        added_p += 1
    return {"watchlist_added": added_w, "portfolio_added": added_p, "skipped": skipped}


def last_changes(*pending_lists):
    """pending_changes(.weekly).json kayıtlarından hisse başına EN SON değişim {old,new,ts}."""
    out = {}
    for lst in pending_lists:
        for d in lst or []:
            if not isinstance(d, dict) or not d.get("ticker"):
                continue
            t = d["ticker"]
            if t not in out or str(d.get("ts") or "") >= str(out[t].get("ts") or ""):
                out[t] = d
    return out


def watch_items(fields, rows, bp_scores, changes, names=None):
    """/api/me/watchlist satırları — hesap listesi sırasıyla, gün sonu piyasa satırıyla.
    prev_signal yalnız değişim son seanstaysa (signal_bars <= 1) ve yeni durum eşleşiyorsa."""
    names = names or {}
    out = []
    for t in fields["watchlist"]:
        s = rows.get(t) or {}
        pos = fields["portfolio"].get(t)
        sig, bars = s.get("signal"), s.get("signal_bars")
        prev = None
        ch = changes.get(t)
        if (isinstance(ch, dict) and isinstance(bars, int) and bars <= 1
                and ch.get("new") == sig and ch.get("old") and ch.get("old") != sig):
            prev = ch.get("old")
        out.append({
            "ticker": t, "name": s.get("name") or names.get(t) or t, "sector": s.get("sector"),
            "price": s.get("price"), "change_pct": s.get("change_pct"), "signal": sig,
            "signal_bars": bars, "signal_date": s.get("signal_date"), "prev_signal": prev,
            "bp": bp_scores.get(t), "qty": pos["qty"] if pos else None, "cost": pos["cost"] if pos else None,
        })
    return out


def origin_allowed(origin, referer, host_url, extra=("https://borsapusula.com", "https://www.borsapusula.com")):
    """CSRF: çerezle yetkilenen durum değiştiren istekte Origin (yoksa Referer) bu siteden
    olmalı. İkisi de yoksa ret (tarayıcılar POST/PUT/DELETE fetch'te Origin gönderir)."""
    def _o(u):
        m = re.match(r"^(https?://[^/?#]+)", (u or "").strip().lower())
        return m.group(1) if m else None
    allowed = {x.lower() for x in extra}
    own = _o(host_url)
    if own:
        allowed.add(own)
    src = _o(origin) if origin and origin != "null" else _o(referer)
    return bool(src) and src in allowed


# ── Servis ──────────────────────────────────────────────────────────────────

class Result:
    __slots__ = ("status", "body", "code", "token")

    def __init__(self, status, body, code=None, token=None):
        self.status, self.body, self.code, self.token = status, body, code, token


def _err(status, key, **extra):
    b = {"ok": False, "error": key, "message": MSG.get(key, key)}
    b.update(extra)
    return Result(status, b)


class AccountService:
    """subs: abone/hesap deposu (app: _sub_lock + _load/_save). sessions/codes: yan dosyalar.
    rate_allow(bucket, key, max, window) -> bool (app: _mail_route_allowed, diskte, süreçler arası).
    valid_ticker(T) -> bool (app: evren içi, endeks değil)."""

    def __init__(self, subs, sessions, codes, pepper, valid_ticker, rate_allow=None, clock=time.time):
        if not pepper or len(pepper) < 16:
            raise ValueError("pepper en az 16 bayt olmalı")
        self.subs, self.sessions, self.codes = subs, sessions, codes
        self.pepper = pepper if isinstance(pepper, bytes) else pepper.encode()
        self.valid_ticker = valid_ticker
        self.rate_allow = rate_allow or (lambda bucket, key, n, w: True)
        self.clock = clock

    # ── anahtarlar ──
    def ekey(self, email):
        return hmac.new(self.pepper, ("e:" + email).encode(), hashlib.sha256).hexdigest()[:32]

    def _code_hash(self, salt, email, code):
        return hmac.new(self.pepper, ("%s:%s:%s" % (salt, email, code)).encode(), hashlib.sha256).hexdigest()

    @staticmethod
    def _sid(token):
        return hashlib.sha256(token.encode()).hexdigest()

    # ── kod isteği ──
    def request_code(self, email_raw, kvkk, ip):
        """Başarıda Result.code = düz kod (yalnız bellekte; app e-postalar, gönderemezse cancel_code)."""
        email = normalize_email(email_raw)
        if not email:
            return _err(400, "email_invalid")
        if kvkk is not True:
            return _err(400, "kvkk_required")
        if not self.rate_allow("acct_code_ip", ip or "-", CODE_REQ_IP[0], CODE_REQ_IP[1]):
            return _err(429, "rate_limited", retry_after=CODE_REQ_IP[1])
        now = self.clock()
        k = self.ekey(email)
        # Kilit ve hız sınırı her adres için aynı işler (kayıtlı olsun olmasın) -> sızıntı yok.
        # Kilitler iç içe alınmaz: önce okuma (atomik dosya), sonra sayaç, sonra yazma kilidi.
        ent = self.codes.load().get(k) or {}
        if isinstance(ent, dict) and ent.get("lu", 0) > now:
            return _err(429, "locked", retry_after=int(ent["lu"] - now))
        for n, w in CODE_REQ_EMAIL:
            if not self.rate_allow("acct_code_email_%d" % w, k, n, w):
                return _err(429, "rate_limited", retry_after=w)
        code = "%06d" % secrets.randbelow(1000000)
        salt = secrets.token_hex(8)
        with self.codes.update() as codes:
            self._prune_codes(codes, now)
            cur = codes.get(k) or {}
            if isinstance(cur, dict) and cur.get("lu", 0) > now:     # arada kilitlendiyse
                return _err(429, "locked", retry_after=int(cur["lu"] - now))
            # Yeni kod eskisinin yerine geçer; deneme sayacı SIFIRLANMAZ (kod yenileyerek
            # 5 deneme sınırı aşılamasın): önceki kodun yanlış denemeleri taşınır.
            carried = int(cur.get("n", 0)) if isinstance(cur, dict) and cur.get("x", 0) > now else 0
            codes[k] = {"h": self._code_hash(salt, email, code), "s": salt, "c": int(now),
                        "x": int(now + CODE_TTL), "n": carried, "k": now_iso(now)}
        logger.info("Hesap kodu uretildi: %s", mask_email(email))
        return Result(200, {"ok": True, "message": MSG["code_sent"]}, code=code)

    def cancel_code(self, email_raw):
        email = normalize_email(email_raw)
        if not email:
            return
        with self.codes.update() as codes:
            codes.pop(self.ekey(email), None)

    @staticmethod
    def _prune_codes(codes, now):
        for k in [k for k, v in codes.items()
                  if not isinstance(v, dict) or (v.get("x", 0) <= now and v.get("lu", 0) <= now)]:
            del codes[k]

    # ── kod doğrulama ──
    def verify_code(self, email_raw, code_raw, ip, import_payload=None):
        """Başarıda Result.token = yeni oturum belirteci (çereze yazılır, sunucuda yalnız özeti)."""
        email = normalize_email(email_raw)
        if not email:
            return _err(400, "email_invalid")
        if not self.rate_allow("acct_verify_ip", ip or "-", VERIFY_IP[0], VERIFY_IP[1]):
            return _err(429, "rate_limited", retry_after=VERIFY_IP[1])
        code = re.sub(r"[\s-]", "", code_raw) if isinstance(code_raw, str) else ""
        if not CODE_RE.match(code):
            return _err(400, "code_format")
        now = self.clock()
        k = self.ekey(email)
        with self.codes.update() as codes:
            ent = codes.get(k)
            if isinstance(ent, dict) and ent.get("lu", 0) > now:
                return _err(429, "locked", retry_after=int(ent["lu"] - now))
            if not isinstance(ent, dict) or not ent.get("h") or ent.get("x", 0) <= now:
                if isinstance(ent, dict) and ent.get("h"):
                    codes.pop(k, None)            # süresi dolmuş kod temizlenir
                return _err(400, "code_expired")
            ok = hmac.compare_digest(ent["h"], self._code_hash(ent.get("s", ""), email, code))
            if not ok:
                ent["n"] = int(ent.get("n", 0)) + 1
                if ent["n"] >= CODE_MAX_ATTEMPTS:
                    codes[k] = {"lu": int(now + LOCK_SECONDS), "x": 0}
                    logger.warning("Hesap kodu kilitlendi (5 yanlis): %s", mask_email(email))
                    return _err(429, "locked", retry_after=LOCK_SECONDS)
                return _err(400, "code_invalid", attempts_left=CODE_MAX_ATTEMPTS - ent["n"])
            kvkk_ts = ent.get("k")
            codes.pop(k, None)                    # tek kullanımlık
        # e-posta sahipliği kanıtlandı -> hesap aç / güncelle (kilitler iç içe değil)
        with self.subs.update() as subs:
            rec = subs.get(email)
            created = rec is None
            if created:
                rec = subs[email] = {
                    "token": secrets.token_hex(24), "subscribed_at": now_iso(now), "name": "",
                    "tickers": [], "active": True, "level": None, "freq": None, "segments": [],
                    "mail_pref": "daily", "profile_done": False,
                }
                migrate_record(rec, now)
                rec["notify"] = {"trend": True, "bulten": False}
                rec.pop("migrated_at", None)
            else:
                migrate_record(rec, now)
                if not rec.get("active", True):
                    rec["active"] = True
                    rec["notify"] = {"trend": False, "bulten": False}   # pasif hesap: e-posta kendiliğinden açılmaz
            if not rec.get("confirmed_at"):
                rec["confirmed_at"] = now_iso(now)
            if not rec.get("kvkk_consent_ts"):
                rec["kvkk_consent_ts"] = kvkk_ts or now_iso(now)
            rec["last_login_at"] = now_iso(now)
            imported = merge_import(rec, import_payload, self.valid_ticker) if import_payload else \
                {"watchlist_added": 0, "portfolio_added": 0, "skipped": []}
            view = self.me_view(email, rec)
        token = self.create_session(email)
        logger.info("Hesap girisi: %s (yeni=%s, aktarilan=%d/%d)", mask_email(email), created,
                    imported["watchlist_added"], imported["portfolio_added"])
        return Result(200, {"ok": True, "me": view, "imported": imported}, token=token)

    # ── oturum ──
    def create_session(self, email):
        token = secrets.token_urlsafe(32)
        now = self.clock()
        with self.sessions.update() as ss:
            for sid in [s for s, v in ss.items() if not isinstance(v, dict) or v.get("x", 0) <= now]:
                del ss[sid]
            ss[self._sid(token)] = {"e": email, "c": int(now), "x": int(now + SESSION_TTL)}
        return token

    def session_email(self, token):
        if not isinstance(token, str) or not TOKEN_RE.match(token):
            return None
        try:
            ss = self.sessions.load()
        except StoreError:
            return None
        v = ss.get(self._sid(token))
        if not isinstance(v, dict) or v.get("x", 0) <= self.clock():
            return None
        return v.get("e")

    def revoke_session(self, token):
        if not isinstance(token, str) or not TOKEN_RE.match(token):
            return False
        with self.sessions.update() as ss:
            return ss.pop(self._sid(token), None) is not None

    def revoke_all(self, email):
        with self.sessions.update() as ss:
            dead = [s for s, v in ss.items() if isinstance(v, dict) and v.get("e") == email]
            for s in dead:
                del ss[s]
        return len(dead)

    def forget(self, email):
        """Hesap silinince/abonelik iptalinde: oturumlar + bekleyen kod da gider (KVKK)."""
        n = self.revoke_all(email)
        with self.codes.update() as codes:
            codes.pop(self.ekey(email), None)
        return n

    # ── okuma ──
    def account(self, email):
        """(kayıt) ya da None — oturum var ama hesap silinmiş/pasifse None."""
        if not email:
            return None
        rec = self.subs.load().get(email)
        if not isinstance(rec, dict) or not rec.get("active", True):
            return None
        return rec

    @staticmethod
    def me_view(email, rec):
        f = account_fields(rec)
        name = (rec.get("name") or "").strip()
        return {
            "ok": True, "logged_in": True, "subscribed": bool(rec.get("active", True)),
            "email": email, "email_masked": mask_ui(email),
            "first_name": name.split()[0] if name else "",
            "confirmed_at": rec.get("confirmed_at"), "kvkk_consent_ts": rec.get("kvkk_consent_ts"),
            "notify": f["notify"], "mail_pref": rec.get("mail_pref") or "daily",
            "profile_done": bool(rec.get("profile_done")),
            "counts": {"watchlist": len(f["watchlist"]), "portfolio": len(f["portfolio"])},
        }

    @staticmethod
    def portfolio_view(rec):
        f = account_fields(rec)
        return [{"ticker": t, "qty": f["portfolio"][t]["qty"], "cost": f["portfolio"][t]["cost"]}
                for t in f["watchlist"] if t in f["portfolio"]]

    # ── yazma ──
    @contextmanager
    def _edit(self, email):
        with self.subs.update() as subs:
            rec = subs.get(email)
            if not isinstance(rec, dict) or not rec.get("active", True):
                raise LookupError("hesap yok")
            migrate_record(rec, self.clock())
            yield rec

    def watch_add(self, email, ticker_raw):
        t = normalize_ticker(ticker_raw)
        if not t or not self.valid_ticker(t):
            return _err(400, "ticker_invalid")
        with self._edit(email) as rec:
            wl = rec["watchlist"]
            if t in wl:
                return Result(200, {"ok": True, "added": False, "ticker": t, "watchlist": list(wl)})
            if len(wl) >= MAX_WATCH:
                return _err(400, "limit")
            wl.append(t)
            return Result(200, {"ok": True, "added": True, "ticker": t, "watchlist": list(wl)})

    def watch_remove(self, email, ticker_raw):
        t = normalize_ticker(ticker_raw)
        if not t:
            return _err(400, "ticker_invalid")
        with self._edit(email) as rec:
            removed = t in rec["watchlist"]
            rec["watchlist"] = [x for x in rec["watchlist"] if x != t]
            rec["portfolio"].pop(t, None)
            return Result(200, {"ok": True, "removed": removed, "ticker": t, "watchlist": list(rec["watchlist"])})

    def watch_replace(self, email, watchlist, portfolio=None):
        if not isinstance(watchlist, list) or (portfolio is not None and not isinstance(portfolio, list)):
            return _err(400, "ticker_invalid")
        with self._edit(email) as rec:
            new_pf = rec["portfolio"] if portfolio is None else {}
            rec["watchlist"], rec["portfolio"] = [], {}
            res = merge_import(rec, {"watchlist": watchlist, "portfolio": portfolio or []}, self.valid_ticker)
            if portfolio is None:          # pozisyonlar korunur, yalnız listede kalanlar
                rec["portfolio"] = {t: p for t, p in new_pf.items() if t in rec["watchlist"]}
            return Result(200, {"ok": True, "watchlist": list(rec["watchlist"]),
                                "portfolio": self.portfolio_view(rec), "skipped": res["skipped"]})

    def position_set(self, email, ticker_raw, qty, cost):
        t = normalize_ticker(ticker_raw)
        if not t or not self.valid_ticker(t):
            return _err(400, "ticker_invalid")
        cp = clean_position(qty, cost)
        if not cp:
            return _err(400, "position_invalid")
        with self._edit(email) as rec:
            wl, pf = rec["watchlist"], rec["portfolio"]
            if t not in wl:
                if len(wl) >= MAX_WATCH:
                    return _err(400, "limit")
                wl.append(t)
            if t not in pf and len(pf) >= MAX_POSITIONS:
                return _err(400, "limit")
            pf[t] = {"qty": cp[0], "cost": cp[1], "ts": int(self.clock())}
            return Result(200, {"ok": True, "position": {"ticker": t, "qty": cp[0], "cost": cp[1]},
                                "watchlist": list(wl)})

    def position_remove(self, email, ticker_raw):
        t = normalize_ticker(ticker_raw)
        if not t:
            return _err(400, "ticker_invalid")
        with self._edit(email) as rec:
            removed = rec["portfolio"].pop(t, None) is not None
            return Result(200, {"ok": True, "removed": removed, "ticker": t})

    def import_merge(self, email, payload):
        with self._edit(email) as rec:
            res = merge_import(rec, payload, self.valid_ticker)
            return Result(200, {"ok": True, "imported": res})

    def set_prefs(self, email, prefs):
        prefs = prefs if isinstance(prefs, dict) else {}
        with self._edit(email) as rec:
            n = account_fields(rec)["notify"]
            for key in ("trend", "bulten"):
                if isinstance(prefs.get(key), bool):
                    n[key] = prefs[key]
            rec["notify"] = n
            if n["trend"] or n["bulten"]:
                if rec.get("mail_pref") not in ("daily", "weekly", "instant", "premium"):
                    rec["mail_pref"] = "daily"
            return Result(200, {"ok": True, "notify": dict(n)})

    def delete_account(self, email):
        with self.subs.update() as subs:
            existed = subs.pop(email, None) is not None
        self.forget(email)
        if existed:
            logger.info("Hesap silindi (KVKK): %s", mask_email(email))
        return existed


def load_or_create_pepper(env_value, path):
    """BP_AUTH_PEPPER ortam değişkeni; yoksa diskte bir kez üretilen 32 bayt (0600).
    Tüm gunicorn işçileri aynı değeri görmeli (işçi başına rastgele olursa bir işçinin
    ürettiği kod diğerinde doğrulanamaz)."""
    if env_value and len(env_value) >= 16:
        return env_value.encode()

    def _read():
        with open(path, "rb") as f:
            return f.read().strip()

    try:
        val = _read()
        if len(val) >= 32:
            return val
        raise ValueError("pepper dosyası kısa/bozuk: %s" % path)
    except FileNotFoundError:
        pass
    # Dört işçi aynı anda açılabilir: dosya içeriğiyle birlikte TEK hamlede görünür
    # (geçici dosya + os.link; link hedef varsa FileExistsError) -> kimse yarım dosya okumaz.
    val = secrets.token_hex(32).encode()
    fd, tmp = tempfile.mkstemp(dir=os.path.dirname(os.path.abspath(path)), suffix=".tmp")
    try:
        with os.fdopen(fd, "wb") as f:
            f.write(val)
            f.flush()
            os.fsync(f.fileno())
        os.chmod(tmp, 0o600)
        try:
            os.link(tmp, path)
            return val
        except FileExistsError:       # başka işçi önce yazdı: onunkini kullan
            return _read()
    finally:
        os.unlink(tmp)
