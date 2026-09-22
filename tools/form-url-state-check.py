#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""KAPI 64 (K-CS, 22.09.2026) -- PAYLASILAN ADRES CUBUGU VE FORM DURUMUNUN TUR-GIDISI.

NEDEN BU KAPI VAR
-----------------
/tarama'da AYNI adres cubugunu paylasan IKI form var (Teknik / Temel).
Yalniz Teknik yaziyordu:

  * applyFilters()      -> params kurar, fetch eder, URL'ye de yazar
  * applyTemelFilters() -> params kurar, fetch eder, URL'ye HIC dokunmaz

CANLI OLCUM (22.09, borsapusula.com/tarama): Temel sekmesinde
Bant=Yesil + Sektor=Enerji + Sirala=Karlilik secildi -> 2 sonuc kaldi,
adres hala `/tarama?tab=temel`. Yani Temel'de yapilan hicbir filtre
paylasilamiyor, yer imine alinamiyor, sayfa yenilenince korunmuyordu.
`tab` disindaki her sey kayboluyordu. Teknik'te ayni is calisiyordu --
"ayni is icin iki kanon" (K-turu ortak mercegi), burada biri YOK bicimde.

IKINCI BULGU -- <select> DEGERININ SESSIZ YUTULMASI
---------------------------------------------------
Iki sekme `sector` / `min_price` / `max_price` / `signal` / `sort` adlarini
paylasiyor ama deger kumeleri ayri (`sort`: teknik `signal_strength|adx|...`,
temel `temel_score|karlilik|...`). Sekme-kor hidrasyon yabanci degeri
<select>'e yaziyor; eslesen <option> olmadigi icin TARAYICI DEGERI SESSIZCE
"" YAPIYOR. Canli olcum (22.09): `/tarama?sort=temel_score` ->
`sortSel.value=""`, `selectedIndex=-1` -- "Sirala" menusu hicbir sey secili
gorunmuyordu ve `_currentSort` da "" oluyordu. Temel URL'ye yazmaya baslayinca
bu yol SISTEMATIK olarak uretilecekti.

NE OLCULUR (uc kural)
---------------------
R1 -- YAZMA SIMETRISI. Bir sablonda `new URLSearchParams({...})` kurup
     `fetch(` ile sunucuya giden birden cok "kurucu" varsa ve BIRI durumunu
     adres cubugina yayimliyorsa (dogrudan `replaceState`/`pushState`, ya da
     govdesinde bunlardan birini bulunduran bir yardimci fonksiyonu cagirarak),
     AYNI sablondaki her kurucu yayimlamalidir.

R2 -- <select> YUTULMASINA KARSI KORUMA. URL parametresini forma yazan her
     "hidrator" (govdesinde hem `searchParams.get`/`URLSearchParams(...search)`
     hem `.value =` bulunan fonksiyon) bir secenek-uyelik kontrolu (`.options`)
     icermelidir -- aksi halde eslesmeyen deger alani sessizce bosaltir.

R3 -- TUR-GIDIS. Yayimlayan bir kurucunun sozlugundeki her parametre adi,
     sablonun hidrator govdelerinde TIRNAKLI bir ad olarak gecmelidir. Adrese
     yazilip geri okunmayan bir parametre, paylasilan baglantiyi sessizce
     eksik birakir (yazmak yetmez, K-CS'in asil zarari budur).

MUAFIYET ANLAM KURALIDIR (43. ders): kapsam "URLSearchParams kurup fetch eden
fonksiyon"dur; tek kurucusu olan sablonlar R1 disindadir (paylasilan adres
cubugu catismasi yoktur), hidratoru olmayan sablonlar R2/R3 disindadir.
"""
import os
import re
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
VERBOSE = '--verbose' in sys.argv


def _templates(ref=None):
    """(yol, icerik) ciftleri. ref verilirse o commit'ten okunur."""
    out = []
    if ref:
        names = subprocess.check_output(
            ['git', 'ls-tree', '-r', '--name-only', ref, 'templates/'],
            cwd=ROOT).decode('utf-8').split('\n')
        for n in names:
            if n.endswith('.html'):
                try:
                    out.append((n, subprocess.check_output(
                        ['git', 'show', '%s:%s' % (ref, n)], cwd=ROOT).decode('utf-8')))
                except subprocess.CalledProcessError:
                    pass
    else:
        tdir = os.path.join(ROOT, 'templates')
        for n in sorted(os.listdir(tdir)):
            if n.endswith('.html'):
                with open(os.path.join(tdir, n), encoding='utf-8') as f:
                    out.append(('templates/' + n, f.read()))
    return out


