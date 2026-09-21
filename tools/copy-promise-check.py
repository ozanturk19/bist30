#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""tools/copy-promise-check.py — K-BH: "KOPYALA" VAADI ILE KOPYALANAN SEY AYNI MI?

SORU: bir dugme "bagLantiyi kopyala" diyorsa, panoya GERCEKTEN bir baglanti mi
  yaziliyor?

OLCULDU (21.09.2026, deploy oncesi yerel agac + canli /portfolio):
  Sitede dort ayri "kopyala" uygulamasi var:
    blog_article.html shareBlogCopy  -> `_BLOG_URL`      (https://... )  DOGRU
    hisse.html        shareSignal    -> `url`            (https://... )  DOGRU
    karsilastir.html  copyShareUrl   -> `window.location.href`           DOGRU
    portfolio.html    copyCloudLink  -> `_safeGetToken()`  <-- YALAN
  portfolio.html'deki dugmenin gorunur ipucu "Baglantiyi panoya kopyala",
  erisilebilir adi "Kopyala" idi (ayrica iki ad birbirini tutmuyordu) ve
  cevresindeki metin "baglantiyla paylasin" diyordu -- ama panoya yazilan sey
  ciplak bir UUID token'di ve sitede token'i URL'den geri yukleyen HICBIR yol
  yok (app.py `/portfolio` hicbir arguman almiyor). Kullanici "baglanti" diye
  kopyaladigi seyi adres cubuguna yapistirinca hicbir yere gitmiyordu.
  Ayni 440px'lik pencere ayrica "baglantiyla paylasin" ile "paylasmamanizi
  oneririz" cumlelerini yan yana tasiyordu.

KANON: kontrolun vaadi (gorunur metin + data-tip + aria-label) "baglanti/link/
  URL kopyala" diyorsa, isleyicisinin panoya yazdigi deger bir URL'den turemeli
  (`http`, `location`, `origin`). Vaat bunlari demiyorsa (ornegin "token'i
  kopyala") kapsam disidir -- kapi ne kopyalandigina karismaz, YALNIZCA vaadin
  tutulup tutulmadigina bakar.

OLCUM DISIPLINI: HTML yorumlari ve JS yorumlari SOYULUR (kendi aciklamam bulgu
  uretmesin). POZITIF ve NEGATIF kontrol birlikte calisir; dedektor ihlali
  goremiyorsa ya da muaf deseni bulgu sayiyorsa sonuc "temiz" degil
  "olculemedi"dir (bkz. K-AX / K-BD dersleri).
"""
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TEMPLATE_DIR = os.path.join(ROOT, 'templates')
JS_DIRS = [os.path.join(ROOT, 'static'), os.path.join(ROOT, 'static', 'js')]

# Vaat = KOPYALA fiili + BAGLANTI ismi birlikte gecmeli.
COPY_VERB = re.compile(r'kopyala|panoya|kopyalan', re.I)
LINK_NOUN = re.compile(r'bağlant|baglant|\blink\b|linki|url', re.I)
# Panoya yazilan degerin URL'den turedigini gosteren izler.
URL_TRACE = re.compile(r'https?://|location\b|\borigin\b|URL\b')

HTML_COMMENT = re.compile(r'<!--.*?-->', re.S)
JS_BLOCK_COMMENT = re.compile(r'/\*.*?\*/', re.S)
JS_LINE_COMMENT = re.compile(r'(?m)^\s*//.*$')

CONTROL = re.compile(
    r'<(?P<tag>button|a)\b(?P<attrs>[^>]*?onclick="(?P<fn>[A-Za-z_$][\w$]*)\([^"]*\)[^"]*"[^>]*)>'
    r'(?P<inner>.*?)</(?P=tag)>', re.S | re.I)


def strip_comments_html(text):
    return HTML_COMMENT.sub(' ', text)


def strip_comments_js(text):
    return JS_LINE_COMMENT.sub('', JS_BLOCK_COMMENT.sub(' ', text))


def promise_text(attrs, inner):
    """Kullaniciya ulasan her ad: gorunur metin + data-tip + aria-label(lar)."""
    parts = [re.sub(r'<[^>]+>', ' ', inner)]
    for m in re.finditer(r'(?:data-tip|aria-label|title)="([^"]*)"', attrs + ' ' + inner):
        parts.append(m.group(1))
    return re.sub(r'\s+', ' ', ' '.join(parts)).strip()


def function_body(text, name):
    """`function NAME(` govdesini suslu parantez esleyerek cikarir."""
    m = re.search(r'function\s+%s\s*\(' % re.escape(name), text)
    if not m:
        m = re.search(r'(?:const|let|var|window\.)\s*%s\s*=\s*(?:async\s*)?(?:function)?\s*\(' % re.escape(name), text)
        if not m:
            return None
    start = text.find('{', m.end() - 1)
    if start < 0:
        return None
    depth, i = 0, start
    while i < len(text):
        if text[i] == '{':
            depth += 1
        elif text[i] == '}':
            depth -= 1
            if depth == 0:
                return text[start:i + 1]
        i += 1
    return None


COPY_SINK = re.compile(r'clipboard\.writeText\(\s*([^)]*?)\s*\)|\.value\s*=\s*([^;\n]+)')


def copied_exprs(body):
    out = []
    for m in COPY_SINK.finditer(body):
        expr = (m.group(1) or m.group(2) or '').strip()
        if expr:
            out.append(expr)
    return out


def traces_to_url(expr, body, filetext):
    """Kopyalanan ifade bir URL'den turuyor mu? Once ifadenin kendisi, sonra
    ayni govdedeki, en son dosya duzeyindeki atamasi incelenir."""
    if URL_TRACE.search(expr):
        return True
    for ident in set(re.findall(r'[A-Za-z_$][\w$]*', expr)):
        for scope in (body, filetext):
            for am in re.finditer(
                    r'(?:const|let|var)?\s*%s\s*=\s*([^;\n]+)' % re.escape(ident), scope):
                if URL_TRACE.search(am.group(1)):
                    return True
    return False


def scan_template(path, rel, js_texts):
    raw = open(path, encoding='utf-8').read()
    html = strip_comments_html(raw)
    js = strip_comments_js(html)
    hits = []
    for m in CONTROL.finditer(html):
        promise = promise_text(m.group('attrs'), m.group('inner'))
        if not (COPY_VERB.search(promise) and LINK_NOUN.search(promise)):
            continue
        fn = m.group('fn')
        body = function_body(js, fn)
        source = js
        if body is None:
            for jt in js_texts:
                body = function_body(jt, fn)
                if body is not None:
                    source = jt
                    break
        line = html[:m.start()].count('\n') + 1
        if body is None:
            hits.append(('ISLEYICI-YOK', rel, line, '%s() bulunamadi — "%s"' % (fn, promise[:60])))
            continue
        exprs = copied_exprs(body)
        if not exprs:
            hits.append(('KOPYALAMA-YOK', rel, line, '%s() panoya hicbir sey yazmiyor — "%s"' % (fn, promise[:60])))
            continue
        if not any(traces_to_url(e, body, source) for e in exprs):
            hits.append(('VAAT-TUTMUYOR', rel, line,
                         '"%s" diyor ama %s() panoya %s yaziyor (URL izi yok)'
                         % (promise[:50], fn, ' / '.join(exprs)[:60])))
    return hits


POS_PROBE = (
    '<button onclick="copyCloudLink()" data-tip="Bağlantıyı panoya kopyala">'
    '<span aria-label="Kopyala">X</span></button>'
    '<script>function copyCloudLink(){ const token = _safeGetToken();'
    ' navigator.clipboard.writeText(token); }</script>'
)
NEG_PROBES = [
    # a) vaat "token" diyor -> kapsam disi (kapi ne kopyalandigina karismaz)
    '<button onclick="copyCloudToken()" data-tip="Token’ı panoya kopyala">X</button>'
    '<script>function copyCloudToken(){ const token = _safeGetToken();'
    ' navigator.clipboard.writeText(token); }</script>',
    # b) vaat "Linki kopyala" ve GERCEKTEN URL kopyaliyor
    '<button onclick="shareBlogCopy()" aria-label="Linki kopyala">X</button>'
    '<script>const _BLOG_URL = "https://borsapusula.com/blog/x";'
    ' function shareBlogCopy(){ navigator.clipboard.writeText(_BLOG_URL); }</script>',
    # c) vaat "Linki Kopyala" ve location.href kopyaliyor
    '<a onclick="copyShareUrl(event)">🔗 Linki Kopyala</a>'
    '<script>function copyShareUrl(e){ const url = window.location.href;'
    ' navigator.clipboard.writeText(url); }</script>',
]


def main():
    js_texts = []
    for d in JS_DIRS:
        if not os.path.isdir(d):
            continue
        for fn in sorted(os.listdir(d)):
            if fn.endswith('.js') and 'lightweight-charts' not in fn:
                js_texts.append(strip_comments_js(open(os.path.join(d, fn), encoding='utf-8').read()))

    files = sorted(f for f in os.listdir(TEMPLATE_DIR) if f.endswith('.html'))
    hits = []
    controls = 0
    for f in files:
        p = os.path.join(TEMPLATE_DIR, f)
        raw = strip_comments_html(open(p, encoding='utf-8').read())
        for m in CONTROL.finditer(raw):
            pr = promise_text(m.group('attrs'), m.group('inner'))
            if COPY_VERB.search(pr) and LINK_NOUN.search(pr):
                controls += 1
        hits += scan_template(p, 'templates/' + f, js_texts)

    import tempfile
    def probe(text):
        fd, tp = tempfile.mkstemp(suffix='.html')
        os.write(fd, text.encode('utf-8'))
        os.close(fd)
        try:
            return scan_template(tp, '__probe__.html', [])
        finally:
            os.unlink(tp)

    pos_ok = 1 if probe(POS_PROBE) else 0
    neg_ok = 0
    for np_ in NEG_PROBES:
        if not probe(np_):
            neg_ok += 1
        else:
            print('  ! NEGATIF KONTROL DUSTU: muaf/dogru desen bulgu uretti -> %s' % np_[:70])

    print('copy-promise-check (K-BH: "kopyala" vaadi = kopyalanan sey)')
    print('  taranan sablon: %d · "baglanti kopyala" vaadi veren kontrol: %d' % (len(files), controls))
    print('  pozitif kontrol: %d/1 · negatif kontrol: %d/%d' % (pos_ok, neg_ok, len(NEG_PROBES)))

    if pos_ok != 1 or neg_ok != len(NEG_PROBES):
        print('K-BH OLCULEMEDI — dedektor kendi kontrolunu gecemedi (sonuc "temiz" DEGIL).')
        return 2

    if hits:
        print('K-BH IHLAL — kontrolun vaadi panoya yazilani tutmuyor (%d):' % len(hits))
        for label, path, line, snippet in hits:
            print('  [%s] %s:%d  %s' % (label, path, line, snippet))
        print('  DUZELTME: ya gercek bir URL kopyala, ya da vaadi kopyalanan seye gore duzelt.')
        return 1

    print('  ✓ "baglanti kopyala" diyen her kontrol gercekten URL kopyaliyor')
    print('  ✓ copy-promise-check PASS')
    return 0


if __name__ == '__main__':
    sys.exit(main())
