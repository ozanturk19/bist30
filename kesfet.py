"""D-59: Keşfet -- orta-uzun vade listeleri (C-56'nin arka ucu).

Dort hazir liste, kural tabanli, yalniz sirketin KAP'ta acikladigi rakamlardan (kap_temel_v2
turetmeleri; kendi duzeltmemiz yok, AI yok) ve son kapanis fiyatindan:

  kaliteli_makul       Kaliteli ve makul fiyatli
  istikrarli_temettu   Istikrarli temettu
  borcsuz_buyuyen      Borcsuz buyuyenler
  sektorune_gore_ucuz  Sektorune gore ucuz

Her listenin kurali TEK cumle (KURAL): sayfada ve metodolojide ayni metin; kod bu cumleyle
birebir ayni seyi yapar (testler cumleyi degil kurali sinar, cumle degisirse kural da degismeli).

Ortak kapi (dort liste):
- KAP kaydi olan, son kapanisi donuk olmayan hisse (endeks satiri yok).
- Veri tamligi SABLONA GORE (D-58): sablonun (sanayi / GYO / banka / sigorta) bekledigi
  gostergelerden hesaplanabilenlerin orani >= 0,8. Bankada net borc, cari oran, kar marji gibi
  sablonda olmayan olculer eksik sayilmaz. Tanim D-40c (temel_skor_v2) veri_tamligi ile birebir
  (EXPECTED = INPUTS tablosu; parite testi D-40c gelince kosar). Bayraktan bagimsiz tek yol:
  TEMEL_V2 acikken sigortanin "eksen yetersiz" limited_data'si (siralama havuzu <5) listeden
  dusurmez -- o bir puanlama siniri, veri eksigi degil.
- Degerleme hukmu hisse sayfasindaki "Fiyati makul mu?" ile tek kaynak (home_fields.valuation):
  v2 acikken temel_v2.degerleme.hukum; kapaliyken KAP F/K (son 12 ay) ve PD/DD'nin ayni D-23
  kovasindaki KAP ortancasina orani (kap_temel_v2.sector_medians: en az 5 sirket; kovada yetmezse
  sirketin KAP sektoru havuzu (D-23b with_fallback); o da yoksa hukum yok).
- TEMEL_V2 acikken BP (Temel v2 %60 + Trend %40) ve degerleme hukmu skor kaydindaki temel_v2'den
  gelir (satir rozeti ve sira); kurallar ve cumleler iki modda ayni.
- Siralar sabit ve aciklanabilir: kalite ve buyume listesi BorsaPusula Skoru'na, temettu listesi
  son 12 ay verimine, ucuzluk listesi sektor ortancasina gore iskontoya gore; esitlikte kod.

Saf fonksiyonlar (ag yok, Flask yok, py3.9 uyumlu). app.py ince baglanti: build() + view().
"""
from __future__ import annotations

import statistics
from datetime import date, datetime, timedelta

import home_fields
import kap_financials as kf
import kap_temel_v2 as kt

LISTS = ("kaliteli_makul", "istikrarli_temettu", "borcsuz_buyuyen", "sektorune_gore_ucuz")
SLUG = {"kaliteli_makul": "kaliteli-makul", "istikrarli_temettu": "istikrarli-temettu",
        "borcsuz_buyuyen": "borcsuz-buyuyenler", "sektorune_gore_ucuz": "sektorune-gore-ucuz"}
_BY_SLUG = {v: k for k, v in SLUG.items()}
BASLIK = {"kaliteli_makul": "Kaliteli ve makul fiyatlı", "istikrarli_temettu": "İstikrarlı temettü",
          "borcsuz_buyuyen": "Borçsuz büyüyenler", "sektorune_gore_ucuz": "Sektörüne göre ucuz"}
# GEO: soru bicimli baslik (sayfa H1/H2 ve JSON-LD ItemList adi)
SORU = {"kaliteli_makul": "Hangi şirketler kaliteli ve makul fiyatlı?",
        "istikrarli_temettu": "Hangi şirketler istikrarlı temettü ödüyor?",
        "borcsuz_buyuyen": "Hangi şirketler borçsuz büyüyor?",
        "sektorune_gore_ucuz": "Hangi şirketler sektörüne göre ucuz?"}
