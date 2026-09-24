#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
K-BT (22.09.2026) — BIR innerHTML YAZIMI KARDES BIR BILESENI YOK ETMEMELI.

`el.innerHTML = ...` bir kabin BUTUN icerigini siler. O kabin icinde, JS'in
BASKA bir yerde `getElementById` ile doldurdugu bir id varsa, yazim o bileseni
DOM'dan kaldirir; bileseni dolduran kod sessizce hicbir sey yapmaz (getElementById
null doner, guard'lar yuzunden hata da atilmaz).

CANLI VAKA (22.09, /hisse): "Hacim Profili" paneli `#entryAnalysisGrid`in ucuncu
cocuguydu. `renderEntryAnalysis()`in "aktif sinyal yok" dali
`grid.innerHTML = '<placeholder>'` yaziyordu -> BEKLE olan **138/217** hissede
panelin markup'i DOM'dan siliniyordu, oysa `rvol`/`signal_vol_ratio` 217/217
hissede DOLU geliyordu. Ayni sinif daha once iki kez P1 uretti:
  * K-U  — "✎ Düzenle" akisi pozisyonu SILIYORDU
  * K-AF — `*` reduce-motion kurali marquee ICERIGINI yok ediyordu

OLCUM: sablonun HTML iskeleti `html.parser` ile gezilir, innerHTML ile UZERINE
YAZILAN her kabin ALT id'leri toplanir. Bir alt id ayni dosyada `getElementById`
ile de kullaniliyorsa ihlal. Jinja kosullari yuzunden iskelet cozulemezse
"OLCULEMEDI" denir -- sessizce PASS DEGIL (K-BP dersi 40).

BEYAZ LISTE: kabin KENDI id'si ve yalnizca o yazimin urettigi id'ler muaftir;
dosya:id cifti olarak yazilir (satir numarasi ASLA anahtar olamaz -- K-BF dersi).

Kullanim:
  python3 tools/innerhtml-sibling-check.py            # calisan agac
  python3 tools/innerhtml-sibling-check.py --ref SHA  # o commit'in agaci
