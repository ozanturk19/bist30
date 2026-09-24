"""D-45: KAP bildirim akisi -- analiz evreninin TEK kaynagi.

Ne yapar
- KAP'in `byCriteria` listesindeki ham kaydi bizim kaydimiza cevirir (`normalize`):
  sinif etiketi, rutin grubu, filtre anahtari, temiz baslik, hisse eslemesi.
- Uye esleme (C-M10 hatasi): kayit YAYINLAYANIN kodlarina (`stockCodes`) gore hisseye
  baglanir. Baska bir uyenin bildiriminde "ilgili sirket" (`relatedStocks`) olarak gecmek
  hisseyi bildirimin sahibi yapmaz (AHGAZ/ENERY listesindeki Dunya Katilim Bankasi sube
  bildirimleri). Istisna: yalniz sirketin KENDISI HAKKINDA olan ucuncu taraf bildirimleri
  (kredi notu, pay alim satim bildirimi, pay alim teklifi) ve borsa duyurulari (rutin).
- Kodlama: KAP ozetinde kesme isareti yerine gelen "?" ("A.S.?nin") ve sondaki "\\n" temizlenir.
- Onem orani: parasal bildirimde tutar / son yillik hasilat (D-40a0 `data/kap_fin/<T>.json`,
  aciklanan veri). Tutar kurallarla okunur; belirsizse None (tahmin yok).
- Tek cumle ozet kurallarla kurulur; AI yok (kanon §3: sirket olgusu AI ile yazilmaz).
- Depo: `data/kap_feed/items/YYYY-MM.json` (aylik parca, atomik yazim) +
  `data/kap_feed/docs/<id>.json` (bildirim metni, bir kez cekilir; bildirim degismez).

Kaynak izi (KAP bildirim no, yayinlayan unvan) yalniz iceride tutulur; API ve sayfa dis
baglanti ve kaynak etiketi tasimaz (kanon §2.8).

Ag erisimi yalniz `KapClient` icinde (>= 2 sn aralik, 429/5xx'te durur). Saf fonksiyonlar
yerel testte agsiz calisir. Python 3.9 uyumlu.
"""
from __future__ import annotations

import html as _html
import json
import os
import re
import tempfile
import time
from datetime import date, datetime, timedelta

SCHEMA_VERSION = 1
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data", "kap_feed")
KEEP_DAYS = 400          # hisse listesi en az 1 yil (C-M10: eskiden ~90 gun)
DUY_KEEP_DAYS = 30       # borsa duyurulari yalniz "gizlenen rutin" sayimi icin
KAP_LIST_URL = "https://www.kap.org.tr/tr/api/disclosure/members/byCriteria"
KAP_PAGE_URL = "https://www.kap.org.tr/tr/Bildirim/%s"
TCMB_URL = "https://www.tcmb.gov.tr/kurlar/%s/%s.xml"
POLL_CLASSES = ("ODA", "FR", "DG", "DUY")

_TR_MONTHS = ("Ocak", "Şubat", "Mart", "Nisan", "Mayıs", "Haziran", "Temmuz", "Ağustos",
              "Eylül", "Ekim", "Kasım", "Aralık")
_TR_DAYS = ("Pazartesi", "Salı", "Çarşamba", "Perşembe", "Cuma", "Cumartesi", "Pazar")

# ----------------------------------------------------------------------------- metin temizligi

# "A.Ş.?nin", "2?nci", "Türkiye?de": kesme isareti KAP ozetinde "?" olarak geliyor.
# Soru isaretinden sonra bosluk/son gelir; kesme isaretinden sonra ek (kucuk harf) gelir.
_APOS_RE = re.compile(r"(?<=[0-9A-Za-zÇĞİÖŞÜÂÎÛçğıöşüâîû.)])\?(?=[a-zçğıöşüâîû])")
_WS_RE = re.compile(r"\s+")


def clean_text(s):
    """KAP metni -> tek satir, temiz. None -> ''."""
    if not s:
        return ""
    s = _html.unescape(str(s))
    s = _APOS_RE.sub("'", s)
    s = _WS_RE.sub(" ", s).strip()
    return s.rstrip(" ,;")


def clean_title(s):
    """Bildirim basligi: temiz metin + 'Hk.' kisaltmasi acilir."""
    s = clean_text(s)
    s = re.sub(r"\s+(?:Hk\.?|hk\.?|Hk\.da|hk\.da|Hak\.)$", " hakkında", s)
    return s


def codes(s):
    """'GARAN, TGB' -> ['GARAN', 'TGB']"""
    return [c.strip().upper() for c in (s or "").split(",") if c.strip()]


# ----------------------------------------------------------------------------- sinif / rutin

