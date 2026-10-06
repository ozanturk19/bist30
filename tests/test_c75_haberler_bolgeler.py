"""C-75 Haberler tasarım denetimi — /haberler (Gündem) üç ayrı bölge ve /haberler/bildirimler satır
anatomisi. Şablonların yerel Jinja render'ı (Flask yerelde yok; static_v/filtreler saplama). Bağlam
app.py rotalarıyla aynı yoldan kurulur: haber_v2.lead_story / company_cards / feed / clean_gundem_haber,
heatmap.layout, kap_feed.query (fikstür: tests/fixtures/haber_v2, 25.09–01.10 KAP akışı + 01.10 ısı haritası).
Denetim raporu: ops plans/2026-09-23-denetim/haberler-tasarim-denetimi.md."""
import json
import os
import re
import sys

import pytest
from jinja2 import ChainableUndefined, Environment, FileSystemLoader

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
import bulten  # noqa: E402
import haber_v2 as hv  # noqa: E402
import heatmap  # noqa: E402
import kap_feed  # noqa: E402

FX = os.path.join(ROOT, "tests", "fixtures", "haber_v2")
DAY = "2026-10-01"
# Görünür metinde asla: işlem/hedef dili, göreli zaman, "Ücretsiz", yüzdenin yanında TAVAN/TABAN rozeti.
BANNED = re.compile(r"\b(AL|SAT|BEKLE)\b|\b([Bb]ugün|[Dd]ün|[Yy]arın|[Gg]ünün)\b|[Hh]edef|kâr al|[Ss]top\b|"
                    r"Ücretsiz|[Kk]ısmi|\bTAVAN\b|\bTABAN\b")

GH = {"baski": "2026-10-01T19:30:00+03:00", "baski_label": "1 Ekim 2026 · 19:30", "maddeler": [
    {"id": "g1", "kategori": "Türkiye", "baslik": "Eylül enflasyon verisi 5 Ekim'de açıklanacak",
     "ozet": "TÜİK eylül ayı tüketici fiyat endeksini 5 Ekim 10:00'da yayımlayacak; beklenti yıllık −%0,4 düşüş.",
     "hisseler": [], "kaynaklar": [{"ad": "AA", "url": "https://www.aa.com.tr/tr/ekonomi"}], "ai": True,
     "onemli": True},
    {"id": "g2", "kategori": "Şirketler", "baslik": "Otokar yeni ihracat sözleşmesi imzaladı",
     "ozet": "Otokar, askeri araç tedariğine yönelik yeni bir ihracat sözleşmesi imzaladığını açıkladı.",
     "hisseler": ["OTKAR"], "kaynaklar": [{"ad": "Dünya", "url": "https://www.dunya.com/ekonomi"},
                                         {"ad": "TRT Haber", "url": "https://www.trthaber.com/ekonomi"}],
     "ai": True, "onemli": False},
    {"id": "g3", "kategori": "Dünya", "baslik": "ABD'de S&P 500 günü artıda tamamladı",
     "ozet": "S&P 500 endeksi 7.677,16 puana yükseldi.", "hisseler": [],
     "kaynaklar": [{"ad": "Bloomberg HT", "url": "https://www.bloomberght.com/"}], "ai": True, "onemli": False}]}


def _env():
    e = Environment(loader=FileSystemLoader(os.path.join(ROOT, "templates")), autoescape=True,
                    undefined=ChainableUndefined, extensions=["jinja2.ext.do"])
    e.globals.update(static_v=lambda p: "/static/" + p, og_image_url="/og.png", should_track=False,
                     cf_beacon_token="", bp_rules={})
    e.filters.update(tr_price=lambda v: hv.tr_num(float(v), 2) if v is not None else "—",
                     tr_num=lambda v: str(v), signal_label=lambda s: s, signal_age_text=lambda *a, **k: "",
                     signal_age_phrase=lambda *a, **k: "", signal_age_days=lambda *a, **k: 0)
    return e


@pytest.fixture(scope="module")
def data():
    with open(os.path.join(FX, "kap_items_0925_1001.json"), encoding="utf-8") as f:
        items = json.load(f)
    with open(os.path.join(FX, "heatmap_20261001.json"), encoding="utf-8") as f:
        snap = json.load(f)
    return items, snap


def _mini(t, ch=1.25):
    return {"t": t, "name": t, "price": 10.5, "ch": ch, "bp": 57, "st": "y", "stn": "Yatay", "sp": None}


