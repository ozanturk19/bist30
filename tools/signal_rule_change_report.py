#!/usr/bin/env python3
"""D-47 — kural değişirse kaç hissenin durumu değişir raporu (salt okur, deploy yok).

`bp_yonlu_sim.py`'nin docstring'inde verilen sözün ("D-47 bu aracı genelleştirecek")
karşılığı. Girdi: tek bir `snapshots/YYYY-MM-DD.json` (gün sonu durumu + göstergeler,
_save_daily_snapshot ile yazılır). Üretim kodu `business_rules.signal_from_indicators`
ile her hissenin durumu (AL/SAT/BEKLE) hem BUGÜNKÜ hem de (varsa) değiştirilmiş eşikle
yeniden hesaplanır; ikisi arasındaki fark raporlanır — ikinci bir sinyal kanonu açılmaz,
yalnızca üretim fonksiyonu farklı bir parametreyle çağrılır.

Bugün tek parametreli eşik `TREND_ADX_MIN` (ADX ≥ 25); yeni bir koşul/eşik eklenirse
bu araca -- eşiğin adı kadar -- bir satır eklenir.

Kullanım:
    python3 tools/signal_rule_change_report.py --snapshot snapshots/2026-10-08.json --adx-min 30
    python3 tools/signal_rule_change_report.py --snapshot snapshots/2026-10-08.json --adx-min 30 --json kanit/d47-adx30.json
"""
import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import business_rules as br  # noqa: E402


def _st_dir(stock):
    st = (stock.get("indicators") or {}).get("supertrend") or {}
    if st.get("bull"):
        return 1
    if st.get("bear"):
        return -1
    return 0


def simulate(stocks, adx_min=None):
    """Her hissede bugünkü ve (adx_min verilmişse) değiştirilmiş eşikle durumu döner.

    `stocks`: snapshot dosyasının `stocks` listesi (her kayıtta adx/di_plus/di_minus/
    e12/e99/weekly_trend/indicators.supertrend alanları). Eksik göstergeli kayıtlar
    (fiyat taze ama gösterge henüz hesaplanmamış) atlanır, karşılaştırılamaz.
    """
    rows = []
    orig_adx_min = br.TREND_ADX_MIN
    try:
        for s in stocks:
            adx, di_p, di_m = s.get("adx"), s.get("di_plus"), s.get("di_minus")
            e12, e99, weekly_dir = s.get("e12"), s.get("e99"), s.get("weekly_trend")
            if any(v is None for v in (adx, di_p, di_m, e12, e99, weekly_dir)):
                continue
            st_dir = _st_dir(s)

            br.TREND_ADX_MIN = orig_adx_min
            before = br.signal_from_indicators(st_dir, adx, di_p, di_m, e12, e99, weekly_dir)

            br.TREND_ADX_MIN = orig_adx_min if adx_min is None else adx_min
            after = br.signal_from_indicators(st_dir, adx, di_p, di_m, e12, e99, weekly_dir)

            rows.append({"ticker": s.get("ticker"), "before": before, "after": after,
                         "degisti": before != after})
    finally:
        br.TREND_ADX_MIN = orig_adx_min
    return rows


def print_report(rows):
    degisen = [r for r in rows if r["degisti"]]
    print(f"Toplam hisse (göstergesi dolu): {len(rows)}  ·  Durum değişen: {len(degisen)}")
    gecisler = {}
    for r in degisen:
        key = f"{r['before']} → {r['after']}"
        gecisler[key] = gecisler.get(key, 0) + 1
    for key, n in sorted(gecisler.items(), key=lambda kv: -kv[1]):
        print(f"  {key}: {n}")
    if degisen:
        print("Örnekler:", ", ".join(f"{r['ticker']} ({r['before']}→{r['after']})"
                                      for r in degisen[:10]))
    return degisen


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                  formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--snapshot", required=True, help="snapshots/YYYY-MM-DD.json yolu")
    ap.add_argument("--adx-min", type=float, default=None,
                    help="ADX eşiğini bu değere değiştirip karşılaştır "
                         "(verilmezse 0 fark beklenir — araç kendi kendini sınar)")
    ap.add_argument("--json", default=None, help="Tam sonucu bu dosyaya da yaz")
    args = ap.parse_args()

    with open(args.snapshot, encoding="utf-8") as f:
        data = json.load(f)
    stocks = data.get("stocks", [])
    rows = simulate(stocks, adx_min=args.adx_min)
    degisen = print_report(rows)

    if args.json:
        with open(args.json, "w", encoding="utf-8") as f:
            json.dump({"snapshot": args.snapshot, "adx_min": args.adx_min,
                       "toplam": len(rows), "degisen": degisen},
                      f, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    main()
