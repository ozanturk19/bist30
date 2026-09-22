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


# Kanonik BICIMLEYICILER: son argumanlari ondalik BASAMAK SAYISIdir, esik
# degil. K-DL (22.09): `bpPctLevel(n, 1)` yazimi `.toFixed(1)`in tam
# esdegeri ama farkli yazildigi icin "1" bir band esigi sanilip
# /karsilastir'in ROE imzasini [0,10,20]'den [0,1,10,20]'ye kaydirdi ve
# SAHTE bir cross-surface ihlali uretti. Bicim sayisi, yazimina bakilmadan,
# esik olamaz.
FMT_CALL = re.compile(r'\b(bpPctLevel|bpFormatPct|bpMoneyCompact)\s*\(')


def _strip_fmt_frac(e):
    """`bpPctLevel(x, 2)` -> `bpPctLevel(x)` (bicim basamagini dusur)."""
    out, pos = [], 0
    for m in FMT_CALL.finditer(e):
        args, end = call_args(e, m.group(1), m.start())
        if args is None:
            continue
        keep = args[:1] if len(args) > 1 else args
        out.append(e[pos:m.start()])
        out.append(m.group(1) + '(' + ','.join(keep) + ')')
        pos = end + 1
    out.append(e[pos:])
    return ''.join(out)


def has_pct_unit(expr):
    """Kart degeri YUZDE mi? K-DL: eski kapi bunu `'%' in val` diye, yani
    sayinin YAZILIS BICIMINDEN okuyordu; deger kanonik bicimleyiciye
    (`bpPctLevel`) tasininca literal '%' kayboldu ve yuzde kartlari
    Kural A'ya dustu -- kapi kendi 52. dersini (hatanin yazimini degil
    kendisini ara) ihlal ediyordu. Yuzde iddiasi ya literal '%' ile ya da
    kanonik yuzde bicimleyicisiyle kurulur."""
    return '%' in expr or 'bpPctLevel(' in expr or 'bpFormatPct(' in expr


def expr_numbers(expr, helpers):
    """Bir arguman ifadesindeki esik kumesi. Yardimci cagrilari cozulur;
    `.toFixed(2)` gibi BICIM sayilari ve olcek bolenleri (/100) elenir."""
    e = expr
    nums = set()
    for name, inner in helpers.items():
        if name + '(' in e:
            nums |= inner
    e = _strip_fmt_frac(e)
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

    # Yerel takma adlar: `const _x = ... f.alan ...` -> _x, (alan, bolen).
    # K-DL (22.09) — ENJEKSIYON POZITIF KONTROLU BU DELIGI ACTI: eski yazim
    # YALNIZ `/ NUM` iceren tanimlari kaydediyordu. Yani K-BX'in kendi
    # duzeltmesini (`f.debt_to_equity / 100`) geri alan bir regresyonda
    # `f.debt_to_equity` referansi karttan TAMAMEN kayboluyor, `refs` bos
    # kaliyor ve kapi -- korumak icin YAZILDIGI hatayi -- sessizce geciriyordu.
    # Takma ad bolensiz de kaydedilir (div=1), olcek duzeltmesi ayri bir sart.
    scaled = {}
    for var, expr in re.findall(r'(?:const|let|var)\s+(_\w+)\s*=\s*([^;\n]*)', src):
        mf = re.search(r'f\.(\w+)', expr)
        if not mf:
            continue
        md = re.search(r'/\s*(\d+(?:\.\d+)?)', expr)
        scaled[var] = (mf.group(1), float(md.group(1)) if md else 1.0)

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
        if has_pct_unit(val):
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



# ── Kural C yardimcilari ──────────────────────────────────────────────────
# Band ETIKETI: kullaniciya gosterilen, BUYUK harfle baslayan Turkce dizge.
# CSS sinif adlari ('up', 'dn', 'mid', 'muted', 'mono') kucuk harfle baslar
# -- ayrim yapisal, beyaz liste degil.
LABEL = re.compile(r"'([A-ZÇĞİÖŞÜ][^']{0,24})'")
# Etiket bazen tirnakli bir sabit degil, dizgenin ICINDEKI HTML metin
# dugumudur (`<span ...>Yok</span>`). Ilk yazimda bu yuzden /karsilastir'in
# "Yok" bandi gorulmeyip YANLIS ALARM cikti -- dedektor etiketin YAZILIS
# BICIMINE degil kullaniciya gorunur olmasina bakmali.
LABEL_HTML = re.compile(r">([A-ZÇĞİÖŞÜ][^<>{}'\"]{0,24})<")
CASE = re.compile(r"case\s+'(\w+)'\s*:")