"""
import os, re, sys, io, subprocess, tempfile, tarfile
from html.parser import HTMLParser

TPL_DIR = 'templates'
VOID = {'area', 'base', 'br', 'col', 'embed', 'hr', 'img', 'input', 'link',
        'meta', 'param', 'source', 'track', 'wbr'}

# `X.innerHTML =` / `getElementById('X').innerHTML =`
INNER_DIRECT = re.compile(r"getElementById\(\s*['\"]([A-Za-z0-9_-]+)['\"]\s*\)\s*\.innerHTML\s*=")
# `const g = document.getElementById('X'); ... g.innerHTML = `
VAR_BIND = re.compile(r"(?:const|let|var)\s+([A-Za-z_$][\w$]*)\s*=\s*document\.getElementById\(\s*['\"]([A-Za-z0-9_-]+)['\"]\s*\)")
VAR_INNER = re.compile(r"(?<![\w$.])([A-Za-z_$][\w$]*)\s*\.innerHTML\s*=")
GET_BY_ID = re.compile(r"getElementById\(\s*['\"]([A-Za-z0-9_-]+)['\"]\s*\)")

# ── MUAFIYETLER: (dosya, KAP, COCUK) ─────────────────────────────────────────
# ANAHTAR COCUGU DA ICERIR. Kap bazli bir muafiyet cazip gorunuyordu ama kapiyi
# KENDI BULGUSUNA KOR BIRAKIYORDU: K-BT'nin canli vakasi (hpRvolRow & co.) tam
# da muaf tutulacak kabin (#entryAnalysisGrid) icindeydi -- kap bazli liste onu
# da yutar, pozitif kontrol sessizce gecerdi (K-BQ dersi 41'in aynasi: kapi
# fix'in KENDISINI olcmeli). Cocugu anahtara koymak, ayni kaba SONRADAN
# eklenen her bileseni yakalar. Satir numarasi ASLA anahtar olamaz (K-BF).
# Her muafiyet kosumda BASILIR; tetiklenmeyeni BAYAT sayilir ve kapi kirilir.
EXEMPT_REASON = {
    ('templates/hisse.html', 'entryAnalysisGrid'):
        'Giris analizinin KENDI cocuklari. Placeholder dallari grid`i eziyor; '
        'basari dali `_pristineEntryGridHtml`den geri yukluyor (~2437). BEKLE`de '
        'geri yukleme HIC olmaz ama bu dort id`yi dolduran kod da ayni erken '
        'return`un arkasinda kaldigi icin gorunur bir kayip yok -- SINYALDEN '
        'BAGIMSIZ bir bilesen bu kaba KONULAMAZ (K-BT`nin ta kendisi).',
    ('templates/index.html', 'heroSubForm'):
        'Abonelik formu: kap YALNIZCA basari dalinda "tesekkurler" mesajiyla '
        'degistirilir, o noktada input/kvkk/msg bir daha okunmaz. Hata dallari '
        'kabi EZMEZ, mesaji #heroSubMsg`e yazar (index.html heroSubmitSub).',
    ('templates/ozet.html', 'ozSubForm'): 'Ayni abonelik kalibi (bkz. heroSubForm).',
    ('templates/blog_article.html', 'artSubForm'): 'Ayni abonelik kalibi (bkz. heroSubForm).',
    ('templates/hisse.html', 'hisseSubCta'): 'Ayni abonelik kalibi (bkz. heroSubForm).',
}
EXEMPT = set([
    ('templates/hisse.html', 'entryAnalysisGrid', 'eqBadge'),
    ('templates/hisse.html', 'entryAnalysisGrid', 'eqNote'),
    ('templates/hisse.html', 'entryAnalysisGrid', 'rrLevels'),
    ('templates/hisse.html', 'hisseSubCta', 'hisseSubEmail'),
    ('templates/hisse.html', 'hisseSubCta', 'hisseSubKvkk'),
    ('templates/index.html', 'heroSubForm', 'heroSubEmail'),
    ('templates/index.html', 'heroSubForm', 'heroSubKvkk'),
    ('templates/index.html', 'heroSubForm', 'heroSubMsg'),
    ('templates/ozet.html', 'ozSubForm', 'ozSubEmail'),
    ('templates/ozet.html', 'ozSubForm', 'ozSubKvkk'),
    ('templates/ozet.html', 'ozSubForm', 'ozSubMsg'),
    ('templates/blog_article.html', 'artSubForm', 'artSubBtn'),
    ('templates/blog_article.html', 'artSubForm', 'artSubEmail'),
    ('templates/blog_article.html', 'artSubForm', 'artSubKvkk'),
])


def _blank(t):
    return ''.join('\n' if ch == '\n' else ' ' for ch in t)


def strip_jinja(src):
    """Jinja blok/ifade/yorumlarini bosluga cevir — HTML iskeleti kalsin."""
    src = re.sub(r'\{#.*?#\}', lambda m: _blank(m.group(0)), src, flags=re.S)
    src = re.sub(r'\{%.*?%\}', lambda m: _blank(m.group(0)), src, flags=re.S)
    src = re.sub(r'\{\{.*?\}\}', lambda m: _blank(m.group(0)), src, flags=re.S)
    # <script>/<style> govdeleri: icindeki `id="..."` metinleri iskelet degil
    src = re.sub(r'<script\b[^>]*>.*?</script>', lambda m: _blank(m.group(0)), src, flags=re.S | re.I)
    src = re.sub(r'<style\b[^>]*>.*?</style>', lambda m: _blank(m.group(0)), src, flags=re.S | re.I)
    return src


class Tree(HTMLParser):
    """id'li her ogenin ALT id kumesini toplar. convert_charrefs kapali degil;
    yalnizca yapi lazim."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.stack = []          # [(tag, id or None)]
        self.desc = {}           # id -> set(alt id)
        self.seen = set()
        self.broken = False

    def handle_starttag(self, tag, attrs):
        if tag in VOID:
            eid = dict(attrs).get('id')
            if eid:
                self._record(eid)
            return
        eid = dict(attrs).get('id')
        if eid:
            self._record(eid)
            self.desc.setdefault(eid, set())
        self.stack.append((tag, eid))

    def _record(self, eid):
        self.seen.add(eid)
        for _t, oid in self.stack:
            if oid:
                self.desc.setdefault(oid, set()).add(eid)

    def handle_startendtag(self, tag, attrs):
        eid = dict(attrs).get('id')
        if eid:
            self._record(eid)

    def handle_endtag(self, tag):
        for i in range(len(self.stack) - 1, -1, -1):
            if self.stack[i][0] == tag:
                del self.stack[i:]
                return
        self.broken = True   # kapanis eslesmedi -> iskelet guvenilmez


def overwritten_containers(src):
    """innerHTML ile UZERINE YAZILAN kap id'leri."""
    ids = set(INNER_DIRECT.findall(src))
    binds = {}
    for m in VAR_BIND.finditer(src):
        binds.setdefault(m.group(1), set()).add(m.group(2))
    for m in VAR_INNER.finditer(src):
        for eid in binds.get(m.group(1), ()):
            ids.add(eid)
    return ids