KURAL = {   # gri dil envanteri K9: kullanicinin gordugu metinde "ortanca" yok, "orta deger" var
    "kaliteli_makul": ("Kârlı olan, özsermaye kârlılığı ve net kâr marjı sektörünün en iyi üçte birinde, fiyatı "
                       "F/K ve PD/DD'ye göre sektörüne kıyasla ucuz ya da makul olan şirketler (banka, sigorta, "
                       "gayrimenkul ve holding şirketleri hariç); BorsaPusula Skoru'na göre sıralı."),
    "istikrarli_temettu": ("Hem son 12 ayda hem de ondan önceki 12 ayda nakit temettü ödemiş şirketler; "
                           "son 12 ayın temettü verimine göre sıralı."),
    "borcsuz_buyuyen": ("Nakdi ve kısa vadeli yatırımları finansal borcundan fazla olan, son yıllık raporunda "
                        "satışlarını artırıp yılı kârla kapatan şirketler; BorsaPusula Skoru'na göre sıralı."),
    "sektorune_gore_ucuz": ("F/K'sı da PD/DD'si de sektörünün orta değerinin altında olan, fiyatı ucuz tarafta "
                            "şirketler; sektörüne göre en ucuzdan sıralı."),
}
VARSAYILAN = LISTS[0]

MIN_COMPLETENESS = 0.8           # C-56: listelere giris (D-40c LIST_COMPLETENESS ile ayni)
MIN_PEERS = kt.MIN_PEERS_KAP     # sektor ortancasi en az 5 sirket (hisse sayfasiyla ayni)
PIOTROSKI_MIN_ITEMS = 7          # D-40c ile ayni: 9 maddenin en az 7'si
BANK_MIN_ITEMS = 4               # D-40c ile ayni: 5 maddenin en az 4'u
# Kaliteli listesi (onayli taslak temel-v2 + D-40c list_membership): yalniz sanayi sablonu; holding ve
# gayrimenkul kovalari disarida (GYO/gayrimenkulde net kar degerleme kazanciyla sisiyor, holdingde
# istirak geliri -- kalite sinyali degil). Kalite olcusu sektorun en iyi ucte biri (D-40c kalite >= 70).
KALITE_DISI_KOVA = ("Holding ve Yatırım", "Gayrimenkul")
TREND = {"AL": ("g", "Güçlü Trend"), "SAT": ("b", "Trend Bozuldu"), "BEKLE": ("y", "Yatay")}

# Sablonun bekledigi gostergeler (veri tamligi paydasi) -- D-40c temel_skor_v2.INPUTS ile ayni.
EXPECTED = {
    "sanayi": ("roe", "net_marj", "saglamlik", "fk", "pd_dd", "gelir_deg", "kar_deg", "ara_gelir_deg",
               "ara_kar_deg", "nb_favok", "cari_oran", "sureklilik", "verim"),
    "gyo": ("roe", "net_marj", "saglamlik", "pd_dd", "gelir_deg", "kar_deg", "ara_gelir_deg", "ara_kar_deg",
            "nb_ozkaynak", "cari_oran", "sureklilik", "verim"),
    "banka": ("roe", "gider_gelir", "saglamlik", "fk", "pd_dd", "gelir_deg", "kar_deg", "ara_gelir_deg",
              "ara_kar_deg", "kredi_mevduat", "ozkaynak_varlik", "sureklilik", "verim"),
    "sigorta": ("roe", "fk", "pd_dd", "kar_deg", "ozkaynak_deg", "ara_kar_deg", "sureklilik", "verim"),
}


# ----------------------------------------------------------------------------- yardimcilar

def _num(v):
    return isinstance(v, (int, float)) and not isinstance(v, bool) and v == v


def _fmt(x, nd=1):
    """Kanon sayi bicimi: ondalik virgul, binlik nokta (§2.10)."""
    s = ("{:,.%df}" % nd).format(abs(x)).replace(",", "_").replace(".", ",").replace("_", ".")
    return ("−" if x < 0 else "") + s


