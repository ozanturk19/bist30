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
]


def fetch(yf_ticker: str) -> dict:
    """Temel analiz bilgilerini döndürür — subprocess isolated."""
    import yfinance as yf

    info = yf.Ticker(yf_ticker).info
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

    return {"ticker": yf_ticker, "info": subset}


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
