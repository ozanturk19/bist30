#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
K-DG (22.09.2026) — TURKCE ARAMA KATLAMASI TEK KANONDAN MI GELIYOR?

"Kullanicinin ASCII klavyeyle yazdigi sorgu Turkce harf iceren adla
eslessin" isi uc yil boyunca BES yerde ayri yazildi ve DORDU farkliydi:

    static/bp-search.js   trFold      tam    (I,I -> i; lower; i,s,g,u,o,c)
    templates/tarama.html _trFold     tam    (birebir kopya)
    templates/karsilastir _normalize  `i` (dotless) KATLANMIYOR
    templates/portfolio   _pfFold     s/g/u/o/c KATLANMIYOR
    templates/blog.html   trFold      hicbir diyakritik KATLANMIYOR

CANLI OLCUM 22.09 -- sablonlardan SOKULEN gercek fonksiyon govdeleri
/api/stocks/list'in 216 sirket adi uzerinde calistirildi; kanondan sapan
ad sayisi: karsilastir 49, portfolio 102, blog 124. Sorgu duzeyinde ayni
urun ayni soruya farkli cevap veriyordu:

    "turk hava yollari" -> ust arama 1 sonuc · /karsilastir 0 · /blog 0
    "is bankasi"        -> ust arama 1 sonuc · /karsilastir 0 · /portfolio 0
    "sabanci holding"   -> ust arama 1 sonuc · /karsilastir 0

/blog'da 91 kartin 86'sinin BASLIGINDA ASCII yazilinca bulunamayan en az
bir kelime vardi: "yonetim" 0 sonuc (kanon 10), "guclu" 0 (8), "turkiye"
0 (9), "temettu" 0 (5), "sirket" 0 (7) -- ustelik "Risk Yonetimi" sayfanin
KENDI kategori cipinin adi.

"Ayni is icin iki kanon basli basina bulgudur" merceginin 5. uygulamasi.

OLCUT (taban SIFIR):

  R1  KANON TEK YERDE — `bpTrFold` yalniz static/bp-vocab.js'te TANIMLI
      olmali (tam olarak bir kez).
  R2  KOPYA YOK — baska hicbir sablon/JS Turkce katlama GOVDESI yazmasin.
      Govde tespiti: ayni fonksiyon/ifade icinde kucultme (`toLowerCase`
      veya `toLocaleLowerCase`) + en az IKI Turkce harf katlamasi
      (I/I/i/s/g/u/o/c -> ASCII). Yorumlar SOYULUR (137. ders): yorumda
      "i -> i" yazmak ihlal degildir, kodda yazmak ihlaldir.
  R3  DELEGE SAFI — yerel sarmalayici (trFold/_trFold/_pfFold/_normalize)
      birakildiysa govdesi TEK satir `return bpTrFold(...)` olmali;
      icinde ek replace/lower varsa ikinci kanon dogmus demektir.
  R4  BAGIMLILIK BILDIRILMIS — `bpTrFold` cagiran her sablon
      bp-vocab.js'i YUKLEMELI.
  R5  YUKLEME SIRASI — bp-search.js artik bpTrFold'a bagimli; onu yukleyen
      her sablon bp-vocab.js'i de yuklemeli ve bp-vocab.js belge sirasinda
      ONCE gelmeli (ikisi de `defer`, sira korunur; K-BE dersi: `defer`
      satir-ici koddan SONRA calisir, o yuzden cagri ani onemli -- arama
      yalniz kullanici yazinca calisir).
  R6  KAPSAM TABANI — en az 4 sarmalayici/cagiri gorulmeli; altina duserse
      dedektor korlesmis demektir (K-AU dersi: sifir tek basina kanit degil).

Kullanim:
  python3 tools/tr-fold-canon-check.py              # calisan agac
  python3 tools/tr-fold-canon-check.py --ref SHA    # o commit'in agaci
  python3 tools/tr-fold-canon-check.py --self-test  # sahte poz/neg
