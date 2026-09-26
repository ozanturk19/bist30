"""D-40a2: Temel v2 veri uclari (C-22b'nin arka ucu) -- D-40a0 KAP kaydindan ek turetmeler.

Ilke (kanon docs/URUN-VE-TASARIM.md §3 "Veri tanimlari"):
- Her oran tek raporun icinden gelir (ayni sutun ya da ayni raporun cari/karsilastirma sutunu).
  Farkli raporlarin tutarlari tek seride birlestirilmez; kendi TUFE duzeltmemiz yok.
- Tek istisna O22=B "son 12 ay" kari: son yillik rapordaki kar + icinde bulunulan yilin son
  ara donem raporundaki (cari - gecen yilin ayni donemi) farki. Iki terim de kendi raporundan,
  TL'ye kendi birim basligiyla (1.000 TL / 1.000.000 TL) cevrilir. F/K ve ozsermaye
  karliligi bununla hesaplanir.
- Degisim grafigi yalniz ayni muhasebe esasindaki yillari tasir (TMS 29 sirketinde 2023+);
  marj ve ozsermaye karliligi gibi oranlar tum yillar icin verilir.
- Ceyreklik degisim ara donem raporunun "3 Aylik" sutunlarindan (Q1'de kumulatif = ceyrek);
  dorduncu ceyrek turetilmez.

kap_financials.py'nin cekme/liste/ayristirma koduna dokunmaz; yalniz kayit (rec) okur.
Saf fonksiyonlar (ag yok, Flask yok, py3.9 uyumlu). app.py ince baglanti: extend().
"""
from __future__ import annotations

import statistics
from datetime import date

import kap_financials as kf

GYO_SECTOR = "GAYRİMENKUL YATIRIM ORTAKLIKLARI"
MIN_PEERS_KAP = 5      # sektor ortancasi icin en az akran (CPO 25.09: az sirkette hukum yok)
SHARE_SANITY = (0.8, 1.25)   # Odenmis Sermaye (1 TL nominal pay) / Yahoo pay adedi

_PERIOD_WORD = {1: "ilk çeyrek", 2: "ilk yarı", 3: "ilk 9 ay"}
_PERIOD_SHORT = {1: "Ç1", 2: "İY", 3: "9A"}


# ----------------------------------------------------------------------------- yardimcilar

def _v(rep, key, col="cur"):
    it = ((rep or {}).get("items") or {}).get(key)
    return None if not it else it.get(col)


def _r(x, n=2):
    return None if x is None else round(x, n)


def _pct(num, den):
    if num is None or den is None or den == 0:
        return None
    return round(num / den * 100.0, 2)


def _tl(rep, v):
    """Raporun kendi birimiyle TL (1.000 TL -> x1000)."""
    m = (rep or {}).get("mult")
    return None if v is None or not m else v * m


def _annual(rec):
    return sorted([r for r in rec.get("reports") or [] if r.get("period") == 4], key=lambda r: r["fy"])


def _interim(rec):
    return sorted([r for r in rec.get("reports") or [] if r.get("period") in (1, 2, 3)],
                  key=lambda r: (r["fy"], r["period"]))


def _latest(rec):
    reps = rec.get("reports") or []
    return max(reps, key=lambda r: (r["fy"], r["period"])) if reps else None


def template_of(rec):
    """Sablon: banka | sigorta | gyo | sanayi (kart sablonu ve metrik secimi)."""
    flags = rec.get("flags") or {}
    d = rec.get("derived") or {}
    if flags.get("banka") or d.get("format") == "banka":
        return "banka"
    if flags.get("sigorta") or d.get("basis") == "sigorta":
        return "sigorta"
    if GYO_SECTOR in (rec.get("sector") or ""):
        return "gyo"
    return "sanayi"


def _equity(rep, template, col="cur"):
    """Ana ortaklik ozkaynagi; sigorta sayfasinda bu kalem eslenmedigi icin ayni raporun
    toplam ozkaynagi (sigorta sirketlerinde azinlik payi yok: donem kari = ana ortaklik payi)."""
    e = kf._equity_parent(rep, col)
    if e is None and template == "sigorta":
        e = _v(rep, "equity_total", col)
    return e