def _pct(x, nd=1, signed=False):
    sign = ("+" if x > 0 else ("−" if x < 0 else "")) if signed else ("−" if x < 0 else "")
    return sign + "%" + _fmt(abs(x), nd)


def _money(tl):
    """Tutar: Mrd ₺ / Mn ₺ (kanon)."""
    a = abs(tl)
    if a >= 1e9:
        return _fmt(tl / 1e9, 1 if a < 1e11 else 0) + " Mrd ₺"
    return _fmt(tl / 1e6, 0) + " Mn ₺"


def resolve(slug):
    """URL parcasi -> liste anahtari (ic anahtar da kabul). Bilinmiyorsa None."""
    s = (slug or "").strip().lower()
    if s in _BY_SLUG:
        return _BY_SLUG[s]
    return s if s in LISTS else None


def _iso(bar_date):
    try:
        return datetime.strptime(bar_date, "%d.%m.%Y").date().isoformat()
    except (TypeError, ValueError):
        return None


# ----------------------------------------------------------------------------- tek sirket (KAP)

def company_facts(rec, price=None, today=None, yahoo_shares=None):
    """Tek sirketin liste ve veri tamligi girdileri, yalniz KAP kaydindan (+ son kapanis).
    Kayit ya da rapor yoksa None."""
    if not rec or not rec.get("reports"):
        return None
    today = today or date.today()
    tpl = kt.template_of(rec)
    d = rec.get("derived") or {}
    ann = kt._annual(rec)
    a = ann[-1] if ann else None
    now = kt.valuation_now(rec, tpl, price, yahoo_shares) if price and price > 0 else None
    last = kt._latest(rec)
    sh = kt.shares_of(last)
    pay_uyumsuz = bool(yahoo_shares and sh and not (kt.SHARE_SANITY[0] < sh / yahoo_shares < kt.SHARE_SANITY[1]))
    priced = bool(price) and price > 0 and not pay_uyumsuz and bool(sh)
    ttm = kt.ttm_net_income(rec)
    eq_last = kt._tl(last, kt._equity(last, tpl))
    f = {"sablon": tpl, "esas": d.get("basis"), "yil": a["fy"] if a else None,
         "fk": (now or {}).get("fk"), "pd_dd": (now or {}).get("pd_dd"), "fiyat_var": now is not None,
         # ozsermaye karliligi (son 12 ay) fiyattan bagimsiz; valuation_now ile ayni formul
         "roe": (kt._pct(ttm["tutar"], eq_last)
                 if ttm and ttm.get("tutar") is not None and eq_last and eq_last > 0 else None),
         "pay_uyumsuz": pay_uyumsuz,
         "yillik_kar": kt._v(a, "net_income_parent") if a else None,
         # zararda F/K ve negatif ozkaynakta PD/DD tanimsiz: veri eksigi sayilmaz (D-40c)
         "fk_hesaplanir": priced and ttm is not None and ttm.get("tutar") is not None,
         "pd_dd_hesaplanir": priced and eq_last is not None}

    # Kalite: net kar marji (sanayi/GYO) ya da gider/gelir (banka); saglamlik maddeleri
    if tpl in ("sanayi", "gyo"):
        f["net_marj"] = (kt.margins(a) or {}).get("net") if a else None
        pio = kt.piotroski(a) if a else None
        f["saglamlik_toplam"] = pio["toplam"] if pio else 0
    elif tpl == "banka":
        br = kt.bank_ratios(a) if a else {}
        f["gider_gelir"] = br.get("gider_gelir")
        f["kredi_mevduat"] = br.get("kredi_mevduat")
        f["ozkaynak_varlik"] = kt._pct(kt._equity(a, tpl), kt._v(a, "total_assets")) if a else None
        bc = kt.bank_checks(a) if a else None      # ozsermaye karliligi maddesi ortancayla tamlikta eklenir
        f["saglamlik_toplam"] = bc["toplam"] if bc else 0

    # Buyume: sirketin ayni rapordaki karsilastirmasi (son yillik + son ara donem kumulatif)
    rev_key = "operating_income" if tpl == "banka" else "revenue"

    def chg(rep, key):
        return kf.pct_change(*kt._pair(rep, key, tpl)) if rep else None
    nxt = [r for r in kt._interim(rec) if a is None or r["fy"] > a["fy"]]
    i = nxt[-1] if nxt else None
    f["kar_deg"] = chg(a, "net_income_parent")
    f["ara_kar_deg"] = chg(i, "net_income_parent")
    if tpl == "sigorta":
        f["ozkaynak_deg"] = chg(a, "equity_parent")
    else:
        f["gelir_deg"] = chg(a, rev_key)
        f["ara_gelir_deg"] = chg(i, rev_key)

    # Bilanco: son yillik raporun cari sutunu (Temel sekmesindeki bilanco paneliyle ayni)
    if tpl in ("sanayi", "gyo"):
        bal = (kt.balance(rec, tpl) or {}).get("cur") or {}
        nd = bal.get("net_borc")
        f["net_borc"] = nd
        f["cari_oran"] = bal.get("cari_oran")
        if tpl == "sanayi":
            fv = bal.get("favok")
            f["nb_favok"] = None if nd is None or fv is None else (round(nd / fv, 2) if fv > 0 else 0.0)
        else:
            eq_a = kt._tl(a, kt._equity(a, tpl)) if a else None
            f["nb_ozkaynak"] = (None if nd is None or eq_a is None or (eq_a <= 0 and nd <= 0)
                                else (round(nd / eq_a * 100.0, 2) if eq_a > 0 else float("inf")))

    # Temettu: odenmis taksitler (brut TL/pay); son 12 ay ve onceki 12 ay (D-40c ile ayni pencere)
    pays = [p for p in (d.get("temettu_odemeleri") or []) if p.get("odeme")]
    t0, t1, t2 = today.isoformat(), (today - timedelta(days=365)).isoformat(), (today - timedelta(days=730)).isoformat()
    son12 = [p for p in pays if t1 < p["odeme"] <= t0]
    onceki12 = [p for p in pays if t2 < p["odeme"] <= t1]
    f["temettu_son12"] = bool(son12)
    f["temettu_onceki12"] = bool(onceki12)
    brut = sum(p.get("brut") or 0.0 for p in son12)
    f["verim"] = round(brut / price * 100.0, 2) if price and price > 0 else None
    return f


