"""D-56 (Bülten v2, O28=A): dondurma anındaki yeni alanlar — günün cümlesi, XU100 30 kapanış
serisi + eşik tarihi, sayım, durum değişimlerinde ad/fiyat/%, önem oranının yapılandırılmış
alanları, sektör başına hisse sayısı (haritayla tek tanım), boş takvim gününde sonraki beş
işlem günü, arşiv listesi, D-56 öncesi görüntüleri tamamlayan araç.

Fikstür tests/fixtures/bulten_v2_20260928.json: VPS salt-okur kopya (01.10 22:3x) — 28.09'un
D-56 öncesi donmuş bülteni, aynı günün donmuş ısı haritası, chart_xu100 kapanışları, durum
değişen hisselerin resmi kapanışı, bildirimlerin önem kaydı. py3.9 uyumlu (app.py yok);
rota testi yalnız VPS'te (3.10+)."""
import json
import os
import re
import sys
from datetime import date

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
import bulten  # noqa: E402

FX = os.path.join(ROOT, "tests", "fixtures", "bulten_v2_20260928.json")
PY310 = pytest.mark.skipif(sys.version_info < (3, 10), reason="app.py 3.10+ ister")
# Kullanıcıya giden cümlede asla: işlem/hedef dili, göreli zaman, yargı, gri/çekinceli dil.
BANNED = re.compile(r"\b(AL|SAT|BEKLE)\b|\b([Bb]ugün|[Dd]ün|[Yy]arın|[Gg]ünün)\b|[Hh]edef|kâr al|stop|"
                    r"LONG|SHORT|Ücretsiz|[Kk]ısmi|[Ss]ınırlı veri|hazırlanıyor|[Gg]üçlü şirket|[Zz]ayıf şirket")


def _fx():
    with open(FX, encoding="utf-8") as f:
        return json.load(f)


def _tdays(*isos):
    s = set(isos)
    return lambda d: d.weekday() < 5 and d.isoformat() not in s


# ── Türkçe ekler ─────────────────────────────────────────────────────────────
@pytest.mark.parametrize("n,want", [(0, "'ı"), (1, "'i"), (2, "'si"), (3, "'ü"), (4, "'ü"), (6, "'sı"),
                                    (9, "'u"), (10, "'u"), (17, "'si"), (40, "'ı"), (60, "'ı"), (77, "'si"),
                                    (86, "'sı"), (91, "'i"), (100, "'ü"), (1000, "'i")])
def test_iyelik(n, want):
    assert bulten.iyelik(n) == want


@pytest.mark.parametrize("n,want", [(2025, "'ten"), (2026, "'dan"), (2030, "'dan"), (2040, "'tan"),
                                    (2000, "'den"), (2023, "'ten"), (2029, "'dan")])
def test_ayrilma(n, want):
    assert bulten.ayrilma(n) == want


@pytest.mark.parametrize("txt,want", [("%16,1", "%16,1'i"), ("~%41,6", "%41,6'sı"), ("%10,0", "%10'u"),
                                      ("%0,9", "%0,9'u"), ("%10,2", "%10,2'si"), ("%3,05", "%3,05'i")])
def test_oran_iyelik(txt, want):
    assert bulten.oran_iyelik(txt) == want


# ── XU100 serisi ve eşik ─────────────────────────────────────────────────────
def test_endeks_gecmisi_gunun_resmi_kapanisi_ile_biter():
    ohlc = [{"time": "2026-09-24", "close": 100.0}, {"time": "2026-09-25", "close": 101.0},
            {"time": "2026-09-28", "close": 99.9}]          # Yahoo'nun gün barı resmiyle değişir
    pts = bulten.endeks_gecmisi(ohlc, "2026-09-28", 99.5)
    assert pts == [("2026-09-24", 100.0), ("2026-09-25", 101.0), ("2026-09-28", 99.5)]
    assert bulten.endeks_serisi(pts, "2026-09-28", n=2) == [["2026-09-25", 101.0], ["2026-09-28", 99.5]]


def test_endeks_serisi_gun_yoksa_bos():
    pts = bulten.endeks_gecmisi([{"time": "2026-09-25", "close": 1.0}], "2026-09-28", None)
    assert bulten.endeks_serisi(pts, "2026-09-28") == []
    assert bulten.endeks_esik(pts, "2026-09-28") is None


