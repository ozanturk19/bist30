#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""KAPI 79 (K-DM) — SEKTOR AKRANI VAADI, AKRANIN VARLIGINA BAGLI OLMALI.

Kok neden (canli 22.09):
  app.py `_get_sector()` siniflandirilamayan ticker'lara "Diğer" doner ve
  (CPO-1464 #3) bu kova icin `_sector_pool = []` yapar -- yani "ayni sektor"
  havuzu KASITLI olarak bostur. Iki tuketici vardi:
    * `related_stocks`  -> `{% if related_stocks %}` ile dalliyordu (dogru),
    * `compare_url`     -> hero'daki Karsilastir dugmesi DALLANMIYORDU.
  Sonuc: 11 hisse (ADEL AGROT BJKAS DURDO FENER FMIZP FORMT GSRAY IEYHO
  KARTN MARTI) icin dugme "Sektordeki diger hisselerle karsilastir" diye
  vaat ediyor, href ise akransiz `/karsilastir?tickers=BJKAS` -- sayfa
  "en az 2 hisse" bos durumuna dusuyordu. Ayni veri boslugunu iki tuketici
  farkli dalliyordu: "ayni is icin iki kanon".

Kurallar (YAPIYA bakar, yaziya degil):
  R1  `href="{{ compare_url }}"` tasiyan her <a>, icindeki her SEKTOR
      iddiasini (`sekt(o|ö)r` kokü) bir `{% if %}` icinde tasimak
      ZORUNDA; kosul akran varligina (`_has_peers`) bagli olmali.
  R2  `_has_peers` (ya da akran-varligi bayragi ne isimle taniniyorsa)
      `compare_url`in KENDISINDEN turetilmeli -- sektor ADINA
      ("Diğer") karsilastirmasiyla DEGIL. (52/162. ders: kapinin da,
      sablonun da olcutu yapisal olmali; yarin kovanin adi degisirse
      yazima bagli guard sessizce coker.)
  R3  `related_stocks` basligindaki sektor iddiasi `{% if related_stocks %}`
      blogu icinde kalmali.
  R4  compare_url'i tuketen BASKA bir sablon varsa o da R1'e tabidir.

Kullanim:
  python3 tools/sector-peer-promise-check.py            # calisan agac
  python3 tools/sector-peer-promise-check.py --self-test
  python3 tools/sector-peer-promise-check.py --ref <commit>
"""
import os, re, subprocess, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SECTOR_RE = re.compile(r"[Ss]ekt[oö]r", re.UNICODE)
A_TAG_RE = re.compile(r"<a\b[^>]*?href=\"\{\{\s*compare_url\s*\}\}\"[^>]*?>", re.S)
SET_RE = re.compile(r"\{\%-?\s*set\s+(_?[A-Za-z_][A-Za-z0-9_]*)\s*=\s*(.+?)-?\%\}", re.S)


def _strip_jinja_comments(text):
    return re.sub(r"\{#.*?#\}", " ", text, flags=re.S)


def _if_spans(tag):
    """Tag icindeki {% if ... %}...{% endif %} araliklarini (start, end, cond) dondur."""
    spans = []
    stack = []
    for m in re.finditer(r"\{\%-?\s*(if|elif|else|endif)\b(.*?)-?\%\}", tag, re.S):
        kind, rest = m.group(1), m.group(2)
        if kind == "if":
            stack.append((m.start(), rest.strip()))
        elif kind == "endif" and stack:
            start, cond = stack.pop()
            spans.append((start, m.end(), cond))
    return spans


def check_text(hisse_html, other_templates=None):
    """(ihlaller, incelenen_etiket_sayisi) dondurur. Saf fonksiyon -> self-test edilebilir."""
    violations = []
    src = _strip_jinja_comments(hisse_html)

    # --- R2: akran-varligi bayragi compare_url'den turetilmis mi? ---
    flags = {}
    for m in SET_RE.finditer(src):
        flags[m.group(1)] = m.group(2)

    tags = A_TAG_RE.findall(src)
    if not tags:
        violations.append("R1: `href=\"{{ compare_url }}\"` tasiyan <a> bulunamadi "
                          "(kapinin korudugu yuzey kaybolmus ya da yazimi degismis).")

    for tag in tags:
        spans = _if_spans(tag)
        for sm in SECTOR_RE.finditer(tag):
            covering = [s for s in spans if s[0] <= sm.start() < s[1]]
            if not covering:
                violations.append(
                    "R1: compare_url dugmesinde KOSULSUZ sektor iddiasi -> "
                    + tag[max(0, sm.start() - 60):sm.start() + 60].replace("\n", " "))
                continue
            cond = " ".join(c for _, _, c in covering)
            # Bayrak adi kosulda TAM SOZCUK olarak gecmeli: `{% set _ = ... %}`
            # gibi tek-alt-cizgi "cop" atamalari `_has_peers` icinde alt-dizi
            # olarak eslesip sahte ihlal uretiyordu (K-DM kapisinin ilk
            # kosumunda tam olarak bu oldu).
            used = [f for f in flags
                    if re.search(r"(?<![A-Za-z0-9_])%s(?![A-Za-z0-9_])" % re.escape(f), cond)]
            if not used:
                violations.append(
                    "R1: sektor iddiasinin kosulu akran-varligi bayragina bagli degil -> "
                    + cond.strip())
                continue
            for f in used:
                if "compare_url" not in flags[f]:
                    violations.append(
                        "R2: `%s` bayragi compare_url'den TURETILMEMIS (yazima bagli guard) -> %s = %s"
                        % (f, f, flags[f].strip()))

    # --- R3: related_stocks basligi kendi kosulu icinde mi? ---
    rel_blocks = re.findall(r"\{\%-?\s*if\s+related_stocks\s*-?\%\}(.*?)\{\%-?\s*endif\s*-?\%\}", src, re.S)
    rel_heading = re.search(r"<h2[^>]*id=\"related-heading\"[^>]*>(.*?)</h2>", src, re.S)
    if rel_heading:
        if not any(rel_heading.group(0) in b for b in rel_blocks):
            violations.append("R3: `related-heading` sektor basligi `{% if related_stocks %}` blogunun DISINDA.")

    # --- R4: baska tuketici ---
    for name, text in (other_templates or {}).items():
        t = _strip_jinja_comments(text)
        for tag in A_TAG_RE.findall(t):
            if SECTOR_RE.search(tag) and not _if_spans(tag):
                violations.append("R4: %s icinde kosulsuz sektor iddiasi tasiyan compare_url baglantisi." % name)

    return violations, len(tags)


# --------------------------------------------------------------------------
SELF_TESTS = [
    # (ad, hisse_html, ihlal_beklenir_mi)
    ("temiz: kosullu vaat + compare_url'den turetilmis bayrak",
     "{% set _has_peers = ',' in compare_url %}\n"
     "<a href=\"{{ compare_url }}\" data-tip=\"{% if _has_peers %}Sektördeki diğer hisselerle{% else %}Başka bir hisseyle{% endif %}\">K</a>",
     False),
    ("ihlal: kosulsuz sektor iddiasi (K-DM oncesi canli hali)",
     "<a href=\"{{ compare_url }}\" data-tip=\"Sektördeki diğer hisselerle karşılaştır\">K</a>",
     True),
    ("ihlal: aria-label'da kosulsuz sektor iddiasi, data-tip kosullu",
     "{% set _has_peers = ',' in compare_url %}\n"
     "<a href=\"{{ compare_url }}\" data-tip=\"{% if _has_peers %}Sektördeki{% endif %}\" aria-label=\"{{ sector }} sektöründeki benzer hisselerle\">K</a>",
     True),
    ("ihlal: bayrak sektor ADINA bagli (yazima bagli guard)",
     "{% set _has_peers = sector != 'Diğer' %}\n"
     "<a href=\"{{ compare_url }}\" data-tip=\"{% if _has_peers %}Sektördeki diğer hisselerle{% endif %}\">K</a>",
     True),
    ("ihlal: kosul var ama akran bayragiyla ilgisiz",
     "{% set _has_peers = ',' in compare_url %}\n"
     "<a href=\"{{ compare_url }}\" data-tip=\"{% if sector %}Sektördeki diğer hisselerle{% endif %}\">K</a>",
     True),
    ("ihlal: compare_url dugmesi tamamen kaybolmus",
     "<a href=\"/karsilastir\">Karşılaştır</a>", True),
    ("temiz: sektorsuz vaat",
     "<a href=\"{{ compare_url }}\" data-tip=\"Başka bir hisseyle karşılaştır\">K</a>", False),
    ("ihlal: related basligi kosulsuz",
     "{% set _has_peers = ',' in compare_url %}\n"
     "<a href=\"{{ compare_url }}\" data-tip=\"{% if _has_peers %}Sektördeki{% endif %}\">K</a>\n"
     "<h2 id=\"related-heading\">{{ sector }} Sektöründen Diğer Hisseler</h2>", True),
    ("temiz: related basligi kendi kosulunda",
     "{% set _has_peers = ',' in compare_url %}\n"
     "<a href=\"{{ compare_url }}\" data-tip=\"{% if _has_peers %}Sektördeki{% endif %}\">K</a>\n"
     "{% if related_stocks %}<h2 id=\"related-heading\">{{ sector }} Sektöründen Diğer Hisseler</h2>{% endif %}", False),
    ("temiz: yorum icindeki sektor sozu ihlal sayilmaz",
     "{% set _has_peers = ',' in compare_url %}\n"
     "{# sektor havuzu bos olabilir #}\n"
     "<a href=\"{{ compare_url }}\" data-tip=\"{% if _has_peers %}Sektördeki{% endif %}\">K</a>", False),
]


def run_self_test():
    ok = 0
    for name, html, expect_fail in SELF_TESTS:
        v, _ = check_text(html)
        got = bool(v)
        if got == expect_fail:
            ok += 1
        else:
            print("  ✗ %s (beklenen ihlal=%s, bulunan=%s) %s" % (name, expect_fail, got, v))
    print("self-test %d/%d" % (ok, len(SELF_TESTS)))
    return 0 if ok == len(SELF_TESTS) else 1


def _read(ref, path):
    if ref:
        return subprocess.check_output(["git", "show", "%s:%s" % (ref, path)], cwd=ROOT).decode("utf-8")
    with open(os.path.join(ROOT, path), encoding="utf-8") as f:
        return f.read()


def main():
    args = sys.argv[1:]
    if "--self-test" in args:
        return run_self_test()
    ref = None
    if "--ref" in args:
        ref = args[args.index("--ref") + 1]

    hisse = _read(ref, "templates/hisse.html")
    others = {}
    tdir = os.path.join(ROOT, "templates")
    for fn in sorted(os.listdir(tdir)):
        if not fn.endswith(".html") or fn == "hisse.html":
            continue
        try:
            txt = _read(ref, "templates/" + fn)
        except subprocess.CalledProcessError:
            continue
        if "compare_url" in txt:
            others[fn] = txt

    violations, n = check_text(hisse, others)
    if violations:
        print("KAPI 79 (K-DM) %d ihlal (%d compare_url baglantisi tarandi):" % (len(violations), n))
        for v in violations:
            print("  -", v)
        return 1
    print("KAPI 79 (K-DM) temiz — %d compare_url baglantisi, sektor vaadi akran varligina bagli." % n)
    return 0


if __name__ == "__main__":
    sys.exit(main())
