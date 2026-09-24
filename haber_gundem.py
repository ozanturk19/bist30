"""D-45: Gundem -- (1) ic girdi: haber RSS basliklari, (2) v1 baskisi: kendi verimizden kurallarla.

(1) Gundem girdisi (`/api/gundem-girdi`, YALNIZ IC KULLANIM, yonetici anahtari ister)
    Turkiye (ekonomi/piyasa) ve Dunya (piyasalar, merkez bankalari, emtia) basliklari + kisa
    aciklama gun icinde toplanir; her madde kaynagini ve baglantisini ICERIDE tasir.
    Bu metinler sitede YAYINLANMAZ: kanon §4 "Baska sitelerin metni kopyalanmaz", §2.8
    "kaynak etiketi yok". Girdi, Gundem'i yazan adimin (O5b AI pilotu ya da editor)
    iki bagimsiz kaynakla dogrulama malzemesidir. Kullanim kosullari teslim notunda.

(2) Gundem v1 baskisi (sayfada gorunen)
    AI kapali (grounding maliyet nedeniyle kapali). Maddeler YALNIZ sitenin kendi verisinden
    (gun sonu hisse verisi, makro serit, KAP akisi, ekonomik takvim) kod tarafindan kurulur;
    rakamlari kod yerlestirir (kanon §3). Gunde 2 baski (08:30 sabah, 19:30 aksam) diske
    dondurulur: `data/gundem/<tarih>-<baski>.json` + `latest.json`.

Saf fonksiyonlar agsiz test edilir. Python 3.9 uyumlu.
"""
from __future__ import annotations

import hashlib
import html as _html
import json
import os
import re
import tempfile
from datetime import date, datetime, timedelta

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
INPUT_DIR = os.path.join(BASE_DIR, "data", "gundem_girdi")
PRINT_DIR = os.path.join(BASE_DIR, "data", "gundem")
INPUT_KEEP_DAYS = 14
PRINT_SLOTS = (("sabah", 8, 30), ("aksam", 19, 30))
EDITION_LABEL = {"sabah": "sabah baskısı", "aksam": "akşam baskısı"}

_TR_MONTHS = ("Ocak", "Şubat", "Mart", "Nisan", "Mayıs", "Haziran", "Temmuz", "Ağustos",
              "Eylül", "Ekim", "Kasım", "Aralık")
_TR_DAYS = ("Pazartesi", "Salı", "Çarşamba", "Perşembe", "Cuma", "Cumartesi", "Pazar")

# ----------------------------------------------------------------------------- (1) girdi

# Envanter (24.09): app.py `_MACRO_RSS_SOURCES` 5 kaynak -- Reuters TR (yanit yok, kapali),
# Haberler.com ekonomi (404), Bloomberg HT (14.09'dan beri yeni madde yok), Dunya ekonomi (calisiyor),
# AA ekonomi (feedparser'in kendi User-Agent'iyla yanit yok; tarayici UA ile calisiyor).
# Dunya grubu icin ayni yayincilarin dunya/finans beslemeleri eklendi.
SOURCES = (
    # (ic ad, url, varsayilan grup, yalniz piyasa konulari mi)
    ("AA Ekonomi", "https://www.aa.com.tr/tr/rss/default?cat=ekonomi", "turkiye", False),
    ("AA Dünya", "https://www.aa.com.tr/tr/rss/default?cat=dunya", "dunya", True),
    ("Dünya Ekonomi", "https://www.dunya.com/rss/ekonomi.xml", "turkiye", False),
    ("Dünya Finans", "https://www.dunya.com/rss/finans.xml", "turkiye", False),
    ("Dünya Dünya", "https://www.dunya.com/rss/dunya.xml", "dunya", True),
    ("TRT Haber Ekonomi", "https://www.trthaber.com/ekonomi_articles.rss", "turkiye", False),
    ("TRT Haber Dünya", "https://www.trthaber.com/dunya_articles.rss", "dunya", True),
    ("Bloomberg HT", "https://www.bloomberght.com/rss", "turkiye", False),
)
UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126 Safari/537.36"

