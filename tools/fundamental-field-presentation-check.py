#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""tools/fundamental-field-presentation-check.py — K-DL: TEMEL ALANIN
SUNUM SOZLESMESI.

NEDEN AYRI BIR KAPI (22.09.2026):

R1 — ISARETLI YUZDE YAZIMI.
  Sitede IKI yuzde kanonu var ve ikisi de mesru:
    * DEGISIM yuzdesi -> `bpFormatPct` / `_fmt_macros.pct_text`: "+1,45%",
      "-4,28%" (isaret zorunlu, '%' SONDA).
    * SEVIYE yuzdesi  -> Turkce yazim, '%' ONDE: "%17,6".
  Sorun, seviye yuzdesinin NEGATIF halinde cikti: `'%' + (-3.5).toFixed(1)`
  **"%-3,5"** uretir — eksi isareti yuzde isaretiyle rakamin ARASINA
  sikisir; iki kanonun da disinda, hicbir dilde gecerli olmayan bir yazim.
  CANLI OLCUM 22.09 (/api/hisse/<T>/fundamentals, 217/217 hisse): en az
  bir negatif yuzde tasiyan **148** hisse (%68) — yani /hisse Temel
  sekmesinin ucte ikisinde bu yazim goruluyordu.
  (Ayrica ayni turda: TAM SIFIR degerler negatifle ayni kefeye dusuyordu
  -- 8 hisse net kar marji %0,0 iken KIRMIZI 'Negatif' etiketliydi.) Ayni yazim /karsilastir ROE satirinda
  BAGIMSIZCA ikinci kez duruyordu (⛔ "ayni is icin iki kanon").

  Kural yapisal: bir '%' isareti dogrudan HESAPLANMIS bir sayi ifadesinin
  onune yazilamaz. Ciplak degisken (`%{{ al_pct }}`, `'%' + winRate`)
  serbesttir — orada isaret uretilemez; `.toFixed(`, aritmetik ya da
  `parseFloat` iceren bir ifade ise isaret uretebilir ve kanonik
  bicimleyiciden (`bpPctLevel` / `bpFormatPct` / `pct_text`) gecmelidir.
  (⛔ 52. ders: kapi alan ADINA bakmaz — /karsilastir'da ifade `n`
  degiskenini kullaniyor, alan adi hic gecmiyor.)

R2 — KAYNAGI OLMAYAN ALAN SUNULMAZ (`beta`).
  `f.beta` (yfinance `beta`) BIST'e gore olculmus bir sayi DEGIL. Sitenin
  kendi verisiyle olcum (494 gunluk kapanis, kiyas XU030): ISCTR kart 0,20
  -> olculen 1,21 · GARAN 0,51 -> 1,15 · AKBNK 0,69 -> 1,29 · FROTO 0,30 ->
  0,86. 25 buyuk hissede kart ortalamasi 0,45; olculen 0,92. Canli dagilim
  da tek basina yeter: beta dolu 128 hissenin 96'si (%75) "Piyasa alti
  hareket", yalnizca 5'i "piyasa ustu" — endeksin kendi agir hisselerinin betasi insa
  geregi ~1 etrafinda olmak ZORUNDA. app.py `_FUND_SANITY` yorumu bunu
  zaten itiraf ediyor: `"beta": (0.10, 5.0),  # 0.06-0.09 beta havacilik
  icin sacma` — alt sinir sayiyi duzeltmez, en ucunu gizler.
  Alan XU030'a gore hesaplanip donene dek (CPO-1787) hicbir yuzeyde
  gosterilmez. Duzeldiginde bu kural kaldirilir.

Kullanim:
  python3 tools/fundamental-field-presentation-check.py
  python3 tools/fundamental-field-presentation-check.py --self-test
  python3 tools/fundamental-field-presentation-check.py --ref SHA
