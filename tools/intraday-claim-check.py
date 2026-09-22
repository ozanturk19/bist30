#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""KAPI 50 (K-CE, 22.09) — GUN-ICI / GERCEK-ZAMANLI IDDIA DEDEKTORU.

NEDEN BU KAPI VAR
-----------------
BorsaPusula'nin veri mimarisi CPO-1508/1512/1703 ile **EOD-only**: `/api/data`
gunde TEK kez, seans kapanisindan sonra yazilir. Yani bu payload'dan turetilen
HICBIR sayi gun ici degildir; `change_pct` her zaman tamamlanmis bir gunun
kapanis-kapanis degisimidir. Site bunu /yasal ve /hakkinda'da yazili olarak
BEYAN ediyor: "fiyatlar gercek zamanli DEGILDIR ... son kapanis".

K-CE'de bu beyanla celisen 5 canli yuzey bulundu:
  * /          "Gün İçi En Çok Hareket Edenler"  (ayni sayfa ayni alani
               "Son kapanışta ne oldu?" diye adlandiriyordu)
  * /portfolio meta description + og + twitter: "anlık değer"  (x3 kanal)
  * /hakkinda  "anlık değer"  -- AYNI SAYFANIN 62 satir asagisindaki
               "gerçek zamanlı değildir" beyaniyla celisiyordu

Bu kapi bu SINIFI arar, o cumlelerin YAZIMINI degil (52. ders): sozluk
mimari olarak IMKANSIZ olan iddialardan olusur, dolayisiyla dogru pozitif
orani tanim geregi 1'dir.

NE TARANIR
----------
Sablonlarin GORUNUR metni + meta/og/twitter `content=` govdeleri.
Jinja `{# #}`, HTML `<!-- -->`, JS `/* */` ve `//` yorumlari SOYULUR --
gerekce notlari kapiyi tetiklemesin (56. ders).

MUAFIYET (beyaz liste degil, ANLAM kurali -- 43. ders)
------------------------------------------------------
* "gün içinde" / "N gün içinde"  -> sure ifadesi ("... zarfinda"), gun-ici DEGIL.
* "gerçek zamanlı" + yakininda olumsuzlama ("değil") -> DOGRU beyanin ta kendisi.
* "anlık kayıt/görüntü/kare"     -> snapshot anlami; /ozet arsiv sayfasi boyle
                                    kullaniyor ve DOGRU.
