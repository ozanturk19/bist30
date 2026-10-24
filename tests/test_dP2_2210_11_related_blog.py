"""D-P2-2210 (11): hisse sayfasındaki 'İlgili blog makaleleri' emekli (canonical_slug'lı)
makaleleri önermemeli — aksi halde kart gereksiz bir 301'e düşer (blog_index'in r95'te
uyguladığı filtre stock_page()'de unutulmuştu)."""
import re

from blog_content import ARTICLES


def _related_blog_for(ticker):
    """app.py stock_page()'deki filtreyle BİREBİR aynı mantık (D-P2-2210 (11) fix)."""
    return [
        a["slug"] for a in ARTICLES
        if not a.get("canonical_slug") and ticker in a.get("related_tickers", [])
    ][:4]


def test_related_blog_excludes_retired_articles():
    retired = {a["slug"] for a in ARTICLES if a.get("canonical_slug")}
    tickers = {t for a in ARTICLES for t in a.get("related_tickers", [])}
    assert tickers, "fixture beklenmedik şekilde boş"
    for ticker in tickers:
        result = _related_blog_for(ticker)
        assert not (set(result) & retired), f"{ticker}: emekli slug sızdı: {result}"


def test_related_blog_stays_nonempty_after_filter():
    # Fix öncesi dolu olan hiçbir ticker, fix sonrası boşa düşmemeli (canonical
    # makale zaten en az aynı related_tickers kapsamını taşıyor, bkz. app.py yorumu).
    retired = {a["slug"] for a in ARTICLES if a.get("canonical_slug")}
    tickers = {t for a in ARTICLES for t in a.get("related_tickers", [])}
    for ticker in tickers:
        before = [a["slug"] for a in ARTICLES if ticker in a.get("related_tickers", [])][:4]
        after = _related_blog_for(ticker)
        if before:
            assert after, f"{ticker}: fix sonrası related_blog boşa düştü"


def test_stock_page_source_filters_canonical_slug(app_function):
    body = app_function("stock_page")
    m = re.search(r"related_blog = \[(.*?)\]\[:4\]", body, re.S)
    assert m, "stock_page() içinde related_blog bloğu bulunamadı"
    assert "not a.get(\"canonical_slug\")" in m.group(1)
