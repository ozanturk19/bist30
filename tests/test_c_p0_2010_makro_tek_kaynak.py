"""C-P0-2010 (20.10, Ozan 2. kez) — üst makro şerit TEK KAYNAK, TEK GÖRÜNÜM, her sayfada sabit.

Canlı denetim 20.10: şerit 13/25 sayfada yoktu (13 şablon ayrı ayrı include ediyordu, kalanlar unutmuştu),
3 sayfada renksizdi (.mc-pos/.mc-neg yalnız 9 sayfa CSS'inde), 375×667'de sabit değildi (portre ≤700 kuralı).
Kilitler:
  1. `_macro_bar.html`'i YALNIZ `_header.html` include eder (header'ı olan her sayfa şeridi otomatik alır).
  2. Ana sayfa varyantı yok: `macro_home` / `macro-bar--home` hiçbir yerde geçmez; "Piyasalar" etiketi şeritte.
  3. Şerit stilleri yalnız static/css/shared.css'te: başka CSS dosyası ya da şablon <style> bloğu
     .mc-pos/.mc-neg/.mc-neu/.macro-bar/#macroBar/.macro-item (ve şeridin diğer parçaları) için kural yazmaz.
  4. Şeridi yapışkan olmaktan çıkaran tek kural yatay ≤500 px istisnası (portre ≤700 kuralı geri gelmez).
  5. Header'ı include eden her şablon şeridi dolduran bp-search.js'i yükler.
  6. Render: _header.html ve bir hata sayfası şeridi tam 1 kez, header'dan ÖNCE basar.
Canlı ölçüm: tools/live/makro-denetim.mjs (çıkış kodu).
"""
import os
import re

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TPL = os.path.join(ROOT, "templates")
CSS_DIRS = [os.path.join(ROOT, "static", "css"), os.path.join(ROOT, "static", "css", "pages")]
SHARED = os.path.join(ROOT, "static", "css", "shared.css")

INCLUDE_RE = re.compile(r"""\{%-?\s*(?:include|import|from)\s+['"]_macro_bar\.html['"]""")
HEADER_INCLUDE_RE = re.compile(r"""\{%-?\s*include\s+['"]_header\.html['"]""")
# Şeridin parçaları: bunlar için kural yalnız shared.css'te
MACRO_SEL_RE = re.compile(r"\.mc-(?:pos|neg|neu|flash)|\.macro-(?:bar|item|track|live|pause-btn|meta|stale-badge)|#macroBar|#macroTrack")


def _templates():
    for f in sorted(os.listdir(TPL)):
        if f.endswith(".html"):
            yield f, open(os.path.join(TPL, f), encoding="utf-8").read()


def _css_files():
    for d in CSS_DIRS:
        for f in sorted(os.listdir(d)):
            if f.endswith(".css"):
                p = os.path.join(d, f)
                yield p, open(p, encoding="utf-8").read()


def _no_comments(css):
    return re.sub(r"/\*.*?\*/", " ", css, flags=re.S)


def _selectors(css):
    """{…} bloklarının seçici metinleri (@media başlıkları dahil; onlar şerit seçicisi taşımaz)."""
    return [m.group(1).strip() for m in re.finditer(r"([^{}]+)\{", _no_comments(css))]


def test_yalniz_header_serit_include_eder():
    includers = [f for f, src in _templates() if INCLUDE_RE.search(src)]
    assert includers == ["_header.html"], f"_macro_bar.html'i include eden şablonlar: {includers}"
    src = open(os.path.join(TPL, "_header.html"), encoding="utf-8").read()
    assert len(INCLUDE_RE.findall(src)) == 1
    assert src.index("_macro_bar.html'") < src.index("<header>"), "şerit header'ın ÜSTÜNDE olmalı"


def test_ana_sayfa_varyanti_yok():
    yasak = ("macro" + "_home", "macro-bar" + "--home")
    hits = []
    for base in ("templates", "static", "tools", "tests"):
        for dp, _dn, fn in os.walk(os.path.join(ROOT, base)):
            for f in fn:
                if not f.endswith((".html", ".css", ".js", ".mjs", ".py", ".json")):
                    continue
                p = os.path.join(dp, f)
                if os.path.abspath(p) == os.path.abspath(__file__):
                    continue
                src = open(p, encoding="utf-8", errors="ignore").read()
                hits += [(os.path.relpath(p, ROOT), y) for y in yasak if y in src]
    for f in os.listdir(ROOT):
        if f.endswith(".py"):
            src = open(os.path.join(ROOT, f), encoding="utf-8", errors="ignore").read()
            hits += [(f, y) for y in yasak if y in src]
    assert not hits, f"ana sayfa varyantı kalıntısı: {hits}"
    bar = open(os.path.join(TPL, "_macro_bar.html"), encoding="utf-8").read()
    assert re.search(r'class="macro-live"><span class="macro-live-dot"></span>Piyasalar</div>', bar)
    assert "{% if" not in bar, "şerit koşulsuz tek görünüm olmalı"


