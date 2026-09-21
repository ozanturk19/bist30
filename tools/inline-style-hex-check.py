#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""tools/inline-style-hex-check.py — K-BW: SABLONUN SATIR-ICI `style=`
ATTRIBUTE'UNDAKI HAM HEX.

NEDEN AYRI BIR KAPI GEREKTI (22.09.2026):
  Sitede rengi denetleyen iki kapi vardi ve `#ff7875` IKISININ DE ARASINDAN
  gecti:
    * `style-guard`      -> yalniz `static/css/*.css` bakar.
    * `js-palette-check` -> JS dosyalari + sablonlarin `<script>` bloklari.
  Ama `templates/hisse.html:139` soyleydi:
        <span style="color:#ff7875">▼ Bozuldu</span>
  Bu ne CSS dosyasi ne de betik: HTML ATTRIBUTE'u. Ucuncu bir kanal.
  Olculdu: `#ff7875` tokens.css'te HIC YOK (kanonik `--bp-sat` = #f85149),
  ve bu rozet CANLI 72/217 hisse sayfasinda basiliyordu -- ayni sayfadaki
  diger her SAT yuzeyi token'dan gelirken.

KANON: satir-ici `style=` icinde bir renk YALNIZ su iki bicimde gecebilir:
  1. `var(--bp-x)`                    -> token
  2. `var(--bp-x, #yedek)`            -> token + yedek (hex yalniz YEDEK
                                         argumanda; _analytics.html boyle)
Ciplak `#rrggbb` / `#rgb` / `rgb()` / `rgba()` -> IHLAL.

MUAFIYET (ALLOW_HEX): marka rengi. Bir baska sirketin markasi bizim
paletimizin parcasi degildir, token'i da olmaz (#25D366 = WhatsApp yesili).
Muafiyet RENGE verilir, satir numarasina degil
(⛔ bkz. c952a78: beyaz liste anahtari satir numarasi olamaz).

Kullanim:
  python3 tools/inline-style-hex-check.py
  python3 tools/inline-style-hex-check.py --ref SHA
"""
import io
import os
import re
import subprocess
import sys
import tarfile
import tempfile

# Baska sirketlerin marka renkleri -- paletin parcasi degil, token'lari olmaz.
ALLOW_HEX = {
    '#25d366',  # WhatsApp
}

STYLE_ATTR = re.compile(r'style\s*=\s*"([^"]*)"', re.I)
HEX = re.compile(r'#[0-9a-fA-F]{3,8}\b')
# `var(--x, #yedek)` -- hex'in MESRU tek yeri. Ic ice var() yok, tek seviye yeter.
VAR_FALLBACK = re.compile(r'var\(\s*--[\w-]+\s*,[^)]*\)')


def strip_jinja_comments(s):
    def blank(m):
        return ''.join('\n' if c == '\n' else ' ' for c in m.group(0))
    s = re.sub(r'\{#.*?#\}', blank, s, flags=re.S)
    s = re.sub(r'<!--.*?-->', blank, s, flags=re.S)
    return s


def token_hexes(root):
    """tokens.css'te TANIMLI hex kumesi -- 'token'da var, kopyalanmis' halini
    ayirt edebilmek icin (kopya da ihlaldir ama mesaji farklidir)."""
    p = os.path.join(root, 'static', 'css', 'tokens.css')
    try:
        src = io.open(p, encoding='utf-8', errors='replace').read()
    except OSError:
        return set()
    return {h.lower() for h in HEX.findall(src)}


def scan(root):
    toks = token_hexes(root)
    bad = []
    tdir = os.path.join(root, 'templates')
    for dp, _, fns in os.walk(tdir):
        for fn in sorted(fns):
            if not fn.endswith('.html'):
                continue
            path = os.path.join(dp, fn)
            rel = os.path.relpath(path, root)
            src = strip_jinja_comments(
                io.open(path, encoding='utf-8', errors='replace').read())
            for m in STYLE_ATTR.finditer(src):
                body = m.group(1)
                # var(--x, #yedek) govdelerini SIL: oradaki hex mesru.
                probe = VAR_FALLBACK.sub(' ', body)
                for hm in HEX.finditer(probe):
                    h = hm.group(0).lower()
                    if h in ALLOW_HEX:
                        continue
                    ln = src[:m.start()].count('\n') + 1
                    why = ('tokens.css\'te AYNI hex tanimli -> KOPYA: token '
                           'degisirse burasi sessizce eski kalir'
                           if h in toks else
                           'tokens.css\'te HIC YOK -> palet disi uydurma renk')
                    bad.append((rel, ln, hm.group(0), why))
    return bad


def tree_at_ref(ref):
    d = tempfile.mkdtemp(prefix='inlinehex-')
    blob = subprocess.check_output(['git', 'archive', ref])
    tarfile.open(fileobj=__import__('io').BytesIO(blob)).extractall(d)
    return d


def main():
    ref = None
    if '--ref' in sys.argv:
        ref = sys.argv[sys.argv.index('--ref') + 1]
    root = (tree_at_ref(ref) if ref
            else os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    bad = scan(root)
    suffix = ' (ref %s)' % ref if ref else ''
    if not bad:
        print('K-BW OK — sablon satir-ici `style=` icinde ciplak renk yok%s.'
              % suffix)
        return 0
    print('K-BW KIRIK — %d ihlal%s:' % (len(bad), suffix))
    for rel, ln, h, why in bad:
        print('  %s:%d  `%s`  %s' % (rel, ln, h, why))
    print('\n  Kanon: satir-ici renk `var(--bp-x)` ya da `var(--bp-x, #yedek)`.')
    print('  Baska sirketin marka rengiyse tools/inline-style-hex-check.py')
    print('  ALLOW_HEX kumesine RENK olarak ekle (satir no olarak DEGIL).')
    return 1


if __name__ == '__main__':
    sys.exit(main())
