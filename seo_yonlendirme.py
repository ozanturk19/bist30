"""D-66 / D-67: yönlendirme ve dizinleme hijyeni — saf yardımcılar (Flask/app.py'yi import etmez).

D-66  /ozet/<gün>: o günün Akşam Bülteni varsa tek 301 → /bulten/<gün> (soru H1'li, Article
      JSON-LD'li aynı gün sayfası); bülteni olmayan eski günler noindex, follow (app.py).
D-67  /hisse/XU030 ve /hisse/XU100 endeks kodu, hisse değil → /hisseler'deki endeks bölümüne tek 301;
      /hisseler bağlamına `hisseler_endeks` (KAP endeks üyeliği + dönem etiketi, C-85 bölümleri için).
C-84  /llms.txt yer tutucuları ([[AD]]) istek anında dolar; dolmayan satır düşer.
"""
from datetime import datetime
from zoneinfo import ZoneInfo

_TZ_TR = ZoneInfo("Europe/Istanbul")

# D-67: endeks kodunun sayfası yok; /hisseler'deki bölüm çapası (C-85: #bist30 / #bist100)
ENDEKS_SAYFASI = {"XU030": "/hisseler#bist30", "XU100": "/hisseler#bist100"}

# BIST endeks dönemleri çeyreklik: 1 Ocak / 1 Nisan / 1 Temmuz / 1 Ekim
_CEYREK = ("Ocak–Mart", "Nisan–Haziran", "Temmuz–Eylül", "Ekim–Aralık")


def ozet_hedefi(tarih, bulten_gunleri):
    """/ozet/<tarih> için 301 hedefi ya da None (bülten yok → sayfa noindex, follow ile kalır)."""
    return "/bulten/" + tarih if tarih in set(bulten_gunleri or ()) else None


def donem_etiketi(generated_at, tz=_TZ_TR):
    """universe.json `generated_at` ('2026-10-12T04:00:03+0000') → 'Ekim–Aralık 2026'.
    Üyelik dosyası KAP Endeksler sayfasının o anki listesidir; hangi çeyrekte (TR saatiyle)
    üretildiyse o dönemin listesidir. Okunamazsa None."""
    try:
        dt = datetime.strptime(str(generated_at), "%Y-%m-%dT%H:%M:%S%z").astimezone(tz)
    except (TypeError, ValueError):
        return None
    return "%s %d" % (_CEYREK[(dt.month - 1) // 3], dt.year)


def hisseler_endeks(universe, evren, adlar):
    """/hisseler bağlamı: {"bist30": [(kod, ad)], "bist100": [(kod, ad)], "donem": "Ekim–Aralık 2026",
    "eksik": [kod]} ya da None. Üyelik universe.json `indices` XU030/XU100'den (KAP); listelerde
    yalnız sayfası olan (`evren`, analiz evreni) kodlar, koda göre sıralı; sayfası olmayan üye
    `eksik`te (bağlantı 404 olmasın). Evren dosyası yoksa ya da dönem okunamazsa None (şablon
    bölümleri çizmez, elle liste yok)."""
    idx = (universe or {}).get("indices") or {}
    donem = donem_etiketi((universe or {}).get("generated_at"))
    if not donem or not idx.get("XU030") or not idx.get("XU100"):
        return None
    evren = set(evren)
    out = {"donem": donem, "eksik": []}
    for ad, kod in (("bist30", "XU030"), ("bist100", "XU100")):
        uyeler = sorted(set(idx[kod]))
        out[ad] = [(t, adlar.get(t, t)) for t in uyeler if t in evren]
        out["eksik"] += [t for t in uyeler if t not in evren and t not in out["eksik"]]
    return out


def yer_tutucu_doldur(metin, yer):
    """C-84: `[[AD]]` yer tutucularını `yer` sözlüğünden doldurur; değeri boş olan yer tutucuyu
    taşıyan SATIR metinden düşer (ör. şablon yayında değil, hiç bülten yok → 404/302'ye bağlantı yok)."""
    for k, v in yer.items():
        if v:
            metin = metin.replace(k, v)
    return "\n".join(ln for ln in metin.split("\n") if "[[" not in ln)
