# Sprint 3.5 Fix 2 — Gemini Global Rate Limiter Pre-flight

**Tarih:** 28 Haziran 2026  
**Hedef deploy:** Pzt 30 Haziran 2026, seans sonrası (18:30+ TR)  
**Effort:** M (~2 saat)

---

## 1. Sorun Özeti

Mevcut `_gemini_rate_lock` + `_gemini_rate_last` yapısı **worker-local** (process içi). 4 gunicorn worker her biri kendi sayacını tutar:

```
Worker-1: last=T   → 6.5s bekle
Worker-2: last=T   → 6.5s bekle   ← aynı anda
Worker-3: last=T   → 6.5s bekle   ← aynı anda
Worker-4: last=T   → 6.5s bekle   ← aynı anda
```

Gerçek efektif rate: **4 worker × ~9.2 req/dk = ~36.8 RPM**  
Gemini free tier limiti: **10 RPM**  
Sonuç: burst durumunda 429 hatası (CPO-884 backlog Fix 2).

---

## 2. Mevcut Kod — Dosya:Satır

| Satır | İçerik |
|---|---|
| `app.py:4722-4725` | Rate limiter sabitleri + worker-local lock + last |
| `app.py:4961-4968` | `_gemini_call` içi rate limit bloğu (sleep dışarıda, CPO-837 fix zaten uygulandı) |

```python
# app.py:4722
_GEMINI_RATE_INTERVAL = float(os.environ.get("GEMINI_RATE_INTERVAL", "6.5"))
_gemini_rate_lock = threading.Lock()   # ← PROBLEM: worker-local
_gemini_rate_last = [0.0]              # ← PROBLEM: worker-local

# app.py:4961-4968
# Faz 12 P2.6 — Rate limiter: 3.5s minimum arası (free tier 20 req/dk aşmaz)
# CPO-837 FIX: sleep lock DIŞINDA
with _gemini_rate_lock:
    _wait = _GEMINI_RATE_INTERVAL - (time.time() - _gemini_rate_last[0])
    _gemini_rate_last[0] = time.time()
if _wait > 0:
    time.sleep(_wait)
```

---

## 3. Fix Tasarımı — Slot Reservation Pattern

### Mekanizma

Ortak bir dosya üzerinden worker'lar "bir sonraki boş slot" bilgisini paylaşır:

1. Worker exclusive flock alır (blocking — sıra bekler)
2. Dosyadan `next_slot` okur (yoksa `0.0`)
3. `next_slot = max(time.time(), next_slot) + _GEMINI_RATE_INTERVAL` hesaplar
4. Dosyaya yeni `next_slot` yazar, flock bırakır
5. `sleep(next_slot - _GEMINI_RATE_INTERVAL - time.time())` → kendi slotunu bekler

Böylece 4 worker aynı anda gelirse slotları otomatik sıralanır:
```
W1: slot T+0       (0s bekle)
W2: slot T+6.5     (6.5s bekle)
W3: slot T+13.0    (13.0s bekle)
W4: slot T+19.5    (19.5s bekle)
```

Efektif rate: **~9.2 req/dk global** (10 RPM limiti geçmez).

### Gevent Uyumluluğu

- flock acquire (kernel call) → gevent monkey-patch altında cooperative yield yapar (gevent I/O ile uyumlu)
- `time.sleep(_wait)` lock dışarıda → CPO-837 pattern korunuyor

---

## 4. Değiştirilecek Satırlar — Tam Diff

### 4a. Yeni sabitler + dosya handle (app.py:4722 civarı — mevcut 4 satırı değiştir)

**SİLİNECEK (app.py:4722-4725):**
```python
_GEMINI_RATE_INTERVAL = float(os.environ.get("GEMINI_RATE_INTERVAL", "6.5"))
_gemini_rate_lock = threading.Lock()
_gemini_rate_last = [0.0]
```

