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

    D-P0-2809a: `=F` sürekli serisi kontrat devri gününde `iloc[-2]`'yi farklı bir
    kontrattan okuyor (ör. Aralık barına karşı Kasım kapanışı) → prev artık öncelikle
    Yahoo'nun kendi aynı-kontrat hesabı olan regularMarketChangePercent'ten türetilir
    (`prev_pct`); `prev_daily` yalnız pct yoksa ve aynı kontrat testini geçerse
    (`same_contract`) kullanılabilir bir yedek olur.
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

    is_future = sym.endswith("=F")
    if is_future:
        try:
            pct = tk.info.get("regularMarketChangePercent")
            if pct is not None:
                out["pct"] = float(pct)
                out["prev_pct"] = float(price) / (1 + float(pct) / 100)
        except Exception:
            pass  # regularMarketChangePercent yoksa prev_daily/prev_close'a düşer

    if daily_prev:
        try:
            bars = tk.history(period="7d", interval="1d")
            closes = bars["Close"].dropna()
            if len(closes) >= 2:
                out["prev_daily"] = float(closes.iloc[-2])
                if is_future:
                    opens = bars["Open"].dropna()
                    vols = bars["Volume"].dropna()
                    if len(opens) >= 1 and len(vols) >= 2 and vols.iloc[-2] > 0:
                        out["same_contract"] = bool(
                            vols.iloc[-1] / vols.iloc[-2] < 10
                            and abs(float(opens.iloc[-1]) / float(closes.iloc[-2]) - 1) < 0.03
                        )
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
