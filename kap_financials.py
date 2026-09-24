"""D-40a0: KAP finansal rapor sayfalarindan "aciklanan veri" kayitlari.

Ilke (kanon docs/URUN-VE-TASARIM.md §3 "Veri tanimlari"):
- Her rapor kendi biriminde, kendi cari/karsilastirma sutunlariyla saklanir.
- Yillik degisim = ayni raporun (cari - karsilastirma) / |karsilastirma|.
  Farkli raporlarin tutarlari tek seride birlestirilmez; kendi TUFE duzeltmemiz yok.
- Her tutar ic dogrulama icin `kaynak: {rapor, donem, birim}` tasir; API'ye ve
  siteye kaynak yazilmaz (apply_to_fundamentals kaynaklari disarida birakir).

Saf fonksiyonlar (ag yok). Ag erisimi tools/build_kap_financials.py'de.
Ayristirici plans/2026-09-23-denetim/kanit/tc/frparse.py'den, kalem eslemesi
build_temel.py'den kopyalandi. Banka bilancosu 6 sutunlu (TP/YP/Toplam x
cari/onceki): sutun basliga gore secilir, yalniz "Toplam".
"""
from __future__ import annotations

import html as _html
import json
import os
import re
from datetime import date, datetime, timedelta

SCHEMA_VERSION = 1
DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "kap_fin")

# D-03 olcumu (Yahoo financialCurrency) + temel-cesitlendirme §1: islevsel para birimi
# doviz, KAP'ta TL'ye cevrilmis sunum. ENKAI/TAVHL'nin TMS 29 uygulayan TL bagli
# ortakliklari oldugu icin parasal pozisyon satiri dolu; esas bu listeden okunur.
YABANCI_PARA = {"THYAO": "USD", "ENKAI": "USD", "TAVHL": "EUR", "PGSUS": "EUR"}

# Parasal pozisyon / hasilat bu oranin altindaysa TMS 29 sayilmaz (THYAO %0,008).
_TMS29_MIN_RATIO = 0.001

# ----------------------------------------------------------------------------- sayfa ayristirma

def unesc(h):
    return (h.replace("\\u003c", "<").replace("\\u003e", ">").replace('\\"', '"')
             .replace("\\u0026", "&").replace("\\r\\n", "\n").replace("\\n", "\n"))


def _txt(s):
    s = re.sub(r'<br\s*/?>', ' ', s)
    s = re.sub(r'<[^>]+>', '', s)
    return re.sub(r'\s+', ' ', _html.unescape(s)).strip()


_TABLE_RE = re.compile(r'<table class="financial-table tbl_([a-z_]+_role_\d+)">')
_TABLE_END = re.compile(r'</tbody></table>(?!</td>)')


def _parse_header(seg):
    """Tablo basligi -> {sutun_no: baslik metni}; rowspan/colspan birlestirilir."""
    first = re.search(r'<tr class="[a-z_]+_role_\d+-row-', seg)
    head = seg[:first.start()] if first else seg
    rows = re.findall(r'<tr[^>]*>(.*?)</tr>', head, re.S)
    grid, occupied = {}, set()
    for ri, row in enumerate(rows):
        cells = re.findall(r'<td([^>]*)>(.*?)</td>(?=\s*(?:<td|$))', row, re.S)
        c = 0
        for attrs, inner in cells:
            while (ri, c) in occupied:
                c += 1
            cs = int((re.search(r'colspan="(\d+)"', attrs) or [0, 1])[1])
            rs = int((re.search(r'rowspan="(\d+)"', attrs) or [0, 1])[1])
            m = re.search(r'content-tr" style="display: block;">(.*?)</div>', inner, re.S)
            txt = _txt(m.group(1)) if m else _txt(inner)
            for dr in range(rs):
                for dc in range(cs):
                    occupied.add((ri + dr, c + dc))
                    grid[(ri + dr, c + dc)] = txt
            c += cs
    cols = {}
    for c in range(max([k[1] for k in grid] + [0]) + 1):
        parts = []
        for ri in range(len(rows)):
            v = grid.get((ri, c))
            if v and v not in parts:
                parts.append(v)
        cols[c] = " / ".join(parts)
    return cols


