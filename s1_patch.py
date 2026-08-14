#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""S1 — --bp-border-subtle token ekle, yerel --border2 statik ayrac kullanimlarini migrate et."""
import sys

def patch(path, replacements):
    with open(path, "r", encoding="utf-8") as f:
        content = f.read()
    for i, (old, new) in enumerate(replacements):
        count = content.count(old)
        if count != 1:
            print(f"FAIL {path} replacement #{i}: found {count} occurrences (expected 1)")
            print(repr(old[:200]))
            sys.exit(1)
        content = content.replace(old, new)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    print(f"OK {path}: {len(replacements)} replacements applied")

patch("static/css/tokens.css", [
    ("  --bp-border:    #2a2a2c;\n  --bp-border2:   #46464d;\n",
     "  --bp-border:    #2a2a2c;\n  --bp-border2:   #46464d;\n  --bp-border-subtle: #21262d;\n"),
])

patch("templates/kategori.html", [
    ("    --border:#30363d; --border2:#21262d;\n", "    --border:#30363d;\n"),
])
patch("templates/varlik.html", [
    ("    --border:#30363d; --border2:#21262d;\n", "    --border:#30363d;\n"),
])
patch("templates/tarama.html", [
    ("    --border:var(--bp-bkl-bd); --border2:#21262d;\n", "    --border:var(--bp-bkl-bd);\n"),
])

for fp in ("templates/kategori.html", "templates/tarama.html", "templates/varlik.html"):
    with open(fp, "r", encoding="utf-8") as f:
        c = f.read()
    n = c.count("var(--border2)")
    if n == 0:
        print(f"FAIL {fp}: 0 var(--border2) found (beklenen >0)")
        sys.exit(1)
    c = c.replace("var(--border2)", "var(--bp-border-subtle)")
    with open(fp, "w", encoding="utf-8") as f:
        f.write(c)
    print(f"OK {fp}: {n} var(--border2) -> var(--bp-border-subtle)")

print("S1 PATCH APPLIED")
