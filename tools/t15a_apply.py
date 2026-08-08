#!/usr/bin/env python3
"""
T1.5a — ham hex -> var(--bp-*) migrasyonu (BorsaPusula, Master Donusum Programi FAZ 1).

TASARIM ILKESI: bu script ajan bulgularina GUVENMEZ. Kendi yapisal guvenligi var.
Bir hex YALNIZCA gercek bir CSS bildirim degeri konumundaysa degistirilir. Ajanlardan
gelen dislama listesi bunun UZERINE binen ikinci bir kapidir, tek kapi degil.

YAPISAL KURAL (tek satir icinde, hex'ten geriye bakarak):
    <prop>:<deger-parcasi>#hex
  - <prop> yalnizca KUCUK harf + tire  -> JS camelCase anahtarlarini (borderColor:) eler
  - <prop>'un solundaki karakter alfanumerik OLAMAZ -> "borderColor:" icindeki "olor:" eslesmesini eler
  - iki nokta ile hex arasinda TIRNAK veya = OLAMAZ -> CSS'te hex asla tirnakli degildir;
    JS'te ('#2a2a2c') daima tirnaklidir. Bu tek kural su uc tuzagi birden kapatir:
        borderColor: '#2a2a2c'      (lightweight-charts JS secenegi)
        ctx.fillStyle = '#e5e1e4'   (canvas)
        stop-color="#b8c3ff"        (SVG oznitelik - zaten iki nokta yok)
        content="#0e0e12"           (meta - iki nokta yok)
  - style="color:#909097" DOGRU sekilde GECER (iki noktadan sonra tirnak yok)
"""
import json
import re
import sys
from pathlib import Path

# T1.5a kanonik harita.
# BILINCLI HARIC: #30363d (--bp-bkl-bd) ve #1e293b (--bp-bkl-bg).
# Bu ikisi GitHub-legacy paletinin genel kenarlik/yuzey degerleridir ve BEKLIYOR sinyal
# token'iyla yalnizca DEGER olarak cakisirlar. Mekanik ikame, jenerik bir kenarliga
# "bu bir bekleme-sinyali kenarligidir" anlami yuklerdi ve T1.5b'nin rol-tabanli
# eslemesini bozardi. T1.5b'ye devredildi.
# #0043eb (--bp-brand-d) HARIC: tuketici sayisi olculdu = 0 (CSS-konum 0, CSS-disi 0).
# Olu token; CPO-1349 par.8 madde-3 geregi tokens.css-ten silinecek, haritada yeri yok.
CANON = {
    "#0e0e12": "--bp-bg",
    "#141416": "--bp-surface",
    "#1c1b1f": "--bp-surface2",
    "#201f21": "--bp-surface3",
    "#2a2a2c": "--bp-border",
    "#46464d": "--bp-border2",
    "#e5e1e4": "--bp-text",
    "#c7c5cd": "--bp-text2",
    "#909097": "--bp-text3",   # BEKLIYOR sinyal baglaminda --bp-bkl (semantic_flags ile)
    "#b8c3ff": "--bp-brand",
    "#00e290": "--bp-al",
    "#f85149": "--bp-sat",
    "#3d0f0f": "--bp-sat-bg",
    "#da3633": "--bp-sat-bd",
    "#f59e0b": "--bp-gold",
    "#ffc850": "--bp-volume",
    "#a855f7": "--bp-premium",
}

HEX_RE = re.compile("(" + "|".join(CANON) + r")\b", re.IGNORECASE)

# Hex'ten geriye bakan CSS-bildirim testi. Satir sonuna ($) demirlenir.
CSS_DECL_RE = re.compile(r"(?:^|[^A-Za-z0-9_-])[a-z][a-z-]*\s*:\s*[^;{}\"'=]*$")


def is_css_value_position(line: str, idx: int) -> bool:
    """idx konumundaki hex gercek bir CSS bildirim degeri mi?"""
    return bool(CSS_DECL_RE.search(line[:idx]))


def main() -> int:
    if len(sys.argv) < 3:
        print("kullanim: t15a_apply.py <templates_dir> <exclusions.json> [--dry-run]", file=sys.stderr)
        return 2

    tdir = Path(sys.argv[1])
    exc_path = Path(sys.argv[2])
    dry = "--dry-run" in sys.argv

    data = json.loads(exc_path.read_text(encoding="utf-8")) if exc_path.exists() else {}
    # (dosya, satir) -> ajan dislamasi. Hex bazinda degil satir bazinda uygulanir:
    # bir satirda hem guvenli hem guvensiz kullanim varsa TAMAMI atlanir (muhafazakar).
    agent_excl = {(e["file"].split("/")[-1], int(e["line"])) for e in data.get("exclusions", [])}
    # (dosya, satir) -> --bp-bkl kullanilacak #909097 satirlari
    bkl_lines = {
        (f["file"].split("/")[-1], int(f["line"]))
        for f in data.get("semantic_flags", [])
        if "bkl" in f.get("suggested_token", "")
    }

    stats = {
        "replaced": 0, "skip_not_css": 0, "skip_agent": 0,
        "bkl_applied": 0, "files_changed": 0,
    }
    skipped_detail = []
    per_file = {}

    for path in sorted(tdir.glob("*.html")):
        name = path.name
        original = path.read_text(encoding="utf-8")
        out_lines = []
        changed = 0

        for lineno, line in enumerate(original.split("\n"), start=1):
            if not HEX_RE.search(line):
                out_lines.append(line)
                continue

            if (name, lineno) in agent_excl:
                n = len(HEX_RE.findall(line))
                stats["skip_agent"] += n
                skipped_detail.append((name, lineno, "ajan-dislamasi", line.strip()[:110]))
                out_lines.append(line)
                continue

            new_line, pos, delta = [], 0, 0
            for m in HEX_RE.finditer(line):
                new_line.append(line[pos:m.start()])
                hexv = m.group(1).lower()
                if is_css_value_position(line, m.start()):
                    token = CANON[hexv]
                    if hexv == "#909097" and (name, lineno) in bkl_lines:
                        token = "--bp-bkl"
                        stats["bkl_applied"] += 1
                    new_line.append(f"var({token})")
                    delta += 1
                else:
                    stats["skip_not_css"] += 1
                    skipped_detail.append((name, lineno, "yapisal-css-degil", line.strip()[:110]))
                    new_line.append(m.group(0))
                pos = m.end()
            new_line.append(line[pos:])
            out_lines.append("".join(new_line))
            changed += delta

        if changed:
            stats["replaced"] += changed
            stats["files_changed"] += 1
            per_file[name] = changed
            if not dry:
                path.write_text("\n".join(out_lines), encoding="utf-8")

    print("=== T1.5a UYGULAMA " + ("(KURU CALISMA)" if dry else "(YAZILDI)") + " ===")
    for k, v in stats.items():
        print(f"  {k:18s} {v}")
    print("\n=== DOSYA BASINA IKAME ===")
    for k, v in sorted(per_file.items(), key=lambda x: -x[1]):
        print(f"  {v:5d}  {k}")

    print(f"\n=== ATLANANLAR ({len(skipped_detail)}) ===")
    from collections import Counter
    for reason, cnt in Counter(s[2] for s in skipped_detail).items():
        print(f"  {reason}: {cnt}")
    print("\n--- atlanan satir ornekleri (ilk 40) ---")
    for name, ln, reason, txt in skipped_detail[:40]:
        print(f"  {name}:{ln} [{reason}] {txt}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
