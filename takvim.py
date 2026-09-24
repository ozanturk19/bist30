"""D-24: /api/takvim -- bilanco, temettu ve makro olaylari tek, tarihe gore sirali listede.

Kanon (docs/URUN-VE-TASARIM.md §2-§3):
- Sirket olgulari yalniz aciklanan veriden. Temettu = kar payi dagitim bildirimleri,
  "aciklandi" = finansal raporun yayin tarihi; ikisi de D-40a0 kaydindan okunur
  (data/kap_fin/<T>.json, tools/build_kap_financials.py uretir; sema 1:
  derived.son_rapor, derived.temettu_odemeleri, flags.banka). Kayit yoksa o hissenin
  temettusu ve "aciklandi" bilgisi yoktur: bos kalir, uydurulmaz.
- Dis veri bilanco tarihi her zaman date_kind="tahmini" (sirket duyurusu degil).
- Makro olaylar, yasal son gunler ve borsa gunleri yalniz resmi takvimden dogrulanmis
  sabitler (ic iz asagidaki yorumlarda; sitede ve API'de kaynak yazilmaz).

Saf fonksiyonlar: ag yok, disk yalniz okuma (load_kap_records). Python 3.9 uyumlu.
"""
from __future__ import annotations

import json
import os
from datetime import date, datetime, timedelta

SCHEMA = 1
KAP_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "kap_fin")
KAP_SCHEMA = 1          # D-40a0 kap_financials.SCHEMA_VERSION
GECMIS_GUN = 730        # 24 ay: bundan eski odeme hic tasinmaz
UFUK_GUN = 365          # tarihli olaylar: bugunden itibaren en fazla 1 yil
SON_ACIKLANAN_GUN = 14  # donem ozetindeki "son aciklananlar" penceresi
LISTE_GUN = 52          # sayfa listesi varsayilan araligi (sonrasi "olay daha" dugmesiyle)
SERIT_HAFTA = 16        # hafta seridi en fazla kac hafta

AY = ("Ocak", "Şubat", "Mart", "Nisan", "Mayıs", "Haziran", "Temmuz", "Ağustos",
      "Eylül", "Ekim", "Kasım", "Aralık")
AYK = ("Oca", "Şub", "Mar", "Nis", "May", "Haz", "Tem", "Ağu", "Eyl", "Eki", "Kas", "Ara")
GUN = ("Pazartesi", "Salı", "Çarşamba", "Perşembe", "Cuma", "Cumartesi", "Pazar")
GUN_HARF = ("P", "S", "Ç", "P", "C")

# ----------------------------------------------------------------------------- dogrulanmis sabitler

# Makro (saat TSI). Ic iz: plans/mockups/takvim_kaynaklar_ic.md, her satir >=2 kaynak.
#   TUFE: TUIK 2026 Ulusal Veri Yayimlama Takvimi (tuik.gov.tr JSON, yayindaOlmayanlarList:
#         "Tuketici Fiyat Endeksi" 2026-10-05 / 11-03 / 12-03 10:00; D-24'te ham dosyadan yeniden okundu).
#   PPK:  tcmb.gov.tr PPK 2026 takvimi (22.10, 10.12 14:00). Fed: federalreserve.gov FOMC takvimi
#         (27-28 Ekim, 8-9 Aralik) + Ekim 2026 takvimi (15-16 Eylul tutanagi 07.10).
#   ABD veri: bls.gov 2026 takvimi (istihdam, TUFE), bea.gov (PCE); OMB PFEI 2026 ile capraz.
#   ABD yaz saati 1 Kasim 2026'da biter: 8:30 ET = 15:30 -> 16:30, 14:00 ET = 21:00 -> 22:00.
# Dogrulanamayan olay eklenmez (TR issizlik, GSYH, sanayi uretimi vb. henuz yok).
MAKRO = (
    # (tarih, saat, bolge, baslik, donem, alt satir)
    ("2026-09-30", "15:30", "ABD", "PCE fiyat endeksi", "Ağustos", "Fed'in izlediği enflasyon ölçüsü"),
    ("2026-10-02", "15:30", "ABD", "Tarım dışı istihdam", "Eylül", "İşsizlik oranıyla birlikte"),
    ("2026-10-05", "10:00", "TR", "Enflasyon (TÜFE)", "Eylül", "Aynı saatte üretici fiyatları (Yİ-ÜFE)"),
    ("2026-10-07", "21:00", "ABD", "Fed toplantı tutanağı", None, "15–16 Eylül toplantısının ayrıntıları"),
    ("2026-10-14", "15:30", "ABD", "Enflasyon (TÜFE)", "Eylül", "Tüketici fiyatları, aylık ve yıllık"),
    ("2026-10-22", "14:00", "TR", "TCMB faiz kararı", None, "Para Politikası Kurulu toplantısı"),
    ("2026-10-28", "21:00", "ABD", "Fed faiz kararı", None, "Başkanın basın toplantısı 21:30"),
    ("2026-11-03", "10:00", "TR", "Enflasyon (TÜFE)", "Ekim", "Aynı saatte üretici fiyatları (Yİ-ÜFE)"),
    ("2026-11-06", "16:30", "ABD", "Tarım dışı istihdam", "Ekim", "İşsizlik oranıyla birlikte"),
    ("2026-11-10", "16:30", "ABD", "Enflasyon (TÜFE)", "Ekim", "Tüketici fiyatları, aylık ve yıllık"),
    ("2026-12-03", "10:00", "TR", "Enflasyon (TÜFE)", "Kasım", "Aynı saatte üretici fiyatları (Yİ-ÜFE)"),
    ("2026-12-04", "16:30", "ABD", "Tarım dışı istihdam", "Kasım", "İşsizlik oranıyla birlikte"),
    ("2026-12-09", "22:00", "ABD", "Fed faiz kararı", None, "Yılın son toplantısı"),
    ("2026-12-10", "14:00", "TR", "TCMB faiz kararı", None, "Yılın son toplantısı"),
    ("2026-12-10", "16:30", "ABD", "Enflasyon (TÜFE)", "Kasım", "Tüketici fiyatları, aylık ve yıllık"),
)

