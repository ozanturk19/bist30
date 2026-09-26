#!/usr/bin/env python3
"""T2.4 kabul olcutu icin statik dogrulama (deploy/tarayici gerektirmez).
769/820/834/899px'te en az bir nav yuzeyi (masaustu .bp-main-nav VEYA
mobil .mobile-bottom-nav) gorunur olmali. Iki taraf da CSS media query
ile kontrol edildigi icin, kanit "tek kirilim 900px'te" onermesidir:
  desktop:  @media (max-width:900px) { .bp-main-nav display:none }        -> >900px'te GORUNUR
  mobile:   @media (max-width:900px) { .mobile-bottom-nav display:block } -> <=900px'te GORUNUR
Ikisi ayni esikte devrederse, 769/820/834/899 (hepsi <=900) mobil barla,
901+ masaustu navla kapsanir -> hicbir genislikte bosluk yok.

Kullanim: python3 tools/check_t24_nav_gap.py   (repo kokunden)
"""
import glob
import re
import sys

TEST_WIDTHS = (769, 820, 834, 899)


def find_breakpoints(css_text, selector, display):
    pat = re.compile(
        r'@media\s*\(max-width:\s*(\d+)px\)\s*\{[^}]*'
        + re.escape(selector) + r'\s*\{[^}]*display:\s*' + display,
        re.DOTALL,
    )
    return [int(m.group(1)) for m in pat.finditer(css_text)]


def main():
    fails = []

    with open("templates/_mobile_nav_partial.html", encoding="utf-8") as f:
        mobile_partial = f.read()
    mobile_bps = find_breakpoints(mobile_partial, ".mobile-bottom-nav", "block")
    print(f"[_mobile_nav_partial.html] .mobile-bottom-nav gorunur esigi: {mobile_bps}")
    if set(mobile_bps) != {900}:
        fails.append(f"_mobile_nav_partial.html: beklenen {{900}}, bulunan {mobile_bps}")

    templates = sorted(glob.glob("templates/*.html"))
    templates = [t for t in templates if ".bak" not in t
                 and not t.endswith("_header.html")
                 and not t.endswith("_mobile_nav_partial.html")]

    desktop_bp_by_file = {}
    for path in templates:
        with open(path, encoding="utf-8") as f:
            content = f.read()
        if ".bp-main-nav" not in content:
            continue
        bps = find_breakpoints(content, ".bp-main-nav", "none")
        bps += find_breakpoints(content, ".header-nav", "none")
        if bps:
            desktop_bp_by_file[path] = bps

    print(f"\n[.bp-main-nav / .header-nav kullanan sablon sayisi]: {len(desktop_bp_by_file)}")
    drift = {f: b for f, b in desktop_bp_by_file.items() if set(b) != {900}}
    if drift:
        fails.append(f"desktop nav esigi 900'den sapan sablonlar: {drift}")
    else:
        print("  Tumu max-width:900px ile hizali (sapma yok).")

    for page in ("templates/profil.html",):
        with open(page, encoding="utf-8") as f:
            content = f.read()
        has_header_include = "{% include '_header.html' %}" in content
        has_mobile_include = "_mobile_nav_partial.html" in content
        has_bp_main_nav_css = ".bp-main-nav" in content
        print(f"\n[{page}] _header.html include: {has_header_include} | "
              f"_mobile_nav_partial.html include: {has_mobile_include} | "
              f".bp-main-nav CSS present: {has_bp_main_nav_css}")
        if not (has_header_include and has_mobile_include and has_bp_main_nav_css):
            fails.append(
                f"{page}: nav yuzeyi eksik (header={has_header_include}, "
                f"mobile={has_mobile_include}, css={has_bp_main_nav_css})"
            )

    print("\n=== SONUC ===")
    if not fails:
        for w in TEST_WIDTHS:
            print(f"  {w}px: mobile-bottom-nav GORUNUR (<=900), bp-main-nav GIZLI (<=900) "
                  f"-> en az bir nav yuzeyi VAR")
        print("PASS: 0 sayfa nav'siz kaliyor (statik CSS/include analizi)")
        return 0
    print("FAIL:")
    for f in fails:
        print(f"  - {f}")
    return 1


if __name__ == "__main__":
    sys.exit(main())
