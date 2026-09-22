#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
tools/static-js-text-check.py -- KAPI 53 (K-CH, 22.09)

SORU -- daha once HIC sorulmadi:
  Tarayiciya GONDERILEN paylasilan JS dosyalari (`static/**/*.js`) hangi metin
  kapisinin girdisinde?  Cevap: HICBIRININ.
    * kapi 50 `intraday-claim-check`      -> yalniz `templates/`
    * kapi 51 `blog-claim-check`          -> yalniz `blog_content.py`
    * kapi 52 `app-published-text-check`  -> yalniz `app.py`
    * `glyph-canon-check`/`legal-text-sync`/... -> yalniz `templates/`
  `copy-promise-check` static'e BAKAR ama yalniz "vaat" kalibi arar; sozluk
  tanimlarini, emekli terimleri, skor adlarini gormez.

BULDUGU (K-CH, canli 22.09 -- ikisi de `static/learning-mode.js`):
  1. Ogrenme Modu sozlugu RSI 45-60 bandini KOSULSUZ "ideal giris penceresi"
     diye tanimliyordu. Urun o adi K-BS/CPO-1745'ten beri yalniz Guclu Trend
     sinyalinde basiyor. Canli: bantta 46 hisse, 45'i Guclu Trend DEGIL ->
     ekran "Notr Bolge" derken sozluk "ideal giris penceresi" diyordu.
  2. `tier_score` tanimi "Premium/Plus/Standart" diyordu: "Premium" 22.08'de
     emekli edildi (K-CG, 80. ders) ve bu, urunun yayimlanan TUM metninde
     kalan TEK canli ornekti -- cunku hicbir kapi bu dosyayi okumuyordu.

== 83. DERS -- "KANAL ENVANTERI" TARAYICIYA INEN HER DOSYAYI KAPSAR ==
80. ders e-posta kanalini bulmustu. Ayni acik burada tekrarladi: emekli bir
sozcuk, HTML'den temizlenip `static/*.js` icinde yasamaya devam etti. Bir
kanal "sablon degil" diye degil, "kullaniciya ULASMIYOR" diye kapsam disi
birakilabilir -- ve paylasilan JS kullaniciya ulasir.

KURALLAR (taban SIFIR):
  R1  emekli "Premium" sozcugu           (kanon: ⭐ Hacim Onayli / tier)
  R2  💎 glifi                            (urunde "Yuksek Skor" demek; 81. ders)
  R3  kanon disi skor adi                 (kanon: Teknik Guc Skoru / BorsaPusula Skoru)
  R4  RSI bandi -> "Ideal Giris" esleme KOSULSUZ yazilmis
      (kanon: yalniz Guclu Trend sinyalinde; digerlerinde Notr Bolge)

77. DERS UYGULAMASI -- YALNIZ DIZE LITERALLERI:
  JS yorumlari YAYIMLANMAZ. Repo'nun olcum notlari yorumlarda emekli terimleri
  bilerek anar (`bp-format.js` "Ideal Giris" karsilastirmasini, `bp-search.js`
  "alt premium CTA" notunu). Bu yuzden dosya HAM GREP'lenmez: elle yazilmis bir
  JS tarayicisi ile yorumlar ve regex literalleri ATILIR, yalnizca '...' "..."
  `...` icerikleri kurala sokulur.

VERI ANAHTARI MUAFIYETI (K-BD dersi -- beyaz liste anahtari DIZENIN KENDISI,
satir numarasi DEGIL): tam-esitlikle kanonik bir bolge/alan adi olan dize
(`'Ideal Giris'` gibi) bir karsilastirma anahtaridir, nesir degildir.