# Finansal rapor yasal son gunleri. Ic iz: MKK 08.01.2026 tarihli 1058 sayili genel mektup
# ("2026 yili finansal rapor ilan tarihleri"; Matriks + Ekoturk haberleri, 13.01.2026).
# Yalniz dogrulanan donem; 2026 yillik raporlari MKK'nin Ocak 2027 mektubuyla eklenir.
DONEMLER = (
    {"donem": "2026/09", "ad": "3. çeyrek", "uzun": "9 aylık", "baslangic": "2026-10-01",
     "son_gunler": (("2026-10-30", "Konsolide olmayan raporlar"),
                    ("2026-11-09", "Konsolide; bankalarda konsolide olmayan"),
                    ("2026-11-19", "Bankaların konsolide raporları"))},
)

# Borsa gunleri. Ic iz: Borsa Istanbul "Pay Piyasasi 2026 Yili Tatil Tablosu" (PDF) + 2 haber.
BORSA_GUNLERI = {
    "2026-10-28": {"not": "Borsa yarım gün", "uzun": "Cumhuriyet Bayramı arifesi · seans yarım gün"},
    "2026-10-29": {"not": "Borsa kapalı", "uzun": "Cumhuriyet Bayramı · seans yok"},
}

# ----------------------------------------------------------------------------- yardimcilar


def _d(s):
    return date.fromisoformat(s[:10])


def gun_etiketi(iso):
    """'2026-09-24' -> '24 Eylül'."""
    d = _d(iso)
    return "%d %s" % (d.day, AY[d.month - 1])


def tarih_etiketi(iso):
    """'2026-09-24' -> '24 Eylül Perşembe' (kanon §2: goreli zaman yok, tarih yazilir)."""
    return "%s %s" % (gun_etiketi(iso), GUN[_d(iso).weekday()])


def _donem_key(donem):
    try:
        y, m = donem.split("/")
        return int(y), int(m)
    except (AttributeError, ValueError):
        return None


def sonraki_donem(donem):
    """'2026/06' -> '2026/09', '2026/12' -> '2027/03'."""
    k = _donem_key(donem)
    if not k:
        return None
    y, m = k
    return "%d/%02d" % ((y + 1, 3) if m >= 12 else (y, m + 3))


_REC_CACHE = {}


def load_kap_records(tickers, base_dir=None):
    """data/kap_fin/<T>.json (mtime onbellekli). Yok/bozuk/sema farkli -> atlanir."""
    out = {}
    base = base_dir or KAP_DIR
    for t in tickers:
        path = os.path.join(base, "%s.json" % t)
        try:
            mtime = os.path.getmtime(path)
        except OSError:
            continue
        hit = _REC_CACHE.get(path)
        if hit and hit[0] == mtime:
            rec = hit[1]
        else:
            try:
                with open(path, encoding="utf-8") as f:
                    rec = json.load(f)
                if rec.get("schema_version") != KAP_SCHEMA or not isinstance(rec.get("derived"), dict):
                    rec = None
            except (OSError, ValueError):
                rec = None
            _REC_CACHE[path] = (mtime, rec)
        if rec:
            out[t] = rec
    return out


