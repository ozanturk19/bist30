"""Sağlık alarmı → admin maile bildirim."""
import os, sys, smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from datetime import datetime

ALARM_TYPE = sys.argv[1] if len(sys.argv) > 1 else "ALARM"   # ALARM | RESOLVED
ADMIN_EMAIL = "ozan-turk19@hotmail.com"  # Senior dev mail

# .env yükle
env = {}
try:
    with open('/root/bist30/.env') as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('#') or '=' not in line: continue
            k, v = line.split('=', 1)
            env[k.strip()] = v.strip()
except Exception:
    sys.exit(0)

if not env.get("SMTP_HOST") or not env.get("SMTP_PASS"):
    sys.exit(0)

now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

if ALARM_TYPE == "RESOLVED":
    subject = "✅ BorsaPusula — Site Sağlıklı (RESOLVED)"
    body = f"""<html><body style='font-family:system-ui,sans-serif;background:#0e0e12;color:#e5e1e4;padding:30px'>
<h2 style='color:#00e290'>✅ Site Sağlığa Kavuştu</h2>
<p>Önceki alarm <strong>çözüldü</strong>. Smoke test başarılı.</p>
<p style='color:#909097;font-size:13px'>Tarih: {now}</p>
</body></html>"""
else:
    subject = "🚨 BorsaPusula — KRİTİK: 3+ Ardışık Sağlık Fail"
    body = f"""<html><body style='font-family:system-ui,sans-serif;background:#0e0e12;color:#e5e1e4;padding:30px'>
<h2 style='color:#f85149'>🚨 SİTE BOZUK — Acil Müdahale</h2>
<p><strong>3 ardışık smoke test fail</strong>. Site şu an muhtemelen down.</p>
<ul>
  <li>Tarih: <strong>{now}</strong></li>
  <li>Kontrol: <code>ssh root@135.181.206.109</code></li>
  <li>Test: <code>bash /root/bist30/smoke_test.sh</code></li>
  <li>Log: <code>journalctl -u bist30 -n 50 --no-pager</code></li>
  <li>Health log: <code>tail /var/log/bist30_health.log</code></li>
</ul>
<p style='color:#909097;font-size:13px'>Bu mail otomatik. Site düzelince RESOLVED maili atacak.</p>
</body></html>"""

try:
    msg = MIMEMultipart('alternative')
    msg['Subject'] = subject
    msg['From'] = env.get("SMTP_FROM", "noreply@borsapusula.com")
    msg['To'] = ADMIN_EMAIL
    msg.attach(MIMEText(body, 'html', 'utf-8'))
    with smtplib.SMTP(env['SMTP_HOST'], int(env.get('SMTP_PORT', '587')), timeout=15) as srv:
        srv.ehlo(); srv.starttls()
        srv.login(env['SMTP_USER'], env['SMTP_PASS'])
        srv.sendmail(env['SMTP_USER'], [ADMIN_EMAIL], msg.as_string())
    print("✓ Mail sent:", subject)
except Exception as e:
    print(f"✗ Mail failed: {e}", file=sys.stderr)
