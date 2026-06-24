#!/usr/bin/env python3
"""
Subprocess-isolated yfinance Ticker.history fetcher (G24a — CPO-740).
Kullanım: python3 yf_chart_fetch.py <yf_ticker> <period>
Çıktı: JSON to stdout (ok) | error JSON to stderr + exit 1

Örnek: python3 yf_chart_fetch.py XU030.IS 5y
Çıktı: {"ticker": "XU030.IS", "rows": N, "columns": [...], "index": [...], "data": {...}}
"""
import sys
import json


def fetch(yf_ticker: str, period: str) -> dict:
    """OHLC tarihsel veri — subprocess isolated, yfinance lock yok."""
    import yfinance as yf

    df = yf.Ticker(yf_ticker).history(period=period, interval="1d", auto_adjust=True)
    if df is None or df.empty:
        return {"error": "empty", "ticker": yf_ticker}

    ohlc_cols = [c for c in ["Open", "High", "Low", "Close", "Volume"] if c in df.columns]
    df = df[ohlc_cols]

    data = {}
    for col in ohlc_cols:
        series = df[col]
        if hasattr(series, "columns"):
            series = series.iloc[:, 0]
        data[col] = [None if (v != v) else float(v) for v in series]

    return {
        "ticker": yf_ticker,
        "rows": len(df),
        "columns": ohlc_cols,
        "index": [str(i) for i in df.index],
        "data": data,
    }


def main():
    if len(sys.argv) < 3:
        err = {"error": "args: yf_ticker period", "usage": "yf_chart_fetch.py XU030.IS 5y"}
        print(json.dumps(err), file=sys.stderr)
        sys.exit(1)

    yf_ticker, period = sys.argv[1], sys.argv[2]
    try:
        result = fetch(yf_ticker, period)
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
