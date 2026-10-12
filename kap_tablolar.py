"""D-60 / C-59: finansal tablo sayfalari (/hisse/<T>/bilanco, /gelir-tablosu, /nakit-akis).

Kaynak: D-40a0 kaydi (data/kap_fin/<T>.json) hangi raporlarin kullanilacagini, donemini,
birimini ve muhasebe esasini soyler; kalemlerin tamami ayni raporlarin onbellekteki sayfasindan
(data/kap_fin/raw/<idx>.html.gz, yalniz bilanco / gelir / nakit akis tablolari) okunur.

Ilke (kanon docs/URUN-VE-TASARIM.md §3 "Aciklanan veri ilkesi"):
- Her sutun TEK raporun cari sutunudur; yuzde degisim AYNI raporun karsilastirma sutunundan.
  Farkli raporlarin tutarlari tek seride birlestirilmez, kendi enflasyon duzeltmemiz yok.
- Kalem sirasi ve adi raporun kendisinden (en yeni raporun sirasi; eski raporda olup yenisinde
  olmayan kalem, onceki komsusunun arkasina girer).
- Sutunun geldigi rapor yalniz ic nitelik olarak tasinir (`rapor`, `donem`); gorunen metinde
  kaynak adi yok. Birim ve para birimi tablo basliginda.
- Veri yoksa gizlenir: bos sutun / tum hucreleri bos ya da sifir olan satir gosterilmez.

Saf modul (ag yok, Flask yok, py3.9). Onbellek: data/kap_tablolar/<T>.json (ayristirilmis
rapor tablolari; rapor listesi degisince kendiliginden yenilenir). Toplu isitma:
    python3 kap_tablolar.py --isit [T1,T2,...]
"""
from __future__ import annotations

import gzip
import html as _html
import json
import os
import re
import sys
import tempfile

import kap_financials as kf

SCHEMA = 1
RAW_DIR = os.path.join(kf.DATA_DIR, "raw")
CACHE_DIR = os.path.join(os.path.dirname(kf.DATA_DIR), "kap_tablolar")

# URL parcasi -> (tablo kodu, gorunen ad, H1 isim tamlamasi)
TABLOLAR = {
    "bilanco": ("BS", "Bilanço", "bilançosu"),
    "gelir-tablosu": ("IS", "Gelir tablosu", "gelir tablosu"),
    "nakit-akis": ("CF", "Nakit akışı", "nakit akışı"),
}
SIRA = ("bilanco", "gelir-tablosu", "nakit-akis")
YIL_AZAMI = 5
CEYREK_AZAMI = 12

_AY_KISA = ("Oca", "Şub", "Mar", "Nis", "May", "Haz", "Tem", "Ağu", "Eyl", "Eki", "Kas", "Ara")
_AY_UZUN = ("Ocak", "Şubat", "Mart", "Nisan", "Mayıs", "Haziran", "Temmuz", "Ağustos", "Eylül",
            "Ekim", "Kasım", "Aralık")
_PARA_ADI = {"USD": "ABD doları", "EUR": "euro"}

