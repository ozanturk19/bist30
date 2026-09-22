#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""KAPI 65 -- K-CT: adres cubugunun SAHIPLIGI (form-disi URL durumu).

Kapi 64 (form-url-state-check) kapsamini "URLSearchParams kurup fetch eden
fonksiyon" + "URL degerini `.value` ile forma yazan hidrator" olarak tanimlar.
/sektor-harita durumunu FORM ALANIYLA degil `aria-pressed` cipleriyle tasir ve
adrese `new URL(location.href)` uzerinden yazar -- kapi 64'un okuma yuzeyine
HIC girmiyordu (76/109. ders: dedektorun sekli yuzeyi secer).

Canli olculen kusur (22.09, borsapusula.com/sektor-harita):
  Karsilastir'da 2 sektor sec -> Isi Haritasi'na don
  -> adres `?tab=heatmap&s=Ulasim&s=Telekom` kaliyordu.
  O adres acildiginda `loadSectors()` hic kosmadigi icin `_selected` [] geliyordu
  -- sayfa KENDI URETTIGI olu derin baglantiyi paylastiriyordu.
  Ayrica `?tab=compare&s=Ulasim` (tek sektor) -> "Secili: 0 sektor":
  yazilan deger okuma esigine (`pre.length >= 2`) takiliyordu.