def _fcf(rep, col="cur"):
    cfo, capex = _v(rep, "cfo", col), _v(rep, "capex", col)
    return None if cfo is None or capex is None else cfo + capex


def period_label(fy, period):
    """(2026, 2) -> '2026 ilk yarı'; yillik -> '2025'."""
    return str(fy) if period == 4 else "%s %s" % (fy, _PERIOD_WORD.get(period, ""))


def quarter_label(fy, period):
    return "%s Ç%s" % (str(fy)[2:], period)


# ----------------------------------------------------------------------------- oranlar (tek rapor)

def margins(rep):
    """Sanayi/GYO: brut, esas faaliyet, FAVOK ve net (ana ortaklik) marji -- raporun cari sutunu."""
    rev = _v(rep, "revenue")
    if not rev or rev <= 0:
        return None
    return {"brut": _pct(_v(rep, "gross_profit"), rev),
            "esas": _pct(_v(rep, "operating_profit"), rev),
            "favok": _pct(kf._ebitda(rep), rev),
            "net": _pct(_v(rep, "net_income_parent"), rev)}


def roe_avg(rep, template):
    """Ozsermaye karliligi (yillik): ana ortaklik kari / ortalama ozkaynak (ayni raporun iki sutunu)."""
    ni = _v(rep, "net_income_parent")
    e1, e0 = _equity(rep, template, "cur"), _equity(rep, template, "prev")
    if ni is None or e1 is None or e0 is None or (e1 + e0) <= 0:
        return None
    return _pct(ni, (e1 + e0) / 2.0)


def bank_ratios(rep):
    """Banka sablonu (ayni rapor): ozsermaye karliligi, gider/gelir, kredi/mevduat, net faiz
    geliri / ortalama varlik, ucret-komisyon payi, beklenen zarar karsiligi / ortalama kredi."""
    oi = _v(rep, "operating_income")
    pe, oe = _v(rep, "personnel_expense"), _v(rep, "other_operating_expense")
    opex = None if pe is None or oe is None else -(pe + oe)
    ta1, ta0 = _v(rep, "total_assets"), _v(rep, "total_assets", "prev")
    l1, l0 = _v(rep, "loans"), _v(rep, "loans", "prev")
    ecl = _v(rep, "ecl_expense")
    return {
        "ozsermaye_karliligi": roe_avg(rep, "banka"),
        "gider_gelir": _pct(opex, oi),
        "kredi_mevduat": _pct(_v(rep, "loans"), _v(rep, "deposits")),
        "net_faiz_marji": (_pct(_v(rep, "net_interest_income"), (ta1 + ta0) / 2.0)
                           if ta1 is not None and ta0 is not None and ta1 + ta0 > 0 else None),
        "ucret_payi": _pct(_v(rep, "net_fees"), oi),
        "risk_maliyeti": (_pct(-ecl, (l1 + l0) / 2.0)
                          if ecl is not None and l1 is not None and l0 is not None and l1 + l0 > 0 else None),
        "ozkaynak_degisim": kf.pct_change(_equity(rep, "banka"), _equity(rep, "banka", "prev")),
        "varlik_degisim": kf.pct_change(ta1, ta0),
    }


def ratios_by_year(rec, template):
    """{yil: {...}} tum yillik raporlar (oranlar tek rapordan: esas farki etkilemez)."""
    out = {}
    for rep in _annual(rec):
        y = str(rep["fy"])
        if template == "banka":
            out[y] = bank_ratios(rep)
            continue
        row = {"ozsermaye_karliligi": roe_avg(rep, template)}
        if template in ("sanayi", "gyo"):
            row.update(margins(rep) or {"brut": None, "esas": None, "favok": None, "net": None})
        else:  # sigorta: hasilat sayfada eslenmedi
            row["ozkaynak_degisim"] = kf.pct_change(_equity(rep, template), _equity(rep, template, "prev"))
            row["varlik_degisim"] = kf.pct_change(_v(rep, "total_assets"), _v(rep, "total_assets", "prev"))
        out[y] = row
    return out