def parse_page(h):
    """KAP Bildirim sayfasi (ham RSC ya da trim_page ciktisi) -> tablolar.
    Sayfa her tabloyu iki kez tasir; ilk (etiketli) kopya alinir."""
    t = unesc(h)
    starts = list(_TABLE_RE.finditer(t))
    tables, seen = [], set()
    for i, m in enumerate(starts):
        role = m.group(1)
        if role in seen:
            continue
        seen.add(role)
        end = starts[i + 1].start() if i + 1 < len(starts) else len(t)
        seg = t[m.start():end]
        pre = t[max(0, m.start() - 3000):m.start()]
        unit = re.findall(r'Sunum Para Birimi</td>\s*<td>([^<]*)</td>', pre)
        nat = re.findall(r'Finansal Tablo Niteliği</td>\s*<td>([^<]*)</td>', pre)
        rows = []
        for rm in re.finditer(r'<tr class="' + re.escape(role) + r'-row-(\d+)[^"]*">(.*?)(?=<tr class="'
                              + re.escape(role) + r'-row-|</tbody></table>(?!</td>))', seg, re.S):
            body = rm.group(2)
            el = re.search(r'taxonomy-field-name">([^<]*)</div>', body)
            tr = re.search(r'content-tr" style="display: block;">([^<]*)</div>', body)
            vals = {}
            for vm in re.finditer(r'taxonomy-context-value col-order-class-(\d+)"><div><div class="[^"]*"'
                                  r'(?: title="([^"]*)")?>([^<]*)</div>', body):
                title, txt = vm.group(2), vm.group(3)
                src = title if title not in (None, "") else txt
                v = None
                if src not in (None, ""):
                    s2 = src.strip()
                    if title in (None, ""):
                        s2 = s2.replace(".", "").replace(",", ".")
                    try:
                        v = float(s2)
                    except ValueError:
                        v = None
                vals[int(vm.group(1))] = v
            rows.append({"el": el.group(1).split("|")[0] if el else None,
                         "tr": _html.unescape(tr.group(1)).strip() if tr else None,
                         "vals": vals})
        tables.append({"role": role, "unit": unit[-1].strip() if unit else None,
                       "nature": nat[-1].strip() if nat else None,
                       "cols": {k: v for k, v in _parse_header(seg).items() if v},
                       "rows": rows})
    return tables


def stmt_of(role):
    code = role.split("_role_")[1]
    if code.startswith("2105"):
        return "OFFBS"
    return {"2": "BS", "3": "IS", "4": "OCI", "5": "CF", "6": "EQ"}.get(code[0], "?")


def trim_page(h):
    """Saklama icin: yalniz bilanco/gelir/nakit akis tablolari + birim/nitelik basligi.
    parse_page(trim_page(h)) ayni kalemleri verir (3-5 MB sayfa -> birkac yuz KB)."""
    t = unesc(h)
    out, seen = [], set()
    for m in _TABLE_RE.finditer(t):
        role = m.group(1)
        if role in seen or stmt_of(role) not in ("BS", "IS", "CF"):
            continue
        seen.add(role)
        end = _TABLE_END.search(t, m.end())
        if not end:
            continue
        pre = t[max(0, m.start() - 3000):m.start()]
        unit = re.findall(r'Sunum Para Birimi</td>\s*<td>([^<]*)</td>', pre)
        nat = re.findall(r'Finansal Tablo Niteliği</td>\s*<td>([^<]*)</td>', pre)
        out.append('<table><tr><td>Sunum Para Birimi</td><td>%s</td></tr><tr><td>Finansal Tablo Niteliği</td>'
                   '<td>%s</td></tr></table>' % (unit[-1] if unit else "", nat[-1] if nat else ""))
        out.append(t[m.start():end.end()])
    return "\n".join(out)


