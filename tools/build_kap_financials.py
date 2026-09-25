#!/usr/bin/env python3
"""D-40a0: KAP finansal rapor kayitlari -> data/kap_fin/<T>.json (VPS'te DEV1 calistirir).

Kullanim:  python3 tools/build_kap_financials.py [TICKER ...]
           Hisse verilmezse sitenin temel veri evreni (last_fundamentals_cache.json anahtarlari).
Nezaket:   liste istekleri (byCriteria) arasi >= 3 sn, rapor sayfalari >= 2 sn, tek is parcacigi.
           KAP HTTP 429 -> ustel bekleme 15/30/60 dk (log'da gorunur) ve ayni istegi yeniden dener;
           ust uste 6 bekleme sonuc vermezse temiz durur, cikis 2 (ayni komutla kaldigi yerden devam).
Liste:     byCriteria cok-oid tek sorguyla (FR 40, ODA 10 sirket/istek; sonuc 2000 satira dayanirsa
           grup ikiye bolunur): ~1.600 tek-sirket sorgusu yerine ~100. 12 saatten taze hisse dosyasi
           atlanir (--force ile yeniden). Sira: once BIST100 (XU100) uyeleri, sonra kalan evren.
Onbellek:  data/kap_fin/raw/<idx>.html.gz (rapor sayfasi yalniz bilanco/gelir/nakit akis
           tablolariyla; temettu bildirimi tam), data/kap_fin/lists/ (kapanmis yil pencereleri
           kalici, acik pencere her calismada tazelenir), data/kap_fin/yil_sonu_kapanis.json
           (BIST bulteni, yil basina tek indirme). Hisse dosyasi atomik yazilir.
Ag cagrisi yalniz KAP + borsaistanbul.com bulteni; Yahoo/Gemini yok.
"""
from __future__ import annotations

import glob
import gzip
import json
import os
import sys
import tempfile
import time
from datetime import date, datetime, timedelta

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

import requests  # noqa: E402

import kap_financials as kf  # noqa: E402
import official_close  # noqa: E402

OUT = kf.DATA_DIR
RAW = os.path.join(OUT, "raw")
LISTS = os.path.join(OUT, "lists")
CLOSES = os.path.join(OUT, "yil_sonu_kapanis.json")
UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126 Safari/537.36"
MIN_GAP_S = 2.0          # rapor sayfasi (GET) araligi
LIST_GAP_S = 3.0         # byCriteria (POST) araligi: 429 kaynagi bu uc
BACKOFF_MIN = (15, 30, 60)   # 429 ustel bekleme (dk); 60'ta sabit
MAX_429_WAITS = 6        # ust uste sonuc vermeyen bekleme -> KapStop (cikis 2)
MAX_5XX_RETRY = 3
OK_STREAK_RESET = 30     # bu kadar basarili istekten sonra ustel bekleme sifirlanir
LIST_CAP = 2000          # KAP liste API'si tek sorguda en fazla bu kadar satir dondurur
LIST_BATCH = {"FR": 40, "ODA": 10}
FRESH_H = 12             # hisse dosyasi bu saatten tazeyse atlanir (--force ile degil)
YEARS = 5        # son 5 yillik rapor
INTERIMS = 5     # son 5 ara donem raporu
DIV_YEARS = 2    # temettu bildirimleri: onceki + bu yil (son 12 ay + duyurulan taksitler)


class KapStop(Exception):
    """KAP 429/5xx: nazikce dur, sonra devam."""


def atomic_write(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=os.path.dirname(path), prefix=".tmp_")
    with os.fdopen(fd, "wb") as f:
        f.write(data)
    os.replace(tmp, path)


def write_json(path, obj):
    atomic_write(path, json.dumps(obj, ensure_ascii=False, separators=(",", ":")).encode("utf-8"))


