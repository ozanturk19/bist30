# -*- coding: utf-8 -*-
"""T2.2 ikinci yari — 16 sablonun inline <header> blogunu kanonik _header.html'e tasi.
GUVENLIK: her sablon icin BEKLENEN header md5'i onceden yazili. Eslesmezse
o sablona DOKUNULMAZ ve script exit 1 doner. "0 degisiklik + basarili" YASAK."""
import re, sys, hashlib

INC = "{% include '_header.html' %}"

# sablon -> (beklenen_header_md5_10, {% with %} argumanlari veya None)
PLAN = {
    'tarama':            ('25f4028362', None),
    'blog':              ('25f4028362', None),
    'gucu_yuksek':       ('25f4028362', None),
    'kategori':          ('25f4028362', None),
    'metodoloji':        ('25f4028362', None),
    'portfolio':         ('25f4028362', None),
    'abd_tarama':        ('69fc6f101a', "hdr_title = (emoji ~ ' ' ~ title), hdr_title_tag = 'div', hdr_sub = 'Supertrend · ADX · EMA Sinyal Tarayıcısı'"),
    'bilanco_takvimi':   ('902647a90c', "hdr_title = '\U0001f4c5 Bilanço Takvimi', hdr_sub = 'Veriler yükleniyor…', hdr_sub_id = 'lastUpdate'"),
    'gizlilik':          ('51ff52d7aa', "hdr_title = '\U0001f512 Gizlilik Politikası'"),
    'gundem':            ('067b7abd17', "hdr_title = 'Piyasa Gündem Merkezi', hdr_sub = 'Yükleniyor…', hdr_sub_id = 'updatedAt'"),
    'hakkinda':          ('3f35666da4', "hdr_title = 'Hakkında'"),
    'iletisim':          ('d364769b53', "hdr_title = '\U0001f4ec İletişim'"),
    'karsilastir':       ('25952d8ab9', "hdr_title = 'Hisse Karşılaştırma', hdr_sub = '2-4 hisseyi seçin', hdr_sub_id = 'compareSubtitle'"),
    'sinyal_performans': ('8b73226352', "hdr_title = 'Sinyal Performans Analizi'"),
    'varlik':            ('bcf2517a64', "hdr_trailing_include = '_header_asset_price.html'"),
    'yasal':             ('ccb96256c2', "hdr_title = '⚖️ Yasal Uyarı & SPK Bildirimi'"),
}

DRY = '--dry-run' in sys.argv
hata, degisen = [], []

for name, (beklenen, args) in PLAN.items():
    path = 'templates/%s.html' % name
    s = open(path, encoding='utf-8').read()
    ms = list(re.finditer(r'<header\b.*?</header>', s, re.S))
    if len(ms) != 1:
        hata.append('%s: <header> blok sayisi %d (1 bekleniyordu)' % (name, len(ms)))
        continue
    blok = ms[0].group(0)
    got = hashlib.md5(blok.encode()).hexdigest()[:10]
    if got != beklenen:
        hata.append('%s: CAPA TUTMADI md5=%s beklenen=%s' % (name, got, beklenen))
        continue
    yeni = INC if args is None else '{%% with %s %%}%s{%% endwith %%}' % (args, INC)
    s2 = s[:ms[0].start()] + yeni + s[ms[0].end():]
    if s2 == s:
        hata.append('%s: ikame SIFIR degisiklik uretti' % name)
        continue
    degisen.append((name, len(blok), len(yeni)))
    if not DRY:
        open(path, 'w', encoding='utf-8').write(s2)

print('%-20s %8s %8s' % ('SABLON', 'ESKI', 'YENI'))
for n, a, b in degisen:
    print('%-20s %8d %8d' % (n, a, b))
print('\nDEGISEN=%d / PLAN=%d   %s' % (len(degisen), len(PLAN), 'KURU CALISMA' if DRY else 'YAZILDI'))
if hata:
    print('\nHATA (%d):' % len(hata))
    for h in hata:
        print('  ', h)
if len(degisen) != len(PLAN) or hata:
    sys.exit(1)
