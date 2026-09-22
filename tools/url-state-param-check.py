#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""KAPI 62 (K-CQ, 22.09.2026) -- URL DURUMUNUN COK-YAZARLI KORUNUMU.

NEDEN BU KAPI VAR
-----------------
/tarama'da URL durumu IKI yazardan yonetiliyordu:

  * `applyFilters()`  -- filtreleri URL'ye yazar. URL'yi SIFIRDAN kuruyordu:
        new URLSearchParams({signal, min_adx, sector, min_price, ...})
        newUrl = location.pathname + '?' + params.toString()
    `tab` bu sozlukte olmadigi icin HER cagri onu dusuruyordu.
  * `switchTaramaTab()` -- sekme adini URL'ye yazar (`set('tab')`/`delete`).

Init akisi `applyFilters()` -> sonra `searchParams.get('tab')` oldugu icin
sekme, okunmadan ONCE siliniyordu.

CANLI OLCUM (22.09): `/tarama?tab=temel` ile acilan sayfa URL'yi `/tarama`ya
ceviriyor ve TEKNIK sekmesini aciyordu (aria-selected teknik:true /
temel:false, panelTemel display:none). Yani Temel sekmesine DOGRUDAN
BAGLANTI -- paylasilan link, yer imi, yonlendirme -- hic calismiyordu.
Enjeksiyon olcumu: yamasiz `?tab=temel&min_adx=30` -> `` (init "teknik"),
yamali -> `?tab=temel` (init "temel").

NE OLCULUR
----------
Bir sablonda URL'yi SIFIRDAN kuran bir yazar varsa (ayni ifadede
`location.pathname` + bir URLSearchParams'in `.toString()`i), o sablonda
DURUM PARAMETRESI olan her ad onun sozlugunde bulunmalidir.

"Durum parametresi" olmanin olcutu okunmak degil, ikisi birden:
  (a) `searchParams.get('X')` ile OKUNUYOR   ve
  (b) `searchParams.set('X'` / `.delete('X'` ile URL'ye YAZILIYOR
Ikinci kosul, `?d=` gibi salt-okunur/tek-yonlu parametreleri disarida
birakir -- muafiyet ANLAM kuralidir, satir numarasi degil (43. ders).

R2 -- VARSAYILAN SEKME URL'DE GORUNMEZ (K-CR, 22.09)
------------------------------------------------------
Uc sekme sisteminde sekme adinin URL kurali UC FARKLIYDI:
  /tarama        varsayilan "teknik" -> `delete('tab')`   (URL temiz)
  /hisse         varsayilan "ozet"   -> `set('tab','ozet')`
  /sektor-harita varsayilan "heatmap"-> `set('tab','heatmap')`
Temiz `/hisse/ASELS` acilisi adres cubugunu `/hisse/ASELS?tab=ozet` yapiyordu;
sayfanin KENDI ilan ettigi kanonik adres (link rel=canonical + og:url, ikisi de
parametresiz -- canli olcum 22.09) bundan farkliydi, yani kullanicinin
kopyaladigi adres ayni icerigi ikinci bir URL'den yayiyordu. /sektor-harita'da
yazilan deger ustelik OLU: okuma tarafi yalniz `=== 'compare'`e bakiyor.
Kanon /tarama'nindir. Olculebilir bicimi: bir sablon `searchParams.set('tab')`
yaziyorsa, ayni sablonda `searchParams.delete('tab')` de bulunmalidir --
varsayilani temizleyecek bir yol yoksa varsayilan kacinilmaz olarak yazilir.

