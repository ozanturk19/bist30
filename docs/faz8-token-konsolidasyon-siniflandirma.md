# FAZ8 Kalem 6-8 — z-index / border-radius / box-shadow Token Konsolidasyon Sınıflandırması (KOD DEĞİŞMEDİ)

**Tarih:** 15.08.2026 · **Kapsam:** Yalnız sınıflandırma + konsolidasyon önerisi (DEV2-125'te "S1/S7 sınıfı bir sınıflandırma+risk turu ister" notuyla backlog'a alınan FAZ8 6-8 kalemi). Bu turda hiçbir CSS/HTML/JS değişmedi — migrasyon kararı bu doküman ışığında CPO onayına bağlı, S7/S1 emsaliyle aynı disiplin.

**Metodoloji:** 3 boyut (z-index/border-radius/box-shadow) için ayrı ayrı tam envanter (`grep -n`/`grep -o` ile tanımlı token + her kullanım yeri + ham kalıntı, örneklem değil) + her boyut için bağımsız bir ikinci ajanın SIFIRDAN aynı taramayı tekrarlayıp birincil raporu sorgulaması (S7'deki "bağımsız eleştiri" deseninin aynısı). z-index ve border-radius'ta bağımsız tur sıfır fark buldu; box-shadow'da bağımsız tur **iki gerçek hata** buldu (aşağıda B3'te) — bu hatalar bu dokümana düzeltilmiş haliyle işlendi, ham öneri değil.

---

## A) z-index — 26 tanımlı token → 6 aile-kökü önerisi (hedef: 6)

**Kaynak:** `grep -n -- '--bp-z-[a-z-]*:' static/css/tokens.css` → 26 tanım (satır 311-344). `grep -rn 'var(--bp-z-' templates/ static/` → 100 kullanım (25 farklı token; 26-25=1 ölü). Ham (`var()` dışı) sayısal z-index: **1** (`static/maintenance.html:115`, Jinja ağacı dışı statik bakım sayfası). Aritmetik: 26 = 25 canlı + 1 ölü; 100 kullanım = grep -o tekil-oluşum sayımıyla birebir. **Bağımsız doğrulama: sıfır fark.**

