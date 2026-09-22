#!/usr/bin/env python3
"""tools/manifest-text-check.py -- KAPI 54 (K-CI): PWA MANIFEST'I BIR YAYIN KANALIDIR

76/83. DERSIN DORDUNCU UYGULAMASI
---------------------------------
Metin/kanon kapilarinin envanteri cikarildiginda gorulen sira:

    K-CF -> blog_content.py       (67 kapinin gormedigi kor alan)
    K-CG -> app.py                (e-posta govdesi + KONU satiri, JSON-LD)
    K-CH -> static/**/*.js        (tarayiciya INEN paylasilan sozluk)
    K-CI -> static/manifest.json  (BU DOSYA)

`static/manifest.json` 53 kapidan **YALNIZ BIRI** tarafindan okunuyordu
(`cachebust-check.py`) -- o da metni degil IKON HASH'ini denetliyor.
Manifest'in metni ise kullaniciya **isletim sistemi kabugunda** ulasir:
yukleme diyalogu, ana ekran adi, uygulama gorev cubugu ve **uzun basinca
acilan kisayol menusu**. Bu kanal, sitedeki hicbir sayfayi degistirmeden
kullaniciya yanlis soz verebilir -- ve 4 aydir oyle yapiyordu.

K-CI'DE BULUNAN 3 IHLAL (hepsi canli olculdu)
---------------------------------------------
1) **KISAYOL DOGDUGU GUNDEN OLU** -- `"Güçlü Trend Sinyalleri"` kisayolu
   `/?filter=al&source=pwa`ya gidiyordu. `filter` diye bir sorgu
   parametresi urunde **HIC var olmadi** (`git log -S 'args.get("filter")'`
   -> 0 commit). Canli olcum: `/?filter=al` ile `/` **byte-ozdes**
   (md5 8a307111...). Playwright: `#fSignal` ogesi o sayfada YOK, 0 filtreli
   satir. Yani uzun basip "Güçlü Trend Sinyalleri" diyen kullanici, duz
   ana sayfaya dusuyordu. Gercek hedef VARDI ve calisiyordu:
   `/tarama?signal=AL` -> olculdu **7 satir, %100 Güçlü Trend**
   (kontrol: parametresiz /tarama -> 216 satir, 7 AL / 137 Yatay / 72 SAT).

2) **YON KILIDI (WCAG 2.1 SC 1.3.4)** -- `"orientation": "portrait-primary"`
   yuklu PWA'da (display:standalone) isletim sistemine ekrani DIKEYE
   KILITLETIR. Oysa `static/css/shared.css:246` blogu tam o durum icin
   yazilmis: K-AY turu 13 sayfayi 667/812x375'te olcup ust zinciri
   sabitlikten cikariyor, alt gezinmeyi 72px'den 52px'e sikistiriyor;
   K-AZ/2'de kendi regresyonu bulunup kapatilmis. Canli olcum (bu kapinin
   yazildigi gun): 375x812 -> header sticky, --bp-chrome-header 60px,
   alt nav 72px · 812x375 -> header **relative**, degiskenler **0px**,
   alt nav **52px**. Yani urun yatayi GERCEKTEN destekliyor ve manifest,
   tam o emegi **uygulamayi yukleyen** kullanici icin ulasilamaz kiliyordu.

3) **INDEXICAL TAZELIK IDDIASI** -- `/ozet` kisayolunun aciklamasi
   `"Bugünkü sinyal özeti"`ydi. Mimari EOD-only; ayni gun canli /ozet
   **"Dün · 21.09.2026" x21** basiyordu (K-CD fix'i dogru calisiyor).
   Sayfa "Dün" derken uygulama kisayolu "Bugünkü" diyordu.

⛔ KANAL FARKI: SABIT DIZE, INDEXICAL SOZCUK TASIYAMAZ
Sablonda "Bugün" bir HATA OLMAK ZORUNDA DEGIL -- Jinja onu okuma anindaki
takvimden yeniden uretebilir (K-CD'nin cozumu tam buydu). Manifest ise
**statik JSON**: orada yazan "bugün", uygulamanin yuklu kaldigi her gun
ayni sekilde okunur ve hicbir mekanizma onu tazeleyemez. Bu yuzden R4 bu
kanalda sablonlardan DAHA KATIDIR: indexical sozcuk kosullu da olsa
yazilamaz, cunku kosulu degerlendirecek bir motor YOK.

KURALLAR
--------
R1  URL SOZU        -- `start_url` ve her `shortcuts[].url` icindeki her
                       sorgu parametresinin urunde bir TUKETICISI olmali.
                       Tuketicisiz parametre, kullaniciya verilmis ama
                       hicbir kodun tutmadigi bir sozdur.
R2  YON KILIDI      -- `orientation` ya HIC olmayacak ya `any`/`natural`
                       olacak (WCAG SC 1.3.4). Kilitleyici deger, repo'da
                       yatay-ozel CSS varsa ayrica onu da iptal eder.
R3  KANON DISI TERIM-- emekli "Premium", 💎 glifi ve kanon disi skor adlari
                       (kapi 50-53 ile AYNI dizeler; 64. ders: kanonu
                       kopyalamadan yan yana koy).
R4  TAZELIK IDDIASI -- indexical zaman sozcugu ("bugün", "dün", "şu an"…)
                       + kapi 50'nin gun-ici/anlik/gercek-zamanli kaliplari.
R5  RENK KANALI     -- `theme_color` / `background_color` ham hex'i
                       tokens.css'te TANIMLI bir deger olmali.
                       (58. ders: bir degerin girebilecegi TUM sozdizimi
                       kanallarini say. Renk icin bilinen kanallar CSS
                       dosyasi, JS/`<script>`, HTML `style=` attribute'uydu
                       -- manifest **DORDUNCUSU** ve hicbiri onu okumuyordu.
                       Bugun ihlal YOK; kapi regresyonu tutmak icin var.)

R1'IN TUKETICI CIKARIMI -- NEDEN "DAR"
--------------------------------------
⛔ 69. DERS: iki taraf ayni sozdizimini kullanmaz. `/tarama?signal=AL`in
tuketicisi `params.get("signal")` DEGIL: `_hydrateFiltersFromUrl()` icinde
`{'signal': 'fSignal', ...}` esleme sozlugunun ANAHTARI, ve okuma
`params.get(param)` diye **degisken uzerinden** yapiliyor. Parametre adi
okuma yerinde GORUNMUYOR. Bu yuzden cikarim esleme sozluklerini de tarar.

⛔ Ters yonde de olctum: "tirnakli token dosyada geciyorsa tuketilmis say"
diye GENIS bir cikarim yazmak cazipti ama YANLIS gecirir -- `source`
parametresi app.py'de bir JSON VERI ANAHTARI olarak ("source": source_name)
gectigi icin tesadufen "tuketilmis" sayilirdi. Cikarim bu yuzden yalnizca
gercek URL-okuma yapilarini sayar, ve tuketicisi bilerek olmayan
parametreler asagida ACIKCA beyan edilir (57. ders: muafiyeti gizlemek
degil YAZMAK gerekir).

Kullanim:  python3 tools/manifest-text-check.py [--verbose]
Cikis:     0 = temiz, 1 = ihlal, 2 = kapi olcum yapamadi
"""

