"""D-40c: Temel skor v2 -- bes eksen (kalite, degerleme, buyume, bilanco sagligi, temettu),
yalniz KAP'ta aciklanan veriyle (kap_temel_v2 turetmeleri); banka / sigorta / GYO sablonlari (D-15).

Bayrak: TEMEL_V2=1 -- yalniz gun sonu skor turunu kosturan surecte (bist30-refresh) okunur.
Kapaliyken bu modul hicbir ciktiyi degistirmez. Web sureci v2'yi skor kaydindaki 'temel_v2'
alanindan anlar (ikinci bayrak yok): bayrak kalkinca sonraki gun sonu turu eski skoru yazar.

Yontem (kanon docs/URUN-VE-TASARIM.md §3 ve §5.6; bilinen yontemler, yeni kavram yok):
- Surekli gostergeler sektor ici YUZDELIK SIRA ile puanlanir (percent rank: grubun en iyisi 100,
  en zayifi 0, esit degerler ortalama sira). Grup: ayni D-23 sektor kovasinda KAP kaydi olan
  sirketler; kova kucukse ayni sablondaki tum sirketler. Muhasebe esasina duyarli gostergeler
  (ozsermaye karliligi, tutar degisimleri) yalniz ayni esas sinifinda (enflasyon duzeltmeli /
  duzeltmesiz / banka / sigorta) siralanir. Her grup en az 5 sirket; yoksa gosterge puanlanmaz.
- Degerleme: F/K (son 12 ay kari, O22) ve PD/DD, ayni D-23 kovasindaki sirketlerin KAP
  degerlerinin ortancasina oranla (yalniz pozitif degerler, en az 5 sirket; yoksa hukum yok).
  Puan = 50 - 50 x log2(oran): ortancada 50, 0,80 katta 66, 1,25 katta 34 (kanon esikleri),
  yarisinda 100, iki katinda 0. Hukum kanon kurali (ucuz / makul / pahali / karisik).
  GYO'da yalniz PD/DD (kar buyuk olcude yatirim amacli gayrimenkul degerleme kazanci).
- Saglamlik: sanayi ve GYO'da Piotroski F-Skor 9 madde, bankada 5 madde (kap_temel_v2) ->
  gecen / hesaplanan x 100. Sigortada yok (prim ve hasar kalemleri okunmuyor).
- Temettu: sureklilik %50 (son iki 12 aylik donemin her biri 50) + son 12 ay verimi %50
  (odeme yapanlar arasinda sektor ici sira; odeme yoksa 0).
- Temel = eksenlerin agirlikli ortalamasi: kalite 30, degerleme 20, buyume 20, bilanco 20,
  temettu 10. Eksik eksenin agirligi kalanlara dagilir; 3 eksenden az ya da veri tamligi
  %60'in altindaysa skor uretilmez (limited_data).
Saf fonksiyonlar (ag yok, Flask yok, py3.9 uyumlu). app.py ince baglanti.
"""
from __future__ import annotations

import math
import os
import statistics
from datetime import date, timedelta

import kap_financials as kf
import kap_temel_v2 as kt

ENV_FLAG = "TEMEL_V2"
SURUM = 2

AXES = ("kalite", "degerleme", "buyume", "bilanco", "temettu")
AXIS_LABELS = {"kalite": "Kalite", "degerleme": "Değerleme", "buyume": "Büyüme",
               "bilanco": "Bilanço sağlığı", "temettu": "Temettü"}
WEIGHTS = {"kalite": 30, "degerleme": 20, "buyume": 20, "bilanco": 20, "temettu": 10}

MIN_POOL = 5              # her karsilastirma en az 5 sirketle (kendisi dahil); yoksa gosterge puanlanmaz
MIN_MEDIAN_N = 5          # degerleme ortancasi: kovada en az 5 pozitif deger (kanon §3)
MIN_AXES = 3
MIN_COMPLETENESS = 0.6    # D-15: altinda limited_data (skor yok, siralama disi)
LIST_COMPLETENESS = 0.8   # C-56: listelere giris
CHEAP_BELOW, EXPENSIVE_ABOVE = 0.80, 1.25    # kanon §5.6
PIOTROSKI_MIN_ITEMS = 7   # 9 maddenin en az 7'si hesaplanabilmeli
BANK_MIN_ITEMS = 4        # 5 maddenin en az 4'u
REPORT_LAG_DAYS = 195     # son rapor donem sonundan bu kadar gun eskiyse "gecikmis" (ceyrek + yasal sure)
BOLUM = {"sanayi": "reel", "gyo": "reel", "banka": "finans", "sigorta": "finans"}