def completeness(f, roe_median=None):
    """Sablona gore veri tamligi (D-58; D-40c veri_tamligi tanimi): sablonun bekledigi
    gostergelerden hesaplanabilenlerin orani. Bankada ozsermaye karliligi maddesi banka
    ortancasi varsa saglamlik maddelerine eklenir."""
    if not f:
        return 0.0
    tpl = f["sablon"]
    exp = EXPECTED[tpl]
    have = 0
    for m in exp:
        if m == "saglamlik":
            tot = f.get("saglamlik_toplam") or 0
            if tpl == "banka" and f.get("roe") is not None and roe_median is not None:
                tot += 1
            have += 1 if tot >= (BANK_MIN_ITEMS if tpl == "banka" else PIOTROSKI_MIN_ITEMS) else 0
        elif m in ("fk", "pd_dd"):
            have += 1 if f.get(m + "_hesaplanir") else 0
        elif m == "sureklilik":
            have += 1
        else:
            have += 1 if f.get(m) is not None else 0
    return round(have / len(exp), 2)


# ----------------------------------------------------------------------------- sektor ortancalari

def sector_medians(facts, bucket_of):
    """{kova: {fk, pd_dd, ozsermaye_karliligi, net_marj, roe_ust, net_marj_ust}} -- her biri
    {deger, n, kapsam} ya da None. F/K, PD/DD ve ozsermaye karliligi hisse sayfasindaki ortancayla
    ayni fonksiyondan (kap_temel_v2.sector_medians); net kar marji ortancasi ve kalite esikleri
    (*_ust: sektorun en iyi ucte birinin alt siniri) ayni kuralla (en az 5 sirket, 'Diger' kovasinda
    yok) ve ayni havuzla (ozsermaye karliligi fiyati olan sirketlerden, marj tum sirketlerden)."""
    # kap_temel_v2.kap_metrics ile ayni girdi: fiyat yoksa uc deger de yok
    metrics = {tk: ({"fk": f.get("fk"), "pd_dd": f.get("pd_dd"), "ozsermaye_karliligi": f.get("roe")}
                    if f.get("fiyat_var") else {}) for tk, f in facts.items() if f}
    sector_of = (lambda t: bucket_of.get(t)) if isinstance(bucket_of, dict) else bucket_of
    out = {}
    for b in sorted({sector_of(t) for t in facts if facts[t]} - {None}):
        med = kt.sector_medians(metrics, sector_of, b)
        ok = b != "Diğer"
        roe = [m["ozsermaye_karliligi"] for t, m in metrics.items()
               if sector_of(t) == b and _num(m.get("ozsermaye_karliligi"))]
        nm = [f["net_marj"] for t, f in facts.items() if f and sector_of(t) == b and _num(f.get("net_marj"))]
        med["net_marj"] = ({"deger": round(statistics.median(nm), 2), "n": len(nm), "kapsam": "sektor"}
                           if ok and len(nm) >= MIN_PEERS else None)
        for k, vals in (("roe_ust", roe), ("net_marj_ust", nm)):
            med[k] = ({"deger": round(statistics.quantiles(vals, n=3, method="inclusive")[1], 2),
                       "n": len(vals), "kapsam": "sektor"} if ok and len(vals) >= MIN_PEERS else None)
        out[b] = med
    return out