def sezon(today):
    """Bugun icin gecerli rapor donemi (son yasal gun >= bugun olan ilk donem) ya da None."""
    iso = today.isoformat()
    for d in DONEMLER:
        if d["son_gunler"][-1][0] >= iso:
            return d
    return None


# ----------------------------------------------------------------------------- temettu


def _odemeler(rec):
    """Kayittaki odeme taksitleri, 'i/n' etiketi ve GK tarihiyle."""
    pays = [p for p in ((rec.get("derived") or {}).get("temettu_odemeleri") or [])
            if p.get("hak_kullanim") and p.get("odeme") and p.get("brut")]
    by_rapor = {}
    for p in pays:
        by_rapor.setdefault((p.get("kaynak") or {}).get("rapor"), []).append(p)
    out = []
    for grp in by_rapor.values():
        grp = sorted(grp, key=lambda p: p["odeme"])
        n = len(grp)
        for i, p in enumerate(grp, 1):
            out.append({"ex": p["hak_kullanim"], "pay": p["odeme"], "brut": p["brut"], "net": p.get("net"),
                        "taksit": "tek" if n == 1 else "%d/%d" % (i, n),
                        "gk": (p.get("kaynak") or {}).get("donem")})
    return sorted(out, key=lambda p: (p["ex"], p["pay"]))


def temettu_olaylari(recs, names, prices, today, ufuk=None):
    """Hak kullanim (ex) tarihi bugun ve sonrasi olan, aciklanmis odemeler.
    date_kind: genel kurul tarihi gelecekteyse (oneri asamasi) 'tahmini', aksi halde 'kesin'."""
    iso = today.isoformat()
    ufuk = ufuk or (today + timedelta(days=UFUK_GUN)).isoformat()
    out = []
    for t, rec in recs.items():
        price = prices.get(t)
        for p in _odemeler(rec):
            if not (iso <= p["ex"] <= ufuk):
                continue
            y = round(p["brut"] / price * 100.0, 2) if price else None
            out.append({"id": "t-%s-%s" % (t, p["ex"]), "date": p["ex"], "kind": "temettu",
                        "date_kind": "tahmini" if (p["gk"] and p["gk"] > iso) else "kesin",
                        "ticker": t, "name": names.get(t, t),
                        "ex_date": p["ex"], "pay_date": p["pay"], "brut_tl": p["brut"], "net_tl": p["net"],
                        "taksit": p["taksit"], "yield_pct": y})
    return out


def temettu_ozeti(recs, today):
    """{T: {next, last}} -- siradaki aciklanmis odeme ve son 24 ayda yapilmis son odeme."""
    iso = today.isoformat()
    lo = (today - timedelta(days=GECMIS_GUN)).isoformat()
    out = {}
    for t, rec in recs.items():
        ps = [p for p in _odemeler(rec) if p["pay"] >= lo]
        nxt = next((p for p in ps if p["ex"] >= iso), None)
        paid = [p for p in ps if p["pay"] <= iso]
        if nxt or paid:
            out[t] = {"next": nxt, "last": paid[-1] if paid else None}
    return out


# ----------------------------------------------------------------------------- bilanco


def _son_rapor(rec):
    sr = ((rec or {}).get("derived") or {}).get("son_rapor") or {}
    if not sr.get("donem") or not sr.get("yayin"):
        return None
    return {"donem": sr["donem"], "date": sr["yayin"][:10]}


