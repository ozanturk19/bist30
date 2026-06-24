#!/usr/bin/env python3
"""
Subprocess-isolated yfinance Ticker.fast_info fetcher (Görev 9 — CPO-740).
Kullanım: python3 yf_macro_fetch.py <sym>
Çıktı: JSON to stdout (ok) | error JSON to stderr + exit 1

Örnek: python3 yf_macro_fetch.py USDTRY=X
Çıktı: {"sym": "USDTRY=X", "price": 38.45, "prev_close": 38.20}
"""
import sys
import json


def fetch(sym: str) -> dict:
    """Tek bir sembol için fast_info çağrısı — subprocess isolated."""
    import yfinance as yf

    tk = yf.Ticker(sym)
    fi = tk.fast_info
    price = getattr(fi, "last_price", None) or getattr(fi, "regularMarketPrice", None)
    prev = getattr(fi, "previous_close", None)

    if price is None:
        return {"error": "no_price", "sym": sym}
    if prev is None:
        return {"error": "no_prev_close", "sym": sym}

    return {
        "sym": sym,
        "price": float(price),
        "prev_close": float(prev),
    }


def main():
    if len(sys.argv) < 2:
        err = {"error": "args: sym", "usage": "yf_macro_fetch.py USDTRY=X"}
        print(json.dumps(err), file=sys.stderr)
        sys.exit(1)

    sym = sys.argv[1]
    try:
        result = fetch(sym)
        if result.get("error"):
            print(json.dumps(result), file=sys.stderr)
            sys.exit(1)
        print(json.dumps(result))
    except Exception as e:
        err = {"error": str(e), "sym": sym, "type": type(e).__name__}
        print(json.dumps(err), file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
