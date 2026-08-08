# -*- coding: utf-8 -*-
"""T2.2 header birlesimi — canli yuzey <header> imzasi yakalayici.
Tam sayfa hash'i CANLI VERI (fiyat/damga) tasidigi icin kullanilamaz;
olcut header blogunun kendisidir. Masaustu + mobil UA ayri olculur."""
import sys, json, hashlib, re, urllib.request

BASE = 'http://127.0.0.1:8003'
UA_D = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0 Safari/537.36'
UA_M = 'Mozilla/5.0 (iPhone; CPU iPhone OS 17_4 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4 Mobile/15E148 Safari/604.1'

ETKILENEN = ['/tarama', '/blog', '/gucu-yuksek', '/kripto', '/metodoloji', '/portfolio',
             '/abd/tarama', '/bilanco-takvimi', '/gizlilik', '/gundem', '/hakkinda',
             '/iletisim', '/karsilastir', '/sinyal-performans', '/btc', '/yasal']
KONTROL   = ['/', '/hisseler', '/ozet', '/sektor-harita', '/hisse/THYAO', '/profil',
             '/heatmap', '/sektor-karsilastir', '/offline', '/emtialar', '/altin']

def fetch(path, ua):
    req = urllib.request.Request(BASE + path, headers={'User-Agent': ua})
    try:
        with urllib.request.urlopen(req, timeout=25) as r:
            return r.status, r.read().decode('utf-8', 'replace')
    except Exception as e:
        return -1, 'ERR:%s' % e

def sig(html):
    ms = re.findall(r'<header\b.*?</header>', html, re.S)
    if not ms:
        return {'n': 0, 'md5': None, 'len': 0}
    joined = '\n<<HDR>>\n'.join(ms)
    return {'n': len(ms), 'md5': hashlib.md5(joined.encode()).hexdigest(), 'len': len(joined)}

out = {}
for grup, urls in (('ETKILENEN', ETKILENEN), ('KONTROL', KONTROL)):
    for u in urls:
        for tag, ua in (('D', UA_D), ('M', UA_M)):
            st, html = fetch(u, ua)
            out['%s %s' % (u, tag)] = {'grup': grup, 'status': st, 'bytes': len(html), **sig(html)}

json.dump(out, open(sys.argv[1], 'w'), indent=1, sort_keys=True)
bad = [k for k, v in out.items() if v['status'] != 200]
print('YAKALANDI: %d yuzey -> %s' % (len(out), sys.argv[1]))
print('status!=200 :', bad if bad else 'YOK')
print('header YOK  :', [k for k, v in out.items() if v['n'] == 0])
print('cok header  :', [(k, v['n']) for k, v in out.items() if v['n'] > 1])