import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _tr import tr_fold  # 84. ders: tekrarlanan tuzak FONKSIYONDA yasar

ROOT = Path(__file__).resolve().parent.parent
MANIFEST = ROOT / "static" / "manifest.json"
TOKENS = ROOT / "static" / "css" / "tokens.css"
SHARED_CSS = ROOT / "static" / "css" / "shared.css"

# ---------------------------------------------------------------- R1
# Tuketicisi BILEREK olmayan parametreler. Bunlar kullaniciya bir DURUM
# soz vermez, yalnizca kokene etiket basar; hicbir kod okumasa da kisayol
# yine de dogru sayfayi acar. (Analitik tarafinda okunmuyor olmasi ayri
# bir konu -- urun hatasi degil, olcum bosluğu; CPO-1765'te DEV1'e not
# dusuldu.)
BEYAN_EDILMIS_TUKETICISIZ = {
    "source": "kokene etiket (PWA atfi) -- kullaniciya durum soz vermez",
}

# app.py tarafi: Flask sorgu okuma yapilari
RE_PY_TUKETICI = re.compile(
    r"""request\.args\.(?:get|getlist)\(\s*["']([A-Za-z0-9_]+)["']"""
    r"""|_q(?:float|int|str)\(\s*["']([A-Za-z0-9_]+)["']"""
)
# istemci tarafi: dogrudan okuma
RE_JS_TUKETICI = re.compile(
    r"""(?:searchParams|params|qs|q)\.(?:get|set|delete|has)\(\s*["']([A-Za-z0-9_]+)["']"""
)
# istemci tarafi: URL -> oge esleme sozlugu ANAHTARLARI (69. ders).
# Yalnizca location.search okuyan dosyalarda ve `'k': 'v'` bicimli
# dize->dize girdilerde gecerli.
RE_URL_OKUMA_VAR = re.compile(r"URLSearchParams\s*\(\s*(?:window\.)?location\.(?:search|href)")
RE_ESLEME_GIRDI = re.compile(r"""["']([A-Za-z0-9_]+)["']\s*:\s*["'][A-Za-z0-9_\-]+["']""")