# Sablon -> eksen -> gostergeler (veri tamligi paydasi da bu tablo)
INPUTS = {
    "sanayi": {"kalite": ("roe", "net_marj", "saglamlik"), "degerleme": ("fk", "pd_dd"),
               "buyume": ("gelir_deg", "kar_deg", "ara_gelir_deg", "ara_kar_deg"),
               "bilanco": ("nb_favok", "cari_oran"), "temettu": ("sureklilik", "verim")},
    "gyo": {"kalite": ("roe", "net_marj", "saglamlik"), "degerleme": ("pd_dd",),
            "buyume": ("gelir_deg", "kar_deg", "ara_gelir_deg", "ara_kar_deg"),
            "bilanco": ("nb_ozkaynak", "cari_oran"), "temettu": ("sureklilik", "verim")},
    "banka": {"kalite": ("roe", "gider_gelir", "saglamlik"), "degerleme": ("fk", "pd_dd"),
              "buyume": ("gelir_deg", "kar_deg", "ara_gelir_deg", "ara_kar_deg"),
              "bilanco": ("kredi_mevduat", "ozkaynak_varlik"), "temettu": ("sureklilik", "verim")},
    # Sigorta: bilanco sagligi icin teknik karsilik / sermaye yeterliligi kalemi okunmuyor (hayat ve
    # emeklilik sirketinde katilimci fon varliklari ozkaynak / varlik oranini anlamsiz kilar) -> eksen yok.
    "sigorta": {"kalite": ("roe",), "degerleme": ("fk", "pd_dd"),
                "buyume": ("kar_deg", "ozkaynak_deg", "ara_kar_deg"),
                "bilanco": (), "temettu": ("sureklilik", "verim")},
}
NA_AXES = {"sigorta": ("bilanco",)}     # sablon geregi hesaplanmayan eksenler (categories_na)
# Sirayla puanlanan gostergeler: True = yuksek deger iyi, False = dusuk deger iyi
HIGHER_BETTER = {"roe": True, "net_marj": True, "gider_gelir": False, "gelir_deg": True, "kar_deg": True,
                 "ara_gelir_deg": True, "ara_kar_deg": True, "ozkaynak_deg": True, "nb_favok": False,
                 "nb_ozkaynak": False, "cari_oran": True, "kredi_mevduat": False, "ozkaynak_varlik": True}
# Muhasebe esasina duyarli gostergeler (tutar degisimi ve ozsermaye karliligi): yalniz ayni esas
# sinifindaki sirketlerle siralanir -- enflasyon duzeltmeli reel TL, nominal TL ve TL'ye cevrilmis
# doviz ayni havuzda karistirilmaz (temel-cesitlendirme §6.3). Oranlar (marj, borc, cari oran,
# verim) tek raporun icinden geldigi icin sektor kovasinda siralanir.
BASIS_SENSITIVE = ("roe", "gelir_deg", "kar_deg", "ara_gelir_deg", "ara_kar_deg", "ozkaynak_deg")
BASIS_CLASS = {"tms29": "reel", "yabanci_para": "duzeltmesiz", "nominal": "duzeltmesiz",
               "banka": "banka", "sigorta": "sigorta"}
CORE_ITEMS = {
    "sanayi": ("revenue", "operating_profit", "net_income_parent", "d_and_a", "cfo", "cash",
               "current_assets", "current_liabilities", "total_assets", "equity_parent"),
    "gyo": ("revenue", "operating_profit", "net_income_parent", "cfo", "cash",
            "current_assets", "current_liabilities", "total_assets", "equity_parent"),
    "banka": ("net_interest_income", "operating_income", "net_income_parent", "loans", "deposits",
              "total_assets", "equity_total"),
    "sigorta": ("net_income_parent", "total_assets", "equity_total"),
}
SIGORTA_NOTU = ("Sigorta şirketlerinde prim, hasar ve teknik karşılık kalemleri henüz okunmuyor: kalite "
                "yalnız özsermaye kârlılığıyla ölçülüyor, bilanço sağlığı hesaplanmıyor.")
LISTS = ("kaliteli_makul", "istikrarli_temettu", "borcsuz_buyuyen", "sektorune_gore_ucuz")
_HOLDING = "Holding ve Yatırım"
_VA_CODE = {"ucuz": "u", "makul": "m", "pahali": "p", "karisik": "k"}


def enabled(environ=None):
    """TEMEL_V2 bayragi: yalniz '1' acar."""
    return (environ if environ is not None else os.environ).get(ENV_FLAG, "").strip() == "1"


# ----------------------------------------------------------------------------- sayi bicimi (kanon §2.10)

def _num(x, nd=2):
    s = ("%." + str(nd) + "f") % abs(x)
    ip, _, fp = s.partition(".")
    ip = "{:,}".format(int(ip)).replace(",", ".")
    return ("−" if x < 0 and round(abs(x), nd) != 0 else "") + ip + ("," + fp if fp else "")


def _pc(x, signed=False, nd=1):
    """%14,8 · +%2,1 · −%21,7 (eksi U+2212)."""
    if x is None:
        return "—"
    body = "%" + _num(abs(x), nd)
    if round(x, nd) < 0:
        return "−" + body
    return ("+" + body) if signed and round(x, nd) > 0 else body


def _money(tl):
    """TL -> '57,0 Mrd ₺' / '912 Mn ₺' / '1,06 T ₺'."""
    a = abs(tl)
    if a >= 1e12:
        s = _num(a / 1e12, 2) + " T"
    elif a >= 1e9:
        s = _num(a / 1e9, 1 if a < 1e11 else 0) + " Mrd"
    else:
        s = _num(a / 1e6, 1 if a < 1e8 else 0) + " Mn"
    return s + " ₺"


# ----------------------------------------------------------------------------- puanlama yardimcilari

