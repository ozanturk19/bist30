#!/usr/bin/env python3
"""K-BM kapisi — KULLANICI VERISI: bozuk yerel kayit SESSIZCE silinmemeli.

Bulgu (21.09, canli olculdu): /portfolio, `bp_portfolio` kaydini
`JSON.parse` edemedigi ya da dizi olmadigini gordugu her durumda bellegi
`[]` yapip "Portföyünüz boş." diyordu. Ham kayit hala tarayicidaydi ve
icindeki pozisyonlar okunabilirdi; kullanici bunu gercek bos portfoy sanip
tek pozisyon ekleyince ilk `save()` ham kaydi KALICI eziyordu.
Ayni is icin ikinci kanon (hisse.html:togglePortfolio) ise islemi iptal
edip "mevcut verin korundu" diyordu — zayif olan kanon veri kaybettiriyordu.

KURAL: kullanici verisi tutan bir localStorage anahtarini `JSON.parse` eden
her yolda, parse/tur hatasinin yakalandigi `catch` blogu su ucundan BIRINI
yapmali:
  (a) ham kaydi YEDEKLE  (bir BACKUP/bozuk anahtarina setItem),
  (b) islemi IPTAL ET    (catch icinde `return` — veri diske dokunulmaz),
  (c) ham kaydi belleGE AL ve kullaniciya kurtarma yolu ver (`_pfCorruptRaw`
      gibi bir degiskene `getItem` ile okunur; kapi bunu (a) ile ayni sayar).
Hicbirini yapmayan yol, "sessizce sifirla" demektir -> IHLAL.

KAPSAM DISI (yeniden uretilebilir onbellek; kaybi kullanici verisi degil):
anahtar adina gore beyaz liste — satir numarasina DEGIL ([[K-BF dersi]]).

Pozitif kontrol SABIT commit'e baglidir (8781e71 = K-BM fix'inden ONCEKI
agac); HEAD'e baglanan pozitif kontrol fix commit'lenince kendini kirar
([[K-BK dersi]]).
"""
import importlib.util
import pathlib
import re
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
TOOLS = ROOT / 'tools'

# Yorum soyucusu: KANON tools/tr-calendar-day-check.py (K-BL'de regex literali
# ogretildi). Kopyalamak "ayni is icin iki kanon" olurdu.
_spec = importlib.util.spec_from_file_location('_trcal', TOOLS / 'tr-calendar-day-check.py')
_trcal = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_trcal)
strip_js_comments = _trcal.strip_js_comments

# Yeniden uretilebilir onbellek anahtarlari — kaybi kullanici verisi degildir.
CACHE_KEYS = {
    'bp_sym_cache', 'bp_symbols_cache', 'bp_search_cache', 'bp_sub_user',
    'bp_stocks_cache', 'bp_404_cache',
}

# (1) dogrudan yazim: JSON.parse(localStorage.getItem('k') || '[]')
PARSE_RE = re.compile(r'JSON\.parse\s*\(\s*([A-Za-z0-9_$.]*localStorage\.getItem\s*\([^)]*\)[^;{]*?)\)')
# (2) ⛔ ES-YAZIM: ham kayit once bir degiskene alinir, parse SONRA yapilir
#     (`const _raw = localStorage.getItem(PF_KEY); JSON.parse(_raw || '[]')`).
#     K-BL dersi: es-yazim korlugu ARA DEGISKENDEN de gelir — kapinin ilk
#     yazimi tam bu yuzden K-BM fix'inden SONRAKI portfolio.html'i hic
#     taramiyordu (pozitif kontrol eski agacta gectigi icin fark edilmedi).
ASSIGN_RE = re.compile(r'\b(?:const|let|var)\s+([A-Za-z0-9_$]+)\s*=\s*([A-Za-z0-9_$.]*localStorage\.getItem\s*\([^)]*\))')
KEY_RE = re.compile(r"getItem\s*\(\s*(?:'([^']+)'|\"([^\"]+)\"|([A-Za-z0-9_$]+))")


