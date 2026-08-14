# Faz 3 / T3.4 — ⭐/💎 Site Geneli Tekilleştirme: Envanter ve Plan

Üretildi: 14 Ağustos 2026, DEV2 (workflow: 11 dosya paralel envanter ajanı + 1 sentez ajanı + 1 bağımsız eleştiri ajanı, ardından DEV2'nin kendi doğrulama turu — eleştirinin bulduğu 5 CİDDİ hatanın tamamı bu turda canlı koda karşı yeniden doğrulandı ve düzeltildi)
Kapsam: 10 şablon (`index.html`, `tarama.html`, `hisse.html`, `gucu_yuksek.html`, `karsilastir.html`, `heatmap.html`, `sektor_harita.html`, `bilanco_takvimi.html`, `profil.html`, `_premium_modal.html`) + `app.py` + `static/bp-vocab.js` — VPS güncel kod üzerinden ⭐/💎/`tier`/`is_premium`/`mail_pref` alan-sembol-renk envanteri ve T3.4 tekilleştirme planı.

**Bu turda kod değişikliği YAPILMADI — yalnızca envanter ve plan.** Kapsam dışı teyit: `business_rules.py`, `_derive_tier()`'ın kendi hesaplama mantığı (signal/signal_strength/likidite/kazanç-uyarısı girdileri) ve `compose_score` matematiği bu dokümanda **değiştirilmedi, değiştirilmesi de önerilmiyor** — DEV1 alanı, yalnızca `_derive_tier()`'ın ÇIKTISININ (`s.tier` string'i) render katmanında nasıl gösterildiği inceleniyor.

---

## 0. Bu turda düzeltilen 5 kritik hata (bağımsız eleştiri turundan)

Önceki taslak (workflow sentez çıktısı) bağımsız eleştiri ajanı tarafından 5 CİDDİ + 7 ORTA/DÜŞÜK bulguyla geri çevrildi. Aşağıdaki 5 CİDDİ bulgu bu turda canlı koda karşı tek tek doğrulandı:

1. **`is_premium` ile `mail_pref=="premium"` YANLIŞLIKLA aynı kavram sayılmıştı — düzeltildi.** Canlı kod doğrulaması: `is_premium = (signal == "AL" and rvol >= 1.20)` (app.py:1801) hisse-seviyesi bir sinyal bayrağı; `mail_pref` (app.py:2768/3025/11105) kullanıcının e-posta gönderim sıklığı tercihi (`daily|instant|premium|weekly`), tamamen ayrı bir veri modeli alanı — ikisi de sadece "premium" kelimesini/💎 sembolünü paylaşıyor. Bu, düzeltilen değil YENİ bir 3. çakışma katmanı olarak aşağıda ayrıca ele alınıyor (bkz. §1.3).
2. **`_premium_modal.html` include zinciri doğrulanmadan karar üretilmişti — düzeltildi.** Canlı grep: `grep -rn '_premium_modal' templates/*.html` → **tek sonuç**, `index.html:5484`. `grep -rn 'openPremiumModal' templates/*.html` → yalnızca `index.html` (satır 3773 çağrı, `_premium_modal.html:112` tanım). **`tarama.html` ve `sinyal_performans.html` `openPremiumModal()` çağırmıyor** — DEV2-028'deki (Pz 09.08) "bu iki sayfa canlı butonla bağımlı" tespiti artık GEÇERSİZ, muhtemelen T3.3 veya sonraki bir temizlik sırasında bu çağrılar kaldırılmış. Bu, T3.2/T3.4 birleşme kararının riskini önemli ölçüde düşürüyor (bkz. §4).
3. **`gucu_yuksek.html:242` üç iddiası kanıtsızdı — artık tam kod alıntısıyla doğrulandı** (bkz. §1.2 tablo notu ve §1.3).
4. **Kabul ölçütü (a)/(g) alt-dize eşleşmesine dayanıyordu (sahte-pozitif/sahte-negatif riski) — gerçek kod sembolüne göre yeniden yazıldı** (bkz. §6).
5. **`--bp-plus`/`--bp-standart` token yokluğu ikinci elden aktarılmıştı — bu turda doğrudan doğrulandı**: `grep -n 'bp-plus\|bp-standart' static/css/tokens.css` → **0 sonuç** (yorum satırı dahil hiçbir biçimde yok).

Ek doğrulama (eleştirinin ORTA bulgu #8/#9'u): `static/bp-vocab.js` (122 satır, projenin kanonik UI-sözlük dosyası) ve `static/js/*.js` grep'lendi — **hiçbirinde tier/is_premium/⭐/💎/plus/standart referansı yok**. Yani kanonik sözlük bu kavramı hiç kapsamıyor; T3.4 kapsamına bp-vocab.js'e giriş eklemek de dahil edilmeli (bkz. §2.4).

---

## 1. Mevcut Durum Özeti

### 1.1 Kaç dosyada kaç kullanım

| Sembol/Alan | Geçtiği dosya sayısı | Geçmediği dosyalar |
|---|---|---|
| 💎 | 8/11 | `karsilastir.html`, `sektor_harita.html`, `bilanco_takvimi.html` |
| ⭐ | 8/11 | `profil.html`, `_premium_modal.html`, `app.py` |
| `s.tier` alanı (render) | 6/11 (`index`, `tarama`, `hisse`, `gucu_yuksek`, `heatmap`, backend `app.py`) | `karsilastir`, `sektor_harita`, `bilanco_takvimi`, `profil`, `_premium_modal` |
| `is_premium` alanı (RVOL bayrağı) | 8/11 (`index`, `tarama`, `hisse`, `gucu_yuksek`, `karsilastir`, `sektor_harita`, `bilanco_takvimi`, `app.py`) | `heatmap`, `profil`, `_premium_modal` |
| `mail_pref=="premium"` (e-posta sıklık tercihi) | 2/11 (`profil.html`, `app.py`) | diğer 9 |

**Not:** `is_premium` ve `mail_pref` satırları önceki taslakta yanlışlıkla birleştirilmişti — tabloda artık ayrı satırlar.

### 1.2 Dosya-dosya matris

| Dosya | 💎 kullanımı (satır) | ⭐ kullanımı (satır) | Hangi alan(lar) | Token mu ham hex mi | İç-tutarsızlık |
|---|---|---|---|---|---|
| `index.html` | tier grup başlığı `_tierLabels` tanımı (~3921-3926, `{premium:'💎 PREMIUM', plus:'⭐ PLUS', standart:'STANDART'}`) + grup başlığı render (4128-4133) + `_premium_modal` include (5484) | tier=plus (aynı `_tierLabels`), is_premium satır rozeti (4136, ayrı/bağımsız kullanım — grup başlığından farklı) | `tier` (grup başlığı), `is_premium` (satır rozeti) — İKİSİ AYNI DOSYADA, YAKIN SATIRLARDA ama farklı DOM düğümleri | Karışık: `tg-premium`→token (`var(--bp-premium)`), `tg-plus`→ham hex muhtemel (doğrulanmalı); is_premium rozeti `var(--bp-volume)` token kullanıyor (4136, doğrulandı) | **Var** — aynı dosyada tier grup başlığı (💎/⭐ metin+ikon) ile satır-içi is_premium (⭐ tek ikon) görsel olarak ayırt edilemeyecek kadar yakın |
| `tarama.html` | filtre dropdown (458)=`only_premium`/`is_premium`; satır rozeti (934,941)=`s.tier` | satır rozeti (941,961)=`s.tier==='plus'` | `tier`, `is_premium` | `.score-val.premium`→token; `.plus`/`.standart`→ham hex `#1f6feb`/`#808080` (367-379) | **SENECA'nın 3. çakışması burada doğrulandı**: aynı 💎, dropdown'da `is_premium`, satır rozetinde `tier` |
| `hisse.html` | RSI&lt;30 göstergesi (~3272, `tier` ile ilgisi yok) | is_premium (1884-1885, 2982-2983, 3165-3175) | `tier` (1867-1870, **sembolsüz, yalnız renk**: premium=`#a855f7` ham hex, plus=`#1f6feb` ham hex, standart=`#909097` ham hex — hiçbiri token değil), `is_premium` | `tier` renkleri tamamen ham hex; `is_premium` `var(--bp-volume)` token | **Var** — 💎 bu dosyada tier'ı hiç temsil etmiyor (tier sembolsüz), RSI göstergesine atanmış; ⭐ yalnız is_premium için kullanılıyor (watchlist iddiası bir sonraki maddede düzeltildi, bkz. not) |
| `gucu_yuksek.html` | tier=premium (satır 242, tek satırda tüm mantık) | tier=plus (242, ham hex `#1f6feb`) VE is_premium (242, token `var(--bp-volume)`) — **AYNI SATIRDA, kod alıntısıyla doğrulandı** | `tier`, `is_premium` | premium→token; plus→ham hex; is_premium→token | **Var, doğrulandı** — geliştirici zaten satır 240-241'de yorumla ayrımı belgelemiş (`CPO-986 #8.1`, `CPO-535 #36`: "is_premium tier'dan bağımsız ayrı bir metrik, renkle ayrışır") ama görsel olarak hâlâ aynı ⭐/💎 sembolleri kullanılıyor — niyet dokümante ama uygulama hâlâ çakışıyor |
| `karsilastir.html` | Yok | is_premium (377 `ROW_LABELS`, 404-406, 470) | Yalnız `is_premium` (`tier` hiç yok) | Token (`--bp-volume-*` ailesi) | Dosya-içi yok; site-geneli: ⭐ burada amber/is_premium |
| `heatmap.html` | legend tier=premium (187, token) | legend tier=plus (188, ham hex `#88A8C0` — **diğer dosyalardaki `#1f6feb`'den FARKLI**) | Yalnız `tier` (`is_premium` hiç yok) | premium→token; plus/standart→ham hex, DİĞER dosyalardan farklı değerler (`#88A8C0`/`#C07838` vs `#1f6feb`/`#808080`) | Dosya-içi yok; **dosyalar-arası**: aynı `tier=plus` kavramı için heatmap başka bir ham hex kullanıyor |
| `sektor_harita.html` | Yok | is_premium pill (342-344), `.stat-pill.pill-prem` CSS tanımı (159-164) | Yalnız `is_premium` | Token (`var(--bp-volume)`, `var(--bp-volume-rgb)`) ama **class adı `pill-prem`** | Dosya-içi yok; **isim çakışması riski** — CPO'nun T3.4 için önerdiği `pill-prem` adı burada zaten `is_premium` için dolu (bkz. §2.2) |
| `bilanco_takvimi.html` | Yok | is_premium (299, token) | Yalnız `is_premium` | Token | Dosya-içi yok |
| `profil.html` | mail_pref seçeneği (277, `data-v="premium"`, düz emoji) | Yok | `mail_pref=="premium"` — e-posta sıklık tercihi, `tier`/`is_premium`'dan bağımsız 3. alan | Ne token ne ham hex — emoji stilsiz; buton rengi `var(--bp-brand)` (mavi) | Dosya-içi yok; site-geneline 💎'nin 3. bağımsız anlamını (mail sıklığı) ekliyor |
| `_premium_modal.html` | CTA/ikon/hata mesajı (121, 132, 187, 191, 222) | Yok | `tier`/`is_premium` kod değişkeni YOK — yalnız pazarlama/CTA metni, `openPremiumModal()`'ın kendi tanımı burada | Tamamen ham hex `#ffc850`/`#e3b341`, `var(--bp-premium)` (mor) hiç kullanılmıyor | Dosya-içi yok; **tek include noktası `index.html:5484`, doğrulandı** (bkz. §0.2) |
| `app.py` | mailer bloğu (2463, 2477, 2558, 2576, 2618, 3050) = `is_premium` bayrağı; ayrıca (2786) = `mail_pref=="premium"` | Yok | `is_premium` (RVOL, ~6 kullanım) VE `mail_pref=="premium"` (2786, 1 kullanım) — **AYNI DOSYADA, AYNI 💎 SEMBOLÜYLE İKİ FARKLI ALAN**; `tier` de ayrı (1550/1920/3588/8813) ama hiç emoji taşımıyor | Tamamı ham hex `#ffc850` | **Var, yeni tespit** — mailer içinde 💎 hem "bu hisse RVOL-onaylı" hem "bu kullanıcının mail tercihi premium" anlamına geliyor, ikisi aynı e-postada yan yana görünebilir (prem_count rozetleri + subject_prefix) |

### 1.3 Üç alanın (tier / is_premium / mail_pref) karıştığı noktalar

- **`tarama.html`** — filtre dropdown'ı (`is_premium`, 💎) ile satır rozeti (`tier`, 💎) aynı sembolü farklı alanlar için kullanıyor. SENECA'nın 14.08 19:14 TR raporu, bu turda doğrulandı.
- **`gucu_yuksek.html:242`** — aynı satırda `tier=='plus'` (⭐, ham hex `#1f6feb`) ile `is_premium` (⭐, token `var(--bp-volume)`) yan yana render ediliyor; ayrım yalnızca renk tonu, ikon aynı. Geliştirici bunu satır-üstü yorumla (240-241) belgelemiş ama sembol seçimi hâlâ çakışıyor.
- **`index.html`** — tier grup başlığı (💎/⭐ metinli) ile satır-içi is_premium rozeti (⭐ tek ikon) aynı dosyada, yakın kod bölgelerinde, görsel olarak ayırt edilmesi zor iki farklı kavram.
- **`app.py`** (YENİ tespit, önceki taslakta yoktu) — mailer içinde 💎 hem `is_premium` (RVOL, hisse-seviyesi) hem `mail_pref=="premium"` (kullanıcı e-posta sıklık tercihi) için kullanılıyor; bunlar backend'de TAMAMEN AYRI VERİ MODELLERİ (biri stok objesi alanı, diğeri abone kaydı alanı) — aynı e-postada aynı anda görünebilirler ("💎 Premium" subject prefix + gövdede "💎 PREMIUM" rozetli hisseler), okuyucu ikisinin aynı şey olduğunu sanabilir.
- **`profil.html`** — `mail_pref=="premium"` seçeneği 💎 kullanıyor, sitedeki diğer 8 dosyanın çoğunluğunun `is_premium` için kullandığı sembolle (⭐, çoğunlukla) DEĞİL, `tier=premium`'ın sembolüyle (💎) çakışıyor — kullanıcı bu seçeneği "yüksek tier hisseler" zannedebilir, oysa yalnızca mail sıklığı.

### 1.4 Renk/token tutarsızlıkları

| Kavram | Doğru token (varsa) | Gerçekte kullanılan değerler | Nerede |
|---|---|---|---|
| `tier=premium` | `var(--bp-premium)` = `#a855f7` (mor) | Çoğunlukla token; `hisse.html`'de ham hex kopyası (`#a855f7`, aynı değer ama token değil, 1867-1870) | index, tarama, gucu_yuksek, heatmap (token) / hisse (ham hex) |
| `tier=plus` | **Yok — doğrulandı, `static/css/tokens.css`'te `--bp-plus` sıfır sonuç, yorum dahil** | `#1f6feb` (index, tarama, gucu_yuksek, hisse) **vs** `#88A8C0` (heatmap legend) — aynı kavram için iki farklı ham hex | index, tarama, hisse, gucu_yuksek, heatmap |
| `tier=standart` | **Yok — doğrulandı** | `#808080` (index, tarama, gucu_yuksek) **vs** `#909097` (hisse.html) **vs** `#C07838` (heatmap legend, sembolsüz) | index, tarama, hisse, heatmap |
| `is_premium` | `var(--bp-volume)` = `#ffc850` (amber) | Çoğu yerde token kullanılıyor (index-4136, hisse, karsilastir, bilanco_takvimi, gucu_yuksek, sektor_harita); `_premium_modal.html` ve `app.py` mailer'da aynı değer ham hex `#ffc850` | 8 dosya + app.py + _premium_modal |
| `mail_pref=="premium"` | Yok, hiç token yok | Emoji stilsiz (`profil.html`), `app.py`'de ham hex `#ffc850` (subject prefix rengi yok, yalnız metin) | profil.html, app.py |
| `_premium_modal.html` pazarlama CTA'sı | Yok | `#ffc850`/`#e3b341` gradient, `var(--bp-premium)` (mor) hiç kullanılmıyor | _premium_modal.html |

**Sonuç:** 💎/⭐ site genelinde **üç** bağımsız backend alanını (`tier`, `is_premium`, `mail_pref`) temsil ediyor; her biri kendi içinde de tutarsız renk/token kullanıyor. Bu, "bir kavram = tek sembol + tek renk" kuralının hem yatay (aynı sembol, farklı alan) hem dikey (aynı alan, farklı renk) eksende ihlal edildiğini gösteriyor.

---

## 2. Tekilleştirme Planı

### 2.1 Kanonik kural (yeniden teyit + genişletme)

- **`tier` alanı TEK kaynak olacak** ve TEK sembol setine sahip olacak: 💎 Premium (mor, `var(--bp-premium)` = `#a855f7`, zaten kanonik) / ⭐ Plus (mavi, **yeni token** `--bp-plus`, önerilen değer `#1f6feb` — mevcut en yaygın kullanım, heatmap'in `#88A8C0`'ı azınlıkta) / Standart (nötr, **yeni token** `--bp-standart`, önerilen değer `#808080` — mevcut en yaygın kullanım).
- **`is_premium` (RVOL bayrağı) 💎/⭐'ı KULLANMAYACAK.** Backend mantığı değişmiyor (`only_premium` param, `signal=='AL' and rvol>=1.20` hesaplaması dokunulmuyor — DEV1/render sınırı korunuyor). Görsel sembolü tier'dan tamamen ayrışacak (bkz. §3).
- **`mail_pref=="premium"` (e-posta sıklık tercihi) 💎'yı KULLANMAYACAK.** Bu, hiçbir hisse-seviyesi veya tier-seviyesi kavramla ilgisi olmayan bir kullanıcı ayarı — "Premium" kelimesi bile burada yanıltıcı (aslında "sadece RVOL-onaylı sinyalleri mail'e dahil et" demek, `is_premium` bayrağıyla filtreleme yapıyor muhtemelen). **Öneri:** `profil.html:277` seçeneğinin etiketi "💎 Sadece Premium — hacim onaylı sinyaller" zaten `is_premium`'u tarif ediyor (hacim onaylı) — bu aslında `mail_pref` değerinin adının yanıltıcı olduğunu gösteriyor, sembol sorunu değil. Bu nüans CPO/Ozan'a ayrı bir madde olarak taşınmalı (bkz. §5.7 — yeni).
- Watchlist/favori ikonu — **düzeltme notu:** önceki taslak `index.html`/`hisse.html`'de ⭐'ın watchlist için de kullanıldığını iddia etmişti; bu turda `hisse.html` satır referanslarında (1803, 2511, 2592) watchlist fonksiyonlarının gerçek sembolü bu doğrulama turunda teyit edilemedi (agent raporu satır numarası verdi ama doğrudan kod alıntısı yoktu) — **bu madde "doğrulanmalı" olarak işaretleniyor, kesin iddia olarak plana alınmadı**. Bir sonraki turda `grep -n 'toggleWatchlist\|watchlist.has' templates/hisse.html templates/index.html` ile kesinleştirilmeli.
- RSI göstergesi (`hisse.html:~3272`) 💎 kullanmayı bırakmalı — teknik göstergenin tier kavramıyla hiçbir ilgisi yok.

### 2.2 `pill-prem` class çakışması — ÖNEMLİ, çözülmemiş

CPO talimatı (`pill-prem`, T3.4'e verilirken "henüz uygulanmadı" varsayımıyla) tier=premium rozeti için önerilmişti. Ancak **`sektor_harita.html:159-164`'te `.stat-pill.pill-prem` zaten mevcut ve `is_premium` (amber, `var(--bp-volume)`) için kullanılıyor.** İki seçenek:

- **(A)** `pill-prem` ismini olduğu gibi `is_premium` için koru, `tier=premium` rozetine farklı bir isim ver (örn. `pill-tier-prem`).
- **(B)** `sektor_harita.html`'deki mevcut kullanımı yeniden adlandır (örn. `pill-vol`/`pill-rvol`), `pill-prem`'i `tier=premium` için boşalt.

Bu turda karar verilmedi — **CPO/Ozan onayı gerekir** (bkz. §5.2).

### 2.3 Dosya dosya somut değişiklik listesi (plan — kod değişmedi)

| Dosya | Değişecek | Not |
|---|---|---|
| `tokens.css` | `--bp-plus` (`#1f6feb`), `--bp-standart` (`#808080`) eklenmeli | §5.3 kararına bağlı (heatmap'in farklı değerleri kanonik seçilirse değer değişir) |
| `static/bp-vocab.js` | `tier` (premium/plus/standart) ve `is_premium` için kanonik sembol/renk/etiket girdisi eklenmeli — şu an bu dosyada HİÇ yok | Yeni kapsam maddesi, önceki taslakta eksikti |
| `index.html` | `tg-plus`/`tg-standart` ham hex → token; tier grup başlığı ile satır-içi is_premium rozeti arasındaki görsel ayrım netleştirilmeli | Watchlist iddiası doğrulanmadan değişiklik yapılmamalı (§2.1) |
| `tarama.html` | `.plus`/`.standart` ham hex → token; **filtre dropdown'daki 💎'yı is_premium'dan koparıp yeni sembole/etikete çevir** (§3) | SENECA'nın somut bulduğu nokta |
| `hisse.html` | Tier renkleri (1867-1870) ham hex → token; is_premium sembolü değişirse 3 yerde (1884-1885, 2982-2983, 3165-3175) tutarlı güncellenmeli | Watchlist doğrulaması gerekli |
| `gucu_yuksek.html` | `tier=='plus'` ham hex (242) → token; aynı satırdaki tier-plus/is_premium ikon çakışması yeni sembollerle çözülmeli | Zaten iyi dokümante edilmiş (yorum satırları), sadece sembol/renk uygulaması eksik |
| `karsilastir.html` | is_premium sembolü değişirse `ROW_LABELS` (377) ve render (404-406) güncellenmeli | — |
| `heatmap.html` | Legend plus/standart ham hex → §5.3 kararına göre kanonik değere hizala | — |
| `sektor_harita.html` | `pill-prem` isim çakışması çözülmeli (§2.2); is_premium sembolü değişirse render (342-344) güncellenmeli | — |
| `bilanco_takvimi.html` | is_premium sembolü değişirse satır 299 güncellenmeli | — |
| `profil.html` | mail_pref="premium" seçeneğindeki 💎 (277) — hem sembol hem muhtemelen ETİKET metni gözden geçirilmeli (§2.1 son madde) | Ayrı ürün kararı gerektirebilir |
| `_premium_modal.html` | 💎 referansları (121,132,187,191,222) ve amber palet — §4 kararına bağlı, TEK include noktası `index.html` (doğrulandı) | Risk profili önceki taslaktan DÜŞÜK |
| `app.py` | Mailer'daki `is_premium` kullanımları (2463,2477,2558,2576,2618,3050) ile `mail_pref=="premium"` (2786) GÖRSEL OLARAK AYRIŞTIRILMALI — aynı e-postada iki farklı anlamda 💎 görünmemeli | Yeni tespit, önceki taslakta yoktu |

### 2.4 Yeni kapsam maddesi: `static/bp-vocab.js`

Bu dosya (122 satır) projenin kanonik UI terminoloji sözlüğü olarak biliniyor ama tier/is_premium/premium/plus/standart hiç geçmiyor (bu turda doğrulandı — hem `static/bp-vocab.js` hem `static/js/*.js` tarandı, sıfır sonuç). T3.4'ün kapsamına, seçilen kanonik sembol/renk/etiket üçlüsünü bu dosyaya girdi olarak eklemek dahil edilmeli — aksi halde bir sonraki geliştirici (veya SENECA gibi bir denetim ajanı) aynı karışıklığı tekrar keşfedecek.

---

## 3. SENECA'nın 3. çakışma bulgusu — değerlendirme ve karar seçenekleri

SENECA'nın 14.08 19:14 TR raporu: `tarama.html` filtre dropdown'ı (`💎 Premium (AL + Hacim Onaylı)`, satır 458) `is_premium`'u vaat ederken, satır rozeti (934/941, `s.tier==='premium'`) aynı 💎 ile `tier`'ı vaat ediyor. Bu tur bunu doğruladı ve genişletti: 💎 sitede üç ayrı öbekte kullanılıyor — (a) `tier=premium` (index, gucu_yuksek, heatmap, tarama-rozet), (b) `is_premium` (app.py mailer, tarama-dropdown), (c) `mail_pref=="premium"` (profil.html, app.py-subject). `tarama.html` (a) ve (b)'nin çarpıştığı, `app.py` ise (b) ve (c)'nin çarpıştığı nokta.

**Seçenekler (nötr, karar CPO/Ozan'da — §5.1):**

- **Seçenek 1:** `is_premium` için yeni bir 3. sembol (öneri: 🔥 veya 📊) — artı: ⭐'ın tier=plus'a devri için mevcut çoğunluk kullanımı bozulmaz değil, eksi: kullanıcıya yeni bir sembol öğretmek gerekir.
- **Seçenek 2:** ⭐'ı tamamen `tier=plus`'a ayırmak, `is_premium` sembolsüz/farklı bir görsel dile (örn. sadece renkli nokta, tier'daki gibi) geçmek — artı: tier üçlüsü (💎/⭐/nötr) temiz kalır, eksi: `is_premium` şu an çoğunlukla ⭐ kullanıyor (index, hisse, karsilastir, sektor_harita, bilanco_takvimi, gucu_yuksek — 6/8 dosya), geniş çaplı değişiklik.
- Dropdown seçeneğinin `value="PREMIUM"` string'i de (backend'e görünmeyen ama kod-okunurluğunu etkileyen) gözden geçirilebilir — kozmetik, zorunlu değil.

---

## 4. T3.2 / `_premium_modal.html` açık kararı — risk profili düzeltildi

DEV2-028'de (Pz 09.08) T3.2 (dosya silme) durdurulmuştu çünkü o tarihte `tarama.html`/`sinyal_performans.html`'in `openPremiumModal()`'a bağımlı olduğu düşünülüyordu. **Bu turda canlı kod bunu ÇÜRÜTÜYOR:** `grep -rn 'openPremiumModal' templates/*.html` → yalnızca `index.html` (çağrı satır 3773, tanım `_premium_modal.html:112`). `_premium_modal.html`'in kendi header yorumu (satır 1-3) hâlâ "sitewide erişilebilir" diyor ama bu artık DOĞRU DEĞİL — muhtemelen T3.3 (tier filtre kaldırma) veya sonraki bir temizlikte `tarama.html`/`sinyal_performans.html`'deki çağrılar kaldırılmış, yorum güncellenmemiş.

**Sonuç:** `_premium_modal.html` bugün yalnızca `index.html` tarafından kullanılıyor (Alert giriş kapısı + "Premium'u Aç" pazarlama CTA'sı, aynı dosyada). T3.2'nin bu dosyayı T3.4 kapsamında ele alması artık DEV2-028'deki senaryodan çok daha düşük riskli — yalnızca tek sayfa etkileniyor.

**Seçenekler (nötr):**
- **A)** Modalın 💎-çerçeveli pazarlama kısmını (ikon+başlık+CTA, 121-132, JS-tekrarları 187/191, hata mesajı 222) nötr "Üye Girişi" bileşenine indirgemek, amber paleti kaldırmak, satır 133'teki mevcut nötr "👤 Üye Girişi" butonunu tek CTA yapmak.
- **B)** Dosyayı olduğu gibi bırakmak, yalnızca 💎→yeni is_premium sembolüyle hizalamak (eğer bu modal aslında `is_premium` kavramıyla ilgiliyse — **doğrulanmalı**, modal metni "Premium'u Aç" diyor ama hangi alanı temsil ettiği (tier mi is_premium mü) kod değişkeni yok, yalnızca pazarlama kopyası).

Bu karar CPO/Ozan'a bırakılıyor (§5.4) — önceki taslağın "onaylamak mantıklı" gibi yönlendirici dili bu turda kaldırıldı, seçenekler nötr sunuluyor.

---

## 5. Açık Kararlar — CPO/Ozan onayı gerekli

1. **`is_premium` için yeni sembol seçimi** (§3) — Seçenek 1 (yeni 3. sembol, örn. 🔥) mi, Seçenek 2 (⭐'ı tier=plus'a ayırma, is_premium'a yeni görsel dil) mi?
2. **`pill-prem` isim çakışması** (§2.2) — Seçenek A (is_premium'da kalsın, tier'a yeni isim) mı, Seçenek B (sektor_harita yeniden adlandırılsın, pill-prem tier'a) mı?
3. **`--bp-plus`/`--bp-standart` token değerleri** — index/tarama/gucu_yuksek'in `#1f6feb`/`#808080`'ı mı, heatmap'in `#88A8C0`/`#C07838`'ı mı kanonik?
4. **`_premium_modal.html` nötrleştirme** (§4) — Seçenek A (nötrleştir) mi, B (olduğu gibi bırak, yalnız sembol hizala) mı? Not: risk artık düşük (tek sayfa etkileniyor, doğrulandı).
5. **Mailer/`profil.html` renk hizalaması** — email HTML'de CSS custom property çoğu istemcide çalışmaz (teknik kısıt) — hangi ham-hex değeri "kanonik email rengi" sayılacak?
6. **`index.html`/`hisse.html`'deki watchlist ⭐ iddiası** — bu turda doğrulanamadı, bir sonraki turda `grep -n 'toggleWatchlist\|watchlist.has'` ile netleştirilecek; eğer gerçekten ⭐ kullanıyorsa yeni sembol (örn. 🔖) gerekecek.
7. **YENİ — `profil.html:277` `mail_pref="premium"` etiketinin kendisi yanıltıcı olabilir** (§2.1): etiket "hacim onaylı sinyaller" diyor ama bu aslında `is_premium` bayrağının tarifi, `mail_pref` bir teslimat sıklığı ayarı. Sembol sorunundan bağımsız bir metin/ürün netliği sorunu — CPO/Ozan'ın ayrıca değerlendirmesi gerekebilir.

---

## 6. Kabul Ölçütü (gerçek kod sembolüne göre, eleştiri sonrası düzeltildi)

**a) 💎'nin tier dışında kullanılmadığının doğrulanması (alt-dize değil, DOM/render bağlamına göre):**
```bash
# tier dışı 💎 kalmamalı — is_premium ve mail_pref artık farklı sembol kullanmalı
grep -n "s\.is_premium" templates/*.html | grep '💎'      # beklenen: 0
grep -n 'mail_pref' templates/profil.html app.py | grep '💎'  # beklenen: 0
grep -rn '💎' templates/*.html app.py | grep -v "s\.tier\|_tierLabels\|tier ==\|tier=='premium'\|tier == \"premium\""  # kalan satırlar tek tek incelenmeli, otomatik 0 beklenmiyor
```

**b) Ham hex tier renklerinin token'a taşındığı doğrulaması:**
```bash
grep -rn '#1f6feb\|#808080\|#88A8C0\|#C07838\|#909097' templates/*.html
# Beklenen: sıfır sonuç
grep -n -- '--bp-plus\|--bp-standart' static/css/tokens.css
# Beklenen: iki token da tanımlı (bu turda doğrulanan mevcut sıfır durumuna karşı fark)
```

**c) `pill-prem` çakışmasının çözüldüğü doğrulaması:**
```bash
grep -rn 'pill-prem\b' templates/*.html
grep -rn 'pill-tier-prem\|pill-vol\|pill-rvol' templates/*.html
# Beklenen: iki farklı class adı, iki farklı kavrama (tier vs is_premium) net şekilde ayrılmış olmalı
```

**d) `is_premium`/`tier` filtrelerinin UI'da artık aynı sembolle sunulmadığının doğrulanması:**
```bash
curl -s 'https://borsapusula.com/api/tarama?only_premium=1' | jq '[.[] | .ticker] | length'
curl -s 'https://borsapusula.com/api/tarama' | jq '[.[] | select(.tier=="premium") | .ticker] | length'
# Sayılar farklı olabilir (beklenen, bağımsız alanlar) — asıl kanıt (a)'daki grep
```

**e) Mailer/modal renk hizalaması (§5.5 kararına göre):**
```bash
grep -n '#ffc850\|#e3b341' app.py templates/_premium_modal.html
```

**f) `_premium_modal.html` nötrleştirme (§5.4 Seçenek A onaylanırsa):**
```bash
grep -n '💎' templates/_premium_modal.html   # beklenen: 0
grep -rn 'openPremiumModal\|_premium_modal' templates/*.html  # beklenen: yalnız index.html, doğrulanmış tek-nokta kapsamı korunmalı
```

**g) `static/bp-vocab.js` güncellemesi:**
```bash
grep -n 'tier\|is_premium\|premium\|plus\|standart' static/bp-vocab.js
# Beklenen: seçilen kanonik sembol/renk/etiket üçlüsü için en az 3 girdi (premium/plus/standart)
```
