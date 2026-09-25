#!/usr/bin/env python3
"""D-10 — yönlü BorsaPusula Skoru simülasyonu (salt okur, deploy yok).

Kanon §3 (O2, long-only):
    BP = 0,6 × Temel + 0,4 × Trend payı
    Trend payı = Güçlü Trend max(50, TG) · Yatay 50 · Trend Bozuldu min(50, 100 − TG)
Bugünkü formül (karşılaştırma): BP = 0,6 × Temel + 0,4 × TG; TG yoksa (Yatay) BP = Temel.

Formül burada BAĞIMSIZ yazılır (kâhin): üretim uygulaması (D-21,
financial_health_score) buna karşı test edilir; aynı kodu çağırsaydı kontrol
kendini doğrulardı.

Girdiler (VPS'ten kopya; araç hiçbir yere yazmaz):
    snapshots/YYYY-MM-DD.json  gün sonu durumu (signal) + göstergeler
    scores/YYYY-MM-DD.json     o günün Temel skoru ve üretimin kullandığı TG
Temel skoru olmayan günlerde bir önceki (yoksa ilk) skor dosyası kullanılır.
TG: skor dosyasında varsa oradan, yoksa göstergelerden business_rules.compose_score.

Kullanım:
    python3 tools/bp_yonlu_sim.py --snapshots DIR --scores DIR [--day YYYY-MM-DD] [--json OUT]
    python3 tools/bp_yonlu_sim.py --canli last_health_scores.json   # D-21 bayrağı açıldıktan sonra
D-47 bu aracı "kural değişirse kaç hissenin durumu değişir" raporuna genelleyecek.
"""
import argparse
import json
import os
import statistics
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from business_rules import compose_score  # noqa: E402  (TG girdisi; formül kâhini aşağıda)

LABEL = {"AL": "Güçlü Trend", "BEKLE": "Yatay", "SAT": "Trend Bozuldu"}


def trend_payi(durum, tg):
    if durum == "AL":
        return 50.0 if tg is None else max(50.0, float(tg))
    if durum == "SAT":
        return 50.0 if tg is None else min(50.0, 100.0 - float(tg))
    return 50.0


def bp_yonlu(temel, durum, tg):
    return None if temel is None else round(0.6 * temel + 0.4 * trend_payi(durum, tg))


def bp_bugun(temel, tg):
    if temel is not None and tg is not None:
        return round(temel * 0.6 + tg * 0.4)
    if temel is not None:
        return round(temel)
    return None if tg is None else round(tg)


def band(v):
    return None if v is None else ("kirmizi" if v < 50 else "sari" if v < 70 else "yesil")


def grid_proof():
    """Tam tamsayı alanı (Temel, TG ∈ 0..100): monotonluk ve yön. Üretimde ikisi de tamsayı."""
    viol_new = viol_old = dir_new = 0
    for t in range(101):
        y_new, y_old = bp_yonlu(t, "BEKLE", None), bp_bugun(t, None)
        prev_gt = prev_tb = None
        for g in range(101):
            gt, tb = bp_yonlu(t, "AL", g), bp_yonlu(t, "SAT", g)
            viol_new += not (gt >= y_new >= tb)
            viol_old += not (bp_bugun(t, g) >= y_old >= bp_bugun(t, g))
            if prev_gt is not None:
                dir_new += (gt < prev_gt) + (tb > prev_tb)   # GT'de güç artınca düşmez, TB'de artmaz
            prev_gt, prev_tb = gt, tb
    return {"kombinasyon": 101 * 101, "monoton_ihlal_yonlu": viol_new,
            "monoton_ihlal_bugun": viol_old, "yon_ihlal_yonlu": dir_new}


def load_days(snap_dir, score_dir):
    score_days = sorted(f[:10] for f in os.listdir(score_dir) if f.endswith(".json") and len(f) == 15)
    scores = {d: json.load(open(os.path.join(score_dir, d + ".json")))["scores"] for d in score_days}
    days = []
    for f in sorted(os.listdir(snap_dir)):
        if not (f.endswith(".json") and len(f) == 15):
            continue
        d = f[:10]
        snap = json.load(open(os.path.join(snap_dir, f)))
        stocks = snap["stocks"] if isinstance(snap, dict) else snap
        if not any(s.get("adx") is not None for s in stocks):
            days.append((d, None, "ADX yok"))
            continue
        prior = [x for x in score_days if x <= d]
        sd = prior[-1] if prior else score_days[0]
        sc = scores[sd]
        rows = []
        for s in stocks:
            e = sc.get(s.get("ticker"))
            if not e or e.get("temel_analiz_skoru") is None:
                continue
            durum = s.get("signal")
            tg = None
            if durum in ("AL", "SAT"):
                tg = e.get("teknik_analiz_skoru") if sd == d else None
                if tg is None:
                    tg = compose_score(s.get("adx"), s.get("vol_ratio"), 3, bool(s.get("confirmed")),
                                       s.get("rsi"), durum)
            t = e["temel_analiz_skoru"]
            rows.append({"t": s["ticker"], "durum": durum, "tg": tg, "temel": t,
                         "dc": e.get("data_completeness"),
                         "eski": bp_bugun(t, tg), "yeni": bp_yonlu(t, durum, tg)})
        days.append((d, rows, sd))
    return days


