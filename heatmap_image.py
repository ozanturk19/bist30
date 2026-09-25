"""D-54: BIST100 ısı haritası paylaşım görseli (Pillow) + kalıcı gün sayfası bağlamı.

Sözleşme (D-54 arka uç / ön yüz dalı ortak; adlar değişmez):
  /harita/<YYYY-AA-GG>.png       1200×630  bağlantı önizlemesi (og:image)
  /harita/<YYYY-AA-GG>-kare.png  1080×1350 telefon paylaşımı
  data/heatmap/<gün>.png ve <gün>-kare.png, EOD dondurmasından (data/heatmap/<gün>.json) hemen
  sonra BİR KEZ üretilir: atomik, var olanın üzerine yazılmaz; route eksikse kilit altında üretir.

Görsel = sitenin haritası (templates/_heatmap.html + static/js/bp-heatmap.js):
  * renk: nötr zemin --bp-surface3 + yön tonu (--bp-al / --bp-sat) bindirmesi,
    k = 0,16 + 0,84·min(|%|/3, 1)^0,72; bayat k×0,45 + çapraz tarama; etiket koyu/beyaz eşiği aynı;
  * geometri: sektör kutuları heatmap.layout (görselin kendi oranında), hisseler her sektörün iç
    kutusunda heatmap.squarify (2 px aralık, etiket şeridi, 6 px altı şerit ağırlık ikiye katlanır);
  * metin: "+%2,31" / "−%1,05" (Türkçe ondalık virgül, gerçek eksi işareti), tarih mutlak
    ("25 Eylül 2026"), veri kaynağı etiketi yok, yargı/işlem dili yok.
Yazı tipleri: assets/fonts/ (sitenin woff2'sinden TTF, servis edilmez; README orada). İşaret:
assets/brand/ (tools/brand-icons.mjs, logo v2 geometrisinden).
Saf modül (app.py'ye bağımlı değil, py3.9); aynı girdi → aynı PNG baytı.
"""
from __future__ import annotations

import fcntl
import io
import math
import os
import re
import tempfile
from contextlib import contextmanager
from datetime import date
from functools import lru_cache

from PIL import Image, ImageChops, ImageDraw, ImageFont

import heatmap

KINDS = {"og": (1200, 630), "kare": (1080, 1350)}
S = 2                        # süper örnekleme: çizim 2×, sonunda LANCZOS ile küçültülür
MINUS = "−"
_DAY = re.compile(r"[0-9]{4}-[0-9]{2}-[0-9]{2}")
_NAME = re.compile(r"([0-9]{4}-[0-9]{2}-[0-9]{2})(\.png|-kare\.png)?")
_HERE = os.path.dirname(os.path.abspath(__file__))
FONT_FILES = {"display": os.path.join(_HERE, "assets", "fonts", "bricolage-800.ttf"),
              "sans": os.path.join(_HERE, "assets", "fonts", "space-grotesk.ttf")}
MARK_FILES = {"sade": os.path.join(_HERE, "assets", "brand", "mark-sade-256.png"),   # <=32 px
              "tam": os.path.join(_HERE, "assets", "brand", "mark-256.png")}
DISCLAIMER = "Bilgi amaçlıdır, yatırım tavsiyesi değildir."
DOMAIN = ("borsa", "pusula", ".com")

# static/css/tokens.css (koyu tema tek tema)
BG = (14, 14, 18)            # --bp-bg
N = (32, 31, 33)             # --bp-surface3 = --hm-n (kutu nötr zemini)
TEXT = (229, 225, 228)       # --bp-text
TEXT2 = (199, 197, 205)      # --bp-text2
TEXT3 = (144, 144, 151)      # --bp-text3
AL = (0, 226, 144)           # --bp-al (yükseliş tonu) = --bp-logo-accent
SAT = (248, 81, 73)          # --bp-sat (düşüş tonu)
VIOLET = (124, 92, 255)      # --bp-art-violet (Data-Art parıltısı)
WHITE = (255, 255, 255)
DIR_RGB = {"up": AL, "dn": SAT, "neu": TEXT2, "na": TEXT2}