SUBJECT_LABEL = {
    "Finansal Rapor": "Finansal rapor",
    "Kar Payı Dağıtım İşlemlerine İlişkin Bildirim": "Temettü",
    "Yeni İş İlişkisi": "Yeni iş ilişkisi",
    "Kredi Derecelendirmesi": "Kredi notu",
    "İhale Süreci / Sonucu": "İhale",
    "Finansal Duran Varlık Edinimi": "Varlık edinimi",
    "Finansal Duran Varlık Satışı": "Varlık satışı",
    "Maddi Duran Varlık Alımı": "Varlık edinimi",
    "Maddi Duran Varlık Satımı": "Varlık satışı",
    "Sermaye Artırımı - Azaltımı İşlemlerine İlişkin Bildirim": "Sermaye artırımı",
    "Birleşme İşlemlerine İlişkin Bildirim": "Birleşme",
    "Bölünme İşlemlerine İlişkin Bildirim": "Bölünme",
    "Ortaklık Aleyhine Dava Açılması veya Davaya İlişkin Gelişmeler": "Dava",
    "Pay Alım Teklifi Yoluyla Pay Toplanmasına İlişkin Bildirim": "Pay alım teklifi",
    "Payların Geri Alınmasına İlişkin Bildirim": "Pay geri alımı",
    "Pay Alım Satım Bildirimi": "Pay alım satımı",
    "Genel Kurul İşlemlerine İlişkin Bildirim": "Genel kurul",
    "Özel Durum Açıklaması (Genel)": "Özel durum",
}
_CLASS_DEFAULT = {"ODA": "Özel durum", "FR": "Rapor", "DG": "Form", "DUY": "Duyuru", "DKB": "Duyuru"}
COMPANY_CLASSES = ("ODA", "FR", "DG")   # disindakiler (DUY sorgusu 'DKB' sinifiyla doner) borsa/kurum duyurusu

_R_BORC = "Borçlanma aracı işlemleri"
_R_GERI = "Pay geri alımı işlemleri"
_R_FORM = "Formlar ve raporlar"
_R_ORTAK = "Ortak ve fon pay işlemleri"
_R_YON = "Yönetim ve genel kurul işleri"
_R_VAR = "Varant ve sertifika işlemleri"
_R_BORSA = "Borsa duyuruları"

ROUTINE_BY_SUBJECT = {
    "Payların Geri Alınmasına İlişkin Bildirim": _R_GERI,
    "Pay Dışında Sermaye Piyasası Aracı İşlemlerine İlişkin Bildirim (Faiz İçeren)": _R_BORC,
    "Pay Dışında Sermaye Piyasası Aracı İşlemlerine İlişkin Bildirim (Faizsiz)": _R_BORC,
    "İhraç Tavanına İlişkin Bildirim": _R_BORC,
    "Borçlanma Araçları, Yatırım Fonları ve Varant İtfa/Kupon/Getiri/ Nakdi Uzlaşı Ödeme İşlemleri": _R_BORC,
    "Yatırım Kuruluşu Varant - Sertifika - Senetlerine İlişkin Bildirim": _R_VAR,
    "Pay Alım Satım Bildirimi": _R_ORTAK,
    "Kurumsal Yönetim Uyum Derecelendirmesi": _R_YON,
    "Yönetim Kurulu Komiteleri": _R_YON,
    "Bağımsız Denetim Kuruluşunun Belirlenmesi": _R_YON,
    "Bilgilendirme Politikası": _R_YON,
    "Genel Kurul İşlemlerine İlişkin Bildirim": _R_YON,
    "Şirket Merkezi Değişikliği": _R_YON,
    "Esas Sözleşme Tadili": _R_YON,
    "Pay Mali Hak Kullanım İşlemi - Nakit Ödeme": _R_BORSA,
}
# Yayinlayan evren disinda ama bildirim hissenin KENDISI hakkinda: hisseye baglanir.
THIRD_PARTY_SUBJECTS = frozenset({
    "Kredi Derecelendirmesi",
    "Pay Alım Satım Bildirimi",
    "Pay Alım Teklifi Yoluyla Pay Toplanmasına İlişkin Bildirim",
})


def _lower_tr(s):
    return (s or "").replace("I", "ı").replace("İ", "i").lower()


def routine_group(kap_class, subject, title):
    """Rutin ise grup adi, degilse None (akista gizlenen bildirimler)."""
    if kap_class not in COMPANY_CLASSES:          # DUY/DKB: borsa, Takasbank, MKK, KAP duyurulari
        return ROUTINE_BY_SUBJECT.get(subject) or _R_BORSA
    if kap_class == "DG":
        return _R_FORM
    if kap_class == "FR" and subject != "Finansal Rapor":
        return _R_FORM
    t = _lower_tr(title)
    if subject == "Payların Geri Alınmasına İlişkin Bildirim" and "başlat" in t:
        return None  # geri alim PROGRAMININ baslatilmasi haberdir; gunluk islem dokumu rutindir
    g = ROUTINE_BY_SUBJECT.get(subject)
    if g:
        return g
    if subject == "Özel Durum Açıklaması (Genel)":
        if "itfa" in t or "kupon" in t or "kira sertifikası" in t:
            return _R_BORC
        if "görev dağılımı" in t:
            return _R_YON
    return None


def filter_key(subject, kap_class, rutin):
    """Sayfa filtreleri: bilanco | temettu | ozel (rutin -> None)."""
    if rutin:
        return None
    if subject == "Finansal Rapor":
        return "bilanco"
    if subject == "Kar Payı Dağıtım İşlemlerine İlişkin Bildirim":
        return "temettu"
    if kap_class == "ODA":
        return "ozel"
    return None


def label_for(subject, kap_class):
    return SUBJECT_LABEL.get(subject) or _CLASS_DEFAULT.get(kap_class) or "Bildirim"


def parse_publish(s):
    try:
        return datetime.strptime((s or "")[:19], "%d.%m.%Y %H:%M:%S")
    except ValueError:
        try:
            return datetime.strptime((s or "")[:16], "%d.%m.%Y %H:%M")
        except ValueError:
            return None