def _gundem_ctx(items, snap, cards=True, gh=True, lead=True):
    groups, tiles = heatmap.layout(snap["rows"])
    ld = hv.lead_story(snap, bulten.isi_haritasi_ozet(snap), [100.0, 101.5, 99.0, 103.2]) if lead else None
    hot = [m["t"] for m in ld["movers"]] if ld else []
    cc = hv.company_cards(items, DAY, {}, n=6, hot_tickers=hot) if cards else []
    res = kap_feed.query(items, page=1, per_page=60)
    days = [{"day": d["day"], "label": d["label"], "total": len(d["items"]), "routine": 0,
             "rows": [dict(kap_feed.public_item(x, {}), mc=_mini(x["ticker"])) for x in d["items"]]}
            for d in kap_feed.group_by_day(res["items"])]
    gd = hv.clean_gundem_haber(GH) if gh else None
    tick = set(hot) | {c["ticker"] for c in cc} | {t for m in (gd or {}).get("maddeler", []) for t in m["hisseler"]}
    return dict(sekme="gundem", gundem=None, gundem_lead=ld, gundem_sirket=cc, gundem_haber=gd,
                mini={t: _mini(t, -2.5 if t == "KUYAS" else 1.25) for t in tick},
                bulten={"tarih": DAY}, heatmap=snap if lead else None, heatmap_groups=groups if lead else [],
                heatmap_tiles=tiles if lead else [], close_label="1 Ekim", feed_days=days, feed_page=1,
                feed_pages=res["pages"], feed_total=res["total"], feed_filter=None, feed_ticker=None,
                feed_counts={}, feed_available=True, coverage=233)


def _render(name, ctx):
    return _env().get_template(name).render(**ctx)


def _visible(html):
    html = re.sub(r"<script\b.*?</script>|<style\b.*?</style>|<head>.*?</head>", " ", html, flags=re.S)
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", html))


def _section(html, sid):
    m = re.search(r'<section class="hv-z[^"]*" id="%s".*?</section>' % sid, html, re.S)
    return m.group(0) if m else ""


def test_three_zones_in_order_with_question_headings(data):
    html = _render("haberler.html", _gundem_ctx(*data))
    pos = [html.find('id="piyasa"'), html.find('id="gundem"'), html.find('id="sirket-bildirimleri"')]
    assert all(p > 0 for p in pos) and pos == sorted(pos)
    for sid, acc in (("piyasa", "hv-z--piyasa"), ("gundem", "hv-z--gundem"), ("sirket-bildirimleri", "hv-z--bildirim")):
        sec = _section(html, sid)
        assert acc in sec                                   # bölge başına tek vurgu sınıfı
        h2 = re.search(r"<h2[^>]*>(.*?)</h2>", sec, re.S).group(1)
        assert h2.strip().endswith("?")                     # GEO: soru başlığı
    assert "1 Ekim&#39;de piyasada ne oldu?" in html
    # eski karışık ızgara ve kategori renk sınıfları yok
    assert "hv-grid" not in html and "hv-c-dunya" not in html and "hv-nc" not in html


def test_market_summary_numbers_and_heatmap(data):
    sec = _section(_render("haberler.html", _gundem_ctx(*data)), "piyasa")
    assert 'class="hv-kv"' in sec and "<dt>BIST100</dt>" in sec and "<dt>Hisseler</dt>" in sec
    assert "Piyasa özeti · 1 Ekim kapanışı" in sec          # "Günün özeti" değil: göreli zaman yok
    assert 'class="hv-tm"' in sec and "Kutu büyüklüğü: piyasa değeri" in sec
    assert 'href="/bulten/2026-10-01"' in sec and 'href="/harita"' in sec
    # yüzde işareti önünde satır kırılmaz (U+2060)
    assert "\u2060%" in sec


def test_news_card_anatomy_fixed_meta_row(data):
    sec = _section(_render("haberler.html", _gundem_ctx(*data)), "gundem")
    arts = re.findall(r'<article class="hv-ni" id="hv-g\d+">(.*?)</article>', sec, re.S)
    assert len(arts) == 3
    for a in arts:
        order = [a.find('class="hv-ni-k"'), a.find("<h3>"), a.find('class="hv-ni-p"'), a.find('class="hv-ni-m"')]
        assert all(p >= 0 for p in order) and order == sorted(order)
        meta = a[a.find('class="hv-ni-m"'):]
        assert "Kaynaklar:" in meta and "Yapay zekâ ile derlendi" in meta   # ikisi de sabit meta satırında
        assert "Kaynaklar:" not in a[:a.find('class="hv-ni-m"')]
        assert '<time datetime="2026-10-01T19:30:00+03:00">19:30</time>' in meta
    assert sec.count('class="hv-hot"') == 1 and "hv-box hv-news odd" in sec   # 3 madde: son madde tam satır
    assert 'href="/hisse/OTKAR"' in sec


