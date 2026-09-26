#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""tools/nav-label-canon-check.py — K-AS kapisi: GEZINME ETIKETI KANONU

WCAG 2.1 · SC 3.2.4 "Consistent Identification" (AA)
                  + SC 2.5.3 "Label in Name" (A)

NEDEN: 21.09 K-AS turunda sitenin UC ayri gezinme yuzeyi (masaustu nav +
drawer / mobil alt nav + sheet / alt bilgi) ayni hedefe GIDEN baglantiyi
FARKLI adla aniyordu:
    /tarama          -> "Tarama"        vs "Hisse Tarayici"
    /sektor-harita   -> "Sektorler"     vs "Sektor Haritasi"
    /ozet            -> "Ozet"          vs "Gunluk Ozet"
    /bilanco-takvimi -> "Bilanco"       vs "Bilanco Takvimi"
    /temettu-takvimi -> "Temettu"       vs "Temettu Takvimi"
    /                -> "Ana Sayfa"     vs "BorsaPusula — Piyasanin Yonu" (logo)
Kullanici alt bilgide "Hisse Tarayici", ust menude "Tarama" gorup iki AYRI
sayfa sanabilir. Ekran okuyucu baglanti listesinde ise ayni sayfa iki kez,
iki farkli adla gorunur.

⛔ BU KAPI NEDEN STATIK (canli dedektorun KOR NOKTASI):
   tools/link-purpose-check.js canli DOM'u olcer ve `aria-hidden="true"`
   altindaki baglantilari — DOGRU OLARAK — ekran okuyucuda yok sayar.
   Ama KAPALI drawer/sheet de aria-hidden'dir. Canli tarama bu yuzden
   /bilanco-takvimi ve /temettu-takvimi catismasini GOREMEDI; ikisi de
   sablon kaynagi okunarak bulundu. Kaynak taramasi gorunurlukten bagimsizdir.
   [[reference_bayragin_varligi_olcum_kaniti_degildir]]

KURAL (iki yonlu):
  1. Gezinme baglantisinin ERISILEBILIR ADI (aria-label varsa o, yoksa
     gorunen metin) hedefin KANONIK adina birebir esit olmali.
  2. aria-label kullanilan yerde GORUNEN metin kanonik adin ICINDE gecmeli
     (SC 2.5.3: sesle "Bilanco"ya dokun diyen kullanici hedefi bulabilmeli).
     ⛔ Ilk surum "ONEK olmali" diyordu — kendi SAHTE POZITIFIMDI: mobil alt
        navin "Ozet" etiketi "Gunluk Ozet"in SON ekidir ve WCAG Understanding
        2.5.3 yalnizca "contained within the accessible name" der, konum
        sartsizdir. Onek OLMAMASI ayrica NOT edilir (ses komutunda kullanici
        adin BASINDAN soylerse eslesmez) ama sapma DEGILDIR.

