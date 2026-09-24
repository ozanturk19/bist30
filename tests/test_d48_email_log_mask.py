"""D-48 (KVKK) — abone e-postaları log satırlarında maskelenir (email_mask.py).

Kabul (plan): digest sonrası journalctl'de `[a-z0-9._-]{3,}@` eşleşmesi 0,
sayaç satırı ("daily digest sonuc: sent=9 …") aynen kalır.
"""
import ast
import logging
import os
import re
import smtplib

import pytest

from email_mask import EmailMaskFilter, mask_email, mask_emails_in_text

_APP_PY = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "app.py")
_RAW_EMAIL = re.compile(r"(?i)[a-z0-9._-]{3,}@")
# app.py'de e-posta adresi taşıyan değişken adları (mail_pref gibi alanlar hariç)
_EMAIL_VARS = re.compile(r"^(to_|match_|target_)?email$|^target$|^em$")


def test_mask_email_keeps_first_char_and_domain():
    assert mask_email("ali.veli@gmail.com") == "a***@gmail.com"
    assert mask_email("  Ozan.T@Hotmail.com ") == "O***@Hotmail.com"
    assert mask_email("x@adalet.gov.tr") == "x***@adalet.gov.tr"
    assert mask_email("") == "" and mask_email(None) == ""
    assert mask_email("adres-yok") == "a***"


def test_mask_emails_in_text_idempotent_and_leaves_other_lines():
    txt = "alici: ali.veli@gmail.com, cc <B.Kaya@firma.com.tr>, özlem@site.com"
    once = mask_emails_in_text(txt)
    assert once == "alici: a***@gmail.com, cc <B***@firma.com.tr>, ö***@site.com"
    assert mask_emails_in_text(once) == once
    assert not _RAW_EMAIL.search(once)
    counter = ("daily digest sonuc: sent=9, skip_pref=1, skip_watchlist=0, "
               "skip_sendfail=0 (active=10, changes=13)")
    assert mask_emails_in_text(counter) == counter
    access = '127.0.0.1 - - "GET /@vite/client HTTP/1.1" 404'
    assert mask_emails_in_text(access) == access


class _ListHandler(logging.Handler):
    def __init__(self):
        super().__init__()
        self.lines = []

    def emit(self, record):
        self.lines.append(self.format(record))


@pytest.fixture
def masked_logger():
    lg = logging.getLogger("d48-test")
    lg.propagate = False
    lg.setLevel(logging.INFO)
    handler, flt = _ListHandler(), EmailMaskFilter()
    lg.addHandler(handler)
    lg.addFilter(flt)
    yield lg, handler
    lg.removeHandler(handler)
    lg.removeFilter(flt)


def test_filter_masks_args_and_smtp_exception_text(masked_logger):
    lg, h = masked_logger
    lg.info("E-posta gönderildi: %s (konu: %s)", "ali.veli@gmail.com", "📊 23 Eylül BIST Sinyalleri")
    err = smtplib.SMTPRecipientsRefused({"b.kaya@firma.com.tr": (550, b"no such user")})
    lg.error("E-posta gönderilemedi (%s): %s", mask_email("b.kaya@firma.com.tr"), err)
    lg.info("%s oran %%50", "ali@x.com")
    lg.info("Digest: %d aktif abone, %d toplam abone", 9, 10)
    assert h.lines[0] == "E-posta gönderildi: a***@gmail.com (konu: 📊 23 Eylül BIST Sinyalleri)"
    assert "b***@firma.com.tr" in h.lines[1]
    assert h.lines[2] == "a***@x.com oran %50"
    assert h.lines[3] == "Digest: 9 aktif abone, 10 toplam abone"
    assert not any(_RAW_EMAIL.search(line) for line in h.lines)


def _logger_calls(tree):
    for node in ast.walk(tree):
        if (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
                and node.func.attr in {"debug", "info", "warning", "error", "exception", "critical"}
                and isinstance(node.func.value, ast.Name) and node.func.value.id == "logger"):
            yield node


def test_app_log_calls_never_pass_raw_email_variable():
    src = open(_APP_PY, encoding="utf-8").read()
    tree = ast.parse(src)
    raw = [(n.lineno, a.id) for n in _logger_calls(tree) for a in n.args[1:]
           if isinstance(a, ast.Name) and _EMAIL_VARS.search(a.id)]
    assert raw == [], f"maskesiz e-posta log argümanı: {raw}"
    wrapped = sum(1 for n in _logger_calls(tree) for a in n.args[1:]
                  if isinstance(a, ast.Call) and getattr(a.func, "id", "") == "_mask_email")
    assert wrapped >= 14
    assert "logger.addFilter(_EmailMaskFilter())" in src