def _seri(vals):
    return [("2026-%02d-%02d" % (1 + i // 28, 1 + i % 28), float(v)) for i, v in enumerate(vals)]


def test_endeks_esik_dusuk_tarih_son_daha_dusuk_gun():
    pts = _seri([50] + [100] * 25 + [60])                    # 25 seans boyunca en düşük
    e = bulten.endeks_esik(pts, pts[-1][0])
    assert e == {"yon": "dusuk", "tarih": pts[0][0], "seans": 25}


def test_endeks_esik_yuksek_ve_kisa_seri_yazilmaz():
    pts = _seri([200] + [100] * 21 + [150])
    assert bulten.endeks_esik(pts, pts[-1][0])["yon"] == "yuksek"
    pts = _seri([50] + [100] * 10 + [60])                     # yalnız 10 seans: yazılmaz
    assert bulten.endeks_esik(pts, pts[-1][0]) is None
    pts = _seri([100] * 30 + [100])                           # değişmeyen gün: yön yok
    assert bulten.endeks_esik(pts, pts[-1][0]) is None


def test_endeks_esik_seride_yoksa_yil_kosulu():
    pts = [("d%03d" % i, 100.0 + i % 3) for i in range(300)] + [("e", 50.0)]
    assert bulten.endeks_esik(pts, "e") == {"yon": "dusuk", "tarih": None, "seans": 300}
    pts = [("d%03d" % i, 100.0) for i in range(100)] + [("e", 50.0)]
    assert bulten.endeks_esik(pts, "e") is None               # 1 yıldan kısa geçmiş: iddia yok


# ── Günün cümlesi ────────────────────────────────────────────────────────────
def test_ozet_28_eylul_taslaktaki_cumle():
    fx = _fx()
    b = fx["bulten"]
    pts = bulten.endeks_gecmisi(fx["xu100"], "2026-09-28", b["bist100"]["kapanis"])
    esik = bulten.endeks_esik(pts, "2026-09-28")
    parts = bulten.ozet_parcalar("2026-09-28", b["bist100"], esik, bulten.sayim(fx["heatmap"]))
    assert bulten.ozet_cumlesi(parts) == (
        "BIST100 %2,38 düşüşle 12.592,76 puanda kapandı, 15 Ocak'tan bu yana en düşük kapanış; "
        "endeksteki 100 hissenin 91'i düştü, 9'u yükseldi.")
    assert ["%2,38", "dn"] in parts and ["12.592,76", "b"] in parts and ["91'i", "dn"] in parts
    assert ["9'u", "up"] in parts
    assert not BANNED.search(bulten.ozet_cumlesi(parts))


def test_ozet_yukselis_cogunluk_once_ve_tamami():
    ix = {"kapanis": 12249.04, "degisim_pct": 2.53}
    s = bulten.ozet_cumlesi(bulten.ozet_parcalar("2026-10-01", ix, None, {"n": 100, "up": 81, "down": 17, "flat": 2}))
    assert s == "BIST100 %2,53 yükselişle 12.249,04 puanda kapandı; endeksteki 100 hissenin 81'i yükseldi, 17'si düştü."
    s = bulten.ozet_cumlesi(bulten.ozet_parcalar("2026-10-01", ix, None, {"n": 100, "up": 100, "down": 0, "flat": 0}))
    assert s.endswith("endeksteki 100 hissenin tamamı yükseldi.")


def test_ozet_onceki_yil_esigi_ve_yil_esigi():
    ix = {"kapanis": 9000.0, "degisim_pct": -1.0}
    s = bulten.ozet_cumlesi(bulten.ozet_parcalar(
        "2026-01-05", ix, {"yon": "dusuk", "tarih": "2025-03-14", "seans": 200}, None))
    assert s == "BIST100 %1,00 düşüşle 9.000,00 puanda kapandı, 14 Mart 2025'ten bu yana en düşük kapanış."
    s = bulten.ozet_cumlesi(bulten.ozet_parcalar(
        "2026-01-05", dict(ix, degisim_pct=1.0), {"yon": "yuksek", "tarih": None, "seans": 300}, None))
    assert s == "BIST100 %1,00 yükselişle 9.000,00 puanda kapandı, son bir yılın en yüksek kapanışı."


def test_ozet_degisimsiz_ve_kapanissiz():
    s = bulten.ozet_cumlesi(bulten.ozet_parcalar("2026-10-01", {"kapanis": 100.0, "degisim_pct": 0.0}, None, None))
    assert s == "BIST100 değişmeden 100,00 puanda kapandı."
    assert bulten.ozet_parcalar("2026-10-01", {"kapanis": None, "degisim_pct": 1.0}, None, None) is None
    assert bulten.ozet_cumlesi(None) is None


# ── Durum, bildirim, takvim ──────────────────────────────────────────────────
def test_durum_degisimleri_ad_fiyat_degisim():
    out = bulten.durum_degisimleri(
        [{"ticker": "THYAO", "old": "BEKLE", "new": "SAT"}, {"ticker": "YOK", "old": "AL", "new": "BEKLE"}],
        {"THYAO": {"name": "Türk Hava Yolları", "price": 287.0, "change_pct": -1.2912}})
    assert out == [
        {"ticker": "THYAO", "onceki": "Yatay", "yeni": "Trend Bozuldu", "ad": "Türk Hava Yolları",
         "fiyat": 287.0, "degisim_pct": -1.29},
        {"ticker": "YOK", "onceki": "Güçlü Trend", "yeni": "Yatay"},
    ]


def test_onem_alanlar_tl_doviz_ve_esik():
    tl = {"pct": 16.11, "txt": "%16,1", "approx": False, "basis": "İhale bedeli / 2025 hasılatı",
          "amount_txt": "137.700.000 ₺", "amount_try_txt": "138 Mn ₺", "rev_year": 2025}
    assert bulten.onem_alanlar(tl) == {"temel": "İhale bedeli", "tutar": "138 Mn ₺", "yil": 2025, "yuzde": 16.11,
                                       "yaklasik": False, "oran_txt": "%16,1'i"}
    fx = dict(tl, pct=41.6, txt="~%41,6", approx=True, amount_txt="25.000.000 $",
              basis="Sözleşme tutarı / 2025 hasılatı")
    al = bulten.onem_alanlar(fx)
    assert al["tutar"] == "25.000.000 $" and al["oran_txt"] == "yaklaşık %41,6'sı" and al["temel"] == "Sözleşme tutarı"
    assert bulten.onem_alanlar(dict(tl, pct=0.04, txt="%0,0")) is None
    assert bulten.onem_alanlar(None) is None
    out = bulten.onemli_bildirimler([{"ticker": "K", "onem": {"pct": 0.02, "txt": "%0,0"}, "date": "x"}])
    assert out[0]["onem"] is None and out[0]["onem_alanlar"] is None       # %0,0 sayfada yazılmaz


def test_takvim_alanlari_ve_yaklasan():
    ev = [
        {"date": "2026-09-30", "kind": "temettu", "ticker": "TUPRS", "name": "Tüpraş", "brut_tl": 6.75,
         "net_tl": 5.73, "yield_pct": 1.69, "pay_date": "2026-10-02", "taksit": "2/2", "date_kind": "kesin",
         "id": "t-TUPRS"},
        {"date": "2026-09-30", "kind": "makro", "time": "15:30", "region": "ABD", "title": "PCE fiyat endeksi",
         "period": "Ağustos", "detail": "Fed'in izlediği enflasyon ölçüsü", "ticker": None},
        {"date": "2026-10-02", "kind": "makro", "title": "Tarım dışı istihdam"},
        {"date": "2026-10-05", "kind": "makro", "title": "Enflasyon (TÜFE)"},
        {"date": "2026-10-05", "kind": "temettu", "ticker": "AEFES"},
        {"date": "2026-10-06", "kind": "temettu", "ticker": "TRALT"},     # 6. işlem günü: dışarıda
    ]
    gun = bulten.sonraki_islem_gunleri("2026-09-28", 5, _tdays("2026-10-29"))
    assert gun == ["2026-09-29", "2026-09-30", "2026-10-01", "2026-10-02", "2026-10-05"]
    snap = bulten.build("2026-09-28", None, None, None, None, None, ev, "2026-09-29", None, takvim_gunleri=gun)
    assert snap["yarin_takvim"] == [] and snap["takvim_gunu"] == "2026-09-29"
    assert [e.get("ticker") or e["title"] for e in snap["yaklasan"]] == [
        "TUPRS", "PCE fiyat endeksi", "Tarım dışı istihdam", "Enflasyon (TÜFE)", "AEFES"]
    t = snap["yaklasan"][0]
    assert t["brut_tl"] == 6.75 and t["pay_date"] == "2026-10-02" and "id" not in t
    assert snap["yaklasan"][1]["detail"].startswith("Fed")
    snap = bulten.build("2026-09-29", None, None, None, None, None, ev, "2026-09-30", None, takvim_gunleri=gun[1:])
    assert len(snap["yarin_takvim"]) == 2 and snap["yaklasan"] == []      # gün doluysa yaklaşan yok


def test_build_gercek_28_eylul():
    fx = _fx()
    b = fx["bulten"]
    rec = {"indices": {"XU100": {"close": 12592.76, "prev_close": 12899.35}}}
    changes = [{"ticker": c["ticker"], "old": {"Yatay": "BEKLE", "Güçlü Trend": "AL", "Trend Bozuldu": "SAT"}[c["onceki"]],
                "new": {"Yatay": "BEKLE", "Güçlü Trend": "AL", "Trend Bozuldu": "SAT"}[c["yeni"]]}
               for c in b["durum_degisimleri"]]
    stocks = {t: {"name": t + " A.Ş.", "price": v["close"], "change_pct": v["change_pct"]} for t, v in fx["resmi"].items()}
    snap = bulten.build("2026-09-28", rec, b["hareketliler"], changes, fx["heatmap"], [], [], "2026-09-29",
                        "2026-09-28T18:41:00+03:00", xu100_ohlc=fx["xu100"], stocks=stocks)
    ix = snap["bist100"]
    assert ix["kapanis"] == 12592.76 and ix["degisim_pct"] == -2.38
    assert len(ix["seri"]) == 30 and ix["seri"][-1] == ["2026-09-28", 12592.76] and ix["seri"][0][0] == "2026-08-18"
    assert ix["esik"] == {"yon": "dusuk", "tarih": "2026-01-15", "seans": 173}
    assert snap["sayim"] == {"n": 100, "up": 9, "down": 91, "flat": 0}
    assert snap["ozet_cumlesi"].startswith("BIST100 %2,38 düşüşle 12.592,76 puanda kapandı, 15 Ocak'tan bu yana")
    assert len(snap["durum_degisimleri"]) == 10 and all("fiyat" in d for d in snap["durum_degisimleri"])
    sk = snap["isi_haritasi_ozet"]
    assert sum(s["hisse_sayisi"] for s in sk) == 100
    assert [s["ortalama_degisim_pct"] for s in sk] == sorted((s["ortalama_degisim_pct"] for s in sk), reverse=True)
    json.dumps(snap, allow_nan=False)                                      # dondurulabilir


def test_sektor_ozeti_harita_grup_etiketiyle_ayni_sayi():
    """templates/_heatmap.html gs.s/gs.w kuralını burada yeniden yap: aynı sayı (tek tanım)."""
    hm = _fx()["heatmap"]
    want = {}
    for r in hm["rows"]:
        if not (r.get("g") and r.get("mcap")):
            continue
        s, w = want.get(r["g"], (0.0, 0.0))
        if r.get("ch") and r["ch"].get("d1") is not None:
            s, w = s + r["ch"]["d1"] * r["mcap"], w + r["mcap"]
        want[r["g"]] = (s, w)
    for row in bulten.isi_haritasi_ozet(hm):
        s, w = want[row["sektor"]]
        assert abs(row["ortalama_degisim_pct"] - s / w) < 1e-4
        assert ("%.1f" % row["ortalama_degisim_pct"]) == ("%.1f" % (s / w))


# ── D-56 öncesi görüntüyü tamamlama + arşiv ──────────────────────────────────
def test_eksikleri_tamamla_ekler_var_olana_dokunmaz_ve_tekrar_degismez():
    fx = _fx()
    snap = json.loads(json.dumps(fx["bulten"]))
    before_mv = json.dumps(snap["hareketliler"])
    stocks = {t: {"name": "Ad " + t, "price": v["close"], "change_pct": v["change_pct"]} for t, v in fx["resmi"].items()}
    ch = bulten.eksikleri_tamamla(snap, heatmap_snap=fx["heatmap"], xu100_ohlc=fx["xu100"], stocks=stocks,
                                  kap_by_href=fx["kap"])
    assert {"bist100.seri/esik", "sayim", "isi_haritasi_ozet", "ozet", "durum_degisimleri",
            "onemli_bildirimler"} <= set(ch)
    assert json.dumps(snap["hareketliler"]) == before_mv
    assert snap["bist100"]["kapanis"] == 12592.76 and snap["bist100"]["degisim_pct"] == -2.38
    assert snap["ozet_cumlesi"].endswith("91'i düştü, 9'u yükseldi.")
    fon = [k for k in snap["onemli_bildirimler"] if k["ticker"] == "FONET"][0]
    assert fon["onem_alanlar"]["oran_txt"] == "%16,1'i" and fon["onem_alanlar"]["temel"] == "İhale bedeli"
    assert all((k["onem"] is None) == (k["onem_alanlar"] is None) for k in snap["onemli_bildirimler"])
    again = json.loads(json.dumps(snap))
    assert bulten.eksikleri_tamamla(again, heatmap_snap=fx["heatmap"], xu100_ohlc=fx["xu100"], stocks=stocks,
                                    kap_by_href=fx["kap"]) == []
    assert again == snap


def test_tamamla_araci_kuru_ve_uygula(tmp_path, capsys):
    sys.path.insert(0, os.path.join(ROOT, "tools"))
    import bulten_v2_tamamla as tool
    fx = _fx()
    (tmp_path / "data" / "bulten").mkdir(parents=True)
    (tmp_path / "data" / "heatmap").mkdir(parents=True)
    (tmp_path / "resmi_kapanis").mkdir()
    p = tmp_path / "data" / "bulten" / "2026-09-28.json"
    p.write_text(json.dumps(fx["bulten"], ensure_ascii=False), encoding="utf-8")
    (tmp_path / "data" / "heatmap" / "2026-09-28.json").write_text(json.dumps(fx["heatmap"]), encoding="utf-8")
    (tmp_path / "chart_xu100.json").write_text(json.dumps({"data": {"ohlc": fx["xu100"]}}), encoding="utf-8")
    (tmp_path / "resmi_kapanis" / "2026-09-28.json").write_text(json.dumps({"stocks": fx["resmi"]}), encoding="utf-8")
    raw = p.read_text(encoding="utf-8")
    assert tool.main(["--root", str(tmp_path)]) == 0
    assert p.read_text(encoding="utf-8") == raw                             # kuru: yazmaz
    assert tool.main(["--root", str(tmp_path), "--apply"]) == 0
    s = json.loads(p.read_text(encoding="utf-8"))
    assert s["ozet_cumlesi"] and len(s["bist100"]["seri"]) == 30 and s["takvim_gunu"] == "2026-09-29"
    assert s["durum_degisimleri"][0]["fiyat"] == fx["resmi"][s["durum_degisimleri"][0]["ticker"]]["close"]
    mt = os.path.getmtime(p)
    assert tool.main(["--root", str(tmp_path), "--apply"]) == 0
    assert os.path.getmtime(p) == mt                                       # ikinci koşu: değişiklik yok
    assert "yazılan: 0" in capsys.readouterr().out.splitlines()[-1]


def test_arsiv_yeniden_eskiye_ve_bellek(tmp_path):
    d = str(tmp_path)
    assert bulten.arsiv(d) == []
    bulten.save_frozen({"tarih": "2026-09-25", "bist100": {"kapanis": 1.0, "degisim_pct": 0.1}}, d)
    bulten.save_frozen({"tarih": "2026-09-28", "bist100": {"kapanis": 2.0, "degisim_pct": -2.38},
                        "ozet_cumlesi": "BIST100 ..."}, d)
    open(os.path.join(d, "2026-09-29.json"), "w").write("{bozuk")
    a = bulten.arsiv(d)
    assert [x["tarih"] for x in a] == ["2026-09-28", "2026-09-25"]          # bozuk gün atlanır
    assert a[0] == {"tarih": "2026-09-28", "kapanis": 2.0, "degisim_pct": -2.38, "ozet_cumlesi": "BIST100 ..."}
    assert bulten.arsiv(d) == a


# ── app.py bağlantısı (VPS: py3.10+) ─────────────────────────────────────────
@PY310
def test_app_bulten_rotalari(tmp_path, monkeypatch):
    import app
    import heatmap as hm
    fx = _fx()
    bd, hd = str(tmp_path / "bulten"), str(tmp_path / "heatmap")
    snap = json.loads(json.dumps(fx["bulten"]))
    bulten.eksikleri_tamamla(snap, heatmap_snap=fx["heatmap"], xu100_ohlc=fx["xu100"])
    bulten.save_frozen(snap, bd)
    bulten.save_frozen(dict(snap, tarih="2026-09-25"), bd)
    hm.save_frozen(fx["heatmap"], hd)
    monkeypatch.setattr(app, "_BULTEN_DIR", bd)
    monkeypatch.setattr(app, "_HEATMAP_DIR", hd)
    c = app.app.test_client()
    r = c.get("/api/bulten/2026-09-28")
    assert r.status_code == 200 and r.get_json()["ozet_cumlesi"] == snap["ozet_cumlesi"]
    if app._bulten_page_ready():
        html = c.get("/bulten/2026-09-28").get_data(as_text=True)
        assert "2026-09-25" in html                                          # önceki gün bağlantısı
    else:
        assert c.get("/bulten/2026-09-28").status_code == 404
    if app._bulten_page_ready("bulten_arsiv.html"):
        r = c.get("/bulten/arsiv")
        assert r.status_code == 200 and "/bulten/2026-09-28" in r.get_data(as_text=True)
    else:
        assert c.get("/bulten/arsiv").status_code == 404
    monkeypatch.setattr(app, "_BULTEN_DIR", str(tmp_path / "bos"))
    assert c.get("/bulten/arsiv").status_code == 404