**EKLENECEKler:**
```python
_GEMINI_RATE_INTERVAL = float(os.environ.get("GEMINI_RATE_INTERVAL", "6.5"))
_GEMINI_RATE_PATH = os.environ.get("GEMINI_RATE_PATH", "/tmp/bp_gemini_rate.lock")
_gemini_rate_fh = None  # worker-local file handle, global slot dosyası paylaşılır


def _gemini_rate_acquire() -> float:
    """Global cross-worker Gemini rate limiter — slot reservation.

    flock ile tek seferde bir worker slot alır; sleep dışarıda kalır (CPO-837 uyumlu).
    Returns: saniye cinsinden beklenecek süre (0.0 ise beklemeden devam).
    """
    global _gemini_rate_fh
    if _gemini_rate_fh is None:
        _gemini_rate_fh = open(_GEMINI_RATE_PATH, "a+")

    _fcntl.flock(_gemini_rate_fh, _fcntl.LOCK_EX)
    try:
        _gemini_rate_fh.seek(0)
        raw = _gemini_rate_fh.read().strip()
        last_slot = float(raw) if raw else 0.0

        now = time.time()
        my_slot = max(now, last_slot) + _GEMINI_RATE_INTERVAL

        _gemini_rate_fh.seek(0)
        _gemini_rate_fh.truncate()
        _gemini_rate_fh.write(f"{my_slot:.6f}")
        _gemini_rate_fh.flush()

        return my_slot - _GEMINI_RATE_INTERVAL - now  # < 0 ise beklemesiz
    finally:
        _fcntl.flock(_gemini_rate_fh, _fcntl.LOCK_UN)
```

### 4b. `_gemini_call` içi rate limit bloğu (app.py:4961-4968 — mevcut 4 satırı değiştir)

**SİLİNECEK:**
```python
with _gemini_rate_lock:
    _wait = _GEMINI_RATE_INTERVAL - (time.time() - _gemini_rate_last[0])
    _gemini_rate_last[0] = time.time()
if _wait > 0:
    time.sleep(_wait)
```

**EKLENECEKler:**
```python
_wait = _gemini_rate_acquire()
if _wait > 0:
    time.sleep(_wait)  # lock serbest — gevent cooperative yield
```

---

## 5. Toplam Değişiklik Özeti

| | Ekle | Sil |
|---|---|---|
| Satır | ~20 | 4 |
| Dosya | `app.py` | — |
| Test gereksinimi | `systemctl restart bist30.service` + 5dk gözlem | — |

---

## 6. Güvenlik & Edge-Case Kontrolleri

| Kontrol | Durum |
|---|---|
| `_fcntl` import var mı? | ✅ Zaten kullanılıyor (`_is_gemini_leader` satır 1751) |
| gevent + flock uyumu | ✅ Kernel blocking call → gevent yield sağlar |
| Sleep lock dışarıda | ✅ CPO-837 pattern korunuyor |
| Staging/prod izolasyonu | ✅ `GEMINI_RATE_PATH` env override mevcut |
| Thread-safe file truncate | ✅ Exclusive lock altında — race yok |
| Dosya sıfırlanırsa (reboot) | ✅ `raw = ""` → `last_slot = 0.0` → `my_slot = now + interval` |
| Worker crash ederken lock tutuyorsa | ✅ `finally` bloğu flock'u serbest bırakır; OS process exit da bırakır |

---

## 7. Deploy Checklist (Pzt 18:30 TR)

```bash
# 1. Diff kontrol
git diff app.py | grep "^[+-]" | grep -v "^---\|^+++"

# 2. Syntax check
cd /root/bist30 && /root/bist30/venv/bin/python3 -m py_compile app.py && echo OK

# 3. Restart
systemctl restart bist30.service

# 4. 5dk smoke — ilk Gemini çağrısında 429 gelmesin
# (cold cache window — min 5dk bekle)
journalctl -u bist30.service -f | grep -i "gemini\|429\|rate"
```

---

*Pre-flight: DEV-887 | Hedef: Sprint 3.5 Fix 2*