# ----------------------------------------------------------------------------- sablonlar
# Sirket turune gore tablo kalibi: varsayilan (sade) gorunumde hangi derinlige kadar kalem
# gorunur, hangi kalemler her zaman gorunur, olgu seridinde hangi kalemler var.
# Kalemler XBRL eleman adiyla (raporun kendi kalemi; turetilmis tutar yok).
SABLONLAR = {
    "sanayi": {
        "BS": {"derinlik": 3, "olgu": (("ifrs-full_Assets", "Toplam varlıklar"),
                                        ("ifrs-full_Liabilities", "Toplam yükümlülükler"),
                                        ("ifrs-full_Equity", "Toplam özkaynaklar")),
               "olcek": "ilk"},
        "IS": {"derinlik": 2, "olgu": (("ifrs-full_Revenue", "Hasılat"),
                                        ("ifrs-full_GrossProfit", "Brüt kâr"),
                                        ("ifrs-full_ProfitLossFromOperatingActivities", "Esas faaliyet kârı"),
                                        ("ifrs-full_ProfitLoss", "Dönem kârı")),
               "olcek": "ilk", "cumle": (0, 2, 3),
               "her_zaman": ("ifrs-full_ProfitLossAttributableToOwnersOfParent",)},
        "CF": {"derinlik": 2, "olgu": (("ifrs-full_CashFlowsFromUsedInOperatingActivities", "İşletme faaliyetleri",
                                         "işletme faaliyetlerinden"),
                                        ("ifrs-full_CashFlowsFromUsedInInvestingActivities", "Yatırım faaliyetleri",
                                         "yatırım faaliyetlerinden"),
                                        ("ifrs-full_CashFlowsFromUsedInFinancingActivities", "Finansman faaliyetleri",
                                         "finansman faaliyetlerinden")),
               "olcek": "yon"},
    },
    "banka": {
        "BS": {"derinlik": 2, "olgu": (("ifrs-full_Assets", "Toplam varlıklar"),
                                        ("kap-fr_Loans", "Krediler"),
                                        ("kap-fr_Deposits", "Mevduat"),
                                        ("ifrs-full_Equity", "Özkaynaklar")),
               "olcek": "ilk", "her_zaman": ("kap-fr_Loans",)},
        "IS": {"derinlik": 2, "olgu": (("kap-fr_InterestIncomeOrExpense", "Net faiz geliri"),
                                        ("kap-fr_FeeAndCommissionIncomeOrExpenses", "Net ücret ve komisyon"),
                                        ("ifrs-full_ProfitLoss", "Dönem net kârı")),
               "olcek": "enbuyuk"},
        "CF": {"derinlik": 2, "olgu": (("kap-fr_CashFlowsFromUsedInBankingOperations", "Bankacılık faaliyetleri",
                                         "bankacılık faaliyetlerinden"),
                                        ("ifrs-full_CashFlowsFromUsedInInvestingActivities", "Yatırım faaliyetleri",
                                         "yatırım faaliyetlerinden"),
                                        ("ifrs-full_CashFlowsFromUsedInFinancingActivities", "Finansman faaliyetleri",
                                         "finansman faaliyetlerinden")),
               "olcek": "yon"},
    },
    "sigorta": {
        "BS": {"derinlik": 3, "olgu": (("ifrs-full_Assets", "Toplam varlıklar"),
                                        ("ifrs-full_Equity", "Özkaynaklar")),
               "olcek": "ilk"},
        "IS": {"derinlik": 2, "olgu": (("kap-fr_NonlifeTechnicalIncome", "Hayat dışı teknik gelir"),
                                        ("kap-fr_LifeTechnicalIncome", "Hayat teknik gelir"),
                                        ("kap-fr_PensionBusinessTechnicalIncome", "Emeklilik teknik gelir"),
                                        ("kap-fr_TechnicalPartBalance", "Genel teknik bölüm dengesi"),
                                        ("ifrs-full_ProfitLoss", "Dönem net kârı")),
               "olcek": "enbuyuk", "cumle": (3, 4)},
        "CF": {"derinlik": 2, "olgu": (("ifrs-full_CashFlowsFromUsedInOperatingActivities", "Esas faaliyetler",
                                         "esas faaliyetlerden"),
                                        ("ifrs-full_CashFlowsFromUsedInInvestingActivities", "Yatırım faaliyetleri",
                                         "yatırım faaliyetlerinden"),
                                        ("ifrs-full_CashFlowsFromUsedInFinancingActivities", "Finansman faaliyetleri",
                                         "finansman faaliyetlerinden")),
               "olcek": "yon"},
    },
}


# Toplam etiketi tasimayan ama tablonun omurgasi olan kalemler (kalin yazilir).
VURGU = frozenset((
    "ifrs-full_Revenue", "ifrs-full_GrossProfit", "ifrs-full_ProfitLossFromOperatingActivities",
    "ifrs-full_ProfitLossBeforeTax", "ifrs-full_ProfitLoss", "ifrs-full_ProfitLossAttributableToOwnersOfParent",
    "ifrs-full_Equity", "ifrs-full_EquityAttributableToOwnersOfParent",
    "ifrs-full_CashFlowsFromUsedInOperatingActivities", "ifrs-full_CashFlowsFromUsedInInvestingActivities",
    "ifrs-full_CashFlowsFromUsedInFinancingActivities", "ifrs-full_IncreaseDecreaseInCashAndCashEquivalents",
    "kap-fr_CashFlowsFromUsedInBankingOperations",
    "kap-fr_InterestIncomeOrExpense", "kap-fr_FeeAndCommissionIncomeOrExpenses",
    "kap-fr_GrossProfitLossFromOperatingActivitiesForBankingSector", "kap-fr_Loans", "kap-fr_Deposits",
))


def sablon_of(rec):
    """Kayit -> sanayi | banka | sigorta (GYO'nun rapor bicimi sanayiyle ayni)."""
    if not rec:
        return "sanayi"
    flags = rec.get("flags") or {}
    if flags.get("banka"):
        return "banka"
    if flags.get("sigorta") or "SİGORTA" in (rec.get("sector") or ""):
        return "sigorta"
    return "sanayi"


# ----------------------------------------------------------------------------- sayfa ayristirma

_ROW_RE_T = r'<tr class="%s-row-(\d+)([^"]*)">(.*?)(?=<tr class="%s-row-|</tbody></table>(?!</td>))'
_EL_RE = re.compile(r'taxonomy-field-name">([^<]*)</div>')
_LBLCLS_RE = re.compile(r'taxonomy-title-panel ([^"]*)"')
_TR_RE = re.compile(r'content-tr" style="display: block;">([^<]*)</div>')
_VAL_RE = re.compile(r'taxonomy-context-value col-order-class-(\d+)"><div><div class="[^"]*"'
                     r'(?: title="([^"]*)")?>([^<]*)</div>')
_UNIT_RE = re.compile(r'Sunum Para Birimi</td>\s*<td>([^<]*)</td>')
_KINDS = ("cur", "prev", "q_cur", "q_prev")


def _num(title, txt):
    src = title if title not in (None, "") else txt
    if src in (None, ""):
        return None
    s = src.strip()
    if title in (None, ""):
        s = s.replace(".", "").replace(",", ".")
    try:
        v = float(s)
    except ValueError:
        return None
    return 0.0 if v == 0 else v


