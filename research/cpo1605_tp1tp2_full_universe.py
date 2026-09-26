"""
CPO-1605 takip | TP1/TP2 backtest — TAM 215-hisse evreni + 3-bar onay +
RVOL kirilimi + entry-quality kirilimi.

CPO'nun 12.09 08:09 prototipinin (28 hisse, yfinance fresh-fetch) devami.
Bu script CANLI yfinance CAGRISI YAPMAZ — /root/bist30/data/charts/chart_*.json
disk cache'inden (production'in kendi ~2y günlük OHLCV cache'i, chart
sayfalarinda kullanilan AYNI veri) okur. Boylece:
  (a) Yahoo rate-limit riskine prod refresh'i maruz birakmiyor,
  (b) 215 hissenin TAMAMI kapsaniyor (CPO'nun 28'ine karsi).

Sinyal motoru app.py analyze() ile BIREBIR ayni mantik (bull_score/
bear_score, _historical_weekly_dir_series haftalik gate, ATR tabanli
entry-quality, TP1=entry+2R/TP2=entry+3R) — indicators.py'nin gercek
fonksiyonlari import edilir, YENIDEN YAZILMAZ.

Iki giris yaklasimi yan yana test edilir:
  A) "signal-start"  — CPO'nun orijinal metodolojisiyle karsilastirma icin
     (sinyalin ilk barinda sabit giris + o barin fiyati/SL'i).
  B) "confirmed-day3" — production'da "confirmed" rozetinin ilk gorundugu
     an (signal_bars==3) sabit giris + O GUNUN fiyati/SL'i/entry-quality'si
     ile TP1/TP2 (production'daki "bugunun fiyati/SL'i" ile ayni an,
     tek-snapshot; GUNLUK KAYAN hedef degil — o ayri, daha karmasik bir faz).

Cikis cozumleme: sinyal sonrasi high/low ile TP1/TP2/SL hangisi ONCE
tetikleniyor. Ayni gun hem TP hem SL tetiklenirse KONSERVATIF varsayim:
SL kazanir. Pencere: 120 bar (~6 ay), CPO'nunkiyle ayni. TP1(final)/TP2/SL/
Timeout merdiven siniflandirmasi CPO'nun tablosuyla ayni sekilde MUTUALLY
EXCLUSIVE (satir toplami %100) — "TP1(final)" sadece TP1'e dokunup TP2'ye
ilerlemeyen VE SL'e takilmayan sinyalleri sayar (TP2'ye ilerleyenler TP2
kovasina gider). Ayrica "TP1-ever-dokunuldu" bilgi amacli inclusive stat
olarak ayri raporlanir (TP2 sonucuna varanlari da icerir).

Dogrulama (12.09.2026, DEV): sinyal motorunun reprodüksiyonu THYAO icin
chart_THYAO.json'daki gercek "signal_history" ile karsilastirildi — 6
kayittan 5'i (tarih+fiyat) BIREBIR eslesti (14.08.2025 AL 322.68,
17.10.2025 SAT 292.00, 03.02.2026 AL 318.75, 06.03.2026 SAT 276.75,
15.06.2026 AL 325.75). Sinyal reprodüksiyonu güvenilir.

SONUC (12.09.2026, 215/215 hisse islendi, disk-cache ~2y): CPO'nun 28-
hisseli prototipiyle (TP2=%0, TP1=%17-18) CARPICI SEKILDE CELISIYOR —
AYNI 28 ticker'a filtrelendiginde bile (approach A, sadece disk-cache +
weekly-gate farkiyla): n=175 TP1(final)=%4.0 TP2=%17.7 SL=%75.4
Timeout=%2.9 TP1-ever=%26.9. Yani universe buyuklugu farki (28 vs 215)
ACIKLAMIYOR — CPO'nun orijinal script'inde (repo disinda, yerel
scratchpad) muhtemel bir metodoloji/kod farki var (ör. rolling-SL
yanlislikla kullanilmis olabilir), ayrica dogrulanmadi. Bu script'in
sonucu daha guvenilir kabul edilebilir cunku (a) production'in gercek
signal_history'siyle capraz dogrulandi, (b) tam 215 evren + 3-bar onay +
RVOL/entry-quality kirilimi var. Tam sonuc tablosu: DEV->CPO mailbox
DEV-1887.
"""
import json, os, sys
import numpy as np
import pandas as pd

