#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
K-BP (21.09.2026) — DEGISIM SIFIRSA YON RENGI YOKTUR.

Yesil (--bp-al) "yukselis", kirmizi (--bp-sat) "dusus" vaadidir; "+" bir
kazanc ima eder. **0 bunlarin hicbiri degildir.** Sitede ayni is icin IKI
kanon vardi:
  (a) `x > 0 ? AL : x < 0 ? SAT : NOTR`  -> /tarama, /gundem, /sektor-harita
  (b) `x >= 0 ? AL : SAT`                -> /karsilastir, /portfolio, /ozet,
                                            /hisse, anasayfa serit, blog widget
21.09 canli kanit (/api/data, 217 hisse): ALARK/DOAS/ARCLK/CEMTS/ISMEN
change_pct = 0. AYNI GUN AYNI HISSE -> /tarama "0,00%" gri rgb(199,197,205),
/karsilastir "+0,00%" YESIL rgb(0,226,144). Site kendi kendisiyle celisiyordu.
/portfolio'da ayni sinif daha da sik goruluyordu: pozisyon guncel fiyattan
eklendiginde K/Z TAM SIFIRDIR ve "+0,00 ₺" YESIL yaziliyordu.

Kanon: bp-format.js -> bpDir / bpDirSign / bpDirColor / bpDirClass /
bpFormatPct / bpZero. Yon, EKRANDA GORUNEN ondaliga yuvarlanmis sayidan
turer (K-BO dersi: esiklenen sayi = okunan sayi).

