"""D-54 — paylaşılabilir ısı haritası: PNG görsel (1200×630 + 1080×1350), katı tarih/ad, sayfa
bağlamı, bir kez üret + atomik yaz, site renk ölçeği ve veri cümlesi eşliği.

Fikstür tests/fixtures/heatmap_20260925.json = VPS data/heatmap/2026-09-25.json (canlı donmuş
görüntü, 25.09 20:2x salt-okur kopya; D-06 bar_date biçimi yüzünden 100/100 "bayat" işaretli —
bayat onarımı _fixed() ile, VPS tek seferlik adımla aynı kural).
"""
import hashlib
import io
import json
import os
import re
import sys

import jinja2
import pytest
from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
import heatmap as hm  # noqa: E402
import heatmap_image as hi  # noqa: E402

FX_PATH = os.path.join(ROOT, "tests", "fixtures", "heatmap_20260925.json")
PY310 = pytest.mark.skipif(sys.version_info < (3, 10), reason="app.py 3.10+ ister")
# Görselde asla: işlem/hedef dili, göreli zaman, "Ücretsiz", veri kaynağı etiketi (kanon §2–§3, D-54).
BANNED = re.compile(r"\b(AL|SAT|BEKLE|al|sat)\b|Ücretsiz|ücretsiz|\b(bugün|Bugün|dün|Dün|yarın|Yarın)\b|"
                    r"Borsa İstanbul|\bBIST verisi|\bKAP\b|Yahoo|[Kk]aynak|[Hh]edef|kâr al|TP[12]|stop")


def _fx():
    with open(FX_PATH, encoding="utf-8") as f:
        return json.load(f)


def _fixed():
    s = _fx()
    for r in s["rows"]:
        r["stale"] = r["ch"]["d1"] is None or abs(r["ch"]["d1"]) > hm.STALE_ABS_D1
    return s


# ── ad / tarih doğrulama (yol güvenliği) ─────────────────────────────────────
@pytest.mark.parametrize("name,want", [
    ("2026-09-25", ("2026-09-25", None)),
    ("2026-09-25.png", ("2026-09-25", "og")),
    ("2026-09-25-kare.png", ("2026-09-25", "kare")),
    ("2024-02-29.png", ("2024-02-29", "og")),
    ("2026-02-30.png", None), ("2026-13-01", None), ("2026-9-25", None), ("26-09-25", None),
    ("2026-09-25.PNG", None), ("2026-09-25-KARE.png", None), ("2026-09-25-kare", None),
    ("2026-09-25.png.png", None), ("2026-09-25.json", None), ("2026-09-25\n", None),
    ("2026-09-25.png\n", None), ("../2026-09-25.png", None), ("2026-09-25/../x.png", None),
    ("٢٠٢٦-09-25.png", None), ("son.png", None), ("", None), (None, None),
])
def test_parse_name_is_strict(name, want):
    assert hi.parse_name(name) == want


def test_file_names_and_paths_refuse_bad_input(tmp_path):
    assert hi.file_name("2026-09-25", "og") == "2026-09-25.png"
    assert hi.file_name("2026-09-25", "kare") == "2026-09-25-kare.png"
    assert hi.url("2026-09-25") == "/harita/2026-09-25.png"
    for day, kind in (("../../etc/passwd", "og"), ("2026-09-25", "x"), ("2026-02-30", "og")):
        with pytest.raises(ValueError):
            hi.image_path(str(tmp_path), day, kind)


# ── metin ────────────────────────────────────────────────────────────────────
def test_tr_number_format_and_possessive():
    assert hi.pct_text(2.314) == "+%2,31"
    assert hi.pct_text(-1.05) == "−%1,05"
    assert hi.pct_text(-0.004) == "%0,00" and hi.pct_text(0) == "%0,00"
    assert hi.pct_text(-3, 0) == "−%3" and hi.pct_text(1.5, 1) == "+%1,5"
    assert [hi.poss(n) for n in (64, 33, 3, 6, 10, 100, 40, 0, 1, 2)] == \
        ["ü", "ü", "ü", "sı", "u", "ü", "ı", "ı", "i", "si"]
    assert hi.day_label("2026-09-25") == "25 Eylül 2026" and hi.day_label("2027-01-02") == "2 Ocak 2027"


