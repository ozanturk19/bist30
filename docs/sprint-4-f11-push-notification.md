# Sprint 4 F11 — Web Push Bildirim Entegrasyonu Spec

**Tarih:** 28 Haziran 2026  
**Sprint:** 4 W1 (30 Haz – 6 Tem 2026)  
**Effort:** S (F15 Dark/Light ile paralel)  
**Ticket:** F11

---

## 1. Mevcut Durum (Altyapı Hazır)

Backend ve service worker altyapısı **tamamen mevcut**. Eksik olan: **frontend JavaScript'i ve kullanıcı UX akışı**.

| Bileşen | Durum | Dosya:Satır |
|---|---|---|
| Service Worker push handler | ✅ Hazır | `static/sw.js:87-119` |
| VAPID key setup | ✅ Hazır | `app.py:126-139` |
| Subscriber storage (`push_subs.json`) | ✅ Hazır | `app.py:143-146` |
| `POST /api/push/subscribe` | ✅ Hazır | `app.py:9231-9253` |
| `POST /api/push/unsubscribe` | ✅ Hazır | `app.py:9256-9268` |
| `GET /api/push/vapid-public-key` | ✅ Hazır | `app.py:9225-9228` |
| `_broadcast_push_changes()` | ✅ Hazır | `app.py:470-540` |
| Watchlist-aware push filtreleme | ✅ Hazır | `app.py:487` |
| Rate limit (24h/1 per ticker, 3/h global) | ✅ Hazır | `app.py:492-494` |
| **Frontend JS subscribe flow** | ❌ Eksik | `static/main.js` |
| **İzin isteme UI (bell icon)** | ❌ Eksik | `templates/` |
| **Watchlist subscription sync** | ❌ Eksik | `static/main.js` |

---

## 2. Frontend Mimari

### 2a. Service Worker Kaydı (zaten kısmen mevcut)

SW zaten `static/sw.js`'de kayıtlı. Push handler `sw.js:88` — aktif.  
Gerekli: SW kayıt sırasında `pushManager.subscribe()` akışı eklenmesi.

### 2b. Push Subscription Akışı (main.js — eklenecek)

```javascript
// VAPID public key'i base64 → Uint8Array dönüşümü
function urlBase64ToUint8Array(base64String) {
  const padding = '='.repeat((4 - base64String.length % 4) % 4);
  const base64 = (base64String + padding)
    .replace(/-/g, '+').replace(/_/g, '/');
  return Uint8Array.from(atob(base64), c => c.charCodeAt(0));
}

async function initPushNotifications() {
  // 1. Browser desteği kontrolü
  if (!('serviceWorker' in navigator) || !('PushManager' in window)) return;

  // 2. Mevcut izin durumunu oku
  const permission = Notification.permission;
  if (permission === 'denied') return;  // Kullanıcı engelledi, UI'da "engellendi" göster

  // 3. SW registration'ı al
  const reg = await navigator.serviceWorker.ready;

  // 4. Mevcut subscription var mı?
  let sub = await reg.pushManager.getSubscription();

  // 5. Yoksa abone ol (izin gerektirir)
  if (!sub) {
    const vapidRes = await fetch('/api/push/vapid-public-key');
    const { publicKey } = await vapidRes.json();
    sub = await reg.pushManager.subscribe({
      userVisibleOnly: true,
      applicationServerKey: urlBase64ToUint8Array(publicKey),
    });
  }

  // 6. Watchlist'i subscription'a ekle ve sunucuya kaydet
  const watchlist = getWatchlistTickers();  // mevcut fonksiyon
  await fetch('/api/push/subscribe', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ ...sub.toJSON(), watchlist }),
  });
}
```

**Not:** Watchlist değiştiğinde `/api/push/subscribe` tekrar çağrılmalı (sunucu `existing_idx is not None` ile REPLACE yapar — `app.py:9245-9246`).

---

## 3. İzin Akışı (Permission Flow)

### 3a. Trigger: Kullanıcı Etkileşimi Zorunlu

`Notification.requestPermission()` yalnızca **kullanıcı etkileşimiyle** (tıklama) tetiklenebilir (tarayıcı güvenlik kısıtı). Otomatik çağrı iOS/Chrome'da engellenir.

### 3b. UI Bileşeni — Zil İkonu

**Konum:** Header sağ tarafı (varsa kullanıcı menüsü yanında)  
**Durumlar:**

| İkon | Durum | Açıklama |
|---|---|---|
| 🔔 (outline) | `default` | İzin verilmemiş, tıklanabilir |
| 🔔 (filled/renkli) | `granted` | Aktif, tıkla → unsubscribe |
| 🔕 | `denied` | Tarayıcı engeli, tıklanamaz |

**HTML:**
```html
<button id="push-bell" class="push-bell-btn" aria-label="Bildirimler">
  <svg><!-- zil ikonu --></svg>
</button>
```

