# T5.9 — Modal/Dialog Focus-Trap Sınıflandırması

**Backlog maddesi (07.08.2026, Master Dönüşüm Programı FAZ5):**
> "Modal/dialog focus-trap (7 bileşen: premium-modal artık silinecek ama alert-modal + mobil sheet kalıyor) — Tab döngüsü modal içinde kalır. Kabul ölçütü: `key==='Tab'` yönetimi 7/7 bileşende."

**Yöntem:** 2 bağımsız paralel salt-okur SSH ajanı (biri class/id tabanlı tarama, diğeri backdrop/toggle-davranışı tabanlı tarama, birbirini görmeden) → 1 sentez ajanı (2 gerçek çelişkiyi kendi SSH doğrulamasıyla çözdü) → 1 tamamen bağımsız kör doğrulama ajanı (kendi sıfırdan taramasını yapıp sentezle karşılaştırdı). S1/S7/T3.4/T5.2/T5.4/T8-serisi/T1.5-serisi/T2.4/api-macro/api-data/template-literal/mono-font/kart-zemin ile aynı desen. Sonuç: **sıfır anlaşmazlık** — doğrulama ajanı kendi bağımsız taramasında birebir aynı 5 bileşene, birebir aynı satır numaralarına ve birebir aynı sonuca ulaştı.

## SONUÇ: BACKLOG SAYISI YANLIŞ (7 değil 5), AMA GERÇEK BOŞLUK VAR (4/5 zaten çözülmüş, 1/5 açık)

Bu, önceki "iddia tamamen geçersiz" sınıflandırmalarından (T2.4, api-macro, template-literal) farklı — burada backlog'un **sayısı yanlış ve "hiçbiri trap yapmıyor" örtük varsayımı da yanlış**, ama gerçek ve somut bir kapsam boşluğu da var. Kısmi-geçerli sınıfı.

### 1) `static/js/focus-trap.js` — merkezi utility zaten kurulu ve sağlam

`window.bpTrapFocus(container, onEscape)` (43 satır): container içindeki focusable elementleri (`a[href], button:not([disabled]), input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])`) bulur, ilkine focus verir, `keydown` dinler — Tab ile son elementten ilkine (Shift+Tab ile tersi) döngü kurar, Escape'te opsiyonel `onEscape` callback'ini çağırır. Döndürdüğü `release()` fonksiyonu hem listener'ı kaldırır hem odağı modal-öncesi elemente iade eder (WCAG 2.4.3 tam kapsamı: Tab-trap + Escape + odak-iade tek fonksiyonda).

### 2) Gerçek backdrop taşıyan modal/dialog/sheet sayısı: 5 (7 değil)

| # | Bileşen | Dosya:satır | `bpTrapFocus` | Escape | `role=dialog` | `aria-modal` |
|---|---|---|---|---|---|---|
| 1 | Alert Ayarları Modal | `templates/index.html:3762-3813` (trap 3802) | **EVET** — `onEscape=closeAlertModal` | evet | evet | evet |
| 2 | Premium/Paywall Modal | `templates/_premium_modal.html:115-154` (trap 150) | **EVET** — `onEscape=closePremiumModal` | evet | evet | evet |
| 3 | Cloud Sync Modal | `templates/portfolio.html:684-696` (trap 691) | **EVET** — `onEscape=closeCloudSync` | evet | evet | evet |
| 4 | Mobil Nav "Daha" Bottom Sheet (`mbnSheet`) | `templates/_mobile_nav_partial.html:147-187` (trap 185) | **EVET** ama `bpTrapFocus(s)` — `onEscape` argümanı **verilmemiş** | evet, ama bpTrapFocus üzerinden değil — bağımsız global `keydown` listener (satır 187) | evet | evet |
| 5 | 🔴 Site İçi Arama / Cmd+K (`bpSearchOverlay`/`.bp-search-modal`) | `static/bp-search.js:242-296` | **HAYIR** — dosyada `bpTrapFocus` sıfır kez geçiyor (grep doğrulandı) | evet, kendi bağımsız `keydown` listener'ı ile | evet (243) | **HAYIR** (grep doğrulandı, yalnız `role="dialog"` var) |

