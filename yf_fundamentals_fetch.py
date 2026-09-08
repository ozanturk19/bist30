#!/usr/bin/env python3
"""
Subprocess-isolated yfinance Ticker.info fetcher (G24c — CPO-740).
Kullanım: python3 yf_fundamentals_fetch.py <yf_ticker>
Çıktı: JSON to stdout (ok) | error JSON to stderr + exit 1

Örnek: python3 yf_fundamentals_fetch.py AKBNK.IS
Çıktı: {"ticker": "AKBNK.IS", "info": {...}}
"""
import sys
import json

_NEEDED_KEYS = [
    "trailingPE", "forwardPE", "priceToBook", "trailingEps",
    "marketCap", "totalRevenue", "netIncomeToCommon", "dividendYield",
    "returnOnEquity", "beta", "sharesOutstanding",
    "fiftyTwoWeekHigh", "fiftyTwoWeekLow", "averageVolume", "shortName",
    "profitMargins", "operatingMargins", "earningsGrowth", "revenueGrowth",
    "debtToEquity", "currentRatio", "priceToSalesTrailing12Months",
    # CPO r174 (Ozan istegi, temel analiz genisletme): analist + sahiplik + defter degeri
    "targetMeanPrice", "recommendationKey", "numberOfAnalystOpinions",
    "bookValue", "totalCash", "heldPercentInsiders", "heldPercentInstitutions",
]

# CPO r174: yillik gelir tablosu trendi (Ciro+Net Kar, tum sektorlerde var) —
# Gross Profit/Operating Income/EBITDA bankalar gibi finansal sektorde hic
# gelmiyor (bkz. AKBNK canli test), o yuzden trend'e dahil edilmedi — sadelik
# icin sadece evrensel iki kalem.
_STATEMENT_ROWS = ["Total Revenue", "Net Income"]


def _fetch_statement_trend(ticker) -> list:
    """Son 4 yillik Ciro+Net Kar trendi — NaN donemler atlanir (bkz. ASELS/AKBNK
    5. sutun hep NaN cikiyor, yfinance eksik yil icin bos sutun donduruyor)."""
    try:
        df = ticker.income_stmt
    except Exception:
        return []
    if df is None or df.empty:
        return []
    out = []
    for col in df.columns:
        year = col.year if hasattr(col, "year") else None
        if year is None:
            continue
        row = {"year": year}
        has_data = False
        for key in _STATEMENT_ROWS:
            if key in df.index:
                v = df.loc[key, col]
                if v is not None and not (isinstance(v, float) and v != v):  # NaN guard
                    row[key.lower().replace(" ", "_")] = float(v)
                    has_data = True
        if has_data:
            out.append(row)
    out.sort(key=lambda r: r["year"])
    return out[-4:]  # en fazla 4 yil


# CPO-1526 (Faz 1 temel-veri fetcher spec): Kaldiraç + Nakit Akışı skor
# girdileri. _fetch_statement_trend()'in aksine çok-yıllık liste değil, tek
# en güncel dönemin normalize edilmiş DÜZ dict'i — bunlar oran/istikrar
# girdisi, çok-yıllık trend grafiği değil. İZOLE: aşağıdaki iki fonksiyon
# şu an fetch()'ten çağrılmıyor, ana refresh döngüsüne bağlı değil.
_BALANCE_SHEET_ROWS = [
    "Current Assets", "Inventory", "Current Liabilities", "Net Debt",
    "Total Debt", "Stockholders Equity",
]
_CASHFLOW_ROWS = [
    "Free Cash Flow", "Operating Cash Flow", "Capital Expenditure",
    "Change In Working Capital",
]


def _latest_col_value(df, key, col):
    if key not in df.index:
        return None
    val = df.loc[key, col]
    if val is None or (isinstance(val, float) and val != val):  # NaN guard
        return None
    return float(val)


