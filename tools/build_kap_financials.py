#!/usr/bin/env python3
"""D-40a0: KAP finansal rapor kayitlari -> data/kap_fin/<T>.json (VPS'te DEV1 calistirir).

Kullanim:  python3 tools/build_kap_financials.py [TICKER ...]
           Hisse verilmezse sitenin temel veri evreni (last_fundamentals_cache.json anahtarlari).
Nezaket:   istekler arasi >= 2 sn, tek is parcacigi. KAP HTTP 429/5xx -> temiz durur, cikis 2;
           ayni komut yeniden calistirilinca kaldigi yerden devam eder.
Onbellek:  data/kap_fin/raw/<idx>.html.gz (rapor sayfasi yalniz bilanco/gelir/nakit akis
           tablolariyla; temettu bildirimi tam), data/kap_fin/lists/ (kapanmis yil pencereleri
           kalici, acik pencere her calismada tazelenir), data/kap_fin/yil_sonu_kapanis.json
           (BIST bulteni, yil basina tek indirme). Hisse dosyasi atomik yazilir.
Ag cagrisi yalniz KAP + borsaistanbul.com bulteni; Yahoo/Gemini yok.
"""
from __future__ import annotations

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
MIN_GAP_S = 2.0
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
    def __init__(self):
        self.s = requests.Session()
        self.s.headers.update({"User-Agent": UA})
        self.last = 0.0
        self.count = 0

    def _call(self, method, url, **kw):
        wait = MIN_GAP_S - (time.time() - self.last)
        if wait > 0:
            time.sleep(wait)
        try:
            r = self.s.request(method, url, timeout=60, **kw)
        finally:
            self.last = time.time()
            self.count += 1
        if r.status_code == 429 or r.status_code >= 500:
            raise KapStop("KAP HTTP %s (%s) — durduruldu; biraz sonra ayni komutla devam edin" % (r.status_code, url))
        if r.status_code != 200:
            raise ValueError("KAP HTTP %s: %s" % (r.status_code, url))
        return r

    def disclosures(self, oid, frm, to, cls):
        payload = {"fromDate": frm, "toDate": to, "disclosureClass": cls, "subjectList": [],
                   "mkkMemberOidList": [oid], "inactiveMkkMemberOidList": [], "bdkMemberOidList": [],
                   "fromSrc": False, "disclosureIndexList": []}
        d = self._call("POST", "https://www.kap.org.tr/tr/api/disclosure/members/byCriteria", json=payload).json()
        if not isinstance(d, list):
            raise ValueError("KAP listesi beklenmedik: %s" % str(d)[:200])
        return d

    def page(self, idx):
        return self._call("GET", "https://www.kap.org.tr/tr/Bildirim/%s" % idx).text


def windows(n_years, today):
    """KAP listesi en fazla 1 yillik aralik kabul ediyor (daha uzunu HTTP 500)."""
    return [("%d-01-01" % y, min("%d-12-31" % y, today.isoformat()))
            for y in range(today.year - n_years + 1, today.year + 1)]


def cached_list(kap, tk, oid, frm, to, cls, today):
    """Kapanmis yil penceresi (to < bugun) bir kez cekilir; acik pencere her calismada."""
    path = os.path.join(LISTS, "%s_%s_%s.json" % (tk, cls, frm[:4]))
    if to < today.isoformat():
        try:
            with open(path, encoding="utf-8") as f:
                cached = json.load(f)
            if cached.get("to") == to:
                return cached["items"]
        except (OSError, ValueError, AttributeError):
            pass
    items = kap.disclosures(oid, frm, to, cls)
    keep = [x for x in items if x.get("subject") in ("Finansal Rapor", kf.DIVIDEND_SUBJECT)]
    write_json(path, {"to": to, "items": keep})
    return keep


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


def main(argv):
    with open(os.path.join(ROOT, "data", "universe.json"), encoding="utf-8") as f:
        companies = json.load(f)["companies"]
    tickers = [t.upper() for t in argv] or default_tickers()
    today = date.today()
    kap = Kap()
    try:
        closes = year_end_closes(today)
    except (requests.RequestException, ValueError) as e:
        print("UYARI: yil sonu kapanislari alinamadi (%s); degerleme bandi bos kalir" % e)
        closes = {}
    t0, done, failed, summary = time.time(), 0, [], {}
    for i, tk in enumerate(tickers, 1):
        comp = companies.get(tk)
        if not comp:
            failed.append((tk, "universe.json'da yok"))
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
        print("%3d/%d %-6s rapor=%d temettu_bildirim=%d esas=%s son=%s istek=%d %.0fs" % (
            i, len(tickers), tk, len(rec["reports"]), len(rec["dividends"]), d["basis"],
            (d["son_rapor"] or {}).get("donem"), kap.count, time.time() - t0), flush=True)
    print("\nBitti: %d hisse, %d hata, %d KAP istegi, %.0f dk" % (done, len(failed), kap.count, (time.time() - t0) / 60))
    for b, tks in sorted(summary.items(), key=lambda kv: str(kv[0])):
        print("  esas %-13s %3d  %s" % (b, len(tks), " ".join(tks) if b in ("nominal", "yabanci_para", "sigorta") else ""))
    for tk, why in failed:
        print("  HATA %s: %s" % (tk, why))
    return 1 if failed and not done else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
