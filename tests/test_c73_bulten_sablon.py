"""C-73 Akşam Bülteni v2 (O28=A) — /bulten/<gün> ve /bulten/arsiv şablonlarının yerel Jinja
render'ı (Flask yerelde yok; static_v/filtreler saplama). Fikstür tests/fixtures/
bulten_v2_sayfa_20260928.json: 28.09'un gerçek donmuş bülteni (D-56 öncesi + D-56 alanlarıyla
tamamlanmış), aynı günün donmuş ısı haritası, arşiv listesi, rotanın haritadan hesapladığı sektör
özeti (prep/D-56-bulten bulten.isi_haritasi_ozet çıktısı)."""
import html as _h
import json
import os
import re
import sys

import pytest
from jinja2 import ChainableUndefined, Environment, FileSystemLoader

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
import heatmap as hm  # noqa: E402

FX = os.path.join(ROOT, "tests", "fixtures", "bulten_v2_sayfa_20260928.json")
# Sayfada asla: işlem/hedef dili, göreli zaman, gri/çekinceli iç dil, kaynak etiketi.
BANNED = re.compile(r"\b(AL|SAT|BEKLE|LONG|SHORT)\b|\b([Bb]ugün|[Dd]ün|[Yy]arın)\b|[Hh]edef|kâr al|[Ss]top\b|"
                    r"Ücretsiz|[Kk]ısmi|[Ss]ınırlı veri|hazırlanıyor|veri tamlığı|[Kk]aynak:|Kaynaklar:|veri kaynağı|Yahoo|\bKAP\b")


def _env():
    e = Environment(loader=FileSystemLoader(os.path.join(ROOT, "templates")), autoescape=True,
                    undefined=ChainableUndefined)
    e.globals["static_v"] = lambda p: "/static/" + p
    e.filters.update(tr_price=lambda v: str(v), tr_num=lambda v: str(v), signal_label=lambda s: s,
                     signal_age_text=lambda s: "", signal_age_phrase=lambda s: "", signal_age_days=lambda s: 0)
    return e


@pytest.fixture(scope="module")
def fx():
    with open(FX, encoding="utf-8") as f:
        return json.load(f)


def _page(fx, v2=True, **extra):
    req = type("R", (), {"args": {}, "path": "/bulten/2026-09-28"})()
    if v2:
        g, t = hm.layout(fx["heatmap"]["rows"])
        snap = dict(fx["v2"], isi_haritasi_ozet=fx["isi_haritasi_ozet"])
        ctx = dict(bulten=snap, onceki="2026-09-25", sonraki="2026-09-29", gunler=[a["tarih"] for a in fx["arsiv"]][::-1],
                   arsiv=fx["arsiv"], heatmap=fx["heatmap"], heatmap_groups=g, heatmap_tiles=t)
    else:
        ctx = dict(bulten=fx["eski"], onceki="2026-09-25", sonraki="2026-09-29", gunler=["2026-09-25", "2026-09-28", "2026-09-29"])
    ctx.update(extra)
    return _h.unescape(_env().get_template("bulten.html").render(request=req, **ctx))


def _text(html):
    body = html.split("<main", 1)[1].split("</main>", 1)[0]
    body = re.sub(r"<script.*?</script>", " ", body, flags=re.S)
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", body))


def test_baslik_soru_ve_gunun_cumlesi_meta_ve_jsonld(fx):
    html = _page(fx)
    assert "<h1 id=\"blH\">28 Eylül 2026'da borsa nasıl kapandı?</h1>" in html
    story = fx["v2"]["ozet_cumlesi"]
    assert story.startswith("BIST100 %2,38 düşüşle 12.592,76 puanda kapandı, 15 Ocak")
    assert '<meta property="og:description" content="%s">' % story in html
    ld = json.loads(re.search(r'<script type="application/ld\+json">(.*?)</script>', html, re.S).group(1))
    art = [n for n in ld["@graph"] if n["@type"] == "Article"][0]
    assert art["description"] == story and art["headline"] == "28 Eylül 2026'da borsa nasıl kapandı?"
    assert '<b class="dn">%2,38</b>' in html and '<b class="dn">91\'i</b>' in html and '<b class="up">9\'u</b>' in html


def test_sektor_tek_tanim_harita_etiketi_cubuk_degeri(fx):
    html = _page(fx)
    gl = dict(re.findall(r'<div class="hm-g" role="group" aria-label="([^"]+)".*?<div class="hm-gl" aria-hidden="true"><b>[^<]+</b><i class="[a-z]+">([^<]+)</i>', html, re.S))
    sk = dict(re.findall(r'<li class="blv-skr"><span class="nm"><span>([^<]+)</span>.*?<span class="v [a-z]+">([^<]+)</span></li>', html, re.S))
    assert len(sk) == 20 and len(gl) == 20
    assert {k: v for k, v in sk.items() if gl.get(k) != v} == {}
    assert "piyasa değeriyle ağırlıklı ortalama" in html


