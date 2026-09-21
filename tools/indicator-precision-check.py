#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
K-BR (22.09.2026) — ESIK TASIYAN GOSTERGE TAM SAYIYA YUVARLANAMAZ.

ADX'in **25** esigi urunun sinyal kuralidir (`adx_bull = adx >= 25 and
di_p > di_m`). Bu sayiyi tam sayiya indirmek iki seyi birden bozar:

  1. `|int` ASAGI KESER. ISDMR ADX **25,9** iken /hisse'nin AI checklist'i
     "✓ ADX **25** — Güçlü trend (**eşik: 25**)" basiyordu: kullaniciya
     "kil payi gecti" diye okunur. (K-BO dersi: ESIKLENEN SAYI, KULLANICININ
     OKUDUGU SAYI OLMALI.)
  2. AYNI SAYFADA iki farkli yuvarlama = iki farkli sayi. ISDMR'de canli:
     checklist "ADX 25" · Hap Bilgi "ADX 26" · indikator paneli "ADX 25,9".
     Anasayfa spotlight'ta ayni kartin SSR hali `|round(0)|int`, CSR hali
     `Math.round` kullaniyordu.

CANLI OLCUM (22.09, /api/data, 217 hisse): `int(adx) != round(adx)` olan
**91** hisse; ADX 25,0-25,9 bandinda **14** hisse. RSI'da 89 hisse.

Site kanonu ZATEN 1 ondalikti: /tarama `(s.adx||0).toFixed(1)`,
/karsilastir `renderAdx`/`renderRsi` `toFixed(1)`. Sapan yalniz /hisse'nin
SSR tarafi ve anasayfa spotlight'iydi -- "emsal ayni depoda yaziliydi,
miras alinmamisti" deseni (K-BO, K-BQ ile ayni aile).

OLCUT (taban SIFIR):
  A) Jinja — `adx`/`rsi` tasiyan bir `{{ }}`/`{% set %}` ifadesinde
     `|int`, `|round`, `|round(0)` zinciri.
  B) JS — `adx`/`rsi` tanimlayicisina YAKIN (<=100 anlamli ch) `Math.round(`
     veya `.toFixed(0)`.
  Muaf: bar GENISLIGI (`width`, `%` yuzdesi) -- gorsel uzunluk, sayi degil.

Kanon: Jinja `'%.1f'|format(x)|replace('.', ',')` · JS `bpIndNum(x)`.
JSON-LD yapisal veride ondalik AYIRAC NOKTA kalir (`'%.1f'|format(x)`).

Kullanim:
  python3 tools/indicator-precision-check.py
  python3 tools/indicator-precision-check.py --ref SHA   # pozitif kontrol
"""
import os, re, sys, subprocess, tempfile, tarfile, io

WINDOW = 100
# ⛔ Lookbehind'da `_` YOK: `seo_adx`, `_adx`, `ssr_adx` gibi adlar da bu
# gostergenin TASIYICISIDIR. Ilk yazim `(?<![A-Za-z_])` kullaniyordu ve
# JSON-LD'deki `{{ seo_adx|round|int }}`'i KACIRDI (kapi kendi fix'imi
# denetlerken ortaya cikti — K-BP dersi 38).
IND = re.compile(r'(?<![A-Za-z])(adx|rsi)(?![A-Za-z])', re.I)
# A) Jinja yuvarlama zinciri
JINJA_ROUND = re.compile(r'\|\s*(int|round)\b')
# B) JS tam sayiya indirme
JS_ROUND = re.compile(r'Math\.round\s*\(|\.toFixed\s*\(\s*0\s*\)')
# Bar genisligi / yuzde baglami — gorsel uzunluk, gosterge SAYISI degil.
# ⛔ Muafiyet YUVARLANAN IFADEYE bakar, satirin geri kalanina DEGIL:
# index.html'de bar genisligi (`adxPct.toFixed(0)`) ile gosterge sayisi
# (`Math.round(s.adx)`) AYNI deyimde yan yanaydi; genis baglam muafiyeti
# gercek ihlali sahte-negatife ceviriyordu.
BAR_ARG = re.compile(r'(pct|width|pxw|oran)\b|style="?width|width:', re.I)
# Jinja tarafinda yuzde/genislik ifadesi
BAR_CTX = re.compile(r'width|Pct\b|pct\b|stroke-dash', re.I)

SKIP_FILES = {'static/bp-format.js'}   # kanonun kendisi


def _blank(t):
    return ''.join('\n' if ch == '\n' else ' ' for ch in t)


def strip_js_comments(s):
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
            if prev == '' or prev in '(,=:[!&|?{};+-*%~^<>':
                j, ok = i + 1, False
                while j < n and s[j] != '\n':
                    if s[j] == '\\': j += 2; continue
                    if s[j] == '[':
                        while j < n and s[j] != ']' and s[j] != '\n':
                            j += 2 if s[j] == '\\' else 1
                    elif s[j] == '/':
                        ok = True; break
                    j += 1
                if ok:
                    while j + 1 < n and s[j+1].isalpha(): j += 1
                    out.append(s[i:j+1]); prev = '/'; i = j + 1; continue
        out.append(c)
        if not c.isspace(): prev = c
        i += 1
    return ''.join(out)


def strip_html_comments(s):
    s = re.sub(r'<!--.*?-->', lambda m: _blank(m.group(0)), s, flags=re.S)
    return re.sub(r'\{#.*?#\}', lambda m: _blank(m.group(0)), s, flags=re.S)


def strip_in_scripts(s):
    return re.sub(r'(<script\b[^>]*>)(.*?)(</script>)',
                  lambda m: m.group(1) + strip_js_comments(m.group(2)) + m.group(3),
                  s, flags=re.S | re.I)


def lineno(s, pos):
    return s.count('\n', 0, pos) + 1


def _span(s, start, end):
    """Pencereyi ANLAMLI KARAKTER cinsinden ac (K-BQ dersi 42: soyulan yorum
    esit uzunlukta bosluga cevrilir ve ham pencereyi doldurur)."""
    lo, cnt = start, 0
    while lo > 0 and cnt < WINDOW:
        lo -= 1
        if not s[lo].isspace(): cnt += 1
    hi, cnt, n = end, 0, len(s)
    while hi < n and cnt < WINDOW:
        if not s[hi].isspace(): cnt += 1
        hi += 1
    return lo, hi


def scan_jinja(path, s):
    v = []
    for m in re.finditer(r'\{\{.*?\}\}|\{%-?\s*set\b.*?-?%\}', s, flags=re.S):
        chunk = m.group(0)
        if not IND.search(chunk) or not JINJA_ROUND.search(chunk):
            continue
        if BAR_CTX.search(chunk):
            continue
        v.append((path, lineno(s, m.start()), 'A/Jinja', ' '.join(chunk.split())[:90]))
    return v


def _rounded_arg_is_bar(win, rm):
    """Yuvarlanan sey bir BAR GENISLIGI/yuzde mi? `Math.round(X)` -> X;
    `Y.toFixed(0)` -> Y. Sadece o ifadeye bakilir."""
    txt = rm.group(0)
    if txt.startswith('Math.round'):
        # Math.round(X) -> X SAGDA
        arg = win[rm.end():rm.end() + 40]
    else:
        # Y.toFixed(0) -> Y SOLDA. `Math.max(0,Math.min(100,s.rsi)).toFixed(0)`
        # gibi sarmalanmis ifadelerde `width:` ancak ~70 ch geride kalir.
        arg = win[max(0, rm.start() - 70):rm.start()]
    return bool(BAR_ARG.search(arg))


def scan_js(path, s):
    """⛔ Ayni yuvarlama deyimi BIRDEN COK gosterge gecisine yakin olabilir
    (`s.rsi != null ? Math.round(s.rsi) : …` -> iki eslesme, ayrica 'ADX'
    METNI de tanimlayiciya uyar). Ihlal YUVARLAMANIN KONUMUNA gore tekillesir,
    yoksa tek kusur iki kez raporlanir ve sayim kapsam yalani soyler."""
    v, seen = [], set()
    for m in IND.finditer(s):
        lo, hi = _span(s, m.start(), m.end())
        win = s[lo:hi]
        # ⛔ TUM yuvarlamalara bak, ILKINE degil: index.html'de bar genisligi
        # (`adxPct.toFixed(0)`, MUAF) gosterge sayisindan (`Math.round(s.adx)`,
        # IHLAL) ONCE geliyordu; "ilk eslesme" mantigi ihlali GIZLIYORDU.
        for rm in JS_ROUND.finditer(win):
            if _rounded_arg_is_bar(win, rm):
                continue
            key = lo + rm.start()
            if key in seen:
                continue
            seen.add(key)
            v.append((path, lineno(s, key), 'B/JS',
                      ' '.join(win[max(0, rm.start() - 45):rm.start() + 55].split())[:90]))
    return v


def prep_and_scan(path, raw):
    if path.endswith('.js'):
        return scan_js(path, strip_js_comments(raw))
    s = strip_in_scripts(strip_html_comments(raw))
    out = scan_jinja(path, s)
    for sm in re.finditer(r'<script\b[^>]*>(.*?)</script>', s, flags=re.S | re.I):
        base = sm.start(1)
        for hit in scan_js(path, sm.group(1)):
            out.append((path, lineno(s, base) + hit[1] - 1, 'B/JS', hit[3]))
    return out


def collect(root):
    files, seen = [], set()
    for sub, exts in (('templates', ('.html',)), ('static', ('.js',))):
        for dp, _, fns in os.walk(os.path.join(root, sub)):
            for fn in sorted(fns):
                if fn.endswith(exts):
                    p = os.path.relpath(os.path.join(dp, fn), root).replace(os.sep, '/')
                    if p not in SKIP_FILES and p not in seen and '.min.' not in p:
                        seen.add(p); files.append(p)
    return sorted(files)


def run(root):
    viol, n = [], 0
    for rel in collect(root):
        try:
            raw = io.open(os.path.join(root, rel), encoding='utf-8').read()
        except Exception:
            continue
        n += 1
        if not IND.search(raw):
            continue
        viol += prep_and_scan(rel, raw)
    return n, viol


def selftest():
    pos = [
        ('<dd>{{ ssr_signal.adx|round|int }}</dd>', 1),
        ("ADX {{ ssr_signal.adx|int if ssr_signal.adx else '—' }}", 1),
        ("{% set d = 'ADX ' ~ (s.adx or 0)|round|int %}", 1),
        ("<script>h += (s.rsi!=null?Math.round(s.rsi):'-');</script>", 1),
        ("<script>var t = 'ADX ' + s.adx.toFixed(0);</script>", 1),
        # ⛔ tuketici adi alt cizgili (JSON-LD kor noktasi)
        ('{{ seo_adx|round|int }}', 1),
        # ⛔ bar genisligi ile gosterge sayisi AYNI deyimde (dar muafiyet sinavi)
        ("<script>h='<i style=\"width:'+adxPct.toFixed(0)+'%\"></i>'+(s.adx!=null?Math.round(s.adx):'-');</script>", 1),
    ]
    neg = [
        ("<dd>{{ '%.1f'|format(ssr_signal.adx)|replace('.', ',') }}</dd>", 0),
        ("<script>e.textContent = bpIndNum(s.adx);</script>", 0),
        # bar GENISLIGI muaf
        ("<script>var adxPct=(s.adx/50)*100; h='<i style=\"width:'+adxPct.toFixed(0)+'%\"></i>';</script>", 0),
        # yorum soyulur
        ("<script>/* s.adx icin Math.round kullanma */ var a=1;</script>", 0),
        ("{# adx|round|int yasak #}<span>x</span>", 0),
        # sarmalanmis bar genisligi (index.html:823 emsali) MUAF
        ("<script>h='<i style=\"width:' + Math.max(0,Math.min(100,s.rsi)).toFixed(0) + '%\"></i>';</script>", 0),
        # alakasiz round (gostergeden UZAK)
        ("<script>var q = s.adx; " + ("var z=1; " * 30) + "var w = Math.round(price);</script>", 0),
    ]
    okp = sum(1 for src, exp in pos if len(prep_and_scan('t.html', src)) == exp)
    okn = sum(1 for src, exp in neg if len(prep_and_scan('t.html', src)) == exp)
    return okp, len(pos), okn, len(neg)


def main():
    ref = None
    if '--ref' in sys.argv:
        ref = sys.argv[sys.argv.index('--ref') + 1]
    print("indicator-precision-check (K-BR: esik tasiyan gosterge tam sayiya yuvarlanamaz)")
    okp, tp, okn, tn = selftest()
    print("  sentetik pozitif: %d/%d · sentetik negatif: %d/%d" % (okp, tp, okn, tn))
    if okp != tp or okn != tn:
        print("  ✗ KAPI KENDI TESTINI GECEMEDI — olcum guvenilir degil.")
        return 2

    root, tmp = os.getcwd(), None
    if ref:
        tmp = tempfile.mkdtemp(prefix='kbr-')
        tarfile.open(fileobj=io.BytesIO(subprocess.check_output(['git', 'archive', ref]))).extractall(tmp)
        root = tmp

    n, viol = run(root)
    print("  taranan dosya: %d%s" % (n, (" (ref %s)" % ref) if ref else ""))
    for p, ln, kind, ctx in viol:
        print("   . %s:%d [%s] %s" % (p, ln, kind, ctx))
    if viol:
        print("  ✗ %d ihlal: ADX/RSI tam sayiya yuvarlaniyor (esik 25 ile cakisir)." % len(viol))
        return 1
    print("  ✓ temiz — ADX/RSI her yuzeyde 1 ondalik kanonunda.")
    return 0


if __name__ == '__main__':
    sys.exit(main())
