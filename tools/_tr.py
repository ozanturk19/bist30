"""tools/_tr.py -- TURKCE METIN KATLAMA: TEK KANON (84. ders, K-CI'de acildi)

NEDEN BU DOSYA VAR
------------------
Python'da `"İ".lower()` **"i" DEGILDIR**: sonuc iki kod noktasidir --
`"i" + U+0307` (birlesen ustnokta). Yani:

    "İdeal Giriş Penceresi".lower() == "ideal giriş penceresi"   -> False

Bu tuzak repo'da **UC KEZ** bagimsiz olarak kesfedildi ve her seferinde
YORUM olarak saklandi:

  1. `tools/threshold-sync-check.py:115` -- tuzagi dogru teshis etti,
     yaniti `I -> ı` (Turkce-dogru buyuk/kucuk esleme) diye yazdi.
  2. `tools/static-js-text-check.py` (kapi 53, 22.09) -- AYNI tuzaga
     yeniden dustu; R4 kurali ihlalin **kanonik** yazimini ("İdeal Giriş
     Penceresi") hic gormedi. 4/4 sentetik kontrol GECTI, cunku
     orneklemlerin hepsi tesadufen kucuk harfliydi -> **kapi kendi kor
     noktasini yesil kontrolle maskeledi** (e2983af ile duzeltildi).
  3. K-CI (22.09) -- iki uygulamanin **BIRBIRIYLE CELISTIGI** olculdu:

        yazim            threshold-sync     kapi 53      "ideal" bulunur mu?
        ---------------  -----------------  -----------  -------------------
        İdeal Giriş      ideal giriş        ideal giriş  TS ✓   K53 ✓
        IDEAL GIRIS      ıdeal gırıs        ideal giris  TS ✗   K53 ✓
        Ideal Giris      ıdeal giris        ideal giris  TS ✗   K53 ✓
        IDEAL GİRİŞ      ıdeal giriş        ideal giriş  TS ✗   K53 ✓

     `threshold-sync`'in yazimi 5 yazimin 3'unde duser. Kendi icinde
     SIMETRIK kullanildigi (hem etiket hem metin ayni fonksiyondan gecer)
     icin orada canli bug uretmiyor -- ama **"ayni is icin iki kanon"
     basli basina bulgudur** ve bu, ölçüm katmanindaki 4. ornegi.

**84. DERSIN DERSI:** tekrarlanan bir olcum tuzagi tek bir dosyanin
YORUMUNDA degil, paylasilan bir FONKSIYONDA yasamak zorundadir. Bilgi
repoda vardi; paylasilmadigi icin ayni kusur yeni kapida tekrarladi.

HANGI FONKSIYON, NE ZAMAN
-------------------------
`tr_fold(s)`  -- **DESEN ARAMA / KARSILASTIRMA** icin. ASCII'ye dogru
                 AGRESIF katlama: noktali `İ`, noktasiz `I`, `ı` -> hepsi
                 ASCII `i`. Birlesen ustnokta (U+0307) atilir. Bir metnin
                 icinde sabit bir kalibi ("ideal giriş", "premium") ararken
                 BUNU kullan: desen ASCII yazildigi icin arama tarafinin da
                 ASCII'ye inmesi gerekir.

`tr_lower(s)`  -- **GORUNTULEME / TURKCE-DOGRU** kucultme. `I -> ı`,
                 `İ -> i`. Kullaniciya gosterilecek ya da Turkce
                 buyuk/kucuk esligi korunmasi gereken yerlerde kullan.
                 **Desen aramada KULLANMA** (yukaridaki tabloya bak).

`fold_map(items)` -- `{tr_fold(x): x}` sozlugu kurar ve **CAKISMAYI
                 SESSIZ GECMEZ**: iki farkli oge ayni anahtara katlanirsa
                 `ValueError` atar. Agresif katlama teorik olarak cakisma
                 uretebilir; sessizce bir ogeyi kaybetmek yerine patlamasi
                 gerekir (60. ders: dusen adim, hatanin nerede oldugunu
                 kanitlamaz -- ama sessiz kayip hic kanitlamaz).

KENDI KENDINI DOGRULAMA
-----------------------
    python3 tools/_tr.py     # 0 = gecti, 1 = dustu
"""

