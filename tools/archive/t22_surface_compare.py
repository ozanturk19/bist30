# -*- coding: utf-8 -*-
"""T2.2 — canli ONCE/SONRA header imzasi karsilastirmasi."""
import json, sys
a = json.load(open(sys.argv[1])); b = json.load(open(sys.argv[2]))
keys = sorted(set(a) | set(b))
ayni = farkli = hata = 0
satir = []
for k in keys:
    x, y = a.get(k), b.get(k)
    if not x or not y:
        hata += 1; satir.append((k, '?', 'EKSIK', 0)); continue
    if y['status'] != 200:
        hata += 1; satir.append((k, x['grup'], 'HTTP %s' % y['status'], 0)); continue
    if x['md5'] == y['md5']:
        ayni += 1
        if x['grup'] == 'ETKILENEN':
            satir.append((k, x['grup'], 'BIREBIR', 0))
    else:
        farkli += 1
        satir.append((k, x['grup'], 'FARKLI', y['len'] - x['len']))

print('%-26s %-10s %-10s %s' % ('YUZEY', 'GRUP', 'SONUC', 'DELTA'))
for s in satir:
    print('%-26s %-10s %-10s %+d' % s)
print()
print('BIREBIR=%d  FARKLI=%d  HATA=%d  TOPLAM=%d' % (ayni, farkli, hata, len(keys)))
sys.exit(0 if (farkli == 0 and hata == 0) else 1)
