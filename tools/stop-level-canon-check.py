#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
K-BQ (21.09.2026) — "STOP" BIR YON IDDIASIDIR; SUPERTREND SEVIYESI DEGILDIR.

`sl_level` Supertrend bandinin GUNCEL degeridir ve sinyal yonunden bagimsiz
HER hissede hesaplanir. Long-only bir urunde bu sayiya "Stop" demek yalnizca
band fiyatin ALTINDAYKEN (yukselis sinyali surerken) anlamlidir.

CANLI OLCUM (21.09, /api/data, 217 hisse):
  * `sl_level > price` olan hisse: **197** — 72/72 SAT + 125/138 BEKLE.
  * AL 7/7'de band fiyatin ALTINDA (orada "stop" dogru).
  * MARTI: fiyat 2,01 ₺, "Hap Bilgi" -> "Stop Seviyesi 2,74 ₺" (%36 YUKARIDA).
    Ayni sayfa iki satir yukarida "Net sinyal olmadigi icin tanimli bir giris
    bolgesi yok" diyordu. Ayni alan /karsilastir'da zaten dogru adlandirilmisti
    ("Supertrend Seviyesi" + "acik bir pozisyonun stopu anlamina gelmez") —
    /hisse o emsali miras almamisti. Klasik "ayni is icin iki kanon".
  * Alt-etiket band fiyatin USTUNDEYKEN de "ST destegi" diyordu: fiyatin
    ustundeki seviye destek degil DIRENCTIR.

OLCUT (taban SIFIR), iki desen:
  A) `sl_level`e YAKIN (<=220 ch) gorunur "Stop" etiketi varken ayni pencerede
     yon kosulu (signal == 'AL' / _sig == 'AL') veya tek kanon `bpStLevelRole`
     YOKSA -> ihlal. ("Stop" kosulsuz bir yon iddiasidir.)
  B) 'ST destegi' / 'ST direnci' / 'destek' / 'direnc' rol metni DUZ STRING
     olarak yaziliysa ve ayni pencerede fiyat karsilastirmasi ya da
     `bpStLevelRole` yoksa -> ihlal. (Rol FIYATTAN turer, sinyalden degil.)

Tek kanon: static/bp-format.js `bpStLevelRole(sl, price, signal)`.

⛔ SOYUCU NOTU (K-BD dersi 39): bu kapinin JS yorum soyucusu REGEX
LITERALINI tanir. `.replace(/[&<>"']/g, ...)` icindeki tirnak aksi halde
string acar ve dosyanin geri kalaninda kod/yorum ayrimi bozulur.

Kullanim:
  python3 tools/stop-level-canon-check.py            # calisan agac
  python3 tools/stop-level-canon-check.py --ref SHA  # pozitif kontrol