def classify_cols(tb):
    """Sutun basligindan tur: current/comparative (kumulatif), q_current/q_comparative (3 aylik).
    Banka bilancosunda TP ve YP sutunlari atlanir, yalniz Toplam kullanilir."""
    out = {}
    for k, hdr in tb["cols"].items():
        h = hdr.strip()
        if " / " in h:
            base, sub = h.rsplit(" / ", 1)
            if sub != "Toplam":
                continue
        else:
            base = h
        if base.startswith("Cari Dönem 3 Aylık"):
            kind = "q_cur"
        elif base.startswith("Önceki Dönem 3 Aylık"):
            kind = "q_prev"
        elif base.startswith("Cari Dönem"):
            kind = "cur"
        elif base.startswith("Önceki Dönem"):
            kind = "prev"
        else:
            continue
        out.setdefault(kind, (k, h))
    return out


# ----------------------------------------------------------------------------- kalem eslemesi (XBRL eleman adi)

IND_ITEMS = [
    ("revenue", "IS", "ifrs-full_Revenue"),
    ("gross_profit", "IS", "ifrs-full_GrossProfit"),
    ("operating_profit", "IS", "ifrs-full_ProfitLossFromOperatingActivities"),
    ("finance_costs", "IS", "ifrs-full_FinanceCosts"),
    ("net_monetary_position", "IS", "ifrs-full_GainsLossesOnNetMonetaryPosition"),
    ("net_income_total", "IS", "ifrs-full_ProfitLoss"),
    ("net_income_parent", "IS", "ifrs-full_ProfitLossAttributableToOwnersOfParent"),
    ("cfo", "CF", "ifrs-full_CashFlowsFromUsedInOperatingActivities"),
    ("d_and_a", "CF", "ifrs-full_AdjustmentsForDepreciationAndAmortisationExpense"),
    ("capex", "CF", "kap-fr_PurchaseOfPropertyPlantEquipmentAndIntangibleAssetsClassifiedAsInvestingActivities"),
    ("dividends_paid", "CF", "ifrs-full_DividendsPaidClassifiedAsFinancingActivities"),
    ("cash", "BS", "ifrs-full_CashAndCashEquivalents"),
    ("current_financial_investments", "BS", "kap-fr_CurrentFinancialInvestments"),
    ("trade_receivables", "BS", "ifrs-full_CurrentTradeReceivables"),
    ("inventories", "BS", "ifrs-full_Inventories"),
    ("current_assets", "BS", "ifrs-full_CurrentAssets"),
    ("total_assets", "BS", "ifrs-full_Assets"),
    # Kiralama borclari KAP taksonomisinde bu uc toplamin alt kiriliminda (THYAO:
    # UV borclanma 726.977 icinde 639.109 kiralama) -> toplamlar kiralamalar dahil.
    ("st_borrowings", "BS", "kap-fr_CurrentBorowings"),
    ("current_portion_lt_borrowings", "BS", "kap-fr_CurrentPortionOfNoncurrentBorrowings"),
    ("lt_borrowings", "BS", "ifrs-full_LongtermBorrowings"),
    ("trade_payables", "BS", "kap-fr_CurrentTradePayables"),
    ("current_liabilities", "BS", "ifrs-full_CurrentLiabilities"),
    ("equity_parent", "BS", "ifrs-full_EquityAttributableToOwnersOfParent"),
    ("equity_total", "BS", "ifrs-full_Equity"),
    ("issued_capital", "BS", "ifrs-full_IssuedCapital"),
]

BANK_ITEMS = [
    ("net_interest_income", "IS", "kap-fr_InterestIncomeOrExpense"),
    ("net_fees", "IS", "kap-fr_FeeAndCommissionIncomeOrExpenses"),
    ("operating_income", "IS", "kap-fr_GrossProfitLossFromOperatingActivitiesForBankingSector"),
    ("ecl_expense", "IS", "kap-fr_AllowanceExpensesForExpectedCreditLosses"),
    ("personnel_expense", "IS", "kap-fr_PersonnelExpenses"),
    ("other_operating_expense", "IS", "kap-fr_OtherOperatingExpenses"),
    ("net_monetary_position", "IS", "ifrs-full_GainsLossesOnNetMonetaryPosition"),
    ("net_income_total", "IS", "ifrs-full_ProfitLoss"),
    ("net_income_parent", "IS", "ifrs-full_ProfitLossAttributableToOwnersOfParent"),
    ("dividends_paid", "CF", "ifrs-full_DividendsPaidClassifiedAsFinancingActivities"),
    ("cash", "BS", "ifrs-full_CashAndCashEquivalents"),
    ("loans", "BS", "kap-fr_Loans"),
    ("total_assets", "BS", "ifrs-full_Assets"),
    ("deposits", "BS", "kap-fr_Deposits"),
    ("equity_total", "BS", "ifrs-full_Equity"),
    ("nci", "BS", "ifrs-full_NoncontrollingInterests"),
    ("issued_capital", "BS", "ifrs-full_IssuedCapital"),
]

