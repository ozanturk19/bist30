#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
K-CA (22.09.2026) — GORUNEN BIR ORAN, YANINDA YAZAN SAYIYLA AYNI KAYNAKTAN GELIR.

Canli 22.09 olcumu (/api/data, 217 hisse):
  * `rr_ratio` alani 79 hissede DOLU ve 79'unun DA degeri tipatip **2.0**
    (kalan 138 null). Sabit. Cunku TP1 = giris + 2 x risk formulunun
    totolojisi. /karsilastir bu alani "Risk/Ödül (R/R)" diye basiyordu ->
    karsilastirmaya giren HER hisse icin ayni "1 : 2,0".
  * /hisse'deki R/R CUBUGU `risk=|cur-sl|`, `reward=|tp2-cur|` ile
    ciziliyordu. TP2 = cur + 3 x risk oldugu icin oran cebirsel olarak HER
    ZAMAN 3,0: canli DOM'da rr_signal'i olan 55 hissenin 55'inde bar tipatip
    **25% / 75%**. Ustelik ayni kartta, cubugun HEMEN ALTINDA, ayni
    "Risk / Ödül" etiketi altinda `rr_signal` yaziyordu: TKFEN "13,25x",
    MAVI "0,34x". Tek kart, tek etiket, IKI KANON.
  * Ayni buyuklugun YAZIMI da ikiye bolunmustu: /gundem "1:2,0",
    /hisse "2,00x", /karsilastir "1 : 2,0".

CPO-DEV2-045 ayni totolojiyi `rr_now` SAYISINDAN silmisti; BARI ve
/karsilastir satirini birakmisti -- 56. ders: bir kapi, kapattigi kanalin
KOMSUSUNU gormez.

Kapi hatanin YAZIMINI degil KENDISINI arar (52. ders):

  A) SABIT ALANIN TUKETIMI — `rr_ratio` frontend'de hicbir yerde
     okunmamali. (Yorumlar soyulur; kendi belgelendirmen kapiyi
     korlestirmesin.)

  B) ORANI CIZEN CUBUK, YANINDA YAZAN SAYIDAN TURER — `.rr-risk-seg` /
     `.rr-reward-seg` genisliklerini kuran blok `rr_signal`e dayanmali ve
     genislik ifadesi hedef/stop seviyelerinden (`tp1`/`tp2`/`sl`) YENIDEN
     hesap yapmamali.

  C) BASILAN ORANIN ANKRASI VAR — bir oran "13,3" diye tek basina
     basilamaz; 1:N yazimi zorunlu. `rr_signal` formatlanan her satirda
     `1:` bulunmali.

Kullanim:
  python3 tools/rr-canon-check.py             # calisan agac
  python3 tools/rr-canon-check.py --ref SHA   # o commit'in agaci
