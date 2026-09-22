#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
K-BZ (22.09.2026) — KOKEN ROZETI, ALTINDAKI ICERIGIN KOKENINI SOYLER.

Bir "kaynak/koken rozeti" (Gemini AI / Algoritmik / KAP + AI ...) okura o anda
ekranda duran metnin NEREDEN geldigini soyler. Rozet JS tarafindan yanitin
`source` alanina gore yeniden yaziliyorsa, SSR'daki sabit metin "yanit henuz
YOK" durumuna aittir -- yani saglayici adi IDDIA EDEMEZ.

CANLI VAKA (22.09, /hisse/<T> -> AI Analiz):
  `#sigExplainBadge` SSR'da kosulsuz "Gemini AI" yaziyordu. Altindaki
  `#sigExplainLoading` ise SSR'in KURAL-TABANLI 3-kriter checklist'iydi
  (Supertrend / ADX / EMA hizalamasi). Yani yanit gelene kadar, hata dalinda
  ve "veri yok" dalinda rozet yapay zeka iddia ederken govde bir Python
  sablonuydu. Ayni sinif: K-AQ (tek rozet ayni anda uc sey diyordu),
  K-BN ("~15 dk gecikmeli" derken fiyat 63 saat eskiydi).

OLCUM (yazimdan bagimsiz -- ders 52):
  1. Sablonun HTML iskeleti gezilir; METNINDE saglayici adi gecen her oge
     bulunur (rozet sinifi/id'si aranmaz -- yazim degisebilir).
  2. O oge JS tarafindan yeniden yazilabilir mi? -> id'si `getElementById`
     ile VEYA sinifi `querySelector`/`querySelectorAll` ile ayni dosyada
     (veya static/*.js icinde) referanslaniyorsa EVET.
  3. Oge SSR'da GORUNUR mu? -> kendisinde ya da atalarinda satir-ici
     `display:none` / `hidden` varsa HAYIR (yanit gelmeden hic gorunmez,
     iddia da okunmaz).
  IHLAL = yeniden yazilabilir VE SSR'da gorunur.

`#newsSource` bu yuzden MUAF DEGIL, sadece IHLAL DEGIL: kabi SSR'da
`style="display:none"` -- rozet ancak JS metni yazdiktan sonra gosteriliyor.
Beyaz liste YOK (K-BF dersi: muafiyet ilk refleks olmamali).

Kullanim:
  python3 tools/provenance-badge-check.py
  python3 tools/provenance-badge-check.py --ref SHA   # o agaci olc
"""
import os, re, sys, subprocess, tempfile, tarfile
from html.parser import HTMLParser

TPL_DIR = 'templates'
JS_DIR_CANDIDATES = ('static', os.path.join('static', 'js'))
VOID = {'area','base','br','col','embed','hr','img','input','link','meta',
        'param','source','track','wbr'}

# Saglayici adlari — rozet metninde gecerse "koken iddiasi" sayilir.
VENDOR = re.compile(r'\b(Gemini|OpenAI|ChatGPT|GPT-\d|Claude|Perplexity|Copilot)\b')
# Duz nesir degil, ROZET olcegi metin: kisa. Uzun paragraflar (gizlilik/hakkinda
# sayfalarindaki aciklamalar) koken rozeti degildir.
BADGE_MAXLEN = 48

HIDDEN_STYLE = re.compile(r'display\s*:\s*none', re.I)


def _blank(t):
    return ''.join('\n' if ch == '\n' else ' ' for ch in t)


def strip_jinja_keep_scripts(src):
    src = re.sub(r'\{#.*?#\}', lambda m: _blank(m.group(0)), src, flags=re.S)
    src = re.sub(r'\{%.*?%\}', lambda m: _blank(m.group(0)), src, flags=re.S)
    src = re.sub(r'\{\{.*?\}\}', lambda m: _blank(m.group(0)), src, flags=re.S)
    return src


def scripts_of(src):
    return '\n'.join(re.findall(r'<script\b[^>]*>(.*?)</script>', src, flags=re.S | re.I))


def html_skeleton(src):
    src = strip_jinja_keep_scripts(src)
    src = re.sub(r'<script\b[^>]*>.*?</script>', lambda m: _blank(m.group(0)), src, flags=re.S | re.I)
    src = re.sub(r'<style\b[^>]*>.*?</style>', lambda m: _blank(m.group(0)), src, flags=re.S | re.I)
    return src


class Finder(HTMLParser):
    """Metninde saglayici adi gecen ogeleri, id/class/gizlilik baglamiyla toplar."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.stack = []      # [(tag, id, classes, hidden_here)]
        self.hits = []       # (lineno, tag, id, classes, hidden_ancestor, text)
        self.broken = False

    def _hidden_now(self):
        return any(h for (_t, _i, _c, h) in self.stack)

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        eid = a.get('id')
        cls = (a.get('class') or '').split()
        hid = bool(HIDDEN_STYLE.search(a.get('style') or '')) or ('hidden' in a)
        if tag in VOID:
            return
        self.stack.append((tag, eid, cls, hid))

    def handle_endtag(self, tag):
        for i in range(len(self.stack) - 1, -1, -1):
            if self.stack[i][0] == tag:
                del self.stack[i:]
                return
        self.broken = True

    def handle_data(self, data):
        if not self.stack:
            return
        txt = data.strip()
        if not txt or not VENDOR.search(txt) or len(txt) > BADGE_MAXLEN:
            return
        tag, eid, cls, _h = self.stack[-1]
        self.hits.append({
            'line': self.getpos()[0], 'tag': tag, 'id': eid, 'class': cls,
            'hidden': self._hidden_now(), 'text': txt,
        })


def js_rewritable(js_blobs, eid, classes):
    if eid and re.search(r"getElementById\(\s*['\"]%s['\"]\s*\)" % re.escape(eid), js_blobs):
        return "getElementById('%s')" % eid
    for c in classes:
        if re.search(r"querySelector(?:All)?\(\s*['\"][^'\"]*\.%s\b" % re.escape(c), js_blobs):
            return "querySelector('.%s')" % c
    return None


def collect(root):
    tpl_dir = os.path.join(root, TPL_DIR)
    shared_js = []
    for d in JS_DIR_CANDIDATES:
        p = os.path.join(root, d)
        if os.path.isdir(p):
            for fn in sorted(os.listdir(p)):
                if fn.endswith('.js'):
                    shared_js.append(open(os.path.join(p, fn), encoding='utf-8', errors='replace').read())
    shared_js = '\n'.join(shared_js)

    violations, cleared, unparsed = [], [], []
    for fn in sorted(os.listdir(tpl_dir)):
        if not fn.endswith('.html'):
            continue
        rel = os.path.join(TPL_DIR, fn)
        src = open(os.path.join(tpl_dir, fn), encoding='utf-8', errors='replace').read()
        js = scripts_of(src) + '\n' + shared_js
        f = Finder()
        try:
            f.feed(html_skeleton(src))
        except Exception as e:
            unparsed.append((rel, str(e)))
            continue
        if f.broken:
            unparsed.append((rel, 'etiket agaci cozulemedi'))
        for h in f.hits:
            why = js_rewritable(js, h['id'], h['class'])
            rec = dict(h); rec['file'] = rel; rec['why'] = why
            if why and not h['hidden']:
                violations.append(rec)
            else:
                cleared.append(rec)
    return violations, cleared, unparsed


def tree_at(ref):
    tmp = tempfile.mkdtemp(prefix='provbadge-')
    tar = os.path.join(tmp, 't.tar')
    subprocess.run(['git', 'archive', '-o', tar, ref], check=True)
    with tarfile.open(tar) as tf:
        tf.extractall(tmp)
    return tmp


def main():
    ref = None
    if '--ref' in sys.argv:
        ref = sys.argv[sys.argv.index('--ref') + 1]
    root = tree_at(ref) if ref else '.'
    violations, cleared, unparsed = collect(root)

    for c in cleared:
        reason = 'SSR`da gizli (yanit gelmeden gorunmez)' if c['hidden'] else 'JS yeniden yazamiyor (sabit iddia)'
        print('  temiz  %s:%d <%s> "%s" — %s' % (c['file'], c['line'], c['tag'], c['text'], reason))
    for u in unparsed:
        print('  OLCULEMEDI %s — %s' % u)
    if unparsed:
        print('✗ K-BZ OLCULEMEDI — sessizce PASS degil (ders 40).')
        return 1
    if violations:
        for v in violations:
            print('  IHLAL %s:%d <%s id=%s> "%s" — %s ile yeniden yazilabiliyor ve SSR`da GORUNUR'
                  % (v['file'], v['line'], v['tag'], v['id'], v['text'], v['why']))
        print('✗ K-BZ KIRIK: koken rozeti, yanit gelmeden saglayici adi iddia ediyor.')
        return 1
    print('K-BZ OK — gorunur koken rozetlerinin hicbiri yanitsiz durumda saglayici adi iddia etmiyor.')
    return 0


if __name__ == '__main__':
    sys.exit(main())