def normalize(raw, universe):
    """KAP liste kaydi -> akis kaydi, ya da None (evrenle ilgisi yok / baska uyenin bildirimi).

    universe: analiz evrenindeki hisse kodlari (set)."""
    try:
        idx = int(raw.get("disclosureIndex"))
    except (TypeError, ValueError):
        return None
    pub = parse_publish(raw.get("publishDate"))
    if not pub:
        return None
    kap_class = (raw.get("disclosureClass") or "").upper()
    subject = clean_text(raw.get("subject"))
    own = [c for c in codes(raw.get("stockCodes")) if c in universe]
    related = [c for c in codes(raw.get("relatedStocks")) if c in universe]
    if own:
        tickers, via = own, "own"
    elif related and (kap_class not in COMPANY_CLASSES or subject in THIRD_PARTY_SUBJECTS):
        tickers, via = related, "related"
    else:
        return None  # C-M10: baska uyenin bildirimi (ilgili sirket listesi) hisseye yazilmaz
    title = clean_title(raw.get("summary")) or subject
    group = routine_group(kap_class, subject, title)
    rutin = group is not None
    return {
        "id": idx,
        "ts": pub.strftime("%Y-%m-%dT%H:%M:%S"),
        "ticker": tickers[0],
        "tickers": tickers,
        "class": label_for(subject, kap_class),
        "subject": subject,
        "kap_class": kap_class,
        "title": title,
        "rutin": rutin,
        "group": group,
        "filter": filter_key(subject, kap_class, rutin),
        "late": bool(raw.get("isLate")),
        "via": via,
        # ic dogrulama izi (API'ye cikmaz)
        "_src": {"kap": idx, "publisher": clean_text(raw.get("kapTitle")),
                 "codes": clean_text(raw.get("stockCodes"))},
        "onem": None,
    }


# ----------------------------------------------------------------------------- depo (aylik parca)

