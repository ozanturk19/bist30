#!/usr/bin/env python3
"""
T1.5a-2 — rgba ikizleri: rgba(<kanonik uclu>, a) -> rgba(var(--bp-*-rgb), a)

NEDEN KANAL TOKEN'I, per-alfa token DEGIL:
  olculdu -- --bp-al icin 49 AYRIK alfa basamagi var (.03 .04 .05 ... .92).
  Her alfa icin token uretmek 150+ token demek; okunmaz ve bakimsiz.
  Kanal token'i (`--bp-al-rgb: 0, 226, 144`) tek kaynagi korur ve alfa
  cagri yerinde kalir.

NEDEN color-mix() DEGIL:
  `color-mix(in srgb, var(--bp-al) 18%, transparent)` ayni sonucu verir AMA
  desteklemeyen tarayicida bildirim TAMAMEN dusertir -> renk sessizce
  kaybolur. Bu tam olarak 08.08 sabahi iki kez yasadigimiz sinif.
  `rgba(var(--x-rgb), .18)` ise var() calisan HER yerde calisir; ek bir
  ozellik destegi istemez. Muhafazakar secim bilincli.

YAPISAL KAPI: t15a_apply.py ile AYNI kural -- rgba yalnizca gercek bir CSS
bildirim degeri konumundaysa degistirilir; iki nokta ile rgba arasinda tirnak
veya = varsa (JS secenek nesnesi, canvas atamasi) DOKUNULMAZ.
Ayrica T1.5a-1'de ajan denetiminin disladigi satirlar burada da dislanir.
"""
import json
import re
import sys
from pathlib import Path

# kanonik hex -> (token adi, RGB uclusu)
CANON = {
    "#0e0e12": "bg", "#141416": "surface", "#1c1b1f": "surface2", "#201f21": "surface3",
    "#2a2a2c": "border", "#46464d": "border2", "#e5e1e4": "text", "#c7c5cd": "text2",
    "#909097": "text3", "#b8c3ff": "brand", "#00e290": "al", "#f85149": "sat",
    "#3d0f0f": "sat-bg", "#da3633": "sat-bd", "#f59e0b": "gold", "#ffc850": "volume",
    "#a855f7": "premium",
}


def rgb(h):
    return (int(h[1:3], 16), int(h[3:5], 16), int(h[5:7], 16))


TRIPLE = {rgb(h): t for h, t in CANON.items()}

RGBA_RE = re.compile(r"rgba?\(\s*(\d{1,3})\s*,\s*(\d{1,3})\s*,\s*(\d{1,3})\s*,([^()]*?)\)")
CSS_DECL_RE = re.compile(r"(?:^|[^A-Za-z0-9_-])[a-z][a-z-]*\s*:\s*[^;{}\"'=]*$")


def main():
    if len(sys.argv) < 3:
        print("kullanim: t15a2_apply.py <templates_dir> <exclusions.json> [--dry-run]", file=sys.stderr)
        return 2
    tdir = Path(sys.argv[1])
    exc_path = Path(sys.argv[2])
    dry = "--dry-run" in sys.argv
    # CPO-1361 §6-2 — kardes script t15a_apply.py sessizce {} ile devam ediyordu;
    # bu script ise cirilciplak patliyordu (exit 1, izlenmesi zor traceback).
    # Ikisi de ayni, ACIK davranisa cekildi.
    if not exc_path.exists():
        print("HATA: exclusions.json bulunamadi: %s" % exc_path, file=sys.stderr)
        print("  Dislama kararlari olmadan kosmak yasak. Bos dislama istiyorsan"
              " ACIKCA bos bir json ver.", file=sys.stderr)
        return 2
    data = json.loads(exc_path.read_text(encoding="utf-8"))
    excl = {(e["file"].split("/")[-1], int(e["line"])) for e in data.get("exclusions", [])}

    stats = {"replaced": 0, "skip_not_css": 0, "skip_agent": 0, "skip_not_canon": 0}
    per_file, per_tok = {}, {}

    for path in sorted(tdir.glob("*.html")):
        name = path.name
        original = path.read_text(encoding="utf-8")
        out_lines, changed = [], 0

        for lineno, line in enumerate(original.split("\n"), start=1):
            if "rgb" not in line:
                out_lines.append(line)
                continue

            new, pos, delta = [], 0, 0
            for m in RGBA_RE.finditer(line):
                new.append(line[pos:m.start()])
                pos = m.end()
                trip = (int(m.group(1)), int(m.group(2)), int(m.group(3)))
                tok = TRIPLE.get(trip)
                if tok is None:
                    stats["skip_not_canon"] += 1
                    new.append(m.group(0))
                    continue
                if (name, lineno) in excl:
                    stats["skip_agent"] += 1
                    new.append(m.group(0))
                    continue
                if not CSS_DECL_RE.search(line[:m.start()]):
                    stats["skip_not_css"] += 1
                    new.append(m.group(0))
                    continue
                alpha = m.group(4)
                new.append("rgba(var(--bp-%s-rgb),%s)" % (tok, alpha))
                delta += 1
                per_tok[tok] = per_tok.get(tok, 0) + 1
            new.append(line[pos:])
            out_lines.append("".join(new))
            changed += delta

        if changed:
            stats["replaced"] += changed
            per_file[name] = changed
            if not dry:
                path.write_text("\n".join(out_lines), encoding="utf-8")

    print("=== T1.5a-2 " + ("(KURU CALISMA)" if dry else "(YAZILDI)") + " ===")
    for k, v in stats.items():
        print("  %-18s %d" % (k, v))
    print("\n=== TOKEN BASINA ===")
    for k, v in sorted(per_tok.items(), key=lambda x: -x[1]):
        print("  %5d  --bp-%s-rgb" % (v, k))
    print("\n=== DOSYA BASINA ===")
    for k, v in sorted(per_file.items(), key=lambda x: -x[1]):
        print("  %5d  %s" % (v, k))
    print("\nGEREKEN KANAL TOKEN'LARI: %d" % len(per_tok))

    # CPO-1361 §6-2 — KOSULSUZ `return 0` KALDIRILDI (kardes script ile ayni).
    if stats["replaced"] == 0:
        print("\nUYARI: HICBIR IKAME YAPILMADI — migrasyon zaten uygulanmis ya da"
              " dedektor eslesmiyor. Sessiz basari yerine EXIT=3.", file=sys.stderr)
        return 3
    return 0


if __name__ == "__main__":
    sys.exit(main())
