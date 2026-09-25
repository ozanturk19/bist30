#!/usr/bin/env python3
"""K-BN — "gosterilen fiyat ne kadar taze?" iddia kapisi.

BULGUNUN KOKENI (21.09, CPO turu). Site EOD-only mimaride: `app.py`
`background_refresh()` icindeki dongu CPO-1508/1512 ile "900s canli dongu
kaldirildi -- ana refresh artik islem gunu basina BIR KEZ, kapanistan sonra
(18:10+ TR)" der. `lib/trading_calendar.market_open()` ise 10:00-17:59 TR.
Yani SEANS BOYUNCA gosterilen fiyat bir ONCEKI kapanistir.

CANLI KANIT (21.09 Pzt 09:07 TR, /var/log/bist30-refresh.log):
  "Disk cache yuklendi: 217 hisse (updated_at=18.09.2026 18:14:33)"
  -> Pazartesi sabahi servis edilen fiyat ~63 SAAT eskiydi.

BUNA RAGMEN uc yuzey kullaniciya alt-gunluk tazelik vaat ediyordu:
  * /yasal (HUKUKI sayfa): "fiyatlar ... ~15 dakika gecikmeli olabilir"
  * _footer.html veri rozeti (fiyat gosteren 12 sayfa): "BIST resmi yayin
    gecikmesi yaklasik 15 dakika"  -- rakam BIST'in kendi yayini icin dogru,
    ama kullanici onu BIZIM fiyatimizin yasi diye okuyor
  * hisse.html tazelik cipi: `age < 300` dalinda 'BIST ~15dk gecikmeli'
Ayni sitenin /hakkinda, /metodoloji, /tarama, /gundem ve index sayfalari ise
dogru olani ("gun sonu", "seans icinde guncellenmez") soyluyordu -- TEK ISE
IKI KANON.

OLCUT
  Kullaniciya gorunen metinde (HTML + sablon-ici JS dizgileri; yorumlar
  soyulur) su iddialar ARANIR:
    1. ALT-GUNLUK GECIKME RAKAMI  ("~15 dakika gecikmeli", "15 dk gecikme",
       "5 saniye gecikmeli" ...) -> KOSULSUZ ihlal. EOD-only'de hicbir
       alt-gunluk rakam gosterdigimiz fiyati tarif etmez.
    2. TAZELIK IDDIASI ("gercek zamanli", "anlik fiyat", "canli fiyat") ->
       yalnizca AYNI CUMLEDE KESIN olumsuzlama varsa (degil/olmaz/hicbir
       zaman/retire) gecerli. "olmayabilir"/"olabilir" gibi TEREDDUTLU
       olumsuzlama ihlaldir: kesin olan bir seyi olasilik gibi sunar.

PREMISE KONTROLU (kural da kanitlanmali)
  Kapinin kurali "cadence EOD-only" varsayimina dayanir. `app.py` icindeki
  EOD imzasi (`_should_run_eod` + `_EOD_POLL_INTERVAL`) kaybolursa kapi
  PASS/FAIL vermez, "cadence degismis, kural yeniden olculmeli" diye DUSER --
  sessizce yanlis kurali dayatmaz.

KAPSAM SINIRI: yalnizca templates/*.html ve tazelik metni yazan paylasilan
JS (static/stale-banner.js). Verinin GERCEKTEN taze olup olmadigini
olcmez -- yalnizca "ne vaat ediliyor" sinifini kapatir.
"""
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

HEDEFLER = sorted(ROOT.glob("templates/*.html")) + [ROOT / "static" / "stale-banner.js"]

# --- yorum soyucular (K-BL dersi: satir sayisini KORU) -------------------
_HTML_YORUM = re.compile(r"<!--.*?-->", re.S)
_JINJA_YORUM = re.compile(r"\{#.*?#\}", re.S)
_BLOK_YORUM = re.compile(r"/\*.*?\*/", re.S)
# K-BL dersi: regex literali bilmeyen soyucu ilk `//`den sonra her seyi yiyordu.
_SATIR_YORUM = re.compile(r"(^|[^:\\])//[^\n]*")


