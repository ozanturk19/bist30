# FAZ1 (Sözlük Evi + Tasarım Token Sistemi) — kalan 6 kalem sınıflandırması

17.08.2026, DEV2 — Workflow ile 6 paralel bağımsız sınıflandırma ajanı + 6 bağımsız kör doğrulama ajanı (S1/S7/T3.4/T-serisi ile aynı desen). KOD DEĞİŞMEDİ, yalnız salt-okur envanter. P0 (CPO-DEV2-007, safe-area) gate'i FAZ2/FAZ5'i kapalı tuttuğu için FAZ1'e (bloklu değil, T0.1'den sonra başlıyor) bakıldı.

## T1.1 — business_rules.py sözlük evi — DURUM: KISMEN

07.08.2026 (`90f75f5`, CPO-1321) ile SIGNAL_LABELS/ENTRY_QUALITY_LABELS/SIGNAL_AGE_LABELS/VOLUME_LABELS eklendi (14 anahtar, hepsi dolu) — kabul ölçütünün "4 sözlük dolu" şartı sağlanıyor. Ama "derive_adx_label ile aynı desen: tek kaynak" şartı sağlanmıyor:
- `app.py:746` hâlâ kendi kopya `_SIGNAL_LABELS` ham-string sözlüğünü kullanıyor, `business_rules.SIGNAL_LABELS`'ı hiç import etmiyor.
- `derive_signal_age_label`/`derive_volume_label` fonksiyonları `business_rules.py` dışında hiçbir yerde çağrılmıyor (0 tüketici).
- Kontrast: `derive_adx_label` app.py'de gerçekten import edilip 7 kez çağrılıyor.

Bağımsız doğrulama: birebir mutabık, tek metodolojik not — "124 kez" rakamı `grep -c` (satır sayımı), `grep -o` ile ham oluşum 167.

Kanıt: `git log -S'SIGNAL_LABELS = {' -- business_rules.py` → `90f75f5`; `grep -n 'from business_rules import' app.py` → SIGNAL_LABELS ailesi yok.

## T1.2 — "Zayıf Trend" → "Trend Bozuldu" — DURUM: KISMEN, 🔴 CANLI KULLANICI-GÖRÜNÜR KALINTI BULUNDU

Ana gövde (`e9d7e98`, 07.08 + takip fix `005a875`, 15.08) tamam — templates/ ve static/'te case-insensitive grep = 0, 5 testlik regresyon suite'i (`tests/test_cpo1321_faz1_t1_2_trend_bozuldu_rename.py`) yeşil.

**Ama app.py'de 2 satır kaldı:**
- `app.py:6584` — `opposite_words` doğrulama listesi (Gemini AI-explain çıktısını yön-tutarlılığı için kontrol eden dahili anahtar-kelime listesi) — kullanıcıya render edilmiyor, muhtemelen kasıtlı/kapsam dışı.
- 🔴 **`app.py:1773`** — entry_note üretici, `"Zayıf trend taze (N bar), SL yakın..."` — bu değer `app.py:1971`'de JSON'a konuyor, `templates/hisse.html:3097`'de `signalData.entry_note` olarak **doğrudan client-side render ediliyor**. Bugünkü (17.08) canlı `last_cache.json`'da **22 kayıtta** fiilen "Zayıf trend taze (...)" görünüyor — gerçek, aktif, kullanıcı-görünür bir T1.2 ihlali.

Bağımsız doğrulama birebir mutabık, ikinci satırı (6584) somut olarak teyit etti.

**Öneri (uygulanmadı, karar kuyruğuna eklendi):** `app.py:1773`'teki string `"Zayıf trend taze..."` → SIGNAL_LABELS'taki kanonik "Trend Bozuldu" ile tutarlı bir ifadeye çevrilmeli (örn. "Trend Bozuldu sinyali taze (N bar), SL yakın" — AL tarafındaki paralel dal "Sinyal taze" ile simetrik olacak şekilde). Küçük ama metin/wording kararı — CPO/Ozan onayı istendi, tek satır + regresyon testine case-insensitive assertion eklenmesi gerekiyor (mevcut test yalnız "Zayıf Trend", büyük-T'yi arıyor, "Zayıf trend" küçük-t'yi yakalamıyor — aynı tuzağın nüksetmemesi için).

## T1.3 — bp-vocab.js / bp-format.js tekilleştirme — DURUM: TAMAM

`6a29ec6` (08.08.2026) ile tamamlanmış. 15 şablon `bp-vocab.js`'i `<script>` ile yüklüyor, hepsi `BP_ASSET_LABELS`/`BP_ASSET_DECIMALS`'tan alıyor (bağımsız kopya harita yok). ALTIN/GÜMÜŞ hem etiket hem ondalık haritasında mevcut. Backlog'un "17 şablon" rakamı konsolidasyon-ÖNCESİ kopya-harita sayısı, "15" konsolidasyon-SONRASI gerçek tüketici sayısı — terminoloji farkı, regresyon değil.

## T1.4 — tokens.css genişletme (10 kategori) — DURUM: TAMAM (tanım), migrasyon adayı yeni bulgu

Backlog'un "bugün 1/10" ifadesi bayat — tokens.css'te 10 kategorinin (spacing/typography/weight/leading/shadow/z-index/duration/easing/radius/breakpoint) **TAMAMI tanımlı**. Ama fiilî kullanım eşit değil:
- **4/10 kategori canlı kullanımda:** typography (1014 ref/27 dosya), shadow (20/9), z-index (100/27), radius (377/29).
- **6/10 kategori tanımlanmış ama SIFIR tüketicili (tamamen ölü):** `--bp-space-*`, `--bp-weight-*`, `--bp-leading-*`, `--bp-dur-*`, `--bp-ease-*`, `--bp-bp-*`.