def parse_statements(page_html):
    """Rapor sayfasi -> {"BS"|"IS"|"CF": {"birim", "basliklar", "satirlar"}}.

    satir = [anahtar, etiket, seviye, bayrak, cur, prev, q_cur, q_prev]
      anahtar: XBRL eleman adi (ayni tabloda ikinci kez geciyorsa "#2" eki)
      bayrak : "a" baslik (tutarsiz), "t" toplam, "" kalem
    Yalniz baslik satirlari ve en az bir sutunu dolu kalemler tutulur; tablo basligi (seviye 0) atilir."""
    t = kf.unesc(page_html)
    starts = list(kf._TABLE_RE.finditer(t))
    out = {}
    for i, m in enumerate(starts):
        role = m.group(1)
        st = kf.stmt_of(role)
        if st not in ("BS", "IS", "CF") or st in out:
            continue
        end = starts[i + 1].start() if i + 1 < len(starts) else len(t)
        seg = t[m.start():end]
        unit = _UNIT_RE.findall(t[max(0, m.start() - 3000):m.start()])
        cols = kf.classify_cols({"cols": {k: v for k, v in kf._parse_header(seg).items() if v}})
        idx = {kind: cols[kind][0] for kind in _KINDS if kind in cols}
        rows, seen = [], {}
        row_re = re.compile(_ROW_RE_T % (re.escape(role), re.escape(role)), re.S)
        for rm in row_re.finditer(seg):
            cls, body = rm.group(2), rm.group(3)
            el = _EL_RE.search(body)
            el = el.group(1).split("|")[0] if el else None
            lab = _TR_RE.search(body)
            lab = re.sub(r"\s+", " ", _html.unescape(lab.group(1))).strip() if lab else ""
            lvl = body.count('<span class="space">')
            if not el or not lab or lvl == 0:
                continue
            if "abstract-row" in cls:
                flag, vals = "a", [None] * 4
            else:
                lc = (_LBLCLS_RE.search(body) or [None, ""])[1]
                flag = "t" if ("TotalLabel" in lc or "otalLabel" in lc or "PeriodEndLabel" in lc
                               or "periodEndLabel" in lc) else ""
                found = {}
                for vm in _VAL_RE.finditer(body):
                    found[int(vm.group(1))] = _num(vm.group(2), vm.group(3))
                vals = [found.get(idx[k]) if k in idx else None for k in _KINDS]
                if all(v is None for v in vals):
                    continue
            n = seen.get(el, 0) + 1
            seen[el] = n
            rows.append([el if n == 1 else "%s#%d" % (el, n), lab, lvl, flag] + vals)
        out[st] = {"birim": unit[-1].strip() if unit else None,
                   "basliklar": {k: cols[k][1] for k in _KINDS if k in cols},
                   "satirlar": rows}
    return out


# ----------------------------------------------------------------------------- onbellek

_MEM = {}


def _imza(rec):
    return [SCHEMA] + sorted(int(r["idx"]) for r in (rec.get("reports") or []))


def _read_raw(idx, raw_dir):
    path = os.path.join(raw_dir, "%s.html.gz" % idx)
    try:
        with gzip.open(path, "rt", encoding="utf-8") as f:
            return f.read()
    except (OSError, EOFError, ValueError):
        return None


