#!/usr/bin/env python3
"""C-26 — sw.js precache listesi + surumu ve manifest.json ikon hash'leri OTOMATIK.

Sablonlar artik `?v=` yazmaz: her asset `{{ static_v('<yol>') }}` ile istenir
(D-19, app.py; md5[:8] icerik ozeti). Elle hash tasiyan yalniz iki statik dosya
kaldi ve ikisini de bu arac uretir:

  static/manifest.json  ikon `src`'leri -> diskteki md5[:8]
  static/sw.js          `const STATIC = [...]` = /offline sayfasinin istedigi her
                        /static/ URL'i (sablon static_v ile render edilir, yani
                        tarayicinin soracagi anahtarin AYNISI) + CORE listesi;
                        `const CACHE` = listenin ozeti -> liste degisince surum
                        kendiliginden degisir, elle "SW bump" yok.

Kullanim:
  python3 tools/sw_manifest.py          # dosyalari yeniden yazar (pre-deploy 11. adim)
  python3 tools/sw_manifest.py --check  # yazmaz; fark varsa ya da sablonda elle
                                        # `?v=` varsa 1 doner
"""
import hashlib
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STATIC_DIR = os.path.join(ROOT, "static")
SW = os.path.join(STATIC_DIR, "sw.js")
MANIFEST = os.path.join(STATIC_DIR, "manifest.json")

# /offline'in istemedigi ama cevrimdisi da lazim olanlar (offline render'ina eklenir).
CORE = [
    "lightweight-charts.min.js",
    "manifest.json",
    "icon-192.png",
    "icon-512.png",
    "css/shared.css",
]

ICON_RE = re.compile(r'"/static/(icon-\d+\.png)(?:\?v=[0-9A-Za-z]+)?"')
STATIC_RE = re.compile(r"const STATIC = \[.*?\];", re.S)
CACHE_RE = re.compile(r"const CACHE = '[^']*';")
MANUAL_V_RE = re.compile(r"/static/[A-Za-z0-9_\-./]+\?v=")


def _md5(rel):
    with open(os.path.join(STATIC_DIR, rel), "rb") as fh:
        return hashlib.md5(fh.read()).hexdigest()[:8]


def static_v(path):
    """app.static_v ile ayni cikti (app import edilmeden)."""
    path = str(path or "").lstrip("/")
    if path.startswith("static/"):
        path = path[len("static/"):]
    full = os.path.join(STATIC_DIR, path)
    if os.path.isfile(full):
        return "/static/" + path + "?v=" + _md5(path)
    return "/static/" + path


def _offline_urls():
    from jinja2 import Environment, FileSystemLoader
    env = Environment(loader=FileSystemLoader(os.path.join(ROOT, "templates")), autoescape=True)
    env.globals["static_v"] = static_v
    html = env.get_template("offline.html").render()
    return sorted(set(re.findall(r'/static/[^"\'\s>)]+', html)))


def build_manifest(src):
    return ICON_RE.sub(lambda m: '"%s"' % static_v(m.group(1)), src)


def build_sw(src):
    urls = sorted(set(_offline_urls()) | {static_v(p) for p in CORE})
    urls.append("/offline")
    body = "const STATIC = [\n" + "".join("  '%s',\n" % u for u in urls) + "];"
    ver = hashlib.md5("\n".join(urls).encode()).hexdigest()[:8]
    src = STATIC_RE.sub(lambda _m: body, src, count=1)
    return CACHE_RE.sub("const CACHE = 'borsapusula-%s';" % ver, src, count=1)


def _manual_v_in_templates():
    out = []
    tdir = os.path.join(ROOT, "templates")
    for dp, _dn, fns in os.walk(tdir):
        for fn in fns:
            if fn.endswith(".html"):
                p = os.path.join(dp, fn)
                with open(p, encoding="utf-8") as fh:
                    for i, line in enumerate(fh, 1):
                        if MANUAL_V_RE.search(line):
                            out.append("%s:%d" % (os.path.relpath(p, ROOT), i))
    return out


def main():
    check = "--check" in sys.argv
    changed = []
    # manifest once: sw.js listesi manifest.json'in YENI md5'ini tasimali.
    for path, build in ((MANIFEST, build_manifest), (SW, build_sw)):
        with open(path, encoding="utf-8") as fh:
            old = fh.read()
        new = build(old)
        if new != old:
            changed.append(os.path.relpath(path, ROOT))
            if not check:
                with open(path, "w", encoding="utf-8") as fh:
                    fh.write(new)
    manual = _manual_v_in_templates()
    for loc in manual:
        print("  ✗ %s: elle `?v=` -> {{ static_v('<yol>') }} kullan" % loc)
    if check:
        for c in changed:
            print("  ✗ %s bayat -> python3 tools/sw_manifest.py" % c)
        return 1 if (changed or manual) else 0
    for c in changed:
        print("  ↻ %s yeniden uretildi (commit'e dahil et)" % c)
    return 1 if manual else 0


if __name__ == "__main__":
    sys.exit(main())