**Not (#4, mimari tutarsızlık, işlevsel değil kritik):** Mobil sheet'te Escape ayrı bir global listener ile çözülmüş, `bpTrapFocus`'un kendi `onEscape` parametresi kullanılmamış — çalışıyor ama diğer 3 bileşenle tutarsız. Backlog gap'i değil, küçük bir tutarlılık notu.

**Backlog'un "premium-modal artık silinecek" notu güncel değil** — `_premium_modal.html` hâlâ canlı, `index.html`'de tek include noktası var (satır 5484), silinmemiş.

### 3) Backlog "7" rakamının olası kaynağı

İki bağımsız ajan da (ve doğrulama ajanı üçüncü kez) aynı 2 "sınırda kalan" adaya ulaştı — ikisi de `role="dialog"` benzeri işaretler taşıyor ama backdrop/body-scroll-lock yok, dolayısıyla WCAG 2.4.3 anlamında gerçek modal değiller:

| Sınırda aday | Dosya:satır | Neden modal sayılmadı |
|---|---|---|
| Alarm Paneli / "Takip Listem" (`alarmPanel`) | `index.html:1649-1657` | `position:fixed;bottom:24px;right:24px` — floating popover, backdrop yok, body-lock yok, `role="dialog"` bile yok, arka plan tam etkileşilebilir |
| Sticky Subscription Toast (`subToast`) | `index.html:2547-2548` | `role="dialog"` **var** (SSH ile doğrulandı) ama backdrop yok, sabit-köşe toast (satır ~1700) — yanıltıcı ARIA etiketi, davranışsal olarak dialog değil |

5 gerçek + bu 2 sınırda aday = 7. Backlog muhtemelen bunları gevşek bir class/role taramasıyla dahil etmiş. Kesin köken doğrulanamaz (orijinal backlog yazarının taraması elimizde yok) ama veriyle tutarlı tek açıklama bu.

### 4) Elenen diğer adaylar (kanıtla, üç ajan da aynı sonuca vardı)

- `adv-panel`/`.bp-filter-panel` (`index.html:1221,2343`) — sayfa akışı içinde genişleyen panel, backdrop yok
- Nav dropdown menüsü (`toggleNavDd`, `index.html:5248` vb.) — disclosure pattern, backdrop yok
- Arama otomatik-tamamlama (`showSearchAc`) — input-bağlı öneri kutusu, backdrop yok
- Tooltip'ler (`sigTip`, `.ind-help`) — hover/tap tooltip, engelleyici değil
- `gnmPanelMakro/Hisse`, `panelIsiHaritasi/Karsilastir` — `role="tabpanel"`, ARIA Tabs pattern (ok tuşu navigasyonu), Tab-trap pattern'i değil
- Loading overlay'ler (`cmpLoadingOverlay`, `.loading-overlay`) — kullanıcı etkileşimiyle açılmıyor, kapatma butonu yok
- `.search-overlay` (bp- önekisiz eski CSS sınıfı, `ozet.html:217`, `sektor_harita.html:128`, `hisse.html:1159-1160`) — **ölü CSS**, eşleşen HTML elementi yok; gerçek arama artık `bp-search.js`'in enjekte ettiği `.bp-search-modal` üzerinden çalışıyor
- `attic/backtest.html` içindeki `closeCompareModal()` — `templates/` dışında, `app.py:11480` ile kalıcı 301 yönlendirilen arşiv/ölü kod, canlı yüzey değil

### 5) Gerçek ve tek kapsam boşluğu: `static/bp-search.js`

Site içi arama (Cmd/Ctrl+K komut paleti) **21 şablonda** yüklü (`grep -rl "bp-search.js" templates/*.html | wc -l` = 21 — iki ajan arasındaki tek gerçek sayı çelişkisiydi, SSH ile "21" doğru sonuç olarak doğrulandı, "26" yanlıştı). `openSearch()`/`closeSearch()` fonksiyonları `bpTrapFocus` çağırmıyor → Tab tuşu overlay dışına (header/nav/arka plan linkleri) kaçabiliyor; `aria-modal="true"` de eksik. Site genelinde tekrarlanan tek paylaşımlı bileşen olduğu için etki alanı en geniş gerçek boşluk bu.

**Önerilen düzeltme (kod değişikliği, uygulanmadı):** `openSearch()` içinde `bpTrapFocus(document.getElementById('bpSearchOverlay').querySelector('.bp-search-modal'), closeSearch)` çağrısı eklenip `release()` saklanmalı ve `closeSearch()` içinde çağrılmalı; markup'a `aria-modal="true"` eklenmeli. Bu, 4 bileşende zaten kanıtlanmış aynı utility'nin 5. çağrı noktasına eklenmesi — yeni tasarım kararı gerektirmiyor (görsel/marka etkisi sıfır, yalnız klavye davranışı), ama site-genelinde en yaygın dinamik bileşen olduğu için (21 şablon, Cmd+K kısayolu) düşük-riskli-ama-sıfır-risk-değil sınıfında — CPO/Ozan onayı sonrası uygulanmalı, bu turda kod değişmedi.

## Kod değişmedi

Bu rapor salt sınıflandırma — hiçbir template/CSS/JS dosyası değiştirilmedi. Migrasyon/gap-kapatma kararı S1/S7/T3.4/T5.2/T5.4/T8-serisi/T1.5-serisi/kart-zemin ile aynı karar kuyruğuna eklenmek üzere CPO/Ozan'a bırakıldı — düşük-risk sınıfında hızlı-onay adayı olarak işaretlendi (anasayfa-yük'ün 2-endpoint lazy-load önerisiyle aynı sınıf).
