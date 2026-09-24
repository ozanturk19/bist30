"""D-48 (KVKK) — abone e-postaları log satırlarında maskelenir.

23.09 19:04 digest ölçümü: `journalctl -u bist30` her gönderimde abonenin tam
adresini yazıyordu ("E-posta gönderildi: …@…"). Artık her adres `a***@alanadi`
biçiminde loglanır; sayaç satırları ("daily digest sonuc: sent=9 …") değişmez.

İki katman:
- `mask_email()` — app.py'de e-posta taşıyan her log çağrısında açıkça sarılır.
- `EmailMaskFilter` — "bist30" logger'ına takılı güvenlik ağı: kaydın son
  metninde kalan her adresi (ör. SMTP hata metnindeki alıcı) maskeler.
"""
from __future__ import annotations

import logging
import re

# Yerel kısmın ilk karakteri korunur, kalanı "***" olur; alan adı aynen kalır.
# "***" yerel-kısım karakter sınıfında olmadığı için maskeli adres ikinci kez
# eşleşmez (işlem idempotent). "/@vite" gibi yolda '@' öncesi harf yoksa dokunulmaz.
_EMAIL_RE = re.compile(r"([\w%+-])[\w.%+-]*@([\w-]+(?:\.[\w-]+)+)")


def mask_email(addr) -> str:
    """"ali.veli@gmail.com" -> "a***@gmail.com". Boş/None -> ""."""
    if not addr:
        return ""
    s = str(addr).strip()
    local, sep, domain = s.rpartition("@")
    if not sep:
        return s[:1] + "***"
    return local[:1] + "***@" + domain


def mask_emails_in_text(text) -> str:
    """Serbest metindeki her e-posta adresini maskeler."""
    return _EMAIL_RE.sub(lambda m: m.group(1) + "***@" + m.group(2), str(text))


class EmailMaskFilter(logging.Filter):
    """Log kaydının biçimlenmiş metnindeki e-postaları maskeler (kaydı düşürmez)."""

    def filter(self, record: logging.LogRecord) -> bool:
        try:
            msg = record.getMessage()
        except Exception:
            return True
        masked = mask_emails_in_text(msg)
        if masked != msg:
            record.msg = masked
            record.args = None
        return True