_MARKET_RE = re.compile(
    r"\b(?:borsa|endeks|hisse|faiz|merkez bankas|fed\b|ecb\b|enflasyon|petrol|brent|altın|gümüş|emtia|dolar|"
    r"euro\b|avro|tahvil|pmi\b|büyüme|gsyh|istihdam|işsizlik|ticaret|gümrük|tarife|opec|döviz|piyasa|ihracat|"
    r"ithalat|bütçe|cari açık|kredi not|resesyon|nasdaq|s&p|dow jones|dax\b|nikkei|bitcoin|doğal gaz|bakır)")
_WORLD_RE = re.compile(
    r"\b(?:abd|amerika|fed\b|avrupa|euro bölgesi|avro bölgesi|ecb\b|almanya|fransa|ingiltere|çin\b|japonya|"
    r"hindistan|rusya|küresel|dünya|new york|wall street|asya|opec|brent|nasdaq|s&p|dow jones|dax\b|nikkei|körfez)")
_TR_RE = re.compile(
    r"\b(?:türkiye|tcmb|bist|borsa istanbul|hazine|tüik|spk\b|bddk|şimşek|karahan|türk lirası|yurt içi|ankara)")


def _lower_tr(s):
    return (s or "").replace("I", "ı").replace("İ", "i").lower()


def _strip_html(s):
    s = re.sub(r"<[^>]+>", " ", s or "")
    s = _html.unescape(s)
    return re.sub(r"\s+", " ", s).strip()


def _norm_title(t):
    t = _lower_tr(t)
    return re.sub(r"[^0-9a-zçğıöşü ]+", "", t).strip()


def classify(title, desc, default_group, market_only):
    """-> 'turkiye' | 'dunya' | None (piyasa disi dunya haberi). Once baslik, sonra baslik+aciklama."""
    lt, ld = _lower_tr(title), _lower_tr(desc)
    if market_only and not (_MARKET_RE.search(lt) or _MARKET_RE.search(ld)):
        return None
    for txt in (lt, lt + " " + ld):
        world, turkey = bool(_WORLD_RE.search(txt)), bool(_TR_RE.search(txt))
        if world and not turkey:
            return "dunya"
        if turkey and not world:
            return "turkiye"
    return default_group


def parse_feed(content, source):
    """RSS icerigi -> girdi maddeleri. source: SOURCES satiri."""
    import feedparser
    name, url, group, market_only = source
    out = []
    for e in (feedparser.parse(content).entries or []):
        title = _strip_html(e.get("title"))
        if not title:
            continue
        desc = _strip_html(e.get("summary") or e.get("description"))
        if len(desc) > 300:
            desc = desc[:297].rsplit(" ", 1)[0] + "…"
        parsed = e.get("published_parsed") or e.get("updated_parsed")
        ts = datetime(*parsed[:6]).strftime("%Y-%m-%dT%H:%M:%SZ") if parsed else None
        g = classify(title, desc, group, market_only)
        if not g:
            continue
        out.append({"id": hashlib.sha1(_norm_title(title).encode("utf-8")).hexdigest()[:12],
                    "title": title, "desc": desc, "group": g, "ts": ts,
                    "src": {"name": name, "url": (e.get("link") or "").strip(), "feed": url}})
    return out


def _tokens(t):
    return set(w for w in _norm_title(t).split() if len(w) > 2)


