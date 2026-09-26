"""D-53: ana sayfa (C-27/C-28/C-30) SSR alanlari — Flask'tan bagimsiz, saf hesaplama (py3.9).

- fin_answer: hisse sayfasindaki "Finansallari nasil?" cevabi (templates/hisse.html `fin_answer`
  makrosu) ile BIREBIR ayni kural: kategori >=70 guclu, <50 zayif (financial_health_score esikleri).
- valuation: hisse sayfasindaki "Fiyati makul mu?" hukmunun (tvValuation) Python karsiligi:
  KAP son 12 ay F/K ve PD/DD'nin sektor ortancasina orani, <0,80 ucuz, >1,25 pahali (kanon §5.6);
  F/K ile PD/DD ters yonde ise karisik; ortanca yoksa hukum yok (None).
- featured_pool: "One cikan sirketler" havuzu — Trend Bozuldu ve donuk hisse haric, BP + veri
  tamligi >=0,8, BP azalan / esitlikte kod artan.
"""

TV_CUT = 0.80
TV_EXP = 1.25
MIN_COMPLETENESS = 0.8
FEATURED_N = 5

_CAT_NAMES = (
    ("karlilik", "kârlılık"),
    ("nakit_akisi", "nakit akışı"),
    ("kaldirac", "borç durumu"),
    ("degerleme_buyume", "değerleme ve büyüme"),
)
_CAT = dict(_CAT_NAMES)


def _num(v):
    return isinstance(v, (int, float)) and not isinstance(v, bool) and v == v


def _cap(text):
    # hisse.html `|capitalize`: yalniz ilk harf buyur (Turkce i/I sorunu yok: kelimeler k/n/b/d)
    return text[:1].upper() + text[1:]


def fin_answer(entry):
    """entry: _financial_health_cache[T]["data"] (yoksa/kategorisiz -> None: 'Veri bekleniyor'
    metnini tuketici yazar). Donus: tek cumle ya da None."""
    if not entry:
        return None
    v2 = entry.get("temel_v2")
    if isinstance(v2, dict):
        if v2.get("cevap"):
            return v2["cevap"]
        if v2.get("limited_data"):
            return "Sınırlı veri"
    cats = entry.get("categories")
    if not isinstance(cats, dict):
        return None
    # hisse.html `categories.items()` sirasini kullanir (esitlikte kaynak sirasi korunur)
    ordered = [(k, v) for k, v in cats.items() if k in _CAT and _num(v)]
    if not ordered:
        return None
    ordered = sorted(ordered, key=lambda kv: kv[1], reverse=True)
    strong = [kv for kv in ordered if kv[1] >= 70]
    weak = [kv for kv in ordered if kv[1] < 50]
    if strong and weak:
        return "%s güçlü, %s zayıf" % (_cap(_CAT[strong[0][0]]), _CAT[weak[-1][0]])
    if len(strong) >= 2:
        return "%s ve %s güçlü" % (_cap(_CAT[strong[0][0]]), _CAT[strong[1][0]])
    if strong:
        return "%s öne çıkıyor" % _cap(_CAT[strong[0][0]])
    if weak:
        return "%s zayıf, diğerleri dengeli" % _cap(_CAT[weak[-1][0]])
    return "Dengeli; belirgin zayıf alan yok"


def valuation(entry, fund):
    """'ucuz' | 'makul' | 'pahali' | 'karisik' | None.

    entry: saglik kaydi (v2 varsa `temel_v2.degerleme.hukum` tek kaynak); fund: /fundamentals
    ucunun dondurdugu sozluk (kap + sektor_ortanca eklenmis)."""
    v2 = (entry or {}).get("temel_v2")
    if isinstance(v2, dict):
        d = v2.get("degerleme") or {}
        h = d.get("hukum")
        return h if h in ("ucuz", "makul", "pahali", "karisik") else None
    f = fund or {}
    k = f.get("kap") if f.get("kap_durum") == "var" else None
    now = (k or {}).get("degerleme_simdi")
    med = f.get("sektor_ortanca") or {}
    if now and not now.get("pay_uyumsuz"):
        pe, pb = now.get("fk"), now.get("pd_dd")
    else:
        pe, pb = (None, None) if k else (f.get("pe_ratio"), f.get("pb_ratio"))
    scored = []
    for v, m in ((pe, med.get("fk")), (pb, med.get("pd_dd"))):
        base = (m or {}).get("deger")
        if _num(v) and v > 0 and _num(base) and base > 0:
            q = v / base
            scored.append(-1 if q < TV_CUT else (1 if q > TV_EXP else 0))
    if not scored:
        return None
    if len(scored) == 2 and scored[0] * scored[1] == -1:
        return "karisik"
    s = sum(scored)
    return "ucuz" if s < 0 else ("pahali" if s > 0 else "makul")


def featured_pool(stocks, n=FEATURED_N):
    """stocks: /api/data satirlari (borsapusula_skoru, hs_available, data_completeness eklenmis).
    JS daRenderFeatured ile ayni suzgec ve sira; ilk n."""
    pool = [
        s for s in stocks
        if not s.get("stale_reason") and s.get("data_quality") != "stale"
        and s.get("signal") != "SAT" and s.get("hs_available")
        and _num(s.get("borsapusula_skoru"))
        and _num(s.get("data_completeness")) and s["data_completeness"] >= MIN_COMPLETENESS
    ]
    pool.sort(key=lambda s: (-s["borsapusula_skoru"], s.get("ticker") or ""))
    return pool[:n]