_PERIOD_MONTH = {1: "03", 2: "06", 3: "09", 4: "12"}


def donem_label(fy, period):
    return "%s/%s" % (fy, _PERIOD_MONTH.get(period, "??"))


def parse_unit(u):
    """'1.000 TL' -> (1000, 'TL'); 'TL' -> (1, 'TL'); tanimsiz -> (None, None)."""
    m = re.match(r'^\s*(?:([\d.]+)\s+)?([A-Z]{2,3})\s*$', u or "")
    if not m:
        return None, None
    return (int(m.group(1).replace(".", "")) if m.group(1) else 1), m.group(2)


def _item(tabs, stmt, el):
    for tb in tabs:
        if stmt_of(tb["role"]) != stmt:
            continue
        for r in tb["rows"]:
            if r["el"] == el:
                cols = classify_cols(tb)
                rec = {"el": el}
                for kind in ("cur", "prev", "q_cur", "q_prev"):
                    if kind in cols:
                        rec[kind] = r["vals"].get(cols[kind][0])
                return rec
    return None


def _headers(tabs):
    out = {}
    for tb in tabs:
        st = stmt_of(tb["role"])
        if st in ("BS", "IS", "CF") and st not in out:
            out[st] = {kind: hdr for kind, (k, hdr) in classify_cols(tb).items()}
    return out


def _is_bank(tabs):
    return any(r["el"] == "kap-fr_InterestIncomeOrExpense" for tb in tabs
               if stmt_of(tb["role"]) == "IS" for r in tb["rows"])


def basis_of(fmt, items, ticker=None, sector=None):
    """Muhasebe esasi: banka | sigorta | yabanci_para | tms29 | nominal."""
    if fmt == "banka":
        return "banka"
    if sector and "SİGORTA" in sector:
        return "sigorta"
    if ticker in YABANCI_PARA:
        return "yabanci_para"
    nmp = items.get("net_monetary_position") or {}
    rev = abs((items.get("revenue") or {}).get("cur") or 0)
    vals = [abs(nmp.get(k) or 0) for k in ("cur", "prev")]
    if rev and max(vals) >= _TMS29_MIN_RATIO * rev:
        return "tms29"
    if not rev and max(vals) > 0:
        return "tms29"
    return "nominal"


def build_report(page_html, meta, ticker=None, sector=None):
    """Tek rapor kaydi. meta: {idx, publish, fy, period} (KAP bildirim listesinden)."""
    tabs = parse_page(page_html)
    if not tabs:
        raise ValueError("finansal tablo bulunamadi (idx %s)" % meta.get("idx"))
    fmt = "banka" if _is_bank(tabs) else "sanayi"
    units = sorted(set(tb["unit"] for tb in tabs if tb["unit"]))
    natures = sorted(set(tb["nature"] for tb in tabs if tb["nature"]))
    unit = units[0] if len(units) == 1 else "|".join(units)
    mult, currency = parse_unit(unit)
    donem = donem_label(meta["fy"], meta["period"])
    kaynak = {"rapor": meta["idx"], "donem": donem, "birim": unit}
    items = {}
    for key, st, el in (BANK_ITEMS if fmt == "banka" else IND_ITEMS):
        it = _item(tabs, st, el)
        if it is not None:
            it["kaynak"] = kaynak
        items[key] = it
    return {"idx": meta["idx"], "publish": meta.get("publish"), "fy": meta["fy"], "period": meta["period"],
            "donem": donem, "nature": natures[0] if len(natures) == 1 else "|".join(natures),
            "unit": unit, "mult": mult, "currency": currency, "format": fmt,
            "basis": basis_of(fmt, items, ticker, sector), "cols": _headers(tabs), "items": items}