Dosyanın kendi yorumu bunu bilinçli bir strateji olarak açıklıyor ("önce ölçek tanımla, migrasyon sonra"), gizli regresyon değil. Ama Master Program'da bu 6 kategorinin migrasyonuna karşılık gelen ayrı bir T-kodu yok — yeni bir kalem olarak açılması önerilir (T1.4-migrate benzeri).

## T1.6 — template-local `:root` GitHub-paleti temizliği — DURUM: KISMEN

Backlog'daki "5 şablon / 312 kullanım" bayat ve rakamsal olarak yanlış. Güncel durum:
- `abd_tarama.html` (T4.1, `f9e4ac8`) ve `kripto_gate.html` (`c57a93b`) **tamamen silinmiş**.
- Geriye yalnız **3 şablon**: `kategori.html`, `tarama.html`, `varlik.html` — her biri 1'er `:root` bloğu.
- `--bg`/`--sat`/`--text3` zaten `var(--bp-*)` alias'ına çevrilmiş; `--al`(#3fb950)/`--brand`(#1f6feb)/`--gold`(#e3b341) hâlâ ham GitHub-paleti hex, kanonik `--bp-al`(#00e290)/`--bp-brand`(#b8c3ff)/`--bp-gold`(#f59e0b)'dan farklı.
- Canlı `var()` sayımı: kategori 53 + tarama 87 + varlik 82(+1 --accent) = **223**, backlog'un 312'si değil.
- `tools/style-guard.py`'de "K-C ŞABLON-YEREL :root" guard'ı var ama **RATCHET** (mevcut borcu bloklamaz, yalnız artışı engeller) — backlog'un istediği sert "yasak" kapısı değil.
- `varlik.html` mum grafiğinde `upColor`/`borderUpColor`/`wickUpColor` hâlâ ham `#3fb950` JS literal; `downColor` ise `bpToken('--bp-sat', ...)` ile çözülüyor — renk kaynağı bölünmüş (kırmızı taraf token, yeşil taraf hardcode).

Migrasyon kararı (3 şablon, ~9 ham-hex token → alias + canvas literal → bpToken + K-C guard ratchet→hard-block) diğer FAZ1/FAZ5/FAZ8 kalemleriyle aynı karar kuyruğuna eklenmeli.

## T1.7 — format-lint v2 kalıcılaştırma — DURUM: muhtemelen T9.2 ile aynı iş, DOĞRULANDI

T9.2 (17.08) zaten "`tools/style-guard.py` + `blog_content.py` + `static/css/*.css` + `static/*.js`" kapsıyor diyordu — bu T1.7'nin istediği aynı şey (v1: 26/33 şablon + blog_content.py yok → v2: tüm sayfa şablonları + 2 ek dosya sınıfı). Bu turda çapraz-doğrulama: `lint_scope.sayfa_sablonlari()` bugün **24** sayfa şablonu döndürüyor (T9.2'nin yazdığı "28" değil) — fark bir regresyon değil, T4.1/T1.6'da tespit edilen 4 sayfanın (abd_tarama, kripto_gate, heatmap, gucu_yuksek) o tarihten sonra silinmesiyle açıklanıyor (28-4=24). Alt satır: T1.7'nin kabul ölçütü fiilen karşılanıyor, yalnız T9.2'deki rakam kendi zamanında doğruydu, sonra bayatladı. Doküman-only not.

## T1.8 — mobil-özel metin taraması — DURUM: KISMEN

3 örnekten 2'si hâlâ gerçek canlı tutarsızlık:
1. "Ana Sayfa" (mobil alt nav, `_mobile_nav_partial.html:119`) vs "Sinyaller" (masaüstü nav, aynı `/` rotası için index/ozet/sektor_harita/hisse.html'de 4 ayrı yerde) — çözülmedi.
2. "GİRİŞ"/"STOP" (mobil JS `mcList` render dalı, `index.html:3982-3986`) vs "Giriş ₺"/"SL ₺" (masaüstü tablo başlığı, aynı sayfada `index.html:2489-2508`) — çözülmedi.
3. "Kalite" çakışması (tier filtresi vs giriş kalitesi) — **artık GEÇERSİZ**, T3.3 ile tier filtresi tamamen kaldırılmış (`index.html:3881-3883` yorum, `/api/tarama`'da `tier` param yok), geriye kalan tek "Kalite" kullanımı tutarlı biçimde entry_quality'yi kısaltıyor.

Not: Backlog'daki "1G" etiketi bayat — mobil şeritteki 3. hücre "1G" değil "DÖNEM" (`index.html:3987`).

Kod değişikliği yapılmadı, hangi etiketin kanonik olacağı (Ana Sayfa mı Sinyaller mi, GİRİŞ/STOP mu Giriş ₺/SL ₺ mü) ürün kararı — CPO/Ozan onayı gerekiyor.

---

## Karar kuyruğuna eklenecek yeni maddeler (bu turdan)

1. **T1.2 residual** — `app.py:1773` "Zayıf trend taze" → kanonik metne çevrilsin (öneri metni yukarıda), 🔴 canlı kullanıcı-görünür, düşük risk ama wording kararı.
2. **T1.4 dead-token migration** — 6/10 tokens.css kategorisi (space/weight/leading/dur/ease/bp) sıfır tüketicili, migrasyon T-kodu açılması önerisi.
3. **T1.6 migration** — 3 şablon (kategori/tarama/varlik) ham-hex → alias, K-C guard ratchet→hard-block, varlik.html canvas upColor hardcode → bpToken.
4. **T1.8 kanonik etiket kararı** — Ana Sayfa/Sinyaller ve GİRİŞ-STOP/Giriş ₺-SL ₺ hangisi kanonik.