sys.path.insert(0, "/root/bist30")
from indicators import compute_ema, compute_adx, compute_supertrend, compute_atr

CHART_DIR = "/root/bist30/data/charts"
FWD_WINDOW = 120


def load_ticker(path):
    with open(path) as f:
        d = json.load(f)
    ohlc = d.get("ohlc") or []
    vol = d.get("volume") or []
    if len(ohlc) < 150:
        return None
    idx = pd.to_datetime([r["time"] for r in ohlc])
    close = pd.Series([r["close"] for r in ohlc], index=idx, dtype=float)
    high = pd.Series([r["high"] for r in ohlc], index=idx, dtype=float)
    low = pd.Series([r["low"] for r in ohlc], index=idx, dtype=float)
    vol_map = {v["time"]: v["value"] for v in vol}
    volume = pd.Series([vol_map.get(r["time"], np.nan) for r in ohlc], index=idx, dtype=float)
    df = pd.DataFrame({"close": close, "high": high, "low": low, "volume": volume}).dropna()
    if len(df) < 150:
        return None
    return df


def historical_weekly_dir_series(close):
    weekly_close = close.resample("W-FRI").last().dropna()
    weekly_ema20 = weekly_close.ewm(span=20, adjust=False).mean()
    ema_prev_by_week = weekly_ema20.shift(1)
    ema_prev_by_week.index = ema_prev_by_week.index.to_period("W-FRI")
    completed_before = pd.Series(range(len(weekly_close)), index=weekly_close.index.to_period("W-FRI"))
    alpha = 2.0 / 21.0
    week_of_day = close.index.to_period("W-FRI")
    dirs = np.zeros(len(close), dtype=int)
    for i, wp in enumerate(week_of_day):
        n_before = completed_before.get(wp)
        ema_prev = ema_prev_by_week.get(wp)
        if n_before is None or n_before < 24 or ema_prev is None or pd.isna(ema_prev):
            dirs[i] = 0
            continue
        ema_now = alpha * float(close.iloc[i]) + (1 - alpha) * float(ema_prev)
        dirs[i] = 1 if ema_now > float(ema_prev) else -1
    return pd.Series(dirs, index=close.index)


def build_signals(df):
    close, high, low, volume = df["close"], df["high"], df["low"], df["volume"]
    ema12 = compute_ema(close, 12)
    ema99 = compute_ema(close, 99)
    adx, di_plus, di_minus = compute_adx(high, low, close)
    supertrend, st_line = compute_supertrend(high, low, close)
    atr14 = compute_atr(high, low, close, 14)
    wdir = historical_weekly_dir_series(close)

    n = len(close)
    signals = []
    for i in range(n):
        ei12, ei99 = float(ema12.iloc[i]), float(ema99.iloc[i])
        ai = float(adx.iloc[i])
        dip, dim = float(di_plus.iloc[i]), float(di_minus.iloc[i])
        sti = supertrend.iloc[i]
        sti = int(sti) if not pd.isna(sti) else 0
        wdi = int(wdir.iloc[i])
        if pd.isna(ai) or pd.isna(dip) or pd.isna(dim):
            signals.append("BEKLE")
            continue
        bs = int(sti == 1) + int(ai >= 25 and dip > dim) + int(ei12 > ei99)
        brs = int(sti == -1) + int(ai >= 25 and dim > dip) + int(ei12 < ei99)
        if bs >= 3 and wdi != -1 and wdi != 0:
            signals.append("AL")
        elif brs >= 3 and wdi != 1 and wdi != 0:
            signals.append("SAT")
        else:
            signals.append("BEKLE")
    return signals, ema12, ema99, adx, di_plus, di_minus, supertrend, st_line, atr14, volume


def episodes_from_signals(signals):
    """Ardisik ayni-sinyal bloklarini (episode) cikar: (start_i, end_i, sig)."""
    eps = []
    i = 0
    n = len(signals)
    while i < n:
        sig = signals[i]
        if sig in ("AL", "SAT"):
            j = i
            while j + 1 < n and signals[j + 1] == sig:
                j += 1
            eps.append((i, j, sig))
            i = j + 1
        else:
            i += 1
    return eps


