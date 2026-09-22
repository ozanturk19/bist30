#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""KAPI 67 -- K-CV: GIZLILIK METNI ILE GERCEK VERI AKISI ARASINDAKI KANON.

Kapi 66 (K-CU) "sunucuda yasayan durumun istemcideki sahibi var mi" diye
soruyordu. Bu kapi ayni paylasilan-yuzey mercegini bir kez daha kaydirir:
kullanicinin verisi hakkinda SITENIN YAZILI BEYANI da bir kanondur, ve
kodla ayrisabilir. Fark su: digerleri bozuldugunda UI yanlis gosterir --
bu bozuldugunda site KVKK kapsaminda YANLIS BEYANDA BULUNUR.

Canli olculen kusur (22.09, /gizlilik):
  * Cerezler paragrafi: "Tarayicinizin oturum verisi (localStorage) tema
    tercihi, IZLEME LISTESI gibi yerel ayarlari saklamak icin kullanilir ve
    SUNUCUYA GONDERILMEZ."  -- Giris yapmis kullanicida /hisse/<T> 🔔 dugmesi
    hisseyi izleme listesine eklerken `POST /api/user-alerts/<T>` gonderiyor;
    kayit `subs[email]["alerts"][ticker]` olarak E-POSTA ADRESIYLE
    ILISKILENDIRILEREK sunucuda duruyor. Beyan duz yanlisti.
  * "tema tercihi" diye saklanan hicbir sey yok (site dark-only; 15 localStorage
    anahtarinin hicbiri temayla ilgili degil) -- var olmayan bir kategori.
  * "Portfoy/izleme listesi (istege bagli bulut senkronizasyonu)" maddesi
    izleme listesini YANLIS KANALA atfediyordu: bulut sync govdesi
    `{positions: portfolio}` -- izleme listesi o kanalda hic yok.
  * Gercek kanal (e-posta anahtarli alarm kaydi) hicbir yerde aciklanmamisti.
  Yani ayni sayfa 20 satir arayla hem "sunucuda saklanir" hem "sunucuya
  gonderilmez" diyordu: tek is icin iki kanon (tekrar eden P1 mercegi).

Kurallar (ikisi de CIFT YONLU -- envanter <-> beyan):
  R1 TOPLAMA KANALI BEYAN EDILMELI -- istemci kodunda kullanici verisini
     sunucuya YAZAN (POST/PUT/DELETE) her endpoint, asagidaki WRITE_CHANNELS
     tablosunda bulunmali; tabloda "anchors" verilmisse o capa metinlerinin
     HEPSI gizlilik.html'de gecmeli. Kodda yeni bir yazma kanali belirip
     tabloda karsiligi yoksa -> FAIL (yeni toplama kanali gizlilik metnine
     islenmemis olabilir). Tabloda olup kodda artik cagrilmayan kanal da
     FAIL -> metin var olmayan bir toplamayi beyan ediyor.
  R2 YEREL DEPO ENVANTERI CIFT YONLU -- kodda gecen her `bp_*` localStorage
     anahtari LOCAL_KEYS tablosunda siniflanmali; tablodaki her anahtar da
     kodda gercekten bulunmali. `server_mirror=True` isaretli bir anahtar
     varken gizlilik.html'de MUTLAK bir "sunucuya gonderilmez" cumlesi
     (nitelendirilmemis) bulunmamali -- nitelendirme icin cumlede
     "varsayilan olarak" / "istisna" gecmeli.

Kullanim:
  python3 tools/privacy-claim-flow-check.py
  python3 tools/privacy-claim-flow-check.py --self-test     # pozitif kontrol
  python3 tools/privacy-claim-flow-check.py --ref <commit>  # eski agaci olc