def test_share_text_and_day_context():
    s = _fx()
    assert hi.share_text(s) == "BIST100 · 25 Eylül kapanışı: 100 hissenin 64'ü yükseldi, 33'ü düştü."
    ctx = hi.day_context(s, ["2026-09-23", "2026-09-25", "2026-09-24", "x", "2026-09-26"])
    assert ctx == {"date": "2026-09-25", "label": "25 Eylül 2026", "prev": "2026-09-24", "next": "2026-09-26",
                   "og_image": "/harita/2026-09-25.png", "og_image_kare": "/harita/2026-09-25-kare.png",
                   "share_text": "BIST100 · 25 Eylül kapanışı: 100 hissenin 64'ü yükseldi, 33'ü düştü."}
    ctx = hi.day_context(s, ["2026-09-25"])
    assert ctx["prev"] is None and ctx["next"] is None
    allup = dict(s, counts={"up": 100, "down": 0, "flat": 0})
    assert hi.share_text(allup).endswith("100 hissenin tamamı yükseldi.")
    assert hi.share_text(dict(s, counts={})) == "BIST100 · 25 Eylül kapanışı."
    assert not BANNED.search(hi.share_text(s))


# ── site eşliği: renk ölçeği ve veri cümlesi _heatmap.html ile aynı ─────────
def _site_html(snap):
    env = jinja2.Environment(loader=jinja2.FileSystemLoader(os.path.join(ROOT, "templates")))
    env.filters["signal_age_days"] = lambda s: 0   # _fmt_macros'taki kullanılmayan makro için
    groups, tiles = hm.layout(snap["rows"])
    return env.get_template("_heatmap.html").render(heatmap=snap, heatmap_groups=groups, heatmap_tiles=tiles)


@pytest.mark.parametrize("fixed", [True, False])
def test_colour_scale_matches_site_template(fixed):
    snap = _fixed() if fixed else _fx()
    html = _site_html(snap)
    site = {t: (cls.split(), float(k)) for cls, t, k in
            re.findall(r'<a class="hm-t ([^"]*)" href="/hisse/([A-Z0-9]+)"[^>]*--k:([0-9.]+)', html)}
    assert len(site) == 100
    for r in snap["rows"]:
        cls, k, dark = hi.tone(r["ch"]["d1"], r["stale"])
        scls, sk = site[r["t"]]
        assert scls[0] == cls and ("dark" in scls) == dark and ("stale" in scls) == r["stale"], r["t"]
        assert abs(sk - k) < 6e-4, (r["t"], sk, k)
    assert hi.tile_rgb("up", 1.0) == hi.AL and hi.tile_rgb("dn", 1.0) == hi.SAT and hi.tile_rgb("neu", 0) == hi.N


def test_sentence_matches_site_thesis():
    snap = _fixed()
    thesis = re.search(r'<p class="hm-thesis">(.*?)</p>', _site_html(snap), re.S).group(1)
    site = re.sub(r"<[^>]+>", "", thesis).replace("-%", "−%").strip()
    runs, extra = hi._sentence_runs(snap, 19)
    mine = " · ".join("".join(t for t, *_ in ch) for ch in [runs] + extra)
    assert mine == site == ("100 hissenin 64'ü yükseldi, 33'ü düştü, 3'ü değişmedi · BIST100 +%0,09 · "
                            "3 tavan, 9 taban")


# ── çizim ────────────────────────────────────────────────────────────────────
@pytest.fixture(scope="module")
def renders():
    snap = _fixed()
    return {k: hi.render_png(snap, k) for k in hi.KINDS}


