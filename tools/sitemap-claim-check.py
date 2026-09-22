#!/usr/bin/env python3
"""tools/sitemap-claim-check.py -- KAPI 56 (K-CK): SITEMAP DE BIR IDDIA METNIDIR

K-CJ tarayici kanalini (robots/llms/humans/security + JSON-LD) kapatti ama
o kanalin EN COK OKUNAN dosyasini -- `/sitemap.xml` -- disarida birakti,
cunku sitemap statik bir metin degil `sitemap()` icinde URETILIYOR. Yine de
her `<url>` girdisi iki AYRI iddia tasir:

    <changefreq>  "bu sayfa ne siklikta degisir"
    <lastmod>     "en son ne zaman degisti"

Bunlar birbirini ve mimariyi DOGRULAMAK ZORUNDADIR.

K-CK'DE BULUNAN 3 IHLAL (canli sitemap uzerinde olculdu)
--------------------------------------------------------
1) **`/` -> `changefreq: hourly`** -- mimari EOD-only (K-CE kanonu:
   6 yuzey "gun ici"/"anlik" derken duzeltildi). Sayfa gunde BIR kez,
   EOD turunda tazeleniyor. Kapi 50 (`intraday-claim-check`) SABLONLARI
   tariyor, uretilen XML'i degil -- ayni yalan bu kanalda hayatta kalmisti.

2) **`/portfolio` ve `/karsilastir`: `changefreq: monthly` + `lastmod:
   bugun`** -- `lastmod` varsayilani `today` oldugu icin bu iki girdi HER
   GUN "bugun degisti" diyor, ayni satirda "ayda bir degisir" derken.
   Canli olcum (22.09): 413 URL'nin 238'i bugunun tarihini tasiyordu.
   Google guvenilmez `lastmod` tasiyan sitemap'lerde alani TUMDEN yok
   sayar -- yani celiski, gercekten gunluk degisen 217 `/hisse/*` girdisinin
   tazelik sinyalini de zehirliyordu.

3) **`/bilanco-takvimi`, `/temettu-takvimi`: `weekly` + `lastmod: bugun`**
   -- ayni celiski. Burada DOGRU taraf lastmod'du (yuk her EOD turunda
   yeniden uretiliyor), yanlis olan `weekly` idi.

KURALLAR
--------
R1  `changefreq` EOD-only mimaride `hourly`/`always` OLAMAZ.
R2  `changefreq` weekly/monthly/yearly olan bir girdi, `lastmod`'u
    ACIKCA TURETMELI (`lastmod` anahtari girdide bulunmali) -- aksi halde
    varsayilan `today`'e duser ve kendi changefreq'iyle celisir.
R3  Literal `loc` degerleri gercek bir Flask rotasina karsilik gelmeli.
R4  Ayni `loc` iki kez eklenmemeli.

ⓘ Kapi app.py'yi STATIK ayristirir (yerel Flask kosmuyor -- Python 3.9).

POZITIF KONTROL
---------------
    python3 tools/sitemap-claim-check.py --ref e7a9221   # 5 ihlal beklenir
"""
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

FORBIDDEN_FREQ = {"hourly", "always"}          # R1 -- EOD-only mimari
SLOW_FREQ = {"weekly", "monthly", "yearly"}    # R2 -- turetilmis lastmod sart


def _read(ref, relpath):
    if ref:
        return subprocess.run(["git", "show", f"{ref}:{relpath}"], cwd=ROOT,
                              capture_output=True, text=True).stdout
    return (ROOT / relpath).read_text(encoding="utf-8")


def _sitemap_src(app_src):
    m = re.search(r'@app\.route\("/sitemap\.xml"\)(.*?)\n@app\.route', app_src, re.S)
    return m.group(1) if m else ""


ENTRY = re.compile(r'\{\s*"loc"\s*:\s*(?P<loc>f?"[^"]*")(?P<rest>.*?)\}', re.S)


def main():
    argv = sys.argv[1:]
    ref = argv[argv.index("--ref") + 1] if "--ref" in argv else None
    verbose = "--verbose" in argv

    app_src = _read(ref, "app.py")
    src = _sitemap_src(app_src)
    if not src:
        print("  [R0] sitemap() govdesi bulunamadi -- kapi kor, ayristirici guncellenmeli")
        return 1

    routes = []
    for raw in re.findall(r'@app\.route\(\s*"([^"]+)"', app_src):
        routes.append(re.compile("^" + re.sub(r"<[^>]+>", "[^/]+", raw) + "$"))

    out, seen = [], {}
    n = 0
    for m in ENTRY.finditer(src):
        n += 1
        loc_raw = m.group("loc")
        rest = m.group("rest")
        is_fstring = loc_raw.startswith('f"')
        loc = loc_raw.lstrip("f").strip('"')
        freq = re.search(r'"changefreq"\s*:\s*"([^"]+)"', rest)
        freq = freq.group(1) if freq else None
        has_lastmod = '"lastmod"' in rest

        if freq in FORBIDDEN_FREQ:
            out.append(("R1", loc, f'changefreq "{freq}" -- mimari EOD-only, '
                                   f'gun-ici tazelik iddiasi (K-CE kanonu)'))
        if freq in SLOW_FREQ and not has_lastmod:
            out.append(("R2", loc, f'changefreq "{freq}" ama `lastmod` turetilmemis -- '
                                   f'varsayilan `today`e duser, her gun "bugun degisti" der'))
        if not is_fstring:
            if not any(r.match(loc) for r in routes):
                out.append(("R3", loc, "rota YOK"))
            if loc in seen:
                out.append(("R4", loc, "ayni loc iki kez ekleniyor"))
            seen[loc] = True

    if verbose:
        print(f"  tarandi: {n} sitemap girdisi, {len(routes)} rota")
    if out:
        for rule, loc, msg in out:
            print(f"  [{rule}] {loc}: {msg}")
        print(f"  TOPLAM {len(out)} ihlal")
        return 1
    print(f"KAPI 56 OK — sitemap iddialari tutarli ({n} girdi)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
