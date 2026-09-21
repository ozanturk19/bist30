#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
K-AQ — ROZET GLIFI <-> KANONIK ANLAM CAKISMASI (pre-deploy kapisi)

Neden var (21.09, canli olculdu):
  * /tarama filtresi "💎 Premium (Guclu Trend + Hacim Onayli)" diyordu ama
    satirlardaki 💎 rozeti tier=='guclu_sinyal' (Teknik Guc Skoru 70+) idi.
    Filtre 5 satir donduruyordu ve 5'inde de 💎 YOKTU -- kullanicinin sectigi
    glif sonuclarda hic gorunmuyordu.
  * /hisse sayfasinda RSI<30 icin de 💎 basiliyordu ("💎 Asiri Satim").
    Canli: 217 hissenin 86'si su anda RSI<30 -> hepsinde ayni glif UCUNCU
    bir anlamda. Ornek: /hisse/EMKEL (Trend Bozuldu) "RSI 10,9 💎 Asiri Satim".

Kural: asagidaki gliflerin her biri SITE GENELINDE TEK bir sey demektir.
Bir glifin gectigi her yerde, ayni etikette/tooltip'te o anlamin anahtar
kelimelerinden en az biri gecmelidir. Gecmiyorsa cakisma vardir -> FAIL.

Kasitli istisna: GOZDEN_GECIRILMIS sozlugune GEREKCESIYLE ekle, sessizce
kaldirma.
"""
import re, sys, pathlib

TPL = pathlib.Path(__file__).resolve().parent.parent / "templates"

# glif -> (kanonik ad, bu glifin YANINDA/tooltip'inde gecmesi beklenen anahtarlar)
KANON = {
    "💎": ("Teknik Guc Skoru bandi (70+ Yuksek Skor / 56-69 Orta Skor)",
           ("Teknik Güç Skoru", "Yüksek Skor", "Orta Skor", "rozet")),
    "⭐": ("Hacim Onayli (Guclu Trend sinyali + RVOL >= 1,20)",
           ("Hacim Onaylı", "Hacim onaylı", "RVOL")),
}

# dosya:satir -> gerekce  (kasitli, gozden gecirilmis istisnalar)
GOZDEN_GECIRILMIS = {
    "hisse.html:1617": "JS bolum yorumu — kullaniciya gorunmez (⭐ Portfolio toggle basligi)",
}

# bir glifin "etiketi": ayni HTML etiketindeki data-tip + glifi iceren metin parcasi
TAG_RE = re.compile(r"<[^<>]*>")

def satir_baglami(line: str, idx: int) -> str:
    """Glifin etrafindaki anlam tasiyan metin: icinde bulundugu <tag ...> tam
    ozniteligi + glifin iki yanindaki 120 karakter + ayni satirdaki data-tip."""
    parca = line[max(0, idx - 140): idx + 140]
    tipler = " ".join(re.findall(r'data-tip(?:ped)?="([^"]*)"', line))
    tipler += " " + " ".join(re.findall(r'data-tooltip="([^"]*)"', line))
    tipler += " " + " ".join(re.findall(r'aria-label="([^"]*)"', line))
    return parca + " " + tipler

def main() -> int:
    print("glyph-canon-check (K-AQ: rozet glifi <-> kanonik anlam)")
    bulgular = []
    sayac = {g: 0 for g in KANON}
    for f in sorted(TPL.glob("*.html")):
        for no, line in enumerate(f.read_text(encoding="utf-8").splitlines(), 1):
            for glif, (ad, anahtarlar) in KANON.items():
                start = 0
                while True:
                    i = line.find(glif, start)
                    if i < 0:
                        break
                    start = i + 1
                    sayac[glif] += 1
                    anahtar = f"{f.name}:{no}"
                    if anahtar in GOZDEN_GECIRILMIS:
                        continue
                    ctx = satir_baglami(line, i)
                    if not any(a in ctx for a in anahtarlar):
                        bulgular.append((anahtar, glif, ad, ctx.strip()[:150]))

    for g, (ad, _) in KANON.items():
        print(f"  {g} = {ad}  ->  {sayac[g]} kullanim")

    if bulgular:
        print(f"\n  ✗ {len(bulgular)} CAKISMA:")
        for anahtar, glif, ad, ctx in bulgular:
            print(f"    {anahtar}  {glif} kanonik olarak «{ad}» demek, ama burada o anlam yok:")
            print(f"        …{ctx}…")
        return 1
    print("  ✓ cakisma YOK")
    return 0

if __name__ == "__main__":
    sys.exit(main())
