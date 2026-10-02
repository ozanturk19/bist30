"""D-56 ince bağlantı (app.py): /haberler/bildirimler rotası, v1 adreslerinin 301'i, Gündem v2
bağlamı. app.py 3.10+ ister → yerelde (3.9) atlanır, VPS venv'de koşar. Şablonlar ön yüz
dalından (C-72) gelir; burada DictLoader ile en küçük şablon verilir (bağlam anahtarlarını basar)."""
from __future__ import annotations

import os
import sys

import pytest

if sys.version_info < (3, 10):
    pytest.skip("app.py 3.10+ ister — VPS venv'de çalıştır", allow_module_level=True)

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)


@pytest.fixture()
def client(monkeypatch):
    import app as A
    from jinja2 import ChoiceLoader, DictLoader
    tpl = {
        "haberler_bildirimler.html": "B|{{ sekme }}|{{ tur or '' }}|{{ feed.page }}/{{ feed.pages }}|{{ feed.total }}"
                                     "|{{ feed.counts['all'] }}|{{ mini|length }}",
        "haberler.html": "H|{{ sekme or '' }}|{{ 'lead' if gundem_lead else '' }}|{{ gundem_sirket|length "
                         "if gundem_sirket is defined else '' }}|{{ gundem_haber is none }}",
    }
    monkeypatch.setattr(A.app.jinja_env, "loader", ChoiceLoader([DictLoader(tpl), A.app.jinja_env.loader]))
    return A.app.test_client()


def test_bildirimler_route_and_redirects(client):
    r = client.get("/haberler/bildirimler")
    assert r.status_code == 200
    body = r.get_data(as_text=True)
    assert body.startswith("B|bildirimler||1/")
    r = client.get("/haberler/bildirimler?tur=bilanco")
    assert r.status_code == 301 and r.headers["Location"].endswith("/haberler/bildirimler?tur=finansal-rapor")
    r = client.get("/haberler/bildirimler?tur=xx")
    assert r.status_code == 301 and r.headers["Location"].endswith("/haberler/bildirimler")
    r = client.get("/haberler/bildirimler?tur=kredi-notu&sayfa=2")
    assert r.status_code == 200 and "|kredi|" in r.get_data(as_text=True)
    r = client.get("/haberler/bildirimler?tarih=2026-09-29&rutin=1")
    assert r.status_code == 200 and r.headers.get("X-Robots-Tag") == "noindex"


def test_haberler_v1_filter_urls_move_to_bildirimler(client):
    r = client.get("/haberler?tur=temettu")
    assert r.status_code == 301 and r.headers["Location"].endswith("/haberler/bildirimler?tur=temettu")
    r = client.get("/haberler?tur=ozel&sayfa=3")
    assert r.status_code == 301 and r.headers["Location"].endswith("/haberler/bildirimler?tur=ozel-durum&sayfa=5")
    # sirketin bildirim listesi (bildirim.html "Tum T bildirimleri", gundem.html "Bildirimler")
    r = client.get("/haberler?hisse=thyao&sayfa=2")
    assert r.status_code == 301 and r.headers["Location"].endswith("/haberler/bildirimler?hisse=THYAO&sayfa=3")
    r = client.get("/haberler/bildirimler?hisse=THYAO")
    assert r.status_code == 200 and r.headers.get("X-Robots-Tag") == "noindex"
    r = client.get("/haberler/bildirimler?hisse=THYAO&tur=bilanco")
    assert r.status_code == 301 and r.headers["Location"].endswith("/haberler/bildirimler?hisse=THYAO&tur=finansal-rapor")
    r = client.get("/haberler")
    assert r.status_code == 200 and r.get_data(as_text=True).startswith("H|gundem|")


def test_gundem_haber_hook_contract(monkeypatch):
    import app as A
    assert A._gundem_haber_ctx() is None or isinstance(A._gundem_haber_ctx(), dict)
    monkeypatch.setattr(A, "_gundem_haber_payload", lambda: {"baski_label": "2 Ekim 2026 · 08:30", "maddeler": [
        {"id": "g-1", "kategori": "Dünya", "baslik": "B", "ozet": "Ö", "hisseler": [], "kaynaklar": [], "ai": True}]},
        raising=False)
    d = A._gundem_haber_ctx()
    assert d["maddeler"][0]["kategori"] == "Dünya" and d["maddeler"][0]["ai"] is True
    monkeypatch.setattr(A, "_gundem_haber_payload", lambda: 1 / 0, raising=False)
    assert A._gundem_haber_ctx() is None


def test_d57_context_processor_value_reaches_haberler(client, monkeypatch):
    """D-57 dalı `import gundem_haber` + context processor ile verir; /haberler `gundem_haber`i açıkça
    geçirdiği için (Flask açık değeri context processor'un üstüne yazar) D-56 kancası modülü okumalı."""
    import types
    import app as A
    doc = {"baski_label": "2 Ekim 2026 · 08:30", "maddeler": [
        {"id": "g-1", "kategori": "Dünya", "baslik": "B", "ozet": "Ö", "hisseler": [],
         "kaynaklar": [{"ad": "AA", "url": "https://www.aa.com.tr/x"}], "ai": True}]}
    monkeypatch.delattr(A, "_gundem_haber_payload", raising=False)
    monkeypatch.setattr(A, "gundem_haber", types.SimpleNamespace(load_latest=lambda: doc), raising=False)

    def _inject():   # D-57 _inject_gundem_haber benzeri
        return {"gundem_haber": doc}
    procs = A.app.template_context_processors[None]
    procs.append(_inject)
    try:
        body = client.get("/haberler").get_data(as_text=True)
    finally:
        procs.remove(_inject)
    assert body.startswith("H|gundem|") and body.endswith("|False")


def test_sitemap_and_llms_list_bildirimler(client):
    sm = client.get("/sitemap.xml").get_data(as_text=True)
    assert "/haberler/bildirimler</loc>" in sm
    ll = client.get("/llms.txt").get_data(as_text=True)
    assert "https://borsapusula.com/haberler/bildirimler" in ll