Kullanim: python3 tools/static-js-text-check.py [--verbose]
Cikis: ihlal varsa 1.
"""
import os, re, sys, pathlib

ROOT = pathlib.Path(__file__).resolve().parent.parent

# --- kapsam: tarayiciya inen, elle yazilmis paylasilan JS -------------------
def hedefler():
    out = []
    for p in sorted((ROOT / "static").rglob("*.js")):
        rel = p.relative_to(ROOT).as_posix()
        if p.name.endswith(".min.js"):      # ucuncu parti, bizim metnimiz degil
            continue
        if "/vendor/" in "/" + rel:
            continue
        out.append(p)
    return out

# --- 77. ders: yalniz dize literalleri --------------------------------------
# Elle yazilmis JS tarayicisi. Yorumlari ve regex literallerini atar.
# Regex/bolme ayrimi: bir '/' ancak onceki ANLAMLI karakter bir deger
# SONLANDIRMIYORSA regex baslatir (standart sezgisel).
_DEGER_SONU = set(")]}") | set("abcdefghijklmnopqrstuvwxyz"
                               "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_$")

def dizeleri_cikar(src):
    """[(satir_no, dize_icerigi)] dondurur."""
    out, i, n = [], 0, len(src)
    satir = 1
    onceki_anlamli = ""
    while i < n:
        c = src[i]
        if c == "\n":
            satir += 1; i += 1; continue
        # yorumlar
        if c == "/" and i + 1 < n and src[i+1] == "/":
            while i < n and src[i] != "\n":
                i += 1
            continue
        if c == "/" and i + 1 < n and src[i+1] == "*":
            j = src.find("*/", i + 2)
            j = n if j < 0 else j + 2
            satir += src.count("\n", i, j)
            i = j; continue
        # regex literali
        if c == "/" and onceki_anlamli not in _DEGER_SONU:
            i += 1; kacis = False; sinif = False
            while i < n:
                ch = src[i]
                if kacis: kacis = False
                elif ch == "\\": kacis = True
                elif ch == "[": sinif = True
                elif ch == "]": sinif = False
                elif ch == "/" and not sinif: i += 1; break
                elif ch == "\n": break
                i += 1
            onceki_anlamli = "/"
            continue
        # dize / sablon literali
        if c in "'\"`":
            tirnak = c; bas = satir; i += 1; buf = []; kacis = False
            while i < n:
                ch = src[i]
                if kacis:
                    buf.append(ch); kacis = False
                elif ch == "\\":
                    kacis = True
                elif ch == tirnak:
                    i += 1; break
                else:
                    if ch == "\n":
                        satir += 1
                        if tirnak != "`":     # kapanmamis tek satir dizesi
                            break
                    buf.append(ch)
                i += 1
            out.append((bas, "".join(buf)))
            onceki_anlamli = tirnak
            continue
        if not c.isspace():
            onceki_anlamli = c
        i += 1
    return out

# --- kurallar ---------------------------------------------------------------
# tam-esitlikle muaf: karsilastirma anahtari olan kanonik adlar (nesir degil)
VERI_ANAHTARLARI = {
    "İdeal Giriş", "İdeal Giriş Penceresi", "Nötr Bölge", "Nötr Bölge (RSI 45-60)",
    "premium", "is_premium", "tier", "only_premium",
}

# ⛔ 84. DERS -- PYTHON'DA `"İ".lower()` "i" DEGILDIR
# `"İ".lower()` == "i" + U+0307 (birlesik ustnokta). Yani `"ideal giriş" in
# dize.lower()` testi, dizede KANONIK yazimla ("İdeal Giriş") gecen bir adi
# GORMEZ. Bu kapinin ilk yazimi tam bu tuzaga dustu: 4/4 sentetik pozitif
# gecti cunku sentetiklerin ve fix-oncesi agacin HEPSI kucuk harfliydi --
# oysa ihlalin DAHA OLASI yazimi buyuk harfli olandir. Eslesme artik
# `_tr_kucult` uzerinden: noktali İ ve noktasiz I, ASCII i'ye indirgenir.
# (18.09 RVOL dersinin ayni ailesi: bir iddia, es-yazimlarin HEPSI taranmadan
# dogrulanmis sayilmaz.)
# ⛔ DERSIN DERSI: `tools/threshold-sync-check.py:115` bu tuzagi ZATEN
# belgelemisti -- ve tam ayni kusur, ayni kanon adinda ('İdeal Giriş'),
# yeni yazilan bu kapida TEKRARLADI. Bilgi repoda duruyordu ama PAYLASILAN
# BIR YARDIMCIDA degil, tek bir dosyanin yorumunda yasiyordu. Tekrarlanan
# bir olcum tuzagi, yorum olarak degil FONKSIYON olarak saklanmalidir.
_TR_HARITA = str.maketrans({
    "İ": "i", "I": "i", "ı": "i", "\u0307": "",
})

def _tr_kucult(s):
    return s.translate(_TR_HARITA).lower().replace("\u0307", "")


KANON_SKOR_ADLARI = ("Teknik Güç Skoru", "BorsaPusula Skoru")
KANON_DISI_SKOR = re.compile(
    r"(Sinyal\s+Skoru|Sinyal\s+kalite\s+puan[ıi]|Kalite\s+Puan[ıi]|Güç\s+Puan[ıi])",
    re.IGNORECASE)

def kurallari_uygula(dize):
    """[(kural, aciklama)]"""
    bulgular = []
    if dize.strip() in VERI_ANAHTARLARI:
        return bulgular
    d = dize
    dl = _tr_kucult(d)

    if re.search(r"\bPremium\b", d):
        bulgular.append(("R1", 'emekli "Premium" sozcugu (kanon: ⭐ Hacim Onaylı / tier)'))
    if "💎" in d:
        bulgular.append(("R2", "💎 glifi -- urunde \"Yuksek Skor\" demek (81. ders)"))
    m = KANON_DISI_SKOR.search(d)
    if m and not any(k in d for k in KANON_SKOR_ADLARI):
        bulgular.append(("R3", 'kanon disi skor adi "%s" (kanon: Teknik Güç Skoru)' % m.group(1)))
    if "ideal giris" in dl.replace("ş", "s") and "45" in d \
            and "guclu trend" not in dl.replace("ü", "u").replace("ç", "c"):
        bulgular.append(("R4", 'RSI bandi -> "İdeal Giriş" eslemesi KOSULSUZ yazilmis '
                               '(kanon: yalniz Güçlü Trend sinyalinde)'))
    return bulgular

def main():
    verbose = "--verbose" in sys.argv
    ihlal = 0
    taranan = 0
    for p in hedefler():
        rel = p.relative_to(ROOT).as_posix()
        src = p.read_text(encoding="utf-8")
        taranan += 1
        for satir, dize in dizeleri_cikar(src):
            for kural, aciklama in kurallari_uygula(dize):
                ihlal += 1
                kisa = dize if len(dize) <= 110 else dize[:110] + "…"
                print("IHLAL %s  %s:%d  %s" % (kural, rel, satir, aciklama))
                print("        » %s" % kisa.replace("\n", " "))
    if verbose:
        print("taranan dosya: %d" % taranan)
    if ihlal:
        print("\nstatic-js-text-check: %d ihlal (taban 0)" % ihlal)
        return 1
    print("static-js-text-check: OK (%d dosya, 0 ihlal)" % taranan)
    return 0

if __name__ == "__main__":
    sys.exit(main())