def percent_rank(value, pool):
    """Yuzdelik sira (percent rank) 0-100: pool sirketin kendi degeri dahil tum grup degerleri.
    Grubun en iyisi 100, en dusugu 0; esit degerler ortalama sirayi paylasir. Kendi degeri
    artarsa sira hic dusmez (monoton)."""
    if value is None or len(pool) < 2:
        return None
    less = sum(1 for x in pool if x < value)
    eq = sum(1 for x in pool if x == value) - 1
    return round((less + 0.5 * eq) / (len(pool) - 1) * 100.0, 1)


def valuation_points(q):
    """Oran (deger / sektor ortancasi) -> 0-100: 50 - 50 x log2(q), [0, 100] araliginda."""
    if q is None or q <= 0:
        return None
    return round(max(0.0, min(100.0, 50.0 - 50.0 * math.log2(q))), 1)


def valuation_verdict(ratios):
    """Kanon §5.6 (D-51 'va' ile ayni kural): oran <0,80 ucuz, >1,25 pahali, arasi makul;
    biri ucuz biri pahaliysa karisik. ratios: oran listesi (F/K, PD/DD)."""
    parts = [-1 if q < CHEAP_BELOW else (1 if q > EXPENSIVE_ABOVE else 0) for q in ratios if q is not None]
    if not parts:
        return None
    if -1 in parts and 1 in parts:
        return "karisik"
    s = sum(parts)
    return "ucuz" if s < 0 else ("pahali" if s > 0 else "makul")


def weighted_temel(axes):
    """Eksenlerin agirlikli ortalamasi (eksik eksenin agirligi kalanlara dagilir)."""
    avail = {k: v for k, v in axes.items() if v is not None}
    if len(avail) < MIN_AXES:
        return None
    w = sum(WEIGHTS[k] for k in avail)
    return round(sum(v * WEIGHTS[k] for k, v in avail.items()) / w)


def _mean(xs):
    xs = [x for x in xs if x is not None]
    return round(sum(xs) / len(xs), 1) if xs else None


# ----------------------------------------------------------------------------- sirket girdileri (tek kayit)

def _period_end(fy, period):
    m, d = {1: (3, 31), 2: (6, 30), 3: (9, 30), 4: (12, 31)}[period]
    return date(fy, m, d)


def _chg(rep, key, tpl, c="cur", p="prev"):
    return kf.pct_change(*kt._pair(rep, key, tpl, c, p)) if rep else None


def _interim_gaps(rec, n=5):
    """Son raporun donemine kadar beklenen son n ara donemden (Q4 yok; kap_financials ayni sayida
    ara donem ceker) kayitta olmayanlar."""
    reps = rec.get("reports") or []
    if not reps:
        return []
    have = {(r["fy"], r["period"]) for r in reps if r.get("period") in (1, 2, 3)}
    last = max(reps, key=lambda r: (r["fy"], r["period"]))
    fy, p = last["fy"], min(last["period"], 3)
    want = []
    while len(want) < n:
        want.append((fy, p))
        fy, p = (fy, p - 1) if p > 1 else (fy - 1, 3)
    return [w for w in want if w not in have]


def _consistent(rep, tpl):
    """Son yillik raporda muhasebe butunlugu (sutun/ayristirma hatasini yakalar): parca <= toplam."""
    if rep is None:
        return True
    v = lambda k: kt._v(rep, k)  # noqa: E731
    ta = v("total_assets")
    if ta is None or ta <= 0:
        return False
    parts = (("loans", "deposits", "equity_total") if tpl == "banka"
             else ("current_assets", "cash", "equity_total"))
    if any(v(k) is not None and v(k) > ta * 1.0001 for k in parts):
        return False
    ca, cash = v("current_assets"), v("cash")
    return not (tpl != "banka" and ca is not None and cash is not None and cash > ca * 1.0001)


