"""C-P1-2210d (23.10) — ortak kabuk tek kaynak (makro şerit testinin eşi).

Geniş denetim 22.10: 13 sayfa CSS'i `:where(body > header)`'ı eziyordu → 5 farklı zemin/çizgi;
alt bilgideki "Gün sonu teknik analiz" notu 8 sayfada yoktu; atlama bağlantısı 2 px görünüyordu.
Kilitler:
  1. Header kök kuralı (`header {…}` / `body > header {…}`) yalnız shared.css'te (+ ilk boyama _bp_critical_css).
  2. Alt bilgi notu varsayılan açık; kapatan yalnız tarihli sayfalar (bulten, harita_gun).
  3. Atlama bağlantısı ekran dışında tamamen gizli (top ≤ -100px).
"""
import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TPL = os.path.join(ROOT, "templates")
CSS_DIRS = [os.path.join(ROOT, "static", "css"), os.path.join(ROOT, "static", "css", "pages")]
HEADER_ROOT_RE = re.compile(r"(?:^|[{};,\s])(?:body\s*>\s*)?header\s*(?:,[^{]*)?\{", re.M)


def _strip_comments(s):
    return re.sub(r"/\*.*?\*/", "", s, flags=re.S)


def test_header_kok_kurali_yalniz_shared():
    bad = []
    for d in CSS_DIRS:
        for f in sorted(os.listdir(d)):
            if f.endswith(".css") and f != "shared.css":
                s = _strip_comments(open(os.path.join(d, f), encoding="utf-8").read())
                if HEADER_ROOT_RE.search(s):
                    bad.append(f)
    for f in sorted(os.listdir(TPL)):
        if f.endswith(".html") and f != "_bp_critical_css.html":
            s = open(os.path.join(TPL, f), encoding="utf-8").read()
            for st in re.findall(r"<style[^>]*>(.*?)</style>", s, flags=re.S):
                if HEADER_ROOT_RE.search(_strip_comments(st)):
                    bad.append(f)
    assert not bad, f"header kök kuralı sayfada eziliyor: {bad}"


def test_footer_notu_varsayilan_acik():
    s = open(os.path.join(TPL, "_footer.html"), encoding="utf-8").read()
    assert "ftr_data_note|default(true)" in s
    kapatan = sorted(f for f in os.listdir(TPL) if f.endswith(".html")
                     and "ftr_data_note=false" in open(os.path.join(TPL, f), encoding="utf-8").read())
    assert kapatan == ["bulten.html", "harita_gun.html"], kapatan


def test_takip_kendine_baglanmaz():
    s = open(os.path.join(TPL, "takip.html"), encoding="utf-8").read()
    assert "ftr_self='/takip'" in s


def test_atlama_baglantisi_tam_gizli():
    for f in ("_head.html", "_bp_critical_css.html"):
        s = open(os.path.join(TPL, f), encoding="utf-8").read()
        tops = [int(t) for t in re.findall(r"\.skip-link\{[^}]*?top:(-?\d+)px", s)]
        assert tops and all(t <= -100 for t in tops), (f, tops)


# --- 23.10 ikinci tur: iki kapsayıcı genişliği, sabit 15 öğeli alt bilgi, tek etkin çip stili ---
def test_kapsayici_genislikleri_yalniz_token():
    """Sayfa kapsayıcısı max-width'i yalnız --bp-container-wide / --bp-container-read olabilir."""
    files = ("shared.css", "data-art.css", "pages/takvim.css", "pages/haberler.css", "pages/err.css", "pages/takip.css")
    bad = []
    for f in files:
        s = _strip_comments(open(os.path.join(ROOT, "static", "css", f), encoding="utf-8").read())
        for m in re.finditer(r"(?:^|[}\s])\.(container|container--wide|tk|hb|err-main|da-page)\s*\{([^}]*)\}", s):
            mw = re.search(r"max-width:\s*([^;}]+)", m.group(2))
            if mw and mw.group(1).strip() not in ("var(--bp-container-wide)", "var(--bp-container-read)"):
                bad.append((f, m.group(1), mw.group(1)))
    assert not bad, bad


def test_footer_her_sayfada_15_oge():
    import jinja2
    env = jinja2.Environment(loader=jinja2.FileSystemLoader(TPL), autoescape=True)
    for self_ in ("", "/", "/tarama", "/bulten/arsiv", "/iletisim"):
        html = env.get_template("_footer.html").render(ftr_self=self_)
        nav = re.search(r'<nav class="da-footer-links".*?</nav>', html, re.S).group(0)
        assert nav.count('class="bp-footer-link') == 15, (self_, nav.count('class="bp-footer-link'))
        if self_ and self_ != "/":
            assert f'href="{self_}"' not in nav, self_


def test_etkin_cip_tek_stil():
    canon = "border-color:var(--bp-brand);background:rgba(var(--bp-brand-rgb),.14);color:var(--bp-brand)"
    for f, sel in (("pages/haberler.css", '.hv-fch[aria-current="true"]{'), ("pages/takvim.css", '.tk-flt button[aria-pressed="true"]{'),
                   ("pages/kesfet.css", '.kf-tab[aria-current="page"]{'), ("pages/haberler.css", '.hb-flt a[aria-current="true"]{')):
        s = open(os.path.join(ROOT, "static", "css", f), encoding="utf-8").read()
        assert sel + canon + "}" in s, (f, sel)
