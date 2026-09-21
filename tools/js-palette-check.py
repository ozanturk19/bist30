#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""tools/js-palette-check.py — K-BG: JS ICINDEKI PALET TOKENS.CSS'E BAGLI MI?

SORU: `style-guard` YALNIZ `static/css/*.css` bakar. Peki grafikleri boyayan
renkler nerede yaziyor?

OLCULDU (21.09.2026): `static/js/bp-chart-common.js` grafik paletini HAM HEX
yaziyordu -- ve bu dosya 20.09 palet gocunun tamamen DISINDA kalmisti:

  #141416 #c7c5cd #b8c3ff #2a2a2c #f85149 #00e290 #e3b341 -> tokens.css'te
      KARSILIGI VAR ama kopyalanmis: tokens degisirse grafik sessizce eski kalir
  #21262d (izgara) -> aslinda `--bp-border-subtle`, farkinda olunmadan kopya
  #3d5a80 (crosshair) -> tokens.css'te HIC YOKTU, Data-Art oncesi paletten
      sag kalan tek renk; bp-chart-common.js ve hisse.html'de BAGIMSIZ yaziliydi

⛔ AYNI DOSYADA IKI KANON: bu dosya `_tok()` yardimcisini ZATEN tasiyordu ve
   `addEmaPair` 20.09'da token'a gecmisti; `baseOpts` ve `addCandleSeries` ham
   hex'te kalmisti. Yani dogru kanon dosyanin kendi icinde, 100 satir asagida
   duruyordu.

KANON: kullaniciya gorunen bir rengi JS'te yazan her yer onu tokens.css'ten
okumalidir -- `_tok('--bp-x', '<yedek hex>')` / `BPChart.tok(...)`. Ham hex
YALNIZ bu cagrinin yedek argumaninda gecebilir (token cozulmezse literale
dusmek dogru davranistir; uydurmamak icin yedek SART).

