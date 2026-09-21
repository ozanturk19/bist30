#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
K-BO (21.09.2026) — HACIM EKSENI YON RENGIYLE BOYANAMAZ.

Hacim (RVOL = 5g/20g, Gunluk Hacim Orani = bugun/20g) YON-BAGIMSIZ bir
buyukluk olcusudur: cokuste de yuksek cikar. Yon rengiyle (--bp-al yesili /
--bp-sat kirmizisi) boyandiginda, ayni satirda "Sinyal" sutunu ve ayni kartta
`seg-al` cubugu zaten o yesili YON anlaminda kullandigi icin kullanici onu
"olumlu" okur. Emsal ayni depoda yaziliydi: tarama.css `.trend-label` notu
(ADX, 10.09 BTCIM) — ama duzeltme kardes RVOL hucresine uygulanmamisti.

Ikinci sinif: hacim ekseninin kanonik rengi --bp-volume (tokens.css
CPO-1149/1150). Baska bir sarinin (--bp-gold premium/altin, --bp-accent-yellow
sari aksan/EMA99, --bp-warn degerlendirme, --bp-stale veri durumu) odunc
alinmasi ayni kavrami iki-uc renge bolen "iki kanon" ihlalidir.

Kapsam: templates/**.html, static/css/**.css, static/js/**.js.
Uc desen:
  A) CSS  — SECICISI hacim eksenini adlandiran bir kuralin govdesinde yasakli renk
  B) JS   — icinde hacim tanimlayicisi (rvol/avgRvol/vol_ratio) GECEN bir deyimde
            yasakli renk
  C) Jinja— icinde hacim tanimlayicisi gecen bir {{ ... }} ifadesinde yasakli renk

YORUMLAR SOYULUR (K-BN dersi: kendi belgelendirmen de kapiyi korlestirir) —
ama soyucu `<script>` govdesine JS yorumu disinda dokunmaz.

Kullanim:
  python3 tools/volume-axis-color-check.py            # calisan agac
  python3 tools/volume-axis-color-check.py --ref SHA  # o commit'in agaci (pozitif kontrol)
"""
import os, re, sys, subprocess, tempfile, tarfile, io

FORBIDDEN = {
    '--bp-al': 'YON rengi (yukselis yesili)',
    '--bp-sat': 'YON rengi (dusus kirmizisi)',
    '--bp-gold': 'PREMIUM/altin ekseni',
    '--bp-accent-yellow': 'sari aksan / EMA99 ekseni',
    '--bp-warn': 'DEGERLENDIRME (dikkat/orta-risk) ekseni',
    '--bp-stale': 'VERI DURUMU (tazelik) ekseni',
}
# Token'i atlayip ham hex yazmak kapiyi asmasin.
FORBIDDEN_HEX = {
    '#00e290': '--bp-al', '#f85149': '--bp-sat', '#f59e0b': '--bp-gold',
    '#e3b341': '--bp-accent-yellow', '#d29922': '--bp-warn', '#f5c949': '--bp-stale',
}
# Hacim eksenini ADLANDIRAN tanimlayicilar. DIKKAT: ciplak "volume" YOK —
# `--bp-volume` token adinin kendisi her eslesmede yanlis pozitif uretirdi.
VOL_ID = re.compile(r'(?<![a-z])(r_?vol|avg_?rvol|vol_ratio|volratio|hacim)(?![a-z])', re.I)

SKIP_FILES = {'static/css/tokens.css'}   # token TANIMI; renkleri burada yan yana durur


def _blank(t):
    """Ayni uzunlukta bosluk, ama SATIR SONLARI korunur — yoksa satir no kayar."""
    return ''.join('\n' if ch == '\n' else ' ' for ch in t)


def strip_css_comments(s):
    return re.sub(r'/\*.*?\*/', lambda m: _blank(m.group(0)), s, flags=re.S)


def strip_js_comments(s):
    """Blok + satir yorumlarini soy. String literalleri ve `https://` korunur."""
    out, i, n = [], 0, len(s)
    while i < n:
        c = s[i]
        if c in '"\'`':
            q = c; out.append(c); i += 1
            while i < n:
                if s[i] == '\\': out.append(_blank(s[i:i+2])); i += 2; continue
                out.append(s[i])
                if s[i] == q: i += 1; break
                i += 1
            continue
        if c == '/' and i + 1 < n:
            if s[i+1] == '*':
                j = s.find('*/', i + 2); j = n if j < 0 else j + 2
                out.append(_blank(s[i:j])); i = j; continue
            if s[i+1] == '/' and (i == 0 or s[i-1] != ':'):
                j = s.find('\n', i); j = n if j < 0 else j
                out.append(_blank(s[i:j])); i = j; continue
        out.append(c); i += 1
    return ''.join(out)