def with_fallback(med, kap_med):
    """D-23b: kovanin ortancasi (sector_medians[kova]) + eksik metrik icin sirketin KAP sektoru
    ortancasi (ayni fonksiyon, sector_taxonomy.kap_bucket_for havuzuyla). Duzeltme tablosu kovayi
    kucultse de ortanca D-23 oncesinden geri gitmez; hisse sayfasindaki yedekle ayni kural."""
    if not kap_med:
        return med or {}
    out = dict(med or {})
    for k, v in kap_med.items():
        if out.get(k) is None and v is not None:
            out[k] = dict(v, havuz="kap")
    return out


def _mv(med, k):
    m = (med or {}).get(k)
    return m.get("deger") if m and m.get("kapsam") == "sektor" else None


# ----------------------------------------------------------------------------- kurallar

def _quality(f, med, bucket=None):
    """kaliteli_makul kalite kosulu (onayli taslak + D-40c): sanayi sablonu, holding ve gayrimenkul
    kovasi degil; ozsermaye karliligi ve net kar marji ikisi de pozitif ve sektorun en iyi ucte birinde
    (esik: sektor dagiliminin 2/3 noktasinin ustu, en az 5 sirket; esitlik ust ucte bire sayilmaz).
    Banka, sigorta ve GYO girmez."""
    if f.get("sablon") != "sanayi" or bucket in KALITE_DISI_KOVA:
        return False
    for k, ek in (("roe", "roe_ust"), ("net_marj", "net_marj_ust")):
        v, cut = f.get(k), _mv(med, ek)
        if not (_num(v) and cut is not None and v > 0 and v > cut):
            return False
    return True


def _cheap(f, med):
    """(F/K / ortanca, PD/DD / ortanca) ikisi de 1'in altindaysa ortalama oran, degilse None."""
    q = []
    for k in ("fk", "pd_dd"):
        v, m = f.get(k), _mv(med, k)
        if not (_num(v) and v > 0 and m and m > 0):
            return None
        q.append(v / m)
    return sum(q) / 2.0 if all(x < 1 for x in q) else None


