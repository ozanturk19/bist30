"""D-45(c): /api/bulten/<tarih> Akşam Bülteni — saf `bulten.py` fonksiyonları.
Ürün dili: AL/SAT yok, durum adları kanonik etiketten (business_rules.SIGNAL_LABELS
ile aynı sözlük). py3.9 uyumlu (app.py'ye bağımlı değil)."""
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
import bulten  # noqa: E402


def test_index_row_hesaplar_degisim():
    rec = {"indices": {"XU100": {"close": 11000.0, "prev_close": 10000.0}}}
    row = bulten._index_row(rec, "XU100")
    assert row == {"kapanis": 11000.0, "degisim_pct": 10.0}


def test_index_row_prev_yoksa_degisim_none():
    rec = {"indices": {"XU100": {"close": 11000.0}}}
    assert bulten._index_row(rec, "XU100")["degisim_pct"] is None


def test_index_row_kayit_yoksa_bos():
    assert bulten._index_row(None, "XU030") == {"kapanis": None, "degisim_pct": None}


def test_durum_degisimleri_al_sat_kelimesi_yok():
    changes = [
        {"ticker": "AKBNK", "old": "BEKLE", "new": "AL"},
        {"ticker": "GARAN", "old": "AL", "new": "SAT"},
    ]
    out = bulten.durum_degisimleri(changes)
    assert out == [
        {"ticker": "AKBNK", "onceki": "Yatay", "yeni": "Güçlü Trend"},
        {"ticker": "GARAN", "onceki": "Güçlü Trend", "yeni": "Trend Bozuldu"},
    ]
    blob = repr(out)
    assert "AL" not in blob.replace("Güçlü Trend", "").replace("Yatay", "")
    assert "SAT" not in blob.replace("Trend Bozuldu", "")


def test_durum_degisimleri_ayni_etiket_elenir():
    # old/new farklı kod ama (varsayımsal) aynı etikete düşerse — mevcut sözlükte
    # olmaz ama savunma: eksik/bilinmeyen kod → dışlanır, KeyError yok.
    assert bulten.durum_degisimleri([{"ticker": "X", "old": "BEKLE", "new": "BEKLE"}]) == []
    assert bulten.durum_degisimleri([{"ticker": "X", "old": None, "new": "AL"}]) == []
    assert bulten.durum_degisimleri([{"ticker": "X", "old": "AL", "new": "BILINMEYEN"}]) == []


def test_durum_degisimleri_bos_liste():
    assert bulten.durum_degisimleri(None) == []
    assert bulten.durum_degisimleri([]) == []


def test_isi_haritasi_ozet_sektor_ortalamasi_ve_bayat_disi():
    snap = {"rows": [
        {"g": "Bankacılık", "ch": {"d1": 2.0}, "stale": False},
        {"g": "Bankacılık", "ch": {"d1": 4.0}, "stale": False},
        {"g": "Bankacılık", "ch": {"d1": 100.0}, "stale": True},   # bayat — dışarıda
        {"g": "Holding", "ch": {"d1": -1.0}, "stale": False},
        {"g": None, "ch": {"d1": 5.0}, "stale": False},             # grupsuz — dışarıda
    ]}
    out = bulten.isi_haritasi_ozet(snap)
    assert out[0] == {"sektor": "Bankacılık", "ortalama_degisim_pct": 3.0}
    assert out[1] == {"sektor": "Holding", "ortalama_degisim_pct": -1.0}
    assert len(out) == 2


def test_isi_haritasi_ozet_snap_yoksa_bos():
    assert bulten.isi_haritasi_ozet(None) == []
    assert bulten.isi_haritasi_ozet({"rows": []}) == []


def test_onemli_bildirimler_onem_orani_azalan():
    items = [
        {"ticker": "A", "company": "A A.Ş.", "title": "Bağış", "href": "/a", "date": "2026-09-27T10:00",
         "onem": {"pct": 2.0, "txt": "%2"}},
        {"ticker": "B", "company": "B A.Ş.", "title": "Yatırım", "href": "/b", "date": "2026-09-27T09:00",
         "onem": {"pct": 40.0, "txt": "%40"}},
        {"ticker": "C", "company": "C A.Ş.", "title": "Rutin dışı", "href": "/c", "date": "2026-09-27T11:00",
         "onem": None},
    ]
    out = bulten.onemli_bildirimler(items, n=2)
    assert [x["ticker"] for x in out] == ["B", "A"]
    assert out[0]["onem"] == "%40"


