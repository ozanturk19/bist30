#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""K-AY kapisi — YAPISKAN CAPA KANONU (ust kabuk olcusu TEK KAYNAKTAN turer)

NEDEN VAR:
  Site her sayfada iki yapiskan bant tasiyor: makro serit (top:0, 32px) +
  header (top = makro seridin alti, 60px + inset). Ucuncu bir bant (yapiskan
  thead / .bp-segments) header'in ALTINA yapismak zorunda.

  21.09'a kadar bu olcu 13 AYRI YERDE ELLE yaziliydi ve UCU header'in KENDI
  safe-area payini saymiyordu: header `top:32px+inset` VE `min-height:
  60px+inset` tasir, yani alt kenari 92px DEGIL `92px + 2*inset`tir.
  Centikli bir telefonda (PWA/standalone, inset 30-59px) olculdu:
    /hisse  .bp-segments (top:92px sabit) -> header'in altinda 50-55px,
            yani sekme seridinin TAMAMI kayboluyordu
    /tarama, /karsilastir yapiskan thead  -> bir inset kadar ortuluydu
  Masaustunde inset=0 oldugu icin 20+ tur denetimden gorunmeden gecti.

KANON:
  Yapiskan/sabit bir ogenin `top` degeri ya SIFIRDIR, ya cikplak bir
  `env(safe-area-inset-top)`tur, ya da kanonik degiskenlerden biridir:
    var(--bp-anchor-macro)   = makro seridin alti  (sayfa header'lari)
    var(--bp-anchor-header)  = header'in alti      (thead, .bp-segments)
  Kabuk olcusunu (32/60/92/122...) ELLE yazan her `top` bir sapmadir --
  dogru sonuc versin ya da vermesin: kanonik kaynak degisince izlemez.

⛔ YORUMLAR SOYULUR: bir kapinin kodda degil ANLATIMDA arama yapmasi
   [[K-AX dersi]] sahte-pozitif uretir. CSS yorumlari once silinir.

Kullanim: python3 tools/sticky-anchor-check.py [--pozitif-kontrol]
"""
import os, re, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CSS_DIRS = ['static/css', 'static/css/pages']
TPL_DIR = 'templates'

IZINLI = re.compile(
    r'^(0|0px|auto|1px|-1px|'
    r'env\(safe-area-inset-top[^)]*\)|'
    r'calc\(\s*env\(safe-area-inset-top[^)]*\)\s*\)|'
    r'var\(--bp-anchor-macro\)|var\(--bp-anchor-header\)|var\(--bp-sticky-top\)|'
    r'var\(--bp-chrome-[a-z-]+\))$'
)
# Kabuk olcusunu elle tasiyan sayilar (px): 32 makro, 60 header, 92/122 toplam
KABUK_SAYI = re.compile(r'\b(3[0-4]|5[89]|6[0-2]|9[0-4]|12[0-4]|15[0-4])px\b')

def yorumsuz(s):
    return re.sub(r'/\*.*?\*/', ' ', s, flags=re.S)

def bloklar(css):
    """{...} bloklarini (selektor, govde) olarak dondurur."""
    for m in re.finditer(r'([^{}]+)\{([^{}]*)\}', css):
        yield m.group(1).strip().replace('\n', ' ')[-90:], m.group(2)

def tara(ekstra_css=None):
    sapmalar, olculen = [], 0
    kaynaklar = []
    for d in CSS_DIRS:
        p = os.path.join(ROOT, d)
        if not os.path.isdir(p): continue
        for f in sorted(os.listdir(p)):
            if f.endswith('.css'):
                kaynaklar.append((os.path.join(d, f), open(os.path.join(p, f), encoding='utf-8').read()))
    for f in sorted(os.listdir(os.path.join(ROOT, TPL_DIR))):
        if not f.endswith('.html'): continue
        raw = open(os.path.join(ROOT, TPL_DIR, f), encoding='utf-8').read()
        for st in re.findall(r'<style[^>]*>(.*?)</style>', raw, flags=re.S):
            kaynaklar.append((os.path.join(TPL_DIR, f), st))
    if ekstra_css:
        kaynaklar.append(('POZITIF-KONTROL', ekstra_css))

    for yol, ham in kaynaklar:
        css = yorumsuz(ham)
        for sel, govde in bloklar(css):
            if not re.search(r'position\s*:\s*(sticky|fixed)', govde): continue
            m = re.search(r'(?<![a-z-])top\s*:\s*([^;}\n]+)', govde)
            if not m: continue
            olculen += 1
            deger = m.group(1).strip().rstrip('!important').strip()
            if IZINLI.match(deger): continue
            if KABUK_SAYI.search(deger) or ('calc(' in deger and KABUK_SAYI.search(deger)):
                sapmalar.append((yol, sel, deger))
            elif re.fullmatch(r'-?\d+(\.\d+)?px', deger) and abs(float(deger[:-2])) >= 8:
                sapmalar.append((yol, sel, deger))
    return sapmalar, olculen

def main():
    sapmalar, olculen = tara()
    # POZITIF KONTROL: kapinin gercekten olctugunu kanitla.
    pk_css = ('.bp-pk-a{position:sticky;top:92px}'
              '.bp-pk-b{position:sticky;top:calc(32px + env(safe-area-inset-top,0px) + 60px)}'
              '.bp-pk-c{position:fixed;top:122px}')
    pk_sapma, _ = tara(pk_css)
    yakalanan = len([s for s in pk_sapma if s[0] == 'POZITIF-KONTROL'])
    print('sticky-anchor-check (K-AY yapiskan capa kanonu)')
    print(f'  olculen yapiskan `top` bildirimi: {olculen} · pozitif kontrol: {yakalanan}/3')
    if yakalanan != 3:
        print('  ✗ KAPI KOR: pozitif kontrolun 3 sahte sapmasindan '
              f'{yakalanan} tanesi yakalandi — dedektor olcmuyor.')
        return 2
    if sapmalar:
        print('K-AY KIRIK — kabuk olcusu elle yazilmis yapiskan capa:')
        for yol, sel, deger in sapmalar:
            print(f'  ✗ {yol}: {sel} -> top:{deger} (kanon: var(--bp-anchor-macro|header))')
        return 1
    print('  ✓ her yapiskan capa kanonik degiskenden turuyor')
    return 0

if __name__ == '__main__':
    sys.exit(main())
