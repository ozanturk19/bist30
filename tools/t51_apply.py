#!/usr/bin/env python3
"""T5.1 — .container max-width -> var(--bp-container-N) mekanik migrasyon.
Deger DEGISTIRILMEZ, yalniz .container{} kuralindeki max-width tokenize edilir.
"""
import re
import sys
import glob

ROOT = sys.argv[1] if len(sys.argv) > 1 else "."

TOKENS_CSS = f"{ROOT}/static/css/tokens.css"

CONTAINER_VALUES = [680, 820, 860, 900, 1100, 1200, 1400]

TOKEN_BLOCK = """
  /* ── 12. KONTEYNER GENISLIGI (container max-width) ─────────────
     OLCUM (22 sablon, .container{} kurali): 1100px:8  820px:4
       1200px:4  1400px:2  860px:2  900px:1  680px:1
     T5.1 kabul olcutu: "tek max-width token seti". 7 deger BILEREK
     ayri tutuldu (820 vs 860 farkli sablon gruplarinin bilinen
     genisligi, snap edilmedi) -- yalniz max-width tokenize edildi,
     margin/padding sablon-ozel kalir (T5.1 kapsami degil). */
  --bp-container-680:  680px;
  --bp-container-820:  820px;
  --bp-container-860:  860px;
  --bp-container-900:  900px;
  --bp-container-1100: 1100px;
  --bp-container-1200: 1200px;
  --bp-container-1400: 1400px;
"""

def patch_tokens_css():
    with open(TOKENS_CSS, "r", encoding="utf-8") as f:
        content = f.read()
    anchor = "  --bp-bp-lg: 900px;\n"
    if anchor not in content:
        raise SystemExit("ANCHOR NOT FOUND in tokens.css")
    if "--bp-container-680" in content:
        print("tokens.css: container tokens already present, skipping")
        return content, False
    content = content.replace(anchor, anchor + TOKEN_BLOCK, 1)
    with open(TOKENS_CSS, "w", encoding="utf-8") as f:
        f.write(content)
    return content, True

CONTAINER_RULE_RE = re.compile(
    r"(\.container\s*\{[^}]*?max-width:\s*)(\d+)px(\s*;)"
)

def patch_template(path):
    with open(path, "r", encoding="utf-8") as f:
        content = f.read()
    changes = []

    def repl(m):
        val = int(m.group(2))
        if val not in CONTAINER_VALUES:
            changes.append(("SKIP-UNKNOWN-VALUE", val))
            return m.group(0)
        changes.append(("OK", val))
        return f"{m.group(1)}var(--bp-container-{val}){m.group(3)}"

    new_content = CONTAINER_RULE_RE.sub(repl, content)
    if new_content != content:
        with open(path, "w", encoding="utf-8") as f:
            f.write(new_content)
    return changes

def bump_cachebust(path, old="20260810I", new="20260810J"):
    with open(path, "r", encoding="utf-8") as f:
        content = f.read()
    count = content.count(f"tokens.css?v={old}")
    if count == 0:
        return 0
    content = content.replace(f"tokens.css?v={old}", f"tokens.css?v={new}")
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    return count

def main():
    _, tokens_changed = patch_tokens_css()
    print(f"tokens.css patched: {tokens_changed}")

    templates = sorted(glob.glob(f"{ROOT}/templates/*.html"))
    total_ok = 0
    total_skip = 0
    per_file = {}
    for t in templates:
        changes = patch_template(t)
        if changes:
            per_file[t] = changes
            for kind, val in changes:
                if kind == "OK":
                    total_ok += 1
                else:
                    total_skip += 1

    print(f"\n.container max-width tokenized: {total_ok} occurrences across {len(per_file)} templates")
    if total_skip:
        print(f"SKIPPED (unknown value, needs manual review): {total_skip}")
        for t, changes in per_file.items():
            for kind, val in changes:
                if kind == "SKIP-UNKNOWN-VALUE":
                    print(f"  {t}: {val}px")

    print("\nPer-file breakdown:")
    for t, changes in per_file.items():
        oks = [c[1] for c in changes if c[0] == "OK"]
        print(f"  {t}: {oks}")

    cb_total = 0
    cb_files = 0
    for t in templates:
        n = bump_cachebust(t)
        if n:
            cb_total += n
            cb_files += 1
    print(f"\ncache-bust I->J bumped: {cb_total} occurrences across {cb_files} templates")

if __name__ == "__main__":
    main()