def key_of(expr, src):
    m = KEY_RE.search(expr)
    if not m:
        return '(bilinmiyor)'
    lit = m.group(1) or m.group(2)
    if lit:
        return lit
    # sabit degisken: `const PF_KEY = 'bp_portfolio';`
    var = m.group(3)
    vm = re.search(r'\b' + re.escape(var) + r"\s*=\s*['\"]([^'\"]+)['\"]", src)
    return vm.group(1) if vm else var


def catch_body(src, pos):
    """pos'u kapsayan en ic try blogunun catch govdesini dondurur ('' = yok)."""
    # geriye dogru en yakin dengelenmemis `try {`
    depth = 0
    i = pos
    while i > 0:
        c = src[i]
        if c == '}':
            depth += 1
        elif c == '{':
            if depth == 0:
                if re.search(r'\btry\s*$', src[max(0, i - 30):i]):
                    break
                # baska bir blok acilisi: disa dogru devam
                depth -= 1
            else:
                depth -= 1
        i -= 1
    else:
        return '', ''
    # try blogunun sonunu bul
    d, j = 0, i
    while j < len(src):
        if src[j] == '{':
            d += 1
        elif src[j] == '}':
            d -= 1
            if d == 0:
                break
        j += 1
    m = re.match(r'\s*catch\s*\([^)]*\)\s*\{', src[j + 1:])
    if not m:
        return '', ''
    start = j + 1 + m.end()
    d, k = 1, start
    while k < len(src) and d:
        if src[k] == '{':
            d += 1
        elif src[k] == '}':
            d -= 1
        k += 1
    return src[start:k - 1], src[k:k + 400]


def kurtariyor_mu(body, sonrasi=''):
    if re.search(r'\breturn\b', body):
        return True, 'catch icinde return (islem iptal, veri korunur)'
    # catch, kapsayan fonksiyonun SON ifadesi ise akis zaten sonlaniyor:
    # `return` yazmak ile ayni sey (orn. v1->v2 migration IIFE'si). Bu yollar
    # catch'te HICBIR SEY yazmadigi icin ham kayit oldugu gibi kalir.
    if re.match(r'\s*\}\s*(?:\)\s*\(\s*\)\s*;?|;?\s*(?:\}|$))', sonrasi):
        return True, 'catch fonksiyonun son ifadesi (yazma yok, ham kayit dokunulmadan kalir)'
    if re.search(r'setItem\s*\(\s*[^;]*(BACKUP|BOZUK|bozuk|backup|yedek)', body):
        return True, 'ham kayit yedekleniyor'
    if re.search(r'=\s*[A-Za-z0-9_$.]*localStorage\.getItem', body):
        return True, 'ham kayit bellege alindi (kurtarma yolu)'
    return False, ''


def tara(dosyalar, etiket=''):
    ihlal, sayim = [], 0
    for f in dosyalar:
        raw = f.read_text(encoding='utf-8', errors='replace')
        src = strip_js_comments(raw)
        yerler = [(m.start(), key_of(m.group(1), src)) for m in PARSE_RE.finditer(src)]
        for am in ASSIGN_RE.finditer(src):
            var, k = am.group(1), key_of(am.group(2), src)
            pm = re.search(r'JSON\.parse\s*\(\s*' + re.escape(var) + r'\b', src[am.end():])
            if pm:
                yerler.append((am.end() + pm.start(), k))
        for pos, k in yerler:
            if k in CACHE_KEYS:
                continue
            sayim += 1
            body, sonrasi = catch_body(src, pos)
            ln = raw[:pos].count('\n') + 1
            if not body.strip():
                ihlal.append((f, ln, k, 'catch YOK veya bos'))
                continue
            ok, _ = kurtariyor_mu(body, sonrasi)
            if not ok:
                ihlal.append((f, ln, k, 'catch var ama ham kayit ne yedekleniyor ne islem iptal ediliyor'))
    return ihlal, sayim


def pozitif_kontrol():
    """8781e71 (K-BM fix'inden ONCE) uzerinde kapi ihlal GORMELI."""
    import tempfile
    try:
        eski = subprocess.run(['git', 'show', '8781e71:templates/portfolio.html'],
                              cwd=ROOT, capture_output=True, text=True, check=True).stdout
    except Exception as e:
        return None, 'git show basarisiz: %s' % e
    with tempfile.TemporaryDirectory() as d:
        p = pathlib.Path(d) / 'portfolio.html'
        p.write_text(eski, encoding='utf-8')
        ihlal, _ = tara([p])
    return len(ihlal), (ihlal[0][3] if ihlal else '')