def interim_ratios(rec, template):
    """Son ara donem (son yillik raporun ertesi yili) kumulatif oranlari -- grafikte kesikli nokta."""
    ann = _annual(rec)
    last_fy = ann[-1]["fy"] if ann else None
    cand = [r for r in _interim(rec) if last_fy is None or r["fy"] > last_fy]
    if not cand:
        return None
    rep = cand[-1]
    out = {"donem": rep["donem"], "etiket": period_label(rep["fy"], rep["period"]),
           "kisa": "%s %s" % (str(rep["fy"])[2:], _PERIOD_SHORT.get(rep["period"], ""))}
    if template in ("sanayi", "gyo"):
        out.update(margins(rep) or {})
    return out


# ----------------------------------------------------------------------------- degisim serileri

_YEAR_KEYS = {
    "sanayi": ("revenue", "gross_profit", "operating_profit", "ebitda", "net_income_parent", "fcf", "equity_parent"),
    "gyo": ("revenue", "gross_profit", "operating_profit", "ebitda", "net_income_parent", "fcf", "equity_parent"),
    "banka": ("net_interest_income", "net_fees", "operating_income", "net_income_parent", "loans", "deposits",
              "total_assets", "equity_parent"),
    "sigorta": ("net_income_parent", "equity_parent", "total_assets", "cfo"),
}
_QUARTER_KEYS = {
    "sanayi": ("revenue", "operating_profit", "net_income_parent"),
    "gyo": ("revenue", "operating_profit", "net_income_parent"),
    "banka": ("net_interest_income", "net_fees", "net_income_parent"),
    "sigorta": ("net_income_parent",),
}


def _pair(rep, key, template, c="cur", p="prev"):
    if key == "fcf":
        return _fcf(rep, c), _fcf(rep, p)
    if key == "ebitda":
        return kf._ebitda(rep, c), kf._ebitda(rep, p)
    if key == "equity_parent":
        return _equity(rep, template, c), _equity(rep, template, p)
    return _v(rep, key, c), _v(rep, key, p)


def yearly_series(rec, template):
    """[{yil, degisim{kalem: %}}] -- her yil kendi raporunun karsilastirmasi. Yalniz son yillik
    raporla ayni muhasebe esasindaki yillar (TMS 29 sirketinde duzeltmesiz 2021-22 raporlari
    grafige girmez); disarida kalanlar 'dusen_yillar'."""
    ann = _annual(rec)
    if not ann:
        return {"seri": [], "dusen_yillar": []}
    basis = ann[-1].get("basis")
    seri, dusen = [], []
    for rep in ann:
        if rep.get("basis") != basis:
            dusen.append(rep["fy"])
            continue
        seri.append({"yil": rep["fy"],
                     "degisim": {k: kf.pct_change(*_pair(rep, k, template)) for k in _YEAR_KEYS[template]}})
    return {"seri": seri, "dusen_yillar": dusen}


def quarterly_series(rec, template):
    """[{donem, ceyrek, degisim{kalem: %}}] -- ara donem raporunun 3 aylik sutunlari (Q1: kumulatif)."""
    out = []
    for rep in _interim(rec):
        c, p = ("cur", "prev") if rep["period"] == 1 else ("q_cur", "q_prev")
        row = {k: kf.pct_change(*_pair(rep, k, template, c, p)) for k in _QUARTER_KEYS[template]}
        if all(v is None for v in row.values()):
            continue
        out.append({"donem": rep["donem"], "ceyrek": quarter_label(rep["fy"], rep["period"]), "degisim": row})
    return out


def latest_amounts(rec, template):
    """Tutar tablosu: son yillik raporun iki sutunu (ayni rapor, ayni birim), TL."""
    ann = _annual(rec)
    if not ann:
        return None
    rep = ann[-1]
    keys = {"sanayi": ("revenue", "net_income_parent", "fcf"), "gyo": ("revenue", "net_income_parent", "fcf"),
            "banka": ("net_interest_income", "net_fees", "net_income_parent"),
            "sigorta": ("net_income_parent", "equity_parent", "total_assets")}[template]
    rows = {}
    for k in keys:
        c, p = _pair(rep, k, template)
        rows[k] = {"cur": _tl(rep, c), "prev": _tl(rep, p)}
    return {"yil": rep["fy"], "onceki_yil": rep["fy"] - 1, "kalemler": rows}


# ----------------------------------------------------------------------------- son 12 ay (O22=B) ve degerleme