def company_inputs(rec, price=None, today=None, yahoo_shares=None):
    """Tek sirketin gosterge degerleri (ham, puansiz) + veri kalitesi kontrolleri.
    KAP kaydi yoksa None, kayitta rapor yoksa {"rapor_yok": True} (ikisi de limited_data)."""
    if not rec:
        return None
    if not rec.get("reports"):
        return {"rapor_yok": True}
    today = today or date.today()
    tpl = kt.template_of(rec)
    d = rec.get("derived") or {}
    ann = kt._annual(rec)
    a = ann[-1] if ann else None
    last = kt._latest(rec)
    ttm = kt.ttm_net_income(rec)
    eq_last = kt._tl(last, kt._equity(last, tpl))
    out = {"sablon": tpl, "esas": d.get("basis"), "yil": a["fy"] if a else None,
           "son_rapor": last["donem"], "son12ay_kar": ttm["tutar"] if ttm else None,
           "yillik_kar": kt._v(a, "net_income_parent") if a else None}

    # Kalite
    out["roe"] = (kt._pct(ttm["tutar"], eq_last)
                  if ttm and ttm.get("tutar") is not None and eq_last and eq_last > 0 else None)
    if tpl in ("sanayi", "gyo"):
        out["net_marj"] = (kt.margins(a) or {}).get("net") if a else None
        pio = kt.piotroski(a) if a else None
        out["saglamlik_ham"] = ({"yontem": "piotroski", "puan": pio["puan"], "toplam": pio["toplam"]}
                                if pio else None)
    elif tpl == "banka":
        br = kt.bank_ratios(a) if a else {}
        out["gider_gelir"] = br.get("gider_gelir")
        out["kredi_mevduat"] = br.get("kredi_mevduat")
        # 5 maddenin 4'u tek rapordan; ozsermaye karliligi maddesi sektor ortancasiyla score_universe'te
        bc = kt.bank_checks(a) if a else None
        out["banka_maddeler"] = ([{"k": i["k"], "gecti": i["gecti"]} for i in bc["maddeler"]] if bc else None)

    # Degerleme (son kapanis; pay adedi Yahoo'yla ayrisirsa oran yok)
    now = kt.valuation_now(rec, tpl, price, yahoo_shares) if price else None
    out["fk"] = now.get("fk") if now else None
    out["pd_dd"] = now.get("pd_dd") if now else None
    sh = kt.shares_of(last)
    out["pay_uyumsuz"] = bool(yahoo_shares and sh and not (kt.SHARE_SANITY[0] < sh / yahoo_shares < kt.SHARE_SANITY[1]))
    priced = bool(price) and not out["pay_uyumsuz"] and bool(sh)
    # F/K zararda, PD/DD negatif ozkaynakta tanimsiz: veri eksigi sayilmaz
    out["fk_hesaplanir"] = priced and ttm is not None and ttm.get("tutar") is not None
    out["pd_dd_hesaplanir"] = priced and eq_last is not None

    # Buyume: sirketin ayni rapordaki karsilastirmasi (son yillik + son ara donem kumulatif)
    rev_key = "operating_income" if tpl == "banka" else "revenue"
    if tpl == "sigorta":
        out["kar_deg"] = _chg(a, "net_income_parent", tpl)
        out["ozkaynak_deg"] = _chg(a, "equity_parent", tpl)
    else:
        out["gelir_deg"] = _chg(a, rev_key, tpl)
        out["kar_deg"] = _chg(a, "net_income_parent", tpl)
    nxt = [r for r in kt._interim(rec) if a is None or r["fy"] > a["fy"]]
    i = nxt[-1] if nxt else None
    out["ara_etiket"] = kt.period_label(i["fy"], i["period"]) if i else None
    out["ara_kar_deg"] = _chg(i, "net_income_parent", tpl)
    if tpl != "sigorta":
        out["ara_gelir_deg"] = _chg(i, rev_key, tpl)

    # Bilanco sagligi (son yillik raporun cari sutunu; Temel sekmesindeki bilanco paneliyle ayni)
    bal = (kt.balance(rec, tpl) or {}).get("cur") or {}
    if tpl in ("sanayi", "gyo"):
        nd = bal.get("net_borc")
        out["net_borc"] = nd
        out["cari_oran"] = bal.get("cari_oran")
        if tpl == "sanayi":
            fv = bal.get("favok")
            if nd is None or fv is None:
                out["nb_favok"] = None
            elif fv > 0:
                out["nb_favok"] = round(nd / fv, 2)
            else:        # FAVOK sifir/negatif: net nakit ise 0, net borc varsa grubun en altinda
                out["nb_favok"] = 0.0 if nd <= 0 else float("inf")
            out["favok"] = fv
        else:
            eq_a = kt._tl(a, kt._equity(a, tpl)) if a else None
            if nd is None or eq_a is None:
                out["nb_ozkaynak"] = None
            elif eq_a > 0:
                out["nb_ozkaynak"] = round(nd / eq_a * 100.0, 2)
            else:
                out["nb_ozkaynak"] = float("inf") if nd > 0 else None
    elif tpl == "banka" and a is not None:
        out["ozkaynak_varlik"] = kt._pct(kt._equity(a, tpl), kt._v(a, "total_assets"))

    # Temettu: odenmis taksitler (brut TL/pay); son 12 ay ve onceki 12 ay
    pays = [p for p in (d.get("temettu_odemeleri") or []) if p.get("odeme")]
    t0, t1, t2 = today.isoformat(), (today - timedelta(days=365)).isoformat(), (today - timedelta(days=730)).isoformat()
    son12 = [p for p in pays if t1 < p["odeme"] <= t0]
    onceki12 = [p for p in pays if t2 < p["odeme"] <= t1]
    out["temettu_son12"] = bool(son12)
    out["temettu_onceki12"] = bool(onceki12)
    out["sureklilik"] = 50.0 * (bool(son12) + bool(onceki12))
    brut = sum(p.get("brut") or 0.0 for p in son12)
    out["verim"] = round(brut / price * 100.0, 2) if price and price > 0 else None   # D-40a0 dividend_yield ile ayni

    # Veri kalitesi (A/B/C): olculebilir kontroller
    problems = []
    if not d.get("basis"):
        problems.append("esas_belirsiz")
    # yillik rapor yasal sure (en gec Nisan sonu) dolmadan bir onceki yilinki beklenmez
    if a is None or a["fy"] < today.year - (1 if (today.month, today.day) >= (4, 30) else 2):
        problems.append("yillik_rapor_eski")
    if (today - _period_end(last["fy"], last["period"])).days > REPORT_LAG_DAYS:
        problems.append("son_rapor_gecikmis")
    if _interim_gaps(rec):
        problems.append("ceyrek_eksik")
    if a is None or any(kt._v(a, k) is None for k in CORE_ITEMS[tpl]):
        problems.append("kalem_eksik")
    if (out["pay_uyumsuz"] or not _consistent(a, tpl)
            or any("|" in (r.get("unit") or "") or not r.get("mult") for r in rec["reports"])):
        problems.append("tutarsizlik")
    if tpl == "sigorta":
        problems.append("sigorta_kalemleri_sinirli")
    out["veri_sorunlari"] = problems
    return out


