#!/usr/bin/env python3
"""bist30-kap-gundem-worker — D-17 kesme hazırlığı (CPO-1830/CPO risk notu 12.10)

D-17 (A1) "kesme" adımı `systemctl disable --now bist30-macro` ile eski 7/24
macro_worker.py sürecini kapatır. O süreç yalnız yfinance makro fetch'i için
değil, BP_ROLE=macro'ya bağlı iki başka iş parçacığı için de tek yaşam alanıydı:
kap-feed (app.py ~9130) ve gundem-haber (app.py ~9189). Bu script o iki
parçacığı YFinance fetch'ten (artık bp-intraday.timer'da, D-17 adım 1-2)
AYRIŞTIRIP ayakta tutar — macro_worker.py kapandıktan sonra da KAP bildirimi
ve Gündem AI baskısı sessizce durmasın.

**Rol seçimi kasıtlı — YENİ bir BP_ROLE string'i DEĞİL:**
- `BP_ROLE=macro` (macro_worker.py ile AYNI): `_is_notify_leader()` ve
  `_is_digest_leader()` wrapper'ları (app.py ~2253, ~2345) bunu zaten
  dışlıyor — bu süreç bildirim/digest liderliğine hiç girmiyor.
- `REFRESH_WORKER=web` (macro_worker.py'den FARKLI — o "1" kullanır):
  `_macro_bg_loop` (app.py:5999 "REFRESH_WORKER==web" dalı) bu değerde
  `_is_macro_leader()` flock'una HİÇ girmeden salt disk-reload moduna
  düşer — bu süreç makro-fetch liderliğine de yarışmaz (macro_worker.py
  REFRESH_WORKER=1 kullandığı için o yarışa girer, kasıtlı: iki süreç farklı
  amaçla aynı flock'u paylaşıyordu).
- Ayrı bir `BP_ROLE` değeri (örn. "kapgundem") DENENMEDİ: `_is_digest_leader()`
  wrapper'ı SADECE `BP_ROLE=="macro"`'yu dışlar, `_is_notify_leader()`'ın
  yaptığı gibi `REFRESH_WORKER=="web"`'i AYRICA kontrol ETMEZ — yeni bir rol
  string'i bu dışlamayı kaçırır ve CPO-1456 sınıfı kalıcı kilit-kazanma riski
  taşır. BP_ROLE=macro + REFRESH_WORKER=web ikilisi her ikisi de başka yerde
  zaten kanıtlanmış dışlama yollarını kullanır — sıfır yeni kilit yüzeyi.

Sonuç: app.py'de kap-feed/gundem-haber gating'i (`BP_ROLE=="macro"`) DEĞİŞMEDİ
— bu süreç de "macro" rolünde sayıldığı için otomatik başlar.

Kesme sırası (Cmt penceresi): (1) bu servis kurulup başlatılır, journalctl'de
kap-feed/gundem-haber thread başlangıcı + 0 traceback doğrulanır, (2) ANCAK
SONRA `systemctl disable --now bist30-macro`. Üst üste binme (dakikalar)
sırasında `_proc_sha_path("macro")` (app.py ~1508, rol-bazlı dosya yolu, pid
değil) iki süreç arasında ezişebilir — yalnız `/api/health`'in macro-pid
göstergesi geçici kararsızlaşır, bildirim/veri etkisi yok.
"""
import os
import sys
import logging
import time

os.environ.setdefault("REFRESH_WORKER", "web")
os.environ.setdefault("BP_ROLE", "macro")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("kap-gundem-worker")

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

logger.info("kap_gundem_worker.py: app.py import ediliyor (kap-feed + gundem-haber thread'leri otomatik başlar)...")
import app  # noqa: E402 — tüm init çalışır; background_refresh() ÇAĞRILMAZ (kasıtlı)

logger.info("kap_gundem_worker.py: background_refresh() ÇAĞRILMIYOR (kasıtlı) — yalnız kap-feed + gundem-haber canlı tutuluyor")
while True:
    time.sleep(3600)