DERS (K-turu ortak mercegi): "ayni is icin iki kanon" basli basina
bulgudur. Burada iki kanon CAKISMIYOR, biri digerinin alanini SESSIZCE
siliyordu -- ve silinen sey bir sonraki satirda okunuyordu.
"""
import os
import re
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TPL = os.path.join(ROOT, "templates")

_RE_U = re.compile(r"\\u([0-9a-fA-F]{4})")
def coz(s):
    return _RE_U.sub(lambda m: chr(int(m.group(1), 16)), s)

_RE_GET = re.compile(r"""searchParams\.get\(\s*['"]([^'"]+)['"]""")
_RE_SETDEL = re.compile(r"""searchParams\.(?:set|delete)\(\s*['"]([^'"]+)['"]""")
# sifirdan kuran yazar: ayni ifadede pathname + <usp>.toString()
_RE_SCRATCH = re.compile(r"location\.pathname\b[^\n;]{0,200}?(\w+)\.toString\(\)")
_RE_USP_ASSIGN = re.compile(r"""(?:var|let|const)\s+(\w+)\s*=\s*new\s+URLSearchParams\(""")


def _tpl_files():
    return [(fn, os.path.join(TPL, fn))
            for fn in sorted(os.listdir(TPL)) if fn.endswith(".html")]


def _read(path, ref=None, rel=None):
    if ref:
        try:
            return subprocess.check_output(
                ["git", "show", "%s:%s" % (ref, rel)], cwd=ROOT,
                stderr=subprocess.DEVNULL).decode("utf-8", "replace")
        except subprocess.CalledProcessError:
            return None
    with open(path, encoding="utf-8") as f:
        return f.read()


def _usp_dict_keys(text, var):
    """`new URLSearchParams({...})` sozluk anahtarlari + `<var>.set('x'` adlari."""
    keys = set()
    m = re.search(r"(?:var|let|const)\s+%s\s*=\s*new\s+URLSearchParams\(\s*\{" % re.escape(var), text)
    if m:
        depth, i = 0, text.index("{", m.start())
        for j in range(i, min(len(text), i + 4000)):
            if text[j] == "{":
                depth += 1
            elif text[j] == "}":
                depth -= 1
                if depth == 0:
                    body = text[i:j]
                    break
        else:
            body = text[i:i + 4000]
        for km in re.finditer(r"""(?:^|[\{,\s])['"]?([A-Za-z_][\w\-]*)['"]?\s*:""", body):
            keys.add(km.group(1))
        # kisayol ozellik ({signal, sector}) -- iki nokta olmayan cıplak adlar
        for km in re.finditer(r"""(?:^|[\{,])\s*([A-Za-z_][\w]*)\s*(?=[,\}])""", body):
            keys.add(km.group(1))
    for km in re.finditer(r"""\b%s\.set\(\s*['"]([^'"]+)['"]""" % re.escape(var), text):
        keys.add(km.group(1))
    return keys


def scan_file(rel, text):
    viol = []
    t = coz(text)
    read = set(_RE_GET.findall(t))
    written = set(_RE_SETDEL.findall(t))
    state = read & written           # hem okunan hem URL'ye yazilan = durum param

    # R2 — varsayilan sekme URL'de gorunmez: set('tab') varsa delete('tab') de olmali
    if re.search(r"""searchParams\.set\(\s*['"]tab['"]""", t) and not re.search(
            r"""searchParams\.delete\(\s*['"]tab['"]""", t):
        m2 = re.search(r"""searchParams\.set\(\s*['"]tab['"]""", t)
        viol.append((rel, t[:m2.start()].count("\n") + 1, "R2",
                     "`searchParams.set('tab')` var ama `delete('tab')` yok -- "
                     "varsayilan sekme de URL'ye yaziliyor, adres sayfanin kendi "
                     "canonical/og:url'inden ayrisiyor (kanon: /tarama)"))

    scratch = _RE_SCRATCH.findall(t)
    if not state or not scratch:
        return viol, len(state)

    for var in set(scratch):
        if not _RE_USP_ASSIGN.search(t) and not re.search(
                r"(?:var|let|const)\s+%s\s*=" % re.escape(var), t):
            continue
        covered = _usp_dict_keys(t, var)
        m = re.search(r"location\.pathname\b[^\n;]{0,200}?%s\.toString\(\)" % re.escape(var), t)
        ln = t[:m.start()].count("\n") + 1 if m else 0
        for name in sorted(state - covered):
            viol.append((rel, ln, "R1",
                         "URL sifirdan `%s`ten kuruluyor ama durum parametresi "
                         "\"%s\" o sozlukte yok -- her cagri onu dusuruyor "
                         "(baska bir yerde set/delete ile yazilip "
                         "searchParams.get ile okunuyor)" % (var, name)))
    return viol, len(state)


def run(ref=None, verbose=False):
    viol, states, files = [], 0, 0
    for fn, path in _tpl_files():
        rel = "templates/" + fn
        text = _read(path, ref, rel)
        if text is None:
            continue
        files += 1
        v, n = scan_file(rel, text)
        viol += v
        states += n
        if verbose and n:
            print("  girdi: %-34s %d durum parametresi" % (rel, n))
    return viol, states, files


def self_test():
    """Pozitif kontrol (85. ders) -- bozuk hali ENJEKTE et."""
    bozuk = """
      function applyFilters(){
        const params = new URLSearchParams({signal: sig, min_adx: a, sector: s});
        const newUrl = window.location.pathname + (params.toString() ? '?' + params.toString() : '');
        history.replaceState(null,'',newUrl);
      }
      function switchTab(tab){
        const url = new URL(window.location.href);
        if (tab==='teknik') url.searchParams.delete('tab'); else url.searchParams.set('tab', tab);
        history.replaceState({tab},'',url.toString());
      }
      const t = new URL(window.location.href).searchParams.get('tab');
    """
    duzeltilmis = bozuk.replace(
        "const newUrl =",
        "const _c = new URLSearchParams(window.location.search).get('tab');\n"
        "        if (_c === 'temel') params.set('tab', _c);\n        const newUrl =")
    # salt-okunur param (yalniz get, hic set/delete) ihlal DEGIL
    saltokunur = """
      const params = new URLSearchParams({signal: sig});
      const newUrl = window.location.pathname + '?' + params.toString();
      history.replaceState(null,'',newUrl);
      const d = new URL(location.href).searchParams.get('d');
    """
    # sifirdan kuran yazar YOKSA ihlal degil
    # R1'e ozgu negatif: sifirdan-kuran yazar YOK (R2'yi tetiklememesi icin
    # varsayilani temizleme yolu da var)
    yazarsiz = """
      const url = new URL(location.href);
      if (t === 'teknik') url.searchParams.delete('tab');
      else url.searchParams.set('tab','temel');
      history.replaceState(null,'',url.toString());
      const t = new URL(location.href).searchParams.get('tab');
    """
    r2_bozuk = """
      function switchTab(tab){
        const url = new URL(location.href);
        url.searchParams.set('tab', tab);
        history.replaceState(null,'',url.toString());
      }
      const t = new URL(location.href).searchParams.get('tab');
    """
    r2_temiz = """
      function switchTab(tab){
        const url = new URL(location.href);
        if (tab === 'ozet') url.searchParams.delete('tab');
        else url.searchParams.set('tab', tab);
        history.replaceState(null,'',url.toString());
      }
      const t = new URL(location.href).searchParams.get('tab');
    """
    ok = 0
    cases = [("POZITIF R2 varsayilan yaziliyor", r2_bozuk, True),
             ("NEGATIF R2 varsayilan siliniyor", r2_temiz, False),
             ("POZITIF bozuk", bozuk, True),
             ("NEGATIF duzeltilmis", duzeltilmis, False),
             ("NEGATIF salt-okunur param", saltokunur, False),
             ("NEGATIF sifirdan-kuran yazar yok", yazarsiz, False)]
    for ad, src, bekle in cases:
        got = scan_file("sentetik.html", src)[0]
        iyi = bool(got) == bekle
        print("  [%s] %-34s -> %d ihlal" % ("OK" if iyi else "FAIL", ad, len(got)))
        ok += iyi
    return 0 if ok == len(cases) else 1


def main():
    if "--self-test" in sys.argv:
        print("KAPI 62 pozitif/negatif kontrol:")
        return self_test()
    ref = None
    if "--ref" in sys.argv:
        ref = sys.argv[sys.argv.index("--ref") + 1]
    verbose = "--verbose" in sys.argv or "-v" in sys.argv
    viol, states, files = run(ref, verbose)
    if states == 0:
        print("KAPI 62 KOR -- 0 durum parametresi ayristirildi (93. ders)")
        return 1
    if viol:
        print("KAPI 62 -- URL DURUM PARAMETRESI SESSIZCE DUSURULUYOR: %d" % len(viol))
        print("URL'yi sifirdan kuran yazar, baska bir yazarin alanini silmemeli;")
        print("silinen deger bir sonraki adimda okunuyorsa baglanti hic calismaz.\n")
        for rel, ln, code, msg in sorted(viol):
            print("  %s:%s  [%s]" % (rel, ln, code))
            print("      %s" % msg)
        return 1
    print("KAPI 62 OK -- URL durum parametreleri korunuyor "
          "(%d parametre / %d sablon)" % (states, files))
    return 0


if __name__ == "__main__":
    sys.exit(main())