# ----------------------------------------------------------------------------- sektor ortancalari (KAP)

def sector_medians(inputs, bucket_of):
    """D-23 kovasi basina KAP ortancalari: F/K ve PD/DD (yalniz pozitif), ozsermaye karliligi
    (son 12 ay). En az MIN_MEDIAN_N deger yoksa None (hukum yok). {kova: {metrik: {deger, n}}}."""
    vals = {}
    for tk, inp in inputs.items():
        if not inp:
            continue
        b = bucket_of.get(tk)
        if not b:
            continue
        for m, pos in (("fk", True), ("pd_dd", True), ("roe", False)):
            v = inp.get(m)
            if v is None or (pos and v <= 0):
                continue
            vals.setdefault(b, {}).setdefault(m, []).append(v)
    out = {}
    for b, byb in vals.items():
        out[b] = {}
        for m, key in (("fk", "fk"), ("pd_dd", "pd_dd"), ("roe", "ozsermaye_karliligi")):
            xs = byb.get(m) or []
            out[b][key] = ({"deger": round(statistics.median(xs), 2), "n": len(xs)}
                           if len(xs) >= MIN_MEDIAN_N else None)
    return out


def _bank_check(items, roe, med):
    """kap_temel_v2.bank_checks ile ayni 5 madde; ozsermaye karliligi maddesi sektor ortancasiyla."""
    if not items:
        return None
    its = [dict(i) for i in items]
    for i in its:
        if i["k"] == "ozsermaye_karliligi_ortanca_ustu":
            i["gecti"] = (roe > med) if roe is not None and med is not None else None
    scored = [i for i in its if i["gecti"] is not None]
    return {"yontem": "banka5", "puan": sum(1 for i in scored if i["gecti"]), "toplam": len(scored)}


# ----------------------------------------------------------------------------- cumleler (betim, yargi yok)

_BASIS_NOTE = {"tms29": "enflasyon düzeltmeli", "banka": "nominal TL", "sigorta": "nominal TL",
               "nominal": "nominal TL", "yabanci_para": "TL'ye çevrilmiş"}
_CEVAP_AD = {"kalite": "kalite", "buyume": "büyüme", "bilanco": "bilanço", "temettu": "temettü"}


def _cap(s):
    return s[:1].upper() + s[1:]


def answer(axes):
    """'Finansallari nasil?' betimleyici cevap (C-22 makrosuyla ayni kural: >=70 guclu, <50 zayif).
    Degerleme ekseni girmez: onu 'Fiyati makul mu?' sorusu cevaplar."""
    items = [(k, axes[k]) for k in AXES if k in _CEVAP_AD and axes.get(k) is not None]
    if not items:
        return None
    order = sorted(items, key=lambda kv: -kv[1])
    st = [k for k, v in order if v >= 70]
    wk = [k for k, v in order if v < 50]
    if st and wk:
        return "%s güçlü, %s zayıf" % (_cap(_CEVAP_AD[st[0]]), _CEVAP_AD[wk[-1]])
    if len(st) >= 2:
        return "%s ve %s güçlü" % (_cap(_CEVAP_AD[st[0]]), _CEVAP_AD[st[1]])
    if st:
        return "%s öne çıkıyor" % _cap(_CEVAP_AD[st[0]])
    if wk:
        return "%s zayıf, diğerleri dengeli" % _cap(_CEVAP_AD[wk[-1]])
    return "Dengeli; belirgin zayıf alan yok"


def rationale(categories):
    """financial_health_score.build_rationale v2 dali (gun sonu 'temel_analiz_aciklamasi')."""
    a = answer(categories or {})
    return (a + ".") if a else "Yeterli finansal veri bulunmadığı için temel analiz skoru hesaplanamadı."


