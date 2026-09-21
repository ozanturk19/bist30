#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""tools/fundamental-card-band-check.py — K-BX: TEMEL ANALIZ KARTLARININ
BIRIM VE BAND SOZLESMESI.

NEDEN AYRI BIR KAPI GEREKTI (22.09.2026):
  `/hisse` Temel sekmesindeki kart izgarasi ayni sayiyi UC yerde kullanir:
  gosterilen METIN, kartin RENGI ve alt ETIKET. 22.09'da bu ucluden ikisi
  birbirinden koptu, iki AYRI sinifta:

  1) BIRIM. yfinance `debtToEquity` alanini YUZDE dondurur (THYAO 89,39 =
     0,89x; OTKAR 869,17 = 8,69x). Kart yuzdeyi dogrudan "x" (kat) diye
     basiyor, esikleri de (2 / 1) ORAN gibi uyguluyordu. CANLI olcum: D/E
     dolu 94 hissenin 85'i kirmizi "Yuksek" etiketliydi; dogru cevrimde
     80'i yesil "Dusuk" cikiyor. Yani kart borcsuz sirketleri asiri borclu
     ilan ediyordu. Backend'in kendi akil-sagligi araligi da bunu soyluyor:
     `_FUND_SANITY["debt_to_equity"]` ust siniri 2000 -- 2000 KAT diye bir
     sey yoktur, %2000 = 20x vardir.
  2) BAND. Beta kartinda RENK 0,7/1,3 esigini, ETIKET 1,0 esigini
     kullaniyordu: canli 62 beta kartinin 11'inde renk ile yazi FARKLI
     bandi soyluyordu (KAREL 0,99 notr renk + "Dusuk volatilite").
     K-BO'nun "esiklenen sayi = gosterilen sayi" kuralinin ayni sinifi.

IKI KURAL (⛔ 52. ders: kapi hatanin OGRENDIGI yazimini degil HATANIN
KENDISINI arar -- ikisi de alan adina degil YAPIYA bakar):

  A) BIRIM TUTARLILIGI. Bir alanin UI'daki EN BUYUK esigi, backend'in o
     alan icin uretebilecegi EN BUYUK degerden (app.py `_FUND_SANITY` ust
     siniri) `MAX_SCALE_GAP` kattan fazla kucukse, UI o alani BASKA BIR
     BIRIMDE esikliyordur. Olcek duzeltmesi (`/ 100` gibi) sayiliyor.
     Ornek: D/E ust sinir 2000, en buyuk UI esigi 2 -> oran 1000 -> IHLAL.
     Duzeltme sonrasi `_deRatio = f.debt_to_equity / 100` -> 20/2 = 10 -> OK.
     Mesru genis araliklar (current_ratio 50 / esik 2 = 25; roe 200 /
     esik 20 = 10) esigin ALTINDA kalir.
  B) BAND TUTARLILIGI. Bir `_fundCard(...)` cagrisinda RENK argumanindaki
     sayisal esik kumesi ile ALT ETIKET argumanindaki esik kumesi AYNI
     olmali. Yardimci fonksiyonlar (`_peColor`, `_ucuzlukEtiketi`, ...)
     tek satirlik tanimlarindan cozulur.

Kullanim:
  python3 tools/fundamental-card-band-check.py
  python3 tools/fundamental-card-band-check.py --ref SHA