def rank(rows, key):
    order = sorted(rows, key=lambda r: r["t"])
    order.sort(key=lambda r: -r[key])          # /api/tarama ile aynı: BP azalan, eşitlikte kod
    return {r["t"]: i + 1 for i, r in enumerate(order)}


def day_metrics(rows):
    m = {"n": len(rows)}
    tb = [r for r in rows if r["durum"] == "SAT"]
    m["durum"] = {k: sum(1 for r in rows if r["durum"] == k) for k in ("AL", "BEKLE", "SAT")}
    for k in ("eski", "yeni"):
        m[k] = {
            "n4_bp_gt_temel_tb": sum(1 for r in tb if r[k] > r["temel"]),
            "tb_bp_gt_yatay": sum(1 for r in tb if r[k] > bp_yonlu(r["temel"], "BEKLE", None)),
            "tb_bp_gt_50": sum(1 for r in tb if r[k] > 50),
            "halka_bp_eq_temel": sum(1 for r in rows if r[k] == r["temel"]),
            "halka_bp_eq_tg": sum(1 for r in rows if r["tg"] is not None and r[k] == r["tg"]),
            "bp_ge_70": sum(1 for r in rows if r[k] >= 70),
            "bp_ge_70_dc08": sum(1 for r in rows if r[k] >= 70 and (r["dc"] or 0) >= 0.8),
        }
        for label, pool in (("ilk20", rows), ("ilk20_dc08", [r for r in rows if (r["dc"] or 0) >= 0.8])):
            rk = rank(pool, k)
            top = [r for r in pool if rk[r["t"]] <= 20]
            m[k][label] = {d: sum(1 for r in top if r["durum"] == d) for d in ("AL", "BEKLE", "SAT")}
    m["bant_degisen"] = sum(1 for r in rows if band(r["eski"]) != band(r["yeni"]))
    m["yeni_esit_eski"] = sum(1 for r in rows if r["eski"] == r["yeni"])
    return m


def detail(rows, tickers=("THYAO", "ECZYT", "SMRTG", "MGROS")):
    rk_old, rk_new = rank(rows, "eski"), rank(rows, "yeni")
    pick = [r for r in rows if r["durum"] == "AL" or r["t"] in tickers]
    out = []
    for r in sorted(pick, key=lambda r: (r["durum"] != "AL", r["t"])):
        out.append({"t": r["t"], "durum": LABEL.get(r["durum"], r["durum"]), "temel": r["temel"], "tg": r["tg"],
                    "bp_eski": r["eski"], "bp_yeni": r["yeni"], "sira_eski": rk_old[r["t"]],
                    "sira_yeni": rk_new[r["t"]], "n": len(rows)})
    moves = {}
    for r in rows:
        key = (band(r["eski"]), band(r["yeni"]))
        if key[0] != key[1]:
            moves["%s→%s" % key] = moves.get("%s→%s" % key, 0) + 1
    spot = {k: max((r for r in rows if r["durum"] != "SAT" and (r["dc"] or 0) >= 0.8),
                   key=lambda r: (r[k], r["t"]))["t"] for k in ("eski", "yeni")}
    top20 = [(r["t"], r["durum"], r["yeni"]) for r in sorted(rows, key=lambda r: (-r["yeni"], r["t"]))[:20]]
    return {"hisseler": out, "bant_gecis": moves, "spotlight_dc08": spot, "ilk20_yeni": top20}


