# T5.1/T5.3/T5.7 Sınıflandırması

**Yöntem:** 3 paralel salt-okur SSH ajanı (biri T5.1, biri T5.3, biri T5.7 — birbirini görmeden) → her biri için ayrı bağımsız kör doğrulama ajanı (kendi sıfırdan grep/wc taramasını yapıp sınıflandırmayla karşılaştırdı). S1/S7/T3.4/T5.2/T5.4/T5.5/T5.6/T5.8/T5.9/T8-serisi ile aynı desen. Sonuç: **3/3'te sıfır anlaşmazlık** — üç doğrulama ajanı da kendi bağımsız taramasında birebir aynı sayılara ve birebir aynı sonuca ulaştı, hiçbir düzeltme gerekmedi.

**Genel sonuç: 3/3 backlog kalemi TAMAM — üçü de gerçek kod değişikliğiyle kapatılmış, yalnızca master dokümandaki DURUM notu hiç işlenmemiş.**

**🔴 Kendi-düzeltme (yazıldıktan sonra fark edildi):** İlk sentez T5.3/T5.7'yi "backlog iddiası tamamen yanlış/bayat, sorun hiç var olmamış" diye çerçevelemişti — bu YANLIŞ bir yorum. `git log --all` taraması şunu gösterdi: bu üç kalem **gerçekten koda dokunularak uygulanmış**, sadece FAZ8 isimli commit'ler/branch'ler altında (T-kod FAZ5'te ama iş FAZ8 a11y turunda yapılmış) ve master dokümanın FAZ5 tablosuna hiç geri yansıtılmamış:
- T5.1: `508bb26`+`b0f2304` (05-06.08 civarı, "faz5-t5.1")
- T5.3: `f203d3f`/`708d99e` (72 th/8 şablon) → `d45b413`/`9459f26` (aria-sort+button, 19 th) → `50e8481`/`fed88e5` (karsilastir matris scope=row/col) → `0dbf4c6` (kalan 2 th+2 caption, "T5.3 tamamlandi 80/80+12/12") — çok adımlı, art arda tamamlanmış bir seri.
- T5.7: `18f5d29` (12.08, "44 oge tarandi, 35'i label-for/aria-label aldı, 5 zaten sağlamdı, 4 premium-modal T3.2'de silinecek diye yatırım yapılmadı")

