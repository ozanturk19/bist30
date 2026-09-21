#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""K-AZ kapisi — GUVENLI ALAN (safe-area) KAPSAM KANONU

NEDEN VAR:
  Site `viewport-fit=cover` + `apple-mobile-web-app-status-bar-style:
  black-translucent` ile calisir: ana ekrana eklenmis PWA'da icerik
  centigin/durum cubugunun ve ev gostergesinin ALTINA cizilir. Bu alanlari
  `env(safe-area-inset-*)` ile ELDE ETMEK katmanin kendi sorumlulugudur.

  15.09'da env() KULLANIMLARI taranmisti (404/410/429/500 fix'i, 87048ee) --
  ama "env() eksik OLAN" katmanlar hic aranmamisti. Negatif iddia
  ("digerleri temiz") bu yuzden yanlisti. 21.09 K-AZ olcumu (Playwright,
  servis edilen CSS/JS'te env(...) -> 47px/34px ikame edilerek):
    · arama modali tam ekran mobil varyanti (`height:100vh`, `top:0`) ->
      arama kutusu VE ✕ kapat dugmesi %100 centigin altindaydi
    · /blog/* `.read-progress` (`top:0`, 3px) -> cubugun TAMAMI gorunmezdi
  Masaustunde ve mobil Safari'de inset = 0 oldugu icin ikisi de gorunmuyordu.

KANON (uc mekanik kural, insan hafizasina dayali muafiyet YOK):
  R1 `position:fixed` + UST kenara sabitlenmis + viewport'un TAMAMINI
     kaplamiyorsa -> `safe-area-inset-top` referansi ZORUNLU.
  R2 aynisi ALT kenar + `safe-area-inset-bottom`.
  R3 viewport YUKSEKLIGINE olculmus panel (`height`/`max-height`:100vh|100dvh)
     -> `safe-area-inset-top` referansi ZORUNLU. (Tam ekran bir panel,
     guvensiz bolgeyi kendisi oymak zorundadir -- kapsayici katmanin
     `inset:0` olmasi ICERIGI kurtarmaz; K-AZ'nin asil hatasi buydu.)
  Viewport'un TAMAMINI kaplayan sabit katman (inset:0 ya da top:0+bottom:0)
  R1/R2'den muaftir: tekduze bir ortu/perdedir, centik ustune denk gelmesi
  bilgi kaybettirmez. Bu muafiyet SELEKTOR ADINA degil GEOMETRIYE bakar.

⛔ Yorumlar soyulur (K-AX dersi: kapi ANLATIMIN icinde arayabilir).

Kullanim: python3 tools/safearea-layer-check.py
"""
import os, re, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CSS_DIRS = ['static/css', 'static/css/pages']
JS_FILES = ['static/bp-search.js', 'static/stale-banner.js', 'static/learning-mode.js']

def yorumsuz(s):
    return re.sub(r'/\*.*?\*/', ' ', s, flags=re.S)

def kaynaklar():
    out = []
    for d in CSS_DIRS:
        p = os.path.join(ROOT, d)
        if not os.path.isdir(p): continue
        for f in sorted(os.listdir(p)):
            if f.endswith('.css'):
                out.append((f'{d}/{f}', open(os.path.join(p, f), encoding='utf-8').read()))
    tdir = os.path.join(ROOT, 'templates')
    for f in sorted(os.listdir(tdir)):
        if f.endswith('.html'):
            raw = open(os.path.join(tdir, f), encoding='utf-8').read()
            for st in re.findall(r'<style[^>]*>(.*?)</style>', raw, flags=re.S):
                out.append((f'templates/{f}', st))
    for f in JS_FILES:
        p = os.path.join(ROOT, f)
        if os.path.exists(p):
            out.append((f, open(p, encoding='utf-8').read()))
    return out

SIFIR = r'0(px)?'

def incele(kaynak_listesi):
    sapmalar, olculen = [], 0
    for yol, ham in kaynak_listesi:
        css = yorumsuz(ham)
        for m in re.finditer(r'([^{}]+)\{([^{}]*)\}', css):
            sel = m.group(1).strip().replace('\n', ' ')[-70:]
            g = m.group(2)
            fixed = re.search(r'position\s*:\s*fixed', g)
            inset0 = re.search(r'(?<![a-z-])inset\s*:\s*' + SIFIR + r'\s*(;|$|!)', g)
            top0 = re.search(r'(?<![a-z-])top\s*:\s*' + SIFIR + r'\s*(;|$|!)', g) or inset0
            bot0 = re.search(r'(?<![a-z-])bottom\s*:\s*' + SIFIR + r'\s*(;|$|!)', g) or inset0
            tamekran = bool(inset0) or bool(top0 and bot0)
            vh_panel = re.search(r'(?<![a-z-])(max-)?height\s*:\s*100(d|l|s)?vh', g)
            has_t = 'safe-area-inset-top' in g
            has_b = 'safe-area-inset-bottom' in g
            if fixed and (top0 or bot0):
                olculen += 1
                if top0 and not tamekran and not has_t:
                    sapmalar.append((yol, sel, 'R1 ust kenara sabit, safe-area-inset-top YOK'))
                if bot0 and not tamekran and not has_b:
                    sapmalar.append((yol, sel, 'R2 alt kenara sabit, safe-area-inset-bottom YOK'))
            if vh_panel:
                olculen += 1
                if not has_t:
                    sapmalar.append((yol, sel, 'R3 viewport yuksekligine olculmus panel, safe-area-inset-top YOK'))
    return sapmalar, olculen

def main():
    src = kaynaklar()
    sapmalar, olculen = incele(src)
    pk = ('.bp-pk-1{position:fixed;top:0;left:0;height:3px}'
          '.bp-pk-2{position:fixed;bottom:0;left:0;height:40px}'
          '.bp-pk-3{position:fixed;top:0;height:100dvh;max-height:100dvh}')
    pk_sapma, _ = incele(src + [('POZITIF-KONTROL', pk)])
    # Ayni sahte kural birden fazla kurali tetikleyebilir -> SELEKTOR bazinda say.
    yakalanan = len({s[1] for s in pk_sapma if s[0] == 'POZITIF-KONTROL'})
    print('safearea-layer-check (K-AZ guvenli alan kapsam kanonu)')
    print(f'  olculen sabit/tam-ekran katman bildirimi: {olculen} · pozitif kontrol: {yakalanan}/3')
    if yakalanan != 3:
        print(f'  ✗ KAPI KOR: pozitif kontrolun 3 sahte sapmasindan {yakalanan} yakalandi.')
        return 2
    if sapmalar:
        print('K-AZ KIRIK — centik/ev gostergesi altinda kalan katman:')
        for yol, sel, neden in sapmalar:
            print(f'  ✗ {yol}: {sel} -> {neden}')
        return 1
    print('  ✓ ust/alt kenara sabitlenen ve tam-ekran her katman guvenli alani oyuyor')
    return 0

if __name__ == '__main__':
    sys.exit(main())