def tuketiciler():
    """Uründe gercekten okunan sorgu parametrelerinin kumesi."""
    bulunan = set()

    app = ROOT / "app.py"
    if app.exists():
        for m in RE_PY_TUKETICI.finditer(app.read_text(encoding="utf-8")):
            bulunan.add(m.group(1) or m.group(2))

    hedefler = list((ROOT / "templates").glob("*.html"))
    hedefler += [p for p in (ROOT / "static").rglob("*.js")
                 if ".min." not in p.name and "vendor" not in p.parts]
    for p in hedefler:
        try:
            src = p.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        for m in RE_JS_TUKETICI.finditer(src):
            bulunan.add(m.group(1))
        # esleme sozlugu anahtarlari -- yalnizca URL okuyan dosyalarda
        if RE_URL_OKUMA_VAR.search(src):
            for m in RE_ESLEME_GIRDI.finditer(src):
                bulunan.add(m.group(1))
    return bulunan


def r1_url_sozu(man, tuk):
    from urllib.parse import urlparse, parse_qs
    bulgular = []
    hedefler = [("start_url", man.get("start_url", ""))]
    for i, ks in enumerate(man.get("shortcuts", []) or []):
        hedefler.append((f'shortcuts[{i}] "{ks.get("name", "?")}"', ks.get("url", "")))
    for etiket, url in hedefler:
        if not url:
            continue
        for ad in parse_qs(urlparse(url).query).keys():
            if ad in BEYAN_EDILMIS_TUKETICISIZ or ad in tuk:
                continue
            bulgular.append(
                ("R1", f'{etiket}: "{url}" -- "{ad}" parametresinin urunde '
                       f'TUKETICISI YOK (kisayol duz sayfaya duser)'))
    return bulgular


# ---------------------------------------------------------------- R2
KILITLEYICI_YON = {"portrait", "portrait-primary", "portrait-secondary",
                   "landscape", "landscape-primary", "landscape-secondary"}
RE_YATAY_CSS = re.compile(r"@media[^{]*orientation:\s*landscape")


def r2_yon_kilidi(man):
    y = (man.get("orientation") or "").strip().lower()
    if not y or y in ("any", "natural"):
        return []
    if y not in KILITLEYICI_YON:
        return [("R2", f'orientation: "{y}" -- taninmayan deger, gozden gecir')]
    ek = ""
    if SHARED_CSS.exists() and RE_YATAY_CSS.search(SHARED_CSS.read_text(encoding="utf-8")):
        ek = (" -- ayrica static/css/shared.css'teki yatay-ozel blogu "
              "(K-AY) yuklu kullanici icin ULASILAMAZ kiliyor")
    return [("R2", f'orientation: "{y}" ekrani KILITLER; WCAG 2.1 SC 1.3.4 '
                   f'"icerik tek bir goruntuleme yonune kisitlanamaz"{ek}')]


# ---------------------------------------------------------------- R3
# Kapi 53 (static-js-text-check) ile AYNI dizeler -- 64. ders: "ayni
# duzeltmeyi kaynaga tasidim" cumlesi dizelerin ayni oldugunu kanitlamaz,
# yan yana koy.
KANON_SKOR_ADLARI = ("Teknik Güç Skoru", "BorsaPusula Skoru")
RE_KANON_DISI_SKOR = re.compile(
    r"(Sinyal\s+Skoru|Sinyal\s+kalite\s+puan[ıi]|Kalite\s+Puan[ıi]|Güç\s+Puan[ıi])",
    re.IGNORECASE)


def r3_kanon(yol, d):
    b = []
    if re.search(r"\bPremium\b", d, re.IGNORECASE):
        b.append(("R3", f'{yol}: emekli "Premium" sozcugu (kanon: ⭐ Hacim Onaylı)'))
    if "💎" in d:
        b.append(("R3", f'{yol}: 💎 glifi -- urunde "Yuksek Skor" demek (81. ders)'))
    m = RE_KANON_DISI_SKOR.search(d)
    if m and not any(k in d for k in KANON_SKOR_ADLARI):
        b.append(("R3", f'{yol}: kanon disi skor adi "{m.group(1)}" '
                        f'(kanon: Teknik Güç Skoru)'))
    return b


# ---------------------------------------------------------------- R4
# Indexical zaman sozcukleri: anlamlarini OKUYAN kisinin takviminden alir.
# Statik JSON'da tazelenemezler (yukaridaki KANAL FARKI notu).
RE_INDEXICAL = re.compile(
    r"\b(bugün(kü|ün)?|dün(kü)?|yarın(ki)?|şu\s+an(ki|da)?|az\s+önce|şimdi)\b",
    re.IGNORECASE)
