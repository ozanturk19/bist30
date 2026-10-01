"""D-56 (Haberler v2, O28=A): sekmeli Haberler sayfasinin arka uc mantigi.

Ne yapar (saf fonksiyonlar, app.py'ye bagimli degil, Python 3.9):
- Bildirim turu (8 tur, taslak `haberler-v2.html`): KAP konusu once, sonra baslik
  anahtar kelimeleri. Turkce kucuk harf (`_lower_tr`: I->ı, İ->i); `str.lower()`
  "İhale"yi "i̇hale" yapip kaciriyordu.
- BUYUK HARF basliklar cumle duzenine ("KREDİ DERECELENDİRME BİLDİRİMİ" ->
  "Kredi derecelendirme bildirimi"); kisaltmalar (SPK, KAP, A.Ş., hisse kodu) korunur.
- `/haberler/bildirimler` sorgusu: rutin elenir, `?tur=` turu, 30'luk sayfa, tur
  sayaclari, gun basliklari; ayni gun ayni sirket ayni tur tek satirda.
- Onem orani gorunumu (yapilandirilmis): yuzde, cubuk genisligi, dayanak, hesap satiri.
- Gundem v2 "gunun hikayesi" karti: donmus isi haritasi goruntusunden (BIST100; Bulten
  ile ayni hisse kumesi ve ayni sektor ortalamasi), 30 gunluk endeks cizgisi.
- Gundem sirket kartlari: gunun rutin-disi bildirimlerinden kural tabanli secim (AI yok;
  sirket olgusu bildirimin kendi rakamlarindan, kanon §3).
- Mini cizgi (sparkline) noktalari: 100x100 kutuda normalize (SVG preserveAspectRatio=none).
- D-57 sozlesmesi (`gundem_haber`) dogrulama: bozuk madde atilir, kaynak baglantisi yalniz http(s).

Dis baglanti yalniz D-57 basin derlemesinin "Kaynaklar" satirinda (O27k=A); kendi verimiz ve
KAP bildirimleri kaynak etiketi tasimaz.
"""
from __future__ import annotations

import json
import os
import re
from datetime import datetime

_TR_MONTHS = ("Ocak", "Şubat", "Mart", "Nisan", "Mayıs", "Haziran", "Temmuz", "Ağustos",
              "Eylül", "Ekim", "Kasım", "Aralık")
_TR_MONTHS_SHORT = ("Oca", "Şub", "Mar", "Nis", "May", "Haz", "Tem", "Ağu", "Eyl", "Eki", "Kas", "Ara")
_TR_DAYS = ("Pazartesi", "Salı", "Çarşamba", "Perşembe", "Cuma", "Cumartesi", "Pazar")

PER_PAGE = 30
WINDOW_DAYS = 30
TICKER_RE = re.compile(r"^[A-Z0-9]{3,6}$")


def _lower_tr(s):
    return (s or "").replace("I", "ı").replace("İ", "i").lower()


def _upper_first_tr(s):
    if not s:
        return s
    c = s[0]
    c = "İ" if c == "i" else ("I" if c == "ı" else c.upper())
    return c + s[1:]


# ----------------------------------------------------------------------------- bildirim turu

# (anahtar, etiket, adres parcasi) — sira filtre cubugu sirasi (taslak ORDER)
TYPES = (
    ("finansal", "Finansal rapor", "finansal-rapor"),
    ("temettu", "Temettü", "temettu"),
    ("sermaye", "Sermaye ve pay", "sermaye"),
    ("yonetim", "Yönetim ve genel kurul", "genel-kurul"),
    ("is", "Sözleşme ve ihale", "ihale"),
    ("kredi", "Kredi notu", "kredi-notu"),
    ("dava", "Dava", "dava"),
    ("ozel", "Özel durum", "ozel-durum"),
)
TYPE_LABEL = {k: l for k, l, _ in TYPES}
TYPE_SLUG = {k: s for k, _, s in TYPES}
SLUG_TYPE = {s: k for k, _, s in TYPES}
# v1 adresleri (?tur=bilanco|temettu|ozel) yeni tur adresine
LEGACY_SLUG = {"bilanco": "finansal-rapor", "temettu": "temettu", "ozel": "ozel-durum"}

