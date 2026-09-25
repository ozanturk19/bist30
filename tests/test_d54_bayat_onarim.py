"""D-42 / D-54 inceleme bulgusu: eski kodla dondurulmuş TÜM günlerin "bayat" onarımı (tools/heatmap_bayat_onarim.py).

Deploy hafta içi 19:05 sonrasına kalırsa o günün ~18:47 görüntüsü de eski kodla (100/100 bayat) donar; onarım
yalnız 25.09'a değil her aday güne uygulanır, onarılan günün görselleri silinir, CF temizlik URL'leri yazılır.
"""
import json
import os
import stat
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tools"))
sys.path.insert(0, ROOT)
import heatmap as hm  # noqa: E402
import heatmap_bayat_onarim as tool  # noqa: E402

FX_PATH = os.path.join(ROOT, "tests", "fixtures", "heatmap_20260925.json")


def _raw():
    with open(FX_PATH, "rb") as f:
        return f.read()


def _put(d, day, snap=None, raw=None):
    p = os.path.join(d, day + ".json")
    with open(p, "wb") as f:
        f.write(raw if raw is not None else tool.dump(snap))
    os.chmod(p, 0o600)
    return p


def _day(asof, **edits):
    s = json.loads(_raw().decode("utf-8"))
    s["asof"] = asof
    for i, d1 in edits.get("d1", {}).items():
        s["rows"][i]["ch"]["d1"] = d1
    return s


def _setup(tmp_path):
    d = str(tmp_path)
    _put(d, "2026-09-25", raw=_raw())                                    # canlı 25.09, 100/100 bayat
    _put(d, "2026-09-28", _day("2026-09-28", d1={0: None, 1: 12.0}))     # Pzt, deploy freeze sonrası: eski kod
    ok = _day("2026-09-29")                                              # yeni kod: gerçek bayat 3 satır
    for i, r in enumerate(ok["rows"]):
        r["stale"] = i < 3
    _put(d, "2026-09-29", ok)
    for n in ("2026-09-25.png", "2026-09-28.png", "2026-09-28-kare.png", "2026-09-29.png"):
        with open(os.path.join(d, n), "wb") as f:
            f.write(b"png")
    return d


def _read(d, day):
    with open(os.path.join(d, day + ".json"), "rb") as f:
        return f.read()


def test_aday_kurali():
    s = _day("2026-09-25")
    assert tool.is_candidate(s, "2026-09-25") and not tool.is_candidate(s, "2026-09-26")
    s["rows"][5]["stale"] = False                                  # tümü bayat değil → dokunulmaz
    assert not tool.is_candidate(s, "2026-09-25")
    s = _day("2026-09-25")
    for r in s["rows"]:
        r["ch"]["d1"] = None                                       # kuralla da hepsi bayat → değişecek bir şey yok
    assert not tool.is_candidate(s, "2026-09-25")


def test_kuru_kosu_hicbir_seye_dokunmaz(tmp_path):
    d = _setup(tmp_path)
    before = {n: open(os.path.join(d, n), "rb").read() for n in os.listdir(d)}
    lines = []
    done = tool.run(d, out=lines.append)
    assert [x["day"] for x in done] == ["2026-09-25", "2026-09-28"]
    assert {n: open(os.path.join(d, n), "rb").read() for n in os.listdir(d)} == before
    assert all("kuru" in ln for ln in lines if ln[:4] == "2026")


def test_tum_eski_gunler_onarilir_gorseller_silinir(tmp_path):
    d = _setup(tmp_path)
    m29 = os.stat(os.path.join(d, "2026-09-29.json")).st_mtime_ns
    raw29 = _read(d, "2026-09-29")
    lines = []
    done = {x["day"]: x for x in tool.run(d, write=True, out=lines.append)}
    assert sorted(done) == ["2026-09-25", "2026-09-28"]
    # 25.09: 100 → 0, yalnız "stale" değerleri değişti (geri kalan bayt aynı), md5 raporlandı
    new25 = _read(d, "2026-09-25")
    assert (done["2026-09-25"]["before"], done["2026-09-25"]["after"]) == (100, 0)
    assert new25.replace(b'"stale":false', b'"stale":true') == _raw()
    assert done["2026-09-25"]["md5_new"] != done["2026-09-25"]["md5_old"]
    # 28.09: d1 yok ve |d1| > 10,5 bayat kalır, kalanı değil
    s28 = json.loads(_read(d, "2026-09-28"))
    assert [i for i, r in enumerate(s28["rows"]) if r["stale"]] == [0, 1]
    assert all(r["stale"] == (r["ch"]["d1"] is None or abs(r["ch"]["d1"]) > hm.STALE_ABS_D1) for r in s28["rows"])
    # yeni kodla dondurulmuş gün ve görseli dokunulmadan kalır
    assert _read(d, "2026-09-29") == raw29 and os.stat(os.path.join(d, "2026-09-29.json")).st_mtime_ns == m29
    left = sorted(n for n in os.listdir(d) if not n.startswith("."))
    assert left == ["2026-09-25.json", "2026-09-28.json", "2026-09-29.json", "2026-09-29.png"]
    assert done["2026-09-28"]["removed"] == ["2026-09-28.png", "2026-09-28-kare.png"]
    assert "  https://borsapusula.com/harita/2026-09-28-kare.png" in lines
    assert "  https://borsapusula.com/harita/2026-09-25.png" in lines
    # dosya kipi korunur (VPS: root 0600), .tmp artığı yok
    assert stat.S_IMODE(os.stat(os.path.join(d, "2026-09-25.json")).st_mode) == 0o600
    # idempotent: ikinci koşu aday bulmaz
    lines = []
    assert tool.run(d, write=True, out=lines.append) == [] and lines == ["aday gun yok (onarilacak bir sey yok)"]


def test_son_gun_siniri(tmp_path):
    d = _setup(tmp_path)
    assert [x["day"] for x in tool.run(d, last_day="2026-09-25", write=True, out=lambda *_: None)] == ["2026-09-25"]
    assert all(r["stale"] for r in json.loads(_read(d, "2026-09-28"))["rows"])
    assert os.path.isfile(os.path.join(d, "2026-09-28.png"))


def test_cli(tmp_path, capsys):
    d = _setup(tmp_path)
    assert tool.main(["--dir", d]) == 0 and "kuru" in capsys.readouterr().out
    assert tool.main(["--dir", d, "--yaz"]) == 0
    assert "ONARILDI" in capsys.readouterr().out
    assert tool.main(["--dir", str(tmp_path / "yok")]) == 0
