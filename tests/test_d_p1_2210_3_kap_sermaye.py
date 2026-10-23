"""D-P1-2210-3: bedelli sermaye artirimi KAP ayristirma + TERP katsayisi (saf matematik).

Fixture gercek KAP bildiriminden (CVKMD, id 1656455, kap_feed.Store VPS onbellegi,
26.09.2026 cekildi) — tests/fixtures/kap_sermaye. app.py'yi import etmez (py3.9
yerel kapida kosar).
"""
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

import kap_sermaye as ks  # noqa: E402

FIX = os.path.join(ROOT, "tests", "fixtures", "kap_sermaye")


def _lines(name):
    with open(os.path.join(FIX, name), encoding="utf-8") as f:
        return json.load(f)["lines"]


def test_cvkmd_tamamlanma_bildirimi_alanlari():
    r = ks.parse_sermaye_artirimi(_lines("cvkmd_1656455.json"))
    assert r["mevcut_sermaye"] == 1400000000.0
    assert r["ulasilacak_sermaye"] == 3780000000.0
    assert r["kayit_tarihi"] == "06.08.2026"
    assert r["odeme_tarihi"] == "07.08.2026"


def test_cvkmd_oran_kap_bildirimindeki_170_ile_ortusuyor():
    r = ks.parse_sermaye_artirimi(_lines("cvkmd_1656455.json"))
    oran = (r["ulasilacak_sermaye"] - r["mevcut_sermaye"]) / r["mevcut_sermaye"]
    assert round(oran, 2) == 1.70  # KAP: "Rüçhan Hakkı Kullanım Oranı (%) 170,00000"


def test_terp_factor_bilinen_ornekle():
    # mevcut=1.4 Mr, ulasilacak=3.78 Mr (oran 1.70), fiyat 1 TL, cum-rights kapanis 10 TL
    # TERP = (10 + 1.70*1) / (1+1.70) = 11.70/2.70 = 4.3333
    f = ks.terp_adjustment_factor(1_400_000_000, 3_780_000_000, 1.0, 10.0)
    assert round(f, 4) == round(4.3333333333 / 10, 4)
    assert 0 < f < 1  # back-adjustment pre-rights barlari asagi cekmeli


def test_terp_factor_fiyat_cum_fiyata_esitse_duzeltme_yok():
    # ruchan fiyati = cum-rights fiyat ise sulanma yok, factor ~ 1
    f = ks.terp_adjustment_factor(1_400_000_000, 3_780_000_000, 10.0, 10.0)
    assert round(f, 4) == 1.0


def test_terp_factor_gecersiz_girdide_none():
    assert ks.terp_adjustment_factor(0, 3_780_000_000, 1.0, 10.0) is None
    assert ks.terp_adjustment_factor(1_400_000_000, 1_400_000_000, 1.0, 10.0) is None  # artirim yok
    assert ks.terp_adjustment_factor(1_400_000_000, 3_780_000_000, 1.0, 0) is None
