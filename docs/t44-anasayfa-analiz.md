# T4.4 — Ana Sayfa 30→6 Blok Konsolidasyonu — Envanter + Plan + Eleştiri

Üretildi: Cum 14.08.2026 TR, DEV2 (workflow: 4 harita ajanı + 1 tasarım ajanı + 1 bağımsız eleştiri ajanı)
Kaynak: `templates/index.html` (5534 satır)

---

## 1. BLOK ENVANTERİ (satır 1899-5534, görünür HTML + JS)

### Görünür HTML iskeleti (1899-2605)

1. satır 1899-1981: Header (logo+nav+aksiyonlar)
2. satır 1984-1988: Makro Ticker Bandı (`#macroTrack`, `/api/macro` 180s)
3. satır 1991-1993: Main container + `_stale_banner.html` include
4. satır 1996-2031: Onboarding banner ("Öğrenme Modu")
5. satır 2034-2070: Dual Endeks Kartları (BIST100/BIST30, sparkline)
6. satır 2073-2084: Öne Çıkanlar (Güçlü Trend + Hareketliler)
7. satır 2088-2115: Grafik Accordion — **`display:none aria-hidden` — DEVRE DIŞI**
8. satır 2117-2135: Stats Bar (Toplam/AL/SAT/BEKLE/Hacim Onaylı)
9. satır 2138-2153: Market Breadth Bar
10. satır 2156-2191: Market Summary hero ("Bugünün Özeti")
11. satır 2194-2199: Preset Chips
12. satır 2203-2210: AI Piyasa Özeti (macroSummaryBar)
13. satır 2214-2220: İdeal Giriş Şeridi
14. satır 2224-2245: Backtest Güven Rozeti
15. satır 2248-2308: Gündem & Haberler (Makro/Hisse sekmesi + Bilanço mini kutu)
16. satır 2310-2319: PWA Install Banner
17. satır 2321-2360: Bildirim Çubuğu (subscribeBar)
18. satır 2363-2380: Filtre çubuğu
19. satır 2382-2429: Gelişmiş Screener Paneli
20. satır 2431-2436: Sektör filtreleri
21. satır 2438-2446: Aktif Filtreler Kutusu
22. satır 2448-2493: Ana Veri Tablosu (`#mainTable` + `#mobileCards`)
23. satır 2497-2501: Alarm FAB
24. satır 2503-2515: Alarm Panel (Takip Listem)
25. satır 2517-2540: Sticky Subscription Toast
26. satır 2544-2605: Footer

### JS fonksiyonel katman (2609-5449, veri/davranış katmanı, HTML üretmiyor)

- 2901-3067: sinyal tooltip, sparkline, chart accordion, endeks fetch
- 3074-3164: SSE canlı fiyat motoru
- 3182-3486: filtre state motoru, gelişmiş filtre paneli, `fetchData()` (merkez veri borusu), `renderMarketSummary()`
- 3488-3709: hero panel, stats/breadth, sektör butonları
- 3711-4120: alarm modalı, `renderTable()` (çekirdek blok)
- 4122-4816: filtre chip sync, skeleton loader, watchlist/alarm sistemi, toast, sticky subscription
- 4860-5449: gündem render, backtest rozeti, PWA/SW/push, arama autocomplete, nav dropdown, AI özet+gündem tab switcher

---

## 2. ÖNERİLEN 6 HEDEF BLOK EŞLEMESİ