def bilanco(tickers, names, recs, estimates, today):
    """-> (olaylar, tarihsizler, donem_ozeti). Sezonun donemi icin her sirket tek durumda:
    aciklandi (rapor yayimlandi, tarihiyle) | tahmini tarihli olay | tarihsiz."""
    iso = today.isoformat()
    sz = sezon(today)
    events, undated, published = [], [], []
    for t in tickers:
        rec = recs.get(t)
        son = _son_rapor(rec)
        banka = bool((rec or {}).get("flags", {}).get("banka")) if rec else None
        est = estimates.get(t)
        if est and est < iso:
            est = None  # gecmiste kalan tahmin tasinmaz
        if sz:
            if son and _donem_key(son["donem"]) >= _donem_key(sz["donem"]):
                published.append({"ticker": t, "name": names.get(t, t), "date": son["date"]})
                continue
            if est and not (sz["baslangic"] <= est <= _gun_ekle(sz["son_gunler"][-1][0], 30)):
                est = None  # sezon penceresi disindaki tahmin baska bir doneme ait olabilir
            donem = sz["donem"]
        else:
            donem = sonraki_donem(son["donem"]) if son else None
        if est:
            events.append({"id": "b-%s-%s" % (t, est), "date": est, "kind": "bilanco", "sub": "rapor",
                           "date_kind": "tahmini", "ticker": t, "name": names.get(t, t),
                           "donem": donem, "banka": banka, "son_rapor": son})
        elif sz:
            undated.append({"ticker": t, "name": names.get(t, t), "kind": "bilanco",
                            "donem": donem, "son_rapor": son})
    for dl, kapsam in (sz["son_gunler"] if sz else ()):
        if dl >= iso:
            events.append({"id": "s-%s" % dl, "date": dl, "kind": "bilanco", "sub": "son_gun",
                           "date_kind": "kesin", "ticker": None, "donem": sz["donem"],
                           "title": "%s rapor için son gün" % sz["uzun"], "detail": kapsam})
    lo = (today - timedelta(days=SON_ACIKLANAN_GUN)).isoformat()
    ozet = None
    if sz:
        ozet = {"donem": sz["donem"], "ad": sz["ad"], "uzun": sz["uzun"], "baslangic": sz["baslangic"],
                "son_gunler": [{"date": d, "kapsam": k} for d, k in sz["son_gunler"]],
                "tahmini": sum(1 for e in events if e.get("sub") == "rapor"),
                "tarihsiz": len(undated), "aciklandi": len(published),
                "son_aciklananlar": sorted((p for p in published if p["date"] >= lo),
                                           key=lambda p: (p["date"], p["ticker"]), reverse=True)}
    return events, sorted(undated, key=lambda u: u["ticker"]), ozet


def _gun_ekle(iso, n):
    return (_d(iso) + timedelta(days=n)).isoformat()


def donem_ozeti(today):
    """/api/bilanco-mini ve Gundem bandi icin: dogrulanmis donem penceresi (baslangic -> son yasal gun)."""
    sz = sezon(today)
    if not sz:
        return []
    start, end = _d(sz["baslangic"]), _d(sz["son_gunler"][-1][0])
    active = today >= start
    return [{"label": "%s raporları" % sz["ad"].capitalize(), "donem": sz["donem"],
             "desc": "%s raporlar; son gün %s" % (sz["uzun"].capitalize(),
                                                  ", ".join(gun_etiketi(d) for d, _ in sz["son_gunler"])),
             "start": start.isoformat(), "end": end.isoformat(),
             "status": "active" if active else "upcoming",
             "days_label": ("%d gün kaldı" % (end - today).days) if active
                           else ("%d gün sonra" % (start - today).days)}]


# ----------------------------------------------------------------------------- makro


def makro_olaylari(today, ufuk=None):
    iso = today.isoformat()
    ufuk = ufuk or (today + timedelta(days=UFUK_GUN)).isoformat()
    out = []
    for i, (d, saat, bolge, baslik, donem, alt) in enumerate(MAKRO):
        if iso <= d <= ufuk:
            out.append({"id": "m-%s-%d" % (d, i), "date": d, "kind": "makro", "date_kind": "kesin",
                        "ticker": None, "time": saat, "region": bolge, "title": baslik,
                        "period": donem, "detail": alt})
    return out


# ----------------------------------------------------------------------------- birlesik


_KIND_ORDER = {"temettu": 0, "bilanco": 1, "makro": 2}


def _sort_key(e):
    # ayni gunde: temettu, bilanco (sirket raporlari, sonra son gun), makro (saatine gore)
    return (e["date"], _KIND_ORDER[e["kind"]], 1 if e.get("sub") == "son_gun" else 0,
            e.get("time") or "", e.get("ticker") or "")