IKI DESEN:
  A) `<sey> >= 0 ?` / `<sey> <= 0 ?` / `var up = <sey> >= 0;` (ya da Jinja
     `{% if x >= 0 %}`) —
     yani SIFIRIN bir YONLE ayni kefeye konmasi — ve yakininda (140 ch)
     bir yon isareti: --bp-al/--bp-sat (veya ham hex), 'up'/'down'/'dn',
     pos-pnl/neg-pnl, sum-green/sum-red, chg-pos/chg-neg, "'+'".
  B) CSS: bir dosyada yon CIFTI tanimliysa (.up + .down/.dn) ama NOTR arm
     (.neu / -neutral / .chg-neu) YOKSA -> ucuncu hal yazilmamis demektir.
     (karsilastir.css'te tam olarak bu vardi.)

Yorumlar soyulur (kendi belgelendirmen kapiyi korlestirmesin), satir sonlari
KORUNUR (K-BO dersi 35: yoksa rapor edilen satir no kayar).

Kullanim:
  python3 tools/direction-zero-check.py             # calisan agac
  python3 tools/direction-zero-check.py --ref SHA   # o commit'in agaci
"""
import os, re, sys, subprocess, tempfile, tarfile, io

DIR_MARK = re.compile(
    r"--bp-al\b|--bp-sat\b|#00e290|#f85149|#ff7875"
    r"|'up'|\"up\"|'down'|\"down\"|'dn'|\"dn\""
    r"|pos-pnl|neg-pnl|sum-green|sum-red|chg-pos|chg-neg"
    r"|score-positive|score-negative"
    r"|'\+'|\"\+\"|'pozitif'|'negatif'|\"pozitif\"|\"negatif\"", re.I)

# SIFIRI BIR YONE KATAN karsilastirma. `> 0` / `< 0` uc-yollu yazimin parcasi
# olabilir, onlara DOKUNMAYIZ; suclu olan `>= 0` ve `<= 0`.
JS_PAT    = re.compile(r"[\w\.\[\]\(\)\$]{1,40}\s*(?:>=|<=)\s*0\b\s*\?")
# 36. ders (K-BO): AYNI ISIN DEGISKENE ATANMIS HALI AYRI BIR YAZIMDIR.
# `var up = s.change_pct >= 0;` ... `up ? '--bp-al' : '--bp-sat'` ternary
# ICERMEDIGI icin JS_PAT'e takilmaz — ama tam olarak ayni hatadir.
JS_ASSIGN = re.compile(r"(?:var|let|const)\s+\w{1,30}\s*=\s*[\w\.\[\]\(\)\$]{1,40}\s*(?:>=|<=)\s*0\s*[;,\)]")
JINJA_PAT = re.compile(r"\{%-?\s*(?:el)?if\s+[^%]{0,80}(?:>=|<=)\s*0\s*%\}")

# ── K-CC (22.09): KAPININ UC KOR NOKTASI ───────────────────────────────────
# 22.09'da kapi "OK" derken anasayfada DORT canli ihlal duruyordu:
#   index.html:280/334  {{ 'var(--bp-al)' if x >= 0 else 'var(--bp-sat)' }}
#   index.html:725      var chg = s.change_pct, chgUp = ... chg >= 0;
#   index.html:848      var pos = s.score >= 0;   (kullanim 400 ch sonra)
# Ucu de ayni hatayi yapiyordu; kapi uc AYRI nedenle goremedi:
#   (i)   JINJA_PAT yalnizca `{% if %}` blogunu ariyordu, SATIR-ICI
#         `{{ ... if ... else ... }}` ifadesini degil.
#   (ii)  JS_ASSIGN `var|let|const` ISTIYORDU; virgullu ikinci bildirim
#         (`var a = ..., b = x >= 0;`) hic eslesmedi.
#   (iii) PROX=140 karakter: karar ile yon isareti arasinda 14 satir vardi.
#         Degiskene atanan bir karar dosyanin HERHANGI bir yerinde
#         kullanilabilir — yakinlik penceresi bu sinifa uygulanamaz.
# ⛔ DERS (66): DEGISKENE ATANAN KARARDA "YAKINLIK" BIR OLCU DEGILDIR;
#    atamayi ADIYLA takip et, kullanim yerinde yon isareti ara.

# Satir-ici Jinja kosulu: `{{ A if <x> >= 0 else B }}`
JINJA_INLINE = re.compile(r"\{\{[^{}]{0,240}?(?:>=|<=)\s*0[^{}]{0,240}?\}\}")
# Jinja/Python KOSULSUZ isaretli bicim: `'%+.2f'|format(x)` -> 0 icin "+0,00"
SIGNED_FMT = re.compile(r"['\"]%\+[#0-9.]*[fdg]")
# Adi ne olursa olsun "<ad> = <sey> >= 0" atamasi (var/let/const SART DEGIL).
# NOT: gövde `[^;,\n]` — virgullu cok-bildirimli satirda (`var a = x, b = y >= 0`)
# adin ILKINE degil, karsilastirmaya EN YAKIN olanina baglanmasi icin.
ANY_ASSIGN = re.compile(r"\b(\w{1,30})\s*=\s*(?!=)[^;,\n]{0,80}?(?:>=|<=)\s*0\b")

# ── 52. ders (K-BW, 22.09): `a >= b` DE AYNI HATADIR ────────────────────────
# Yukaridaki uc desen de SIFIR LITERALINI arar. Ama yon cogu zaman iki sayinin
# KARSILASTIRMASIDIR ve o zaman ortada yazili bir `0` YOKTUR:
#     var up = last >= first;          <- /hisse sparkline, 22.09'a kadar canli
#     close >= open ? '--bp-al' : ...  <- doji mumu (a4d710f)
# `last == first` -> "degisim 0" demektir; yesile boyamak K-BP'nin yasakladigi
# seyin ta kendisi. Kapi bunu goremedigi icin sparkline aylarca gecti.
# ⛔ DERS: BIR KAPI, HATANIN OGRENDIGI YAZIMINI DEGIL, HATANIN KENDISINI
#    ARAMALIDIR. `x >= 0` ile `a >= b` ayni karardir.
#
# Yanlis alarmi dar tutan uc kosul birlikte aranir:
#   (i)  iki taraf da SAYI LITERALI degil (indeks/uzunluk kiyaslari elenir),
#   (ii) ya yon adli bir degiskene atanmis ya da bir ternary'nin kosulu,
#   (iii) 140 karakter icinde bir YON ISARETI var (DIR_MARK).
_OPND = r"[\w\.\[\]\(\)\$]{1,40}"
NONZERO_ASSIGN = re.compile(
    r"(?:var|let|const)\s+(?:is)?(?:up|down|dn|rising|falling|pos|neg|dir|yon)\w{0,10}"
    r"\s*=\s*(" + _OPND + r")\s*(?:>=|<=)\s*(" + _OPND + r")\s*[;,\)]", re.I)
NONZERO_TERN = re.compile(
    r"(" + _OPND + r")\s*(?:>=|<=)\s*(" + _OPND + r")\s*\?")
_NUMLIT = re.compile(r"^-?\d+(?:\.\d+)?$")
PROX = 140

ALLOW = {
    # Kanonun KENDISI: bp-format.js icinde 0 ile karsilastirma yapilir.
    'static/bp-format.js',
}

def _blank(t):
    return ''.join('\n' if ch == '\n' else ' ' for ch in t)

def strip_comments(s):
    s = re.sub(r'/\*.*?\*/', lambda m: _blank(m.group(0)), s, flags=re.S)
    s = re.sub(r'\{#.*?#\}', lambda m: _blank(m.group(0)), s, flags=re.S)
    s = re.sub(r'<!--.*?-->', lambda m: _blank(m.group(0)), s, flags=re.S)
    # // yorumlari: URL'lerin // sini yakalamamak icin basinda : olmayanlar
    s = re.sub(r'(?<![:\'"\\])//[^\n]*', lambda m: _blank(m.group(0)), s)
    return s

def scan_tree(root):
    bad = []
    # ── A) iki-yollu yon dali ────────────────────────────────────────────
    for sub, exts in (('templates', ('.html',)), ('static', ('.js',))):
        base = os.path.join(root, sub)
        for dp, _, fns in os.walk(base):
            for fn in fns:
                if not fn.endswith(exts):
                    continue
                path = os.path.join(dp, fn)
                rel = os.path.relpath(path, root)
                if rel in ALLOW:
                    continue
                src = strip_comments(open(path, encoding='utf-8', errors='replace').read())
                # ── D) satir-ici Jinja kosulu: yon isareti AYNI {{ }} icinde ──
                for m in JINJA_INLINE.finditer(src):
                    hit = DIR_MARK.search(m.group(0))
                    if not hit:
                        continue
                    ln = src[:m.start()].count('\n') + 1
                    bad.append((rel, ln, 'D',
                                f"satir-ici Jinja kosulu `{' '.join(m.group(0).split())[:90]}` "
                                f"-> 0 bir YONLE ayni kefede (kanon: _fmt_macros.html)"))
                # ── E) kosulsuz isaretli bicim: 0 da '+' aliyor ───────────
                if rel.startswith('templates' + os.sep):
                    for m in SIGNED_FMT.finditer(src):
                        ln = src[:m.start()].count('\n') + 1
                        bad.append((rel, ln, 'E',
                                    f"`{m.group(0)}` KOSULSUZ isaret basar -> degismeyen "
                                    f"deger \"+0,00\" olur (kanon: _fmt_macros.html pct_text)"))
                # ── F) degiskene atanan karar: ADIYLA takip et ────────────
                for m in ANY_ASSIGN.finditer(src):
                    name = m.group(1)
                    if name in ('i', 'j', 'n'):
                        continue
                    for u in re.finditer(r"[(\s!]" + re.escape(name) + r"\s*\?", src):
                        win = src[max(0, u.start() - PROX): u.end() + PROX]
                        hit = DIR_MARK.search(win)
                        if not hit:
                            continue
                        ln = src[:m.start()].count('\n') + 1
                        bad.append((rel, ln, 'F',
                                    f"`{' '.join(m.group(0).split())[:70]}` -> `{name} ? ...` "
                                    f"(satir {src[:u.start()].count(chr(10))+1}) yaninda yon "
                                    f"isareti `{hit.group(0)}` (kanon: bp-format.js bpDir*)"))
                        break
                for pat in (JS_PAT, JS_ASSIGN, JINJA_PAT):
                    for m in pat.finditer(src):
                        win = src[max(0, m.start() - PROX): m.end() + PROX]
                        hit = DIR_MARK.search(win)
                        if not hit:
                            continue
                        ln = src[:m.start()].count('\n') + 1
                        bad.append((rel, ln, 'A',
                                    f"`{' '.join(m.group(0).split())}` + yon isareti "
                                    f"`{hit.group(0)}` -> 0 bir YONLE ayni kefede "
                                    f"(kanon: bp-format.js bpDir*)"))
                # ── C) sifir literali OLMADAN ayni karar: `a >= b` ──────────
                for pat in (NONZERO_ASSIGN, NONZERO_TERN):
                    for m in pat.finditer(src):
                        lhs, rhs = m.group(1), m.group(2)
                        if _NUMLIT.match(lhs) or _NUMLIT.match(rhs):
                            continue          # indeks/uzunluk kiyasi, yon degil
                        win = src[max(0, m.start() - PROX): m.end() + PROX]
                        hit = DIR_MARK.search(win)
                        if not hit:
                            continue
                        ln = src[:m.start()].count('\n') + 1
                        bad.append((rel, ln, 'C',
                                    f"`{' '.join(m.group(0).split())}` + yon isareti "
                                    f"`{hit.group(0)}` -> ESITLIK (fark = 0) bir YONLE "
                                    f"ayni kefede (kanon: bp-format.js bpDir*)"))
    # ── B) CSS'te notr arm eksik ────────────────────────────────────────
    cssroot = os.path.join(root, 'static', 'css')
    for dp, _, fns in os.walk(cssroot):
        for fn in fns:
            if not fn.endswith('.css'):
                continue
            path = os.path.join(dp, fn)
            rel = os.path.relpath(path, root)
            src = strip_comments(open(path, encoding='utf-8', errors='replace').read())
            # K-CC: desen `-pos/-neg/-neu` VE `-up/-down/-neu` sonekli her
            # cifti kapsar (index.css'te `.da-tile-pos/.da-tile-neg` cifti
            # notr armsiz duruyordu; sabit ad listesi bunu goremiyordu).
            has_pos = re.search(r'\.[\w-]*(?:up|pos|green|positive)\b\s*[,{ ]', src)
            has_neg = re.search(r'\.[\w-]*(?:down|dn|neg|red|negative)\b\s*[,{ ]', src)
            has_neu = re.search(r'\.[\w-]*(?:neu|neutral)\b\s*[,{ ]', src)
            if has_pos and has_neg and not has_neu:
                ln = src[:has_pos.start()].count('\n') + 1
                bad.append((rel, ln, 'B',
                            f"yon CIFTI tanimli (`{has_pos.group(0).strip(' ,{')}` + "
                            f"`{has_neg.group(0).strip(' ,{')}`) ama NOTR arm yok -> "
                            f"0 zorunlu olarak bir yon rengi aliyor"))
    return bad

def tree_at_ref(ref):
    d = tempfile.mkdtemp(prefix='dirzero-')
    blob = subprocess.check_output(['git', 'archive', ref])
    tarfile.open(fileobj=io.BytesIO(blob)).extractall(d)
    return d

def main():
    ref = None
    if '--ref' in sys.argv:
        ref = sys.argv[sys.argv.index('--ref') + 1]
    root = tree_at_ref(ref) if ref else os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    bad = scan_tree(root)
    if not bad:
        print(f"K-BP OK — yon ekseninde sifir hicbir yerde bir yonle ayni kefede degil"
              f"{' (ref '+ref+')' if ref else ''}.")
        return 0
    print(f"K-BP KIRIK — {len(bad)} ihlal{' (ref '+ref+')' if ref else ''}:")
    for rel, ln, kind, msg in sorted(bad):
        print(f"  [{kind}] {rel}:{ln}  {msg}")
    print("\n  Kanon: static/bp-format.js -> bpDir / bpDirSign / bpDirColor /")
    print("         bpDirClass / bpFormatPct / bpZero  (>0 AL · <0 SAT · =0 NOTR)")
    return 1

if __name__ == '__main__':
    sys.exit(main())
