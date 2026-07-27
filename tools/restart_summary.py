"""Restart frekans özeti — CPO-1128 (4) revize.

Tek başına ALERT.md'ye güvenmek yanlış: health_cron.sh'ın AUTO-RESTART
dalı (bu patch'ten önce) hiçbir yere KIRMIZI yazmıyordu, tek üretici
smoke-watch.sh idi. Bu yüzden restart sayımı üç kaynağı BİRLİKTE okur:

  1. /var/log/bist30_health.log (+ rotasyonlu .1 / .N.gz) — health_cron.sh
     "AUTO-RESTART triggered" satırları. Tarih formatı GNU `date` çıktısı;
     tuzak: bazı sistem locale'lerinde 12 saatlik AM/PM basılıyor
     ("Sun Jul 26 08:38:31 PM UTC 2026") — 24 saatlik regex ile grep
     atmak bu satırları KAÇIRIR, "restart yok" yanılgısına yol açar.
  2. ALERT.md "### RESTART-AUTO [...]" — smoke-watch.sh kaynaklı.
  3. ALERT.md "### RESTART-AUTO-HEALTHCRON [...]" — health_cron.sh'ın
     (bu patch sonrası) kendi yazdığı satır.

health_cron.sh artık HEM log'a HEM ALERT.md'ye yazıyor (aynı olay) —
bu yüzden (1) ve (3) zaman damgası ±MERGE_WINDOW_SEC içinde çakışırsa
TEK olay sayılır (dedup), yoksa (patch öncesi tarihsel kayıtlarda
olduğu gibi) (1) tek başına sayılır.

No global state, dış bağımlılık yok (stdlib only) — VPS venv veya
system python3 fark etmeksizin çalışır.
"""

import argparse
import gzip
import json
import re
from datetime import datetime, timedelta, timezone

MERGE_WINDOW_SEC = 120
EVENING_BAND_START = (16, 30)  # TR saat, dahil
EVENING_BAND_END = (21, 20)  # TR saat, dahil

_MONTHS = {
    m: i + 1
    for i, m in enumerate(
        [
            "Jan", "Feb", "Mar", "Apr", "May", "Jun",
            "Jul", "Aug", "Sep", "Oct", "Nov", "Dec",
        ]
    )
}

# "Sun Jul 26 08:38:31 PM UTC 2026" veya "Sun Jul 26 20:38:31 UTC 2026"
_HEALTHLOG_DATE_RE = re.compile(
    r"^\w{3}\s+(?P<mon>\w{3})\s+(?P<day>\d{1,2})\s+"
    r"(?P<hh>\d{1,2}):(?P<mm>\d{2}):(?P<ss>\d{2})"
    r"(?:\s+(?P<ampm>AM|PM))?\s+\S+\s+(?P<year>\d{4})$"
)
_HEALTHLOG_LINE_RE = re.compile(
    r"^(?P<ts>.+?)\s+AUTO-RESTART triggered after (?P<fails>\d+) fails\s*$"
)

# "### RESTART-AUTO [2026-07-25 21:40:01 TR]"
_ALERT_HEADER_RE = re.compile(
    r"^### (?P<tag>RESTART-AUTO(?:-HEALTHCRON)?) \["
    r"(?P<y>\d{4})-(?P<m>\d{2})-(?P<d>\d{2}) "
    r"(?P<hh>\d{2}):(?P<mm>\d{2}):(?P<ss>\d{2}) TR\]\s*$"
)

TR_OFFSET = timedelta(hours=3)


def _parse_healthlog_ts(raw: str):
    m = _HEALTHLOG_DATE_RE.match(raw.strip())
    if not m:
        return None
    hh = int(m.group("hh"))
    ampm = m.group("ampm")
    if ampm:
        if ampm == "AM":
            hh = 0 if hh == 12 else hh
        else:  # PM
            hh = hh if hh == 12 else hh + 12
    mon = _MONTHS.get(m.group("mon"))
    if mon is None:
        return None
    try:
        return datetime(
            int(m.group("year")), mon, int(m.group("day")),
            hh, int(m.group("mm")), int(m.group("ss")),
            tzinfo=timezone.utc,
        )
    except ValueError:
        return None


def _read_lines(path):
    try:
        if path.endswith(".gz"):
            with gzip.open(path, "rt", errors="replace") as f:
                return f.readlines()
        with open(path, "r", errors="replace") as f:
            return f.readlines()
    except FileNotFoundError:
        return []


def parse_health_log_events(paths):
    """paths: bist30_health.log + rotasyonlu kopyalar (herhangi bir sırada)."""
    events = []
    for path in paths:
        for line in _read_lines(path):
            m = _HEALTHLOG_LINE_RE.match(line.rstrip("\n"))
            if not m:
                continue
            ts = _parse_healthlog_ts(m.group("ts"))
            if ts is None:
                continue
            events.append(
                {
                    "ts": ts,
                    "source": "HEALTHCRON-LOG",
                    "fails": int(m.group("fails")),
                    "file": path,
                }
            )
    return events


