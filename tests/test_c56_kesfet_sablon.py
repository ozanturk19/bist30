"""C-56 (01.10) — Keşfet orta-uzun vade listeleri şablonu (D-59 bağlamının tüketicisi).

Kilitler:
  1. /kesfet/<liste>: H1 + soru biçimli H2, kural tek cümle + metodoloji bağlantısı, dört liste
     bağlantısı (paylaşılabilir adres, seçili olan aria-current), satır başına hisse bağlantısı.
  2. Satır: şirket · neden · değerleme rozeti (hisse "Fiyatı makul mu?" sözcükleri) · trend rozeti ·
     BP halkası (sayı ve yay aynı değer); hüküm yoksa yalnız "—" (açıklama metni yok).
  3. 15'ten uzun listede satırların hepsi SSR'da basılı (JS kapalıyken tam liste), "Tümünü göster"
     düğmesi gizli başlar; 15 ve altında düğme yok.
  4. Meta: canonical listenin kendi adresi, JSON-LD CollectionPage + ItemList (satır sayısı kadar) +
     BreadcrumbList; tarih "1 Ekim 2026 kapanışı" (göreli zaman yok).
  5. Bağlam yoksa ya da liste boşsa sayfa 500 vermez; dil kuralları (AL/SAT, hedef, gri ifade yok).
  6. metodoloji.html: kesfet_kurallari varsa "Orta-uzun vade listeleri nasıl seçiliyor?" bölümü
     (id kesfet-listeleri) dört kuralla; yoksa bölüm yok.

app.py py3.9'da içe aktarılamaz: jinja2 ile doğrudan render; bağlam D-59 kesfet.view çıktısı
(tests/fixtures/kesfet_view_20261001.json, 01.10 VPS kopyası, satırlar kısaltıldı).
"""
import json
import os
import re
import types

import pytest

jinja2 = pytest.importorskip("jinja2")
markupsafe = pytest.importorskip("markupsafe")

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FX = json.load(open(os.path.join(ROOT, "tests", "fixtures", "kesfet_view_20261001.json"), encoding="utf-8"))

ENV = jinja2.Environment(loader=jinja2.FileSystemLoader(os.path.join(ROOT, "templates")), autoescape=True,
                         undefined=jinja2.ChainableUndefined)
ENV.globals.update(static_v=lambda p: "/static/" + p)
ENV.filters.update(tr_price=str, tr_num=str, signal_label=lambda s: s, signal_age_text=lambda s: "",
                   signal_age_phrase=lambda s: "", signal_age_days=lambda s: 0)


def _render(name="kesfet.html", path="/kesfet/istikrarli-temettu", **ctx):
    req = types.SimpleNamespace(args={}, path=path)
    return ENV.get_template(name).render(request=req, og_image_url="/og-image.png", should_track=False, **ctx)


def _main(html):
    return html[html.index('<main'):html.index('</main>')]


def _ld(html):
    m = re.search(r'<script type="application/ld\+json">(.*?)</script>', html, re.S)
    return json.loads(m.group(1))


def test_baslik_soru_kural_ve_liste_secici():
    v = FX["temettu"]
    html = _render(kesfet=v)
    main = _main(html)
    assert re.search(r'<h1[^>]*>Orta-uzun vade listeleri</h1>', main)
    assert '<h2 class="kf-q da-display" id="kfH">Hangi şirketler istikrarlı temettü ödüyor?</h2>' in main
    assert v["kural"] in main and 'href="/metodoloji#kesfet-listeleri"' in main
    assert "1 Ekim 2026 kapanışı" in main
    tabs = re.findall(r'<a class="kf-tab" href="(/kesfet/[a-z-]+)"( aria-current="page")?>', main)
    assert [t[0] for t in tabs] == ["/kesfet/kaliteli-makul", "/kesfet/istikrarli-temettu",
                                    "/kesfet/borcsuz-buyuyenler", "/kesfet/sektorune-gore-ucuz"]
    assert [bool(t[1]) for t in tabs] == [False, True, False, False]
    for l in v["listeler"]:
        assert ">%s</span><b class=\"kf-tab-n da-num\">%d</b>" % (l["baslik"], l["sayi"]) in main


