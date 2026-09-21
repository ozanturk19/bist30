#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
K-BU (22.09.2026) — GOSTERILEN SAYI, INSAN-OKUR ETIKETTEN GERI AYRISTIRILMAZ.

Backend bir gostergeyi IKI bicimde birden servis eder:
  * `adx: 25.9`            -> makine icin, TAM hassasiyet
  * `indicators.adx.label` -> "ADX 26", INSAN icin, YUVARLANMIS

/gundem'in kart render'i ikincisini aliyor, icinden sayiyi PARSE EDIYOR ve
`.toFixed(1)` ile geri basiyordu. Bu islem kaybi KURTARMAZ, yalnizca
yuvarlanmis degere SAHTE bir ondalik ekler: "26,0". AYNI SAYFANIN SSR
makrosu ise ayni hisse icin `'%.1f'|format(s.adx)` ile "25,9" basiyordu ve
grid `innerHTML` ile bastan yazildigi icin CSR, SSR'in DOGRU sayisini
YANLIS olanla EZIYORDU (K-BR dersi: SSR != CSR bicimi = gorunur ziplama).

CANLI OLCUM (22.09 00:5x, /api/gundem): **7/7 kartta** SSR != CSR —
ENERY 43,6→44,0 · AYGAZ 35,1→35,0 · TUPRS 34,7→35,0 · TKFEN 33,4→33,0 ·
AHGAZ 29,6→30,0 · ISDMR 25,9→26,0 · BIMAS 25,1→25,0.
Son ikisi urunun **ADX 25 esigine** cakisiyor: yuvarlama "kil payi gecti"yi
"tam esikte"ye, "tam esikte"yi "rahat gecti"ye cevirebiliyordu.

⛔ K-BR kapisi (37) bu ihlali GORMEDI: o kapi `|int` / `Math.round` /
`.toFixed(0)` YAZIMLARINI arar, buradaki kayip ise BACKEND'de olmus ve
frontend'e hazir yuvarlanmis METIN olarak gelmisti. Ayni aile: K-BO'nun
token kapisi, K-BS'nin SINIF ADI kanalini kaciriyordu — bir kanon kapisi
yalnizca ARADIGI KANALDA korur.

OLCUT (taban SIFIR): `parseFloat(` / `parseInt(` / `Number(` cagrisinin
ARGUMANI, adinda `label`/`lbl` gecen bir alana ya da `textContent` /
`innerText` / `innerHTML` / `.title` gibi SUNUM yuzeyine bakiyorsa ihlal.

MUAF:
  * `.value` — form girdisi. Kullanicinin YAZDIGI metin zaten tek kaynaktir
    (bkz. bpParseTrNumber, TR ondalik girdi kanonu / K-BA).
  * `dataset.*` / `getAttribute('data-...')` — makine-okur tasiyici; sayiyi
    sunumdan AYIRMAK icin zaten dogru desen.

Kanon: ham alanı oku (`s.adx`), bicimi kanondan al (`bpIndNum`, bp-format.js).

Kullanim:
  python3 tools/label-derived-number-check.py
  python3 tools/label-derived-number-check.py --ref SHA   # pozitif kontrol