def rvol_at(volume, i):
    if i < 19:
        return None
    v5 = float(volume.iloc[i - 4:i + 1].mean())
    v20 = float(volume.iloc[i - 19:i + 1].mean())
    if v20 > 0 and not pd.isna(v20) and not pd.isna(v5):
        return round(v5 / v20, 2)
    return None


def entry_quality_at(sig, signal_price, c, sl_val, atr_now):
    if atr_now is None or atr_now <= 0 or sl_val is None:
        return None, None
    if sig == "AL":
        if c <= sl_val:
            return None, None
        risk = c - sl_val
        pct_moved = (c - signal_price) / signal_price * 100
    else:
        if c >= sl_val:
            return None, None
        risk = sl_val - c
        pct_moved = (signal_price - c) / signal_price * 100
    atr_pct = atr_now / c * 100
    if atr_pct <= 0:
        return None, None
    atrs_moved = pct_moved / atr_pct
    if atrs_moved < 1.0:
        q = "IDEAL"
    elif atrs_moved < 2.0:
        q = "IYI"
    elif atrs_moved < 3.5:
        q = "DIKKATLI"
    else:
        q = "UZAK"
    return q, risk


def resolve_full(sig, entry_i, entry_price, risk, high, low, n, window=FWD_WINDOW):
    """TP1 sonra TP2'ye devam edip etmedigini de izler (ayri kayit)."""
    if sig == "AL":
        tp1 = entry_price + risk * 2
        tp2 = entry_price + risk * 3
        sl = entry_price - risk
    else:
        tp1 = entry_price - risk * 2
        tp2 = entry_price - risk * 3
        sl = entry_price + risk
    end = min(entry_i + window, n - 1)
    censored = (entry_i + window) > (n - 1)
    tp1_hit = False
    for k in range(entry_i + 1, end + 1):
        hi, lo = float(high.iloc[k]), float(low.iloc[k])
        if sig == "AL":
            hit_sl, hit_tp2, hit_tp1 = lo <= sl, hi >= tp2, hi >= tp1
        else:
            hit_sl, hit_tp2, hit_tp1 = hi >= sl, lo <= tp2, lo <= tp1
        if hit_tp1:
            tp1_hit = True
        if hit_sl:
            return ("SL", tp1_hit, censored)
        if hit_tp2:
            return ("TP2", True, censored)
    return ("TIMEOUT", tp1_hit, censored)


