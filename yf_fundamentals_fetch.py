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