def build(tickers, names, recs, estimates, prices, today, fiyat_tarihi=None, updated_at=None):
    """/api/takvim yuku. tickers = analiz evreni (endeks haric)."""
    ufuk = (today + timedelta(days=UFUK_GUN)).isoformat()
    uni = list(tickers)
    uset = set(uni)
    recs = {t: r for t, r in recs.items() if t in uset}
    b_events, undated, ozet = bilanco(uni, names, recs, estimates or {}, today)
    events = temettu_olaylari(recs, names, prices or {}, today, ufuk) + \
        [e for e in b_events if e["date"] <= ufuk] + makro_olaylari(today, ufuk)
    events.sort(key=_sort_key)
    counts = {"all": len(events)}
    for k in _KIND_ORDER:
        counts[k] = sum(1 for e in events if e["kind"] == k)
    iso = today.isoformat()
    return {"schema": SCHEMA, "asof": iso, "updated_at": updated_at, "fiyat_tarihi": fiyat_tarihi,
            "kapsam": len(uni), "kap_kayit": len(recs), "events": events, "undated": undated,
            "bilanco_donemi": ozet, "counts": counts,
            "days": {d: v for d, v in BORSA_GUNLERI.items() if iso <= d <= ufuk}}


# ----------------------------------------------------------------------------- SSR baglami (/takvim)


def _durum(signal):
    return {"AL": "g", "SAT": "b"}.get(signal, "y")


def ssr_context(payload, stocks, today):
    """Sayfa icin sunucu tarafli baglam: gun gruplari + hafta seridi + mini kart verisi.
    stocks: {T: {price, change_pct, borsapusula_skoru, signal}} (/api/data kaydi)."""
    iso = today.isoformat()
    events = [e for e in (payload.get("events") or []) if e.get("date", "") >= iso]
    days = payload.get("days") or {}
    more_after = (today + timedelta(days=LISTE_GUN)).isoformat()
    rows = []
    for e in events:
        r = dict(e)
        s = stocks.get(e.get("ticker")) if e.get("ticker") else None
        if s:
            r["hisse"] = {"change_pct": s.get("change_pct"), "bp": s.get("borsapusula_skoru"),
                          "durum": _durum(s.get("signal"))}
        r["kalan"] = (_d(e["date"]) - today).days
        rows.append(r)
    by_date = {}
    for r in rows:
        by_date.setdefault(r["date"], []).append(r)
    for d in days:
        if d >= iso:
            by_date.setdefault(d, [])
    groups = [{"date": d, "gun": gun_etiketi(d), "hafta_gunu": GUN[_d(d).weekday()],
               "not": days.get(d), "late": d > more_after, "events": by_date[d]}
              for d in sorted(by_date)]
    late_n = sum(len(g["events"]) for g in groups if g["late"])
    # hafta seridi: bu haftanin pazartesisinden son olaya kadar (en fazla SERIT_HAFTA hafta)
    start = today - timedelta(days=today.weekday())
    last = _d(groups[-1]["date"]) if groups else today
    kinds = {}
    for r in rows:
        kinds.setdefault(r["date"], []).append({"temettu": "t", "bilanco": "b", "makro": "m"}[r["kind"]])
    weeks = []
    w = start
    while w <= last and len(weeks) < SERIT_HAFTA:
        ds = []
        for i in range(5):
            x = w + timedelta(days=i)
            xi = x.isoformat()
            ks = sorted(kinds.get(xi, []), key=lambda k: "tbm".index(k))
            note = days.get(xi)
            ds.append({"date": xi, "gun_no": x.day, "harf": GUN_HARF[i], "past": xi < iso, "now": xi == iso,
                       "off": bool(note and note["not"] == "Borsa kapalı"),
                       "half": bool(note and note["not"] != "Borsa kapalı"),
                       "kinds": ks, "etiket": tarih_etiketi(xi), "not": note})
        a, b = w, w + timedelta(days=4)
        label = ("%d–%d %s" % (a.day, b.day, AYK[a.month - 1]) if a.month == b.month
                 else "%d %s – %d %s" % (a.day, AYK[a.month - 1], b.day, AYK[b.month - 1]))
        weeks.append({"label": label, "ay_basi": not weeks or any(x["gun_no"] == 1 for x in ds), "days": ds})
        w += timedelta(days=7)
    fd = payload.get("fiyat_tarihi")
    return {"asof": iso, "asof_label": tarih_etiketi(iso), "groups": groups, "weeks": weeks,
            "more_after": more_after, "more_label": gun_etiketi(_gun_ekle(more_after, 1)), "late_n": late_n,
            "last_label": gun_etiketi(groups[-1]["date"]) if groups else None,
            "counts": payload.get("counts") or {"all": 0, "bilanco": 0, "temettu": 0, "makro": 0},
            "undated": payload.get("undated") or [], "donem": payload.get("bilanco_donemi"),
            "fiyat_label": gun_etiketi(fd) if fd else None, "kapsam": payload.get("kapsam")}
