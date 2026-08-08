# -*- coding: utf-8 -*-
"""T2.2 PRE-DEPLOY KAPISI. Uc soruyu KOSARAK yanitlar; biri bile hayirsa exit 1."""
import re, os, sys, glob, hashlib, subprocess, flask

# NOT: Flask root_path'i CAGIRAN MODULUN DOSYA KONUMUNDAN turetir, cwd'den DEGIL.
# tools/ altindan calisirken template_folder='templates' -> tools/templates olur ve
# loader HICBIR sablon bulamaz; kapi 0/36 ile "hepsi kirik" der. Mutlak kok ver.
ROOT = os.path.abspath(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.chdir(ROOT)
app = flask.Flask(__name__, root_path=ROOT, template_folder='templates')
_ctx = app.app_context(); _ctx.push()   # DispatchingJinjaLoader app context ISTER
env = app.jinja_env
print('KOK           : %s' % ROOT)
fail = []

# --- KAPI 1: TUM sablonlar Jinja'da derleniyor mu (syntax) ---
# app.py'nin OZEL Jinja filtrelerini kaydet — aksi halde kapi urun kusuru OLMAYAN
# "No filter named X" hatalari uretir ve KENDI KORLUGUNU urun kusuru sanir.
_app_src = open('app.py', encoding='utf-8').read()
_custom = sorted(set(re.findall(r"@app\.template_filter\(\s*['\"]([a-zA-Z0-9_]+)['\"]", _app_src)
                     + re.findall(r"app\.jinja_env\.filters\[\s*['\"]([a-zA-Z0-9_]+)['\"]\s*\]", _app_src)))
for _f in _custom:
    env.filters.setdefault(_f, lambda v, *a, **k: v)
print('KOK filtre stub : %d (%s)' % (len(_custom), ', '.join(_custom) or '-'))

tpls = sorted(os.path.basename(f) for f in glob.glob('templates/*.html'))
d_ok = 0
for t in tpls:
    try:
        env.get_template(t); d_ok += 1
    except Exception as e:
        fail.append('DERLEME %s: %s' % (t, e))
print('KAPI1 derleme : %d/%d' % (d_ok, len(tpls)))

# --- KAPI 2: {% with %} bir {% block %} ICINDE include'a siziyor mu? ---
# (_head.html dokumanindaki "blok icinde {% set %} calismaz" uyarisinin karsiti)
probe_with = env.from_string(
    "{% extends '_base.html' %}{% block body %}"
    "{% with hdr_title = 'PROBE_TITLE', hdr_sub = 'PROBE_SUB', hdr_sub_id = 'probeId' %}"
    "{% include '_header.html' %}{% endwith %}{% endblock %}")
out_with = probe_with.render()
probe_set = env.from_string(
    "{% extends '_base.html' %}{% block body %}"
    "{% set hdr_title = 'PROBE_TITLE' %}"
    "{% include '_header.html' %}{% endblock %}")
out_set = probe_set.render()
w_ok = ('PROBE_TITLE' in out_with) and ('PROBE_SUB' in out_with) and ('id="probeId"' in out_with)
print('KAPI2 {%% with %%} blok icinde include-a siziyor : %s' % ('EVET' if w_ok else 'HAYIR'))
print('      ({%% set %%} ayni yerde siziyor mu         : %s)  <- karsilastirma icin'
      % ('EVET' if 'PROBE_TITLE' in out_set else 'HAYIR'))
if not w_ok:
    fail.append('KAPI2: {% with %} parametreleri _header.html-e ULASMIYOR')

# --- KAPI 3: hicbir sayfa sablonunda inline <header> KALMADI mi (16 hedef icin) ---
HEDEF = ['tarama','blog','gucu_yuksek','kategori','metodoloji','portfolio','abd_tarama',
         'bilanco_takvimi','gizlilik','gundem','hakkinda','iletisim','karsilastir',
         'sinyal_performans','varlik','yasal']
kalan = []
for n in HEDEF:
    s = open('templates/%s.html' % n, encoding='utf-8').read()
    if re.search(r'<header\b', s):
        kalan.append(n)
    if "_header.html" not in s:
        fail.append('KAPI3: %s _header.html-i include ETMIYOR' % n)
print('KAPI3 hedefte kalan inline <header> : %d %s' % (len(kalan), kalan or ''))
if kalan:
    fail.append('KAPI3: inline header kaldi: %s' % kalan)

# --- POZITIF KONTROL: kapilar gercekten atesleniyor mu? ---
try:
    env.from_string("{% if %}").render(); fail.append('POZITIF KONTROL: bozuk sablon HATA VERMEDI')
except Exception:
    print('POZITIF KONTROL derleme kapisi : bozuk sablon YAKALANDI (kapi kor degil)')

# --- OLCUM: kaynak header cesitliligi ---
BASE_REF = os.environ.get('T22_BASE_REF', 'e4d6c4a')
pages = [os.path.basename(f) for f in sorted(glob.glob('templates/*.html'))
         if not os.path.basename(f).startswith('_')]

def olc(getter, etiket):
    md5s, tasiyan, blok = set(), 0, 0
    for n in pages:
        try:
            src = getter(n)
        except Exception:
            continue
        ms = re.findall(r'<header\b.*?</header>', src, re.S)
        if ms:
            tasiyan += 1; blok += len(ms)
            for m in ms:
                md5s.add(hashlib.md5(m.encode()).hexdigest())
    print('OLCUM %-6s inline header tasiyan sablon=%2d/%d  blok=%2d  FARKLI md5=%2d'
          % (etiket, tasiyan, len(pages), blok, len(md5s)))
    return len(md5s)

onc = olc(lambda n: subprocess.run(['git', 'show', '%s:templates/%s' % (BASE_REF, n)],
                                   capture_output=True, text=True, check=True).stdout, 'ONCE')
son = olc(lambda n: open('templates/%s' % n, encoding='utf-8').read(), 'SONRA')
print('OLCUM kaynak header cesitliligi    : %d -> %d' % (onc, son))

print()
if fail:
    print('KAPI SONUCU: RED (%d)' % len(fail))
    for f_ in fail: print('  ', f_)
    sys.exit(1)
print('KAPI SONUCU: GECTI (3/3)')