"""
import io
import os
import re
import subprocess
import sys
import tarfile
import tempfile

TEMPLATE = os.path.join('templates', 'hisse.html')
APP = 'app.py'

# UI esigi ile backend'in uretebilecegi tavan arasindaki KABUL EDILEN en
# buyuk oran. 100x'lik bir birim hatasi bu esigi her zaman asar; mesru
# "genis kuyruk" araliklari (current_ratio 50/2=25) altinda kalir.
MAX_SCALE_GAP = 50.0

NUM = re.compile(r'(?<![\w.])(\d+(?:\.\d+)?)(?![\w.])')
# Tek satirlik yardimci: function _ad(v) { ... }
HELPER = re.compile(r'function\s+(_[A-Za-z0-9_]+)\s*\(([^)]*)\)\s*\{(.*?)\n?\}',
                    re.S)


def strip_comments(src):
    """Yorumlari BOSLUKLA (satir sayisi korunarak) degistir.
    ⛔ 50. ders: kendi yorumun dedektoru kirletir."""
    def blank(m):
        return ''.join('\n' if c == '\n' else ' ' for c in m.group(0))
    src = re.sub(r'/\*.*?\*/', blank, src, flags=re.S)
    src = re.sub(r'\{#.*?#\}', blank, src, flags=re.S)
    src = re.sub(r'<!--.*?-->', blank, src, flags=re.S)
    return src


def split_args(s):
    """Ust duzey virgullerden bol (parantez/tirnak/sablon dizgisi farkinda)."""
    out, depth, buf, q = [], 0, [], None
    i = 0
    while i < len(s):
        c = s[i]
        if q:
            if c == '\\':
                buf.append(c)
                i += 1
                if i < len(s):
                    buf.append(s[i])
                i += 1
                continue
            if c == q:
                q = None
        elif c in '"\'`':
            q = c
        elif c in '([{':
            depth += 1
        elif c in ')]}':
            depth -= 1
        elif c == ',' and depth == 0:
            out.append(''.join(buf))
            buf = []
            i += 1
            continue
        buf.append(c)
        i += 1
    out.append(''.join(buf))
    return [a.strip() for a in out]


def call_args(src, name, start):
    """`name(` cagrisinin argumanlarini ve cagri bitis indeksini dondur."""
    i = src.index('(', start)
    depth, j, q = 0, i, None
    while j < len(src):
        c = src[j]
        if q:
            if c == '\\':
                j += 2
                continue
            if c == q:
                q = None
        elif c in '"\'`':
            q = c
        elif c == '(':
            depth += 1
        elif c == ')':
            depth -= 1
            if depth == 0:
                return split_args(src[i + 1:j]), j
        j += 1
    return None, start


def helper_numbers(src):
    """Tek satirlik yardimcilarin ICINDEKI sayisal esikler."""
    out = {}
    for m in HELPER.finditer(src):
        body = m.group(3)
        if len(body) > 600:          # buyuk fonksiyon: esik tablosu degil
            continue
        out[m.group(1)] = {float(x) for x in NUM.findall(body)}
    return out


def expr_numbers(expr, helpers):
    """Bir arguman ifadesindeki esik kumesi. Yardimci cagrilari cozulur;
    `.toFixed(2)` gibi BICIM sayilari ve olcek bolenleri (/100) elenir."""
    e = expr
    nums = set()
    for name, inner in helpers.items():
        if name + '(' in e:
            nums |= inner
    e = re.sub(r'\.toFixed\(\s*\d+\s*\)', ' ', e)
    e = re.sub(r'(?:minimum|maximum)FractionDigits\s*:\s*\d+', ' ', e)
    e = re.sub(r'/\s*\d+(?:\.\d+)?', ' ', e)        # olcek bolme
    nums |= {float(x) for x in NUM.findall(e)}
    return nums


def sanity_ranges(root):
    src = io.open(os.path.join(root, APP), encoding='utf-8',
                  errors='replace').read()
    m = re.search(r'_FUND_SANITY\s*=\s*\{(.*?)\n\}', src, re.S)
    if not m:
        return {}
    out = {}
    for k, lo, hi in re.findall(
            r'"([\w]+)"\s*:\s*\(\s*(-?\d+(?:\.\d+)?)\s*,\s*'
            r'(-?\d+(?:\.\d+)?)\s*\)', m.group(1)):
        out[k] = (float(lo), float(hi))
    return out


def scan(root):
    src = strip_comments(io.open(os.path.join(root, TEMPLATE),
                                 encoding='utf-8', errors='replace').read())
    helpers = helper_numbers(src)
    sanity = sanity_ranges(root)
    bad = []

    # Olcek duzeltmeleri: `const _x = f.alan / 100` -> _x, (alan, 100)
    scaled = {}
    for var, fld, div in re.findall(
            r'(?:const|let|var)\s+(_\w+)\s*=\s*[^;\n]*?f\.(\w+)[^;\n]*?'
            r'/\s*(\d+(?:\.\d+)?)', src):
        scaled[var] = (fld, float(div))

    pos = 0
    while True:
        i = src.find('_fundCard(', pos)
        if i < 0:
            break
        args, end = call_args(src, '_fundCard', i)
        pos = end + 1
        if not args or len(args) < 3:
            continue
        ln = src[:i].count('\n') + 1
        label = args[0].strip().strip('\'"')
        val, color = args[1], args[2]
        sub = args[3] if len(args) > 3 else None

        # ── Kural B: renk bandi == etiket bandi ───────────────────────────
        if sub and sub.strip() not in ('null', "''", '""'):
            cn, sn = expr_numbers(color, helpers), expr_numbers(sub, helpers)
            if cn != sn:
                bad.append((ln, label, 'BAND',
                            'renk esikleri %s, etiket esikleri %s — ayni '
                            'sayi iki ayri banda bolunuyor'
                            % (sorted(cn), sorted(sn))))

        # ── Kural A: UI esigi backend'in birimiyle ayni mi? ───────────────
        # YALNIZ "kat/oran" iddiasi tasiyan kartlar: deger `x` sonekiyle ya
        # da soneksiz basiliyorsa UI o sayinin BIR ORAN oldugunu soyluyor ve
        # esikleri dagilimi kusatmalidir. `%` onekli kartlar disarida: orada
        # esik bir olcek isareti degil NITEL bir taban (kazanc buyumesi
        # %1000 olabilir, "Guclu" esigi yine %10'dur) -- bu ayrim alan ADINA
        # degil kartin KENDI birim iddiasina bakar.
        if '%' in val:
            continue
        refs = set(re.findall(r'f\.(\w+)', val + ' ' + color + ' ' + (sub or '')))
        for v in re.findall(r'(_\w+)', val + ' ' + color + ' ' + (sub or '')):
            if v in scaled:
                refs.add(scaled[v][0])
        thr = expr_numbers(color, helpers) | (
            expr_numbers(sub, helpers) if sub else set())
        thr = {t for t in thr if t > 0}
        if not thr:
            continue
        for fld in refs:
            if fld not in sanity:
                continue
            hi = sanity[fld][1]
            # Bu alan sablonda olceklenmisse tavan da olceklenir.
            for var, (f2, div) in scaled.items():
                if f2 == fld and var in (val + color + (sub or '')):
                    hi = hi / div
            gap = hi / max(thr)
            if gap > MAX_SCALE_GAP:
                bad.append((ln, label, 'BIRIM',
                            'backend `%s` en fazla %g uretebilir ama UI en '
                            'buyuk esigi %g — %.0fx fark, UI baska bir '
                            'birimde esikliyor (olcek duzeltmesi yok)'
                            % (fld, hi, max(thr), gap)))
    return bad


def tree_at_ref(ref):
    d = tempfile.mkdtemp(prefix='fundband-')
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
        print('K-BX OK — temel analiz kartlarinda birim/band sapmasi yok%s.'
              % suffix)
        return 0
    print('K-BX KIRIK — %d ihlal%s:' % (len(bad), suffix))
    for ln, label, kind, why in bad:
        print('  %s:%d  [%s] "%s"\n      %s' % (TEMPLATE, ln, kind, label, why))
    print('\n  Kanon: gosterilen sayi, renk ve alt etiket AYNI ifadeyi ve')
    print('  AYNI band kumesini kullanir; backend alaninin birimi UI esigiyle')
    print('  ayni olmalidir (degilse sablonda BIR KEZ olcek duzeltilir).')
    return 1


if __name__ == '__main__':
    sys.exit(main())