def kap_publish_iso(s):
    """KAP listesi '04.02.2026 18:10:07' -> '2026-02-04T18:10'."""
    try:
        return datetime.strptime(s[:16], "%d.%m.%Y %H:%M").strftime("%Y-%m-%dT%H:%M")
    except (TypeError, ValueError):
        return None


def select_disclosures(items, years=5, interims=5):
    """KAP 'Finansal Rapor' listesinden son `years` yillik + son `interims` ara donem.
    Donus {(fy, period): [meta, ...]} (ikili yayinda birden cok aday -> choose_report)."""
    groups = {}
    for x in items:
        if x.get("subject") != "Finansal Rapor" or not x.get("year") or x.get("period") not in (1, 2, 3, 4):
            continue
        meta = {"idx": int(x["disclosureIndex"]), "fy": int(x["year"]), "period": int(x["period"]),
                "publish": kap_publish_iso(x.get("publishDate"))}
        groups.setdefault((meta["fy"], meta["period"]), {})[meta["idx"]] = meta
    annual = sorted((k for k in groups if k[1] == 4), reverse=True)[:years]
    inter = sorted((k for k in groups if k[1] != 4), reverse=True)[:interims]
    return {k: sorted(groups[k].values(), key=lambda m: m["idx"]) for k in annual + inter}


def choose_report(candidates):
    """Ayni donemin raporlarindan secim (GARAN gibi ikili yayin): Konsolide olan,
    ayni nitelikte birden cok varsa en yeni bildirim (duzeltme)."""
    if not candidates:
        return None
    kons = [c for c in candidates if c.get("nature") == "Konsolide"]
    return max(kons or candidates, key=lambda c: c["idx"])


# ----------------------------------------------------------------------------- temettu (Kar Payi Dagitim Islemlerine Iliskin Bildirim)

DIVIDEND_SUBJECT = "Kar Payı Dağıtım İşlemlerine İlişkin Bildirim"


def _flat(h):
    s = unesc(h)
    s = re.sub(r"<script.*?</script>", " ", s, flags=re.S)
    s = re.sub(r"<[^>]+>", " | ", s)
    s = _html.unescape(s)
    return re.sub(r"(\s*\|\s*)+", " | ", s)


def _tr_num(x):
    return float(x.replace(".", "").replace(",", "."))


def _tr_date(x):
    return datetime.strptime(x, "%d.%m.%Y").date().isoformat()


def parse_dividend(page_html, ticker, meta):
    """Tek bildirim -> {idx, publish, gk_tarihi, odeme_sekli, taksitler[]}.
    Tutar = 1 TL nominal paya brut/net TL; islem goren pay grubu (hisse kodu gecen satir)."""
    s = _flat(page_html)
    gk = re.search(r"Genel Kurul Tarihi \| ([\d.]{10})", s)
    sekil = re.search(r"Nakit Kar Payı Ödeme Şekli \| ([^|]+) \|", s)
    amounts = {}
    for m in re.finditer(r"\| [^|]*\b" + re.escape(ticker) + r"\b[^|]* \| (\d+\. Taksit|Peşin) \| ([\d.,]+) \| "
                         r"[\d.,]+ \| [\d.,]+ \| ([\d.,]+) \|", s):
        amounts.setdefault(m.group(1), (_tr_num(m.group(2)), _tr_num(m.group(3))))
    dates = {}
    for m in re.finditer(r"\| (\d+\. Taksit|Peşin) \| ([\d.]{10}) \| ([\d.]{10}) \| ([\d.]{10}) \| ([\d.]{10})(?= \|)", s):
        dates.setdefault(m.group(1), m)
    taksitler = []
    for name, (brut, net) in amounts.items():
        d = dates.get(name)
        taksitler.append({"taksit": name, "brut": brut, "net": net,
                          "hak_kullanim": _tr_date(d.group(3)) if d else None,
                          "odeme": _tr_date(d.group(4)) if d else None})
    taksitler.sort(key=lambda x: x["odeme"] or "")
    return {"idx": meta["idx"], "publish": meta.get("publish"),
            "gk_tarihi": _tr_date(gk.group(1)) if gk else None,
            "odeme_sekli": sekil.group(1).strip() if sekil else None,
            "taksitler": [t for t in taksitler if t["brut"] > 0]}


