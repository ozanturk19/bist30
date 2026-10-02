"""Faz 12 P2.4 — DQV multi-tier alerting (monitoring-only, non-blocking)

D-13: alarm tek kanal e-posta (send_ops_email); Telegram ve Sentry silindi."""

import os
import smtplib
from email.mime.text import MIMEText
import time
import logging
import threading
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

ALERT_MD_PATH = os.environ.get("DQV_ALERT_PATH", "/root/bist30/ALERT.md")

# DQV event → tier (P0=critical/immediate, P1=hourly-summary)
DQV_TIER = {
    "DQV_BR":       "P1",
    "DQV_CROSS":    "P1",
    "DQV_ANOMALY":  "P1",
    "DQV_EMAIL_QA": "P1",
    "DQV_FROZEN":   "P1",
    "DQV_SV_DATA":  "P0",
    "DQV_SV_MACRO": "P0",
    "DQV_SV_CHART": "P0",
}

# CPO-1155 §2: aynı (event, ticker, tier) tekrar ederse ALERT.md/log
# spam olmaz — pencere içinde bastırılır, ilk görülüşte ve pencere kapanınca
# "+N suppressed" özetiyle geçer. Process-local (worker başına), disk/IPC yok
# — amaç tek bir kronik olayın binlerce satır üretmesini önlemek, kesin
# global tekilleştirme değil.
DEDUP_WINDOW_S = int(os.environ.get("DQV_ALERT_DEDUP_WINDOW_S", "300"))
_dedup_lock = threading.Lock()
_last_emit = {}  # fingerprint -> (last_emit_ts, suppressed_count)


def _classify_severity(default_tier, errors):
    """CPO-1155 §2: sabit P0 yerine flag-bazlı şiddet.

    Yalnızca "None is not of type ..." kalıbı (beklenen alan session-dışı/
    veri-eksik anında null geldiğinde oluşan bilinen drift, ör. CPO-1152/
    1153'teki updated_at) P1'e düşürülür. Başka her "is not of type" hatası
    (ör. array/object bekleyip string gelmesi, gerçek veri bozulması) ve
    required-alan eksikliği gibi yapısal hatalar default_tier'de (P0) kalır
    — kapsamı bilerek dar tutuyoruz, aksi halde gerçek bozulmalar da
    sessizce P1'e düşebilir."""
    if default_tier != "P0" or not errors:
        return default_tier
    for err in errors:
        if not (err.get("message") or "").startswith("None is not of type"):
            return default_tier
    return "P1"


def emit_alert(event: str, detail: str = "", ticker: str = None, errors=None):
    """
    Non-blocking DQV alert. Tier derived from DQV_TIER (default P1),
    downgraded via _classify_severity when `errors` (schema_validator
    error list) indicates non-structural drift.
    P0/P1: ALERT.md append + logger.warning (e-posta yalnız send_ops_email çağıranlarda)
    All exceptions swallowed — never raises.
    """
    try:
        tier = _classify_severity(DQV_TIER.get(event, "P1"), errors)
        fingerprint = (event, ticker, tier)
        now = time.time()
        with _dedup_lock:
            last = _last_emit.get(fingerprint)
            if last is not None and (now - last[0]) < DEDUP_WINDOW_S:
                _last_emit[fingerprint] = (last[0], last[1] + 1)
                return
            suppressed = last[1] if last is not None else 0
            _last_emit[fingerprint] = (now, 0)

        ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
        ticker_tag = f"[{ticker}]" if ticker else ""
        suffix = f" (+{suppressed} suppressed in last {DEDUP_WINDOW_S}s)" if suppressed else ""
        line = f"[{ts}] {tier}{ticker_tag} {event}: {detail}{suffix}"

        logger.warning("ALERT_%s %s%s: %s%s", tier, event, ticker_tag, detail, suffix)
        _append_alert_md(line)
    except Exception as _e:
        logger.warning("emit_alert exception: %s", _e)


def _append_alert_md(line: str):
    try:
        with open(ALERT_MD_PATH, "a", encoding="utf-8") as f:
            f.write(line + "\n")
    except Exception as _e:
        logger.warning("ALERT.md append failed: %s", _e)


def send_ops_email(subject: str, text: str) -> bool:
    """Sistem alarmı e-postası (tek kanal, D-13). Alıcı ADMIN_MAIL
    (varsayılan iletisim@borsapusula.com). SMTP eksik/hata → False, asla raise etmez."""
    host = os.environ.get("SMTP_HOST", "")
    user = os.environ.get("SMTP_USER", "")
    pw = os.environ.get("SMTP_PASS", "")
    if not (host and user and pw):
        return False
    to = os.environ.get("ADMIN_MAIL", "iletisim@borsapusula.com")
    try:
        msg = MIMEText(text, "plain", "utf-8")
        msg["Subject"] = f"[BorsaPusula alarm] {subject}"
        msg["From"] = os.environ.get("SMTP_FROM", "BorsaPusula <noreply@borsapusula.com>")
        msg["To"] = to
        with smtplib.SMTP(host, int(os.environ.get("SMTP_PORT", "587") or 587), timeout=15) as srv:
            srv.ehlo()
            srv.starttls()
            srv.login(user, pw)
            srv.sendmail(user, [to], msg.as_string())
        logger.info("Alarm e-postası gönderildi: %s", subject)
        return True
    except Exception as e:
        logger.warning("Alarm e-postası gönderilemedi (%s): %s", subject, e)
        return False
