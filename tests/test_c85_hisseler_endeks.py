"""C-85 (15.10, SEO #10) — /hisseler BIST 30 / BIST 100 bölümleri (C-SEO şablonu, D-SEO bağlamı).

Kilitler:
  1. `hisseler_endeks` varsa ham HTML'de iki H2: "BIST 30 hisseleri hangileri? (<dönem>)" (#bist30) ve
     "BIST 100 hisseleri hangileri?" (#bist100); bölümlerde tam 30 ve 100 hisse bağlantısı, alfabetik.
  2. Başlık ve açıklama dönemi taşır; bağlam yoksa sayfa eskisi gibi (bölüm yok, eski başlık).
  3. Dil: AL/SAT, "Ücretsiz", göreli zaman yok.
app.py py3.9'da içe aktarılamaz: jinja2 ile doğrudan render.
"""
import os
import re

import pytest

jinja2 = pytest.importorskip("jinja2")

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ENV = jinja2.Environment(loader=jinja2.FileSystemLoader(os.path.join(ROOT, "templates")), autoescape=True)
ENV.globals.update(static_v=lambda p: "/static/" + p)
ENV.filters.update(tr_price=str, tr_num=str, signal_label=lambda s: s, signal_age_text=lambda s: "",
                   signal_age_phrase=lambda s: "", signal_age_days=lambda s: 0)

B30 = ["AKBNK", "AEFES", "ASELS", "ASTOR", "BIMAS", "EKGYO", "ENKAI", "EREGL", "FROTO", "GUBRF", "SAHOL", "KRDMD",
       "KCHOL", "MGROS", "PGSUS", "PETKM", "SASA", "TAVHL", "TOASO", "TRMET", "TCELL", "TUPRS", "TRALT", "THYAO",
       "GARAN", "ISCTR", "SISE", "VAKBN", "TTKOM", "YKBNK"]
B100 = B30 + ["X%02d" % i for i in range(70)]


def _render(endeks=True):
    pairs = sorted((t, "Şirket " + t) for t in B100)
    by_letter = {}
    for t, n in pairs:
        by_letter.setdefault(t[0], []).append((t, n))
    ctx = dict(by_sector={"Diğer": pairs}, sectors_sorted=["Diğer"], by_letter=by_letter,
               letters_sorted=sorted(by_letter), total_count=len(pairs), og_image_url="/og.png", should_track=False)
    if endeks:
        ctx["hisseler_endeks"] = {"bist30": B30, "bist100": B100, "donem": "Ekim–Aralık 2026"}
    return ENV.get_template("hisseler.html").render(**ctx)


def _sec(html, sid):
    return re.search(r'<section class="hh-endeks-sec" id="%s".*?</section>' % sid, html, re.S).group(0)


def test_iki_h2_tam_30_ve_100_baglanti():
    html = _render()
    s30, s100 = _sec(html, "bist30"), _sec(html, "bist100")
    assert re.search(r'<h2[^>]*>BIST 30 hisseleri hangileri\? <span class="hh-nw">\(Ekim–Aralık 2026\)</span></h2>', s30)
    assert re.search(r"<h2[^>]*>BIST 100 hisseleri hangileri\?</h2>", s100)
    k30 = re.findall(r'<a class="hh-chip" href="/hisse/([A-Z0-9]+)"', s30)
    k100 = re.findall(r'<a class="hh-chip" href="/hisse/([A-Z0-9]+)"', s100)
    assert k30 == sorted(B30) and len(k30) == 30
    assert k100 == sorted(B100) and len(k100) == 100
    assert 'title="Şirket THYAO"' in s30


def test_baslik_donem_ve_baglamsiz():
    html = _render()
    assert "<title>BIST 30 ve BIST 100 hisseleri (Ekim–Aralık 2026) · 100 şirketin listesi | BorsaPusula</title>" in html
    bare = _render(endeks=False)
    assert "hh-endeks" not in bare and 'id="bist30"' not in bare
    assert "<title>BIST Hisse Listesi — 100 Şirket (BIST100 + ek hisseler) | BorsaPusula</title>" in bare


def test_dil():
    t = re.sub(r"<[^>]+>", " ", _sec(_render(), "bist30") + _sec(_render(), "bist100"))
    assert not re.search(r"\b(AL|SAT)\b|Ücretsiz|\bbugün|\bdün\b|tavsiye", t)