### 1. PİYASA NABZI
**Gömülen:** Makro ticker (1984-1988) + Dual endeks kartları (2034-2070) + Stats bar (2117-2135) + Breadth bar (2138-2153)
**Değişiklik:** 4 yatay şerit → tek panel. Stats/Breadth GÖRSEL olarak yakınlaşıyor (dedup DEĞİL — bkz. eleştiri #6).

### 2. BUGÜNÜN ÖZETİ ⚠️ SEO RİSKİ — CPO/Ozan onayı olmadan uygulanmayacak
**Gömülen:** Market summary hero (2156-2191) + Öne Çıkanlar (2073-2084) + AI özet (2203-2210) + İdeal giriş (2214-2220) + Backtest rozeti (2224-2245) + Gündem&Haberler (2248-2308)
**Değişiklik:** 6 blok → iç sekmeli/akordeonlu tek kart.
**RİSK:** Sekme içeriği DOM'da SSR ile hazır+CSS-gizli mi, yoksa fetch-on-click mi olacağı belirlenmeden uygulanırsa Google crawler içeriği görmeyebilir (ana sayfa zaten GSC -%31 de-index trendinde).

### 3. FİLTRE — ilk uygulanacak, düşük risk
**Gömülen:** Preset chips (2194-2199) + Filtre çubuğu (2363-2380) + Gelişmiş panel (2382-2429) + Sektör filtreleri (2431-2436) + Aktif filtreler kutusu (2438-2446)
**Değişiklik:** 5 ayrı filtre yüzeyi → tek bileşen (chip satırı + toggle'lı gelişmiş panel + aktif-filtre özet). State motoru (`setFilter`/`applyPreset`/localStorage/URL) DEĞİŞMİYOR, yalnız DOM konumlandırması.

### 4. TABLO — düşük risk, çoğunlukla dokümantasyon
**Gömülen:** Ana tablo (2448-2493, değişmiyor) + Onboarding banner (1996-2031, tablo üstü şerit) + Alarm FAB/Panel (2497-2515, "tabloya ait aksiyon katmanı" olarak kavramsal bağlanıyor — KOD DEĞİŞMİYOR)

### 5. TEK ÜYE-KAZANIM BLOĞU ⚠️ BÜYÜME KARARI — Ozan onayı ŞART
**Gömülen:** Bildirim çubuğu (2321-2360) + Sticky toast (2517-2540) + PWA banner (2310-2319) + Premium modal tetikleyicisi
**RİSK:** 4 bağımsız dönüşüm tetikleyicisini (anında/25sn/scroll%40/premium-tık) 1'e indirmek conversion rate'i düşürebilir — her tetikleyicinin ayrı verisi yok, körü körüne birleştirilmemeli.

### 6. FOOTER
Değişmiyor.

---

## 3. KALDIRILANLAR (aday, Ozan onayı gerekli)

**Grafik Accordion** (satır 2088-2115, JS 2682-2870, ~190 satır) — zaten `display:none aria-hidden`, kullanıcı görmüyor. Hisse detayında zaten candlestick var (duplicate). **NOT: bu madde kesinleşmiş değil, BELİRSİZ listesinde — silme kararı Ozan'a ait.**

---

## 4. BELİRSİZ / OZAN-CPO ONAYI GEREKTİREN KARARLAR

1. Bugünün Özeti iç yapısı (sekme/akordeon/tek-scroll)
2. Üye-kazanım tek-CTA mimarisi + hangi CTA öncelikli
3. Grafik Accordion'un tamamen silinmesi mi, backlog'da kalması mı
4. Gelişmiş filtre panelinde chip vs dropdown (5+ seçenek)
5. Premium modal tetikleme noktası/kopyası

---

## 5. UYGULAMA SIRASI (risk artan)

1. **Filtre birleştirme** — EN DÜŞÜK RİSK, ilk uygulanacak
2. **Piyasa Nabzı görsel gruplama** (dedup YOK, yalnız yakınlaştırma)
3. **Tablo'ya onboarding/alarm bağlama** — çoğunlukla dokümantasyon
4. **Bugünün Özeti** — SEO doğrulaması sonrası, CPO onayı ile
5. **Tek Üye-Kazanım Bloğu** — Ozan onayı + conversion verisi sonrası
6. **Grafik Accordion silme** — Ozan onayı sonrası, en son (geri dönüşü yok)

Her adım: eski blok geçici olarak `display:none` + İLGİLİ JS HANDLER'LARI DA DEVRE DIŞI (duplicate ID/handler çakışması riski — eleştiri #5), yeni blok QA'dan geçince eski silinir. Her commit bağımsız rollback edilebilir olmalı.

---

## 6. BAĞIMSIZ ELEŞTİRİNİN TAM BULGU LİSTESİ

1. **CİDDİ** — Üye-kazanım tek-CTA: büyüme kararı, UI dedup değil, conversion verisi olmadan karar verilemez
2. **CİDDİ** — Bugünün Özeti sekmeleşmesi: SEO/crawl riski doğrulanmamış (fetch-on-click mi, SSR+CSS-gizli mi belirsiz)
3. **ORTA** — AI özet ile Gündem/Makro sekmesi "aynı içerik" iddiası ispatsız
4. **ORTA** — Grafik Accordion hem "silindi" hem "belirsiz" listesinde çelişkiliydi (düzeltildi → tamamen BELİRSİZ)
5. **ORTA** — `display:none` paralel-tutma stratejisi duplicate ID/JS-handler çakışma riskini ele almıyor
6. **ORTA** — Stats Bar/Breadth Bar "aynı veri" iddiası doğrulanmadı
7. **DÜŞÜK** — Alarm FAB "blok sayılmıyor" kozmetik yeniden-etiketleme, gerçek konsolidasyon değil — öyle raporlanmamalı
8. **DÜŞÜK** — PWA install banner'ın `beforeinstallprompt` browser-eligibility bağımlılığı ele alınmamış