def check_tree(root):
    viol, unmeasured, used = [], [], set()
    tdir = os.path.join(root, TPL_DIR)
    for dp, _dn, fn in os.walk(tdir):
        for f in sorted(fn):
            if not f.endswith('.html'):
                continue
            path = os.path.join(dp, f)
            rel = os.path.relpath(path, root)
            try:
                raw = io.open(path, encoding='utf-8').read()
            except (UnicodeDecodeError, OSError):
                continue
            containers = overwritten_containers(raw)
            if not containers:
                continue
            populated = set(GET_BY_ID.findall(raw))
            t = Tree()
            try:
                t.feed(strip_jinja(raw))
                t.close()
            except Exception as e:
                unmeasured.append((rel, 'parse hatasi: %s' % e))
                continue
            if t.broken:
                unmeasured.append((rel, 'HTML iskeleti cozulemedi (kapanis eslesmedi)'))
                continue
            for cid in sorted(containers):
                for child in sorted(t.desc.get(cid, ())):
                    if child == cid:
                        continue
                    if child not in populated:
                        continue
                    if (rel, cid, child) in EXEMPT:
                        used.add((rel, cid, child))
                        continue
                    viol.append((rel, cid, child))
    return viol, unmeasured, used


def export_ref(ref):
    tmp = tempfile.mkdtemp(prefix='k-bt-')
    tar = subprocess.check_output(['git', 'archive', ref])
    tarfile.open(fileobj=io.BytesIO(tar)).extractall(tmp)
    return tmp


def main():
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    if '--ref' in sys.argv:
        ref = sys.argv[sys.argv.index('--ref') + 1]
        os.chdir(root)
        root = export_ref(ref)
    print('innerhtml-sibling-check (K-BT: innerHTML yazimi kardes bileseni yok etmemeli)')
    sp, sn = self_test()
    print('  sentetik pozitif: %d/%d · sentetik negatif: %d/%d' % (sp, 2, sn, 2))
    if sp != 2 or sn != 2:
        print('  ✗ DEDEKTOR KIRIK — sentetik testler gecmedi, olcum guvenilmez.')
        return 1
    viol, unmeasured, used = check_tree(root)
    for rel, why in unmeasured:
        print('  ! OLCULEMEDI %s — %s' % (rel, why))
    for (rel, cid), why in sorted(EXEMPT_REASON.items()):
        kids = sorted(c for (r, k, c) in EXEMPT if (r, k) == (rel, cid))
        hit = sum(1 for c in kids if (rel, cid, c) in used)
        print('  muafiyet [%d/%d] %s #%s (%s) — %s'
              % (hit, len(kids), rel, cid, ', '.join(kids), why))
    stale = [k for k in EXEMPT if k not in used]
    if viol:
        print('  IHLAL: %d' % len(viol))
        for rel, cid, child in viol:
            print('    %s: #%s uzerine innerHTML yaziliyor, icinde JS ile doldurulan #%s var' % (rel, cid, child))
        return 1
    if unmeasured:
        print('  ✗ en az bir dosya olculemedi — sessiz PASS verilmez.')
        return 1
    if stale:
        print('  ✗ BAYAT MUAFIYET: %s — artik tetiklenmiyor, listeden cikar.' % stale)
        return 1
    print('  ✓ temiz — muaf kaplar disinda hicbir innerHTML yazimi JS ile doldurulan bir kardesi kapsamiyor.')
    return 0


def self_test():
    """Dedektorun kendisi olculur (K-BP dersi: kapi yazarini denetler)."""
    POS = [
        ('<div id="box"><span id="child">x</span></div>',
         "document.getElementById('box').innerHTML = 'y'; document.getElementById('child');"),
        ('<div id="wrap"><p id="inner"></p></div>',
         "const w = document.getElementById('wrap'); w.innerHTML = ''; document.getElementById('inner');"),
    ]
    NEG = [
        # cocuk JS ile doldurulmuyor -> ihlal degil
        ('<div id="box"><span id="child">x</span></div>',
         "document.getElementById('box').innerHTML = 'y';"),
        # kap uzerine innerHTML YAZILMIYOR (sadece okunuyor)
        ('<div id="box"><span id="child">x</span></div>',
         "var t = document.getElementById('box').innerHTML; document.getElementById('child');"),
    ]
    def run(markup, js):
        raw = markup + '<script>' + js + '</script>'
        containers = overwritten_containers(raw)
        populated = set(GET_BY_ID.findall(raw))
        t = Tree(); t.feed(strip_jinja(raw)); t.close()
        if t.broken:
            return False
        for cid in containers:
            for ch in t.desc.get(cid, ()):
                if ch != cid and ch in populated:
                    return True
        return False
    return sum(1 for m, j in POS if run(m, j)), sum(1 for m, j in NEG if not run(m, j))


if __name__ == '__main__':
    sys.exit(main())
