"""SEO9 #6 (CPO-1194/1201/1206) — nginx 5xx-oranı görünürlüğü.

Bugüne kadar restart/deploy kaynaklı 5xx patlamaları ALERT.md'ye hiç
düşmüyordu (CPO-1206 §8: "bugünkü 12 restart 0 alarm üretti"). Bu modül
per-vhost access log'unu (SEO9 #2'de eklenen `seos9` log_format, $status +
$host alanlarını taşıyor) trailing pencerede tarar, 5xx sayısı eşiği aşarsa
P1 ALERT.md satırı üretir. Saf fonksiyonlar (test edilebilir) + ince CLI.
"""

import datetime
import re
import sys

_MONTHS = {
    "Jan": 1, "Feb": 2, "Mar": 3, "Apr": 4, "May": 5, "Jun": 6,
    "Jul": 7, "Aug": 8, "Sep": 9, "Oct": 10, "Nov": 11, "Dec": 12,
}

# nginx combined + seo9 eki: [$time_local] "$request" $status ...
# time_local sunucu yerel saatidir; VPS UTC+0000 çalışıyor (CPO-1206 örnek
# satırlarında offset hep +0000), o yüzden offset'i ayrıca çevirmiyoruz —
# çevirmek gerekirse offset grubu zaten yakalanıyor, ileride genişletilebilir.
_LINE_RE = re.compile(
    r'\[(\d{2})/(\w{3})/(\d{4}):(\d{2}):(\d{2}):(\d{2}) ([+-]\d{4})\]'
    r' "[^"]*" (\d{3})'
)

DEFAULT_LOG_PATH = "/var/log/nginx/borsapusula-access.log"
DEFAULT_WINDOW_MINUTES = 5
DEFAULT_THRESHOLD_ABS = 3
ALERT_MD_PATH = "/root/bist30/ALERT.md"
STATE_LOG_PATH = "/root/bist30/logs/nginx_5xx_monitor.log"


def parse_line(line):
    """Tek log satırından (utc_datetime, status_int) döner, eşleşmezse None."""
    m = _LINE_RE.search(line)
    if not m:
        return None
    day, mon_abbr, year, hh, mm, ss, offset = m.group(1, 2, 3, 4, 5, 6, 7)
    month = _MONTHS.get(mon_abbr)
    if month is None:
        return None
    try:
        naive = datetime.datetime(
            int(year), month, int(day), int(hh), int(mm), int(ss)
        )
    except ValueError:
        return None
    offset_min = int(offset[0] + offset[1:3]) * 60 + int(offset[0] + offset[3:5])
    tz = datetime.timezone(datetime.timedelta(minutes=offset_min))
    aware = naive.replace(tzinfo=tz)
    utc_dt = aware.astimezone(datetime.timezone.utc)
    status = int(m.group(8))
    return utc_dt, status


def parse_window(lines, now_utc, window_minutes=DEFAULT_WINDOW_MINUTES):
    """Trailing pencerede (total, five_xx, five_xx_by_status) döner.

    lines: log satırları (herhangi bir iterable — dosyanın tamamı olmak
    zorunda değil, çağıran son N satırı tail'leyip verebilir).
    """
    cutoff = now_utc - datetime.timedelta(minutes=window_minutes)
    total = 0
    five_xx = 0
    by_status = {}
    for line in lines:
        parsed = parse_line(line)
        if parsed is None:
            continue
        ts, status = parsed
        if ts < cutoff or ts > now_utc:
            continue
        total += 1
        if 500 <= status <= 599:
            five_xx += 1
            by_status[status] = by_status.get(status, 0) + 1
    return total, five_xx, by_status


def should_alert(five_xx, threshold_abs=DEFAULT_THRESHOLD_ABS):
    """Basit mutlak-eşik kararı — düşük trafikli pencerelerde oran yanıltır
    (ör. 1 istek 1 hata = %100 ama tek olay), mutlak sayım restart kümesini
    daha güvenilir yakalar (CPO-1206 §8 örneği: kısa restart'ta birkaç 5xx)."""
    return five_xx >= threshold_abs


def format_alert_line(now_utc, total, five_xx, by_status, window_minutes):
    status_summary = ",".join(
        f"{code}x{count}" for code, count in sorted(by_status.items())
    )
    now_str = now_utc.strftime("%Y-%m-%d %H:%M:%S")
    return (
        f"[{now_str} UTC] P1 NGINX_5XX: son {window_minutes}dk pencerede "
        f"5xx={five_xx}/{total} istek ({status_summary})\n"
    )


def format_state_line(now_utc, total, five_xx, alerted):
    now_str = now_utc.strftime("%Y-%m-%d %H:%M:%S")
    return (
        f"{now_str} UTC | NGINX_5XX | total={total} five_xx={five_xx} "
        f"alerted={str(alerted).lower()}\n"
    )


def _tail_lines(path, max_lines=8000):
    try:
        with open(path, "r", errors="replace") as f:
            lines = f.readlines()
    except OSError:
        return []
    return lines[-max_lines:]


def run(
    log_path=DEFAULT_LOG_PATH,
    alert_md_path=ALERT_MD_PATH,
    state_log_path=STATE_LOG_PATH,
    window_minutes=DEFAULT_WINDOW_MINUTES,
    threshold_abs=DEFAULT_THRESHOLD_ABS,
    now_utc=None,
):
    now_utc = now_utc or datetime.datetime.now(datetime.timezone.utc)
    lines = _tail_lines(log_path)
    total, five_xx, by_status = parse_window(lines, now_utc, window_minutes)
    alerted = should_alert(five_xx, threshold_abs)

    try:
        with open(state_log_path, "a") as f:
            f.write(format_state_line(now_utc, total, five_xx, alerted))
    except OSError:
        pass

    if alerted:
        try:
            with open(alert_md_path, "a") as f:
                f.write(format_alert_line(now_utc, total, five_xx, by_status, window_minutes))
        except OSError:
            pass

    return total, five_xx, alerted


if __name__ == "__main__":
    run()
    sys.exit(0)
