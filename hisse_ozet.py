"""D-68 (SEO denetimi 15.10 #4, arka uc): hisse sayfasinin cevap-onde blogu icin kural tabanli baglam.

Hisse sayfasi (stock_page) bu modulun `build()` ciktisini `ozet` olarak sablona verir; sablon (C-80)
alanlari ham HTML'e yazar. Saf modul: ag yok, Flask yok, py3.9. AI metni YOK; her sayi sitenin zaten
kullandigi kaynaktan gelir:

- Sirket faaliyet ozeti: KAP "faaliyet konusu" (kap_sirket_bilgileri.json). Temizlik: literal "\\n"
  kalmaz, BUYUK HARF metin cumle duzenine iner (Turkce I/i). Metin yoksa bos (THYAO) -- uydurulmaz.
- Baslik olgulari ve "Fiyati makul mu?": /api/hisse/<T>/fundamentals ile AYNI zincirin ciktisi
  (`fund` = _fundamentals_temel_v2(_fundamentals_kap(...))). Bicim ve kural hisse.js `hxFillFund` /
  `tvValuation` ile birebir (esik 0,80 / 1,25; v2 hukmu varsa o; home_fields.valuation).
- Son rapor hasilat (banka: net faiz geliri) ve net kar: KAP kaydinin en son raporu, yuzde AYNI
  raporun karsilastirma sutunundan (kap_tablolar.degisim; isaret degisirse yuzde yok, olgu yazilir).
- Temettu: son 12 ayin gercek odemeleri (kap_financials.dividend_ttm), verim = brut toplam / kapanis.
- Trend: Guclu Trend / Trend Bozuldu / Yatay + durumun basladigi gun (ssr_signal.signal_date).
- Bildirimler: KAP akis deposundaki son 3 bildirim (once rutin olmayanlar), site ici baglanti; Haberler
  sekmesinin ham HTML'i icin ayni kuralla son 10 (`bildirim_listesi`; JS sekme acilinca tam listeyi cizer).
- Mini tablo: son 4 aciklanan ceyregin 3 aylik tutarlari (ara donem raporlarinin "3 Aylik"
  sutunlari; 4. ceyrek yillik rapordan turetilmez -- kanon §3), yuzde ayni raporun gecen yil
  ayni ceyregine gore.
- SSS: ilk soru H1 ile ayni ("{Ad} ({T}) hissesi nasil?"), cevabi 3-4 cumlelik tam paragraf (Ozan 15.10:
  paragraf H1 altinda gosterilmez); sonra ne is yapar, temettu, bilanco, F/K + bir trend sorusu (O8: "teknik
  gorunumu nasil?"). FAQPage JSON-LD de bu listeden.
- "{Ad} kisaca" karti (`kisaca`): Faaliyet, Son rapor (donem), Borc durumu (D-69: net borc/FAVOK son yillik +
  cari oran son bilanco; bankada kredi/mevduat), Degerleme, Sektordeki yeri (D-69: fund["sektor_sira"],
  CPO-1826 F/K + ozsermaye karliligi sirasi), Temettu (son 12 ay), Trend satirlari; bos veri satiri
  yazilmaz, baslik olgulari tekrar edilmez.

Eksik veri -> alan None / bos liste; sablon gizler. Bir bolum hata verirse yalniz o bolum bos kalir.
"""
from __future__ import annotations

import logging
import re
from datetime import date, datetime

import home_fields
import kap_financials as kf
import kap_tablolar as kt
import kap_temel_v2 as kv

log = logging.getLogger(__name__)

AY = ("Ocak", "Şubat", "Mart", "Nisan", "Mayıs", "Haziran", "Temmuz", "Ağustos", "Eylül",
      "Ekim", "Kasım", "Aralık")
AY_KISA = ("Oca", "Şub", "Mar", "Nis", "May", "Haz", "Tem", "Ağu", "Eyl", "Eki", "Kas", "Ara")
NB = " "          # sayi ile olcek/simge ayni satirda kalir
EKSI = "−"        # kanon §2.10: eksi isareti U+2212
DURUM = {"AL": "Güçlü Trend", "SAT": "Trend Bozuldu"}   # diger her durum Yatay (kanon §3)
TV_CUT, TV_EXP = home_fields.TV_CUT, home_fields.TV_EXP
HUKUM = {"ucuz": "Ucuz tarafta", "makul": "Makul", "pahali": "Pahalı tarafta", "karisik": "Karışık"}
_CEYREK_AY = {1: (1, 3), 2: (4, 6), 3: (7, 9)}
_DONEM_SONU = {1: (3, 31), 2: (6, 30), 3: (9, 30), 4: (12, 31)}
_SAYI_ADI = {1: "son çeyrekte", 2: "son iki çeyrekte", 3: "son üç çeyrekte", 4: "son dört çeyrekte"}
_PARA_ADI = {"USD": "dolar", "EUR": "euro", "GBP": "sterlin"}


# ----------------------------------------------------------------------------- bicim (kanon §2.10)

def _num(v):
    return isinstance(v, (int, float)) and not isinstance(v, bool) and v == v and v not in (float("inf"), float("-inf"))


def sayi(x, nd=2):
    """tr-TR sayi: binlik '.', ondalik ','; eksi U+2212 (yuvarlaninca 0 olan eksi isaretsiz)."""
    s = ("{:,.%df}" % nd).format(abs(x)).replace(",", "_").replace(".", ",").replace("_", ".")
    return (EKSI if x < 0 and s.strip("0,.") else "") + s


def para(v, frac=None):
    """Tutar (TL): hisse.js `_tvMoney` ile ayni olcek ve hane -- '383 Mrd ₺', '1,02 T ₺', '45,3 Mrd ₺'.
    frac verilirse olcekli degerin hanesi sabit (Yahoo yedegi `_fmtMoneyObj`: 2)."""
    a = abs(v)
    if frac is None:
        frac = 2 if a >= 1e12 else (0 if a >= 1e11 else 1)
    for mn, u in ((1e12, "T"), (1e9, "Mrd"), (1e6, "Mn")):
        if a >= mn:
            return sayi(v / mn, frac) + NB + u + NB + "₺"
    return sayi(v, 2) + NB + "₺"


def yuzde(v, nd=1):
    """Seviye yuzdesi (bpPctLevel): '%11,0', eksi '−%3,5'."""
    r = round(v, nd)
    return (EKSI if r < 0 else "") + "%" + sayi(abs(r), nd)