KAPSAM: static/js/*.js + static/*.js (ucuncu-parti minify dosyalar HARIC) ve
sablonlarin satir-ici betikleri. CSS dosyalari style-guard'in isidir.

⚠️ RATCHET (TAVAN), SIFIR DEGIL -- VE BU GECICIDIR.
   Ilk olcumde 86 ihlal cikti: grafik dosyasi yalnizca gorunen kismidi, JS
   katmaninin TAMAMI palet sisteminin disindaydi (bp-search 48, hisse.html 11,
   learning-mode 12, _analytics 8, stale-banner 4, tooltip/toast 3).
   86 cagri yerini tek seferde tasimak, dogrulanamayacak kadar buyuk bir
   degisiklik olurdu; o yuzden style-guard'in K-B kontrolunde zaten kullanilan
   desen uygulandi: DOSYA BASINA TAVAN, kural "ARTAMAZ".
   Bugun tam gocen dosyalarin tavani 0'dir ve 0 kalmalidir.
   HEDEF SIFIR: her tur birkac dosya indirilip taban `--baseline` ile
   sikistirilmali. Tavan bir hedef DEGIL, yalnizca kanamanin durdurulmasidir.
"""
import glob
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT)

# ucuncu parti / uretilmis dosyalar
HARIC = ('lightweight-charts.min.js',)
RATCHET = os.path.join('tools', 'js_palette_ratchet.json')

HEX_RE = re.compile(r'#[0-9a-fA-F]{6}\b|#[0-9a-fA-F]{3}\b')
# `_tok('--x', '#hex')` / `BPChart.tok("--x", "#hex")` -> yedek argumani MUAF
TOK_RE = re.compile(r'\b(?:_tok|BPChart\s*\.\s*tok)\s*\(\s*[\'"]--[\w-]+[\'"]\s*,\s*[\'"][^\'"]*[\'"]\s*\)')
SCRIPT_RE = re.compile(r'<script\b(?![^>]*\bsrc=)[^>]*>(.*?)</script>', re.S | re.I)


def strip_comments(src):
    out = []
    i, n = 0, len(src)
    while i < n:
        c = src[i]
        if c in '"\'`':
            q = c
            out.append(c)
            i += 1
            while i < n:
                if src[i] == '\\' and i + 1 < n:
                    out.append('  ')
                    i += 2
                    continue
                out.append('\n' if src[i] == '\n' else src[i])
                if src[i] == q:
                    i += 1
                    break
                i += 1
            continue
        if c == '/' and i + 1 < n and src[i + 1] == '/':
            while i < n and src[i] != '\n':
                out.append(' ')
                i += 1
            continue
        if c == '/' and i + 1 < n and src[i + 1] == '*':
            while i < n and not (src[i] == '*' and i + 1 < n and src[i + 1] == '/'):
                out.append('\n' if src[i] == '\n' else ' ')
                i += 1
            out.append('  ')
            i += 2
            continue
        out.append(c)
        i += 1
    return ''.join(out)


def scan_js(path, src, base_line=1):
    """Yorumlar soyulur; _tok(...) yedek argumanlari MASKELENIR; kalan hex ihlaldir."""
    clean = strip_comments(src)
    # tok cagrilarini ayni uzunlukta bosluga cevir (satir/sutun kaymasin)
    clean = TOK_RE.sub(lambda m: ' ' * len(m.group(0)), clean)
    hits = []
    for m in HEX_RE.finditer(clean):
        line = base_line + clean[:m.start()].count('\n')
        hits.append((path, line, m.group(0)))
    return hits


def scan_file(rel):
    src = open(rel, encoding='utf-8').read()
    if rel.endswith('.js'):
        return scan_js(rel, src)
    hits = []
    for m in SCRIPT_RE.finditer(src):
        base = src[:m.start(1)].count('\n') + 1
        hits.extend(scan_js(rel, m.group(1), base))
    return hits


def targets():
    out = []
    for pat in ('static/*.js', 'static/js/*.js', 'templates/*.html'):
        for p in sorted(glob.glob(pat)):
            if os.path.basename(p) in HARIC:
                continue
            out.append(p)
    return out


def main():
    files = targets()
    if not files:
        print('K-BG OLCULEMEDI: taranacak dosya yok.')
        return 2

    sayim = {}
    ornek = {}
    for rel in files:
        h = scan_file(rel)
        if h:
            sayim[rel] = len(h)
            ornek[rel] = h[:3]

    # POZITIF KONTROL
    pos = scan_js('__probe__.js', "var c = { color: '#ff00aa' };")
    # NEGATIF KONTROL — muaf desenler bulgu URETMEMELI
    neg_probes = [
        ("_tok yedek argumani", "var c = _tok('--bp-al', '#00e290');"),
        ("BPChart.tok yedek", 'var c = BPChart.tok("--bp-brand", "#b8c3ff");'),
        ("yorum icinde hex", "/* eskiden #58a6ff idi */ var c = _tok('--bp-brand', '#b8c3ff');"),
    ]
    neg_ok = 0
    for ad, probe in neg_probes:
        if not scan_js('__probe__.js', probe):
            neg_ok += 1
        else:
            print('  ! NEGATIF KONTROL DUSTU: %s' % ad)
    if not pos:
        print('  ! POZITIF KONTROL DUSTU: duz ham hex yakalanamadi')

    if '--baseline' in sys.argv:
        with open(RATCHET, 'w', encoding='utf-8') as fh:
            json.dump(sayim, fh, indent=2, sort_keys=True, ensure_ascii=False)
            fh.write('\n')
        print('js-palette-check: taban yazildi -> %s (%d dosya, %d ihlal)'
              % (RATCHET, len(sayim), sum(sayim.values())))
        return 0

    print('js-palette-check (K-BG: JS paleti <-> tokens.css) — RATCHET')
    print('  taranan dosya: %d (haric: %s)' % (len(files), ', '.join(HARIC)))
    print('  pozitif kontrol: %d/1 · negatif kontrol: %d/%d'
          % (1 if pos else 0, neg_ok, len(neg_probes)))

    if not pos or neg_ok != len(neg_probes):
        print('K-BG OLCULEMEDI — dedektor kendi kontrolunu gecemedi (sonuc "temiz" DEGIL).')
        return 2

    if not os.path.exists(RATCHET):
        print('K-BG OLCULEMEDI: taban dosyasi yok (%s). `--baseline` ile olustur.' % RATCHET)
        return 2
    with open(RATCHET, encoding='utf-8') as fh:
        taban = json.load(fh)

    print('  toplam ham renk: %d (taban toplami: %d) · hedef SIFIR'
          % (sum(sayim.values()), sum(taban.values())))

    artan = []
    for rel, n in sorted(sayim.items()):
        t = taban.get(rel, 0)
        if n > t:
            artan.append((rel, t, n, ornek[rel]))
    dusen = [(rel, taban[rel], sayim.get(rel, 0))
             for rel in sorted(taban) if sayim.get(rel, 0) < taban[rel]]

    if artan:
        print('K-BG IHLAL — ham renk ARTTI (tavan asildi):')
        for rel, t, n, orn in artan:
            print('  %s: taban %d -> simdi %d' % (rel, t, n))
            for _p, line, hexv in orn:
                print('      %s:%d  %s' % (rel, line, hexv))
        print("  DUZELTME: _tok('--bp-x', '<yedek hex>') / BPChart.tok(...) kullan.")
        return 1

    if dusen:
        print('  ↓ IYILESME (taban sikistirilmali: python3 tools/js-palette-check.py --baseline):')
        for rel, t, n in dusen:
            print('      %s: %d -> %d' % (rel, t, n))

    print('  ✓ hicbir dosyada ham renk artmadi')
    return 0


if __name__ == '__main__':
    sys.exit(main())