def memberships(f, med, verdict, bucket=None):
    """Bir sirketin girdigi listeler (ortak kapidan gecmis sirket icin); bucket: D-23 kovasi."""
    out = []
    if verdict in ("ucuz", "makul") and _quality(f, med, bucket):
        out.append("kaliteli_makul")
    if f.get("temettu_son12") and f.get("temettu_onceki12") and _num(f.get("verim")) and f["verim"] > 0:
        out.append("istikrarli_temettu")
    if (f["sablon"] in ("sanayi", "gyo") and _num(f.get("net_borc")) and f["net_borc"] < 0
            and _num(f.get("gelir_deg")) and f["gelir_deg"] > 0
            and _num(f.get("yillik_kar")) and f["yillik_kar"] > 0):
        out.append("borcsuz_buyuyen")
    if verdict == "ucuz" and _cheap(f, med) is not None:
        out.append("sektorune_gore_ucuz")
    return out


def reason(key, f, med):
    """Satirin tek cumlelik nedeni: kuralin olctugu rakamlar, betim (yargi yok)."""
    if key == "kaliteli_makul":
        return "Özsermaye kârlılığı %s (sektör %s), net kâr marjı %s (sektör %s)" % (
            _pct(f["roe"]), _pct(_mv(med, "ozsermaye_karliligi")), _pct(f["net_marj"]), _pct(_mv(med, "net_marj")))
    if key == "istikrarli_temettu":
        return "Son 12 ayda temettü verimi %s; önceki 12 ayda da ödeme yaptı" % _pct(f["verim"])
    if key == "borcsuz_buyuyen":
        return "%s yılında satışlar %s, net nakit %s" % (f["yil"], _pct(f["gelir_deg"], 1, signed=True),
                                                       _money(-f["net_borc"]))
    if key == "sektorune_gore_ucuz":
        return "F/K %s (sektör %s), PD/DD %s (sektör %s)" % (
            _fmt(f["fk"], 2), _fmt(_mv(med, "fk"), 2), _fmt(f["pd_dd"], 2), _fmt(_mv(med, "pd_dd"), 2))
    return None


def _sort_key(key, row, f, med):
    if key == "istikrarli_temettu":
        return (-(f.get("verim") or 0.0), row["ticker"])
    if key == "sektorune_gore_ucuz":
        return (_cheap(f, med), row["ticker"])
    return (-(row["bp"] if _num(row["bp"]) else -1), row["ticker"])


# ----------------------------------------------------------------------------- evren

def verdict(entry, f, med):
    """Hisse sayfasi "Fiyati makul mu?" ile ayni hukum (home_fields.valuation)."""
    fund = {"kap_durum": "var",
            "kap": {"degerleme_simdi": {"fk": f.get("fk"), "pd_dd": f.get("pd_dd"),
                                        "pay_uyumsuz": f.get("pay_uyumsuz")}},
            "sektor_ortanca": {k: (med or {}).get(k) for k in ("fk", "pd_dd")}}
    return home_fields.valuation(entry, fund)


