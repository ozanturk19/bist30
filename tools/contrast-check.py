#!/usr/bin/env python3
"""
K-I  METIN KONTRASTI — BLOKLAYICI, taban SIFIR  (CPO, 20.09.2026)

NEDEN AYRI BIR KAPI
-------------------
20.09'da /404'te olculen bulgu: arama butonu `background:var(--bp-brand)`
(#b8c3ff, acik periwinkle) uzerine `color:#fff` yaziyordu -> **1.71:1**.
WCAG 2.1 AA metin esigi 4.5:1; buton yazisi neredeyse okunmuyordu ve bu
canlida aylarca durdu.

Mevcut kapilarin HICBIRI bunu goremezdi, ucu de AYRI nedenle:
  * css-token-guard -> yorum-ayristirici kazasi dedektoru; renkle ilgilenmez.
  * style-guard K-B  -> yalniz KANONIK-DEGERLI ham hex sayar (token'i olan
    bir rengin hex yazimi). `#fff`in token'i YOK, dolayisiyla K-B'ye hic
    gorunmez.
  * style-guard K-E  -> olu palet DENYLIST'i; `#fff` olu palette degil.
  Yani "ne kanonik ne denylist'te" olan bir renk iki kapinin ARASINDAN
  dusuyordu (bu bosluk 20.09 /sektor-harita turunda dedektor olarak
  kaydedilmisti; bu kapi onu kapatiyor).

Asil nokta su: bulgunun kendisi bir HEX YAZIM meselesi degildi. `#fff`
yerine kanonik `var(--bp-text)` yazilsaydi ihlal AYNEN surecekti (beyaza
yakin metin, acik zemin). Yazim denetleyen bir kapi bu sinifi hic
yakalayamaz — OLCULMESI gereken sey renklerin KENDISI.

OLCUT
-----
Ayni kuralda (veya ayni inline `style` icinde) hem zemin hem metin rengi
YAZILI ise, ikisi cozulup WCAG 2.1 bagil parlaklik kontrasti hesaplanir:
  * varsayilan esik 4.5:1 (AA, normal metin)
  * ayni blokta font-size >= 24px, ya da >= 18.66px + kalin ise 3:1
    (AA, buyuk metin)

KAPSAM SINIRI — ACIKCA BELGELENIYOR (bkz. feedback_kural_da_kanitlanmali)
-------------------------------------------------------------------------
Bu kapi YALNIZCA ikisi de AYNI yerde yazili ciftleri gorur (20.09 olcumu:
80 cift). MIRAS alinan zemin uzerindeki metni (sayfadaki cogu metin)
goremez, cunku zemini statik olarak bilemez. Yari saydam (`rgba` alfa<1)
degerler de ATLANIR: gercek karisim zemine bagli, uydurmak yanlis olur.
Yani bu kapi "sayfa AA uyumlu" DEMEZ; yalnizca yazarin ayni nefeste
belirttigi bir ciftte kendini vurmasini engeller. Tam kapsam icin canli
`getComputedStyle` olcumu hala gerekli.

MUAFIYET: `@media print` bloklari atlanir — orada `#fff`/`#000` zorlamasi
kasitli ve dogrudur (shared.css:96, koyu temayi kagida uygun hale getirir).

Jinja ifadesi (`{{ }}`/`{% %}`) iceren inline style'lar atlanir: degeri
render zamaninda belli olur, statik olarak cozulemez.

POZITIF KONTROL (20.09, olculdu): 404.css'teki fix geri alindiginda kapi
`.search-row button 1.71:1` diyerek FAIL verdi; uc satirlik bir inline
fixture'da her iki dal (CSS + inline) ve buyuk-metin esigi de dogrulandi.
Kapinin TEMIZ demesi ile kuralin dogru olmasi ayni sey degildir.

Kullanim:  python3 tools/contrast-check.py [--verbose] [dosya ...]
Cikis:     0 = temiz, 1 = esik alti cift var (deploy engellenmeli)
"""
import re
import sys
import pathlib

ROOT = pathlib.Path(__file__).resolve().parent.parent

ESIK_NORMAL = 4.5
ESIK_BUYUK = 3.0

_tok_cache = {}


def token_haritasi():
    if _tok_cache:
        return _tok_cache
    src = (ROOT / "static/css/tokens.css").read_text(encoding="utf-8")
    src = re.sub(r"/\*.*?\*/", "", src, flags=re.S)
    for m in re.finditer(r"(--[\w-]+)\s*:\s*([^;]+);", src):
        _tok_cache[m.group(1)] = m.group(2).strip()
    return _tok_cache


def _hex2rgb(h):
    h = h.lstrip("#")
    if len(h) == 3:
        h = "".join(c * 2 for c in h)
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4)) if len(h) >= 6 else None