# Çizim ölçüleri (1× px). og: bağlantı önizlemesi, kare: telefon.
SPEC = {
    "og": dict(pad=40, top=34, title=(34, 44), sent=19, gap_head=18, gap_foot=16, bottom=26,
               gap_g=6, gap_t=2, label_h=19, label_fs=11, fs=(10.0, 26.0, 5.6), lim_fs=9,
               mark=30, mark_kind="sade", brand_fs=19, disc_fs=13, leg_bar=(200, 8), leg_fs=12),
    "kare": dict(pad=52, top=58, title=(38, 60), sent=26, gap_head=28, gap_foot=26, bottom=50,
                 gap_g=8, gap_t=3, label_h=26, label_fs=15, fs=(12.0, 34.0, 5.4), lim_fs=12,
                 mark=46, mark_kind="tam", brand_fs=28, disc_fs=18, leg_bar=(280, 12), leg_fs=17),
}


# ── Ad / tarih / metin (sayfa bağlamı da kullanır) ───────────────────────────
def valid_day(s):
    """Katı YYYY-AA-GG (yalnız ASCII rakam) ve gerçek takvim günü."""
    if not isinstance(s, str) or not _DAY.fullmatch(s):
        return False
    try:
        date.fromisoformat(s)
    except ValueError:
        return False
    return True


def parse_name(name):
    """/harita/<name>: '2026-09-25' → (gün, None) sayfa; '.png' → 'og'; '-kare.png' → 'kare';
    başka her şey (yol geçişi, boşluk, sondaki satır sonu, Unicode rakam) → None."""
    m = _NAME.fullmatch(name or "")
    if not m or not valid_day(m.group(1)):
        return None
    return m.group(1), {None: None, ".png": "og", "-kare.png": "kare"}[m.group(2)]


def file_name(day, kind):
    if not valid_day(day) or kind not in KINDS:
        raise ValueError("gecersiz gun/tur: %r %r" % (day, kind))
    return day + ("-kare.png" if kind == "kare" else ".png")


def image_path(dir_, day, kind):
    return os.path.join(dir_, file_name(day, kind))


def url(day, kind="og"):
    return "/harita/" + file_name(day, kind)


def day_label(day):
    """'2026-09-25' → '25 Eylül 2026'."""
    d = date.fromisoformat(day)
    return "%d %s %d" % (d.day, heatmap.MONTHS[d.month - 1], d.year)


def pct_text(v, frac=2):
    """Site bpf.pct_text ile aynı yuvarlama; eksi işareti U+2212: +%2,31 · −%1,05 · %0,00."""
    if v is None:
        return "—"
    r = round(v, frac)
    if r == 0:
        r = 0.0
    sign = "+" if r > 0 else (MINUS if r < 0 else "")
    return sign + "%" + ("%.*f" % (frac, abs(r))).replace(".", ",")


