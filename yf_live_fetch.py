#!/usr/bin/env python3
"""
Subprocess-isolated yfinance batch live price fetcher (G24d — CPO-740).
Kullanım:
  python3 yf_live_fetch.py bist "<AKBNK.IS ARCLK.IS ...>"
  python3 yf_live_fetch.py global '["BTC-USD","GC=F",...]'

bist mode:
  argv[2]: space-joined yf symbols (e.g. "AKBNK.IS ARCLK.IS ...")
  Cikti: {"mode": "bist", "payload": {"AKBNK": {"price": 1.23, "change_pct": 0.5}}}
  Not: .IS suffix kaldirilir

global mode:
  argv[2]: JSON list of yf symbols (e.g. '["BTC-USD", "GC=F"]')
  Cikti: {"mode": "global", "payload": {"BTC-USD": {"price": 67890.12, "change_pct": 1.5}}}
  Not: orijinal yf sembol key olarak kalir (app.py mapping yapar)
"""
import sys
import json


def _parse_multiticker_df(df, syms):
    """yf.download MultiIndex DataFrame'i parse et → {sym: {price, change_pct}}."""
    import pandas as pd

    payload = {}
    for sym in syms:
        try:
            if isinstance(df.columns, pd.MultiIndex):
                lvls = df.columns.get_level_values(0)
                if sym not in lvls:
                    continue
                closes = df[sym]["Close"].dropna()
            else:
                closes = df["Close"].dropna()

            if closes is None or len(closes) < 2:
                continue

            price = float(closes.iloc[-1])
            today_date = closes.index[-1].date()
            prev_bars = closes[closes.index.map(lambda x: x.date()) < today_date]
            prev = float(prev_bars.iloc[-1]) if len(prev_bars) > 0 else float(closes.iloc[-2])
            chg = ((price - prev) / prev * 100) if prev else 0

            payload[sym] = {"price": round(price, 6), "change_pct": round(chg, 2)}
        except Exception:
            continue
    return payload


def fetch_bist(tickers_str):
    """BIST batch live prices — subprocess isolated."""
    import yfinance as yf

    df = yf.download(
        tickers_str, period="2d", interval="1m",
        progress=False, auto_adjust=True, group_by="ticker", timeout=30, threads=False
    )
    if df is None or df.empty:
        return {"error": "empty_df", "mode": "bist"}

    syms = tickers_str.split()
    raw = _parse_multiticker_df(df, syms)
    payload = {sym.replace(".IS", ""): v for sym, v in raw.items()}
    return {"mode": "bist", "payload": payload}


def fetch_global(symbols_json):
    """Global prices (BTC, emtia, ABD hisseleri) — subprocess isolated."""
    import yfinance as yf

    syms = json.loads(symbols_json)
    df = yf.download(
        " ".join(syms), period="2d", interval="1m",
        progress=False, auto_adjust=True, group_by="ticker", timeout=30, threads=False
    )
    if df is None or df.empty:
        return {"error": "empty_df", "mode": "global"}

    payload = _parse_multiticker_df(df, syms)
    return {"mode": "global", "payload": payload}


def main():
    if len(sys.argv) < 3:
        err = {
            "error": "args: mode tickers",
            "usage": "yf_live_fetch.py bist 'AKBNK.IS ...' | yf_live_fetch.py global '[\"BTC-USD\",...]'",
        }
        print(json.dumps(err), file=sys.stderr)
        sys.exit(1)

    mode = sys.argv[1]
    arg = sys.argv[2]

    if mode == "bist":
        result = fetch_bist(arg)
    elif mode == "global":
        result = fetch_global(arg)
    else:
        err = {"error": f"unknown mode: {mode}", "modes": ["bist", "global"]}
        print(json.dumps(err), file=sys.stderr)
        sys.exit(1)

    if result.get("error"):
        print(json.dumps(result), file=sys.stderr)
        sys.exit(1)

    print(json.dumps(result))


if __name__ == "__main__":
    main()
