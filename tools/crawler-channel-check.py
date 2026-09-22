#!/usr/bin/env python3
"""tools/crawler-channel-check.py -- KAPI 55 (K-CJ): TARAYICI/AI-MOTOR KANALI

76/83. DERSIN BESINCI UYGULAMASI -- KANAL ENVANTERI
---------------------------------------------------
    K-CF -> blog_content.py       (67 kapinin gormedigi kor alan)
    K-CG -> app.py e-posta govdesi
    K-CH -> static/**/*.js        (tarayiciya INEN paylasilan sozluk)
    K-CI -> static/manifest.json  (isletim sistemi kabugu)
    K-CJ -> /robots.txt · /llms.txt · /humans.txt · JSON-LD  (BU DOSYA)

Bu kanalin okuyucusu insan degil MAKINE: Googlebot, GPTBot, ClaudeBot,
PerplexityBot ve JSON-LD'yi HTML govdesinden daha guvenilir sayan cevap
motorlari. Yani buradaki bir yalan, kullanici siteyi hic acmadan once
ona ulasir. 54 kapidan HICBIRI bu dort yuzeyi okumuyordu.

K-CJ'DE BULUNAN 4 IHLAL
-----------------------
1) **/robots.txt -- ADLI GRUPLAR `/admin/` KORUMASINI MIRAS ALMIYOR.**
   REP (RFC 9309 §2.2.1): bir tarayici kendisine EN OZEL eslesen TEK
   grubu uygular, diger gruplarin (`User-agent: *` dahil) kurallari onun
   icin YOK HUKMUNDEDIR. Dosyada `Disallow: /admin/` SADECE `*` grubunda
   yaziyordu; Googlebot, Bingbot, Yandex, DuckDuckBot, Slurp, GPTBot,
   ClaudeBot ve PerplexityBot kendi gruplarini eslestirdikleri icin o
   satiri hic gormuyorlardi. Yani "admin kapali" niyeti, gercekte
   adi geceni HIC KAPSAMAYAN bir kuraldi. (Manifest dersinin kardesi:
   kural VARDI, uygulandigi kume yanlisti.)

2) **/robots.txt -- `Crawl-delay: 5` OLU GRUPTAYDI.** Yorumu "Crawl-delay
   for politeness" (yani genel niyet) diyor ama satir dosyanin SONUNDA,
   `User-agent: DotBot` + `Disallow: /` grubunun icinde duruyordu.
   Gruplama satir sirasina gore yapildigi icin direktif yalnizca DotBot'a
   aitti -- ve o grup zaten tumden bloke oldugu icin direktif ISLEVSIZDI.
   86. dersin bicimsel hali: bir direktifin sertligi, BAGLI OLDUGU GRUBA
   baglidir; yer degistirince anlami degisir.

3) **/humans.txt -- "acik kaynakli metodoloji" URUNDE KARSILIGI OLMAYAN
   IDDIA.** Sitede tek bir kamuya acik depo baglantisi yok (`github`
   gecisi: yalnizca bir CSS palet YORUMU). /metodoloji kurallari
   YAYINLIYOR -- bu "seffaf"tir, "acik kaynak" DEGILDIR; ikisi farkli
   taahhutlerdir. Ayni cumledeki "Backtest ile HER ZAMAN dogrulanan"
   mutlak ifadesi de /yasal'in "backtest sonuclari gelecekteki getirileri
   garanti etmez" maddesiyle ayni kanalda celisiyordu.

4) **/humans.txt -- `Components: Lightweight Charts, Chart.js`; Chart.js
   URUNDE YOK.** `grep -rni 'chart\.js|chartjs' templates/ static/ app.py`
   (lightweight haric) -> 0 eslesme. Grafik katmani tumuyle
   lightweight-charts; Chart.js adi bir gecis artigi olarak kalmisti.

KURALLAR
--------
R1  robots.txt: tumden bloke OLMAYAN her `User-agent` grubu, REQUIRED_PRIVATE
    yollarinin hepsini kendi govdesinde tasimali (miras YOK).
R2  robots.txt: `Disallow: /` tasiyan (tumden bloke) bir grupta Disallow
    disinda direktif olmamali -- islevsizdir, niyet yanlis gruba yazilmistir.
R3  Tarayici kanallarinda "acik kaynak" iddiasi, agacta kamuya acik bir
    depo URL'si (github.com/gitlab.com/...) YOKSA yasak.
R4  humans.txt `Components:` kalemlerinin her biri frontend'de gercekten
    kullanilmali (kullanim TURU dogrulanir -- 87. ders: salt ad gecisi
    yetmez, dosya/istek olarak gorunmeli).
R5  llms.txt + sablon JSON-LD icindeki her literal https://borsapusula.com/<yol>
    gercek bir Flask rotasina karsilik gelmeli (K-CI'nin `?filter=al`
    sinifinin genellestirilmis hali).

POZITIF KONTROL
---------------
    python3 tools/crawler-channel-check.py --ref bdc6013   # 4 ihlal beklenir
"""
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# R1: adli her allow-grubunda bulunmasi ZORUNLU gizli yollar.
REQUIRED_PRIVATE = ["/admin/"]

