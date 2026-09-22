#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""tools/template-color-channel-check.py — K-BY: SABLONDA **HANGI KANALDAN
OLURSA OLSUN** PALET DISI RENK.

NEDEN BU KAPI (22.09.2026):
  Sitede rengi denetleyen UC kapi vardi ve her biri BIR KANALI taniyordu:
    * style-guard            -> static/css/*.css govdesi
    * js-palette-check       -> .js dosyalari + sablonlarin <script> bloklari
    * inline-style-hex-check -> sablonlarin satir-ici `style="..."` metni
  K-BY olcumu: `templates/hisse.html` hero karti rengi BUNLARIN HICBIRINDE
  degildi. Once bir Jinja degiskenine yaziliyordu:
        {% set _hc='#16a34a' %}
  ve ancak 40 satir asagida `style="--hero-accent:{{ _hc }}"` ile
  enterpole ediliyordu. Kapi 42 `style=` govdesine bakar, orada sadece
  `{{ _hc }}` gorur. DORDUNCU kanal.
  Canli olculdu: 217 hisse sayfasinin **79'u** boyle bir hex ile
  boyaniyordu; ayni kartin ROZETI bir onceki turda (K-BW, #ff7875)
  duzeltilmisti -- iki satir yukarisi hayatta kaldi.
  BESINCI kanal ayni turda cikti: `templates/index.html` hero-art'inda
  SVG SUNUM OZNITELIKLERI (`fill="#ff37d8"`, `stop-color="#1fe0ff"`).
  Ayni SVG'nin 3 dairesi zaten `fill="var(--bp-art-violet)"` idi.

⛔ 52. DERS (K-BW): kapi, hatanin OGRENDIGI yazimini degil HATANIN KENDISINI
  aramalidir. Bu yuzden burada kanal SAYMIYORUZ. Kural tek ve yapisal:

KANON: bir sablon dosyasinda -- yorumlar cikarildiktan sonra -- gecen HER
  renk hex'i ya tokens.css'te TANIMLI olmalidir ya da hic olmamalidir.
  Kanal (style= / {% set %} / fill= / <script> / duz metin) FARK ETMEZ.

YAPISAL MUAFIYETLER (beyaz liste DEGIL -- ⛔ bkz. c952a78):
  1. AKROMATIK (r==g==b): #fff / #000 / #2a2a2c gibi notrler palet KIMLIGI
     tasimaz; yapisal tonlardir (hairline, golge, katman zemini).
  2. ALLOW_HEX: baska bir sirketin MARKA rengi. Bizim paletimizin parcasi
     degildir, token'i da olmaz (#25D366 = WhatsApp).
  3. Yorumlar: {# #}, <!-- -->, /* */ tamamen silinir -- bir turun NE'sini
     anlatan yorum, o rengi URETMEZ.

KAPSAM DISI (bilerek) — tokens.css'te TANIMLI bir degerin YEDEK olarak
  yazilmasi: `var(--bp-border,#2a2a2c)`, `_tok('--bp-al','#00e290')`,
  `BPChart.tok('--bp-chart-crosshair','#3d5a80')`, `<meta name="theme-color">`.
  Bu kalip K-BG'de BILEREK kuruldu (token tek kaynak, hex yalniz token
  okunamazsa devreye girer) ve olcum sirasinda 17 mesru ornegi sayildi.
  Bu kapi TEK bir seyi arar: **paletin disindan uydurulmus** renk. Token
  degerinin elle kopyalanip SURUKLENMESI ayri bir eksendir; onu style-guard
  ve js-palette-check kendi alanlarinda kovalar.

Kullanim:
  python3 tools/template-color-channel-check.py
  python3 tools/template-color-channel-check.py --ref SHA   # pozitif kontrol
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

# 3 / 6 / 8 haneli hex. `&#8217;` gibi HTML varliklarini disla ((?<!&)).
HEX = re.compile(r'(?<![&\w])#(?:[0-9a-fA-F]{8}|[0-9a-fA-F]{6}|[0-9a-fA-F]{3})\b')


def strip_comments(s):
    """Yorumlari SATIR SAYISINI KORUYARAK sil (satir no dogru kalsin)."""
    def blank(m):
        return ''.join('\n' if c == '\n' else ' ' for c in m.group(0))
    s = re.sub(r'\{#.*?#\}', blank, s, flags=re.S)     # Jinja
    s = re.sub(r'<!--.*?-->', blank, s, flags=re.S)    # HTML
    s = re.sub(r'/\*.*?\*/', blank, s, flags=re.S)     # CSS/JS blok
    return s


def is_achromatic(h):
    """r == g == b  ->  palet kimligi tasimayan notr ton."""
    v = h.lstrip('#')
    if len(v) == 3:
        v = ''.join(c * 2 for c in v)
    if len(v) == 8:          # #rrggbbaa -> alfa'yi at
        v = v[:6]
    if len(v) != 6:
        return False
    r, g, b = (int(v[i:i + 2], 16) for i in (0, 2, 4))
    return r == g == b


def token_hexes(root):
    p = os.path.join(root, 'static', 'css', 'tokens.css')
    try:
        src = io.open(p, encoding='utf-8', errors='replace').read()
    except OSError:
        return set()
    # tokens.css'in KENDI yorumlari ornek hex icerebilir -> onlari sayma.
    return {m.group(0).lower() for m in HEX.finditer(strip_comments(src))}


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
            src = strip_comments(
                io.open(path, encoding='utf-8', errors='replace').read())
            for m in HEX.finditer(src):
                h = m.group(0).lower()
                if h in ALLOW_HEX or is_achromatic(h) or h in toks:
                    continue
                ln = src[:m.start()].count('\n') + 1
                bad.append((rel, ln, m.group(0),
                            'tokens.css\'te HIC YOK -> palet disi uydurma renk'))
    return bad


def tree_at_ref(ref):
    d = tempfile.mkdtemp(prefix='tplcolor-')
    blob = subprocess.check_output(['git', 'archive', ref])
    tarfile.open(fileobj=io.BytesIO(blob)).extractall(d)
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
        print('K-BY OK — sablonlarda palet disi renk kanali yok%s.' % suffix)
        return 0
    print('K-BY KIRIK — %d ihlal%s:' % (len(bad), suffix))
    for rel, ln, h, why in bad:
        print('  %s:%d  `%s`  %s' % (rel, ln, h, why))
    print('\n  Kanon: renk YALNIZ tokens.css\'ten gelir -- kanal fark etmez')
    print('  (style= / {%% set %%} / fill= / stop-color= / <script>).')
    print('  Notr (r==g==b) ve baska sirket markasi muaftir; marka rengini')
    print('  tools/template-color-channel-check.py ALLOW_HEX kumesine RENK')
    print('  olarak ekle (satir no olarak DEGIL).')
    return 1


if __name__ == '__main__':
    sys.exit(main())
