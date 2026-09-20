#!/usr/bin/env python3
"""K-J — cache-bust hash surukleme dedektoru (CPO, 20.09.2026).

NEDEN AYRI BIR KAPI:
  static/sw.js'in STATIC precache listesi ile templates/offline.html'in
  <link> etiketleri AYNI dosyalarin cache-bust hash'ini ELLE tasiyordu ve
  ikisi birbirinden kopmustu:
      sw.js        -> /static/css/tokens.css?v=1eabd653
      offline.html -> /static/css/tokens.css?v=a9ea1d38
  `caches.match` varsayilan olarak query string'i ANAHTARIN PARCASI sayar,
  yani cevrimdisi kullanici offline.html'i cache'ten aliyor ama sayfanin
  istedigi CSS'lerin HICBIRI cache'te bulunamiyordu; ag da yok. Sonuc:
  /offline tam da ise yarayacagi anda STILSIZ aciliyordu.

  Ayni sinifin ikinci yuzu daha sinsi: bir CSS dosyasi degisip sablondaki
  ?v= GUNCELLENMEZSE Cloudflare kullanicilara ESKI dosyayi servis etmeye
  devam eder -- deploy "basarili" gorunur, fix canliya CIKMAZ. Ustteki 10
  katin hicbiri bunu goremez (hepsi dosyanin ICINE bakar, referansa degil).

OLCUT (taban SIFIR):
  Sablonlarda ve static/*.js icinde gecen her `/static/<yol>?v=<deger>`
  referansi icin, <deger> 8 haneli hex ise (yani md5 prefix konvansiyonu)
  dosyanin gercek `md5 -q <dosya> | cut -c1-8` degerine ESIT olmak zorunda.

IKINCI OLCUM — /offline precache KAPSAMI:
  Ayni sinifin diger yuzu hash degil VARLIK meselesi: offline.html'in
  istedigi bir dosya sw.js STATIC listesinde HIC yoksa (ya da orada farkli
  bir anahtarla duruyorsa) sonuc yine aynidir -- cevrimdisi kullanici o
  dosyayi alamaz. Olcum sirasinda bulundu: manifest.json / icon-192.png /
  icon-512.png listede SORGUSUZ yaziliydi, sayfalar ise hepsini `?v=<md5>`
  ile istiyordu -- ucu de cache'te kimsenin sormadigi bir anahtarda
  duruyordu. Bu yuzden offline.html Jinja ile render edilip icindeki her
  `/static/...` URL'i STATIC listesinde BIREBIR aranir.

KAPSAM SINIRI (bilerek):
  `?v=75`, `?v=4`, `?v=20260915A` gibi ELLE artirilan surum etiketleri bu
  kapinin disindadir -- bunlar md5 degil, kasitli manuel konvansiyon; tek
  gereklilikleri her degisimde artirilmalari ve bunu bu kapi olcemez.
  Referansi olup diskte OLMAYAN dosya da hata sayilir (404 asset).
"""
import hashlib
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCAN_DIRS = [
    ("templates", (".html",)),
    ("static", (".js",)),
    ("static/css", (".css",)),
    ("static/css/pages", (".css",)),
]
REF_RE = re.compile(r"/static/([A-Za-z0-9_\-./]+?\.(?:css|js|svg|png|json|woff2?))\?v=([A-Za-z0-9]+)")
MD5_RE = re.compile(r"^[0-9a-f]{8}$")


def _scan_files():
    for rel, exts in SCAN_DIRS:
        d = os.path.join(ROOT, rel)
        if not os.path.isdir(d):
            continue
        for name in sorted(os.listdir(d)):
            if name.endswith(exts) and os.path.isfile(os.path.join(d, name)):
                yield os.path.join(rel, name)


def _offline_precache_problems():
    """offline.html'in istedigi her /static/ URL'i sw.js STATIC'inde var mi."""
    try:
        from jinja2 import Environment, FileSystemLoader
    except ImportError:  # jinja2 yoksa bu olcum atlanir (ust katlar zaten var)
        return [], 0
    env = Environment(loader=FileSystemLoader(os.path.join(ROOT, "templates")), autoescape=True)
    html = env.get_template("offline.html").render()
    wanted = sorted(set(re.findall(r'/static/[^"\'\s>]+', html)))
    with open(os.path.join(ROOT, "static", "sw.js"), encoding="utf-8") as fh:
        sw = fh.read()
    m = re.search(r"const STATIC = \[(.*?)\];", sw, re.S)
    if not m:
        return ["static/sw.js: STATIC listesi bulunamadi (kapi olcum yapamadi)"], 0
    precached = set(re.findall(r"'([^']+)'", m.group(1)))
    out = []
    for url in wanted:
        if url not in precached:
            out.append(
                f"templates/offline.html: {url} sw.js STATIC listesinde YOK "
                f"-> cevrimdisi kullanici bu dosyayi alamaz"
            )
    return out, len(wanted)


def main():
    verbose = "--verbose" in sys.argv
    problems, checked, skipped = [], 0, 0
    for rel in _scan_files():
        with open(os.path.join(ROOT, rel), encoding="utf-8") as fh:
            src = fh.read()
        for m in REF_RE.finditer(src):
            asset, ver = m.group(1), m.group(2)
            disk = os.path.join(ROOT, "static", asset)
            if not os.path.exists(disk):
                problems.append(f"{rel}: /static/{asset} referansi var ama dosya DISKTE YOK")
                continue
            if not MD5_RE.match(ver):
                skipped += 1
                continue
            with open(disk, "rb") as fh:
                real = hashlib.md5(fh.read()).hexdigest()[:8]
            checked += 1
            if ver != real:
                problems.append(
                    f"{rel}: /static/{asset}?v={ver} -> diskteki dosya {real} "
                    f"(referans BAYAT; Cloudflare eski surumu servis eder)"
                )

    off_problems, off_count = _offline_precache_problems()
    problems.extend(off_problems)

    if problems:
        print("K-J KIRIK — cache-bust hash suruklemesi:")
        for p in problems:
            print("  ✗ " + p)
        print(f"\n{len(problems)} sorun / {checked} md5 referansi denetlendi.")
        return 1
    if verbose:
        print(f"K-J PASS — {checked} md5 cache-bust referansi diskle birebir "
              f"({skipped} manuel surum etiketi kapsam disi); "
              f"/offline'in {off_count} asset'inin hepsi sw.js precache'inde.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
