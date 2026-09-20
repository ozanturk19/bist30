#!/usr/bin/env python3
"""K-H — hukuki metin / "Son güncelleme" tarih senkron kapisi.

BULGUNUN KOKENI (20.09, CPO turu, commit 4937090): /gizlilik Eylul'de YENI
veri kategorileri (bp_sub cerezi, bildirim sikligi, portfoy bulut senkronu,
iletisim formu) ve YENI ucuncu taraflar (Google Fonts, Cloudflare Analytics)
kazandi; /yasal sinyal hesaplama + veri gecikmesi ifadelerini degistirdi.
Ikisi de "Son guncelleme: **Agustos** 2026" demeye devam ediyordu. /gizlilik'in
kendi son bolumu "Onemli degisiklikler bu sayfada duyurulacaktir" diye soz
veriyor -- tarih o sozun kullaniciya gorunen TEK kanitidir. KVKK Madde 10
aydinlatma yukumlulugu acisindan bayat tarih, metnin kendisi kadar onemli.

NEDEN ONCEKI 11 KAT GOREMEZ: hepsi KODA bakar (Jinja sozdizimi, token, ham
hex, kontrast, cascade sirasi, cache-bust referansi). Bu bulgu kodda degil --
iki METIN alani arasindaki ANLAMSAL sozlesmede. Olculmesi gereken sey
"prose degisti mi" ve "tarih onunla birlikte degisti mi".

OLCUT
  Her hukuki sablonun <main> icindeki DUZ METNI (etiket/oznitelik/Jinja/
  yorum/script haric, bosluk normalize) hash'lenir ve baseline'da tutulur.
  - metin hash'i AYNI                       -> PASS (dokunulmamis)
  - metin degisti + tarih de degisti        -> PASS, baseline tazelenir
  - metin degisti + tarih AYNI              -> FAIL  (bu turun bulgusu)

  Stil/etiket-only duzenlemeler metin hash'ini DEGISTIRMEZ, yani bir Data-Art
  gecisi bu kapiyi tetiklemez. "Son guncelleme" satirinin KENDISI metinden
  cikarilir; aksi halde tarihi degistirmek metni de degistirir ve kapi
  kendi kendini besleyen bir donguye girerdi.

KAPSAM SINIRI (acikca yazili): yalnizca asagidaki LEGAL_PAGES listesi
taranir ve yalnizca <main> bolgesi olculur. Sayfanin hukuki DOGRULUGUNU
denetlemez -- yalnizca "prose degisti ama tarih donmus kaldi" sinifini kapatir.
"""
import hashlib
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BASELINE = ROOT / "tools" / "legal_text_baseline.json"

LEGAL_PAGES = ["templates/gizlilik.html", "templates/yasal.html"]

_MAIN_RE = re.compile(r"<main\b[^>]*>(.*?)</main>", re.S | re.I)
_UPDATED_RE = re.compile(r'<p[^>]*class="[^"]*\bupdated\b[^"]*"[^>]*>(.*?)</p>', re.S | re.I)
_DROP_BLOCKS = re.compile(r"<(script|style)\b.*?</\1>", re.S | re.I)
_HTML_COMMENT = re.compile(r"<!--.*?-->", re.S)
_JINJA = re.compile(r"\{\{.*?\}\}|\{%.*?%\}|\{#.*?#\}", re.S)
_TAG = re.compile(r"<[^>]+>")


def extract(path: Path):
    """(<main> icindeki duz metin, 'Son guncelleme' satirinin ham metni)."""
    raw = path.read_text(encoding="utf-8")
    m = _MAIN_RE.search(raw)
    if not m:
        return None, None
    body = m.group(1)

    upd_m = _UPDATED_RE.search(body)
    updated = None
    if upd_m:
        updated = _norm(_strip(upd_m.group(1)))
        body = body[: upd_m.start()] + body[upd_m.end() :]

    return _norm(_strip(body)), updated


def _strip(s: str) -> str:
    s = _DROP_BLOCKS.sub(" ", s)
    s = _HTML_COMMENT.sub(" ", s)
    s = _JINJA.sub(" ", s)
    s = _TAG.sub(" ", s)
    return s


def _norm(s: str) -> str:
    return re.sub(r"\s+", " ", s).strip()


def main() -> int:
    write = "--no-write" not in sys.argv
    baseline = json.loads(BASELINE.read_text(encoding="utf-8")) if BASELINE.exists() else {}
    updated_baseline = False
    failures = []

    for rel in LEGAL_PAGES:
        path = ROOT / rel
        if not path.exists():
            failures.append(f"{rel}: dosya yok (LEGAL_PAGES listesi bayat)")
            continue
        text, updated = extract(path)
        if text is None:
            failures.append(f"{rel}: <main> bulunamadi")
            continue
        if updated is None:
            failures.append(f'{rel}: `<p class="updated">` ("Son guncelleme") satiri yok')
            continue

        digest = hashlib.sha256(text.encode("utf-8")).hexdigest()
        prev = baseline.get(rel)

        if prev is None:
            baseline[rel] = {"text_sha256": digest, "updated": updated}
            updated_baseline = True
            print(f"  · {rel}: baseline ILK KEZ yazildi ({updated})")
            continue

        if prev["text_sha256"] == digest:
            continue

        if prev["updated"] != updated:
            baseline[rel] = {"text_sha256": digest, "updated": updated}
            updated_baseline = True
            print(f'  · {rel}: metin degisti VE tarih tazelendi ("{prev["updated"]}" -> "{updated}") — baseline guncellendi')
        else:
            failures.append(
                f'{rel}: <main> metni degisti ama "Son guncelleme" hala "{updated}". '
                f"Hukuki metin degistiginde tarih de guncellenmeli (KVKK m.10 / sayfanin "
                f'kendi "degisiklikler burada duyurulacaktir" sozu).'
            )

    if updated_baseline and write and not failures:
        BASELINE.write_text(
            json.dumps(baseline, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        print(f"  · baseline yazildi: {BASELINE.relative_to(ROOT)} (commit'e dahil et)")

    if failures:
        for f in failures:
            print(f"  FAIL {f}")
        return 1

    print(f"  {len(LEGAL_PAGES)} hukuki sayfa: metin/tarih senkron")
    return 0


if __name__ == "__main__":
    sys.exit(main())
