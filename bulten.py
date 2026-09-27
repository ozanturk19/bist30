"""D-45(c): Akşam Bülteni — resmi kapanış turundan (D-04c) sonra bir kez üretilip
data/bulten/<gün>.json'a dondurulur. Sözleşme (CPO buna göre yazar): GET
/api/bulten/<tarih> -> {tarih, bist100, hareketliler, durum_degisimleri,
isi_haritasi_ozet, onemli_bildirimler, yarin_takvim, updated_at, frozen}.
Saf modül (app.py'ye bağımlı değil); dondurma heatmap.py'nin <gün>.json-yoksa-yaz
desenini tekrarlar (os.link ile üzerine yazmaz), "tarih" alanına göre.
Ürün dili: AL/SAT/yön yok — durum adları business_rules.SIGNAL_LABELS'tan.
"""
from __future__ import annotations

import json
import os
import re
import tempfile

SIGNAL_LABELS = {"AL": "Güçlü Trend", "SAT": "Trend Bozuldu", "BEKLE": "Yatay"}
_DAY_FILE = re.compile(r"^[0-9]{4}-[0-9]{2}-[0-9]{2}\.json\Z")


def _index_row(rec, code):
    row = ((rec or {}).get("indices") or {}).get(code) or {}
    close, prev = row.get("close"), row.get("prev_close")
    chg = round((close - prev) / prev * 100, 2) if close and prev else None
    return {"kapanis": close, "degisim_pct": chg}


def durum_degisimleri(changes):
    """changes: [{ticker, old, new}] (resmi kapanış sinyali, önceki gün snapshot'ına göre).
    AL/SAT kodları kanonik etikete çevrilir; etiket değişmeyen (ör. iki BEKLE alt durumu) atılır."""
    out = []
    for c in changes or []:
        old_lbl = SIGNAL_LABELS.get(c.get("old"))
        new_lbl = SIGNAL_LABELS.get(c.get("new"))
        if not new_lbl or not old_lbl or old_lbl == new_lbl:
            continue
        out.append({"ticker": c["ticker"], "onceki": old_lbl, "yeni": new_lbl})
    return out


def isi_haritasi_ozet(heatmap_snap):
    """Sektör başına ortalama günlük değişim (donmuş ısı haritası görüntüsünden; D-42)."""
    if not heatmap_snap:
        return []
    groups = {}
    for r in heatmap_snap.get("rows") or []:
        g = r.get("g")
        d1 = (r.get("ch") or {}).get("d1")
        if not g or r.get("stale") or d1 is None:
            continue
        groups.setdefault(g, []).append(d1)
    out = [{"sektor": g, "ortalama_degisim_pct": round(sum(v) / len(v), 2)} for g, v in groups.items()]
    out.sort(key=lambda x: -x["ortalama_degisim_pct"])
    return out


def onemli_bildirimler(kap_items, n=5):
    """kap_items: kap_feed.public_item(...) çıktısı, o günün rutin-olmayan bildirimleri.
    Sıra: önem oranı (varsa) azalan, sonra en yeni. onem henüz çoğu kayıtta boş
    (metin geri beslemesi birkaç gün sürer) — o durumda yalnız zaman sırası geçerli."""
    items = sorted(
        kap_items or [],
        key=lambda it: ((it.get("onem") or {}).get("pct") or 0, it.get("date") or ""),
        reverse=True,
    )[:n]
    return [{
        "ticker": it.get("ticker"), "company": it.get("company"), "title": it.get("title"),
        "href": it.get("href"), "onem": (it.get("onem") or {}).get("txt"),
    } for it in items]


def yarin_takvim(events, next_day_iso):
    """events: takvim.build()['events'] (bilanço/temettü/makro); yalnız ertesi işlem günü."""
    return [{
        "kind": e.get("kind"), "ticker": e.get("ticker"), "title": e.get("title"),
        "period": e.get("period"), "time": e.get("time"),
    } for e in (events or []) if e.get("date") == next_day_iso]


def build(day_iso, rec, movers, changes, heatmap_snap, kap_items, takvim_events, next_day_iso, updated_at):
    return {
        "tarih": day_iso,
        "bist100": _index_row(rec, "XU100"),
        "hareketliler": movers or {"up": [], "down": []},
        "durum_degisimleri": durum_degisimleri(changes),
        "isi_haritasi_ozet": isi_haritasi_ozet(heatmap_snap),
        "onemli_bildirimler": onemli_bildirimler(kap_items),
        "yarin_takvim": yarin_takvim(takvim_events, next_day_iso),
        "updated_at": updated_at,
        "frozen": True,
    }


# ── Donmuş görüntü (disk) ─────────────────────────────────────────────────────
def save_frozen(snap, dir_):
    """<dir>/<tarih>.json atomik ve YALNIZ YOKSA yazılır (os.link: var olanın üzerine
    yazmaz). Yazıldıysa yol, o gün zaten donmuşsa None."""
    os.makedirs(dir_, exist_ok=True)
    path = os.path.join(dir_, "%s.json" % snap["tarih"])
    if os.path.exists(path):
        return None
    fd, tmp = tempfile.mkstemp(dir=dir_, suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(snap, f, ensure_ascii=False, allow_nan=False, separators=(",", ":"))
            f.flush()
            os.fsync(f.fileno())
        try:
            os.link(tmp, path)
        except FileExistsError:
            return None
    finally:
        os.unlink(tmp)
    return path


def days(dir_):
    """Donmuş görüntüsü olan günler, artan ('2026-09-25', ...); klasör yoksa []."""
    try:
        return sorted(n[:-5] for n in os.listdir(dir_) if _DAY_FILE.match(n))
    except OSError:
        return []


def latest_path(dir_):
    d = days(dir_)
    return os.path.join(dir_, d[-1] + ".json") if d else None