_SUBJ_TYPE = {
    "Finansal Rapor": "finansal",
    "Kar Payı Dağıtım İşlemlerine İlişkin Bildirim": "temettu",
    "Kredi Derecelendirmesi": "kredi",
    "Ortaklık Aleyhine Dava Açılması veya Davaya İlişkin Gelişmeler": "dava",
    "Kurumsal Yönetim İlkelerine Uyum Derecelendirmesi": "yonetim",
    "Kurumsal Yönetim Uyum Derecelendirmesi": "yonetim",
    "Genel Kurul İşlemlerine İlişkin Bildirim": "yonetim",
    "Yönetim Kurulu Komiteleri": "yonetim",
    "Esas Sözleşme Tadili": "yonetim",
    "Sermaye Artırımı - Azaltımı İşlemlerine İlişkin Bildirim": "sermaye",
    "Payların Geri Alınmasına İlişkin Bildirim": "sermaye",
    "Pay Alım Teklifi Yoluyla Pay Toplanmasına İlişkin Bildirim": "sermaye",
    "Pay Alım Satım Bildirimi": "sermaye",
    "Birleşme İşlemlerine İlişkin Bildirim": "sermaye",
    "Bölünme İşlemlerine İlişkin Bildirim": "sermaye",
    "Kayıtlı Sermaye Tavanı İşlemlerine İlişkin Bildirim": "sermaye",
    "Finansal Duran Varlık Edinimi": "sermaye",
    "Finansal Duran Varlık Satışı": "sermaye",
    "Ayrılma Hakkı Kullanımına İlişkin Bildirim": "sermaye",
    "Yeni İş İlişkisi": "is",
    "İhale Süreci / Sonucu": "is",
    "Sözleşme Feshi": "is",
}
_KW = (
    ("temettu", re.compile(r"kâr payı|kar payı|temettü")),
    ("kredi", re.compile(r"kredi derecelendirme|kredi not")),
    ("dava", re.compile(r"\bdava|mahkeme|hukuki süreç|tahkim|icra takib")),
    ("yonetim", re.compile(r"kurumsal yönetim|esas sözleşme")),
    ("sermaye", re.compile(r"pay alım|pay satın alım|pay satış|sermaye art|sermaye azalt|bedelsiz|bedelli|"
                           r"geri alım|birleşme|bölünme|ortaklık yapısı|iştirak")),
    ("is", re.compile(r"ihale|sözleşme|sipariş|anlaşma|iş ilişkisi|protokol")),
    ("yonetim", re.compile(r"yönetim kurulu|genel kurul|yatırımcı ilişkileri|görev dağılımı|genel müdür|"
                           r"atama|istifa|denetim komitesi")),
)


def filing_type(item):
    """Bildirim -> tur anahtari (TYPES). Once KAP konusu, sonra baslik (Turkce kucuk harf)."""
    subject = item.get("subject") or ""
    if subject == "Finansal Rapor" or item.get("kap_class") == "FR":
        return "finansal"
    k = _SUBJ_TYPE.get(subject)
    if k:
        return k
    t = _lower_tr(item.get("title"))
    for key, rx in _KW:
        if rx.search(t):
            return key
    return "ozel"


def bildirimler_url(tur_slug=None, hisse=None, page=None, tarih=None, rutin=False, base="/haberler/bildirimler"):
    """/haberler/bildirimler adresi (sabit parametre sirasi: hisse, tur, tarih, rutin, sayfa)."""
    q = []
    if hisse:
        q.append("hisse=" + hisse)
    if tur_slug:
        q.append("tur=" + tur_slug)
    if tarih:
        q.append("tarih=" + tarih)
        if rutin:
            q.append("rutin=1")
    if page and int(page) > 1:
        q.append("sayfa=%d" % int(page))
    return base + ("?" + "&".join(q) if q else "")


def legacy_haberler_redirect(args):
    """Eski /haberler bildirim adresleri (?tur=bilanco|temettu|ozel, ?hisse=T, ?sayfa=N; v1 60'lik
    sayfa) -> yeni /haberler/bildirimler adresi ya da None (yonlendirme yok). v1 sayfa N'nin ilk
    satiri v2'de (30'luk) 2N-1. sayfasinda."""
    tur, hisse, sayfa = args.get("tur"), (args.get("hisse") or "").upper(), args.get("sayfa")
    if not (tur or hisse or sayfa):
        return None
    k, slug = tur_from_arg(tur)
    try:
        p = int(sayfa) if sayfa else 1
    except (TypeError, ValueError):
        p = 1
    return bildirimler_url(tur_slug=(slug or TYPE_SLUG[k]) if k else None,
                           hisse=hisse if TICKER_RE.match(hisse) else None,
                           page=2 * p - 1 if p > 1 else None)


def tur_from_arg(arg):
    """?tur= degeri -> (tur anahtari | None, yonlendirilecek yeni adres parcasi | None)."""
    if not arg:
        return None, None
    if arg in SLUG_TYPE:
        return SLUG_TYPE[arg], None
    if arg in LEGACY_SLUG:
        return SLUG_TYPE[LEGACY_SLUG[arg]], LEGACY_SLUG[arg]
    return None, None


# ----------------------------------------------------------------------------- baslik