# Desen aramasi icin: noktali/noktasiz TUM i-ailesi ASCII 'i'ye iner.
# U+0307 (COMBINING DOT ABOVE) atilir -- `"İ".lower()`in urettigi artik.
_FOLD = str.maketrans({
    "İ": "i", "I": "i", "ı": "i", "̇": "",
    "Ş": "ş", "Ğ": "ğ", "Ü": "ü", "Ö": "ö", "Ç": "ç",
})

# Turkce-dogru kucultme: I -> ı (noktasiz), İ -> i (noktali).
_LOWER = str.maketrans({
    "İ": "i", "I": "ı", "̇": "",
    "Ş": "ş", "Ğ": "ğ", "Ü": "ü", "Ö": "ö", "Ç": "ç",
})


def tr_fold(s):
    """Desen arama/karsilastirma icin ASCII'ye agresif katlama."""
    return s.translate(_FOLD).lower().replace("̇", "")


def tr_lower(s):
    """Turkce-dogru kucultme (goruntuleme). Desen aramada kullanma."""
    return s.translate(_LOWER).lower().replace("̇", "")


def fold_map(items):
    """{tr_fold(x): x} -- cakisma olursa ValueError (sessiz kayip yok)."""
    out = {}
    for it in items:
        k = tr_fold(it)
        if k in out and out[k] != it:
            raise ValueError(
                f"tr_fold cakismasi: {out[k]!r} ve {it!r} ayni anahtara "
                f"({k!r}) katlaniyor -- biri sessizce kaybolurdu"
            )
        out[k] = it
    return out


if __name__ == "__main__":
    import sys

    hata = []

    def esit(ad, gercek, beklenen):
        if gercek != beklenen:
            hata.append(f"{ad}: {gercek!r} != {beklenen!r}")

    # 1) tr_fold: "ideal giriş" kalibi BES yazimin HEPSINDE bulunmali.
    #    (84. ders: es-yazim taranmadan bir dedektor dogrulanmis sayilmaz.)
    for y in ["İdeal Giriş Penceresi", "IDEAL GIRIS PENCERESI",
              "ideal giriş penceresi", "Ideal Giris Penceresi",
              "IDEAL GİRİŞ PENCERESİ"]:
        if "ideal giris" not in tr_fold(y).replace("ş", "s"):
            hata.append(f"tr_fold kor: {y!r} -> {tr_fold(y)!r}")

    # 2) tr_fold: U+0307 artigi kalmamali (lower()'in kendi cikti tuzagi).
    esit("U+0307 artigi", "̇" in tr_fold("İİİ"), False)

    # 3) tr_lower: Turkce-dogru yon (I -> ı, İ -> i).
    esit("tr_lower I", tr_lower("IRMAK"), "ırmak")
    esit("tr_lower İ", tr_lower("İZMİR"), "izmir")

    # 4) tr_fold ile tr_lower AYRISMALI -- ayrismazsa iki fonksiyondan
    #    biri gereksizdir ve cagri yerleri yanlis olani secebilir.
    esit("fold/lower ayrismasi", tr_fold("IRMAK") != tr_lower("IRMAK"), True)

    # 5) Diger Turkce harfler her iki yonde de korunur.
    esit("diger harfler", tr_fold("ŞĞÜÖÇ"), "şğüöç")
    esit("diger harfler (lower)", tr_lower("ŞĞÜÖÇ"), "şğüöç")

    # 6) fold_map cakismayi SESSIZ GECMEMELI (pozitif kontrol: bozuk hali
    #    enjekte et -- 60. ders).
    try:
        fold_map(["Ilik", "İlik"])   # ikisi de "ilik"e katlanir
        hata.append("fold_map cakismayi sessiz gecti")
    except ValueError:
        pass
    # ...ve cakismayanda patlamamali (negatif kontrol).
    try:
        m = fold_map(["Güçlü Trend", "Trend Bozuldu", "Yatay"])
        esit("fold_map saglam", len(m), 3)
        # tr_fold yalnizca i-ailesini ASCII'ye indirir; ç/ğ/ö/ş/ü KORUNUR
        # (bunlarda buyuk/kucuk esligi Python'da zaten dogru calisir).
        esit("fold_map anahtar", m["güçlü trend"], "Güçlü Trend")
    except ValueError as e:
        hata.append(f"fold_map saglam halde patladi: {e}")

    if hata:
        print("DUSTU:")
        for h in hata:
            print("  -", h)
        sys.exit(1)
    print("tools/_tr.py kendi kendini dogruladi: 6/6 kontrol GECTI")
    sys.exit(0)