def ttm_net_income(rec):
    """O22=B: son yillik ana ortaklik kari + (son ara donem cari - gecen yilin ayni donemi).
    Ara donem raporu son yillik raporun ertesi yiline ait olmali; yoksa yalniz yillik kar."""
    ann = _annual(rec)
    if not ann:
        return None
    a = ann[-1]
    ni_a = _tl(a, _v(a, "net_income_parent"))
    if ni_a is None:
        return None
    nxt = [r for r in _interim(rec) if r["fy"] == a["fy"] + 1]
    if nxt:
        i = nxt[-1]
        c, p = _v(i, "net_income_parent"), _v(i, "net_income_parent", "prev")
        if c is not None and p is not None and i.get("mult"):
            return {"tutar": ni_a + (c - p) * i["mult"], "yontem": "son12ay",
                    "yillik": a["donem"], "ara": i["donem"], "etiket": period_label(i["fy"], i["period"]),
                    "fark": (c - p) * i["mult"]}
    return {"tutar": ni_a, "yontem": "yillik", "yillik": a["donem"], "ara": None, "etiket": str(a["fy"]), "fark": None}


def shares_of(rep):
    """1 TL nominal pay varsayimi: Odenmis Sermaye (TL) = pay adedi (kanon §3 degerleme bandi ile ayni)."""
    cap = _v(rep, "issued_capital")
    return _tl(rep, cap) if cap and cap > 0 else None


def valuation_now(rec, template, price, yahoo_shares=None):
    """Son kapanisla: piyasa degeri = fiyat x son raporun Odenmis Sermayesi; F/K = / son 12 ay kari;
    PD/DD = / son aciklanan (ara donem dahil) ana ortaklik ozkaynagi; ozsermaye karliligi (son 12 ay)
    = son 12 ay kari / ayni ozkaynak. Pay adedi Yahoo'yla %20'den fazla ayrisiyorsa oran verilmez."""
    last = _latest(rec)
    if not last or not price or price <= 0:
        return None
    sh = shares_of(last)
    ttm = ttm_net_income(rec)
    eq = _tl(last, _equity(last, template))
    out = {"pay_adedi": sh, "piyasa_degeri": None, "fk": None, "pd_dd": None, "ozsermaye_karliligi": None,
           "son12ay_kar": ttm["tutar"] if ttm else None, "son12ay_yontem": ttm["yontem"] if ttm else None,
           "son12ay_etiket": ttm["etiket"] if ttm else None, "ozkaynak": eq, "ozkaynak_donem": last["donem"],
           "pay_uyumsuz": False}
    if yahoo_shares and sh and not (SHARE_SANITY[0] < sh / yahoo_shares < SHARE_SANITY[1]):
        out["pay_uyumsuz"] = True
        sh = None
    if sh:
        mcap = price * sh
        out["piyasa_degeri"] = round(mcap)
        if ttm and ttm["tutar"] and ttm["tutar"] > 0:
            out["fk"] = round(mcap / ttm["tutar"], 2)
        if eq and eq > 0:
            out["pd_dd"] = round(mcap / eq, 2)
    if ttm and ttm["tutar"] is not None and eq and eq > 0:
        out["ozsermaye_karliligi"] = _pct(ttm["tutar"], eq)
    return out


def valuation_band(rec, template):
    """D-40a0 bandi; sigortada ozkaynak toplam ozkaynaktan (PD/DD bos kalmasin)."""
    band = list(((rec.get("derived") or {}).get("degerleme_bandi")) or [])
    if template != "sigorta":
        return [{k: b.get(k) for k in ("yil", "tarih", "kapanis", "fk", "pd_dd")} for b in band]
    by_fy = {r["fy"]: r for r in _annual(rec)}
    out = []
    for b in band:
        rep = by_fy.get(b.get("yil"))
        pd = b.get("pd_dd")
        if pd is None and rep is not None:
            eq = _tl(rep, _equity(rep, template))
            if eq and eq > 0 and b.get("piyasa_degeri"):
                pd = round(b["piyasa_degeri"] / eq, 2)
        out.append({"yil": b.get("yil"), "tarih": b.get("tarih"), "kapanis": b.get("kapanis"),
                    "fk": b.get("fk"), "pd_dd": pd})
    return out