def canli(path, tickers=("THYAO", "ECZYT", "SMRTG")):
    """D-21 bayrak açıldıktan sonra: last_health_scores.json (ya da scores/<gün>.json)
    kayıtlarını kâhine karşı denetler. Beklenen: hata 0, bp_trend eksik 0, tb_bp_gt_yatay 0,
    yapisal_kopya 0. n4_bp_gt_temel_tb ve bp_eq_temel bilgi içindir (bkz. rapor)."""
    raw = json.load(open(path))
    entries = raw.get("scores", raw)
    entries = {t: (w.get("data") if isinstance(w.get("data"), dict) else w) for t, w in entries.items()}
    out = {"kayit": len(entries), "hata": [], "bp_trend_eksik": 0, "tb_bp_gt_yatay": 0,
           "n4_bp_gt_temel_tb": 0, "bp_eq_temel": 0, "yapisal_kopya": 0, "bp_ge_70": 0, "hisseler": []}
    for t, e in sorted(entries.items()):
        temel, bp, tg, tr = e.get("temel_analiz_skoru"), e.get("borsapusula_skoru"), e.get("teknik_analiz_skoru"), e.get("bp_trend")
        if temel is None:
            if bp is not None:
                out["hata"].append(t)          # yönlüde Temel yoksa BP üretilmez
            continue
        if not tr:
            out["bp_trend_eksik"] += 1         # bayrak kapalıyken üretilmiş kayıt
            continue
        durum = tr.get("durum")
        if bp != bp_yonlu(temel, durum, tg) or tr.get("pay") != trend_payi(durum, tg):
            out["hata"].append(t)
        out["tb_bp_gt_yatay"] += durum == "SAT" and bp > bp_yonlu(temel, "BEKLE", None)
        out["n4_bp_gt_temel_tb"] += durum == "SAT" and bp > temel
        out["bp_eq_temel"] += bp == temel
        out["yapisal_kopya"] += bool(e.get("partial")) and tg is None and bp == temel
        out["bp_ge_70"] += bp >= 70
        if durum == "AL" or t in tickers:
            out["hisseler"].append({"t": t, "durum": LABEL.get(durum, durum), "temel": temel, "tg": tg,
                                    "pay": tr.get("pay"), "bp": bp})
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--snapshots")
    ap.add_argument("--scores")
    ap.add_argument("--day", default=None, help="ayrıntı günü (varsayılan: son gün)")
    ap.add_argument("--json", default=None)
    ap.add_argument("--canli", default=None, metavar="last_health_scores.json",
                    help="D-21 sonrası canlı kayıt denetimi (simülasyon yerine)")
    a = ap.parse_args()
    if a.canli:
        print(json.dumps(canli(a.canli), ensure_ascii=False, indent=1))
        return
    if not (a.snapshots and a.scores):
        ap.error("--snapshots ve --scores gerekli (ya da --canli)")

    days = load_days(a.snapshots, a.scores)
    used = [(d, rows, sd) for d, rows, sd in days if rows]
    per_day = {d: day_metrics(rows) for d, rows, _ in used}
    agg = {}
    for k in ("eski", "yeni"):
        for f in ("n4_bp_gt_temel_tb", "tb_bp_gt_yatay", "tb_bp_gt_50", "halka_bp_eq_temel",
                  "halka_bp_eq_tg", "bp_ge_70", "bp_ge_70_dc08"):
            vals = [per_day[d][k][f] for d in per_day]
            agg["%s.%s" % (k, f)] = {"medyan": statistics.median(vals), "en_cok": max(vals), "toplam": sum(vals)}
        for f in ("ilk20", "ilk20_dc08"):
            tot = {s: sum(per_day[d][k][f][s] for d in per_day) for s in ("AL", "BEKLE", "SAT")}
            agg["%s.%s_ort" % (k, f)] = {s: round(v / len(per_day), 1) for s, v in tot.items()}
    agg["bant_degisen"] = {"medyan": statistics.median(per_day[d]["bant_degisen"] for d in per_day)}
    day = a.day or used[-1][0]
    rows = dict((d, r) for d, r, _ in used)[day]
    out = {"gun_sayisi": len(days), "kullanilan": len(used),
           "atlanan": [d for d, rows, why in days if not rows],
           "ilk_gun": used[0][0], "son_gun": used[-1][0],
           "temel_kaynak_gunleri": sorted({sd for _, _, sd in used}),
           "izgara": grid_proof(), "toplu": agg, "gun": day,
           "gun_olcum": per_day[day], "gun_ayrinti": detail(rows)}
    txt = json.dumps(out, ensure_ascii=False, indent=1)
    if a.json:
        with open(a.json, "w", encoding="utf-8") as f:
            f.write(txt)
    print(txt)


if __name__ == "__main__":
    main()
