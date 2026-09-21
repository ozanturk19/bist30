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
    # ── B) CSS'te notr arm eksik ────────────────────────────────────────
    cssroot = os.path.join(root, 'static', 'css')
    for dp, _, fns in os.walk(cssroot):
        for fn in fns:
            if not fn.endswith('.css'):
                continue
            path = os.path.join(dp, fn)
            rel = os.path.relpath(path, root)
            src = strip_comments(open(path, encoding='utf-8', errors='replace').read())
            has_pos = re.search(r'\.(up|chg-pos|pos-pnl|sum-green|score-positive)\b\s*[,{ ]', src)
            has_neg = re.search(r'\.(down|dn|chg-neg|neg-pnl|sum-red|score-negative)\b\s*[,{ ]', src)
            has_neu = re.search(r'\.(neu|chg-neu|neu-pnl|sum-neutral|score-neutral)\b\s*[,{ ]', src)
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