def strip_html_comments(s):
    s = re.sub(r'<!--.*?-->', lambda m: _blank(m.group(0)), s, flags=re.S)
    return re.sub(r'\{#.*?#\}', lambda m: _blank(m.group(0)), s, flags=re.S)


def strip_in_scripts(s):
    """<script>...</script> govdelerinde JS yorumlarini soy, disina dokunma."""
    def repl(m):
        body = strip_js_comments(m.group(2))
        return m.group(1) + body + m.group(3)
    return re.sub(r'(<script\b[^>]*>)(.*?)(</script>)', repl, s, flags=re.S | re.I)


# JS/Jinja tarafinda "deyim" penceresi dev `innerHTML` birlestirmelerinde
# yuzlerce satir olabiliyor: ayni deyimde hem bir RVOL satiri hem de ALAKASIZ
# bir degisim-yuzdesi renklendirmesi bulunuyor (index.html daSpotlight,
# sektor_harita col.innerHTML — ikisi de ELLE dogrulandi, SAHTE POZITIFTI).
# Bu yuzden B/C desenlerinde renk, bir hacim tanimlayicisina bu mesafeden
# YAKIN olmali. A/CSS'te kisit yok: orada birim zaten tek kuraldir.
PROXIMITY = 140


def bad_colors(chunk, proximity=None):
    """Yasakli renk gecislerini dondur. `proximity` verilirse, renk bir hacim
    tanimlayicisina en fazla o kadar karakter uzakta olmali."""
    vol_spans = [m.span() for m in VOL_ID.finditer(chunk)] if proximity else None

    def near(a, b):
        if vol_spans is None:
            return True
        return any(max(0, max(a, x) - min(b, y)) <= proximity for x, y in vol_spans)

    hits, seen = [], set()
    for tok, why in FORBIDDEN.items():
        for m in re.finditer(re.escape(tok) + r'(?![a-z-])', chunk):
            if near(*m.span()) and tok not in seen:
                seen.add(tok); hits.append((tok, why)); break
    low = chunk.lower()
    for hx, tok in FORBIDDEN_HEX.items():
        for m in re.finditer(re.escape(hx), low):
            if near(*m.span()) and hx not in seen:
                seen.add(hx); hits.append((hx + ' (= ' + tok + ')', FORBIDDEN[tok])); break
    return hits


def lineno(s, pos):
    return s.count('\n', 0, pos) + 1


def scan_css(path, raw):
    v = []
    s = strip_css_comments(raw)
    for m in re.finditer(r'([^{}@;]+)\{([^{}]*)\}', s):
        sel, body = m.group(1), m.group(2)
        if not VOL_ID.search(sel):
            continue
        for tok, why in bad_colors(body):
            v.append((path, lineno(s, m.start(2)), 'A/CSS',
                      sel.strip().splitlines()[-1].strip()[:60], tok, why))
    return v


def scan_js_stmts(path, s, tag):
    v = []
    for stmt in re.finditer(r'[^;{}]+', s):
        chunk = stmt.group(0)
        if not VOL_ID.search(chunk):
            continue
        for tok, why in bad_colors(chunk, PROXIMITY):
            v.append((path, lineno(s, stmt.start()), tag,
                      ' '.join(chunk.split())[:70], tok, why))
    return v


def scan_html(path, raw):
    v = []
    s = strip_in_scripts(strip_html_comments(raw))
    # C) Jinja ifadeleri
    for m in re.finditer(r'\{\{.*?\}\}', s, flags=re.S):
        chunk = m.group(0)
        if not VOL_ID.search(chunk):
            continue
        for tok, why in bad_colors(chunk, PROXIMITY):
            v.append((path, lineno(s, m.start()), 'C/Jinja',
                      ' '.join(chunk.split())[:70], tok, why))
    # B) <script> govdeleri (deyim bazli)
    for sm in re.finditer(r'<script\b[^>]*>(.*?)</script>', s, flags=re.S | re.I):
        base = sm.start(1)
        body = sm.group(1)
        for hit in scan_js_stmts(path, body, 'B/JS'):
            v.append((path, lineno(s, base) + hit[1] - 1, 'B/JS', hit[3], hit[4], hit[5]))
    return v


