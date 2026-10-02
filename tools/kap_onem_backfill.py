"""K20(a/b) backfill: pick_amount'un "Toplam Tutar" onceligi (f54c70d, 30.09) ve
parse_detail'in tablo satirlarini "Baslik: Deger" metnine cevirmesi (K20(a)) deploy'dan
ONCE enrich edilmis kayitlarin onbellekteki `onem`/`ozet` alanlarini degistirmez --
Store.merge eski onem/ozet'i hep korur (bildirim metni bir kez cekilir, degismez ilkesi).
Bu, dogru "Toplam Tutar" yerine yanlislikla "Nominal"/"Beher Pay Fiyati" secilmis eski
kayitlarda (ornek: BERA 1667811 "%0,0" -> olmasi gereken "%1,3") kalici hataya yol acar.

Bu betik `doc` onbellegindeki fields'i YENIDEN CEKMEDEN (KAP'a agi yalnizca onbellek
eksikse dokunulur -- burada dokunulmaz), guncel pick_amount/compute_onem/summary_sentence
ile onem+ozet'i yeniden hesaplar ve degisenleri Store.merge ile yazar.

Varsayilan kuru kosu (rapor). `--apply` ile yazar. Sirket adi mevcut ozet metninden
("Ad, ... tarihinde") cikarilir (app.py import edilmez -- D-20 modul-seviyesi thread
yan etkisinden kacinmak icin).

Kullanim: python3 tools/kap_onem_backfill.py [--apply] [--kap-fin-dir DIR]
"""
from __future__ import annotations

import argparse
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

import kap_feed as kf  # noqa: E402


def _company_from_ozet(ozet):
    if not ozet or "," not in ozet:
        return None
    return ozet.split(",", 1)[0].strip()


def _fx_of(old_onem):
    fx = (old_onem or {}).get("fx")
    if not fx:
        return None, None
    return fx.get("rate"), fx.get("date")


def recompute(store, kap_fin_dir=None):
    """[(item, eski_onem, yeni_onem, yeni_ozet), ...] -- yalnizca DEGISENLER."""
    out = []
    for it in store.all_items():
        subject = it.get("subject")
        if not it.get("doc") or it.get("onem") is None or subject not in kf.ONEM_SUBJECTS:
            continue
        doc = store.doc(it["id"])
        if not doc:
            continue
        amount = kf.pick_amount(subject, it.get("title") or "", doc)
        old_onem = it["onem"]
        if not amount:
            new_onem = None
        else:
            fx_rate, fx_date = _fx_of(old_onem)
            if amount["cur"] != "TRY" and not fx_rate:
                continue  # tarihsel kur yeniden cekilmez; degistirmeden atla
            revenue = kf.annual_revenue(it["ticker"], kap_fin_dir)
            new_onem = kf.compute_onem(amount, revenue, subject, fx_rate=fx_rate, fx_date=fx_date)
        old_pct = (old_onem or {}).get("pct")
        new_pct = (new_onem or {}).get("pct")
        if old_pct == new_pct and bool(old_onem) == bool(new_onem):
            continue
        company = _company_from_ozet(it.get("ozet"))
        new_ozet = kf.summary_sentence(it, company, new_onem) if company else it.get("ozet")
        out.append((it, old_onem, new_onem, new_ozet))
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--apply", action="store_true", help="degisiklikleri yaz (varsayilan: kuru kosu)")
    ap.add_argument("--kap-fin-dir", default=None, help="D-40a0 data/kap_fin dizini (varsayilan: kf varsayilani)")
    args = ap.parse_args()

    store = kf.Store()
    if not store.available():
        print("kap_feed store bos/yok: %s" % store.base)
        return 1
    changes = recompute(store, args.kap_fin_dir)
    print("%d kayitta onem degisiyor" % len(changes))
    for it, old_onem, new_onem, _ in changes:
        old_txt = (old_onem or {}).get("txt")
        new_txt = (new_onem or {}).get("txt")
        print("  %d %-8s %s -> %s" % (it["id"], it["ticker"], old_txt, new_txt))
    if not changes:
        return 0
    if not args.apply:
        print("kuru kosu -- yazmak icin --apply")
        return 0
    updated = []
    for it, _, new_onem, new_ozet in changes:
        it2 = dict(it)
        it2["onem"] = new_onem
        if new_ozet:
            it2["ozet"] = new_ozet
        updated.append(it2)
    n = store.merge(updated)
    print("merge: %d ay parcasi guncellendi" % n)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
