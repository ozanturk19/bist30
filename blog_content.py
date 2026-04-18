# -*- coding: utf-8 -*-
"""BorsaPusula blog makaleleri — slug → makale verisi"""

ARTICLES = [
  {
    "slug": "bist100-nedir",
    "title": "BIST100 Nedir? Hangi Hisseler Var?",
    "desc": "Borsa İstanbul'un en önemli endeksi BIST100'ü, kapsamını ve nasıl takip edileceğini öğrenin.",
    "date": "2026-04-01",
    "mins": 5,
    "cat": "Temel Kavramlar",
    "body": """
<p>BIST100 (BİST 100 Endeksi), Borsa İstanbul'da en yüksek işlem hacmine sahip <strong>100 hissenin</strong> fiyat hareketlerini izleyen bir endekstir. Türkiye borsasının "nabzı" olarak bilinir; yabancı yatırımcılar Türk hisse piyasasını değerlendirirken ilk baktıkları göstergedir.</p>

<h2>Endeks Nasıl Hesaplanır?</h2>
<p>BIST100, piyasa değeri ağırlıklı bir endekstir. Her hissenin endeks üzerindeki etkisi, o hissenin <em>piyasa değerine</em> (fiyat × dolaşımdaki hisse adedi) orantılıdır. Piyasa değeri büyük şirketler (AKBNK, GARAN, THYAO gibi) endeksi daha fazla etkiler.</p>

<h2>BIST30, BIST50, BIST100 Farkı</h2>
<ul>
  <li><strong>BIST30:</strong> En likit 30 hisse. Vadeli işlemler (VİOP) için temel alınır.</li>
  <li><strong>BIST50:</strong> En likit 50 hisse. BIST30'un genişletilmiş hali.</li>
  <li><strong>BIST100:</strong> En likit 100 hisse. Genel piyasa barometresi.</li>
</ul>
<p>Bir hissenin BIST30'da olması, o hissenin hem likit hem de kurumsal yatırımcıların portföyünde bulunduğunun göstergesidir.</p>

<h2>Endeks Revizyonları</h2>
<p>Borsa İstanbul, endeks bileşenlerini <strong>her yıl Mart ve Eylül</strong> aylarında günceller. Kriterleri sağlayamayanlar endeksten çıkar, yeni yüksek hacimli hisseler girer. Bu değişiklikler kurumsal yatırımcıların alım-satım kararlarını önemli ölçüde etkiler.</p>

<h2>BIST100'ü Takip Etmenin Yolları</h2>
<ul>
  <li>BorsaPusula'da 90 BIST100 hissesinin anlık sinyalini izleyin.</li>
  <li>Günlük <a href="/ozet">Sinyal Özeti</a> sayfasından piyasa genelinin durumunu görün.</li>
  <li>Endeks bileşenlerinin tamamı Borsa İstanbul resmi sitesinde yayınlanır.</li>
</ul>

<h2>BIST100 ile Yatırım Stratejisi</h2>
<p>Endeks içindeki hisseler daha düşük riskli kabul edilir çünkü likiditesi yüksektir — hızla alınıp satılabilir. Ancak "endeks hissesi" olmak tek başına kaliteli yatırım anlamına gelmez; teknik ve temel analiz her zaman gereklidir.</p>
"""
  },
  {
    "slug": "supertrend-indikatoru-nedir",
    "title": "Supertrend İndikatörü Nedir? Nasıl Kullanılır?",
    "desc": "Supertrend(10,3) indikatörünün çalışma prensibi, parametreleri ve BIST hisselerinde nasıl yorumlanacağı.",
    "date": "2026-04-02",
    "mins": 6,
    "cat": "Teknik Analiz",
    "body": """
<p>Supertrend, <strong>ATR (Average True Range)</strong> tabanlı bir trend takip göstergesidir. Fiyatın üzerinde mi yoksa altında mı seyrettiğine bakarak basit bir AL/SAT sinyali üretir. Hem yeni hem de deneyimli yatırımcıların sıkça kullandığı bir indikatördür.</p>

<h2>Nasıl Hesaplanır?</h2>
<p>Supertrend iki değişkene dayanır:</p>
<ul>
  <li><strong>Period (Dönem):</strong> ATR hesabında kullanılan bar sayısı. BorsaPusula'da <code>10</code> kullanılır.</li>
  <li><strong>Multiplier (Çarpan):</strong> ATR'nin kaç katı band genişliği olacağı. BorsaPusula'da <code>3</code> kullanılır.</li>
</ul>
<p>Formül özeti:</p>
<pre>Üst Band = (Yüksek + Düşük) / 2 + Multiplier × ATR(Period)
Alt Band  = (Yüksek + Düşük) / 2 - Multiplier × ATR(Period)</pre>
<p>Fiyat üst bandı yukarı kırarsa <strong>LONG (AL)</strong>, alt bandı aşağı kırarsa <strong>SHORT (SAT)</strong> sinyali oluşur.</p>

<h2>Supertrend(10,3) Neden?</h2>
<p>Düşük period + yüksek multiplier → daha az sahte sinyal ama geç tepki. Yüksek period + düşük multiplier → hızlı ama çok fazla whipsaw (sahte sinyal). <code>(10,3)</code> kombinasyonu, günlük BIST hisseleri için gürültü ile duyarlılık arasında kabul görmüş bir denge noktasıdır.</p>

<h2>Grafiklerde Nasıl Görünür?</h2>
<ul>
  <li>Fiyatın <strong>altındaki yeşil çizgi</strong> → Yükselen trend, destek seviyesi</li>
  <li>Fiyatın <strong>üzerindeki kırmızı çizgi</strong> → Düşen trend, direnç seviyesi</li>
</ul>
<p>Çizgi renk değiştirdiği anda sinyal oluşur. BorsaPusula grafiklerinde bu geçiş noktaları açıkça görülebilir.</p>

<h2>Supertrend'in Zayıf Yönleri</h2>
<p>Yatay (sideways) piyasalarda Supertrend çok sık sinyal üretir ve sahte girişlere yol açar. Bu yüzden BorsaPusula, Supertrend'i tek başına değil <strong>ADX ≥ 25 filtresiyle</strong> birlikte kullanır. ADX trendin <em>var olduğunu</em> doğrulamadan Supertrend sinyali geçerli sayılmaz.</p>

<h2>Stop Loss Olarak Supertrend</h2>
<p>AL pozisyonunda Supertrend alt bandı dinamik stop loss görevi görür. Fiyat bu seviyenin altına inerse sinyal SAT'a döner ve pozisyondan çıkılması gerekir. Bu mekanizma, büyük kayıpları otomatik olarak sınırlar.</p>
"""
  },
  {
    "slug": "adx-indikatoru-nedir",
    "title": "ADX İndikatörü Nedir? Trend Gücünü Nasıl Ölçer?",
    "desc": "ADX (Average Directional Index) nedir, 25 eşik değeri neden önemlidir, DI+ ve DI- nasıl yorumlanır?",
    "date": "2026-04-03",
    "mins": 5,
    "cat": "Teknik Analiz",
    "body": """
<p>ADX (Average Directional Index — Ortalama Yönlü Hareket Endeksi), bir trendin <strong>gücünü</strong> ölçen bir göstergedir. Dikkat: ADX yön söylemez, yalnızca trendin ne kadar güçlü olduğunu söyler. J. Welles Wilder tarafından 1978'de geliştirilmiştir.</p>

<h2>ADX Değerleri Nasıl Yorumlanır?</h2>
<table style="width:100%;border-collapse:collapse;margin:12px 0">
  <tr style="background:#21262d"><th style="padding:8px;text-align:left">ADX Değeri</th><th style="padding:8px;text-align:left">Anlam</th></tr>
  <tr><td style="padding:8px;border-top:1px solid #30363d">0 – 20</td><td style="padding:8px;border-top:1px solid #30363d">Trend yok, yatay piyasa</td></tr>
  <tr><td style="padding:8px;border-top:1px solid #30363d">20 – 25</td><td style="padding:8px;border-top:1px solid #30363d">Zayıf trend oluşuyor</td></tr>
  <tr><td style="padding:8px;border-top:1px solid #30363d"><strong>25 – 40</strong></td><td style="padding:8px;border-top:1px solid #30363d"><strong>Güçlü trend ✅ Sinyal geçerli</strong></td></tr>
  <tr><td style="padding:8px;border-top:1px solid #30363d">40+</td><td style="padding:8px;border-top:1px solid #30363d">Çok güçlü trend</td></tr>
</table>

<h2>DI+ ve DI− Nedir?</h2>
<p>ADX sistemi üç çizgiden oluşur:</p>
<ul>
  <li><strong>ADX (siyah/sarı):</strong> Trend gücü — 25'in üzeri sinyal için şart</li>
  <li><strong>DI+ (yeşil):</strong> Yükselen baskı (Positive Directional Indicator)</li>
  <li><strong>DI− (kırmızı):</strong> Düşen baskı (Negative Directional Indicator)</li>
</ul>
<p><strong>DI+ &gt; DI−</strong> ise piyasada alış baskısı hâkim → AL yönü<br>
<strong>DI− &gt; DI+</strong> ise piyasada satış baskısı hâkim → SAT yönü</p>

<h2>Neden ADX ≥ 25 Şartı?</h2>
<p>Trend yokken (ADX &lt; 25) Supertrend de EMA da sahte sinyal üretir. ADX filtresi, yalnızca gerçekten güçlü bir trendin başladığı anlarda devreye girmesini sağlar. BorsaPusula'nın üçlü filtre sisteminde ADX, "gürültüyü kesen" kritik katmandır.</p>

<h2>Pratik Kullanım Örneği</h2>
<p>Diyelim ki THYAO için Supertrend LONG sinyali verdi. Ancak ADX = 18. Bu durumda BorsaPusula <strong>AL sinyali üretmez</strong> — trend yeterince güçlü değil demektir. ADX 28'e çıktığında ve DI+ > DI− olduğunda sinyal geçerli hale gelir.</p>
"""
  },
  {
    "slug": "ema-hareketli-ortalama-nedir",
    "title": "EMA (Üstel Hareketli Ortalama) Nedir?",
    "desc": "EMA12 ve EMA99 kesişimi neden trend sinyali olarak kullanılır? EMA ile SMA farkı nedir?",
    "date": "2026-04-04",
    "mins": 4,
    "cat": "Teknik Analiz",
    "body": """
<p>EMA (Exponential Moving Average — Üstel Hareketli Ortalama), son fiyatlara daha fazla ağırlık vererek hesaplanan bir hareketli ortalamadır. Basit hareketli ortalamanın (SMA) aksine, EMA son gelişmelere daha hızlı tepki verir.</p>

<h2>EMA ile SMA Farkı</h2>
<p><strong>SMA (Basit Ortalama):</strong> Son N günün kapanışının aritmetik ortalaması. Her güne eşit ağırlık verilir.<br>
<strong>EMA:</strong> Son günlere üstel olarak artan ağırlık verilir. Fiyat ani değişimlerine daha hızlı adapte olur.</p>
<p>Sonuç: EMA, trend değişimlerini SMA'dan daha erken yakalar — ancak daha fazla gürültü içerebilir.</p>

<h2>EMA12 ve EMA99 Neden?</h2>
<ul>
  <li><strong>EMA12:</strong> ~2.5 haftalık kısa dönem momentumu temsil eder</li>
  <li><strong>EMA99:</strong> ~5 aylık uzun dönem trendi temsil eder</li>
</ul>
<p>Bu iki ortalama birbirini <em>kestiğinde</em> trend değişimi sinyali oluşur:</p>
<ul>
  <li><strong>EMA12 &gt; EMA99 (Altın Kesişim):</strong> Kısa dönem momentum uzun dönem trendin üzerine çıktı → Yükselen trend başlangıcı</li>
  <li><strong>EMA12 &lt; EMA99 (Ölüm Kesişimi):</strong> Kısa dönem momentum uzun dönem trendin altına düştü → Düşen trend başlangıcı</li>
</ul>

<h2>BorsaPusula Grafiklerinde EMA</h2>
<p>Hisse detay sayfalarında EMA12 <span style="color:#58a6ff">mavi</span>, EMA99 <span style="color:#e3b341">sarı</span> renkte gösterilir. İki ortalama arasındaki dolgu EMA12 > EMA99 ise yeşil, EMA12 < EMA99 ise kırmızı renge döner — trendin yönü tek bakışta anlaşılır.</p>

<h2>EMA Tek Başına Yeterli Mi?</h2>
<p>Hayır. EMA kesişimleri gecikmeli sinyal üretir ve yatay piyasalarda çok sık kesişim yaşanır. Bu yüzden BorsaPusula, EMA'yı Supertrend ve ADX ile birlikte <strong>üçüncü teyit katmanı</strong> olarak kullanır. Üç kriter aynı anda aynı yönü gösterdiğinde sinyal çok daha güvenilirdir.</p>
"""
  },
  {
    "slug": "teknik-analiz-temelleri",
    "title": "Teknik Analiz Nedir? Borsa Başlangıç Rehberi",
    "desc": "Teknik analiz nedir, temel analizden farkı nedir, hangi göstergeler kullanılır? Yeni yatırımcılar için kapsamlı rehber.",
    "date": "2026-04-05",
    "mins": 7,
    "cat": "Temel Kavramlar",
    "body": """
<p>Teknik analiz, geçmiş fiyat hareketleri ve işlem hacmini inceleyerek gelecekteki fiyat hareketlerini tahmin etmeye çalışan bir yöntemdir. Temel varsayımı şudur: <em>Piyasa tüm bilgiyi zaten fiyatlamıştır ve fiyatlar trendler halinde hareket eder.</em></p>

<h2>Teknik Analiz vs Temel Analiz</h2>
<table style="width:100%;border-collapse:collapse;margin:12px 0">
  <tr style="background:#21262d"><th style="padding:8px;text-align:left">Kriter</th><th style="padding:8px;text-align:left">Teknik Analiz</th><th style="padding:8px;text-align:left">Temel Analiz</th></tr>
  <tr><td style="padding:8px;border-top:1px solid #30363d">Odak</td><td style="padding:8px;border-top:1px solid #30363d">Fiyat & hacim</td><td style="padding:8px;border-top:1px solid #30363d">Finansal tablolar</td></tr>
  <tr><td style="padding:8px;border-top:1px solid #30363d">Zaman ufku</td><td style="padding:8px;border-top:1px solid #30363d">Kısa-orta vadeli</td><td style="padding:8px;border-top:1px solid #30363d">Uzun vadeli</td></tr>
  <tr><td style="padding:8px;border-top:1px solid #30363d">Araçlar</td><td style="padding:8px;border-top:1px solid #30363d">Grafik, indikatör</td><td style="padding:8px;border-top:1px solid #30363d">PE, PB, EPS, gelir</td></tr>
  <tr><td style="padding:8px;border-top:1px solid #30363d">Soru</td><td style="padding:8px;border-top:1px solid #30363d">Ne zaman al/sat?</td><td style="padding:8px;border-top:1px solid #30363d">Hangi hisseyi al?</td></tr>
</table>
<p>İdeal yaklaşım ikisini birleştirmektir: Temel analizle "hangi hisse" sorusunu, teknik analizle "ne zaman gir" sorusunu yanıtlayın.</p>

<h2>Temel Grafik Bileşenleri</h2>
<ul>
  <li><strong>Mum (Candlestick) Grafiği:</strong> Her bar açılış, kapanış, yüksek ve düşük fiyatı gösterir. Yeşil mum: kapanış > açılış (yükseliş). Kırmızı mum: kapanış < açılış (düşüş).</li>
  <li><strong>Destek Seviyesi:</strong> Fiyatın düşerken durduğu, alım ilgisinin güçlendiği bölge.</li>
  <li><strong>Direnç Seviyesi:</strong> Fiyatın yükselirken durduğu, satış baskısının arttığı bölge.</li>
  <li><strong>Trend:</strong> Yükselen (higher highs + higher lows), düşen (lower highs + lower lows) veya yatay.</li>
</ul>

<h2>Popüler Teknik Göstergeler</h2>
<ul>
  <li><strong>Trend Takip:</strong> Supertrend, EMA, MACD</li>
  <li><strong>Momentum:</strong> RSI, Stochastic</li>
  <li><strong>Hacim:</strong> OBV (On Balance Volume), VWAP</li>
  <li><strong>Volatilite:</strong> Bollinger Bantları, ATR</li>
  <li><strong>Trend Gücü:</strong> ADX, DI+/DI−</li>
</ul>

<h2>Teknik Analizin Sınırları</h2>
<p>Teknik analiz istatistiksel olasılıklar üzerine çalışır — kesin değildir. Beklenmedik haberler (savaş, deprem, merkez bankası kararı) en iyi teknik kurulumu da bozabilir. Bu yüzden <strong>stop loss</strong> kullanmak vazgeçilemez bir kuraldir.</p>
"""
  },
  {
    "slug": "stop-loss-nedir",
    "title": "Stop Loss Nedir? Neden Hayati Önem Taşır?",
    "desc": "Stop loss emri nedir, nasıl belirlenir, psikolojik hatalar nasıl önlenir? Risk yönetiminin temeli.",
    "date": "2026-04-06",
    "mins": 5,
    "cat": "Risk Yönetimi",
    "body": """
<p>Stop loss (zarar durdur emri), bir hissenin belirlenen fiyat seviyesinin altına düşmesi durumunda <strong>otomatik olarak pozisyonun kapatılması</strong> emridir. "Kaybetmeden önce çık" prensibidir.</p>

<h2>Neden Vazgeçilmez?</h2>
<p>Pek çok yatırımcı zarar ettiğinde "düzelir" diye bekler. Bu bekleme süreci şöyle ilerler:</p>
<ul>
  <li>%10 zarar: "Biraz daha bekleyeyim"</li>
  <li>%25 zarar: "Ortalama düşüreyim"</li>
  <li>%50 zarar: "Çıksam yarı fiyatına sattım olur"</li>
  <li>%80 zarar: "Artık ne önemi var..."</li>
</ul>
<p>Stop loss bu psikolojik tuzağa düşmekten korur. Küçük kayıpları keserek büyük kayıpların önüne geçer.</p>

<h2>Stop Loss Seviyeleri Nasıl Belirlenir?</h2>
<ul>
  <li><strong>Supertrend Stop:</strong> BorsaPusula sisteminde Supertrend bandı dinamik stop loss olarak işlev görür.</li>
  <li><strong>ATR Tabanlı Stop:</strong> Giriş fiyatı − (2 × ATR). Volatiliteye uyarlanmış stop.</li>
  <li><strong>Destek Tabanlı Stop:</strong> En yakın güçlü destek seviyesinin hemen altı.</li>
  <li><strong>Yüzde Tabanlı Stop:</strong> Giriş fiyatının %5–8 altı. Basit ama mekanik.</li>
</ul>

<h2>Pozisyon Büyüklüğü ile İlişkisi</h2>
<p>Stop loss yalnızca "nerede çıkarım" sorusunu değil, "ne kadar girerim" sorusunu da yanıtlar. Kural: <strong>Tek işlemde portföyün %1–2'sinden fazla risk alma.</strong></p>
<pre>Pozisyon Büyüklüğü = (Portföy × Risk%) ÷ (Giriş - Stop)
Örnek: 100.000₺ portföy, %1 risk, 10₺ giriş, 9₺ stop
→ (100.000 × 0,01) ÷ (10 - 9) = 1.000 lot</pre>

<h2>Trailing Stop (İzleyen Stop)</h2>
<p>Fiyat lehte yükselirken stop seviyesi de otomatik yükselir. Bu şekilde kazanç kilitlenir. BorsaPusula'nın Supertrend stop'u aslında bir trailing stop mantığıyla çalışır: Fiyat yükseldikçe Supertrend alt bandı da yükselir.</p>
"""
  },
  {
    "slug": "risk-yonetimi-portfoy",
    "title": "Borsa'da Risk Yönetimi: Portföy Nasıl Korunur?",
    "desc": "Pozisyon büyüklüğü, çeşitlendirme, korelasyon ve maksimum drawdown yönetimi ile portföyünüzü koruyun.",
    "date": "2026-04-07",
    "mins": 6,
    "cat": "Risk Yönetimi",
    "body": """
<p>Risk yönetimi, yatırım dünyasında "hayatta kalmak" anlamına gelir. En iyi teknik analizi yapan yatırımcı bile risk yönetimi olmadan kalıcı zarar görebilir. Amaç kayıpları sıfırlamak değil; <em>kontrol altında tutmaktır.</em></p>

<h2>1. Pozisyon Büyüklüğü Kuralı</h2>
<p>Tek bir işlemde portföyün <strong>%1–2'sinden</strong> fazla risk almayın. Bu kural uygulandığında 50 ardı ardına kaybeden işlem bile sizi batırmaz.</p>

<h2>2. Portföy Çeşitlendirmesi</h2>
<ul>
  <li><strong>Sektör çeşitlendirmesi:</strong> Tüm paranızı tek sektöre (örn. bankacılık) koymayın.</li>
  <li><strong>Korelasyon:</strong> GARAN ve AKBNK'ın ikisi de bankacılık — biri düşünce diğeri de düşer. Düşük korelasyonlu hisseler seçin.</li>
  <li><strong>Nakit rezervi:</strong> Portföyün %20–30'unu nakit tutun. Fırsatları kaçırmamak için.</li>
</ul>

<h2>3. Maksimum Drawdown (MDD)</h2>
<p>Drawdown, portföyün tepe değerinden çukur değerine kadar düşüşüdür. Kural: <strong>MDD %20'yi geçerse pozisyonları küçültün.</strong> Büyük drawdown psikolojik baskı yaratır ve hatalı kararları tetikler.</p>

<h2>4. Sinyal Onayı ve Pozisyon Alımı</h2>
<p>BorsaPusula sisteminde "3 gün onay" kuralı bu yüzden var. İlk çıkan sinyal gürültü olabilir; üç gün boyunca devam eden sinyal trendin gerçekten oluştuğunu gösterir. Bu kurala uymak, sahte girişleri büyük ölçüde azaltır.</p>

<h2>5. Kâr Hedefleri</h2>
<p>Risk:Ödül oranı en az <strong>1:2</strong> olmalıdır. Yani 5₺ risk alıyorsanız, en az 10₺ kâr potansiyeli olan işlemlere girin. Bu oran zamanla bileşik getiriyi dramatik şekilde artırır.</p>

<h2>6. Piyasa Barometresi Kullanımı</h2>
<p><a href="/ozet">BorsaPusula Özet</a> sayfasındaki barometrede AL oranı %30'un altındaysa piyasa genel olarak baskı altında demektir. Böyle dönemlerde yeni pozisyon açmak yerine mevcut pozisyonları korumak ve nakit tutmak daha akılcıdır.</p>
"""
  },
  {
    "slug": "al-sat-sinyali-nasil-yorumlanir",
    "title": "AL/SAT Sinyali Nedir? Nasıl Yorumlanır?",
    "desc": "Algoritmik AL ve SAT sinyallerinin ne anlama geldiği, nasıl kullanılacağı ve hangi tuzaklardan kaçınılacağı.",
    "date": "2026-04-08",
    "mins": 5,
    "cat": "Temel Kavramlar",
    "body": """
<p>BorsaPusula'daki AL ve SAT sinyalleri, <strong>üç teknik kriteri aynı anda</strong> sağlayan hisseler için otomatik olarak üretilir. Bu sinyaller bir tavsiye değil, teknik bir tespittir. Kararı yatırımcı verir.</p>

<h2>AL Sinyali Ne Demek?</h2>
<p>AL sinyali şu dört koşul aynı anda sağlandığında oluşur:</p>
<ul>
  <li>✅ Supertrend LONG modda (fiyat bandın üzerinde)</li>
  <li>✅ ADX ≥ 25 (güçlü trend var)</li>
  <li>✅ DI+ &gt; DI− (alış yönünde güç)</li>
  <li>✅ EMA12 &gt; EMA99 (kısa dönem uzun dönemin üzerinde)</li>
</ul>
<p>Bu koşullar yükselen trendin başlangıcını veya güçlenmesini işaret eder.</p>

<h2>SAT Sinyali Ne Demek?</h2>
<p>SAT sinyali yukarıdakilerin tersidir: ST SHORT + ADX ≥ 25 + DI− &gt; DI+ + EMA12 &lt; EMA99. Bu sinyal hem açığa satış yapanlar için hem de mevcut AL pozisyonundan çıkmak isteyenler için geçerlidir.</p>

<h2>Sinyal Kaç Gündür Devam Ediyor?</h2>
<p>Hisse sayfasında "X gündür AL" ifadesine dikkat edin. 1. günde oluşan sinyal henüz teyit edilmemiştir. <strong>3 gün ve üzeri</strong> sinyaller daha güvenilirdir. Giriş fiyatı, sinyalin oluştuğu günün kapanış fiyatı olarak gösterilir.</p>

<h2>BEKLE Sinyali</h2>
<p>Üç kriterin tamamı aynı yönü göstermiyorsa sinyal BEKLE'dir. Bu, "kaçırma korkusuyla" pozisyon almamak için önemli bir filtredir. Pek çok iyi işlem, BEKLE'den AL'a geçişi sabırla bekleyerek yakalanır.</p>

<h2>Neyi Yapmaz?</h2>
<ul>
  <li>Geleceği tahmin etmez — olasılıkları ifade eder</li>
  <li>Temel sorunları görmez (şirket iflası, manipülasyon)</li>
  <li>Makro riski hesaba katmaz (kur krizi, siyasi gelişme)</li>
</ul>
<p>Sinyal sistemi bir araçtır. Kararı hâlâ siz verirsiniz.</p>
"""
  },
  {
    "slug": "haftalik-trend-filtresi",
    "title": "Haftalık Trend Filtresi: Büyük Trende Karşı Gitme",
    "desc": "Günlük sinyal neden haftalık EMA20 ile filtrelenir? Çok zaman dilimi analizi neden önemlidir?",
    "date": "2026-04-09",
    "mins": 4,
    "cat": "Teknik Analiz",
    "body": """
<p>BorsaPusula'nın sinyal motoru yalnızca günlük verilere bakmaz. Günlük sinyaller, <strong>haftalık EMA20 yönüyle filtrelenir.</strong> Bu "trend gate" mekanizması, büyük trende karşı pozisyon almayı engeller.</p>

<h2>Neden Çok Zaman Dilimi?</h2>
<p>Büyük resmi görmeden günlük grafiğe bakmak, ormanı değil yalnızca ağaçları görmektir. Haftalık grafik düşüş trendindeyken günlük grafikte kısa süreli AL sinyalleri oluşabilir — bunlar genellikle "ölü kedi sıçraması"dır ve sürdürülebilir değildir.</p>

<h2>EMA20 Haftalık Neden?</h2>
<p>Haftalık EMA20 ≈ günlük EMA100. Bu seviyenin üzerindeki fiyat, orta vadeli yükseliş trendi içinde demektir. Kurumsal yatırımcıların çok büyük bölümü bu seviyeyi takip eder.</p>

<h2>Filtre Nasıl Çalışır?</h2>
<ul>
  <li>Haftalık EMA20 yükseliyor + Günlük AL sinyali → <strong>Geçerli</strong></li>
  <li>Haftalık EMA20 düşüyor + Günlük AL sinyali → <strong>Engellendi</strong></li>
  <li>Haftalık EMA20 düşüyor + Günlük SAT sinyali → <strong>Geçerli</strong></li>
</ul>

<h2>Pratikte Ne Fark Yaratır?</h2>
<p>Bu filtre, yıllık sinyal sayısını azaltır ama kaliteyi artırır. Daha az ama daha doğru sinyal demektir. Özellikle 2023–2024 dönemindeki BIST100 düzeltmelerinde bu filtre pek çok yanlış AL sinyalini dışarıda bıraktı.</p>
"""
  },
  {
    "slug": "pe-orani-nedir",
    "title": "F/K Oranı (PE Ratio) Nedir? Hisse Pahalı mı Ucuz mu?",
    "desc": "Fiyat/Kazanç oranı nasıl hesaplanır, hangi sektörlerde nasıl yorumlanır, tek başına yeterli midir?",
    "date": "2026-04-10",
    "mins": 5,
    "cat": "Temel Analiz",
    "body": """
<p>F/K oranı (Fiyat/Kazanç — Price-to-Earnings, PE Ratio), bir hissenin <strong>kaç yıllık kazancını fiyatladığını</strong> gösterir. Hissenin ucuz mu pahalı mı olduğunu anlamak için en yaygın kullanılan temel analiz göstergesidir.</p>

<h2>Formül</h2>
<pre>F/K = Hisse Fiyatı ÷ Hisse Başına Kazanç (EPS)
Örnek: Hisse 50₺, EPS = 5₺ → F/K = 10</pre>
<p>F/K = 10, yani yatırımcı kazancın 10 katını ödüyor. Şirket her yıl aynı kazancı sürdürürse yatırım 10 yılda geri döner.</p>

<h2>Yüksek vs Düşük F/K</h2>
<ul>
  <li><strong>Düşük F/K (örn. 5–8):</strong> Hisse ucuz görünüyor. Ama neden ucuz? Büyüme beklentisi yok mu, risk mi var?</li>
  <li><strong>Yüksek F/K (örn. 20–30):</strong> Piyasa yüksek büyüme bekliyor. Ama beklenti gerçekleşmezse sert düşebilir.</li>
</ul>

<h2>Sektöre Göre F/K Farklılıkları</h2>
<p>Bankacılık sektöründe F/K 8 normalken teknoloji şirketlerinde 30–50 olağandır. Bu yüzden farklı sektörlerdeki hisseleri F/K ile karşılaştırmak yanıltıcıdır. <strong>Aynı sektör içi karşılaştırma</strong> daha anlamlıdır.</p>

<h2>BIST100'de F/K Ortalamaları</h2>
<p>BIST100 tarihsel olarak gelişmiş piyasalara (ABD S&amp;P500 ~20) göre düşük F/K'larla işlem görür (genellikle 8–15 aralığında). Bu hem risk primini hem de Türkiye'ye özgü makroekonomik belirsizliği yansıtır.</p>

<h2>BorsaPusula'da F/K</h2>
<p>Her hisse sayfasının <strong>Temel Analiz</strong> bölümünde güncel F/K oranı gösterilir. Bu veri yfinance üzerinden 4 saatte bir güncellenir. Teknik sinyal + temel oran kombinasyonu çok daha güçlü bir karar zemini sunar.</p>
"""
  },
  {
    "slug": "piyasa-degerlemesi-pb-ratio",
    "title": "PD/DD Oranı (PB Ratio) Nedir?",
    "desc": "Fiyat/Defter Değeri oranı ne anlama gelir, hangi durumlarda önem kazanır ve BIST hisselerinde nasıl kullanılır?",
    "date": "2026-04-11",
    "mins": 4,
    "cat": "Temel Analiz",
    "body": """
<p>PD/DD oranı (Piyasa Değeri / Defter Değeri — Price-to-Book Ratio), bir şirketin borsada işlem gördüğü değerin, <strong>muhasebe kayıtlarındaki öz kaynak değeriyle</strong> karşılaştırılmasıdır.</p>

<h2>Formül</h2>
<pre>PD/DD = Hisse Fiyatı ÷ Hisse Başına Defter Değeri</pre>
<p>Defter değeri = Toplam Varlıklar − Toplam Borçlar (öz kaynak). Kısacası şirket bugün tasfiye edilseydi hissedara ne düşerdi?</p>

<h2>Yorumlama</h2>
<ul>
  <li><strong>PD/DD &lt; 1:</strong> Hisse defter değerinin altında işlem görüyor. Teorik olarak "ucuz" ama genellikle sorun var (düşük kârlılık, borç yükü).</li>
  <li><strong>PD/DD = 1:</strong> Piyasa defter değerine eşit değerleme yapıyor.</li>
  <li><strong>PD/DD &gt; 1:</strong> Piyasa şirkete defter değerinin üzerinde değer biçiyor — büyüme veya kaliteli iş modeli beklentisi var.</li>
</ul>

<h2>Hangi Sektörlerde Önemlidir?</h2>
<p>Bankacılık, sigorta ve holding sektörlerinde F/K yerine PD/DD daha anlamlıdır çünkü bu şirketlerin değeri büyük ölçüde varlık tabanına dayanır.</p>

<h2>Sınırları</h2>
<p>Defter değeri muhasebe kurallarına göre hesaplanır ve enflasyon yüksek ülkelerde (Türkiye gibi) çarpıcı şekilde yanıltıcı olabilir. Enflasyon döneminde sabit varlıkların gerçek değeri defter değerinin çok üzerinde olabilir.</p>
"""
  },
  {
    "slug": "algoritmik-trading-nedir",
    "title": "Algoritmik Trading Nedir? Bireysel Yatırımcı İçin Ne İfade Eder?",
    "desc": "Algoritmik trading sistemlerinin çalışma prensibi, avantajları ve sınırları. Bireysel yatırımcı nasıl faydalanabilir?",
    "date": "2026-04-12",
    "mins": 5,
    "cat": "Temel Kavramlar",
    "body": """
<p>Algoritmik trading (algo trading), önceden tanımlanmış kurallara göre alım-satım kararlarını <strong>otomatik olarak veren</strong> bilgisayar programlarıdır. Artık global işlemlerin %70-80'i algoritmalar tarafından gerçekleştirildiği tahmin edilmektedir.</p>

<h2>Algoritmik Sistemlerin Avantajları</h2>
<ul>
  <li><strong>Duygusuzluk:</strong> Korku, açgözlülük veya önyargı yoktur. Kural çalışır, karar verilir.</li>
  <li><strong>Hız:</strong> Milisaniyeler içinde işlem yapabilir.</li>
  <li><strong>Tutarlılık:</strong> Aynı koşullar her zaman aynı kararı üretir.</li>
  <li><strong>Backtesting:</strong> Strateji geçmiş verilerle test edilebilir.</li>
</ul>

<h2>BorsaPusula'nın Yaklaşımı</h2>
<p>BorsaPusula tam otomatik emir vermez. Bunun yerine algoritmik sinyal üretir ve kararı yatırımcıya bırakır. Bu "yarı otomatik" model şu avantajları sağlar:</p>
<ul>
  <li>Algoritmanın tutarlılığı + insanın bağlamsal değerlendirmesi</li>
  <li>Temel analiz, haberler veya makro faktörleri entegre etme imkânı</li>
  <li>Sistematik bir tarama — 90 hisseyi manuel incelemenize gerek yok</li>
</ul>

<h2>Backtesting ve Gerçekçi Beklentiler</h2>
<p>Algoritmaların geçmişte iyi performans göstermesi, gelecekte de aynı başarıyı garantilemez. Piyasa rejimleri değişir. 2020-2022 bull piyasasında iyi çalışan bir strateji, 2023 korreksiyonunda başarısız olabilir. Bu yüzden sistemi periyodik olarak gözden geçirmek önemlidir.</p>

<h2>Bireysel Yatırımcı Ne Yapabilir?</h2>
<p>Kendi algo sisteminizi kurmak için programlama bilgisi gerekir. Ancak BorsaPusula gibi platformlar aracılığıyla algoritmaların ürettiği sinyalleri kullanmak için teknik bilgiye ihtiyaç yoktur. Önemli olan sistemi <em>anlamak</em> ve kurallara uymaktır.</p>
"""
  },
  {
    "slug": "destek-direnc-seviyeleri",
    "title": "Destek ve Direnç Seviyeleri Nedir?",
    "desc": "Borsa grafiklerindeki en önemli kavramlardan destek ve direnç seviyeleri nasıl belirlenir ve kullanılır?",
    "date": "2026-04-13",
    "mins": 5,
    "cat": "Teknik Analiz",
    "body": """
<p>Destek ve direnç, teknik analizin temel taşlarıdır. Bu seviyeleri anlayan bir yatırımcı, fiyatın nerede durabileceğini veya tersine dönebileceğini daha iyi öngörebilir.</p>

<h2>Destek Seviyesi</h2>
<p>Destek, fiyatın <strong>defalarca düşüp toparlandığı</strong> bölgedir. Bu bölgede alıcılar devreye girerek fiyatın daha aşağıya gitmesini engeller. Bir destek kırıldığında — özellikle yüksek hacimle — genellikle hızlı bir düşüş yaşanır.</p>

<h2>Direnç Seviyesi</h2>
<p>Direnç, fiyatın <strong>defalarca yükselip geri döndüğü</strong> bölgedir. Bu bölgede satıcılar baskın gelir. Direncin kırılması "kırılım" (breakout) olarak adlandırılır ve güçlü bir yükseliş sinyali verir.</p>

<h2>Rol Değişimi Prensibi</h2>
<p>Kırılan bir direnç sonradan <strong>destek</strong> haline gelir. Kırılan bir destek ise <strong>direnç</strong>e dönüşür. Bu prensip teknik analizin en güçlü öngörülerinden biridir.</p>

<h2>Nerede Oluşur?</h2>
<ul>
  <li>Önceki yüksek ve düşük noktalar</li>
  <li>Yuvarlak sayılar (100₺, 50₺, 200₺)</li>
  <li>EMA ve Supertrend seviyeleri</li>
  <li>Fibonacci geri çekilme seviyeleri (%38.2, %50, %61.8)</li>
</ul>

<h2>BorsaPusula Grafiklerinde Kullanımı</h2>
<p>Hisse grafiklerinde Supertrend bandı önemli bir dinamik destek/direnç görevi görür. AL sinyalinde Supertrend alt bandının üzerinde kaldıkça trend devam ediyor demektir. Bu bandın kırılması ise SAT sinyaline geçiş anlamına gelir.</p>
"""
  },
  {
    "slug": "rsi-gostergesi-nedir",
    "title": "RSI Göstergesi Nedir? Aşırı Alım/Satım Bölgeleri",
    "desc": "RSI (Göreceli Güç Endeksi) nasıl hesaplanır, 30 ve 70 seviyeleri neden önemlidir, uyuşmazlık (divergence) nedir?",
    "date": "2026-04-14",
    "mins": 5,
    "cat": "Teknik Analiz",
    "body": """
<p>RSI (Relative Strength Index — Göreceli Güç Endeksi), bir varlığın son dönemde ne kadar hızlı hareket ettiğini ölçen bir <strong>momentum osilatörüdür.</strong> 0–100 arasında değer alır.</p>

<h2>Formül</h2>
<pre>RSI = 100 − (100 ÷ (1 + RS))
RS = Ortalama Yükselen Bar / Ortalama Düşen Bar (genellikle son 14 bar)</pre>

<h2>Temel Yorumlama</h2>
<ul>
  <li><strong>RSI &gt; 70:</strong> Aşırı alım bölgesi. Hisse kısa vadede pahalı, geri çekilme olabilir.</li>
  <li><strong>RSI &lt; 30:</strong> Aşırı satım bölgesi. Hisse kısa vadede ucuz, toparlanma olabilir.</li>
  <li><strong>RSI = 50:</strong> Nötr bölge, belirgin güç yok.</li>
</ul>
<p>⚠️ Dikkat: Güçlü bir trendde RSI uzun süre 70 üzerinde kalabilir. "Aşırı alım" tek başına satış sinyali değildir.</p>

<h2>RSI Uyuşmazlığı (Divergence)</h2>
<p>En güçlü RSI sinyallerinden biri:</p>
<ul>
  <li><strong>Bearish Divergence:</strong> Fiyat yeni yüksek yaparken RSI yeni yüksek yapamıyor → Trend zayıflıyor, dönüş yakın olabilir.</li>
  <li><strong>Bullish Divergence:</strong> Fiyat yeni düşük yaparken RSI yeni düşük yapamıyor → Düşüş momentumu azalıyor, toparlanma gelebilir.</li>
</ul>

<h2>BorsaPusula ile RSI Kombine Kullanım</h2>
<p>BorsaPusula AL sinyali verdiğinde, RSI 50–65 arasındaysa trend henüz erken aşamada demektir — potansiyel iyi. RSI 80'in üzerindeyken AL sinyali geliyorsa, trendin güçlü ama kısa vadeli geri çekilme riskinin yüksek olduğunu aklınızda bulundurun.</p>
"""
  },
  {
    "slug": "macd-gostergesi-nedir",
    "title": "MACD Göstergesi Nedir? Trend ve Momentum Kombinasyonu",
    "desc": "MACD nasıl hesaplanır, sinyal çizgisi ve histogram nasıl yorumlanır, hangi tuzaklara dikkat edilmeli?",
    "date": "2026-04-15",
    "mins": 5,
    "cat": "Teknik Analiz",
    "body": """
<p>MACD (Moving Average Convergence Divergence), iki EMA arasındaki farkı takip eden hem trend hem momentum göstergesidir. Gerald Appel tarafından geliştirilmiştir ve en yaygın kullanılan indikatörlerden biridir.</p>

<h2>MACD Hesabı</h2>
<pre>MACD Çizgisi = EMA(12) − EMA(26)
Sinyal Çizgisi = EMA(9) of MACD
Histogram = MACD − Sinyal</pre>

<h2>Sinyal Türleri</h2>
<ul>
  <li><strong>MACD ÜZERİNE geçişi:</strong> MACD çizgisi sinyali yukarı kesince AL işareti</li>
  <li><strong>MACD ALTİNA geçişi:</strong> MACD çizgisi sinyali aşağı kesince SAT işareti</li>
  <li><strong>Sıfır geçişi:</strong> MACD sıfırın üstüne çıkarsa güçlü yükseliş; altına inerse güçlü düşüş</li>
  <li><strong>Histogram küçülmesi:</strong> Momentum zayıflıyor — trend değişimi yaklaşıyor olabilir</li>
</ul>

<h2>MACD'nin Güçlü Yönleri</h2>
<p>Hem trend takibi hem momentum ölçümü yapar. Bu çift işlev sayesinde trendin hem yönünü hem de gücünü aynı anda değerlendirmek mümkündür.</p>

<h2>MACD'nin Zayıf Yönleri</h2>
<p>EMA tabanlı olduğu için gecikmeli bir göstergedir. Yatay piyasalarda çok fazla sahte sinyal üretir. BorsaPusula'da ADX filtresi bu sorunu kısmen çözer — ADX &lt; 25 ise trend yok demektir ve MACD sinyalleri güvenilir değildir.</p>
"""
  },
  {
    "slug": "hacim-analizi",
    "title": "Hacim Analizi: Fiyat Hareketi Kadar Önemli",
    "desc": "İşlem hacmi neden önemlidir, yükselen fiyat + düşen hacim ne anlama gelir, OBV ve VWAP nasıl kullanılır?",
    "date": "2026-04-16",
    "mins": 5,
    "cat": "Teknik Analiz",
    "body": """
<p>İşlem hacmi (volume), belirli bir zaman diliminde el değiştiren hisse adedidir. Fiyat hareketini doğrulayan veya çürüten en önemli araçtır. <em>"Fiyat ne yaparsa yapsın, hacim her şeyi söyler."</em></p>

<h2>Temel Kurallar</h2>
<ul>
  <li><strong>Yüksek fiyat + Yüksek hacim:</strong> Güçlü yükseliş, trend sağlam</li>
  <li><strong>Yüksek fiyat + Düşük hacim:</strong> Zayıf yükseliş, sürdürülemeyebilir</li>
  <li><strong>Düşük fiyat + Yüksek hacim:</strong> Güçlü satış baskısı</li>
  <li><strong>Düşük fiyat + Düşük hacim:</strong> İlgisiz düşüş, süreç yavaşlıyor</li>
</ul>

<h2>Kırılımlarda Hacim</h2>
<p>Bir direnç seviyesi yüksek hacimle kırılırsa "gerçek kırılım" sayılır. Düşük hacimle kırılıyorsa "sahte kırılım" riski yüksek — fiyat hızla geri dönebilir.</p>

<h2>OBV (On Balance Volume)</h2>
<p>OBV, yükselen günlerin hacmini ekleyip düşen günlerin hacmini çıkararak kümülatif bir değer üretir. OBV yeni yüksek yaparken fiyat yapmıyorsa, kurumsal alımlar var demektir — güçlü bullish sinyal.</p>

<h2>VWAP (Hacim Ağırlıklı Ortalama Fiyat)</h2>
<p>Gün içi işlemlerde kullanılan bir referans fiyatıdır. Kurumsal alıcılar genellikle VWAP altında almaya çalışır. Fiyat VWAP'ın üzerindeyse güçlü, altındaysa zayıf momentum var.</p>

<h2>BIST100'de Hacim Dikkat Noktaları</h2>
<p>Özellikle BIST30 dışındaki hisselerde (BIST100'ün daha küçük şirketleri) hacim düşük olabilir. Düşük hacimli hisselerde manipülasyon riski daha yüksektir. BorsaPusula'nın BIST100 odaklı olması bu risk faktörünü minimize eder.</p>
"""
  },
  {
    "slug": "fibonacci-seviyeleri",
    "title": "Fibonacci Geri Çekilme Seviyeleri Nedir?",
    "desc": "Fibonacci oranları borsa analizinde nasıl kullanılır? %38.2, %50, %61.8 seviyeleri neden önemlidir?",
    "date": "2026-04-17",
    "mins": 5,
    "cat": "Teknik Analiz",
    "body": """
<p>Fibonacci dizisi (0, 1, 1, 2, 3, 5, 8, 13, 21…), doğada sık karşılaşılan bir matematiksel örüntüdür. Teknik analistler bu oranların finansal piyasalarda da geçerli olduğunu gözlemlemişlerdir.</p>

<h2>Temel Fibonacci Oranları</h2>
<ul>
  <li><strong>%23.6:</strong> Zayıf geri çekilme</li>
  <li><strong>%38.2:</strong> Normal geri çekilme — sığ</li>
  <li><strong>%50.0:</strong> Kritik orta seviye (Fibonacci dizisinden değil ama yaygın kullanılır)</li>
  <li><strong>%61.8 (Altın Oran):</strong> En kritik geri çekilme seviyesi</li>
  <li><strong>%78.6:</strong> Derin geri çekilme</li>
</ul>

<h2>Nasıl Çizilir?</h2>
<p>Trend dip noktasından (0%) tepe noktasına (100%) bir çizgi çizilir. Fibonacci seviyeleri bu aralıkta otomatik olarak belirlenir. Fiyat bu seviyelerde destek bulabilir.</p>

<h2>%61.8 — Altın Oran</h2>
<p>Her Fibonacci sayısını bir öncekine bölünce elde edilen değer (örn. 21÷13 ≈ 1.618) altın orana yaklaşır. Bu oran, borsalarda en kritik geri çekilme seviyeleri için kullanılır. Birçok büyük yükseliş trendi %61.8 geri çekilmesinden sonra devam etmiştir.</p>

<h2>BorsaPusula ile Kullanımı</h2>
<p>Supertrend AL sinyali geldiğinde, fiyat aynı zamanda %38.2 veya %61.8 Fibonacci desteğindeyse sinyal daha güçlü bir "giriş noktası" işaret eder. İki farklı metodun aynı seviyeye işaret etmesi "confluance" (örtüşme) olarak adlandırılır.</p>
"""
  },
  {
    "slug": "bollinger-bantlari",
    "title": "Bollinger Bantları Nedir? Volatilite ile Fiyat İlişkisi",
    "desc": "Bollinger Bantları nasıl hesaplanır, bant sıkışması ne anlama gelir, AL/SAT sinyali olarak nasıl kullanılır?",
    "date": "2026-04-18",
    "mins": 4,
    "cat": "Teknik Analiz",
    "body": """
<p>Bollinger Bantları, John Bollinger tarafından geliştirilen ve fiyatın hareketli ortalama etrafındaki <strong>standart sapmasını</strong> görselleştiren bir volatilite göstergesidir.</p>

<h2>Yapısı</h2>
<ul>
  <li><strong>Orta Bant:</strong> SMA(20) — 20 günlük basit ortalama</li>
  <li><strong>Üst Bant:</strong> SMA(20) + 2 × Standart Sapma</li>
  <li><strong>Alt Bant:</strong> SMA(20) − 2 × Standart Sapma</li>
</ul>
<p>İstatistiksel olarak fiyatın yaklaşık <strong>%95'i</strong> bantlar arasında kalır.</p>

<h2>Bant Sıkışması (Squeeze)</h2>
<p>Bantlar daraldığında düşük volatilite dönemindeyiz demektir. Bu genellikle büyük bir hareketin habercisidir — yukarı mı aşağı mı olduğunu Bollinger bantları söylemez. ADX ve Supertrend yön için kullanılır.</p>

<h2>Temel Sinyaller</h2>
<ul>
  <li>Fiyat üst bandı aşarsa → Güçlü yükseliş (veya aşırı alım)</li>
  <li>Fiyat alt bandı kırarsa → Güçlü düşüş (veya aşırı satım)</li>
  <li>Fiyat orta banda döner → Ortalamaya dönüş (mean reversion) ticareti için fırsat</li>
</ul>

<h2>Kombinasyon Kullanımı</h2>
<p>Bollinger sıkışması + ADX düşük = büyük hareket hazırlığı. Bu noktada Supertrend yönü gösterene kadar beklemek akılcıdır. BorsaPusula'nın sistemi zaten bu mantıkla kurulmuştur: ADX yükselmeden sinyal üretilmez.</p>
"""
  },
  {
    "slug": "temettü-yatırımı",
    "title": "Temettü Yatırımı: Düzenli Gelir İçin BIST Hisseleri",
    "desc": "Temettü nedir, temettü verimi nasıl hesaplanır, hangi BIST100 şirketleri yüksek temettü dağıtır?",
    "date": "2026-04-19",
    "mins": 5,
    "cat": "Temel Analiz",
    "body": """
<p>Temettü (dividend), şirketin kârının bir bölümünü hissedarlara nakit olarak dağıtmasıdır. Temettü yatırımı, hisse fiyatı artışından bağımsız düzenli gelir elde etme stratejisidir.</p>

<h2>Temettü Verimi (Dividend Yield)</h2>
<pre>Temettü Verimi = (Hisse Başına Temettü ÷ Hisse Fiyatı) × 100</pre>
<p>Örnek: Hisse 50₺, yıllık temettü 5₺ → Verim = %10</p>

<h2>Neye Dikkat Edilmeli?</h2>
<ul>
  <li><strong>Sürdürülebilirlik:</strong> Şirket uzun vadede aynı temettüyü dağıtabilecek mi?</li>
  <li><strong>Ödeme Oranı (Payout Ratio):</strong> Kârın yüzde kaçı temettü olarak dağıtılıyor? %80 üzeri riskli.</li>
  <li><strong>Düzenlilik:</strong> Geçmişte temettü kesiyor mu?</li>
  <li><strong>Büyüme:</strong> Çok yüksek temettü verimli bir şirket büyümeye yatırım yapmıyordur.</li>
</ul>

<h2>BIST100'de Temettü Kültürü</h2>
<p>Türk borsasında holding şirketleri (KCHOL, SAHOL), telekomünikasyon (TCELL) ve petrol/kimya (TUPRS, PETKM) sektörleri tarihsel olarak temettü dağıtan şirketler arasında öne çıkar. Ancak yüksek enflasyon dönemlerinde şirketler temettü yerine yatırıma yönelebilir.</p>

<h2>Temettü + Sinyal Kombinasyonu</h2>
<p>Yüksek temettü verimine sahip bir hisse <em>aynı zamanda</em> AL sinyali veriyorsa hem temettü geliri hem de fiyat artışı potansiyeli bir arada sunulmuş demektir. BorsaPusula'nın temel analiz bölümünde temettü verimi de gösterilir.</p>
"""
  },
  {
    "slug": "enflasyon-ve-borsa",
    "title": "Enflasyon ve Borsa: Yüksek Enflasyonda Yatırım",
    "desc": "Yüksek enflasyon döneminde borsa nasıl davranır, hangi sektörler fırsat sunar, reel getiri nasıl hesaplanır?",
    "date": "2026-04-20",
    "mins": 6,
    "cat": "Makro Ekonomi",
    "body": """
<p>Türkiye son yıllarda yüksek enflasyonla yaşayan önemli ekonomilerden biri. Bu durum yatırımcılar için hem tehdit hem de fırsat yaratıyor. Peki enflasyon döneminde borsa nasıl davranır?</p>

<h2>Enflasyon-Borsa İlişkisi</h2>
<p>Genel kural: Hisse senetleri enflasyona karşı <em>kısmen</em> koruma sağlar çünkü şirketler fiyatlarını artırabilir ve kârları nominal olarak büyüyebilir. Ancak gerçek tablolar daha karmaşık:</p>
<ul>
  <li>Yüksek faiz → Discount rate artar → Hisse değerlemeleri düşer</li>
  <li>Maliyet enflasyonu → Marjlar sıkışır → Kârlılık azalır</li>
  <li>Fiyatı geçirebilen şirketler → Enflasyona karşı dirençli</li>
</ul>

<h2>Enflasyona Karşı Dirençli Sektörler</h2>
<ul>
  <li><strong>Enerji ve Hammadde:</strong> Fiyat artışından direkt yarar (TUPRS, EREGL)</li>
  <li><strong>Savunma Sanayii:</strong> Döviz bazlı sözleşmeler (ASELS)</li>
  <li><strong>Bankacılık:</strong> Yüksek faizde net faiz marjı genişler (kısmen)</li>
  <li><strong>Perakende (temkinli):</strong> Fiyat geçirebilen büyük zincirler</li>
</ul>

<h2>Reel Getiri Hesabı</h2>
<pre>Reel Getiri = ((1 + Nominal Getiri) ÷ (1 + Enflasyon)) − 1</pre>
<p>Hisse %80 artarken enflasyon %65 ise reel getiri yaklaşık %9'dur. Nominal rakamlar yanıltıcı olabilir.</p>

<h2>Döviz Riski ve BIST</h2>
<p>TL'nin değer kaybettiği dönemlerde BIST100 TL bazında yükselirken USD bazında düşebilir. Yabancı yatırımcılar dolarlı getiriyi baz alır. Türk yatırımcılar için TL bazlı hesap yapılır ama reel satın alma gücüne dikkat edilmelidir.</p>
"""
  },
  {
    "slug": "borsa-sozlugu",
    "title": "Borsa Sözlüğü: En Sık Kullanılan 40 Terim",
    "desc": "Borsa yatırımcılarının bilmesi gereken temel terimlerin Türkçe açıklamaları. Hisse, endeks, lot, emir türleri ve daha fazlası.",
    "date": "2026-04-21",
    "mins": 8,
    "cat": "Temel Kavramlar",
    "body": """
<p>Borsaya yeni başlayanlar için en zorlu engellerden biri terminolojidir. Bu sözlük, en sık kullanılan 40 terimi sade Türkçeyle açıklar.</p>

<h2>A–E</h2>
<ul>
  <li><strong>ADX:</strong> Trend gücü ölçen gösterge. 25+ güçlü trend.</li>
  <li><strong>AL (Long):</strong> Fiyat yükselir beklentisiyle hisse satın alma.</li>
  <li><strong>ATR:</strong> Average True Range — ortalama fiyat dalgalanma aralığı.</li>
  <li><strong>Bant:</strong> Supertrend veya Bollinger gibi göstergelerdeki fiyat kanalı.</li>
  <li><strong>Bear Market:</strong> %20+ düşüş yaşanan piyasa koşulları.</li>
  <li><strong>Bull Market:</strong> %20+ yükseliş yaşanan piyasa koşulları.</li>
  <li><strong>Crossover (Kesişim):</strong> İki göstergenin birbirini kesmesi.</li>
  <li><strong>Drawdown:</strong> Tepe değerden çukur değere düşüş miktarı.</li>
  <li><strong>EMA:</strong> Üstel Hareketli Ortalama — son fiyatlara daha fazla ağırlık verir.</li>
  <li><strong>Endeks:</strong> Belirli hisse grubunun ağırlıklı ortalaması (BIST100 gibi).</li>
  <li><strong>EPS:</strong> Hisse Başına Kazanç. Şirket kârı ÷ hisse adedi.</li>
</ul>

<h2>F–L</h2>
<ul>
  <li><strong>F/K (PE):</strong> Fiyat/Kazanç oranı.</li>
  <li><strong>Fibonacci:</strong> Matematiksel oranlar tabanlı destek/direnç seviyeleri.</li>
  <li><strong>Hacim:</strong> Belirli sürede el değiştiren hisse adedi.</li>
  <li><strong>Kaldıraç:</strong> Sahip olunanın üzerinde işlem yapma imkânı. Yüksek risk!</li>
  <li><strong>KAP:</strong> Kamuyu Aydınlatma Platformu. Şirket açıklamaları.</li>
  <li><strong>Lot:</strong> Borsa İstanbul'da 1 lot = 1 hisse.</li>
  <li><strong>Likidite:</strong> Bir varlığın kolayca alınıp satılabilme özelliği.</li>
</ul>

<h2>M–R</h2>
<ul>
  <li><strong>MACD:</strong> Trend + momentum göstergesi. İki EMA farkı.</li>
  <li><strong>Momentum:</strong> Fiyat hareketinin hızı ve yönü.</li>
  <li><strong>Osilatör:</strong> Belirli aralıkta salınan gösterge (RSI 0-100 gibi).</li>
  <li><strong>Piyasa Değeri:</strong> Hisse fiyatı × toplam hisse adedi.</li>
  <li><strong>Pivot Noktası:</strong> Dün kapanışından hesaplanan destek/direnç seviyeleri.</li>
  <li><strong>PD/DD (PB):</strong> Piyasa Değeri / Defter Değeri.</li>
  <li><strong>RSI:</strong> Momentum göstergesi. 30 aşırı satım, 70 aşırı alım.</li>
</ul>

<h2>S–Z</h2>
<ul>
  <li><strong>SAT (Short):</strong> Düşüş beklentisiyle pozisyon almak.</li>
  <li><strong>SMA:</strong> Basit Hareketli Ortalama.</li>
  <li><strong>Stop Loss:</strong> Zarar durdurma emri. Belirli fiyatın altında otomatik satış.</li>
  <li><strong>Supertrend:</strong> ATR tabanlı trend takip göstergesi.</li>
  <li><strong>Take Profit:</strong> Kâr realizasyonu emri.</li>
  <li><strong>Temettü:</strong> Şirketin kârından hissedarlara yapılan nakit ödeme.</li>
  <li><strong>Trend:</strong> Fiyatın genel hareket yönü.</li>
  <li><strong>Volatilite:</strong> Fiyat dalgalanma şiddeti.</li>
  <li><strong>VWAP:</strong> Hacim ağırlıklı ortalama fiyat.</li>
  <li><strong>Whipsaw:</strong> Sahte kırılım — fiyat direnç/destek kırar sonra geri döner.</li>
</ul>
"""
  },
  {
    "slug": "sinyal-sistemi-nasil-calisir",
    "title": "BorsaPusula Sinyal Sistemi Nasıl Çalışır?",
    "desc": "BorsaPusula'nın üçlü filtre sistemi, haftalık trend gate, sinyal onayı ve piyasa barometresi nasıl çalışır?",
    "date": "2026-04-22",
    "mins": 6,
    "cat": "BorsaPusula",
    "body": """
<p>BorsaPusula, 90 BIST100 hissesini her gün algoritmik olarak analiz eder ve her hisse için AL, SAT veya BEKLE kararı üretir. Bu makalede bu sistemin arka planını anlıyoruz.</p>

<h2>Üçlü Filtre Mantığı</h2>
<p>Tek bir gösterge sahte sinyal üretebilir. Üç göstergenin aynı anda aynı yönü göstermesi, yanlış sinyal olasılığını dramatik şekilde düşürür. BorsaPusula'nın üç kriteri:</p>
<ol>
  <li><strong>Supertrend(10,3):</strong> Trend yönü ve dinamik destek/direnç</li>
  <li><strong>ADX ≥ 25 + DI+/DI−:</strong> Trendin güçlü olduğunu ve yönünü doğrulama</li>
  <li><strong>EMA12 &gt; EMA99 (veya tersi):</strong> Orta-uzun vadeli trendin teyidi</li>
</ol>

<h2>Haftalık Trend Gate</h2>
<p>Günlük sinyaller, haftalık EMA20 yönüyle filtrelenir. Haftalık düşüş trendindeyken günlük AL sinyali engellenir. Bu filtre, yükselen trendin "büyük resmini" kaçırmamayı sağlar.</p>

<h2>Sinyal Onayı (3 Bar Kuralı)</h2>
<p>İlk gün oluşan sinyal "ham sinyal"dir. 3 gün boyunca aynı kalan sinyal "onaylı" sayılır. BorsaPusula hisse sayfalarında kaç gündür devam ettiği gösterilir.</p>

<h2>Piyasa Barometresi</h2>
<p><a href="/ozet">Günlük Özet</a> sayfasındaki barometresi tüm piyasanın anlık durumunu gösterir. AL hisselerinin oranı %50'nin üzerindeyse genel trend yukarı; %30'un altındaysa savunmacı bir duruş önerilir.</p>

<h2>Veri Kaynağı ve Güncelleme Sıklığı</h2>
<p>Tüm fiyat verileri Yahoo Finance (yfinance) API'sından alınır. Günlük barlar (2 yıl geçmiş) ve haftalık barlar (1 yıl) kullanılır. Sinyaller <strong>15 dakikada bir</strong> güncellenir. Canlı fiyatlar 30 saniyede bir SSE ile yayınlanır.</p>
"""
  },
  {
    "slug": "bist100-sektorler",
    "title": "BIST100 Sektörleri: Hangi Hisse Hangi Sektörde?",
    "desc": "Bankacılık, enerji, sanayi, teknoloji ve diğer BIST100 sektörlerinin özellikleri ve başlıca şirketleri.",
    "date": "2026-04-23",
    "mins": 6,
    "cat": "Temel Kavramlar",
    "body": """
<p>BIST100 tek bir endeks olsa da içinde çok farklı sektörlerden şirketler bulunur. Sektörel analiz, piyasayı daha iyi anlamayı ve çeşitlendirilmiş bir portföy kurmayı sağlar.</p>

<h2>Bankacılık ve Finans</h2>
<p><strong>Başlıca hisseler:</strong> AKBNK, GARAN, ISCTR, VAKBN, YKBNK, HALKB, ALBRK</p>
<p>BIST100'ün en ağırlıklı sektörü. Faiz oranı değişimlerine, enflasyona ve ekonomik döngülere duyarlı. Yüksek faiz döneminde net faiz marjı genişleyebilir ama takipteki kredi riski artar.</p>

<h2>Enerji ve Petrokimya</h2>
<p><strong>Başlıca hisseler:</strong> TUPRS, PETKM, AKSEN, ZOREN, CWENE, ENJSA</p>
<p>Ham petrol fiyatları, döviz kuru ve elektrik tarifeleri bu sektörü doğrudan etkiler. Yenilenebilir enerji şirketleri (CWENE, ENJSA) uzun vadeli büyüme potansiyeli taşır.</p>

<h2>Sanayi ve Savunma</h2>
<p><strong>Başlıca hisseler:</strong> ASELS, FROTO, TOASO, TTRAK, OTKAR, ASUZU</p>
<p>İhracat bazlı şirketler döviz geliri elde eder ve TL değer kaybından faydalanır. Savunma sanayii (ASELS, ASELSAN) uzun vadeli Ar-Ge yatırımlarıyla değer yaratır.</p>

<h2>Holding ve Yatırım</h2>
<p><strong>Başlıca hisseler:</strong> KCHOL, SAHOL, GLYHO, NTHOL, AGHOL</p>
<p>Holdinglerin değeri portföylerindeki şirketlerin toplamıdır. Genellikle holding iskontoluyla işlem görürler — değerleme yaparken "şirketin piyasa değeri, elindeki hisselerin değerinden az mı?" sorusunu sormak gerekir.</p>

<h2>Perakende ve Gıda</h2>
<p><strong>Başlıca hisseler:</strong> BIMAS, MGROS, SOKM, ULKER, TATGD</p>
<p>Zorunlu tüketim (staples) kategorisi. Ekonomik durgunlukta görece dayanıklıdır. Fiyat geçirme gücü enflasyon döneminde kritiktir.</p>

<h2>Teknoloji ve Telekomünikasyon</h2>
<p><strong>Başlıca hisseler:</strong> TCELL, TTKOM, LOGO, NETAS, SELEC</p>
<p>Türk teknoloji ekosistemi gelişiyor. Telekomünikasyon şirketleri nispeten savunmacı; yazılım şirketleri (LOGO) büyüme potansiyeli yüksek.</p>

<h2>BorsaPusula'da Sektör Filtresi</h2>
<p>Ana sayfada sektör butonlarıyla yalnızca ilgilendiğiniz sektörün hisselerini görebilirsiniz. Hangi sektörün kaç AL sinyali verdiğini karşılaştırarak güçlü sektörleri tespit edebilirsiniz.</p>
"""
  },
  {
    "slug": "yeni-baslayanlar-icin-borsa",
    "title": "Yeni Başlayanlar İçin Borsa: 10 Temel Kural",
    "desc": "Borsaya yeni başlıyorsanız bilmeniz gereken 10 temel kural. Duygusal kararlardan kaçının, disiplinli bir sistem kurun.",
    "date": "2026-04-24",
    "mins": 6,
    "cat": "Temel Kavramlar",
    "body": """
<p>Her yıl binlerce kişi borsaya ilk kez giriyor. Bunların önemli bir kısmı ilk aylarında kayıp yaşayarak çıkıyor. Bu 10 kural, o hataların büyük bölümünü önler.</p>

<h2>1. Kaybetmeyi Göze Alabileceğiniz Parayla Başlayın</h2>
<p>Kiranızı, acil fonunuzu veya kısa vadeli ihtiyaçlarınız için ayırdığınız parayı borsaya koymayın. Piyasa size kötü timing sunabilir; o süre boyunca psikolojik baskı altında iyi karar vermek zorlaşır.</p>

<h2>2. Önce Öğrenin, Sonra Girin</h2>
<p>Birkaç makale okuyarak veya sosyal medyada haber takip ederek öğrenilmez. Teknik analiz, temel analiz ve risk yönetiminin temellerini kavramadan ciddi para yatırmayın.</p>

<h2>3. Stop Loss Kullanın, Her Zaman</h2>
<p>"Bu sefer düzelir" düşüncesi en büyük tuzaktır. Stop loss kullanmayan yatırımcılar küçük kayıpları büyük felaketlere dönüştürür.</p>

<h2>4. Haber Peşinden Koşmayın</h2>
<p>Sosyal medyada "bu hisse patlayacak" postları gördüğünüzde genellikle bu bilgi zaten fiyatlanmıştır. Haberi gördüğünüzde girenler çoğunlukla en tepeden alır.</p>

<h2>5. Tek Hisseye Yatırım Yapmayın</h2>
<p>En iyi analistler bile yanılır. Portföyünüzü en az 5-8 farklı hisseye dağıtın ve farklı sektörler seçin.</p>

<h2>6. Sistematik Olun</h2>
<p>Her işlem için önceden kurallar belirleyin: Neden girdim? Nerede çıkarım (stop)? Kâr hedefim ne? Bunları yazmadan pozisyon açmayın.</p>

<h2>7. Kaldıraç Kullanmayın (Başlangıçta)</h2>
<p>Kaldıraçlı işlemler (Viop, türev) hem kazancı hem kaybı büyütür. Tecrübeli olmadan kaldıraç kullanmak sermayeyi çok hızlı eritir.</p>

<h2>8. Günlük Fiyat Takibini Sınırlandırın</h2>
<p>Ekrana sürekli bakmak duygusal kararları tetikler. Günlük grafiklere yönelik sinyal sistemi kullanıyorsanız, güncellemeyi sabah bir kez kontrol etmek yeterlidir.</p>

<h2>9. Kaybeden İşlemlerden Öğrenin</h2>
<p>Her kaybı not edin: Ne oldu, neden yanlış oldu, bir daha ne yapardım? Bu "işlem günlüğü" zamanla en değerli öğrenme kaynağınız olur.</p>

<h2>10. Sabır En Büyük Silah</h2>
<p>Çoğu kazanan işlem, bir sinyal oluştuğunda hemen almak değil, doğru kurulumu <em>beklemekten</em> gelir. BEKLE sinyali de bir sinyaldir — "henüz hazır değil, izle" demektir.</p>
"""
  },
  {
    "slug": "borsa-psikolojisi",
    "title": "Borsa Psikolojisi: Duygular Neden En Büyük Düşmanınız?",
    "desc": "Korku, açgözlülük ve FOMO borsada nasıl zarar verir? Davranışsal finans perspektifinden yatırımcı hataları.",
    "date": "2026-04-25",
    "mins": 6,
    "cat": "Risk Yönetimi",
    "body": """
<p>Teknik analiz bilgisi, iyi bir strateji ve disiplin — bunların hepsi tek bir düşman tarafından çökertilir: <strong>duygular.</strong> Davranışsal finans araştırmaları, yatırımcıların sistematik olarak duygusal hatalar yaptığını gösteriyor.</p>

<h2>Korku ve Açgözlülük Döngüsü</h2>
<p>Piyasa yükselirken: "Ben neden girmedim? Kaçırıyorum!" → Tepeye yakın alış<br>
Piyasa düşerken: "Bir daha asla borsa!" → Dibe yakın satış<br>
Bu döngü, alıcıları tepede ve satıcıları dipte toplar. Kurumsal oyuncular bu psikolojiden faydalanır.</p>

<h2>FOMO (Kaçırma Korkusu)</h2>
<p>Sosyal medyada biri %200 kazandığını paylaşınca irrasyonel alım kararları tetiklenir. FOMO ile alınan pozisyonlarda analiz değil, his hakimdir. Sonuç genellikle felaket olur.</p>

<h2>Kayıptan Kaçınma (Loss Aversion)</h2>
<p>Nobel ekonomisti Kahneman'ın araştırmaları, insanların kaybın acısını kazancın sevincinin yaklaşık 2 katı hissetttiğini gösteriyor. Bu yüzden yatırımcılar zarar eden pozisyonları kapatmaz — "zarar realize olmadı" rasyonalizasyonu ile bekler.</p>

<h2>Geri Görüş Yanılgısı (Hindsight Bias)</h2>
<p>"Bunu baştan biliyordum zaten" hissi, gelecekteki kararları abartılı özgüvenle almaya yol açar. Geçmişteki başarı şansın mı yoksa becerinin mi ürünüydü, bunu sorgulamak gerekir.</p>

<h2>Algoritmik Sistemin Psikolojik Değeri</h2>
<p>BorsaPusula gibi kural tabanlı sistemler duyguları denklemden çıkarır. "Hisse düşüyor, çıkmalı mıyım?" sorusunun cevabı nettir: Supertrend SAT'a geçmedikçe sistem AL der. Bu netlik paniği önler.</p>

<h2>Pratik Çözümler</h2>
<ul>
  <li>İşlem öncesi "İşlem Planı" yazın (giriş, stop, hedef)</li>
  <li>Sosyal medyadan öneri almayın, kendiniz analiz yapın</li>
  <li>Portföyünüzü saatte bir değil günde bir kez kontrol edin</li>
  <li>Kaybeden işlemleri hemen not alın — ertelemek inkâra döner</li>
</ul>
"""
  },
  {
    "slug": "supertrend-vs-macd",
    "title": "Supertrend vs MACD: Hangi Gösterge Ne Zaman Daha İyi?",
    "desc": "İki popüler trend göstergesini karşılaştırıyoruz. Supertrend ve MACD'nin güçlü ve zayıf yönleri.",
    "date": "2026-04-26",
    "mins": 5,
    "cat": "Teknik Analiz",
    "body": """
<p>Hem Supertrend hem MACD trend takip göstergeleridir ancak çok farklı çalışırlar. Hangi piyasa koşullarında hangisi daha iyi performans gösterir?</p>

<h2>Temel Farklılıklar</h2>
<table style="width:100%;border-collapse:collapse;margin:12px 0">
  <tr style="background:#21262d"><th style="padding:8px;text-align:left">Özellik</th><th style="padding:8px;text-align:left">Supertrend</th><th style="padding:8px;text-align:left">MACD</th></tr>
  <tr><td style="padding:8px;border-top:1px solid #30363d">Taban</td><td style="padding:8px;border-top:1px solid #30363d">ATR (volatilite)</td><td style="padding:8px;border-top:1px solid #30363d">EMA farkı</td></tr>
  <tr><td style="padding:8px;border-top:1px solid #30363d">Çıktı</td><td style="padding:8px;border-top:1px solid #30363d">Fiyat üzerinde çizgi</td><td style="padding:8px;border-top:1px solid #30363d">Osilatör + histogram</td></tr>
  <tr><td style="padding:8px;border-top:1px solid #30363d">Stop Loss</td><td style="padding:8px;border-top:1px solid #30363d">Doğrudan band seviyeleri</td><td style="padding:8px;border-top:1px solid #30363d">Yoktur</td></tr>
  <tr><td style="padding:8px;border-top:1px solid #30363d">Volatilite adaptasyonu</td><td style="padding:8px;border-top:1px solid #30363d">✅ Evet (ATR ile)</td><td style="padding:8px;border-top:1px solid #30363d">❌ Hayır</td></tr>
  <tr><td style="padding:8px;border-top:1px solid #30363d">Divergence</td><td style="padding:8px;border-top:1px solid #30363d">❌ Hayır</td><td style="padding:8px;border-top:1px solid #30363d">✅ Evet</td></tr>
</table>

<h2>Supertrend'in Avantajı</h2>
<p>Volatiliteye göre otomatik adapte olur. Düşük volatilite döneminde bantlar daralır, yüksek volatilitede genişler. Bu sayede farklı piyasa koşullarında aynı parametreler kullanılabilir.</p>

<h2>MACD'nin Avantajı</h2>
<p>Divergence (uyuşmazlık) tespiti yapabilir. Fiyat yeni yüksek yaparken MACD yapamıyorsa, bu trend zayıflama işareti olarak okunur. Supertrend bunu yapamaz.</p>

<h2>Neden Supertrend + ADX?</h2>
<p>BorsaPusula'nın ADX filtresi, MACD'nin divergence değerinin bir bölümünü karşılar. ADX düşükse trend güçlü değildir — bu bilgi MACD divergence'a benzer bir uyarı işlevi görür. İkisinin de güçlü yönlerini birleştiren bir yaklaşımdır.</p>
"""
  },
  {
    "slug": "hisse-secim-kriterleri",
    "title": "Hangi Hisseyi Seçmeli? Teknik + Temel Kombinasyon",
    "desc": "Birden fazla AL sinyali olan hisseler arasında nasıl seçim yapılır? Teknik ve temel kriterleri birleştiren bir yaklaşım.",
    "date": "2026-04-27",
    "mins": 6,
    "cat": "Strateji",
    "body": """
<p>BorsaPusula'da aynı anda onlarca hisse AL sinyali verebilir. Bunların hepsine girilmez — portföy kapasitesi sınırlıdır. Peki nasıl seçim yapılır?</p>

<h2>Teknik Puanlama (1-3 puan)</h2>
<ul>
  <li><strong>+1:</strong> Sinyal 3+ gündür devam ediyor (onaylı)</li>
  <li><strong>+1:</strong> ADX 35'in üzerinde (çok güçlü trend)</li>
  <li><strong>+1:</strong> Haftalık ve aylık grafik de AL yönünde</li>
</ul>

<h2>Temel Puanlama (1-3 puan)</h2>
<ul>
  <li><strong>+1:</strong> F/K sektör ortalamasının altında</li>
  <li><strong>+1:</strong> Pozitif ROE (öz kaynak kârlılığı)</li>
  <li><strong>+1:</strong> Temettü verimi > %3</li>
</ul>

<h2>Risk Puanlaması (−1 ile −3)</h2>
<ul>
  <li><strong>−1:</strong> Yüksek borç/öz kaynak oranı</li>
  <li><strong>−1:</strong> Son çeyrekte kâr düşüşü</li>
  <li><strong>−2:</strong> Sektör genel baskı altında (sektör barometresi negatif)</li>
</ul>

<h2>Piyasa Bağlamı</h2>
<p><a href="/ozet">Sinyal Özeti</a> sayfasındaki barometresi kontrol edin. AL oranı %60 üzerindeyse piyasa geneli güçlü — daha agresif girilir. %30 altındaysa piyasa zayıf — yalnızca en güçlü sinyaller değerlendirilir.</p>

<h2>Pratik Örnek</h2>
<p>Diyelim ki THYAO ve ASELS her ikisi de AL sinyali veriyor:</p>
<ul>
  <li>THYAO: Sinyal 5 gündür, ADX=38, F/K makul → Skor: +5</li>
  <li>ASELS: Sinyal bugün oluştu, ADX=22 → Skor: +1</li>
</ul>
<p>THYAO açıkça daha güçlü bir kurulum sunuyor.</p>
"""
  },
]

ARTICLES_BY_SLUG = {a["slug"]: a for a in ARTICLES}
CATEGORIES = sorted(set(a["cat"] for a in ARTICLES))