def poss(n):
    """Türkçe 3. tekil iyelik eki sayının okunuşuna göre (_heatmap.html _poss ile aynı): 64'ü, 33'ü, 3'ü, 6'sı."""
    u, t = n % 10, (n // 10) % 10
    if n == 0:
        return "ı"
    if u:
        return ["", "i", "si", "ü", "ü", "i", "sı", "si", "i", "u"][u]
    if t:
        return ["", "u", "si", "u", "ı", "si", "ı", "i", "i", "ı"][t]
    return "ü" if (n // 100) % 10 else "i"


def _counts(snap):
    c = snap.get("counts") or {}
    return int(c.get("up") or 0), int(c.get("down") or 0), int(c.get("flat") or 0)


def count_segments(snap, flat=True):
    """Veri cümlesi parçaları [(metin, rol)]; rol: txt | up | dn | neu. Boşsa []."""
    up, dn, fl = _counts(snap)
    n = int(snap.get("n") or len(snap.get("rows") or []))
    if not (up or dn or fl):
        return []
    seg = [("%d hissenin" % n, "txt")]
    if up == n:
        return seg + [(" tamamı ", "txt"), ("yükseldi", "up")]
    if dn == n:
        return seg + [(" tamamı ", "txt"), ("düştü", "dn")]
    parts = [(up, "up", "yükseldi"), (dn, "dn", "düştü")] + ([(fl, "neu", "değişmedi")] if flat else [])
    sep = " "
    for k, role, verb in parts:
        if k:
            seg += [(sep, "txt"), (str(k), role), ("'%s %s" % (poss(k), verb), "txt")]
            sep = ", "
    return seg


def share_text(snap):
    """'BIST100 · 25 Eylül kapanışı: 100 hissenin 64'ü yükseldi, 33'ü düştü.'"""
    head = "BIST100 · %s kapanışı" % (snap.get("asof_label") or heatmap.date_label(snap["asof"]))
    body = "".join(t for t, _ in count_segments(snap, flat=False))
    return (head + ": " + body + ".") if body else (head + ".")


def day_context(snap, days):
    """/harita/<gün> SSR bağlamı `harita_gun` (ön yüz şablonu harita_gun.html)."""
    day = snap["asof"]
    days = sorted(d for d in days if valid_day(d))
    prev = [d for d in days if d < day]
    nxt = [d for d in days if d > day]
    return {"date": day, "label": day_label(day), "prev": prev[-1] if prev else None,
            "next": nxt[0] if nxt else None, "og_image": url(day, "og"),
            "og_image_kare": url(day, "kare"), "share_text": share_text(snap)}


# ── Renk ölçeği (_heatmap.html ile aynı) ─────────────────────────────────────
def dir_cls(v, frac=2):
    """bpf.dir_class: görünen yuvarlamaya göre up | dn | neu (None → na)."""
    if v is None:
        return "na"
    r = round(v, frac)
    return "up" if r > 0 else ("dn" if r < 0 else "neu")


def tone(v, stale=False):
    """(sınıf, k, koyu_etiket): sınıf up|dn|neu|na; k bindirme opaklığı."""
    cls = dir_cls(v)
    k = 0.0
    if cls in ("up", "dn"):
        k = 0.16 + 0.84 * min(abs(round(v, 2)) / 3.0, 1.0) ** 0.72
    if stale:
        k *= 0.45
    dark = (cls == "up" and k >= 0.55) or (cls == "dn" and k >= 0.83)
    return cls, k, dark


def mix(a, b, k):
    return tuple(int(round(a[i] * (1 - k) + b[i] * k)) for i in range(3))


def tile_rgb(cls, k):
    return mix(N, AL if cls == "up" else SAT, k) if cls in ("up", "dn") else N


# ── Yazı tipi / ölçüm ─────────────────────────────────────────────────────────
@lru_cache(maxsize=96)
def _font(key, px, weight=400):
    f = ImageFont.truetype(FONT_FILES[key], size=max(1, int(round(px * S))))
    if key == "sans":
        f.set_variation_by_axes([weight])
    return f


def _w(text, key, px, weight=400, track=0.0):
    """Metin genişliği (1× px); track em cinsinden harf aralığı."""
    if not text:
        return 0.0
    f = _font(key, px, weight)
    return (f.getlength(text) + track * px * S * (len(text) - 1)) / S


def _fit(text, key, px, weight, width, track=0.0):
    """width'e sığan en uzun önek + '…' (hiç sığmıyorsa '')."""
    if _w(text, key, px, weight, track) <= width:
        return text
    for i in range(len(text) - 1, 0, -1):
        t = text[:i].rstrip() + "…"
        if _w(t, key, px, weight, track) <= width:
            return t
    return ""


class _Canvas:
    def __init__(self, w, h):
        self.W, self.H = w, h
        self.img = Image.new("RGB", (w * S, h * S), BG)
        self.d = ImageDraw.Draw(self.img)
        self.texts = []

    def text(self, x, y, s, key, px, fill, weight=400, anchor="la", track=0.0):
        """(x, y) 1× px; anchor Pillow anlamında. Çizilen her metin self.texts'e girer (dil taraması)."""
        if not s:
            return 0.0
        f = _font(key, px, weight)
        self.texts.append(s)
        if not track:
            self.d.text((x * S, y * S), s, font=f, fill=fill, anchor=anchor)
            return f.getlength(s) / S
        w = _w(s, key, px, weight, track)
        x0 = x - (w if anchor[0] == "r" else (w / 2 if anchor[0] == "m" else 0))
        a = "l" + anchor[1]
        for i, ch in enumerate(s):
            cx = x0 * S + f.getlength(s[:i]) + track * px * S * i
            self.d.text((cx, y * S), ch, font=f, fill=fill, anchor=a)
        return w

    def runs(self, x, y, runs, anchor="ls"):
        """Aynı taban çizgisinde renkli parçalar: [(metin, key, px, weight, fill)]."""
        for s, key, px, weight, fill in runs:
            x += self.text(x, y, s, key, px, fill, weight, anchor=anchor)
        return x


def _glow(img, cx, cy, r, rgb, alpha):
    """Data-Art parıltısı: yumuşak radyal renk (deterministik)."""
    size = max(2, int(r * 2 * S))
    g = Image.radial_gradient("L").resize((size, size), Image.Resampling.BILINEAR)
    g = g.point(lambda v: int(round(max(0.0, 1.0 - v / 255.0) ** 1.6 * alpha * 255)))
    layer = Image.new("RGB", (size, size), rgb)
    img.paste(layer, (int((cx - r) * S), int((cy - r) * S)), g)


@lru_cache(maxsize=4)
def _sheen_strip(alpha):
    """1×256 dikey maske: üstte alpha, %42'de 0 (CSS 155° parlaklık, dikey yaklaşımı)."""
    col = Image.new("L", (1, 256))
    col.putdata([int(round(max(0.0, 1.0 - (i / 255.0) / 0.42) * alpha * 255)) for i in range(256)])
    return col


def _tile(c, x0, y0, x1, y1, rgb, radius, sheen, hatch):
    """S× tam sayı köşeler; yuvarlatılmış kutu + parlaklık (+ bayat taraması)."""
    w, h = x1 - x0, y1 - y0
    if w <= 0 or h <= 0:
        return
    r = min(radius, w // 2, h // 2)
    c.d.rounded_rectangle((x0, y0, x1 - 1, y1 - 1), radius=r, fill=rgb)
    m = Image.new("L", (w, h), 0)
    ImageDraw.Draw(m).rounded_rectangle((0, 0, w - 1, h - 1), radius=r, fill=255)
    sh = ImageChops.multiply(_sheen_strip(sheen).resize((w, h), Image.Resampling.BILINEAR), m)
    c.img.paste(WHITE, (x0, y0, x1, y1), sh)
    if hatch:
        hm = Image.new("L", (w, h), 0)
        hd = ImageDraw.Draw(hm)
        step, lw = int(round(9.9 * S)), 2 * S
        for i in range(-h, w + h, step):
            hd.line((i, h, i + h, 0), fill=int(0.10 * 255), width=lw)
        c.img.paste(WHITE, (x0, y0, x1, y1), ImageChops.multiply(hm, m))


def _tri(c, x, y, size, up, fill):
    """▲/▼ (yazı tipinde glif yok): x,y 1× sol-üst, size 1× px."""
    s = size * S
    x, y = x * S, y * S
    pts = [(x, y + s), (x + s, y + s), (x + s / 2, y)] if up else [(x, y), (x + s, y), (x + s / 2, y + s)]
    c.d.polygon(pts, fill=fill)


# ── Treemap ──────────────────────────────────────────────────────────────────
def _squarify_px(nodes, x, y, w, h, gap, min_t):
    """nodes: [{t, v}] → her düğüme (x0, y0, x1, y1) S× tam sayı. bp-heatmap.js layoutTiles ile aynı
    kural: kutu gap/2 büyütülür, düğüm gap/2 içeri çekilir; min_t altı kutunun yerleşim ağırlığı
    ikiye katlanır (gerçek değer değişmez)."""
    h2 = gap / 2.0
    for n in nodes:
        n["lv"] = n["v"]
    for _ in range(6):
        nodes.sort(key=lambda n: (-n["lv"], n["t"]))
        rects = heatmap.squarify([n["lv"] for n in nodes], x - h2, y - h2, w + gap, h + gap)
        bad = False
        for n, (rx, ry, rw, rh) in zip(nodes, rects):
            n["x0"] = int(round((rx + h2) * S))
            n["y0"] = int(round((ry + h2) * S))
            n["x1"] = max(n["x0"], int(round((rx + rw - h2) * S)))
            n["y1"] = max(n["y0"], int(round((ry + rh - h2) * S)))
            if (n["x1"] - n["x0"]) < min_t * S or (n["y1"] - n["y0"]) < min_t * S:
                n["lv"] *= 2
                bad = True
        if not bad:
            break
    return nodes


def _draw_map(c, snap, X, Y, MW, MH, sp):
    rows = {r["t"]: r for r in snap.get("rows") or []}
    groups, _ = heatmap.layout(snap.get("rows") or [], MW, MH)
    gap_g, gap_t = sp["gap_g"], sp["gap_t"]
    Wg, Hg = MW + gap_g, MH + gap_g
    tiles_out = []
    for g in groups:
        gx0 = X + round(g["x"] / 100.0 * Wg)
        gy0 = Y + round(g["y"] / 100.0 * Hg)
        gx1 = max(gx0, X + round((g["x"] + g["w"]) / 100.0 * Wg - gap_g))
        gy1 = max(gy0, Y + round((g["y"] + g["h"]) / 100.0 * Hg - gap_g))
        gw, gh = gx1 - gx0, gy1 - gy0
        members = [r for r in rows.values() if r.get("g") == g["g"] and r.get("mcap")]
        lh = sp["label_h"] if (gh >= sp["label_h"] * 2.9 and gw >= 64) else 0
        if lh:
            _group_label(c, g["g"], members, gx0, gy0, gw, lh, sp)
        nodes = _squarify_px([{"t": r["t"], "v": r["mcap"]} for r in members],
                             gx0, gy0 + lh, gw, gh - lh, gap_t, 6)
        for n in nodes:
            r = rows[n["t"]]
            _draw_tile(c, r, n, sp)
            tiles_out.append({"t": n["t"], "x": n["x0"] / S, "y": n["y0"] / S,
                              "w": (n["x1"] - n["x0"]) / S, "h": (n["y1"] - n["y0"]) / S,
                              "tk": n.get("tk", False), "v": n.get("vv", False)})
    return tiles_out


def _group_label(c, name, members, x, y, w, lh, sp):
    fs = sp["label_fs"]
    s = sum(r["ch"]["d1"] * r["mcap"] for r in members if r["ch"].get("d1") is not None)
    ws = sum(r["mcap"] for r in members if r["ch"].get("d1") is not None)
    gch = s / ws if ws else None
    ch = pct_text(gch, 1) if gch is not None else ""
    cls = dir_cls(gch, 1)
    chw = _w(ch, "sans", fs, 600) if ch else 0
    base = y + lh * 0.72
    up = name.translate(str.maketrans("iı", "İI")).upper()
    label = _fit(up, "display", fs, 800, w - (chw + 8 if ch else 0) - 1, track=0.09)
    if not label:
        return
    lw = c.text(x, base, label, "display", fs, TEXT2, 800, anchor="ls", track=0.09)
    if ch and lw + 8 + chw <= w:
        c.text(x + lw + 8, base, ch, "sans", fs, {"up": AL, "dn": SAT}.get(cls, TEXT2), 600, anchor="ls")


def _draw_tile(c, r, n, sp):
    v = (r.get("ch") or {}).get("d1")
    stale = bool(r.get("stale"))
    cls, k, dark = tone(v, stale)
    rgb = tile_rgb(cls, k)
    x0, y0, x1, y1 = n["x0"], n["y0"], n["x1"], n["y1"]
    hatch = stale or cls == "na"
    _tile(c, x0, y0, x1, y1, rgb, 5 * S, 0.08 if hatch else 0.12, hatch)
    lim = r.get("lim") if r.get("lim") in ("tavan", "taban") else None
    if lim:   # site: iç kenar rgba(text,.6)
        c.d.rounded_rectangle((x0, y0, x1 - 1, y1 - 1), radius=min(5 * S, (x1 - x0) // 2, (y1 - y0) // 2),
                              outline=mix(rgb, TEXT, 0.6), width=int(1.5 * S))
    # Yazı: boyut kutu alanından (bp-heatmap.js: sqrt(w·h)/6,2, 9..24 px; görselde okunurluk için ölçek)
    w, h = (x1 - x0) / S, (y1 - y0) / S
    lo, hi, div = sp["fs"]
    fs = round(max(lo, min(hi, math.sqrt(w * h) / div)) * 2) / 2.0   # 0,5 px adım: az yazı tipi nesnesi
    fg = BG if dark else WHITE
    tk = r["t"]
    vt = pct_text(v) if v is not None else ""
    pad = max(6.0, fs * 0.42)
    tkw = _w(tk, "sans", fs, 700)
    vfs = fs * 0.74
    vw = _w(vt, "sans", vfs, 500)
    tk_ok = pad + tkw <= w - 3 and pad * 0.7 + fs * 1.05 <= h - 2
    v_ok = tk_ok and bool(vt) and pad + vw <= w - 3 and pad * 0.7 + fs * 1.05 + 3 + vfs * 1.1 <= h - 3
    x, y = x0 / S + pad, y0 / S + pad * 0.7
    if tk_ok:
        c.text(x, y, tk, "sans", fs, fg, 700, anchor="la")
        n["tk"] = True
    if v_ok:
        c.text(x, y + fs * 1.05 + 3, vt, "sans", vfs, mix(rgb, fg, 0.92), 500, anchor="la")
        n["vv"] = True
    if lim and tk_ok:
        lfs = sp["lim_fs"]
        txt = "TAVAN" if lim == "tavan" else "TABAN"
        bw = lfs * 0.9 + 4 + _w(txt, "sans", lfs, 700, 0.08) + 10
        bh = lfs + 6
        if pad + tkw + 6 + bw + 5 <= w and 5 + bh <= h - 2:
            bx1, by0 = x1 / S - 5, y0 / S + 5
            bx0 = bx1 - bw
            c.d.rounded_rectangle((bx0 * S, by0 * S, bx1 * S, (by0 + bh) * S), radius=4 * S,
                                  fill=mix(rgb, BG, 0.45))
            _tri(c, bx0 + 5, by0 + 3 + lfs * 0.1, lfs * 0.8, lim == "tavan", TEXT)
            c.text(bx0 + 5 + lfs * 0.9 + 4, by0 + 3, txt, "sans", lfs, TEXT, 700, anchor="la", track=0.08)


# ── Başlık / lejant / alt bilgi ──────────────────────────────────────────────
def _sentence_runs(snap, px):
    ROLE = {"txt": ("sans", 400, TEXT2), "up": ("sans", 600, AL), "dn": ("sans", 600, SAT),
            "neu": ("sans", 600, TEXT)}
    runs = [(t, ROLE[r][0], px, ROLE[r][1], ROLE[r][2]) for t, r in count_segments(snap)]
    xu = ((snap.get("xu100") or {}).get("ch") or {}).get("d1")
    rows = snap.get("rows") or []
    tv = sum(1 for r in rows if r.get("lim") == "tavan")
    tb = sum(1 for r in rows if r.get("lim") == "taban")
    extra = []
    if xu is not None:
        cls = dir_cls(xu)
        extra.append([("BIST100 ", "sans", px, 400, TEXT2),
                      (pct_text(xu), "sans", px, 600, {"up": AL, "dn": SAT}.get(cls, TEXT))])
    lim = []
    if tv:
        lim += [(str(tv), "sans", px, 600, TEXT), (" tavan", "sans", px, 400, TEXT2)]
    if tb:
        lim += ([(", ", "sans", px, 400, TEXT2)] if tv else []) + [(str(tb), "sans", px, 600, TEXT),
                                                                   (" taban", "sans", px, 400, TEXT2)]
    if lim:
        extra.append(lim)
    return runs, extra


def _wrap_runs(chunks, width):
    """chunks: [runs] (bölünmez öbekler, araya ' · '); satırlara böler."""
    lines, cur, cw = [], [], 0.0
    for ch in chunks:
        sep = [(" · ", ch[0][1], ch[0][2], 400, TEXT3)] if cur else []
        ww = sum(_w(t, k, p, wt) for t, k, p, wt, _ in sep + ch)
        if cur and cw + ww > width:
            lines.append(cur)
            cur, cw = [], 0.0
            sep = []
            ww = sum(_w(t, k, p, wt) for t, k, p, wt, _ in ch)
        cur += sep + ch
        cw += ww
    if cur:
        lines.append(cur)
    return lines


def _legend(c, x, y, sp, flags):
    """Renk ölçeği çubuğu + birimli işaretler + açıklama. y = çubuğun üstü. Genişlik döner."""
    bw, bh = sp["leg_bar"]
    fs = sp["leg_fs"]
    ticks = [pct_text(-3, 0), pct_text(-1.5, 1), "0", pct_text(1.5, 1), pct_text(3, 0)]
    tw = _legend_width(sp, flags)
    capw = tw - bw - 16 - sum(16 + fs + 6 + _w(lbl, "sans", fs, 400) for on, lbl in _SWATCHES(flags) if on)
    bar = Image.new("RGB", (int(bw * S), 1))
    stops = (SAT, N, AL)
    bar.putdata([mix(stops[0], stops[1], t / 0.5) if t < 0.5 else mix(stops[1], stops[2], (t - 0.5) / 0.5)
                 for t in (i / max(1, bw * S - 1) for i in range(int(bw * S)))])
    bar = bar.resize((int(bw * S), int(bh * S)))
    m = Image.new("L", bar.size, 0)
    ImageDraw.Draw(m).rounded_rectangle((0, 0, bar.size[0] - 1, bar.size[1] - 1), radius=bar.size[1] // 2, fill=255)
    c.img.paste(bar, (int(x * S), int(y * S)), m)
    ty = y + bh + 4
    for i, t in enumerate(ticks):
        tx = x + bw * i / 4.0
        c.text(tx, ty, t, "sans", fs * 0.92, TEXT3, 500, anchor="la" if i == 0 else ("ra" if i == 4 else "ma"))
    cx = x + bw + 16
    c.text(cx, y + bh / 2.0, LEG_CAP, "sans", fs, TEXT2, 500, anchor="lm")
    c.text(cx, ty, LEG_NOTE, "sans", fs * 0.92, TEXT3, 400, anchor="la")
    sx = cx + capw
    for on, lbl in _SWATCHES(flags):
        if not on:
            continue
        sx += 16
        _tile(c, int(sx * S), int((y - 2) * S), int((sx + fs) * S), int((y - 2 + fs) * S), N, 2 * S, 0.08, True)
        c.text(sx + fs + 6, y - 2 + fs / 2.0, lbl, "sans", fs, TEXT3, 400, anchor="lm")
        sx += fs + 6 + _w(lbl, "sans", fs, 400)
    return tw


@lru_cache(maxsize=4)
def _mark(kind, px):
    im = Image.open(MARK_FILES[kind]).convert("RGBA")
    return im.resize((int(px * S), int(px * S)), Image.Resampling.LANCZOS)


def _brand(c, x, y_mid, sp):
    m = _mark(sp["mark_kind"], sp["mark"])
    c.img.paste(m, (int(x * S), int((y_mid - sp["mark"] / 2.0) * S)), m)
    fs = sp["brand_fs"]
    tx = x + sp["mark"] + fs * 0.5
    base = y_mid + fs * 0.36
    for s, fill in zip(DOMAIN, (TEXT, AL, TEXT3)):
        tx += c.text(tx, base, s, "display", fs, fill, 800, anchor="ls")
    return tx - x


# ── Çizim ────────────────────────────────────────────────────────────────────
def render(snap, kind="og"):
    """(PIL.Image RGB W×H, meta). meta: texts (çizilen her metin), tiles [{t,x,y,w,h,tk,v}],
    map (x,y,w,h), size, legend True."""
    if kind not in KINDS:
        raise ValueError(kind)
    W, H = KINDS[kind]
    sp = SPEC[kind]
    c = _Canvas(W, H)
    P = sp["pad"]
    _glow(c.img, W * 0.18, -H * 0.05, max(W, H) * 0.42, VIOLET, 0.16)
    _glow(c.img, W * 0.92, H * 1.02, max(W, H) * 0.30, (34, 211, 238), 0.05)

    # Başlık: "BIST100 · 25 Eylül 2026 kapanışı" (tek satır, genişliğe sığdırılır)
    day = snap["asof"]
    t1, t2 = "BIST100", " · %s kapanışı" % day_label(day)
    lo, hi = sp["title"]
    tp = hi
    while tp > lo and _w(t1 + t2, "display", tp, 800, -0.03) > W - 2 * P:
        tp -= 1
    y = sp["top"]
    base = y + tp * 0.80
    x = P + c.text(P, base, t1, "display", tp, TEXT, 800, anchor="ls", track=-0.03)
    c.text(x, base, t2, "display", tp, TEXT3, 800, anchor="ls", track=-0.03)
    y = base + tp * 0.22

    # Veri cümlesi (+ BIST100 değişimi, tavan/taban)
    runs, extra = _sentence_runs(snap, sp["sent"])
    chunks = ([runs] if runs else []) + extra
    lines = _wrap_runs(chunks, W - 2 * P)
    lh = sp["sent"] * 1.42
    for ln in lines:
        y += lh
        c.runs(P, y - sp["sent"] * 0.30, ln)
    head_bottom = y + sp["gap_head"] - sp["sent"] * 0.1

    # Alt bilgi: og tek satır (işaret + alan adı · lejant · uyarı); kare iki satır.
    drawn = [r for r in snap.get("rows") or [] if r.get("mcap")]
    flags = {"stale": any(r.get("stale") for r in drawn),
             "na": any((r.get("ch") or {}).get("d1") is None for r in drawn)}
    bw, bh = sp["leg_bar"]
    leg_h = bh + 4 + sp["leg_fs"] * 1.2
    if kind == "og":
        foot_h = max(sp["mark"], leg_h)
        fy = H - sp["bottom"] - foot_h
        map_bottom = fy - sp["gap_foot"]
    else:
        foot_h = leg_h + 30 + sp["mark"]
        fy = H - sp["bottom"] - foot_h
        map_bottom = fy - sp["gap_foot"]
    X, Y = P, int(round(head_bottom))
    MW, MH = W - 2 * P, int(round(map_bottom - head_bottom))
    tiles = _draw_map(c, snap, X, Y, MW, MH, sp)

    if kind == "og":
        mid = fy + foot_h / 2.0
        _brand(c, P, mid, sp)
        c.text(W - P, mid, DISCLAIMER, "sans", sp["disc_fs"], TEXT3, 400, anchor="rm")
        dw = _w(DISCLAIMER, "sans", sp["disc_fs"])
        # lejant ortada: marka ile uyarı arasına ortalanır
        bwid = sp["mark"] + sp["brand_fs"] * 0.5 + sum(_w(s, "display", sp["brand_fs"], 800) for s in DOMAIN)
        lw = _legend_width(sp, flags)
        lx = P + bwid + ((W - P - dw) - (P + bwid) - lw) / 2.0
        _legend(c, lx, mid - leg_h / 2.0, sp, flags)
    else:
        _legend(c, P, fy, sp, flags)
        mid = fy + leg_h + 30 + sp["mark"] / 2.0
        _brand(c, P, mid, sp)
        c.text(W - P, mid, DISCLAIMER, "sans", sp["disc_fs"], TEXT3, 400, anchor="rm")

    out = c.img.resize((W, H), Image.Resampling.LANCZOS)
    return out, {"kind": kind, "size": (W, H), "texts": c.texts, "tiles": tiles,
                 "map": (X, Y, MW, MH), "legend": True, "flags": flags}


LEG_CAP, LEG_NOTE = "Gün sonu değişim", "Kutu büyüklüğü: piyasa değeri"


def _SWATCHES(flags):
    return ((flags.get("stale"), "Veri gecikmeli"), (flags.get("na"), "Değişim verisi yok"))


def _legend_width(sp, flags):
    fs = sp["leg_fs"]
    capw = max(_w(LEG_CAP, "sans", fs, 500), _w(LEG_NOTE, "sans", fs * 0.92, 400))
    return sp["leg_bar"][0] + 16 + capw + sum(16 + fs + 6 + _w(lbl, "sans", fs, 400)
                                              for on, lbl in _SWATCHES(flags) if on)


def render_png(snap, kind="og"):
    img, meta = render(snap, kind)
    buf = io.BytesIO()
    img.save(buf, format="PNG", optimize=True)
    return buf.getvalue(), meta


# ── Disk: bir kez üret, atomik yaz, üzerine yazma ────────────────────────────
@contextmanager
def _locked(path):
    fd = os.open(path, os.O_CREAT | os.O_RDWR, 0o644)
    try:
        fcntl.flock(fd, fcntl.LOCK_EX)
        yield
    finally:
        fcntl.flock(fd, fcntl.LOCK_UN)
        os.close(fd)


def _write_once(path, data):
    """tmp + os.link: yoksa yazar (True), varsa dokunmaz (False); .tmp artığı kalmaz."""
    d = os.path.dirname(path)
    fd, tmp = tempfile.mkstemp(dir=d, suffix=".tmp")
    try:
        with os.fdopen(fd, "wb") as f:
            f.write(data)
            f.flush()
            os.fsync(f.fileno())
        try:
            os.link(tmp, path)
        except FileExistsError:
            return False
    finally:
        os.unlink(tmp)
    return True


def ensure(dir_, day, load_snap, kinds=("og", "kare")):
    """Günün eksik görsellerini (yalnız eksikleri) dosya kilidi altında üretir; var olana dokunmaz.
    load_snap() yalnız bir şey eksikse çağrılır (donmuş görüntü + güncel grup). Yazılan yollar döner."""
    paths = [(k, image_path(dir_, day, k)) for k in kinds]
    if all(os.path.isfile(p) for _, p in paths):
        return []
    os.makedirs(dir_, exist_ok=True)
    written, snap = [], None
    with _locked(os.path.join(dir_, ".harita.lock")):
        for k, p in paths:
            if os.path.isfile(p):
                continue
            if snap is None:
                snap = load_snap()
                if not snap or snap.get("asof") != day:
                    raise ValueError("gorunum %s degil" % day)
            data, _ = render_png(snap, k)
            if _write_once(p, data):
                written.append(p)
    return written