def dividend_payments(disclosures):
    """Her genel kurul icin en son yayimlanan bildirim gecerlidir (oneri -> karar -> guncelleme).
    Donus: odeme tarihli taksitler (brut TL/pay, kaynak ile)."""
    last = {}
    for d in sorted(disclosures, key=lambda d: d["idx"]):
        last[d.get("gk_tarihi") or d["idx"]] = d
    out = []
    for d in last.values():
        for t in d["taksitler"]:
            if t.get("odeme"):
                out.append(dict(t, kaynak={"rapor": d["idx"], "donem": d.get("gk_tarihi"), "birim": "TL/pay brüt"}))
    return sorted(out, key=lambda t: t["odeme"])


def dividend_ttm(payments, today):
    """Son 12 ay (odeme tarihi today-365 < t <= today). Aciklanmis ama odenmemis taksit girmez."""
    lo = (today - timedelta(days=365)).isoformat()
    hi = today.isoformat()
    paid = [p for p in payments if lo < p["odeme"] <= hi]
    past = [p for p in payments if p["odeme"] <= hi]
    return {"pencere": [lo, hi], "odeme_var": bool(paid),
            "brut_toplam": round(sum(p["brut"] for p in paid), 7),
            "odemeler": [{"odeme": p["odeme"], "brut": p["brut"]} for p in paid],
            "son_odeme": ({"odeme": past[-1]["odeme"], "brut": past[-1]["brut"]} if past else None),
            "duyurulan": [{"odeme": p["odeme"], "brut": p["brut"]} for p in payments if p["odeme"] > hi]}


# ----------------------------------------------------------------------------- turetilmis alanlar

def _v(rep, key, col="cur"):
    it = (rep.get("items") or {}).get(key)
    return None if not it else it.get(col)


def pct_change(cur, prev):
    if cur is None or prev is None or prev == 0:
        return None
    return round((cur - prev) / abs(prev) * 100.0, 2)


def _ebitda(rep, col="cur"):
    op, da = _v(rep, "operating_profit", col), _v(rep, "d_and_a", col)
    return None if op is None or da is None else op + da


def _equity_parent(rep, col="cur"):
    if rep["format"] == "banka":
        e = _v(rep, "equity_total", col)
        return None if e is None else e - (_v(rep, "nci", col) or 0)
    return _v(rep, "equity_parent", col)


def _borrowings(rep, col="cur"):
    parts = [_v(rep, k, col) for k in ("st_borrowings", "current_portion_lt_borrowings", "lt_borrowings")]
    return None if all(p is None for p in parts) else sum(p or 0 for p in parts)


_CHANGE_KEYS = {"sanayi": ("revenue", "gross_profit", "operating_profit", "ebitda", "net_income_parent", "equity_parent"),
                "banka": ("net_interest_income", "net_fees", "operating_income", "net_income_parent", "loans",
                          "deposits", "total_assets", "equity_parent")}
_Q_KEYS = {"sanayi": ("revenue", "operating_profit", "net_income_parent"),
           "banka": ("net_interest_income", "operating_income", "net_income_parent")}


def _pair(rep, key, cur="cur", prev="prev"):
    if key == "ebitda":
        return _ebitda(rep, cur), _ebitda(rep, prev)
    if key == "equity_parent":
        return _equity_parent(rep, cur), _equity_parent(rep, prev)
    return _v(rep, key, cur), _v(rep, key, prev)


def _kaynak(rep):
    return {"rapor": rep["idx"], "donem": rep["donem"], "birim": rep["unit"]}


def yearly_change(rep):
    """Yillik raporun kendi karsilastirmasi: {kalem: {pct, cur, prev, kaynak}}."""
    out = {}
    for key in _CHANGE_KEYS[rep["format"]]:
        cur, prev = _pair(rep, key)
        out[key] = {"pct": pct_change(cur, prev), "cur": cur, "prev": prev, "kaynak": _kaynak(rep)}
    return out