def collect(root):
    files = []
    for sub, exts in (('templates', ('.html',)), ('static/css', ('.css',)), ('static/js', ('.js',))):
        d = os.path.join(root, sub)
        for dp, _, fns in os.walk(d):
            for fn in sorted(fns):
                if fn.endswith(exts):
                    p = os.path.relpath(os.path.join(dp, fn), root)
                    if p.replace(os.sep, '/') not in SKIP_FILES:
                        files.append(p)
    return sorted(files)


def run(root):
    viol, n = [], 0
    for rel in collect(root):
        try:
            raw = io.open(os.path.join(root, rel), encoding='utf-8').read()
        except Exception:
            continue
        n += 1
        if rel.endswith('.css'):
            viol += scan_css(rel, raw)
        elif rel.endswith('.js'):
            viol += scan_js_stmts(rel, strip_js_comments(raw), 'B/JS')
        else:
            viol += scan_html(rel, raw)
    return n, viol


def selftest():
    """Sentetik pozitif/negatif — kapi gercekten ayirt ediyor mu."""
    pos = [
        ('.rvol-cell.high { color:var(--bp-al); }', scan_css, 1),
        ('.cmp-rvol-high { color:var(--bp-gold); }', scan_css, 1),
        ('.rvol-dot.high { background:#00e290; }', scan_css, 1),
    ]
    # B/C: yakinlik kisiti gercekten ayirt ediyor mu?
    pos += [
        ("<script>const rc = avgRvol >= 2.0 ? 'var(--bp-al)' : 'x';</script>", scan_html, 1),
        ("{{ 'var(--bp-al)' if sec.avg_rvol >= 2.0 else 'y' }}", scan_html, 1),
    ]
    neg = [
        # UZAK renk: ayni dev deyimde ama hacimle ilgisiz (gercek sahte-pozitif vakasi)
        ("<script>h = rvolPct + '" + ('z' * 400) + "' + 'var(--bp-al)';</script>", scan_html, 0),
        ('.rvol-cell.high { color:var(--bp-volume); }', scan_css, 0),
        ('.trend-label.strong { color:var(--bp-al); }', scan_css, 0),   # ADX, hacim degil
        ('/* rvol --bp-al olmamali */ .x{color:var(--bp-volume)}', scan_css, 0),  # yorum soyulur
        ('.cmp-stock-rvol { color:var(--bp-text3); }', scan_css, 0),
    ]
    okp = sum(1 for src, fn, exp in pos if len(fn('t', src)) == exp)
    okn = sum(1 for src, fn, exp in neg if len(fn('t', src)) == exp)
    return okp, len(pos), okn, len(neg)


def main():
    ref = None
    if '--ref' in sys.argv:
        ref = sys.argv[sys.argv.index('--ref') + 1]
    print("volume-axis-color-check (K-BO: hacim ekseni yon rengiyle boyanamaz)")
    okp, tp, okn, tn = selftest()
    print("  sentetik pozitif: %d/%d · sentetik negatif: %d/%d" % (okp, tp, okn, tn))
    if okp != tp or okn != tn:
        print("  ✗ KAPI KENDI TESTINI GECEMEDI — olcum guvenilir degil.")
        return 2

    root = os.getcwd()
    tmp = None
    if ref:
        tmp = tempfile.mkdtemp(prefix='kbo-')
        tar = subprocess.check_output(['git', 'archive', ref])
        tarfile.open(fileobj=io.BytesIO(tar)).extractall(tmp)
        root = tmp

    n, viol = run(root)
    print("  taranan dosya: %d%s" % (n, (" (ref %s)" % ref) if ref else ""))
    for p, ln, kind, ctx, tok, why in viol:
        print("   . %s:%d [%s] %s  ->  %s : %s" % (p, ln, kind, ctx, tok, why))
    if viol:
        print("  ✗ %d ihlal: hacim ekseni yabanci bir eksenin rengiyle boyaniyor." % len(viol))
        print("    Kanon: --bp-volume (tokens.css CPO-1149/1150). Esik kanonu: RVOL >= 1,20.")
        return 1
    print("  ✓ hacim ekseninin her yuzeyi --bp-volume kanonunda")
    return 0


if __name__ == '__main__':
    sys.exit(main())