def _sentences(inp, ax, med, check):
    tpl = inp["sablon"]
    yil = inp.get("yil")
    s = {}
    # Kalite
    parts = []
    if inp.get("roe") is not None:
        r = "Özsermaye kârlılığı son 12 ayda " + _pc(inp["roe"])
        if tpl == "banka" and (med or {}).get("ozsermaye_karliligi"):
            r += " · banka ortancası " + _pc(med["ozsermaye_karliligi"]["deger"])
        parts.append(r)
    elif inp.get("son12ay_kar") is not None:
        parts.append("Özkaynak negatif; özsermaye kârlılığı hesaplanmıyor")
    if tpl in ("sanayi", "gyo") and inp.get("net_marj") is not None:
        parts.append("%s net kâr marjı %s" % (yil, _pc(inp["net_marj"])))
    if tpl == "banka" and inp.get("gider_gelir") is not None:
        parts.append("%s gider / gelir %s" % (yil, _pc(inp["gider_gelir"])))
    if check:
        parts.append("sağlamlık kontrolü %s/%s" % (check["puan"], check["toplam"]))
    s["kalite"] = "; ".join(parts) + "." if parts else None
    if tpl == "sigorta":
        s["kalite"] = (s["kalite"] + " " if s["kalite"] else "") + "Prim ve hasar kalemleri okunmadığı için kalite yalnız bu göstergeyle ölçülüyor."
    # Degerleme
    vparts, why = [], None
    for m, lab in (("fk", "F/K"), ("pd_dd", "PD/DD")):
        if tpl == "gyo" and m == "fk":
            continue
        v, mm = inp.get(m), (med or {}).get(m)
        if v is not None and mm:
            vparts.append("%s %s · sektör ortancası %s" % (lab, _num(v), _num(mm["deger"])))
        elif v is not None:
            vparts.append("%s %s" % (lab, _num(v)))
    if inp.get("pay_uyumsuz"):
        why = "Pay adedi doğrulanamadığı için F/K ve PD/DD hesaplanmıyor."
    elif ax.get("degerleme") is None and vparts:
        why = "Sektörde karşılaştırılabilir en az 5 şirket olmadığı için değerleme puanı verilmiyor."
    elif ax.get("degerleme") is None:
        why = "Değerleme oranları hesaplanamadı."
    txt = "; ".join(vparts)
    if tpl != "gyo" and inp.get("fk") is None and inp.get("son12ay_kar") is not None and inp["son12ay_kar"] <= 0:
        txt = "Son 12 ayda zarar olduğu için F/K yok" + ("; " + txt if txt else "")
    if tpl == "gyo" and txt:
        txt += " (GYO'da F/K kullanılmıyor)"
    s["degerleme"] = ((txt + ". ") if txt else "") + (why or "")
    s["degerleme"] = s["degerleme"].strip() or None
    # Buyume
    lab_rev = "faaliyet gelirleri" if tpl == "banka" else "hasılat"
    g = []
    if tpl == "sigorta":
        a_ = [x for x in (("net kâr", inp.get("kar_deg")), ("özkaynak", inp.get("ozkaynak_deg"))) if x[1] is not None]
        b_ = [x for x in (("net kâr", inp.get("ara_kar_deg")),) if x[1] is not None]
    else:
        a_ = [x for x in ((lab_rev, inp.get("gelir_deg")), ("net kâr", inp.get("kar_deg"))) if x[1] is not None]
        b_ = [x for x in ((lab_rev, inp.get("ara_gelir_deg")), ("net kâr", inp.get("ara_kar_deg"))) if x[1] is not None]
    if a_ and yil:
        g.append("%s: %s" % (yil, ", ".join("%s %s" % (n, _pc(v, True)) for n, v in a_)))
    if b_ and inp.get("ara_etiket"):
        g.append("%s: %s" % (inp["ara_etiket"], ", ".join("%s %s" % (n, _pc(v, True)) for n, v in b_)))
    note = _BASIS_NOTE.get(inp.get("esas"))
    s["buyume"] = (" · ".join(g) + (" (%s)" % note if note else "") + ".") if g else None
    # Bilanco
    b = []
    nd = inp.get("net_borc")
    if tpl == "sanayi" and nd is not None:
        if nd <= 0:
            b.append("Net nakit " + _money(-nd))
        elif inp.get("nb_favok") not in (None, float("inf")):
            b.append("Net borç FAVÖK'ün %s katı" % _num(inp["nb_favok"]))
        else:
            b.append("Net borç %s, FAVÖK negatif" % _money(nd))
    if tpl == "gyo" and nd is not None:
        if nd <= 0:
            b.append("Net nakit " + _money(-nd))
        elif inp.get("nb_ozkaynak") not in (None, float("inf")):
            b.append("Net borç özkaynağın " + _pc(inp["nb_ozkaynak"]))
    if tpl == "banka" and inp.get("kredi_mevduat") is not None:
        b.append("Kredi / mevduat " + _pc(inp["kredi_mevduat"]))
    if tpl in ("banka", "sigorta") and inp.get("ozkaynak_varlik") is not None:
        b.append("özkaynak / varlık " + _pc(inp["ozkaynak_varlik"]))
    if inp.get("cari_oran") is not None:
        b.append("cari oran " + _num(inp["cari_oran"]))
    s["bilanco"] = (_cap(" · ".join(b)) + ".") if b else None
    if tpl == "sigorta":
        s["bilanco"] = "Teknik karşılık ve sermaye yeterliliği kalemleri okunmadığı için hesaplanmıyor."
    # Temettu
    if inp.get("temettu_son12"):
        t = ("Son 12 ay temettü verimi " + _pc(inp["verim"], nd=2)) if inp.get("verim") is not None else "Son 12 ayda ödeme var"
        t += " · önceki 12 ayda da ödeme var" if inp.get("temettu_onceki12") else " · önceki 12 ayda ödeme yok"
    elif inp.get("temettu_onceki12"):
        t = "Son 12 ayda ödeme yok · önceki 12 ayda ödeme var"
    else:
        t = "Son iki yılda nakit temettü ödemesi yok"
    s["temettu"] = t + "."
    return s


# ----------------------------------------------------------------------------- evren puanlamasi

def _keys(tk, inp, bucket_of, metric):
    """Gostergenin (birincil, yedek) grup anahtari: esasa duyarli gosterge -> (kova, esas sinifi),
    esas sinifi; digerleri -> kova, sablon."""
    b = bucket_of.get(tk)
    if metric in BASIS_SENSITIVE:
        cls = BASIS_CLASS.get(inp.get("esas"), "belirsiz")
        return ("kova-esas", b, cls, metric), ("esas", cls, metric)
    return ("kova", b, metric), ("sablon", inp["sablon"], metric)