_KEEP_UPPER = {
    "KAP", "SPK", "BDDK", "EPDK", "TCMB", "BIST", "BİST", "ABD", "AB", "GYO", "MKK", "TL", "USD", "EUR",
    "ESG", "KVKK", "TÜBİTAK", "SGK", "JCR", "YK", "AŞ", "A.Ş.", "T.A.Ş.", "A.Ş", "OYAK", "TOKİ", "KDV",
    "IPO", "ICR", "SPK'NIN", "KAP'TA", "BAE", "NATO", "AR-GE", "TSE", "TMSF", "AA", "AA+", "AAA", "BBB",
}
_NICE = {"FITCH": "Fitch", "MOODY'S": "Moody's", "S&P": "S&P", "SPK'NIN": "SPK'nın", "KAP'TA": "KAP'ta"}
_TOKEN_RE = re.compile(r"\S+")


def _is_caps(s):
    letters = [ch for ch in s if ch.isalpha()]
    return bool(letters) and sum(1 for ch in letters if ch.isupper()) / float(len(letters)) > 0.8


def sentence_case(title, keep=()):
    """BUYUK HARF baslik -> cumle duzeni (Turkce). Buyuk harf degilse aynen doner.
    keep: korunacak ek kodlar (bildirimin hisse kodlari)."""
    t = (title or "").strip()
    if not t or not _is_caps(t):
        return t
    keep = set(k.upper() for k in keep or ())
    out = []
    for i, m in enumerate(_TOKEN_RE.finditer(t)):
        w = m.group(0)
        core = w.strip("()[],.;:\"'“”")
        if core in _NICE:
            out.append(w.replace(core, _NICE[core]))
        elif core in _KEEP_UPPER or core in keep or (re.fullmatch(r"[A-ZÇĞİÖŞÜ]{1,4}\d*", core or "") and
                                                     core in keep):
            out.append(w)
        elif re.fullmatch(r"[IVX]+", core or "") and len(core) <= 4 and i > 0:
            out.append(w)   # roma rakami (II. Tertip)
        else:
            out.append(_lower_tr(w))
    s = " ".join(out)
    return _upper_first_tr(s)


def display_title(item):
    return sentence_case(item.get("title") or "", keep=item.get("tickers") or [item.get("ticker")])


# ----------------------------------------------------------------------------- bicim

def tr_num(v, dec=2):
    s = "{:,.{d}f}".format(abs(v), d=dec).replace(",", "X").replace(".", ",").replace("X", ".")
    return ("−" if v < 0 else "") + s


def tr_pct(v, dec=2, signed=True):
    """2.13 -> '+%2,13' ; -0.88 -> '−%0,88' (U+2212)."""
    txt = ("%." + str(dec) + "f") % abs(v)
    txt = txt.replace(".", ",")
    if not signed or v == 0:
        return "%" + txt
    return ("+%" if v > 0 else "−%") + txt


def big_try(v):
    """-> '137,7 Mn ₺' / '1,2 Mrd ₺' (kanon §2.10 birimleri)."""
    a = abs(v)
    if a >= 1e9:
        return tr_num(v / 1e9, 1) + " Mrd ₺"
    if a >= 1e6:
        return tr_num(v / 1e6, 1) + " Mn ₺"
    return tr_num(v, 0) + " ₺"


def day_label(day_iso):
    d = datetime.strptime(day_iso[:10], "%Y-%m-%d").date()
    return "%d %s" % (d.day, _TR_MONTHS[d.month - 1])


def day_parts(day_iso):
    d = datetime.strptime(day_iso[:10], "%Y-%m-%d").date()
    return {"d": d.day, "m": _TR_MONTHS[d.month - 1], "ms": _TR_MONTHS_SHORT[d.month - 1],
            "w": _TR_DAYS[d.weekday()], "iso": d.isoformat()}


def range_label(first_iso, last_iso):
    """('2026-09-25','2026-09-28') -> '25–28 Eylül' ; ay farkliysa '30 Eylül – 2 Ekim'."""
    a = datetime.strptime(first_iso[:10], "%Y-%m-%d").date()
    b = datetime.strptime(last_iso[:10], "%Y-%m-%d").date()
    if a > b:
        a, b = b, a
    if a == b:
        return "%d %s" % (a.day, _TR_MONTHS[a.month - 1])
    if a.month == b.month and a.year == b.year:
        return "%d–%d %s" % (a.day, b.day, _TR_MONTHS[b.month - 1])
    return "%d %s – %d %s" % (a.day, _TR_MONTHS[a.month - 1], b.day, _TR_MONTHS[b.month - 1])


# ----------------------------------------------------------------------------- onem orani

