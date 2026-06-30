# W3 tokens.css Migrate Analiz — Çar 01 Tem 2026

**Hazırlayan:** DEV | **Tarih:** Sal 30 Haz 2026 14:00 TR  
**Kapsam:** CPO-921 → W3 #0 analiz görevi

---

## Özet

31 template incelendi. 2 gruba ayrıldı:

| Grup | Şablon Sayısı | Durum | Migrate Türü |
|------|--------------|-------|-------------|
| A | 14 template + 2 partial | Zaten `var(--bp-*)` kullanıyor, inline `:root` tanımlı | **Hızlı** — sadece link ekle + inline `:root` sil |
| B | 15 template | Hardcoded hex renk, `var(--bp-*)` YOK | **Tam migrate** — link + hex → var() dönüşümü |

**Çar 09:00 hedefi:** Sadece Grup A (hızlı migrate). Grup B ayrı görev.

---

## Grup A — Template Migrate Listesi (Risk Sırası)

### Adım 1: Düşük risk (sinyal sayfaları, az kullanım)

| # | Template | Token kullanım | Inline def sayısı | Notlar |
|---|---------|----------------|------------------|--------|
| 1 | `sinyal_performans.html` | 3 uses | 1 (eksik) | Çok az token, düşük trafik |
| 2 | `portfolio.html` | 3 uses | 1 (eksik) | Düşük trafik |
| 3 | `heatmap.html` | 24 uses | 1 | Sector map, medium trafik |
| 4 | `sektor_karsilastir.html` | 24 uses | 1 | Sektör karşılaştırma |

### Adım 2: Orta risk (detay sayfaları)

| # | Template | Token kullanım | Inline def sayısı | Notlar |
|---|---------|----------------|------------------|--------|
| 5 | `sektor_harita.html` | 28 uses | 1 | — |
| 6 | `bilanco_takvimi.html` | 28 uses | 1 | — |
| 7 | `backtest.html` | 34 uses | 1 | — |
| 8 | `ozet.html` | 32 uses | 1 | — |
| 9 | `profil.html` | 32 uses | 1 | — |
| 10 | `karsilastir.html` | 42 uses | 1 | — |
| 11 | `gundem.html` | 44 uses | 1 | — |
| 12 | `virtual_portfolio.html` | 51 uses | 1 | — |

### Adım 3: Yüksek trafik (en son)

| # | Template | Token kullanım | Inline def sayısı | Notlar |
|---|---------|----------------|------------------|--------|
| 13 | `hisse.html` | 49 uses | 2 (eksik) | **DİKKAT:** Inline def eksik token içeriyor |
| 14 | `index.html` | 295 uses | 2 (tam) | **LANDING PAGE** — tokens.css ile tam eşleşiyor |

---

## hisse.html Özel Durum

**Problem:** hisse.html inline `:root` tanımı EKSİK token içeriyor:

Eksik tokenlar (inline'da yok, tokens.css'te var):
```
--bp-al-bg, --bp-al-bd
--bp-sat-bg, --bp-sat-bd  
--bp-bkl-bg, --bp-bkl-bd
--bp-surface3, --bp-brand-d
--bp-radius (sadece --bp-radius-sm var)
```

**Sonuç:** tokens.css link edilince bu tokenlar KAZANILACAK. Mevcut hardcoded hex kullanan hisse.html stilleri değişmeyecek (zaten var() kullanmıyorlar). Görsel etki: **sıfır veya pozitif** (ekstra token = potansiyel gelecek kayıp).

---

## index.html Özel Durum

**Durum:** inline `:root` ve `html[data-theme="light"]` tanımları tokens.css ile **tam eşleşiyor**. 2 tanım dark + light = ikisi de aynı değerlerde.

**Sonuç:** link ekle + inline tanım sil = sıfır görsel değişim. En güvenli migrate.

---

## Migrate Teknik Adımları (Her Template)

```html
<!-- HEAD'e ekle (mevcut CSS linklerden ÖNCE veya sonra, <style>'dan önce) -->
<link rel="stylesheet" href="/static/css/tokens.css">
```

**Silinecek bloklar:**
```css
/* Bu iki blok style içinden kaldırılacak: */
:root {
  --bp-bg: #0e0e12;
  /* ... tüm --bp-* tanımları ... */
}
html[data-theme="light"] {
  --bp-bg: #f5f6fa;
  /* ... tüm --bp-* tanımları ... */
}
```

**KORUNACAK:** Tüm `var(--bp-*)` kullanımları, diğer stil kuralları.

---

## Grup B — Full Migrate (Ayrı Görev, W3 #2+)

Bu templateler `var(--bp-*)` KULLANMIYOR, hardcoded renk var:

```
abd_tarama.html, blog.html, blog_article.html, gizlilik.html,
gucu_yuksek.html, hakkinda.html, hisseler.html, iletisim.html,
kategori.html, kripto_gate.html, metodoloji.html, offline.html,
tarama.html, varlik.html, yasal.html
```

Bu templateler için ek görsel analiz + hex → var() toplu dönüşüm gerekli.
Önce Visual Regression baseline alınmalı (Per planı), sonra migrate.

---

## CPO-921 Plan Uyumu

| CPO Planı | DEV Analiz | Fark |
|-----------|-----------|------|
| index.html → hisse.html → diğer | diğer → hisse.html → index.html | **Ters risk sırası öneriliyor** |
| Sebep (CPO): En kritik sayfalar önce validate | Sebep (DEV): Düşük trafikli sayfalarda token.css doğrulanır, sonra kritik sayfalara güvenle geçilir | — |

**CPO onayı gerekiyor:** Hangi sıra? (DEV önerisi: risk-based = küçükten büyüğe)

---

## Tahmini Çar Süresi

- Grup A (14 template) migrate: ~2.5-3h (her template ~10-15dk)
- Smoke test her migrate sonrası: ~15dk toplam
- index.html + hisse.html ayrıca dikkatli: +30dk
- **Toplam: 3-4h** ✓ (CPO planı ile uyumlu)
