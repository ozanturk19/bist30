"""C-68 (25.09) — ısı haritası paylaşımının şablon tarafı (D-54 sözleşmesinin tüketicisi).

Kilitler:
  1. Paylaşım bağlamı YOKKEN (`heatmap_og_image` / `harita_gun` verilmez: D-54 öncesi)
     ana sayfa ısı haritası bloğunda Paylaş çıkmaz ve üst satır C-29 ile aynıdır.
  2. `heatmap_og_image` VARKEN: tek Paylaş; kalıcı bağlantı /harita/<gün>, "Görseli indir"
     düz <a download>, paylaşım metni görseldeki cümleyle aynı biçimde.
  3. /sektor-harita (hm_full): varsayılan görünümde kalıcı bağlantı, varsayılan dışında
     görünümün adresi (?renk=&donem=); "Geçmiş günler" → /harita.
  4. harita_gun.html: H1, og/twitter meta (1200×630, summary_large_image), canonical,
     JSON-LD (WebPage + ImageObject + BreadcrumbList), önceki/sonraki gün, bağlam yoksa
     boş durum (500 değil); dil kuralları (göreli zaman / kaynak etiketi / AL-SAT yok).
  5. index.html ve sektor_harita.html og:image: heatmap_og_image varsa o, yoksa eskisi.

app.py py3.9'da içe aktarılamaz: jinja2 ile doğrudan render; veri D-42 fikstürü
(tests/fixtures/heatmap_20260923.json) → heatmap.build + heatmap.layout (route ile aynı yardımcılar).
"""
import json
import os
import re
import sys
import types

import pytest

jinja2 = pytest.importorskip("jinja2")

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
import heatmap as hm  # noqa: E402

FX = json.load(open(os.path.join(ROOT, "tests", "fixtures", "heatmap_20260923.json"), encoding="utf-8"))
DAY = FX["asof"][:10]
PERMA = "https://borsapusula.com/harita/" + DAY


def _snap():
    rows = {t: dict(r, bar_date=FX["asof"]) for t, r in FX["rows"].items()}
    snap = hm.build(FX["asof"], FX["members"], FX["official"], rows, FX["fund"], FX["bp"], FX["sectors"],
                    FX["names"], FX["xu100"], "2026-09-23T18:40:12+03:00")
    groups, tiles = hm.layout(snap["rows"])
    return hm.json_safe(snap), groups, tiles


SNAP, GROUPS, TILES = _snap()


