#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
KAPI 72 — K-DB (22.09): PYTHON KANALINDAKI HER HAM HEX KANONA BAGLI OLMALI.

`js-palette-check.py`in Python esdegeri: repo kokundeki *.py dosyalarinda
gecen her `#rrggbb` (ve `#rrggbbaa`) tokens.css'teki bir token degeri olmali.

NEDEN BU KAPI VAR
-----------------
22.09'a kadar UC palet kapisinin UCU de app.py'yi hic gormuyordu:
  * `style-guard.py`            -> yalniz `static/css/*.css`
  * `js-palette-check.py`       -> yalniz JS
  * `template-color-channel-check.py` / `canon-css-dup-check.py` -> sablon/CSS
Oysa app.py urunun EN KAMUSAL gorselini uretiyor: `/og-image.png` --
21 sablonun og:image'i (CPO-1767) ve `static/manifest.json`in
`screenshots[form_factor=wide]` girdisi, yani Chrome PWA kurulum istemi.

K-DB canli olcumu (22.09, 1200x630 PNG piksel sayimi): 12 ayri renk, 11'i
kanon disi. Kart bastan asagi GitHub koyu temasinin paletiyle boyaniyordu
(#0d1117 / #161b22 / #58a6ff / #f0f6fc / #8b949e / #30363d / #3fb950 ...).
Tek esleseni `#f85149` (SAT) idi -> ayni gorselde yon cifti ASIMETRIKTI.

TOKENS.CSS YORUM TUZAGI (bu kapinin en kritik ayrintisi)
--------------------------------------------------------
Kanon kumesi `tokens.css`ten okunur ama **CSS yorumlari ONCE SOYULUR**.
Olculdu: yorumlu okumada 35, yorumsuzda 28 hex var -- 7 renk YALNIZ
yorumlarda geciyor (`#161618`, `#1c1c1f`, `#8b949e`, `#00e6a0`, `#3d0f0f`,
`#1e293b`, `#1fe0ff`). Bunlar cogunlukla "bu renk kanon DEGIL" diye
yazilmis notlar. Yorumlar soyulmasa `#8b949e` (og kartinin GitHub grisi)
KANON sayilir ve kapi ihlali gormezdi -- kapi kendi belgelendirmesiyle
korlesirdi. Bkz. [[reference_tokens_css_yorum_ayristirici_tuzagi]].

app.py tarafinda ise **Python yorumlari** soyulur (tokenize ile, cunku
`"#0e0e12"` bir STRING icinde gecer ve naif `#`-kirpma onu yer). Renk
kararlarinin GEREKCESI yorumlarda eski/kanon-disi hex'leri ANMAK
zorundadir; kapi gerekcenin YAZIMINI degil, kodun KENDISINI olcer.

MUAFIYET
--------
`tools/app_hex_exempt.json` -> e-posta govdesi (CPO-1782, DEV1 alani).
Dondurulmus liste, SADECE KUCULEBILIR: listede olup app.py'de artik
gecmeyen bir hex de FAIL uretir (ratchet asagi).

EK KONTROL
----------
`_OG_PALETTE`in her girdisi satir-sonu yorumunda bir `--bp-*` token adi
tasir; kapi o token'in tokens.css'teki DEGERIYLE birebir esit oldugunu
dogrular. Boylece palet tablosu tokens.css'ten sessizce ayrisamaz.

Kullanim:
  python3 tools/py-palette-check.py
  python3 tools/py-palette-check.py --ref SHA     # pozitif kontrol
  python3 tools/py-palette-check.py --self-test
"""
import io, json, os, re, subprocess, sys, tokenize

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HEX = re.compile(r"#([0-9a-fA-F]{6})(?:[0-9a-fA-F]{2})?\b")  # #rrggbb ve #rrggbbaa
# Taranan kanal: repo kokundeki her Python dosyasi (app.py + notify_health.py + ...).
# `tools/` ve `static/` disarida: kapilarin KENDI ornek/self-test hex'leri kanon degildir.
PY_GLOB = "*.py"


def canon_values(css_text):
    """tokens.css -> kanonik hex kumesi. CSS YORUMLARI SOYULUR (bkz. modul docstring)."""
    body = re.sub(r"/\*.*?\*/", "", css_text, flags=re.S)
    return {("#" + h).lower() for h in HEX.findall(body)}


def canon_map(css_text):
    """--bp-token -> deger (yorumsuz govdeden)."""
    body = re.sub(r"/\*.*?\*/", "", css_text, flags=re.S)
    return {m.group(1): m.group(2).lower()
            for m in re.finditer(r"(--bp-[a-z0-9-]+)\s*:\s*(#[0-9a-fA-F]{6})\b", body)}


def strip_py_comments(src):
    """Python yorumlarini soy, SATIR NUMARALARINI KORU (35. ders)."""
    lines = src.splitlines()
    out = list(lines)
    try:
        for tok in tokenize.generate_tokens(io.StringIO(src).readline):
            if tok.type != tokenize.COMMENT:
                continue
            r, c = tok.start[0] - 1, tok.start[1]
            if 0 <= r < len(out):
                out[r] = out[r][:c] + " " * len(out[r][c:])
    except (tokenize.TokenError, IndentationError, SyntaxError):
        pass
    return out


def check(app_src, css_text, exempt, collect=None):
    canon = canon_values(css_text)
    cmap = canon_map(css_text)
    lines = strip_py_comments(app_src)
    viol, seen = [], collect if collect is not None else set()
    for i, line in enumerate(lines, 1):
        for h in HEX.findall(line):
            hl = ("#" + h).lower()
            if hl in canon or hl in exempt:
                seen.add(hl)
                continue
            viol.append((i, hl, line.strip()[:110]))
    stale = sorted(e for e in exempt if e not in seen)

    # _OG_PALETTE <-> tokens.css capraz kontrolu (ham kaynakta, yorumlar GEREKLI)
    drift = []
    m = re.search(r"_OG_PALETTE\s*=\s*\{(.*?)\n\}", app_src, re.S)
    if not m:
        drift.append(("_OG_PALETTE", "tablo bulunamadi"))
    else:
        for row in m.group(1).splitlines():
            rm = re.search(r'"([a-z0-9_]+)"\s*:\s*"(#[0-9a-fA-F]{6})"\s*,?\s*#\s*(--bp-[a-z0-9-]+)', row)
            if not rm:
                if row.strip() and not row.strip().startswith("#"):
                    drift.append((row.strip()[:60], "token adi yorumda YOK"))
                continue
            key, val, tok = rm.group(1), rm.group(2).lower(), rm.group(3)
            if tok not in cmap:
                drift.append((key, f"{tok} tokens.css'te yok"))
            elif cmap[tok] != val:
                drift.append((key, f"{tok}={cmap[tok]} ama tabloda {val}"))
    return viol, stale, drift


def py_files(ref=None):
    """Taranacak Python dosyalari (repo koku). `--ref` modunda o commit'in agaci."""
    if ref is None:
        import glob
        return sorted(os.path.basename(f) for f in glob.glob(os.path.join(ROOT, PY_GLOB)))
    out = subprocess.check_output(["git", "-C", ROOT, "ls-tree", "--name-only", ref]).decode()
    return sorted(n for n in out.split() if n.endswith(".py"))


def read(path, ref=None):
    if ref is None:
        return open(os.path.join(ROOT, path), encoding="utf-8").read()
    return subprocess.check_output(["git", "-C", ROOT, "show", f"{ref}:{path}"]).decode("utf-8")


def main():
    args = sys.argv[1:]
    if "--self-test" in args:
        return self_test()
    ref = None
    if "--ref" in args:
        ref = args[args.index("--ref") + 1]
    css = read("static/css/tokens.css", ref)
    exempt = set(json.load(open(os.path.join(ROOT, "tools/app_hex_exempt.json"),
                                encoding="utf-8"))["hexes"])
    viol, seen_all, drift = [], set(), []
    for name in py_files(ref):
        src = read(name, ref)
        v, _st, d = check(src, css, exempt, collect=seen_all)
        viol += [(name, ln, h, t) for ln, h, t in v]
        if name == "app.py":
            drift += d
    stale = sorted(e for e in exempt if e not in seen_all)
    for name, ln, h, txt in viol:
        print(f"  {name}:{ln}  {h}  KANON DISI  | {txt}")
    for h in stale:
        print(f"  MUAFIYET BAYAT: {h} app.py'de artik gecmiyor -> tools/app_hex_exempt.json'dan SIL")
    for k, why in drift:
        print(f"  _OG_PALETTE['{k}'] {why}")
    n = len(viol) + len(stale) + len(drift)
    print(f"{'FAIL' if n else 'OK'} py-palette-check: {len(viol)} kanon disi hex, "
          f"{len(stale)} bayat muafiyet, {len(drift)} palet-token sapmasi"
          f"{' (ref ' + ref + ')' if ref else ''}")
    return 1 if n else 0


def self_test():
    css = open(os.path.join(ROOT, "static/css/tokens.css"), encoding="utf-8").read()
    ok = True
    cases = [
        ('img = Image.new("RGB", (1,1), "#0d1117")', set(), 1, "kanon disi hex yakalanmali"),
        ('img = Image.new("RGB", (1,1), "#0e0e12")', set(), 0, "kanon hex temiz gecmeli"),
        ('x = 1  # eski renk #3fb950 idi', set(), 0, "YORUMDAKI hex kapiyi tetiklememeli"),
        ('body = "#8b949e"', set(), 1, "YALNIZ tokens.css YORUMUNDA gecen renk kanon SAYILMAMALI"),
        ('body = "#161618"', {"#161618"}, 0, "muafiyet listesi calismali"),
        ('body = "#0e0e12"', {"#161618"}, 1, "BAYAT muafiyet FAIL vermeli"),
        ('body = "#1f6feb44"', set(), 1, "8 HANELI (#rrggbbaa) kanon disi yakalanmali"),
        ('body = "#00e29033"', set(), 0, "8 HANELI kanon rgb'li alfa varyanti gecmeli"),
    ]
    for src, ex, want, why in cases:
        v, st, _ = check(src + "\n", css, ex)
        got = len(v) + len(st)
        flag = "OK " if got == want else "FAIL"
        if got != want:
            ok = False
        print(f"  {flag} ({got}/{want}) {why}")
    print(("OK" if ok else "FAIL") + " self-test")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