"""
import io
import os
import re
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CANON_FILE = 'static/bp-vocab.js'
CANON_FN = 'bpTrFold'
MIN_WRAPPERS = 4

# Turkce -> ASCII katlama yazimlari (kod icinde)
# buyuk/kucuk her iki yazim da sayilir (karsilastir.html [Ğğ] gibi sinif yazimlari kullaniyordu)
FOLD_CHARS = ['İ', 'ı', 'Ş', 'ş', 'Ğ', 'ğ',
              'Ü', 'ü', 'Ö', 'ö', 'Ç', 'ç']
RE_FOLD_REPL = re.compile(
    r"replace\s*\(\s*/\s*\[?[" + ''.join(FOLD_CHARS) + r"I]" )
RE_LOWER = re.compile(r"\.to(?:Locale)?LowerCase\s*\(")
WRAPPER_NAMES = ('trFold', '_trFold', '_pfFold', '_normalize', 'bpTrFold')
# saf delege: `return bpTrFold(<dengeli>)` ve BASKA HICBIR SEY (zincirlenmis
# .replace(...) ikinci kanonun tohumudur -- R3 onu yakalar)
RE_PURE_DELEGATE = re.compile(
    r"return\s+" + CANON_FN + r"\s*\((?:[^()]|\([^()]*\))*\)\s*;?")


def strip_comments(src):
    """Yorum ve Jinja yorumlarini bosluga cevir (137. ders: yorum kapi degil,
    yorum ihlal de degil). Satir sayisi korunur."""
    out = []
    i, n = 0, len(src)
    state = None  # 'line','block','jinja','sq','dq','tpl'
    while i < n:
        c = src[i]
        nxt = src[i + 1] if i + 1 < n else ''
        if state is None:
            if c == '/' and nxt == '/':
                state = 'line'; out.append('  '); i += 2; continue
            if c == '/' and nxt == '*':
                state = 'block'; out.append('  '); i += 2; continue
            if c == '{' and nxt == '#':
                state = 'jinja'; out.append('  '); i += 2; continue
            if c in '"\'`':
                state = {'"': 'dq', "'": 'sq', '`': 'tpl'}[c]; out.append(c); i += 1; continue
            out.append(c); i += 1; continue
        if state == 'line':
            if c == '\n': state = None; out.append('\n')
            else: out.append(' ')
            i += 1; continue
        if state == 'block':
            if c == '*' and nxt == '/': state = None; out.append('  '); i += 2; continue
            out.append('\n' if c == '\n' else ' '); i += 1; continue
        if state == 'jinja':
            if c == '#' and nxt == '}': state = None; out.append('  '); i += 2; continue
            out.append('\n' if c == '\n' else ' '); i += 1; continue
        # dize icindeyiz
        if c == '\\':
            out.append(c); out.append(nxt); i += 2; continue
        if (state == 'dq' and c == '"') or (state == 'sq' and c == "'") or (state == 'tpl' and c == '`'):
            state = None
        out.append(c); i += 1; continue
    return ''.join(out)


def function_bodies(src):
    """(ad, govde, satir) — `function AD(...) { ... }` bloklarini suslu
    parantez DENGESIYLE okur (komsuluk penceresi DEGIL, K-DE dersi)."""
    for m in re.finditer(r"function\s+([A-Za-z_$][\w$]*)\s*\(", src):
        name = m.group(1)
        i = src.find('{', m.end())
        if i < 0:
            continue
        d, j = 0, i
        while j < len(src):
            if src[j] == '{': d += 1
            elif src[j] == '}':
                d -= 1
                if d == 0:
                    j += 1
                    break
            j += 1
        yield name, src[i:j], src[:m.start()].count('\n') + 1


def is_fold_body(body):
    return bool(RE_LOWER.search(body)) and len(RE_FOLD_REPL.findall(body)) >= 2


def scan_tree(read, listdir):
    """read(relpath)->str|None, listdir(reldir)->[names]"""
    viol, wrappers = [], []

    canon_src = read(CANON_FILE)
    if canon_src is None:
        viol.append((CANON_FILE, 0, 'R1', 'kanon dosyasi yok'))
        canon_src = ''
    canon_clean = strip_comments(canon_src)
    n_canon = len(re.findall(r"function\s+" + CANON_FN + r"\s*\(", canon_clean))
    if n_canon != 1:
        viol.append((CANON_FILE, 0, 'R1',
                     '%s tanimi %d kez (tam 1 olmali)' % (CANON_FN, n_canon)))

    files = [CANON_FILE]
    files += ['static/' + f for f in sorted(listdir('static')) if f.endswith('.js') and f != 'bp-vocab.js']
    files += ['templates/' + f for f in sorted(listdir('templates')) if f.endswith('.html')]

    for rel in files:
        src = read(rel)
        if src is None:
            continue
        clean = strip_comments(src)
        for name, body, line in function_bodies(clean):
            if rel != CANON_FILE and is_fold_body(body):
                viol.append((rel, line, 'R2',
                             '%s() kendi Turkce katlama govdesini yaziyor — kanon %s()' % (name, CANON_FN)))
            if name in WRAPPER_NAMES and name != CANON_FN and rel != CANON_FILE:
                wrappers.append((rel, name))
                inner = body.strip()[1:-1].strip()
                if CANON_FN in inner:
                    if not RE_PURE_DELEGATE.fullmatch(inner):
                        viol.append((rel, line, 'R3',
                                     '%s() bpTrFold cagiriyor ama govdesi saf delege degil' % name))
        # R4 / R5
        if rel.startswith('templates/'):
            has_vocab = 'bp-vocab.js' in src
            calls_canon = CANON_FN in clean
            if calls_canon and not has_vocab:
                viol.append((rel, 0, 'R4', 'bpTrFold cagiriyor ama bp-vocab.js yuklenmiyor'))
            if 'src="/static/bp-search.js' in src:   # YORUMDA ANMAK YUKLEMEK DEGILDIR (137. ders)
                if not has_vocab:
                    viol.append((rel, 0, 'R5', 'bp-search.js yukluyor ama bp-vocab.js yok (bpTrFold tanimsiz kalir)'))
                else:
                    iv, isr = src.find('src="/static/bp-vocab.js'), src.find('src="/static/bp-search.js')
                    if iv >= 0 and isr >= 0 and iv > isr:
                        viol.append((rel, 0, 'R5', 'bp-vocab.js belge sirasinda bp-search.js SONRASINDA'))
    return viol, wrappers


def fs_reader(base):
    def read(rel):
        p = os.path.join(base, rel)
        if not os.path.exists(p):
            return None
        return io.open(p, encoding='utf-8').read()

    def listdir(rel):
        p = os.path.join(base, rel)
        return os.listdir(p) if os.path.isdir(p) else []
    return read, listdir


def git_reader(ref):
    def read(rel):
        try:
            return subprocess.check_output(['git', 'show', '%s:%s' % (ref, rel)],
                                           cwd=ROOT, stderr=subprocess.DEVNULL).decode('utf-8')
        except subprocess.CalledProcessError:
            return None

    def listdir(rel):
        try:
            out = subprocess.check_output(['git', 'ls-tree', '--name-only', '%s:%s' % (ref, rel)],
                                          cwd=ROOT, stderr=subprocess.DEVNULL).decode('utf-8')
            return out.split()
        except subprocess.CalledProcessError:
            return []
    return read, listdir


SELF_TESTS = [
    # (aciklama, kaynak, fold govdesi mi)
    ("tam kanon govdesi",
     "function f(s){return String(s).replace(/İ/g,'i').replace(/I/g,'i').toLowerCase()"
     ".replace(/ı/g,'i').replace(/ş/g,'s');}", True),
    ("locale'li varyant (karsilastir yazimi)",
     "function f(s){return (s||'').replace(/İ/g,'i').toLocaleLowerCase('tr-TR')"
     ".replace(/[Ğğ]/g,'g').replace(/[Üü]/g,'u');}", True),
    ("saf delege — ihlal DEGIL",
     "function f(s){return bpTrFold(s);}", False),
    ("yorumda katlama anlatimi — ihlal DEGIL (137. ders)",
     "function f(s){/* İ -> i, ş -> s, toLowerCase */ return bpTrFold(s);}", False),
    ("tek replace + lower — katlama sayilmaz (sahte pozitif kalkani)",
     "function f(s){return String(s).replace(/İ/g,'i').toLowerCase();}", False),
    ("dize icindeki katlama metni — ihlal DEGIL",
     "function f(s){return t(\"replace(/İ/g,'i') toLowerCase\");}", False),
    ("iki katlama ama lower YOK — katlama sayilmaz",
     "function f(s){return s.replace(/ş/g,'s').replace(/ğ/g,'g');}", False),
]


def self_test():
    hit = 0
    for desc, src, expect in SELF_TESTS:
        clean = strip_comments(src)
        got = any(is_fold_body(b) for _, b, _ in function_bodies(clean))
        ok = (got == expect)
        hit += ok
        print("   %s %s" % ('✓' if ok else '✗', desc))
    # R3: kirli delege yakalanmali
    dirty = "function _pfFold(s){return bpTrFold(s).replace(/x/g,'y');}"
    clean = strip_comments(dirty)
    inner = list(function_bodies(clean))[0][1].strip()[1:-1].strip()
    ok = not RE_PURE_DELEGATE.fullmatch(inner)
    hit += ok
    print("   %s kirli delege (R3) yakalandi" % ('✓' if ok else '✗'))
    return hit, len(SELF_TESTS) + 1


def main():
    if '--self-test' in sys.argv:
        hit, tot = self_test()
        print("tr-fold-canon-check --self-test: %d/%d" % (hit, tot))
        return 0 if hit == tot else 2

    if '--ref' in sys.argv:
        ref = sys.argv[sys.argv.index('--ref') + 1]
        read, listdir = git_reader(ref)
        label = 'ref %s' % ref
    else:
        read, listdir = fs_reader(ROOT)
        label = 'calisan agac'

    viol, wrappers = scan_tree(read, listdir)
    print("tr-fold-canon-check (K-DG Turkce arama katlamasi tek kanon) — %s" % label)
    print("  sarmalayici/cagiri: %d" % len(wrappers))

    if '--ref' not in sys.argv and len(wrappers) < MIN_WRAPPERS:
        print("  ✗ kapsam tabani altinda (%d/%d) — dedektor korlesmis" % (len(wrappers), MIN_WRAPPERS))
        return 2
    if viol:
        print("  ✗ %d ihlal:" % len(viol))
        for f, l, rule, why in viol:
            print("      · %-28s %s  %-4s %s" % (f, ('%4d' % l) if l else '   -', rule, why))
        return 1
    print("  ✓ katlama tek kanondan (%s / %s), her cagiran bagimliligi bildiriyor" % (CANON_FILE, CANON_FN))
    return 0


if __name__ == '__main__':
    sys.exit(main())
