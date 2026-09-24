"""D-42: BIST100 ısı haritası verisi — gün sonu, resmi kapanıştan (D-04 18:35 turu)
sonra bir kez hesaplanır ve diske dondurulur; ertesi gün yeniden hesaplanmaz.

Sözleşme (CPO ön yüzü buna göre yazılıyor, alan adları değişmez): GET /api/heatmap
?universe=bist100 → {asof, asof_label, universe, n, counts, xu100, rows[], notes,
updated_at, frozen}; anasayfa SSR: heatmap / heatmap_groups / heatmap_tiles
(squarified treemap, 16:10 kutunun yüzdesi). Saf modül (app.py'ye bağımlı değil,
py3.9 yerel test); tek yan etki save_frozen() dosya yazımı.
"""
from __future__ import annotations

import json
import math
import os
import re
import tempfile
from datetime import date, timedelta

import sector_taxonomy

# D-23: grup (`g`) = sitenin tek sektör taksonomisi (sector_taxonomy.py; KAP alt sektörü → BIST
# sektör endeksine hizalı kova). /hisse sektör etiketi ve /tarama filtresiyle aynı ad.
OTHER = sector_taxonomy.OTHER
TREND = {"AL": "guclu", "SAT": "bozuk", "BEKLE": "yatay"}
MONTHS = ("Ocak", "Şubat", "Mart", "Nisan", "Mayıs", "Haziran", "Temmuz", "Ağustos",
          "Eylül", "Ekim", "Kasım", "Aralık")
SANITY_BAND = (0.8, 1.25)   # PD / (pay adedi × kapanış); dışı → işaret + adet×kapanış (plan D-42)
STALE_ABS_D1 = 10.5         # BIST ±%10 limitini aşan günlük değişim = seri kırığı
MAX_REF_GAP_DAYS = 12       # dönem referans barı hedef tarihten en fazla bu kadar eski (bayram tatili payı)
PERIODS = ("w1", "m1", "ytd", "y1")
# Pay piyasası fiyat adımı (TL): (üst sınır hariç, adım)
_TICKS = ((20.0, 0.01), (50.0, 0.02), (100.0, 0.05), (250.0, 0.10), (500.0, 0.25),
          (1000.0, 0.50), (2500.0, 1.00), (float("inf"), 2.50))
BOX_W, BOX_H = 160.0, 100.0  # 16:10; geometri gerçek oranda hesaplanır, çıktı yüzde
MIN_ROWS = 95                # kalite kapısı: bundan az dolu satırlı görüntü dondurulmaz
_DAY_FILE = re.compile(r"^\d{4}-\d{2}-\d{2}\.json$")


def date_label(iso):
    d = date.fromisoformat(iso[:10])
    return "%d %s" % (d.day, MONTHS[d.month - 1])


def tr_title(s):
    """'GIDA, İÇECEK VE TÜTÜN' → 'Gıda, İçecek ve Tütün' (Türkçe I/İ doğru)."""
    if not s:
        return None
    words = s.translate(str.maketrans("Iİ", "ıi")).lower().split()
    out = []
    for i, w in enumerate(words):
        if i and w in ("ve", "ile"):
            out.append(w)
        else:
            out.append({"i": "İ", "ı": "I"}.get(w[0], w[0].upper()) + w[1:])
    return " ".join(out)


def group_of(sector):
    """KAP alt sektörü → kova (boş/tanınmayan → 'Diğer')."""
    return sector_taxonomy.bucket(sector)


def regroup(rows, group_for):
    """Donmuş satırların `g` alanını güncel taksonomiye çeker (fiyat/değişim dokunulmaz): taksonomi
    değişince son görüntü ertesi günün dondurulmasını beklemeden sitenin geri kalanıyla aynı grubu
    gösterir. group_for(t) None dönerse satır olduğu gibi kalır. Değişen satır sayısı döner."""
    n = 0
    for r in rows or []:
        g = group_for(r.get("t"))
        if g and g != r.get("g"):
            r["g"] = g
            n += 1
    return n


def pct(a, b):
    if a is None or not b:
        return None
    return round((a / b - 1.0) * 100.0, 2)


def _minus_months(d, n):
    y, m = divmod(d.year * 12 + d.month - 1 - n, 12)
    m += 1
    last = (date(y + (m == 12), m % 12 + 1, 1) - timedelta(days=1)).day
    return date(y, m, min(d.day, last))


def ref_dates(asof):
    return {"w1": asof - timedelta(days=7), "m1": _minus_months(asof, 1),
            "ytd": date(asof.year - 1, 12, 31), "y1": _minus_months(asof, 12)}