# R3: "acik kaynak" ailesinin yazimlari (tr_fold ile taranir).
# 84. DERS: `tr_fold` yalniz i/I ailesini katlar (ç/ğ/ö/ş/ü KALIR) -- bu yuzden
# desen es-yazimlari ACIKCA kapsar. Ilk yazimi "acik kaynak" idi ve gercek
# ihlali ("açık kaynaklı") KACIRDI; pozitif kontrol olmasa kapi bos "OK" derdi.
OPEN_SOURCE_PAT = re.compile(r"a[c\u00e7][i\u0131]k kayna|open[ -]?source|opensource")
REPO_URL_PAT = re.compile(r"https?://(www\.)?(github|gitlab|bitbucket|codeberg|sourcehut|sr\.ht)\.")

# R4: bileseni "gercekten kullaniliyor" sayacak kanit desenleri (kullanim TURU).
COMPONENT_EVIDENCE = {
    "lightweight charts": re.compile(r"lightweight-charts|LightweightCharts"),
    "chart.js":           re.compile(r"chart\.js|chartjs|new\s+Chart\s*\("),
}

sys.path.insert(0, str(ROOT / "tools"))
try:
    from _tr import tr_fold  # kanon: tek yazim-katlama yardimcisi (84. ders)
except Exception:  # pragma: no cover
    def tr_fold(s):
        return s.lower()


def _read(ref, relpath):
    if ref:
        return subprocess.run(["git", "show", f"{ref}:{relpath}"], cwd=ROOT,
                              capture_output=True, text=True).stdout
    p = ROOT / relpath
    return p.read_text(encoding="utf-8") if p.exists() else ""


def _extract_body(app_src, funcname):
    """app.py icindeki bir route fonksiyonunun `body = \"\"\"...\"\"\"` blogu."""
    m = re.search(r"def %s\(\):(.*?)\n    return Response" % re.escape(funcname),
                  app_src, re.S)
    if not m:
        return ""
    seg = m.group(1)
    q = re.search(r'body\s*=\s*f?"""(.*?)"""', seg, re.S)
    return q.group(1) if q else ""


def _routes(app_src):
    """Flask rota desenleri -> regex (dinamik segmentler joker)."""
    pats = []
    for raw in re.findall(r'@app\.route\(\s*"([^"]+)"', app_src):
        pats.append(re.compile("^" + re.sub(r"<[^>]+>", "[^/]+",
                                            re.escape(raw).replace(r"\<", "<").replace(r"\>", ">"))
                               .replace("<[^/]+>", "[^/]+") + "$"))
    return pats


# ---------------------------------------------------------------- robots.txt
def _parse_groups(body):
    """robots.txt'yi satir sirasina gore gruplara boler (REP §2.2.1)."""
    groups, cur = [], None
    for ln in body.splitlines():
        s = ln.split("#", 1)[0].strip()
        if not s or ":" not in s:
            continue
        key, val = (x.strip() for x in s.split(":", 1))
        k = key.lower()
        if k == "user-agent":
            if cur and cur["rules"]:
                groups.append(cur)
                cur = None
            if cur is None:
                cur = {"agents": [], "rules": []}
            cur["agents"].append(val)
        elif k in ("sitemap", "host"):
            continue  # gruba ait DEGIL
        elif cur is not None:
            cur["rules"].append((k, val))
    if cur and cur["rules"]:
        groups.append(cur)
    return groups


def check_robots(body, out):
    for g in _parse_groups(body):
        agents = ", ".join(g["agents"])
        blocked = any(k == "disallow" and v == "/" for k, v in g["rules"])
        if blocked:
            extra = [k for k, _ in g["rules"] if k != "disallow"]
            for k in sorted(set(extra)):
                out.append(("R2", "robots.txt",
                            f"`{k}` direktifi tumden bloke grupta ({agents}) -- islevsiz; "
                            f"niyet baska gruba yazilmali"))
            continue
        if "*" in g["agents"]:
            continue  # `*` grubu zaten referans grup
        have = {v for k, v in g["rules"] if k == "disallow"}
        for need in REQUIRED_PRIVATE:
            if need not in have:
                out.append(("R1", "robots.txt",
                            f"`{agents}` grubu `Disallow: {need}` tasimiyor -- REP'te "
                            f"`User-agent: *` MIRAS ALINMAZ, bu tarayici icin admin ACIK"))