def _pool(metric, tk, inputs, bucket_of, groups):
    """Karsilastirma grubu: birincil (sektor kovasi) >= 5 sirket -> yedek (esas sinifi / sablon)
    >= 5 -> yok (gosterge puanlanmaz)."""
    k1, k2 = _keys(tk, inputs[tk], bucket_of, metric)
    p1 = groups.get(k1) or []
    if k1[1] and len(p1) >= MIN_POOL:
        return p1, "sektor"
    p2 = groups.get(k2) or []
    if len(p2) >= MIN_POOL:
        return p2, ("esas" if metric in BASIS_SENSITIVE else "sablon")
    return None, None


def _groups(inputs, bucket_of):
    g = {}
    for tk, inp in inputs.items():
        if not inp or inp.get("rapor_yok"):
            continue
        ms = [m for ax in INPUTS[inp["sablon"]].values() for m in ax if m in HIGHER_BETTER]
        if inp.get("verim"):      # verim sirasi yalniz odeme yapanlar arasinda
            ms.append("verim")
        for m in ms:
            v = inp.get(m)
            if v is None:
                continue
            for k in _keys(tk, inp, bucket_of, m):
                g.setdefault(k, []).append(v)
    return g


def _limited(sebep, sektor=None):
    return {"saglik": {"temel_analiz_skoru": None, "data_completeness": 0.0, "categories_complete": False,
                       "categories": {}, "categories_na": []},
            "detay": {"surum": SURUM, "temel": None, "limited_data": True, "sebep": sebep, "sektor": sektor,
                      "veri_notu": None, "veri_notu_nedenleri": [], "veri_tamligi": 0.0,
                      "agirliklar": dict(WEIGHTS), "eksenler": {}, "listeler": []}}


def score_company(tk, inputs, bucket_of, medians, groups):
    inp = inputs.get(tk)
    b = bucket_of.get(tk)
    if not inp:
        return _limited("kap_kaydi_yok", b)
    if inp.get("rapor_yok"):
        return _limited("rapor_yok", b)
    tpl = inp["sablon"]
    med = medians.get(b) or {}
    pts, used = {}, {}

    def ranked(m):
        v = inp.get(m)
        if v is None:
            return None
        pool, kapsam = _pool(m, tk, inputs, bucket_of, groups)
        if pool is None:
            return None
        pr = percent_rank(v, pool)
        used[m] = kapsam
        return pr if HIGHER_BETTER[m] else round(100.0 - pr, 1)

    # saglamlik (Piotroski / banka 5 madde)
    check = None
    if tpl in ("sanayi", "gyo") and inp.get("saglamlik_ham"):
        check = inp["saglamlik_ham"]
        pts["saglamlik"] = (round(check["puan"] / check["toplam"] * 100.0, 1)
                            if check["toplam"] >= PIOTROSKI_MIN_ITEMS else None)
    elif tpl == "banka":
        roe_med = (med.get("ozsermaye_karliligi") or {}).get("deger")
        check = _bank_check(inp.get("banka_maddeler"), inp.get("roe"), roe_med)
        pts["saglamlik"] = (round(check["puan"] / check["toplam"] * 100.0, 1)
                            if check and check["toplam"] >= BANK_MIN_ITEMS else None)
    for m in ("roe", "net_marj", "gider_gelir", "gelir_deg", "kar_deg", "ara_gelir_deg", "ara_kar_deg",
              "ozkaynak_deg", "nb_favok", "nb_ozkaynak", "cari_oran", "kredi_mevduat", "ozkaynak_varlik"):
        if any(m in xs for xs in INPUTS[tpl].values()):
            pts[m] = ranked(m)
    # degerleme
    ratios = {}
    for m in INPUTS[tpl]["degerleme"]:
        v, mm = inp.get(m), med.get(m)
        if v is not None and v > 0 and mm:
            ratios[m] = round(v / mm["deger"], 2)
            pts[m] = valuation_points(v / mm["deger"])
        else:
            pts[m] = None
    # temettu: sureklilik her zaman bilinir; verim odeme yapanlar arasinda sira, odeme yoksa 0
    pts["sureklilik"] = inp.get("sureklilik")
    vr = inp.get("verim")
    if vr is None:
        pts["verim"] = None
    elif vr > 0:
        pool, kapsam = _pool("verim", tk, inputs, bucket_of, groups)
        pts["verim"] = percent_rank(vr, pool) if pool else None
        used["verim"] = kapsam
    else:
        pts["verim"] = 0.0

    axes = {ax: _mean([pts.get(m) for m in INPUTS[tpl][ax]]) for ax in AXES}

    # Veri tamligi: sablonun beklenen gostergelerinden hesaplanabilen ham degerler
    have = 0
    expected = [m for xs in INPUTS[tpl].values() for m in xs]
    for m in expected:
        if m == "saglamlik":
            have += 1 if (check and check["toplam"] >= (BANK_MIN_ITEMS if tpl == "banka" else PIOTROSKI_MIN_ITEMS)) else 0
        elif m == "fk":
            have += 1 if inp.get("fk_hesaplanir") else 0
        elif m == "pd_dd":
            have += 1 if inp.get("pd_dd_hesaplanir") else 0
        elif m == "sureklilik":
            have += 1
        else:
            have += 1 if inp.get(m) is not None else 0
    tamlik = round(have / len(expected), 2)

    temel = weighted_temel(axes)
    sebep = None
    if temel is None:
        sebep = "eksen_yetersiz"
    elif tamlik < MIN_COMPLETENESS:
        sebep, temel = "tamlik_dusuk", None
    limited = temel is None
    probs = inp.get("veri_sorunlari") or []
    grade = "A" if not probs else ("B" if len(probs) == 1 else "C")
    hukum = valuation_verdict(list(ratios.values()))
    sent = _sentences(inp, axes, med, check)
    detay = {
        "surum": SURUM, "sablon": tpl, "esas": inp.get("esas"), "sektor": b,
        "temel": temel, "limited_data": limited, "sebep": sebep,
        "veri_notu": grade, "veri_notu_nedenleri": probs, "veri_tamligi": tamlik,
        "agirliklar": dict(WEIGHTS),
        "eksenler": {ax: {"ad": AXIS_LABELS[ax], "puan": axes[ax], "cumle": sent.get(ax),
                          "girdiler": {m: {"deger": (check if m == "saglamlik" else _jsonable(inp.get(m))),
                                           "puan": pts.get(m), "grup": used.get(m)}
                                       for m in INPUTS[tpl][ax]}}
                     for ax in AXES},
        "degerleme": {"hukum": hukum, "fk": inp.get("fk"), "pd_dd": inp.get("pd_dd"), "oran": ratios},
        "ortanca": med,
        "saglamlik": check,
        "cevap": answer(axes),
        "sablon_notu": SIGORTA_NOTU if tpl == "sigorta" else None,
        "roe": inp.get("roe"),
        "listeler": [],
    }
    detay["listeler"] = list_membership(inp, detay, b)
    na = list(NA_AXES.get(tpl, ()))
    saglik = {"temel_analiz_skoru": temel, "data_completeness": tamlik,
              "categories_complete": (not limited) and all(axes[a] is not None for a in AXES),
              "categories": ({a: axes[a] for a in AXES if axes[a] is not None} if not limited else {}),
              "categories_na": na}
    return {"saglik": saglik, "detay": detay}


