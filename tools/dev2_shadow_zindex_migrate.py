#!/usr/bin/env python3
"""FAZ8 - box-shadow elevation alt-kumesi + iki off-scale z-index'in isimlendirilmesi.

DEV2-050'nin ayirdigi "elevation" (notr siyah, modal/dropdown govdesi) alt-kumesi;
glow (renk-semantik) kumeye DOKUNULMADI. tokens.css'te zaten tanimli ama hic
tuketilmeyen --bp-shadow-sm/md/lg'ye 7 tam-esit occurrence baglanir + yeni
--bp-shadow-dropdown tokeni (3 tam-esit occurrence, z-index:500'e DOKUNULMADI,
o ayri bir tur). --bp-shadow-sm'e baglanacak tam-esit occurrence bulunamadi,
tuketilmeden birakildi.

Ayrica DEV2-050 SS2'de somutlanan gercek stacking-order riski kapatiliyor:
.sig-tip (z-index:9000) ve .premium-modal-backdrop (z-index:9998) sayisal
degerleri KORUNARAK ayni committe isimlendiriliyor (--bp-z-tooltip,
--bp-z-modal-top) - biri degisip digeri degismezse bugunku sira
(9000 < 9998, modal tooltip'in ustunde) sessizce bozulurdu.

Her replace tam 1 (ya da grep ile onceden dogrulanmis N) kez eslesmezse
script hicbir dosyaya yazmadan abort eder.
"""
import sys

TOKENS_CSS_OLD = """  --bp-shadow-sm: 0 4px 14px rgba(0, 0, 0, 0.40);
  --bp-shadow-md: 0 8px 24px rgba(0, 0, 0, 0.50);
  --bp-shadow-lg: 0 20px 60px rgba(0, 0, 0, 0.60);"""
TOKENS_CSS_NEW = """  --bp-shadow-sm: 0 4px 14px rgba(0, 0, 0, 0.40);
  --bp-shadow-md: 0 8px 24px rgba(0, 0, 0, 0.50);
  --bp-shadow-lg: 0 20px 60px rgba(0, 0, 0, 0.60);
  --bp-shadow-dropdown: 0 12px 32px rgba(0, 0, 0, 0.55);"""

ZINDEX_COMMENT_OLD = """  --bp-z-modal:    1000;
  --bp-z-toast:    9999;"""
ZINDEX_COMMENT_NEW = """  --bp-z-modal:    1000;
  --bp-z-toast:    9999;
  --bp-z-tooltip:    9000;
  --bp-z-modal-top:  9998;"""

# (path, [(old, new, expected_count), ...])
JOBS = [
    ("static/css/tokens.css", [
        (TOKENS_CSS_OLD, TOKENS_CSS_NEW, 1),
        (ZINDEX_COMMENT_OLD, ZINDEX_COMMENT_NEW, 1),
    ]),
    ("templates/ozet.html", [
        ("box-shadow: 0 20px 60px rgba(0,0,0,0.6);", "box-shadow: var(--bp-shadow-lg);", 1),
    ]),
    ("templates/sektor_harita.html", [
        ("box-shadow: 0 20px 60px rgba(0,0,0,0.6);", "box-shadow: var(--bp-shadow-lg);", 1),
    ]),
    ("templates/index.html", [
        ("box-shadow: 0 20px 60px rgba(0,0,0,0.6);", "box-shadow: var(--bp-shadow-lg);", 1),
        ("box-shadow: 0 12px 32px rgba(0,0,0,.55);", "box-shadow: var(--bp-shadow-dropdown);", 1),
        ("z-index: 9000;", "z-index: var(--bp-z-tooltip);", 1),
        ("z-index: 9998;", "z-index: var(--bp-z-modal-top);", 1),
    ]),
    ("templates/hisse.html", [
        ("box-shadow: 0 20px 60px rgba(0,0,0,0.6);", "box-shadow: var(--bp-shadow-lg);", 1),
        ("box-shadow: 0 8px 24px rgba(0,0,0,0.5);", "box-shadow: var(--bp-shadow-md);", 2),
        ("box-shadow: 0 12px 32px rgba(0,0,0,.55);", "box-shadow: var(--bp-shadow-dropdown);", 1),
    ]),
    ("templates/karsilastir.html", [
        ("box-shadow: 0 8px 24px rgba(0,0,0,.5);", "box-shadow: var(--bp-shadow-md);", 1),
    ]),
    ("templates/varlik.html", [
        ("box-shadow: 0 12px 32px rgba(0,0,0,.55);", "box-shadow: var(--bp-shadow-dropdown);", 1),
    ]),
    ("templates/_premium_modal.html", [
        ("z-index: 9998;", "z-index: var(--bp-z-modal-top);", 1),
    ]),
]


def main():
    dry_run = "--apply" not in sys.argv
    file_texts = {}
    report = []
    ok = True

    for path, replacements in JOBS:
        with open(path, encoding="utf-8") as f:
            text = f.read()
        for old, new, expected in replacements:
            n = text.count(old)
            if n != expected:
                ok = False
                report.append(f"FAIL {path}: expected {expected}x got {n}x -> {old[:60]!r}")
                continue
            text = text.replace(old, new, expected)
            report.append(f"OK   {path}: {expected}x -> {old[:60]!r}")
        file_texts[path] = text

    print("\n".join(report))
    if not ok:
        print("ABORTED - hicbir dosyaya yazilmadi")
        sys.exit(1)

    if dry_run:
        print(f"DRY-RUN - {len(file_texts)} dosya degisecekti, yazilmadi")
        return

    for path, text in file_texts.items():
        with open(path, "w", encoding="utf-8") as f:
            f.write(text)
    print(f"YAZILDI - {len(file_texts)} dosya")


if __name__ == "__main__":
    main()