def test_bolumler_ve_sayilar(fx):
    html = _page(fx)
    assert html.count('class="hm-t ') == 100 and html.count("<rect class=") == 100     # harita + nabız şeridi
    assert html.count('class="blv-mr"') == 10 and html.count('class="blv-dr"') == 10
    assert html.count('class="blv-kr"') == 5
    assert "29 Eylül Salı takvimde ne var?" in html and "Sonraki beş işlem günü" in html
    assert html.count("<time datetime=") == 5
    assert 'href="/harita/2026-09-28">Tam harita' in html and 'href="/bulten/arsiv"' in html
    assert 'rel="prev" href="/bulten/2026-09-25"' in html and 'rel="next" href="/bulten/2026-09-29"' in html
    assert html.count('class="blv-ad"') == 5 and 'aria-current="page"' in html
    assert "İhale bedeli 138 Mn ₺, şirketin 2025 hasılatının <b>%16,1'i</b>" in html


def test_hareketlilerde_tavan_taban_rozeti_yok_durumda_kirmizi_yok(fx):
    html = _page(fx)
    mv = html.split('aria-labelledby="mvH"', 1)[1].split("</section>", 1)[0]
    assert not re.search(r"TAVAN|TABAN|tavan|taban", mv)
    dd = html.split('aria-labelledby="ddH"', 1)[1].split("</section>", 1)[0]
    pills = re.findall(r'class="blv-st ([a-z]+)"', dd)
    assert pills and set(pills) <= {"g", "y", "b"}
    assert not re.search(r'class="(go|to|from) [^"]*dn', dd)


def test_dil_taramasi(fx):
    for html in (_page(fx), _page(fx, v2=False)):
        t = _text(html)
        assert not BANNED.search(t), BANNED.search(t).group(0)


def test_eski_rota_baglami_bolum_gizler_hata_yok(fx):
    """C-73 D-56'dan önce deploy edilirse: harita/arşiv yok, eski json — 500 yok, boş bölüm yok."""
    html = _page(fx, v2=False)
    assert 'aria-labelledby="hmH"' not in html and "/bulten/arsiv" not in html
    assert "28 Eylül 2026'da borsa nasıl kapandı?" in html
    assert 'aria-labelledby="skH"' in html and 'aria-labelledby="ddH"' in html
    assert html.count('class="blv-ad"') == 3
    assert 'src="/static/js/bp-heatmap.js"' in html                      # Paylaş için tek kez
    assert _page(fx).count('src="/static/js/bp-heatmap.js"') == 1


def test_isi_haritasi_parcasi_varsayilan_cikti_degismedi(fx):
    """hm_bare verilmezse kök <section>, başlık ve 'Tüm harita' aynen; bare modda nabız şeridi."""
    g, t = hm.layout(fx["heatmap"]["rows"])
    tpl = _env().get_template("_heatmap.html")
    out = tpl.render(heatmap=fx["heatmap"], heatmap_groups=g, heatmap_tiles=t)
    assert out.lstrip().startswith('<section class="da-section" id="sektorler" aria-labelledby="hmTitle">')
    assert "hm-pulse" not in out and "Tüm harita" in out and 'id="hmTitle"' in out
    bare = tpl.render(heatmap=fx["heatmap"], heatmap_groups=g, heatmap_tiles=t, hm_bare=True, hm_more="/harita/2026-09-28")
    assert bare.lstrip().startswith('<section class="hm-bare" id="sektorler">') and 'id="hmTitle"' not in bare
    assert "Tüm harita" not in bare and 'href="/harita/2026-09-28">Tam harita' in bare
    assert "hm-pulse" in bare and "Paylaş" not in bare
    full = tpl.render(heatmap=fx["heatmap"], heatmap_groups=g, heatmap_tiles=t, hm_full=True, hm_bare=True)
    assert "hm-pulse" not in full                                          # tam sayfada yok sayılır


def test_arsiv_sayfasi(fx):
    req = type("R", (), {"args": {}, "path": "/bulten/arsiv"})()
    html = _h.unescape(_env().get_template("bulten_arsiv.html").render(request=req, arsiv=fx["arsiv"]))
    assert "Ekim 2026'da borsa nasıl kapandı?" in html and "Eylül 2026'da borsa nasıl kapandı?" in html
    for a in fx["arsiv"]:
        assert 'href="/bulten/%s"' % a["tarih"] in html
    ld = json.loads(re.search(r'<script type="application/ld\+json">(.*?)</script>', html, re.S).group(1))
    lst = ld["@graph"][0]["mainEntity"]
    assert lst["numberOfItems"] == len(fx["arsiv"]) and lst["itemListElement"][0]["url"].endswith(fx["arsiv"][0]["tarih"])
    assert not BANNED.search(_text(html))
