#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
K-DP — KONTROLUN ROLU ILE DAVRANISI AYNI SEYI SOYLEMELI  (pre-deploy kapisi)

Neden var (22.09 olcum, canli DOM):
  /karsilastir'daki "🔗 Linki Kopyala" bir <a href="."> idi. `.` bu sayfada
  ANA SAYFAYA cozuluyordu -- canli olcum: `a.href == "https://borsapusula.com/"`.
  Dugmenin TEK isi "bu karsilastirmanin adresini ver"ken:
     · sag tik > "Baglanti adresini kopyala"  -> ana sayfa (vaadin TAM TERSI)
     · Ctrl/Cmd+tik, orta tik, "yeni sekmede ac" -> ana sayfa
     · SPACE tusu -> <a href> SPACE ile ETKINLESMEZ (tarayici sayfayi kaydirir);
       elemanin kendi onkeydown'i da yoktu -> klavye kullanicisi kopyalayamiyordu
     · ekran okuyucu "baglanti" diye duyuruyordu -> gezinme vaadi
  Hemen yanindaki kardes kontrol (.compare-btn) ZATEN gercek <button>'di:
  ayni satirda, ayni gorunumde, iki kanon (52. ders).

  Ayni turda ikinci sinif: /hisse'de iki baglanti
     `<a href="#signalSummarySection" onclick="...applyTab('ozet');return false">`
  `return false` VARSAYILAN FRAGMENT GEZINMESINI IPTAL EDIYORDU. Sekme
  degisiyordu ama tarayici hedefe NE KAYDIRIYOR NE ODAK TASIYORDU: tiklamadan
  sonra `location.href`te fragment YOKTU ve hedefin konumu tamamen sansa
  kaliyordu (olcum: /hisse/GARAN'da ekranin 2487px USTUNDE, /hisse/AKBNK'de
  tesadufen goruste). Dahasi `window.applyTab && applyTab(...); return false`
  ifadesi applyTab TANIMSIZ oldugunda da `return false` calistirir -- yani
  href'in var olma sebebi olan "JS calismazsa hic olmazsa baglanti islesin"
  yedegi, tam da ise yarayacagi senaryoda yok ediliyordu.

Kanon (iki kural):
  A) Bir <a> GEZINIR. href'i yer tutucu ise (`.`, `#`, bos, `javascript:`)
     eleman gezinmiyor demektir -> <button type="button"> olmali.
     Muafiyet: sayfa-ici gercek capa (`#birSey`) yer tutucu DEGILDIR.
  B) Gercek sayfa-ici capaya (`href="#birSey"`) sahip bir <a>'nin satir-ici
     onclick'i varsayilani IPTAL ETMEMELI (`return false` / `preventDefault`).
     Iptal edilirse vaat edilen sicrama HIC olmaz; capanin varligi sozlesmeyi
     karsilanmis gosterir, davranis yoktur (K-S/K-DO sinifi).

