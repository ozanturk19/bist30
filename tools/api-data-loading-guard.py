#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
K-BK kapisi (pre-deploy 30 -> 31) — `/api/data` TUKETICISI, BOS LISTEYI
"VERI YOK" DIYE SUNMADAN ONCE `loading` BAYRAGINI OKUMALI.

NEDEN VAR (21.09, K-BK turunda CANLI olculdu)
---------------------------------------------
`/api/data` soguk baslangicta -- backend `_cache["data"]` dolmadan, yani HER
`systemctl restart bist30` sonrasi -- su cevabi verir:

    {"stocks": [], "loading": true, ...}

Bu "hisse yok" DEGIL, "hisse listesi henuz hazir degil" demektir. Uc tuketici
vardi, ikisi bu ayrimi yapmiyordu:

  * `templates/index.html` daLoadData()  -> dort bolume birden kesin hukumlu
    "Su an gosterilecek hisse verisi yok." yaziyordu. daLoadData() sayfa omru
    boyunca BIR KEZ cagrilir ve bos dalinda tekrar-dene dugmesi yoktur: yalan
    kendiliginden iyilesmiyordu.
  * `templates/404.html` hisse arama -> `_tickers` BOS DIZI oluyor, bos dizi
    truthy oldugu icin "liste hazir" sayiliyor ve THYAO icin bile
    `"THYAO" ile eslesen bir hisse bulunamadi` yaziyordu.
  * `static/bp-search.js` loadSyms() -> KANON: `d.loading` dalini yazili
    gerekcesiyle ele alan TEK yer. Iki kopya kanonu hic gormemisti.

Ayni aile: [[reference_k_turu_olcum_dersleri_hub]] "yoklugu 0/bos ile temsil
etme" (K-BJ) ve K-V "bos != hata". Burada ucuncu varyant: **bos != yukleniyor**.

YONTEM
------
1. Yorumlar SOYULUR (JS `//`, `/* */`, Jinja `{# #}`) -- satir sayisi korunur
   (K-BJ dersi: yorum soyarken satir numaralari kaymamali). Yorumda gecen
   "loading" kelimesi kapiyi GECIRMEZ; bu dosyanin kendi aciklamalari da
   aynen bu yuzden taranmaz.
2. `fetch('/api/data')` (tam eslesme; `/api/data-lite`, `/api/data-quality`
   HARIC) her gecisi icin sonraki WINDOW satir taranir.
3. O pencerede `stocks` TUKETILIYORSA (`.stocks` erisimi) ve bir BOSLUK DALI
   varsa (`!<sey>.length`, `.length === 0`, `length ? :` vb.), pencerede
   `loading` de gecmek ZORUNDADIR.

Taban SIFIR: yeni bir ihlal kapiyi kirar.