class Kap:
    def __init__(self, sleep=time.sleep, clock=time.time):
        self.s = requests.Session()
        self.s.headers.update({"User-Agent": UA})
        self.last = 0.0
        self.count = 0
        self.level = 0       # ardisik 429 bekleme seviyesi (ustel)
        self.ok_streak = 0
        self.sleep = sleep
        self.clock = clock

    def _call(self, method, url, gap=MIN_GAP_S, **kw):
        waits = errs = 0
        while True:
            wait = gap - (self.clock() - self.last)
            if wait > 0:
                self.sleep(wait)
            try:
                r = self.s.request(method, url, timeout=60, **kw)
            finally:
                self.last = self.clock()
                self.count += 1
            if r.status_code == 429:
                waits += 1
                if waits > MAX_429_WAITS:
                    raise KapStop("KAP HTTP 429 (%s) — %d bekleme sonuc vermedi; durduruldu, ayni komutla devam edin" % (url, MAX_429_WAITS))
                self.level += 1
                self.ok_streak = 0
                mins = BACKOFF_MIN[min(self.level, len(BACKOFF_MIN)) - 1]
                print("KAP 429 (%s): %d dk bekleniyor (bekleme #%d, seviye %d, istek %d)" % (
                    url.rsplit("/", 1)[-1], mins, waits, self.level, self.count), flush=True)
                self.sleep(mins * 60)
                continue
            if r.status_code >= 500:
                errs += 1
                if errs > MAX_5XX_RETRY:
                    raise ValueError("KAP HTTP %s: %s" % (r.status_code, url))
                print("KAP HTTP %s (%s): %d sn bekleniyor (deneme %d/%d)" % (
                    r.status_code, url.rsplit("/", 1)[-1], 30 * errs, errs, MAX_5XX_RETRY), flush=True)
                self.sleep(30 * errs)
                continue
            if r.status_code != 200:
                raise ValueError("KAP HTTP %s: %s" % (r.status_code, url))
            self.ok_streak += 1
            if self.ok_streak >= OK_STREAK_RESET:
                self.level = 0
            return r

    def disclosures(self, oids, frm, to, cls):
        """oids: tek oid ya da liste (cok-oid tek sorgu)."""
        if isinstance(oids, str):
            oids = [oids]
        payload = {"fromDate": frm, "toDate": to, "disclosureClass": cls, "subjectList": [],
                   "mkkMemberOidList": list(oids), "inactiveMkkMemberOidList": [], "bdkMemberOidList": [],
                   "fromSrc": False, "disclosureIndexList": []}
        d = self._call("POST", "https://www.kap.org.tr/tr/api/disclosure/members/byCriteria",
                       gap=LIST_GAP_S, json=payload).json()
        if not isinstance(d, list):
            raise ValueError("KAP listesi beklenmedik: %s" % str(d)[:200])
        return d

    def page(self, idx):
        return self._call("GET", "https://www.kap.org.tr/tr/Bildirim/%s" % idx).text


def windows(n_years, today):
    """KAP listesi en fazla 1 yillik aralik kabul ediyor (daha uzunu HTTP 500)."""
    return [("%d-01-01" % y, min("%d-12-31" % y, today.isoformat()))
            for y in range(today.year - n_years + 1, today.year + 1)]


def _keep(items):
    return [x for x in items if x.get("subject") in ("Finansal Rapor", kf.DIVIDEND_SUBJECT)]


def _list_path(tk, cls, frm):
    return os.path.join(LISTS, "%s_%s_%s.json" % (tk, cls, frm[:4]))


def read_list_cache(tk, cls, frm, to):
    """Onbellekteki liste ya da None. Pencere sonu (to) tutmuyorsa gecersiz: kapanmis yil kalici,
    acik yil (to = bugun) yalniz ayni gun gecerli."""
    try:
        with open(_list_path(tk, cls, frm), encoding="utf-8") as f:
            cached = json.load(f)
        if cached.get("to") == to:
            return cached["items"]
    except (OSError, ValueError, AttributeError, KeyError):
        pass
    return None


def cached_list(kap, tk, oid, frm, to, cls, today):
    """Prefetch'in yazdigi onbellek; yoksa tek-sirket sorgusuna duser."""
    items = read_list_cache(tk, cls, frm, to)
    if items is not None:
        return items
    keep = _keep(kap.disclosures(oid, frm, to, cls))
    write_json(_list_path(tk, cls, frm), {"to": to, "items": keep})
    return keep


def _codes(item):
    """Sirket kodlari: stockCodes (sirketin kendi yayini) ve relatedStocks (KAP'in sirket adina yayini,
    stockCodes null; 25.09 AGROT 1515091 toplu-tek karsilastirmasinda bulundu)."""
    out = []
    for key in ("stockCodes", "relatedStocks"):
        out += [c.strip() for c in str(item.get(key) or "").split(",") if c.strip()]
    return out