def quarter_change(rep):
    """Ara donem raporunun '3 Aylik' sutunlari; Q1'de kumulatif = ceyrek. Yillik raporda yok (Q4 turetilmez)."""
    if rep["period"] == 4:
        return None
    cols = ("cur", "prev") if rep["period"] == 1 else ("q_cur", "q_prev")
    out = {}
    for key in _Q_KEYS[rep["format"]]:
        cur, prev = _v(rep, key, cols[0]), _v(rep, key, cols[1])
        out[key] = {"pct": pct_change(cur, prev), "cur": cur, "prev": prev, "kaynak": _kaynak(rep)}
    return out


def net_debt(rep):
    """Net borc (kiralamalar dahil) = KV + UV'nin KV kismi + UV borclanmalar - nakit - KV finansal yatirimlar.
    FAVOK = esas faaliyet kari + nakit akistaki amortisman duzeltmesi. Ikisi ayni rapor, ayni birim."""
    if rep["format"] != "sanayi":
        return None
    b = _borrowings(rep)
    cash = _v(rep, "cash")
    if b is None or cash is None:
        return None
    fi = _v(rep, "current_financial_investments") or 0
    nd = b - cash - fi
    eb = _ebitda(rep)
    return {"net_borc": nd, "borclanma": b, "nakit": cash, "kv_finansal_yatirim": fi, "favok": eb,
            "net_borc_favok": round(nd / eb, 2) if eb and eb > 0 else None,
            "mult": rep["mult"], "kaynak": _kaynak(rep)}


def valuation_band(annual, closes):
    """Yil sonu piyasa degeri / o yilin raporundaki ana ortaklik net kari ve ozkaynagi.
    Piyasa degeri = yil sonu resmi kapanis x o raporun Odenmis Sermaye'si (1 TL nominal pay).
    closes: {"2025": {"date": "2025-12-31", "close": 184.4}}."""
    out = []
    for rep in sorted(annual, key=lambda r: r["fy"]):
        c = (closes or {}).get(str(rep["fy"]))
        cap = _v(rep, "issued_capital")
        if not c or not cap or not rep.get("mult"):
            continue
        shares = cap * rep["mult"]
        mcap = c["close"] * shares
        ni, eq = _v(rep, "net_income_parent"), _equity_parent(rep)
        out.append({"yil": rep["fy"], "tarih": c["date"], "kapanis": c["close"], "pay_adedi": shares,
                    "piyasa_degeri": round(mcap),
                    "fk": round(mcap / (ni * rep["mult"]), 2) if ni and ni > 0 else None,
                    "pd_dd": round(mcap / (eq * rep["mult"]), 2) if eq and eq > 0 else None,
                    "kaynak": _kaynak(rep)})
    return out


def derive(reports, dividends=None, closes=None):
    """Rapor kayitlari + temettu bildirimleri + yil sonu kapanislari -> turetilmis alanlar."""
    annual = [r for r in reports if r["period"] == 4]
    interim = sorted([r for r in reports if r["period"] != 4], key=lambda r: (r["fy"], r["period"]))
    latest_fy = max(annual, key=lambda r: r["fy"]) if annual else None
    latest = max(reports, key=lambda r: (r["fy"], r["period"])) if reports else None
    return {
        "yillik_degisim": {str(r["fy"]): yearly_change(r) for r in sorted(annual, key=lambda r: r["fy"])},
        "ceyreklik_degisim": {r["donem"]: quarter_change(r) for r in interim},
        "net_borc": net_debt(latest_fy) if latest_fy else None,
        "degerleme_bandi": valuation_band(annual, closes),
        "temettu_odemeleri": dividend_payments(dividends or []),
        "son_yillik": latest_fy["donem"] if latest_fy else None,
        "son_rapor": ({"donem": latest["donem"], "yayin": latest.get("publish")} if latest else None),
        "basis": latest["basis"] if latest else None,
        "format": latest["format"] if latest else None,
    }


