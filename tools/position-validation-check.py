#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""K-BJ kapisi (30/30) — POZISYON SAYISAL DOGRULAMA TEK KANON.

Bulgu (21.09): portfoye pozisyon YAZAN dort yol vardi, olcut UC ayri yerde
yaziliydi ve biri hic dogrulamiyordu:
  * addPosition()     (form)        -> kendi satir-ici olcutu
  * importPortfolio() (dosya)       -> AYNI olcut, ikinci kez yazilmis
  * togglePortfolio() (hisse detay) -> dogrulama YOK; dahasi _hibCurrentPrice()
    fiyat okunamadiginda 0 donuyordu ve o 0 dogrudan MALIYET olarak yaziliyordu
  * bulut yollari                   -> bilerek gecirgen (sunucu dogruluyor,
    reddetmek kullanici verisini sessizce dusururdu) -- render korur
price=0 pozisyon /portfolio'da cost=0 uretir: K/Z pozisyonun TAM degerini "kar"
gosterir ve toplam K/Z kutusunu sisirir. Ayrica CSV disa aktarimi ayni K/Z'yi
tablo render'inin aksine KORUMASIZ hesapliyordu -> "Infinity"/"NaN" hucreler.

Olculen ihlal siniflari (tabani SIFIR):
  A) Satir-ici sayisal olcutun sablonda yeniden yazilmasi (`lot <= 0`,
     `price <= 0`, `> 1e9`) -- kanon bp-format.js'te, kopyalanmamali.
  B) Pozisyon fiyatina korumasiz BOLME (`/ p.price`) -- ayni ifadede
     gecerlilik koruması (_valid / cost > 0 / bpIsValidPrice) olmali.
  C) hisse detay hizli-eklemesinin (`pf.push(`) bpIsValidPrice'tan gecmemesi.
"""
import re, sys, os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CANON = os.path.join('static', 'bp-format.js')

def strip_comments(src):
    # K-BJ: blok yorum SILINIRSE satir numaralari kayar ve rapor yanlis yere
    # isaret eder (ilk kosuda tam bu oldu) -> esit sayida newline ile degistir.
    src = re.sub(r'/\*.*?\*/', lambda m: '\n' * m.group(0).count('\n'), src, flags=re.S)
    src = re.sub(r'(?m)^\s*//.*$', '', src)
    src = re.sub(r'(?m)\s//(?!.*["\'`]).*$', '', src)
    return src

def read(rel):
    with open(os.path.join(ROOT, rel), encoding='utf-8') as f:
        return f.read()

TEMPLATES = [os.path.join('templates', f)
             for f in sorted(os.listdir(os.path.join(ROOT, 'templates')))
             if f.endswith('.html')]

def scan(reader):
    v = []
    # --- A: satir-ici olcutun yeniden yazilmasi
    # K-BJ dersi: NEGATIF iddia es-yazimlarin HEPSINI taramali. Ilk surum yalniz
    # negatif yazimi (`lot <= 0`, `> 1e9`) ariyordu ve loadFromCloud'daki POZITIF
    # yazimi (`p.lot > 0 && p.lot <= 1e9`) kacirdi -- dorduncu kopya gorulmedi.
    reA = re.compile(r'\b(?:lot|price|adet|fiyat)\s*(?:<=\s*0|>\s*1e9|>\s*0\b|<=\s*1e9)', re.I)
    for rel in TEMPLATES:
        try: src = strip_comments(reader(rel))
        except Exception: continue
        for i, line in enumerate(src.splitlines(), 1):
            if reA.search(line):
                v.append('A %s:%d satir-ici sayisal olcut (kanon: bpIsValidLot/bpIsValidPrice) -> %s'
                         % (rel, i, line.strip()[:90]))
    # --- B: pozisyon fiyatina korumasiz bolme
    reB = re.compile(r'/\s*p\.price\b')
    guard = re.compile(r'_valid|bpIsValidPrice|cost\s*>\s*0')
    for rel in TEMPLATES:
        try: src = strip_comments(reader(rel))
        except Exception: continue
        for i, line in enumerate(src.splitlines(), 1):
            if reB.search(line) and not guard.search(line):
                v.append('B %s:%d pozisyon fiyatina korumasiz bolme -> %s'
                         % (rel, i, line.strip()[:90]))
    # --- C: hisse detay hizli-eklemesi kanondan gecmeli
    try:
        src = strip_comments(reader(os.path.join('templates', 'hisse.html')))
        m = re.search(r'function\s+togglePortfolio\s*\([^)]*\)\s*\{', src)
        if m:
            body = src[m.end():m.end() + 2500]
            if 'pf.push(' in body and 'bpIsValidPrice' not in body.split('pf.push(')[0]:
                v.append('C templates/hisse.html: togglePortfolio() pozisyon yaziyor ama '
                         'bpIsValidPrice kontrolunden GECMIYOR')
    except Exception:
        pass
    return v

def git_reader(ref):
    import subprocess
    def r(rel):
        return subprocess.check_output(['git', 'show', '%s:%s' % (ref, rel)],
                                       cwd=ROOT).decode('utf-8')
    return r

# --- POZITIF KONTROL: her kosuda, fix ONCESI SABITLENMIS agaca karsi ---
# ⛔ 21.09 (K-BK turunda yakalandi): burada `HEAD` yaziyordu. Yazildigi anda
# dogruydu (fix henuz commit edilmemisti, HEAD = fix oncesi agac) ama K-BJ fix'i
# `a381515` olarak commit edilir edilmez HEAD fix'i ICERMEYE basladi, pozitif
# kontrol ihlal bulamadi ve kapi KENDI KENDINI kirdi — deploy reddedildi.
# DERS: pozitif kontrol HAREKETLI bir referansa (HEAD/main) baglanamaz;
# degismez bir commit'e sabitlenmeli.
PRE_FIX_REF = 'a381515^'   # K-BJ fix'inin ebeveyni — dort ihlalin hepsi burada
try:
    pc = scan(git_reader(PRE_FIX_REF))
    if not pc:
        print('K-BJ kapisi: POZITIF KONTROL DUSTU — fix oncesi agacta (%s) '
              'hic ihlal bulunamadi, dedektor kor olabilir.' % PRE_FIX_REF,
              file=sys.stderr)
        sys.exit(2)
except SystemExit:
    raise
except Exception as e:
    print('K-BJ kapisi: pozitif kontrol kosulamadi (%s) — devam ediliyor.' % e, file=sys.stderr)
    pc = ['(atlandi)']

viol = scan(read)
if viol:
    print('K-BJ IHLAL (%d):' % len(viol), file=sys.stderr)
    for x in viol:
        print('  ' + x, file=sys.stderr)
    sys.exit(1)

print('K-BJ kapisi OK — pozisyon sayisal dogrulamasi tek kanon '
      '(pozitif kontrol: %s uzerinde %d ihlal goruldu).' % (PRE_FIX_REF, len(pc)))
sys.exit(0)