def degisim_metni(p):
    """Degisim yuzdesi (kap_tablolar ile ayni): '+%43,4' / '−%24,6'; >=100'de tam sayi."""
    return kt._pct_text(p)


def tarih_metni(d):
    return "%d %s %d" % (d.day, AY[d.month - 1], d.year) if d else None


def _gun(s):
    """'14.10.2026' | '2026-10-14' | '2026-10-14T..' -> date (yoksa None)."""
    if not s:
        return None
    s = str(s).strip()
    for fmt, n in (("%d.%m.%Y", 10), ("%Y-%m-%d", 10)):
        try:
            return datetime.strptime(s[:n], fmt).date()
        except ValueError:
            continue
    return None


_BIRLER = {1: "bir", 2: "iki", 3: "üç", 4: "dört", 5: "beş", 6: "altı", 7: "yedi", 8: "sekiz", 9: "dokuz"}
_ONLAR = {1: "on", 2: "yirmi", 3: "otuz", 4: "kırk", 5: "elli", 6: "altmış", 7: "yetmiş", 8: "seksen",
          9: "doksan"}


def _yil_ek(yil, ayrilma=False):
    """Yilin okunusuna gore bulunma/ayrilma eki: 2026 -> 'da' / 'dan', 2025 -> 'te' / 'ten'."""
    y = int(yil)
    if y % 10:
        w = _BIRLER[y % 10]
    elif (y // 10) % 10:
        w = _ONLAR[(y // 10) % 10]
    else:
        w = "yüz" if (y // 100) % 10 else "bin"
    unlu = [c for c in w if c in "aeıioöuü"][-1]
    sert = w[-1] in "fstkçşhp"
    ek = ("t" if sert else "d") + ("a" if unlu in "aıou" else "e")
    return "'" + ek + ("n" if ayrilma else "")


def tarihten(d):
    """'28 Eylül 2026'dan' (ayrilma)."""
    return tarih_metni(d) + _yil_ek(d.year, True)


def tarihte(d):
    """'28 Eylül 2026'da' (bulunma)."""
    return tarih_metni(d) + _yil_ek(d.year)


def _tr_lower(s):
    return s.replace("I", "ı").replace("İ", "i").lower()


def _tr_upper1(s):
    if not s:
        return s
    c = s[0]
    c = {"i": "İ", "ı": "I"}.get(c, c.upper())
    return c + s[1:]


# ----------------------------------------------------------------------------- faaliyet konusu

_KISALTMA = (("a.ş.", "A.Ş."), ("t.a.ş.", "T.A.Ş."), ("t.c.", "T.C."), ("ltd.", "Ltd."), ("şti.", "Şti."),
             ("a.o.", "A.O."), ("kktc", "KKTC"), ("abd", "ABD"), ("ar-ge", "Ar-Ge"))


def faaliyet_temizle(s):
    """KAP faaliyet konusu -> okunur tek paragraf ya da None.
    Literal '\\n' / '\\\\n' ve satir sonlari bosluga; cok bosluk teke; %80'den fazlasi BUYUK HARF ise
    cumle duzenine (Turkce kucuk harf + cumle basi buyuk, bilinen kisaltmalar korunur)."""
    if not s or not isinstance(s, str):
        return None
    t = s.replace("\\\\n", " ").replace("\\n", " ").replace("\\r", " ")
    t = re.sub(r"\s+", " ", t.replace("\r", " ").replace("\n", " ")).strip()
    harf = [c for c in t if c.isalpha()]
    if harf and sum(1 for c in harf if c.isupper()) / len(harf) > 0.8:
        t = _tr_lower(t)
        kor = {}
        for i, (k, v) in enumerate(_KISALTMA):   # kisaltmanin noktasi cumle sonu sayilmasin
            ph = "\x00%d\x00" % i
            t, n = re.subn(r"(?<![\wçğıöşü])" + re.escape(k) + r"(?![\wçğıöşü])", ph, t)
            if n:
                kor[ph] = v
        t = re.sub(r"(^|[.!?…]\s+)(\w)", lambda m: m.group(1) + _tr_upper1(m.group(2)), t)
        for ph, v in kor.items():
            t = t.replace(ph, v)
    return t or None


# ----------------------------------------------------------------------------- olgular (hxFillFund ile ayni)

def _kap(fund):
    f = fund or {}
    return f.get("kap") if f.get("kap_durum") == "var" and isinstance(f.get("kap"), dict) else None


def olgular(fund, price):
    """Baslik olgulari (#hxFacts): {piyasa_degeri, ozsermaye_karliligi, marj, temettu} -> {metin, soluk}
    ya da None (sablon o kutuda JS'e birakir). marj sigortada gizli (None + `marj_gizli`)."""
    f = fund or {}
    if not f:
        return None
    k = _kap(f)
    now = (k or {}).get("degerleme_simdi") or None
    out = {"piyasa_degeri": None, "ozsermaye_karliligi": None, "marj": None, "marj_etiket": "Net kâr marjı",
           "marj_gizli": False, "temettu": None}
    if now and now.get("piyasa_degeri"):
        out["piyasa_degeri"] = {"metin": para(now["piyasa_degeri"]), "soluk": False}
    elif _num(((f.get("market_cap") or {}).get("value"))):
        mc = f["market_cap"]
        if (mc.get("currency") or "TRY") == "TRY":
            out["piyasa_degeri"] = {"metin": para(mc["value"], 2), "soluk": False}
    roe = now.get("ozsermaye_karliligi") if now else None
    if _num(roe):
        out["ozsermaye_karliligi"] = {"metin": yuzde(roe, 1), "soluk": False}
    elif _num(f.get("roe")):
        out["ozsermaye_karliligi"] = {"metin": yuzde(f["roe"], 1), "soluk": False}
    bank = bool(k and k.get("sablon") == "banka")
    out["marj_gizli"] = bool(k and k.get("sablon") == "sigorta")
    out["marj_etiket"] = "Gider / gelir" if bank else "Net kâr marjı"
    if k:
        yillar = k.get("yillar") or []
        yr = (k.get("oranlar") or {}).get(str(yillar[-1])) if yillar else None
        mv = (yr or {}).get("gider_gelir" if bank else "net")
    else:
        mv = f.get("profit_margin")
    if _num(mv) and not out["marj_gizli"]:
        out["marj"] = {"metin": yuzde(mv, 1), "soluk": False}
    t = (k or {}).get("temettu")
    if isinstance(t, dict):
        if t.get("odeme_var") and _num(price) and price > 0:
            out["temettu"] = {"metin": yuzde(t["brut_toplam"] / price * 100.0, 2), "soluk": False}
        elif not t.get("odeme_var"):
            out["temettu"] = {"metin": "Ödeme yok", "soluk": True}
    return out


# ----------------------------------------------------------------------------- Fiyati makul mu? (tvValuation)

def _med_metni(m, nd):
    return ("sektör " if m.get("kapsam") == "sektor" else "BIST ") + sayi(m["deger"], nd)


def degerleme(fund, entry, price):
    """Ozet Q2 (Fiyati makul mu?) -- hisse.js hxFillFund + tvValuation'in Python karsiligi.
    entry: _financial_health_cache[T]['data'] (temel_v2 hukmu ve kapsami icin)."""
    f = fund or {}
    if not f:
        return None
    k = _kap(f)
    now = (k or {}).get("degerleme_simdi") or None
    med = f.get("sektor_ortanca") or {}
    if now and not now.get("pay_uyumsuz"):
        pe, pb = now.get("fk"), now.get("pd_dd")
    else:
        pe, pb = (None, None) if k else (f.get("pe_ratio"), f.get("pb_ratio"))
    rows = []
    for lab, v, m, nd in (("F/K", pe, med.get("fk"), 1), ("PD/DD", pb, med.get("pd_dd"), 2)):
        m = m if isinstance(m, dict) and _num(m.get("deger")) else None
        ok = _num(v) and v > 0
        q = v / m["deger"] if ok and m and m["deger"] > 0 else None
        rows.append({"etiket": lab, "deger": v if ok else None, "nd": nd, "ortanca": m, "q": q,
                     "t": None if q is None else (-1 if q < TV_CUT else (1 if q > TV_EXP else 0))})
    v2 = (entry or {}).get("temel_v2") if isinstance((entry or {}).get("temel_v2"), dict) else None
    if v2 is not None:
        d = v2.get("degerleme") or {}
        hukum = d.get("hukum") if d.get("hukum") in HUKUM else None
        has_med, wide = bool(d.get("hukum")), d.get("kapsam") == "piyasa"
    else:
        hukum = home_fields.valuation(None, f)
        has_med, wide = bool(med.get("fk") or med.get("pd_dd")), False
    vis = [r for r in rows if r["deger"] is not None]
    kv_rows = [{"dt": r["etiket"], "dd": sayi(r["deger"], r["nd"]),
                "ortanca": _med_metni(r["ortanca"], r["nd"]) if r["ortanca"] else None} for r in vis]
    if not kv_rows:
        kv_rows = [{"dt": "F/K ve PD/DD", "dd": "hesaplanamıyor", "ortanca": None}]
    cevap = " · ".join("%s %s" % (r["etiket"], sayi(r["deger"], r["nd"])) for r in vis) if vis else "Veri yok"
    sinif = "hx-dot--na"
    if hukum:
        cevap = HUKUM[hukum]
        sinif = ("hx-dot--warn" if hukum in ("karisik", "pahali")
                 else ("hx-dot--val" if hukum == "ucuz" else "hx-dot--brand"))
    analist = None
    tgt, cnt = f.get("analyst_target"), f.get("analyst_count")
    if _num(tgt) and cnt and _num(price) and price > 0:
        up = (tgt / price - 1.0) * 100.0
        analist = {"hedef": sayi(tgt, 2) + NB + "₺", "fark": yuzde(abs(up), 1),
                   "yon": "üstünde" if up > 0 else ("altında" if up < 0 else "düzeyinde"), "sayi": int(cnt)}
    cur = f.get("financial_currency") or "TRY"
    notu = None
    if k and k.get("basis") == "yabanci_para":
        notu = "Şirket rakamlarını %s ile açıklıyor; burada TL'ye çevrilmiş hali var." % _PARA_ADI.get(cur, "döviz")
    elif vis and not has_med:
        notu = ("Sektörde karşılaştırma için yeterli şirket yok." if v2 is not None else
                "Sektörde karşılaştırma için yeterli şirket yok; bu yüzden ucuz ya da pahalı denmiyor.")
    elif wide:
        notu = "Sektörde yeterli şirket olmadığı için piyasa geneline göre."
    elif cur != "TRY" and not vis:
        notu = "Şirket finansallarını %s cinsinden raporluyor; F/K ve PD/DD bu yüzden hesaplanmıyor." % cur
    return {"satirlar": kv_rows, "cevap": cevap, "sinif": sinif, "hukum": hukum, "genis": wide,
            "fk": rows[0], "pd_dd": rows[1], "analist": analist, "not": notu,
            "zarar": bool(now and not now.get("pay_uyumsuz") and _num(now.get("son12ay_kar"))
                          and now["son12ay_kar"] <= 0),
            "pay_uyumsuz": bool(now and now.get("pay_uyumsuz"))}


# ----------------------------------------------------------------------------- son rapor

_RAPOR_KALEM = {"sanayi": (("revenue", "Hasılat"), ("net_income_parent", "Net kâr")),
                "gyo": (("revenue", "Hasılat"), ("net_income_parent", "Net kâr")),
                "banka": (("net_interest_income", "Net faiz geliri"), ("net_income_parent", "Net kâr")),
                "sigorta": (("net_income_parent", "Net kâr"),)}


def _net(rep, col):
    v = kf._v(rep, "net_income_parent", col)
    return kf._v(rep, "net_income_total", col) if v is None else v


def _kalem(rep, key, col_c="cur", col_p="prev"):
    if key == "net_income_parent":
        return _net(rep, col_c), _net(rep, col_p)
    return kf._v(rep, key, col_c), kf._v(rep, key, col_p)


def _ozkaynak(rep, tpl, col="cur"):
    e = kv._equity(rep, tpl, col)
    return e if e is not None else kf._v(rep, "equity_total", col)


def son_rapor(rec):
    """En son raporun hasilat (banka: net faiz geliri) ve net kari + AYNI raporun karsilastirma
    sutununa gore degisim. Zarar 'Net zarar' diye yazilir; isaret degistiyse yuzde yok, `don` olgusu var."""
    rep = kv._latest(rec or {})
    if not rep or not rep.get("mult"):
        return None
    tpl = kv.template_of(rec)
    m = rep["mult"]
    kalemler = []
    for key, etiket in _RAPOR_KALEM[tpl]:
        c, p = _kalem(rep, key)
        if c is None:
            continue
        tl = c * m
        kar = key == "net_income_parent"
        zarar = kar and tl < 0
        kalemler.append({"anahtar": key, "etiket": "Net zarar" if zarar else etiket, "tl": tl,
                         "metin": para(abs(tl) if zarar else tl), "degisim": kt.degisim(c, p),
                         "degisim_metin": degisim_metni(kt.degisim(c, p)),
                         "don": kf.sign_reversal(c, p) if kar else None})
    if not kalemler:
        return None
    ozk = None
    if tpl == "sigorta":
        e = _ozkaynak(rep, tpl)
        if e is not None:
            ozk = {"tl": e * m, "metin": para(e * m)}
    yillik = rep["period"] == 4
    return {"donem": rep["donem"], "etiket": kv.period_label(rep["fy"], rep["period"]), "yillik": yillik,
            "yayin": (rep.get("publish") or "")[:10] or None, "esas": rep.get("basis"), "sablon": tpl,
            "kalemler": kalemler, "ozkaynak": ozk}


# ----------------------------------------------------------------------------- mini tablo (4 ceyrek)

_MINI_SATIR = {"sanayi": (("revenue", "Hasılat"), ("net_income_parent", "Net kâr")),
               "gyo": (("revenue", "Hasılat"), ("net_income_parent", "Net kâr")),
               "banka": (("net_interest_income", "Net faiz geliri"), ("net_income_parent", "Net kâr")),
               "sigorta": (("net_income_parent", "Net kâr"), ("ozkaynak", "Özkaynaklar"))}


def mini_tablo(rec, n=4):
    """Son n aciklanan ceyregin 3 aylik tutarlari (yeniden eskiye). Q1'de kumulatif = ceyrek; Q2/Q3
    raporun '3 Aylik' sutunlari. Ozkaynak (sigorta) donem sonu tutari, yuzdesiz."""
    reps = [r for r in kv._interim(rec or {}) if r.get("mult")]
    if not reps:
        return None
    reps = list(reversed(reps[-n:]))   # yeniden eskiye: finansal tablo sayfalariyla ayni sira
    tpl = kv.template_of(rec)
    sutunlar, satirlar = [], []
    for rep in reps:
        a, b = _CEYREK_AY[rep["period"]]
        sutunlar.append({"ust": "%s–%s" % (AY_KISA[a - 1], AY_KISA[b - 1]), "alt": str(rep["fy"]),
                         "tam": "%s–%s %d" % (AY[a - 1], AY[b - 1], rep["fy"]), "donem": rep["donem"]})
    for key, etiket in _MINI_SATIR[tpl]:
        kar = key == "net_income_parent"
        ham = []
        for rep in reps:
            if key == "ozkaynak":
                c, p = _ozkaynak(rep, tpl), None
            else:
                cols = ("cur", "prev") if rep["period"] == 1 else ("q_cur", "q_prev")
                c, p = _kalem(rep, key, *cols)
            ham.append(None if c is None else (c * rep["mult"], kt.degisim(c, p) if p is not None else None,
                                               kf.sign_reversal(c, p) if kar else None))
        dolu = [h[0] for h in ham if h]
        if not dolu:
            continue
        # satir basina tek olcek (finansal tablo sayfalari gibi birim basliktadir): hucrede yalniz sayi
        mx = max(abs(v) for v in dolu)
        bolen, birim = ((1e12, "T ₺") if mx >= 1e12 else (1e9, "Mrd ₺") if mx >= 1e9 else (1e6, "Mn ₺") if mx >= 1e6
                        else (1.0, "₺"))
        hucre = []
        for h in ham:
            if not h:
                hucre.append(None)
                continue
            x = h[0] / bolen
            hucre.append({"sayi": sayi(x, 0 if abs(x) >= 100 else (1 if abs(x) >= 10 else 2)), "metin": para(h[0]),
                          "degisim": degisim_metni(h[1]) if h[1] is not None else None, "eksi": h[0] < 0,
                          "don": h[2]})
        satirlar.append({"anahtar": key, "etiket": etiket, "birim": birim, "hucreler": hucre})
    if not satirlar:
        return None
    esas = (reps[0].get("basis") or "")
    notlar = ["Yüzde: önceki yılın aynı çeyreğine göre."]
    if esas == "tms29":
        notlar.append("Enflasyon düzeltmeli; her sütun kendi rapor tarihinin parasıyla.")
    elif esas == "yabanci_para":
        notlar.append("TL'ye çevrilmiş tutarlar.")
    adlar = " ve ".join(_tr_lower(s["etiket"][:1]) + s["etiket"][1:] for s in satirlar
                        if s["anahtar"] != "ozkaynak") or "net kâr"
    return {"soru": "%s %s nasıl değişti?" % (_tr_upper1(_SAYI_ADI.get(len(reps), "son çeyreklerde")), adlar),
            "sutunlar": sutunlar, "satirlar": satirlar, "notlar": notlar, "sablon": tpl}


# ----------------------------------------------------------------------------- temettu

def temettu(rec, fund, today, price):
    """Son 12 ay odemeleri (dividend_ttm; /fundamentals'taki kap.temettu ile ayni fonksiyon)."""
    k = _kap(fund)
    t = (k or {}).get("temettu")
    if not isinstance(t, dict):
        d = (rec or {}).get("derived") or {}
        if not rec:
            return None
        t = kf.dividend_ttm(d.get("temettu_odemeleri") or [], today)
    out = dict(t)
    out["verim_metin"] = (yuzde(t["brut_toplam"] / price * 100.0, 2)
                          if t.get("odeme_var") and _num(price) and price > 0 else None)
    out["brut_metin"] = _hisse_basi(t.get("brut_toplam")) if t.get("odeme_var") else None
    return out


def _hisse_basi(v):
    if not _num(v):
        return None
    return sayi(v, 2 if abs(v) >= 0.1 else 4) + NB + "₺"


# ----------------------------------------------------------------------------- trend, bildirimler

def trend(signal):
    s = signal or {}
    if not s:
        return None
    kod = s.get("signal")
    bas = _gun(s.get("signal_date"))
    out = {"kod": kod if kod in DURUM else "BEKLE", "etiket": DURUM.get(kod, "Yatay"),
           "baslangic": bas.isoformat() if bas else None, "baslangic_metin": tarih_metni(bas) if bas else None}
    pr, sl = s.get("price"), s.get("sl_level")
    if _num(pr) and pr > 0 and _num(sl) and sl > 0:
        out["donus"] = {"metin": sayi(sl, 2) + NB + "₺", "fark": yuzde(abs(sl - pr) / pr * 100.0, 1),
                        "yon": "üstünde" if sl > pr else "altında"}
    return out


def bildirimler(items, n=3):
    """KAP akis kayitlari (yeniden eskiye) -> son n satir; once rutin olmayanlar, eksikse rutinle tamamlanir.
    Satir site ici bildirim sayfasina baglanir (dis baglanti yok, kanon §2.8)."""
    lst = [it for it in (items or []) if isinstance(it, dict) and it.get("id") and it.get("ts")]
    sec = [it for it in lst if not it.get("rutin")][:n]
    if len(sec) < n:
        ids = {it["id"] for it in sec}
        sec += [it for it in lst if it["id"] not in ids][: n - len(sec)]
    sec.sort(key=lambda it: (it["ts"], it["id"]), reverse=True)
    out = []
    for it in sec:
        d = _gun(it["ts"])
        out.append({"tarih": d.isoformat() if d else None, "tarih_metin": tarih_metni(d) if d else "",
                    "baslik": (it.get("title") or it.get("subject") or "").strip(),
                    "tur": it.get("class") or "", "href": "/hisse/%s/bildirim/%d" % (it["ticker"], int(it["id"]))})
    return [o for o in out if o["baslik"]]


# ----------------------------------------------------------------------------- cumleler

def _kapanis(signal):
    s = signal or {}
    d = _gun(s.get("bar_date"))
    pr = s.get("price")
    if not d or not _num(pr) or pr <= 0:
        return None
    return {"tarih": d.isoformat(), "metin": tarih_metni(d), "gun": d, "fiyat": pr, "fiyat_metin": sayi(pr, 2) + NB + "₺"}


def _ad_kod(ad, t):
    return "%s (%s)" % (ad, t) if ad and ad != t else t


def _rapor_cumlesi(r):
    if not r:
        return None
    karsi = "önceki yıla göre" if r["yillik"] else "önceki yılın aynı dönemine göre"
    once = "önceki yıl" if r["yillik"] else "önceki yılın aynı döneminde"
    parca = []
    for i, k in enumerate(r["kalemler"]):
        s = "%s %s" % (_tr_lower(k["etiket"][:1]) + k["etiket"][1:], k["metin"])
        if k.get("don") == "zarara_dondu":
            s += " (%s net kâr)" % once
        elif k.get("don") == "kara_gecti":
            s += " (%s net zarar)" % once
        elif k["degisim_metin"]:
            s += " (%s%s)" % ((karsi + " ") if i == 0 else "", k["degisim_metin"])
        parca.append(s)
    bas = ("%s yıllık raporunda" % r["etiket"]) if r["yillik"] else ("%s raporunda" % r["etiket"])
    if r["esas"] == "yabanci_para":
        bas += " (TL'ye çevrilmiş)"
    cumle = "%s %s oldu" % (_tr_upper1(bas), ", ".join(parca))
    if r.get("ozkaynak"):
        cumle += "; dönem sonu özkaynaklar %s" % r["ozkaynak"]["metin"]
    return cumle + "."


def _hukum_ifadesi(dg):
    if not dg or not dg.get("hukum"):
        return None
    ref = "piyasa geneline" if dg.get("genis") else "sektörüne"
    return {"ucuz": "fiyat %s göre ucuz tarafta" % ref, "makul": "fiyat %s göre makul düzeyde" % ref,
            "pahali": "fiyat %s göre pahalı tarafta" % ref,
            "karisik": "iki oran %s göre farklı yönleri gösteriyor" % ref}[dg["hukum"]]


def _oran_metni(r):
    s = "%s %s" % (r["etiket"], sayi(r["deger"], r["nd"]))
    if r["ortanca"]:
        s += " (%s ortancası %s)" % ("sektör" if r["ortanca"].get("kapsam") == "sektor" else "BIST",
                                     sayi(r["ortanca"]["deger"], r["nd"]))
    return s


def _degerleme_cumlesi(dg):
    if not dg or dg.get("pay_uyumsuz"):
        return None
    oranlar = [r for r in (dg["fk"], dg["pd_dd"]) if r["deger"] is not None]
    if not oranlar:
        return None
    if dg["fk"]["deger"] is None and dg.get("zarar"):
        s = "Son 12 ayda net zarar olduğu için F/K hesaplanmıyor; %s" % _oran_metni(dg["pd_dd"])
    else:
        s = " ve ".join(_oran_metni(r) for r in oranlar)
    h = _hukum_ifadesi(dg)
    return s + ("; " + h if h else "") + "."


def _durum_ifadesi(tr, kisa=False):
    """'28 Eylül 2026'dan beri Trend Bozuldu durumu sürüyor' (kisa: '... beri Trend Bozuldu')."""
    if not tr or not tr.get("baslangic"):
        return None
    d = _gun(tr["baslangic"])
    if kisa:
        return "%s beri %s" % (tarihten(d), tr["etiket"])
    ad = "Yatay durum" if tr["etiket"] == "Yatay" else "%s durumu" % tr["etiket"]
    return "%s beri %s sürüyor" % (tarihten(d), ad)


def paragraf(ad, t, sektor, kap, olg, rapor, dg, tm, tr):
    """Cevap-onde paragraf: 3-4 cumle. Sayilar bu baglamdaki alanlardan; eksik alanin cumlesi yazilmaz."""
    cumleler = []
    sk = (" %s sektöründe" % sektor) if sektor and sektor != "Diğer" else " Borsa İstanbul'da"
    s1 = "%s%s işlem görüyor" % (_ad_kod(ad, t), sk)
    if kap:
        s1 += "; %s kapanışında hisse fiyatı %s" % (kap["metin"], kap["fiyat_metin"])
        pd = (olg or {}).get("piyasa_degeri")
        if pd:
            s1 += ", piyasa değeri %s" % pd["metin"]
    cumleler.append(s1 + ".")
    for c in (_rapor_cumlesi(rapor), _degerleme_cumlesi(dg)):
        if c:
            cumleler.append(c)
    son = []
    if tm:
        if tm.get("odeme_var") and tm.get("brut_metin"):
            son.append("Son 12 ayda hisse başına brüt %s temettü ödedi" % tm["brut_metin"])
        else:
            son.append("Son 12 ayda temettü ödemedi")
    di = _durum_ifadesi(tr)
    if di:
        son.append(di if son else _tr_upper1(di))
    if son:
        cumleler.append("; ".join(son) + ".")
    return cumleler


def meta_aciklama(t, kap, dg, tm, tr):
    """<meta description>: temel olguyla baslar (C-79, her gun degismez: F/K vs sektor ortancasi,
    son 12 ay temettu, trend + tarih), gunluk kapanis+tarih en sonda. Kapanis yoksa None (sablon
    sabit yedek yazar)."""
    if not kap:
        return None
    parca = []
    if dg and not dg.get("pay_uyumsuz"):
        r = dg["fk"] if dg["fk"]["deger"] is not None else (dg["pd_dd"] if dg["pd_dd"]["deger"] is not None else None)
        if r:
            parca.append("%s %s" % (t, _oran_metni(r)))
    if tm:
        parca.append(("son 12 ay temettü verimi %s" % tm["verim_metin"]) if tm.get("verim_metin")
                     else "son 12 ayda temettü ödemesi yok")
    di = _durum_ifadesi(tr, kisa=True)
    if di:
        parca.append(di)
    if not parca:
        parca.append(t)
    parca.append("%s kapanışı %s" % (kap["metin"], kap["fiyat_metin"]))
    return ", ".join(parca) + "."


# ----------------------------------------------------------------------------- SSS

def _bilanco_cevabi(rec):
    """Son raporun bilanco tarihi itibariyla buyuklukler (tek rapor, ayni birim). Banka: kredi/mevduat;
    sanayi/GYO: net borc (kiralamalar dahil, kap_financials.net_debt) ve cari oran."""
    rep = kv._latest(rec or {})
    if not rep or not rep.get("mult"):
        return None
    tpl = kv.template_of(rec)
    m = rep["mult"]
    ay, gun = _DONEM_SONU[rep["period"]]

    def tl(key):
        v = kf._v(rep, key)
        return None if v is None else v * m

    parca, ek = [], []
    if tl("total_assets") is not None:
        parca.append("toplam varlıklar %s" % para(tl("total_assets")))
    if tpl == "banka":
        ln, dp, e = tl("loans"), tl("deposits"), kf._equity_parent(rep)
        parca += [("krediler %s" % para(ln)) if ln is not None else None,
                  ("mevduat %s" % para(dp)) if dp is not None else None,
                  ("özkaynaklar %s" % para(e * m)) if e is not None else None]
        if ln is not None and dp:
            ek.append("kredilerin mevduata oranı %s" % yuzde(ln / dp * 100.0, 1))
    else:
        ep = kf._v(rep, "equity_parent")
        e = _ozkaynak(rep, tpl)
        parca.append(("ana ortaklık özkaynağı %s" % para(ep * m)) if ep is not None else
                     (("özkaynaklar %s" % para(e * m)) if e is not None else None))
        if tpl in ("sanayi", "gyo"):
            nd = kf.net_debt(rep)
            if nd and nd.get("net_borc") is not None:
                v = nd["net_borc"] * m
                ek.append(("net borç %s (kiralamalar dahil)" % para(v)) if v >= 0 else ("net nakit %s" % para(-v)))
            ca, cl = kf._v(rep, "current_assets"), kf._v(rep, "current_liabilities")
            if _num(ca) and _num(cl) and cl > 0:
                ek.append("cari oran %s" % sayi(ca / cl, 2))
    parca = [x for x in parca if x]
    if not parca:
        return None
    out = "%d %s %d itibarıyla %s." % (gun, AY[ay - 1], rep["fy"], ", ".join(parca))
    if ek:
        out += " " + _tr_upper1("; ".join(ek)) + "."
    return out


def borc_durumu(rec):
    """D-69 (Ozan notu O30): "Borç durumu" satırı -- sanayi/GYO'da net borç/FAVÖK (son yıllık rapor,
    kiralamalar dahil; net nakitte "Net nakit X") + cari oran (son bilanço, dönem farketmez); bankada
    kredi/mevduat oranı (son bilanço). kf.net_debt/_latest ile AYNI kaynak (_bilanco_cevabi'nin SSS
    cevabıyla aynı mantık); değer yoksa yazılmaz, uydurulmaz."""
    if not rec:
        return None
    tpl = kv.template_of(rec)
    parca = []
    if tpl == "banka":
        rep = kv._latest(rec)
        if rep and rep.get("mult"):
            ln, dp = kf._v(rep, "loans"), kf._v(rep, "deposits")
            if ln is not None and dp:
                parca.append("Kredi/mevduat oranı %s" % yuzde(ln / dp * 100.0, 1))
    elif tpl in ("sanayi", "gyo"):
        yillik = [r for r in (rec.get("reports") or []) if r.get("period") == 4]
        if yillik:
            nd = kf.net_debt(max(yillik, key=lambda r: r["fy"]))
            if nd and nd.get("net_borc") is not None and nd["net_borc"] < 0:
                parca.append("Net nakit %s" % para(-nd["net_borc"] * nd["mult"]))
            elif nd and nd.get("net_borc_favok") is not None:
                parca.append("Net borç FAVÖK'ün %s katı" % sayi(nd["net_borc_favok"], 1))
        rep = kv._latest(rec)
        if rep and rep.get("mult"):
            ca, cl = kf._v(rep, "current_assets"), kf._v(rep, "current_liabilities")
            if _num(ca) and _num(cl) and cl > 0:
                parca.append("Cari oran %s" % sayi(ca / cl, 2))
    return " · ".join(parca) if parca else None


_SEKTOR_SIRA_METIN = {"fk": "F/K'de %d şirket arasında %d.",
                      "ozsermaye_karliligi": "Özsermaye kârlılığında %d şirket arasında %d."}


def sektor_sirasi(sira):
    """D-69 (Ozan notu O30): "Sektördeki yeri" satırı -- fund["sektor_sira"] (kap_temel_v2.sector_rank,
    CPO-1826) F/K ve özsermaye kârlılığında sektör içi sıra. <5 akran ya da hissenin kendi değeri yoksa
    sector_rank zaten None döner, o metrik atlanır; ikisi de yoksa satır yazılmaz."""
    if not sira:
        return None
    parca = [_SEKTOR_SIRA_METIN[k] % (sira[k]["toplam"], sira[k]["sira"])
             for k in ("fk", "ozsermaye_karliligi") if (sira.get(k) or {}).get("sira")]
    return " ".join(parca) if parca else None


def _temettu_cevabi(tm, kap):
    if not tm:
        return None
    if tm.get("odeme_var"):
        tarihler = [tarih_metni(_gun(o["odeme"])) for o in tm.get("odemeler") or [] if _gun(o.get("odeme"))]
        s = "Son 12 ayda hisse başına brüt %s temettü ödendi" % tm["brut_metin"]
        if tarihler:
            s += " (%s)" % (" ve ".join([", ".join(tarihler[:-1]), tarihler[-1]]) if len(tarihler) > 1 else tarihler[0])
        if tm.get("verim_metin") and kap:
            s += "; %s kapanışına göre verim %s" % (kap["metin"], tm["verim_metin"])
        s += "."
    else:
        s = "Son 12 ayda temettü ödemesi yok."
        so = tm.get("son_odeme")
        if so and _gun(so.get("odeme")):
            s += " Son ödeme %s, hisse başına brüt %s." % (tarihte(_gun(so["odeme"])), _hisse_basi(so.get("brut")))
    du = [o for o in tm.get("duyurulan") or [] if _gun(o.get("odeme"))]
    if du:
        o = du[0]
        s += " Açıklanan sonraki ödeme %s, hisse başına brüt %s." % (tarihte(_gun(o["odeme"])), _hisse_basi(o.get("brut")))
    return s


def _fk_cevabi(dg, kap):
    if not dg or dg.get("pay_uyumsuz"):
        return None
    fk, pb = dg["fk"], dg["pd_dd"]
    bas = ("%s kapanışına göre " % kap["metin"]) if kap else ""
    if fk["deger"] is not None:
        s = bas + "F/K %s" % sayi(fk["deger"], 1)
        if fk["ortanca"]:
            s += "; %s ortancası %s" % ("sektör" if fk["ortanca"].get("kapsam") == "sektor" else "BIST",
                                        sayi(fk["ortanca"]["deger"], 1))
        s = s[:1].upper() + s[1:] + "."
    elif dg.get("zarar"):
        s = "Son 12 ayda net zarar olduğu için F/K hesaplanmıyor."
    else:
        return None
    if pb["deger"] is not None:
        s += " PD/DD %s" % sayi(pb["deger"], 2)
        if pb["ortanca"]:
            s += ", %s ortancası %s" % ("sektör" if pb["ortanca"].get("kapsam") == "sektor" else "BIST",
                                        sayi(pb["ortanca"]["deger"], 2))
        s += "."
    return s


def _trend_cevabi(tr, kap):
    if not tr:
        return None
    s = ("%s kapanışında trend durumu %s" % (kap["metin"], tr["etiket"])) if kap else "Trend durumu %s" % tr["etiket"]
    if tr.get("baslangic"):
        s += "; bu durum %s başladı" % tarihte(_gun(tr["baslangic"]))
    s += "."
    dn = tr.get("donus")
    if dn:
        s += " Trend dönüş seviyesi (Supertrend) %s." % dn["metin"]
    return s


def sss(ad, t, sektor, faaliyet, tm, kap, rec, dg, tr, par=None):
    out = []
    if par and kap:
        # Ozan 15.10: kendi basina anlamli tam paragraf H1 altinda degil, H1 ile ayni ilk SSS sorusunun cevabi
        # (ham HTML'de SSS bolumunde ve FAQPage JSON-LD'de); sayfada gorunen ozet "kisaca" kartinda maddeler.
        out.append({"q": "%s hissesi nasıl?" % _ad_kod(ad, t), "a": " ".join(par), "tur": "ozet"})
    if faaliyet:
        sk = ("%s Borsa İstanbul'da %s sektöründe yer alıyor. " % (ad, sektor)) if sektor and sektor != "Diğer" else ""
        out.append({"q": "%s ne iş yapar?" % ad, "a": sk + "Faaliyet konusu: " + faaliyet, "tur": "faaliyet"})
    a = _temettu_cevabi(tm, kap)
    if a:
        out.append({"q": "%s temettü veriyor mu?" % t, "a": a, "tur": "temettu"})
    a = _bilanco_cevabi(rec)
    if a:
        out.append({"q": "%s bilançosu nasıl?" % t, "a": a, "tur": "bilanco"})
    a = _fk_cevabi(dg, kap)
    if a:
        out.append({"q": "%s F/K oranı kaç?" % t, "a": a, "tur": "fk"})
    a = _trend_cevabi(tr, kap)
    if a:
        out.append({"q": "%s hissesinin teknik görünümü nasıl?" % t, "a": a, "tur": "trend"})
    return out


# ----------------------------------------------------------------------------- "{Ad} kisaca" karti

_HUKUM_KISA = {"ucuz": "ucuz tarafta", "makul": "makul", "pahali": "pahalı tarafta", "karisik": "karışık"}
_FAALIYET_AZAMI = 110


_ON_EK = re.compile(r"^(?:Şirket(?:'in|in)?|Banka(?:'nın|nın)?|Holding(?:'in|in)?|Ortaklık(?:'ın|ın)?)\s*"
                    r"(?:(?:başlıca|esas|fiili)\s+)?(?:faaliyet konusu|amacı(?:\s+ve\s+(?:faaliyet\s+)?konusu)?|"
                    r"amaç ve konusu)?\s*[,;:]\s*")


def faaliyet_kisa(metin, azami=_FAALIYET_AZAMI):
    """Faaliyet konusunun tek satirlik kisa hali: kalip on ek ("Şirketin amacı,", "Şirket;") atilir, ilk cumle
    yeterince uzunsa o; uzunsa son kelime sinirinda '…' (metin uydurulmaz, yalniz kisaltilir)."""
    if not metin:
        return None
    t = _ON_EK.sub("", metin.strip())
    t = _tr_upper1(t) if t else t
    ilk = re.split(r"(?<=\.)\s", t, maxsplit=1)[0]
    if len(ilk) >= 25:
        t = ilk
    t = t.rstrip(" ;")
    if len(t) <= azami:
        return t.rstrip(".") if t.endswith(".") and not t.endswith("..") else t
    kes = t[:azami + 1]
    kes = kes[:kes.rfind(" ")] if " " in kes else kes[:azami]
    return kes.rstrip(" ,;:.-–") + "…"


def _oran_kisa(r, etiketli):
    s = "%s %s" % (r["etiket"], sayi(r["deger"], r["nd"]))
    m = r.get("ortanca")
    if m:
        ad = ("sektör ortancası " if m.get("kapsam") == "sektor" else "BIST ortancası ") if etiketli else ""
        s += " (%s%s)" % (ad, sayi(m["deger"], r["nd"]))
    return s


def kisaca(ad, t, sektor, faaliyet, kap, rapor, dg, tm, tr, borc=None, sira=None):
    """Ozet sekmesindeki "{Ad} kisaca" karti: kendi donemini tasiyan etiket/deger satirlari. Veri yoksa satir
    yazilmaz ("—" yok). Baslik olgulari (piyasa degeri, ozsermaye karliligi, marj) burada tekrar edilmez."""
    rows = []
    sk = sektor if sektor and sektor != "Diğer" else None
    fk = faaliyet_kisa(faaliyet)
    if fk and sk and len(fk) < 25 and _tr_lower(fk)[:5] == _tr_lower(sk)[:5]:
        fk = None   # "Bankacılık sektörü · Bankacılık" tekrari
    if sk or fk:
        rows.append({"anahtar": "faaliyet", "etiket": "Faaliyet",
                     "deger": " · ".join(x for x in (("%s sektörü" % sk) if sk else None, fk) if x)})
    if rapor and rapor.get("kalemler"):
        don = ("%s yıllık" % rapor["etiket"]) if rapor["yillik"] else rapor["etiket"]
        if rapor.get("esas") == "yabanci_para":
            don += ", TL'ye çevrilmiş"
        once = "önceki yıl" if rapor["yillik"] else "geçen yıl aynı dönem"
        parca = []
        for k in rapor["kalemler"]:
            s = "%s %s" % (k["etiket"], k["metin"])
            if k.get("don") == "zarara_dondu":
                s += " (%s kâr)" % once
            elif k.get("don") == "kara_gecti":
                s += " (%s zarar)" % once
            elif k.get("degisim_metin"):
                s += " (%s)" % k["degisim_metin"]
            parca.append(s)
        if rapor.get("ozkaynak"):
            parca.append("Dönem sonu özkaynaklar %s" % rapor["ozkaynak"]["metin"])
        rows.append({"anahtar": "son_rapor", "etiket": "Son rapor (%s)" % don, "deger": " · ".join(parca)})
    if borc:
        rows.append({"anahtar": "borc", "etiket": "Borç durumu", "deger": borc})
    if dg and not dg.get("pay_uyumsuz"):
        oran = [r for r in (dg["fk"], dg["pd_dd"]) if r["deger"] is not None]
        parca = []
        if dg["fk"]["deger"] is None and dg.get("zarar"):
            parca.append("F/K hesaplanmıyor (son 12 ayda net zarar)")
        for i, r in enumerate(oran):
            parca.append(_oran_kisa(r, i == 0))   # ilk oranin ortancasi adiyla, ikincisi yalniz sayi
        if oran:
            s = " · ".join(parca)
            if dg.get("hukum") in _HUKUM_KISA:
                s += " →" + NB + _HUKUM_KISA[dg["hukum"]]   # ok, hukumle ayni satirda kalir
            rows.append({"anahtar": "degerleme", "etiket": "Değerleme", "deger": s})
    if sira:
        rows.append({"anahtar": "sektor_sira", "etiket": "Sektördeki yeri", "deger": sira})
    if tm:
        if tm.get("odeme_var") and tm.get("brut_metin"):
            s = "Hisse başına brüt %s" % tm["brut_metin"]
            if tm.get("verim_metin"):
                s += " · verim %s" % tm["verim_metin"]
        else:
            s = "Ödeme yok"
        rows.append({"anahtar": "temettu", "etiket": "Temettü (son 12 ay)", "deger": s})
    di = _durum_ifadesi(tr, kisa=True)
    if di:
        rows.append({"anahtar": "trend", "etiket": "Trend", "deger": di})
    if not rows:
        return None
    return {"baslik": "%s kısaca" % (ad or t),
            "alt": ("%s kapanışı itibarıyla" % kap["metin"]) if kap else None,
            "satirlar": rows}


# ----------------------------------------------------------------------------- servis

def _guvenli(ad, fn, *a, **kw):
    try:
        return fn(*a, **kw)
    except Exception as e:  # bir bolum bozuksa digerleri yine cizilir
        log.warning("hisse_ozet.%s: %s", ad, e)
        return None


def build(ticker, name=None, sector=None, rec=None, fund=None, entry=None, signal=None, kap_info=None,
          items=None, today=None):
    """stock_page() baglami `ozet`.
    rec: kap_financials kaydi · fund: /fundamentals zinciri (bos olabilir) · entry: saglik kaydi (temel_v2)
    signal: _cache satiri (ssr_signal) · kap_info: KAP_INFO[T] · items: kap_feed.for_ticker ciktisi."""
    today = today or date.today()
    t = ticker
    ad = name or t
    price = (signal or {}).get("price")
    faaliyet = _guvenli("faaliyet", faaliyet_temizle, (kap_info or {}).get("faaliyet_konusu"))
    kap = _guvenli("kapanis", _kapanis, signal)
    olg = _guvenli("olgular", olgular, fund, price)
    dg = _guvenli("degerleme", degerleme, fund, entry, price)
    rapor = _guvenli("son_rapor", son_rapor, rec)
    tm = _guvenli("temettu", temettu, rec, fund, today, price)
    tr = _guvenli("trend", trend, signal)
    borc = _guvenli("borc_durumu", borc_durumu, rec)
    sira = _guvenli("sektor_sirasi", sektor_sirasi, (fund or {}).get("sektor_sira"))
    bl = _guvenli("bildirimler", bildirimler, items) or []
    bliste = _guvenli("bildirim_listesi", bildirimler, items, n=10) or []
    mt = _guvenli("mini_tablo", mini_tablo, rec)
    par = _guvenli("paragraf", paragraf, ad, t, sector, kap, olg, rapor, dg, tm, tr) or []
    return {
        "ticker": t, "ad": ad, "sektor": sector if sector and sector != "Diğer" else None,
        "faaliyet": faaliyet, "kapanis": ({k: v for k, v in kap.items() if k != "gun"} if kap else None),
        "olgular": olg, "degerleme": dg, "son_rapor": rapor, "temettu": tm, "trend": tr,
        "bildirimler": bl, "bildirim_listesi": bliste, "mini_tablo": mt, "paragraf": par,
        "meta": _guvenli("meta", meta_aciklama, t, kap, dg, tm, tr),
        "kisaca": _guvenli("kisaca", kisaca, ad, t, sector, faaliyet, kap, rapor, dg, tm, tr, borc, sira),
        "sss": _guvenli("sss", sss, ad, t, sector, faaliyet, tm, kap, rec, dg, tr, par) or [],
    }
