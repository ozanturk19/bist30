"""
Sektör-içi normalizasyon (CPO-1528 Faz 2): temel analiz metriklerini sektör
bağlamında karşılaştırılabilir hale getirir. Flask'tan bağımsız, saf hesaplama
— business_rules.py deseni.

Yöntem: percentile rank (z-score DEĞİL). Türk hisse yfinance verisi sıkça bozuk
oluyor (bkz. app.py _FUND_SANITY) ve küçük sektörler (Telekom 2, Sigorta 4 hisse)
z-score'u dengesizleştirir; percentile aykırı-değere dayanıklı + doğal 0-100
sınırlı + LLM özetinde okunaklı ("sektöründeki hisselerin %78'inden yüksek").
"""

import statistics

# CPO-1528: bir metrik için sektördeki geçerli (None olmayan) veri sayısı bu
# eşiğin altındaysa percentile sektör yerine BIST100-geneli havuza göre
# hesaplanır (CPO'nun kendi teknik kararı, düşük-riskli varsayılan).
MIN_SECTOR_N = 5

# financial_health_score.py'nin kategorilerinde kullandığı tüm metrikler —
# compute_sector_stats() bunlar için median/stdev/n üretir.
METRICS = [
    "pe_ratio", "pb_ratio", "roe", "profit_margin", "gross_margin",
    "ebitda_margin", "fcf_to_sales", "ocf_stability_cv", "net_debt_to_ebitda",
    "current_ratio", "quick_ratio", "ev_to_ebitda", "revenue_growth",
]


def compute_percentile(ticker_value, sector_values):
    """ticker_value'nun sector_values içindeki percentile rank'i (0-100).

    None'lar sector_values'tan filtrelenir. Standart formül:
    (sayı_kucuk_esit / toplam_n) * 100. ticker_value None ise veya havuzda
    hiç geçerli değer yoksa None döner."""
    if ticker_value is None:
        return None
    valid = [v for v in sector_values if v is not None]
    n = len(valid)
    if n == 0:
        return None
    le = sum(1 for v in valid if v <= ticker_value)
    return (le / n) * 100


def metric_pool(stocks_with_fundamentals, metric, sector=None):
    """Bir metrik için geçerli (None olmayan) değer havuzu.

    sector verilirse sadece o sektördeki hisseler, verilmezse BIST100-geneli."""
    return [
        s.get(metric) for s in stocks_with_fundamentals
        if s.get(metric) is not None and (sector is None or s.get("sector") == sector)
    ]


def ticker_metric_percentile(ticker_value, metric, sector, stocks_with_fundamentals):
    """Bir ticker'ın bir metrikteki sektör-içi percentile'ı.

    Küçük sektör eşiği: sektördeki geçerli veri sayısı MIN_SECTOR_N'den azsa
    BIST100-geneli havuza düşer (fallback)."""
    sector_pool = metric_pool(stocks_with_fundamentals, metric, sector)
    pool = sector_pool if len(sector_pool) >= MIN_SECTOR_N else metric_pool(stocks_with_fundamentals, metric)
    return compute_percentile(ticker_value, pool)


def compute_sector_stats(stocks_with_fundamentals):
    """Her sektör × metrik için median/stdev/n üretir.

    stocks_with_fundamentals: her eleman düz dict — 'sector' alanı +
    Faz 1/2 fundamentals metrikleri (None'lar filtrelenir).
    Çıktı: {sector_name: {metric_name: {"median":..., "stdev":..., "n":...}}}
    """
    by_sector = {}
    for s in stocks_with_fundamentals:
        sector = s.get("sector") or "Diğer"
        by_sector.setdefault(sector, []).append(s)

    stats = {}
    for sector, items in by_sector.items():
        stats[sector] = {}
        for metric in METRICS:
            vals = [it.get(metric) for it in items if it.get(metric) is not None]
            n = len(vals)
            if n == 0:
                stats[sector][metric] = {"median": None, "stdev": None, "n": 0}
                continue
            median = statistics.median(vals)
            stdev = statistics.pstdev(vals) if n > 1 else 0.0
            stats[sector][metric] = {"median": median, "stdev": stdev, "n": n}
    return stats
