#!/usr/bin/env python3
"""D-56 (Bülten v2): D-56 öncesi dondurulmuş Akşam Bültenlerine yeni alanları bir kez ekler.

Ne ekler (bulten.eksikleri_tamamla — var olan değere dokunmaz):
  bist100.seri/esik   chart_xu100.json geçmişi + günün donmuş resmi kapanışı (geçmiş yok/boş ya da
                      önceki işlem gününe ulaşmıyorsa yazılmaz, cümle de beklenir: sonraki koşu doldurur)
  sayim               günün donmuş ısı haritası görüntüsü (data/heatmap/<gün>.json)
  isi_haritasi_ozet   aynı görüntüden, piyasa değeriyle ağırlıklı (harita etiketiyle tek tanım)
                      + hisse_sayisi — TEK değiştirilen alan (toplama kuralı değişti, gün verisi değil)
  ozet_cumlesi/parcalar  yukarıdakilerden kural tabanlı cümle
  durum_degisimleri[].ad/fiyat/degisim_pct   resmi_kapanis/<gün>.json (o günün resmi kapanışı) +
                      ad: last_cache.json / ısı haritası satırı
  onemli_bildirimler[].onem_alanlar          data/kap_feed (kaydın onem'i); %0,1 altı gizlenir
  takvim_gunu         sonraki işlem günü (lib.trading_calendar)

Varsayılan KURU çalışma (yalnız rapor). --apply ile atomik yazar (tmp + os.replace; dosya
mtime'ı değişir, web işçileri bir sonraki istekte yeniden okur — restart gerekmez).

Kullanım (VPS):  cd /root/bist30 && venv/bin/python tools/bulten_v2_tamamla.py [--apply] [--gun 2026-09-28]
"""
import argparse
import json
import os
import sys
import tempfile
from datetime import date

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
import bulten  # noqa: E402


def _read(path):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return None


def _write_atomic(path, obj):
    d = os.path.dirname(path)
    fd, tmp = tempfile.mkstemp(dir=d, suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(obj, f, ensure_ascii=False, allow_nan=False, separators=(",", ":"))
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)


def _names(root, hm):
    out = {}
    cache = _read(os.path.join(root, "last_cache.json"))
    rows = cache.get("data") if isinstance(cache, dict) else cache
    for s in rows or []:
        if isinstance(s, dict) and s.get("ticker") and s.get("name"):
            out[s["ticker"]] = s["name"]
    for r in (hm or {}).get("rows") or []:
        if r.get("t") and r.get("n"):
            out.setdefault(r["t"], r["n"])
    return out


def _stocks(root, day, hm):
    rec = _read(os.path.join(root, "resmi_kapanis", day + ".json")) or {}
    names = _names(root, hm)
    out = {}
    for t, v in (rec.get("stocks") or {}).items():
        if not isinstance(v, dict):
            continue
        out[t] = {"name": names.get(t), "price": v.get("close"), "change_pct": v.get("change_pct")}
    return out


def _kap_by_href(root):
    try:
        import kap_feed
    except Exception as e:  # pragma: no cover - VPS'te var
        print("kap_feed içe aktarılamadı: %s (onem_alanlar atlanır)" % e)
        return None
    st = kap_feed.Store(os.path.join(root, "data", "kap_feed"))
    if not st.available():
        return None
    return {"/hisse/%s/bildirim/%d" % (it["ticker"], it["id"]): it for it in st.all_items()}


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=ROOT)
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--gun")
    a = ap.parse_args(argv)
    bdir = os.path.join(a.root, "data", "bulten")
    xu = (_read(os.path.join(a.root, "chart_xu100.json")) or {}).get("data") or {}
    ohlc = xu.get("ohlc") or []
    kap = _kap_by_href(a.root)
    try:
        from lib.trading_calendar import is_trading_day
    except Exception:
        is_trading_day = None
    n_changed = 0
    for day in bulten.days(bdir):
        if a.gun and day != a.gun:
            continue
        path = os.path.join(bdir, day + ".json")
        snap = _read(path)
        if not snap:
            print(day, "okunamadı, atlandı")
            continue
        hm = _read(os.path.join(a.root, "data", "heatmap", day + ".json"))
        onceki = bulten.onceki_islem_gunu(day, is_trading_day) if is_trading_day else None
        changed = bulten.eksikleri_tamamla(snap, heatmap_snap=hm, xu100_ohlc=ohlc,
                                           stocks=_stocks(a.root, day, hm), kap_by_href=kap,
                                           onceki_gun=onceki)
        if snap.get("takvim_gunu") is None and is_trading_day:
            snap["takvim_gunu"] = bulten.sonraki_islem_gunleri(day, 1, is_trading_day)[0]
            changed.append("takvim_gunu")
        print("%s %s | %s" % (day, ", ".join(changed) or "değişiklik yok", snap.get("ozet_cumlesi")))
        if changed and a.apply:
            _write_atomic(path, snap)
            n_changed += 1
    print("yazılan: %d%s" % (n_changed, "" if a.apply else " (kuru çalışma; --apply ile yazılır)"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