# ---------------------------------------------------------------- humans.txt
def check_humans(body, tree_text, out):
    for ln in body.splitlines():
        if ln.strip().lower().startswith("components:"):
            for item in ln.split(":", 1)[1].split(","):
                name = item.strip()
                if not name:
                    continue
                pat = COMPONENT_EVIDENCE.get(tr_fold(name))
                if pat is None:
                    out.append(("R4", "humans.txt",
                                f"`Components: {name}` -- kapida kanit deseni tanimli degil; "
                                f"COMPONENT_EVIDENCE'a ekle (bilerek muafsa acikca beyan et)"))
                elif not pat.search(tree_text):
                    out.append(("R4", "humans.txt",
                                f"`Components: {name}` URUNDE YOK -- frontend'de tek kullanim "
                                f"kaniti bulunamadi"))


def check_open_source(name, body, repo_url_exists, out):
    if repo_url_exists:
        return
    for i, ln in enumerate(body.splitlines(), 1):
        if OPEN_SOURCE_PAT.search(tr_fold(ln)):
            out.append(("R3", name,
                        f"satir {i}: \"acik kaynak\" iddiasi -- agacta kamuya acik depo "
                        f"URL'si yok; /metodoloji SEFFAFTIR, acik kaynak degildir"))


# ------------------------------------------------------------------ R5: URL
URL_PAT = re.compile(r"https://borsapusula\.com(/[^\s\"'\)\]}<>,]*)")


def check_urls(name, text, routes, out):
    for raw in set(URL_PAT.findall(text)):
        path = raw.split("?", 1)[0].split("#", 1)[0].rstrip("/") or "/"
        if "{" in path or "%" in path:
            continue  # Jinja/encode -- literal degil
        if path.startswith("/static/"):
            # Flask'in kendi static handler'i sunar -- rota tablosunda gorunmez.
            # 87. ders: varligi ADIN gecisiyle degil DOSYANIN kendisiyle dogrula.
            if not (ROOT / path.lstrip("/")).exists():
                out.append(("R5", name, f"`{raw}` -> `static/` altinda DOSYA YOK"))
            continue
        if not any(r.match(path) for r in routes):
            out.append(("R5", name, f"`{raw}` -> `{path}` rotasi YOK"))


def main():
    ref = None
    argv = sys.argv[1:]
    if "--ref" in argv:
        ref = argv[argv.index("--ref") + 1]
    verbose = "--verbose" in argv

    app_src = _read(ref, "app.py")
    robots = _extract_body(app_src, "robots")
    llms = _extract_body(app_src, "llms_txt")
    humans = _extract_body(app_src, "humans_txt")
    sec = _extract_body(app_src, "security_txt")
    routes = _routes(app_src)

    tree_text = "\n".join(
        _read(ref, str(p.relative_to(ROOT)))
        for p in sorted(list((ROOT / "templates").glob("*.html")) +
                        list((ROOT / "static").glob("*.js")))
        if "lightweight-charts.min" not in p.name
    ) + app_src

    repo_url_exists = bool(REPO_URL_PAT.search(tree_text))

    jsonld = []
    for p in sorted((ROOT / "templates").glob("*.html")):
        src = _read(ref, str(p.relative_to(ROOT)))
        for m in re.finditer(r"<script[^>]*application/ld\+json[^>]*>(.*?)</script>", src, re.S):
            jsonld.append((p.name, m.group(1)))

    out = []
    check_robots(robots, out)
    check_humans(humans, tree_text, out)
    for nm, body in (("llms.txt", llms), ("humans.txt", humans),
                     ("robots.txt", robots), ("security.txt", sec)):
        check_open_source(nm, body, repo_url_exists, out)
        check_urls(nm, body, routes, out)
    for fname, block in jsonld:
        check_urls(f"JSON-LD {fname}", block, routes, out)

    if verbose:
        print(f"  tarandi: robots({len(robots.splitlines())} satir) "
              f"llms({len(llms.splitlines())}) humans({len(humans.splitlines())}) "
              f"security({len(sec.splitlines())}) JSON-LD({len(jsonld)} blok) "
              f"rota({len(routes)})")
    if out:
        for rule, where, msg in out:
            print(f"  [{rule}] {where}: {msg}")
        print(f"  TOPLAM {len(out)} ihlal")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