| Kategori | Adet | Not |
|---|---|---|
| ÖLÜ-TOKEN | 1 | `--bp-z-base` (1), 0 kullanım — silinebilir |
| BENZERSİZ-KORUNMALI | 20 | Gerçek eşzamanlı-render sıralaması taşıyan tokenlar (örn. alarm-widget üçlüsü sub-toast(997)<alarm-fab(998)<alarm-panel(999); mobile-nav sheet(260)>sheet-backdrop(250); nav-dropdown(500) her sayfada search-dropdown/fab-up'ın üstünde kalmalı) |
| BİRLEŞTİRİLEBİLİR-ADAY | 5 | search-dropdown(400)+fab-up(400) — asla aynı sayfada değil, zaten aynı değer; chart-legend(30)+chart-date-label(20) — asla aynı sayfada değil; page-toast(999)+alarm-panel(999) — asla aynı sayfada değil, zaten aynı değer; trend-strip(5) — izole, tek kullanım |

**Öneri:** 26 tanım → **6 aile-kökü** (local=1, chrome=90, overlay=300, panel=997, top=9000, +base'in silinmesi), geri kalan 19 token bu köklerden `calc(kök + sabit-offset)` ile TÜRETİLİR — hiçbir sayfada hesaplanan z-index değeri değişmez, dolayısıyla hiçbir görsel sıra bozulmaz. Gerçek birleşme (token sayısını fiilen azaltan, offset değil) yalnız 3 çiftte mümkün: search-dropdown↔fab-up, chart-legend↔chart-date-label, page-toast↔alarm-panel — üçü de "asla aynı sayfada render edilmiyor" kanıtıyla bağımsız ajan tarafından da doğrulandı.

**Konsolidasyon dışı, ayrı bilet önerilen 2 bulgu (migrasyon riski değil, mevcut bug adayı):**
1. `--bp-z-sticky` (200) hem `_mobile_nav_partial.html`'in mobil alt-nav'ı hem `portfolio.html:238`'deki `#cloudModal`'ı kullanıyor — mobilde cloudModal açıkken iki eleman aynı z-index'i paylaşıyor, gizli çakışma riski.
2. `--bp-z-toast` (9999, 16 kullanım) 5 farklı amaçla paylaşılıyor (skip-link, okuma ilerleme çubuğu, nav-more-menu, learning-mode popover, gerçek toast) — aşırı-genelleşmiş, konsolidasyon değil ayrıştırma ihtiyacı olabilir.

---

## B) border-radius — 16 tanımlı token → 4 basamak + pill önerisi (hedef: 4)

**Kaynak:** `grep -n -- '--bp-radius[a-z0-9-]*:' static/css/tokens.css` ham 17 satır → **1'i yorum bloğu içi metin** (tokens.css'in bilinen "yorum ayrıştırıcı tuzağı", bkz. proje hafızası), gerçek tanım **16**. `grep -o 'var(--bp-radiusX)'` occurrence-bazlı toplam **520** kullanım (satır-bazlı sayım 499 — bazı satırlarda shorthand ile 2 token birden geçiyor, occurrence daha doğru). Ham (`var()` dışı) sayısal radius: **108** satır (33'ü `50%` dairesel, ayrı kategori). Bağımsız tur: **sıfır fark**, tüm 16 tokenın kullanım sayısı ve örnek dosya/satır atıfları tek tek doğrulandı.

| Kategori | Adet | Not |
|---|---|---|
| BENZERSİZ-KORUNMALI | 1 | `--bp-radius-pill` (999px) — tam-yuvarlak semantiği px ölçeğine indirgenemez |
| BİRLEŞTİRİLEBİLİR-ADAY | 14 | 4 basamağa (xs/badge/md/lg) toplanabilir, aşağıda Δ-risk sınıflı |
| AYRI/BEKLEYEN KARAR (ne 4'lü merdivende ne pill'de) | 1 | `--bp-radius-20` (20px, 16 kullanım) — `docs/faz5-cekirdek-komponent-analiz.md §6`'da ve tokens.css:381-386 yorumunda zaten "CPO onayı gerekir / per-örnek yükseklik doğrulaması yapılmadı" notuyla açık soru; bu tur çözmedi |

**Önerilen 4 basamak** (hedef değer = kümedeki en yüksek kullanımlı mevcut token, migrasyon acısı minimize edilerek seçildi):

| Basamak | Hedef | Kapsanan (Δ, kullanım) | Toplam kullanım | Risk |
|---|---|---|---|---|
| XS | 3px (`-sm`) | `-1`(1px,Δ2 ⚠️) · `-xs`(2px,Δ1) · `-sm`(3px,Δ0) | 42 | 1 sınırda |
| Badge | 4px (`-4`) | `-5`(5px,Δ1) · `-4`(4px,Δ0) | 51 | görünmez |
| MD | 8px (`-md`) | bare `--bp-radius`(6px,143,Δ2 ⚠️ **en yüksek hacim**) · `-7`(7px,Δ1) · `-9`(9px,Δ1) · `-md`(8px,Δ0) | 279 | 1 sınırda (en riskli tekil) |
| LG | 10px (`-lg`) | `-11`(11px,Δ1) · `-xl`(12px,34,Δ2 ⚠️) · `-14`(14px,9,Δ4 🔴) · `-16`(16px,1,Δ6 🔴) · `-lg`(10px,Δ0) | 131 | 2 sınırda + 2 açıkça görünür |

**Δ≤1px (8 birleşme): kesinlikle güvenli/görünmez. Δ=2px (3 birleşme, ⚠️): "<2px" kuralının tam sınırında, görsel QA önerilir. Δ≥4px (2 birleşme, 🔴 — `-14`→10px, `-16`→10px): açıkça fark edilir bir törpüleme, "fark yok" iddiası DEĞİL — özellikle modal/panel gibi büyük yüzeylerde stakeholder onayı gerektirir.**

---

## C) box-shadow — 9 tanımlı token → 2 aile (nötr elevation hedef 3 + renkli glow ayrı) önerisi

**Kaynak:** `grep -n -- '--bp-shadow[a-z0-9-]*:' static/css/tokens.css` → 9 tanım (satır 286-301): 6 **nötr elevation** (sm/md/lg/dropdown/up-sm/up-lg) + 3 **renkli glow/focus-ring** (focus-al/focus-sat/glow-volume — hedef "3"ün kapsamı DIŞINDA, ayrı aile). Nötr ailenin `var()` kullanımı: sm4+md4+lg4+dropdown6+up-sm1+up-lg1 = **20**. Renkli aile: **0** kullanım (3'ü de ÖLÜ-TOKEN — ama ihtiyaç canlı, aşağıda). Ham (`var()` dışı) box-shadow: **32** satır.

| Kategori | Adet | Not |
|---|---|---|
| BENZERSİZ-KORUNMALI | 3 | sm/md/lg — orantılı 3 basamaklı nötr elevation ölçeği, konsolidasyonun HEDEFİ |
| BİRLEŞTİRİLEBİLİR-ADAY (nötr aile) | 3 | dropdown(6 kullanım)→md'ye; up-sm+up-lg → **doğrulama sonrası GERİ ÇEKİLDİ, bkz. C3** |
| ÖLÜ-TOKEN (ama ihtiyaç canlı) | 3 | focus-al/focus-sat/glow-volume — 0 `var()` kullanımı ama ~24-28 ham satır aynı değerleri elle tekrar yazıyor |

**C1) sm/md/lg çekirdeği + dropdown→md birleşimi — bağımsız turda ONAYLANDI, uygulanabilir.** dropdown (offset12/blur32/alpha.55) md'ye (8/24/.50) lg'den daha yakın; 6 çağrı yeri (`index.html`×4, `hisse.html`, `varlik.html`) `var(--bp-shadow-md)`'ye yönlendirilebilir, gerçek elevation basamağı bozulmaz.

**C2) Asıl yüksek-etkili fırsat konsolidasyon değil, renkli ailenin bağlanması.** focus-al/focus-sat/glow-volume 0 kullanımda görünüyor ama 24-28 ham satır (`rgba(var(--bp-al-rgb)/--bp-sat-rgb/--bp-volume-rgb),…)`) bu tokenların değerlerini elle tekrar yazıyor. **glow-volume için "ham satır token ile birebir aynı" doğrulandı** (`index.html:626` + `_premium_modal.html:74`, karakter karakter eşleşiyor) — bağlanması güvenli.

**C3) 🔴 focus-sat İÇİN DÜZELTME (bağımsız tur bulgusu, birincil rapor YANLIŞ):** Birincil ajan `index.html:1299/1303` ve `hisse.html:394/398`'deki `0 0 6px rgba(var(--bp-sat-rgb),.18)` satırlarını token `--bp-shadow-focus-sat: 0 0 0 6px rgba(var(--bp-sat-rgb),.18)` ile "birebir aynı" saymıştı. **Geometri farklı**: ham satır 3-değerli (blur=6px, spread YOK → yumuşak halo), token 4-değerli (blur=0, spread=6px → keskin focus-ring). Yalnız renk/alfa örtüşüyor. Bu satırları doğrudan tokena bağlamak sinyal rozetlerindeki yumuşak parıltıyı sert bir halkaya çevirip **görsel regresyona yol açar** — basit token-tekilleştirme değil, gerçek görünüm değişikliği. **Bu görevde önerilmiyor, ayrı görsel karar gerektirir.**