"""
import os, re, sys, subprocess, tempfile, tarfile, io

SCAN = (('templates', ('.html',)), ('static', ('.js',)))

DEAD_FIELD = re.compile(r'\brr_ratio\b')
SEG        = re.compile(r'rr-(?:risk|reward)-seg')
# genislik kuran atamalar: `let riskW = ...`, `const rewW = ...`, ayrica
# CIPLAK yeniden atama (`riskW = Math.max(...)`) -- yoksa kapinin icinden
# ikinci bir yazimla kacilabilirdi.
WIDTH_ASSIGN = re.compile(
    r'(?:(?:var|let|const)\s+)?\b(?:riskW|rewW|rewardW)\s*=\s*([^;\n]{0,160})')
# Genislik ya ORAN ALANINDAN ya da DIGER GENISLIK DEGISKENINDEN turemeli.
# (`100 - riskW` mesru bir zincir; `risk / total * 100` degil.)
RR_SOURCE    = re.compile(r'rr_?sig', re.I)
WIDTH_CHAIN  = re.compile(r'\b(?:riskW|rewW|rewardW)\b')
# rr_signal'i bicimleyen satir
RR_FMT = re.compile(r'rr_?[sS]ig(?:nal)?[^\n]{0,80}?(?:toFixed\(|\|format\(|toLocaleString\()')


def _blank(t):
    return ''.join('\n' if ch == '\n' else ' ' for ch in t)


def strip_comments(s):
    s = re.sub(r'/\*.*?\*/', lambda m: _blank(m.group(0)), s, flags=re.S)
    s = re.sub(r'\{#.*?#\}', lambda m: _blank(m.group(0)), s, flags=re.S)
    s = re.sub(r'<!--.*?-->', lambda m: _blank(m.group(0)), s, flags=re.S)
    s = re.sub(r'(?<![:\'"\\])//[^\n]*', lambda m: _blank(m.group(0)), s)
    return s


def scan_tree(root):
    bad = []
    for sub, exts in SCAN:
        base = os.path.join(root, sub)
        for dp, _, fns in os.walk(base):
            for fn in sorted(fns):
                if not fn.endswith(exts):
                    continue
                path = os.path.join(dp, fn)
                rel = os.path.relpath(path, root)
                src = strip_comments(open(path, encoding='utf-8', errors='replace').read())

                # ── A) sabit alanin tuketimi ────────────────────────────
                for m in DEAD_FIELD.finditer(src):
                    ln = src[:m.start()].count('\n') + 1
                    bad.append((rel, ln, 'A',
                                "`rr_ratio` okunuyor — bu alan canli evrende SABIT "
                                "(79/79 hissede 2.0). Kanon: `rr_signal`."))

                # ── B) cubuk <-> sayi ayni kaynaktan ────────────────────
                segs = list(SEG.finditer(src))
                if segs:
                    if 'rr_signal' not in src:
                        ln = src[:segs[0].start()].count('\n') + 1
                        bad.append((rel, ln, 'B',
                                    "R/R cubugu ciziliyor ama dosyada `rr_signal` yok — "
                                    "cubuk, yaninda yazan sayidan baska bir seyi gosteriyor."))
                    for wm in WIDTH_ASSIGN.finditer(src):
                        expr = wm.group(1)
                        if RR_SOURCE.search(expr) or WIDTH_CHAIN.search(expr):
                            continue          # oran alanindan / genislik zincirinden: dogru
                        ln = src[:wm.start()].count('\n') + 1
                        bad.append((rel, ln, 'B',
                                    f"cubuk genisligi `{' '.join(wm.group(0).split())[:90]}` — "
                                    f"yaninda YAZAN orandan (`rr_signal`) turemiyor, "
                                    f"bagimsiz bir hesap; ikisi celisebilir."))

                # ── C) basilan oranin 1:N ankrasi ───────────────────────
                for m in RR_FMT.finditer(src):
                    ls = src.rfind('\n', 0, m.start()) + 1
                    le = src.find('\n', m.end())
                    line = src[ls: le if le > 0 else len(src)]
                    if '1:' in line or '1 :' in line:
                        continue
                    ln = src[:m.start()].count('\n') + 1
                    bad.append((rel, ln, 'C',
                                "R/R degeri `1:N` ankrasi olmadan basiliyor — "
                                "cıplak bir oran hangi tarafin 1 oldugunu soylemez."))
    return bad


def tree_at_ref(ref):
    d = tempfile.mkdtemp(prefix='rrcanon-')
    blob = subprocess.check_output(['git', 'archive', ref])
    tarfile.open(fileobj=io.BytesIO(blob)).extractall(d)
    return d


def main():
    ref = None
    if '--ref' in sys.argv:
        ref = sys.argv[sys.argv.index('--ref') + 1]
    root = tree_at_ref(ref) if ref else os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    bad = scan_tree(root)
    tag = f" (ref {ref})" if ref else ""
    if not bad:
        print(f"K-CA OK — R/R tek kanon: cubuk da sayi da `rr_signal`den, yazim 1:N{tag}.")
        return 0
    print(f"K-CA KIRIK — {len(bad)} ihlal{tag}:")
    for rel, ln, kind, msg in sorted(bad):
        print(f"  [{kind}] {rel}:{ln}  {msg}")
    print("\n  Kanon: R/R = rr_signal = (TP1 - sinyal fiyati) / (sinyal fiyati - Supertrend).")
    print("         Gosterilen her R/R -- sayi da, cubuk da -- BU alandan turer; yazim `1:N,N`.")
    return 1


if __name__ == '__main__':
    sys.exit(main())
