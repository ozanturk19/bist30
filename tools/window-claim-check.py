#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
K-CB (22.09.2026) — BEYAN EDILEN PENCERE, GOSTERILEN VERIYLE AYNI OLMALI.

Canli 22.09 olcumu (217 hisse, /api/hisse/<T>/chart + /api/data + /api/karsilastir):

  * /hisse grafigi: GORUNEN sure etiketi (#chartPeriod) bar sayisindan
    DINAMIK turetiliyordu ve kodun yanindaki not "yanlis bir '2 Yil' iddiasi
    hicbir an ekranda durmaz" diyordu -- ama AYNI ogenin `aria-label`i SSR'da
    SABIT "2 yıl" yaziyor ve HIC guncellenmiyordu. DSTKF: 405 bar / 592
    takvim gunu -> goren kullanici "405 İşlem Günü", ekran okuyucu "2 yıl".
    Yazarin ekranda asla gorunmeyecegine yemin ettigi iddia, erisilebilirlik
    agacinda kalicilasmisti.
  * /portfolio sparkline'in erisilebilir adi "Son 30 gün" diyordu; veri
    `ohlc.slice(-30)`, yani 30 SEANS (~42 takvim gunu) ve 30'dan AZ da
    olabilir. AYNI endpoint'in AYNI dilimi /hisse'de "Son 30 seans" diye
    etiketleniyordu: tek veri, iki birim. Ustelik bu metin egrinin TEK metin
    esdegeriydi (K-AI) -- hata dogrudan ekran okuyucuya gidiyordu.
  * 52-hafta barinin kismi dali `bars_used + ' Günlük Aralık'` yaziyordu;
    `bars_used` bir BAR sayacidir (canli: 215/215 hissede 252 -> dal su an
    OLU, ama yazim yanlisti).
Kapi hatanin YAZIMINI degil KENDISINI arar (52. ders):

  A) SSR'DA DONMUS PENCERE IDDIASI — bir `aria-label` icinde LITERAL bir
     sayi + zaman birimi (gün/seans/yıl/hafta/ay) varsa, o ogenin adi JS
     tarafindan guncelleniyor olmalidir (`setAttribute('aria-label'` ayni
     dosyada, ayni id icin). Guncellenmiyorsa iddia donmustur.

  B) PENCERE METNI TEK KANON — bar sayisindan pencere metni ureten esik
     YALNIZ bp-format.js `bpBarWindowText`te yasar. Baska bir dosyada
     "bar sayisi >= N ? <zaman metni> : <zaman metni>" bicimli bir ucul
     (ya da o esigin literali) bulunursa iki kopya var demektir -- ikisi
     ayri ayri kayar, K-CB'nin kok nedeni buydu.

  D) JS'TE KURULAN ERISILEBILIR AD DA VERIDEN TURER — bir `aria-label`
     dize icinde birlestirilerek kuruluyorsa, o ifadeye beslenen degiskenin
     TANIMI da literal bir pencere sayisi tasiyamaz. /portfolio'daki hata
     tam buydu: `aria-label="' + _lbl + '"` masumdu, `_lbl` ise
     `'Son 30 gün: ' + ...` diye kuruluyordu ve veri 30 SEANS'ti. (A ekseni
     yalnizca oznitelikteki literalleri gorur; bu eksen onun kor noktasi.)

Kullanim:
  python3 tools/window-claim-check.py             # calisan agac
  python3 tools/window-claim-check.py --ref SHA   # o commit'in agaci