# C-27 (25.09): kanon §1 + §2.7 (Ozan O16b=B not 3) ana sayfa kahramanında
# GÜN SONU kapanışının altında, yalnız seans içinde görünen ve makro şerit
# (/api/macro, gün içi 15 dk gecikmeli akış) verisini gösteren satırı AÇIKÇA
# ister: "Seans içi · 15 dk gecikmeli". Bu satır EOD fiyatını değil gün içi
# akışı tarif eder. Muafiyet yapısaldır: yalnız `data-intraday` işaretli TEK
# öğenin (iç içe aynı etiket yok) metni; işaretsiz aynı cümle ihlal kalır
# (sentetik pozitif + negatif aşağıda).
_SEANS_ICI = re.compile(r"<(\w+)\b[^>]*\bdata-intraday\b[^>]*>.*?</\1\s*>", re.S)


def _bosluga_cevir(m):
    """Eslesmeyi ayni uzunlukta bosluga cevir -> satir/sutun numaralari kayar."""
    return re.sub(r"[^\n]", " ", m.group(0))


# Oznitelik metni de kullaniciya gorunur (ipucu/ekran okuyucu/SEO aciklamasi) —
# etiketi soyarken kaybolmasin diye ONCE cikarilip AYRI taranir.
_GORUNUR_OZNITELIK = re.compile(
    r"""\b(?:data-tip|title|aria-label|alt|content|placeholder)\s*=\s*(["'])(.*?)\1""", re.S | re.I)


def soy(metin: str) -> str:
    """Yorumlari VE etiketleri ayni uzunlukta bosluga cevirir.

    Etiketler de soyulur cunku iddia cumlesi etiketle BOLUNEBILIR
    ("gecikmesi yaklasik <strong>15 dakika</strong>" — K-BN'in asil footer
    vakasi tam buydu ve etiket-duyarli ilk yazim bunu KACIRDI). Uzunluk
    korundugu icin satir/sutun numaralari kaymaz.
    """
    metin = _HTML_YORUM.sub(_bosluga_cevir, metin)
    metin = _JINJA_YORUM.sub(_bosluga_cevir, metin)
    metin = _SEANS_ICI.sub(_bosluga_cevir, metin)
    metin = _BLOK_YORUM.sub(_bosluga_cevir, metin)
    metin = _SATIR_YORUM.sub(lambda m: m.group(1) + " " * (len(m.group(0)) - len(m.group(1))), metin)
    # oznitelik degerleri KALSIN, geri kalan etiket govdesi bosluga cevrilsin
    def _etiket(m):
        govde = m.group(0)
        out = list(re.sub(r"[^\n]", " ", govde))
        for a in _GORUNUR_OZNITELIK.finditer(govde):
            i0, i1 = a.span(2)
            out[i0:i1] = list(a.group(2))
        return "".join(out)

    # ⛔ KAPININ ILK YAZIMININ KOR NOKTASI (kapi kendi pozitif kontrolunde
    # yakalandi): etiket soyucusu `<script>` govdesine de giriyordu ve JS'teki
    # KARSILASTIRMA operatorlerini etiket saniyordu — `age > 900 ... age < 300`
    # arasindaki her sey "etiket" diye bosluga cevrilip 'BIST ~15dk gecikmeli'
    # dizgisi TAMAMEN yok oluyordu (hisse.html ihlali sessizce kaciyordu).
    # Cozum: script govdeleri etiket soyucusundan MUAF, yalnizca yorumlari
    # soyulmus haliyle taranir.
    parcalar, son = [], 0
    for m in re.finditer(r"<script\b[^>]*>.*?</script\s*>", metin, re.S | re.I):
        parcalar.append(re.sub(r"<[^>]+>", _etiket, metin[son:m.start()]))
        parcalar.append(m.group(0))          # script govdesi OLDUGU GIBI
        son = m.end()
    parcalar.append(re.sub(r"<[^>]+>", _etiket, metin[son:]))
    return "".join(parcalar)


