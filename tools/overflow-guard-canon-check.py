#!/usr/bin/env python3
"""KAPI 84 — yatay-tasma guard'i TEK KANON mu? (K-DR / CPO-1791, 22.09.2026)

NEDEN BU KAPI VAR
  22.09'da olculdu: ayni is (belgenin yatay kaymasini kesmek) 15 sayfa
  CSS'inde UC FARKLI YAZIMLA duruyordu, 8 sayfada ise hic yoktu. Uc yazim
  ayni seyi YAPMIYOR -- 320px'te canli pozitif kontrol (`right:-60px` oge
  enjekte + `window.scrollTo(300,0)`):

      html,body{overflow-x:clip}   -> scrollX 0   guard TUTUYOR
      body{overflow-x:hidden}      -> scrollX 60  guard ETKISIZ (5 sayfa)
      html{overflow-x:hidden}      -> scrollX 60  guard ETKISIZ (3 sayfa)

  Yani "guard'li" 15 sayfanin 8'inde guard yalnizca YAZIYORDU. `hidden` bir
  kaydirma kabi kurar (tekerlegi keser, programatik kaydirmayi kesmez) ve
  diger ekseni `auto`ya zorlayarak icerideki `position:sticky` cocuklari
  kirar; `clip` kaydirma kabi KURMAZ.

OLCUT (taban SIFIR)
  1) shared.css TAM OLARAK BIR kanonik bildirim tasir:
     `html, body { overflow-x: clip; }`  (secici sirasi serbest, deger clip)
  2) Baska HICBIR CSS dosyasi ve hicbir sablon <style> blogu `html` ya da
     `body` seciciyle `overflow-x` YAZMAZ -- ne clip ne hidden ne auto.
     (Kap/oge duzeyindeki `overflow-x` serbest; kapi yalniz KOK seciciye
     bakar.)
  3) Kanonik bildirimin degeri `hidden` OLAMAZ.

NE OLCMEZ
  Bu kapi guard'in VARLIGINI olcer, icerigin kirpilip kirpilmadigini DEGIL.
  O olcum KAPI 83'undur (`tools/clipped-content-check.mjs`, gunluk harness).
  Ikisi birlikte anlamlidir: guard belge kaymasini keser, kapi 83 "kirpildi
  ama ulasilamiyor"u arar. Guard eklemek kapi 83'u BORCLANDIRIR (179. ders).
"""
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CANON_FILE = ROOT / "static" / "css" / "shared.css"

BLOCK_COMMENT = re.compile(r"/\*.*?\*/", re.S)
JINJA_COMMENT = re.compile(r"\{#.*?#\}", re.S)
STYLE_BLOCK = re.compile(r"<style[^>]*>(.*?)</style>", re.S | re.I)
# "html {", "body {", "html, body {", "html,body{" ... -- yalniz KOK secici
ROOT_RULE = re.compile(
    r"(?<![\w.#\-\[])((?:html|body)(?:\s*,\s*(?:html|body))*)\s*\{([^{}]*)\}", re.I
)
OVERFLOW_X = re.compile(r"(?<![\w-])overflow(?:-x)?\s*:\s*([a-z-]+)", re.I)


def strip_comments(text: str) -> str:
    return JINJA_COMMENT.sub(" ", BLOCK_COMMENT.sub(" ", text))


def root_overflow_decls(css: str):
    """(secici, deger, ham) -- kok seciciye yazilmis her overflow/overflow-x."""
    out = []
    for m in ROOT_RULE.finditer(css):
        sel, body = m.group(1), m.group(2)
        for d in OVERFLOW_X.finditer(body):
            out.append((re.sub(r"\s+", "", sel).lower(), d.group(1).lower(), m.group(0)))
    return out


def main() -> int:
    violations = []

    # --- 1/3: kanonik bildirim ---
    canon_css = strip_comments(CANON_FILE.read_text(encoding="utf-8"))
    canon = root_overflow_decls(canon_css)
    if len(canon) != 1:
        violations.append(
            f"shared.css: kanonik kok-guard sayisi {len(canon)} (beklenen 1) -> {canon}"
        )
    else:
        sel, val, _ = canon[0]
        if sorted(sel.split(",")) != ["body", "html"]:
            violations.append(
                f"shared.css: kanon secicisi '{sel}' -- `html, body` olmali "
                "(yalniz body ETKISIZ, olculdu: scrollX 60)"
            )
        if val != "clip":
            violations.append(
                f"shared.css: kanon degeri '{val}' -- `clip` olmali "
                "(`hidden` kaydirma kabi kurar, sticky'yi kirar, programatik "
                "kaydirmayi kesmez)"
            )

    # --- 2/3: baska hicbir CSS dosyasi kok-guard yazmaz ---
    for css_file in sorted((ROOT / "static" / "css").rglob("*.css")):
        if css_file == CANON_FILE:
            continue
        for sel, val, raw in root_overflow_decls(
            strip_comments(css_file.read_text(encoding="utf-8"))
        ):
            violations.append(
                f"{css_file.relative_to(ROOT)}: kok seciciye guard yazilmis "
                f"-> `{sel}{{overflow-x:{val}}}` ({raw.strip()[:60]}...) "
                "-- kanon shared.css'te"
            )

    # --- 3/3: sablon <style> bloklari + SAF CSS parcallari ---
    # Dikkat: sitenin kritik CSS'i `_bp_critical_css.html` icinde HAM CSS olarak
    # duruyor ve kendi <style> etiketi YOK (sayfa onu `<style id=...>` icine
    # include ediyor). Yalniz <style> blogu arayan bir tarama bu dosyaya
    # YAPISAL OLARAK kordur -- bu yuzden HTML etiketi hic icermeyen sablonlar
    # butunuyle CSS sayilir.
    for tpl in sorted((ROOT / "templates").glob("*.html")):
        text = tpl.read_text(encoding="utf-8")
        stripped = strip_comments(text)
        blocks = STYLE_BLOCK.findall(stripped)
        if not re.search(r"<[a-zA-Z]", stripped):
            blocks = [stripped]  # saf CSS parcasi
        for block in blocks:
            for sel, val, raw in root_overflow_decls(block):
                violations.append(
                    f"{tpl.relative_to(ROOT)}: sablon-ici kok guard "
                    f"-> `{sel}{{overflow-x:{val}}}` -- kanon shared.css'te"
                )

    if violations:
        print("KAPI 84 (yatay-tasma guard kanonu): FAIL")
        for v in violations:
            print("  -", v)
        return 1
    print("KAPI 84 (yatay-tasma guard kanonu): PASS — tek kanon shared.css")
    return 0


if __name__ == "__main__":
    sys.exit(main())
