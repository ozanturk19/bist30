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


def fetch(sym: str, daily_prev: bool = False) -> dict:
    """Tek bir sembol için fast_info çağrısı — subprocess isolated.

    daily_prev=True: vadeli (=F) semboller için fast_info.previous_close bayat/farklı
    seans değeri veriyor (D-49: Brent -1,3 vs günlük bar -2,14; gümüş +0,24 vs +1,24);
    günlük barın sondan bir önceki kapanışı `prev_daily` olarak eklenir.
    """
    import yfinance as yf

    tk = yf.Ticker(sym)
    fi = tk.fast_info
    price = getattr(fi, "last_price", None) or getattr(fi, "regularMarketPrice", None)
    prev = getattr(fi, "previous_close", None)

    if price is None:
        return {"error": "no_price", "sym": sym}
    if prev is None:
        return {"error": "no_prev_close", "sym": sym}

    out = {
        "sym": sym,
        "price": float(price),
        "prev_close": float(prev),
    }
    if daily_prev:
        try:
            closes = tk.history(period="7d", interval="1d")["Close"].dropna()
            if len(closes) >= 2:
                out["prev_daily"] = float(closes.iloc[-2])
        except Exception:
            pass  # fast_info prev_close'a düşer
    return out


def main():
    if len(sys.argv) < 2:
        err = {"error": "args: sym", "usage": "yf_macro_fetch.py USDTRY=X"}
        print(json.dumps(err), file=sys.stderr)
        sys.exit(1)

    sym = sys.argv[1]
    try:
        result = fetch(sym, daily_prev=(len(sys.argv) > 2 and sys.argv[2] == "daily"))
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