def helper_labels(src):
    """Tek satirlik yardimcilarin ICINDEKI etiket sozcukleri.

    K-DI (22.09): `expr_numbers` yardimci cagrilarinin ESIKLERINI cozuyordu
    ama ETIKETLERINI cozmuyordu. `/hisse` F/K karti etiketi
    `_ucuzlukEtiketi(f.pe_ratio, 12, 25)` ile veriyor -- 'Ucuz'/'Makul'/
    'Pahali' sozcukleri CAGRIDA degil yardimcinin GOVDESINDE. Imza etiket
    kumesini bos gorunce `cross_surface` o alani HIC kaydetmiyordu, yani
    kapi F/K ve F/DD'yi yillardir izlemiyordu. Tam da bu yuzden
    `/karsilastir`in ayni alanlari YARGISIZ basmasi (renk yok, etiket yok)
    sessiz kaldi: yargidan KACINAN yuzey, karsilastirmaya hic girmiyordu.
    (⛔ 52. ders: kapi hatanin ogrendigi yazimini degil kendisini arar.)"""
    out = {}
    for m in HELPER.finditer(src):
        body = m.group(3)
        if len(body) > 600:
            continue
        out[m.group(1)] = set(LABEL.findall(body))
    return out


def expr_labels(expr, hlabels):
    lbls = set(LABEL.findall(expr))
    lbls |= {x.strip() for x in LABEL_HTML.findall(expr) if x.strip()}
    for name, inner in hlabels.items():
        if name + '(' in expr:
            lbls |= inner
    return lbls


def band_signature(text, helpers, hlabels=None):
    """Bir kod parcasindaki (esik kumesi, etiket kumesi) imzasi."""
    return (frozenset(expr_numbers(text, helpers)),
            frozenset(expr_labels(text, hlabels or {})))


def block_after(src, start):
    """`case 'x':` sonrasi bir sonraki `case`/`default`e kadar olan govde."""
    nxt = [m.start() for m in re.finditer(r"\n\s*(?:case\s+'|default\s*:)",
                                          src[start:])]
    return src[start:start + (nxt[0] if nxt else 1200)]


def cross_surface(root):
    """AYNI backend alani, FARKLI sayfada FARKLI band -> ihlal.

    22.09'da canli: ROE dolu 103 hissenin 23'u iki sayfada farkli kefede
    (BIMAS %15,6 -> /hisse "Orta", /karsilastir "Iyi"). /hisse 20/10 +
    Guclu/Orta/Zayif, /karsilastir 15/7 + Iyi/Orta/Zayif kullaniyordu.
    ⛔ "Ayni is icin iki kanon" basli basina bulgudur (3 kez P1 uretti)."""
    seen = {}
    tdir = os.path.join(root, 'templates')
    for dp, _, fns in os.walk(tdir):
        for fn in sorted(fns):
            if not fn.endswith('.html'):
                continue
            rel = os.path.relpath(os.path.join(dp, fn), root)
            src = strip_comments(io.open(os.path.join(dp, fn),
                                         encoding='utf-8',
                                         errors='replace').read())
            helpers = helper_numbers(src)
            hlabels = helper_labels(src)
            # (a) _fundCard(...) cagrilari -> RENK + ETIKET argumanlari
            pos = 0
            while True:
                i = src.find('_fundCard(', pos)
                if i < 0:
                    break
                args, end = call_args(src, '_fundCard', i)
                pos = end + 1
                if not args or len(args) < 4:
                    continue
                text = args[2] + ' ' + args[3]
                flds = set(re.findall(r'f\.(\w+)', args[1] + ' ' + text))
                sig = band_signature(text, helpers, hlabels)
                if not sig[1]:
                    continue
                for fld in flds:
                    seen.setdefault(fld, []).append(
                        (rel, src[:i].count('\n') + 1, sig))
            # (b) `case 'alan':` bloklari (karsilastir tipi sutun render'i)
            for m in CASE.finditer(src):
                body = block_after(src, m.end())
                sig = band_signature(body, helpers, hlabels)
                if not sig[1]:
                    continue
                seen.setdefault(m.group(1), []).append(
                    (rel, src[:m.start()].count('\n') + 1, sig))

    bad = []
    for fld, occ in sorted(seen.items()):
        sigs = {o[2] for o in occ}
        if len(sigs) > 1:
            nerede = ' · '.join(
                '%s:%d esik%s etiket%s'
                % (r, l, sorted(s[0]), sorted(s[1])) for r, l, s in occ)
            bad.append((occ[0][1], fld, 'KANON',
                        '`%s` alani %d yuzeyde FARKLI bantlaniyor -> %s'
                        % (fld, len(occ), nerede)))
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
    bad = scan(root) + cross_surface(root)
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