def coz_renk(v, derinlik=0):
    """var() zincirini cozup (r,g,b) dondurur; cozemezse None (atlanir)."""
    v = v.strip().replace("!important", "").strip()
    if derinlik > 6 or not v:
        return None
    m = re.fullmatch(r"var\((--[\w-]+)(?:\s*,\s*(.+))?\)", v)
    if m:
        t = token_haritasi().get(m.group(1))
        if t:
            return coz_renk(t, derinlik + 1)
        return coz_renk(m.group(2), derinlik + 1) if m.group(2) else None
    if v.startswith("#"):
        return _hex2rgb(v)
    if v == "white":
        return (255, 255, 255)
    if v == "black":
        return (0, 0, 0)
    m = re.fullmatch(
        r"rgba?\(\s*([^,\s]+)[,\s]+([^,\s]+)[,\s]+([^,\s/]+)(?:[,/\s]+([\d.%]+))?\s*\)", v)
    if m:
        alfa = m.group(4)
        if alfa and alfa not in ("1", "1.0", "100%"):
            return None          # yari saydam: gercek karisim zemine bagli
        try:
            return tuple(int(float(m.group(i))) for i in (1, 2, 3))
        except ValueError:
            return None
    return None


def coz_boyut(v, derinlik=0):
    v = v.strip()
    if derinlik > 5:
        return v
    m = re.fullmatch(r"var\((--[\w-]+)(?:\s*,\s*(.+))?\)", v)
    if m:
        t = token_haritasi().get(m.group(1))
        if t:
            return coz_boyut(t, derinlik + 1)
        return coz_boyut(m.group(2), derinlik + 1) if m.group(2) else v
    return v


def _px(v):
    if not v:
        return None
    m = re.match(r"([\d.]+)px", coz_boyut(v.strip()) or "")
    return float(m.group(1)) if m else None


def parlaklik(c):
    def f(v):
        v /= 255
        return v / 12.92 if v <= 0.03928 else ((v + 0.055) / 1.055) ** 2.4
    return 0.2126 * f(c[0]) + 0.7152 * f(c[1]) + 0.0722 * f(c[2])


def kontrast(a, b):
    l1, l2 = parlaklik(a), parlaklik(b)
    return (max(l1, l2) + 0.05) / (min(l1, l2) + 0.05)


def _cift(govde):
    bg = re.search(r"(?:^|;)\s*background(?:-color)?\s*:\s*([^;]+)", govde)
    fg = re.search(r"(?:^|;)\s*color\s*:\s*([^;]+)", govde)
    if not (bg and fg):
        return None
    b = coz_renk(bg.group(1))
    g = coz_renk(fg.group(1))
    if not b or not g:
        return None
    fs = re.search(r"(?:^|;)\s*font-size\s*:\s*([^;]+)", govde)
    fw = re.search(r"(?:^|;)\s*font-weight\s*:\s*([^;]+)", govde)
    boyut = _px(fs.group(1)) if fs else None
    kalin = bool(fw and re.search(r"(bold|[7-9]00)", fw.group(1)))
    esik = ESIK_BUYUK if (boyut and (boyut >= 24 or (boyut >= 18.66 and kalin))) else ESIK_NORMAL
    return b, g, esik, bg.group(1).strip(), fg.group(1).strip()


def tara(dosyalar=None):
    ihlaller, sayac = [], 0
    if dosyalar:
        css = [p for p in dosyalar if p.suffix == ".css"]
        html = [p for p in dosyalar if p.suffix == ".html"]
    else:
        css = sorted(list(ROOT.glob("static/css/*.css")) + list(ROOT.glob("static/css/pages/*.css")))
        html = sorted(ROOT.glob("templates/*.html"))

    for f in css:
        t = re.sub(r"/\*.*?\*/", "", f.read_text(encoding="utf-8"), flags=re.S)
        t = re.sub(r"@media\s+print\s*\{(?:[^{}]|\{[^{}]*\})*\}", "", t)
        for blk in re.finditer(r"([^{}]+)\{([^{}]*)\}", t):
            c = _cift(blk.group(2))
            if not c:
                continue
            sayac += 1
            b, g, esik, bs, gs = c
            oran = kontrast(b, g)
            if oran < esik:
                sel = blk.group(1).strip().splitlines()[-1].strip()
                ihlaller.append((f"{f.relative_to(ROOT)}", sel[:60], bs[:30], gs[:24], oran, esik))

    for f in html:
        t = f.read_text(encoding="utf-8")
        for m in re.finditer(r'style="([^"]*)"', t):
            govde = m.group(1)
            if "{{" in govde or "{%" in govde:
                continue
            c = _cift(";" + govde)
            if not c:
                continue
            sayac += 1
            b, g, esik, bs, gs = c
            oran = kontrast(b, g)
            if oran < esik:
                satir = t[:m.start()].count("\n") + 1
                ihlaller.append((f"{f.relative_to(ROOT)}:{satir}", "(inline style)", bs[:30], gs[:24], oran, esik))
    return ihlaller, sayac


def main():
    argv = [a for a in sys.argv[1:] if not a.startswith("-")]
    verbose = "--verbose" in sys.argv
    ihlaller, sayac = tara([pathlib.Path(a) for a in argv] if argv else None)
    if verbose or ihlaller:
        print(f"K-I kontrast: {sayac} cift degerlendirildi, {len(ihlaller)} esik alti")
    for d, sel, bs, gs, oran, esik in sorted(ihlaller, key=lambda x: x[4]):
        print(f"  FAIL {d}  {sel}\n       bg={bs}  fg={gs}  ->  {oran:.2f}:1  (esik {esik}:1)")
    return 1 if ihlaller else 0


if __name__ == "__main__":
    sys.exit(main())
