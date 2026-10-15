"""D-63: site haritası dizini (sitemapindex) + 5 alt harita.

Yerel (py3.9): sitemap_build.py saf yardımcıları + app.py sitemap bölgesinin kaynak taraması.
VPS (py3.10+): /sitemap.xml ve /sitemap-<ad>.xml uçları Flask test istemcisiyle.
"""
import os
import re
import sys
from datetime import date, datetime

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
import sitemap_build as sb  # noqa: E402
from lib import trading_calendar as tc  # noqa: E402

PY310 = pytest.mark.skipif(sys.version_info < (3, 10), reason="app.py 3.10+ ister")


def test_kapanis_gunu_seans_icinde_onceki_islem_gunu():
    # 15.10.2026 Perşembe 11:00 TR (seans içi): beklenen veri günü 14.10, ısı haritası da 14.10'da.
    beklenen = tc.expected_data_date(datetime(2026, 10, 15, 11, 0, tzinfo=tc._TZ_TR))
    assert beklenen == date(2026, 10, 14)
    assert sb.kapanis_gunu(["2026-10-13", "2026-10-14"], beklenen) == "2026-10-14"
    # Pazartesi seans içi: önceki işlem günü Cuma
    assert tc.expected_data_date(datetime(2026, 10, 12, 11, 0, tzinfo=tc._TZ_TR)) == date(2026, 10, 9)
    # kapanıştan sonra (18:45) bugünün görüntüsü dondu
    beklenen = tc.expected_data_date(datetime(2026, 10, 15, 18, 45, tzinfo=tc._TZ_TR))
    assert sb.kapanis_gunu(["2026-10-14", "2026-10-15"], beklenen) == "2026-10-15"
    # görüntü henüz donmadıysa ısı haritasının son günü (gerçek veri günü) kalır
    assert sb.kapanis_gunu(["2026-10-14"], beklenen) == "2026-10-14"
    # ısı haritası beklenen günü aşamaz; hiç yoksa beklenen gün
    assert sb.kapanis_gunu(["2026-10-16"], date(2026, 10, 15)) == "2026-10-15"
    assert sb.kapanis_gunu([], date(2026, 10, 14)) == "2026-10-14"


def test_son_gunler_90_takvim_gunu_yeniden_eskiye():
    gunler = ["2026-07-17", "2026-07-18", "2026-10-13", "2026-10-14"]
    # (15.10 − 90 gün, 15.10] = 18.07–15.10
    assert sb.son_gunler(gunler, date(2026, 10, 15)) == ["2026-10-14", "2026-10-13", "2026-07-18"]
    assert sb.son_gunler(gunler, date(2026, 10, 13), n=1) == ["2026-10-13"]
    assert sb.son_gunler([], date(2026, 10, 15)) == []


def test_blog_lastmod_json_ld_datemodified_ile_ayni():
    assert sb.blog_lastmod({"date": "2026-05-01"}) == "2026-05-01"
    assert sb.blog_lastmod({"date": "2026-05-01", "updated": "2026-10-02"}) == "2026-10-02"
    assert sb.blog_lastmod({}) is None


def test_urlset_ve_dizin():
    g = [{"loc": "/hisse/THYAO", "lastmod": "2026-10-14"}, {"loc": "/a&b", "lastmod": None}]
    x = sb.urlset(g)
    assert x.startswith('<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">')
    assert "<url><loc>https://borsapusula.com/hisse/THYAO</loc><lastmod>2026-10-14</lastmod></url>" in x
    assert "<url><loc>https://borsapusula.com/a&amp;b</loc></url>" in x          # uydurma lastmod yok
    alt = {"sayfalar": [{"loc": "/", "lastmod": "2026-10-14"}, {"loc": "/yasal", "lastmod": "2026-09-30"}],
           "hisseler": [], "finansal": [{"loc": "/f", "lastmod": None}], "blog": [{"loc": "/b", "lastmod": "2026-10-02"}]}
    idx = sb.sitemapindex(alt)
    assert "<sitemapindex" in idx and "<urlset" not in idx
    assert re.findall(r"<loc>([^<]+)</loc>", idx) == [
        "https://borsapusula.com/sitemap-%s.xml" % a for a in ("sayfalar", "hisseler", "finansal", "gunluk", "blog")]
    assert "<sitemap><loc>https://borsapusula.com/sitemap-sayfalar.xml</loc><lastmod>2026-10-14</lastmod></sitemap>" in idx
    assert "<sitemap><loc>https://borsapusula.com/sitemap-hisseler.xml</loc></sitemap>" in idx


def _sitemap_bolgesi():
    src = open(os.path.join(ROOT, "app.py"), encoding="utf-8").read()
    m = re.search(r'@app\.route\("/sitemap\.xml"\)(.*?)\n@app\.route\("/robots\.txt"\)', src, re.S)
    assert m, "sitemap bölgesi bulunamadı"
    return m.group(1)


def test_app_sitemap_kaynagi_bildirim_ozet_takip_yok():
    src = _sitemap_bolgesi()
    assert "/bildirim/" not in src and "/ozet/" not in src and '"/takip"' not in src
    assert "changefreq" not in src and "priority" not in src        # Google ikisini de yok sayar
    assert '@app.route("/sitemap-<any(sayfalar, hisseler, finansal, gunluk, blog):ad>.xml")' in src
    # takvim günü (today) lastmod kaynağı değil: tarih yalnız günlük pencere hesabında
    assert src.count("datetime.now(") == 1 and "_bugun = datetime.now(_TZ_TR).date()" in src


@PY310
def test_app_dizin_ve_alt_haritalar(monkeypatch, tmp_path):
    import app
    hm = tmp_path / "heatmap"
    hm.mkdir()
    for d in ("2026-10-13", "2026-10-14"):
        (hm / (d + ".json")).write_text("{}", encoding="utf-8")
    monkeypatch.setattr(app, "_HEATMAP_DIR", str(hm))
    monkeypatch.setattr(app, "_expected_data_date", lambda: date(2026, 10, 14))   # 15.10 seans içi
    monkeypatch.setattr(app, "_sitemap_cache", {})
    c = app.app.test_client()
    r = c.get("/sitemap.xml")
    assert r.status_code == 200 and r.mimetype == "application/xml"
    idx = r.get_data(as_text=True)
    assert re.findall(r"<loc>([^<]+)</loc>", idx) == [
        "https://borsapusula.com/sitemap-%s.xml" % a for a in sb.ALT_HARITALAR]
    hepsi = []
    for a in sb.ALT_HARITALAR:
        r = c.get("/sitemap-%s.xml" % a)
        assert r.status_code == 200 and r.mimetype == "application/xml", a
        hepsi += re.findall(r"<loc>([^<]+)</loc>", r.get_data(as_text=True))
    assert len(hepsi) == len(set(hepsi))
    assert not [u for u in hepsi if "/bildirim/" in u or "/ozet/" in u or u.endswith("/takip")]
    hisse = c.get("/sitemap-hisseler.xml").get_data(as_text=True)
    assert hisse.count("<url>") == app.BIST_STOCK_COUNT
    assert "<loc>https://borsapusula.com/hisse/THYAO</loc><lastmod>2026-10-14</lastmod>" in hisse
    assert "/hisse/XU030<" not in hisse and "/hisse/XU100<" not in hisse
    sayfa = c.get("/sitemap-sayfalar.xml").get_data(as_text=True)
    assert "<loc>https://borsapusula.com/</loc><lastmod>2026-10-14</lastmod>" in sayfa
    assert c.get("/sitemap-yok.xml").status_code == 404