def build(stocks, entries, records, shares=None, bucket_of=None, names=None, today=None, kap_bucket_of=None):
    """stocks: _cache satirlari (ticker, price, signal, stale_reason, data_quality, bar_date, name);
    entries: {T: saglik kaydi (borsapusula_skoru, temel_v2...)}; records: {T: KAP kaydi};
    shares: {T: Yahoo pay adedi} (pay adedi sagligi, hisse sayfasiyla ayni); bucket_of: {T: D-23 kovasi}
    ya da fonksiyon; names: {T: gorunen ad}; kap_bucket_of: {T: yalniz KAP'tan kova} ya da fonksiyon
    (D-23b ortanca yedegi, with_fallback). Donus: {"tarih", "listeler": {anahtar: [satir]}}. Satir: ticker, name, sector, bp, trend, trend_kod, degerleme, neden, sablon."""
    today = today or date.today()
    shares = shares or {}
    names = names or {}
    sector_of = (lambda t: bucket_of.get(t)) if isinstance(bucket_of, dict) else (bucket_of or (lambda t: None))
    kap_of = (lambda t: kap_bucket_of.get(t)) if isinstance(kap_bucket_of, dict) else kap_bucket_of
    rows = [s for s in stocks or [] if isinstance(s, dict) and s.get("ticker")]
    # Ortancalar donuk satirlar dahil tum evrenden (hisse sayfasindaki _kap_sector_metrics ile ayni
    # havuz); listeye yalniz son kapanisi donuk olmayan hisse girer (one cikan havuzuyla ayni kural).
    live = [s for s in rows if not s.get("stale_reason") and s.get("data_quality") != "stale"]
    facts = {}
    for s in rows:
        tk = s["ticker"]
        try:
            facts[tk] = company_facts((records or {}).get(tk), s.get("price"), today, shares.get(tk))
        except Exception:      # tek bozuk kayit listeyi dusurmesin
            facts[tk] = None
    meds = sector_medians(facts, sector_of)
    kap_meds = sector_medians(facts, kap_of) if kap_of else {}
    lists = {k: [] for k in LISTS}
    keys = {k: {} for k in LISTS}
    for s in live:
        tk = s["ticker"]
        f = facts.get(tk)
        if not f:
            continue
        b = sector_of(tk)
        med = with_fallback(meds.get(b), kap_meds.get(kap_of(tk)) if kap_of else None)
        entry = ((entries or {}).get(tk)) or {}
        if completeness(f, _mv(med, "ozsermaye_karliligi")) < MIN_COMPLETENESS:
            continue
        hk = verdict(entry, f, med)
        tr = TREND.get(s.get("signal"))
        bp = entry.get("borsapusula_skoru")
        row = {"ticker": tk, "name": names.get(tk) or s.get("name") or tk, "sector": b,
               "bp": int(round(bp)) if _num(bp) else None,
               "trend": tr[1] if tr else None, "trend_kod": tr[0] if tr else None,
               "degerleme": hk, "sablon": f["sablon"]}
        for key in memberships(f, med, hk, b):
            r = dict(row, neden=reason(key, f, med))
            lists[key].append(r)
            keys[key][tk] = _sort_key(key, r, f, med)
    for key in LISTS:
        lists[key].sort(key=lambda r, k=key: keys[k][r["ticker"]])
    dates = [_iso(s.get("bar_date")) for s in live]
    dates = [x for x in dates if x]
    return {"tarih": max(set(dates), key=dates.count) if dates else None, "listeler": lists}


def ready(stocks, entries, shares):
    """Sonuc onbellege yazilabilir mi: evren, skor kayitlari (BP) ve pay adetleri (pay adedi sagligi)
    birlikte yuklu. Web worker'da _cache acilista, skor ve temel onbellekleri background_refresh'in
    pid gecikmesinden (0-89 sn) sonra dolar; yarim girdiyle kurulan sonuc (BP yok, siralar alfabetik,
    yanlis pay adediyle F/K) 10 dk dondurulmasin."""
    return (bool(stocks) and any(isinstance(e, dict) and e for e in (entries or {}).values())
            and any(_num(v) and v > 0 for v in (shares or {}).values()))


def summary(result, aktif=None):
    """Liste secici: [{anahtar, slug, baslik, sayi, aktif}] (sabit sira)."""
    ls = (result or {}).get("listeler") or {}
    return [{"anahtar": k, "slug": SLUG[k], "baslik": BASLIK[k], "sayi": len(ls.get(k) or []),
             "aktif": k == aktif} for k in LISTS]


def view(result, key):
    """/api/kesfet/<liste> ve /kesfet/<liste> SSR baglami (ayni sozluk)."""
    key = key if key in LISTS else VARSAYILAN
    rows = ((result or {}).get("listeler") or {}).get(key) or []
    return {"anahtar": key, "slug": SLUG[key], "baslik": BASLIK[key], "soru": SORU[key],
            "kural": KURAL[key], "tarih": (result or {}).get("tarih"), "sayi": len(rows),
            "satirlar": rows, "listeler": summary(result, key)}


def rules():
    """Metodoloji icin: [{anahtar, slug, baslik, kural}] (sayfadakiyle ayni cumleler)."""
    return [{"anahtar": k, "slug": SLUG[k], "baslik": BASLIK[k], "kural": KURAL[k]} for k in LISTS]
