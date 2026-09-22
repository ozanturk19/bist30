#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""KAPI 51 — blog_content.py icerik-dogruluk kapisi (K-CF, 22.09.2026).

YAPISAL BOSLUK (bu kapinin varlik sebebi)
-----------------------------------------
`blog_content.py` 7371 satir ve ~130 makale tasiyor; icerik-dogruluk
kapilarinin (intraday-claim, window-claim, threshold-sync, canon-conflict,
legal-text-sync, relative-time-anchor, nav-label-canon ...) HICBIRI bu
dosyayi taramiyordu -- 68 kapidan yalniz `style-guard.py` aciyordu, o da
salt renk icin. Sonuc: /metodoloji'de 22.09'da (K-CB/CPO-1745) retire
edilmis kanon blogda KOSULSUZ yasamaya devam etti, evren sayisi 214'te
dondu (canli 217), var olmayan iki sayfa ("Sinyal Performans", ana sayfada
"BIST30 filtresi") vaat edildi ve EOD-only urun kuru "anlik" gosterdigini
yazdi. Besi de FAQPage JSON-LD'ye de basiliyordu -- yani Google'in zengin
sonuclarina.

OLCUM YONTEMI
-------------
Dosya `ast` ile ayristirilir ve YALNIZ string literalleri taranir. Bu,
Python yorumlarini ve kod govdesini otomatik disarida birakir; markdown
basliklarindaki `#` ise korunur (56. ders: yorum soymak gerekir ama
`#` ile baslayan her satiri atmak markdown'i yok eder).
Kural CUMLE granulerliginde isler: koca bir makale govdesinin herhangi
bir yerinde "Güçlü Trend" gecmesi, 40 satir asagidaki kosulsuz bir
cumleyi muaf yapmasin (43. ders: muafiyet anlam kuralidir, beyaz liste
degil -- ama anlam AYNI CUMLEDE aranir).
"""
import ast, io, os, re, sys, unicodedata

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TARGET = os.path.join(ROOT, 'blog_content.py')

# ── Cumle bolucu: HTML blok sonlari + markdown satir/madde sonlari + nokta ──
_SPLIT = re.compile(r'</li>|</p>|</h[1-6]>|</td>|<br\s*/?>|\n|(?<=[.!?:])\s+')

def sentences(text):
    for part in _SPLIT.split(text or ''):
        p = re.sub(r'<[^>]+>', ' ', part or '')       # etiketleri soy
        p = re.sub(r'\s+', ' ', p).strip()
        if p:
            yield p

# ── R1: retire edilmis kanon — KOSULSUZ "İdeal Giriş Penceresi" ────────────
# business_rules.derive_rsi_zone (CPO-1745): bu ad YALNIZ signal=='AL'
# (Güçlü Trend) icin doner, aksi halde "Nötr Bölge". Kosulu tasimayan her
# yazim, urunun artik basmadigi bir adi ogretiyor demektir.
IDEAL = 'İdeal Giriş Penceresi'
IDEAL_COND = ('Güçlü Trend', 'Nötr Bölge', 'yalnız', 'yalnızca', 'varsa',
              'verdiğinde', 'ise ')

# ── R2: mimari olarak imkansiz tazelik vaadi (kapi 50 sozlugunun blog esi) ─
# /api/data EOD-only (CPO-1508/1512/1703). Urunun KENDI yuzeyi hakkinda
# "anlik / gun ici / gercek zamanli / canli" demek hicbir kosulda dogru olamaz.
PRODUCT = re.compile(
    r'BorsaPusula|Platform|ana sayfa|anasayfa|hisse sayfa|Tarama sayfa|Özet sayfa|'
    r'makro ticker|ticker band|/tarama|/ozet|/hisse/|Günlük Özet', re.I)
IMPOSSIBLE = re.compile(
    r'anlık|gün içi|gün-içi|gerçek zamanlı|gerçek-zamanlı|'
    r'canlı (?:fiyat|takip|veri|akış)', re.I)
NEGATED = re.compile(
    r'sunmaz|sunmuyor|değildir|değil\b|yoktur|vermez|çalışmaz|'
    r'retire|kaldırıl|yok\b', re.I)

# ── R3: kirilgan evren sayisi ──────────────────────────────────────────────
# Tam sayi yazmak, evren buyudugunde SESSIZCE yalana donusur -- 214 boyle
# bayatladi. Urunun kapsamindan bahseden cumlede 150-399 arasi tam bir
# "N hisse" yazimi yasak; bant ("200'ün üzerinde") kullanilir.
BRITTLE_COUNT = re.compile(r'\b(1[5-9]\d|2\d\d|3\d\d)\s*hisse')
# Kapsam fiili: sayinin URUNUN TARADIGI EVREN oldugunu belli eden baglam.
# Bu olmadan "500 hisselik S&P" gibi egitim metinleri yanlis-pozitif olurdu.
SCOPE_VERB = re.compile(
    r'tara|analiz|izley|takip|sinyal|hesapla|incele|kapsa|Platform|BorsaPusula', re.I)

# ── R4: ic baglantilar — yalnizca dogrulanmis hedefler ────────────────────
# Her yeni hedef, hem HTTP durumu hem de METNIN sayfaya verdigi ADIN
# dogrulanmasini gerektirir (K-CF: /gucu-yuksek "Güçlü Momentum" diye
# tanitiliyordu, /sinyal-performans hic var olmayan bir sayfaydi).
# Deger = o rotanin KANONIK GORUNUR ADI (bp-vocab / _header.html nav etiketi).
# None = ad zorunlulugu yok (ana sayfa/hukuki sayfalar cesitli anilir).
# Ad kontrolu YALNIZ "sayfa" sozcugu gecen cumlelerde uygulanir -- yani metin
# bir SAYFAYI ADLANDIRIYORSA adin dogru olmasi gerekir (K-CF: /gucu-yuksek
# "Güçlü Momentum" diye tanitiliyordu, oyle bir sayfa adi hic olmadi).
ALLOWED_LINKS = {
    '/': None, '/hakkinda': None, '/blog': None, '/yasal': None,
    '/gizlilik': None, '/iletisim': None,
    '/ozet': 'Özet', '/tarama': 'Tarama', '/gucu-yuksek': 'Tarama',
    '/metodoloji': 'Metodoloji', '/hisseler': 'Hisseler',
    '/karsilastir': 'Karşılaştır', '/gundem': 'Gündem',
    '/sektor-harita': 'Sektör', '/bilanco-takvimi': 'Bilanço',
    '/temettu-takvimi': 'Temettü', '/portfolio': 'Portföy',
}
LINK_RE = re.compile(r'href="(/[^"#?]*)|\]\((/[^)"#?]*)')

# ── R5: sinyal adi kanonu (bp-vocab BP_SIG_LABELS) ────────────────────────
# Urunun kendi kararlari "Güçlü Trend / Trend Bozuldu / Yatay" diye anilir;
# ham payload kodlari (AL/SAT/BEKLE) kullanici metnine girmez.
RAW_SIG = re.compile(r'\bAL\s*/\s*SAT\b|["“‘](?:AL|SAT|BEKLE)["”’]|'
                     r'\b(?:AL|SAT|BEKLE) sinyali\b')



# ── R6: BIST30 bir ALT KUME — urun yuzeyinin kapsami olarak yazilamaz ──────
# Canli evren 217 hisse (BIST100 + otesi). "tüm BIST30" / "BIST30 filtresi"
# gibi yazimlar ya kapsami kucultur ya da olmayan bir kontrolu vaat eder
# (K-CF: ana sayfada BIST30 filtresi HIC yoktu, kapsam 217'ydi).
BIST30_SCOPE = re.compile(u'tüm\\s+BIST\\s*-?30|BIST\\s*-?30[\'\u2019"]?\\s*filtre', re.I)

def scan(path):
    src = io.open(path, encoding='utf-8').read()
    tree = ast.parse(src)
    out = []
    seen_links = {}
    for node in ast.walk(tree):
        if not (isinstance(node, ast.Constant) and isinstance(node.value, str)):
            continue
        val, ln = node.value, node.lineno
        for m in LINK_RE.finditer(val):
            seen_links.setdefault(m.group(1) or m.group(2), ln)
        for s in sentences(val):
            if IDEAL in s and not any(c in s for c in IDEAL_COND):
                out.append((ln, 'R1-RETIRE-EDILMIS-KANON',
                            'kosulsuz "%s" (CPO-1745: yalniz Guclu Trend)' % IDEAL, s))
            if PRODUCT.search(s):
                m = IMPOSSIBLE.search(s)
                if m and not NEGATED.search(s):
                    out.append((ln, 'R2-IMKANSIZ-TAZELIK',
                                'EOD-only urunde "%s"' % m.group(0), s))
            # R3 urun adina BAGLI DEGIL: "Platform 214 hisseyi tarar" ya da
            # ozne-siz "214 hisseyi manuel incelemenize gerek yok" da ayni
            # kirilgan sayidir (K-CF pozitif kontrolu bu ikisini kacirmisti).
            m = BRITTLE_COUNT.search(s)
            if m and SCOPE_VERB.search(s):
                out.append((ln, 'R3-KIRILGAN-EVREN-SAYISI',
                            '"%s" tam sayisi bayatlar — bant kullan' % m.group(0), s))
            m = BIST30_SCOPE.search(s)
            if m:
                out.append((ln, 'R6-BIST30-KAPSAM-IDDIASI',
                            '"%s" — BIST30 alt kume; canli evreni/kontrolu dogrula'
                            % m.group(0).strip(), s))
            m = RAW_SIG.search(s)
            if m:
                out.append((ln, 'R5-HAM-SINYAL-KODU',
                            '"%s" -> bp-vocab BP_SIG_LABELS kullan' % m.group(0), s))
    for href, ln in sorted(seen_links.items()):
        if href.rstrip('/') and href not in ALLOWED_LINKS and not href.startswith('/hisse/') \
           and not href.startswith('/blog/'):
            out.append((ln, 'R4-DOGRULANMAMIS-BAGLANTI',
                        '%s ALLOWED_LINKS\'te yok — HTTP durumunu VE metindeki '
                        'sayfa adini dogrula, sonra ekle' % href, ''))
    out.extend(name_violations(tree))
    return sorted(set(out))


def name_violations(tree):
    """R4b — bir sayfayi ADLANDIRAN cumle, kanonik adi tasimali."""
    bad = []
    for node in ast.walk(tree):
        if not (isinstance(node, ast.Constant) and isinstance(node.value, str)):
            continue
        for raw in _SPLIT.split(node.value):
            hrefs = [m.group(1) or m.group(2) for m in LINK_RE.finditer(raw or '')]
            if not hrefs:
                continue
            txt = re.sub(r'\s+', ' ', re.sub(r'<[^>]+>', ' ', raw)).strip()
            if 'sayfa' not in txt.lower():
                continue
            for h in hrefs:
                want = ALLOWED_LINKS.get(h)
                if want and want.lower() not in txt.lower():
                    bad.append((node.lineno, 'R4b-YANLIS-SAYFA-ADI',
                                '%s kanonik adi "%s" — cumlede yok' % (h, want), txt))
    return bad


def main():
    path = sys.argv[1] if len(sys.argv) > 1 else TARGET
    if not os.path.exists(path):
        print('SKIP blog-claim-check: %s yok' % path); return 0
    v = scan(path)
    if not v:
        print('PASS blog-claim-check: %s temiz (R1-R6, 7 kural)' % os.path.basename(path))
        return 0
    print('FAIL blog-claim-check: %d ihlal' % len(v))
    for ln, rule, why, s in v:
        print('  %s:%d  [%s] %s' % (os.path.basename(path), ln, rule, why))
        if s:
            print('        > %s' % (s[:150]))
    return 1


if __name__ == '__main__':
    sys.exit(main())