def build_record(ticker, reports, dividends=None, closes=None, sector=None, generated_at=None):
    rec = {"schema_version": SCHEMA_VERSION, "ticker": ticker, "sector": sector,
           "generated_at": generated_at, "reports": sorted(reports, key=lambda r: (r["fy"], r["period"])),
           "dividends": dividends or []}
    rec["derived"] = derive(reports, dividends, closes)
    d = rec["derived"]
    rec["flags"] = {"banka": d["format"] == "banka", "sigorta": d["basis"] == "sigorta",
                    "yabanci_para": YABANCI_PARA.get(ticker)}
    return rec


# ----------------------------------------------------------------------------- servis (app.py ince baglanti)

_RECORD_CACHE = {}


def load_record(ticker, base_dir=None):
    """data/kap_fin/<T>.json (mtime onbellekli). Yok/bozuk/sema farkli -> None."""
    path = os.path.join(base_dir or DATA_DIR, "%s.json" % ticker)
    try:
        mtime = os.path.getmtime(path)
    except OSError:
        return None
    hit = _RECORD_CACHE.get(path)
    if hit and hit[0] == mtime:
        return hit[1]
    try:
        with open(path, encoding="utf-8") as f:
            rec = json.load(f)
        if rec.get("schema_version") != SCHEMA_VERSION or not rec.get("derived"):
            rec = None
    except (OSError, ValueError):
        rec = None
    _RECORD_CACHE[path] = (mtime, rec)
    return rec


def _strip(o):
    """API'ye giden kopyada ic dogrulama izi (kaynak) yok."""
    if isinstance(o, dict):
        return {k: _strip(v) for k, v in o.items() if k != "kaynak"}
    if isinstance(o, list):
        return [_strip(v) for v in o]
    return o


def apply_to_fundamentals(data, rec, price=None, today=None):
    """KAP kaydi varsa buyume, net borc, degerleme bandi ve temettu aciklanan veriden.
    Yahoo'nun revenue_growth/earnings_growth alanlari (tek ceyrek nominal) buyume diye
    kullanilmaz: kayit yoksa None. Diger Yahoo alanlari aynen kalir."""
    if not data:
        return data
    out = dict(data)
    out["revenue_growth"] = None
    out["earnings_growth"] = None
    if not rec:
        return out
    d = rec["derived"]
    today = today or date.today()
    fy = d.get("son_yillik")
    yc = d["yillik_degisim"].get(fy[:4]) if fy else None
    if yc:
        rev_key = "operating_income" if d.get("format") == "banka" else "revenue"
        out["revenue_growth"] = (yc.get(rev_key) or {}).get("pct")
        out["earnings_growth"] = (yc.get("net_income_parent") or {}).get("pct")
    nd = d.get("net_borc")
    if nd:
        out["net_debt_to_ebitda"] = nd["net_borc_favok"]
        mcap = (data.get("market_cap") or {}).get("value")
        if mcap and nd["favok"] and nd["favok"] > 0 and nd.get("mult"):
            out["ev_to_ebitda"] = round((mcap + nd["net_borc"] * nd["mult"]) / (nd["favok"] * nd["mult"]), 2)
    dv = dividend_ttm(d.get("temettu_odemeleri") or [], today)
    if price:
        out["dividend_yield"] = round(dv["brut_toplam"] / price * 100.0, 2)
    band = d.get("degerleme_bandi") or []
    out["kap"] = _strip({
        "schema_version": SCHEMA_VERSION,
        "basis": d.get("basis"),
        "flags": rec.get("flags"),
        "son_rapor": d.get("son_rapor"),
        "son_yillik": fy,
        "yillik_degisim": {y: {k: v["pct"] for k, v in c.items()} for y, c in d["yillik_degisim"].items()},
        "ceyreklik_degisim": {q: ({k: v["pct"] for k, v in c.items()} if c else None)
                              for q, c in d["ceyreklik_degisim"].items()},
        "net_borc": ({"net_borc_tl": nd["net_borc"] * nd["mult"] if nd.get("mult") else None,
                      "favok_tl": nd["favok"] * nd["mult"] if nd.get("mult") and nd["favok"] is not None else None,
                      "net_borc_favok": nd["net_borc_favok"], "donem": fy} if nd else None),
        "degerleme_bandi": [{k: b[k] for k in ("yil", "tarih", "kapanis", "fk", "pd_dd")} for b in band],
        "temettu": dv,
    })
    return out