def parse_alert_md_events(path):
    events = []
    for line in _read_lines(path):
        m = _ALERT_HEADER_RE.match(line.rstrip("\n"))
        if not m:
            continue
        ts_tr = datetime(
            int(m.group("y")), int(m.group("m")), int(m.group("d")),
            int(m.group("hh")), int(m.group("mm")), int(m.group("ss")),
        )
        ts_utc = (ts_tr - TR_OFFSET).replace(tzinfo=timezone.utc)
        tag = m.group("tag")
        source = "SMOKE-WATCH" if tag == "RESTART-AUTO" else "HEALTHCRON-ALERT"
        events.append({"ts": ts_utc, "source": source, "file": path})
    return events


def _is_evening_band(ts_utc):
    tr = ts_utc + TR_OFFSET
    start = tr.replace(
        hour=EVENING_BAND_START[0], minute=EVENING_BAND_START[1], second=0
    )
    end = tr.replace(hour=EVENING_BAND_END[0], minute=EVENING_BAND_END[1], second=59)
    return start <= tr <= end


def merge_events(health_log_events, alert_events):
    """HEALTHCRON-LOG + HEALTHCRON-ALERT aynı restart'sa tek olaya birleştir.
    SMOKE-WATCH her zaman ayrı olay (farklı tetikleyici/script)."""
    smoke = [e for e in alert_events if e["source"] == "SMOKE-WATCH"]
    hc_alert = [e for e in alert_events if e["source"] == "HEALTHCRON-ALERT"]
    hc_alert_used = [False] * len(hc_alert)

    merged = []
    for hle in health_log_events:
        match_idx = None
        for i, ae in enumerate(hc_alert):
            if hc_alert_used[i]:
                continue
            if abs((hle["ts"] - ae["ts"]).total_seconds()) <= MERGE_WINDOW_SEC:
                match_idx = i
                break
        if match_idx is not None:
            hc_alert_used[match_idx] = True
            merged.append(
                {
                    "ts": hle["ts"],
                    "sources": ["HEALTHCRON-LOG", "HEALTHCRON-ALERT"],
                    "fails": hle.get("fails"),
                }
            )
        else:
            merged.append(
                {"ts": hle["ts"], "sources": ["HEALTHCRON-LOG"], "fails": hle.get("fails")}
            )

    # Patch öncesi ALERT'te olup log'da eşleşmeyen HEALTHCRON-ALERT olmamalı
    # (log her zaman yazılıyor) ama savunmacı davran — eşleşmeyeni de ekle.
    for i, ae in enumerate(hc_alert):
        if not hc_alert_used[i]:
            merged.append({"ts": ae["ts"], "sources": ["HEALTHCRON-ALERT"], "fails": None})

    for se in smoke:
        merged.append({"ts": se["ts"], "sources": ["SMOKE-WATCH"], "fails": None})

    merged.sort(key=lambda e: e["ts"])
    return merged


def summarize(events, since=None):
    if since is not None:
        events = [e for e in events if e["ts"] >= since]
    per_day = {}
    evening_count = 0
    for e in events:
        tr = e["ts"] + TR_OFFSET
        day_key = tr.strftime("%Y-%m-%d")
        per_day[day_key] = per_day.get(day_key, 0) + 1
        if _is_evening_band(e["ts"]):
            evening_count += 1
    return {
        "total": len(events),
        "per_day_tr": dict(sorted(per_day.items())),
        "evening_band_16_30_21_20_tr": evening_count,
        "events": [
            {
                "ts_utc": e["ts"].strftime("%Y-%m-%d %H:%M:%S UTC"),
                "ts_tr": (e["ts"] + TR_OFFSET).strftime("%Y-%m-%d %H:%M:%S TR"),
                "sources": e["sources"],
            }
            for e in events
        ],
    }


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument(
        "--health-log",
        action="append",
        default=[],
        help="bist30_health.log veya rotasyon dosyası (tekrarlanabilir)",
    )
    ap.add_argument(
        "--alert-md", default="/root/ops/ALERT.md", help="ALERT.md yolu"
    )
    ap.add_argument(
        "--days", type=int, default=7, help="son N gün ile sınırla (varsayılan 7)"
    )
    ap.add_argument("--json", action="store_true", help="JSON çıktı")
    args = ap.parse_args()

    health_paths = args.health_log or [
        "/var/log/bist30_health.log",
        "/var/log/bist30_health.log.1",
        "/var/log/bist30_health.log.2.gz",
        "/var/log/bist30_health.log.3.gz",
        "/var/log/bist30_health.log.4.gz",
        "/var/log/bist30_health.log.5.gz",
        "/var/log/bist30_health.log.6.gz",
        "/var/log/bist30_health.log.7.gz",
    ]

    health_events = parse_health_log_events(health_paths)
    alert_events = parse_alert_md_events(args.alert_md)
    merged = merge_events(health_events, alert_events)

    since = None
    if args.days > 0:
        now = datetime.now(timezone.utc)
        since = now - timedelta(days=args.days)

    result = summarize(merged, since=since)

    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return

    print(f"Restart özeti — son {args.days} gün (kaynak: health_cron.log[+rotasyon] + ALERT.md)")
    print(f"Toplam restart: {result['total']}")
    print(f"Akşam bandı (16:30-21:20 TR): {result['evening_band_16_30_21_20_tr']}")
    print("Gün başına:")
    for day, count in result["per_day_tr"].items():
        print(f"  {day}: {count}")
    print("Olaylar:")
    for e in result["events"]:
        print(f"  {e['ts_tr']} ({e['ts_utc']}) sources={'+'.join(e['sources'])}")


if __name__ == "__main__":
    main()
