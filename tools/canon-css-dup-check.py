#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""tools/canon-css-dup-check.py -- K-CY (KAPI 70):
KANONIK CSS BLOGUNUN SAHIBI OLDUGU SECICIYI JS ENJEKTE ETTIGI CSS YENIDEN BOYAYAMAZ.

OLCULDU (22.09.2026, canli /tarama + /portfolio):
  `templates/_bp_critical_css.html` ust navigasyonun KANONIK kaynagi oldugunu
  YAZIYORDU (kendi yorumunda "simdi tum sayfalarda var" diyordu) ve kural
  gercekten 20 sayfanin hepsine YUKLENIYORDU -- ama HICBIRINDE GORUNMUYORDU:
  `static/bp-search.js` ayni nav stilinin ham-hex'li ikinci kopyasini runtime'da
  <head>'in SONUNA enjekte ediyordu. Ozgulluk esit
  (`.bp-nav-item.active` = `.bp-nav-item[aria-current="page"]` = 0,2,1), kaynak
  sirasi JS'i sonra koyuyor -> JS kazaniyordu.

  Canli computed: color/background = `--bp-al` (AL SINYALI YESILI), border-color
  = `--bp-brand`, transform = none. Yani TEK OGE IKI RENK SOZLUGUNDEN boyaniyor,
  kanonigin Data-Art hapi (pill + rotate(-1deg)) hic render edilmiyordu.
  Ustelik DURUM ANAHTARI da ikilesmisti: kanonik `[aria-current="page"]`,
  kopya `.active` -- ayni sey icin iki anahtar, iki sozluk.

NEDEN MEVCUT KAPILAR GOREMEDI:
  - `style-guard` / `css-token-guard` YALNIZ `static/css/*.css` okur; bu CSS bir
    JS string'i icinde yasiyor.
  - `js-palette-check` (K-BG) ham hex SAYAR ama tavanli ratchet'tir ve "bu renk
    yanlis ANLAM tasiyor" ya da "bu kural baskasinin kuralini eziyor" demez.
  - `da-override-check` sablon->sablon bakar, JS kanalini gormez.
  => 74. ders: yeni bir KANAL her zaman yeni bir kor nokta demektir.

KURAL (iki bagimsiz ihlal sinifi):
  A) SAHIPLIK: kanonik blogun tanimladigi bir secici icin, JS'ten enjekte edilen
     CSS KIMLIK tasiyan bir ozellik (renk/zemin/kenarlik/yaricap/golge/donusum/
     font-agirligi/font-ailesi/metin-donusumu) BILDIREMEZ.
     @media icindeki GEOMETRI rafinasyonu (padding/gap/font-size/letter-spacing)
     mesrudur ve ihlal SAYILMAZ -- kapi yazimi degil kusuru arar (52. ders).
  B) DURUM ANAHTARI: kanonik blok bir tabani `S` bir durumla (ornegin
     `[aria-current="page"]`) boyuyorsa, JS ayni `S` tabanini BASKA bir durum
     anahtariyla (`.active`, `.current`, `[data-active]`, ...) boyayamaz.
     Iki anahtar = iki kanon.

KAPSAM: static/*.js + static/js/*.js (ucuncu-parti minify HARIC).
SIFIR IHLAL sarti -- tavan/ratchet YOK (bu sinif tek seferde kapatilabilir
buyuklukte olculdu: tek dosya, tek blok).

Pozitif kontrol:  python3 tools/canon-css-dup-check.py --ref b4b8bcf
  (K-CY oncesi agacta A ve B siniflarindan ihlal DUSMELI.)
"""
import os, re, subprocess, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CANON = 'templates/_bp_critical_css.html'
THIRD_PARTY = ('lightweight-charts.min.js',)

IDENTITY_PROPS = (
    'color', 'background', 'background-color', 'border', 'border-color',
    'border-radius', 'box-shadow', 'transform', 'font-weight', 'font-family',
    'text-transform',
)
STATE_KEYS = ('[aria-current="page"]', "[aria-current='page']", '.active',
              '.current', '[data-active]', '[data-current]', '.is-active',
              '.selected')

RULE_RE = re.compile(r'([^{}]+)\{([^{}]*)\}')


def _norm(sel):
    return re.sub(r'\s+', ' ', sel).strip().replace('"', "'")


def _split_state(sel):
    """`.bp-nav-item[aria-current='page']` -> ('.bp-nav-item', "[aria-current='page']")"""
    for k in STATE_KEYS:
        kk = k.replace('"', "'")
        if sel.endswith(kk) and len(sel) > len(kk):
            return sel[:-len(kk)], kk
    return sel, None


def _strip_media(css):
    """@media bloklarini isaretli dondur: (govde, media_ici_mi)."""
    out = []
    i = 0
    while i < len(css):
        m = re.search(r'@media[^{]*\{', css[i:])
        if not m:
            out.append((css[i:], False))
            break
        out.append((css[i:i + m.start()], False))
        j = i + m.end()
        depth = 1
        k = j
        while k < len(css) and depth:
            if css[k] == '{':
                depth += 1
            elif css[k] == '}':
                depth -= 1
            k += 1
        out.append((css[j:k - 1], True))
        i = k
    return out


def canon_selectors(text):
    """Kanonik sablondan {secici: set(ozellik)} cikar."""
    css = re.sub(r'\{#.*?#\}', '', text, flags=re.S)
    css = re.sub(r'/\*.*?\*/', '', css, flags=re.S)
    owned = {}
    for body, _ in _strip_media(css):
        for sel, decls in RULE_RE.findall(body):
            if '@' in sel:
                continue
            props = {d.split(':', 1)[0].strip().lower()
                     for d in decls.split(';') if ':' in d}
            for one in sel.split(','):
                one = _norm(one)
                if one:
                    owned.setdefault(one, set()).update(props)
    return owned