def onem_view(onem):
    """kap_feed.compute_onem ciktisi -> kart/satir gorunumu (yapilandirilmis) ya da None.
    {pct, big, w (cubuk %, olcek %0-%50), basis, year, lab, calc, amount}"""
    if not onem or not isinstance(onem.get("pct"), (int, float)):
        return None
    pct = float(onem["pct"])
    basis = (onem.get("basis") or "Tutar").split(" / ")[0]
    year = onem.get("rev_year")
    big = ("~" if onem.get("approx") else "") + tr_pct(pct, 1, signed=False)
    amount = onem.get("amount_txt") or ""
    calc = amount
    if onem.get("fx") and onem.get("amount_try"):
        calc += " ≈ " + big_try(onem["amount_try"])
    elif onem.get("amount_try"):
        calc = big_try(onem["amount_try"])
    if onem.get("rev"):
        calc += " ÷ %s (%s hasılatı)" % (big_try(onem["rev"]), year)
    # iki cubuklu karsilastirma (tutar ve dayanak): oran %0-%50 olcegini asinca (>= %50) oran cubugu
    # dolu kalir; o zaman iki tutar yan yana cizilir (taslak 'bars').
    bars = None
    a_try, rev = onem.get("amount_try"), onem.get("rev")
    if isinstance(a_try, (int, float)) and isinstance(rev, (int, float)) and a_try > 0 and rev > 0:
        mx = float(max(a_try, rev))
        bars = [{"l": basis, "t": big_try(a_try), "w": round(max(1.5, a_try / mx * 100.0), 1)},
                {"l": "%s hasılatı" % year if year else "Hasılat", "t": big_try(rev),
                 "w": round(max(1.5, rev / mx * 100.0), 1)}]
    return {
        "pct": round(pct, 2),
        "big": big,
        "w": round(max(2.0, min(100.0, pct / 50.0 * 100.0)), 1),
        "basis": basis,
        "year": year,
        "lab": "%s, %s hasılatına oranı" % (basis, year) if year else basis,
        "calc": calc,
        "amount": amount,
        "bars": bars,
        "vis": "bars" if bars and pct >= 50.0 else "ratio",
    }


# ----------------------------------------------------------------------------- akis

def is_listed(it):
    """Sayfada listelenen sirket bildirimi (rutin degil, sirket sinifi)."""
    return not it.get("rutin") and it.get("kap_class") in ("ODA", "FR", "DG")


def window_items(items, today_iso, days=WINDOW_DAYS):
    """Son `days` takvim gunu (bugun dahil); items yeniden eskiye sirali."""
    from datetime import timedelta
    d0 = datetime.strptime(today_iso[:10], "%Y-%m-%d").date()
    cut = (d0 - timedelta(days=days - 1)).isoformat()
    out = []
    for it in items:
        if it["ts"][:10] < cut:
            break
        if it["ts"][:10] <= d0.isoformat():
            out.append(it)
    return out


def type_counts(items):
    c = {k: 0 for k, _, _ in TYPES}
    for it in items:
        if is_listed(it):
            c[filing_type(it)] += 1
    c["all"] = sum(c[k] for k, _, _ in TYPES)
    return c


def row_view(it, names=None):
    """Akis satiri (kap_feed.public_item'in alt kumesi + tur + temiz baslik + onem gorunumu)."""
    names = names or {}
    k = filing_type(it)
    ts = it["ts"]
    return {
        "id": it["id"], "date": ts, "day": ts[:10], "time": ts[11:16],
        "ticker": it["ticker"], "tickers": it.get("tickers") or [it["ticker"]],
        "company": names.get(it["ticker"]) or it["ticker"],
        "k": k, "kl": TYPE_LABEL[k], "ks": TYPE_SLUG[k],
        "title": display_title(it),
        "onem": onem_view(it.get("onem")),
        "href": "/hisse/%s/bildirim/%d" % (it["ticker"], it["id"]),
    }


def group_rows(rows):
    """Ayni gun + ayni hisse + ayni tur -> tek satir (ilk satir + 'more'); sira korunur."""
    out, idx = [], {}
    for r in rows:
        key = (r["day"], r["ticker"], r["k"])
        if key in idx:
            out[idx[key]]["more"].append(r)
            continue
        idx[key] = len(out)
        out.append(dict(r, more=[]))
    return out


def _has_ticker(it, ticker):
    return ticker in (it.get("tickers") or [it.get("ticker")])


