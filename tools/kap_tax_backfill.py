"""D-40b CPO-1826 adim (b): `tax_expense` (IND_ITEMS'a bugun eklendi, abda137e) mevcut
data/kap_fin/<T>.json kayitlarina geri doldurulur.

Ag cagrisi YOK -- yalniz data/kap_fin/raw/<idx>.html.gz onbellegi (zaten tum BS/IS/CF
tablolarini tutar, IND_ITEMS'a gore onceden filtrelenmemis) guncel kap_financials.IND_ITEMS
ile yeniden ayristirilir (kf.build_report, meta mevcut kayittan: idx/fy/period/publish).

Guvenlik: her raporun TUM diger alanlari eski ciktiyla birebir ayni kalmali -- yalniz
'items' sozlugune yeni alan(lar) eklenir (old None -> new deger). Beklenmeyen bir fark
(top-level ya da var olan bir alanin degismesi) bulunursa o rapora DOKUNULMAZ, rapor
edilir -- elle incelenmeden yazilmaz.

Varsayilan kuru kosu. `--apply` ile data/kap_fin/<T>.json dosyalarina yazar.

Kullanim: python3 tools/kap_tax_backfill.py [--apply] [TICKER ...]
"""
from __future__ import annotations

import argparse
import gzip
import json
import os
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

import kap_financials as kf  # noqa: E402

RAW = os.path.join(kf.DATA_DIR, "raw")


def atomic_write(path, text):
    d = os.path.dirname(path)
    fd, tmp = tempfile.mkstemp(dir=d)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(text)
        os.replace(tmp, path)
    except Exception:
        os.unlink(tmp)
        raise


def diff_keys(old, new):
    """old/new rapor sozlugu -- items disindaki alanlarda fark var mi, items'ta
    hangi anahtarlar degisti/eklendi (beklenen: yalniz yeni alan eklenmesi)."""
    top_diff = [k for k in old if k != "items" and old.get(k) != new.get(k)]
    item_changed = []
    for k in set(old.get("items", {})) | set(new.get("items", {})):
        ov, nv = old.get("items", {}).get(k), new.get("items", {}).get(k)
        if ov != nv:
            item_changed.append((k, ov is None, nv is None))
    return top_diff, item_changed


def process_file(path, apply_):
    with open(path, encoding="utf-8") as f:
        doc = json.load(f)
    ticker, sector = doc.get("ticker"), doc.get("sector")
    reports = doc.get("reports", [])
    changed, newly_filled, unexpected_diffs, errors = 0, [], [], []
    for i, rep in enumerate(reports):
        idx = rep["idx"]
        raw_path = os.path.join(RAW, "%s.html.gz" % idx)
        if not os.path.exists(raw_path):
            errors.append((idx, "no_raw_cache"))
            continue
        try:
            with gzip.open(raw_path, "rt", encoding="utf-8") as f:
                html = f.read()
            meta = {"idx": idx, "fy": rep["fy"], "period": rep["period"], "publish": rep.get("publish")}
            new_rep = kf.build_report(html, meta, ticker, sector)
        except Exception as e:
            errors.append((idx, "%s: %s" % (type(e).__name__, e)))
            continue
        top_diff, item_changed = diff_keys(rep, new_rep)
        unexpected = [c for c in item_changed if not (c[1] and c[2] is False)]
        if top_diff or unexpected:
            unexpected_diffs.append((idx, top_diff, unexpected))
            continue
        if item_changed:
            newly_filled.append((idx, [c[0] for c in item_changed]))
            reports[i] = new_rep
            changed += 1
    if changed and apply_:
        atomic_write(path, json.dumps(doc, ensure_ascii=False, indent=1))
    return {"ticker": ticker, "n_reports": len(reports), "changed": changed,
            "newly_filled": newly_filled, "unexpected_diffs": unexpected_diffs, "errors": errors}


def main():
    p = argparse.ArgumentParser()
    p.add_argument("tickers", nargs="*")
    p.add_argument("--apply", action="store_true")
    a = p.parse_args()
    files = (
        [os.path.join(kf.DATA_DIR, "%s.json" % t) for t in a.tickers]
        if a.tickers
        else sorted(
            os.path.join(kf.DATA_DIR, f) for f in os.listdir(kf.DATA_DIR) if f.endswith(".json")
        )
    )
    tot_reports = tot_changed = tot_tax_filled = 0
    all_unexpected, all_errors = [], []
    for path in files:
        if not os.path.exists(path):
            print("SKIP (yok): %s" % path)
            continue
        r = process_file(path, a.apply)
        tot_reports += r["n_reports"]
        tot_changed += r["changed"]
        tot_tax_filled += sum(1 for _, keys in r["newly_filled"] if "tax_expense" in keys)
        if r["unexpected_diffs"]:
            all_unexpected.append((r["ticker"], r["unexpected_diffs"]))
        if r["errors"]:
            all_errors.append((r["ticker"], r["errors"]))
    print("=== D-40b CPO-1826 tax_expense backfill (%s) ===" % ("YAZILDI" if a.apply else "KURU KOSU"))
    print("dosya: %d, toplam rapor: %d, degisen rapor: %d, tax_expense dolan: %d"
          % (len(files), tot_reports, tot_changed, tot_tax_filled))
    if all_unexpected:
        print("BEKLENMEYEN FARK (%d hisse, dokunulmadi):" % len(all_unexpected))
        for tk, diffs in all_unexpected[:10]:
            print("  %s: %s" % (tk, diffs))
    if all_errors:
        print("HATA (%d hisse):" % len(all_errors))
        for tk, errs in all_errors[:10]:
            print("  %s: %s" % (tk, errs))


if __name__ == "__main__":
    main()