Kullanim: python3 tools/nav-label-canon-check.py [--kill-fix]
Cikis: 0 temiz · 1 sapma · 2 kapsam tabani altina dustu
"""
import os, re, sys, html

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
T = os.path.join(ROOT, 'templates')
KILL = '--kill-fix' in sys.argv

# ── KANONIK GEZINME SOZLUGU (baglayici) ──────────────────────────────────
CANON = {
    '/':                 'Piyasa',           # C-31 (O17=A): 5 öğeli menü adları
    '/ozet':             'Günlük Özet',
    '/gundem':           'Gündem',
    '/tarama':           'Keşfet',
    '/karsilastir':      'Karşılaştır',
    '/portfolio':        'Takip',
    '/sektor-harita':    'Sektörler',
    '/hisseler':         'Tüm Hisseler',
    '/takvim':           'Takvim',            # C-36: iki takvim tek sayfada
    '/blog':             'Öğren',
    '/metodoloji':       'Metodoloji',
    '/hakkinda':         'Hakkında',
    '/gizlilik':         'Gizlilik & KVKK',
    '/yasal':            'Yasal Uyarı',
    '/iletisim':         'İletişim',
}
# Logo AYRI: marka isareti, gorunen metni yok (SVG aria-hidden) -> 2.5.3
# uygulanmaz, ama adi hedefi SOYLEMELI.
LOGO_OK = {'BorsaPusula ana sayfası'}

# Gezinme YUZEYLERI — sadece bunlar SC 3.2.4 kapsaminda.
#
# ⛔ ELEME 1 — SAYFA GOVDESI BILEREK DISARIDA. Bir CUMLE ICI baglanti gezinme
#    BILESENI degildir: 404'teki "…İsterseniz Tarama sayfasindan goz atin"
#    veya 500'deki "…sorun devam ederse bize bildirin" ayni hedefe gider ama
#    amaci cumlenin kendisinden bellidir (SC 2.4.4 "in context" KARSILANIR).
#    Kapinin ilk surumu hata sayfalarini DOSYA butun olarak tarayip bu ikisini
#    sapma sandi — iki SAHTE POZITIF. Bu yuzden hata sayfalarinda YALNIZ
#    "Populer Sayfalar" izgarasi (bir gezinme bileseni) olculur.
# ⛔ ELEME 2 — a.brand / a.logo-link MARKA isaretidir. Hata sayfalarindaki
#    <a class="brand" href="/">Borsa Pusula</a> gorunen metni MARKA ADIDIR;
#    marka isaretinin ana sayfaya gitmesi evrensel bir kalip ve ekran okuyucu
#    kullanicisi icin ogrenilmis bir yoldur. _header.html'deki logo FARKLIYDI
#    ve degistirildi: onun gorunen metni HIC YOKTU (SVG aria-hidden) ve tek
#    adi bir SLOGAN'di ("BorsaPusula — Piyasanin Yonu") — hedefi hic soylemiyordu.
#    Gorunen marka adi olan baglantilar bu yuzden ayri sayilir, sapma DEGIL.
#    (Pratikte hata sayfalarinin a.brand'i zaten ELEME 1'in kapsam blogunun
#    disinda kalir; kural yine de burada, cunku kapsam blogu degisirse
#    dogru davranis korunmalidir.)
FILES = ['_header.html', '_mobile_nav_partial.html', '_footer.html',
         '404.html', '410.html', '429.html', '500.html']
# Hata sayfalarinda yalnizca bu blok gezinme bilesenidir:
SCOPE_BLOCK = {'404.html': 'popular-grid', '410.html': 'popular-grid',
               '429.html': 'popular-grid', '500.html': 'popular-grid'}

A_RE = re.compile(r'<a\b([^>]*)>(.*?)</a>', re.S)
HREF_RE = re.compile(r'href="([^"]*)"')
AL_RE = re.compile(r'aria-label="([^"]*)"')
TAG_RE = re.compile(r'<[^>]+>', re.S)
HID_RE = re.compile(r'<(svg|span)\b[^>]*aria-hidden="true"[^>]*>.*?</\1>', re.S)
JINJA_RE = re.compile(r'\{[%{#].*?[%}#]\}', re.S)


def visible_text(inner: str) -> str:
    inner = HID_RE.sub(' ', inner)          # aria-hidden icerik ada girmez
    inner = JINJA_RE.sub(' ', inner)
    inner = TAG_RE.sub(' ', inner)
    return re.sub(r'\s+', ' ', html.unescape(inner)).strip()


def main():
    bad, notes, checked, files_seen, brand = [], [], 0, 0, 0
    for fn in FILES:
        p = os.path.join(T, fn)
        if not os.path.exists(p):
            continue
        files_seen += 1
        src = open(p, encoding='utf-8').read()
        blk = SCOPE_BLOCK.get(fn)
        if blk:
            i = src.find(blk)
            if i < 0:
                print(f'  ✗ {fn}: kapsam blogu "{blk}" BULUNAMADI — sablon degismis')
                return 2
            j = src.find('</div>', src.find('>', i))
            src = src[i:j if j > 0 else len(src)]
        if KILL:
            # POZITIF KONTROL — uc EKSENI birden bozar (her biri ayri kod yolu)
            if fn == '_footer.html':
                src = src.replace('>Tarama</a>', '>Hisse Tarayıcı</a>')          # eksen 1: ad != kanonik
            if fn == '_header.html':
                src = src.replace('aria-label="Bilanço Takvimi">',
                                  'aria-label="Bilanço Takvimi">Takvim<!--')      # eksen 2: SC 2.5.3
                src = src.replace('aria-label="BorsaPusula ana sayfası"',
                                  'aria-label="Piyasanın Yönü"')                  # eksen 3: logo adi
        for m in A_RE.finditer(src):
            attrs, inner = m.group(1), m.group(2)
            hm = HREF_RE.search(attrs)
            if not hm:
                continue
            href = hm.group(1).split('?')[0].split('#')[0]
            if href != '/' and href.endswith('/'):
                href = href[:-1]
            am = AL_RE.search(attrs)
            alabel = am.group(1).strip() if am else ''
            vis = visible_text(inner)
            if 'logo-link' in attrs or 'class="brand"' in attrs:
                checked += 1
                if vis:
                    brand += 1          # ELEME 2: gorunen marka adi var -> sapma degil
                elif alabel not in LOGO_OK:
                    bad.append((fn, href, f'logo adi hedefi soylemiyor: "{alabel}"'))
                continue
            if href not in CANON:
                continue
            checked += 1
            canon = CANON[href]
            acc = alabel or vis
            if acc != canon:
                bad.append((fn, href, f'erisilebilir ad "{acc}" != kanonik "{canon}"'))
            elif alabel and vis and vis not in canon:
                bad.append((fn, href,
                            f'SC 2.5.3: gorunen "{vis}" kanonik "{canon}" adinin ICINDE gecmiyor'))
            elif alabel and vis and not canon.startswith(vis):
                notes.append((fn, href, f'gorunen "{vis}" kanonik "{canon}" adinin ONEKI degil (ses komutu notu, sapma DEGIL)'))

    print('nav-label-canon-check (K-AS: gezinme etiketi kanonu)')
    print(f'  {files_seen} gezinme yuzeyi · {len(CANON)} kanonik hedef · {checked} baglanti olculdu')
    print(f'  ayri sayilan (sapma DEGIL): {brand} marka isareti · {len(notes)} ses-komutu notu')
    for fn, href, why in notes:
        print(f'      · {fn:28} {href:20} {why}')
    if checked < 40:
        print(f'  ✗ KAPSAM TABANI ALTINDA ({checked} < 40) — secici/dosya listesi bozulmus olabilir')
        return 2
    if bad:
        print(f'  ✗ {len(bad)} SAPMA:')
        for fn, href, why in bad:
            print(f'      {fn:28} {href:20} {why}')
        return 1
    print('  ✓ tum gezinme yuzeyleri kanonikle ayni')
    return 0


sys.exit(main())
