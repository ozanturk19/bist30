#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""KAPI 66 -- K-CU: SUNUCUDA YASAYAN DURUMUN ISTEMCIDEKI SAHIBI.

Kapi 64/65 adres cubugunu (URL) paylasilan yuzey olarak ele aliyordu. Bu kapi
ayni merceği (111. ders: "paylasilan yuzeyin bir SAHIBI var mi") bir sonraki
paylasilan yuzeye tasir: SUNUCUDA tutulan ve istemcide de bir kopyasi bulunan
durum (alarm/abonelik/tercih).

Canli olculen kusur (22.09, /hisse/<T> 🔔 dugmesi):
  Dugmenin durumu YALNIZ `localStorage.bp_watchlist_v2`den okunuyordu; gercek
  e-posta alarmi ise sunucuda yasiyor ve onu `POST/DELETE /api/user-alerts/<T>`
  yaziyordu. `GET /api/user-alerts` uretimde CANLI ama sitenin HICBIR yuzeyi
  onu okumuyordu -- iki kanon, hic bulusmuyorlar. Sonuclari:
    * Telefonda takibe alinan hisse masaustunde "Bildirim al" gorunuyordu;
      e-posta geliyor ama alarm KAPATILAMIYORDU (kapatma dalina ancak yerel
      listede "takipte" gorunurse giriliyordu).
    * Tarayici verisi silinince sunucudaki alarm YETIM kaliyordu: hicbir sayfa
      alarm listesi gostermedigi icin e-postalar suresiz devam ediyordu.
  Pozitif kontrol (harness, eski kod): sunucuda kayitli + yerelde yok iken
  tiklama POST gonderiyordu (kullanici KAPATMAK isterken alarm yeniden
  aciliyordu), ters durumda DELETE -- etiket ile eylem ZIT yone gidiyordu.

