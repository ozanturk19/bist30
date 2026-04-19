# BorsaPusula — Güvenlik Analizi

> Tarih: Nisan 2026 | Hazırlayan: Kapsamlı kod + altyapı incelemesi

---

## 🔴 KRİTİK — Hemen Müdahale

### 1. GitHub URL'de Plaintext Token

**Nerede:** `.git/config` → `remote.origin.url`

```
https://ozanturk19:<GITHUB_TOKEN>@github.com/...
```

**Risk:** Bu token git log'larında, `.git/config` içinde ve `git remote -v` çıktısında açık görünür. GitHub token'ın sızdırılması hesabına tam erişim sağlar (repo oluşturma, silme, kod değiştirme).

**Çözüm — Hemen Yap:**
```bash
# 1. GitHub → Settings → Developer Settings → Personal Access Tokens
#    → Eski tokeni REVOKE et

# 2. Yeni token oluştur (sadece repo: read/write)

# 3. URL'yi temizle
cd "/Users/mac/Bist ve BTC/Bist30"
git remote set-url origin https://github.com/ozanturk19/bist30.git

# 4. Gelecekte token'ı URL'ye yapıştırma — macOS Keychain kullan:
# git config --global credential.helper osxkeychain
# git push → ilk seferinde sor, sonra kaydet
```

---

## 🟠 YÜKSEK — Bu Hafta Çözülmeli

### 2. Korumasız POST Endpointleri

**Hangi endpoint'ler:**
- `POST /api/refresh` — Tüm 145 hisse verisi yeniden çekilir (Yahoo Finance)
- `POST /api/backtest/run` — 145 hisse × 2 yıl hesaplama (~5-10 dk CPU)

**Risk:** Herhangi biri bu URL'leri çağırabilir:
- Kötü niyetli script → saniyede yüzlerce istek → CPU %100, VPS çöker (DoS)
- Rakip bot → sürekli yük → yfinance rate limit yasağı
- Yahoo Finance çok sık çağrılırsa IP banlama riski

**Çözüm — Flask-Limiter (15 dk kurulum):**

```bash
pip install flask-limiter
```

```python
# app.py başına ekle
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

limiter = Limiter(
    app,
    key_func=get_remote_address,
    default_limits=["200 per minute"]
)

# Korumasız endpointlere uygula
@app.route("/api/refresh", methods=["POST"])
@limiter.limit("1 per 5 minutes")  # 5 dakikada 1 kez
def api_refresh():
    ...

@app.route("/api/backtest/run", methods=["POST"])
@limiter.limit("1 per 30 minutes")  # 30 dakikada 1 kez
def api_backtest_run():
    ...
```

### 3. SSE Sınırsız Bağlantı

**Nerede:** `GET /api/stream` — her browser bağlantısı server'da açık kalır

**Risk:** 
- 1000 kullanıcı = 1000 açık bağlantı → Gevent worker tıkanır
- Bot/scraper sahte SSE bağlantısı açarsa bellek tükenir

**Çözüm:**
```python
MAX_SSE_CLIENTS = 500  # makul bir limit

@app.route("/api/stream")
def api_stream():
    with _sse_lock:
        if len(_sse_clients) >= MAX_SSE_CLIENTS:
            return Response("Too many connections", status=429)
        client_queue = collections.deque()
        _sse_clients.append(client_queue)
    ...
```

### 4. subscribers.json — Tek Kopya, Şifrelenmemiş

**Risk:**
- VPS disk arızası → tüm email listesi kaybolur
- subscribers.json git'e push edilirse → email adresleri herkese açık (KVKK ihlali)
- Dosya izinleri geniş olursa başka kullanıcılar okuyabilir

**Çözüm:**
```bash
# VPS'de dosya izinlerini kısıtla
ssh root@135.181.206.109 "chmod 600 /root/bist30/subscribers.json"

# Günlük yedek için cron
ssh root@135.181.206.109 "mkdir -p /root/backups"
# crontab -e → şunu ekle:
0 3 * * * cp /root/bist30/subscribers.json /root/backups/subscribers_$(date +\%Y\%m\%d).json && find /root/backups -name 'subscribers_*.json' -mtime +30 -delete
```