def test_filing_preview_rows_grid_and_no_source_labels(data):
    sec = _section(_render("haberler.html", _gundem_ctx(*data)), "sirket-bildirimleri")
    rows = re.findall(r'<article class="hv-br t-(\w+)">(.*?)</article>', sec, re.S)
    assert 5 <= len(rows) <= 8
    for k, r in rows:
        order = [r.find('class="hv-tkc"'), r.find('class="hv-bb"'), r.find('class="hv-ty"'), r.find('class="hv-tim"')]
        assert all(p >= 0 for p in order) and order == sorted(order), k
        assert re.search(r'class="hv-tim" datetime="2026-\d\d-\d\dT[\d:]+">\d{1,2} (Eylül|Ekim) · \d\d:\d\d<', r)
    dts = re.findall(r'class="hv-tim" datetime="([^"]+)"', sec)
    assert dts == sorted(dts, reverse=True)                 # yeniden eskiye
    assert "Kaynak" not in _visible(sec) and "KAP" not in _visible(sec)
    assert 'href="/haberler/bildirimler"' in sec


def test_filing_preview_tops_up_from_feed_when_few_cards(data):
    ctx = _gundem_ctx(*data)
    ctx["gundem_sirket"] = ctx["gundem_sirket"][:2]
    sec = _section(_render("haberler.html", ctx), "sirket-bildirimleri")
    tick = re.findall(r'<a class="hv-tkl" href="/hisse/(\w+)"', sec)
    assert len(tick) == 6 and len(set(tick)) == 6           # 2 kart + 4 akış satırı, hisse tekrarı yok


def test_language_rules_and_jsonld(data):
    html = _render("haberler.html", _gundem_ctx(*data))
    vis = _visible(html)
    assert not BANNED.search(vis), BANNED.search(vis)
    ld = [json.loads(m) for m in re.findall(r'<script type="application/ld\+json">(.*?)</script>', html, re.S)]
    coll = [d for d in ld if d.get("@type") == "CollectionPage"][0]
    items = coll["mainEntity"]["itemListElement"]
    assert coll["mainEntity"]["numberOfItems"] == len(items) == 1 + 3 + 6
    assert items[0]["item"]["url"].endswith("#hv-lead") and items[1]["item"]["url"].endswith("#hv-g1")


def test_empty_context_degrades(data):
    html = _render("haberler.html", _gundem_ctx(*data, cards=False, gh=False, lead=False) | {"feed_days": []})
    assert 'id="piyasa"' not in html and 'id="gundem"' not in html
    assert 'id="sirket-bildirimleri"' in html and 'class="hv-empty"' in html


def test_bildirimler_rows_share_anatomy_and_calm_filters(data):
    items, _ = data
    fd = hv.feed(items, DAY, names={})
    tick = {r["ticker"] for d in fd["days"] for r in d["rows"]}
    html = _render("haberler_bildirimler.html", dict(
        sekme="bildirimler", feed=fd, tur=None, tur_slug=None, types=hv.TYPES, tarih=None, rutin=False,
        mini={t: _mini(t) for t in tick}, feed_available=True, coverage=233, close_label="1 Ekim", hisse=None,
        hisse_name=None))
    assert 'class="hv-mix"' not in html and 'class="hv-mixl"' not in html   # 8 renkli karışım çubuğu kalktı
    assert not re.search(r'class="hv-fch[^"]*"[^>]*>\s*<svg', html)        # filtre çiplerinde simge yok
    rows = re.findall(r'<article class="hv-br t-\w+">(.*?)</article>', html, re.S)
    assert len(rows) == sum(len(d["rows"]) for d in fd["days"])
    assert all('class="hv-tkc"' in r and 'class="hv-tim"' in r for r in rows)
    assert html.count('class="hv-box hv-rows"') == len(fd["days"])
    assert "getBoundingClientRect().bottom" in html and "showActive()" in html
    assert not BANNED.search(_visible(html))


def test_css_contracts():
    with open(os.path.join(ROOT, "static", "css", "haber-sekmeler.css"), encoding="utf-8") as f:
        tabs = f.read()
    with open(os.path.join(ROOT, "static", "css", "pages", "haberler.css"), encoding="utf-8") as f:
        css = f.read()
    # sekme çubuğu site başlığının altına yapışır, çapalar sekme yüksekliğini bilir
    assert ".hv .hv-tabs{position:sticky;top:var(--bp-anchor-header)" in tabs
    assert "--bp-chrome-extra:48px" in tabs
    # 30 günlük çizgiler nötr; yön rengi yalnız yüzdede
    assert ".hv-spk polyline{fill:none;stroke:var(--bp-brand)" in css
    assert ".hv-spk.u polyline" not in css and ".hv-spb.d polygon" not in css
    # satır zamanı ısı haritası sınıfıyla çakışmaz
    assert re.search(r"(^|\n)\.hv-tim\{", css) and ".hv-tm{position:relative" in css
    # kategori/tür gökkuşağı yok
    assert "--hv-pink" not in css and "--hv-teal" not in css and ".hv .t-finansal" not in css