**C4) 🔴 up-sm/up-lg birleştirmesi İÇİN DÜZELTME (bağımsız tur bulgusu, birincil öneri GERİ ÇEKİLDİ):** Birincil ajan bu ikisini "iki ayrı büyüklük kademesini haklı çıkaracak kanıt yok" diyerek birleştirilebilir saymıştı. Bağımsız tur bağlamı kontrol etti: `up-sm` (`hisse.html:1739`) ince, sabit bir alt aksiyon çubuğunda (`padding:6px 10px`); `up-lg` (`_mobile_nav_partial.html:59`) `max-height:75vh` tam-ekran bottom-sheet modalinde. Bu tam olarak sm/md/lg'yi "korunmalı" saydıran "elevation ağırlığı UI ağırlığına göre ölçeklenir" mantığının yukarı-gölge versiyonu — ince çubuk ile tam-ekran sheet'in aynı gölge ağırlığını paylaşması savunulamaz. **Bu birleşme önerilmiyor, up-sm ve up-lg AYRI kalmalı.**

**Sonuç — hedef "3"e gerçekçi yol:** sm/md/lg çekirdeği korunur + dropdown→md (C1, güvenli) = **fiilen 3 nötr elevation tokenına iner** (up-sm/up-lg C4 sonrası ayrı kalır, bunlar "yukarı-gölge" adında farklı bir alt-aile — konsolidasyon hedefinin doğal bir istisnası). Renkli glow ailesi (3 token) hedefin dışında ayrı bir sınıf.

---

## Bağımsız eleştiri özeti

3 boyut için 3 ayrı bağımsız ajan, birincil ajanın verisine bakmadan SIFIRDAN aynı grep taramasını tekrarladı:
- **z-index:** 26/26 token, 100/100 kullanım, sınıflandırma tamamen doğrulandı — sıfır fark.
- **border-radius:** 16/16 token, 520/520 occurrence, tier gruplama toplamı (42+51+279+131+1+16=520) doğrulandı — sıfır fark.
- **box-shadow:** sayısal iskelet (9 token, kullanım sayıları, 32 ham kalıntı) doğrulandı ama **iki gerçek hata** bulundu ve düzeltildi (C3 focus-sat geometri karışıklığı, C4 up-sm/up-lg birleştirme gerekçesi) + küçük bir eksik-enümerasyon (ham kalıntı listesinde 2 atlanan satır, toplam sayıyı etkilemiyor).

S7'deki disiplinle aynı: bu doküman yalnız sınıflandırma + risk raporu, **hiçbir migrasyon uygulanmadı**.

## Sıradaki

Migrasyon kararı (hangi token isimleri kalıcılaşsın, Δ≥2px birleşmeler için görsel QA kim yapacak, `--bp-radius-20`↔pill açık sorusu, box-shadow renkli ailenin bağlanması) CPO onayı bekliyor — S1/S7/T3.4 emsaliyle aynı sınıf (kod-değiştiren ama görsel-tarafsız migrasyon, tek seferlik onay). En düşük riskli, en yüksek etkili 3 alt-adım (uygulanırsa ayrı onaylanabilir): (1) z-index'teki 3 "asla aynı sayfada değil" çiftinin birleştirilmesi, (2) box-shadow dropdown→md birleşimi (C1), (3) box-shadow glow-volume'un 2 ham satıra bağlanması (C2) — üçü de bağımsız turdan sıfır itirazla geçti.
