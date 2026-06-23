#!/usr/bin/env python3
"""
Subprocess-isolated yfinance fetcher (POC Gün 1 — CPO-740).
Kullanım: python3 yf_fetch.py <ticker> <period> <interval>
Çıktı: JSON to stdout (ok) | error JSON to stderr + exit 1

Tasarım: Her çağrı fresh Python interpreter → no global state contamination.
app.py _fetch_daily() bu scripti subprocess.run() ile çağırır.
"""
import sys
import json


def fetch(ticker: str, period: str, interval: str) -> dict:
    """Core fetch logic — isolated so it can be unit-tested without subprocess."""
    import yfinance as yf

    df = yf.download(
        ticker + ".IS",
        period=period,
        interval=interval,
        auto_adjust=True,
        progress=False,
        threads=False,
    )
    if df is None or df.empty:
        return {"error": "empty", "ticker": ticker}

    # Flatten MultiIndex columns (yfinance v0.2+ format)
    if hasattr(df.columns, "get_level_values"):
        cols = list(df.columns.get_level_values(0))
    else:
        cols = list(df.columns)

    # Build data dict: column → list of values
    # yfinance v0.2+ MultiIndex: df["Close"] may return a single-column DataFrame
    # instead of a Series; squeeze it to get values.
    data = {}
    for col in set(cols):
        series = df[col]
        if hasattr(series, "columns"):
            series = series.iloc[:, 0]
        data[col] = [None if (v != v) else float(v) for v in series]

    return {
        "ticker": ticker,
        "rows": len(df),
        "columns": cols,
        "index": [str(i) for i in df.index],
        "data": data,
    }


def main():
    if len(sys.argv) < 4:
        err = {"error": "args: ticker period interval", "usage": "yf_fetch.py AKBNK 2y 1d"}
        print(json.dumps(err), file=sys.stderr)
        sys.exit(1)

    ticker, period, interval = sys.argv[1], sys.argv[2], sys.argv[3]

    try:
        result = fetch(ticker, period, interval)
        if result.get("error"):
            print(json.dumps(result), file=sys.stderr)
            sys.exit(1)
        print(json.dumps(result))

    except Exception as e:
        err = {"error": str(e), "ticker": ticker, "type": type(e).__name__}
        print(json.dumps(err), file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