def fetch_group(kap, tks, oid_of, cls, frm, to):
    """Bir grup sirketin listesini tek sorguyla ceker, sirket basina onbellege yazar. Sonuc
    LIST_CAP'e dayanirsa (KAP fazlasini sessizce keser) grubu ikiye boler. Toplu sonucta hic
    satiri cikmayan sirket yazilmaz (cached_list tek sorguyla dogrular)."""
    items = kap.disclosures([oid_of[t] for t in tks], frm, to, cls)
    if len(items) >= LIST_CAP:
        if len(tks) == 1:
            print("UYARI: %s %s %s tek sirket sonucu %d satira dayandi (kesilmis olabilir)" % (tks[0], cls, frm[:4], len(items)))
        else:
            h = len(tks) // 2
            return (fetch_group(kap, tks[:h], oid_of, cls, frm, to)
                    + fetch_group(kap, tks[h:], oid_of, cls, frm, to))
    by = {t: [] for t in tks}
    for x in items:
        for c in _codes(x):
            if c in by:
                by[c].append(x)
    wrote = 0
    for t in tks:
        if by[t]:
            write_json(_list_path(t, cls, frm), {"to": to, "items": _keep(by[t])})
            wrote += 1
    return [wrote]


def prefetch_lists(kap, tickers, companies, today):
    """Eksik liste onbelleklerini cok-oid sorgularla doldurur; dondurur: (sorgu sayisi, yazilan dosya)."""
    oid_of = {t: companies[t]["mkk"] for t in tickers if companies.get(t, {}).get("mkk")}
    need = {}
    for cls, n in (("FR", YEARS), ("ODA", DIV_YEARS)):
        for frm, to in windows(n, today):
            for t in oid_of:
                if read_list_cache(t, cls, frm, to) is None:
                    need.setdefault((cls, frm, to), []).append(t)
    before, wrote = kap.count, 0
    for (cls, frm, to), tks in sorted(need.items(), key=lambda kv: (kv[0][0] != "FR", kv[0][1])):
        for i in range(0, len(tks), LIST_BATCH[cls]):
            wrote += sum(fetch_group(kap, tks[i:i + LIST_BATCH[cls]], oid_of, cls, frm, to))
        print("  liste %s %s: %d sirket, toplam istek %d" % (cls, frm[:4], len(tks), kap.count), flush=True)
    return kap.count - before, wrote


def cached_page(kap, idx, trim):
    path = os.path.join(RAW, "%s.html.gz" % idx)
    if os.path.exists(path):
        with gzip.open(path, "rt", encoding="utf-8") as f:
            return f.read()
    h = kap.page(idx)
    body = kf.trim_page(h) if trim else h
    if body:  # tablosuz/bos sayfa onbellege yazilmaz (sonraki calismada yeniden denenir)
        atomic_write(path, gzip.compress(body.encode("utf-8")))
    return body


def year_end_closes(today):
    """{yil: {date, closes{T: kapanis}}}: yilin son islem gunu resmi kapanisi (BIST bulteni)."""
    try:
        with open(CLOSES, encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, ValueError):
        data = {}
    changed = False
    for y in range(today.year - YEARS, today.year):
        if str(y) in data:
            continue
        d = date(y, 12, 31)
        for _ in range(10):
            time.sleep(MIN_GAP_S)
            got = official_close.fetch_bulletin(d)
            if got:
                p = official_close.parse_bulletin(got["raw"])
                data[str(y)] = {"date": p["date"], "closes": {t: s["close"] for t, s in p["stocks"].items()}}
                changed = True
                break
            d -= timedelta(days=1)
        else:
            print("UYARI: %d yil sonu bulteni bulunamadi (degerleme bandinda o yil olmayacak)" % y)
    if changed:
        write_json(CLOSES, data)
    return data


def build_ticker(kap, tk, comp, closes, today):
    oid, sector = comp.get("mkk"), comp.get("sector")
    if not oid:
        raise ValueError("universe.json'da mkk oid yok")
    fr = []
    for frm, to in windows(YEARS, today):
        fr += cached_list(kap, tk, oid, frm, to, "FR", today)
    reports = []
    for key, metas in sorted(kf.select_disclosures(fr, YEARS, INTERIMS).items()):
        cands = []
        for m in metas:
            try:
                cands.append(kf.build_report(cached_page(kap, m["idx"], trim=True), m, tk, sector))
            except ValueError as e:
                print("  %s %s idx %s atlandi: %s" % (tk, key, m["idx"], e))
        r = kf.choose_report(cands)
        if r:
            reports.append(r)
    divs = []
    for frm, to in windows(DIV_YEARS, today):
        for x in cached_list(kap, tk, oid, frm, to, "ODA", today):
            if x.get("subject") != kf.DIVIDEND_SUBJECT:
                continue
            meta = {"idx": int(x["disclosureIndex"]), "publish": kf.kap_publish_iso(x.get("publishDate"))}
            divs.append(kf.parse_dividend(cached_page(kap, meta["idx"], trim=False), tk, meta))
    tk_closes = {y: {"date": v["date"], "close": v["closes"][tk]} for y, v in closes.items() if tk in v["closes"]}
    rec = kf.build_record(tk, reports, divs, tk_closes, sector, datetime.now().strftime("%Y-%m-%dT%H:%M"))
    write_json(os.path.join(OUT, "%s.json" % tk), rec)
    return rec