def merge_input(existing, new):
    """Ayni basligi tekille, benzer basliklari (ortak kelime >= %50) 'kaynaklar' altinda say."""
    by_id = {x["id"]: x for x in existing}
    for it in new:
        cur = by_id.get(it["id"])
        if cur:
            if it["src"]["name"] not in [s["name"] for s in cur["sources"]]:
                cur["sources"].append(it["src"])
            continue
        it = dict(it)
        it["sources"] = [it.pop("src")]
        by_id[it["id"]] = it
    items = sorted(by_id.values(), key=lambda x: x.get("ts") or "", reverse=True)
    toks = [(_tokens(x["title"]), x) for x in items]
    for tk, x in toks:
        names = set(s["name"].split()[0] for s in x["sources"])
        for tk2, y in toks:
            if y is x or not tk or not tk2:
                continue
            if len(tk & tk2) / float(min(len(tk), len(tk2))) >= 0.5:
                names.update(s["name"].split()[0] for s in y["sources"])
        x["independent_sources"] = len(names)  # yayinci bazinda (AA/Dunya/TRT/Bloomberg)
    return items


def _atomic_write(path, obj):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=os.path.dirname(path), prefix=".tmp_")
    with os.fdopen(fd, "wb") as f:
        f.write(json.dumps(obj, ensure_ascii=False, separators=(",", ":")).encode("utf-8"))
    os.replace(tmp, path)