# --- iddia desenleri -----------------------------------------------------
# 1) alt-gunluk gecikme rakami
GECIKME_RE = re.compile(
    r"\d{1,3}\s*(?:dk|dakika|saniye|sn|saat)\w*\s*(?:</strong>\s*)?"
    r"(?:\w+\s+){0,2}?gecikme\w*"
    r"|gecikme\w*\s*(?:\w+\s+){0,3}?(?:</strong>\s*)?\d{1,3}\s*(?:dk|dakika|saniye|sn|saat)\b",
    re.I)

# 2) tazelik iddiasi
TAZELIK_RE = re.compile(r"ger[cç]ek[\s\-]?zamanl[iı]|anl[iı]k\s+fiyat|canl[iı]\s+fiyat", re.I)

KESIN_OLUMSUZ = re.compile(r"de[gğ]il|olmaz|hi[cç]bir\s+zaman|retire", re.I)
TEREDDUT = re.compile(r"olmayabilir|olabilir|olmayabilirler", re.I)

# cumle siniri: yalnizca gercek cumle sonu. Etiketler zaten bosluga
# cevrildigi icin <strong> cumleyi BOLMEZ.
CUMLE_BOL = re.compile(r"(?<=[.;!?])\s+|\n")


def cumleler(metin: str):
    """(ofset, cumle) — ofsetten satir numarasi turetilebilsin diye."""
    poz = 0
    for parca in CUMLE_BOL.split(metin):
        if parca is None:
            continue
        idx = metin.find(parca, poz)
        if idx == -1:
            idx = poz
        yield idx, parca
        poz = idx + len(parca)


def satir_no(metin: str, ofset: int) -> int:
    return metin.count("\n", 0, ofset) + 1


def tara_metin(ham: str):
    """(satir, sinif, kanit) listesi."""
    m = soy(ham)
    bulgular = []
    for ofset, c in cumleler(m):
        duz = re.sub(r"\s+", " ", c).strip()
        if not duz:
            continue
        g = GECIKME_RE.search(c)
        if g:
            bulgular.append((satir_no(m, ofset + g.start()), "GECIKME-RAKAMI", duz[:160]))
        t = TAZELIK_RE.search(c)
        if t:
            if TEREDDUT.search(c):
                bulgular.append((satir_no(m, ofset + t.start()), "TEREDDUTLU-OLUMSUZ", duz[:160]))
            elif not KESIN_OLUMSUZ.search(c):
                bulgular.append((satir_no(m, ofset + t.start()), "TAZELIK-IDDIASI", duz[:160]))
    return bulgular


def tara_dosya(p: Path):
    return tara_metin(p.read_text(encoding="utf-8"))


# --- premise: cadence hala EOD-only mu? ----------------------------------
def cadence_eod_mi():
    app = (ROOT / "app.py").read_text(encoding="utf-8")
    return ("_should_run_eod" in app and "_EOD_POLL_INTERVAL" in app), app


# --- sentetik kontroller -------------------------------------------------
POZITIF = [
    ("gecikme rakami", "<p>fiyatlar ~15 dakika gecikmeli olabilir</p>"),
    ("gecikme rakami/strong", "<p>gecikmesi yaklasik <strong>15 dakika</strong></p>"),
    ("cikplak tazelik", "<p>Anlik fiyat takibi</p>"),
    ("tereddutlu olumsuz", "<p>fiyatlar gercek zamanli olmayabilir.</p>"),
    # script govdesindeki dizgi + ONCESINDE JS karsilastirma operatoru
    # (kapinin ilk yazimi tam burada korlesmisti)
    ("seans ici satiri isaretsiz", "<div class=\"hp-seans-l\">Seans içi · 15 dk gecikmeli</div>"),
    ("script icinde, < > operatorlerinin ardinda",
     "<script>\nif (age > 900) x=1;\nelse if (age < 300) { label = 'BIST ~15dk gecikmeli'; }\n</script>"),
]
NEGATIF = [
    ("kesin olumsuz", "<p>fiyatlar gercek zamanli degildir.</p>"),
    ("EOD ifadesi", "<p>Gun sonu (EOD) teknik analiz -- son kapanisa aittir.</p>"),
    ("yorumdaki iddia", "<!-- eskiden ~15 dakika gecikmeli diyordu -->\n<p>Gun sonu.</p>"),
    ("gun-sonu gecikme yok", "<p>sinyaller gunde bir kez, kapanistan sonra hesaplanir.</p>"),
    ("seans ici satiri data-intraday", "<div class=\"hp-seans-l\" data-intraday><i></i>Seans içi · 15 dk gecikmeli</div>\n<p>Gun sonu.</p>"),
    ("script icinde temiz karsilastirma",
     "<script>\nif (a > 1 && b < 2) { label = 'Gun sonu verileri'; }\n</script>"),
]