def default_tickers():
    with open(os.path.join(ROOT, "last_fundamentals_cache.json"), encoding="utf-8") as f:
        return sorted(t for t in json.load(f) if t not in ("XU030", "XU100"))


def order_universe(tickers, companies):
    """BIST100 (XU100) uyeleri once, her grup kendi icinde alfabetik."""
    return sorted(tickers, key=lambda t: ("XU100" not in (companies.get(t, {}).get("indices") or []), t))


def fresh_record(tk, now=None):
    """Hisse dosyasi FRESH_H saatten tazeyse kaydi dondurur, degilse None."""
    path = os.path.join(OUT, "%s.json" % tk)
    try:
        if (now or time.time()) - os.path.getmtime(path) < FRESH_H * 3600:
            with open(path, encoding="utf-8") as f:
                return json.load(f)
    except (OSError, ValueError):
        pass
    return None


def count_files():
    return len([p for p in glob.glob(os.path.join(OUT, "*.json")) if p != CLOSES])


def main(argv):
    force = "--force" in argv
    args = [a for a in argv if a != "--force"]
    with open(os.path.join(ROOT, "data", "universe.json"), encoding="utf-8") as f:
        companies = json.load(f)["companies"]
    tickers = [t.upper() for t in args] or order_universe(default_tickers(), companies)
    today = date.today()
    kap = Kap()
    try:
        closes = year_end_closes(today)
    except (requests.RequestException, ValueError) as e:
        print("UYARI: yil sonu kapanislari alinamadi (%s); degerleme bandi bos kalir" % e)
        closes = {}
    t0, done, skipped, failed, summary = time.time(), 0, 0, [], {}
    todo = [t for t in tickers if force or fresh_record(t) is None]
    try:
        if todo:
            n, w = prefetch_lists(kap, todo, companies, today)
            print("liste onbellegi: %d istek, %d dosya yazildi; %d/%d hisse bekliyor, dosya=%d" % (
                n, w, len(todo), len(tickers), count_files()), flush=True)
    except KapStop as e:
        print("DURDU (liste): %s" % e)
        return 2
    except (ValueError, requests.RequestException) as e:
        print("UYARI: toplu liste onbellegi tamamlanamadi (%s); hisse basina tek sorguya duser" % str(e)[:120])
    for i, tk in enumerate(tickers, 1):
        comp = companies.get(tk)
        if not comp:
            failed.append((tk, "universe.json'da yok"))
            continue
        rec = None if force else fresh_record(tk)
        if rec is not None:
            skipped += 1
            summary.setdefault(rec["derived"]["basis"], []).append(tk)
            continue
        try:
            rec = build_ticker(kap, tk, comp, closes, today)
        except KapStop as e:
            print("DURDU (%d/%d, %s): %s" % (i, len(tickers), tk, e))
            print("Tamamlanan %d hisse korunuyor; tekrar calistirinca onbellekten devam eder." % done)
            return 2
        except (ValueError, KeyError, requests.RequestException) as e:
            failed.append((tk, str(e)[:120]))
            continue
        done += 1
        d = rec["derived"]
        summary.setdefault(d["basis"], []).append(tk)
        print("%3d/%d %-6s rapor=%d temettu_bildirim=%d esas=%s son=%s istek=%d dosya=%d %.0fs" % (
            i, len(tickers), tk, len(rec["reports"]), len(rec["dividends"]), d["basis"],
            (d["son_rapor"] or {}).get("donem"), kap.count, count_files(), time.time() - t0), flush=True)
    print("\nBitti: %d hisse uretildi, %d taze atlandi, %d hata, %d KAP istegi, %.0f dk" % (
        done, skipped, len(failed), kap.count, (time.time() - t0) / 60))
    for b, tks in sorted(summary.items(), key=lambda kv: str(kv[0])):
        print("  esas %-13s %3d  %s" % (b, len(tks), " ".join(tks) if b in ("nominal", "yabanci_para", "sigorta") else ""))
    for tk, why in failed:
        print("  HATA %s: %s" % (tk, why))
    return 1 if failed and not (done or skipped) else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