def test_satir_rozetler_halka_ve_hisse_baglantisi():
    v = FX["temettu"]
    main = _main(_render(kesfet=v))
    rows = re.findall(r'<li><a class="kf-row" href="/hisse/([A-Z0-9]+)">(.*?)</a></li>', main, re.S)
    assert [t for t, _ in rows] == [r["ticker"] for r in v["satirlar"]]
    words = {"ucuz": "Ucuz tarafta", "makul": "Makul", "pahali": "Pahalı tarafta", "karisik": "Karışık"}
    for (tk, body), r in zip(rows, v["satirlar"]):
        assert r["neden"] in body and r["name"] in body
        val = re.search(r'<span class="kf-val kf-val--(\w+)"><span class="sr-only">Değerleme: </span>([^<]*)</span>', body)
        if r["degerleme"]:
            assert val.group(2) == words[r["degerleme"]]
        else:
            assert (val.group(1), val.group(2)) == ("yok", "—")
        kod = {"g": "strong", "y": "flat", "b": "broken"}[r["trend_kod"]]
        assert '<span class="da-signal da-signal--%s"><span class="sr-only">Trend: </span>%s</span>' % (kod, r["trend"]) in body
        assert 'stroke-dasharray="%d 100"' % r["bp"] in body and '<b class="da-ring-num">%d</b>' % r["bp"] in body
    assert any(r["degerleme"] is None for r in v["satirlar"])   # fikstürde hükümsüz satır var (ISMEN, ANHYT)


def test_tumunu_goster_ssr_tam_liste_js_kirpar():
    v = FX["temettu"]
    main = _main(_render(kesfet=v))
    assert main.count('class="kf-row"') == len(v["satirlar"]) == 18
    assert '<button type="button" class="da-btn da-btn--secondary kf-all" id="kfAll" hidden>' in main
    assert "ol.setAttribute('data-clip','15')" in main
    css = open(os.path.join(ROOT, "static", "css", "pages", "kesfet.css"), encoding="utf-8").read()
    assert ".kf-rows[data-clip] > li:nth-child(n+16){display:none}" in css
    short = _main(_render(kesfet=FX["ucuz"], path="/kesfet/sektorune-gore-ucuz"))
    assert short.count('class="kf-row"') == 4 and "kfAll" not in short


def test_meta_canonical_json_ld():
    v = FX["temettu"]
    html = _render(kesfet=v)
    assert '<link rel="canonical" href="https://borsapusula.com/kesfet/istikrarli-temettu">' in html
    assert "<title>İstikrarlı temettü · Orta-uzun vade listeleri | BorsaPusula</title>" in html
    g = {n["@type"]: n for n in _ld(html)["@graph"]}
    assert set(g) == {"CollectionPage", "ItemList", "BreadcrumbList"}
    il = g["ItemList"]
    assert il["name"] == v["soru"] and il["description"] == v["kural"] and il["numberOfItems"] == 18
    assert il["itemListElement"][0] == {"@type": "ListItem", "position": 1,
                                        "url": "https://borsapusula.com/hisse/" + v["satirlar"][0]["ticker"],
                                        "name": v["satirlar"][0]["ticker"] + " · " + v["satirlar"][0]["name"]}
    assert [x["name"] for x in g["BreadcrumbList"]["itemListElement"]] == ["Ana Sayfa", "Keşfet", "İstikrarlı temettü"]
    # kök (/kesfet) varsayılan listeyi gösterir; kanonik adres listenin kendisi
    root = _render(kesfet=FX["ucuz"], kesfet_kok=True, path="/kesfet")
    assert '<link rel="canonical" href="https://borsapusula.com/kesfet/sektorune-gore-ucuz">' in root


def test_bos_ve_baglamsiz_500_vermez():
    empty = dict(FX["ucuz"], satirlar=[], sayi=0, tarih=None)
    main = _main(_render(kesfet=empty))
    assert "Bu listeye giren şirket yok." in main and "kf-row" not in main and "kapanışı" not in main
    bare = _main(_render())
    assert "Orta-uzun vade listeleri" in bare and "kf-tab" not in bare


_YASAK = re.compile(r"\b(AL|SAT|LONG|SHORT)\b|hedef (fiyat|seviye)|\bstop\b|giriş fiyat|kâr al|Ücretsiz|Kısmi|veri tamlığı|"
                    r"Sınırlı veri|hazırlanıyor|\bbugün|\bdün\b|\byarın|Kaynak:")


def _text(html):
    html = re.sub(r"<script.*?</script>|<style.*?</style>", " ", html, flags=re.S)
    return re.sub(r"<[^>]+>", " ", html)


def test_dil_kurallari():
    for v in (FX["temettu"], FX["ucuz"]):
        t = _text(_main(_render(kesfet=v)))
        assert not _YASAK.search(t), _YASAK.search(t)


def test_metodoloji_kesfet_bolumu():
    html = _render("metodoloji.html", path="/metodoloji", kesfet_kurallari=FX["kurallar"])
    assert '<h2 id="kesfet-listeleri">Orta-uzun vade listeleri nasıl seçiliyor?</h2>' in html
    for r in FX["kurallar"]:
        assert '<li><a href="/kesfet/%s"><strong>%s</strong></a>: %s</li>' % (
            r["slug"], r["baslik"], markupsafe.escape(r["kural"])) in html
    assert 'id="kesfet-listeleri"' not in _render("metodoloji.html", path="/metodoloji")
