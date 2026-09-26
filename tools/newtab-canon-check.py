#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
K-AW — YENI SEKME UYARISI KANONU  (pre-deploy kapisi)

Neden var (21.09 olcum, yerel agac + canli kabuk enjeksiyonu):
  Sitede 27 adet `target="_blank"` baglanti vardi. 18'i acilan yeni sekmeyi
  ERISILEBILIR ADINDA hic soylemiyordu; 4'u (makro/sirket haber kartlari)
  siteden CIKIP 3. parti bir alan adina gidiyordu ve GORSEL isareti de yoktu.
  Ayni davranis dort ayri sekilde anlatiliyordu:
     · sr-only " (yeni sekmede acilir)"     -> KVKK baglantilari (K-AS)
     · aria-label "... (yeni sekmede acilir)" -> /gundem KAP rozeti
     · yalniz gorsel ↗ (aria-hidden)         -> /karsilastir KAP  (SR'a SESSIZ)
     · hicbir sey                            -> 9 .jargon-term + 4 haber karti
  Ekran okuyucu kullanicisi baglantiyi izledikten sonra "geri" tusuyla
  donemez (yeni sekmede gecmis yoktur) -- uyari verilmemesi WCAG 3.2.5 /
  G201 kapsaminda bir yon kaybi.

Kanon (tek kural, iki katman):
  A) HER `target="_blank"` baglantinin ERISILEBILIR ADI "yeni sekmede acilir"
     ibaresini tasir. Tasiyici ya `<span class="sr-only">` ya da `aria-label`
     olabilir -- ama ad icinde GORUNMELIDIR (yani `aria-hidden` bir kutunun
     icine saklanamaz).
  B) Hedef SITEDEN CIKIYORSA (http(s) + borsapusula.com disi) baglanti ayrica
     GORUNUR bir ↗ tasir. Ic hedefler (KVKK, /metodoloji sozluk terimleri)
     ↗ TASIMAZ -- ↗ bu sitede "siteden ayriliyorsun" demektir, "yeni sekme"
     degil; ikisini ayni gliften turetmek K-AQ'daki coklu-anlam hatasidir.

  B'nin TEK muafiyeti -- KARDES OK: haber/KAP satirlarinda ayni hedef IKI
     baglantiyla sunulur (genis basligin kendisi + satir sonundaki ↗ dugmesi:
     hisse.html 3176/3179 ve 3225/3231). Gorsel isaret satirda ZATEN var,
     basliga ikinci bir ↗ koymak ayni satirda cift ok demek olurdu. Muafiyet
     DAR tanimlidir: ayni dosyada, href IFADESI birebir ayni, ve 800 karakter
     icinde baska bir `target=_blank` baglanti ↗ tasiyorsa B aranmaz. Sadece
     "yakininda bir ok var" yetmez -- ayni hedefi gostermeli.
     [[reference_bilgi_kardes_elemanda_olabilir]]

