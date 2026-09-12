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

Güven eşiği (CPO-1528 P1 denetimi, 09.09): toplam veri bulunan metrik sayısı
MIN_METRICS_FOR_SCORE altındaysa (ör. tek bir metrik geçerli) skor/bant
BASTIRILIR (None döner) — tek metriğin doğrudan 0-100 skoru ve rengini
belirlemesini, ve %60 ağırlıkla BorsaPusula Skoru'na sızmasını önler. Bu,
data_completeness<0.6 iken rationale'a eklenen "sınırlı veri" dipnotundan
AYRI ve daha sert bir kapı — dipnot skoru göstermeye devam eder, bu kapı
skoru hiç üretmez.

Bantlar: 0-49 kırmızı, 50-69 sarı, 70-100 yeşil (Site Contract, sabit).
"""

import sector_stats

# En az bu kadar metrik veri içermeden Temel Analiz Skoru/bant üretilmez
# (bkz. modül docstring'indeki "Güven eşiği"). 14 metriklik havuzda ~%21 —
# en küçük kategorilerin (nakit_akışı/kaldıraç, 3 metrik) tek başına dolu
# olmasına izin verecek kadar gevşek, tek/çift metriğin skoru tek başına
# belirlemesini engelleyecek kadar sıkı.
MIN_METRICS_FOR_SCORE = 3

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

CATEGORY_LABELS = {
    "karlilik": "Kârlılık",
    "nakit_akisi": "Nakit Akışı",
    "kaldirac": "Kaldıraç",
    "degerleme_buyume": "Değerleme/Büyüme",
}

# CPO-1617/1619 (12.09.2026): bu tickerlarda Kaldıraç kategorisi veri
# BOŞLUĞU değil, yapısal olarak UYGULANAMAZ — mevduat bankası (+ ağırlıklı
# finansal iştirak/GYO) bilanço sunumunda "Current Assets/Current
# Liabilities/EBITDA" satırları yfinance'da hiç yok (bkz.
# yf_fundamentals_fetch.py _fetch_balance_sheet_trend/_fetch_latest_income_items
# docstring'leri, AKBNK ile canlı doğrulandı), o yüzden net_debt_to_ebitda/
# current_ratio/quick_ratio hep None gelir. CPO'nun 214-ticker taramasıyla
# doğrulanan tam liste — aynı "Bankacılık" sektöründeki leasing/faktoring/
# aracı kurum tickerları (ISFIN/CRDFA/ISMEN) BU LİSTEDE YOK, çünkü onlarda
# kaldıraç metrikleri gerçekten hesaplanabiliyor (mevduat bankası bilanço
# yapısına sahip değiller). Liste elle tutuluyor çünkü kod tabanında
# "mevduat bankası" ayrımını yapan başka bir sektör alt-kırılımı yok.
LEVERAGE_NA_TICKERS = {
    "AKBNK", "GARAN", "HALKB", "ISCTR", "VAKBN", "YKBNK",
    "ALBRK", "KLNMA", "TSKB", "SKBNK",  # mevduat bankaları
    "SAHOL",  # holding, ağırlıklı finansal iştirak yapısı
    "YESIL",  # GYO, bilanço yapısı benzer şekilde uyumsuz
}


def _band(score):
    if score is None:
        return None
    if score < 50:
        return BAND_KIRMIZI
    if score < 70:
        return BAND_SARI
    return BAND_YESIL


def _metric_score(metric, value, sector, stocks_with_fundamentals, reverse, ticker_fundamentals=None):
    """Tek bir metriğin 0-100 skoru. ocf_positive_quarters (gerçek çeyrek sayısı
    üzerinden sayaç, bkz. ocf_quarters_used) percentile'a girmez, doğrudan
    ölçeklenir — sektör-içi kıyas anlamsız."""
    if value is None:
        return None
    if metric == "ocf_positive_quarters":
        quarters_used = (ticker_fundamentals or {}).get("ocf_quarters_used") or 4
        return max(0.0, min(100.0, (value / quarters_used) * 100.0))
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
            "categories_complete": bool, "band": str|None,
            "categories": {kategori: skor}, "categories_na": [kategori, ...]}

    categories_na (CPO-1617), categories dict'inde eksik olan kategorilerden
    hangilerinin GEÇİCİ veri boşluğu değil, ticker'ın sektör/bilanço yapısı
    gereği YAPISAL OLARAK uygulanamaz olduğunu işaretler (bkz.
    LEVERAGE_NA_TICKERS). categories_complete hâlâ False kalır (numerik skor
    hâlâ yok) — bu alan sadece nedeni ayırt etmek için, radar gibi tüketen
    kod "veri yok" yerine "sektöre özgü, uygulanamaz" gösterebilsin diye var.

    categories_complete, 4 kategorinin (karlilik/nakit_akisi/kaldirac/
    degerleme_buyume) HEPSİNİN skoru hesaplanabildiğini gösterir — bununla
    compute_borsapusula_score()'un döndürdüğü "partial" (composite skorun
    temel/teknik bileşenlerinden biri mi eksik) TAMAMEN AYRI bir kavramdır.
    İkisini karıştırmak CPO-1606 P0'ına (hisse.html radar_dim, 4 banka
    ticker'ı) yol açtı: kaldirac kategorisi eksik olsa da hem temel_skor
    hem teknik_skor mevcutsa composite.partial=False kalıyor, kategori
    eksikliğini hiç yansıtmıyordu. Kullanan kod categories_complete'i
    kullanmalı, partial'ı değil."""
    category_scores = {}
    metrics_with_data = 0

    for cat_name, cat in CATEGORIES.items():
        metric_scores = []
        for metric, reverse in cat["metrics"]:
            value = ticker_fundamentals.get(metric)
            score = _metric_score(metric, value, sector, stocks_with_fundamentals, reverse, ticker_fundamentals)
            if score is not None:
                metric_scores.append(score)
                metrics_with_data += 1
        if metric_scores:
            category_scores[cat_name] = sum(metric_scores) / len(metric_scores)

    data_completeness = round(metrics_with_data / TOTAL_METRIC_COUNT, 2)
    categories_complete = len(category_scores) == len(CATEGORIES)

    ticker = ticker_fundamentals.get("ticker")
    categories_na = [
        c for c in CATEGORIES
        if c not in category_scores and c == "kaldirac" and ticker in LEVERAGE_NA_TICKERS
    ]

    if not category_scores or metrics_with_data < MIN_METRICS_FOR_SCORE:
        return {
            "temel_analiz_skoru": None,
            "data_completeness": data_completeness,
            "categories_complete": categories_complete,
            "band": None,
            "categories": {},
            "categories_na": categories_na,
        }

    total_weight = sum(CATEGORIES[c]["weight"] for c in category_scores)
    weighted_sum = sum(category_scores[c] * CATEGORIES[c]["weight"] for c in category_scores)
    score = weighted_sum / total_weight

    return {
        "temel_analiz_skoru": round(score),
        "data_completeness": data_completeness,
        "categories_complete": categories_complete,
        "band": _band(round(score)),
        "categories": {c: round(s, 1) for c, s in category_scores.items()},
        "categories_na": categories_na,
    }