def period_returns(series):
    """series: [(iso_tarih, kapanış)] artan; son bar = gün sonu resmi kapanış.
    {w1, m1, ytd, y1} yüzde (2 hane); referans barı yoksa/boşluk büyükse None."""
    pts = [(str(t)[:10], float(c)) for t, c in series or [] if c]
    out = dict.fromkeys(PERIODS)
    if len(pts) < 2:
        return out
    asof = date.fromisoformat(pts[-1][0])
    last = pts[-1][1]
    for k, ref in ref_dates(asof).items():
        cand = [p for p in pts[:-1] if p[0] <= ref.isoformat()]
        if not cand:
            continue
        rd, rc = cand[-1]
        if (ref - date.fromisoformat(rd)).days > MAX_REF_GAP_DAYS:
            continue
        out[k] = pct(last, rc)
    return out


def patch_series(series, asof_iso, close):
    """Seriyi asof'ta keser, son barı resmi kapanışla değiştirir/ekler."""
    pts = [(str(t)[:10], c) for t, c in series or [] if str(t)[:10] <= asof_iso]
    if close:
        if pts and pts[-1][0] == asof_iso:
            pts[-1] = (asof_iso, close)
        else:
            pts.append((asof_iso, close))
    return pts


def tick_size(price):
    for up, t in _TICKS:
        if price < up:
            return t
    return _TICKS[-1][1]


def limit_prices(prev):
    """(taban, tavan): baz ±%10, fiyat adımına içeri yuvarlanır."""
    up, dn = prev * 1.10, prev * 0.90
    tu, td = tick_size(up), tick_size(dn)
    return (round(math.ceil(dn / td - 1e-9) * td, 2), round(math.floor(up / tu + 1e-9) * tu, 2))


def limit_flag(close, prev):
    if not close or not prev:
        return None
    taban, tavan = limit_prices(prev)
    if close >= tavan - 1e-6:
        return "tavan"
    if close <= taban + 1e-6:
        return "taban"
    return None


def reported_mcap(fund):
    """Temel önbellekteki PD (TL) ya da None ({value, currency} ya da sayı)."""
    mc = (fund or {}).get("market_cap")
    if isinstance(mc, dict):
        if mc.get("currency") not in (None, "TRY"):
            return None
        mc = mc.get("value")
    return float(mc) if isinstance(mc, (int, float)) and mc > 0 else None


def mcap_tl(close, shares, reported):
    """(PD_TL, not). Kutu = resmi kapanış × pay adedi; PD/(adet×kapanış) bant dışıysa not."""
    if close and isinstance(shares, (int, float)) and shares > 0:
        m = close * shares
        if reported:
            r = reported / m
            if not (SANITY_BAND[0] <= r <= SANITY_BAND[1]):
                return m, "PD sanity %.2f -> adet*fiyat" % r
        return m, None
    if reported:
        return reported, "pay adedi yok -> PD"
    return None, "PD yok"


def build(asof_iso, members, official, rows, fund, scores, sectors, names, xu100_series, updated_at):
    """Sözleşme sözlüğü. official = resmi_kapanis arşiv kaydı; rows = {t: analiz satırı
    (bar_date, period_ret, signal, signal_bars, price)}; fund = {t: temel veri};
    scores = {t: BorsaPusula skoru}; sectors = {t: KAP alt sektörü}; names = {t: ad}."""
    offs = (official or {}).get("stocks") or {}
    out, notes = [], []
    for t in members:
        off, row = offs.get(t), (rows or {}).get(t) or {}
        if off:
            p, prev = off.get("close"), off.get("prev_close")
            d1 = pct(p, prev)
        else:
            p, prev, d1 = row.get("price"), None, None
            notes.append("%s: resmi kapanis yok" % t)
        if not p:
            notes.append("%s: fiyat yok, satir yok" % t)
            continue
        pr = row.get("period_ret") or {}
        ch = {"d1": d1}
        ch.update({k: pr.get(k) for k in PERIODS})
        stale = (not off) or row.get("bar_date") != asof_iso or (d1 is not None and abs(d1) > STALE_ABS_D1)
        m, why = mcap_tl(p, (fund.get(t) or {}).get("shares"), reported_mcap(fund.get(t)))
        if why:
            notes.append("%s: %s" % (t, why))
        sb = row.get("signal_bars")
        out.append({
            "t": t, "n": names.get(t) or t, "g": group_of(sectors.get(t)), "sub": tr_title(sectors.get(t)),
            "mcap": round(m / 1e9, 2) if m else None, "p": round(p, 2), "ch": ch,
            "bp": scores.get(t), "tr": TREND.get(row.get("signal")),
            "days": int(sb) if isinstance(sb, (int, float)) else None,
            "lim": limit_flag(p, prev) if off else None, "stale": bool(stale),
        })
    out.sort(key=lambda r: (-(r["mcap"] or 0), r["t"]))
    known = [r["ch"]["d1"] for r in out if r["ch"]["d1"] is not None]
    xi = ((official or {}).get("indices") or {}).get("XU100") or {}
    xs = patch_series(xu100_series, asof_iso, xi.get("close"))
    xprev = xi.get("prev_close") or (xs[-2][1] if xi.get("close") and len(xs) >= 2 else None)
    xch = {"d1": pct(xi.get("close"), xprev)}
    xch.update(period_returns(xs) if xi.get("close") else dict.fromkeys(PERIODS))
    return {
        "asof": asof_iso, "asof_label": date_label(asof_iso), "universe": "BIST100", "n": len(out),
        "counts": {"up": sum(1 for d in known if d > 0), "down": sum(1 for d in known if d < 0),
                   "flat": sum(1 for d in known if d == 0)},
        "xu100": {"close": xi.get("close"), "ch": xch},
        "rows": out, "notes": notes, "updated_at": updated_at, "frozen": True,
    }