Cikis: 0 temiz · 1 sapma · 2 kapsam tabani altinda / pozitif kontrol dustu.
"""
import os, re, sys, glob, io

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MIN_LINKS = 11          # kapsam tabani: bu sayinin altina duserse dedektor korlesmistir (C-P1-2509: hisse Haberler dis baglantilari kalkti, 20->17; C-36: eski iki takvim sablonu silindi, 16->14; C-65: ana sayfa + /gundem RSS ve KAP dis baglantilari kalkti, 14->11)
WARN = re.compile(r'yeni\s+sekmede\s+a[çc][ıi]l[ıi]r', re.I)
ARROW = '↗'        # ↗


def files():
    out = []
    for pat in ('templates/*.html', 'static/*.js', 'static/js/*.js'):
        out += sorted(glob.glob(os.path.join(ROOT, pat)))
    return out


def anchors(src):
    """Her `target="_blank"` icin onu saran <a ...> ... </a> parcasini dondur."""
    for m in re.finditer(r'target=(["\'])_blank\1', src):
        start = src.rfind('<a', 0, m.start())
        if start < 0:
            continue
        end = src.find('</a>', m.end())
        span = src[start:end + 4] if end > 0 else src[start:m.end() + 400]
        yield start, src[:start].count('\n') + 1, span


def accessible_name_text(span):
    """Erisilebilir ada KATILAN metin: aria-label + aria-hidden OLMAYAN icerik.

    aria-hidden="true" bir kutunun ICINDEKI metin ada katilmaz -- bu yuzden
    `<span aria-hidden="true">KAP ↗</span>` tek basina uyari SAYILMAZ.
    """
    al = ' '.join(re.findall(r'aria-label=(["\'])(.*?)\1', span, re.S) and
                  [g[1] for g in re.findall(r'aria-label=(["\'])(.*?)\1', span, re.S)] or [])
    body = re.sub(r'<(\w+)[^>]*aria-hidden=(["\'])true\2[^>]*>.*?</\1>', ' ', span, flags=re.S)
    body = re.sub(r'<[^>]+>', ' ', body)
    return al + ' ' + body


def href_of(span):
    m = re.search(r'href=(["\'])(.*?)\1', span, re.S)
    return m.group(2) if m else ''


def is_external(href):
    h = href.strip()
    if h.startswith('${') or h.startswith("' +") or 'safeHref' in h:
        return None            # calisma aninda belli olur -> cagri yerinden karar
    return bool(re.match(r'https?://', h)) and 'borsapusula.com' not in h


SIBLING_WINDOW = 800   # karakter -- ayni satir/kart bloğu kadar dar


def scan_text(src, fname='<fixture>'):
    found = [(pos, line, span) for pos, line, span in anchors(src)]
    devs = []
    for pos, line, span in found:
        name = accessible_name_text(span)
        if not WARN.search(name):
            devs.append((fname, line, 'A', 'erisilebilir adda "yeni sekmede acilir" YOK'))
            continue
        href = href_of(span)
        ext = is_external(href)
        if ext is None:
            # dinamik href: dis kaynak oldugu varsayilir (KAP / haber alan adlari)
            ext = ('kap_url' in span or 'item.url' in span or 'ev.url' in span or 'd.url' in span)
        if not ext or ARROW in span:
            continue
        # KARDES OK muafiyeti: ayni hedefe giden, yakindaki baska bir baglanti
        # gorsel oku zaten tasiyor mu?
        sib = any(p2 != pos and abs(p2 - pos) <= SIBLING_WINDOW
                  and href_of(s2) == href and href != '' and ARROW in s2
                  for p2, _, s2 in found)
        if not sib:
            devs.append((fname, line, 'B', 'siteden cikiyor ama gorunur ↗ YOK'))
    return len(found), devs


FIXTURES = [
    # (ad, kaynak, beklenen sapma sayisi)
    ('uyarisiz-ic',
     '<a href="/metodoloji" target="_blank" rel="noopener">ADX</a>', 1),
    ('uyarili-ic',
     '<a href="/metodoloji" target="_blank" rel="noopener">ADX'
     '<span class="sr-only"> (yeni sekmede açılır)</span></a>', 0),
    ('uyari-aria-hidden-icinde-saklanmis',
     '<a href="https://kap.org.tr/x" target="_blank"><span aria-hidden="true">'
     'KAP ↗ (yeni sekmede açılır)</span></a>', 1),
    ('dis-hedef-ok-yok',
     '<a href="https://kap.org.tr/x" target="_blank" aria-label="KAP (yeni sekmede açılır)">KAP</a>', 1),
    ('dis-hedef-tam',
     '<a href="https://kap.org.tr/x" target="_blank"><span aria-hidden="true">KAP ↗</span>'
     '<span class="sr-only">ASELS KAP bildirimleri (kap.org.tr, yeni sekmede açılır)</span></a>', 0),
    ('kardes-ok-ayni-hedef',
     '<a href="https://x.com/n" target="_blank">Başlık<span class="sr-only"> (yeni sekmede açılır)</span></a>'
     '<a href="https://x.com/n" target="_blank" aria-label="Haberi aç (yeni sekmede açılır)">↗</a>', 0),
    ('kardes-ok-FARKLI-hedef-muaf-DEGIL',
     '<a href="https://x.com/n" target="_blank">Başlık<span class="sr-only"> (yeni sekmede açılır)</span></a>'
     '<a href="https://y.com/z" target="_blank" aria-label="Başka (yeni sekmede açılır)">↗</a>', 1),
]


def positive_control():
    hit = 0
    for name, src, expect in FIXTURES:
        _, devs = scan_text(src, name)
        if len(devs) == expect:
            hit += 1
    return hit, len(FIXTURES)


def main():
    total, devs = 0, []
    for f in files():
        src = io.open(f, encoding='utf-8').read()
        n, d = scan_text(src, os.path.relpath(f, ROOT))
        total += n
        devs += d

    pc_hit, pc_tot = positive_control()
    print("newtab-canon-check (K-AW yeni sekme uyarisi kanonu)")
    print("  taranan target=_blank baglanti: %d · pozitif kontrol: %d/%d" % (total, pc_hit, pc_tot))

    if pc_hit != pc_tot:
        print("  ✗ POZITIF KONTROL DUSTU — dedektor korlesmis, sayilar guvenilmez")
        return 2
    if total < MIN_LINKS:
        print("  ✗ kapsam tabani altinda (%d/%d) — dedektor korlesmis" % (total, MIN_LINKS))
        return 2
    if devs:
        print("  ✗ %d sapma:" % len(devs))
        for fn, line, ax, why in devs:
            print("      · [%s] %s:%d  %s" % (ax, fn, line, why))
        return 1
    print("  ✓ her yeni sekme baglantisi adinda uyariyor, siteden cikanlar ↗ tasiyor")
    return 0


if __name__ == '__main__':
    sys.exit(main())
