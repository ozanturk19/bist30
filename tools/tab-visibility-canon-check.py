#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""KAPI 61 (K-CP, 22.09.2026) -- SEKME/PANEL GORUNURLUGUNDE TEK KANON.

NEDEN BU KAPI VAR
-----------------
K-CP'de /hisse sekme sisteminde UC ayri yer ayni seyi -- "bu bolum simdi
gorunsun mu" -- karar veriyordu:

  1. applyTab()'in `data-tab-content` niteligi uzerinden calisan dongusu
     (gercek kanon: her panel kendi sahibi sekmeyi kendi uzerinde tasir),
  2. ayni fonksiyonun basindaki `ALL_PANELS` / `SHOW_FOR_TAB` ID LISTESI
     (ikinci kanon: uc ID sayiyordu, ai sekmesinin `aiFundSection`ini ve
     haberler sekmesinin `kapSection`ini hic bilmiyordu -- hem eksikti hem
     de 1. adim zaten uzerine yaziyordu, yani etkisizdi),
  3. `renderEntryAnalysis()` icindeki "aktif sekme ozet degilse DOKUNMA ve
     RETURN" erken cikisi (ucuncu kanon).

3 numara 05.09'daki bir sizinti onariminda eklenmisti ve sizintiyi gercekten
kapatiyordu, ama ZAMANI yanlis varsayiyordu: bu IIFE sayfa omrunde en fazla
iki kez (renderSummary cagrilarinda) ve HER IKISI DE applyTab(initial)'den
SONRA calisir. Yani sayfa ?tab=ai / ?tab=grafik / ?tab=haberler ile acildiysa
-- ya da localStorage'daki `bp_hisse_tab` yuzunden oyle acildiysa, ki bir kez
AI sekmesine bakan kullanicinin SONRAKI her hisse sayfasi oyle acilir --
grid HIC doldurulmuyordu. Kullanici Ozet'e tikladiginda applyTab bolumu
goruntuye aliyor, ama icerigi bos kaliyordu.

CANLI OLCUM (22.09, BIMAS -- AL sinyali + entry_quality DOLU):
    ?tab=ozet  -> eqBadge 45 / rrBar 228 / rrLevels 1632 karakter
                  (SL 400,06 · Simdi 432,25 · TP1 496,63 · TP2 528,82 · 1:2,0)
    ?tab=ai    -> Ozet'e gecilince UCU DE 0 karakter; ekranda yalniz
                  "DEGERLENDIRME" ve "RISK / ODUL" etiketleri asili kaliyor.
Sinyalsiz hissede de ayni: "aktif sinyal yok" aciklamasi hic basilmiyordu.

DERS (K-turu ortak mercegi): "ayni is icin iki kanon" basli basina bulgudur.
Gorunurluk TEK yerden yonetilir; render fonksiyonu icerigi KOSULSUZ uretir,
bolum gizliyse kullanici gormez.

NE OLCULUR
----------
R1  `data-tab-content` tasiyan bir panelin ID'sine JS'ten `style.display`
    yazilmasi (ikinci kanon). Kapi hatanin YAZIMINI degil KENDISINI arar:
    getElementById / querySelector / degisken uzerinden yazim, hepsi.
R2  role="tab" olan bir ogenin `aria-controls`unda gecen her ID, ya
    `data-tab-content` tasimali ya da tasiyan bir panelin ID'si olmali --
    aksi halde sekme, applyTab'in hic bilmedigi bir bolumu sahipleniyordur.
R3  `data-tab-content` degerleri, ayni dosyadaki VALID_TABS listesi (+
    "always") ile birebir tutmali. Yeni bir sekme adi yazim hatasiyla
    girerse panel HICBIR sekmede gorunmez.
R4  Render/ciz fonksiyonlarinin sekme durumunu sorgulamasi
    (`a.active` seciciyle veya `aria-selected` okuyarak) yasak -- gorunurluk
    karari applyTab'e aittir. Muaf: applyTab'in kendisi ve sekme dugmelerini
    yoneten blok.