def quality(snap):
    """(ok, neden): eksik görüntü dondurulmaz (önceki gün servis edilmeye devam eder)."""
    rows = snap.get("rows") or []
    full = [r for r in rows if r.get("mcap") and r["ch"].get("d1") is not None]
    if len(full) < MIN_ROWS:
        return False, "%d/%d satirda PD ve d1 dolu (< %d)" % (len(full), len(rows), MIN_ROWS)
    return True, "ok"


# ── Squarified treemap (Bruls, Huizing, van Wijk 2000) ────────────────────────
def _layout(sizes, x, y, dx, dy):
    out = []
    if dx >= dy:
        w = sum(sizes) / dy
        for s in sizes:
            out.append((x, y, w, s / w))
            y += s / w
    else:
        h = sum(sizes) / dx
        for s in sizes:
            out.append((x, y, s / h, h))
            x += s / h
    return out


def _leftover(sizes, x, y, dx, dy):
    if dx >= dy:
        w = sum(sizes) / dy
        return x + w, y, dx - w, dy
    h = sum(sizes) / dx
    return x, y + h, dx, dy - h


def _worst(sizes, x, y, dx, dy):
    return max(max(w / h, h / w) for _, _, w, h in _layout(sizes, x, y, dx, dy))


def squarify(values, x, y, dx, dy):
    """values azalan sırada, pozitif → [(x, y, w, h)]; alanlar değerle orantılı, dikdörtgeni tam doldurur."""
    total = float(sum(values))
    sizes = [v * dx * dy / total for v in values]
    rects = []
    while sizes:
        i = 1
        while i < len(sizes) and _worst(sizes[:i], x, y, dx, dy) >= _worst(sizes[:i + 1], x, y, dx, dy):
            i += 1
        rects += _layout(sizes[:i], x, y, dx, dy)
        x, y, dx, dy = _leftover(sizes[:i], x, y, dx, dy)
        sizes = sizes[i:]
    return rects


def _pct_rect(x, y, w, h):
    return {"x": round(x / BOX_W * 100, 3), "y": round(y / BOX_H * 100, 3),
            "w": round(w / BOX_W * 100, 3), "h": round(h / BOX_H * 100, 3)}


def layout(rows):
    """(heatmap_groups, heatmap_tiles): gruplar toplam PD'ye, kutular grup içinde PD'ye göre azalan."""
    by_g = {}
    for r in rows or []:
        if r.get("mcap") and r["mcap"] > 0:
            by_g.setdefault(r["g"], []).append(r)
    order = sorted(by_g.items(), key=lambda kv: (-sum(r["mcap"] for r in kv[1]), kv[0]))
    if not order:
        return [], []
    groups, tiles = [], []
    grects = squarify([sum(r["mcap"] for r in v) for _, v in order], 0.0, 0.0, BOX_W, BOX_H)
    for (g, members), (gx, gy, gw, gh) in zip(order, grects):
        groups.append(dict({"g": g}, **_pct_rect(gx, gy, gw, gh)))
        ms = sorted(members, key=lambda r: (-r["mcap"], r["t"]))
        for r, rect in zip(ms, squarify([r["mcap"] for r in ms], gx, gy, gw, gh)):
            tiles.append(dict({"t": r["t"], "g": g}, **_pct_rect(*rect)))
    return groups, tiles


# ── Donmuş görüntü (disk) ─────────────────────────────────────────────────────
def json_safe(o):
    """NaN/±inf → None, numpy skaler → Python skaleri (anasayfa `tojson` ve JSON.parse güvenli)."""
    if isinstance(o, dict):
        return {str(k): json_safe(v) for k, v in o.items()}
    if isinstance(o, (list, tuple)):
        return [json_safe(v) for v in o]
    if hasattr(o, "item") and not isinstance(o, (str, bytes)):
        try:
            o = o.item()
        except (TypeError, ValueError):
            return None
    if isinstance(o, float) and not math.isfinite(o):
        return None
    return o


def save_frozen(snap, dir_):
    """<dir>/<asof>.json atomik ve YALNIZ YOKSA yazılır (os.link: var olanın üzerine yazmaz).
    Yazıldıysa yol, o gün zaten donmuşsa None. NaN yazılmaz (allow_nan=False)."""
    os.makedirs(dir_, exist_ok=True)
    snap = json_safe(snap)
    path = os.path.join(dir_, "%s.json" % snap["asof"])
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


def latest_path(dir_):
    try:
        days = sorted(n for n in os.listdir(dir_) if _DAY_FILE.match(n))
    except OSError:
        return None
    return os.path.join(dir_, days[-1]) if days else None