def _atomic_write(path, obj):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    data = json.dumps(obj, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    fd, tmp = tempfile.mkstemp(dir=os.path.dirname(path), prefix=".tmp_")
    try:
        with os.fdopen(fd, "wb") as f:
            f.write(data)
        os.replace(tmp, path)
    except BaseException:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


class Store:
    """data/kap_feed: items/YYYY-MM.json + docs/<id>.json + meta.json. mtime onbellekli okuma."""

    def __init__(self, base_dir=None):
        self.base = base_dir or DATA_DIR
        self.items_dir = os.path.join(self.base, "items")
        self.docs_dir = os.path.join(self.base, "docs")
        self.meta_path = os.path.join(self.base, "meta.json")
        self._shards = {}      # key -> (mtime, {id: item})
        self._merged = None    # (signature, sorted list, by_id)

    # -- okuma
    def available(self):
        return os.path.isdir(self.items_dir) and any(n.endswith(".json") for n in os.listdir(self.items_dir))

    def _shard_keys(self):
        try:
            return sorted(n[:-5] for n in os.listdir(self.items_dir)
                          if re.match(r"^\d{4}-\d{2}\.json$", n))
        except OSError:
            return []

    def _load_shard(self, key):
        path = os.path.join(self.items_dir, key + ".json")
        try:
            mtime = os.path.getmtime(path)
        except OSError:
            self._shards.pop(key, None)
            return {}
        hit = self._shards.get(key)
        if hit and hit[0] == mtime:
            return hit[1]
        try:
            with open(path, encoding="utf-8") as f:
                d = json.load(f)
            items = {int(k): v for k, v in (d.get("items") or {}).items()}
        except (OSError, ValueError, AttributeError):
            items = {}
        self._shards[key] = (mtime, items)
        return items

    def all_items(self):
        """Tum kayitlar, yeniden eskiye. Parca degismediyse ayni liste (ucuz)."""
        keys = self._shard_keys()
        shards = [(k, self._load_shard(k)) for k in keys]
        sig = tuple((k, self._shards.get(k, (0,))[0]) for k in keys)
        if self._merged and self._merged[0] == sig:
            return self._merged[1]
        by_id = {}
        for _, items in shards:
            by_id.update(items)
        lst = sorted(by_id.values(), key=lambda x: (x["ts"], x["id"]), reverse=True)
        self._merged = (sig, lst, by_id)
        return lst

    def get(self, idx):
        self.all_items()
        return self._merged[2].get(int(idx)) if self._merged else None

    def meta(self):
        try:
            with open(self.meta_path, encoding="utf-8") as f:
                return json.load(f)
        except (OSError, ValueError):
            return {}

    def doc(self, idx):
        try:
            with open(os.path.join(self.docs_dir, "%d.json" % int(idx)), encoding="utf-8") as f:
                return json.load(f)
        except (OSError, ValueError, TypeError):
            return None

    # -- yazma (yalniz poller)
    def merge(self, items, today=None):
        """Yeni kayitlari aylik parcalara isler; eski onem/ozet alanlarini korur. Degisen parca sayisi."""
        today = today or date.today()
        by_key = {}
        for it in items:
            by_key.setdefault(it["ts"][:7], []).append(it)
        changed = 0
        for key, new in by_key.items():
            cur = dict(self._load_shard(key))
            dirty = False
            for it in new:
                old = cur.get(it["id"])
                if old:
                    for k in ("onem", "ozet", "doc"):
                        if old.get(k) is not None and it.get(k) is None:
                            it[k] = old[k]
                if old != it:
                    cur[it["id"]] = it
                    dirty = True
            if dirty:
                self.write_shard(key, cur)
                changed += 1
        self.prune(today)
        return changed

    def write_shard(self, key, items):
        _atomic_write(os.path.join(self.items_dir, key + ".json"),
                      {"schema_version": SCHEMA_VERSION, "items": {str(k): v for k, v in items.items()}})
        self._shards.pop(key, None)
        self._merged = None

    def prune(self, today):
        """KEEP_DAYS'ten eski parca silinir; DUY kayitlari DUY_KEEP_DAYS sonra dusurulur."""
        cutoff = (today - timedelta(days=KEEP_DAYS)).strftime("%Y-%m")
        duy_cut = (today - timedelta(days=DUY_KEEP_DAYS)).isoformat()
        for key in self._shard_keys():
            if key < cutoff:
                try:
                    os.remove(os.path.join(self.items_dir, key + ".json"))
                except OSError:
                    pass
                self._shards.pop(key, None)
                self._merged = None
                continue
            if key <= duy_cut[:7]:
                cur = self._load_shard(key)
                keep = {k: v for k, v in cur.items()
                        if not (v.get("kap_class") not in COMPANY_CLASSES and v["ts"][:10] < duy_cut)}
                if len(keep) != len(cur):
                    self.write_shard(key, keep)

    def save_doc(self, idx, doc):
        _atomic_write(os.path.join(self.docs_dir, "%d.json" % int(idx)), doc)

    def save_meta(self, meta):
        _atomic_write(self.meta_path, meta)


# ----------------------------------------------------------------------------- sorgu / API bicimi

def public_item(it, names=None):
    """API'ye giden kopya: ic iz (_src, via) yok, dis baglanti yok."""
    names = names or {}
    ts = it["ts"]
    return {
        "id": it["id"],
        "date": ts,
        "day": ts[:10],
        "time": ts[11:16],
        "ticker": it["ticker"],
        "tickers": it.get("tickers") or [it["ticker"]],
        "company": names.get(it["ticker"]) or it["ticker"],
        "class": it["class"],
        "subject": it["subject"],
        "title": it["title"],
        "summary": it.get("ozet"),
        "onem": it.get("onem"),
        "rutin": bool(it.get("rutin")),
        "group": it.get("group"),
        "filter": it.get("filter"),
        "href": "/hisse/%s/bildirim/%d" % (it["ticker"], it["id"]),
    }


def query(items, page=1, per_page=50, filt=None, tickers=None, include_rutin=False, day=None):
    """items: yeniden eskiye sirali. -> {items, page, pages, total, routine_hidden}"""
    tset = set(t.upper() for t in tickers) if tickers else None
    out, hidden = [], 0
    for it in items:
        if day and it["ts"][:10] != day:
            continue
        if tset and not (tset & set(it.get("tickers") or [it["ticker"]])):
            continue
        if it.get("rutin") and not include_rutin:
            hidden += 1
            continue
        if filt and it.get("filter") != filt:
            continue
        out.append(it)
    per_page = max(1, min(int(per_page or 50), 200))
    total = len(out)
    pages = max(1, (total + per_page - 1) // per_page)
    page = max(1, min(int(page or 1), pages))
    return {"items": out[(page - 1) * per_page: page * per_page], "page": page, "pages": pages,
            "total": total, "routine_hidden": hidden}


def day_label(day_iso):
    """'2026-09-24' -> '24 Eylül Perşembe' (goreli zaman yok, kanon §2.7)."""
    try:
        d = datetime.strptime(day_iso[:10], "%Y-%m-%d").date()
    except (TypeError, ValueError):
        return day_iso or ""
    return "%d %s %s" % (d.day, _TR_MONTHS[d.month - 1], _TR_DAYS[d.weekday()])


def date_long(ts_iso):
    """'2026-09-23T09:15:00' -> '23 Eylül 2026'"""
    try:
        d = datetime.strptime(ts_iso[:10], "%Y-%m-%d").date()
    except (TypeError, ValueError):
        return ""
    return "%d %s %d" % (d.day, _TR_MONTHS[d.month - 1], d.year)


def group_by_day(items):
    """Sirali kayitlar -> [{day, label, items}] (ayni sira)."""
    days = []
    for it in items:
        d = it["ts"][:10] if "ts" in it else it["day"]
        if not days or days[-1]["day"] != d:
            days.append({"day": d, "label": day_label(d), "items": []})
        days[-1]["items"].append(it)
    return days


def day_counts(items, day):
    """Bir gunun toplam / rutin sayisi (sayfadaki 'N bildirim · M rutin gizli' satiri)."""
    total = rut = 0
    for it in items:
        if it["ts"][:10] == day:
            total += 1
            rut += 1 if it.get("rutin") else 0
    return {"total": total, "routine": rut}


def legacy_rows(items):
    """Eski /api/hisse/<T>/kap bicimi (hisse.html, sinyal hikayesi, piyasa kutusu okur).
    `url` geriye donuk uyum icin kalir (C-24 hisse sekmesi site ici `href`'e gecer)."""
    rows = []
    for it in items:
        ts = datetime.strptime(it["ts"], "%Y-%m-%dT%H:%M:%S")
        rows.append({
            "date": ts.strftime("%d.%m.%Y %H:%M:%S"),
            "summary": it["title"],
            "subject": it["subject"],
            "class": it["kap_class"] if it["kap_class"] in ("ODA", "FR") else it["kap_class"],
            "type": it["kap_class"],
            "index": it["id"],
            "url": "https://www.kap.org.tr/tr/Bildirim/%d" % it["id"],
            "href": "/hisse/%s/bildirim/%d" % (it["ticker"], it["id"]),
            "late": it.get("late", False),
            "rutin": bool(it.get("rutin")),
            "label": it["class"],
        })
    return rows


def for_ticker(items, ticker, days=365, today=None, classes=("ODA", "FR")):
    """Hisse listesi: sahibi ya da hakkindaki ucuncu taraf bildirimi; son `days` gun.
    Varsayilan siniflar eski ucla ayni (ODA + FR); formlar (DG) ve borsa duyurulari (DUY) disarida."""
    t = ticker.upper()
    cutoff = ((today or date.today()) - timedelta(days=days)).isoformat()
    return [it for it in items if t in (it.get("tickers") or [it["ticker"]])
            and it["ts"][:10] >= cutoff and (not classes or it["kap_class"] in classes)]


# ----------------------------------------------------------------------------- bildirim metni

_NOISE = {"[CONSOLIDATION_METHOD_TITLE]", "[CONSOLIDATION_METHOD]", "İlgili Şirketler", "Related Companies",
          "İlgili Fonlar", "Related Funds", "[]", "Türkçe", "Turkish", "İngilizce", "English"}
_EN_WORDS = re.compile(r"\b(the|of|and|our|has|have|been|was|is|are|with|for|which|this|to|by|company|shall|said)\b",
                       re.I)
_TR_CHARS = re.compile(r"[çğıöşüÇĞİÖŞÜ]")
_RESP_START = "Yukarıdaki açıklamalarımızın"
_SKIP_FLAG_FIELDS = {"oda_UpdateAnnouncementFlag", "oda_CorrectionAnnouncementFlag",
                     "oda_DelayedAnnouncementFlag", "oda_DateOfThePreviousNotificationAboutTheSameSubject"}


def _is_english(seg):
    """Ingilizce cumle: >=2 Ingilizce baglac ve Turkce harf yok; ya da >=3 baglac (Turkce ozel adli EN cumle)."""
    n = len(_EN_WORDS.findall(seg))
    return (n >= 2 and not _TR_CHARS.search(seg)) or n >= 3


def _turkish_part(segs):
    """Bolumler -> Ingilizce ilk CUMLEYE kadar olan Turkce kisim (ayni bolumde TR+EN olabilir)."""
    out = []
    for seg in segs:
        sents = re.split(r"(?<=[.!?])\s+(?=[A-Z])", seg)
        keep = []
        for sn in sents:
            if _is_english(sn):
                if keep:
                    out.append(clean_text(" ".join(keep)))
                return out
            keep.append(sn)
        out.append(clean_text(" ".join(keep)))
    return [x for x in out if x]


def _tr_value(vals):
    """Iki dilli deger listesinden Turkcesi; 'Hayır (No)' -> 'Hayır'."""
    vals = [v for v in vals if v]
    if not vals:
        return ""
    v = vals[0]
    v = re.sub(r"\s*\((?:Yes|No|Customer|Supplier|None|Other)\)$", "", v)
    return clean_text(v)


def _flat(page_html):
    from kap_financials import _flat as kf_flat  # tek ayristirici (D-40a0)
    return kf_flat(page_html)


def parse_detail(page_html):
    """KAP bildirim sayfasi -> {'fields': [[etiket, deger]], 'text': str, 'resp': str|None, 'lines': []}.

    Iki bicim: (1) 'oda_*' alanli form (etiket/deger TR+EN), (2) alansiz form (temettu vb.):
    satirlar sirayla. Ingilizce kisim atilir (Turkce metin esastir)."""
    s = _flat(page_html)
    toks = [t.strip() for t in s.split("|")]
    toks = [t for t in toks if t]
    try:
        start = toks.index("Özet Bilgi") + 2
    except ValueError:
        start = 0
    end = len(toks)
    resp = None
    for i in range(start, len(toks)):
        if toks[i].startswith(_RESP_START):
            end, resp = i, clean_text(toks[i])
            break
    body = [t for t in toks[start:end] if t not in _NOISE]
    fields, text_segs, lines = [], [], []
    if any(t.startswith("oda_") for t in body):
        i = 0
        while i < len(body):
            t = body[i]
            if not t.startswith("oda_"):
                i += 1
                continue
            name = t
            j = i + 1
            while j < len(body) and not body[j].startswith("oda_"):
                j += 1
            chunk = body[i + 1:j]
            i = j
            if name == "oda_ExplanationTextBlock":  # etiketsiz serbest metin: TR bolumler, EN'de durur
                text_segs.extend(_turkish_part(chunk))
                continue
            if name.endswith(("Abstract", "Section")) or len(chunk) < 2:
                continue
            label, vals = clean_text(chunk[0]), chunk[2:]
            if name in _SKIP_FLAG_FIELDS:
                v = _tr_value(vals)
                if name == "oda_UpdateAnnouncementFlag" and v == "Evet":
                    fields.append([label.rstrip("?").strip() + "?", "Evet"])
                continue
            v = _tr_value(vals)
            if v and v != "-":
                fields.append([label, v])
    else:
        lines = _turkish_part(body)
    text = " ".join(x for x in text_segs if x)
    text = re.sub(r"\s+([.,;:])", r"\1", text)
    return {"fields": fields, "text": text, "resp": resp, "lines": lines}


# ----------------------------------------------------------------------------- tutar ve onem orani

_CUR = [
    (r"Türk\s+Liras[ıi]|TL|TRY|₺", "TRY"),
    (r"ABD\s+Dolar[ıi]|Amerikan\s+Dolar[ıi]|USD|US\$|\$|Dolar", "USD"),
    (r"Euro|EUR|Avro|€", "EUR"),
]
_NUM = r"\d{1,3}(?:\.\d{3})+(?:,\d+)?|\d+(?:,\d+)?"
_MULT = r"(?:\s*(milyar|milyon|bin)\b)?"
_CUR_ALT = "|".join(p for p, _ in _CUR)
_AMOUNT_RE = re.compile(r"(?<![\d.,])(%s)%s\s*,?-?\s*(%s)(?![A-Za-zçğıöşü])" % (_NUM, _MULT, _CUR_ALT))
_AMOUNT_PRE_RE = re.compile(r"(?<![A-Za-z])(USD|EUR|TRY|TL)\s*(%s)%s" % (_NUM, _MULT))
_MULTS = {"milyar": 1e9, "milyon": 1e6, "bin": 1e3, None: 1.0, "": 1.0}


def _cur_of(tok):
    for pat, code in _CUR:
        if re.fullmatch(pat, tok.strip(), flags=re.I):
            return code
    return None


def _num(s):
    if "." in s and "," not in s and re.fullmatch(r"\d{1,3}(?:\.\d{3})+", s):
        return float(s.replace(".", ""))
    return float(s.replace(".", "").replace(",", "."))


def find_amounts(text):
    """Metindeki para tutarlari -> [(deger, para, konum)] (Turkce yazim; '33,8 milyon $')."""
    out = []
    for m in _AMOUNT_RE.finditer(text or ""):
        cur = _cur_of(m.group(3))
        if not cur:
            continue
        out.append((_num(m.group(1)) * _MULTS[m.group(2)], cur, m.start()))
    for m in _AMOUNT_PRE_RE.finditer(text or ""):
        cur = _cur_of(m.group(1))
        out.append((_num(m.group(2)) * _MULTS[m.group(3)], cur, m.start()))
    out.sort(key=lambda x: x[2])
    return out


ONEM_SUBJECTS = {
    "Yeni İş İlişkisi": ("Sözleşme tutarı", "sözleşme"),
    "İhale Süreci / Sonucu": ("İhale bedeli", "ihale bedeli"),
    "Finansal Duran Varlık Edinimi": ("İşlem tutarı", "işlem tutarı"),
    "Finansal Duran Varlık Satışı": ("İşlem tutarı", "işlem tutarı"),
    "Maddi Duran Varlık Alımı": ("İşlem tutarı", "işlem tutarı"),
    "Maddi Duran Varlık Satımı": ("İşlem tutarı", "işlem tutarı"),
    "Özel Durum Açıklaması (Genel)": ("Sözleşme tutarı", "sözleşme"),
}
_CONTRACT_WORDS = ("sözleşme", "sipariş", "ihale", "iş ilişkisi", "anlaşma")
_AMOUNT_FIELD_RE = re.compile(r"(Bedeli|Tutarı|Değeri|Fiyatı)\b")


def pick_amount(subject, title, detail):
    """Bildirimin tek parasal tutari -> {value, cur, kind, raw} ya da None (belirsizse None).

    Sira: (1) yapilandirilmis tutar alani (Ihale Bedeli) (2) sirketin verdigi TL karsiligi
    (3) 'Sirket Payi' tutari (4) metinde 'tutar/bedel/toplam' yakininda TEK farkli tutar."""
    if subject not in ONEM_SUBJECTS or not detail:
        return None
    text = detail.get("text") or ""
    if subject == "Özel Durum Açıklaması (Genel)":
        low = _lower_tr(title + " " + text)
        if not any(w in low for w in _CONTRACT_WORDS):
            return None
    for label, value in detail.get("fields") or []:
        if _AMOUNT_FIELD_RE.search(label) and "Oran" not in label:
            am = find_amounts(value)
            if len(am) >= 1:
                return {"value": am[0][0], "cur": am[0][1], "kind": "alan", "raw": value}
    m = re.search(r"(?:Türk\s+Lirası|TL)\s+karşılığı[^0-9]{0,40}(%s)" % _NUM, text)
    if m:
        return {"value": _num(m.group(1)), "cur": "TRY", "kind": "tl_karsiligi", "raw": m.group(0)}
    m = re.search(r"Şirket\s+Payı[^0-9:]{0,40}:?\s*(%s)\s*(%s)" % (_NUM, _CUR_ALT), text, flags=re.I)
    if m and _cur_of(m.group(2)):
        return {"value": _num(m.group(1)), "cur": _cur_of(m.group(2)), "kind": "sirket_payi", "raw": m.group(0)}
    cands = []
    for val, cur, pos in find_amounts(text):
        pre = _lower_tr(text[max(0, pos - 90):pos])
        if "sermaye" in pre[-45:]:
            continue
        if any(w in pre for w in ("tutar", "bedel", "toplam", "değer", "büyüklü")):
            cands.append((val, cur))
    distinct = sorted(set(cands))
    if len(distinct) == 1:
        return {"value": distinct[0][0], "cur": distinct[0][1], "kind": "metin", "raw": None}
    return None


def annual_revenue(ticker, kap_fin_dir=None):
    """D-40a0 kaydindan son yillik hasilat (TL). Banka/sigorta/kayit yok -> None."""
    try:
        import kap_financials as kf
    except ImportError:
        return None
    rec = kf.load_record(ticker, kap_fin_dir)
    if not rec:
        return None
    annual = [r for r in rec.get("reports") or [] if r.get("period") == 4 and r.get("format") == "sanayi"]
    if not annual:
        return None
    last = max(annual, key=lambda r: r["fy"])
    rev = ((last.get("items") or {}).get("revenue") or {}).get("cur")
    if not rev or not last.get("mult") or last.get("currency") != "TRY" and last.get("currency") != "TL":
        return None
    return {"fy": last["fy"], "value": float(rev) * float(last["mult"])}


def fmt_pct(p):
    """4.664 -> '%4,7' ; 38.07 -> '%38,1'"""
    return "%" + ("%.1f" % p).replace(".", ",")


def fmt_try(v):
    """TL tutar -> '1.646.250.192 ₺'"""
    return "{:,.0f}".format(v).replace(",", ".") + " ₺"


def fmt_big_try(v):
    """-> '35,3 Mrd ₺' / '842 Mn ₺' (kanon §2.10)"""
    if abs(v) >= 1e9:
        return ("%.1f" % (v / 1e9)).replace(".", ",") + " Mrd ₺"
    if abs(v) >= 1e6:
        return ("%.0f" % (v / 1e6)) + " Mn ₺"
    return fmt_try(v)


_CUR_SIGN = {"TRY": "₺", "USD": "$", "EUR": "€"}


def fmt_amount(value, cur):
    txt = "{:,.2f}".format(value).replace(",", "X").replace(".", ",").replace("X", ".")
    if txt.endswith(",00"):
        txt = txt[:-3]
    return "%s %s" % (txt, _CUR_SIGN.get(cur, cur))


def compute_onem(amount, revenue, subject, fx_rate=None, fx_date=None):
    """Tutar / son yillik hasilat. Doviz tutari TCMB alis kuruyla cevrilir ve '~' alir."""
    if not amount or not revenue or not revenue.get("value"):
        return None
    basis, short = ONEM_SUBJECTS.get(subject, ("Tutar", "tutar"))
    if amount["kind"] == "sirket_payi":
        basis, short = "Şirket payı tutarı", "şirket payı"
    approx = False
    fx = None
    if amount["cur"] == "TRY":
        try_amount = amount["value"]
    elif fx_rate:
        try_amount = amount["value"] * fx_rate
        approx = True
        fx = {"cur": amount["cur"], "rate": round(fx_rate, 4), "rate_txt": ("%.2f" % fx_rate).replace(".", ","),
              "date": fx_date}
    else:
        return None
    pct = try_amount / revenue["value"] * 100.0
    if pct <= 0 or pct > 10000:
        return None
    txt = ("~" if approx else "") + fmt_pct(pct)
    return {
        "pct": round(pct, 2), "txt": txt, "approx": approx,
        "basis": "%s / %d hasılatı" % (basis, revenue["fy"]),
        "formula": "%s / yıllık hasılat = %s" % (short, txt),
        "amount_txt": fmt_amount(amount["value"], amount["cur"]),
        "amount_try": round(try_amount), "amount_try_txt": fmt_big_try(try_amount),
        "rev_year": revenue["fy"], "rev": revenue["value"], "rev_txt": fmt_big_try(revenue["value"]),
        "fx": fx,
    }


def summary_sentence(item, company, onem=None):
    """Kural tabanli tek cumle (AI yok). Betim; yargi yok."""
    cls = item["class"]
    title = item["title"]
    when = date_long(item["ts"])
    kind = _lower_tr(cls[:1]) + cls[1:]
    s = "%s, %s tarihinde %s bildirimi yayımladı" % (company, when, kind)
    if _lower_tr(title) not in (_lower_tr(cls), _lower_tr(item.get("subject"))):
        s += ": “%s”" % title.rstrip(".")
    s += "."
    if onem:
        ratio = onem["txt"].replace("~", "yaklaşık ")
        s += " Bildirilen %s %s; şirketin %d hasılatına oranı %s." % (
            _lower_tr(onem["basis"].split(" / ")[0]), onem["amount_txt"], onem["rev_year"], ratio)
    return s


# ----------------------------------------------------------------------------- TCMB kuru

def parse_tcmb(xml_text):
    """TCMB gunluk kur XML -> {'USD': alis, 'EUR': alis}"""
    out = {}
    for code in ("USD", "EUR"):
        m = re.search(r'Kod="%s".*?<ForexBuying>([\d.]+)</ForexBuying>' % code, xml_text or "", re.S)
        if m:
            out[code] = float(m.group(1))
    return out


# ----------------------------------------------------------------------------- KAP istemcisi + poll

class KapStop(Exception):
    """KAP 429/5xx: nazikce dur, sonraki turda devam."""


class KapClient:
    """Tek KAP istemcisi (liste + bildirim sayfasi): >= min_gap sn aralik, tek is parcacigi."""

    UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126 Safari/537.36"

    def __init__(self, session=None, min_gap=2.0, timeout=30):
        if session is None:
            import requests
            session = requests.Session()
        self.s = session
        self.min_gap = min_gap
        self.timeout = timeout
        self.last = 0.0
        self.count = 0

    def _call(self, method, url, **kw):
        wait = self.min_gap - (time.time() - self.last)
        if wait > 0:
            time.sleep(wait)
        try:
            r = self.s.request(method, url, timeout=self.timeout,
                               headers={"User-Agent": self.UA, "Accept": "application/json, text/html"}, **kw)
        finally:
            self.last = time.time()
            self.count += 1
        if r.status_code == 429 or r.status_code >= 500:
            raise KapStop("KAP HTTP %s" % r.status_code)
        if r.status_code != 200:
            raise ValueError("KAP HTTP %s: %s" % (r.status_code, url))
        return r

    def disclosures(self, oids, frm, to, kap_class):
        payload = {"fromDate": frm, "toDate": to, "disclosureClass": kap_class, "subjectList": [],
                   "mkkMemberOidList": list(oids), "inactiveMkkMemberOidList": [], "bdkMemberOidList": [],
                   "fromSrc": False, "disclosureIndexList": []}
        d = self._call("POST", KAP_LIST_URL, json=payload).json()
        if not isinstance(d, list):
            raise ValueError("KAP listesi beklenmedik: %s" % str(d)[:120])
        return d

    def page(self, idx):
        return self._call("GET", KAP_PAGE_URL % int(idx)).text


def fetch_list(client, oids, universe, frm, to, classes=POLL_CLASSES):
    """Evren icin tarih araligi (<= 1 yil) -> normalize edilmis kayitlar."""
    out = []
    for cls in classes:
        for raw in client.disclosures(oids, frm, to, cls):
            it = normalize(raw, universe)
            if it:
                out.append(it)
    return out


def enrich(store, client, item, names, fx_getter=None, kap_fin_dir=None):
    """Bildirim metnini (bir kez) ceker, onem + ozet alanlarini doldurur."""
    doc = store.doc(item["id"])
    if doc is None:
        detail = parse_detail(client.page(item["id"]))
        doc = {"id": item["id"], "fetched_at": datetime.now().strftime("%Y-%m-%dT%H:%M"), **detail}
        store.save_doc(item["id"], doc)
    onem = None
    amount = pick_amount(item["subject"], item["title"], doc)
    if amount:
        rate = rate_day = None
        if amount["cur"] != "TRY" and fx_getter:
            try:
                got = fx_getter(item["ts"][:10], amount["cur"])  # -> (kur, kur_gunu) | None
                if got:
                    rate, rate_day = got
            except Exception:  # kur yoksa oran yok (tahmin yok)
                rate = None
        onem = compute_onem(amount, annual_revenue(item["ticker"], kap_fin_dir), item["subject"],
                            fx_rate=rate, fx_date=rate_day)
    item["onem"] = onem
    item["ozet"] = summary_sentence(item, names.get(item["ticker"]) or item["ticker"], onem)
    item["doc"] = True
    return item


def poll_once(store, client, oids, universe, names, now=None, max_docs=15, days_back=1,
              fx_getter=None, kap_fin_dir=None, log=None, classes=POLL_CLASSES):
    """Artimli tur: son `days_back` gun + bugun listesi (sinif basina 1 istek) + yeni rutin-disi
    bildirimlerin metni (tur basina en fazla `max_docs`). Donus: istatistik."""
    now = now or datetime.now()
    frm = (now.date() - timedelta(days=days_back)).isoformat()
    to = now.date().isoformat()
    items = fetch_list(client, oids, universe, frm, to, classes)
    stats = {"listed": len(items), "docs": 0, "requests": 0}
    existing = {it["id"]: it for it in store.all_items()}
    for it in items:
        old = existing.get(it["id"])
        if old:
            for k in ("onem", "ozet", "doc"):
                if old.get(k) is not None:
                    it[k] = old[k]
    todo = [it for it in items if not it.get("rutin") and not it.get("doc")]
    todo.sort(key=lambda x: x["ts"], reverse=True)
    for it in todo[:max_docs]:
        try:
            enrich(store, client, it, names, fx_getter, kap_fin_dir)
            stats["docs"] += 1
        except KapStop:
            raise
        except (ValueError, KeyError) as e:
            if log:
                log("kap_feed: bildirim %s metni alinamadi: %s" % (it["id"], e))
    stats["changed_shards"] = store.merge(items, now.date())
    meta = store.meta()
    meta.update({"schema_version": SCHEMA_VERSION, "updated_at": now.strftime("%Y-%m-%dT%H:%M:%S"),
                 "last_window": [frm, to], "last_listed": len(items)})
    store.save_meta(meta)
    stats["requests"] = client.count
    return stats


def backfill_docs(store, client, names, limit=30, days=90, fx_getter=None, kap_fin_dir=None, today=None):
    """Metni olmayan eski rutin-disi kayitlar (son `days` gun, yeniden eskiye), tur basina `limit`."""
    cutoff = ((today or date.today()) - timedelta(days=days)).isoformat()
    todo = [it for it in store.all_items() if not it.get("rutin") and not it.get("doc")
            and it["ts"][:10] >= cutoff][:limit]
    done = []
    for it in todo:
        try:
            done.append(enrich(store, client, dict(it), names, fx_getter, kap_fin_dir))
        except (ValueError, KeyError):
            continue
    if done:
        store.merge(done)
    return len(done)
