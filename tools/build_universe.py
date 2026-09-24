#!/usr/bin/env python3
"""D-46: KAP'tan evren dosyası (data/universe.json) üretir.

Kaynak (tek GET, Next.js RSC gömülü JSON): KAP Endeksler + Sektörler.
Çıktı (VPS: data/universe.json; repo tohumu: universe_seed.json): kod -> unvan/resmi sektör/ana sektör, endeks üyelikleri (XU030/XU050/XU100/
XYLDZ/XUTUM). Atomik yazılır; doğrulama kırmızıysa mevcut dosya DEĞİŞMEZ (exit 1).

Kullanım: python3 tools/build_universe.py [--out data/universe.json] [--dry-run]
Cron (VPS, Pzt 07:00 TR): bkz. plan D-46. Dönem geçişi (01.10) elle bir koşu ister.
"""
import argparse
import json
import os
import re
import sys
import tempfile
import time
import urllib.request

KAP = "https://www.kap.org.tr/tr/"
UA = {"User-Agent": "Mozilla/5.0 (BorsaPusula universe builder)"}
INDEX_CODES = ("XU030", "XU050", "XU100", "XYLDZ", "XUTUM")
# beklenen boyut aralıkları (bozuk sayfa/format değişimi = dosya yazılmaz)
EXPECT = {"XU030": (28, 32), "XU050": (48, 52), "XU100": (98, 102),
          "XYLDZ": (200, 400), "XUTUM": (450, 700)}

# Canlı sitede yanlış görünen adlar (23.09 ölçümü, KAP üye unvanı). Dosyaya
# `names_override` olarak yazılır; app.py STOCK_NAMES üzerine uygular.
NAME_FIX = {
    'ALKLC': 'Altınkılıç Gıda ve Süt', 'GENTS': 'Gentaş Dekoratif Yüzeyler', 'GMTAS': 'Gimat Mağazacılık',
    'IEYHO': 'Işıklar Enerji ve Yapı Holding', 'LRSHO': 'Loras Holding', 'MPARK': 'MLP Sağlık Hizmetleri',
    'MRGYO': 'Martı GYO', 'PRKAB': 'Türk Prysmian Kablo', 'TUREX': 'Tureks Turizm', 'EMKEL': 'Emek Elektrik Endüstrisi',
    'GESAN': 'Girişim Elektrik', 'AKSEN': 'Aksa Enerji', 'TCKRC': 'Kıraç Galvaniz', 'PASEU': 'Pasifik Eurasia Lojistik',
    'HATSN': 'Hat-San Gemi İnşaa', 'BINHO': '1000 Yatırımlar Holding', 'PSGYO': 'Pasifik GYO', 'EUREN': 'Europen Endüstri',
    'DERHL': 'Derlüks Yatırım Holding', 'TABGD': 'TAB Gıda',
}


def _payload(page, timeout=40):
    req = urllib.request.Request(KAP + page, headers=UA)
    html = urllib.request.urlopen(req, timeout=timeout).read().decode("utf-8", "replace")
    parts = re.findall(r'self\.__next_f\.push\(\[1,"(.*?)"\]\)</script>', html, flags=re.S)
    if not parts:
        raise RuntimeError(f"{page}: gömülü veri bulunamadı")
    return "".join(json.loads('"' + p + '"') for p in parts)


def _objects(text, start_re):
    dec = json.JSONDecoder()
    for m in re.finditer(start_re, text):
        try:
            obj, _ = dec.raw_decode(text, m.start())
        except ValueError:
            continue
        yield obj


def parse_indices(text):
    out = {}
    dec = json.JSONDecoder()
    for code in INDEX_CODES:
        m = re.search(r'"code":"%s","content":\[' % code, text)
        if not m:
            continue
        arr, _ = dec.raw_decode(text, m.end() - 1)
        out[code] = [(o["stockCode"], o.get("title", ""), o.get("mkkMemberOid", "")) for o in arr]
    return out


def parse_sectors(text):
    sec, main = {}, {}
    for o in _objects(text, r'\{"sectorName"'):
        if o.get("stockCode"):
            sec[o["stockCode"]] = o["sectorName"]
    for o in _objects(text, r'\{"mainSectorName"'):
        if o.get("stockCode"):
            main[o["stockCode"]] = o["mainSectorName"]
    return sec, main


def build():
    idx = parse_indices(_payload("Endeksler"))
    sec, main = parse_sectors(_payload("Sektorler"))
    problems = []
    for code, (lo, hi) in EXPECT.items():
        n = len(idx.get(code, []))
        if not lo <= n <= hi:
            problems.append(f"{code}: {n} üye (beklenen {lo}-{hi})")
    if not (450 <= len(sec) <= 800):
        problems.append(f"sektör eşlemesi {len(sec)} kod (beklenen 450-800)")
    if problems:
        raise RuntimeError("; ".join(problems))
    companies = {}
    for code, members in idx.items():
        for sc, title, oid in members:
            c = companies.setdefault(sc, {"title": title, "mkk": oid, "indices": []})
            c["indices"].append(code)
    for sc, c in companies.items():
        c["sector"] = sec.get(sc)
        c["main_sector"] = main.get(sc)
    return {
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "source": "kap.org.tr Endeksler + Sektorler",
        "indices": {k: [m[0] for m in v] for k, v in idx.items()},
        "companies": companies,
        "names_override": NAME_FIX,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=os.path.join(os.path.dirname(__file__), "..", "data", "universe.json"))
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    try:
        data = build()
    except Exception as e:  # noqa: BLE001 — mevcut dosya korunur
        print(f"UNIVERSE FAIL: {e}", file=sys.stderr)
        return 1
    summary = {k: len(v) for k, v in data["indices"].items()}
    print("UNIVERSE OK", summary, "companies", len(data["companies"]))
    if a.dry_run:
        return 0
    out = os.path.abspath(a.out)
    os.makedirs(os.path.dirname(out), exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=os.path.dirname(out), suffix=".tmp")
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=1, sort_keys=True)
    os.replace(tmp, out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