def js_rules(text):
    """JS icindeki CSS string literallerinden (secici, ozellikler, media_ici) uret."""
    text = re.sub(r'/\*.*?\*/', '', text, flags=re.S)
    out = []
    for lit in re.findall(r"'((?:[^'\\]|\\.)*)'|\"((?:[^\"\\]|\\.)*)\"", text):
        s = lit[0] or lit[1]
        if '{' not in s or '}' not in s or ':' not in s:
            continue
        for body, in_media in _strip_media(s):
            for sel, decls in RULE_RE.findall(body):
                if '@' in sel or not sel.strip():
                    continue
                props = {d.split(':', 1)[0].strip().lower()
                         for d in decls.split(';') if ':' in d}
                for one in sel.split(','):
                    one = _norm(one)
                    if one:
                        out.append((one, props, in_media))
    return out


def read(path, ref=None):
    if ref:
        try:
            return subprocess.check_output(
                ['git', 'show', '%s:%s' % (ref, path)], cwd=ROOT).decode('utf-8', 'replace')
        except subprocess.CalledProcessError:
            return ''
    full = os.path.join(ROOT, path)
    if not os.path.exists(full):
        return ''
    with open(full, encoding='utf-8') as f:
        return f.read()


def js_files(ref=None):
    if ref:
        names = subprocess.check_output(
            ['git', 'ls-tree', '-r', '--name-only', ref], cwd=ROOT).decode().split('\n')
    else:
        names = []
        for d in ('static', 'static/js'):
            p = os.path.join(ROOT, d)
            if os.path.isdir(p):
                names += [os.path.join(d, n) for n in os.listdir(p)]
    return sorted(n for n in names
                  if n.endswith('.js')
                  and (n.startswith('static/') and n.count('/') <= 2)
                  and not n.endswith(THIRD_PARTY))


def main():
    ref = None
    if '--ref' in sys.argv:
        ref = sys.argv[sys.argv.index('--ref') + 1]
    verbose = '--verbose' in sys.argv or ref is not None

    owned = canon_selectors(read(CANON, ref))
    if not owned:
        print('canon-css-dup-check: KANONIK BLOK OKUNAMADI (%s)' % CANON)
        return 1

    owned_bases = {}
    for sel in owned:
        base, state = _split_state(sel)
        if state:
            owned_bases.setdefault(base, set()).add(state)

    viol = []
    for f in js_files(ref):
        for sel, props, in_media in js_rules(read(f, ref)):
            if sel in owned:
                # Yalnizca KANONIGIN DE bildirdigi kimlik ozelligi cakismadir:
                # kanonik `display:none` tutup JS'in gorunumu tamamladigi yerler
                # (arama katmani, acilir menu govdesi) IKI KANON DEGIL, is bolumudur.
                hit = sorted(p for p in props
                             if p in IDENTITY_PROPS and p in owned[sel])
                if hit:
                    viol.append(('A', f, sel, ', '.join(hit)))
            base, state = _split_state(sel)
            if state and base in owned_bases and state not in owned_bases[base]:
                viol.append(('B', f, sel,
                             'kanonik anahtar: %s' % ' / '.join(sorted(owned_bases[base]))))

    seen, uniq = set(), []
    for v in viol:
        if v not in seen:
            seen.add(v)
            uniq.append(v)

    if uniq:
        print('canon-css-dup-check: %d ihlal' % len(uniq))
        for cls, f, sel, detail in uniq:
            print('  [%s] %s  ->  %s   (%s)' % (cls, f, sel, detail))
        print('  A = kanonik secicinin kimlik ozelligi JS\'ten yeniden bildirilmis')
        print('  B = ayni taban icin IKINCI durum anahtari')
        return 1
    if verbose:
        print('canon-css-dup-check: 0 ihlal (%d kanonik secici tarandi)' % len(owned))
    return 0


if __name__ == '__main__':
    sys.exit(main())