def _inline_js(html):
    """src'siz <script> govdelerinin birlesimi."""
    return '\n'.join(re.findall(r'<script(?![^>]*\bsrc=)[^>]*>(.*?)</script>', html, re.S))


_FN_RE = re.compile(r'(?:async\s+)?function\s+([A-Za-z_$][\w$]*)\s*\([^)]*\)\s*\{')


def _functions(js):
    """{ad: govde} -- parantez esleyerek, string/yorum farkindaligi olmadan
    ama suslu parantez sayimi bu sablonlar icin yeterli (self-test dogruluyor)."""
    fns = {}
    for m in _FN_RE.finditer(js):
        i = m.end() - 1
        depth = 0
        for j in range(i, len(js)):
            c = js[j]
            if c == '{':
                depth += 1
            elif c == '}':
                depth -= 1
                if depth == 0:
                    fns[m.group(1)] = js[i + 1:j]
                    break
    return fns


def _split_top_level(s):
    parts, depth, cur = [], 0, ''
    for c in s:
        if c in '([{':
            depth += 1
        elif c in ')]}':
            depth -= 1
        if c == ',' and depth == 0:
            parts.append(cur)
            cur = ''
        else:
            cur += c
    if cur.strip():
        parts.append(cur)
    return parts


_USP_OBJ_RE = re.compile(r'new\s+URLSearchParams\(\s*\{(.*?)\}\s*\)', re.S)


def _param_keys(body):
    """Kurucunun sozlugundeki parametre adlari (kisayol ozellikler dahil)."""
    keys = []
    for m in _USP_OBJ_RE.finditer(body):
        for part in _split_top_level(m.group(1)):
            part = re.sub(r'/\*.*?\*/', '', part, flags=re.S).strip()
            if not part:
                continue
            name = part.split(':', 1)[0].strip().strip('"\'')
            if re.match(r'^[A-Za-z_$][\w$]*$', name):
                keys.append(name)
    # ayrica acikca set edilenler
    keys += re.findall(r"\.set\(\s*['\"]([\w-]+)['\"]", body)
    return sorted(set(keys))


WRITER_TOKENS = ('replaceState', 'pushState')


def check(ref=None):
    violations = []
    n_tpl = n_builder = 0

    for path, html in _templates(ref):
        js = _inline_js(html)
        if 'URLSearchParams' not in js:
            continue
        n_tpl += 1
        fns = _functions(js)

        # kurucular: URLSearchParams kurup fetch eden fonksiyonlar
        builders = {n: b for n, b in fns.items()
                    if 'new URLSearchParams(' in b and 'fetch(' in b}

        # yayimci yardimcilar: govdesinde replaceState/pushState olanlar VE onlari
        # cagiranlar (gecisli kapanis -- K-CS'te zincir
        # applyTemelFilters -> _publishTaramaUrl -> _writeTaramaUrl -> replaceState).
        # Kurucular bu kumeye alinmaz: yargiladigimiz sey onlarin kendisi.
        helpers = set(n for n, b in fns.items()
                      if any(t in b for t in WRITER_TOKENS) and n not in builders)
        while True:
            grown = set(n for n, b in fns.items()
                        if n not in helpers and n not in builders
                        and any(re.search(r'\b%s\s*\(' % re.escape(h), b) for h in helpers))
            if not grown:
                break
            helpers |= grown
        n_builder += len(builders)

        # hidratorlar: URL parametresi okuyup forma yazan fonksiyonlar
        hydrators = {n: b for n, b in fns.items()
                     if ('.value' in b and '=' in b
                         and ('searchParams.get' in b
                              or re.search(r'URLSearchParams\(\s*(window\.)?location\.search', b))
                         and n not in builders)}

        def publishes(body):
            if any(t in body for t in WRITER_TOKENS):
                return True
            return any(re.search(r'\b%s\s*\(' % re.escape(h), body) for h in helpers)

        pub = {n: publishes(b) for n, b in builders.items()}

        # ---- R1: yazma simetrisi ----
        if len(builders) > 1 and any(pub.values()) and not all(pub.values()):
            for n, ok in sorted(pub.items()):
                if not ok:
                    violations.append(
                        '%s: R1 -- `%s()` URL durumunu yayimlamiyor, ayni sablondaki '
                        '%s yayimliyor (paylasilan adres cubugu, yarim tur-gidis)'
                        % (path, n, ', '.join('`%s()`' % k for k, v in sorted(pub.items()) if v)))

        # ---- R2: <select> yutulmasi ----
        # koruma hidratorun KENDI govdesinde ya da cagirdigi bir yardimcida olabilir
        guard_fns = set(n for n, b in fns.items()
                        if '.options' in b or "querySelector('option" in b)

        def guarded(body):
            if '.options' in body or 'querySelector' in body:
                return True
            return any(re.search(r'\b%s\s*\(' % re.escape(g), body) for g in guard_fns)

        for n, b in sorted(hydrators.items()):
            if not guarded(b):
                violations.append(
                    '%s: R2 -- `%s()` URL degerini forma yaziyor ama secenek-uyelik '
                    'kontrolu (`.options`) yok; eslesmeyen deger <select>i sessizce bosaltir'
                    % (path, n))

        # ---- R3: tur-gidis ----
        if hydrators:
            # Okuma yuzeyi = hidrator govdeleri + onlarin adiyla andigi ust-seviye
            # esleme sozlukleri (K-CS'te `_TARAMA_URL_MAP` fonksiyonlarin DISINDA
            # duruyor; yalniz govdelere bakan bir dedektor haritayi hic gormez).
            read_blob = '\n'.join(hydrators.values())
            for om in re.finditer(r'\bconst\s+([A-Za-z_$][\w$]*)\s*=\s*\{', js):
                name = om.group(1)
                if not re.search(r'\b%s\b' % re.escape(name), read_blob):
                    continue
                i, depth = om.end() - 1, 0
                for j in range(i, len(js)):
                    if js[j] == '{':
                        depth += 1
                    elif js[j] == '}':
                        depth -= 1
                        if depth == 0:
                            read_blob += '\n' + js[i:j + 1]
                            break
            quoted = set(re.findall(r"['\"]([\w-]+)['\"]", read_blob))
            for n, b in sorted(builders.items()):
                if not pub.get(n):
                    continue
                for k in _param_keys(b):
                    if k not in quoted:
                        violations.append(
                            '%s: R3 -- `%s()` `%s` parametresini adrese yaziyor ama '
                            'hicbir hidrator onu geri okumuyor (paylasilan baglanti eksik acilir)'
                            % (path, n, k))

    return violations, n_tpl, n_builder


