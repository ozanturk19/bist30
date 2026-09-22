#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""tools/brand-wordmark-canon-check.py -- K-CZ (KAPI 71):
MARKA SOZCUK-ISARETININ VURGULU YARISI TEK TOKEN'DAN BOYANIR.

OLCULDU (22.09.2026, sablon+CSS envanteri):
  "Borsa|Pusula" sozcuk-isaretinin ikinci yarisi UC AYRI renk kanonundan
  boyaniyordu:
    --bp-al          -> templates/_header.html (SVG tspan) + templates/_footer.html
                        => ust+alt bilgi 20+ sayfanin HEPSINDE
    --bp-brand       -> static/css/pages/404.css `header .brand-name b`
                        (404/410/429/500) -- bu deger CPO-1558 ONCESI logo
                        gradyaninin rengiydi, goc orada yarim kalmisti
    --bp-accent-cyan -> static/css/pages/hakkinda.css `.hero-title span`
                        => /hakkinda'da AYNI EKRANDA header logosu yesil,
                           hero basligi camgobegi: ayni kelime iki renkte

  Ayrica --bp-al bu uründe ANLAM TASIR ("AL sinyali"). K-BO kurali:
  yon/sinyal rengi, yon tasimayan bir buyuklugu boyayamaz. Marka adi yon
  tasimaz. K-CY'de ayni ihlal navigasyonda bulunmustu (nav aktif ogesi
  --bp-al ile boyaniyordu); bu, ayni sinifin bir katman yukarisi: MARKA.

KURAL (sifir sarti, ratchet YOK):
  Bir sablonda `Borsa<TAG ...>Pusula</TAG>` deseni varsa, o TAG'in etkin renk
  bildirimi `var(--bp-logo-accent)` OLMALIDIR. Renk kaynagi;
    (a) satir-ici `fill="var(--X)"` / `style="color:var(--X)"`,
    (b) `class="..."` -> CSS'te `.<sinif>` seciciisinin `color:`,
    (c) ebeveyn sinifi + tag -> CSS'te `.<ebeveyn> <tag>` seciciisinin `color:`
  kanallarindan cozulur. Cozulemeyen de IHLAL'dir: renk kaynagi bilinmiyorsa
  kanona ait oldugu da bilinemez (129. ders: yuklendigini grep ile bilirsin,
  kazandigini degil -- bu yuzden kapi TEK bir kaynak cozmeyi sart kosar, iki
  farkli token cozerse de ihlaldir).

MUAF: vurgusuz duz metin "BorsaPusula" (og/meta/aria/gövde metni) -- orada
  sozcuk-isareti RENDER EDILMIYOR, yalniz ad geciyor. `.off-brand` (offline)
  bilerek vurgusuzdur (terminal sayfa, eyebrow dili).

KULLANIM:
  python3 tools/brand-wordmark-canon-check.py            # calisan agac
  python3 tools/brand-wordmark-canon-check.py --ref SHA  # pozitif kontrol
  python3 tools/brand-wordmark-canon-check.py --self-test