Kullanim: python3 tools/api-data-loading-guard.py
"""
import glob
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WINDOW = 90

# `/api/data` — ardindan harf/tire gelirse (data-lite, data-quality) ESLESMEZ.
FETCH_RE = re.compile(r"""fetch\(\s*['"]/api/data(?![\w-])""")
STOCKS_RE = re.compile(r"\.stocks\b")
LOADING_RE = re.compile(r"\bloading\b")
# ⛔ K-BJ dersi burada DEDEKTORUN KENDISINE carpti (21.09, K-BK pozitif
# kontrolu): ilk surum yalniz NEGATIF yazimlari (`!real.length`,
# `!Array.isArray`) ariyordu ve `templates/404.html`'in POZITIF yazimini
# (`if (d && Array.isArray(d.stocks))`) kacirdi — dort ihlalden ucunu buldu.
# Bir sekil/bosluk dali hangi yazimda olursa olsun sayilir.
EMPTY_BRANCH_RE = re.compile(
    r"""(?:\.length\b)"""                       # herhangi bir uzunluk okumasi
    r"""|(?:Array\.isArray)"""                  # sekil kontrolu (her iki yazim)
    r"""|(?:\|\|\s*\[\s*\])"""                  # d.stocks || []
)


def strip_comments(text):
    """JS //, /* */ ve Jinja {# #} yorumlarini bosluga cevirir; \n KORUNUR."""
    out = []
    i, n = 0, len(text)
    in_line = in_block = in_jinja = False
    while i < n:
        c = text[i]
        nxt = text[i + 1] if i + 1 < n else ''
        if in_line:
            if c == '\n':
                in_line = False
                out.append(c)
            else:
                out.append(' ')
            i += 1
        elif in_block:
            if c == '*' and nxt == '/':
                in_block = False
                out.append('  ')
                i += 2
            else:
                out.append(c if c == '\n' else ' ')
                i += 1
        elif in_jinja:
            if c == '#' and nxt == '}':
                in_jinja = False
                out.append('  ')
                i += 2
            else:
                out.append(c if c == '\n' else ' ')
                i += 1
        elif c == '/' and nxt == '/':
            in_line = True
            out.append('  ')
            i += 2
        elif c == '/' and nxt == '*':
            in_block = True
            out.append('  ')
            i += 2
        elif c == '{' and nxt == '#':
            in_jinja = True
            out.append('  ')
            i += 2
        else:
            out.append(c)
            i += 1
    return ''.join(out)


def scan(rel):
    path = os.path.join(ROOT, rel)
    try:
        with open(path, encoding='utf-8') as fh:
            raw = fh.read()
    except (OSError, UnicodeDecodeError):
        return []
    lines = strip_comments(raw).split('\n')
    hits = []
    for idx, line in enumerate(lines):
        if not FETCH_RE.search(line):
            continue
        win = '\n'.join(lines[idx:idx + WINDOW])
        if not STOCKS_RE.search(win):
            continue                      # stocks tuketmiyor -> kapsam disi
        if not EMPTY_BRANCH_RE.search(win):
            continue                      # bosluk dali yok -> kapsam disi
        if not LOADING_RE.search(win):
            hits.append((idx + 1, line.strip()[:90]))
    return hits


# --- POZITIF KONTROL ---------------------------------------------------------
# ⛔ K-BJ kapisi (gate 30) burada `HEAD`e baglanmisti; fix commit edilir edilmez
# HEAD fix'i icermeye basladi, kontrol ihlal bulamadi ve kapi KENDI KENDINI
# kirdi. Bu yuzden DEGISMEZ bir commit'e sabitleniyor.
PRE_FIX_REF = '455f134'   # K-BK fix'inden onceki agac — dort ihlalin hepsi burada


def scan_ref(ref):
    """Verilen commit'teki agaci tarar (dosya sistemine dokunmadan)."""
    import subprocess
    hits = []
    try:
        listing = subprocess.check_output(
            ['git', 'ls-tree', '-r', '--name-only', ref], cwd=ROOT
        ).decode('utf-8').split('\n')
    except Exception:
        return None
    for rel in listing:
        if not (rel.startswith('templates/') or rel.startswith('static/')):
            continue
        if not (rel.endswith('.html') or rel.endswith('.js')):
            continue
        try:
            raw = subprocess.check_output(['git', 'show', f'{ref}:{rel}'],
                                          cwd=ROOT).decode('utf-8')
        except Exception:
            continue
        lines = strip_comments(raw).split('\n')
        for idx, line in enumerate(lines):
            if not FETCH_RE.search(line):
                continue
            win = '\n'.join(lines[idx:idx + WINDOW])
            if not STOCKS_RE.search(win) or not EMPTY_BRANCH_RE.search(win):
                continue
            if not LOADING_RE.search(win):
                hits.append(f'{rel}:{idx + 1}')
    return hits


def main():
    pc = scan_ref(PRE_FIX_REF)
    if pc is None:
        print(f'  ! pozitif kontrol kosulamadi ({PRE_FIX_REF} okunamadi) — devam')
    elif not pc:
        print(f'  ✗ POZITIF KONTROL DUSTU: fix oncesi agacta ({PRE_FIX_REF}) '
              f'hic ihlal bulunamadi — dedektor kor olabilir.')
        return 2
    else:
        print(f'  pozitif kontrol: {len(pc)}/4 ihlal ({PRE_FIX_REF}) — '
              + ', '.join(pc))

    targets = []
    for pat in ('templates/*.html', 'static/*.js', 'static/js/*.js'):
        targets += sorted(glob.glob(os.path.join(ROOT, pat)))
    total = 0
    consumers = 0
    for path in targets:
        rel = os.path.relpath(path, ROOT)
        raw_lines = open(path, encoding='utf-8', errors='ignore').read()
        if FETCH_RE.search(strip_comments(raw_lines)):
            consumers += 1
        for lineno, snippet in scan(rel):
            total += 1
            print(f"  IHLAL {rel}:{lineno} — /api/data tuketiliyor, bos liste "
                  f"dali var ama `loading` HIC okunmuyor\n"
                  f"        soguk baslangicta kullaniciya 'veri yok' yalani "
                  f"gosterilir: {snippet}")
    if total:
        print(f"\n  ✗ api-data-loading-guard: {total} ihlal "
              f"({consumers} tuketici tarandi)")
        return 1
    print(f"  ✓ api-data-loading-guard: 0 ihlal ({consumers} /api/data "
          f"tuketicisi, hepsi `loading` dalini okuyor)")
    return 0


if __name__ == '__main__':
    sys.exit(main())