def _atomic_write_json(path, obj):
    d = os.path.dirname(path)
    try:
        os.makedirs(d, exist_ok=True)
        fd, tmp = tempfile.mkstemp(dir=d, prefix=".tmp-", suffix=".json.gz")
    except OSError:
        return
    try:
        body = json.dumps(obj, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
        with os.fdopen(fd, "wb") as f:
            f.write(gzip.compress(body, 6))
        os.replace(tmp, path)
    except OSError:
        try:
            os.unlink(tmp)
        except OSError:
            pass


def load_parsed(ticker, rec, raw_dir=None, cache_dir=None, write=True):
    """Kaydin raporlari icin ayristirilmis tablolar: {str(idx): {"BS":..,"IS":..,"CF":..} | None}.
    Onbellek (cache_dir/<T>.json) rapor listesi ayniysa okunur; degilse ham sayfalardan kurulur."""
    if not rec or not rec.get("reports"):
        return None
    raw_dir = raw_dir or RAW_DIR
    cache_dir = cache_dir or CACHE_DIR
    path = os.path.join(cache_dir, "%s.json.gz" % ticker)
    sig = _imza(rec)
    try:
        mtime = os.path.getmtime(path)
    except OSError:
        mtime = None
    hit = _MEM.get(path)
    if hit and hit[0] == mtime and hit[1].get("imza") == sig:
        return hit[1]["raporlar"]
    doc = None
    if mtime is not None:
        try:
            with gzip.open(path, "rt", encoding="utf-8") as f:
                doc = json.load(f)
        except (OSError, EOFError, ValueError):
            doc = None
    if not doc or doc.get("imza") != sig:
        raporlar = {}
        for r in rec["reports"]:
            h = _read_raw(r["idx"], raw_dir)
            try:
                raporlar[str(r["idx"])] = parse_statements(h) if h else None
            except Exception:  # bozuk sayfa: o sutun gosterilmez
                raporlar[str(r["idx"])] = None
        doc = {"imza": sig, "ticker": ticker, "raporlar": raporlar}
        if write:
            _atomic_write_json(path, doc)
            try:
                mtime = os.path.getmtime(path)
            except OSError:
                mtime = None
    _MEM[path] = (mtime, doc)
    return doc["raporlar"]


def has_tables(rec, raw_dir=None):
    """Hisse sayfasindaki baglanti icin ucuz kontrol: en az bir raporun sayfasi onbellekte mi."""
    if not rec or not rec.get("reports"):
        return False
    raw_dir = raw_dir or RAW_DIR
    return any(os.path.exists(os.path.join(raw_dir, "%s.html.gz" % r["idx"])) for r in rec["reports"])


# ----------------------------------------------------------------------------- bicim (kanon §2.10)

def _fmt(x, nd=0):
    s = ("{:,.%df}" % nd).format(abs(x)).replace(",", "_").replace(".", ",").replace("_", ".")
    return ("−" if x < 0 and s.strip("0,.") else "") + s


def _pct_text(p):
    if p is None:
        return None
    nd = 0 if abs(p) >= 100 else 1
    r = round(p, nd)
    if r == 0:
        return "%" + _fmt(0.0, nd)
    return ("+" if r > 0 else "−") + "%" + _fmt(abs(r), nd)


_NB = "\u00a0"  # sayi ile olcek/simge ayni satirda kalir ("1,02 T ₺" satir sonunda bolunmez)


def para_kisa(tl):
    """Olgu metni: '1,99 T ₺' / '911 Mrd ₺' / '86,0 Mrd ₺' / '742 Mn ₺' (bosluklar bolunmez)."""
    a = abs(tl)
    if a >= 1e12:
        return _fmt(tl / 1e12, 2) + _NB + "T" + _NB + "₺"
    if a >= 1e9:
        return _fmt(tl / 1e9, 1 if a < 1e11 else 0) + _NB + "Mrd" + _NB + "₺"
    if a >= 1e6:
        return _fmt(tl / 1e6, 0) + _NB + "Mn" + _NB + "₺"
    return _fmt(tl, 0) + _NB + "₺"


def _hucre(x):
    """Tablo hucresi (olcekli tutar): tam sayi; 1'in altindaki sifir olmayan tutar tek ondalikla."""
    if x != 0 and abs(x) < 1 and round(abs(x), 1) >= 0.1:
        return _fmt(x, 1)
    return _fmt(x, 0)


def degisim(cur, prev):
    """Ayni raporun iki sutunu -> yuzde. Iki deger ayni isaretliyse buyukluk degisimi
    (gider -100 -> -120 = +%20); isaret degismisse ya da onceki 0 ise yuzde yok."""
    if cur is None or prev is None or prev == 0:
        return None
    if (cur < 0) != (prev < 0) and cur != 0:
        return None
    return round((abs(cur) - abs(prev)) / abs(prev) * 100.0, 2)


# ----------------------------------------------------------------------------- donem etiketleri

_DATE_RE = re.compile(r"(\d{2})\.(\d{2})\.(\d{4})")


def _dates(header):
    return [(int(y), int(m), int(d)) for d, m, y in _DATE_RE.findall(header or "")]


def _tarih_uzun(dt):
    return "%d %s %d" % (dt[2], _AY_UZUN[dt[1] - 1], dt[0])


def _rapor_donemi(stmts, kind="cur"):
    """Raporun akis tablosundan (gelir, yoksa nakit akis) (baslangic, bitis) tarihleri."""
    for st in ("IS", "CF"):
        h = ((stmts.get(st) or {}).get("basliklar") or {}).get(kind)
        ds = _dates(h)
        if len(ds) >= 2:
            return ds[0], ds[-1]
    return None, None


def _yil_etiketi(bas, bit, fy):
    if bas and bit and bas[1] == 1 and bit[1] == 12 and bas[0] == bit[0]:
        return str(bit[0]), str(bit[0])
    if bas and bit:
        return "%d/%02d" % (bas[0], bit[0] % 100), "%s %d – %s %d" % (_AY_UZUN[bas[1] - 1], bas[0],
                                                                       _AY_UZUN[bit[1] - 1], bit[0])
    return str(fy), str(fy)


def _aralik(bas, bit):
    """('Nis–Haz', '2026', 'Nisan–Haziran 2026')."""
    if bas[0] == bit[0]:
        return ("%s–%s" % (_AY_KISA[bas[1] - 1], _AY_KISA[bit[1] - 1]), str(bit[0]),
                "%s–%s %d" % (_AY_UZUN[bas[1] - 1], _AY_UZUN[bit[1] - 1], bit[0]))
    return ("%s %02d–%s" % (_AY_KISA[bas[1] - 1], bas[0] % 100, _AY_KISA[bit[1] - 1]), str(bit[0]),
            "%s %d – %s %d" % (_AY_UZUN[bas[1] - 1], bas[0], _AY_UZUN[bit[1] - 1], bit[0]))


# ----------------------------------------------------------------------------- muhasebe esasi

def _esas(rep, stmts):
    """Sutunun esasi: enflasyon | cevrilmis | nominal. Banka ve sigortada raporun kendi
    'net parasal pozisyon' satiri doluysa enflasyon duzeltmeli sayilir."""
    b = rep.get("basis")
    if b == "tms29":
        return "enflasyon"
    if b == "yabanci_para":
        return "cevrilmis"
    if b in ("banka", "sigorta"):
        for r in ((stmts.get("IS") or {}).get("satirlar") or []):
            if r[0] == "ifrs-full_GainsLossesOnNetMonetaryPosition" and any(v for v in r[4:6] if v):
                return "enflasyon"
    return "nominal"


ESAS_ETIKET = {"enflasyon": "Enflasyon düzeltmeli", "cevrilmis": "TL'ye çevrilmiş", "nominal": "Nominal"}


def _esas_notu(esas, para_birimi=None):
    if esas == "enflasyon":
        return "enflasyon düzeltmeli; her sütun kendi rapor tarihinin parasıyla"
    if esas == "cevrilmis":
        ad = _PARA_ADI.get(para_birimi or "", para_birimi)
        return ("işlevsel para birimi %s, TL'ye çevrilmiş" % ad) if ad else "TL'ye çevrilmiş"
    return "nominal"


# ----------------------------------------------------------------------------- gorunumler

def _sutun_adaylari(rec, parsed, st, tur):
    """Rapor (yeni -> eski) -> [(rep, stmts, cur_kind, prev_kind)]."""
    out = []
    reps = sorted(rec.get("reports") or [], key=lambda r: (r["fy"], r["period"]), reverse=True)
    for rep in reps:
        stmts = (parsed or {}).get(str(rep["idx"]))
        tb = (stmts or {}).get(st)
        if not tb or not tb.get("satirlar"):
            continue
        hdr = tb.get("basliklar") or {}
        if tur == "yillik":
            if rep["period"] != 4 or "cur" not in hdr:
                continue
            kinds = ("cur", "prev")
        elif st == "IS":
            if rep["period"] == 4:
                continue
            kinds = ("cur", "prev") if rep["period"] == 1 else ("q_cur", "q_prev")
            if kinds[0] not in hdr:
                continue
        else:
            if "cur" not in hdr:
                continue
            kinds = ("cur", "prev")
        out.append((rep, stmts, kinds[0], kinds[1]))
        if len(out) >= (YIL_AZAMI if tur == "yillik" else CEYREK_AZAMI):
            break
    return out


def _sutun_etiketi(rep, stmts, st, tur, kind):
    """{'ust','alt','tam'}: masaustu tek satir 'tam' degil 'ust alt'; telefonda iki satir."""
    tb = stmts[st]
    if tur == "yillik":
        bas, bit = _rapor_donemi(stmts, "cur")
        kisa, tam = _yil_etiketi(bas, bit, rep["fy"])
        return {"ust": kisa, "alt": "", "tam": tam}
    hdr = (tb.get("basliklar") or {}).get(kind)
    ds = _dates(hdr)
    if st == "BS" and ds:
        d = ds[-1]
        return {"ust": "%d %s" % (d[2], _AY_KISA[d[1] - 1]), "alt": str(d[0]), "tam": _tarih_uzun(d)}
    if len(ds) >= 2:
        u, a, tam = _aralik(ds[0], ds[-1])
        return {"ust": u, "alt": a, "tam": tam}
    return {"ust": rep["donem"], "alt": "", "tam": rep["donem"]}


def _karsilastirma(stmts, st, kind):
    ds = _dates(((stmts.get(st) or {}).get("basliklar") or {}).get(kind))
    return _tarih_uzun(ds[-1]) if ds else None


def _birlestir(listeler):
    """Yeni -> eski kalem listeleri; ilk listenin sirasi esas, eksik anahtar onceki komsusunun arkasina."""
    order, keys = [], []
    for rows in listeler:
        prev_key = None
        for r in rows:
            k = r[0]
            if k not in keys:
                at = (keys.index(prev_key) + 1) if prev_key is not None else 0
                order.insert(at, r)
                keys.insert(at, k)
            prev_key = k
    return order


def _olcek(maks_tl):
    if maks_tl >= 1e9:
        return 1e6, "Milyon"
    return 1e3, "Bin"


def gorunum(rec, parsed, slug, tur):
    """Tek tablo gorunumu (yillik | ceyreklik) ya da None (gosterilecek sutun yok)."""
    st = TABLOLAR[slug][0]
    sab = SABLONLAR[sablon_of(rec)][st]
    aday = _sutun_adaylari(rec, parsed, st, tur)
    if not aday:
        return None
    para = aday[0][0].get("currency") or "TL"
    aday = [a for a in aday if (a[0].get("currency") or "TL") == para and a[0].get("mult")]
    ki = {k: i for i, k in enumerate(_KINDS)}
    sutunlar, degerler = [], []
    for rep, stmts, ck, pk in aday:
        tb = stmts[st]
        m = rep["mult"]
        vals = {}
        for r in tb["satirlar"]:
            if r[3] == "a":
                continue
            c, p = r[4 + ki[ck]], r[4 + ki[pk]]
            if c is None and p is None:
                continue
            vals[r[0]] = (None if c is None else c * m, degisim(c, p))
        esas = _esas(rep, stmts)
        sutunlar.append({"rapor": rep["idx"], "donem": rep["donem"], "esas": esas,
                         "etiket": _sutun_etiketi(rep, stmts, st, tur, ck),
                         "karsilastirma": _karsilastirma(stmts, st, pk)})
        degerler.append(vals)
    satirlar_ham = _birlestir([stmts[st]["satirlar"] for _, stmts, _, _ in aday])
    maks = max([abs(v[0]) for vals in degerler for v in vals.values() if v[0] is not None] or [0])
    bolen, olcek_adi = _olcek(maks)
    her_zaman = set(sab.get("her_zaman") or ())
    olgu_k = {o[0] for o in sab.get("olgu") or ()}
    satirlar = []
    for r in satirlar_ham:
        key, lab, lvl, flag = r[0], r[1], r[2], r[3]
        if flag == "a":
            satirlar.append({"anahtar": key, "etiket": lab, "seviye": lvl, "baslik": True,
                             "toplam": False, "detay": lvl > sab["derinlik"], "hucreler": []})
            continue
        hucre, dolu = [], False
        for vals in degerler:
            v = vals.get(key)
            if not v or v[0] is None:
                hucre.append(None)
                continue
            x = v[0] / bolen
            dolu = dolu or v[0] != 0
            hucre.append({"metin": _hucre(x), "degisim": _pct_text(v[1]), "deger": round(x, 3)})
        if not dolu:
            continue
        satirlar.append({"anahtar": key, "etiket": lab, "seviye": lvl, "baslik": False,
                         "toplam": flag == "t" or key in VURGU,
                         "detay": (lvl > sab["derinlik"] and flag != "t" and key not in her_zaman
                                   and key not in olgu_k),
                         "hucreler": hucre})
    satirlar = _baslik_detayi(_ara_toplam_ayikla(_bos_baslik_ayikla(satirlar)))
    if not satirlar:
        return None
    taban = min(s["seviye"] for s in satirlar)
    for s in satirlar:
        s["girinti"] = min(s["seviye"] - taban, 5)
    esaslar = []
    for i, s in enumerate(sutunlar):
        if esaslar and esaslar[-1]["esas"] == s["esas"]:
            esaslar[-1]["kapsam"] += 1
        else:
            esaslar.append({"esas": s["esas"], "etiket": ESAS_ETIKET[s["esas"]], "kapsam": 1})
    tek_esas = esaslar[0]["esas"] if len(esaslar) == 1 else None
    birim = "%s %s" % (olcek_adi, para)
    yab = (rec.get("flags") or {}).get("yabanci_para")
    return {
        "tur": tur, "sutunlar": sutunlar, "satirlar": satirlar,
        "birim": birim,
        "birim_notu": birim + (" · " + _esas_notu(tek_esas, yab) if tek_esas else
                               (" · enflasyon düzeltmeli sütunlar kendi rapor tarihinin parasıyla"
                                if any(g["esas"] == "enflasyon" for g in esaslar) else "")),
        "esas_gruplari": esaslar if len(esaslar) > 1 else [],
        "degisim_notu": _degisim_notu(st, tur),
        "detay_sayisi": sum(1 for s in satirlar if s["detay"] and not s["baslik"]),
    }


def _bos_baslik_ayikla(satirlar):
    """Arkasinda (daha derin seviyede) dolu kalem kalmayan basliklari at."""
    out = []
    for i, s in enumerate(satirlar):
        if s["baslik"]:
            ok = False
            for n in satirlar[i + 1:]:
                if n["seviye"] <= s["seviye"]:
                    break
                if not n["baslik"]:
                    ok = True
                    break
            if not ok:
                continue
        out.append(s)
    return out


def _baslik_detayi(satirlar):
    """Sade gorunumde altinda gorunen kalem kalmayan baslik da ayrintidir (bos baslik gosterilmez)."""
    for i, s in enumerate(satirlar):
        if not s["baslik"]:
            continue
        gorunen = False
        for n in satirlar[i + 1:]:
            if n["seviye"] <= s["seviye"]:
                break
            if not n["baslik"] and not n["detay"]:
                gorunen = True
                break
        s["detay"] = s["detay"] or not gorunen
    return satirlar


def _ara_toplam_ayikla(satirlar):
    """'ARA TOPLAM' satiri hemen arkasindaki toplamla her sutunda aynıysa tekrar sayilir, atilir."""
    out = []
    for i, s in enumerate(satirlar):
        if s["etiket"].strip().upper() == "ARA TOPLAM":
            nxt = next((n for n in satirlar[i + 1:] if not n["baslik"]), None)
            if nxt and [h and h["metin"] for h in s["hucreler"]] == [h and h["metin"] for h in nxt["hucreler"]]:
                continue
        out.append(s)
    return out


def _degisim_notu(st, tur):
    if st == "BS":
        return "Rakamların altındaki yüzde, aynı raporun önceki yıl sonu sütununa göre değişimdir."
    if tur == "yillik":
        return "Rakamların altındaki yüzde, aynı raporun önceki yıl sütununa göre değişimdir."
    if st == "IS":
        return "Rakamların altındaki yüzde, aynı raporda önceki yılın aynı çeyreğine göre değişimdir."
    return "Rakamların altındaki yüzde, aynı raporda önceki yılın aynı dönemine göre değişimdir."


# ----------------------------------------------------------------------------- olgular

def _zarar_etiketi(etiket):
    """Eksi kar kalemi zarar diye yazilir: 'Dönem kârı' -> 'Dönem zararı', 'Brüt kâr' -> 'Brüt zarar'."""
    return etiket.replace("kârı", "zararı").replace("kâr", "zarar")


def _bas_harf_kucuk(s):
    if len(s) > 1 and s[1].isupper():  # kisaltma ile baslayan ad
        return s
    return _tr_lower(s[0]) + s[1:]


def olgular(rec, parsed, slug):
    """Olgu seridi + giris cumlesi (tek rapordan; bilancoda en son rapor, akislarda son yillik)."""
    st = TABLOLAR[slug][0]
    sab = SABLONLAR[sablon_of(rec)][st]
    aday = _sutun_adaylari(rec, parsed, st, "ceyreklik" if st == "BS" else "yillik")
    if not aday:
        return None
    rep, stmts, ck, pk = aday[0]
    ki = {k: i for i, k in enumerate(_KINDS)}
    rows = {r[0]: r for r in stmts[st]["satirlar"] if r[3] != "a"}
    m = rep.get("mult") or 1
    kalemler = []
    for o in sab["olgu"]:
        el, etiket = o[0], o[1]
        r = rows.get(el)
        if not r or r[4 + ki[ck]] is None:
            continue
        c, p = r[4 + ki[ck]], r[4 + ki[pk]]
        tl = c * m
        akis = st == "CF"
        zarar = tl < 0 and not akis and "kâr" in etiket
        kalemler.append({"anahtar": el, "etiket": _zarar_etiketi(etiket) if zarar else etiket,
                         "cumle_ad": o[2] if len(o) > 2 else None,
                         "tl": tl, "metin": para_kisa(abs(tl) if zarar else tl),
                         "degisim": _pct_text(degisim(c, p)), "eksi": tl < 0})
    if sab["olcek"] == "enbuyuk":
        # seritte yalniz anlamli buyuklukler (tablo tam kalir): sifir ve en buyugun binde 5'inden kucuk kalem yok
        enb = max([abs(k["tl"]) for k in kalemler] or [0])
        kalemler = [k for k in kalemler if k["tl"] != 0 and abs(k["tl"]) >= 0.005 * enb]
    if not kalemler:
        return None
    if sab["olcek"] == "ilk":
        ref = abs(kalemler[0]["tl"]) or 1
    else:
        ref = max(abs(k["tl"]) for k in kalemler) or 1
    for k in kalemler:
        k["pay"] = round(min(100.0, abs(k["tl"]) / ref * 100.0), 1)
    if st == "BS":
        ds = _dates((stmts[st].get("basliklar") or {}).get(ck))
        donem = _tarih_uzun(ds[-1]) if ds else rep["donem"]
        bas = "%s itibarıyla" % donem
    else:
        bas_d, bit_d = _rapor_donemi(stmts, ck)
        kisa, tam = _yil_etiketi(bas_d, bit_d, rep["fy"])
        donem = kisa
        bas = ("%s yılında" % kisa) if kisa.isdigit() else ("%s döneminde" % tam)
    secim = kalemler[:3]
    if sab.get("cumle"):
        secim = [k for k in kalemler if k["anahtar"] in {sab["olgu"][i][0] for i in sab["cumle"]}] or secim
    return {"donem": donem, "rapor": rep["idx"], "kalemler": kalemler, "olcek": sab["olcek"],
            "cumle": _cumle(st, bas, secim)}


def _cumle(st, bas, kalemler):
    """Betimleyici tek cumle (yargi yok): donem + rakamlar; ilk kalemde ayni raporun yuzdesi."""
    bas = bas[0].upper() + bas[1:]
    parca = []
    if st == "CF":
        for k in kalemler:
            yon = "nakit çıkışı" if k["eksi"] else "nakit girişi"
            parca.append("%s %s %s" % (k["cumle_ad"] or _bas_harf_kucuk(k["etiket"]), para_kisa(abs(k["tl"])), yon))
        return "%s %s oldu." % (bas, ", ".join(parca))
    for i, k in enumerate(kalemler):
        s = "%s %s" % (_bas_harf_kucuk(k["etiket"]), k["metin"])
        if i == 0 and k["degisim"]:
            s += " (%s %s)" % ("önceki yıl sonuna göre" if st == "BS" else "önceki yıla göre", k["degisim"])
        parca.append(s)
    return "%s %s%s." % (bas, ", ".join(parca), "" if st == "BS" else " oldu")


# ----------------------------------------------------------------------------- Turkce ek

_UNLU = "aeıioöuü"
_HARF_OKUNUS = {"A": "a", "B": "be", "C": "ce", "Ç": "çe", "D": "de", "E": "e", "F": "fe", "G": "ge",
                "Ğ": "ge", "H": "he", "I": "ı", "İ": "i", "J": "je", "K": "ke", "L": "le", "M": "me",
                "N": "ne", "O": "o", "Ö": "ö", "P": "pe", "R": "re", "S": "se", "Ş": "şe", "T": "te",
                "U": "u", "Ü": "ü", "V": "ve", "W": "ve", "X": "iks", "Y": "ye", "Z": "ze", "Q": "kü"}


def _tr_lower(s):
    return s.replace("I", "ı").replace("İ", "i").lower()


def _okunur(w):
    """Buyuk harfli sozcuk sozcuk gibi mi okunur (TÜPRAŞ, BİM) yoksa harf harf mi (THY, BBVA, THYAO)?
    Unlu var, iki unsuzle baslamiyor ve ucten uzun unsuz dizisi yok."""
    lw = _tr_lower(w)
    if not any(c in _UNLU for c in lw) or (len(lw) > 1 and lw[0] not in _UNLU and lw[1] not in _UNLU):
        return False
    run = 0
    for c in lw:
        run = 0 if c in _UNLU else run + 1
        if run >= 3:
            return False
    return True


def iyelik(ad):
    """Tamlayan eki (kesme isaretiyle): "Türk Hava Yolları" -> "'nın", "Garanti BBVA" -> "'nın",
    "THY" -> "'nin", "TÜPRAŞ" -> "'ın". Harf harf okunan kisaltmada son harfin okunusu esas alinir."""
    w = (ad or "").strip().split(" ")[-1] if ad else ""
    w = re.sub(r"[^\wÇĞİÖŞÜçğıöşü]", "", w)
    if not w:
        return "'nin"
    if len(w) > 1 and w == w.upper() and any(c.isalpha() for c in w) and not _okunur(w):
        ses = _HARF_OKUNUS.get(w[-1], _tr_lower(w[-1]))
    else:
        ses = _tr_lower(w)
    unluler = [c for c in ses if c in _UNLU]
    son = unluler[-1] if unluler else "e"
    ek = {"a": "ın", "ı": "ın", "e": "in", "i": "in", "o": "un", "u": "un", "ö": "ün", "ü": "ün"}[son]
    return "'" + ("n" + ek if ses[-1] in _UNLU else ek)


# ----------------------------------------------------------------------------- sayfa baglami

def baglantilar(ticker, rec, raw_dir=None):
    """Hisse sayfasi Temel sekmesi: [{slug, ad, href}] (tablolar yoksa bos)."""
    if not has_tables(rec, raw_dir):
        return []
    return [{"slug": s, "ad": TABLOLAR[s][1], "href": "/hisse/%s/%s" % (ticker, s)} for s in SIRA]


def sayfa(ticker, slug, rec, name=None, raw_dir=None, cache_dir=None, write=True):
    """/hisse/<T>/<slug> sablon baglami ya da None (404)."""
    if slug not in TABLOLAR or not rec:
        return None
    parsed = load_parsed(ticker, rec, raw_dir=raw_dir, cache_dir=cache_dir, write=write)
    if not parsed:
        return None
    yil = gorunum(rec, parsed, slug, "yillik")
    ceyrek = gorunum(rec, parsed, slug, "ceyreklik")
    if not yil and not ceyrek:
        return None
    st, baslik, tamlama = TABLOLAR[slug]
    ad = name or ticker
    ol = olgular(rec, parsed, slug)
    son = max(rec["reports"], key=lambda r: (r["fy"], r["period"]))
    yayin = (son.get("publish") or "")[:10] or None
    return {
        "ticker": ticker, "ad": ad, "slug": slug, "baslik": baslik, "sablon": sablon_of(rec),
        "soru": "%s%s %s nasıl?" % (ad, iyelik(ad), tamlama),
        "olgu": ol,
        "yillik": yil, "ceyreklik": ceyrek,
        "varsayilan": "yillik" if yil else "ceyreklik",
        "sekmeler": [{"slug": s, "ad": TABLOLAR[s][1], "href": "/hisse/%s/%s" % (ticker, s),
                      "aktif": s == slug} for s in SIRA],
        "son_yayin": yayin,
        "kanonik": "https://borsapusula.com/hisse/%s/%s" % (ticker, slug),
    }


def sitemap_girdileri(tickers, load_record=None, raw_dir=None):
    """[{loc, lastmod}] -- tablosu olan her hisse icin 3 sayfa (son rapor yayin gunu)."""
    load_record = load_record or kf.load_record
    out = []
    for t in tickers:
        rec = load_record(t)
        if not has_tables(rec, raw_dir):
            continue
        son = max(rec["reports"], key=lambda r: (r["fy"], r["period"]))
        lm = (son.get("publish") or "")[:10] or None
        for s in SIRA:
            out.append({"loc": "/hisse/%s/%s" % (t, s), "lastmod": lm})
    return out


def isit(tickers=None, base_dir=None, raw_dir=None, cache_dir=None, log=print):
    """Onbellegi toplu kur (deploy sonrasi istege bagli; ag yok)."""
    base = base_dir or kf.DATA_DIR
    if not tickers:
        tickers = sorted(f[:-5] for f in os.listdir(base) if f.endswith(".json") and f[:-5].isupper())
    n = 0
    for t in tickers:
        rec = kf.load_record(t, base_dir=base)
        if rec and load_parsed(t, rec, raw_dir=raw_dir, cache_dir=cache_dir):
            n += 1
    log("kap_tablolar: %d / %d hisse hazır" % (n, len(tickers)))
    return n


if __name__ == "__main__":  # pragma: no cover
    if len(sys.argv) > 1 and sys.argv[1] == "--isit":
        isit(sys.argv[2].split(",") if len(sys.argv) > 2 else None)
    else:
        print(__doc__)