"""
import os
import re
import subprocess
import sys

CANON = "--bp-logo-accent"
TAGS = "tspan|span|b|strong|em|i"
WORDMARK = re.compile(
    r"Borsa\s*<(" + TAGS + r")\b([^>]*)>\s*Pusula\s*</\1>", re.IGNORECASE
)
VAR_RE = re.compile(r"var\(\s*(--[a-z0-9-]+)\s*\)", re.IGNORECASE)
CSS_DIRS = ["static/css", "static/css/pages"]
TPL_DIR = "templates"


def _read(path, ref):
    if ref:
        try:
            return subprocess.check_output(
                ["git", "show", "%s:%s" % (ref, path)], stderr=subprocess.DEVNULL
            ).decode("utf-8", "replace")
        except subprocess.CalledProcessError:
            return None
    if not os.path.exists(path):
        return None
    with open(path, encoding="utf-8") as fh:
        return fh.read()


def _list(path_dir, suffix, ref):
    if ref:
        out = subprocess.check_output(
            ["git", "ls-tree", "-r", "--name-only", ref, path_dir]
        ).decode("utf-8", "replace")
        names = [n for n in out.splitlines() if n.endswith(suffix)]
    else:
        names = []
        for root, _dirs, files in os.walk(path_dir):
            for f in files:
                if f.endswith(suffix):
                    names.append(os.path.join(root, f))
    return sorted(names)


def _css_corpus(ref):
    """{selector_text: [tokens]} -- yalnizca `color:` bildirimleri."""
    rules = []
    seen = set()
    for d in CSS_DIRS:
        for path in _list(d, ".css", ref):
            if path in seen:
                continue
            seen.add(path)
            src = _read(path, ref)
            if not src:
                continue
            src = re.sub(r"/\*.*?\*/", " ", src, flags=re.S)
            for m in re.finditer(r"([^{}]+)\{([^{}]*)\}", src):
                sel, body = m.group(1).strip(), m.group(2)
                cm = re.search(r"(?<![-a-z])color\s*:\s*([^;]+)", body)
                if not cm:
                    continue
                toks = VAR_RE.findall(cm.group(1))
                rules.append((path, sel, toks or [cm.group(1).strip()]))
    return rules


def _resolve(tag, attrs, line, css_rules):
    """(tokens, channel) -- bu vurgulu yarinin renk kaynagini coz."""
    found = []
    inline = VAR_RE.findall(attrs)
    if inline:
        return inline, "satir-ici"

    classes = []
    cm = re.search(r'class\s*=\s*"([^"]*)"', attrs)
    if cm:
        classes = cm.group(1).split()
    for path, sel, toks in css_rules:
        for c in classes:
            if re.search(r"\.%s(?![\w-])" % re.escape(c), sel):
                found.extend(toks)
    if found:
        return found, "sinif"

    # ebeveyn sinifi + tag  (ornek: `header .brand-name b`)
    parents = re.findall(r'class\s*=\s*"([^"]*)"', line)
    pcls = [c for grp in parents for c in grp.split()]
    for path, sel, toks in css_rules:
        if not re.search(r"(?<![\w-])%s\s*$" % re.escape(tag), sel.strip(), re.I):
            continue
        for c in pcls:
            if re.search(r"\.%s(?![\w-])" % re.escape(c), sel):
                found.extend(toks)
    if found:
        return found, "ebeveyn+tag"
    return [], "COZULEMEDI"


def scan(ref=None):
    css_rules = _css_corpus(ref)
    violations = []
    checked = 0
    for path in _list(TPL_DIR, ".html", ref):
        src = _read(path, ref)
        if not src:
            continue
        for m in WORDMARK.finditer(src):
            checked += 1
            tag, attrs = m.group(1), m.group(2)
            line_start = src.rfind("\n", 0, m.start()) + 1
            line_end = src.find("\n", m.end())
            line = src[line_start : line_end if line_end > 0 else len(src)]
            lineno = src.count("\n", 0, m.start()) + 1
            toks, channel = _resolve(tag, attrs, line, css_rules)
            uniq = sorted(set(toks))
            if uniq == [CANON]:
                continue
            violations.append(
                (path, lineno, tag, channel, uniq or ["(renk kaynagi yok)"])
            )
    return checked, violations


def self_test():
    """Kapinin kusuru GERCEKTEN yakaladigini kanitlar (52. ders: bozuk hali enjekte et)."""
    cases = [
        ('<p>Borsa<span style="color:var(--bp-al)">Pusula</span></p>', True),
        ('<p>Borsa<span style="color:var(--bp-logo-accent)">Pusula</span></p>', False),
        ('<text>Borsa<tspan fill="var(--bp-brand)">Pusula</tspan></text>', True),
        ("<p>Borsa<b>Pusula</b></p>", True),  # cozulemeyen = ihlal
        ("<p>BorsaPusula bir uründür.</p>", False),  # vurgusuz duz metin: muaf
    ]
    ok = 0
    for src, should_flag in cases:
        m = WORDMARK.search(src)
        if not m:
            flagged = False
        else:
            toks, _ch = _resolve(m.group(1), m.group(2), src, [])
            flagged = sorted(set(toks)) != [CANON]
        if flagged == should_flag:
            ok += 1
        else:
            print("  SELF-TEST FAIL: %r -> %s (beklenen %s)" % (src, flagged, should_flag))
    print("self-test %d/%d" % (ok, len(cases)))
    return 0 if ok == len(cases) else 1


def main():
    if "--self-test" in sys.argv:
        return self_test()
    ref = None
    if "--ref" in sys.argv:
        ref = sys.argv[sys.argv.index("--ref") + 1]
    checked, violations = scan(ref)
    label = "brand-wordmark-canon" + (" [ref=%s]" % ref if ref else "")
    if violations:
        print("FAIL %s -- %d ihlal / %d sozcuk-isareti" % (label, len(violations), checked))
        for path, lineno, tag, channel, toks in violations:
            print("  %s:%d  <%s> kanal=%s renk=%s (kanon: %s)"
                  % (path, lineno, tag, channel, ",".join(toks), CANON))
        return 1
    print("PASS %s -- %d sozcuk-isareti, hepsi %s" % (label, checked, CANON))
    return 0


if __name__ == "__main__":
    sys.exit(main())