**JS:**
```javascript
document.getElementById('push-bell')?.addEventListener('click', async () => {
  if (Notification.permission === 'denied') {
    showToast('Bildirimler tarayıcıdan engellendi. Tarayıcı ayarlarından açın.');
    return;
  }
  if (Notification.permission === 'granted') {
    await unsubscribePush();
    updateBellUI('default');
  } else {
    const perm = await Notification.requestPermission();
    if (perm === 'granted') {
      await initPushNotifications();
      updateBellUI('granted');
    }
  }
});
```

---

## 4. Watchlist Senkronizasyonu

Kullanıcı watchlist'e hisse eklediğinde/çıkardığında push subscription'ı güncellenmeli:

```javascript
// Mevcut watchlist güncelleme fonksiyonuna ek
async function onWatchlistChange() {
  // ... mevcut kod ...
  
  // Push subscription'ı watchlist ile senkronize et
  if (Notification.permission === 'granted') {
    const reg = await navigator.serviceWorker.ready;
    const sub = await reg.pushManager.getSubscription();
    if (sub) {
      await fetch('/api/push/subscribe', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ ...sub.toJSON(), watchlist: getWatchlistTickers() }),
      });
    }
  }
}
```

---

## 5. Unsubscribe

```javascript
async function unsubscribePush() {
  const reg = await navigator.serviceWorker.ready;
  const sub = await reg.pushManager.getSubscription();
  if (!sub) return;
  
  await fetch('/api/push/unsubscribe', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ endpoint: sub.endpoint }),
  });
  await sub.unsubscribe();
}
```

---

## 6. VAPID Key Üretimi (Kurulum — bir kez)

Sunucuda henüz `vapid_private.pem` ve `vapid_public.txt` yoksa:

```bash
cd /root/bist30
/root/bist30/venv/bin/python3 -c "
from py_vapid import Vapid
v = Vapid()
v.generate_keys()
v.save_key('vapid_private.pem')
with open('vapid_public.txt', 'w') as f:
    f.write(v.public_key.decode('utf-8'))
print('VAPID_PUBLIC=', v.public_key.decode())
"
```

`VAPID_PUBLIC` değeri `.env` dosyasına da eklenebilir (app.py:128 otomatik okur).

---

## 7. Tarayıcı Uyumluluğu

| Tarayıcı | Web Push | Notlar |
|---|---|---|
| Chrome 50+ | ✅ | Tam destek |
| Firefox 44+ | ✅ | Tam destek |
| Safari 16+ (macOS/iOS) | ✅ | iOS 16.4+ PWA olarak açıksa |
| Safari < 16 | ❌ | Fallback: sessiz |
| Samsung Internet | ✅ | Chromium tabanlı |

**iOS notu:** Push notification iOS'ta yalnızca PWA olarak "Ana ekrana ekle" ile çalışır (Safari browser tab'ında çalışmaz). `manifest.json` ve `icon-192.png` zaten mevcut.

---

## 8. Payload Formatı (Mevcut — `app.py:512-518`)

```json
{
  "title": "AKBNK — AL ▲ Güçlü Trend",
  "body": "Akbank sinyali değişti: SAT → AL",
  "url": "/hisse/AKBNK",
  "tag": "borsapusula-signal",
  "icon": "/static/icon-192.png"
}
```

`tag: "borsapusula-signal"` → aynı tag'li bildirim varsa update eder (spam önler).  
`renotify: true` → aynı tag tekrar gelse bile titreşim/ses verir (`sw.js:96`).

---

## 9. Test Planı

```
1. VAPID anahtarları /root/bist30/vapid_private.pem + vapid_public.txt var mı?
2. Chrome DevTools → Application → Service Workers → push-bell tıkla
3. İzin ver → zil dolu görünsün
4. DevTools → Application → Push → test payload gönder
5. Bildirim geldi mi? İkona tıklandığında doğru URL açılıyor mu?
6. Watchlist'e yeni hisse ekle → /api/push/subscribe tekrar çağrıldı mı?
7. Unsubscribe: zil tıkla → /api/push/unsubscribe çağrıldı mı?
8. 429 durumu: 24h'te 2. push aynı ticker'a → sessizce drop edilmeli
```

---

## 10. Implementation Sırası (Sprint 4 W1)

1. **Gün 1:** Zil ikonu HTML + CSS (dark/light tema uyumlu)
2. **Gün 2:** `main.js` — `initPushNotifications()` + `urlBase64ToUint8Array()`
3. **Gün 3:** Permission flow + bell state güncellemesi
4. **Gün 4:** Watchlist sync + unsubscribe
5. **Gün 5:** Test + deploy (seans sonrası)

---

*Spec: DEV-887 | Hedef: Sprint 4 W1*