Kurallar:
  R1 YAZMA/OKUMA ASIMETRISI -- frontend bir kaynagi POST/DELETE ile YAZIYORSA
     ve app.py o kaynak icin bir GET rotasi sunuyorsa, frontend o GET'i en az
     bir yerde OKUMALI. Okumuyorsa istemcinin gosterdigi durum sunucununkinden
     serbestce ayrisir ve kullanici kendi yazdigi kaydi goremez/geri alamaz.
  R2 DALLANMA SAHIBI -- sunucuya durum YAZAN (POST/DELETE) bir fonksiyonun
     "hangi yone yazacagim" dallanmasi, dogrudan `localStorage` okumasindan
     TUREYEMEZ. Otorite sunucudayken yerel kopyadan dallanmak, etiketin
     soyledigiyle tiklamanin yaptigini ters yone dusurur (K-CU'nun ta kendisi).
     Muaf: giris/oturum gerektirmeyen, yalniz yerel yasayan durum -- yani ayni
     fonksiyon sunucuya hic yazmiyorsa R2 zaten uygulanmaz.
  R3 BOS != BILINMIYOR -- R1'in eslestirdigi kaynaklarin GET okumasi, `r.ok`
     kontrolu VE govde dogrulamasi yapmali ([[K-BK]]: HTTP 200 + eksik govde
     "kaydin yok" demek degildir; oyle yorumlanirsa dugme sunucuda duran bir
     alarmi "yok" diye gosterir).

Kullanim:
  python3 tools/client-server-state-owner-check.py            # agaci tara
  python3 tools/client-server-state-owner-check.py --self-test
  python3 tools/client-server-state-owner-check.py --ref <sha> # regresyon
"""
import os, re, sys, subprocess

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Durum tasiyan API kaynaklari disindaki yazmalar (form gonderimi, olcum,
# oturum acma) bu kapinin konusu degil: onlarin istemcide kalici bir "durum
# kopyasi" yoktur. Kapsam R1'de app.py'nin GET rotasiyla zaten daraltiliyor,
# bu liste yalnizca bilinen istisnalari acik tutar.
_R1_MUAF = {
    '/api/log-error',      # tek yonlu telemetri, istemcide durum kopyasi yok
    '/api/track',
}

_FN_RE = re.compile(r'(?:async\s+)?function\s+([A-Za-z_$][\w$]*)\s*\([^)]*\)\s*\{')


def _read(path, ref=None):
    if ref:
        return subprocess.check_output(['git', 'show', '%s:%s' % (ref, path)],
                                       cwd=ROOT).decode('utf-8')
    with open(os.path.join(ROOT, path), encoding='utf-8') as f:
        return f.read()


def _client_files(ref=None):
    """templates/**/*.html + static/**/*.js"""
    if ref:
        names = subprocess.check_output(['git', 'ls-tree', '-r', '--name-only', ref],
                                        cwd=ROOT).decode('utf-8').split('\n')
        for n in names:
            if (n.startswith('templates/') and n.endswith('.html')) or \
               (n.startswith('static/') and n.endswith('.js')):
                yield n, _read(n, ref)
        return
    for sub, ext in (('templates', '.html'), ('static', '.js')):
        base = os.path.join(ROOT, sub)
        for dirpath, _d, files in os.walk(base):
            for n in sorted(files):
                if n.endswith(ext):
                    rel = os.path.relpath(os.path.join(dirpath, n), ROOT)
                    yield rel, _read(rel, None)


def _body(src, start):
    """start = govde acan '{' indeksi; eslesen '}'e kadar dondurur."""
    depth, i, n = 0, start, len(src)
    while i < n:
        c = src[i]
        if c == '{':
            depth += 1
        elif c == '}':
            depth -= 1
            if depth == 0:
                return src[start:i + 1]
        i += 1
    return src[start:]


def _functions(src):
    for m in _FN_RE.finditer(src):
        b = src.find('{', m.end() - 1)
        if b < 0:
            continue
        yield m.group(1), _body(src, b)


# ── fetch cagrilarini cikar ────────────────────────────────────────────────
_FETCH_RE = re.compile(r'fetch\(\s*([`\'"])(/api/[^`\'"]*)\1\s*(,\s*\{(?P<opt>[^}]*)\})?')


def _norm(url):
    """`/api/user-alerts/${TICKER}` -> ('/api/user-alerts', True)  (alt-yol mu)"""
    u = re.sub(r'\$\{[^}]*\}', '*', url).split('?')[0].rstrip('/')
    parts = [p for p in u.split('/') if p]
    # /api/<kaynak>[/<alt>]
    if len(parts) >= 2:
        base = '/' + '/'.join(parts[:2])
        return base, len(parts) > 2
    return u, False


def _fetches(src):
    out = []
    for m in _FETCH_RE.finditer(src):
        opt = m.group('opt') or ''
        mm = re.search(r"method\s*:\s*['\"](\w+)['\"]", opt)
        method = (mm.group(1) if mm else 'GET').upper()
        base, is_sub = _norm(m.group(2))
        out.append({'base': base, 'sub': is_sub, 'method': method,
                    'pos': m.start(), 'raw': m.group(2)})
    return out


# ── app.py GET rotalari ────────────────────────────────────────────────────
_ROUTE_RE = re.compile(r'@app\.route\(\s*["\']([^"\']+)["\']\s*(?:,\s*methods\s*=\s*\[([^\]]*)\])?\s*\)')


def _get_routes(ref=None):
    src = _read('app.py', ref)
    got = set()
    for m in _ROUTE_RE.finditer(src):
        path, methods = m.group(1), (m.group(2) or '')
        ms = re.findall(r"['\"](\w+)['\"]", methods) or ['GET']
        if 'GET' not in [x.upper() for x in ms]:
            continue
        base, is_sub = _norm(path)
        if not is_sub:            # yalniz koleksiyon/kaynak GET'i sayilir
            got.add(base)
    return got


# ── kurallar ───────────────────────────────────────────────────────────────
def rule_R1(files, get_routes):
    """Yazilan ama GET'i hic okunmayan kaynak."""
    writes, reads = {}, set()
    for name, src in files:
        for f in _fetches(src):
            if f['method'] in ('POST', 'DELETE', 'PUT', 'PATCH'):
                writes.setdefault(f['base'], []).append(name)
            elif f['method'] == 'GET':
                reads.add(f['base'])
    bad = []
    for base, where in sorted(writes.items()):
        if base in _R1_MUAF or base not in get_routes or base in reads:
            continue
        bad.append('R1 %s: POST/DELETE ile yaziliyor (%s), app.py GET rotasi VAR, '
                   'ama hicbir istemci yuzeyi okumuyor -- istemci durumu sunucudan ayrisir'
                   % (base, ', '.join(sorted(set(where)))))
    return bad


# NEGATIF KONTROL DERSI (109/kapi 64): ilk yazim yalniz `const|let|var X = ...`
# bicimini okuyordu; gercek kusurda degisken ONCE `let w;` diye bildirilip
# ATAMA ayri satirdaydi (`w = JSON.parse(localStorage.getItem(...))`) -- kapi
# K-CU'nun kendisini R2'de KACIRIYORDU. Bildirimli ve bildirimsiz atamanin
# ikisi de okunur; ayni kusur iki yazimla yazilabiliyorsa kapi ikisini de gorur.
_LS_READ_RE = re.compile(r'(?:(?:const|let|var)\s+)?([A-Za-z_$][\w$]*)\s*=\s*[^;\n=][^;\n]*localStorage\.getItem')
_DERIVE_RE = re.compile(r'(?:(?:const|let|var)\s+)?([A-Za-z_$][\w$]*)\s*=\s*([^;\n=][^;\n]*)')


def _enclosing_ifs(body, pos):
    """`pos`daki cagriyi KUSATAN if kosullarini dondur (blok ve tek-satir)."""
    out = []
    for m in re.finditer(r'\bif\s*\(', body):
        # kosulun kapanis parantezi (ic ice parantez sayarak)
        i, depth = m.end() - 1, 0
        while i < len(body):
            if body[i] == '(':
                depth += 1
            elif body[i] == ')':
                depth -= 1
                if depth == 0:
                    break
            i += 1
        cond = body[m.end():i]
        j = i + 1
        while j < len(body) and body[j] in ' \t\r\n':
            j += 1
        if j < len(body) and body[j] == '{':
            blk = _body(body, j)
            lo, hi = j, j + len(blk)
        else:                                   # suslu parantezsiz tek deyim
            k = body.find(';', j)
            lo, hi = j, (k if k >= 0 else j)
        if lo <= pos <= hi:
            out.append(cond)
    return out


def rule_R2(files):
    """Sunucuya durum yazan cagriyi KUSATAN yon dallanmasi yerel kopyadan
       gelemez. Uyelik sorgusu (`indexOf`/`includes`/`some`/`has`) ile
       BAKIM dallanmasi (`Array.isArray(w)`, `_safeWrite(w)`) ayrilir:
       birincisi "hangi yone yazayim" sorusudur, ikincisi veri butunlugu."""
    MEMBER = r'\.(?:indexOf|includes|some|find|findIndex|has)\s*\(|\bin\s'
    bad = []
    for name, src in files:
        for fn, body in _functions(src):
            fs = _fetches(body)
            writes = [f for f in fs if f['method'] in ('POST', 'DELETE', 'PUT', 'PATCH')]
            if not writes:
                continue
            base = set(_LS_READ_RE.findall(body))
            if not base:
                continue
            # UYELIK taint'i: yerel kopyada "bu kayit var mi" sorusundan turer
            member = set()
            for _ in range(3):
                for var, rhs in _DERIVE_RE.findall(body):
                    if var in member:
                        continue
                    src_vars = base | member
                    if any(re.search(r'\b%s\b' % re.escape(t), rhs) for t in src_vars) \
                       and re.search(MEMBER, rhs):
                        member.add(var)
            seen = set()
            for f in writes:
                for cond in _enclosing_ifs(body, f['pos']):
                    hit = [t for t in member if re.search(r'\b%s\b' % re.escape(t), cond)]
                    direct = re.search(MEMBER, cond) and any(
                        re.search(r'\b%s\b' % re.escape(t), cond) for t in base)
                    if not hit and not direct:
                        continue
                    key = (name, fn, cond.strip()[:60])
                    if key in seen:
                        continue
                    seen.add(key)
                    bad.append('R2 %s :: %s() -- sunucuya durum YAZAN cagriyi kusatan '
                               'dallanma `%s` yerel kopyadaki uyelik sorgusundan geliyor; '
                               'otorite sunucuda, etiketle eylem ters yone dusebilir'
                               % (name, fn, cond.strip()[:60]))
    return bad


def rule_R3(files, get_routes, r1_bases):
    """R1 kapsamindaki kaynaklarin GET okumasi r.ok + govde dogrulamali."""
    bad = []
    for name, src in files:
        for f in _fetches(src):
            if f['method'] != 'GET' or f['base'] not in r1_bases:
                continue
            tail = src[f['pos']:f['pos'] + 1400]
            if not re.search(r'\br\.ok\b|\bres\.ok\b|\bresp\.ok\b|\.ok\s*\?', tail):
                bad.append('R3 %s: `%s` GET okumasi r.ok kontrolu yapmiyor '
                           '(HTTP 4xx/5xx govdesi "kaydin yok" gibi yorumlanir)' % (name, f['raw']))
                continue
            # govde dogrulamasi: beklenen alanin varligi sinaniyor mu
            if not re.search(r'(?:!\s*j(?:son)?\b|typeof\s+\w+|\bok\s*!==\s*true|throw\s+new\s+Error)', tail):
                bad.append('R3 %s: `%s` GET govdesi dogrulanmiyor '
                           '([[K-BK]] 200 + eksik govde "bos" degil "bilinmiyor"dur)' % (name, f['raw']))
    return bad


# ── self-test ──────────────────────────────────────────────────────────────
_ST_APP = '''
@app.route("/api/user-alerts", methods=["GET"])
def g(): pass
@app.route("/api/user-alerts/<t>", methods=["POST"])
def s(t): pass
'''

_ST_CASES = [
    # (ad, istemci kaynagi, beklenen kural ya da None)
    ('R1 ihlali: yazilan kaynak hic okunmuyor',
     "fetch(`/api/user-alerts/${T}`, { method: 'POST' });", 'R1'),
    ('R1 temiz: GET de okunuyor',
     "fetch('/api/user-alerts', { credentials:'same-origin' }).then(r => r.ok ? r.json() : 0)"
     ".then(j => { if (!j || j.ok !== true) throw new Error('x'); });\n"
     "fetch(`/api/user-alerts/${T}`, { method: 'POST' });", None),
    ('R2 ihlali: dallanma localStorage indeksinden',
     "fetch('/api/user-alerts').then(r => r.ok ? r.json() : 0).then(j => { if (!j) throw new Error('x'); });\n"
     "function tg() {\n  const w = JSON.parse(localStorage.getItem(K) || '[]');\n"
     "  const idx = w.indexOf(T);\n  if (idx >= 0) {\n"
     "    fetch(`/api/user-alerts/${T}`, { method: 'DELETE' });\n  }\n}", 'R2'),
    ('R2 temiz: dallanma paylasilan okuyucudan',
     "fetch('/api/user-alerts').then(r => r.ok ? r.json() : 0).then(j => { if (!j) throw new Error('x'); });\n"
     "function tg() {\n  const w = JSON.parse(localStorage.getItem(K) || '[]');\n"
     "  const st = _state();\n  if (st === 'on') {\n"
     "    fetch(`/api/user-alerts/${T}`, { method: 'DELETE' });\n  }\n}", None),
    ('R3 ihlali: GET okumasi r.ok kontrolsuz',
     "fetch('/api/user-alerts').then(r => r.json()).then(j => { use(j); });\n"
     "fetch(`/api/user-alerts/${T}`, { method: 'POST' });", 'R3'),
]


def _self_test():
    routes = set()
    for m in _ROUTE_RE.finditer(_ST_APP):
        ms = re.findall(r"['\"](\w+)['\"]", m.group(2) or '') or ['GET']
        if 'GET' in [x.upper() for x in ms]:
            base, sub = _norm(m.group(1))
            if not sub:
                routes.add(base)
    okc = 0
    for label, src, expect in _ST_CASES:
        files = [('sentetik.html', src)]
        r1 = rule_R1(files, routes)
        bases = set(re.findall(r'R1 (\S+):', ' '.join(r1)))
        # R3 kapsami: yazilan + GET rotasi olan her kaynak (ihlal olmasa da)
        wbases = {f['base'] for _n, s in files for f in _fetches(s)
                  if f['method'] in ('POST', 'DELETE', 'PUT', 'PATCH')} & routes
        found = set()
        if r1:
            found.add('R1')
        if rule_R2(files):
            found.add('R2')
        if rule_R3(files, routes, wbases):
            found.add('R3')
        exp = {expect} if expect else set()
        good = (found == exp)
        okc += 1 if good else 0
        print('  %s  %s%s' % ('PASS' if good else 'FAIL', label,
                              '' if good else '   -> bulunan: %s, beklenen: %s' % (sorted(found), sorted(exp))))
    print('  %d/%d' % (okc, len(_ST_CASES)))
    return 0 if okc == len(_ST_CASES) else 1


def main():
    if '--self-test' in sys.argv:
        return _self_test()
    ref = None
    if '--ref' in sys.argv:
        ref = sys.argv[sys.argv.index('--ref') + 1]
    files = list(_client_files(ref))
    routes = _get_routes(ref)
    v = []
    r1 = rule_R1(files, routes)
    v += r1
    v += rule_R2(files)
    wbases = {f['base'] for _n, s in files for f in _fetches(s)
              if f['method'] in ('POST', 'DELETE', 'PUT', 'PATCH')} & routes
    v += rule_R3(files, routes, wbases)
    for x in v:
        print('  ✗ ' + x)
    if v:
        print('  %d ihlal' % len(v))
        return 1
    print('  istemci/sunucu durum sahipligi temiz (%d dosya, %d GET rotasi)' % (len(files), len(routes)))
    return 0


if __name__ == '__main__':
    sys.exit(main())
