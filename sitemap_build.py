"""D-63: site haritası dizini (sitemapindex) + 5 alt harita — saf yardımcılar.

Google site haritasını hiç almamıştı (SEO denetimi 15.10): tek 755 KB dosya, 4.767 adresin %76'sı
bildirim sayfası, 246 adreste lastmod = takvim günü. Yeni düzen:

    /sitemap.xml            -> <sitemapindex>, 5 <sitemap>
    /sitemap-sayfalar.xml   merkez sayfalar (~20)        lastmod: son kapanış günü / şablon tarihi
    /sitemap-hisseler.xml   /hisse/<T> (233)             lastmod: son kapanış günü
    /sitemap-finansal.xml   /hisse/<T>/<tablo> (696)     lastmod: son raporun yayın günü
    /sitemap-gunluk.xml     /bulten/<g> + /harita/<g>    lastmod: sayfanın kendi günü (son 90 takvim günü)
    /sitemap-blog.xml       /blog/<slug> (~90)           lastmod: makalenin dateModified'ı

Bildirim sayfaları, /ozet/<g> ve noindex sayfalar (/takip) haritada yok. Girdileri app.py toplar
(`_sitemap_alt_girdileri`); bu modül Flask/app.py'yi import etmez, yerelde test edilir.
"""
from datetime import date, timedelta
from xml.sax.saxutils import escape

BASE = "https://borsapusula.com"
ALT_HARITALAR = ("sayfalar", "hisseler", "finansal", "gunluk", "blog")
GUNLUK_GUN = 90   # günlük sayfalar: son 90 takvim günü (~63 işlem günü × 2 sayfa)


def _iso(d):
    return d.isoformat() if hasattr(d, "isoformat") else str(d)[:10]


def kapanis_gunu(heatmap_gunleri, beklenen):
    """Son kapanış günü (ISO). Kaynak: donmuş ısı haritasının son günü (kapanıştan sonra yazılır);
    beklenen veri gününü (lib.trading_calendar.expected_data_date) aşamaz. Seans içinde ikisi de
    önceki işlem günüdür. Isı haritası hiç yoksa beklenen veri günü."""
    b = _iso(beklenen)
    if heatmap_gunleri:
        return min(heatmap_gunleri[-1], b)
    return b


def son_gunler(gunler, bugun, n=GUNLUK_GUN):
    """Artan ISO gün listesinden son `n` takvim gününe düşenler, yeniden eskiye."""
    b = bugun if isinstance(bugun, date) else date.fromisoformat(str(bugun)[:10])
    sinir = (b - timedelta(days=n)).isoformat()
    return [g for g in reversed(gunler) if sinir < g <= b.isoformat()]


def blog_lastmod(makale):
    """Makale sayfasının JSON-LD dateModified'ı ile aynı kural (blog_article.html):
    `updated` varsa o, yoksa `date`."""
    v = makale.get("updated") or makale.get("date")
    return str(v)[:10] if v else None


def en_son(girdiler):
    lm = [g["lastmod"] for g in girdiler if g.get("lastmod")]
    return max(lm) if lm else None


def urlset(girdiler, base=BASE):
    """[{loc, lastmod?}] -> <urlset>. lastmod yoksa yazılmaz (uydurma tarih yok)."""
    out = ['<?xml version="1.0" encoding="UTF-8"?>',
           '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
    for g in girdiler:
        lm = "<lastmod>%s</lastmod>" % g["lastmod"] if g.get("lastmod") else ""
        out.append("  <url><loc>%s</loc>%s</url>" % (escape(base + g["loc"]), lm))
    out.append("</urlset>")
    return "\n".join(out)


def sitemapindex(alt, base=BASE):
    """{ad: [girdi]} -> <sitemapindex>; her alt haritanın lastmod'u kendi girdilerinin en yenisi."""
    out = ['<?xml version="1.0" encoding="UTF-8"?>',
           '<sitemapindex xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
    for ad in ALT_HARITALAR:
        lm = en_son(alt.get(ad) or [])
        out.append("  <sitemap><loc>%s/sitemap-%s.xml</loc>%s</sitemap>"
                   % (base, ad, "<lastmod>%s</lastmod>" % lm if lm else ""))
    out.append("</sitemapindex>")
    return "\n".join(out)