"""
import os, re, sys, subprocess, tempfile, tarfile, io

WINDOW = 220          # "yakinlik" penceresi (K-BO dersi 34: dev innerHTML deyimleri)
SL_ID = re.compile(r'(?<![A-Za-z_])sl_level(?![A-Za-z_])')

# Gorunur "Stop" ETIKETI. Kucuk harf `stop` KASITLI DISARIDA:
# SVG gradyan (`stop-color`, `grad.addColorStop`), `stopPropagation`,
# `clearTimeout`/`stop()` gibi kod tokenlari ayni dosyalarda bolca geciyor.
STOP_LABEL = re.compile(r'Stop(?![A-Za-z(])')

# Yon kosulu / tek kanon — bunlardan biri pencerede varsa "Stop" gerekcelidir.
GUARD = re.compile(
    r"bpStLevelRole"
    r"|signal\s*(?:===?|==)\s*['\"]AL['\"]"
    r"|_sig\s*==\s*['\"]AL['\"]"
    r"|signal\s*==\s*['\"]AL['\"]"
)

# B) Rol metinleri (gorunur Turkce). Bunlar duz string yazildiginda yon iddiasidir.
ROLE_TXT = re.compile(r'(ST deste[gğ]i|ST diren[cç]i|deste[gk]\b|diren[cç]\b)', re.I)
# Fiyat karsilastirmasi (yonu FIYATTAN turetme kaniti).
PRICE_CMP = re.compile(
    r"bpStLevelRole"
    r"|sl_level\s*[<>]\s*(?:ssr_signal\.)?price"
    r"|(?:ssr_signal\.)?price\s*[<>]\s*(?:ssr_signal\.)?sl_level"
    r"|_slAbove|\.above\b"
)

SCAN_DIRS = (('templates', ('.html',)), ('static', ('.js',)), ('static/css', ('.css',)))
# bp-format.js KANONUN KENDISI: rol metinleri orada tanimlanir.
SKIP_FILES = {'static/bp-format.js'}


def _blank(t):
    """Ayni uzunlukta bosluk, SATIR SONLARI korunur (K-BO dersi 35)."""
    return ''.join('\n' if ch == '\n' else ' ' for ch in t)


def strip_js_comments(s):
    """Blok + satir yorumlarini soy. String, sablon ve REGEX literali korunur."""
    out, i, n = [], 0, len(s)
    prev = ''                      # son anlamli (bosluk disi) karakter
    while i < n:
        c = s[i]
        if c in '"\'`':
            q = c; out.append(c); i += 1
            while i < n:
                if s[i] == '\\': out.append(_blank(s[i:i+2])); i += 2; continue
                out.append(s[i])
                if s[i] == q: i += 1; break
                i += 1
            prev = q
            continue
        if c == '/' and i + 1 < n:
            if s[i+1] == '*':
                j = s.find('*/', i + 2); j = n if j < 0 else j + 2
                out.append(_blank(s[i:j])); i = j; continue
            if s[i+1] == '/' and prev != ':':
                j = s.find('\n', i); j = n if j < 0 else j
                out.append(_blank(s[i:j])); i = j; continue
            # ⛔ REGEX LITERALI: bir operatorun/acilisinin ARDINDAN gelen `/`
            if prev in '' or prev in '(,=:[!&|?{};+-*%~^<>' or prev == '':
                j = i + 1; ok = False
                while j < n and s[j] != '\n':
                    if s[j] == '\\': j += 2; continue
                    if s[j] == '[':
                        while j < n and s[j] != ']' and s[j] != '\n':
                            j += 2 if s[j] == '\\' else 1
                    elif s[j] == '/':
                        ok = True; break
                    j += 1
                if ok:
                    while j < n and s[j+1:j+2].isalpha(): j += 1   # bayraklar
                    out.append(s[i:j+1]); prev = '/'; i = j + 1; continue
        out.append(c)
        if not c.isspace(): prev = c
        i += 1
    return ''.join(out)


def strip_html_comments(s):
    s = re.sub(r'<!--.*?-->', lambda m: _blank(m.group(0)), s, flags=re.S)
    return re.sub(r'\{#.*?#\}', lambda m: _blank(m.group(0)), s, flags=re.S)


def strip_in_scripts(s):
    def repl(m):
        return m.group(1) + strip_js_comments(m.group(2)) + m.group(3)
    return re.sub(r'(<script\b[^>]*>)(.*?)(</script>)', repl, s, flags=re.S | re.I)


def strip_css_comments(s):
    return re.sub(r'/\*.*?\*/', lambda m: _blank(m.group(0)), s, flags=re.S)


def lineno(s, pos):
    return s.count('\n', 0, pos) + 1


def _span(s, start, end):
    """WINDOW'u BOSLUK OLMAYAN karakter cinsinden ac.

    ⛔ Soyulan yorumlar esit uzunlukta BOSLUGA cevrilir (satir no korunsun diye).
    Ham karakterle olculen bir pencere, araya giren uzun bir yorum yuzunden
    gercek yon kosulunu disarida birakir — kapi kendi belgelendirmesini ihlal
    sanir. Bu yuzden pencere 'anlamli karakter' sayar."""
    lo = start; cnt = 0
    while lo > 0 and cnt < WINDOW:
        lo -= 1
        if not s[lo].isspace(): cnt += 1
    hi = end; cnt = 0
    n = len(s)
    while hi < n and cnt < WINDOW:
        if not s[hi].isspace(): cnt += 1
        hi += 1
    return lo, hi


JINJA_IF = re.compile(r'\{%-?\s*(if|elif|else|endif)\b(.*?)-?%\}', re.S)


def _open_conditions(s, pos):
    """`pos`u SARAN acik {% if %} kosullarinin metni.

    ⛔ Ders: bir korumanin YAKINLIGI ile KAPSAMI ayri seylerdir. Hero blogunda
    `{% if _sig == 'AL' %}` kosulu `sl_level`den 253 anlamli karakter uzaktaydi
    (araya iki kardes satir girmisti) — pencere onu goremiyordu ama koruma
    GERCEKTEN oradaydi. Pencereyi buyutmek sahte-negatif uretir; dogru olcum
    blok YAPISINI okumaktir."""
    stack = []
    for m in JINJA_IF.finditer(s):
        if m.end() > pos:
            break
        kind, expr = m.group(1), m.group(2)
        if kind == 'if':
            stack.append(expr)
        elif kind == 'elif':
            if stack: stack[-1] = expr
        elif kind == 'else':
            if stack: stack[-1] = ''
        elif kind == 'endif':
            if stack: stack.pop()
    return ' '.join(stack)


def scan(path, s):
    """A + B desenleri, `sl_level` cevresindeki WINDOW penceresinde."""
    v = []
    for m in SL_ID.finditer(s):
        lo, hi = _span(s, m.start(), m.end())
        win = s[lo:hi] + ' ' + _open_conditions(s, m.start())
        if GUARD.search(win):
            continue
        sm = STOP_LABEL.search(win)
        if sm:
            v.append((path, lineno(s, m.start()), 'A/Stop-kosulsuz',
                      ' '.join(win[max(0, sm.start() - 40):sm.start() + 60].split())[:80]))
            continue
        rm = ROLE_TXT.search(win)
        if rm and not PRICE_CMP.search(win):
            v.append((path, lineno(s, m.start()), 'B/rol-sabit',
                      ' '.join(win[max(0, rm.start() - 40):rm.start() + 60].split())[:80]))
    return v


def prep(path, raw):
    if path.endswith('.css'):
        return strip_css_comments(raw)
    if path.endswith('.js'):
        return strip_js_comments(raw)
    return strip_in_scripts(strip_html_comments(raw))


def collect(root):
    files, seen = [], set()
    for sub, exts in SCAN_DIRS:
        d = os.path.join(root, sub)
        for dp, _, fns in os.walk(d):
            for fn in sorted(fns):
                if fn.endswith(exts):
                    p = os.path.relpath(os.path.join(dp, fn), root).replace(os.sep, '/')
                    if p not in SKIP_FILES and p not in seen:
                        seen.add(p); files.append(p)
    return sorted(files)


def run(root):
    viol, n = [], 0
    for rel in collect(root):
        try:
            raw = io.open(os.path.join(root, rel), encoding='utf-8').read()
        except Exception:
            continue
        if 'sl_level' not in raw:
            n += 1; continue
        n += 1
        viol += scan(rel, prep(rel, raw))
    return n, viol


def selftest():
    pos = [
        # A) "Stop" etiketi, yon kosulu YOK
        ('<dt>Stop Seviyesi</dt><dd>{{ ssr_signal.sl_level }}</dd>', 1),
        # saran blok KAPANDIKTAN sonra koruma yok
        ("{% if _sig == 'AL' %}<i>x</i>{% endif %}" + ("<span>y</span>" * 30) +
         "<strong>Stop:</strong>{{ ssr_signal.sl_level }}", 1),
        ("<script>x = s.sl_level; lbl.textContent = 'Stop: ' + v;</script>", 1),
        # B) rol metni sabit, fiyat karsilastirmasi YOK
        ("<script>if (s.sl_level) p.textContent = 'ST desteği: ' + pct;</script>", 1),
    ]
    neg = [
        # A-muaf: yon kosulu ayni pencerede
        ("{% if _sig == 'AL' %}<span>Stop: {{ ssr_signal.sl_level }}</span>{% endif %}", 0),
        # B-muaf: tek kanon
        ("<script>const r = bpStLevelRole(s.sl_level, p, s.signal); e.textContent = r.label;</script>", 0),
        # ⛔ SARAN {% if %} BLOGU: kosul pencerenin DISINDA kalsa bile gecerli
        ("{% if _sig == 'AL' %}<div>" + ("<span>x</span>" * 30) +
         "<strong>Stop:</strong>{{ ssr_signal.sl_level }}</div>{% endif %}", 0),
        # ⛔ ...ama {% endif %}'ten SONRASI korunmaz
        # ⛔ UZUN YORUM ARAYA GIRSE BILE yon kosulu pencerede sayilmali
        ("{% if _sig == 'AL' %}" + ("{# " + "a" * 400 + " #}") +
         "<span>Stop: {{ ssr_signal.sl_level }}</span>{% endif %}", 0),
        # yorum soyulur (kendi belgelendirmen kapiyi korlestirmesin)
        ("<script>/* sl_level icin 'Stop' demeyin */ var a = 1;</script>", 0),
        ("{# sl_level yaninda Stop yazilmaz #}<span>x</span>", 0),
        # SVG gradyani / kod tokeni "Stop" sayilmaz
        ("<script>g.addColorStop(0, c); var z = s.sl_level;</script>", 0),
        # ⛔ REGEX LITERALI soyucuyu bozmamali: asagidaki ihlal HALA gorulmeli
        ("<script>var e = t.replace(/[&<>\"']/g, '');\nvar q = s.sl_level;\nl.textContent = 'Stop: ' + q;</script>", 1),
    ]
    okp = sum(1 for src, exp in pos if len(scan('t', prep('t.html', src))) == exp)
    okn = sum(1 for src, exp in neg if len(scan('t', prep('t.html', src))) == exp)
    return okp, len(pos), okn, len(neg)


def main():
    ref = None
    if '--ref' in sys.argv:
        ref = sys.argv[sys.argv.index('--ref') + 1]
    print("stop-level-canon-check (K-BQ: 'Stop' yon iddiasidir, Supertrend seviyesi degil)")
    okp, tp, okn, tn = selftest()
    print("  sentetik pozitif: %d/%d · sentetik negatif: %d/%d" % (okp, tp, okn, tn))
    if okp != tp or okn != tn:
        print("  ✗ KAPI KENDI TESTINI GECEMEDI — olcum guvenilir degil.")
        return 2

    root = os.getcwd(); tmp = None
    if ref:
        tmp = tempfile.mkdtemp(prefix='kbq-')
        tar = subprocess.check_output(['git', 'archive', ref])
        tarfile.open(fileobj=io.BytesIO(tar)).extractall(tmp)
        root = tmp

    n, viol = run(root)
    print("  taranan dosya: %d%s" % (n, (" (ref %s)" % ref) if ref else ""))
    for p, ln, kind, ctx in viol:
        print("   . %s:%d [%s] %s" % (p, ln, kind, ctx))
    if viol:
        print("  ✗ %d ihlal: 'stop'/'destek'/'direnc' yonu kosulsuz iddia ediliyor." % len(viol))
        return 1
    print("  ✓ temiz — sl_level yuzeylerinde yon iddiasi kosula/kanona bagli.")
    return 0


if __name__ == '__main__':
    sys.exit(main())