@pytest.mark.parametrize("kind,size", [("og", (1200, 630)), ("kare", (1080, 1350))])
def test_png_size_and_all_100_tiles(renders, kind, size):
    data, meta = renders[kind]
    im = Image.open(io.BytesIO(data))
    assert im.format == "PNG" and im.size == size and meta["size"] == size
    assert len(data) < 600 * 1024          # bağlantı önizlemesi sınırı (WhatsApp ~600 KB)
    tiles = meta["tiles"]
    assert len(tiles) == 100 and len({t["t"] for t in tiles}) == 100
    X, Y, MW, MH = meta["map"]
    for t in tiles:
        assert t["w"] >= 1 and t["h"] >= 1, t
        assert X - 0.5 <= t["x"] and t["x"] + t["w"] <= X + MW + 0.5, t
        assert Y - 0.5 <= t["y"] and t["y"] + t["h"] <= Y + MH + 0.5, t
    for a in range(len(tiles)):
        for b in range(a + 1, len(tiles)):
            p, q = tiles[a], tiles[b]
            ox = min(p["x"] + p["w"], q["x"] + q["w"]) - max(p["x"], q["x"])
            oy = min(p["y"] + p["h"], q["y"] + q["h"]) - max(p["y"], q["y"])
            assert ox <= 0 or oy <= 0, (p["t"], q["t"])
    labelled = {t["t"] for t in tiles if t["tk"] and t["v"]}
    assert {"ASELS", "GARAN", "KCHOL", "TUPRS", "BIMAS", "THYAO", "DSTKF"} <= labelled
    assert sum(t["tk"] for t in tiles) >= 40


@pytest.mark.parametrize("kind", ["og", "kare"])
def test_rendered_text_legend_brand_and_language(renders, kind):
    _, meta = renders[kind]
    texts = meta["texts"]
    joined = "\n".join(texts)
    assert "BIST100" in texts and " · 25 Eylül 2026 kapanışı" in texts
    for must in ("Gün sonu değişim", "Kutu büyüklüğü: piyasa değeri", "−%3", "−%1,5", "0", "+%1,5", "+%3",
                 hi.DISCLAIMER, "borsa", "pusula", ".com", "+%1,22", "−%1,16"):
        assert must in texts, must
    assert "BANKACILIK" in texts and "HOLDİNG VE YATIRIM" in texts
    assert meta["legend"] and not meta["flags"]["stale"]
    assert not BANNED.search(joined), BANNED.search(joined)
    assert all(BANNED.search(x) for x in ("Güçlü AL", "Kaynak: KAP", "bugün kapanış", "Yahoo", "Ücretsiz"))
    assert "-%" not in joined          # eksi işareti U+2212


def test_stale_rows_get_legend_swatch():
    _, meta = hi.render(_fx(), "og")    # canlı 25.09 dosyası: 100/100 bayat (onarım öncesi)
    assert meta["flags"]["stale"] and "Veri gecikmeli" in meta["texts"]


def test_render_is_deterministic(renders):
    snap = _fixed()
    for k in hi.KINDS:
        again, _ = hi.render_png(snap, k)
        assert hashlib.sha256(again).hexdigest() == hashlib.sha256(renders[k][0]).hexdigest()
    assert renders["og"][0] != renders["kare"][0]


# ── disk: bir kez üret, atomik, üzerine yazma ────────────────────────────────
def test_ensure_writes_once_atomically(tmp_path):
    d = str(tmp_path)
    snap = _fixed()
    calls = []

    def load():
        calls.append(1)
        return snap

    w = hi.ensure(d, "2026-09-25", load, kinds=("og",))
    assert [os.path.basename(p) for p in w] == ["2026-09-25.png"] and len(calls) == 1
    st = os.stat(os.path.join(d, "2026-09-25.png"))
    w = hi.ensure(d, "2026-09-25", load)
    assert [os.path.basename(p) for p in w] == ["2026-09-25-kare.png"] and len(calls) == 2
    assert os.stat(os.path.join(d, "2026-09-25.png")).st_mtime_ns == st.st_mtime_ns
    assert hi.ensure(d, "2026-09-25", load) == [] and len(calls) == 2       # hepsi var: yükleme bile yok
    assert not [n for n in os.listdir(d) if n.endswith(".tmp")]
    assert Image.open(os.path.join(d, "2026-09-25-kare.png")).size == (1080, 1350)
    with pytest.raises(ValueError):
        hi.ensure(d, "2026-09-24", load)                                   # görüntü başka günün
    with pytest.raises(ValueError):
        hi.ensure(d, "../x", load)
    assert not os.path.exists(os.path.join(d, "2026-09-24.png"))