"""
import os, re, sys, subprocess, tempfile, tarfile, io

# Sayiya cevirme cagrilari. Tekli `+x` KAPSAM DISI: ayirt edilemeyecek kadar
# cok yerde string birlestirme olarak geciyor, sahte-pozitif uretirdi.
NUMCALL = re.compile(r'\b(parseFloat|parseInt|Number)\s*\(')
# Sunum yuzeyi: insan icin uretilmis metin tasiyicilari.
PRESENT = re.compile(r'(?:\blabel\b|\bLabel\b|\blbl\b|\bLbl\b|[A-Za-z_$]*[Ll]abel\b|'
                     r'textContent|innerText|innerHTML|\.title\b)')
# Makine-okur tasiyicilar ve kullanici girdisi — bunlar DOGRU desen.
EXEMPT = re.compile(r'\.value\b|\bdataset\b|getAttribute\s*\(\s*[\'"]data-')

SKIP_NAME = ('.min.', 'lightweight-charts')


def _blank(t):
    return ''.join('\n' if ch == '\n' else ' ' for ch in t)


def strip_js_comments(s):
    """K-BQ dersi 42 ile ayni soyucu: yorum ESIT UZUNLUKTA bosluga cevrilir,
    boylece satir/sutun konumlari kaymaz ve `\\n` korunur."""
    out, i, n, prev = [], 0, len(s), ''
    while i < n:
        c = s[i]
        if c in '"\'`':
            q = c; out.append(c); i += 1
            while i < n:
                if s[i] == '\\': out.append(_blank(s[i:i+2])); i += 2; continue
                out.append(s[i])
                if s[i] == q: i += 1; break
                i += 1
            prev = q; continue
        if c == '/' and i + 1 < n:
            if s[i+1] == '*':
                j = s.find('*/', i + 2); j = n if j < 0 else j + 2
                out.append(_blank(s[i:j])); i = j; continue
            if s[i+1] == '/' and prev != ':':
                j = s.find('\n', i); j = n if j < 0 else j
                out.append(_blank(s[i:j])); i = j; continue
        out.append(c)
        if not c.isspace(): prev = c
        i += 1
    return ''.join(out)


def strip_html_comments(s):
    s = re.sub(r'<!--.*?-->', lambda m: _blank(m.group(0)), s, flags=re.S)
    return re.sub(r'\{#.*?#\}', lambda m: _blank(m.group(0)), s, flags=re.S)


def lineno(s, pos):
    return s.count('\n', 0, pos) + 1


def _arg_expr(s, open_paren):
    """Cagrinin ARGUMANINI dengeli parantezle cikar. ⛔ Pencere DEGIL argüman:
    K-BQ dersi 40 (yakinlik != kapsam) — 60 karakterlik kor pencere, komsu
    satirdaki alakasiz bir `label`i ihlal sayardi."""
    depth, i, n = 0, open_paren, len(s)
    while i < n:
        if s[i] == '(':
            depth += 1
        elif s[i] == ')':
            depth -= 1
            if depth == 0:
                return s[open_paren + 1:i]
        elif s[i] == '\n' and depth > 0 and i - open_paren > 400:
            break
        i += 1
    return s[open_paren + 1:open_paren + 120]


def scan_js(path, s):
    v = []
    for m in NUMCALL.finditer(s):
        arg = _arg_expr(s, m.end() - 1)
        if not PRESENT.search(arg):
            continue
        if EXEMPT.search(arg):
            continue
        v.append((path, lineno(s, m.start()), ' '.join((m.group(1) + '(' + arg).split())[:100]))
    return v


def prep_and_scan(path, raw):
    if path.endswith('.js'):
        return scan_js(path, strip_js_comments(raw))
    s = strip_html_comments(raw)
    out = []
    for sm in re.finditer(r'<script\b[^>]*>(.*?)</script>', s, flags=re.S | re.I):
        base = sm.start(1)
        for hit in scan_js(path, strip_js_comments(sm.group(1))):
            out.append((path, lineno(s, base) + hit[1] - 1, hit[2]))
    return out


def collect(root):
    files = []
    for sub, exts in (('templates', ('.html',)), ('static', ('.js',))):
        for dp, _, fns in os.walk(os.path.join(root, sub)):
            for fn in sorted(fns):
                if not fn.endswith(exts):
                    continue
                p = os.path.relpath(os.path.join(dp, fn), root).replace(os.sep, '/')
                if any(k in p for k in SKIP_NAME):
                    continue
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
        if not NUMCALL.search(raw):
            continue
        viol += prep_and_scan(rel, raw)
    return n, viol


def selftest():
    pos = [
        # K-BU'nun canli vakasi (gundem.html, fix oncesi)
        ("<script>const lbl=(inds.adx||{}).label||'';"
         "return parseFloat(lbl.replace('ADX','').trim())||null;</script>", 1),
        ("<script>var a = parseFloat(s.adxLabel);</script>", 1),
        ("<script>var n = parseInt(cell.textContent, 10);</script>", 1),
        ("<script>var q = Number(el.innerText);</script>", 1),
        ("<script>var t = parseFloat(row.querySelector('.v').innerHTML);</script>", 1),
    ]
    neg = [
        # kanon: ham alan + bpIndNum
        ("<script>h += bpIndNum(s.adx);</script>", 0),
        ("<script>var a = parseFloat(s.adx);</script>", 0),
        # form girdisi MUAF
        ("<script>var lot = parseFloat(document.getElementById('lot').value);</script>", 0),
        # makine-okur tasiyici MUAF
        ("<script>var n = parseFloat(tr.dataset.sortVal);</script>", 0),
        ("<script>var n = parseFloat(td.getAttribute('data-num'));</script>", 0),
        # yorum soyulur (ders 42: sahte-pozitif uretmemeli)
        ("<script>/* parseFloat(x.label) yasak */ var a=1;</script>", 0),
        ("{# parseFloat(s.adx_label) yasak #}<span>x</span>", 0),
        # ⛔ yakinlik != kapsam: KOMSU satirdaki 'label' ihlal degildir
        ("<script>var lblTxt = s.adx_label; var p = parseFloat(s.price);</script>", 0),
    ]
    okp = sum(1 for src, exp in pos if len(prep_and_scan('t.html', src)) == exp)
    okn = sum(1 for src, exp in neg if len(prep_and_scan('t.html', src)) == exp)
    return okp, len(pos), okn, len(neg)


def main():
    ref = None
    if '--ref' in sys.argv:
        ref = sys.argv[sys.argv.index('--ref') + 1]
    print("label-derived-number-check (K-BU: sayi insan-okur etiketten ayristirilmaz)")
    okp, tp, okn, tn = selftest()
    print("  sentetik pozitif: %d/%d · sentetik negatif: %d/%d" % (okp, tp, okn, tn))
    if okp != tp or okn != tn:
        print("  ✗ KAPI KENDI TESTINI GECEMEDI — olcum guvenilir degil.")
        return 2

    root, tmp = os.getcwd(), None
    if ref:
        tmp = tempfile.mkdtemp(prefix='kbu-')
        tarfile.open(fileobj=io.BytesIO(subprocess.check_output(['git', 'archive', ref]))).extractall(tmp)
        root = tmp

    n, viol = run(root)
    print("  taranan dosya: %d%s" % (n, (" (ref %s)" % ref) if ref else ""))
    for p, ln, ctx in viol:
        print("   . %s:%d  %s" % (p, ln, ctx))
    if viol:
        print("  ✗ %d ihlal: gosterilen sayi sunum metninden geri ayristiriliyor." % len(viol))
        return 1
    print("  ✓ temiz — sayilar ham alanindan okunuyor, etiketten degil.")
    return 0


if __name__ == '__main__':
    sys.exit(main())