"""
import io
import os
import re
import subprocess
import sys
import tarfile
import tempfile

SCAN_DIRS = ('templates', 'static')
SCAN_EXT = ('.html', '.js')

CANON_FMT = ('bpPctLevel', 'bpFormatPct', 'pct_text')
# Isaret uretebilen = HESAPLANMIS ifade.
COMPUTED = re.compile(r'\.toFixed\s*\(|parseFloat\s*\(|[*/]|(?<![<>=!+\-])-|'
                      r'\|\s*round|\|\s*format|%\s*\(')


def strip_comments(src):
    """⛔ 50. ders: kendi yorumun dedektoru kirletir. ⛔ 158. ders: bir
    sablon DORT yorum lehcesi tasir."""
    def blank(m):
        return ''.join('\n' if c == '\n' else ' ' for c in m.group(0))
    src = re.sub(r'/\*.*?\*/', blank, src, flags=re.S)
    src = re.sub(r'\{#.*?#\}', blank, src, flags=re.S)
    src = re.sub(r'<!--.*?-->', blank, src, flags=re.S)
    src = re.sub(r'(?m)^\s*//.*$', blank, src)
    return src


def _match_close(src, i, open_tok, close_tok):
    """`${`/`{{` acilisindan kapanisa kadar olan ifadeyi dondur."""
    depth, j = 1, i + len(open_tok)
    while j < len(src):
        if src.startswith(close_tok, j):
            depth -= 1
            if depth == 0:
                return src[i + len(open_tok):j], j + len(close_tok)
            j += len(close_tok)
            continue
        if src.startswith(open_tok, j):
            depth += 1
            j += len(open_tok)
            continue
        if open_tok == '${' and src[j] == '{':
            depth += 1
        elif open_tok == '${' and src[j] == '}':
            depth -= 1
            if depth == 0:
                return src[i + len(open_tok):j], j + 1
        j += 1
    return None, len(src)


def _pct_sites(src):
    """'%' isaretinden HEMEN sonra gelen enterpolasyonlar."""
    out = []
    for m in re.finditer(r'%(?=\$\{|\{\{)', src):
        i = m.end()
        tok = ('${', '}') if src.startswith('${', i) else ('{{', '}}')
        expr, _ = _match_close(src, i, tok[0], tok[1])
        if expr is not None:
            out.append((m.start(), expr))
    # `'%' + x` / `"%" ~ x` birlestirmeleri
    for m in re.finditer(r'''['"]%['"]\s*[+~]\s*([^;,)\]}\n]{1,80})''', src):
        out.append((m.start(), m.group(1)))
    return out


def check_src(src):
    src = strip_comments(src)
    bad = []
    for pos, expr in _pct_sites(src):
        e = expr.strip()
        if any(c + '(' in e for c in CANON_FMT):
            continue
        if not COMPUTED.search(e):
            continue                      # ciplak degisken: isaret uretemez
        bad.append((src[:pos].count('\n') + 1, 'R1', e[:80]))
    for m in re.finditer(r'\b[fsd]\.beta\b|\bbeta\s*:', src):
        bad.append((src[:m.start()].count('\n') + 1, 'R2', m.group(0)))
    return bad


def scan(root):
    out = []
    for d in SCAN_DIRS:
        base = os.path.join(root, d)
        for dp, _, fns in os.walk(base):
            for fn in sorted(fns):
                if not fn.endswith(SCAN_EXT):
                    continue
                p = os.path.join(dp, fn)
                rel = os.path.relpath(p, root)
                src = io.open(p, encoding='utf-8', errors='replace').read()
                for ln, rule, snip in check_src(src):
                    out.append((rel, ln, rule, snip))
    return out


SELF = [
    # (kaynak, beklenen ihlal sayisi, aciklama)
    ("x = `%${f.roe.toFixed(1)}`", 1, 'R1 hesaplanmis yuzde (orijinal hata)'),
    ("x = `%${n.toFixed(1).replace('.', ',')}`", 1, 'R1 alan adi GECMEDEN'),
    ("x = bpPctLevel(f.roe, 1)", 0, 'R1 kanonik bicimleyici'),
    ("x = `%${activeTag}`", 0, 'R1 ciplak degisken'),
    ("<span>%{{ al_pct }}</span>", 0, 'R1 Jinja ciplak degisken'),
    ("<span>%{{ (v * 100)|round(1) }}</span>", 1, 'R1 Jinja hesaplanmis'),
    ("y = '%' + winRate", 0, 'R1 birlestirme, ciplak'),
    ("y = '%' + (a - b).toFixed(1)", 1, 'R1 birlestirme, hesaplanmis'),
    ("/* `%${f.roe.toFixed(1)}` */", 0, 'R1 yorum soyulur'),
    ("{# %{{ (v*100)|round(1) }} #}", 0, 'R1 Jinja yorumu soyulur'),
    ("// x = `%${f.roe.toFixed(1)}`", 0, 'R1 JS satir yorumu soyulur'),
    ("v = f.beta != null ? f.beta : null", 2, 'R2 beta sunumu'),
    ("v = s.roe", 0, 'R2 beta disi alan'),
    ("x = `%${bpPctLevel(f.roe, 1)}`", 0, 'R1 kanon ic ice'),
]


def self_test():
    ok = 0
    for src, want, desc in SELF:
        got = len(check_src(src))
        flag = 'OK ' if got == want else 'FAIL'
        if got == want:
            ok += 1
        else:
            print('  %s %-38s bekleniyor=%d bulunan=%d | %s'
                  % (flag, desc, want, got, src[:50]))
    print('self-test %d/%d' % (ok, len(SELF)))
    return 0 if ok == len(SELF) else 1


def checkout(ref):
    d = tempfile.mkdtemp(prefix='ffpc-')
    tar = os.path.join(d, 'a.tar')
    with open(tar, 'wb') as fh:
        subprocess.check_call(['git', 'archive', ref], stdout=fh)
    with tarfile.open(tar) as tf:
        tf.extractall(d)
    return d


def main():
    if '--self-test' in sys.argv:
        return self_test()
    root = '.'
    label = 'calisan agac'
    if '--ref' in sys.argv:
        ref = sys.argv[sys.argv.index('--ref') + 1]
        root = checkout(ref)
        label = 'ref ' + ref
    bad = scan(root)
    if not bad:
        print('K-DL OK — isaretli yuzde yazimi tek kanondan, kaynaksiz alan '
              'sunulmuyor (%s).' % label)
        return 0
    print('K-DL KIRIK — %d ihlal (%s):' % (len(bad), label))
    for rel, ln, rule, snip in bad:
        print('  %s:%d  [%s] %s' % (rel, ln, rule, snip))
    print()
    print('  R1: seviye yuzdesi `bpPctLevel`, degisim yuzdesi `bpFormatPct`/')
    print('      `pct_text` ile basilir — "%" isaretinin ardina hesaplanmis')
    print('      bir sayi yazilirsa negatifte "%-3,5" cikar.')
    print('  R2: `beta` BIST\'e gore olculmus degil (CPO-1787) — gosterilmez.')
    return 1


if __name__ == '__main__':
    sys.exit(main())