```bash
# .gitignore'a ekle (LOCAL'de):
echo "subscribers.json" >> "/Users/mac/Bist ve BTC/Bist30/.gitignore"
```

### 5. Rate Limiting Genel Yokluğu

**Etkilenen tüm endpointler:**
- `/api/subscribe` — spam abone kaydı, email bounce
- `/api/hisse/<t>/news` — Gemini API kotası tükenir (paralı)
- `/api/hisse/<t>/signal-explanation` — Gemini quota

**Çözüm:**
```python
# Subscribe için
@app.route("/api/subscribe", methods=["POST"])
@limiter.limit("5 per hour")  # aynı IP'den günde 5 kayıt
def api_subscribe():
    ...

# Gemini çağrıları için
@app.route("/api/hisse/<ticker>/news")
@limiter.limit("30 per minute")
def api_news(ticker):
    ...
```

---

## 🟡 ORTA — Bu Ay Çözülmeli

### 6. Nginx'te Content Security Policy (CSP) Eksik

**Mevcut durum:** Nginx'te `X-Frame-Options` ve `X-Content-Type-Options` var ama CSP yok.

**Risk:** XSS saldırısında kötü JS kodu yüklenebilir.

**Çözüm — nginx config'e ekle:**
```nginx
add_header Content-Security-Policy "
  default-src 'self';
  script-src 'self' 'unsafe-inline' https://fonts.googleapis.com;
  style-src 'self' 'unsafe-inline' https://fonts.googleapis.com https://fonts.gstatic.com;
  font-src https://fonts.gstatic.com;
  connect-src 'self';
  img-src 'self' data:;
  frame-ancestors 'none';
" always;
```

> Not: `'unsafe-inline'` kaldırmak için tüm inline script/style'ları nonce-tabanlı yapmanız gerekir — büyük refaktör olur, şimdilik `unsafe-inline` kabul edilebilir.

### 7. Flask Secret Key Yok

**Mevcut durum:** `app = Flask(__name__)` — secret key set edilmemiş.

**Risk:** Session cookie imzalama çalışmıyor. Şu an session kullanılmıyor ama eklenirse güvensiz olur.

**Çözüm:**
```python
import secrets
app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", secrets.token_hex(32))
```

```ini
# systemd'ye ekle
Environment=FLASK_SECRET_KEY=uzun-rastgele-bir-string-buraya
```

### 8. Gemini API Key systemd'de Açık

**Mevcut durum:** `systemd service` dosyasında:
```ini
Environment=GEMINI_API_KEY=AIzaSyDj7qZ7Flp1vmuyTVsHj4dTdI3CaiPBBiQ
```

**Risk:** 
- `systemctl show bist30` komutu root yetkisiyle API key'i gösterir
- Systemd servis dosyası `/etc/systemd/system/` altında root ile okunabilir
- Log dosyalarına kazara yazılabilir

**Mevcut durum değerlendirmesi:** VPS'e sadece siz root olarak erişiyorsanız **kabul edilebilir risk**. Ancak en iyi pratik:

**Çözüm:**
```bash
# /root/bist30/.env dosyası oluştur (chmod 600)
cat > /root/bist30/.env << 'EOF'
GEMINI_API_KEY=AIzaSy...
TELEGRAM_BOT_TOKEN=...
SMTP_PASS=...
EOF
chmod 600 /root/bist30/.env

# app.py başına ekle
from dotenv import load_dotenv
load_dotenv()  # .env dosyasını otomatik yükler

# pip install python-dotenv
```

### 9. Hatalı Ticker ile Arbitrary Path Traversal Riski

**Mevcut durum:**
```python
@app.route("/hisse/<ticker>")
def hisse_page(ticker):
    if ticker not in BIST100:
        return render_template("index.html"), 404
```

**Değerlendirme:** `ticker` doğrudan dosya yoluna kullanılmıyor, sadece BIST100 listesinde aranıyor. ✅ Güvenli.

Ama `/api/hisse/<ticker>/chart` gibi endpointlerde de kontrol var mı?

```python
# Mevcut kontrol yeterli:
if ticker not in BIST100:
    return safe_json({"error": "Hisse bulunamadı"}), 404
```

