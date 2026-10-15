"""D-64: metni olmayan bildirim sayfası `noindex, follow`; gri cümle ("henüz işlenmedi") yerine
başlık, tür, tarih ve bildirimin KAP sayfası. Metinli bildirim dizinlenebilir kalır.

Yerel (py3.9): bildirim.html'in Jinja render'ı (bağlam _bildirim_payload ile aynı alanlar) +
app.py kaynağı. VPS (py3.10+): /hisse/<T>/bildirim/<no> Flask test istemcisiyle.
"""
import json
import os
import re
import sys

import pytest
from jinja2 import ChainableUndefined, Environment, FileSystemLoader

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
import kap_feed  # noqa: E402

PY310 = pytest.mark.skipif(sys.version_info < (3, 10), reason="app.py 3.10+ ister")
NOINDEX = '<meta name="robots" content="noindex, follow">'
IT = {"id": 1671025, "ticker": "ANELE", "tickers": ["ANELE"], "class": "Özel durum",
      "subject": "Özel Durum Açıklaması (Genel)", "title": "Lusail Plaza Towers (Plot 3&4) projesi hakkında",
      "ts": "2026-10-01T19:54:53", "rutin": False, "onem": None}


def _env():
    e = Environment(loader=FileSystemLoader(os.path.join(ROOT, "templates")), autoescape=True,
                    undefined=ChainableUndefined, extensions=["jinja2.ext.do"])
    e.globals.update(static_v=lambda p: "/static/" + p, og_image_url="/og.png", should_track=False,
                     cf_beacon_token="", bp_rules={})
    e.filters.update(tr_price=lambda v: str(v), tr_num=lambda v: str(v), signal_label=lambda s: s,
                     signal_age_text=lambda *a, **k: "", signal_age_phrase=lambda *a, **k: "",
                     signal_age_days=lambda *a, **k: 0)
    return e


def _b(doc):
    pub = kap_feed.public_item(IT, {"ANELE": "Anel Elektrik"})
    pub["summary"] = kap_feed.summary_sentence(IT, "Anel Elektrik", None)
    return {"item": pub, "headline": "Anel Elektrik: " + IT["title"], "date_long": kap_feed.date_long(IT["ts"]),
            "day_label": kap_feed.day_label(IT["ts"]),
            "text": {"fields": doc.get("fields") or [], "text": doc.get("text") or "",
                     "lines": doc.get("lines") or [], "resp": doc.get("resp")},
            "has_text": bool(doc.get("text") or doc.get("lines") or doc.get("fields")),
            "ekler": [], "similar": []}


def _render(doc):
    mc = {"t": "ANELE", "name": "Anel Elektrik", "price": 10.5, "ch": 1.2, "bp": 50, "st": "y", "stn": "Yatay"}
    return _env().get_template("bildirim.html").render(
        b=_b(doc), mc=mc, canonical="https://borsapusula.com/hisse/ANELE/bildirim/1671025",
        close_label="1 Ekim", kap_url=kap_feed.KAP_PAGE_URL % IT["id"], request=None)


def test_metinsiz_noindex_kunye_ve_kap_baglantisi():
    for doc in ({}, {"resp": "Sorumluluk beyanı"}):
        html = _render(doc)
        head, body = html.split("</head>", 1)
        assert NOINDEX in head
        assert "henüz işlenmedi" not in html
        main = body[body.index("<main"):body.index("</main>")]
        assert "<h2 id=\"hbKnH\">Bildirim bilgileri</h2>" in main
        assert "<dt>Başlık</dt><dd>Lusail Plaza Towers (Plot 3&amp;4) projesi hakkında</dd>" in main
        assert "<dt>Tür</dt><dd>Özel Durum Açıklaması (Genel)</dd>" in main
        assert '<time datetime="2026-10-01T19:54:53">1 Ekim 2026 · 19:54</time>' in main
        assert '<a class="hb-all" href="https://www.kap.org.tr/tr/Bildirim/1671025">' in main
        assert "Bildirimin tam metni KAP'ta ↗" in main
        assert "<details" not in main          # boş tam metin kutusu yok
        assert 'target="_blank"' not in main   # aynı sekme (K-AW yeni sekme kanonu dışı)


def test_metinli_dizinlenebilir_kap_baglantisi_yok():
    for doc in ({"text": "Şirketimiz ihaleyi kazanmıştır."}, {"lines": ["Satır 1"]},
                {"fields": [["Konu", "İhale"]]}):
        html = _render(doc)
        head, body = html.split("</head>", 1)
        assert 'name="robots"' not in head
        assert '<link rel="canonical" href="https://borsapusula.com/hisse/ANELE/bildirim/1671025">' in head
        main = body[body.index("<main"):body.index("</main>")]
        assert "Bildirimin tam metni</summary>" in main and "kap.org.tr" not in main


def test_app_kaynagi_metin_tanimi_ve_kap_baglami():
    src = open(os.path.join(ROOT, "app.py"), encoding="utf-8").read()
    assert '"has_text": bool(doc.get("text") or doc.get("lines") or doc.get("fields")),' in src
    m = re.search(r"def bildirim_page\(ticker, idx\):(.*?)\n\n\n", src, re.S)
    assert m and 'kap_url=kap_feed.KAP_PAGE_URL % it["id"]' in m.group(1)
    p = re.search(r"def _bildirim_payload\(idx\):(.*?)\n\n\n", src, re.S).group(1)
    assert "kap.org.tr" not in p and "KAP_PAGE_URL" not in p     # API yükünde dış bağlantı yok (D-45)


@PY310
def test_app_bildirim_sayfasi(tmp_path, monkeypatch):
    import app as appmod
    with open(os.path.join(ROOT, "tests", "fixtures", "kap_feed", "kap_liste_ornek.json"), encoding="utf-8") as f:
        rows = json.load(f)
    uni = {"AHGAZ", "ASTOR", "EKGYO", "FORTE", "THYAO", "ULKER", "AKCNS", "LINK", "GARAN", "ESCOM", "MIATK", "ORGE"}
    st = kap_feed.Store(str(tmp_path / "kap_feed"))
    st.merge([x for x in (kap_feed.normalize(r, uni) for r in rows) if x])
    st.save_doc(1666965, {"text": "Bildirimin gövdesi."})
    monkeypatch.setattr(appmod, "_KAP_STORE", st)
    c = appmod.app.test_client()
    if not appmod._tpl_ready("bildirim.html"):
        pytest.skip("bildirim.html yok")
    metinli = c.get("/hisse/ASTOR/bildirim/1666965").get_data(as_text=True)
    assert NOINDEX not in metinli and "kap.org.tr" not in metinli.split("<main", 1)[1]
    metinsiz_id = next(x["id"] for x in st.all_items() if x["id"] != 1666965 and x["ticker"] in uni)
    t = st.get(metinsiz_id)["ticker"]
    r = c.get("/hisse/%s/bildirim/%d" % (t, metinsiz_id))
    html = r.get_data(as_text=True)
    assert r.status_code == 200 and NOINDEX in html and "henüz işlenmedi" not in html
    assert "https://www.kap.org.tr/tr/Bildirim/%d" % metinsiz_id in html
    assert "kap.org.tr" not in c.get("/api/bildirim/%d" % metinsiz_id).get_data(as_text=True)