def main():
    print("eod-freshness-claim-check (K-BN: gosterilen fiyatin tazelik vaadi)")

    eod, _ = cadence_eod_mi()
    if not eod:
        print("  ⚠ PREMISE DUSTU: app.py'de EOD imzasi (_should_run_eod/_EOD_POLL_INTERVAL) YOK.")
        print("    Cadence degismis olabilir -- bu kapinin kurali yeniden olculmeli.")
        return 2
    print("  premise: app.py EOD-only cadence imzasi VAR (_should_run_eod + _EOD_POLL_INTERVAL)")

    hata = 0
    for ad, ornek in POZITIF:
        if not tara_metin(ornek):
            print(f"  ✗ SENTETIK POZITIF KACTI: {ad}")
            hata += 1
    for ad, ornek in NEGATIF:
        b = tara_metin(ornek)
        if b:
            print(f"  ✗ SENTETIK NEGATIF YANLIS-POZITIF: {ad} -> {b}")
            hata += 1
    print(f"  sentetik pozitif: {len(POZITIF) - min(hata, len(POZITIF))}/{len(POZITIF)} · "
          f"sentetik negatif: {len(NEGATIF)}/{len(NEGATIF)}" if not hata else "")
    if hata:
        print("  KAPI KENDI KENDINI DUSURDU (sentetik kontrol basarisiz).")
        return 1

    # pozitif kontrol: fix ONCESI agac (K-BK dersi: SABIT commit, HEAD degil)
    ONCE = "8cc1f8a"
    pk = 0
    for yol in ("templates/yasal.html", "templates/_footer.html",
                "templates/hisse.html", "templates/_stale_banner.html"):
        try:
            eski = subprocess.run(["git", "show", f"{ONCE}:{yol}"], cwd=ROOT,
                                  capture_output=True, text=True, check=True).stdout
        except Exception as e:
            print(f"  ⚠ pozitif kontrol okunamadi ({yol}): {e}")
            continue
        b = tara_metin(eski)
        pk += len(b)
    if pk < 5:
        print(f"  ✗ POZITIF KONTROL DUSTU: {ONCE} agacinda yalnizca {pk} ihlal goruldu (>=5 bekleniyordu)")
        print("    Kapi bugunku agaci olcmuyor olabilir (K-BM dersi: es-yazim korlugu).")
        return 1
    print(f"  pozitif kontrol: {ONCE} (fix oncesi) agacinda {pk} ihlal goruldu")

    ihlal = []
    for p in HEDEFLER:
        if not p.exists():
            continue
        for ln, sinif, kanit in tara_dosya(p):
            ihlal.append((p.relative_to(ROOT), ln, sinif, kanit))

    print(f"  taranan dosya: {len(HEDEFLER)}")
    if ihlal:
        print(f"\n  ✗ {len(ihlal)} ihlal — gosterilen fiyat icin alt-gunluk tazelik vaadi:")
        for yol, ln, sinif, kanit in ihlal:
            print(f"      {yol}:{ln}  [{sinif}]  {kanit}")
        print("\n  EOD-only'de gosterilen fiyat bir ONCEKI kapanistir; alt-gunluk rakam")
        print("  vermek ya da tazeligi tereddutle olumsuzlamak kullaniciyi yaniltir.")
        return 1

    print("  ✓ hicbir yuzey alt-gunluk tazelik vaat etmiyor")
    return 0


if __name__ == "__main__":
    sys.exit(main())
