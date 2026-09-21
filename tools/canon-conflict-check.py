#!/usr/bin/env python3
"""K-AP — KANONIK TEK KAYNAK ile SAYFA-YEREL KOPYANIN CATISMASI (CPO, 21.09.2026).

NEDEN AYRI BIR KAPI:
  Bu boyut, ayni turda iki gercek kusuru ortaya cikardi ve ikisi de mevcut
  13 kapinin HICBIRINE gorunmuyordu -- cunku her kapi bir dosyanin ICINE
  bakiyor, bu ise IKI dosyanin AYNI SECICI uzerindeki anlasmazligi:

  1) `.header-search-btn` sinir rengi. K-Y (21.09) tam bu dugmeyi olcup
     `--bp-ctl-border`i (3,83:1) yaratmisti; fix `bp-search.js`in enjekte
     ettigi stile uygulandi ama `_bp_critical_css.html` + `pages/hisse.css`
     + `pages/ozet.css` eski `--bp-border`da (1,34:1) kaldi. JS `defer`
     yuklendigi icin ilk boyada -- ve JS duserse KALICI olarak -- eski
     deger goruluyordu.
  2) `/temettu-takvimi` `body{font-family}`. Sayfa CSS'i kanonik
     `'Space Grotesk','Manrope'` yerine `'Inter','Segoe UI'` yaziyordu:
     21 sayfanin 20'si bir yazi tipinde, o TEK BASINA baskasinda.

OLCUT (taban SIFIR):
  KANONIK katman = `static/css/tokens.css` + `static/css/data-art.css` +
  `templates/_bp_critical_css.html` (satir ici, ama pages/*.css'ten ONCE).
  EZEN katman  = `static/css/pages/*.css` + sablon ici <style> (kritik blok
  haric) -- ikisi de kanonigin ALTINDA yuklenir, yani esit ozgullukte
  KAZANIRLAR.
  Ayni secici + ayni ozellik + FARKLI deger => catisma.

KAPSAM SINIRI (bilerek):
  - `--*` ozel ozellikleri haric (bir sayfanin yerel token'i kasitli bir
    tema deltasidir, cakisma degil).
  - Degerler bosluk-normalize edilir: `rect(0, 0, 0, 0)` ile `rect(0,0,0,0)`
    ayni degerdir, bulgu degildir.
  - Kasitli delta OLABILIR: bu kapi "yanlis" demiyor, "iki kaynak ayni sey
    hakkinda FARKLI konusuyor" diyor. Kasitli olan GOZDEN_GECIRILMIS'e
    GEREKCESIYLE eklenir -- boylece bir daha sessizce surüklenemez.
"""
import re
import sys
import pathlib
from collections import defaultdict

ROOT = pathlib.Path(__file__).resolve().parent.parent

# (secici, ozellik) -> gerekce. Kasitli, gozden gecirilmis deltalar.
GOZDEN_GECIRILMIS = {}


def _rules(css, src):
    css = re.sub(r'/\*.*?\*/', '', css, flags=re.S)
    out = []

    def walk(txt, media=''):
        i, buf = 0, ''
        while i < len(txt):
            c = txt[i]
            if c == '{':
                sel = ' '.join(buf.split())
                buf = ''
                d, j = 1, i + 1
                while j < len(txt) and d:
                    if txt[j] == '{':
                        d += 1
                    elif txt[j] == '}':
                        d -= 1
                    j += 1
                body = txt[i + 1:j - 1]
                if sel.startswith('@'):
                    if sel.startswith('@media') or sel.startswith('@supports'):
                        walk(body, media + sel + ' ')
                else:
                    decls = {}
                    for part in re.split(r';(?![^()]*\))', body):
                        if ':' in part:
                            k, v = part.split(':', 1)
                            k = k.strip().lower()
                            if k and not k.startswith('--'):
                                v = ' '.join(v.split()).rstrip('!important').strip()
                                decls[k] = re.sub(r'\s*,\s*', ',', v)
                    for s in sel.split(','):
                        out.append((media + ' '.join(s.split()), decls, src))
                i = j
            elif c == '}':
                buf = ''
                i += 1
            else:
                buf += c
                i += 1

    walk(css)
    return out


def main():
    canon = []
    for rel in ('static/css/tokens.css', 'static/css/data-art.css'):
        canon += _rules((ROOT / rel).read_text(encoding='utf-8'), rel)
    crit = (ROOT / 'templates/_bp_critical_css.html').read_text(encoding='utf-8')
    crit = re.sub(r'\{#-.*?-#\}', '', crit, flags=re.S)
    canon += _rules(crit, 'templates/_bp_critical_css.html')

    canon_map = defaultdict(dict)
    for sel, decls, src in canon:
        for k, v in decls.items():
            canon_map[sel][k] = (v, src)

    over = []
    for f in sorted((ROOT / 'static/css/pages').glob('*.css')):
        over += _rules(f.read_text(encoding='utf-8'), 'static/css/pages/' + f.name)
    for f in sorted((ROOT / 'templates').glob('*.html')):
        html = f.read_text(encoding='utf-8')
        for m in re.finditer(r'<style([^>]*)>(.*?)</style>', html, re.S):
            if 'bp-critical-css' in m.group(1):
                continue
            body = re.sub(r'\{[{%#].*?[}%#]\}', '', m.group(2), flags=re.S)
            over += _rules(body, 'templates/' + f.name)

    hits = defaultdict(list)
    skipped = 0
    for sel, decls, src in over:
        if sel not in canon_map:
            continue
        for k, v in decls.items():
            if k not in canon_map[sel]:
                continue
            cv, csrc = canon_map[sel][k]
            if v == cv:
                continue
            if (sel, k) in GOZDEN_GECIRILMIS:
                skipped += 1
                continue
            hits[(sel, k)].append((src, v, cv, csrc))

    print('canon-conflict-check (K-AP: kanonik kaynak <-> sayfa-yerel kopya)')
    print(f'  kanonik kural: {len(canon_map)} secici · ezen katman: {len(over)} kural')
    if skipped:
        print(f'  gozden gecirilmis-kasitli: {skipped}')
    if not hits:
        print('  ✓ catisma YOK')
        return 0
    n = sum(len(v) for v in hits.values())
    print(f'\n  ✗ K-AP KIRIK — {n} catisan bildirim ({len(hits)} secici/ozellik cifti):')
    for (sel, k), lst in sorted(hits.items()):
        print(f'\n    {sel}  ::  {k}')
        print(f'      KANONIK ({lst[0][3]}): {lst[0][2]}')
        for src, v, cv, csrc in lst:
            print(f'      EZEN    {src}: {v}')
    print('\n  Cozum: sayfa-yerel kopyayi kanonige esitle, ya da delta KASITLIYSA'
          '\n  GOZDEN_GECIRILMIS sozlugune GEREKCESIYLE ekle.')
    return 1


if __name__ == '__main__':
    sys.exit(main())
