#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
K-AR — BANT ESIGI KOPYALARININ KANONIKLE SENKRONU (pre-deploy kapisi)

Neden var: `business_rules.py:derive_adx_label` kendi docstring'inde soyle
diyor: "Bu fonksiyon kanonik kaynaktir; ancak app.py'nin ImportError-fallback'i
ve templates/hisse.html'in JS ilk-render fallback'i esikleri KENDI
KOPYALARINDA tutar (otomatik senkron kilidi YOK, elle esitlenmeli)."
Yani kod, kendi kor noktasini yaziyla ilan ediyordu ama kapisi yoktu.
Bu dosya o kilidi kuruyor.

Yontem — YERE gore degil GOREVE gore tarama: kanonik etiket kumesini
(Zayif/Orta/Guclu/Cok Guclu · Asiri Satim/.../Asiri Alim) tasiyan HER
merdiven ifadesi, app.py ve templates/*.html icinde nerede olursa olsun
bulunur; etiketin yaninda yazan sayi kanonikle karsilastirilir.
Boylece gelecekte ACILAN yeni bir kopya da kendiliginden kapsama girer.

Taban SIFIR.
"""
import re, sys, pathlib

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

ROOT = pathlib.Path(__file__).resolve().parent.parent

LADDERS = {
    "ADX (trend gucu bandi)": {
        "canon_fn": "derive_adx_label",
        # etiket -> kanonik alt sinir (None = taban/else dali)
        "labels": ["Çok Güçlü", "Güçlü", "Orta", "Zayıf"],
        # kanonik fonksiyonun kendi govdesinde degisken "a"/"adx"; JS'te s.adx
        "var": r"^(a|adx|_?adx\w*|\w*\.adx\w*)$",
    },
    "RSI (bolge etiketi)": {
        "canon_fn": "derive_rsi_zone",
        "labels": ["Aşırı Satım", "Dip Toparlanması", "İdeal Giriş Penceresi",
                   "Trend Güçleniyor", "Dikkatli", "Aşırı Alım"],
        "var": r"^(r|rsi|_?rsi\w*|\w*\.rsi\w*)$",
    },
}

def kanonik(fn_name):
    """business_rules.py'deki fonksiyon govdesinden etiket->esik haritasi."""
    src = (ROOT / "business_rules.py").read_text(encoding="utf-8")
    m = re.search(rf"^def {fn_name}\(.*?\n(.*?)(?=^def |\Z)", src, re.S | re.M)
    if not m:
        print(f"  ✗ kanonik fonksiyon bulunamadi: {fn_name}")
        sys.exit(2)
    body = m.group(1)
    sirali = [(op, float(esik), etiket) for op, esik, etiket in re.findall(
        r"if\s+\w+\s*([<>]=?)\s*([0-9.]+)\s*:\s*\n?\s*return\s+\"([^\"]+)\"", body)]
    taban = re.findall(r"\n\s*return\s+\"([^\"]+)\"\s*$", body.rstrip() + "\n")
    return sirali, (taban[-1] if taban else None)


def araliklar(sirali, taban):
    """Kanonik merdivenden etiket -> (alt, ust) araligi. Nesir iddialari
    ('70-80 dikkatli', '40+ Cok Guclu', '18 alti Zayif') bu aralikla olculur.
    Ilk yazimda yalnizca TEK esik tutuluyordu ve dedektor '70-80 dikkatli'
    ifadesini "esik 70, kanonik 80" diye sahte-pozitif raporladi: `<` merdiveni
    UST siniri, `>=` merdiveni ALT siniri yazar."""
    out = {}
    if sirali and sirali[0][0].startswith("<"):          # artan `<` merdiveni
        onceki = None
        for _, esik, etiket in sirali:
            out[etiket] = (onceki, esik)
            onceki = esik
        if taban:
            out[taban] = (onceki, None)
    else:                                                 # azalan `>=` merdiveni
        onceki = None
        for _, esik, etiket in sirali:
            out[etiket] = (esik, onceki)
            onceki = esik
        if taban:
            out[taban] = (None, onceki)
    return out

def merdivenleri_bul(text, labels, degisken_re):
    """Metinde, KARSILASTIRILAN DEGISKENI de yakalayarak sayi->etiket ciftleri.
    JS  : `s.adx >= 40 ? 'Çok Güçlü' : s.adx >= 25 ? 'Güçlü'`
    PY  : `if a >= 40: return "Çok Güçlü"`

    Degisken suzgeci SART: "Güçlü / Orta / Zayıf" kelimeleri sitede ROE, kar
    marji, cari oran gibi TEMEL ANALIZ kartlarinda da kullaniliyor (ornegin
    `f.roe > 20 ? 'Güçlü' : f.roe > 10 ? 'Orta'`). Ilk yazimda suzgec yoktu ve
    dedektor bu 8 satiri "ADX esigi sapmis" diye raporladi -- hepsi sahte
    pozitifti. Bant etiketi TEK BASINA kimlik degildir; olculen BUYUKLUK de
    eslesmeli.
    """
    hits = []
    lbl_alt = "|".join(re.escape(l) for l in labels)
    pat = re.compile(
        r"([A-Za-z_][A-Za-z0-9_.\[\]']{0,24})\s*([<>]=?)\s*([0-9]+(?:\.[0-9]+)?)"
        r"\s*(?::|\?|\)|\s)*\s*(?:return\s+)?['\"](" + lbl_alt + r")['\"]")
    for m in pat.finditer(text):
        if not degisken_re.search(m.group(1)):
            continue
        hits.append((m.group(2), float(m.group(3)), m.group(4), m.start()))
    return hits

# --- 2. KATMAN: DUZ METIN IDDIALARI -------------------------------------
# Esikler sadece kodda degil, kullaniciya gosterilen NESIRDE de tekrar ediliyor:
#   tarama.html : "40+ Cok Guclu, 25-40 Guclu, 18-25 Orta, <18 Zayif"
#   hisse.html  : "30 alti asiri satim, 30-45 dip toparlanmasi, ..."
# 17.09 denetiminde tam bu katman kirikti (RSI tooltip'i 6 bolgeyi 3 bolge diye
# anlatiyordu). Kod dogru olsa bile metin yanlis olabilir -- ayri olculmeli.
NESIR = re.compile(
    r"(?:(?P<alt>[0-9]+(?:[.,][0-9]+)?)\s*(?:-|–|—)\s*(?P<ust>[0-9]+(?:[.,][0-9]+)?)"
    r"|(?P<arti>[0-9]+(?:[.,][0-9]+)?)\s*\+"
    r"|(?P<ustu>[0-9]+(?:[.,][0-9]+)?)\s*üstü"
    r"|(?P<alti>[0-9]+(?:[.,][0-9]+)?)\s*altı"
    r"|&lt;\s*(?P<lt>[0-9]+(?:[.,][0-9]+)?)"
    # 22.09 (K-CN): kanonik yazim artik KOSULU da tasiyor ("45-60 Güçlü Trend
    # sinyalinde İdeal Giriş Penceresi") -- K-BS/K-CB/K-CH'den beri vaat iceren
    # ad, onu doguran kosulla birlikte yaziliyor. Ilk NESIR regex'i etiketi
    # sayinin HEMEN ardinda bekledigi icin bu yazimi DUSURUYORDU: hisse.html
    # RSI tooltip'i kanona cekilince nesir kapsami sessizce 9'dan 8'e indi ve
    # kapi KAPSAM KAYBI verdi. Araya giren "<kosul> sinyalinde" ibaresi ve
    # tire/em-dash sonlandiricisi artik taniniyor -- kapi kanonik yazimi
    # olcmeye devam ediyor.
    r")\s*:?\s*(?:[A-Za-zÇĞİÖŞÜçğıöşü ]{3,30}?\s+sinyalinde\s+)?"
    r"(?P<etiket>[A-Za-zÇĞİÖŞÜçğıöşü ]{3,28}?)(?=[,.;)\n\"—–]|&#10;|$)", re.M)

# Turkce kucultme tuzagi: Python'da "İ".lower() iki kod noktasi uretir
# ("i" + birlesen ustnokta), bu yuzden "İdeal Giriş Penceresi".lower() ==
# "ideal giriş penceresi" KARSILASTIRMASI FALSE doner. Ilk yazimda RSI
# nesrindeki "45-60 ideal giriş penceresi" iddiasi tam bu yuzden sessizce
# kapsam disi kaldi -- dedektor "temiz" diyordu ama o satiri hic olcmemisti.
# 22.09 (K-CI): bu dosyanin yardimcisi tuzagi DOGRU teshis etti ama yaniti
# `I -> ı` (Turkce-dogru buyuk/kucuk esligi) diye yazdi. Olculdu: ASCII bir
# kalibi ("ideal giris") ararken bu yazim 5 es-yazimin 3'unde DUSER
# ("IDEAL GIRIS" -> "ıdeal gırıs"). Burada simetrik kullanildigi icin canli
# bug uretmiyordu, ama kapi 53 ayni ise BASKA bir yanit yazmisti -- "ayni is
# icin iki kanon". Ikisi de tools/_tr.py'ye tasindi.
# `fold_map` ayrica CAKISMAYI SESSIZ GECMEZ: iki farkli etiket ayni anahtara
# katlanirsa biri sessizce kaybolacagi yerde ValueError atar.
from _tr import tr_fold as tr_lower, fold_map


UNI = re.compile(r"\\u([0-9a-fA-F]{4})")

def coz(text):
    """Sablon-ici JS dizgileri Turkce harfleri \\uXXXX kacisiyla tasiyabiliyor
    (ornek hisse.html RSI tooltip'i: "a\\u015f\\u0131r\\u0131 sat\\u0131m").
    Ham metinde arayan HER dedektor bu metni GOREMEZ -- ilk yazimda 6 RSI
    bolgesinden yalniz 1'ini ('70-80 dikkatli', kacissiz olan) yakalamistim.
    Once kacislari coz, sonra ara."""
    return UNI.sub(lambda m: chr(int(m.group(1), 16)), text)


def nesir_kontrol(labels, arlk):
    """Metindeki '<sayi> <etiket>' iddialarini kanonik ARALIKLA karsilastirir."""
    lower = fold_map(labels)
    bulgular, sayac = [], 0
    for f in sorted((ROOT / "templates").glob("*.html")):
        text = coz(f.read_text(encoding="utf-8"))
        for m in NESIR.finditer(text):
            et = tr_lower(m.group("etiket").strip())
            if et not in lower:
                continue
            kanon_et = lower[et]
            if kanon_et not in arlk:
                continue
            alt_k, ust_k = arlk[kanon_et]
            sayac += 1
            iddia = []
            if m.group("alt"):
                iddia = [("alt", float(m.group("alt").replace(",", "."))),
                         ("ust", float(m.group("ust").replace(",", ".")))]
            elif m.group("arti") or m.group("ustu"):
                iddia = [("alt", float((m.group("arti") or m.group("ustu")).replace(",", ".")))]
            elif m.group("alti") or m.group("lt"):
                iddia = [("ust", float((m.group("alti") or m.group("lt")).replace(",", ".")))]
            for yon, deger in iddia:
                beklenen = alt_k if yon == "alt" else ust_k
                if beklenen is None:
                    continue
                if abs(deger - beklenen) > 1e-9:
                    satir = text[:m.start()].count("\n") + 1
                    bulgular.append((f"{f.relative_to(ROOT)}:{satir}", kanon_et, deger,
                                     beklenen, m.group(0).strip()[:60]))
    return bulgular, sayac


def main():
    print("threshold-sync-check (K-AR: bant esigi kopyalari <-> business_rules)")
    hedefler = [ROOT / "app.py"] + sorted((ROOT / "templates").glob("*.html"))
    toplam_kopya = 0
    bulgular = []

    for ad, cfg in LADDERS.items():
        sirali, taban = kanonik(cfg["canon_fn"])
        var_re = re.compile(cfg["var"])
        canon_num = {etiket: esik for _, esik, etiket in sirali}
        print(f"  {ad}: kanonik {cfg['canon_fn']}() -> " +
              " · ".join(f"{e}{op}{v:g}" for op, v, e in sirali))
        for f in hedefler:
            text = f.read_text(encoding="utf-8")
            for op, num, etiket, pos in merdivenleri_bul(text, cfg["labels"], var_re):
                if etiket not in canon_num:
                    continue  # taban/else dali -- sayisi yok
                toplam_kopya += 1
                if abs(num - canon_num[etiket]) > 1e-9:
                    satir = text[:pos].count("\n") + 1
                    bulgular.append(
                        (f"{f.relative_to(ROOT)}:{satir}", ad, etiket, num, canon_num[etiket]))
    print(f"  kanonik disi kopya taranan esik sayisi: {toplam_kopya}")

    nesir_toplam = 0
    for ad, cfg in LADDERS.items():
        sirali, taban = kanonik(cfg["canon_fn"])
        nb, ns = nesir_kontrol(cfg["labels"], araliklar(sirali, taban))
        nesir_toplam += ns
        for yer, etiket, bulunan, beklenen, ham in nb:
            bulgular.append((yer, ad + " [nesir]", etiket, bulunan, beklenen))
    print(f"  kullaniciya gosterilen nesirde taranan esik iddiasi: {nesir_toplam}")

    # KAPSAM TABANI (K-AO dersi): dedektorun "0 sapma" demesi, olctugu sey
    # sayisi dusmediyse anlamlidir. Bir refaktor tooltip'i veya merdiveni
    # dedektorun goremedigi bir bicime sokarsa bu kapi FAIL verir, sessiz
    # kapsam kaybi olmaz. Taban duserse once NEDEN dustugunu olc.
    TABAN_KOD, TABAN_NESIR = 11, 9
    if toplam_kopya < TABAN_KOD or nesir_toplam < TABAN_NESIR:
        print(f"\n  ✗ KAPSAM KAYBI: kod {toplam_kopya}/{TABAN_KOD}, nesir {nesir_toplam}/{TABAN_NESIR}")
        print("    Dedektor daha az sey olcuyor -- 'sapma yok' ciktisi artik kanit degil.")
        return 2

    if bulgular:
        print(f"\n  ✗ {len(bulgular)} SAPMA:")
        for yer, ad, etiket, bulunan, beklenen in bulgular:
            print(f"    {yer}  [{ad}] «{etiket}» esigi {bulunan:g}, kanonik {beklenen:g}")
        return 1
    print("  ✓ tum kopyalar kanonikle ayni")
    return 0

if __name__ == "__main__":
    sys.exit(main())