def load_input(day, base_dir=None):
    try:
        with open(os.path.join(base_dir or INPUT_DIR, "%s.json" % day), encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return None


def collect_input(get, now=None, base_dir=None, log=None):
    """Tum kaynaklari okur (get(url) -> bytes), gunun dosyasina birlestirir. Eski dosyalar silinir."""
    base = base_dir or INPUT_DIR
    now = now or datetime.now()
    day = now.date().isoformat()
    new, status = [], {}
    for src in SOURCES:
        try:
            got = parse_feed(get(src[1]), src)
            new.extend(got)
            status[src[0]] = len(got)
        except Exception as e:  # tek kaynak dusmesi turu bozmaz
            status[src[0]] = "hata: %s" % str(e)[:80]
            if log:
                log("gundem_girdi %s: %s" % (src[0], e))
    cur = load_input(day, base) or {"date": day, "items": []}
    cur["items"] = merge_input(cur["items"], new)
    cur["updated_at"] = now.strftime("%Y-%m-%dT%H:%M")
    cur["status"] = status
    _atomic_write(os.path.join(base, "%s.json" % day), cur)
    cutoff = (now.date() - timedelta(days=INPUT_KEEP_DAYS)).isoformat()
    for n in os.listdir(base):
        if re.match(r"^\d{4}-\d{2}-\d{2}\.json$", n) and n[:10] < cutoff:
            try:
                os.remove(os.path.join(base, n))
            except OSError:
                pass
    return status


# ----------------------------------------------------------------------------- (2) v1 baskisi

def _pct(v, signed=True):
    """2.13 -> '+%2,13' ; -0.88 -> '−%0,88' (U+2212)"""
    txt = ("%.2f" % abs(v)).replace(".", ",")
    if not signed:
        return "%" + txt
    if v > 0:
        return "+%" + txt
    if v < 0:
        return "−%" + txt
    return "%" + txt


def _num(v, dec=2):
    s = "{:,.{d}f}".format(v, d=dec)
    return s.replace(",", "X").replace(".", ",").replace("X", ".")


def day_label(d):
    return "%d %s %s" % (d.day, _TR_MONTHS[d.month - 1], _TR_DAYS[d.weekday()])


def _dm(d):
    return "%d %s" % (d.day, _TR_MONTHS[d.month - 1])


STATE = {"AL": "Güçlü Trend", "SAT": "Trend Bozuldu", "BEKLE": "Yatay"}


def _chip_tk(s):
    return {"k": "tk", "t": s["ticker"], "ch": round(s.get("change_pct") or 0.0, 2), "href": "/hisse/%s" % s["ticker"]}


def _item_market(stocks, xu100, close_day):
    ch = [s for s in stocks if isinstance(s.get("change_pct"), (int, float))]
    up = sum(1 for s in ch if s["change_pct"] > 0)
    dn = sum(1 for s in ch if s["change_pct"] < 0)
    flat = len(ch) - up - dn
    close, chg = xu100.get("close"), xu100.get("change_pct")
    if not close or chg is None:
        return None
    verb = "yükselişle" if chg > 0 else ("düşüşle" if chg < 0 else "değişmeden")
    h = "BIST100 %s %s puanda kapandı" % ((_pct(chg, False) + " " + verb) if chg else verb, _num(close))
    p = "%s kapanışı: BIST100 %s puan (%s). Kapsamdaki %d hisse: %d yükselen, %d düşen, %d değişmeyen." % (
        _dm(close_day), _num(close), _pct(chg), len(ch), up, dn, flat)
    top = sorted(ch, key=lambda s: s["change_pct"], reverse=True)
    chips = [{"k": "hm", "l": "Isı haritası", "href": "/sektor-harita"}]
    if top:
        chips.append(_chip_tk(top[0]))
        chips.append(_chip_tk(top[-1]))
    return {"id": "bist", "h": h, "p": p, "chips": chips}


def _item_sectors(stocks):
    by = {}
    for s in stocks:
        if s.get("sector") and isinstance(s.get("change_pct"), (int, float)):
            by.setdefault(s["sector"], []).append(s["change_pct"])
    avg = sorted(((sum(v) / len(v), k, len(v)) for k, v in by.items() if len(v) >= 3 and k != "Diğer"),
                 reverse=True)
    if len(avg) < 2:
        return None
    hi, lo = avg[0], avg[-1]
    h = "En çok %s %s, en çok %s %s" % (
        "yükselen" if hi[0] >= 0 else "gerileyen", hi[1], "düşen" if lo[0] < 0 else "yükselen", lo[1])
    if hi[0] < 0 and lo[0] < 0:
        h = "Tüm sektörler ekside; en sınırlı düşüş %s, en sert düşüş %s" % (hi[1], lo[1])
    elif hi[0] > 0 and lo[0] > 0:
        h = "Tüm sektörler artıda; en güçlü %s, en zayıf %s" % (hi[1], lo[1])
    else:
        h = "Sektörlerde en güçlü %s, en zayıf %s" % (hi[1], lo[1])
    parts = ["%s %s" % (k, _pct(a)) for a, k, n in avg[:2]] + ["%s %s" % (k, _pct(a)) for a, k, n in avg[-2:]]
    p = "Hisselerin eşit ağırlıklı ortalama değişimine göre: %s." % " · ".join(dict.fromkeys(parts))
    chips = [{"k": "sec", "l": hi[1], "href": "/sektor-harita?tab=compare&s=%s" % hi[1]},
             {"k": "sec", "l": lo[1], "href": "/sektor-harita?tab=compare&s=%s" % lo[1]},
             {"k": "hm", "l": "Isı haritası", "href": "/sektor-harita"}]
    return {"id": "sektor", "h": h, "p": p, "chips": chips}


def _macro(macro, label):
    for m in macro or []:
        if m.get("label") == label and isinstance(m.get("price"), (int, float)):
            return m
    return None


def _item_fx(macro):
    usd, eur, gold = _macro(macro, "USDTRY"), _macro(macro, "EURTRY"), _macro(macro, "ALTIN")
    if not usd:
        return None
    h = "Dolar/TL %s" % _num(usd["price"], 4 if usd["price"] < 10 else 2)
    parts = ["Dolar/TL %s (%s)" % (_num(usd["price"]), _pct(usd.get("change") or 0))]
    if eur:
        parts.append("Euro/TL %s (%s)" % (_num(eur["price"]), _pct(eur.get("change") or 0)))
    if gold:
        parts.append("ons altın %s $ (%s)" % (_num(gold["price"]), _pct(gold.get("change") or 0)))
        h += ", ons altın %s $" % _num(gold["price"])
    return {"id": "kur", "h": h, "p": "; ".join(parts) + ".", "chips": []}


def _item_states(stocks, close_day):
    tag = close_day.strftime("%d.%m.%Y")
    moved = [s for s in stocks if s.get("signal_date") == tag and s.get("signal") in STATE]
    if not moved:
        return None
    cnt = {k: [s for s in moved if s["signal"] == k] for k in ("AL", "BEKLE", "SAT")}
    h = "Son seansta %d hissede durum değişti" % len(moved)
    bits = ["Güçlü Trend'e geçen: %d" % len(cnt["AL"]), "Yatay'a dönen: %d" % len(cnt["BEKLE"]),
            "Trend Bozuldu'ya geçen: %d" % len(cnt["SAT"])]
    p = "%s kapanışına göre. %s." % (_dm(close_day), " · ".join(bits))
    pick = sorted(cnt["AL"], key=lambda s: -(s.get("borsapusula_skoru") or 0))[:3] or \
        sorted(moved, key=lambda s: -(s.get("borsapusula_skoru") or 0))[:3]
    chips = [_chip_tk(s) for s in pick]
    return {"id": "durum", "h": h, "p": p, "chips": chips}


_LEAD_CLASSES = ("Finansal rapor", "Yeni iş ilişkisi", "İhale", "Pay alım teklifi", "Birleşme", "Temettü",
                 "Varlık edinimi", "Varlık satışı")


def _item_kap(feed_items, names, day):
    todays = [it for it in feed_items if it["ts"][:10] == day and not it.get("rutin")]
    if not todays:
        return None
    ranked = sorted([it for it in todays if it.get("onem")], key=lambda it: -it["onem"]["pct"])
    newsy = [it for it in todays if it.get("class") in _LEAD_CLASSES]
    lead = ranked[0] if ranked else (newsy[0] if newsy else todays[0])
    co = names.get(lead["ticker"]) or lead["ticker"]
    h = "Şirket bildirimlerinde öne çıkan: %s" % co
    p = "%s tarihinde kapsamdaki şirketlerden %d bildirim (rutin duyurular hariç). %s: “%s”" % (
        _dm(datetime.strptime(day, "%Y-%m-%d").date()), len(todays), co, lead["title"].rstrip("."))
    if lead.get("onem"):
        p += " (%s)" % lead["onem"]["formula"]
    p += "."
    chips = [{"k": "tk", "t": lead["ticker"], "ch": None, "href": "/hisse/%s" % lead["ticker"]},
             {"k": "doc", "l": "Bildirim sayfası", "href": "/hisse/%s/bildirim/%d" % (lead["ticker"], lead["id"])}]
    return {"id": "bildirim", "h": h, "p": p, "chips": chips}


def _item_us(macro, now):
    sp, nq = _macro(macro, "SP500"), _macro(macro, "NASDAQ")
    if not sp:
        return None
    # ABD seansi 16:30-23:00 TSI: bu arada baski "gun icinde", disinda "son kapanis"
    live = (now.hour, now.minute) >= (16, 30) and now.hour < 23 and now.weekday() < 5
    when = "gün içinde" if live else "son kapanışta"
    def mv(m):
        c = m.get("change") or 0
        return "%s %s" % (_pct(c, False), "yükseldi" if c > 0 else ("düştü" if c < 0 else "yatay"))
    h = "ABD borsaları %s: S&P 500 %s" % (when, mv(sp))
    p = "S&P 500 %s puan (%s)" % (_num(sp["price"]), _pct(sp.get("change") or 0))
    if nq:
        p += ", Nasdaq %s puan (%s)" % (_num(nq["price"]), _pct(nq.get("change") or 0))
    return {"id": "abd", "h": h, "p": p + ".", "chips": []}


def _item_commod(macro, now):
    br, au, ag = _macro(macro, "PETROL"), _macro(macro, "ALTIN"), _macro(macro, "GUMUS")
    if not br:
        return None
    c = br.get("change") or 0
    h = "Brent petrol gün içinde %s %s" % (_pct(c, False), "yükseldi" if c > 0 else ("düştü" if c < 0 else "yatay seyretti"))
    p = "Brent varil başına %s $ (%s)" % (_num(br["price"]), _pct(c))
    if au:
        p += "; ons altın %s $ (%s)" % (_num(au["price"]), _pct(au.get("change") or 0))
    if ag:
        p += "; gümüş %s $ (%s)" % (_num(ag["price"]), _pct(ag.get("change") or 0))
    return {"id": "emtia", "h": h, "p": p + ".", "chips": []}


def _item_cb(calendar, today):
    """Ekonomik takvimdeki sonraki merkez bankasi kararlari (TCMB PPK, Fed)."""
    nxt = {}
    for e in calendar or []:
        try:
            d = datetime.strptime(e["date"], "%Y-%m-%d").date()
        except (KeyError, ValueError):
            continue
        if d < today:
            continue
        key = "TCMB" if "TCMB" in e.get("event", "") else ("Fed" if "Fed" in e.get("event", "") else None)
        if key and (key not in nxt or d < nxt[key]):
            nxt[key] = d
    if not nxt:
        return None
    parts = []
    if "Fed" in nxt:
        parts.append("Fed'in sonraki faiz kararı %s" % _dm(nxt["Fed"]))
    if "TCMB" in nxt:
        parts.append("TCMB Para Politikası Kurulu toplantısı %s" % _dm(nxt["TCMB"]))
    return {"id": "mb", "h": "Merkez bankası takvimi", "p": "; ".join(parts) + ".", "chips": []}


def build_print(stocks, macro, xu100, feed_items, names, calendar, now, close_day, edition):
    """Gundem baskisi (tum rakamlar sitenin kendi verisinden). -> dict ya da None."""
    tr = [x for x in (_item_market(stocks, xu100, close_day), _item_sectors(stocks), _item_fx(macro),
                      _item_states(stocks, close_day), _item_kap(feed_items, names, close_day.isoformat())) if x]
    world = [x for x in (_item_us(macro, now), _item_commod(macro, now), _item_cb(calendar, now.date())) if x]
    if len(tr) + len(world) < 3:
        return None
    return {
        "schema_version": 1,
        "date": now.date().isoformat(),
        "date_label": _dm(now.date()),
        "day_label": day_label(now.date()),
        "edition": edition,
        "edition_label": EDITION_LABEL.get(edition, edition),
        "time": now.strftime("%H:%M"),
        "close_day": close_day.isoformat(),
        "groups": [{"name": "Türkiye", "items": tr}, {"name": "Dünya", "items": world}],
        "printed_at": now.strftime("%Y-%m-%dT%H:%M:%S"),
    }


def due_slot(now, printed):
    """Hafta ici; saati gecmis ve henuz basilmamis son baski -> 'sabah'|'aksam'|None.
    printed: basilmis anahtarlar kumesi ('2026-09-24-aksam')."""
    if now.weekday() >= 5:
        return None
    due = None
    for name, hh, mm in PRINT_SLOTS:
        if (now.hour, now.minute) >= (hh, mm):
            due = name
    if due and "%s-%s" % (now.date().isoformat(), due) not in printed:
        return due
    return None


def save_print(doc, base_dir=None):
    base = base_dir or PRINT_DIR
    _atomic_write(os.path.join(base, "%s-%s.json" % (doc["date"], doc["edition"])), doc)
    _atomic_write(os.path.join(base, "latest.json"), doc)


def printed_keys(base_dir=None):
    try:
        return set(n[:-5] for n in os.listdir(base_dir or PRINT_DIR) if re.match(r"^\d{4}-\d{2}-\d{2}-\w+\.json$", n))
    except OSError:
        return set()


_PRINT_CACHE = {}


def load_latest(base_dir=None):
    path = os.path.join(base_dir or PRINT_DIR, "latest.json")
    try:
        mtime = os.path.getmtime(path)
    except OSError:
        return None
    hit = _PRINT_CACHE.get(path)
    if hit and hit[0] == mtime:
        return hit[1]
    try:
        with open(path, encoding="utf-8") as f:
            doc = json.load(f)
    except (OSError, ValueError):
        doc = None
    _PRINT_CACHE[path] = (mtime, doc)
    return doc