Kurallar:
  R1 TEK YAYIMCI  -- bir sablonda `history.push/replaceState`i GOVDESINDE
     dogrudan bulunduran en fazla BIR fonksiyon olabilir. Iki yazar =
     "ayni is icin iki kanon" (K-turu ortak merceği); sektor_harita'da
     `switchSektorTab` yalniz `tab`i, `updateHint` yalniz `s`yi yaziyordu ve
     ikisi birbirinden habersizdi.
  R2 TUR-GIDIS   -- yayimcinin govdesinde literal adla yazilan her parametre
     (`searchParams.set('x'` / `.append('x'`) ayni sablonda geri OKUNMALI
     (`searchParams.get('x')` / `.getAll('x')`).
  R3 BIRIKME     -- `append('x')` mevcut adresi TASIYAN bir URL uzerinde
     onceden `delete('x')` yapilmadan cagrilirsa deger her yayimda birikir
     (`?s=A&s=A&s=B`). Sifirdan kuran yayimci (durum degiskeninden
     `new URLSearchParams(...)`, /tarama'nin `_writeTaramaUrl`i) MUAF.
  R4 SEKME KAPSAMI -- `tab` yazan bir yayimci, mevcut adresi tasiyorsa kendi
     yazdigi HER parametreyi ayrica `delete` etmeli. K-CT'nin ta kendisi:
     `tab` varsayilana donerken `s` adreste kaliyordu, yani adres artik
     gosterilmeyen sekmenin durumunu iddia ediyordu.
  Muafiyet anlam kuralidir: `set()` ayni anahtari degistirir, birikmez --
  bu yuzden R3 yalniz `append`e, R4 yalniz sekme kapsamli yayimciya bakar.
"""
import os, re, sys, subprocess

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

_FN_RE = re.compile(r'(?:async\s+)?function\s+([A-Za-z_$][\w$]*)\s*\([^)]*\)\s*\{')
WRITER_TOKENS = ('pushState', 'replaceState')


def _templates(ref=None):
    if ref:
        names = subprocess.check_output(
            ['git', 'ls-tree', '-r', '--name-only', ref, 'templates/'],
            cwd=ROOT).decode('utf-8').split('\n')
        for n in names:
            if n.endswith('.html'):
                blob = subprocess.check_output(['git', 'show', '%s:%s' % (ref, n)],
                                               cwd=ROOT).decode('utf-8')
                yield n, blob
        return
    tdir = os.path.join(ROOT, 'templates')
    for dirpath, _dirs, files in os.walk(tdir):
        for n in sorted(files):
            if n.endswith('.html'):
                fp = os.path.join(dirpath, n)
                with open(fp, encoding='utf-8') as f:
                    yield os.path.relpath(fp, ROOT), f.read()


def _inline_js(html):
    return '\n'.join(re.findall(r'<script(?![^>]*\bsrc=)[^>]*>(.*?)</script>', html, re.S))


def _functions(js):
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


_WRITES_RE = re.compile(r"searchParams\.(?:set|append)\(\s*['\"]([\w-]+)['\"]")
_APPENDS_RE = re.compile(r"searchParams\.append\(\s*['\"]([\w-]+)['\"]")
_DELETES_RE = re.compile(r"searchParams\.delete\(\s*['\"]([\w-]+)['\"]")
# Okuma yuzeyi: `params.get('x')` cok kez `searchParams` adini TASIMAZ
# (`var params = new URLSearchParams(location.search)`), bu yuzden alici adi
# serbest birakildi -- 109. ders: dedektorun okuma yuzeyi govdeyle bitmez.
_READS_RE = re.compile(r"\.get(?:All)?\(\s*['\"]([\w-]+)['\"]")
_CARRIES_RE = re.compile(r'new\s+URL\(\s*(?:window\.)?location\.href'
                         r'|URLSearchParams\(\s*(?:window\.)?location\.search')


def check(ref=None, _src=None):
    violations = []
    n_tpl = 0
    stream = [('<enjekte>', _src)] if _src is not None else _templates(ref)

    for path, html in stream:
        js = _inline_js(html)
        if not any(t in js for t in WRITER_TOKENS):
            continue
        n_tpl += 1
        fns = _functions(js)
        writers = sorted(n for n, b in fns.items() if any(t in b for t in WRITER_TOKENS))

        # ---- R1: tek yayimci ----
        if len(writers) > 1:
            violations.append(
                '%s: R1 -- adres cubugunu %d ayri fonksiyon yaziyor (%s); '
                'tek yayimci olmali, aksi halde her yazar digerinin parametresinden '
                'habersiz kalir (K-CT: Isi Haritasi adresinde Karsilastir durumu)'
                % (path, len(writers), ', '.join('`%s()`' % w for w in writers)))

        reads = set(_READS_RE.findall(js))
        for w in writers:
            body = fns[w]
            written = sorted(set(_WRITES_RE.findall(body)))
            appended = set(_APPENDS_RE.findall(body))
            deleted = set(_DELETES_RE.findall(body))
            carries = bool(_CARRIES_RE.search(body))
            for k in written:
                # ---- R2: tur-gidis ----
                if k not in reads:
                    violations.append(
                        '%s: R2 -- `%s()` `%s` parametresini adrese yaziyor ama sablon '
                        'onu hicbir yerde geri okumuyor (paylasilan baglanti olu acilir)'
                        % (path, w, k))
                # ---- R3: birikme ----
                if carries and k in appended and k not in deleted:
                    violations.append(
                        '%s: R3 -- `%s()` mevcut adresi tasiyip `%s`i `append` ediyor ama '
                        'once `delete` etmiyor: deger her yayimda birikir (?%s=A&%s=A)'
                        % (path, w, k, k, k))
                # ---- R4: sekme kapsami ----
                if carries and 'tab' in written and k not in deleted:
                    violations.append(
                        '%s: R4 -- `%s()` sekme kapsamli bir yayimci (`tab` yaziyor) ama '
                        '`%s`i hic `delete` etmiyor: sekme varsayilana donunce adres artik '
                        'gosterilmeyen sekmenin durumunu iddia eder' % (path, w, k))

    return violations, n_tpl


# ── Pozitif kontrol (59. ders: dusen adim kusuru kanitlamaz, bozugu ENJEKTE et) ──
_OK = """<script>
function _pub(tab) {
  var url = new URL(location.href);
  url.searchParams.delete('tab'); url.searchParams.delete('s');
  if (tab === 'compare') { url.searchParams.set('tab','compare'); url.searchParams.append('s','X'); }
  history.replaceState(null, '', url.toString());
}
function _read() { var p = new URLSearchParams(location.search);
  return p.get('tab') === 'compare' || p.getAll('s').length > 0; }
</script>"""

_BAD_R1 = _OK.replace('function _read() {',
                      "function _other() { history.replaceState(null,'',location.pathname); }\n"
                      'function _read() {')
_BAD_R2 = _OK.replace("p.getAll('s').length > 0", 'false')
_BAD_R3 = _OK.replace("url.searchParams.delete('tab'); url.searchParams.delete('s');",
                      "url.searchParams.delete('tab');")


def self_test():
    cases = [('temiz agac', _OK, 0), ('R1 ikinci yazar', _BAD_R1, 'R1'),
             ('R2 okunmayan parametre', _BAD_R2, 'R2'),
             ('R3 biriken append', _BAD_R3, 'R3'), ('R4 sekme disi sizinti', _BAD_R3, 'R4')]
    ok = 0
    for name, src, want in cases:
        v, _ = check(_src=src)
        if want == 0:
            good = not v
        else:
            good = any(want + ' --' in x for x in v)
        print('  %s %-26s %s' % ('✓' if good else '✗', name,
                                 ('%d ihlal' % len(v)) if v else 'ihlal yok'))
        if not good:
            for x in v:
                print('      ' + x)
        ok += 1 if good else 0
    print('self-test %d/%d' % (ok, len(cases)))
    return ok == len(cases)


if __name__ == '__main__':
    if '--self-test' in sys.argv:
        sys.exit(0 if self_test() else 1)
    ref = None
    if '--ref' in sys.argv:
        ref = sys.argv[sys.argv.index('--ref') + 1]
    v, n = check(ref)
    if v:
        print('KAPI 65 KIRIK — adres cubugu sahipligi (%d ihlal):' % len(v))
        for x in v:
            print('  - ' + x)
        sys.exit(1)
    print('KAPI 65 OK — adres cubugunun tek sahibi var, yazilan her parametre '
          'geri okunuyor ve sekme degisiminde temizleniyor (%d sablon)' % n)
