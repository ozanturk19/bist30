"""CPO-1218 P0 — /api/stream (SSE) fd sızıntısı regresyon testi.

02 Ağu 2026 16:05-16:12 UTC canlı ölçüm (CPO): bir worker `ss -tanp` ile 99/100
bağlantıda CLOSE-WAIT durumunda bulundu, py-spy 4 worker'ın da idle olduğunu
gösterdi (hub bloke değil — CPO-1217 hipotezi bu yüzden geri çekildi). Kanıt:
15:07 reload'unda SIGTERM alan eski worker'ın döktüğü satırlar, tek bir
/api/stream bağlantısının 5600 saniye (93 dakika) açık kaldığını gösterdi.

Kök neden: generate() içindeki `while True` döngüsü istemci/nginx bağlantıyı
kopardığında bunu ASLA tespit edemiyordu — CLOSE-WAIT durumundaki bir sokete
keepalive yazmak hata fırlatmıyor (canlı ölçüm: 2163s açık kalan tek bir
stream, ~144 keepalive hatasız gönderilmiş). Worker `--worker-connections 100`
tavanına ulaşınca yeni bağlantı alamıyor → 60s nginx upstream timeout → 504.

Fix: `_SSE_MAX_LIFETIME_S` mutlak ömür tavanı (240s) — generator bu süre
dolunca yazma hatası beklemeden kendiliğinden sonlanır, `finally` bloğu
_sse_clients temizliğini çalıştırır, HTTP yanıtı kapanır, fd serbest kalır.
İstemci tarafında native `EventSource` (templates/*.html, tüm kullanım
noktaları) otomatik reconnect yapar — kullanıcı etkisi yok.

Python 3.9 (yerel Mac) app.py'yi (3.10+ sözdizimi) import edemediği için
fonksiyon kaynaktan izole exec edilir (bkz. test_cpo1137_canonical_freshness.py).
Gerçek zaman kaybetmemek için time.sleep()/time.monotonic() sahte (fake) bir
saatle simüle edilir — 240s+ süren senaryo testte milisaniyeler sürer.
"""
import collections
import json
import os
import re
from datetime import datetime, timedelta, timezone

_APP_PY = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "app.py")

with open(_APP_PY, encoding="utf-8") as _f:
    _SRC = _f.read()

_TZ_TR = timezone(timedelta(hours=3))


class _FakeTime:
    """time.monotonic() ilerlemesini time.sleep() çağrılarıyla simüle eder —
    gerçek zaman geçmeden 240s+ bir senaryoyu anında test etmeyi sağlar."""
    def __init__(self):
        self.t = 0.0

    def monotonic(self):
        return self.t

    def sleep(self, s):
        self.t += s


def _load_api_stream():
    m = re.search(r"def api_stream\(\):.*?\n\n\n", _SRC, re.DOTALL)
    assert m, "api_stream() app.py'de bulunamadı — fonksiyon adı/imzası değişmiş olabilir"
    const_m = re.search(r"_SSE_MAX_LIFETIME_S = (\d+)", _SRC)
    assert const_m, "_SSE_MAX_LIFETIME_S sabiti bulunamadı"

    fake_time = _FakeTime()
    sse_clients = []
    ns = {
        "collections": collections,
        "json": json,
        "datetime": datetime,
        "_TZ_TR": _TZ_TR,
        "_sse_lock": __import__("threading").Lock(),
        "_sse_clients": sse_clients,
        "_lock": __import__("threading").Lock(),
        "_live_prices": {"THYAO": 100.0},
        "time": fake_time,
        "Response": lambda gen, **kw: gen,  # gerçek Response yerine generator'ı doğrudan döndür
        "_SSE_MAX_LIFETIME_S": int(const_m.group(1)),
    }
    exec(m.group(0), ns)
    return ns["api_stream"], sse_clients, fake_time


def test_sse_max_lifetime_constant_is_sane():
    """CPO-1218 önerisi 120-300s bandı — sabit bu bandın dışına çıkarsa (ör.
    biri unutup çok büyük/küçük bir değer koyarsa) test yakalar."""
    const_m = re.search(r"_SSE_MAX_LIFETIME_S = (\d+)", _SRC)
    assert const_m
    value = int(const_m.group(1))
    assert 120 <= value <= 300, f"_SSE_MAX_LIFETIME_S={value} CPO-1218 önerilen bandın (120-300s) dışında"


def test_sse_stream_terminates_without_disconnect_signal():
    """En kritik regresyon: istemci HİÇ kopmasa (write hiç hata vermese) bile —
    canlıda ölçülen tam senaryo — generator ömür tavanında kendiliğinden durur."""
    api_stream, sse_clients, fake_time = _load_api_stream()
    gen = api_stream()

    chunks = []
    for _ in range(100_000):  # üst sınır — sonsuz döngü regresyonuna karşı guard
        try:
            chunks.append(next(gen))
        except StopIteration:
            break
    else:
        raise AssertionError(
            "generate() 100_000 chunk sonra hâlâ durmadı — CPO-1218 fix'i "
            "regresyona uğramış olabilir (ömür tavanı çalışmıyor)"
        )

    assert fake_time.monotonic() >= 240, (
        f"stream ömür tavanından ÖNCE durdu (t={fake_time.monotonic()}) — beklenmeyen erken çıkış"
    )
    assert sse_clients == [], "generator bittiğinde _sse_clients temizlenmemiş (finally bloğu çalışmamış)"


def test_sse_finally_cleans_up_even_on_forced_close():
    """generator .close() ile (istemci gerçekten koptuğunda WSGI katmanının
    yapacağı şey) erken kapatılırsa da finally _sse_clients'i temizlemeli."""
    api_stream, sse_clients, _fake_time = _load_api_stream()
    gen = api_stream()
    next(gen)  # ilk chunk'ı tüket (initial_msg veya ilk keepalive/loop adımı)
    assert len(sse_clients) == 1
    gen.close()
    assert sse_clients == [], "generator.close() sonrası _sse_clients hâlâ dolu — fd sızıntısı regresyonu"
