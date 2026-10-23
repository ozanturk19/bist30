"""D-P1-2210-3: KAP bedelli sermaye artirimi bildirimlerinden fiyat-dizisi duzeltme katsayisi.

Amac: bedelli sermaye artirimi olan hisselerde (CANTE, CVKMD, ENTRA, FENER, KONTR,
MARTI, MERKO, MRGYO, SKBNK, USAK) YTD/1Y/52h/grafik/isi haritasi gibi turetilmis
serilerin kayit tarihinden ONCEKI barlarini, Borsa Istanbul'un teorik ruchan-sonrasi
fiyat (TERP) yontemiyle geriye-dogru duzeltmek icin gereken katsayiyi hesaplar.

Bu modul SAF matematik + KAP metin-ayristirma icerir; HICBIR canli kod yolunu
(app.py analyze()/heatmap.py/_compute_chart_data) henuz CAGIRMAZ — katsayinin her
hisse icin cum-rights kapanis fiyatiyla dogrulanmasi ve wiring D-P1-2210-3'un
kalan adimidir (bkz. MASTER-PLAN notu).

Veri kaynagi: kap_feed.Store().doc(idx)["lines"] — "Sermaye Artırımı - Azaltımı
İşlemlerine İlişkin Bildirim" / "...Tamamlanması..." bildirimi (ornek fixture:
tests/fixtures/kap_sermaye/cvkmd_1656455.json, CVKMD 31.08.2026, id 1656455 —
kap_feed.Store icin VPS'teki gercek onbellekten alindi).
"""
import re


def _tl(s):
    """'1.400.000.000' ya da '170,00000' -> float. Bos/eslesmezse None."""
    if not s:
        return None
    s = s.strip().split()[0] if " " in s.strip() else s.strip()
    s = s.replace(".", "").replace(",", ".")
    try:
        return float(s)
    except ValueError:
        return None


def _after(lines, label, offset=1):
    """lines listesinde label'in İLK gectigi yerden offset kadar ileri deger (yoksa None)."""
    try:
        i = lines.index(label)
    except ValueError:
        return None
    j = i + offset
    return lines[j] if 0 <= j < len(lines) else None


def parse_sermaye_artirimi(lines):
    """KAP 'Sermaye Artırımı ... Tamamlanması' bildirimi lines[] -> temel alanlar.

    Hisse sinifi (A/B grubu) yapisindan BAGIMSIZ, sirket seviyesinde bir kez gecen
    4 alanla sinirli (fiyat/oran payi-sinifina gore degisebildigi icin burada
    CIKARILMAZ — ayri, hisseye-ozel dogrulama gerektirir, D-P1-2210-3 kalan adimi).
    """
    return {
        "mevcut_sermaye": _tl(_after(lines, "Mevcut Sermaye (TL)")),
        "ulasilacak_sermaye": _tl(_after(lines, "Ulaşılacak Sermaye (TL)")),
        "kayit_tarihi": (_after(lines, "Kayıt Tarihi") or "").split(" ")[0] or None,
        "odeme_tarihi": (_after(lines, "Ödeme Tarihi") or "").split(" ")[0] or None,
    }


def terp_adjustment_factor(mevcut_sermaye, ulasilacak_sermaye, fiyat, p_cum):
    """Borsa Istanbul teorik ruchan-sonrasi fiyat (TERP) geriye-duzeltme katsayisi.

    mevcut_sermaye/ulasilacak_sermaye: artirim ONCESI/SONRASI toplam sermaye (TL,
    nominal 1 TL/pay oldugundan pay adedi ile orantili). fiyat: ruchan kullandirma
    fiyati (TL/pay). p_cum: kayit tarihinden onceki son kapanis (cum-rights, TL).

    Donus: pre-rights barlara uygulanacak CARPAN (factor <= 1 beklenir, cunku
    TERP < p_cum olur — yeni paylar daha ucuza satildigi icin fiyat sulanir).
    Tum turetilmis seriler (YTD/1Y/52h/chart) icin: duzeltilmis_close =
    ham_close * factor (kayit tarihinden ONCEKI barlarda), kayit tarihi ve
    sonrasi barlar DEGISMEZ.
    """
    if not (mevcut_sermaye and ulasilacak_sermaye and p_cum) or mevcut_sermaye <= 0 or p_cum <= 0:
        return None
    yeni_sermaye = ulasilacak_sermaye - mevcut_sermaye
    if yeni_sermaye <= 0:
        return None
    oran = yeni_sermaye / mevcut_sermaye  # ruchan hakki kullanim orani (örn. 1.70)
    terp = (p_cum + oran * fiyat) / (1 + oran)
    if terp <= 0:
        return None
    return terp / p_cum
