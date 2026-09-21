#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
K-BV (22.09.2026) — PARA OLCEGI KISALTMASI TEK KANONDAN GELIR.

Sitede AYNI buyukluk UC ayri yazimla basiliyordu; ikisi AYNI SEKMEDE,
birbirinin birkac piksel altinda:
  (a) `Mrd₺` / `Mn₺`   -> /hisse Temel kartlari (_fmtMoneyObj), /karsilastir
                          (_fmtMcap): 2 ondalik, sembolden once BOSLUK YOK
  (b) `Mr ₺`  / `Mn ₺` -> /hisse Temel sekmesi Ciro/Net Kar grafigi
                          (_fmtCompactCur): 1 ondalik / tam sayi, bosluk VAR,
                          T basamagi YOK
  (c) `M₺` / `K₺`      -> /portfolio (fmtM): milyar ve trilyon basamagi HIC
                          yok; 1,2 milyarlik portfoy "1.200,00 M₺" yaziyordu

Canli olcum 22.09 (7/7 hisse, /api/hisse/<T>/fundamentals): ASELS Temel
sekmesinde "Yillik Ciro 197,98 Mrd₺" kartinin hemen altindaki grafik ayni
kalemi "180,4 Mr ₺" diye yaziyordu; TUPRS kartta "1,03 T₺" iken grafigin
trilyon basamagi olmadigi icin 2022 cirosu "916,8 Mr ₺" kaliyordu. Bu metin
yalnizca gorunen etiket degil, grafik gruplarinin aria-label/data-tip okumasi
da -- ekran okuyucu "Mr" duyuyordu.

Kanon: static/bp-format.js -> bpMoneyCompact(v, {sym, frac}).
       `<sayi> <OLCEK> <SEMBOL>`, olcekler T / Mrd / Mn, 1.000.000 alti TAM.

IKI DESEN (taban SIFIR):
  A) OLCEK BOLMESI: sablon/statik JS icinde 1e6 / 1e9 / 1e12 (ve ondalik
     yazimlari) ile BOLME. Para olcekleme kanonun isidir; burada bolme
     yapiliyorsa ikinci bir olcek tablosu yaziliyor demektir.
     ⛔ 49. ders (K-BU): kapiyi YAZIMA degil DEGERIN KAYNAGINA bagla --
     bu yuzden olcut kisaltmanin harfleri degil, olceklemenin KENDISI.
  B) OLCEK BIRIMI DIZGESI: betik baglaminda, icerigi yalnizca bir olcek
     kisaltmasi (+ istege bagli para sembolu) olan dize sabiti -- `' Mrd'`,
     `' Mn '`, `' M₺'`, `' K₺'`. Backend zaten olceklenmis bir sayi
     donduruyorsa A deseni tetiklenmez, etiket yine de elle yazilir.

Yorumlar soyulur (⛔ 50. ders: kendi belgelendirmen dedektoru kirletir),
satir sonlari KORUNUR (⛔ 35. ders: yoksa rapor edilen satir no kayar).
HTML'de YALNIZCA <script> bloklari taranir -- duz metindeki "5 Mn ₺"
(metodoloji.html) bir kod kanonu degil, proza.

Kullanim:
  python3 tools/money-scale-canon-check.py             # calisan agac
  python3 tools/money-scale-canon-check.py --ref SHA   # o commit'in agaci