def test_write_once_never_overwrites(tmp_path):
    p = str(tmp_path / "2026-09-25.png")
    assert hi._write_once(p, b"a") is True
    assert hi._write_once(p, b"b") is False
    assert open(p, "rb").read() == b"a"


def test_days_and_latest(tmp_path):
    d = str(tmp_path)
    assert hm.days(d) == [] and hm.latest_path(d) is None and hm.days(d + "/yok") == []
    for n in ("2026-09-24.json", "2026-09-25.json", "2026-09-25.png", "2026-09-25-kare.png", ".harita.lock",
              "x.json", "2026-09-26.json.tmp"):
        open(os.path.join(d, n), "w").close()
    assert hm.days(d) == ["2026-09-24", "2026-09-25"]
    assert hm.latest_path(d) == os.path.join(d, "2026-09-25.json")


def test_layout_box_parameter_keeps_16_10_default():
    rows = _fx()["rows"]
    assert hm.layout(rows) == hm.layout(rows, hm.BOX_W, hm.BOX_H)
    g, t = hm.layout(rows, 1120, 420)
    assert len(t) == 100 and abs(sum(x["w"] * x["h"] for x in g) - 10000) < 1


# ── app.py bağlantısı (VPS: py3.10+) ─────────────────────────────────────────
@PY310
def test_app_harita_routes(tmp_path, monkeypatch):
    import app
    d = str(tmp_path / "heatmap")
    prev = _fixed()
    prev["asof"], prev["asof_label"] = "2026-09-24", "24 Eylül"
    hm.save_frozen(prev, d)
    hm.save_frozen(_fixed(), d)
    monkeypatch.setattr(app, "_HEATMAP_DIR", d)
    c = app.app.test_client()
    assert sorted(os.path.basename(p) for p in app._render_heatmap_images("2026-09-25")) == \
        ["2026-09-25-kare.png", "2026-09-25.png"]
    assert app._render_heatmap_images("2026-09-25") == []
    r = c.get("/harita/2026-09-25.png")
    assert r.status_code == 200 and r.mimetype == "image/png" and r.headers["Cache-Control"] == "public, max-age=3600"
    assert Image.open(io.BytesIO(r.data)).size == (1200, 630)
    r = c.get("/harita/2026-09-24-kare.png")
    assert r.status_code == 200 and r.headers["Cache-Control"] == "public, max-age=31536000, immutable"
    assert Image.open(io.BytesIO(r.data)).size == (1080, 1350)
    r = c.get("/harita/son.png")
    assert r.status_code == 302 and r.headers["Location"].endswith("/harita/2026-09-25.png")
    for bad in ("2026-09-23.png", "2026-02-30.png", "2026-09-25.PNG", "..%2Fapp.py", "2026-09-25.json", "x"):
        assert c.get("/harita/" + bad).status_code == 404, bad
    assert app._heatmap_og_image() == "/harita/2026-09-25.png"
    if app._harita_page_ready():
        r = c.get("/harita/2026-09-25")
        assert r.status_code == 200 and "/harita/2026-09-25.png" in r.get_data(as_text=True)
        assert c.get("/harita").headers["Location"].endswith("/harita/2026-09-25")
    else:     # ön yüz şablonu henüz yok: 500 değil 404
        assert c.get("/harita/2026-09-25").status_code == 404 and c.get("/harita").status_code == 404
    assert c.get("/harita/2026-09-23").status_code == 404
    assert c.get("/").status_code == 200 and c.get("/sektor-harita").status_code == 200
    monkeypatch.setattr(app, "_HEATMAP_DIR", str(tmp_path / "bos"))
    assert app._heatmap_og_image() is None and c.get("/harita/son.png").status_code == 404
