#!/usr/bin/env python3
"""K-K — kanonik `.da-*` bildiriminin SAYFA CSS'inde KISAYOLLA silinmesi.

21.09.2026 CPO. Bu kapi, ayni turda KENDI fix'imin urettigi bir regresyondan
dogdu: `.da-select` (data-art.css) `appearance:none` + kendi SVG ok isaretini
`background-image` ile veriyor. /iletisim'in `.cf-input` kurali ise
`background: var(--bp-border-subtle)` KISAYOLUNU kullaniyordu ve
iletisim.css data-art.css'ten SONRA yuklendigi icin kisayol
`background-image`i de sifirladi -> canlida `appearance:none` + ok YOK, yani
HICBIR acilir-liste gostergesi olmayan bir <select>. Ne token, ne ham-hex, ne
kontrast, ne cascade-sirasi (K-G), ne cache-bust (K-J) kapisi bunu goremez:
ihlal TEK bir dosyada degil, iki dosyanin KESISIMINDE -- ve yalniz o iki
sinif AYNI OGEDE bulustugunda gerceklesir.

Olcut: bir sablonda `class="... da-X ..."` tasiyan bir oge varsa, o ogenin
DIGER siniflari/id'si icin yazilmis ve data-art.css'ten SONRA yuklenen her
kural (pages/*.css + sablon-ici <style> + inline style) taranir; `.da-X`in
bildirdigi bir LONGHAND'i bir KISAYOL ile sifirliyorsa FAIL.

Dogrudan longhand ezmesi (`padding-right:30px`) KASITLI bir deltadir, kapsam
disi. Kapi yalniz SESSIZ olani -- yazarin adini bile anmadigi bir ozelligin
yan etkiyle silinmesini -- yakalar.
"""
import re, sys, pathlib

ROOT = pathlib.Path(__file__).resolve().parent.parent
DA_CSS = ROOT / "static/css/data-art.css"
TEMPLATES = sorted((ROOT / "templates").glob("*.html"))
PAGE_CSS = sorted((ROOT / "static/css/pages").glob("*.css"))

# kisayol -> sifirladigi longhand'ler
SHORTHAND = {
    "background": {"background-color", "background-image", "background-repeat",
                   "background-position", "background-size", "background-attachment"},
    "padding":    {"padding-top", "padding-right", "padding-bottom", "padding-left"},
    "margin":     {"margin-top", "margin-right", "margin-bottom", "margin-left"},
    "font":       {"font-size", "font-family", "font-weight", "font-style", "line-height"},
    "border":     {"border-width", "border-style", "border-color",
                   "border-top-width", "border-right-width", "border-bottom-width", "border-left-width"},
    "flex":       {"flex-grow", "flex-shrink", "flex-basis"},
    "inset":      {"top", "right", "bottom", "left"},
    "overflow":   {"overflow-x", "overflow-y"},
    "transition": {"transition-property", "transition-duration", "transition-timing-function"},
}

def strip_comments(css):
    return re.sub(r"/\*.*?\*/", "", css, flags=re.S)

def rules(css):
    """(selector, body) ciftleri — at-rule govdeleri duzlestirilir."""
    css = strip_comments(css)
    css = re.sub(r"@media[^{]*\{", "", css)       # media sarmallarini ac
    css = re.sub(r"@supports[^{]*\{", "", css)
    out = []
    for m in re.finditer(r"([^{}]+)\{([^{}]*)\}", css):
        sel, body = m.group(1).strip(), m.group(2)
        if sel.startswith("@") or not sel:
            continue
        out.append((sel, body))
    return out

def declared_props(body):
    props = set()
    for d in body.split(";"):
        if ":" in d:
            props.add(d.split(":", 1)[0].strip().lower())
    return props

# 1) data-art.css: .da-X -> bildirdigi longhand'ler
canonical = {}
for sel, body in rules(DA_CSS.read_text(encoding="utf-8")):
    for cls in re.findall(r"\.(da-[a-z0-9-]+)", sel):
        canonical.setdefault(cls, set()).update(declared_props(body))

# 2) sablonlar: da-X tasiyan ogelerin DIGER sinif/id'leri + inline style
#    kanonik_sinif -> {"classes": {...}, "ids": {...}}
partners = {}
inline_hits = []   # (sablon, da-cls, shorthand, longhand)
tag_re = re.compile(r"<(\w+)([^>]*?)>", re.S)
for t in TEMPLATES:
    html = t.read_text(encoding="utf-8")
    for m in tag_re.finditer(html):
        attrs = m.group(2)
        cm = re.search(r'class\s*=\s*"([^"]*)"', attrs) or re.search(r"class\s*=\s*'([^']*)'", attrs)
        if not cm:
            continue
        classes = cm.group(1).split()
        da = [c for c in classes if c in canonical]
        if not da:
            continue
        others = [c for c in classes if c not in canonical]
        im = re.search(r'id\s*=\s*"([^"]*)"', attrs) or re.search(r"id\s*=\s*'([^']*)'", attrs)
        for c in da:
            p = partners.setdefault(c, {"classes": set(), "ids": set()})
            p["classes"].update(others)
            if im:
                p["ids"].add(im.group(1).strip())
        sm = re.search(r'style\s*=\s*"([^"]*)"', attrs)
        if sm:
            props = declared_props(sm.group(1))
            for c in da:
                for sh, longs in SHORTHAND.items():
                    if sh in props:
                        clob = longs & canonical[c]
                        if clob:
                            inline_hits.append((t.name, c, sh, sorted(clob)))

# 3) data-art.css'ten SONRA yuklenen kurallar
later = [(p.relative_to(ROOT).as_posix(), p.read_text(encoding="utf-8")) for p in PAGE_CSS]
for t in TEMPLATES:
    html = t.read_text(encoding="utf-8")
    for sm in re.finditer(r"<style[^>]*>(.*?)</style>", html, re.S):
        later.append((f"templates/{t.name} <style>", sm.group(1)))

hits = list(inline_hits)
for path, css in later:
    for sel, body in rules(css):
        props = declared_props(body)
        shs = [s for s in SHORTHAND if s in props]
        if not shs:
            continue
        for da_cls, longs in canonical.items():
            p = partners.get(da_cls)
            if not p:
                continue
            touches = any(re.search(r"\.%s(?![\w-])" % re.escape(c), sel) for c in p["classes"]) \
                   or any(re.search(r"#%s(?![\w-])" % re.escape(i), sel) for i in p["ids"])
            if not touches:
                continue
            for sh in shs:
                clob = SHORTHAND[sh] & longs - props   # yazar longhand'i ACIKCA geri yazmissa sorun yok
                if clob:
                    hits.append((path, da_cls, sh, sorted(clob), sel.strip()[:70]))

if hits:
    print("K-K KIRIK — kanonik .da-* bildirimi kisayolla siliniyor:")
    for h in hits:
        if len(h) == 4:
            print(f"  {h[0]}  inline style  `{h[2]}:` kisayolu {h[1]}'in {h[3]} bildirimini siliyor")
        else:
            print(f"  {h[0]}  `{h[4]}`  ->  `{h[2]}:` kisayolu {h[1]}'in {h[3]} bildirimini siliyor")
    sys.exit(1)

print(f"K-K: {len(canonical)} kanonik .da-* sinifi, {sum(len(v['classes'])+len(v['ids']) for v in partners.values())} ortak secici — kisayol silmesi YOK")