def _jsonable(v):
    return None if isinstance(v, float) and math.isinf(v) else v


def list_membership(inp, detay, bucket):
    """C-56 orta-uzun vade listeleri (kural tek yerde). Sinirli veri ya da tamlik <0,8 -> hicbiri."""
    if detay["limited_data"] or detay["veri_tamligi"] < LIST_COMPLETENESS:
        return []
    tpl, ax, hk = inp["sablon"], detay["eksenler"], detay["degerleme"]["hukum"]
    out = []
    if (tpl == "sanayi" and bucket != _HOLDING and (ax["kalite"]["puan"] or 0) >= 70
            and hk in ("ucuz", "makul")):
        out.append("kaliteli_makul")
    if inp.get("temettu_son12") and inp.get("temettu_onceki12"):
        out.append("istikrarli_temettu")
    if (tpl in ("sanayi", "gyo") and inp.get("net_borc") is not None and inp["net_borc"] < 0
            and (inp.get("gelir_deg") or 0) > 0 and (inp.get("yillik_kar") or 0) > 0):
        out.append("borcsuz_buyuyen")
    if hk == "ucuz" and len(detay["degerleme"]["oran"]) == len(INPUTS[tpl]["degerleme"]):
        out.append("sektorune_gore_ucuz")
    return out


def score_universe(inputs, bucket_of):
    """inputs: {T: company_inputs(...) ya da None}; bucket_of: {T: D-23 kovasi}.
    Donus: {T: {"saglik": compute_health_score bicimi (band haric), "detay": temel_v2 alani}}."""
    medians = sector_medians(inputs, bucket_of)
    groups = _groups(inputs, bucket_of)
    return {tk: score_company(tk, inputs, bucket_of, medians, groups) for tk in inputs}


# ----------------------------------------------------------------------------- web tarafi yardimcilari

def api_medians(detay):
    """/fundamentals 'sektor_ortanca' bicimi (kap_temel_v2.sector_medians ile ayni anahtarlar):
    v2 acikken gun sonu turunun KAP ortancalari; kapsam her zaman 'sektor'."""
    if not detay or not isinstance(detay.get("ortanca"), dict):
        return None
    o = detay["ortanca"]
    return {k: ({"deger": o[k]["deger"], "n": o[k]["n"], "kapsam": "sektor"} if o.get(k) else None)
            for k in ("fk", "pd_dd", "ozsermaye_karliligi")}


def tarama_view(detay):
    """/api/tarama satiri: v2 acikken degerleme bandi (va) ve F/K, PD/DD, ozsermaye karliligi
    ayni kaynaktan (KAP) -- tarama ile hisse sayfasi ayni hukmu verir."""
    if not detay or detay.get("sebep") in ("kap_kaydi_yok", "rapor_yok"):
        return None       # KAP kaydi yok: satir eskisi gibi (Yahoo oranlari)
    dg = detay.get("degerleme") or {}
    return {"va": _VA_CODE.get(dg.get("hukum")), "pe": dg.get("fk"), "pb": dg.get("pd_dd"), "roe": detay.get("roe")}
