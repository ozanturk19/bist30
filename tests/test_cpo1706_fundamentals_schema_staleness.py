"""CPO-1706 -- fundamentals "şema tam mı" kontrolü sadece anahtar VARLIĞINA
bakıyordu (`"statement_trend_quarterly" in data`), İÇERİĞE değil.

`_get_fundamentals()` bu alanı HER yazımda `_fetched.get(...) or []` ile
garanti "var" ediyor -- boş liste bile olsa. Yahoo bir turda
financialCurrency/quarterly-income-stmt ucunu boş döndürürse (script hata
vermez, CB de yakalamaz -- sadece o alt-alanlar boş gelir) kayıt bir daha
ASLA "eksik" sayılmıyordu, sadece ~3.5s TTL dolunca yeniden denenirdi.

Canlı kanıt (22.09 ~03:1x TR, VPS last_fundamentals_cache.json): 217/217
ticker financial_currency=null yazılmış, İKİ ayrı warmup turunda (iki farklı
process restart'ı) da aynı sonuç -- hiçbir FAIL/circuit-breaker log'u yok.
Aynı script'i izole/manuel çağırmak (aynı 1sn aralıkla, arka arkaya 7 hisse)
HER SEFERİNDE doğru sonuç verdi -- yani script kendisi sağlıklı, sadece
daemon bağlamındaki bir turun ürettiği boş/null veri asla yeniden
denenmiyordu.

Fix: tek bir `_fundamentals_schema_ok()` yardımcısı -- hem `_get_fundamentals()`
içindeki cache-fresh kararı (satır ~8594) hem `_fundamentals_warmup_daemon()`
içindeki yeniden-çekme kararı (satır ~13946) aynı fonksiyonu çağırıyor, iki
kopya mantık birbirinden sapamaz (DEV-1034/_derive_tier ile aynı desen).

NOT: Bu fix Yahoo'nun neden boş döndürdüğünü AÇIKLAMIYOR (hipotez: eşzamanlı
ana refresh döngüsüyle rekabet, doğrulanmadı) -- sadece "bir kez boş yazılırsa
bir daha asla denenmez" açığını kapatıyor. "Kalıcı çözüm" değil, self-heal
döngüsünü onarıyor.
"""
import os
import re

_APP_PY = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "app.py")


def _read_app():
    with open(_APP_PY, encoding="utf-8") as f:
        return f.read()


def _extract_function_body(src, func_name):
    pattern = rf"def {func_name}\(.*?(?=\ndef |\Z)"
    m = re.search(pattern, src, re.DOTALL)
    return m.group(0) if m else None


def _load_schema_ok():
    src = _read_app()
    body = _extract_function_body(src, "_fundamentals_schema_ok")
    assert body, "_fundamentals_schema_ok() bulunamadı"
    ns = {}
    exec(body, ns)
    return ns["_fundamentals_schema_ok"]


# ── statik: iki çağrı yeri de ortak yardımcıyı kullanıyor mu ───────────────

def test_get_fundamentals_uses_shared_helper():
    src = _read_app()
    body = _extract_function_body(src, "_get_fundamentals")
    assert body, "_get_fundamentals() bulunamadı"
    assert "_schema_ok = _fundamentals_schema_ok(cached[\"data\"]) if cached else False" in body, (
        "_get_fundamentals() artık _fundamentals_schema_ok() üzerinden karar vermeli "
        "-- anahtar-varlığı kontrolüne geri dönülmüş olabilir"
    )
    assert '"statement_trend_quarterly" in cached' not in body, (
        "eski anahtar-varlığı kontrolü hâlâ duruyor (içerik değil)"
    )


def test_warmup_daemon_uses_shared_helper():
    src = _read_app()
    body = _extract_function_body(src, "_fundamentals_warmup_daemon")
    assert body, "_fundamentals_warmup_daemon() bulunamadı"
    assert "_stale_schema = bool(_fc) and not _fundamentals_schema_ok(_fc.get(\"data\"))" in body, (
        "_fundamentals_warmup_daemon() artık _fundamentals_schema_ok() üzerinden "
        "karar vermeli -- anahtar-varlığı kontrolüne geri dönülmüş olabilir"
    )
    assert '"statement_trend_quarterly" not in (_fc.get("data") or {})' not in body, (
        "eski anahtar-varlığı kontrolü hâlâ duruyor (içerik değil)"
    )


# ── işlevsel: helper'ın kendisi doğru sınıflandırıyor mu ───────────────────

def _full_data(**overrides):
    d = {
        "statement_trend_quarterly": [{"period": "2025Q2", "total_revenue": 1}],
        "financial_currency": "TRY",
        "statement_currency": "TRY",
    }
    d.update(overrides)
    return d


def test_full_record_is_ok():
    schema_ok = _load_schema_ok()
    assert schema_ok(_full_data()) is True


def test_empty_dict_is_not_ok():
    schema_ok = _load_schema_ok()
    assert schema_ok({}) is False
    assert schema_ok(None) is False


def test_key_present_but_empty_list_is_not_ok():
    """Asıl CPO-1706 açığı: `_fetched.get(...) or []` yüzünden anahtar HEP var,
    ama boş liste -- eski kontrol bunu 'şema tam' sayıyordu."""
    schema_ok = _load_schema_ok()
    assert schema_ok(_full_data(statement_trend_quarterly=[])) is False


def test_null_financial_currency_is_not_ok():
    """Canlıda gözlenen asıl semptom: statement_trend_quarterly dolu olsa bile
    financial_currency None ise para birimi hâlâ yanlış -- bu da tazelik
    dışında sayılmalı."""
    schema_ok = _load_schema_ok()
    assert schema_ok(_full_data(financial_currency=None)) is False


def test_null_statement_currency_is_not_ok():
    schema_ok = _load_schema_ok()
    assert schema_ok(_full_data(statement_currency=None)) is False