def main():
    files = sorted(f for f in os.listdir(CHART_DIR) if f.startswith("chart_") and f.endswith(".json"))
    rows = []
    skipped = []
    for fn in files:
        ticker = fn[len("chart_"):-len(".json")]
        path = os.path.join(CHART_DIR, fn)
        try:
            df = load_ticker(path)
        except Exception as e:
            skipped.append((ticker, str(e)))
            continue
        if df is None:
            skipped.append((ticker, "insufficient bars"))
            continue
        try:
            signals, ema12, ema99, adx, di_plus, di_minus, supertrend, st_line, atr14, volume = build_signals(df)
        except Exception as e:
            skipped.append((ticker, f"signal-build error: {e}"))
            continue
        close, high, low = df["close"], df["high"], df["low"]
        n = len(close)
        eps = episodes_from_signals(signals)
        for (start_i, end_i, sig) in eps:
            bars = end_i - start_i + 1
            confirmed = bars >= 3
            signal_price = float(close.iloc[start_i])

            # --- Approach A: signal-start entry ---
            sl_a = float(st_line.iloc[start_i]) if not pd.isna(st_line.iloc[start_i]) else None
            if sl_a is not None and ((sig == "AL" and signal_price > sl_a) or (sig == "SAT" and signal_price < sl_a)):
                risk_a = abs(signal_price - sl_a)
                if risk_a > 0:
                    outcome_a, tp1_hit_a, censored_a = resolve_full(sig, start_i, signal_price, risk_a, high, low, n)
                    rvol_a = rvol_at(volume, start_i)
                    rows.append({
                        "ticker": ticker, "sig": sig, "approach": "A_signal_start",
                        "confirmed": confirmed, "bars": bars,
                        "rvol": rvol_a, "premium": (rvol_a is not None and rvol_a >= 1.20),
                        "entry_quality": None,
                        "outcome": outcome_a, "tp1_hit": tp1_hit_a, "censored": censored_a,
                    })

            # --- Approach B: confirmed-day3 entry (only if episode reached bar 3) ---
            if bars >= 3:
                day3_i = start_i + 2
                c3 = float(close.iloc[day3_i])
                sl_b = float(st_line.iloc[day3_i]) if not pd.isna(st_line.iloc[day3_i]) else None
                atr3 = float(atr14.iloc[day3_i]) if not pd.isna(atr14.iloc[day3_i]) else None
                if sl_b is not None:
                    eq, risk_b = entry_quality_at(sig, signal_price, c3, sl_b, atr3)
                    if risk_b is not None and risk_b > 0:
                        outcome_b, tp1_hit_b, censored_b = resolve_full(sig, day3_i, c3, risk_b, high, low, n)
                        rvol_b = rvol_at(volume, day3_i)
                        rows.append({
                            "ticker": ticker, "sig": sig, "approach": "B_confirmed_day3",
                            "confirmed": True, "bars": bars,
                            "rvol": rvol_b, "premium": (rvol_b is not None and rvol_b >= 1.20),
                            "entry_quality": eq,
                            "outcome": outcome_b, "tp1_hit": tp1_hit_b, "censored": censored_b,
                        })

    out = pd.DataFrame(rows)
    out.to_csv("/root/bist30/data-staging/cpo1605_full_universe_backtest_raw.csv", index=False)

    def summarize(df, label):
        df = df[~df["censored"]]  # timeout icin sansur olanlari cikar (asagida ayrica raporlanacak)
        n = len(df)
        if n == 0:
            print(f"{label}: n=0")
            return
        # Mutually-exclusive merdiven siniflandirma (CPO'nun tablosuyla ayni: toplam %100)
        is_tp2 = df["outcome"] == "TP2"
        is_sl = df["outcome"] == "SL"
        is_tp1_final = (df["outcome"] == "TIMEOUT") & df["tp1_hit"]
        is_timeout_final = (df["outcome"] == "TIMEOUT") & ~df["tp1_hit"]
        tp1 = is_tp1_final.mean() * 100
        tp2 = is_tp2.mean() * 100
        sl = is_sl.mean() * 100
        timeout = is_timeout_final.mean() * 100
        tp1_ever = df["tp1_hit"].mean() * 100
        print(f"{label}: n={n}  TP1(final)={tp1:.1f}%  TP2={tp2:.1f}%  SL={sl:.1f}%  Timeout={timeout:.1f}%  [TP1-ever-dokunuldu={tp1_ever:.1f}%]")

    print(f"\nToplam ticker: {len(files)}  islenen: {len(files) - len(skipped)}  atlanan: {len(skipped)}")
    if skipped:
        print("Atlanan ornekler:", skipped[:5])

    for approach in ["A_signal_start", "B_confirmed_day3"]:
        sub = out[out["approach"] == approach]
        print(f"\n=== {approach} ===")
        summarize(sub, "  Tum sinyaller")
        summarize(sub[sub["sig"] == "AL"], "  Sadece AL")
        summarize(sub[sub["sig"] == "SAT"], "  Sadece SAT")
        if approach == "A_signal_start":
            summarize(sub[sub["confirmed"]], "  Sadece confirmed (>=3 bar)")
            summarize(sub[~sub["confirmed"]], "  Sadece unconfirmed (<3 bar)")
        prem = sub[sub["premium"] == True]
        nonprem = sub[(sub["premium"] == False) & (sub["rvol"].notna())]
        summarize(prem, "  RVOL>=1.20 (premium)")
        summarize(nonprem, "  RVOL<1.20")
        for eq in ["IDEAL", "IYI", "DIKKATLI", "UZAK"]:
            summarize(sub[sub["entry_quality"] == eq], f"  Entry quality={eq}")

    n_censored = out["censored"].sum()
    print(f"\nSansurlu (120-bar penceresi veri sonuna tasan, TIMEOUT olarak sayilmayan) kayit: {n_censored}/{len(out)}")


if __name__ == "__main__":
    main()