# ----------------------------------------------------------------------------- bilanco ve saglamlik

def balance(rec, template):
    """Bilanco sagligi tablosu: son yillik raporun cari ve karsilastirma sutunu (TL)."""
    ann = _annual(rec)
    if not ann:
        return None
    rep = ann[-1]
    cols = {}
    for col in ("cur", "prev"):
        if template == "banka":
            row = {"krediler": _tl(rep, _v(rep, "loans", col)), "mevduat": _tl(rep, _v(rep, "deposits", col)),
                   "kredi_mevduat": _pct(_v(rep, "loans", col), _v(rep, "deposits", col)),
                   "ozkaynak": _tl(rep, _equity(rep, template, col))}
        elif template == "sigorta":
            row = {"ozkaynak": _tl(rep, _equity(rep, template, col)),
                   "toplam_varlik": _tl(rep, _v(rep, "total_assets", col)),
                   "nakit": _tl(rep, _v(rep, "cash", col)),
                   "cari_oran": _r(_ratio(_v(rep, "current_assets", col), _v(rep, "current_liabilities", col)))}
        else:
            b, cash = kf._borrowings(rep, col), _v(rep, "cash", col)
            fi = _v(rep, "current_financial_investments", col) or 0
            nd = None if b is None or cash is None else b - cash - fi
            eb = kf._ebitda(rep, col)
            row = {"net_borc": _tl(rep, nd), "favok": _tl(rep, eb),
                   "net_borc_favok": round(nd / eb, 2) if nd is not None and eb and eb > 0 else None,
                   "cari_oran": _r(_ratio(_v(rep, "current_assets", col), _v(rep, "current_liabilities", col))),
                   "nakit": _tl(rep, cash)}
        cols[col] = row
    return {"yil": rep["fy"], "onceki_yil": rep["fy"] - 1, "cur": cols["cur"], "prev": cols["prev"]}


def _ratio(a, b):
    return None if a is None or not b else a / b


def piotroski(rep):
    """Piotroski F-Skor 9 madde, tek yillik raporun iki sutunu (kanon §3). Klasik yontem donem
    basi varliklari kullanir; tek raporda iki sutun oldugu icin donem sonu varliklar kullanilir.
    Girdisi eksik madde puana girmez ('eksik')."""
    g = lambda k, c="cur": _v(rep, k, c)  # noqa: E731
    ni1, ni0 = g("net_income_total"), g("net_income_total", "prev")
    ta1, ta0 = g("total_assets"), g("total_assets", "prev")
    cfo = g("cfo")
    roa1, roa0 = _ratio(ni1, ta1), _ratio(ni0, ta0)
    ltd1 = _ratio(g("lt_borrowings") or 0, ta1) if ta1 else None
    ltd0 = _ratio(g("lt_borrowings", "prev") or 0, ta0) if ta0 else None
    cr1 = _ratio(g("current_assets"), g("current_liabilities"))
    cr0 = _ratio(g("current_assets", "prev"), g("current_liabilities", "prev"))
    sh1, sh0 = g("issued_capital"), g("issued_capital", "prev")
    gm1, gm0 = _ratio(g("gross_profit"), g("revenue")), _ratio(g("gross_profit", "prev"), g("revenue", "prev"))
    at1, at0 = _ratio(g("revenue"), ta1), _ratio(g("revenue", "prev"), ta0)

    def item(k, ok, cur, prev, scale=1.0, nd=2):
        if ok is None:
            return {"k": k, "gecti": None, "cur": None, "prev": None}
        return {"k": k, "gecti": bool(ok), "cur": _r(cur * scale if cur is not None else None, nd),
                "prev": _r(prev * scale if prev is not None else None, nd)}

    both = lambda a, b: a is not None and b is not None  # noqa: E731
    items = [
        item("aktif_karliligi_pozitif", (roa1 > 0) if roa1 is not None else None, roa1, None, 100),
        item("isletme_nakit_akisi_pozitif", (cfo > 0) if cfo is not None else None, _tl(rep, cfo), None, 1, 0),
        item("aktif_karliligi_artti", (roa1 > roa0) if both(roa1, roa0) else None, roa1, roa0, 100),
        item("nakit_akisi_kardan_buyuk", (cfo > ni1) if both(cfo, ni1) else None, _tl(rep, cfo), _tl(rep, ni1), 1, 0),
        item("uv_borc_orani_dustu", (ltd1 < ltd0) if both(ltd1, ltd0) else None, ltd1, ltd0, 100),
        item("cari_oran_artti", (cr1 > cr0) if both(cr1, cr0) else None, cr1, cr0),
        item("yeni_pay_yok", (sh1 <= sh0) if both(sh1, sh0) else None, _tl(rep, sh1), _tl(rep, sh0), 1, 0),
        item("brut_marj_artti", (gm1 > gm0) if both(gm1, gm0) else None, gm1, gm0, 100),
        item("aktif_devir_artti", (at1 > at0) if both(at1, at0) else None, at1, at0),
    ]
    scored = [i for i in items if i["gecti"] is not None]
    return {"yontem": "piotroski", "yil": rep["fy"], "puan": sum(1 for i in scored if i["gecti"]),
            "toplam": len(scored), "maddeler": items,
            "eksik": [i["k"] for i in items if i["gecti"] is None]}


