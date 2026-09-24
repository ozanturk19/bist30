"""D-51: /api/tarama satirlarina eklenen turetilmis alanlar (Flask'tan bagimsiz, saf hesaplama).

- va: "Fiyati makul mu?" bandi (u/m/p/k). Kanon (docs/URUN-VE-TASARIM.md §5.6): oran =
  deger / ortanca; <0,80 ucuz, >1,25 pahali, arasi makul; F/K ile PD/DD ters yonde ise
  Karisik. Ortanca: sektor (gecerli akran >=3) yoksa BIST geneli — metrik basina.
- ema_diff: (EMA12 / EMA99 - 1) x 100, isaretli, 2 ondalik.
- lim: gun sonu tavan/taban bayragi (heatmap.limit_flag ile ayni fiyat adimi hesabi).
"""

import statistics

import heatmap

MIN_PEERS = 3
CHEAP_BELOW = 0.80
EXPENSIVE_ABOVE = 1.25


def _positive(v):
    return isinstance(v, (int, float)) and not isinstance(v, bool) and v == v and v > 0


def valuation_medians(fund_by_ticker, sector_of):
    """{"sector": {sektor: {"pe": (med, n), "pb": (med, n)}}, "market": {"pe": med, "pb": med}}.

    Yalniz pozitif oranlar (zarar eden sirketin F/K'si tanimsiz) ortancaya girer."""
    by_sec, allv = {}, {"pe": [], "pb": []}
    for tk, fund in fund_by_ticker.items():
        sec = sector_of(tk)
        for key, field in (("pe", "pe_ratio"), ("pb", "pb_ratio")):
            v = (fund or {}).get(field)
            if _positive(v):
                by_sec.setdefault(sec, {"pe": [], "pb": []})[key].append(v)
                allv[key].append(v)
    sector = {s: {k: (statistics.median(v), len(v)) if v else (None, 0) for k, v in d.items()}
              for s, d in by_sec.items()}
    market = {k: (statistics.median(v) if v else None) for k, v in allv.items()}
    return {"sector": sector, "market": market}


def derive_valuation_band(pe, pb, sector, medians):
    """'u' | 'm' | 'p' | 'k' | None (F/K ve PD/DD ikisi de tanimsizsa)."""
    sec = (medians.get("sector") or {}).get(sector) or {}
    parts = []
    for key, v in (("pe", pe), ("pb", pb)):
        if not _positive(v):
            continue
        med, n = sec.get(key, (None, 0))
        if not (med and n >= MIN_PEERS):
            med = (medians.get("market") or {}).get(key)
        if not _positive(med):
            continue
        q = v / med
        parts.append(-1 if q < CHEAP_BELOW else (1 if q > EXPENSIVE_ABOVE else 0))
    if not parts:
        return None
    if len(parts) == 2 and parts[0] != parts[1] and parts[0] != 0 and parts[1] != 0:
        return "k"
    s = sum(parts)
    return "u" if s < 0 else ("p" if s > 0 else "m")


def ema_diff_pct(indicators):
    """indicators.ema1299: diff_pct mutlak, yon bull/bear'dan; None ise None."""
    e = (indicators or {}).get("ema1299") or {}
    d = e.get("diff_pct")
    if d is None:
        return None
    if e.get("bear") and not e.get("bull"):
        d = -d
    return round(d, 2)


def limit_flag_from_change(price, change_pct):
    """Onceki kapanis satirda yok: fiyat / (1 + degisim) fiyat adimina oturtulup
    heatmap.limit_flag'e verilir (degisim 2 ondalik yuvarlandigi icin adim payi yeter)."""
    if not _positive(price) or change_pct is None or abs(change_pct) < 9.0:
        return None
    prev = price / (1 + change_pct / 100.0)
    if prev <= 0:
        return None
    tick = heatmap.tick_size(prev)
    prev = round(round(prev / tick) * tick, 2)
    return heatmap.limit_flag(price, prev)