# kapi 50 ile ayni kaliplar
RE_GUNICI = re.compile(r"gün[\s\-]?içi(?!nde)", re.IGNORECASE)
RE_ANLIK = re.compile(
    r"anlık\s+(?!kayıt|kaydı|kaydını|görüntü|görüntüsü|kare|karesi)"
    r"[a-zçğıöşü]", re.IGNORECASE)
RE_GZ = re.compile(r"gerçek\s+zamanlı", re.IGNORECASE)
RE_CANLI = re.compile(r"canlı\s+(fiyat\w*|hisse\s+veri\w*|borsa\s+veri\w*)",
                      re.IGNORECASE)


def r4_tazelik(yol, d):
    b = []
    m = RE_INDEXICAL.search(d)
    if m:
        b.append(("R4", f'{yol}: indexical zaman sozcugu "{m.group(0)}" -- '
                        f'manifest STATIK JSON, bunu tazeleyecek motor YOK '
                        f'(mimari EOD-only)'))
    for rx, ad in ((RE_GUNICI, "gün içi"), (RE_ANLIK, "anlık <finansal>"),
                   (RE_GZ, "gerçek zamanlı"), (RE_CANLI, "canlı fiyat/veri")):
        mm = rx.search(d)
        if mm and not (rx is RE_GZ and re.search(r"değil", d, re.IGNORECASE)):
            b.append(("R4", f'{yol}: EOD-only mimaride "{mm.group(0).strip()}" '
                            f'iddiasi (kapi 50 ile ayni kanon)'))
    return b


# ---------------------------------------------------------------- R5
RE_HEX = re.compile(r"#[0-9a-fA-F]{3,8}\b")


def r5_renk(man):
    if not TOKENS.exists():
        return [("R5", "static/css/tokens.css okunamadi -- kapi olcum yapamadi")]
    tanimli = {h.lower() for h in RE_HEX.findall(TOKENS.read_text(encoding="utf-8"))}
    b = []
    for alan in ("theme_color", "background_color"):
        v = (man.get(alan) or "").strip().lower()
        if not v:
            continue
        if not RE_HEX.fullmatch(v):
            b.append(("R5", f'{alan}: "{v}" ham hex degil -- elle gozden gecir'))
        elif v not in tanimli:
            b.append(("R5", f'{alan}: "{v}" tokens.css\'te TANIMLI DEGIL '
                            f'(palet disi; 58. dersin 4. renk kanali)'))
    return b


# ---------------------------------------------------------------- surucu
def metin_alanlari(man):
    """(yol, dize) -- kullaniciya GORUNEN her manifest metni."""
    for k in ("name", "short_name", "description"):
        if man.get(k):
            yield k, man[k]
    for i, ks in enumerate(man.get("shortcuts", []) or []):
        for k in ("name", "short_name", "description"):
            if ks.get(k):
                yield f"shortcuts[{i}].{k}", ks[k]
    for k in ("categories",):
        for j, v in enumerate(man.get(k, []) or []):
            if isinstance(v, str):
                yield f"{k}[{j}]", v


def main():
    verbose = "--verbose" in sys.argv
    if not MANIFEST.exists():
        print("manifest-text-check: static/manifest.json YOK -- kapi olcum yapamadi")
        return 2
    try:
        man = json.loads(MANIFEST.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        print(f"IHLAL R0  static/manifest.json: gecersiz JSON ({e})")
        return 1

    tuk = tuketiciler()
    if not tuk:
        print("manifest-text-check: sorgu parametresi tuketicisi HIC bulunamadi "
              "-- cikarim bozuk, kapi olcum yapamadi")
        return 2

    bulgular = []
    bulgular += r1_url_sozu(man, tuk)
    bulgular += r2_yon_kilidi(man)
    bulgular += r5_renk(man)
    alan_sayisi = 0
    for yol, d in metin_alanlari(man):
        alan_sayisi += 1
        bulgular += r3_kanon(yol, d)
        bulgular += r4_tazelik(yol, d)

    if verbose:
        print(f"  taranan metin alani: {alan_sayisi}")
        print(f"  bilinen sorgu tuketicisi: {len(tuk)}")
        print(f"  ornek: {', '.join(sorted(tuk)[:12])}")
        # tr_fold kullaniliyor: kanon adlarinin es-yazimlari da tek anahtara
        # iner (84. ders). Burada yalnizca gozlem amacli basilir.
        print(f"  tr_fold('IDEAL GIRIS') = {tr_fold('IDEAL GIRIS')!r}")

    if bulgular:
        for kural, aciklama in bulgular:
            print(f"IHLAL {kural}  static/manifest.json: {aciklama}")
        print(f"\nmanifest-text-check: {len(bulgular)} ihlal (taban 0)")
        return 1
    print(f"manifest-text-check: OK ({alan_sayisi} metin alani, "
          f"{len(man.get('shortcuts', []) or [])} kisayol, 0 ihlal)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