def test_serit_stilleri_yalniz_shared_css():
    ihlal = []
    for p, css in _css_files():
        if p == SHARED:
            continue
        for sel in _selectors(css):
            if MACRO_SEL_RE.search(sel):
                ihlal.append((os.path.relpath(p, ROOT), sel[-80:]))
    for f, src in _templates():
        for st in re.findall(r"<style[^>]*>(.*?)</style>", src, flags=re.S):
            for sel in _selectors(st):
                if MACRO_SEL_RE.search(sel):
                    ihlal.append(("templates/" + f, sel[-80:]))
    assert not ihlal, f"şerit kuralı shared.css dışında: {ihlal}"
    shared = _selectors(open(SHARED, encoding="utf-8").read())
    for need in (".mc-pos", ".mc-neg", ".mc-neu", ".macro-bar", ".macro-item", ".macro-live", ".mc-flash-up"):
        assert any(need in s for s in shared), f"shared.css'te {need} kuralı yok"


def test_mc_renkleri_token():
    css = _no_comments(open(SHARED, encoding="utf-8").read())
    assert re.search(r"\.mc-pos\{color:var\(--bp-up\)\}", css)
    assert re.search(r"\.mc-neg\{color:var\(--bp-down\)\}", css)
    assert re.search(r"\.mc-neu\{color:var\(--bp-text-3\)\}", css)


def test_serit_yalniz_yatay_kisa_ekranda_yapismaz():
    css = _no_comments(open(SHARED, encoding="utf-8").read())
    m = re.search(r"@media \(orientation: landscape\) and \(max-height: 500px\) \{", css)
    assert m, "yatay ≤500 px istisnası shared.css'te olmalı"
    depth, i = 1, m.end()
    while depth:
        depth += {"{": 1, "}": -1}.get(css[i], 0)
        i += 1
    assert re.search(r"#macroBar, \.macro-bar, header \{ position: relative !important; \}", css[m.end():i])
    rest = css[:m.start()] + css[i:]
    assert "orientation: portrait" not in rest, "portre kısa ekran kuralı geri geldi (C-P0-2010)"
    for blk in re.finditer(r"([^{}]+)\{([^{}]*)\}", rest):
        hedef = any(x.strip() in (".macro-bar", "#macroBar") for x in blk.group(1).split(","))
        assert not (hedef and re.search(r"position\s*:\s*(relative|static)", blk.group(2))), \
            f"şerit yapışkanlığı kaldırılıyor: {blk.group(1).strip()[-80:]}"
    bar = re.search(r"\.macro-bar\{([^}]*)\}", css)
    assert bar and "position:sticky" in bar.group(1) and "top:0" in bar.group(1)


def test_header_olan_her_sablon_bp_search_yukler():
    eksik = [f for f, src in _templates()
             if f != "_header.html" and HEADER_INCLUDE_RE.search(src) and not re.search(r"static_v\('bp-search\.js'\)", src)]
    assert not eksik, f"header var ama bp-search.js yok (şerit boş kalır): {eksik}"


def test_render_serit_bir_kez_header_ustunde():
    jinja2 = pytest.importorskip("jinja2")
    env = jinja2.Environment(loader=jinja2.FileSystemLoader(TPL), autoescape=True)
    env.globals.update(static_v=lambda p: "/static/" + p)
    env.filters.update(tr_price=str, tr_num=str, signal_label=lambda v: v, signal_age_text=lambda v: "",
                       signal_age_phrase=lambda v: "", signal_age_days=lambda v: 0)
    for name in ("_header.html", "404.html"):
        html = env.get_template(name).render()
        assert html.count('id="macroBar"') == 1, name
        assert html.index('id="macroBar"') < html.index("<header>"), name
        assert ">Piyasalar</div>" in html, name