"""
import os
import re
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TPL = os.path.join(ROOT, "templates")

_RE_U = re.compile(r"\\u([0-9a-fA-F]{4})")
def coz(s):
    return _RE_U.sub(lambda m: chr(int(m.group(1), 16)), s)


def _tpl_files():
    out = []
    for fn in sorted(os.listdir(TPL)):
        if fn.endswith(".html"):
            out.append((fn, os.path.join(TPL, fn)))
    return out


def _read(path, ref=None, rel=None):
    if ref:
        try:
            return subprocess.check_output(
                ["git", "show", "%s:%s" % (ref, rel)], cwd=ROOT,
                stderr=subprocess.DEVNULL).decode("utf-8", "replace")
        except subprocess.CalledProcessError:
            return None
    with open(path, encoding="utf-8") as f:
        return f.read()


_RE_PANE = re.compile(r'data-tab-content\s*=\s*"([^"]*)"')
_RE_TAB = re.compile(r'<a[^>]*role\s*=\s*"tab"[^>]*>', re.I)
_RE_ARIA_CTRL = re.compile(r'aria-controls\s*=\s*"([^"]*)"')
_RE_VALID = re.compile(r"VALID_TABS\s*=\s*\[([^\]]*)\]")
_RE_ACTIVE_SEL = re.compile(r"""querySelector(?:All)?\(\s*['"][^'"]*a\.active[^'"]*['"]""")
_RE_ARIA_SEL_READ = re.compile(r"""getAttribute\(\s*['"]aria-selected['"]\s*\)""")
# atama: `.style.display =` ; karsilastirma degil (`== === != !==`)
_RE_DISP_ASSIGN = re.compile(r"style\.display\s*(?<![=!])=(?!=)")


def _id_of_line(line):
    m = re.search(r'\bid\s*=\s*"([^"]+)"', line)
    return m.group(1) if m else None


_RE_VAR_BIND = re.compile(
    r"""(?:var|let|const)\s+(\w+)\s*=\s*document\.getElementById\(\s*['"]([^'"]+)['"]""")


def _strip_comments(lines):
    """87. ders: kapi hatanin YAZIMINI degil kendisini arar.

    Bir yorumda gecen `section.style.display='block'` -- ornegin bu bulgunun
    kendi aciklama blogu -- IHLAL DEGILDIR; tersine, gercek ihlal degisken
    uzerinden yazildigi icin gozden kacabilir. Yorum satirlari ve Jinja
    yorumlari bosaltilir (satir numaralari korunur)."""
    out, in_block, in_jinja = [], False, False
    for line in lines:
        s = line
        if in_block:
            if "*/" in s:
                s, in_block = s.split("*/", 1)[1], False
            else:
                out.append("")
                continue
        if in_jinja:
            if "#}" in s:
                s, in_jinja = s.split("#}", 1)[1], False
            else:
                out.append("")
                continue
        # tek satirlik bloklar
        s = re.sub(r"/\*.*?\*/", " ", s)
        s = re.sub(r"\{#.*?#\}", " ", s)
        if "/*" in s:
            s, in_block = s.split("/*", 1)[0], True
        if "{#" in s:
            s, in_jinja = s.split("{#", 1)[0], True
        # `//` yorumu -- dize icindeki `https://` yanlis kesmesin diye kaba filtre
        m = re.search(r"(?<![:'\"])//", s)
        if m:
            s = s[:m.start()]
        out.append(s)
    return out


def _display_writers(text, pane_ids):
    """R1: panel ID'sine JS'ten style.display yazimi (ikinci kanon).

    Degisken izleme AKIS SIRALIDIR: `const sec = getElementById('x')` bagi,
    ayni adla yeni bir bag kurulana kadar gecerli kalir. Sabit N-satirlik
    pencere (ilk yazim) gercek ihlali kaciriyordu: /hisse'de bag 2464'te,
    yazimlar 2486/2499/2511'deydi."""
    hits = []
    lines = _strip_comments(text.splitlines())
    bind = {}
    for i, line in enumerate(lines, 1):
        raw = coz(line)
        for m in _RE_VAR_BIND.finditer(raw):
            bind[m.group(1)] = m.group(2)
        if "style.display" not in raw:
            continue
        # ATAMA mi karsilastirma mi: `.style.display =` evet; `== === != !==` hayir
        if not _RE_DISP_ASSIGN.search(raw):
            continue
        # a) ayni satirda dogrudan panel ID'si
        hit = None
        for pid in pane_ids:
            if re.search(r"""['"]%s['"]""" % re.escape(pid), raw):
                hit = pid
                break
        # b) panele bagli bir degisken uzerinden
        if hit is None:
            for var, pid in bind.items():
                if pid in pane_ids and re.search(
                        r"\b%s\s*\.style\.display\s*(?<![=!])=(?!=)" % re.escape(var), raw):
                    hit = pid
                    break
        if hit:
            hits.append((i, hit, raw.strip()[:150]))
    return hits


def _applytab_span(text):
    """applyTab govdesi + sekme dugmesi blogu (R4 muafiyeti)."""
    m = re.search(r"function applyTab\s*\(", text)
    if not m:
        return (0, 0)
    start = text[:m.start()].count("\n") + 1
    # applyTab'i iceren IIFE'nin sonuna kadar: `window.applyTab = applyTab;`
    m2 = re.search(r"window\.applyTab\s*=\s*applyTab", text)
    end = (text[:m2.start()].count("\n") + 1) if m2 else start + 120
    return (start, end)


def scan_file(rel, text):
    viol = []
    panes = {}          # id -> owners
    for i, line in enumerate(text.splitlines(), 1):
        if "data-tab-content" in line:
            m = _RE_PANE.search(line)
            if m:
                pid = _id_of_line(line)
                panes[pid or "#anonim@%d" % i] = (m.group(1).split(), i)
    if not panes:
        return viol, 0

    pane_ids = {p for p in panes if not p.startswith("#")}

    # R3 — deger sozlugu
    mv = _RE_VALID.search(text)
    valid = set()
    if mv:
        valid = set(re.findall(r"""['"]([^'"]+)['"]""", mv.group(1)))
    allowed = valid | {"always"}
    if valid:
        for pid, (owners, ln) in panes.items():
            for o in owners:
                if o not in allowed:
                    viol.append((rel, ln, "R3",
                                 "%s: data-tab-content=\"%s\" -- VALID_TABS disinda (%s)"
                                 % (pid, o, ", ".join(sorted(allowed)))))

    # R2 — aria-controls paritesi
    for i, line in enumerate(text.splitlines(), 1):
        for tag in _RE_TAB.findall(line):
            mc = _RE_ARIA_CTRL.search(tag)
            if not mc:
                continue
            for cid in mc.group(1).split():
                if cid not in pane_ids:
                    viol.append((rel, i, "R2",
                                 'role="tab" aria-controls="%s" -- bu ID '
                                 "data-tab-content tasimiyor, applyTab onu "
                                 "hic gormuyor" % cid))

    # R1 — ikinci kanon: panel ID'sine display yazimi
    for ln, pid, frag in _display_writers(text, pane_ids):
        viol.append((rel, ln, "R1",
                     "%s: data-tab-content'li panele JS'ten style.display "
                     "yaziliyor (ikinci kanon) -- %s" % (pid, frag)))

    # R4 — render tarafinda sekme durumu sorgusu
    a, b = _applytab_span(text)
    for i, line in enumerate(text.splitlines(), 1):
        if a <= i <= b:
            continue
        raw = coz(line)
        if _RE_ACTIVE_SEL.search(raw) or _RE_ARIA_SEL_READ.search(raw):
            viol.append((rel, i, "R4",
                         "applyTab disinda aktif-sekme sorgusu -- gorunurluk "
                         "karari render fonksiyonuna sizmis: %s" % raw.strip()[:120]))
    return viol, len(panes)


def run(ref=None, verbose=False):
    viol, panes_total, files = [], 0, 0
    for rel_fn, path in _tpl_files():
        rel = "templates/" + rel_fn
        text = _read(path, ref, rel)
        if text is None:
            continue
        files += 1
        v, n = scan_file(rel, text)
        viol += v
        panes_total += n
        if verbose and n:
            print("  girdi: %-34s %d panel" % (rel, n))
    return viol, panes_total, files


def self_test():
    """Pozitif kontrol (85. ders) -- bozuk hali ENJEKTE et, yazimi arama."""
    cases = [
        ("R1", '<div id="p1" data-tab-content="ozet"></div>\n'
               '<script>var VALID_TABS=["ozet"];function applyTab(t){}\n'
               'window.applyTab=applyTab;\n'
               "document.getElementById('p1').style.display='block';</script>"),
        ("R1", '<div id="p2" data-tab-content="ozet"></div>\n'
               '<script>var VALID_TABS=["ozet"];function applyTab(t){}\n'
               'window.applyTab=applyTab;\n'
               "const sec = document.getElementById('p2');\n"
               "if (sec) sec.style.display = 'block';</script>"),
        ("R2", '<a role="tab" aria-controls="yokPanel">X</a>\n'
               '<div id="p3" data-tab-content="ozet"></div>\n'
               '<script>var VALID_TABS=["ozet"];</script>'),
        ("R3", '<div id="p4" data-tab-content="ozett"></div>\n'
               '<script>var VALID_TABS=["ozet"];</script>'),
        ("R4", '<div id="p5" data-tab-content="ozet"></div>\n'
               '<script>var VALID_TABS=["ozet"];function applyTab(t){}\n'
               'window.applyTab=applyTab;\n'
               "const a=document.querySelector('.bp-segments-inner a.active');</script>"),
    ]
    ok = 0
    for want, src in cases:
        got = [c for _r, _l, c, _m in scan_file("sentetik.html", src)[0]]
        print("  [%s] %-4s enjekte -> %s" % ("OK" if want in got else "FAIL", want, got or "-"))
        ok += want in got
    neg = [
        # dogru kanon: gorunurluk yalniz applyTab icinde, render kosulsuz
        '<a role="tab" aria-controls="p9">X</a>\n'
        '<div id="p9" data-tab-content="ozet"></div>\n'
        '<script>var VALID_TABS=["ozet"];\n'
        'function applyTab(t){document.querySelectorAll("[data-tab-content]")'
        '.forEach(function(p){p.style.display="";});}\n'
        'window.applyTab=applyTab;\n'
        'document.getElementById("p9").innerHTML="x";</script>',
        # display OKUMA yazim degildir
        '<div id="p10" data-tab-content="ozet"></div>\n'
        '<script>var VALID_TABS=["ozet"];function applyTab(t){}\n'
        'window.applyTab=applyTab;\n'
        'var v = document.getElementById("p10").style.display !== "none";</script>',
    ]
    for src in neg:
        got = [c for _r, _l, c, _m in scan_file("sentetik.html", src)[0]]
        print("  [%s] NEGATIF temiz kanon -> %s" % ("OK" if not got else "FAIL", got or "-"))
        ok += not got
    return 0 if ok == len(cases) + len(neg) else 1


def main():
    if "--self-test" in sys.argv:
        print("KAPI 61 pozitif/negatif kontrol:")
        return self_test()
    ref = None
    if "--ref" in sys.argv:
        ref = sys.argv[sys.argv.index("--ref") + 1]
    verbose = "--verbose" in sys.argv or "-v" in sys.argv
    viol, panes, files = run(ref, verbose)
    if panes == 0:
        print("KAPI 61 KOR -- 0 sekme paneli ayristirildi (93. ders)")
        return 1
    if viol:
        print("KAPI 61 -- SEKME GORUNURLUGUNDE IKINCI KANON: %d" % len(viol))
        print("Gorunurlugun tek kanonu applyTab'in `data-tab-content` dongusudur;")
        print("render fonksiyonu icerigi KOSULSUZ uretir, panel gizliyse gorulmez.\n")
        for rel, ln, code, msg in sorted(viol):
            print("  %s:%s  [%s]" % (rel, ln, code))
            print("      %s" % msg)
        return 1
    print("KAPI 61 OK -- sekme gorunurlugu tek kanonda (%d panel / %d sablon)"
          % (panes, files))
    return 0


if __name__ == "__main__":
    sys.exit(main())