def bank_checks(rep, roe=None, roe_median=None):
    """Banka 5 madde (kanon §3). Ozsermaye karliligi karsilastirmasi ayni kaynaktan: bankanin ve
    banka ortancasinin sitedeki (son 12 ay) degeri; ortanca yoksa madde puana girmez."""
    r = bank_ratios(rep)
    ni = _v(rep, "net_income_parent")
    eq_g, ta_g = r["ozkaynak_degisim"], r["varlik_degisim"]
    items = [
        {"k": "net_kar_pozitif", "gecti": (ni > 0) if ni is not None else None, "cur": _tl(rep, ni), "prev": None},
        {"k": "ozsermaye_karliligi_ortanca_ustu",
         "gecti": (roe > roe_median) if roe is not None and roe_median is not None else None,
         "cur": roe, "prev": roe_median},
        {"k": "kredi_mevduat_100_alti", "gecti": (r["kredi_mevduat"] <= 100) if r["kredi_mevduat"] is not None else None,
         "cur": r["kredi_mevduat"], "prev": None},
        {"k": "ozkaynak_varliktan_hizli", "gecti": (eq_g >= ta_g) if eq_g is not None and ta_g is not None else None,
         "cur": eq_g, "prev": ta_g},
        {"k": "gider_gelir_40_alti", "gecti": (r["gider_gelir"] <= 40) if r["gider_gelir"] is not None else None,
         "cur": r["gider_gelir"], "prev": None},
    ]
    scored = [i for i in items if i["gecti"] is not None]
    return {"yontem": "banka5", "yil": rep["fy"], "puan": sum(1 for i in scored if i["gecti"]),
            "toplam": len(scored), "maddeler": items, "eksik": [i["k"] for i in items if i["gecti"] is None]}


def checks(rec, template, roe=None, roe_median=None):
    ann = _annual(rec)
    if not ann:
        return None
    if template == "banka":
        return bank_checks(ann[-1], roe, roe_median)
    if template == "sigorta":
        return None      # sigorta sayfasinda hasilat/brut kar eslenmedi: 9 maddenin 4'u hesaplanamaz
    return piotroski(ann[-1])


# ----------------------------------------------------------------------------- temettu

def dividend_years(rec, today):
    """Odenmis taksitlerin yillara gore brut toplami (TL/pay, odendigi yilin parasiyla).
    Kapsam yalniz cekilen bildirimler kadar (10 yillik gecmis D-40b)."""
    by = {}
    for p in ((rec.get("derived") or {}).get("temettu_odemeleri")) or []:
        if p.get("odeme") and p["odeme"] <= today.isoformat():
            y = int(p["odeme"][:4])
            by[y] = round(by.get(y, 0.0) + (p.get("brut") or 0.0), 7)
    return [{"yil": y, "brut": by[y]} for y in sorted(by)]


# ----------------------------------------------------------------------------- sektor ortancasi

def _positive(v):
    return isinstance(v, (int, float)) and not isinstance(v, bool) and v == v and v > 0


