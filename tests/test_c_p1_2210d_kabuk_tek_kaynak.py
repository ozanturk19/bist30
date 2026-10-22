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
