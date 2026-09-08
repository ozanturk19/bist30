"""
Temel Analiz Skoru + BorsaPusula Kompozit Skoru (CPO-1528 Faz 2). Flask'tan
bağımsız, saf hesaplama — business_rules.py / sector_stats.py deseni.

Kategori → metrik eşlemesi (her kategori kendi içinde EŞİT AĞIRLIKLI ortalama):
  Kârlılık (%30):            profit_margin, roe, gross_margin, ebitda_margin
  Nakit Akışı (%30):         fcf_to_sales, ocf_positive_quarters (4 üzerinden),
                             ocf_stability_cv (düşük=iyi, TERS)
  Kaldıraç (%25):            net_debt_to_ebitda (düşük=iyi, TERS),
                             current_ratio, quick_ratio
  Değerleme/Büyüme (%15):    pe_ratio (TERS), pb_ratio (TERS),
                             ev_to_ebitda (TERS), revenue_growth

TERS metrikler için percentile'ı (100 - percentile) olarak kullanılır — düşük
ham değer yüksek skor demek (ör. düşük borç iyi).

Eksik metrik: kategori skoru kalan metriklerin ortalaması (eksiği 50 ile
doldurmuyoruz — yanıltıcı olur). Kategori tamamen boşsa üst-seviye ağırlıklar
kalan kategoriler arasında yeniden dağıtılır; sonuçla birlikte
`data_completeness` (0-1 arası, gerçekte veri bulunan metrik oranı) taşınır.

Bantlar: 0-49 kırmızı, 50-69 sarı, 70-100 yeşil (Site Contract, sabit).
"""

import sector_stats

# metric adı -> (ters mi, ocf_positive_quarters gibi özel doğrudan-ölçek mi)
CATEGORIES = {
    "karlilik": {
        "weight": 30,
        "metrics": [
            ("profit_margin", False),
            ("roe", False),
            ("gross_margin", False),
            ("ebitda_margin", False),
        ],
    },
    "nakit_akisi": {
        "weight": 30,
        "metrics": [
            ("fcf_to_sales", False),
            ("ocf_positive_quarters", False),  # özel doğrudan-ölçek, bkz. _metric_score
            ("ocf_stability_cv", True),
        ],
    },
    "kaldirac": {
        "weight": 25,
        "metrics": [
            ("net_debt_to_ebitda", True),
            ("current_ratio", False),
            ("quick_ratio", False),
        ],
    },
    "degerleme_buyume": {
        "weight": 15,
        "metrics": [
            ("pe_ratio", True),
            ("pb_ratio", True),
            ("ev_to_ebitda", True),
            ("revenue_growth", False),
        ],
    },
}

TOTAL_METRIC_COUNT = sum(len(c["metrics"]) for c in CATEGORIES.values())

BAND_KIRMIZI, BAND_SARI, BAND_YESIL = "kirmizi", "sari", "yesil"


def _band(score):
    if score is None:
        return None
    if score < 50:
        return BAND_KIRMIZI
    if score < 70:
        return BAND_SARI
    return BAND_YESIL


def _metric_score(metric, value, sector, stocks_with_fundamentals, reverse):
    """Tek bir metriğin 0-100 skoru. ocf_positive_quarters (4 üzerinden sayaç)
    percentile'a girmez, doğrudan ölçeklenir — sektör-içi kıyas anlamsız."""
    if value is None:
        return None
    if metric == "ocf_positive_quarters":
        return max(0.0, min(100.0, (value / 4.0) * 100.0))
    pct = sector_stats.ticker_metric_percentile(value, metric, sector, stocks_with_fundamentals)
    if pct is None:
        return None
    return (100.0 - pct) if reverse else pct


def compute_health_score(ticker_fundamentals, sector, stocks_with_fundamentals):
    """Bir ticker için Temel Analiz Skoru (0-100).

    ticker_fundamentals: bu ticker'ın düz fundamentals dict'i.
    sector: bu ticker'ın sektörü (SECTORS/_build_sector_map çıktısı).
    stocks_with_fundamentals: TÜM ticker'ların fundamentals+sector dict listesi
    (percentile havuzu için gerekli — sector_stats.ticker_metric_percentile).

    Çıktı: {"temel_analiz_skoru": int|None, "data_completeness": float,
            "band": str|None, "categories": {kategori: skor}}
    """
    category_scores = {}
    metrics_with_data = 0

    for cat_name, cat in CATEGORIES.items():
        metric_scores = []
        for metric, reverse in cat["metrics"]:
            value = ticker_fundamentals.get(metric)
            score = _metric_score(metric, value, sector, stocks_with_fundamentals, reverse)
            if score is not None:
                metric_scores.append(score)
                metrics_with_data += 1
        if metric_scores:
            category_scores[cat_name] = sum(metric_scores) / len(metric_scores)

    data_completeness = round(metrics_with_data / TOTAL_METRIC_COUNT, 2)

    if not category_scores:
        return {
            "temel_analiz_skoru": None,
            "data_completeness": data_completeness,
            "band": None,
            "categories": {},
        }

    total_weight = sum(CATEGORIES[c]["weight"] for c in category_scores)
    weighted_sum = sum(category_scores[c] * CATEGORIES[c]["weight"] for c in category_scores)
    score = weighted_sum / total_weight

    return {
        "temel_analiz_skoru": round(score),
        "data_completeness": data_completeness,
        "band": _band(score),
        "categories": {c: round(s, 1) for c, s in category_scores.items()},
    }


def compute_borsapusula_score(teknik_skor, temel_skor, weights=None):
    """BorsaPusula kompozit skoru — basit ağırlıklı ortalama.

    teknik_skor: mevcut signal_strength (compose_score çıktısı, YENİDEN
    HESAPLAMA YOK, doğrudan okunur). Biri None ise kompozit mevcut tek
    bileşene düşer + partial=True taşır."""
    w = weights or {"temel": 0.6, "teknik": 0.4}
    if temel_skor is not None and teknik_skor is not None:
        composite = temel_skor * w["temel"] + teknik_skor * w["teknik"]
        return {"borsapusula_skoru": round(composite), "partial": False}
    if temel_skor is not None:
        return {"borsapusula_skoru": round(temel_skor), "partial": True}
    if teknik_skor is not None:
        return {"borsapusula_skoru": round(teknik_skor), "partial": True}
    return {"borsapusula_skoru": None, "partial": True}