def kap_metrics(rec, price, yahoo_shares=None):
    """Bir hissenin KAP'tan turetilen F/K, PD/DD ve ozsermaye karliligi (valuation_now ile ayni deger);
    sektor ortancasi sirketin kendi KAP degerleriyle ayni tutarli veriden kurulur (Yahoo karisimi yok)."""
    if not rec:
        return None
    now = valuation_now(rec, template_of(rec), price, yahoo_shares)
    if not now:
        return None
    return {k: now.get(k) for k in ("fk", "pd_dd", "ozsermaye_karliligi")}


def sector_medians(kap_by_ticker, sector_of, sector):
    """F/K, PD/DD (yalniz pozitif) ve ozsermaye karliligi ortancasi, ayni sektor grubundaki
    sirketlerin KAP degerlerinden (kap_metrics). Grupta gecerli akran < MIN_PEERS_KAP ya da sektor
    belirsizse (None / 'Diger') hukum yok: BIST geneli yedegi YOK (elma-armut kiyas). Donus metrik
    basina {deger, n, kapsam: 'sektor'} ya da None."""
    fields = (("fk", True), ("pd_dd", True), ("ozsermaye_karliligi", False))
    out = {k: None for k, _ in fields}
    if sector in (None, "", "Diğer"):
        return out
    for k, pos in fields:
        vals = []
        for tk, m in (kap_by_ticker or {}).items():
            v = (m or {}).get(k)
            ok = _positive(v) if pos else (isinstance(v, (int, float)) and not isinstance(v, bool) and v == v)
            if ok and sector_of(tk) == sector:
                vals.append(v)
        if len(vals) >= MIN_PEERS_KAP:
            out[k] = {"deger": round(statistics.median(vals), 2), "n": len(vals), "kapsam": "sektor"}
    return out


# ----------------------------------------------------------------------------- servis (app.py ince baglanti)

def build_v2(rec, price=None, today=None, yahoo_shares=None, roe=None, medians=None):
    """kap blogunun Temel v2 ekleri (kaynak izi yok)."""
    today = today or date.today()
    tpl = template_of(rec)
    ann = _annual(rec)
    last = _latest(rec)
    ys = yearly_series(rec, tpl)
    bank_med = ((medians or {}).get("ozsermaye_karliligi") or {})
    now = valuation_now(rec, tpl, price, yahoo_shares)
    # Pay adedi Yahoo'yla ayrisiyorsa (1 TL nominal varsayimi tutmuyor) bant da guvenilmez: gosterilmez.
    band = [] if (now and now.get("pay_uyumsuz")) else valuation_band(rec, tpl)
    return {
        "sablon": tpl,
        "son_rapor_etiket": period_label(last["fy"], last["period"]) if last else None,
        "yillar": [r["fy"] for r in ann],
        "oranlar": ratios_by_year(rec, tpl),
        "ara_donem": interim_ratios(rec, tpl),
        "yillik_seri": ys["seri"],
        "dusen_yillar": ys["dusen_yillar"],
        "ceyrek_seri": quarterly_series(rec, tpl),
        "tutarlar": latest_amounts(rec, tpl),
        "son12ay": ttm_net_income(rec),
        "degerleme_simdi": now,
        "degerleme_bandi_v2": band,
        "bilanco": balance(rec, tpl),
        "saglamlik": checks(rec, tpl, roe, bank_med.get("deger") if bank_med.get("kapsam") == "sektor" else None),
        "temettu_yillar": dividend_years(rec, today),
    }


def extend(data, rec, price=None, today=None, medians=None):
    """/api/hisse/<T>/fundamentals icin: kap_financials.apply_to_fundamentals ciktisina
    Temel v2 alanlari. Kayit yoksa kap_durum='hazirlaniyor' (arayuz eski alanlarla + sessiz not)."""
    if not data:
        return data
    out = dict(data)
    out["sektor_ortanca"] = medians
    if not rec or not out.get("kap"):
        out["kap_durum"] = "hazirlaniyor"
        return out
    out["kap_durum"] = "var"
    kap = dict(out["kap"])
    kap.update(kf._strip(build_v2(rec, price=price, today=today, yahoo_shares=data.get("shares"),
                                  roe=data.get("roe"), medians=medians)))
    out["kap"] = kap
    return out