"""
import os, re, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TPL  = os.path.join(ROOT, "templates")

# --- mimari olarak imkansiz iddialar ---
# 1) "gün içi" (ama "gün içinde" DEGIL: sure zarfi)
RE_GUNICI = re.compile(r"gün[\s\-]?içi(?!nde)", re.IGNORECASE)
# 2) "anlık <finansal isim>" -- "anlık kayıt/görüntü/kare" (snapshot) haric
RE_ANLIK  = re.compile(
    r"anlık\s+(?!kayıt|kaydı|kaydını|görüntü|görüntüsü|kare|karesi)"
    r"(fiyat\w*|değer\w*|veri\w*|kur\w*|hacim\w*|seviye\w*|tutar\w*)",
    re.IGNORECASE)
# 3) "gerçek zamanlı" -- olumsuzlanmamis hali
RE_GZ     = re.compile(r"gerçek\s+zamanlı", re.IGNORECASE)
RE_GZ_NEG = re.compile(r"değil", re.IGNORECASE)
# 4) "canlı fiyat/veri" (makro seridi GERCEKTEN canli oldugu icin "canlı" tek
#    basina taranmaz; yalniz FIYAT/HISSE verisine baglanan hali)
RE_CANLI  = re.compile(r"canlı\s+(fiyat\w*|hisse\s+veri\w*|borsa\s+veri\w*)",
                       re.IGNORECASE)

# --- MUAFIYET: ayni metin parcasi iddiayi ZATEN olumsuzluyor/emekliye ayiriyor.
#     Bu bir beyaz liste DEGIL, anlam kurali (43. ders: beyaz liste anahtari
#     satir numarasi olamaz). Ornek dogru kullanim, /hakkinda yol haritasi:
#       "🔚 Canlı fiyat akışı (SSE) — EOD-only mimariye geçişle retire edildi"
#     Burada cumle ozelligin YOKLUGUNU beyan ediyor; bir vaat degil.
RE_DISCLAIM = re.compile(
    r"değildir|değil\b|retire|kaldırıl|iptal|sunulm[au]|sunmuyor|"
    r"sağlanmıyor|desteklenmiyor|yoktur|planlanmıyor",
    re.IGNORECASE)

def strip_comments(src):
    src = re.sub(r"\{#.*?#\}", "", src, flags=re.S)
    src = re.sub(r"<!--.*?-->", "", src, flags=re.S)
    src = re.sub(r"/\*.*?\*/", "", src, flags=re.S)
    src = re.sub(r"(?m)^\s*//.*$", "", src)
    return src

def visible_segments(src):
    """(satir_no, metin) — gorunur metin dugumleri + meta content govdeleri."""
    out = []
    for m in re.finditer(r">([^<>]{1,600})<", src):
        out.append((src[:m.start()].count("\n") + 1, m.group(1)))
    for m in re.finditer(r"""<meta\b[^>]*?content=["']([^"']{1,600})["']""",
                         src, re.I | re.S):
        out.append((src[:m.start()].count("\n") + 1, m.group(1)))
    # JS string literalleri icindeki kullanici metni (innerHTML ile basilanlar)
    for m in re.finditer(r"""(['"`])((?:\\.|(?!\1)[^\\\n])*)\1""", src):
        t = m.group(2)
        if len(t) > 3:
            out.append((src[:m.start()].count("\n") + 1, t))
    return out

def scan_text(t):
    hits = []
    # Iddiayi ayni parcada olumsuzlayan/emekliye ayiran metin ihlal degildir.
    if RE_DISCLAIM.search(t):
        return hits
    if RE_GUNICI.search(t):
        hits.append(('gun-ici', RE_GUNICI.search(t).group(0)))
    m = RE_ANLIK.search(t)
    if m:
        hits.append(('anlik-finansal', m.group(0)))
    for m in RE_GZ.finditer(t):
        tail = t[m.end(): m.end() + 40]
        if not RE_GZ_NEG.search(tail):
            hits.append(('gercek-zamanli', m.group(0)))
    m = RE_CANLI.search(t)
    if m:
        hits.append(('canli-fiyat', m.group(0)))
    return hits

def main():
    argv = sys.argv[1:]
    targets = [a for a in argv if not a.startswith("-")]
    files = ([os.path.join(ROOT, p) for p in targets] if targets else
             sorted(os.path.join(TPL, f) for f in os.listdir(TPL)
                    if f.endswith(".html")))
    viol = []
    for path in files:
        try:
            src = open(path, encoding="utf-8").read()
        except OSError:
            continue
        src = strip_comments(src)
        rel = os.path.relpath(path, ROOT)
        seen = set()
        for line, text in visible_segments(src):
            for kind, frag in scan_text(text):
                key = (rel, line, kind, frag.lower())
                if key in seen:
                    continue
                seen.add(key)
                viol.append((rel, line, kind, frag, text.strip()[:110]))
    if viol:
        print("KAPI 50 — GUN-ICI / GERCEK-ZAMANLI IDDIA: %d IHLAL" % len(viol))
        print("Mimari EOD-only (CPO-1508/1512/1703): /api/data gunde TEK tur,")
        print("kapanistan sonra. /yasal + /hakkinda 'gercek zamanli DEGILDIR,")
        print("son kapanis' diye BEYAN ediyor. Asagidaki metinler bu beyanla celisiyor.\n")
        for rel, line, kind, frag, ctx in viol:
            print("  %s:%d  [%s] %r" % (rel, line, kind, frag))
            print("      ... %s" % ctx)
        print("\nDogru kanon: 'son kapanış' / 'güncel'.")
        return 1
    print("KAPI 50 OK — gun-ici/gercek-zamanli iddia yok (%d sablon)" % len(files))
    return 0

if __name__ == "__main__":
    sys.exit(main())