Sayılardaki düşüş (T5.3: 80→71 th, T1.1'dekiyle aynı desen) FAZ4'te kaldırılan/birleştirilen sayfalarla (`/heatmap`, `/gucu-yuksek`, `/abd/tarama`, `/sektor-karsilastir`) açıklanıyor — bu sayfalardaki tablolar implementasyondan SONRA silindi, kapsam küçüldü ama oran hep %100 kaldı. Doğru DURUM: **TAMAM (uygulanmış)**, "iddia geçersizdi" değil. Aşağıdaki madde bazlı bulgular (sayılar, doğrulama) hâlâ geçerli — yalnız "neden eksiklik yok" açıklaması düzeltildi: backlog'un orijinal rakamları (84 th, 48 alan, 1 label-for) o TARİHTEKİ gerçek açığı doğru yansıtıyordu, sonradan kapatıldı.

---

## T5.1 — Container/Layout Primitifi

**Backlog maddesi:** "`.container`/layout primitifi (23 şablon, 7 varyant → 1). Kabul ölçütü: Tek max-width token seti."

**Sonuç: İŞ ZATEN YAPILMIŞ — backlog bayat.**

- Gerçek kapsam: 20 şablon `.container{}` kuralı + 2 şablon (`404.html`, `profil.html`) `main{}` sarmalayıcısı = 22 şablon (23 değil).
- `.container{}` içindeki max-width değerleri artık ham px DEĞİL — `static/css/tokens.css:429-436`'daki `--bp-container-N` token setine BAĞLANMIŞ durumda (commit `508bb26` "faz5-t5.1", 22 şablon/7 değer, sıfır görsel değişiklik; ardından `b0f2304` ile `main{}` sarmalayıcı 3 token daha eklemiş).
- Canlı kullanımda 8 farklı değer (640/680/720/820/860/1100/1200/1400px) + `--bp-container-900` tüketicisiz (ölü token — tek tüketicisi olan `gucu_yuksek.html` T4.2'de `/tarama`'ya birleşince silindi).
- **"7 varyant → 1" hedefi orijinal uygulayıcı tarafından bilinçli olarak REDDEDİLMİŞ** — `tokens.css:421-424` yorumu: "7 deger BILEREK ayri tutuldu (820 vs 860 farkli sablon gruplarinin bilinen genisligi, snap edilmedi)". Tek değere zorlamak (örn. 1400px'lik `hisse.html`/`index.html`'i 1100px'e sıkıştırmak, %27 fark) yatay taşma riski yaratır.

**Öneri:** Backlog kalemini KAPAT. İsteğe bağlı kozmetik temizlik: `--bp-container-900` (tokens.css:435) ölü token silinebilir, tokens.css:419-436'daki "22 şablon" yorumu bayat iç-dağılım notuyla güncellenebilir (düşük öncelik, kod değişikliği).

---

## T5.3 — Tablo Bileşeni: scope=/caption/aria-sort + Gerçek `<button>`

**Backlog maddesi:** "84 `<th>`'nin tamamında scope; klavyeyle sıralama çalışır."

**Sonuç: TAMAM — `f203d3f`/`d45b413`/`50e8481`/`0dbf4c6` serisiyle uygulanmış, güncel durum bunu doğruluyor.**

- Gerçek `<th>` sayısı **71** (84 değil; ham `grep -o '<th'` 82 veriyor ama 11'i `<thead>` alt-dize yanlış-eşleşmesi — asıl 84 rakamının kaynağı ne bu substring hatasıyla ne mevcut kodla açıklanabiliyor, muhtemelen hiç doğrulanmamış/bayat bir sayı).
- 71 `<th>`'nin **TAMAMI** (71/71) zaten `scope=` taşıyor.
- 11 `<table>`'ın **TAMAMI** (11/11) zaten `<caption>` taşıyor.
- Sıralanabilir başlık deseni yalnız 3 şablonda var (`index.html`, `sinyal_performans.html`, `tarama.html`) — bu 3 şablondaki **tüm** sıralanabilir `<th>` zaten gerçek `<button type="button">` içeriyor (0 istisna, div/th üzerine çıplak onclick deseni yok), `aria-sort` niteliği JS ile dinamik güncelleniyor. Diğer 5 tablo (hisse/portfolio/karsilastir/kategori/varlik) statik/sıralanamaz — kapsam dışı.

**Öneri:** Backlog kalemini TAMAM işaretle. Gelecekte statik 5 tablodan biri sıralanabilir hale getirilirse aynı buton+aria-sort deseni oraya da uygulanmalı — ama bu ayrı, yeni bir T-kalemi olur.

---

## T5.7 — Form Alanlarına Erişilebilir Ad

**Backlog maddesi:** "Form alanlarına erişilebilir ad (48 alan, `aria-label`/`label[for]`). Kabul ölçütü: `label[for]` sayısı 1 → 48."

**Sonuç: TAMAM — `18f5d29` ile uygulanmış (+ sonraki küçük dokunuşlarla tamamlanmış), güncel boşluk sıfır.**

- Gerçek form-alanı (input/select/textarea) sayısı **43** (48 değil; `type="hidden"` sayısı 0, fark açıklanamıyor).
- `label[for]` sayısı **15** (1 değil — backlog'un tek-satır grep'i muhtemelen çok-satırlı `<label ... for="...">` bloklarını kaçırmış).
- Kalan **27** alan `aria-label` taşıyor, **1** alan (`portfolio.html:224`, gizli dosya-yükleme input'u) sarmalayan `<label>` içinde (implicit association).
- **27 + 15 + 1 = 43 = tüm alanlar.** Kritik formlar (iletişim, tarama filtreleri, 404 arama, alarm ayarları, portfolio) tek tek doğrulandı — hiçbiri yalnızca placeholder'a dayanmıyor, hepsinin gerçek `label[for]` veya `aria-label`'ı var.

**Öneri:** Backlog kalemini TAMAM işaretle. Kod tabanında şu an erişilebilir addan yoksun tek bir form alanı bile yok (0/43).

---

## Ortak not

Bu turda (workflow ile sınıflandırma sırasında) kod DEĞİŞMEDİ — üç kalem de daha ÖNCEKİ turlarda (05-12.08 arası, FAZ8-a11y adı altında) gerçek kod değişiklikleriyle zaten kapatılmıştı, bu tur yalnızca doğrulama + eksik DURUM notunu tamamlama işlevi gördü. Karar kuyruğuna yeni madde EKLENMEDİ — tasarım/marka onayı gerektiren bir migrasyon kararı yok, üçü de "TAMAM" statüsünde kapanıyor.
