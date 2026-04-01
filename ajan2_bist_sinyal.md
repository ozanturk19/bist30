# AJAN 2: BIST 30 Sinyal Botu (Sadece Sinyal — Otomatik Emir Yok)

## GENEL BAĞLAM
Ben Ozan, teknik bilgisi olmayan bir kullanıcıyım. Her şeyi Türkçe, adım adım açıkla. Teknik jargonu minimumda tut. Bu ajan SADECE BIST sinyal botu ile ilgilenir — BTC tarafına karışmaz.

---

## GÖREV
Hetzner VPS üzerinde çalışan bir BIST 30 sinyal botu kurmak. Bot otomatik emir VERMEZ — sadece sinyal üretir ve Telegram + e-posta ile bildirim gönderir. Alım/satım kararı kullanıcıya aittir.

---

## MEVCUT DURUM

### VPS
- Provider: Hetzner CX23
- IP: 135.181.206.109
- OS: Ubuntu 24.04
- BTC botu aynı VPS'te çalışıyor (`~/btc_bot/`) — ona dokunma

### BIST Botu
- Henüz yazılmadı — sen yazacaksın
- Klasör: `~/bist_bot/`

---

## BIST SİNYAL BOTU MİMARİSİ

### Temel Kural
BIST 30 hisseleri için Borsa İstanbul'da Futures API yoktur. Bu yüzden:
- **Veri kaynağı:** Yahoo Finance (yfinance kütüphanesi) veya TEFAS/IsYatirim scraping
- **Emir:** YOK — sadece sinyal
- **Bildirim:** Telegram + E-posta

### Takip Edilecek Enstrümanlar
BIST 30 endeksindeki hisseler + XU030 endeksi (öncelikli).
Kullanıcıyla hangi hisselerin takip edileceğini netleştir.

### Sinyal Motoru
Aşağıdaki indikatörler kullanılacak (HTML dashboard ile aynı mantık):

**5 Katman:**
1. **EMA 20/50/200** — Trend filtresi. EMA20 > EMA50 > EMA200 = bull alignment
2. **Bollinger Band** — Kırılım tespiti, yalnızca trend yönünde
3. **MACD Histogram** — Momentum onayı
4. **RSI (14)** — 50-75 long ideal / 25-50 short ideal
5. **ADX (14)** — ADX > 25 güçlü trend filtresi

**Zaman dilimi:** 4H (BIST için günlük de eklenebilir)
**Minimum onay:** 3/5 koşul

### Bildirim Sistemi
**Telegram:**
- Kullanıcının Telegram bot token'ı ve chat ID'si gerekli
- BotFather'dan nasıl alınacağını kullanıcıya anlat
- Mesaj formatı:
  ```
  🟢 BIST SİNYAL — LONG
  Hisse: THYAO
  Fiyat: 342.50 TL
  Sinyal: EMA hizalı ✅ | BB kırılım ✅ | MACD ✅ | RSI 58 ✅ | ADX 31 ✅
  SL: ~334.00 TL | Hedef: ~359.00 TL
  Zaman: 14:00 4H mum kapanışı
  ⚠️ Bu bir bildirimdir, otomatik emir verilmez.
  ```

**E-posta:**
- Gmail SMTP (App Password ile)
- Kullanıcıdan Gmail adresi ve App Password al
- Aynı sinyal içeriği, HTML formatında

### Dosya Yapısı
```
~/bist_bot/
├── bot.py
├── requirements.txt
├── .env
├── .env.example
├── bist-bot.service
└── bist_bot.log
```

### Requirements (taslak — sen tamamla)
```
yfinance>=0.2.0
pandas>=2.0.0
numpy>=1.24.0
python-dotenv>=1.0.0
schedule>=1.2.0
python-telegram-bot>=20.0
```

### Çevresel Değişkenler (.env)
```
TELEGRAM_BOT_TOKEN=...
TELEGRAM_CHAT_ID=...
EMAIL_SENDER=...@gmail.com
EMAIL_APP_PASSWORD=...
EMAIL_RECEIVER=...@gmail.com
HISSELER=THYAO,GARAN,AKBNK,EREGL,SASA
```

### systemd Servis (bist-bot.service)
```ini
[Unit]
Description=BIST 30 Sinyal Botu
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/root/bist_bot
ExecStart=/root/bist_bot/venv/bin/python bot.py
Restart=always
RestartSec=30

[Install]
WantedBy=multi-user.target
```

### Zamanlama
- BIST seans saatleri: 10:00–18:00 (Türkiye saati)
- 4H mum kapanışlarında kontrol: 10:00, 14:00, 18:00
- Seans dışında çalışmaz (gereksiz API çağrısı yapma)

---

## SIRAYI DEVRAL — NEREDEN BAŞLA

### Adım 1 — Kullanıcıdan bilgi al
Şunları sor:
1. Hangi hisseler takip edilsin? (örn: THYAO, GARAN, AKBNK, EREGL — XU030'un tamamı mı?)
2. Telegram botu var mı? (yoksa BotFather kurulumunu anlat)
3. Gmail App Password mevcut mu? (yoksa nasıl alınacağını anlat)

### Adım 2 — Bot kodunu yaz
Yukarıdaki mimariye göre tam `bot.py` dosyasını oluştur.

### Adım 3 — VPS'e kur
BTC botunun yanına, ayrı klasöre:
```bash
mkdir ~/bist_bot && cd ~/bist_bot
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### Adım 4 — Test et
Tek bir hisse için sinyal üret, Telegram ve e-postaya test mesajı gönder.

### Adım 5 — systemd ile kalıcı hale getir
BTC servisine dokunmadan, ayrı servis olarak kur.

---

## ÖNEMLİ KISITLAMALAR
- BTC botuna (`~/btc_bot/`) kesinlikle dokunma
- Otomatik emir kodu YAZMA — kullanıcı bunu istemedi
- Sinyal mesajlarına her zaman "Bu bir bildirimdir, otomatik emir verilmez" uyarısı ekle
- BIST hisseleri TL bazlı, dolar karışıklığı yapma

## KULLANICI TERCİHLERİ
- Türkçe konuş
- Her adımda ne yapması gerektiğini tek tek söyle
- Hata olursa önce 1 cümle sebep, sonra çözüm
- Ekran görüntüsü paylaşabilir, ona göre yönlendir
- BTC tarafına hiç karışma — o ayrı bir ajan