SENTETIK = [
    # (ad, kod, ihlal_bekleniyor_mu)
    ('sessiz sifirla', "const K='bp_portfolio';\nlet pf;\ntry { pf = JSON.parse(localStorage.getItem(K) || '[]'); } catch(e) { pf = []; }\nrender(pf);\n", True),
    ('ara degisken + sessiz sifirla', "const K='bp_portfolio';\nlet pf;\ntry { const raw = localStorage.getItem(K); pf = JSON.parse(raw || '[]'); } catch(e) { pf = []; }\nrender(pf);\n", True),
    ('catch icinde return', "function f(){\n const K='bp_portfolio';\n let pf;\n try { pf = JSON.parse(localStorage.getItem(K)||'[]'); } catch(e) { warn(); return; }\n pf.push(1);\n}\n", False),
    ('ham kayit yedekleniyor', "const K='bp_portfolio';\nlet pf;\ntry { const raw = localStorage.getItem(K); pf = JSON.parse(raw||'[]'); } catch(e) { localStorage.setItem(BOZUK_KEY, localStorage.getItem(K)); pf=[]; }\nsave(pf);\n", False),
    ('onbellek anahtari muaf', "try { var s = JSON.parse(localStorage.getItem('bp_sub_user')||'[]'); } catch(e) { s=[]; }\n", False),
]


def ic_kontroller():
    """Kapinin kendisi olculur: hem yakalamali hem de sahte alarm vermemeli."""
    import tempfile
    poz = poz_t = neg = neg_t = 0
    for ad, kod, bekle in SENTETIK:
        with tempfile.TemporaryDirectory() as d:
            f = pathlib.Path(d) / 'x.js'
            f.write_text(kod, encoding='utf-8')
            ihlal, _ = tara([f])
        if bekle:
            poz_t += 1
            poz += 1 if ihlal else 0
        else:
            neg_t += 1
            neg += 1 if not ihlal else 0
    return poz, poz_t, neg, neg_t


def main():
    dosyalar = sorted(list((ROOT / 'templates').glob('*.html')) + list((ROOT / 'static').glob('*.js')))
    dosyalar = [f for f in dosyalar if 'lightweight-charts' not in f.name]
    ihlal, sayim = tara(dosyalar)

    pk, pk_not = pozitif_kontrol()
    poz, poz_t, neg, neg_t = ic_kontroller()
    print('local-data-guard (K-BM: bozuk yerel kayit sessizce silinmemeli)')
    print('  taranan dosya: %d · kullanici verisi parse yolu: %d · onbellek muafiyeti: %d anahtar'
          % (len(dosyalar), sayim, len(CACHE_KEYS)))
    print('  sentetik pozitif: %d/%d · sentetik negatif: %d/%d' % (poz, poz_t, neg, neg_t))
    if poz != poz_t or neg != neg_t:
        print('  ✗ KAPI KENDI KONTROLUNDEN DUSTU — dedektor kor veya sahte alarm uretiyor.')
        return 1
    if pk is None:
        print('  ⚠ pozitif kontrol KOSULAMADI: %s' % pk_not)
    elif pk < 1:
        print('  ✗ POZITIF KONTROL DUSTU: 8781e71 uzerinde ihlal gorulmedi — kapi kor.')
        return 1
    else:
        print('  pozitif kontrol: %d ihlal (8781e71 = K-BM oncesi) — %s' % (pk, pk_not))

    if ihlal:
        print('  ✗ %d ihlal:' % len(ihlal))
        for f, ln, k, sb in ihlal:
            print('     %s:%d  anahtar=%s  -> %s' % (f.relative_to(ROOT), ln, k, sb))
        return 1
    print('  ✓ bozuk yerel kayit hicbir yolda sessizce sifirlanmiyor')
    return 0


if __name__ == '__main__':
    sys.exit(main())