"""
import io
import os
import re
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PRIVACY = 'templates/gizlilik.html'

# --- R1 tablosu: istemciden kullanici verisi yazan her kanal + gizlilik capasi ---
# anchors: gizlilik.html'de GECMESI gereken metinler (hepsi).
WRITE_CHANNELS = {
    '/api/subscribe':      ['E-posta adresi', 'Abonelik tamamen gönüllülük'],
    '/api/profile':        ['Bildirim tercihleri', 'mail sıklığı tercihi'],
    '/api/portfolio':      ['Buluta kaydet', 'bağlantı koduyla (token)'],
    '/api/user-alerts':    ['Hisse bazlı e-posta alarmları', 'o hissenin sembolü ve seçtiğiniz alarm koşulu'],
    '/api/contact':        ['İletişim formu', 'ayrı bir veritabanında saklanmaz'],
    '/api/log-error':      ['JavaScript hatası', 'kaynak dosyası/satır numarası'],
}

# --- R2 tablosu: kodda yasayan her bp_* yerel anahtari ---
# server_mirror=True -> bu anahtarin icerigi (tamami ya da bir tureviyle)
# kullanicinin bir eylemiyle sunucuya da yaziliyor.
LOCAL_KEYS = {
    'bp_portfolio':          dict(server_mirror=True,  note='Cloud Sync: POST /api/portfolio/<token>'),
    'bp_portfolio_bozuk':    dict(server_mirror=False, note='bozuk kaydin yerel yedegi'),
    'bp_cloud_token':        dict(server_mirror=False, note='token yalniz URL yolunda kullanilir'),
    'bp_watchlist_v2':       dict(server_mirror=True,  note='giris varsa POST/DELETE /api/user-alerts/<T>'),
    'bp_watchlist':          dict(server_mirror=False, note='legacy, yalniz bir kez migrate edilir'),
    'bp_sub_user':           dict(server_mirror=False, note='/api/me yanitinin yerel onbellegi'),
    'bp_sub_dismissed_v2':   dict(server_mirror=False, note='abonelik bandi kapatildi mi'),
    'bp_ga_consent':         dict(server_mirror=False, note='GA4 onayi'),
    'bp_learning_mode':      dict(server_mirror=False, note='Ogrenme Modu acik/kapali'),
    'bp_show_tooltips':      dict(server_mirror=False, note='ipucu balonlari'),
    'bp_hisse_tab':          dict(server_mirror=False, note='son acik sekme'),
    'bp_tarama_tab':         dict(server_mirror=False, note='son acik sekme'),
    'bp_ls_warn_dismissed':  dict(server_mirror=False, note='localStorage uyari bandi'),
    'bp_search_cache_v1':    dict(server_mirror=False, note='arama onbellegi'),
    'bp_search_t_v1':        dict(server_mirror=False, note='arama onbellegi zaman damgasi'),
}

# Mutlak "sunucuya gitmez" iddiasi -- nitelendirilmemisse R2 ihlali.
_ABS_CLAIM_RE = re.compile(
    r'[^.]*(?:sunucuya\s+(?:gönderilmez|gonderilmez|gitmez|aktarılmaz|aktarilmaz)'
    r'|sunucuda\s+(?:saklanmaz|tutulmaz))[^.]*', re.I)
_QUALIFIERS = ('varsayılan olarak', 'varsayilan olarak', 'istisna')

_FETCH_RE = re.compile(r"""fetch\(\s*[`'"]([^`'"]+)""")
_METHOD_RE = re.compile(r"method\s*:\s*['\"](\w+)", re.I)


def _read(path, ref=None):
    if ref:
        try:
            return subprocess.check_output(['git', 'show', '%s:%s' % (ref, path)],
                                           cwd=ROOT, stderr=subprocess.DEVNULL).decode('utf-8', 'replace')
        except subprocess.CalledProcessError:
            return ''
    fp = os.path.join(ROOT, path)
    if not os.path.exists(fp):
        return ''
    return io.open(fp, encoding='utf-8', errors='replace').read()


def _client_files(ref=None):
    if ref:
        out = subprocess.check_output(['git', 'ls-tree', '-r', '--name-only', ref],
                                      cwd=ROOT).decode('utf-8', 'replace').split('\n')
        paths = [p for p in out if (p.startswith('templates/') and p.endswith('.html'))
                 or (p.startswith('static/') and p.endswith('.js'))]
    else:
        paths = []
        for base in ('templates', 'static'):
            for dirpath, _d, files in os.walk(os.path.join(ROOT, base)):
                if 'node_modules' in dirpath:
                    continue
                for f in files:
                    if f.endswith('.html') or f.endswith('.js'):
                        paths.append(os.path.relpath(os.path.join(dirpath, f), ROOT))
    return [(p, _read(p, ref)) for p in sorted(paths)]


def _write_endpoints(files):
    """Istemcide POST/PUT/DELETE ile cagrilan /api/... taban yollari."""
    found = set()
    for _name, src in files:
        for m in _FETCH_RE.finditer(src):
            url = m.group(1)
            if not url.startswith('/api/'):
                continue
            tail = src[m.end():m.end() + 400]
            meth = _METHOD_RE.search(tail)
            if not meth or meth.group(1).upper() not in ('POST', 'PUT', 'DELETE', 'PATCH'):
                continue
            base = '/' + '/'.join(url.split('?')[0].strip('/').split('/')[:2])
            found.add(base)
    return found


def _plain(html):
    """Iddia OLUSTURULMUS metinde yasar, isaretlemede degil (52. ders).

    Kapinin ilk yazimi ham HTML'de cumle ariyordu; `[^.<>]*` sinirlayicisi
    "varsayilan olarak" nitelendirmesini <strong>...</strong> icinde birakinca
    cumleyi ikiye boluyor ve DUZELTILMIS metni ihlal sayiyordu. Etiketleri
    bosluga cevirip olc.
    """
    txt = re.sub(r'(?is)<(script|style)\b.*?</\1>', ' ', html)
    txt = re.sub(r'<[^>]+>', ' ', txt)
    txt = txt.replace('&nbsp;', ' ').replace('&amp;', '&')
    return re.sub(r'[ \t]+', ' ', txt)


def _storage_keys(files):
    """Yerel depoya YAZILAN/OKUNAN bp_* anahtarlarini topla.

    115. ders (ilk yazimin kusurun YAZIMINI kacirmasi) burada bir kez daha
    isirdi: kapinin ilk hali yalniz `localStorage`in +-300 karakter komsulugunu
    tariyordu, ama gercek kodda anahtar SABITE aliniyor
    (`const HIB_WATCH_KEY = 'bp_watchlist_v2'`) ve localStorage cagrisi
    yuzlerce satir asagida sabiti kullaniyor -> K-CV'nin kendi anahtari
    "kodda yok" sayiliyordu. Bu yuzden dolayli yol da izlenir: KEY/TOKEN adli
    bir tanimlayiciya atanan bp_* dizgesi, o tanimlayici ayni dosyada bir
    localStorage/sessionStorage cagrisinda geciyorsa sayilir.
    """
    keys = set()
    lit = re.compile(r"""['"](bp_[a-z0-9_]+)['"]""")
    assign = re.compile(r"""(?:const|let|var)\s+([A-Za-z_$][\w$]*)\s*=\s*['"](bp_[a-z0-9_]+)['"]""")
    for _name, src in files:
        if 'localStorage' not in src and 'sessionStorage' not in src:
            continue
        # a) dogrudan: anahtar localStorage cagrisinin yakininda
        for m in lit.finditer(src):
            w = src[max(0, m.start() - 300):m.end() + 300]
            if 'localStorage' in w or 'sessionStorage' in w:
                keys.add(m.group(1))
        # b) dolayli: sabite alinmis anahtar, sabit storage cagrisinda kullaniliyor
        for m in assign.finditer(src):
            ident, key = m.group(1), m.group(2)
            if re.search(r'(?:local|session)Storage\.\w+\(\s*%s\b' % re.escape(ident), src):
                keys.add(key)
    return keys


def rule_R1(files, privacy):
    v = []
    found = _write_endpoints(files)
    for ep in sorted(found - set(WRITE_CHANNELS)):
        v.append('R1 %s: istemci bu endpoint\'e kullanici verisi YAZIYOR ama '
                 'WRITE_CHANNELS tablosunda yok -- gizlilik metnine islendi mi?' % ep)
    for ep in sorted(set(WRITE_CHANNELS) - found):
        v.append('R1 %s: tabloda beyan edilmis ama istemcide artik yazma cagrisi yok -- '
                 'gizlilik metni var olmayan bir toplamayi aciklıyor olabilir.' % ep)
    for ep in sorted(found & set(WRITE_CHANNELS)):
        for anchor in WRITE_CHANNELS[ep]:
            if anchor not in privacy:
                v.append('R1 %s: gizlilik.html capasi kayip -> %r' % (ep, anchor))
    return v


def rule_R2(files, privacy):
    v = []
    in_code = _storage_keys(files)
    for k in sorted(in_code - set(LOCAL_KEYS)):
        v.append('R2 %s: kodda yerel depo anahtari var, LOCAL_KEYS tablosunda yok -- '
                 'gizlilik siniflandirmasi yapilmamis.' % k)
    for k in sorted(set(LOCAL_KEYS) - in_code):
        v.append('R2 %s: tabloda var ama kodda bulunamadi -- olu siniflandirma.' % k)
    mirrored = [k for k, d in LOCAL_KEYS.items() if d['server_mirror'] and k in in_code]
    if mirrored:
        for sent in _ABS_CLAIM_RE.findall(_plain(privacy)):
            low = sent.lower()
            if not any(q in low for q in _QUALIFIERS):
                v.append('R2 gizlilik.html: NITELENDIRILMEMIS mutlak iddia (%s sunucuya da '
                         'yaziliyor): %r' % (', '.join(sorted(mirrored)), sent.strip()[:120]))
    return v


# ---------------------------------------------------------------- pozitif kontrol
_CASES = [
    # (ad, dosyalar, gizlilik metni, beklenen ihlal var mi)
    ('K-CV kusuru: mutlak iddia + sunucuya yazilan anahtar',
     [('templates/x.html', "localStorage.getItem('bp_watchlist_v2');"
                           "fetch('/api/user-alerts/'+T,{method:'POST'})")],
     'localStorage izleme listesi gibi ayarlari saklar ve sunucuya gönderilmez.', True),
    ('duzeltilmis: iddia nitelendirilmis',
     [('templates/x.html', "localStorage.getItem('bp_watchlist_v2');"
                           "fetch('/api/user-alerts/'+T,{method:'POST'})")],
     'localStorage ... varsayılan olarak sunucuya gönderilmez. İki istisna vardır.', False),
    ('siniflanmamis yeni anahtar',
     [('templates/x.html', "localStorage.setItem('bp_yeni_alan','1')")],
     'metin', True),
    ('beyan edilmemis yeni yazma kanali',
     [('templates/x.html', "fetch('/api/telemetry',{method:'POST'})")],
     'metin', True),
    ('temiz: yerel-only anahtar, mutlak iddia serbest',
     [('templates/x.html', "localStorage.getItem('bp_show_tooltips')")],
     'Bu veriler sunucuya gönderilmez.', False),
]


def _self_test():
    global LOCAL_KEYS, WRITE_CHANNELS
    real_lk, real_wc = LOCAL_KEYS, WRITE_CHANNELS
    ok = 0
    for name, files, privacy, expect in _CASES:
        # Tablolari vakanin kodunda GERCEKTEN gecen anahtarlara indirge.
        # Dikkat: naif `k in src` alt-dize eslemesi 'bp_watchlist'i
        # 'bp_watchlist_v2' iceren kodda da var sayar -> sahte ihlal.
        src = '\n'.join(s for _n, s in files)
        present = set(re.findall(r"['\"](bp_[a-z0-9_]+)['\"]", src))
        LOCAL_KEYS = {k: v for k, v in real_lk.items() if k in present}
        WRITE_CHANNELS = {k: [] for k in real_wc if k in src}
        v = rule_R1(files, privacy) + rule_R2(files, privacy)
        got = bool(v)
        mark = '✓' if got == expect else '✗'
        if got == expect:
            ok += 1
        print('  %s %s (ihlal=%s, beklenen=%s)' % (mark, name, got, expect))
    LOCAL_KEYS, WRITE_CHANNELS = real_lk, real_wc
    print('  %d/%d' % (ok, len(_CASES)))
    return 0 if ok == len(_CASES) else 1


def main():
    if '--self-test' in sys.argv:
        return _self_test()
    ref = None
    if '--ref' in sys.argv:
        ref = sys.argv[sys.argv.index('--ref') + 1]
    files = _client_files(ref)
    privacy = _read(PRIVACY, ref)
    if not privacy:
        print('  ✗ %s okunamadi' % PRIVACY)
        return 1
    v = rule_R1(files, privacy) + rule_R2(files, privacy)
    for x in v:
        print('  ✗ ' + x)
    if v:
        print('  %d ihlal' % len(v))
        return 1
    print('  gizlilik beyani <-> veri akisi tutarli (%d yazma kanali, %d yerel anahtar)'
          % (len(WRITE_CHANNELS), len(LOCAL_KEYS)))
    return 0


if __name__ == '__main__':
    sys.exit(main())