def _tier_word(score):
    if score >= 70:
        return "güçlü"
    if score >= 50:
        return "ortalama"
    return "zayıf"


def build_rationale(categories, data_completeness):
    """CPO-1531 Faz 3 — kategori skorlarından deterministik Türkçe gerekçe cümlesi.

    En güçlü ve en zayıf kategoriyi karşılaştırır. Bu cümle Gemini'ye SADECE
    akıcı Türkçe'ye çevrilmek üzere verilir — yeni analiz/yorum YAPILMAZ,
    burada üretilen anlam sabittir (_enrich_signal_explanation'daki
    önce-hesapla-sonra-Türkçeleştir deseniyle birebir)."""
    if not categories:
        return "Yeterli finansal veri bulunmadığı için temel analiz skoru hesaplanamadı."

    ranked = sorted(categories.items(), key=lambda kv: kv[1], reverse=True)
    best_name, best_score = ranked[0]
    worst_name, worst_score = ranked[-1]
    best_label = CATEGORY_LABELS.get(best_name, best_name)
    worst_label = CATEGORY_LABELS.get(worst_name, worst_name)

    if len(ranked) == 1 or best_name == worst_name:
        sentence = f"{best_label} kategorisinde {_tier_word(best_score)} bir görünüm var (skor: {best_score:.0f})."
    else:
        sentence = (
            f"{best_label} kategorisinde {_tier_word(best_score)} bir görünüm var (skor: {best_score:.0f}), "
            f"{worst_label} kategorisinde ise {_tier_word(worst_score)} sonuçlar öne çıkıyor (skor: {worst_score:.0f})."
        )

    if data_completeness is not None and data_completeness < 0.6:
        sentence += " Bazı finansal veriler eksik olduğu için skor sınırlı veriyle hesaplanmıştır."

    return sentence


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