"""
import os, re, sys, subprocess, tempfile, tarfile, io

# 1e6 / 1e9 / 1e12 ve duz yazimlari (1000000, 1_000_000, 1.000.000 degil --
# JS'te nokta ondaliktir). Bolme isareti ZORUNLU.
SCALE_DIV = re.compile(
    r"/\s*(?:1e(?:6|9|12)\b|1_?0{6}(?:_?0{3}){0,2}\b)", re.I)

# Icerigi SADECE olcek kisaltmasi (+ istege bagli para sembolu/kodu) olan
# dize sabiti. `'Mn'`, `' Mrd'`, `' Mr '`, `'M₺'`, `' K₺'`, `'T$'` ...
#
# ⛔ TEK HARFLI token (T/K/B/M) TEK BASINA OLCUT OLAMAZ: ilk yazimda
# bp-search.js:390'daki `e.key === 'K'` (Cmd/Ctrl+K kisayolu) ihlal diye
# raporlandi. Tek harf ancak bir BOSLUKLA (" T" -> sayiya eklenen sonek)
# ya da bir PARA SEMBOLUYLE ("M₺") birlikte olcek anlamina gelir.
_CUR = r"(?:₺|\$|€|£|TL|TRY|USD|EUR)"
SCALE_LIT = re.compile(
    r"(['\"])(?:"
    r"\s*(?:Mrd|Mio|Mlr|Mn|Mr|mrd|mn|bn)\s*" + _CUR + r"?\s*"
    r"|\s+[TKBM]\s*" + _CUR + r"?\s*"
    r"|\s*[TKBM]\s*" + _CUR + r"\s*"
    r")\1")

ALLOW = {
    # Kanonun KENDISI: olcek tablosu ve bolme burada yasar.
    'static/bp-format.js',
    # Ucuncu parti, minify: bizim kanonumuzun kapsami disinda.
    'static/lightweight-charts.min.js',
}

SCRIPT_RE = re.compile(r'<script\b[^>]*>(.*?)</script>', re.S | re.I)


def _blank(t):
    return ''.join('\n' if ch == '\n' else ' ' for ch in t)


def strip_comments(s):
    s = re.sub(r'/\*.*?\*/', lambda m: _blank(m.group(0)), s, flags=re.S)
    s = re.sub(r'\{#.*?#\}', lambda m: _blank(m.group(0)), s, flags=re.S)
    s = re.sub(r'<!--.*?-->', lambda m: _blank(m.group(0)), s, flags=re.S)
    s = re.sub(r'(?<![:\'"\\])//[^\n]*', lambda m: _blank(m.group(0)), s)
    return s


def script_only(s):
    """HTML'de <script> disini bosluga cevirir (satir sayisi KORUNUR)."""
    out = list(_blank(s))
    for m in SCRIPT_RE.finditer(s):
        a, b = m.start(1), m.end(1)
        out[a:b] = list(s[a:b])
    return ''.join(out)


def scan_tree(root):
    bad = []
    for sub, exts in (('templates', ('.html',)), ('static', ('.js',))):
        base = os.path.join(root, sub)
        for dp, _, fns in os.walk(base):
            for fn in sorted(fns):
                if not fn.endswith(exts):
                    continue
                path = os.path.join(dp, fn)
                rel = os.path.relpath(path, root)
                if rel in ALLOW:
                    continue
                raw = open(path, encoding='utf-8', errors='replace').read()
                src = strip_comments(raw)
                if fn.endswith('.html'):
                    src = script_only(src)
                for m in SCALE_DIV.finditer(src):
                    ln = src[:m.start()].count('\n') + 1
                    bad.append((rel, ln, 'A',
                                f"`{' '.join(m.group(0).split())}` -> elle olcekleme "
                                f"(kanon: bp-format.js bpMoneyCompact)"))
                for m in SCALE_LIT.finditer(src):
                    ln = src[:m.start()].count('\n') + 1
                    bad.append((rel, ln, 'B',
                                f"olcek birimi dizgesi {m.group(0)} -> ikinci bir "
                                f"kisaltma kanonu (kanon: bpMoneyCompact)"))
    return bad


def tree_at_ref(ref):
    d = tempfile.mkdtemp(prefix='moneyscale-')
    blob = subprocess.check_output(['git', 'archive', ref])
    tarfile.open(fileobj=io.BytesIO(blob)).extractall(d)
    return d


def main():
    ref = None
    if '--ref' in sys.argv:
        ref = sys.argv[sys.argv.index('--ref') + 1]
    root = tree_at_ref(ref) if ref else os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    bad = scan_tree(root)
    tag = (' (ref ' + ref + ')') if ref else ''
    if not bad:
        print(f"K-BV OK — para olcegi kisaltmasi tek kanondan geliyor{tag}.")
        return 0
    print(f"K-BV KIRIK — {len(bad)} ihlal{tag}:")
    for rel, ln, kind, msg in sorted(bad):
        print(f"  [{kind}] {rel}:{ln}  {msg}")
    print("\n  Kanon: static/bp-format.js -> bpMoneyCompact(v, {sym, frac})")
    print("         `<sayi> <OLCEK> <SEMBOL>` · T / Mrd / Mn · 1.000.000 alti tam")
    return 1


if __name__ == '__main__':
    sys.exit(main())