def self_test():
    """Pozitif kontrol: bozuk hali ENJEKTE et (59. ders -- dusen adim kusuru kanitlamaz)."""
    src = os.path.join(ROOT, 'templates', 'tarama.html')
    with open(src, encoding='utf-8') as f:
        good = f.read()
    cases = [
        ('R1 (Temel yayimlamiyor)',
         lambda s: s.replace("  _publishTaramaUrl('temel', params, { sort: 'temel_score', sort_dir: 'desc' });", ''),
         'R1'),
        ('R2 (secenek kontrolu yok)',
         lambda s: s.replace(
             "  if (el.tagName === 'SELECT' && !Array.from(el.options).some(o => o.value === val)) {\n"
             "    console.warn('URL parametresi bu sekmenin seçenekleri arasında yok, yok sayıldı:', elId, val);\n"
             "    return false;\n"
             "  }\n", ''),
         'R2'),
        ('R3 (`band` geri okunmuyor)',
         lambda s: s.replace("'band': 'fBant',", "'bant_yok': 'fBant',"),
         'R3'),
    ]
    ok = 0
    total = len(cases) + 1
    for label, mutate, tag in cases:
        broken = mutate(good)
        if broken == good:
            print('  ✗ %s: enjeksiyon UYGULANMADI (desen degismis)' % label)
            continue
        with open(src, 'w', encoding='utf-8') as f:
            f.write(broken)
        try:
            v, _, _ = check()
        finally:
            with open(src, 'w', encoding='utf-8') as f:
                f.write(good)
        hit = [x for x in v if tag in x and 'tarama.html' in x]
        if hit:
            print('  ✓ %s -> yakalandi: %s' % (label, hit[0]))
            ok += 1
        else:
            print('  ✗ %s -> YAKALANMADI' % label)
    v, _, _ = check()
    if not v:
        print('  ✓ negatif kontrol (calisma agaci) -> 0 ihlal')
        ok += 1
    else:
        print('  ✗ negatif kontrol -> %d ihlal: %s' % (len(v), v[0]))
    print('self-test %d/%d' % (ok, total))
    return 0 if ok == total else 1


def main():
    if '--self-test' in sys.argv:
        return self_test()
    ref = None
    if '--ref' in sys.argv:
        ref = sys.argv[sys.argv.index('--ref') + 1]
    v, n_tpl, n_builder = check(ref)
    if v:
        print('KAPI 64 KIRIK — %d ihlal:' % len(v))
        for x in v:
            print('  - ' + x)
        return 1
    print('KAPI 64 OK — form durumu adres cubuguyla tur-gidis yapiyor '
          '(%d sablon / %d kurucu)' % (n_tpl, n_builder))
    return 0


if __name__ == '__main__':
    sys.exit(main())