**Durum:** ✅ Korunuyor — BIST100 whitelist kontrolü var.

### 10. Email Enumeration

**Mevcut durum:**
```python
if email in subs:
    return safe_json({"ok": False, "error": "Bu e-posta zaten kayıtlı"})
```

**Risk:** Saldırgan istediği email adreslerini deneyerek hangilerinin kayıtlı olduğunu öğrenebilir (KVKK problemi).

**Çözüm:**
```python
# Kayıtlı olsun olmasın aynı mesajı dön
return safe_json({"ok": True, "message": "E-posta adresiniz varsa onay gönderildi."})
```

---

## 🟢 İYİ YAPILMIŞ — Takdir Edilecek Güvenlik Kararları

### ✅ debug=False (Production)
`app.run(debug=False)` — hata mesajları kullanıcıya açılmıyor.

### ✅ Nginx Security Headers
```nginx
add_header X-Frame-Options "SAMEORIGIN";
add_header X-Content-Type-Options "nosniff";
add_header Referrer-Policy "strict-origin-when-cross-origin";
```

### ✅ Token Tabanlı Unsubscribe
`secrets.token_hex(24)` kullanılmış — tahmin edilemez, cryptographically secure.

### ✅ Email Regex Validation
```python
re.match(r'^[^@]+@[^@]+\.[^@]+$', email)
```

### ✅ Thread-Safe Data Cache
`threading.Lock()` ile `_cache` ve `_sub_lock` korunuyor.

### ✅ Ticker Whitelist
Tüm `/api/hisse/<ticker>` endpointleri BIST100 listesine karşı kontrol ediyor.

### ✅ Cloudflare Proxy
- DDoS koruması CF tarafında
- IP gizleme (gerçek VPS IP'si bir ölçüde gizlenir)
- SSL CF tarafında (HTTP/HTTPS)

### ✅ Gzip Sıkıştırma
Nginx gzip aktif — hem performans hem de bandwidth tasarrufu.

---

## Öncelikli Eylem Planı

### Bu Hafta (Kritik)
```
1. [ ] GitHub token'ı REVOKE et → yeni token al → git remote URL'yi temizle
2. [ ] subscribers.json → .gitignore'a ekle
3. [ ] Flask-Limiter kur → /api/refresh ve /api/backtest/run'a limit ekle
4. [ ] subscribers.json cron backup kur (VPS'de)
5. [ ] chmod 600 /root/bist30/subscribers.json
```

### Bu Ay
```
6. [ ] SSE max bağlantı limiti ekle (500)
7. [ ] Flask secret_key env var'a taşı
8. [ ] Gemini API key'i .env dosyasına taşı (python-dotenv)
9. [ ] /api/subscribe rate limit (5/saat per IP)
10. [ ] Email enumeration fix (aynı mesajı dön)
```

### İleride (Opsiyonel)
```
11. [ ] CSP header ekle (nginx)
12. [ ] Fail2ban kur (SSH brute force koruması)
13. [ ] VPS firewall — sadece 80, 443, SSH portları açık olsun
14. [ ] Otomatik SSL (Certbot — şu an CF yeterli ama CF'siz backup)
15. [ ] Log rotation — journalctl boyut sınırı
```

---

## Özet Risk Matrisi

| # | Risk | Etki | Olasılık | Öncelik |
|---|------|------|----------|---------|
| 1 | GitHub'da token | Kritik | Yüksek | 🔴 Hemen |
| 2 | /api/refresh DoS | Yüksek | Orta | 🟠 Bu hafta |
| 3 | /api/backtest DoS | Yüksek | Orta | 🟠 Bu hafta |
| 4 | subscribers.json kaybı | Yüksek | Düşük | 🟠 Bu hafta |
| 5 | Rate limit yok (Gemini) | Orta | Orta | 🟡 Bu ay |
| 6 | SSE bağlantı flood | Orta | Düşük | 🟡 Bu ay |
| 7 | Secret key yok | Düşük | Düşük | 🟡 Bu ay |
| 8 | Email enumeration | Düşük | Düşük | 🟡 Bu ay |
| 9 | CSP eksik | Düşük | Çok düşük | 🟢 İleride |