def feed(items, today_iso, tur=None, page=1, per_page=PER_PAGE, day=None, include_rutin=False,
         names=None, days=WINDOW_DAYS, ticker=None):
    """/haberler/bildirimler akisi. ticker: tek sirketin bildirimleri (`?hisse=`; 30 gun penceresi
    yok, depodaki tum gecmis — eski /haberler?hisse= listesinin yerine).
    -> {days:[{day,label,w,total,routine,mix,rows}], counts, total, page, pages, shown_from,
        shown_to, range_label, first_day, last_day}"""
    if day:
        win = [it for it in items if it["ts"][:10] == day]
    elif ticker:
        win = [it for it in items if it["ts"][:10] <= today_iso[:10]]
    else:
        win = window_items(items, today_iso, days)
    if ticker:
        win = [it for it in win if _has_ticker(it, ticker)]
    company = [it for it in win if it.get("kap_class") in ("ODA", "FR", "DG")]
    counts = type_counts(company)
    sel = [it for it in company if (include_rutin or not it.get("rutin"))
           and (not tur or filing_type(it) == tur)]
    total = len(sel)
    per_page = max(1, min(int(per_page or PER_PAGE), 100))
    pages = max(1, (total + per_page - 1) // per_page)
    page = max(1, min(int(page or 1), pages))
    vis = sel[(page - 1) * per_page: page * per_page]
    out_days = []
    for it in vis:
        d = it["ts"][:10]
        if not out_days or out_days[-1]["day"] != d:
            dp = day_parts(d)
            day_all = [x for x in company if x["ts"][:10] == d]
            day_sel = [x for x in day_all if (include_rutin or not x.get("rutin"))
                       and (not tur or filing_type(x) == tur)]
            mix = {}
            for x in day_all:
                if is_listed(x):
                    kk = filing_type(x)
                    mix[kk] = mix.get(kk, 0) + 1
            out_days.append({
                "day": d, "label": "%d %s" % (dp["d"], dp["m"]), "w": dp["w"],
                "total": len(day_sel),
                "routine": 0 if (tur or include_rutin) else sum(1 for x in day_all if x.get("rutin")),
                "mix": [{"k": kk, "l": TYPE_LABEL[kk], "n": mix[kk]}
                        for kk in sorted(mix, key=lambda z: (-mix[z], [t[0] for t in TYPES].index(z)))],
                "rows": [],
            })
        out_days[-1]["rows"].append(row_view(it, names))
    for dd in out_days:
        dd["rows"] = group_rows(dd["rows"])
    days_present = sorted(set(it["ts"][:10] for it in company)) if company else []
    return {
        "days": out_days, "counts": counts, "total": total, "page": page, "pages": pages,
        "per_page": per_page,
        "shown_from": (page - 1) * per_page + 1 if total else 0,
        "shown_to": (page - 1) * per_page + len(vis),
        "first_day": days_present[0] if days_present else None,
        "last_day": days_present[-1] if days_present else None,
        "range_label": range_label(days_present[0], days_present[-1]) if days_present else "",
    }


# ----------------------------------------------------------------------------- mini cizgi

_SPARK_CACHE = {}


def closes_from_chart_file(path, n=30):
    """data/charts/chart_<T>.json -> son n kapanis (mtime onbellekli). Yoksa []."""
    try:
        mt = os.path.getmtime(path)
    except OSError:
        return []
    hit = _SPARK_CACHE.get(path)
    if hit and hit[0] == mt:
        return hit[1]
    try:
        with open(path, encoding="utf-8") as f:
            d = json.load(f)
        vals = [float(p["close"]) for p in (d.get("ohlc") or []) if isinstance(p, dict)
                and isinstance(p.get("close"), (int, float))][-n:]
    except (OSError, ValueError, TypeError, KeyError):
        vals = []
    _SPARK_CACHE[path] = (mt, vals)
    return vals


def spark(vals, pad=6.0):
    """Kapanislar -> 100x100 kutuda polyline noktalari. <2 nokta -> None.
    {pts, area, up, lo, hi, first, last, lx, ly}"""
    vals = [float(v) for v in (vals or []) if isinstance(v, (int, float))]
    if len(vals) < 2:
        return None
    lo, hi = min(vals), max(vals)
    n = len(vals)

    def X(i):
        return i / float(n - 1) * 100.0

    def Y(v):
        return 50.0 if hi == lo else pad + (1 - (v - lo) / (hi - lo)) * (100.0 - 2 * pad)

    pts = " ".join("%.1f,%.1f" % (X(i), Y(v)) for i, v in enumerate(vals))
    return {"pts": pts, "area": "0,100 " + pts + " 100,100", "up": vals[-1] >= vals[0],
            "lo": lo, "hi": hi, "first": vals[0], "last": vals[-1],
            "lx": round(X(n - 1), 1), "ly": round(Y(vals[-1]), 1)}


# ----------------------------------------------------------------------------- gunun hikayesi

def _count_lim(rows, kind):
    return sum(1 for r in rows if r.get("lim") == kind)


def sector_extremes(sectors):
    """bulten.isi_haritasi_ozet ciktisi -> (en yuksek, en dusuk) | (None, None)."""
    s = [x for x in sectors or [] if isinstance(x.get("ortalama_degisim_pct"), (int, float))]
    if len(s) < 2:
        return None, None
    s = sorted(s, key=lambda x: -x["ortalama_degisim_pct"])
    return s[0], s[-1]


def lead_story(snap, sectors, xu_closes):
    """Donmus isi haritasi (BIST100) + sektor ozeti (Bulten ile ayni) + 30 gunluk endeks ->
    gunun hikayesi karti ya da None. Cumleler kod tarafindan, rakamlar goruntuden."""
    if not snap or not snap.get("xu100") or not snap.get("rows"):
        return None
    xu = snap["xu100"]
    close = xu.get("close")
    ch = (xu.get("ch") or {}).get("d1")
    if not close or ch is None:
        return None
    m1 = (xu.get("ch") or {}).get("m1")
    cnt = snap.get("counts") or {}
    up, dn, flat = int(cnt.get("up") or 0), int(cnt.get("down") or 0), int(cnt.get("flat") or 0)
    rows = snap["rows"]
    tavan, taban = _count_lim(rows, "tavan"), _count_lim(rows, "taban")
    if round(ch, 2) > 0:
        title = "BIST100 %s yükseldi; %d hisse değer kazandı" % (tr_pct(ch, 2, False), up)
        if tavan >= 3:
            title += ", %d hisse tavanda kapandı" % tavan
    elif round(ch, 2) < 0:
        title = "BIST100 %s düştü; %d hisse değer kaybetti" % (tr_pct(ch, 2, False), dn)
        if taban >= 3:
            title += ", %d hisse tabanda kapandı" % taban
    else:
        title = "BIST100 değişmeden kapandı; %d hisse yükseldi, %d hisse düştü" % (up, dn)
    text = "Endeks %s puanda kapandı" % tr_num(close)
    if isinstance(m1, (int, float)):
        text += "; 1 aylık değişim %s" % tr_pct(m1)
    text += "."
    hi, lo = sector_extremes(sectors)
    n_sec = len([x for x in sectors or [] if isinstance(x.get("ortalama_degisim_pct"), (int, float))])
    if hi and lo:
        a, b = hi["ortalama_degisim_pct"], lo["ortalama_degisim_pct"]
        if a < 0 and b < 0:
            text += " %d sektörün tümü ekside; en sınırlı düşüş %s (%s), en sert düşüş %s (%s)." % (
                n_sec, hi["sektor"], tr_pct(a), lo["sektor"], tr_pct(b))
        elif a > 0 and b > 0:
            text += " %d sektörün tümü artıda; en güçlü artış %s (%s), en sınırlı artış %s (%s)." % (
                n_sec, hi["sektor"], tr_pct(a), lo["sektor"], tr_pct(b))
        else:
            text += " Sektörlerde en çok yükselen %s (%s), en çok düşen %s (%s)." % (
                hi["sektor"], tr_pct(a), lo["sektor"], tr_pct(b))
    ranked = sorted([r for r in rows if isinstance((r.get("ch") or {}).get("d1"), (int, float))
                     and not r.get("stale")], key=lambda r: -r["ch"]["d1"])
    movers = []
    if ranked:
        movers = [{"t": ranked[0]["t"], "ch": ranked[0]["ch"]["d1"]}]
        if ranked[-1]["t"] != ranked[0]["t"]:
            movers.append({"t": ranked[-1]["t"], "ch": ranked[-1]["ch"]["d1"]})
    sp = spark(xu_closes)
    day = snap.get("asof")
    return {
        "day": day, "day_label": day_label(day) if day else "", "title": title, "text": text,
        "close": close, "ch": ch, "m1": m1, "up": up, "down": dn, "flat": flat,
        "tavan": tavan, "taban": taban, "n": snap.get("n") or len(rows),
        "hot": abs(ch) >= 2.0, "sp": sp,
        "sp_first": sp["first"] if sp else None, "movers": movers,
        "sector_hi": hi, "sector_lo": lo,
    }


# ----------------------------------------------------------------------------- kredi notu basamaklari

_SCALE_SP = ("AAA", "AA+", "AA", "AA-", "A+", "A", "A-", "BBB+", "BBB", "BBB-", "BB+", "BB", "BB-", "B+", "B",
             "B-", "CCC+", "CCC", "CCC-", "CC", "C", "RD", "D")
_SCALE_MOODYS = ("Aaa", "Aa1", "Aa2", "Aa3", "A1", "A2", "A3", "Baa1", "Baa2", "Baa3", "Ba1", "Ba2", "Ba3", "B1",
                 "B2", "B3", "Caa1", "Caa2", "Caa3", "Ca", "C")
_AGENCIES = (("Fitch", re.compile(r"\bFitch\b", re.I), _SCALE_SP),
             ("Moody's", re.compile(r"\bMoody", re.I), _SCALE_MOODYS),
             ("S&P", re.compile(r"\bS&P\b|Standard\s*(?:&|and)\s*Poor", re.I), _SCALE_SP),
             ("JCR", re.compile(r"\bJCR\b", re.I), _SCALE_SP))
_Q = "[\"'‘’“”`´]"
_RTOK = re.compile(_Q + r"{1,2}\s*([A-Za-z]{1,4}[0-9]?\s*[+\-−–]?)\s*(\((?:tr|TR|Trk)\))?\s*" + _Q + r"{1,2}")
_RMOVE = re.compile(_Q + r"{1,2}\s*([A-Za-z]{1,4}[0-9]?[+\-−–]?)\s*(?:\((?:tr|TR)\))?\s*" + _Q +
                    r"{1,2}\s*'?(?:t|d)[ae]n\s+" + _Q + r"{1,2}\s*([A-Za-z]{1,4}[0-9]?[+\-−–]?)\s*(?:\((?:tr|TR)\))?\s*" +
                    _Q + r"{1,2}")
# KAP derecelendirme metinlerindeki edilgen kaliplar ("revize edilmiştir", "düşürülmüştür",
# "izlemeye alınmıştır"); "teyit" degisiklik degildir. Yon yalniz acik fiilden (izleme etiketi yon soylemez).
_RCHANGE = re.compile(r"revize ed|düşürül|indiril|yükseltil|izlemeye alın|izleme listesine alın|Rating Watch", re.I)
_RDOWN = re.compile(r"düşürül|indiril", re.I)
_RUP = re.compile(r"yükseltil", re.I)
_OUTLOOK = {"negatif": "negatif", "pozitif": "pozitif", "stabil": "stabil", "durağan": "durağan",
            "gelişen": "gelişen", "negative": "negatif", "positive": "pozitif", "stable": "stabil"}


def _rnorm(tok):
    return re.sub(r"\s+", "", tok or "").replace("−", "-").replace("–", "-")


def rating_view(text):
    """KAP kredi derecelendirme bildirimi metni -> not basamaklari gorunumu ya da None.
    Yalniz bildirimin kendi metninden (kod; AI yok): kurulus (Fitch/Moody's/S&P/JCR), kurulusun
    olcegindeki ilk tirnakli not, 'X'ten Y'ye' gecisi, izleme/gorunum etiketi, degisiklik var mi.
    -> {agency, lab, scale[7], at, prev, dir, tag, tag_dir, changed, national}"""
    t = re.sub(r"\s+", " ", text or "")
    if not t:
        return None
    ag = next(((name, scale) for name, rx, scale in _AGENCIES if rx.search(t)), None)
    if not ag:
        return None
    name, scale = ag
    prev = at = None
    national = False
    mv = _RMOVE.search(t)
    if mv and _rnorm(mv.group(1)) in scale and _rnorm(mv.group(2)) in scale:
        prev, at = _rnorm(mv.group(1)), _rnorm(mv.group(2))
        national = "(tr" in mv.group(0).lower()
    else:
        for m in _RTOK.finditer(t):
            tok = _rnorm(m.group(1))
            if tok in scale:
                at, national = tok, bool(m.group(2))
                break
    if not at:
        return None
    i = scale.index(at)
    lo = max(0, min(i - 3, len(scale) - 7))
    win = list(scale[lo:lo + 7])
    d = None
    if prev and prev != at:
        d = "down" if scale.index(prev) < i else "up"
    tag, tag_dir = None, None
    if re.search(r"Rating Watch Negative|\bRWN\b|negatif izleme", t, re.I):
        tag, tag_dir = "Negatif izleme", "down"
    elif re.search(r"Rating Watch Positive|\bRWP\b|pozitif izleme", t, re.I):
        tag, tag_dir = "Pozitif izleme", "up"
    else:
        om = re.search(r"[Gg]örünüm\w*[^.]{0,80}?" + _Q + r"?\s*(Negatif|Pozitif|Stabil|Durağan|Gelişen|Negative|"
                       r"Positive|Stable)\b", t, re.I)
        if om:
            w = _OUTLOOK.get(_lower_tr(om.group(1)), _lower_tr(om.group(1)))
            tag = "Görünüm " + w
            tag_dir = "down" if w == "negatif" else ("up" if w == "pozitif" else None)
    changed = bool(d) or bool(_RCHANGE.search(t))
    if d is None and changed:
        d = "down" if _RDOWN.search(t) and not _RUP.search(t) else ("up" if _RUP.search(t) and not _RDOWN.search(t)
                                                                   else None)
    disp = lambda x: x.replace("-", "−")  # noqa: E731
    pv = prev if prev and prev != at else None
    return {"agency": name,
            "lab": "%s · %snot basamakları" % (name, "ulusal " if national else ""),
            "scale": [disp(x) for x in win], "at_i": win.index(at),
            "prev_i": win.index(pv) if pv in win else None,
            "at": disp(at) + (" (tr)" if national else ""), "prev": disp(pv) + (" (tr)" if national else "") if pv else None,
            "dir": d, "tag": tag, "tag_dir": tag_dir, "changed": changed, "national": national}


# ----------------------------------------------------------------------------- gundem sirket kartlari

_CARD_TYPES = ("is", "sermaye", "kredi", "temettu", "finansal", "dava")


def company_cards(items, day_iso, names=None, n=6, hot_tickers=(), doc_fn=None):
    """Gunun (day_iso ve oncesindeki son islem gununun) rutin-disi bildirimlerinden kartlar.
    Sira: onem orani azalan, sonra haber niteligindeki turler, sonra en yeni. Ayni hisse bir kez.
    doc_fn(id) -> bildirim metni sozlugu (kap_feed.Store.doc): kredi notu kartinda not basamaklari.
    'Öne çıkan' (taslak kurali): onem orani %5 ve ustu, kredi notu ya da gorunum degisikligi,
    sitedeki en cok yukselen/dusen hissenin bildirimi."""
    names = names or {}
    days = sorted(set(it["ts"][:10] for it in items if it["ts"][:10] <= day_iso and is_listed(it)),
                  reverse=True)[:2]
    pool = [it for it in items if it["ts"][:10] in days and is_listed(it)]

    def rank(it):
        o = it.get("onem") or {}
        k = filing_type(it)
        return (-(o.get("pct") or 0.0), 0 if k in _CARD_TYPES else 1,
                _CARD_TYPES.index(k) if k in _CARD_TYPES else 9, "~" if not it["ts"] else "", it["ts"])
    pool = sorted(pool, key=lambda it: it["ts"], reverse=True)
    pool = sorted(pool, key=lambda it: rank(it)[:3])
    out, seen = [], set()
    for it in pool:
        if it["ticker"] in seen:
            continue
        k = filing_type(it)
        if k == "ozel" and not it.get("onem"):
            continue
        seen.add(it["ticker"])
        r = row_view(it, names)
        r["rating"] = None
        if k == "kredi" and doc_fn:
            try:
                r["rating"] = rating_view((doc_fn(it["id"]) or {}).get("text"))
            except Exception:  # noqa: BLE001 — metin okunamazsa kart 30 gunluk cizgiyle
                r["rating"] = None
        r["hot"] = bool((r["onem"] and r["onem"]["pct"] >= 5.0) or it["ticker"] in set(hot_tickers or ())
                        or (r["rating"] and r["rating"]["changed"]))
        r["time_label"] = "%s · %s" % (day_label(r["day"]), r["time"])
        out.append(r)
        if len(out) >= n:
            break
    return out


# ----------------------------------------------------------------------------- D-57 sozlesmesi

GH_CATS = ("Türkiye", "Dünya", "Piyasa", "Şirketler", "Merkez bankaları", "Emtia")
_URL_OK = re.compile(r"^https?://[^\s\"'<>]+$")


def gundem_haber_source(ns):
    """D-57 baskisini veren fonksiyon (app.py ad alani `ns` icinde) ya da None.
    Once `_gundem_haber_payload()` kancasi; yoksa D-57 dalinin modulu `gundem_haber.load_latest()`
    (D-57 bu modulu app.py'ye `import gundem_haber` ile ekler ve degeri context processor ile verir).
    /haberler sablona `gundem_haber`i ACIKCA gecirdigi icin (Flask acik degeri context processor'un
    ustune yazar) kaynak burada bulunmazsa D-57 baskisi hic gorunmez."""
    fn = ns.get("_gundem_haber_payload")
    if callable(fn):
        return fn
    fn = getattr(ns.get("gundem_haber"), "load_latest", None)
    return fn if callable(fn) else None


def gundem_haber_from(ns, log=None):
    """D-57 son baskisi -> clean_gundem_haber ciktisi ya da None (kaynak yok/hata/madde yok)."""
    fn = gundem_haber_source(ns)
    if fn is None:
        return None
    try:
        return clean_gundem_haber(fn())
    except Exception as e:  # noqa: BLE001 — Gundem v1 maddeleriyle cizilir
        if log:
            log("gundem_haber okunamadı: %s" % e)
        return None


def clean_gundem_haber(doc, max_items=8):
    """D-57 /api/gundem-haber sozlugu -> dogrulanmis kopya ya da None (madde yoksa)."""
    if not isinstance(doc, dict):
        return None
    items = []
    for m in doc.get("maddeler") or []:
        if not isinstance(m, dict):
            continue
        h, oz = (m.get("baslik") or "").strip(), (m.get("ozet") or "").strip()
        if not h or m.get("kategori") not in GH_CATS:
            continue
        src = [{"ad": str(s.get("ad") or "").strip(), "url": s.get("url")}
               for s in m.get("kaynaklar") or [] if isinstance(s, dict) and s.get("ad")
               and isinstance(s.get("url"), str) and _URL_OK.match(s["url"])]
        tk = [t for t in m.get("hisseler") or [] if isinstance(t, str) and re.fullmatch(r"[A-Z0-9]{3,6}", t)][:3]
        items.append({"id": str(m.get("id") or len(items)), "kategori": m["kategori"], "baslik": h, "ozet": oz,
                      "hisseler": tk, "kaynaklar": src[:4], "ai": bool(m.get("ai")),
                      "onemli": bool(m.get("onemli"))})
        if len(items) >= max_items:
            break
    if not items:
        return None
    return {"baski": doc.get("baski"), "baski_label": doc.get("baski_label") or "", "maddeler": items}