"""
import os, re, sys, subprocess, tempfile, tarfile, io

SCAN = (('templates', ('.html',)), ('static', ('.js',)))

UNIT = r'(?:gün|Gün|GÜN|seans|Seans|yıl|Yıl|hafta|Hafta|ay|Ay)'
# LITERAL sayi + birim. `{{ ... }}` / `${ ... }` icindeki sayilar literal DEGIL.
ARIA = re.compile(r'aria-label\s*=\s*"([^"]*)"')
LIT_WINDOW = re.compile(r'(?<![\w{$])\d+\s*' + UNIT)
ID_ATTR = re.compile(r'\bid\s*=\s*"([^"]+)"')
SET_ARIA = re.compile(r"setAttribute\(\s*['\"]aria-label['\"]")

# B) bar esigi + iki zaman metni tasiyan ucul
TERNARY = re.compile(
    r'[><]=?\s*(\d{2,4})\s*\?\s*([\'"][^\'"]{0,40}[\'"])\s*:\s*([^;\n]{0,80})')
UNIT_IN_STR = re.compile(r'[\'"][^\'"]*' + UNIT + r'[^\'"]*[\'"]')
CANON_FILE = os.path.join('static', 'bp-format.js')


def _blank(t):
    return ''.join('\n' if ch == '\n' else ' ' for ch in t)


def strip_comments(s):
    s = re.sub(r'/\*.*?\*/', lambda m: _blank(m.group(0)), s, flags=re.S)
    s = re.sub(r'\{#.*?#\}', lambda m: _blank(m.group(0)), s, flags=re.S)
    s = re.sub(r'<!--.*?-->', lambda m: _blank(m.group(0)), s, flags=re.S)
    s = re.sub(r'(?<![:\'"\\])//[^\n]*', lambda m: _blank(m.group(0)), s)
    return s


def strip_py_comments(s):
    s = re.sub(r'"""(?:.|\n)*?"""', lambda m: _blank(m.group(0)), s)
    s = re.sub(r'(?m)^\s*#[^\n]*', lambda m: _blank(m.group(0)), s)
    s = re.sub(r'(?<![\'"])#[^\n]*', lambda m: _blank(m.group(0)), s)
    return s


def _owner_id(src, pos):
    """aria-label'in ait oldugu etiketin id'si (ayni acilis etiketi icinde)."""
    start = src.rfind('<', 0, pos)
    end = src.find('>', pos)
    if start < 0 or end < 0:
        return None
    m = ID_ATTR.search(src[start:end])
    return m.group(1) if m else None


def axis_a(rel, src, bad):
    for m in ARIA.finditer(src):
        val = m.group(1)
        # Jinja/JS enterpolasyonunu cikar: oradaki sayi literal degil
        plain = re.sub(r'\{\{.*?\}\}', ' ', val)
        plain = re.sub(r'\$\{.*?\}', ' ', plain)
        hit = LIT_WINDOW.search(plain)
        if not hit:
            continue
        oid = _owner_id(src, m.start())
        dynamic = False
        if oid:
            for sm in SET_ARIA.finditer(src):
                ctx = src[max(0, sm.start() - 300): sm.start() + 200]
                if oid in ctx:
                    dynamic = True
                    break
        if dynamic:
            continue
        ln = src[:m.start()].count('\n') + 1
        bad.append((rel, ln, 'A',
                    f"erisilebilir ad SABIT bir pencere iddia ediyor: "
                    f"\"{hit.group(0).strip()}\" — veri bu pencereyi tutmayabilir "
                    f"ve bu ad hicbir yerde guncellenmiyor."))


def axis_b(rel, src, bad):
    if rel.replace('\\', '/') == CANON_FILE.replace('\\', '/'):
        return
    for m in TERNARY.finditer(src):
        a, b = m.group(2), m.group(3)
        if UNIT_IN_STR.search(a) and UNIT_IN_STR.search(b):
            ln = src[:m.start()].count('\n') + 1
            bad.append((rel, ln, 'B',
                        f"bar esiginden pencere metni uretiliyor "
                        f"(`{' '.join(m.group(0).split())[:70]}`) — bu esik/yazim "
                        f"YALNIZ bp-format.js `bpBarWindowText`te olmali; "
                        f"ikinci kopya gorunen etiketle erisilebilir adi ayirir."))


ARIA_IN_JS = re.compile(r"""aria-label\s*=\s*\\?['"]""")
CONCAT_ID = re.compile(r"\+\s*([A-Za-z_$][\w$]*)\s*\+")
ASSIGN_TPL = r"(?:var|let|const)\s+%s\s*=\s*([^;\n]{0,200})"


def axis_d(rel, src, bad):
    """aria-label'i KURAN ifadeye beslenen degiskenin tanimi literal pencere
    tasiyamaz (A ekseninin kor noktasi: dizeyle birlestirilen adlar)."""
    for m in ARIA_IN_JS.finditer(src):
        le = src.find('\n', m.end())
        stmt = src[m.end(): le if le > 0 else len(src)]
        for idm in CONCAT_ID.finditer(stmt[:200]):
            name = idm.group(1)
            am = re.search(ASSIGN_TPL % re.escape(name), src)
            if not am:
                continue
            init = am.group(1)
            hit = LIT_WINDOW.search(re.sub(r'\$\{.*?\}', ' ', init))
            if not hit:
                continue
            ln = src[:am.start()].count('\n') + 1
            bad.append((rel, ln, 'D',
                        f"erisilebilir adi kuran `{name}` LITERAL bir pencere "
                        f"tasiyor: \"{hit.group(0).strip()}\" — sayi cizilen "
                        f"veriden gelmeli (dizi uzunlugundan), elle yazilmaktan degil."))


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
                axis_a(rel, src, bad)
                axis_b(rel, src, bad)
                axis_d(rel, src, bad)
    return bad


def tree_at_ref(ref):
    d = tempfile.mkdtemp(prefix='wincl-')
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
        print(f"K-CB OK — pencere beyanlari veriden turuyor{tag}.")
        return 0
    print(f"K-CB KIRIK — {len(bad)} ihlal{tag}:")
    for rel, ln, kind, msg in sorted(bad):
        print(f"  [{kind}] {rel}:{ln}  {msg}")
    print("\n  Kanon: ekranda yazan pencere CIZILEN VERIDEN turer; bar sayisindan")
    print("         pencere metni ureten tek yer bp-format.js `bpBarWindowText`.")
    return 1


if __name__ == '__main__':
    sys.exit(main())