def _poss(n):
    u, t = n % 10, (n // 10) % 10
    if n == 0:
        return "ı"
    if u:
        return ["", "i", "si", "ü", "ü", "i", "sı", "si", "i", "u"][u]
    if t:
        return ["", "u", "si", "u", "ı", "si", "ı", "i", "i", "ı"][t]
    return "ü" if (n // 100) % 10 else "i"


def _share_text(s):
    c = s["counts"]
    return "%s · %s kapanışı: %d hissenin %d'%s yükseldi, %d'%s düştü." % (
        s.get("universe") or "BIST100", s["asof_label"], s["n"], c["up"], _poss(c["up"]), c["down"], _poss(c["down"]))


def _env():
    e = jinja2.Environment(loader=jinja2.FileSystemLoader(os.path.join(ROOT, "templates")), autoescape=True,
                           undefined=jinja2.ChainableUndefined)
    e.filters.update(tr_price=lambda v: str(v), tr_num=lambda v: str(v), signal_label=lambda s: s,
                     signal_age_text=lambda s: "", signal_age_phrase=lambda s: "", signal_age_days=lambda s: 0)
    return e


E = _env()
BASE = {"og_image_url": "/og-image.png", "should_track": False, "cf_beacon_token": ""}


def _req(path, **args):
    return types.SimpleNamespace(args=dict(args), path=path)


def _partial(**ctx):
    return E.get_template("_heatmap.html").render(**BASE, heatmap=SNAP, heatmap_groups=GROUPS, heatmap_tiles=TILES, **ctx)


def _day_ctx(**over):
    hg = {"date": DAY, "label": "23 Eylül 2026", "prev": "2026-09-22", "next": "2026-09-24",
          "og_image": "/harita/%s.png" % DAY, "og_image_kare": "/harita/%s-kare.png" % DAY,
          "share_text": _share_text(SNAP)}
    hg.update(over)
    return {"heatmap": SNAP, "heatmap_groups": GROUPS, "heatmap_tiles": TILES, "harita_gun": hg}


def _attr(html, name):
    m = re.search(r'%s="([^"]*)"' % re.escape(name), html)
    return jinja2.utils.markupsafe.Markup(m.group(1)).unescape() if m else None


# ── 1-2: ana sayfa bloğu ──────────────────────────────────────────────────────
def test_home_block_without_share_context_has_no_share_control():
    out = _partial()
    assert "data-hm-share" not in out and "hm-top" not in out and "hm-arc" not in out
    assert '<div class="hm-head">\n      <div class="da-eyebrow">Piyasa haritası</div>\n      <h2 class="hm-title' in out


def test_home_block_with_og_image_has_one_share_control():
    out = _partial(heatmap_og_image="/harita/%s.png" % DAY)
    assert out.count("data-hm-share") == 1 and out.count("<summary") == 1
    assert _attr(out, "data-url") == PERMA
    assert _attr(out, "data-kare") == "/harita/%s-kare.png" % DAY
    assert _attr(out, "data-text") == _share_text(SNAP)
    assert _attr(out, "data-title") == "BIST100 ısı haritası · 23 Eylül 2026"
    assert 'href="%s" data-share-copy>Bağlantıyı kopyala</a>' % PERMA in out
    assert 'href="/harita/%s.png" download="borsapusula-isi-haritasi-%s.png">Görseli indir</a>' % (DAY, DAY) in out
    assert "data-view" not in out and "hm-arc" not in out
    assert out.count('<h2 class="hm-title') == 1


# ── 3: tam sayfa ──────────────────────────────────────────────────────────────
@pytest.mark.parametrize("mode,per,href", [
    ("chg", "d1", PERMA),
    ("bp", "d1", "https://borsapusula.com/sektor-harita?renk=bp"),
    ("chg", "m1", "https://borsapusula.com/sektor-harita?donem=1a"),
    ("tr", "y1", "https://borsapusula.com/sektor-harita?renk=trend&amp;donem=1y"),
])
def test_full_page_share_link_is_view_url_when_not_default(mode, per, href):
    out = _partial(heatmap_og_image="/harita/%s.png" % DAY, hm_full=True, hm_mode=mode, hm_per=per, hm_path="/sektor-harita")
    assert 'href="%s" data-share-copy>' % href in out
    assert _attr(out, "data-url") == PERMA and _attr(out, "data-view") == "https://borsapusula.com/sektor-harita"
    assert '<a class="hm-arc" href="/harita">Geçmiş günler</a>' in out
    assert out.count("data-hm-share") == 1


def test_full_page_without_share_context_is_unchanged():
    out = _partial(hm_full=True, hm_mode="bp", hm_per="d1", hm_path="/sektor-harita")
    assert "data-hm-share" not in out and "hm-arc" not in out and "hm-ctl-top" not in out
    assert '<div class="hm-ctl">' in out


# ── 4: gün sayfası ───────────────────────────────────────────────────────────
def _day(**over):
    return E.get_template("harita_gun.html").render(**BASE, request=_req("/harita/" + DAY), **_day_ctx(**over))


def test_day_page_head_meta_and_jsonld():
    out = _day()
    h1 = re.findall(r"<h1[^>]*>(.*?)</h1>", out, re.S)
    assert len(h1) == 1 and re.sub(r"<[^>]+>|\s+", " ", h1[0]).split() == "BIST100 ısı haritası · 23 Eylül 2026".split()
    assert '<link rel="canonical" href="%s">' % PERMA in out
    img = "https://borsapusula.com/harita/%s.png" % DAY
    for k, v in (("og:image", img), ("og:image:width", "1200"), ("og:image:height", "630"), ("og:url", PERMA)):
        assert '<meta property="%s"' % k in out and re.search(r'property="%s"\s+content="%s"' % (re.escape(k), re.escape(v)), out), k
    assert re.search(r'name="twitter:card"\s+content="summary_large_image"', out)
    assert re.search(r'name="twitter:image"\s+content="%s"' % re.escape(img), out)
    lds = [json.loads(s) for s in re.findall(r'<script type="application/ld\+json">(.*?)</script>', out, re.S)]
    graph = [g for x in lds for g in x.get("@graph", [])]
    types_ = {g["@type"] for g in graph}
    assert {"WebPage", "ImageObject", "BreadcrumbList"} <= types_
    io = next(g for g in graph if g["@type"] == "ImageObject")
    assert io["contentUrl"] == img and io["width"] == 1200 and io["height"] == 630 and io["encodingFormat"] == "image/png"
    wp = next(g for g in graph if g["@type"] == "WebPage")
    assert wp["url"] == PERMA and wp["primaryImageOfPage"]["@id"] == img
    assert "Bu harita nedir?" in out and out.count("data-hm-share") == 1
    assert _attr(out, "data-text") == _share_text(SNAP)


def test_day_page_prev_next_navigation():
    out = _day()
    assert '<a class="hg-pg hg-prev" rel="prev" href="/harita/2026-09-22"><span aria-hidden="true">←</span> 22 Eylül 2026</a>' in out
    assert '<a class="hg-pg hg-next" rel="next" href="/harita/2026-09-24">24 Eylül 2026 <span aria-hidden="true">→</span></a>' in out
    only = _day(prev=None, next=None)
    assert "hg-pager" not in only


def test_day_page_without_context_renders_empty_state():
    out = E.get_template("harita_gun.html").render(**BASE, request=_req("/harita/x"))
    assert "Bu günün haritası yok" in out and "data-hm-share" not in out and "application/ld+json" not in out


def test_day_page_language_rules():
    out = _day()
    main = re.search(r"<main.*?</main>", out, re.S).group(0)
    main = re.sub(r'<script type="application/json".*?</script>', "", main, flags=re.S)
    text = re.sub(r"<[^>]+>", " ", main) + " " + " ".join(re.findall(r'(?:content|data-text|data-title|aria-label)="([^"]*)"', out))
    bad = re.findall(r"\b(bugün|dün|günün|ücretsiz|yahoo|kap|borsa istanbul verisi|al|sat|hedef)\b", text, re.I)
    assert bad == []


# ── 5: og:image geçişi ───────────────────────────────────────────────────────
def _og(html):
    return re.search(r'<meta property="og:image"\s+content="([^"]+)"', html).group(1), \
        re.search(r'<meta name="twitter:image"\s+content="([^"]+)"', html).group(1)


@pytest.mark.parametrize("tpl,path", [("index.html", "/"), ("sektor_harita.html", "/sektor-harita")])
def test_og_image_override(tpl, path):
    ctx = {"heatmap": SNAP, "heatmap_groups": GROUPS, "heatmap_tiles": TILES}
    t = E.get_template(tpl)
    plain = t.render(**BASE, request=_req(path), **ctx)
    assert _og(plain) == ("https://borsapusula.com/og-image.png",) * 2 and "og:image:alt" not in plain
    shared = t.render(**BASE, request=_req(path), heatmap_og_image="/harita/%s.png" % DAY, **ctx)
    assert _og(shared) == ("https://borsapusula.com/harita/%s.png" % DAY,) * 2
    assert 'content="BIST100 ısı haritası · 23 Eylül kapanışı"' in shared


def test_day_page_footer_note_is_dated():
    # Kalıcı sayfa ertesi kapanıştan sonra geçmiş gündür: tarihsiz "son kapanışa aittir" rozeti yanlış olur.
    out = _day()
    foot = re.search(r'<footer class="da-footer">.*?</footer>', out, re.S).group(0)
    assert "Bu sayfadaki değişimler 23 Eylül 2026 kapanışına aittir; sayfa sonradan güncellenmez." in foot
    assert "son kapanış" not in foot and "EOD" not in foot
    empty = E.get_template("harita_gun.html").render(**BASE, request=_req("/harita/x"))
    efoot = re.search(r'<footer class="da-footer">.*?</footer>', empty, re.S).group(0)
    assert "da-footer-note" not in efoot and "son kapanış" not in efoot
