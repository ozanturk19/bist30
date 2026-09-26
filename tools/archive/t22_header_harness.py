# -*- coding: utf-8 -*-
"""T2.2 ikinci yari — _header.html render harness.
Her Class A sablonunun MEVCUT header'ini, _header.html'in ayni parametrelerle
render edilmis ciktisiyla BAYT BAYT karsilastirir. Hicbir sablona dokunmaz."""
import re, os, sys, json, subprocess
from jinja2 import Environment, FileSystemLoader, select_autoescape

env = Environment(loader=FileSystemLoader('templates'),
                  autoescape=select_autoescape(['html']))

# Sayfa -> _header.html parametreleri (kaynaktan elle turetildi, harness dogrular)
PARAMS = {
    'tarama':            {},
    'blog':              {},
    'gucu_yuksek':       {},
    'kategori':          {},
    'metodoloji':        {},
    'portfolio':         {},
    'abd_tarama':        {'hdr_title': '__EMOJI__ __TITLE__', 'hdr_title_tag': 'div',
                          'hdr_sub': 'Supertrend · ADX · EMA Sinyal Tarayıcısı'},
    'bilanco_takvimi':   {'hdr_title': '\U0001f4c5 Bilanço Takvimi',
                          'hdr_sub': 'Veriler yükleniyor…', 'hdr_sub_id': 'lastUpdate'},
    'gizlilik':          {'hdr_title': '\U0001f512 Gizlilik Politikası'},
    'gundem':            {'hdr_title': 'Piyasa Gündem Merkezi',
                          'hdr_sub': 'Yükleniyor…', 'hdr_sub_id': 'updatedAt'},
    'hakkinda':          {'hdr_title': 'Hakkında'},
    'iletisim':          {'hdr_title': '\U0001f4ec İletişim'},
    'karsilastir':       {'hdr_title': 'Hisse Karşılaştırma',
                          'hdr_sub': '2-4 hisseyi seçin', 'hdr_sub_id': 'compareSubtitle'},
    'sinyal_performans': {'hdr_title': 'Sinyal Performans Analizi'},
    'varlik':            {'hdr_trailing_include': '_header_asset_price.html'},
    'yasal':             {'hdr_title': '⚖️ Yasal Uyarı & SPK Bildirimi'},
}

BASE_REF = os.environ.get('T22_BASE_REF', 'e4d6c4a')   # birlesim ONCESI son commit

def cur_header(name):
    """ORIJINAL header'i CALISMA AGACINDAN DEGIL git'ten alir — boylece birlesim
    uygulandiktan sonra da kosturulabilir (calisma agacinda artik inline header YOK)."""
    s = subprocess.run(['git', 'show', '%s:templates/%s.html' % (BASE_REF, name)],
                       capture_output=True, text=True, check=True).stdout
    m = re.search(r'<header\b.*?</header>', s, re.S)
    return m.group(0) if m else None

tpl = env.get_template('_header.html')
ok = fail = 0
report = []
for name, p in PARAMS.items():
    cur = cur_header(name)
    got = tpl.render(**p)
    # abd_tarama Jinja degiskeni tasiyor: harness'ta yer tutucuyla karsilastir
    cur_cmp = cur.replace('{{ emoji }}', '__EMOJI__').replace('{{ title }}', '__TITLE__') if cur else cur
    if cur_cmp == got:
        ok += 1; report.append((name, 'BIREBIR', 0, ''))
    else:
        fail += 1
        # ilk fark noktasi
        i = next((k for k in range(min(len(cur_cmp), len(got))) if cur_cmp[k] != got[k]),
                 min(len(cur_cmp), len(got)))
        report.append((name, 'FARKLI', len(got) - len(cur_cmp),
                       'off=%d cur=%r got=%r' % (i, cur_cmp[i:i+70], got[i:i+70])))

print('%-20s %-8s %6s  %s' % ('SABLON', 'SONUC', 'DELTA', 'ILK FARK'))
for r in report:
    print('%-20s %-8s %6d  %s' % r)
print()
print('BIREBIR=%d  FARKLI=%d  TOPLAM=%d' % (ok, fail, ok + fail))
sys.exit(0 if fail == 0 else 1)