def test_onemli_bildirimler_hepsi_onemsiz_zamana_gore_sirali():
    items = [
        {"ticker": "A", "date": "2026-09-27T09:00", "onem": None},
        {"ticker": "B", "date": "2026-09-27T15:00", "onem": None},
    ]
    out = bulten.onemli_bildirimler(items, n=5)
    assert [x["ticker"] for x in out] == ["B", "A"]


def test_onemli_bildirimler_bos_liste():
    assert bulten.onemli_bildirimler([]) == []
    assert bulten.onemli_bildirimler(None) == []


def test_yarin_takvim_yalniz_ertesi_gun():
    events = [
        {"date": "2026-09-27", "kind": "makro", "title": "Bugünkü", "ticker": None, "period": None, "time": "10:00"},
        {"date": "2026-09-28", "kind": "bilanco", "title": "Ertesi gün raporu", "ticker": "THYAO",
         "period": "2026/2Ç", "time": None},
        {"date": "2026-09-29", "kind": "temettu", "title": "Sonraki gün", "ticker": "GARAN",
         "period": None, "time": None},
    ]
    out = bulten.yarin_takvim(events, "2026-09-28")
    assert len(out) == 1
    assert out[0]["ticker"] == "THYAO" and out[0]["kind"] == "bilanco"


def test_yarin_takvim_bos():
    assert bulten.yarin_takvim([], "2026-09-28") == []
    assert bulten.yarin_takvim(None, "2026-09-28") == []


def test_build_sozlesme_sema():
    rec = {"indices": {"XU100": {"close": 11000.0, "prev_close": 10500.0}}}
    movers = {"up": [{"ticker": "AKBNK"}], "down": []}
    changes = [{"ticker": "GARAN", "old": "BEKLE", "new": "AL"}]
    snap = bulten.build("2026-09-27", rec, movers, changes, None, [], [], "2026-09-28",
                        "2026-09-27T18:40:00+03:00")
    assert set(snap.keys()) == {
        "tarih", "bist100", "hareketliler", "durum_degisimleri", "isi_haritasi_ozet",
        "onemli_bildirimler", "yarin_takvim", "updated_at", "frozen",
    }
    assert snap["tarih"] == "2026-09-27"
    assert snap["frozen"] is True
    assert snap["hareketliler"] == movers
    assert snap["durum_degisimleri"] == [{"ticker": "GARAN", "onceki": "Yatay", "yeni": "Güçlü Trend"}]


def test_build_movers_none_ise_bos_iskelet():
    snap = bulten.build("2026-09-27", None, None, None, None, None, None, "2026-09-28", None)
    assert snap["hareketliler"] == {"up": [], "down": []}


def test_save_frozen_yazar_ve_ikinci_kez_uzerine_yazmaz(tmp_path):
    d = str(tmp_path)
    snap = {"tarih": "2026-09-27", "frozen": True}
    path = bulten.save_frozen(snap, d)
    assert path == os.path.join(d, "2026-09-27.json")
    assert json.load(open(path, encoding="utf-8")) == snap
    # ikinci kez: dosya var, None döner, içerik değişmez (dondurma tek seferlik)
    assert bulten.save_frozen({"tarih": "2026-09-27", "frozen": "degisti"}, d) is None
    assert json.load(open(path, encoding="utf-8"))["frozen"] is True


def test_days_ve_latest_path(tmp_path):
    d = str(tmp_path)
    assert bulten.days(d) == []
    assert bulten.latest_path(d) is None
    bulten.save_frozen({"tarih": "2026-09-25"}, d)
    bulten.save_frozen({"tarih": "2026-09-27"}, d)
    bulten.save_frozen({"tarih": "2026-09-26"}, d)
    assert bulten.days(d) == ["2026-09-25", "2026-09-26", "2026-09-27"]
    assert bulten.latest_path(d) == os.path.join(d, "2026-09-27.json")


def test_days_bozuk_dosya_adi_yok_sayilir(tmp_path):
    d = str(tmp_path)
    os.makedirs(d, exist_ok=True)
    open(os.path.join(d, "latest.json"), "w").close()
    open(os.path.join(d, "2026-09-27.json"), "w").close()
    assert bulten.days(d) == ["2026-09-27"]