Cikis: 0 temiz · 1 sapma · 2 kapsam tabani altinda / pozitif kontrol dustu.
"""
import os, re, sys, glob, io

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MIN_ANCHORS = 150       # kapsam tabani: <a ...> sayisi bunun altina duserse dedektor korlesmistir

# href'i yer tutucu sayilanlar: gezinme YOK demektir
PLACEHOLDER = re.compile(r'^\s*(?:\.|#|)\s*$')
JS_HREF = re.compile(r'^\s*javascript:', re.I)
# gercek sayfa-ici capa
FRAGMENT = re.compile(r'^#[A-Za-z][\w:.\-]*$')
# varsayilani iptal eden satir-ici ifadeler
CANCELS = re.compile(r'\breturn\s+false\b|\.preventDefault\s*\(')

ATAG = re.compile(r'<a\b[^>]*>', re.I | re.S)

# 77. ders: bir hatanin YORUMDA ANILMASI ihlal degildir. Bu kapinin kendi
# gerekce yorumu `<a href=".">` ifadesini birebir icerir; maskelemezsek kapi
# kendi belgelendirmesini sapma sayar. Satir numaralari korunmali -> yorumun
# yerine ayni sayida satirsonu konur.
COMMENTS = re.compile(r'<!--.*?-->|\{#.*?#\}|/\*.*?\*/', re.S)


def strip_comments(src):
    return COMMENTS.sub(lambda m: '\n' * m.group(0).count('\n'), src)


def files():
    out = []
    for pat in ('templates/*.html', 'static/*.js', 'static/js/*.js'):
        out += sorted(glob.glob(os.path.join(ROOT, pat)))
    return out


def attr(tag, name):
    m = re.search(r'\b%s=(["\'])(.*?)\1' % name, tag, re.S)
    return m.group(2) if m else None


def scan_text(src, fname='<fixture>'):
    src = strip_comments(src)
    devs = []
    tags = ATAG.findall(src)
    for m in ATAG.finditer(src):
        tag = m.group(0)
        line = src[:m.start()].count('\n') + 1
        href = attr(tag, 'href')
        onclick = attr(tag, 'onclick') or ''
        if href is None:
            # href'siz <a>: odaklanabilir degildir, link rolu de yoktur.
            # Yalnizca onclick TASIYORSA bir kontrol olmaya calisiyor demektir.
            if onclick:
                devs.append((fname, line, 'A', '<a> href TASIMIYOR ama onclick var -> <button> olmali'))
            continue
        # Sunucu/istemci sablon ifadesi: calisma aninda belli olur, karar verme
        if '{{' in href or '${' in href or 'safeHref' in href or "' +" in href:
            continue
        if JS_HREF.match(href) or PLACEHOLDER.match(href):
            devs.append((fname, line, 'A',
                         'href="%s" yer tutucu -> gezinme yok, <button type="button"> olmali' % href.strip()))
            continue
        if FRAGMENT.match(href.strip()) and CANCELS.search(onclick):
            devs.append((fname, line, 'B',
                         'href="%s" capasina gidecegini soyluyor ama onclick varsayilani IPTAL ediyor'
                         % href.strip()))
    return len(tags), devs


FIXTURES = [
    # (ad, kaynak, beklenen sapma sayisi)
    ('nokta-href-kopyala-dugmesi',
     '<a id="shareBtn" class="share-btn" href="." onclick="copyShareUrl(event);return false">Linki Kopyala</a>', 1),
    ('gercek-dugme',
     '<button type="button" id="shareBtn" class="share-btn" onclick="copyShareUrl(event)">Linki Kopyala</button>', 0),
    ('bos-href',
     '<a href="" onclick="doThing()">Yap</a>', 1),
    ('diyez-yer-tutucu',
     '<a href="#" onclick="doThing()">Yap</a>', 1),
    ('javascript-href',
     '<a href="javascript:void(0)" onclick="doThing()">Yap</a>', 1),
    ('hrefsiz-a-onclick-ile',
     '<a onclick="doThing()">Yap</a>', 1),
    ('hrefsiz-a-onclicksiz-zararsiz',
     '<a name="eski-capa"></a>', 0),
    ('capa-iptal-ediliyor',
     '<a href="#signalSummarySection" onclick="window.applyTab&&applyTab(\'ozet\');return false">Panel</a>', 1),
    ('capa-preventDefault-ile-iptal',
     '<a href="#signalSummarySection" onclick="event.preventDefault();applyTab(\'ozet\')">Panel</a>', 1),
    ('capa-iptalsiz-DOGRU',
     '<a href="#signalSummarySection" onclick="window.applyTab&&applyTab(\'ozet\')">Panel</a>', 0),
    ('normal-gezinme-baglantisi',
     '<a href="/hisse/AKBNK" class="da-link">AKBNK</a>', 0),
    ('skip-link-zararsiz',
     '<a href="#main-content" class="skip-link">Ana içeriğe atla</a>', 0),
    ('dinamik-href-karar-verilmez',
     '<a href="${safeHref(item.url)}" onclick="event.stopPropagation()">Haber</a>', 0),
    ('jinja-href-karar-verilmez',
     '<a href="{{ url_for(\'index\') }}" onclick="x();return false">Ana</a>', 0),
    ('stopPropagation-iptal-DEGIL',
     '<a href="#adx" onclick="event.stopPropagation()">ADX</a>', 0),
    ('html-yorumunda-anilma-ihlal-DEGIL',
     '<!-- eskiden `<a href="." onclick="x();return false">` idi -->'
     '<button type="button" onclick="x()">Kopyala</button>', 0),
    ('jinja-yorumunda-anilma-ihlal-DEGIL',
     '{# <a href="#" onclick="y()">eski</a> #}<a href="/tarama">Tarama</a>', 0),
    ('yorum-MASKESI-gercek-ihlali-YUTMAMALI',
     '<!-- aciklama -->\n<a href="." onclick="x();return false">Kopyala</a>', 1),
]


def positive_control():
    hit = 0
    for name, src, expect in FIXTURES:
        _, devs = scan_text(src, name)
        if len(devs) == expect:
            hit += 1
        else:
            print("      ! fixture '%s': beklenen %d, bulunan %d" % (name, expect, len(devs)))
    return hit, len(FIXTURES)


def read_at(ref, rel):
    import subprocess
    r = subprocess.run(['git', '-C', ROOT, 'show', '%s:%s' % (ref, rel)],
                       capture_output=True, text=True)
    return r.stdout if r.returncode == 0 else None


def main():
    # --ref <commit>: 164. ders — kapiyi, KORUMAK ICIN YAZILDIGI hatayi
    # enjekte ederek sina. Fix oncesi agacta ihlal SAYMALI.
    ref = None
    if '--ref' in sys.argv:
        ref = sys.argv[sys.argv.index('--ref') + 1]

    total, devs = 0, []
    for f in files():
        rel = os.path.relpath(f, ROOT)
        src = read_at(ref, rel) if ref else io.open(f, encoding='utf-8').read()
        if src is None:
            continue
        n, d = scan_text(src, rel)
        total += n
        devs += d

    pc_hit, pc_tot = positive_control()
    print("control-role-behavior-check (K-DP kontrol rolu = davranisi)")
    print("  taranan <a>: %d · pozitif kontrol: %d/%d" % (total, pc_hit, pc_tot))

    if pc_hit != pc_tot:
        print("  ✗ POZITIF KONTROL DUSTU — dedektor korlesmis, sayilar guvenilmez")
        return 2
    if total < MIN_ANCHORS:
        print("  ✗ kapsam tabani altinda (%d/%d) — dedektor korlesmis" % (total, MIN_ANCHORS))
        return 2
    if devs:
        print("  ✗ %d sapma:" % len(devs))
        for fn, line, ax, why in devs:
            print("      · [%s] %s:%d  %s" % (ax, fn, line, why))
        return 1
    print("  ✓ her <a> gezinir, her capa gercekten sicrar")
    return 0


if __name__ == '__main__':
    sys.exit(main())