def _fetch_balance_sheet_trend(ticker) -> dict:
    """En güncel yıllık bilanço anlık görüntüsü — Kaldıraç/Likidite skor
    girdileri (CPO-1526). Bankacılık sektöründe Current Assets/Inventory/
    Current Liabilities satırları yfinance'da hiç yok (AKBNK ile canlı
    doğrulandı, bkz. _STATEMENT_ROWS üstündeki Gross Profit/EBITDA notuyla
    aynı kısıt) — o durumda quick_ratio None kalır, exception atılmaz."""
    try:
        df = ticker.balance_sheet
    except Exception:
        return {}
    if df is None or df.empty:
        return {}
    col = df.columns[0]  # yfinance en güncel dönemi ilk sütuna koyar (canlı doğrulandı)

    current_assets = _latest_col_value(df, "Current Assets", col)
    inventory = _latest_col_value(df, "Inventory", col)
    current_liabilities = _latest_col_value(df, "Current Liabilities", col)

    quick_ratio = None
    if current_assets is not None and current_liabilities:
        quick_ratio = (current_assets - (inventory or 0.0)) / current_liabilities

    return {
        "quick_ratio": quick_ratio,
        "net_debt": _latest_col_value(df, "Net Debt", col),
        "total_debt": _latest_col_value(df, "Total Debt", col),
        "stockholders_equity": _latest_col_value(df, "Stockholders Equity", col),
    }


def _fetch_cashflow_trend(ticker) -> dict:
    """En güncel yıllık nakit akış anlık görüntüsü + son 4 çeyrek Operating
    Cash Flow istikrar metriği (CPO-1526). fcf_to_sales oranı burada
    HESAPLANMIYOR — Total Revenue income_stmt'ten geliyor (_fetch_statement_trend),
    cross-statement birleştirme sonraki kablaj adımında (fetch() içinde veya
    sector_stats.py'de) yapılacak; burada sadece ham free_cash_flow dönüyor.
    İstikrar metriği (ocf_stability_cv) = son 4 çeyreğin OCF'inin ortalama-
    mutlak-değere normalize edilmiş std sapması (şirket büyüklüğünden bağımsız
    karşılaştırma için) — en az 3/4 çeyrek veri yoksa hiç hesaplanmaz (THYAO
    canlı testinde en eski 2 çeyrek NaN çıktı, yfinance kısmi çeyrek verisi
    döndürebiliyor)."""
    out = {}
    try:
        df = ticker.cashflow
    except Exception:
        df = None
    if df is not None and not df.empty:
        col = df.columns[0]
        out["free_cash_flow"] = _latest_col_value(df, "Free Cash Flow", col)
        out["operating_cash_flow"] = _latest_col_value(df, "Operating Cash Flow", col)
        out["capital_expenditure"] = _latest_col_value(df, "Capital Expenditure", col)
        out["working_capital_change"] = _latest_col_value(df, "Change In Working Capital", col)

    try:
        qdf = ticker.quarterly_cashflow
    except Exception:
        qdf = None
    if qdf is not None and not qdf.empty and "Operating Cash Flow" in qdf.index:
        vals = []
        for c in qdf.columns[:4]:  # en güncel 4 çeyrek (columns[0] = en güncel, canlı doğrulandı)
            v = qdf.loc["Operating Cash Flow", c]
            if v is not None and not (isinstance(v, float) and v != v):
                vals.append(float(v))
        if len(vals) >= 3:
            mean = sum(vals) / len(vals)
            mean_abs = sum(abs(v) for v in vals) / len(vals)
            out["ocf_quarters_used"] = len(vals)
            out["ocf_positive_quarters"] = sum(1 for v in vals if v > 0)
            if mean_abs > 0:
                variance = sum((v - mean) ** 2 for v in vals) / len(vals)
                out["ocf_stability_cv"] = (variance ** 0.5) / mean_abs

    return out


def fetch(yf_ticker: str) -> dict:
    """Temel analiz bilgilerini döndürür — subprocess isolated."""
    import yfinance as yf

    t = yf.Ticker(yf_ticker)
    info = t.info
    if not info or not isinstance(info, dict):
        return {"error": "empty_info", "ticker": yf_ticker}

    subset = {}
    for k in _NEEDED_KEYS:
        v = info.get(k)
        if v is None or v == "N/A":
            subset[k] = None
        elif isinstance(v, (int, float)):
            subset[k] = float(v)
        else:
            subset[k] = str(v)

    trend = _fetch_statement_trend(t)

    return {"ticker": yf_ticker, "info": subset, "statement_trend": trend}


def main():
    if len(sys.argv) < 2:
        err = {"error": "args: yf_ticker", "usage": "yf_fundamentals_fetch.py AKBNK.IS"}
        print(json.dumps(err), file=sys.stderr)
        sys.exit(1)

    yf_ticker = sys.argv[1]
    try:
        result = fetch(yf_ticker)
        if result.get("error"):
            print(json.dumps(result), file=sys.stderr)
            sys.exit(1)
        print(json.dumps(result))
    except Exception as e:
        err = {"error": str(e), "ticker": yf_ticker, "type": type(e).__name__}
        print(json.dumps(err), file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
