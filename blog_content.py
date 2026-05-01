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
""",
    "faqs": [
      {
        "q": "BIST100 ile BIST30 arasındaki fark nedir?",
        "a": "BIST100, Borsa İstanbul'daki en likit 100 hisseyi kapsar. BIST30 ise bunların en büyük 30'unu içerir ve vadeli işlemler (VİOP) için temel endeks olarak kullanılır. BIST30 daha dar ama daha likit bir endekstir."
      },
      {
        "q": "BIST100 endeksi ne zaman güncellenir?",
        "a": "Borsa İstanbul, endeks bileşenlerini her yıl Mart ve Eylül aylarında günceller. Yeterli işlem hacmini veya piyasa değerini koruyamayan hisseler endeksten çıkarılır, yeni şirketler dahil edilir."
      },
      {
        "q": "BorsaPusula'da kaç BIST100 hissesi takip ediliyor?",
        "a": "BorsaPusula, BIST100 bünyesindeki 90'dan fazla hisse için algoritmik Supertrend + ADX + EMA teknik analiz sinyallerini günlük olarak hesaplar ve ücretsiz sunar."
      }
    ]
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
""",
    "faqs": [
      {
        "q": "Supertrend indikatörü ne işe yarar?",
        "a": "Supertrend, fiyatın trend yönünü ve olası dönüş noktalarını ATR tabanlı bantlarla gösterir. Yeşil bant fiyatın altında ise yükseliş trendi, kırmızı bant üstündeyse düşüş trendi sinyali verir."
      },
      {
        "q": "BorsaPusula'da Supertrend hangi parametrelerle kullanılır?",
        "a": "BorsaPusula'da Supertrend(10,3) parametreleri kullanılır: 10 günlük ATR periyodu ve 3 çarpan. Bu ayarlar BIST100 hisseleri için optimize edilmiştir."
      },
      {
        "q": "Supertrend tek başına yeterli mi?",
        "a": "Hayır. BorsaPusula sinyali için Supertrend'e ek olarak ADX≥25 (güçlü trend onayı) ve EMA12/EMA99 (yön filtresi) koşullarının üçü birden sağlanmalıdır. Yalnız kullanıldığında yatay piyasalarda çok fazla sahte sinyal üretir."
      }
    ]
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
""",
    "faqs": [
      {
        "q": "ADX değeri ne anlama gelir?",
        "a": "ADX (Average Directional Index), trendin gücünü 0-100 arası bir skala ile ölçer. 0-25 arası zayıf veya yok sayılabilir trend, 25-50 orta güçlü trend, 50+ güçlü trend anlamına gelir. Yön bilgisi vermez; yalnızca trendin ne kadar güçlü olduğunu gösterir."
      },
      {
        "q": "BorsaPusula neden ADX ≥ 25 şartı koyuyor?",
        "a": "ADX < 25 ise piyasa yatay seyrediyordur ve trend indikatörleri (Supertrend, EMA) çok sayıda sahte sinyal üretir. BorsaPusula, ADX ≥ 25 şartıyla yalnızca gerçek trend başlangıçlarında sinyal vererek başarı oranını artırır."
      },
      {
        "q": "DI+ ve DI- ne işe yarar?",
        "a": "DI+ (yeşil) alış baskısını, DI- (kırmızı) ise satış baskısını gösterir. DI+ > DI- ise yükseliş yönü hâkim, DI- > DI+ ise düşüş yönü hâkimdir. ADX bu iki değerin mutlak farkından türetilir."
      }
    ]
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
""",
    "faqs": [
      {"q": "EMA ile SMA arasındaki temel fark nedir?", "a": "EMA (Üstel Hareketli Ortalama), son fiyatlara daha fazla ağırlık verirken SMA (Basit Hareketli Ortalama) tüm periyotlara eşit ağırlık verir. Bu nedenle EMA fiyat değişimlerine daha hızlı tepki verir."},
      {"q": "BorsaPusula neden EMA12 ve EMA99 kullanıyor?", "a": "EMA12 yaklaşık 2.5 haftalık kısa dönem momentumu, EMA99 ise 5 aylık uzun dönem trendi temsil eder. Bu iki ortalamanın kesişimi, kısa dönem ivmesinin uzun dönem trendi geçtiğini gösterir."},
      {"q": "EMA kesişimi tek başına yeterli bir sinyal midir?", "a": "Hayır. EMA kesişimleri gecikmeli sinyal üretir ve yatay piyasalarda sık sık sahte kesişim yaşanır. BorsaPusula üçüncü teyit katmanı olarak kullanır: Supertrend + ADX + EMA üçü aynı anda teyit vermelidir."}
    ],
    "related_tickers": ['AKBNK', 'GARAN', 'THYAO']
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
""",
    "faqs": [
      {"q": "Teknik analiz mi temel analiz mi daha önemlidir?", "a": "İkisi birbirini tamamlar. Temel analiz 'hangi hisseye' gireceğinizi belirler; teknik analiz 'ne zaman' gireceğinizi söyler. BorsaPusula teknik sinyaller üretir ancak temel verilerle birlikte değerlendirilmesi tavsiye edilir."},
      {"q": "Teknik analiz geçmişe mi geleceğe mi bakar?", "a": "Teknik analiz geçmiş fiyat ve hacim verilerini inceleyerek geleceğe dair olasılıksal tahminler yapar. Tarih tekerrür eder prensibi üzerine kuruludur ancak kesin öngörü değildir."},
      {"q": "BorsaPusula hangi teknik göstergeleri kullanıyor?", "a": "BorsaPusula üçlü filtre sistemi kullanır: Supertrend (ATR tabanlı trend yönü), ADX ≥ 25 (trend gücü doğrulaması) ve EMA12/EMA99 kesişimi (orta-uzun vadeli trend teyidi). Üçü aynı anda AL yönünde olduğunda sinyal verilir."}
    ],
    "related_tickers": ['AKBNK', 'ASELS', 'THYAO']
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
""",
    "faqs": [
      {"q": "Stop loss nedir ve neden kullanılmalıdır?", "a": "Stop loss, hisse belirlenen fiyat seviyesinin altına düşünce pozisyonu otomatik kapatan emirdir. Küçük kayıpları keserek büyük felaketlerin önüne geçer ve duygusal karar vermeyi engeller."},
      {"q": "BorsaPusula stop loss seviyesi nasıl hesaplanır?", "a": "BorsaPusula her AL sinyali için ATR tabanlı stop loss seviyesi hesaplar. Bu seviye Supertrend bandıyla örtüşür. Fiyat bu seviyenin altına düştüğünde sistem SAT sinyaline geçer."},
      {"q": "Stop loss seviyesini ne kadar geniş tutmalıyım?", "a": "Çok dar stop erken durdurur, çok geniş stop riski artırır. BorsaPusula ATR bazlı stop volatiliteye göre otomatik ayarlanır. Swing işlemler için genellikle giriş fiyatının %5-10 altı uygundur."}
    ],
    "related_tickers": ['AKBNK', 'GARAN', 'THYAO']
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
""",
    "faqs": [
      {"q": "Portföyde kaç hisse bulunmalıdır?", "a": "Yeterli çeşitlendirme için genellikle 8-15 hisse önerilir. Çok az hisse riski konsantre eder; çok fazla hisse ise takibi zorlaştırır ve getiriyi ortalamaya yaklaştırır. Farklı sektörlerden seçim yapılması önemlidir."},
      {"q": "Her işlemde portföyün yüzde kaçını riske etmeliyim?", "a": "Profesyonel risk yönetiminde tek işlemde toplam portföyün maksimum %1-2'si riske edilir. Bu kural, 50 arka arkaya kayıp yaşasanız bile hesabınızın büyük bölümünü korumanızı sağlar."},
      {"q": "Sektör çeşitlendirmesi neden önemlidir?", "a": "Tek sektördeki hisseler aynı makroekonomik faktörlerden etkilenir. Bankacılık + sanayi + perakende gibi bağımsız sektörlere dağılmak sektörel şoklardan korunma sağlar."}
    ],
    "related_tickers": ['AKBNK', 'ASELS', 'EREGL']
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
""",
    "faqs": [
      {"q": "AL sinyali ne anlama gelir?", "a": "AL sinyali, Supertrend yükseliş bandında, ADX 25 üzerinde ve EMA12 > EMA99 koşullarının tamamının sağlandığını gösterir. Hissenin güçlü yükseliş trendinde olduğu anlamına gelir, ancak her AL sinyali yatırım tavsiyesi değildir."},
      {"q": "Sinyal kaç gündür devam ediyor bilgisi önemli midir?", "a": "Evet, çok önemlidir. 3+ gündür devam eden onaylı sinyal, ilk günkü ham sinyalden çok daha güvenilirdir. Onaylı sinyal trendin gerçek ve sürdürülebilir olduğunu gösterir."},
      {"q": "BEKLE sinyalinde ne yapmalıyım?", "a": "BEKLE sinyali ne alın ne satın demektir, trend henüz belirgin değil. Mevcut pozisyonunuz varsa tutmaya devam edebilirsiniz. Yeni pozisyon için AL sinyalini beklemek gereksiz risk almaktan daha akıllıcadır."}
    ],
    "related_tickers": ['AKBNK', 'GARAN', 'ASELS', 'THYAO']
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
""",
    "faqs": [
      {"q": "Haftalık trend filtresi neden kullanılır?", "a": "Günlük sinyaller kısa vadeli gürültüye duyarlıdır. Haftalık EMA20 yönüyle filtrelemek büyük trende karşı giriş yapmayı önler ve sahte sinyal sayısını önemli ölçüde azaltır."},
      {"q": "Çoklu zaman dilimi analizi nedir?", "a": "Farklı periyotlardaki trendlerin aynı anda değerlendirilmesidir. Üst zaman dilimi trend yönü belirler, alt zaman dilimi giriş zamanlar. BorsaPusula haftalık trendin desteğini alan günlük sinyalleri tercih eder."},
      {"q": "MTF analizi BorsaPusula'da nasıl görülür?", "a": "Her hisse sayfasında H4, Günlük, Haftalık ve Aylık zaman dilimlerini gösteren MTF analizi bulunur. Tüm periyotlarda AL gösteren hisseler en güçlü adaylardır."}
    ],
    "related_tickers": ['AKBNK', 'ASELS']
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
""",
    "faqs": [
      {"q": "F/K oranı kaç olmalıdır?", "a": "Evrensel bir doğru değer yoktur. BIST100 bankacılık hisseleri genellikle 5-12 arasında işlem görürken teknoloji şirketleri 20-50 olabilir. Önemli olan aynı sektördeki rakiplerle karşılaştırmaktır."},
      {"q": "Düşük F/K her zaman ucuz hisse demek midir?", "a": "Hayır. Düşük F/K büyüme beklentisinin olmadığını, şirkette sorunlar olduğunu veya sektörün baskı altında olduğunu gösterebilir. F/K'yı ROE, büyüme oranı ve sektör bağlamıyla birlikte değerlendirin."},
      {"q": "BorsaPusula'da F/K bilgisi nerede görünür?", "a": "Her hisse detay sayfasının Temel Analiz bölümünde F/K oranı gösterilir. Bu veri Yahoo Finance'den günlük güncellenir. Teknik sinyal ile düşük F/K kombinasyonu özellikle güçlü bir seçim kriteri olabilir."}
    ],
    "related_tickers": ['AKBNK', 'GARAN', 'EREGL']
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
""",
    "faqs": [
      {"q": "PD/DD oranı 1'in altında olması ne anlama gelir?", "a": "Hissenin defter değerinin altında işlem gördüğünü gösterir. Teorik olarak şirketin tasfiye değerinden daha ucuza alınıyor demektir. Ancak genellikle düşük kârlılık veya yüksek borç gibi riskleri yansıtır."},
      {"q": "PD/DD oranı hangi sektörlerde daha önemlidir?", "a": "Bankacılık, sigorta ve holding sektörlerinde PD/DD çok daha anlamlıdır. Bu şirketlerin değeri büyük ölçüde varlık tabanına dayanır ve F/K yetersiz kalır."},
      {"q": "Enflasyon PD/DD değerlendirmesini nasıl etkiler?", "a": "Yüksek enflasyon ortamında sabit varlıkların defter değeri gerçek piyasa değerinin çok altında kalabilir. Bu nedenle Türkiye gibi yüksek enflasyonlu piyasalarda PD/DD tek başına yanıltıcı olabilir."}
    ],
    "related_tickers": ['AKBNK', 'GARAN', 'EREGL']
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
""",
    "faqs": [
      {"q": "Algoritmik trading bireysel yatırımcı için nasıl faydalıdır?", "a": "BorsaPusula gibi platformlar sayesinde programlama bilgisi olmadan algoritmik sinyallerden yararlanılabilir. Platform 145 hisseyi tarar ve AL/SAT/BEKLE kararı üretir; siz sadece değerlendirip karar verirsiniz."},
      {"q": "Algoritmik sistemler her zaman başarılı mı olur?", "a": "Hayır. Algoritmik sistemler istatistiksel olasılıklar üzerinde çalışır, kesinlik garantisi vermez. Piyasa rejimleri değişebilir ve sistemi periyodik olarak gözden geçirmek önemlidir."},
      {"q": "BorsaPusula tam otomatik işlem yapıyor mu?", "a": "Hayır. BorsaPusula algoritmik sinyal üretir ancak emir vermez. Bu yarı otomatik model algoritmanın tutarlılığını insanın bağlamsal değerlendirmesiyle birleştirir."}
    ],
    "related_tickers": ['AKBNK', 'THYAO', 'ASELS']
  },
  {
    "slug": "destek-direnc-seviyeleri",
    "canonical_slug": "destek-direnc-seviyeleri-nedir",
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
""",
    "faqs": [
      {"q": "Destek seviyesi nasıl belirlenir?", "a": "Destek, fiyatın geçmişte birden fazla kez düşüp toparlandığı fiyat bölgesidir. Önceki diplere bakılır; yuvarlak sayılar, EMA seviyeleri ve Fibonacci geri çekilmeleri de destek oluşturur."},
      {"q": "Kırılan bir direnç neden destek olur?", "a": "Rol değişimi prensibi olarak bilinir. Direnç kırıldığında piyasa o seviyenin üzerinde işlem yapmayı kabul etmiştir. Eski direnç seviyesi artık alıcıların referans fiyatı haline gelir ve geri çekilmelerde destek görevi görür."},
      {"q": "Supertrend dinamik destek işlevi görür mü?", "a": "Evet. BorsaPusula grafiklerinde Supertrend bandı hem AL/SAT sinyali üretir hem de dinamik destek/direnç göstergesi işlevi görür. AL sinyalinde fiyat Supertrend'in üzerinde kaldığı sürece trend devam eder."}
    ],
    "related_tickers": ['AKBNK', 'ASELS', 'THYAO']
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
""",
    "faqs": [
      {"q": "RSI 30 altına düştüğünde hisse mutlaka alınmalı mıdır?", "a": "Hayır. RSI 30 altı aşırı satım bölgesi olsa da güçlü düşüş trendinde RSI uzun süre 30 altında kalabilir. BorsaPusula Supertrend ve ADX teyidiyle birlikte değerlendirmek gerekir."},
      {"q": "RSI divergence nasıl tespit edilir?", "a": "Bearish divergence: Fiyat yeni yüksek yaparken RSI yapamıyor. Bullish divergence: Fiyat yeni düşük yaparken RSI yapamıyor. Bu uyumsuzluk yaklaşan trend dönüşüne işaret edebilir."},
      {"q": "BorsaPusula'da RSI değeri nerede görünür?", "a": "Her hisse sayfasında güncel RSI değeri gösterilir. AL sinyalinde RSI 50-65 arasındaki hisseler ideal giriş noktasındadır, henüz aşırı alım bölgesine girmemiş demektir."}
    ],
    "related_tickers": ['AKBNK', 'GARAN', 'ASELS']
  },
  {
    "slug": "macd-gostergesi-nedir",
    "canonical_slug": "macd-indikatoru-nedir",
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
""",
    "faqs": [
      {"q": "MACD hangi parametrelerle kullanılır?", "a": "Standart MACD: EMA(12) - EMA(26) = MACD çizgisi, EMA(9) of MACD = sinyal çizgisi, MACD - Sinyal = histogram. Bu parametreler Gerald Appel tarafından tanımlanmış global standart değerlerdir."},
      {"q": "MACD histogram ne anlama gelir?", "a": "MACD histogramı MACD ile sinyal çizgisi arasındaki farkı gösterir. Histogram büyüyorsa momentum artıyor, küçülüyorsa zayıflıyor. Sıfırdan yükseğe geçiş AL, sıfırın altına iniş SAT momentumu gösterir."},
      {"q": "MACD Supertrend'den üstün müdür?", "a": "İkisi farklı avantajlar sunar. MACD divergence tespit edebilir, Supertrend edemez. Supertrend volatiliteye adapte olur (ATR bazlı), MACD olamaz. BorsaPusula Supertrend + ADX kombinasyonunu tercih eder."}
    ],
    "related_tickers": ['AKBNK', 'THYAO', 'ASELS']
  },
  {
    "slug": "hacim-analizi",
    "canonical_slug": "hacim-analizi-nedir",
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
""",
    "faqs": [
      {"q": "Düşük hacimli kırılım neden güvenilmez sayılır?", "a": "Güçlü kırılımın arkasında kurumsal alıcıların varlığı gerekir. Düşük hacimli kırılım büyük oyuncuların o yönde konumlanmadığına işaret eder, sahte kırılım riski yüksektir."},
      {"q": "BorsaPusula hacim verisini nasıl kullanıyor?", "a": "Sinyal üretiminde doğrudan hacim göstergesi kullanılmasa da her hisse sayfasındaki grafiklerde hacim çubukları gösterilir. Sinyal tarihleri etrafındaki hacim artışları sinyalin gücünü değerlendirmenize yardımcı olur."},
      {"q": "Vol Ratio ne anlama gelir?", "a": "Vol Ratio, son günün hacminin 20 günlük ortalamaya oranıdır. 1.5 üzeri, normalin 1.5 katı hacim anlamına gelir; sinyal günlerinde dikkat çekici bir göstergedir."}
    ],
    "related_tickers": ['AKBNK', 'THYAO', 'ASELS']
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
""",
    "faqs": [
      {"q": "Fibonacci seviyeleri nasıl çizilir?", "a": "Yükselen trendde trend başlangıcından (0%) sonuna (100%) çizgi çekin. Fibonacci aracı bu iki nokta arasında otomatik olarak %23.6, %38.2, %50, %61.8 ve %78.6 seviyelerini hesaplar."},
      {"q": "Neden %61.8 altın oran olarak adlandırılır?", "a": "Her Fibonacci sayısının kendinden öncekine oranı yaklaşık 1.618'e yaklaşır (altın oran). Bu oran doğada ve mimaride de karşımıza çıkar. Analistler fiyatların bu seviyede tepki verdiğini gözlemlemişlerdir."},
      {"q": "Supertrend ile Fibonacci kombinasyonu nasıl kullanılır?", "a": "AL sinyali geldiğinde fiyat eş zamanlı olarak %38.2 veya %61.8 Fibonacci desteğindeyse iki metodun aynı seviyeye işaret etmesi confluance (örtüşme) oluşturur. Bu giriş noktasının güvenilirliğini artırır."}
    ],
    "related_tickers": ['AKBNK', 'THYAO']
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
""",
    "faqs": [
      {"q": "Bollinger Bantları nasıl hesaplanır?", "a": "Orta bant SMA(20), üst bant SMA(20) + 2×standart sapma, alt bant SMA(20) − 2×standart sapma şeklinde hesaplanır. Volatilite arttığında bantlar genişler, azaldığında daralır."},
      {"q": "Bollinger Bant sıkışması ne anlama gelir?", "a": "Bantların birbirine yaklaştığı sıkışma dönemleri yaklaşan güçlü bir hareketi işaret eder. Sıkışma sonrası kırılımın yönü bir sonraki trendin yönünü belirler. Yüksek hacimli kırılım daha güvenilirdir."},
      {"q": "Fiyatın üst banta dokunması satış sinyali midir?", "a": "Mutlaka değil. Güçlü trendlerde fiyat uzun süre üst bantta yürüyebilir. BorsaPusula Supertrend + ADX sinyali üst bantta bile aktif olabilir; tek başına bant dokunuşu satış kriteri değildir."}
    ],
    "related_tickers": ['AKBNK', 'GARAN', 'THYAO']
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
""",
    "faqs": [
      {"q": "Temettü verimi nasıl hesaplanır?", "a": "Temettü Verimi = Yıllık Temettü ÷ Hisse Fiyatı × 100. Örneğin hisse 50₺ ve yıllık temettü 3₺ ise verimi %6'dır. Devlet tahvil faizleriyle karşılaştırılarak değerlendirilir."},
      {"q": "BIST'te yüksek temettü veren hisseler hangileridir?", "a": "BIST'te tarihsel olarak yüksek temettü veren sektörler bankacılık (GARAN, AKBNK) ve sanayi (EREGL, TTRAK) olarak öne çıkar. Temettü politikasının tutarlılığı tek seferlik yüksek temettüden daha değerlidir."},
      {"q": "Temettü için en iyi giriş zamanı ne zamandır?", "a": "Temettü hakkı için hisse temettü sonrası pay tarihinden önce alınmalıdır. Ancak hisse ex-dividend günü temettü miktarı kadar düşer. Teknik sinyalin de desteklediği dönemlerde almak en akıllı yaklaşımdır."}
    ],
    "related_tickers": ['EREGL', 'GARAN', 'AKBNK']
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
""",
    "faqs": [
      {"q": "Yüksek enflasyonda hangi hisseler daha iyi performans gösterir?", "a": "Fiyat geçirme gücü yüksek sektörler (enerji, hammadde, perakende) ve döviz geliri olan ihracatçı şirketler enflasyon ortamında görece dayanıklıdır. Sabit maliyetli işletmeler ise baskı altında kalır."},
      {"q": "Türkiye'deki yüksek enflasyon BIST'i nasıl etkiliyor?", "a": "Yüksek enflasyon döneminde BIST nominal olarak yükselse de dolar bazında değer kaybedebilir. Gerçek getiriyi ölçmek için enflasyon düzeltmesi yapılmalıdır."},
      {"q": "Enflasyon döneminde tahvil mi hisse mi?", "a": "Tarihsel olarak hisse senetleri uzun vadede enflasyona karşı tahvillerden daha iyi koruma sağlar çünkü şirketler fiyatlarını enflasyonla artırabilir. Ancak yüksek faiz artışının eşlik ettiği dönemlerde kısa vadede her ikisi de değer kaybedebilir."}
    ],
    "related_tickers": ['EREGL', 'THYAO', 'TUPRS']
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
""",
    "faqs": [
      {"q": "Borsa işlemlerinde en sık kullanılan terimler nelerdir?", "a": "En temel kavramlar: AL/SAT emri, stop loss (zarar durdur), take profit (kâr al), piyasa emri, limit emir, spread, lot, portföy, pozisyon, volatilite ve hacim. Bu terimlerin anlamını bilmeden işlem yapmamak önemlidir."},
      {"q": "Bull ve Bear piyasası ne demektir?", "a": "Bull (boğa) piyasası fiyatların genel olarak yükseldiği iyimser dönemdir. Bear (ayı) piyasası ise fiyatların %20 veya daha fazla düştüğü karamser dönemdir. Bu iki kavram piyasa senaryolarını anlatmak için sıkça kullanılır."},
      {"q": "BorsaPusula teknik terimlerini nerede açıklıyor?", "a": "ADX, RSI, Supertrend, EMA gibi tüm teknik göstergeler için Metodoloji sayfasında detaylı açıklamalar bulunur. Her sinyal bileşeninin nasıl hesaplandığı ve yorumlandığı anlatılır."}
    ],
    "related_tickers": ['AKBNK', 'THYAO']
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
""",
    "faqs": [
      {"q": "BorsaPusula sinyalleri ne sıklıkla güncelleniyor?", "a": "Sinyal hesaplamaları 15 dakikada bir yapılır. Canlı fiyatlar SSE teknolojisiyle 30 saniyede bir güncellenir. Sinyaller Yahoo Finance verilerinden hesaplanır ve piyasa saatleri içinde aktiftir."},
      {"q": "Üçlü filtre sistemi neden tek göstergeden daha güvenilir?", "a": "Supertrend + ADX + EMA üçünün aynı anda aynı yönü göstermesi gerektiğinden rastgele kesişim olasılığı dramatik biçimde azalır. Bu da sahte sinyal sayısını önemli ölçüde düşürür."},
      {"q": "Onaylı sinyal ile ham sinyal arasındaki fark nedir?", "a": "Ham sinyal oluştuğu ilk gündür ve daha az güvenilirdir. Onaylı sinyal aynı sinyalin 3+ gün sürmesidir ve trend gücünü doğrular. Kaç gündür devam ettiği hisse sayfalarında signal_bars değeriyle gösterilir."}
    ],
    "related_tickers": ['AKBNK', 'GARAN', 'ASELS', 'THYAO']
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
""",
    "faqs": [
      {"q": "BIST100'de en büyük sektör hangisidir?", "a": "Bankacılık ve finans sektörü BIST100'ün en yüksek ağırlığını oluşturur. AKBNK, GARAN, ISCTR, VAKBN gibi büyük bankalar endeksi güçlü şekilde etkiler. Bankacılık haberleri tüm endeksi etkiler."},
      {"q": "Sektör rotasyonu ne demektir?", "a": "Piyasa döngüsünün farklı aşamalarında farklı sektörler öne çıkar. Ekonomi büyürken sanayi ve teknoloji liderken resesyonda zorunlu tüketim ve sağlık savunmacı sektörler öne geçer."},
      {"q": "BorsaPusula'da sektör filtresi nasıl kullanılır?", "a": "Ana sayfada sektör butonlarıyla yalnızca ilgili sektörün hisseleri görülür. Sektör ısı haritası (/sektor-harita) tüm sektörlerin AL/SAT/BEKLE dağılımını görsel karşılaştırma imkânı sunar."}
    ],
    "related_tickers": ['AKBNK', 'ASELS', 'THYAO', 'BIMAS']
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
""",
    "faqs": [
      {"q": "Borsaya başlamak için minimum ne kadar sermaye gerekir?", "a": "Teknik olarak birkaç yüz TL ile borsaya başlanabilir. Ancak çeşitlendirme yapabilmek ve işlem maliyetlerinin getiriyi yememesi için en az 10.000-50.000 TL ile başlamak önerilir. Her zaman kaybetmeyi göze alabileceğiniz para kullanın."},
      {"q": "Borsayı öğrenmek için nereden başlamalıyım?", "a": "BorsaPusula Blog'undaki temel kavramlar makaleleri ile başlayabilirsiniz. Metodoloji sayfası algoritmanın nasıl çalıştığını açıklar. Daha sonra küçük miktarlarla uygulama yaparak deneyim kazanın."},
      {"q": "BorsaPusula sinyallerini nasıl takip etmeliyim?", "a": "Ana sayfadan tüm hisselerin AL/SAT/BEKLE durumunu görebilirsiniz. İlgilendiğiniz hisseler için Günlük Özet sayfasını sabah kontrol edin. E-posta aboneliğiyle sinyal değişimlerini otomatik alın."}
    ],
    "related_tickers": ['AKBNK', 'GARAN', 'BIMAS']
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
""",
    "faqs": [
      {"q": "FOMO yatırım kararlarını nasıl etkiler?", "a": "FOMO, sosyal medyada başkasının kazandığını gördüğünüzde irrasyonel alım kararları almanıza neden olur. Genellikle rallinin tepesine yakın giriş yapılır ve ardından düşüş yaşanır. Kural tabanlı sinyal sistemleri FOMO'yu önlemenin en etkili yoludur."},
      {"q": "Kaybeden pozisyonları kapatmak neden psikolojik olarak zordur?", "a": "Kahneman'ın kayıptan kaçınma teorisine göre insanlar kaybın acısını kazancın sevincinin 2 katı hisseder. Bu nedenle 'bekleyeyim düzelir' rasyonalizasyonuna sığınılır. Stop loss bu tuzağı mekanik olarak ortadan kaldırır."},
      {"q": "Algoritmik sinyal kullanmak psikolojik hatayı önler mi?", "a": "Önemli ölçüde evet. Supertrend SAT'a geçmedikçe sistem AL der ve bu netlik panikleri önler. Ancak algoritmaya körce güvenmek de tuzaktır; sistemi anlamak ve bağlamsal değerlendirme yapmak gerekir."}
    ],
    "related_tickers": ['AKBNK', 'THYAO']
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
""",
    "faqs": [
      {"q": "Supertrend mi MACD mi daha iyi bir göstergedir?", "a": "Birinin diğerinden üstün olduğunu söylemek yanıltıcı olur. Supertrend volatiliteye uyum sağlar ve dinamik stop loss verir; MACD divergence tespiti yapabilir. BorsaPusula Supertrend + ADX kombinasyonunu tercih eder."},
      {"q": "Neden BorsaPusula MACD yerine Supertrend kullanıyor?", "a": "Supertrend ATR bazlı olduğundan farklı volatilite ortamlarında aynı parametrelerle kullanılabilir ve dinamik stop loss sağlar. MACD gecikmeli ve sabit parametreli olduğundan BIST piyasasına daha az uyumludur."},
      {"q": "İki gösterge çakıştığında ne yapmalıyım?", "a": "Supertrend AL + MACD da AL yönünde ise sinyal güçlüdür. Supertrend AL ancak MACD bearish divergence gösteriyorsa dikkatli olunmalıdır. Çakışma güvenilirliği artırır, uyuşmazlık uyarı işareti verir."}
    ],
    "related_tickers": ['AKBNK', 'ASELS', 'THYAO']
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
""",
    "faqs": [
      {"q": "Çok sayıda AL sinyali arasından nasıl seçim yapılır?", "a": "Teknik puanlama: sinyal kaç gündür sürüyor, ADX değeri, MTF uyumu. Temel puanlama: F/K, ROE, temettü. Piyasa bağlamı: genel AL oranı. Bu üç boyutu birleştirerek en yüksek puanlı hisseyi seçin."},
      {"q": "ADX değeri hisse seçiminde ne kadar önemlidir?", "a": "ADX 25 üzeri trend güçlü, ADX 35 üzeri çok güçlü demektir. Aynı sinyal gücünde iki hisse arasında seçimde ADX değeri yüksek olan daha güvenilir trend gösterir ve tercih edilmelidir."},
      {"q": "Giriş kalitesi IDEAL/IYI/DIKKATLI/UZAK neye göre belirlenir?", "a": "BorsaPusula giriş kalitesi güncel fiyatın Supertrend'e olan mesafesine göre belirlenir. IDEAL fiyat Supertrend'e çok yakın (az risk), IYI makul mesafede, DIKKATLI nispeten uzak, UZAK çok uzak ve yüksek risk anlamına gelir."}
    ],
    "related_tickers": ['ASELS', 'THYAO', 'AKBNK']
  },

  {
    "slug": "kap-bildirimleri-nedir",
    "title": "KAP Bildirimleri Nedir? Yatırımcı İçin Rehber",
    "desc": "KAP (Kamuyu Aydınlatma Platformu) bildirimleri nelerdir, nasıl okunur ve sinyal üzerindeki etkisi ne anlama gelir?",
    "date": "2026-05-01",
    "mins": 6,
    "cat": "Temel Kavramlar",
    "body": """
<p><strong>KAP (Kamuyu Aydınlatma Platformu)</strong>, halka açık şirketlerin yatırımcıları bilgilendirmek amacıyla yaptıkları resmi açıklamaları yayınladıkları platformdur. Türkiye'de borsaya kote her şirket, SPK düzenlemeleri gereği önemli her gelişmeyi KAP üzerinden kamuoyuyla paylaşmak zorundadır.</p>

<h2>KAP Bildirimi Türleri</h2>
<ul>
  <li><strong>ÖDA (Özel Durum Açıklaması):</strong> Şirketin değerini etkileyebilecek önemli gelişmeler — büyük sözleşmeler, ortaklık değişiklikleri, önemli davalar</li>
  <li><strong>FR (Finansal Rapor):</strong> Üç aylık ve yıllık mali tablolar — bilanço, gelir tablosu, nakit akışı</li>
  <li><strong>ODA (Olağan/Olağanüstü Genel Kurul):</strong> Genel kurul kararları, temettü açıklamaları</li>
  <li><strong>Pay Alım/Satım:</strong> İçeriden işlem bildirimleri — yöneticilerin hisse alım/satımları</li>
  <li><strong>Sözleşme:</strong> Kamu ya da özel sektörle imzalanan önemli sözleşmeler</li>
</ul>

<h2>KAP Bildirimini Nasıl Yorumlamalısınız?</h2>
<p>Her KAP bildirimi aynı etkiyi yaratmaz. Değerlendirme için bu soruları sorun:</p>
<ol>
  <li><strong>Büyüklük:</strong> Bu sözleşme/gelişme şirketin yıllık cirosunun yüzde kaçını etkiliyor?</li>
  <li><strong>Yinelelenebilirlik:</strong> Tek seferlik mi, tekrarlayan mı?</li>
  <li><strong>Piyasanın beklentisi:</strong> Beklenen bir gelişmeyse zaten fiyatlanmış olabilir.</li>
  <li><strong>Teknik sinyal ile uyum:</strong> Hisse aynı anda AL sinyali veriyor mu?</li>
</ol>

<h2>KAP + Teknik Sinyal Kombinasyonu</h2>
<p>BorsaPusula'nın en güçlü özelliklerinden biri, KAP bildirimleri ile teknik sinyalleri aynı ekranda göstermesidir. Bir hissenin hem AL sinyali verdiği hem de güçlü bir KAP bildirimi yaptığı dönemler — örneğin büyük sözleşme + Supertrend AL uyumu — genellikle güçlü katalizör oluşturur.</p>

<h2>KAP Bildirimlerine Nasıl Erişilir?</h2>
<p>BorsaPusula'da her hisse sayfasında <strong>"KAP Bildirimleri"</strong> sekmesi bulunur. Son 90 günlük bildirimler orada listelenir. Doğrudan KAP platformuna (kap.org.tr) da erişebilirsiniz.</p>

<h2>Sık Yapılan Hatalar</h2>
<ul>
  <li>KAP bildirimi yayınlanır yayınlanmaz panikle alım/satım yapmak — çoğunlukla haber zaten fiyatlanmıştır.</li>
  <li>Her FR (finansal rapor) bildirimini olumlu zannetmek — rakamların detayını okumak gerekir.</li>
  <li>KAP bildirimine güvenerek teknik sinyali görmezden gelmek — ikisi birlikte değerlendirilmelidir.</li>
</ul>
""",
    "faqs": [
      {"q": "KAP nedir ve neden önemlidir?", "a": "KAP (Kamuyu Aydınlatma Platformu), Türkiye'de borsaya kote şirketlerin zorunlu resmi açıklamalarını yaptıkları platformdur. Finansal sonuçlar, büyük sözleşmeler ve şirketi etkileyen önemli gelişmeler burada yayınlanır. Yatırımcılar için şeffaf ve güvenilir birincil haber kaynağıdır."},
      {"q": "KAP bildirimi hisse fiyatını etkiler mi?", "a": "Evet, özellikle beklenmedik özel durum açıklamaları (ÖDA) ve finansal sonuçlar (FR) hisse fiyatını doğrudan etkiler. Ancak beklenen bir bildirimse piyasa bunu önceden fiyatlamış olabilir. KAP bildirimini teknik sinyal ile birlikte değerlendirmek daha sağlıklı karar verilmesini sağlar."},
      {"q": "BorsaPusula'da KAP bildirimleri nasıl gösterilir?", "a": "Her hisse sayfasında 'KAP Bildirimleri' sekmesi bulunur ve son 90 güne ait resmi KAP bildirimleri listelenir. Ayrıca 'Sinyalin Hikayesi' bölümünde sinyal tarihi etrafındaki KAP bildirimleri de gösterilir."}
    ],
    "related_tickers": ['AKBNK', 'ASELS', 'THYAO']
  },

  {
    "slug": "bist30-hisseleri-2026",
    "title": "BIST30 Hisseleri 2026 — Tam Liste ve Analiz",
    "desc": "BIST30 endeksindeki tüm hisseler, sektörel dağılım ve teknik sinyal özetleriyle 2026 güncel rehber.",
    "date": "2026-05-01",
    "mins": 8,
    "cat": "Temel Kavramlar",
    "body": """
<p><strong>BIST30</strong>, Borsa İstanbul'daki en yüksek işlem hacmine sahip 30 büyük hisseyi kapsayan prestijli bir endekstir. Türkiye vadeli işlemler piyasasının (VİOP) temel endeksi olması nedeniyle kurumsal yatırımcılar ve fon yöneticilerinin en yakından takip ettiği endekstir.</p>

<h2>BIST30 Hisseleri (2026)</h2>
<p>Endeks bileşenleri Borsa İstanbul tarafından Mart ve Eylül aylarında güncellenir. 2026 yılı itibarıyla BIST30 şu sektörlerden oluşmaktadır:</p>

<h3>Bankacılık</h3>
<ul>
  <li><strong>AKBNK</strong> — Akbank T.A.Ş.</li>
  <li><strong>GARAN</strong> — Garanti BBVA</li>
  <li><strong>ISCTR</strong> — İş Bankası C</li>
  <li><strong>VAKBN</strong> — Vakıfbank</li>
  <li><strong>YKBNK</strong> — Yapı Kredi Bankası</li>
  <li><strong>HALKB</strong> — Halkbank</li>
</ul>

<h3>Holding ve Sanayi</h3>
<ul>
  <li><strong>KCHOL</strong> — Koç Holding</li>
  <li><strong>SAHOL</strong> — Sabancı Holding</li>
  <li><strong>ARCLK</strong> — Arçelik</li>
  <li><strong>FROTO</strong> — Ford Otosan</li>
  <li><strong>TOASO</strong> — Tofaş Oto</li>
  <li><strong>EREGL</strong> — Ereğli Demir Çelik</li>
</ul>

<h3>Enerji ve Petrokimya</h3>
<ul>
  <li><strong>TUPRS</strong> — Tüpraş</li>
  <li><strong>PETKM</strong> — Petkim</li>
  <li><strong>SASA</strong> — Sasa Polyester</li>
  <li><strong>AKSEN</strong> — Aksen Enerji</li>
  <li><strong>ENKAI</strong> — Enka İnşaat</li>
</ul>

<h3>Diğer Sektörler</h3>
<ul>
  <li><strong>THYAO</strong> — Türk Hava Yolları (Ulaşım)</li>
  <li><strong>TCELL</strong> — Turkcell (Telekom)</li>
  <li><strong>TTKOM</strong> — Türk Telekom (Telekom)</li>
  <li><strong>BIMAS</strong> — BİM Mağazalar (Perakende)</li>
  <li><strong>MGROS</strong> — Migros (Perakende)</li>
  <li><strong>ASELS</strong> — Aselsan (Savunma)</li>
  <li><strong>EKGYO</strong> — Emlak Konut GYO</li>
  <li><strong>TKFEN</strong> — Tekfen Holding</li>
  <li><strong>TAVHL</strong> — TAV Havalimanları</li>
  <li><strong>PGSUS</strong> — Pegasus Hava Yolları</li>
  <li><strong>SISE</strong> — Şişe Cam</li>
  <li><strong>HEKTS</strong> — Hektaş</li>
</ul>

<h2>BIST30'un Önemi</h2>
<p>BIST30 hisseleri birkaç kritik özellik taşır:</p>
<ul>
  <li><strong>Yüksek likidite:</strong> Kolayca alınıp satılabilir; büyük emirler fiyatı fazla etkilemez.</li>
  <li><strong>Kurumsal takip:</strong> Yabancı yatırımcılar ve büyük fonlar bu hisseleri yoğun takip eder.</li>
  <li><strong>VİOP bağlantısı:</strong> Vadeli işlemler (BIST30 futures) ile hedge edilebilir.</li>
  <li><strong>Endeks fonu yatırımı:</strong> BIST30 ETF'leri aracılığıyla tek alımla 30 hisseye yatırım yapılabilir.</li>
</ul>

<h2>BIST30 Sinyal Analizi — Güncel Durum</h2>
<p>BorsaPusula, BIST30 hisselerinin tamamı için Supertrend, ADX ve EMA tabanlı algoritmik sinyal hesaplar. <a href="/">Güncel sinyalleri</a> görmek için ana sayfayı ziyaret edin. <a href="/ozet">Sinyal Özeti</a> sayfasında ise tüm endeksin anlık durumunu tek bakışta görebilirsiniz.</p>

<h2>Hangi BIST30 Hissesi Daha İyi?</h2>
<p>"En iyi BIST30 hissesi" sorusunun tek bir yanıtı yoktur. Değerlendirirken şunlara bakın:</p>
<ol>
  <li><strong>Aktif sinyal:</strong> AL sinyali var mı, kaç gündür sürüyor?</li>
  <li><strong>Trend gücü:</strong> ADX değeri 25'in üzerinde mi?</li>
  <li><strong>Giriş kalitesi:</strong> Fiyat Supertrend'e yakın mı (IDEAL/İYİ)?</li>
  <li><strong>Risk/Ödül:</strong> R/R oranı en az 1:2 mi?</li>
  <li><strong>Sektör bağlamı:</strong> Sektörde genel trend yukarı mı?</li>
</ol>
<p><a href="/gucu-yuksek">Güçlü Momentum</a> sayfasında tüm bu kriterleri en iyi karşılayan BIST30 hisseleri sıralanmaktadır.</p>
""",
    "faqs": [
      {"q": "BIST30'da kaç hisse var ve hangileri?", "a": "BIST30, Borsa İstanbul'da en likit 30 hisseyi kapsar. Bankacılık (AKBNK, GARAN, ISCTR, YKBNK, VAKBN, HALKB), holding/sanayi (KCHOL, SAHOL, ARCLK, FROTO, TOASO, EREGL), enerji (TUPRS, AKSEN, ENKAI, SASA) ve diğer sektörlerden oluşur."},
      {"q": "BIST30 endeksi ne kadar sıklıkla güncellenir?", "a": "Borsa İstanbul, BIST30 endeks bileşenlerini her yıl Mart ve Eylül aylarında inceler ve günceller. Yeterli likidite ve piyasa değeri kriterlerini karşılayamayan hisseler çıkarılır, yerlerine uygun hisseler alınır."},
      {"q": "BIST30 hisselerinin teknik sinyalleri nereden takip edilir?", "a": "BorsaPusula'da BIST30 hisselerinin tamamı için Supertrend + ADX + EMA algoritmik sinyalleri ücretsiz olarak sunulmaktadır. Ana sayfada 'BIST30' filtresiyle bu hisseleri ayrıca görebilirsiniz."}
    ],
    "related_tickers": ['AKBNK', 'GARAN', 'THYAO', 'EREGL', 'ASELS']
  },
  {
    "slug": "swing-trading-nedir",
    "title": "Swing Trading Nedir? BIST'te Swing Trade Nasıl Yapılır?",
    "cat": "Strateji",
    "read_min": 7,
    "summary": "Swing trading, birkaç günden birkaç haftaya uzanan fiyat hareketlerinden kazanç sağlamayı hedefleyen bir trading stratejisidir. BIST hisselerinde nasıl uygulanır, hangi indikatörler kullanılır?",
    "body": """## Swing Trading Nedir?

Swing trading, bir hisse senedini birkaç gün ile birkaç hafta arasında tutarak, **orta vadeli fiyat dalgalanmalarından** kazanç sağlamayı hedefleyen bir stratejidir.

Günlük (day trading) gibi çok kısa vadeli değil, uzun vadeli yatırım gibi aylar/yıllar süren bir strateji de değil. "Swing" (salınım) adını, fiyatın yukarı-aşağı salınımlarından yararlanma mantığından alır.

## Swing Trade vs Diğer Stratejiler

| Strateji | Süre | Odak | Risk |
|----------|------|------|------|
| Scalping | Dakika - Saat | Küçük hareketler | Çok yüksek |
| Day Trading | Aynı gün | Günlük hareket | Yüksek |
| **Swing Trading** | **3-20 gün** | **Trend dalgaları** | **Orta** |
| Pozisyon Trading | Hafta - Ay | Büyük trendler | Orta-Düşük |
| Yatırım | Yıl+ | Değer artışı | Uzun vadeli |

## BIST'te Swing Trading Mantığı

BIST hisseleri günde %5-15 hareket edebilir. Swing trader bu dalgalanmalardan yararlanır:

- **Giriş:** Trend başlangıcında veya geri çekilmede
- **Tutma:** Trendin devam ettiği süre (ortalama 5-15 gün)
- **Çıkış:** Hedef fiyata ulaşınca veya sinyal tersine döünce

## Swing Trading İçin Temel İndikatörler

### 1. Supertrend
Swing traderin en iyi arkadaşı. Trendin yönünü ve döndüğü noktayı net olarak gösterir:
- **Yeşil Supertrend:** Uzun pozisyon tutmak için uygun
- **Kırmızı Supertrend:** Düşüş trendinde çıkmak gerekir

### 2. ADX (Average Directional Index)
Trendin **gücünü** ölçer (yönünü değil):
- ADX > 25 → Güçlü trend var, swing fırsatı yüksek
- ADX < 20 → Yatay piyasa, swing yapmak riskli

### 3. RSI (Relative Strength Index)
Giriş/çıkış zamanlaması için:
- RSI 35-40 bölgesinde geri çekilme → Potansiyel alım fırsatı
- RSI 70+ bölgesinde fiyat → Kar alım bölgesi

### 4. EMA (Hareketli Ortalama)
- EMA 20 > EMA 50 > EMA 100 hizalaması → Güçlü yükseliş trendi
- Fiyat EMA 20'ye geri çekilirse → Swing alım noktası

## Pratik Swing Trading Stratejisi: Pullback Al

**Adım 1:** Ana trend yukarı olduğunu doğrula (EMA hizalama + Supertrend yeşil)

**Adım 2:** Fiyatın bir geri çekilme (pullback) yaşadığını bekle — genellikle EMA 20 veya 50 seviyesine

**Adım 3:** RSI 35-45 bölgesine gelince alım yap

**Adım 4:** Stop-loss: Giriş fiyatının %3-5 altına koy

**Adım 5:** Hedef: Önceki zirve veya R/R = 1:2 seviyesi

## Swing Trading Risk Yönetimi

Swing traderde sermayeyi korumak kritiktir:

- **Her işlemde maksimum %1-2 risk** (stop-loss ile hesaplanır)
- **Pozisyon büyüklüğü** = (Sermaye × Risk%) ÷ (Giriş - Stop)
- **En az 1:2 risk/ödül oranı** — 1 birim riskle 2 birim kazanç hedefle
- **Aynı anda çok fazla pozisyon açma** — maksimum 3-5 pozisyon

## BIST'te Swing Trading: Dikkat Edilecekler

**Makro faktörler önemli:**
- Dolar/TL hareketi BIST'i direkt etkiler
- TCMB kararları, enflasyon verileri sert hareketler yaratabilir
- Bu haberleri takip et, stop-loss'unu koruyun

**Likiditeye dikkat:**
- BIST30 hisseleri swing için uygundur — likiditesi yüksek
- Küçük hisselerde alım/satım spreadi swing karı yiyebilir

**Piyasa saatleri:**
- BIST 10:00-18:00 arası açık
- İlk 30 dakika (10:00-10:30) ve son 30 dakika (17:30-18:00) en volatil

## BorsaPusula ile Swing Fırsatı Bul

BorsaPusula'daki algoritmik sinyaller tam olarak swing trading için tasarlanmıştır:

- **AL sinyali** = Supertrend + ADX + EMA üçlü onayı → Swing giriş fırsatı
- **ADX değeri** → Trendin ne kadar güçlü olduğunu gösterir
- **Sinyal yaşı** → Kaç gün önce girdi, henüz erken mi geç mi?
- **Giriş/SL seviyeleri** → Stop-loss otomatik hesaplanmış

[Şu anki swing fırsatlarını gör →](/)""",
    "faqs": [
      {"q": "Swing trading günlük tradingden ne farkı var?", "a": "Day trading aynı gün içinde pozisyon kapatır, gecelik risk almaz. Swing trading ise 3-20 gün arasında pozisyon tutar, gecelik fiyat hareketlerinden de yararlanır. Daha az ekran başında olunmasını gerektirdiği için çalışan bireysel yatırımcılara daha uygundur."},
      {"q": "BIST'te swing trading için minimum sermaye ne olmalı?", "a": "Minimum 10.000 TL önerilir. Bunun altında tek bir hissede anlamlı pozisyon almak ve risk yönetimi yapmak zorlaşır. Swing trading için her işlemde sermayenin maksimum %1-2'si riske atılmalıdır."},
      {"q": "Swing traderde en önemli indikatör hangisi?", "a": "Supertrend ve ADX kombinasyonu swing traderin temel araçlarıdır. Supertrend trendin yönünü ve döndüğü noktayı gösterirken, ADX trendin gücünü ölçer. ADX 25 üzerindeyken Supertrend yeşilse güçlü bir swing fırsatı mevcuttur."},
      {"q": "Stop-loss olmadan swing trade yapılabilir mi?", "a": "Kesinlikle hayır. Stop-loss, swing traderin en önemli koruma mekanizmasıdır. Borsada her işlem ters gidebilir. Stop-loss olmadan küçük bir kayıp büyüyerek sermayenin büyük bölümünü eritebilir."},
      {"q": "BIST'te en iyi swing trade günleri hangileridir?", "a": "Genel olarak Salı-Perşembe en istikrarlı trading günleridir. Pazartesi sabahı hafta sonu haberleri fiyatlanır (gap riski yüksek). Cuma öğleden sonra pozisyon tutmak hafta sonu riski taşır."}
    ],
    "related_tickers": ['AKBNK', 'THYAO', 'EREGL', 'ASELS', 'GARAN']
  },
  {
    "slug": "atr-indikatoru-nedir",
    "title": "ATR (Average True Range) Nedir? Volatilite Ölçümü",
    "cat": "Teknik Analiz",
    "read_min": 5,
    "summary": "ATR (Ortalama Gerçek Aralık), bir varlığın volatilitesini ölçen bir teknik indikatördür. Stop-loss hesaplamada ve Supertrend'in temelinde kullanılır.",
    "body": """## ATR (Average True Range) Nedir?

ATR, **Average True Range** (Ortalama Gerçek Aralık) kelimelerinin kısaltmasıdır. 1978 yılında J. Welles Wilder tarafından geliştirilen bu indikatör, bir hisse senedinin **ne kadar volatil (oynak) olduğunu** ölçer.

ATR fiyatın yönünü değil, sadece **hareket genişliğini** ölçer. Bu yüzden hem yükselen hem düşen piyasada geçerlidir.

## True Range (Gerçek Aralık) Nasıl Hesaplanır?

Her mum çubuğu için "True Range" şu üç değerin en büyüğüdür:

1. **Günlük Yüksek - Günlük Düşük** (normal gün içi aralık)
2. **|Günlük Yüksek - Önceki Kapanış|** (gap yukarı durumunda)
3. **|Günlük Düşük - Önceki Kapanış|** (gap aşağı durumunda)

**ATR = Belirli periyot boyunca True Range'in üstel hareketli ortalaması** (genellikle 14 periyot)

## ATR Ne Anlama Gelir?

| ATR Değeri | Anlam | Ne Yapmalı? |
|-----------|-------|------------|
| Düşük ATR | Düşük volatilite, sıkışık fiyat | Kırılma bekleniyor |
| Yükselen ATR | Volatilite artıyor, trend güçleniyor | Dikkatli ol, pozisyon yönet |
| Çok yüksek ATR | Panik/coşku, aşırı hareket | Stop-loss genişlet |

## ATR'nin Kullanım Alanları

### 1. Stop-Loss Belirleme (En Önemli Kullanım)
ATR tabanlı stop-loss, sabit yüzde stop'tan çok daha akıllıcadır:

```
Stop-Loss = Giriş Fiyatı - (ATR × Çarpan)

Swing Trade için: ATR × 1.5
Günlük Trade için: ATR × 1.0
Pozisyon Trade için: ATR × 2.0-3.0
```

**Örnek:** AKBNK ATR = 2.5 TL, giriş 85 TL
- Stop = 85 - (2.5 × 1.5) = 85 - 3.75 = **81.25 TL**

Bu yaklaşım, hissenin volatilitesine göre dinamik stop belirler.

### 2. Supertrend İndikatöründe
BorsaPusula'nın kullandığı **Supertrend indikatörü** doğrudan ATR kullanır:

```
Supertrend = Temel Fiyat ± (ATR × Çarpan)
```

Varsayılan parametreler: ATR(10) × 3.0

ATR yükseldikçe Supertrend bantları genişler, yani daha fazla hareket tolerans edilir.

### 3. Pozisyon Büyüklüğü Hesabı
```
Pozisyon = (Sermaye × Risk%) ÷ (ATR × Çarpan)
```

ATR yüksek hissede daha az lot al, ATR düşük hissede daha fazla.

## BIST Hisselerinde Tipik ATR Değerleri

| Hisse | Günlük ATR | Haftalık ATR |
|-------|-----------|-------------|
| BIST30 büyük cap | %1.5-3.0 | %4-8 |
| BIST100 orta cap | %2.0-4.0 | %6-12 |
| Küçük hisseler | %3.0-8.0+ | %10-25+ |

BIST büyük hisseleri günlük %2-3 ATR ile hareket ediyorsa, bu normal ve beklenen bir volatilitedir.

## ATR ve Diğer İndikatörlerle Birlikte Kullanım

**ATR + Supertrend:** Supertrend, ATR üzerine inşa edilmiştir. ATR yükselince Supertrend daha geniş bantlarla hareket eder.

**ATR + ADX:** Her ikisi de Welles Wilder'ın eserleridir. ADX trendin varlığını, ATR trendin genişliğini gösterir.

**ATR + Bollinger Bantları:** Her ikisi de volatilite ölçer. ATR yükseldiğinde Bollinger bantları da genişler.

## ATR'nin Sınırlamaları

- **Yön bilgisi vermez** — sadece genişlik/volatilite
- **Gecikmeli gösterge** — geçmiş volatiliteyi ölçer
- **Çok düşük ATR aldatıcı olabilir** — sessizlik öncesi fırtına

## BorsaPusula'da ATR Etkisi

BorsaPusula sinyalleri ATR'yi arka planda kullanır:

- **Sinyal kalitesi** — Supertrend, ATR ile dinamik destek/direnç çizer
- **Stop-loss seviyeleri** — Görüntülenen SL seviyeleri ATR bazlıdır
- **Risk değerlendirmesi** — Giriş kalitesi kısmen volatiliteye göre belirlenir

Yüksek ATR dönemlerinde sinyaller daha geniş stop ile gelir, bu normaldir ve piyasanın oynaklığını yansıtır.

[BIST hisselerinin sinyal ve SL seviyelerini gör →](/)""",
    "faqs": [
      {"q": "ATR indikatörü için ideal periyot nedir?", "a": "Standart ATR periyodu 14'tür. Kısa vadeli trading için 7-10, uzun vadeli pozisyonlar için 20-21 kullanılabilir. BorsaPusula'nın Supertrend sinyallerinde ATR(10) kullanılmaktadır."},
      {"q": "ATR değeri ne kadar olmalı ki işlem yapılabilir?", "a": "Belirli bir 'ideal ATR' yoktur. Önemli olan ATR'nin trend sırasında yükselmesi, daralma dönemlerinde düşmesidir. Yükselen ATR ile birlikte gelen fiyat kırılması güçlü bir sinyal olarak yorumlanır."},
      {"q": "Supertrend ile ATR arasındaki ilişki nedir?", "a": "Supertrend indikatörü tamamen ATR üzerine inşa edilmiştir. Supertrend = Orta Fiyat ± (ATR × Çarpan) formülünü kullanır. ATR yükseldikçe Supertrend bantları genişler ve stop seviyesi uzaklaşır; bu volatiliteye adaptasyondur."},
      {"q": "ATR stop-loss neden sabit yüzde stop'tan iyidir?", "a": "Sabit yüzde stop (%5 gibi) piyasanın volatilitesini görmezden gelir. Çok oynak hissede %5 çok dar, durağan hissede çok geniş olabilir. ATR tabanlı stop ise hissenin kendi volatilitesine göre dinamik olarak ayarlanır, gereksiz stop-out'ları azaltır."},
      {"q": "ATR sadece hisse senedi için mi kullanılır?", "a": "Hayır. ATR her finansal varlıkta kullanılabilir: forex (USD/TRY gibi), kripto para (BTC), emtia (altın, petrol), endeksler (BIST30, S&P500). Hesaplama prensibi aynıdır."}
    ],
    "related_tickers": ['AKBNK', 'THYAO', 'ASELS', 'EREGL', 'GARAN']
  },

  # ── Makale 32 ──────────────────────────────────────────────────────
  {
    "slug": "macd-indikatoru-nedir",
    "title": "MACD İndikatörü Nedir? Nasıl Yorumlanır?",
    "cat": "Teknik Analiz",
    "read_min": 6,
    "summary": "MACD (Moving Average Convergence/Divergence), trend yönünü ve momentumu aynı anda ölçen en popüler teknik analiz araçlarından biridir. Sinyal üretme kurallarını ve BIST'te nasıl kullanıldığını öğrenin.",
    "body": """## MACD Nedir?

**MACD (Hareketli Ortalama Yakınsama/Iraksama)**, iki üstel hareketli ortalamanın (EMA) farkına dayanan bir momentum indikatörüdür. 1979'da Gerald Appel tarafından geliştirilmiştir.

MACD üç bileşenden oluşur:
- **MACD Hattı** = EMA(12) − EMA(26)
- **Sinyal Hattı** = EMA(9) of MACD
- **Histogram** = MACD − Sinyal Hattı

## MACD Sinyalleri Nasıl Okunur?

### 1. MACD Kesişimleri
- MACD hattı sinyal hattını **yukarı keser** → Alış sinyali
- MACD hattı sinyal hattını **aşağı keser** → Satış sinyali

### 2. Sıfır Çizgisi Kesişimi
- MACD hattı sıfırın **üzerine geçer** → Yükseliş trendi güçleniyor
- MACD hattı sıfırın **altına iner** → Düşüş trendi güçleniyor

### 3. Histogram Yorumu
Histogram büyürse momentum güçleniyor, küçülürse zayıflıyor demektir:
- Pozitif histogram büyüyorsa: Güçlenen yükseliş
- Pozitif histogram küçülüyorsa: Yükseliş yoruluyor, dikkat
- Negatif histogram küçülüyorsa: Düşüş yavaşlıyor, toparlanma beklentisi

### 4. Uyumsuzluk (Divergence)
MACD'nin en güçlü sinyali **uyumsuzluk**tur:
- **Boğa uyumsuzluğu:** Fiyat yeni dip yaparken MACD yeni dip yapmaz → Dönüş sinyali
- **Ayı uyumsuzluğu:** Fiyat yeni zirve yaparken MACD yeni zirve yapmaz → Düzeltme sinyali

## MACD ile BIST Uygulaması

BIST hisselerinde MACD kullanırken dikkat edilmesi gerekenler:

**Haftalık grafikte daha güvenilir.** Günlük MACD çok gürültülüdür, haftalık MACD daha kaliteli sinyal üretir.

**Trend yönüyle kullanın.** MACD'yi yalnız kullanmak yerine EMA veya Supertrend gibi trend filtresiyle birleştirin:
- Trend yukarıysa (EMA12 > EMA99) → yalnızca MACD alım sinyallerini değerlendirin
- Trend aşağıysa → yalnızca satış sinyallerini değerlendirin

**Hacim teyidi şart.** MACD kesişimi düşük hacimde oluşursa güvenilirlik azalır.

## MACD vs RSI — Hangisi Daha İyi?

| Özellik | MACD | RSI |
|---------|------|-----|
| Tip | Trend + Momentum | Momentum (osilatör) |
| Gecikme | Orta | Düşük |
| En iyi kullanım | Trend varlığında | Aşırı alım/satım tespiti |
| Uyumsuzluk | ✅ Çok güçlü | ✅ Güçlü |

**Sonuç:** MACD ve RSI birbirini tamamlar. MACD trend yönünü ve momentumu, RSI aşırı alım/satım bölgelerini gösterir.

## BorsaPusula'da MACD

BorsaPusula'nın sinyal motoru Supertrend + ADX + EMA12/99 kombinasyonunu kullanır. MACD histogram, sinyal sayfalarında destekleyici gösterge olarak sunulur. [Canlı sinyalleri görmek için ana sayfayı ziyaret edin.](/)""",
    "faqs": [
      {"q": "MACD için en iyi periyot ayarları nelerdir?", "a": "Standart ayarlar EMA(12,26,9)'dur. Kısa vadeli trading için (3,10,16) kullanılabilir. BIST günlük grafiklerinde standart 12-26-9 ayarı yeterince iyi performans göstermektedir."},
      {"q": "MACD sıfır çizgisinin önemi nedir?", "a": "MACD hattı sıfırın üzerindeyse EMA12 > EMA26 demektir, yani kısa vadeli ortalama uzun vadeliyi geçmiştir ve yükseliş momentumu var. Sıfırın altındaysa tersi geçerlidir."},
      {"q": "MACD uyumsuzluğu neden önemlidir?", "a": "Uyumsuzluk, fiyat ile momentum arasındaki çelişkiyi gösterir. Fiyat yeni zirve yaparken MACD yapmıyorsa, yükseliş momentumu zayıflıyor demektir ve yakında düzeltme gelebilir. Bu sinyaller çok güvenilir olmakla birlikte kesin değildir."},
      {"q": "MACD ile ne sıklıkla işlem yapılabilir?", "a": "Günlük grafikte MACD ayda 2-5 sinyal üretebilir. Çok kısa vadeli grafikte (15dk) sinyaller çok fazla ve gürültülü olur. Haftalık grafikte sinyaller seyrek ama güvenilir olur."},
      {"q": "MACD'yi Supertrend ile birleştirmek mümkün mü?", "a": "Evet, ikisi çok iyi tamamlar. Supertrend trend yönünü ve stop seviyesini belirler; MACD giriş zamanlaması için kullanılır. Supertrend AL veriyorken MACD kesişimi oluşursa sinyal kalitesi artar."}
    ],
    "related_tickers": ['AKBNK', 'GARAN', 'THYAO', 'SISE', 'KRDMD']
  },

  # ── Makale 33 ──────────────────────────────────────────────────────
  {
    "slug": "destek-direnc-seviyeleri-nedir",
    "title": "Destek ve Direnç Seviyeleri Nedir? Nasıl Belirlenir?",
    "cat": "Teknik Analiz",
    "read_min": 7,
    "summary": "Destek ve direnç seviyeleri, teknik analizin temel taşlarıdır. Fiyatın nerede durduğunu, nerede geri döndüğünü anlamak için bu kavramları öğrenmek şarttır.",
    "body": """## Destek Nedir?

**Destek seviyesi**, fiyatın düşerken *durduğu* veya *geri döndüğü* fiyat bölgesidir. Teknik açıdan bakıldığında, bu seviyede alıcılar satıcıları bastırır ve fiyat düşmeyi durdurur.

Destek seviyelerini oluşturan faktörler:
- Önceki dip noktaları
- Yuvarlak sayılar (100 TL, 50 TL gibi)
- Hareketli ortalamalar (EMA50, EMA200)
- Supertrend çizgisi (AL sinyalinde)
- Fibonacci geri çekilme seviyeleri

## Direnç Nedir?

**Direnç seviyesi**, fiyatın yükselirken *durduğu* veya *geri döndüğü* fiyat bölgesidir. Bu bölgede satıcılar alıcıları bastırır.

Direnç seviyelerini oluşturan faktörler:
- Önceki zirve noktaları
- Yuvarlak sayılar
- Uzun vadeli hareketli ortalamalar (EMA200)
- Supertrend çizgisi (SAT sinyalinde)
- Önceki destek kırıldıktan sonra oluşan dirençler

## Destek ve Direnç'in Temel Özellikleri

### Rol Değişimi
Kırılan destek, dirençe dönüşür; kırılan direnç, desteğe dönüşür. Bu en önemli kuraldır:

```
Fiyat 90 TL desteği aşağı kırarsa → 90 TL artık direnç olur
Fiyat 90 TL direncini yukarı kırarsa → 90 TL artık destek olur
```

### Test Sayısı = Güvenilirlik
Bir seviye ne kadar çok test edilip tutunursa, o kadar güçlüdür:
- 2 kez test → zayıf seviye
- 3-4 kez test → güçlü seviye
- 5+ kez test → çok güçlü, kırılması halinde büyük hareket beklenebilir

### Hacim Teyidi
Destek/direnç bölgesine yaklaşırken hacim artışı önemlidir:
- Desteğe inerken hacim artarsa → Alıcılar devreye giriyor, güçlü destek
- Desteği kırarken hacim artarsa → Güçlü kırılım, sahte değil

## BIST Hisselerinde Pratik Uygulama

### Adım 1: Grafik Çerçevesini Belirle
- **Uzun vadeli destek/direnç:** Haftalık veya aylık grafik
- **Kısa vadeli destek/direnç:** Günlük grafik
- **Giriş noktası:** 4 saatlik veya günlük grafik

### Adım 2: Seviyeleri İşaretle
1. Açık zirveler ve dipleri işaretle
2. Bu seviyelerde birden fazla temas var mı kontrol et
3. Hacmin nasıl davrandığına bak

### Adım 3: Stop-Loss Yerleştir
- AL pozisyonu için: Destek seviyesinin biraz altına stop koy (ATR × 0.5 mesafe)
- SAT pozisyonu için: Direnç seviyesinin biraz üstüne stop koy

### Adım 4: Hedef Fiyat Belirle
- Bir sonraki anlamlı destek/direnç seviyesini hedef al
- Risk/ödül oranının en az 1:2 olmasını hedefle

## Supertrend ile Birleştirme

BorsaPusula'nın sinyalleri, Supertrend çizgisini dinamik destek/direnç olarak kullanır:

- **AL sinyalinde:** Supertrend alt çizgisi → dinamik destek, stop-loss buraya konulur
- **SAT sinyalinde:** Supertrend üst çizgisi → dinamik direnç, stop-loss buraya konulur

Bu yaklaşım, klasik statik destek/direnç yerine piyasanın volatilitesine otomatik adapte olur.

## Yaygın Hatalar

❌ **Tek bir çizgi olarak düşünmek** — Destek/direnç bir çizgi değil, bir *bölge*dir. ±%1-2 tolerans bırakın.

❌ **Küçük zaman diliminde aramak** — 15 dakikalık grafikteki "kritik destek" büyük zaman diliminde anlamsız olabilir.

❌ **Sabır göstermemek** — Fiyat desteğe dokunduktan hemen sonra giriş yerine, tepkiyi onaylayana kadar bekleyin.

❌ **Stop koymamak** — Destek kırılabilir. Her desteğin altına mutlaka stop koyun.

[Canlı Supertrend seviyeleri ve AL/SAT sinyallerini gör →](/)""",
    "faqs": [
      {"q": "Destek ve direnç nasıl çizilir?", "a": "Grafikte önceki zirve ve dip noktalarını bulun. Birden fazla kez fiyatın durduğu veya geri döndüğü seviyeleri yatay çizgilerle işaretleyin. Bu seviyelere ne kadar çok dokunulmuşsa o kadar güçlüdür."},
      {"q": "Yuvarlak sayılar neden önemli destek/direnç seviyeleridir?", "a": "100, 50, 200 gibi yuvarlak sayılar psikolojik olarak önemlidir. Birçok yatırımcı bu seviyelerde emir verir. Bu yüzden bu seviyelerde çok sayıda alış/satış emri birikir ve fiyat buralarda sıkça durur veya geri döner."},
      {"q": "Destek kırılınca ne yapmalı?", "a": "Destek kırılması, piyasanın yukarı yönlü görüşünü bozar. Varsa stop-loss devreye girer. Kırılım güçlüyse (yüksek hacimle) yeni destek seviyesini belirleyip bekleyin. Sahte kırılım ihtimali için hacmi kontrol edin."},
      {"q": "Dinamik destek nedir?", "a": "Hareketli ortalamalar (EMA50, EMA200) veya Supertrend gibi fiyatla birlikte hareket eden göstergeler dinamik destek oluşturur. Statik seviyelerin aksine zamanla değişirler ve trend içinde sürekli fiyatı destekler ya da dirençlendirirler."},
      {"q": "Destek ve direnç seviyeleri ne kadar güvenilirdir?", "a": "Destek/direnç seviyeleri kesin değildir, olasılıksal bir yaklaşımdır. Güçlü seviyeler daha sık tutunur ama bazen kırılır. Bu yüzden her zaman stop-loss kullanmak ve risk yönetimine uymak şarttır."}
    ],
    "related_tickers": ['THYAO', 'AKBNK', 'EREGL', 'FROTO', 'TUPRS']
  },

  # ── Makale 34 ──────────────────────────────────────────────────────
  {
    "slug": "hacim-analizi-nedir",
    "title": "Hacim Analizi: Fiyatı Hacimle Doğrulama",
    "cat": "Teknik Analiz",
    "read_min": 5,
    "summary": "Hacim, fiyat hareketinin arkasındaki 'güç'ü gösterir. Yüksek hacimli kırılımlar ve düşük hacimli hareketler arasındaki farkı anlamak, daha kaliteli giriş noktaları bulmanızı sağlar.",
    "body": """## Hacim Neden Önemlidir?

**Hacim**, belirli bir zaman diliminde alınıp satılan hisse adedidir. Fiyatın nereye gittiğini görürsünüz, hacim ise bu hareketin *ne kadar kararlı* olduğunu söyler.

Temel kural: **Hacim trendin arkasında ise trend güvenilirdir.**

## Hacim Analizi Temel Kuralları

### Kural 1: Kırılım + Hacim = Güçlü Sinyal
Fiyat önemli bir direnç seviyesini kırıyorsa ve hacim normalden %50+ fazlaysa:
- Bu **gerçek bir kırılım** olma ihtimali yüksektir
- Kurumsal yatırımcılar devreye girmiş demektir

Fiyat kırılıyor ama hacim normalin altındaysa:
- **Sahte kırılım** ihtimali yüksektir
- Fiyat çok geçmeden geri dönebilir

### Kural 2: Trend + Hacim
| Fiyat | Hacim | Yorum |
|-------|-------|-------|
| Yükseliyor | Yüksek | ✅ Güçlü yükseliş trendi |
| Yükseliyor | Düşük | ⚠️ Zayıf yükseliş, dikkat |
| Düşüyor | Yüksek | ❌ Güçlü düşüş trendi |
| Düşüyor | Düşük | 🔄 Zayıf düşüş, toparlanma yakın |

### Kural 3: Hacim Uyumsuzluğu
Fiyat yeni zirve yapıyor ama hacim azalıyorsa → yükseliş güç kaybediyor, düzeltme yakın.

Fiyat yeni dip yapıyor ama hacim azalıyorsa → düşüş güç kaybediyor, toparlanma yakın.

## BIST'te Hacim Nasıl Kullanılır?

### Ortalama Hacim Referansı
BorsaPusula, her hisse için 20 günlük ortalama hacmi referans alır. Günlük hacim bu ortalamanın:
- **2x üzerinde:** Yüksek hacim — sinyal güvenilirliği artar
- **1-2x arası:** Normal hacim
- **0.5x altında:** Düşük hacim — sinyaller daha az güvenilir

### Supertrend + Hacim Teyidi
BorsaPusula sinyallerinde hacim teyidi önemli rol oynar:
- AL sinyali + yüksek hacim = **Güçlü AL**, giriş kalitesi yüksek
- AL sinyali + düşük hacim = **Zayıf AL**, kırılım sahte olabilir

Hisse sayfasında "Volume Teyidi" bölümü bu bilgiyi otomatik gösterir.

## Dikkat Edilmesi Gereken Hacim Kalıpları

### Climax Volume (Doruk Hacim)
Uzun bir trendin sonunda normalin 3-5 katı hacim oluşur. Bu genellikle trendin bitmekte olduğunu gösterir:
- Güçlü yükseliş + rekor hacim → kurumsal satış başlamış olabilir
- Güçlü düşüş + rekor hacim → paniksel satışlar bitiyor, dip olabilir

### Volume Dry-Up (Hacim Kuruması)
Trend devam ederken hacim azalır. Bu konsolidasyon döneminin sinyal olabilir:
- Konsolidasyon süresince hacim kurur → kırılım hazırlanıyor
- Kırılım geldiğinde güçlü hacim eşlik etmeli

## Hacim İndikatörleri

En yaygın kullanılanlar:
- **OBV (On-Balance Volume):** Yükselen günlerde hacim ekler, düşende çıkarır. Uyumsuzluklar için kullanılır.
- **Chaikin Money Flow:** Hacim para akışını ölçer. +0.25 üstü güçlü alım baskısı, -0.25 altı güçlü satım baskısı.
- **Volume MA:** 20 günlük hacim ortalaması, referans için kullanılır.

## Özet: Hacim Kontrol Listesi

Her sinyal öncesi şunları kontrol edin:
1. ✅ Hacim ortalamanın üzerinde mi?
2. ✅ Kırılım hacimli mi yoksa hacimsiz mi?
3. ✅ Trend yönüyle hacim uyumlu mu?
4. ✅ Hacim uyumsuzluğu var mı?

[BIST hisselerinin hacim verisini ve AL/SAT sinyallerini gör →](/)""",
    "faqs": [
      {"q": "Hacim analizi için hangi periyot kullanılmalı?", "a": "Günlük grafikte 20 günlük ortalama hacim sık kullanılan referanstır. Kısa vadeli işlemler için 5-10 günlük ortalama daha duyarlıdır. BorsaPusula'nın vol_ratio metriği 20 günlük ortalaması üzerinden hesaplanır."},
      {"q": "Düşük hacimli hisseler nasıl ele alınmalı?", "a": "Düşük hacimli (illik) hisseler, büyük alım-satım emirlerinde fiyatı hızla etkileyebilir. Bu hisselerde teknik analiz daha az güvenilir olur. BIST30 hisselerinin yüksek likiditesi teknik analizin etkinliğini artırır."},
      {"q": "Hisse başına hacim mi endeks hacmi mi önemlidir?", "a": "Her ikisi de önemlidir. Endeks hacmi piyasa genelinin katılımını gösterir. Hisse hacmi ise o spesifik hissede ne kadar para hareket ettiğini gösterir. Kırılım sinyallerinde hisse bazlı hacim daha kritiktir."},
      {"q": "MACD ile hacim birlikte nasıl kullanılır?", "a": "MACD momentum gösterirken hacim bu momentumun gücünü teyit eder. MACD kesişimi oluştuktan sonra hacim de artıyorsa sinyal güçlüdür. MACD kesişti ama hacim yoksa, sahte sinyal ihtimali yüksektir."},
      {"q": "Hacim olmadan teknik analiz yapılabilir mi?", "a": "Yapılabilir ama eksik kalır. Hacim, fiyatın manipülatif mi yoksa gerçek mi olduğunu anlamada kritik rol oynar. Özellikle kırılım sinyallerinde hacim teyidi olmadan işlem açmak risk seviyesini önemli ölçüde artırır."}
    ],
    "related_tickers": ['AKBNK', 'GARAN', 'THYAO', 'EREGL', 'BIMAS']
  },

  # ── Makale 35 ──────────────────────────────────────────────────────
  {
    "slug": "guclu-momentum-hisseleri-nasil-tespit-edilir",
    "title": "Güçlü Momentum Hisseleri Nasıl Tespit Edilir?",
    "cat": "Trading Stratejileri",
    "read_min": 6,
    "summary": "Momentum yatırımcıları, güçlü trend içindeki hisseleri erken tespit ederek üstün getiri elde eder. ADX, Supertrend ve hacim kombinasyonuyla güçlü momentum hisseleri nasıl bulunur?",
    "body": """## Momentum Nedir?

**Momentum**, bir hissenin fiyat hareketinin gücünü ve sürdürülebilirliğini ölçer. "Güçlü momentum" olan hisseler, yükseliş veya düşüşlerini belirli bir süre daha devam ettirme eğilimindedir.

*Momentum yatırımının temel fikri:* Yükselen hisseler yükselmeye, düşen hisseler düşmeye devam eder.

## Güçlü Momentum Göstergeleri

### 1. ADX (Ortalama Yönsel İndeks)

ADX, trendin *yönünü değil, gücünü* ölçer:

| ADX Değeri | Yorum |
|-----------|-------|
| < 20 | Yatay piyasa, zayıf trend |
| 20–25 | Trend oluşmaya başlıyor |
| 25–35 | **Güçlü trend — işlem yapılabilir** |
| 35–50 | Çok güçlü trend |
| > 50 | Aşırı trend, dikkat! |

**Kural:** ADX ≥ 25 olmadan momentum stratejisi uygulamak risklidir.

### 2. Supertrend İndikatörü

Supertrend hem yönü hem de dinamik stop seviyesini gösterir:
- **Yeşil çizgi** (fiyatın altında) = yükseliş momentumu aktif
- **Kırmızı çizgi** (fiyatın üstünde) = düşüş momentumu aktif

Fiyat Supertrend çizgisinin üzerinde ve çizgi uzaklaşıyorsa momentum güçlüdür.

### 3. EMA Hizalaması

Güçlü yükseliş momentumunda:
- EMA 12 > EMA 50 > EMA 200 (tüm kısa vadeli ortalamar uzun vadeliyi geçmiş)
- EMA'lar arasındaki mesafe artıyorsa momentum güçleniyor

### 4. Hacim Teyidi

Güçlü momentum için hacim şart:
- Yükseliş günlerinde hacim ortalamanın **üzerinde** olmalı
- Düşüş günlerinde hacim ortalamanın **altında** olmalı
- "Vol Ratio" ≥ 1.5 güçlü alıcı ilgisine işaret eder

## Güçlü Momentum Hisseleri Nasıl Taranır?

**Filtre kriterleri:**
1. Supertrend = AL (yükseliş trendi aktif)
2. ADX ≥ 25 (trend güçlü)
3. EMA12 > EMA99 (uzun vadeli eğilim yukarı)
4. Sinyal 3+ bar onaylı (geçici sinyal değil)
5. Hacim ≥ ortalamanın 1.2x'i

Bu kriterlerin tamamını sağlayan hisseler en güçlü momentum adaylarıdır.

## BorsaPusula'da Momentum Taraması

[BorsaPusula'nın tarama sayfası](/tarama) bu kriterlerin tamamını uygular:
- "Güçlü Trend" filtresi → Supertrend AL + ADX uyumlu
- "ADX ≥ 25" gelişmiş filtresi → trend gücü doğrulaması
- "Vol Ratio" filtresi → hacim teyidi
- Sinyal güç çubukları → momentum yoğunluğunu görsel olarak gösterir

## Momentum Stratejisinin Riskleri

Momentum stratejisi güçlü olmakla birlikte riskler içerir:

**Geç giriş riski:** Sinyal oluştuktan 5-10 bar sonra girilirse fiyat zirveye yakın olabilir.

**Stop-out riski:** Güçlü momentumda bile geçici düzeltmeler olur. ATR bazlı stop, bu dalgalanmalara alan bırakır.

**Momentum kırılması:** ADX 50+ iken sinyaller çok sık tersine döner. Aşırı yükselmiş hisselerde daha geniş stop kullanın.

**Makro riskler:** TCMB kararı, jeopolitik gelişmeler ve FED açıklamaları tek bir seansta tüm momentumu bozabilir.

## Örnek: BIST'te Momentum Tradeı

Klasik BIST momentum yaklaşımı:
1. BorsaPusula sinyaller sayfasında "⚡ Bugün" filtresi → yeni sinyaller
2. ADX ≥ 25 + hacim teyidi olanları seç
3. Supertrend çizgisi giriş fiyatı olarak kullan
4. SL = Supertrend çizgisi altına 1-2 ATR mesafe
5. TP = giriş fiyatının 2-3x SL mesafesi (R/R ≥ 1:2)

Momentum trading'de disiplin kazanmadan başarı sürdürülebilir değildir.""",
    "faqs": [
      {"q": "Momentum hissesi ne kadar süre elde tutulmalı?", "a": "Supertrend sinyali devam ettiği sürece pozisyon korunabilir. Klasik yaklaşımda sinyal kapanana (Supertrend tersine dönene) veya stop-loss tetiklenene kadar beklenebilir. Bu bazen 2 hafta, bazen 3 ay sürebilir."},
      {"q": "Momentum ve trend takip aynı şey mi?", "a": "Çok benzer stratejilerdir. Trend takip daha uzun vadeli (haftalar-aylar), momentum genellikle daha kısa vadeli (günler-haftalar) olur. Her ikisi de 'güçlü yükselişi takip et' prensibine dayanır."},
      {"q": "ADX 50'nin üzerindeyken ne yapılmalı?", "a": "ADX 50+ aşırı momentum gösterir ve genellikle yakında yavaşlama/düzeltme gelir. Bu seviyede yeni pozisyon açmak yerine mevcut pozisyonun stop'unu sıkılaştırmak veya kısmi kar almak düşünülebilir."},
      {"q": "Düşük ADX'te momentum stratejisi işe yarar mı?", "a": "ADX 20'nin altındayken piyasa yatay hareket eder ve momentum sinyalleri çok fazla false positive üretir. Bu ortamda momentum stratejisi yerine destek/direnç ticareti daha uygun olabilir."},
      {"q": "BorsaPusula'da en güçlü momentum hisseleri nasıl bulunur?", "a": "Ana sayfadaki 'Güçlü Trend' filtresini seçin, ardından gelişmiş filtrelerden 'ADX ≥ 25' ve 'Vol Ratio ≥ 1.5' seçin. Sinyal güç çubukları en yüksek olan hisseler en güçlü momentum adaylarıdır."}
    ],
    "related_tickers": ['AKBNK', 'THYAO', 'GARAN', 'KCHOL', 'BIMAS']
  },

  # ── Makale 36 ──────────────────────────────────────────────────────
  {
    "slug": "mum-grafik-formasyonlari",
    "title": "Mum Grafik Formasyonları: 10 Kritik Sinyal",
    "cat": "Teknik Analiz",
    "read_min": 8,
    "summary": "Mum grafik (candlestick) formasyonları, fiyat dönüşlerini ve devam sinyallerini en erken tespit eden araçlardan biridir. Yatırımcının bilmesi gereken 10 kritik formasyon ve anlamları.",
    "body": """## Mum Grafik Nedir?

**Mum grafik (Candlestick)**, her dönem için dört fiyat noktasını görselleştirir: Açılış, Kapanış, En Yüksek, En Düşük. 17. yüzyılda Japon pirinç tüccarları tarafından geliştirilmiş olan bu sistem, günümüzde en yaygın kullanılan grafik türüdür.

Her mum:
- **Gövde (Body):** Açılış ve kapanış arasındaki fark
- **Fitil (Shadow/Wick):** Gövdenin dışındaki yüksek ve düşük noktalar
- **Renk:** Yeşil/beyaz = kapanış > açılış (yükseliş), Kırmızı/siyah = kapanış < açılış (düşüş)

## Dönüş Formasyonları — 7 Kritik Sinyal

### 1. Doji

Açılış ve kapanış neredeyse aynı fiyatta. Gövde çok küçük, fitiller uzun.

**Anlam:** Alıcı-satıcı dengesi, kararsızlık. Güçlü trend sonrasında doji görülürse dönüş yakın olabilir.

**BIST'te:** Uzun süreli yükselişin ardından doji → kısmi kar alma fırsatı.

### 2. Çekiç (Hammer)

Küçük gövde yukarıda, uzun alt fitil (gövdenin en az 2 katı). Düşüş trendinin sonunda görülür.

**Anlam:** Satıcılar fiyatı aşağı çekti ama alıcılar geri kazandı. Güçlü dönüş sinyali.

**Teyit:** Ertesi gün yeşil mum ile teyit edilirse güvenilirlik artar.

### 3. Ters Çekiç (Inverted Hammer)

Küçük gövde aşağıda, uzun üst fitil. Düşüş trendinin sonunda.

**Anlam:** Alıcılar fiyatı yukarı itmek istedi ama tam başaramadı. Potansiyel dönüş, teyit gerekli.

### 4. Asılı Adam (Hanging Man)

Çekiç ile aynı şekil ama *yükseliş trendinin sonunda* görülür.

**Anlam:** Yükseliş trendinde satış baskısı artıyor. Dikkatli olun!

### 5. Karanlık Bulut Örtüsü (Dark Cloud Cover)

İki mum formasyonu:
1. Güçlü yeşil mum
2. Önceki mumun üzerinde açılıp gövdesinin ortasının altında kapanan kırmızı mum

**Anlam:** Alıcılar kontrolü kaybetti, satıcılar devreye girdi. Yükseliş trendinde ayı dönüşü sinyali.

### 6. Üçlü Karga (Three Black Crows)

Üst üste üç güçlü kırmızı mum, her biri öncekinin kapanışının altında açılır.

**Anlam:** Güçlü satış baskısı, trend dönüşünü teyit eder. Nadiren görülür ama çok güvenilir bir sinyal.

### 7. Engulfing (Yutan Formasyon)

**Boğa Engulfing:** Kırmızı mum ardından tamamen onu kapsayan büyük yeşil mum.

**Ayı Engulfing:** Yeşil mum ardından tamamen onu kapsayan büyük kırmızı mum.

**Anlam:** Önceki günün tüm hareketi tersine döndü. En güvenilir dönüş sinyallerinden biri.

## Devam Formasyonları — 3 Önemli Sinyal

### 8. Marubozu

Fitilsiz veya çok kısa fitilli güçlü mum. Açılıştan kapanışa tek yönlü güçlü hareket.

**Anlam:** Tam kontrol — yeşil marubozu alıcıların, kırmızı marubozu satıcıların tam hakimiyetini gösterir. Trend devam edebilir.

### 9. Spinning Top

Küçük gövde, her iki yönde de uzun fitiller.

**Anlam:** Alıcı-satıcı dengesi, kararsızlık. Devam mı dönüş mü olduğunu sonraki mum belirler.

### 10. Üç Beyaz Asker (Three White Soldiers)

Üst üste üç güçlü yeşil mum, her biri öncekinin üzerinde kapanır.

**Anlam:** Güçlü yükseliş momentumu. Düşüş trendi sonunda görülürse çok güçlü dönüş sinyalidir.

## Mum Formasyonlarını Doğru Kullanmak

Mum formasyonları *tek başına yeterli değildir*. Güvenilirliği artırmak için:

1. **Hacim teyidi:** Dönüş formasyonu yüksek hacimle oluşursa güvenilirlik 2x artar
2. **Destek/Direnç uyumu:** Formasyon önemli bir destek/direnç bölgesinde oluşursa daha anlamlı
3. **Büyük zaman dilimi:** Haftalık grafikte oluşan formasyonlar günlük grafiğe göre çok daha güçlü
4. **Supertrend onayı:** Formasyon Supertrend yönüyle uyumluysa işleme girilebilir

## BorsaPusula Bağlantısı

BorsaPusula'nın sinyal algoritması doğrudan mum formasyonlarına bakmaz; Supertrend + ADX + EMA kombinasyonunu kullanır. Ancak bu sinyaller zaten güçlü mum oluşumlarıyla sık sık örtüşür. [Canlı sinyalleri görmek için ana sayfayı ziyaret edin.](/)""",
    "faqs": [
      {"q": "Mum grafik formasyonları ne kadar güvenilir?", "a": "Tek başına kullanıldığında %50-65 başarı oranına sahiptirler. Hacim teyidi, destek/direnç uyumu ve büyük zaman dilimiyle birleştirildiğinde güvenilirlik %70-80'e çıkabilir. Hiçbir formasyon %100 kesin değildir."},
      {"q": "Çekiç ve ters çekiç arasındaki fark nedir?", "a": "Çekiç'te uzun fitil altta, gövde yukarıdadır; güçlü dönüş sinyalidir. Ters Çekiç'te uzun fitil üstte, gövde alttadır; daha zayıf bir sinyal olup mutlaka teyit gerektir."},
      {"q": "Engulfing formasyon en güvenilir formasyon mudur?", "a": "Boğa ve Ayı Engulfing, en güvenilir tek mum dönüş formasyonları arasında sayılır. Özellikle yüksek hacimle teyit edilmesi halinde çok değerli sinyallerdir. Yine de kesin değildir."},
      {"q": "Doji'yi nasıl yorumlamalıyım?", "a": "Doji tek başına 'piyasa kararsız' der. Anlam kazanması için bağlamı önemlidir. Güçlü bir yükseliş trendinin tepesinde oluşan doji, düşüş uyarısı verebilirken; destek bölgesindeki doji al fırsatı işareti olabilir."},
      {"q": "Mum formasyonlarını BIST'te kullanmak ne kadar etkili?", "a": "BIST'te yabancı yatırımcı oranı düşük olduğundan teknik analiz sinyalleri bazen daha az güvenilir olabilir. Bununla birlikte BIST30 hisseleri yeterli likiditeye sahiptir ve mum formasyonları genel olarak işlevseldir."}
    ],
    "related_tickers": ['AKBNK', 'GARAN', 'THYAO', 'FROTO', 'TUPRS']
  },

  # ── Makale 37 ──────────────────────────────────────────────────────
  {
    "slug": "dolar-tl-borsa-iliskisi",
    "title": "Dolar/TL ve BIST İlişkisi: Kur Yükselince Ne Olur?",
    "cat": "Makro Analiz",
    "read_min": 5,
    "summary": "Türk yatırımcılar için en kritik makro faktörlerden biri kur hareketleridir. USD/TRY artışı BIST'i nasıl etkiler? Hangi sektörler kurdan kazanır, hangisi kaybeder?",
    "body": """## Kur-Borsa İlişkisi Neden Önemli?

Türkiye ekonomisinin dışa açıklığı nedeniyle **USD/TRY kuru, BIST'in en kritik makro değişkenlerinden biridir.** Kur yükseldiğinde (TL değer kaybettiğinde) bazı sektörler kazanırken bazıları kaybeder.

Bu ilişkiyi doğru anlamak; sektör rotasyonunu zamanında görmek ve portföyünüzü kuruma karşı konumlandırmak için şarttır.

## Kur Artışında Kazanan Sektörler

### 1. İhracata Yönelik Şirketler 🟢

Gelirleri dolar/euro bazlı ama maliyetleri TL olan şirketler kur artışından *direkt kazanır*:

- **Otomotiv:** FROTO, TOASO (ihracat ağırlıklı, TL maliyeti düşük)
- **Beyaz eşya / Ev aletleri:** ARCLK, VESTL
- **Tekstil / Konfeksiyon:** İhracatçı şirketler
- **Demir-çelik:** EREGL (hem ihracatçı hem emtia fiyatı USD bazlı)

**Neden kazanır?** 1 dolar gelirleri TL olarak daha fazlaya çevrilir. Yabancı piyasalarda Türk ürünleri daha ucuzladığı için talep artar.

### 2. Turizm Şirketleri (Dolaylı) 🟡

Kur yükseldiğinde Türkiye yabancı turistler için ucuzlar, talep artar:
- Otel şirketleri, havacılık (THYAO özellikle)

**Not:** THYAO yakıt maliyeti USD bazlı olduğu için net etki karmaşıktır.

### 3. Bankalar (Karma) 🟡

Bankalar hem TL hem döviz varlık/yükümlülüklerine sahiptir. Kısa vadede belirsiz etki yaşanır; uzun vadede yüksek enflasyon dönemlerinde kredi büyümesi ve faiz marjı belirleyici olur.

## Kur Artışında Kaybeden Sektörler

### 1. İthalata Bağımlı Şirketler 🔴

Hammaddesi veya ürünleri USD/EUR bazlı olan şirketler:
- **Enerji şirketleri:** Petrol fiyatı USD bazlı → artan maliyet
- **İlaç sektörü:** Bileşenler çoğunlukla ithal
- **Teknoloji dağıtıcıları:** Ürün maliyetleri dolar bazlı
- **Perakende:** Çok sayıda ithal ürün satan şirketler

### 2. Yüksek Döviz Borcu Olan Şirketler 🔴

USD borcu olan şirketlerin borç yükü TL cinsinden artar. Bu şirketlerin kur artışından negatif etkilendiğini görürsünüz.

## Nominal vs Reel Getiri: Dolar Bazında BIST

BIST nominal (TL bazında) çok iyi görünse bile, dolar bazında değerlendirildiğinde farklı bir tablo çıkabilir.

**Örnek hesaplama:**
- BIST endeksi +50% yükseldi (TL bazında)
- Aynı dönemde USD/TRY +40% arttı
- Dolar bazında BIST getirisi: ≈ +7% (50% ÷ 1.4 − 1)

Bu nedenle yabancı yatırımcılar BIST'i **dolar bazında** değerlendirir. BIST/USD'nin güçlendiği dönemler, yabancı ilgisinin arttığı dönemlerdir.

## TCMB Kararlarının Kur Üzerindeki Etkisi

Türkiye'de para politikası ve kur arasındaki ilişki özellikle kritiktir:

- **Faiz artışı** → TL güçlenir (yabancı yatırımcı ilgisi artar) → Kur düşer → İhracatçılar kısmen olumsuz etkilenir
- **Faiz indirimi** → TL zayıflar (yabancı sermaye çıkışı riski) → Kur yükselir → İhracatçılar kazanır ama ithalatçılar kaybeder
- **Ortodoks para politikası** → Enflasyon kontrol altında → TL değer kaybı yavaşlar → Daha istikrarlı BIST ortamı

## BorsaPusula'da Kur Takibi

BorsaPusula'nın **[makro ticker bandı](/),** USD/TRY kurunu anlık olarak gösterir. Kur hareketlerine göre sektör filtresi kullanarak:
- Kur yükselişinde: FROTO, EREGL gibi ihracatçı hisselerin sinyallerini takip edin
- Kur düşüşünde: İthalatçı şirketler ve tüketici sektörü sinyallerini değerlendirin

[Tüm BIST100 hisselerinin canlı sinyallerine bakmak için ana sayfayı ziyaret edin.](/)""",
    "faqs": [
      {"q": "Kur yükselince BIST her zaman düşer mi?", "a": "Hayır. Kur yükselişi piyasayı hem pozitif (ihracatçı şirketler, döviz geliri olanlar) hem negatif (ithalatçılar, döviz borçlular) etkiler. BIST üzerindeki net etki, hangi sektörlerin ağırlıklı olduğuna bağlıdır. Hızlı kur yükselişleri genellikle genel bir risk kaçışına yol açsa da orta vadede ihracat odaklı şirketler kazanır."},
      {"q": "Dolar/TL ve altın arasındaki ilişki nasıl?", "a": "Altın hem USD hem güvenli liman varlığı olduğundan, Türk yatırımcı için TL bazındaki altın fiyatı kur × uluslararası altın fiyatından oluşur. Kur yükselirken uluslararası altın sabit kalsa bile TL bazındaki altın fiyatı artar."},
      {"q": "Yabancı yatırımcı BIST'e ne zaman ilgi gösterir?", "a": "Yabancılar genellikle TL'nin istikrar kazandığı, reel faizin pozitife döndüğü veya BIST'in dolar bazında aşırı değer kaybettiği dönemlerde ilgi gösterir. BIST/USD tarihi düşüklerine yakın seviyeler alım fırsatı olarak değerlendirilebilir."},
      {"q": "Türk şirketlerinin döviz borcu ne kadar önemli?", "a": "Şirket bilançolarında 'net döviz pozisyonu' kritik bir metriktir. Net döviz açığı büyük olan şirketler (borçları alacaklarından fazla), kur artışında zarar yazar. KAP bildirimleri ve yıllık raporlarda bu bilgiye ulaşılabilir."},
      {"q": "Kur korumalı mevduat (KKM) BIST'i nasıl etkiler?", "a": "KKM, TL'nin değer kaybetmesi durumunda Hazine farkı karşıladığından, TL'yi tutmayı cazip kılar. Bu mekanizma güçlüyken TL baskısı sınırlı kalır ve BIST daha istikrarlı seyreder. KKM'nin kaldırılması veya zayıflaması kur riskini artırabilir."}
    ],
    "related_tickers": ['FROTO', 'TOASO', 'EREGL', 'THYAO', 'AKBNK']
  },

  # ── Makale 38 ──────────────────────────────────────────────────────
  {
    "slug": "stokastik-osilatoru-nedir",
    "title": "Stokastik Osilatör Nedir? RSI ile Nasıl Birlikte Kullanılır?",
    "cat": "Teknik Analiz",
    "date": "01.05.2026",
    "read_min": 6,
    "summary": "Stokastik osilatör, fiyatın belirli bir dönemdeki fiyat aralığına göre nerede kapandığını ölçer. Aşırı alım/satım bölgelerini RSI'dan farklı bir perspektifle gösterir. İki göstergeyi birlikte kullanmak sinyal güvenilirliğini artırır.",
    "body": """## Stokastik Osilatör Nedir?

**Stokastik osilatör** (Stochastic Oscillator), George Lane tarafından 1950'lerde geliştirilen bir momentum göstergesidir. Temel fikri şudur: *Yükselen piyasada kapanışlar fiyat aralığının üst yarısında, düşen piyasada ise alt yarısında gerçekleşme eğilimindedir.*

Formül:
```
%K = (Kapanış - En Düşük(n)) / (En Yüksek(n) - En Düşük(n)) × 100
%D = %K'nın n-dönemlik hareketli ortalaması
```

Standart parametre: **%K(14), %D(3)** — yani 14 günlük fiyat aralığı.

## Stokastik Nasıl Okunur?

| Değer | Yorum |
|-------|-------|
| 80+ | Aşırı alım bölgesi — dikkatli olun |
| 20- | Aşırı satım bölgesi — toparlanma yakın olabilir |
| %K > %D | Yükseliş momentumu |
| %K < %D | Düşüş momentumu |

**Kesişim sinyalleri:**
- %K, %D'yi aşağıdan yukarıya keser → Potansiyel **alım** sinyali
- %K, %D'yi yukarıdan aşağıya keser → Potansiyel **satım** sinyali

## Stokastik ile RSI Arasındaki Fark

| Özellik | RSI | Stokastik |
|---------|-----|-----------|
| Ne ölçer? | Fiyat değişimlerinin hızı | Kapanışın fiyat aralığındaki konumu |
| Duyarlılık | Daha pürüzsüz | Daha hızlı/duyarlı |
| Aşırı alım/satım | 70/30 | 80/20 |
| Trend mi, momentum mu? | Her ikisi | Ağırlıklı momentum |
| Yanlış sinyal | Trend piyasada az | Trend piyasada çok |

**Kritik fark:** RSI trend takibi için daha güvenilirken, stokastik yatay piyasalarda daha etkilidir. BorsaPusula'nın sinyal motoru trend gücü için ADX + RSI kombinasyonu kullanır.

## İki Göstergeyi Birlikte Kullanma

Sinyal güvenilirliği için iki göstergenin aynı yönü işaret etmesi tercih edilir:

**Güçlü AL Kombinasyonu:**
1. Stokastik 20'nin altından %K > %D kesişimi
2. RSI 30-50 arası (aşırı satımdan çıkıyor)
3. Fiyat güçlü destek seviyesinde

**Güçlü SAT Kombinasyonu:**
1. Stokastik 80'in üstünden %K < %D kesişimi
2. RSI 70 üzerinde (aşırı alım)
3. Fiyat önemli direnç seviyesinde

## BorsaPusula Sinyalleriyle İlişkisi

BorsaPusula'nın AL sinyali, **ADX ≥ 25 + Supertrend + EMA12/99** üçlü kritere dayanır. RSI, bu sistemde *tamamlayıcı gösterge* olarak kullanılır. [Hisse sayfasındaki](/hisse/AKBNK) sinyal badge'ine hover ettiğinizde RSI değerini görebilirsiniz.

Stokastik osilatörü grafik platformunda ek katman olarak kullanarak, BorsaPusula sinyallerine **ikinci bir momentum teyidi** ekleyebilirsiniz.

## Dikkat Edilmesi Gereken Tuzaklar

1. **Trend piyasasında yanlış sinyal:** Güçlü yükseliş trendinde stokastik uzun süre 80'in üzerinde kalabilir. Bu "aşırı alım" değil, güçlü trendin göstergesidir.
2. **Parametre oyuncağı:** 14 yerine 5 veya 3 kullanmak aşırı duyarlı sinyaller üretir.
3. **Tek başına kullanım:** Stokastik tek başına hiçbir zaman yeterli değildir. Trend onayı için ADX ve Supertrend gibi trend göstergeleri gerekir.

> *"Momentum göstergeleri size nereye gittiğinizi söyler; trend göstergeleri ise ne kadar hızlı gittiğinizi."*""",
    "faqs": [
      {"q": "Stokastik osilatör nedir?",
       "a": "Stokastik osilatör, kapanış fiyatının belirli bir dönemdeki yüksek-düşük aralığına göre konumunu ölçen bir momentum göstergesidir. 0-100 arasında değer alır; 80 üzeri aşırı alım, 20 altı aşırı satım kabul edilir."},
      {"q": "RSI mi stokastik mi daha iyi?",
       "a": "Her ikisinin de farklı güçlü yanları vardır. RSI trend piyasalarda daha güvenilirken, stokastik yatay piyasalarda daha etkilidir. İkisini birlikte kullanmak sinyal güvenilirliğini artırır."},
      {"q": "Stokastik %K ve %D çizgisi ne anlama gelir?",
       "a": "%K hızlı stokastik çizgisidir ve anlık fiyat konumunu gösterir. %D ise %K'nın hareketli ortalamasıdır ve daha pürüzsüz bir sinyal çizgisi sağlar. %K'nın %D'yi keserek üzerine çıkması alım, altına inmesi satım sinyali olarak yorumlanır."},
      {"q": "Stokastik hangi piyasalarda işe yarar?",
       "a": "Stokastik, yatay (range-bound) piyasalarda ve kısa vadeli işlemlerde güçlüdür. Güçlü yükseliş veya düşüş trendlerinde ise uzun süre aşırı alım/satım bölgesinde kalarak yanıltıcı sinyaller üretebilir."},
      {"q": "BorsaPusula stokastik osilatör kullanıyor mu?",
       "a": "BorsaPusula'nın sinyal motoru Supertrend + ADX + EMA üçlü kriterine dayanır. Stokastik doğrudan kullanılmasa da RSI tamamlayıcı gösterge olarak hisse sayfalarında gösterilir. Stokastiği grafik platformunuzda ek teyit için kullanabilirsiniz."}
    ],
    "related_tickers": ['AKBNK', 'GARAN', 'THYAO', 'ASELS', 'TUPRS']
  },

  # ── Makale 39 ──────────────────────────────────────────────────────
  {
    "slug": "kaldirach-ve-marjin-riskleri",
    "title": "Kaldıraç ve Marjin: Borçlanarak Yatırım Yapmanın Riskleri",
    "cat": "Risk Yönetimi",
    "date": "01.05.2026",
    "read_min": 7,
    "summary": "Kaldıraç, hem kazancınızı hem kaybınızı büyütür. Marjin hesabı nasıl çalışır, marjin çağrısı ne demektir ve kaldıraç neden deneyimsiz yatırımcılar için tehlikelidir? Türkiye piyasaları için kapsamlı rehber.",
    "body": """## Kaldıraç (Leverage) Nedir?

**Kaldıraç**, ödünç alınan para kullanarak yatırım büyüklüğünü artırmaktır. Örneğin:

- Sermazye: 10.000 ₺
- 2:1 kaldıraç kullanırsanız: 20.000 ₺ değerinde pozisyon açabilirsiniz
- Hisse %10 yükselirse: 2.000 ₺ kâr (%20 getiri sermayenize)
- Hisse %10 düşerse: 2.000 ₺ zarar (**%20 kayıp sermayenizden**)

Kaldıraç, *hem kazancı hem kaybı* eşit oranda büyütür.

## Marjin Hesabı Nasıl Çalışır?

**Marjin**, borsa hesabınızda açık tutmanız gereken minimum teminat miktarıdır.

### Başlangıç Marjini (Initial Margin)
Pozisyon açmak için gereken minimum teminat. Örneğin %50 başlangıç marjini → 20.000 ₺ pozisyon için 10.000 ₺ nakit gerekir.

### Sürdürme Marjini (Maintenance Margin)
Pozisyon açık tutmak için gereken minimum. Genellikle başlangıç marjininin altındadır (%25-30).

### Marjin Çağrısı (Margin Call) ⚠️
Hesabınızdaki öz sermaye sürdürme marjininin altına düştüğünde aracı kurum sizi arar:
1. Ya ek teminat yatırırsınız
2. Ya da pozisyon otomatik kapatılır (zararla)

## Kaldıraç Riski: Gerçek Senaryo

| Durum | Kaldıraçsız | 2:1 Kaldıraç |
|-------|-------------|---------------|
| Sermaye | 10.000 ₺ | 10.000 ₺ |
| Pozisyon | 10.000 ₺ | 20.000 ₺ |
| Hisse %25 düşer | -2.500 ₺ (%25 kayıp) | -5.000 ₺ (**%50 kayıp**) |
| Hisse %50 düşer | -5.000 ₺ (%50 kayıp) | -10.000 ₺ (**%100 — sıfır**) |

**Kaldıraçla sermayenizi tamamen kaybetmek çok daha kolaydır.**

## Türkiye'de Kaldıraç: Mevzuat ve Uygulamalar

### Hisse Senedi Marjin Kredisi
Türkiye'de aracı kurumlar, BIST hisselerinde marjin kredisi sunar. Yasal çerçeve SPK düzenlemelerine tabidir.

**Dikkat:** Marjin kredisi faizi, hissenin değerlenmesinden daha hızlı birikebilir. Yıllık %30-40 faiz oranlarında, bir hissenin bu maliyeti karşılaması için ciddi bir yükseliş şarttır.

### Türev Piyasalar (VİOP)
Vadeli işlem sözleşmelerinde kaldıraç çok daha yüksektir:
- **BIST30 vadeli:** ~10:1 kaldıraç
- **Döviz vadeli:** ~20-50:1 kaldıraç
- **Kripto:** Bazı platformlarda 100:1'e kadar

Bu piyasalarda deneyimsiz yatırımcılar kısa sürede büyük kayıplar yaşayabilir.

## Kaldıraç Ne Zaman Kullanılabilir?

Kaldıraç, belirli koşullar altında ve **çok küçük miktarlarda** değerlendirilebilir:

1. ✅ Güçlü trend onayı var (ADX ≥ 35, Supertrend onaylı)
2. ✅ Net bir stop-loss seviyesi belirlendi
3. ✅ Toplam pozisyon büyüklüğü portföyün max %10'u
4. ✅ Maksimum 2:1 kaldıraç (daha yüksek = spekülasyon)
5. ✅ Marjin çağrısı riskini karşılayabilecek rezerv nakit var

## BorsaPusula Kullanıcıları İçin Not

BorsaPusula'nın sinyal sistemi, trend gücünü **confirmed** (3+ bar onaylı) ve **entry_quality** metrikleriyle değerlendirir. "IDEAL" veya "İYİ" giriş kalitesi olan, yüksek ADX'li sinyaller bile kaldıraçsız kullanıldığında daha güvenlidir.

> **Altın kural:** Kaldıraç, kazancınızı artırmak için değil, yalnızca çok emin olduğunuz işlemleri *biraz* büyütmek için kullanın. Emin olmak için önce kaldıraçsız deneyin.""",
    "faqs": [
      {"q": "Kaldıraç nedir, basitçe açıklar mısınız?",
       "a": "Kaldıraç, sahip olduğunuzdan daha büyük bir yatırım pozisyonu açmak için borç para kullanmaktır. 2:1 kaldıraç, 10.000 ₺ sermaye ile 20.000 ₺ pozisyon açmak anlamına gelir. Hisse değer kazanırsa kâr iki katına çıkar, değer kaybederse zarar da iki katına çıkar."},
      {"q": "Marjin çağrısı (margin call) nedir?",
       "a": "Kaldıraçlı pozisyonunuz zarara uğradığında ve hesabınızdaki teminat minimum seviyenin altına düştüğünde aracı kurum 'marjin çağrısı' yapar. Ya ek teminat yatırmanız ya da pozisyonunuzun otomatik kapatılmasına izin vermeniz gerekir."},
      {"q": "BIST hisselerinde kaldıraç kullanabilir miyim?",
       "a": "Evet, SPK lisanslı aracı kurumlar marjin kredisi sunar. Ancak Türkiye'de marjin faizi yüksektir ve kreditli işlem, hissenin değer kazancının faiz maliyetini karşılamasını gerektirir."},
      {"q": "Kaldıraç yeni başlayan yatırımcılar için uygun mu?",
       "a": "Hayır. Kaldıraç, hem teknik analiz hem de risk yönetimi konusunda deneyim gerektiren ileri seviye bir araçtır. Yeni yatırımcıların önce kaldıraçsız işlem yaparak piyasayı öğrenmeleri tavsiye edilir."},
      {"q": "Kaç yıllık deneyimden sonra kaldıraç kullanılabilir?",
       "a": "Kural değil, bireysel yetkinliğe bağlıdır. Ancak en az 2-3 yıl sürekli kaldıraçsız işlem geçmişi, net bir kâr-zarar kaydı ve sağlam bir risk yönetimi disiplini olmadan kaldıraç önerilmez."}
    ],
    "related_tickers": ['AKBNK', 'GARAN', 'ISCTR', 'THYAO', 'EREGL']
  },

  # ── Makale 40 ──────────────────────────────────────────────────────
  {
    "slug": "dca-duzenli-yatirim-stratejisi",
    "title": "DCA (Düzenli Yatırım) Stratejisi: Ortalama Maliyet Düşürme Nedir?",
    "cat": "Strateji",
    "date": "01.05.2026",
    "read_min": 6,
    "summary": "Dollar-Cost Averaging (DCA), belirli aralıklarla sabit miktarda yatırım yaparak piyasa zamanlaması riskini azaltan bir stratejidir. BIST'te DCA nasıl uygulanır, avantajları ve sınırlılıkları nelerdir?",
    "body": """## DCA (Dollar-Cost Averaging) Nedir?

**Düzenli Yatırım Stratejisi** (DCA — Dollar-Cost Averaging), piyasanın nerede olduğundan bağımsız olarak **belirli aralıklarla sabit bir miktar yatırım** yapma yöntemidir.

Örneğin:
- Her ay 1.000 ₺ BIST30 endeks fonu veya seçili bir hisse alırsınız
- Fiyat düşükse daha fazla lot, yüksekse daha az lot alırsınız
- Zaman içinde ortalama maliyetiniz, piyasanın ortalamasına yaklaşır

## DCA Nasıl Çalışır? Somut Örnek

| Ay | Hisse Fiyatı | Yatırım | Alınan Lot | Toplam Lot |
|----|-------------|---------|------------|------------|
| Ocak | 100 ₺ | 1.000 ₺ | 10 | 10 |
| Şubat | 80 ₺ | 1.000 ₺ | 12,5 | 22,5 |
| Mart | 60 ₺ | 1.000 ₺ | 16,7 | 39,2 |
| Nisan | 90 ₺ | 1.000 ₺ | 11,1 | 50,3 |
| Mayıs | 110 ₺ | 1.000 ₺ | 9,1 | 59,4 |

**Toplam yatırım:** 5.000 ₺
**Ortalama maliyet:** 5.000 / 59,4 = **84,2 ₺**
**Son fiyat:** 110 ₺ → **%31 kâr** (tek seferde 100 ₺'den alsaydınız: %10)

## DCA'nın Avantajları

1. **Piyasa zamanlaması riski yok:** "Dip nerede?" sorusuna cevap aramaya gerek kalmaz
2. **Duygusal disiplin:** Panik satış ve FOMO alımları azalır
3. **Volatilite arkadaşınız olur:** Düşüşler daha ucuz alım fırsatıdır
4. **Basitlik:** Karmaşık analiz gerektirmez, herkes uygulayabilir
5. **Yeni başlayanlar için ideal:** Piyasayı öğrenirken risk sınırlı kalır

## DCA'nın Sınırlamaları

1. **Güçlü yükseliş trendinde alt-performans:** Fiyat sürekli yükseliyorsa, her ay daha pahalıya alırsınız
2. **Likidite sorunları:** Aylık düzenli gelir gerektiriyor
3. **Kötü varlık seçimi:** DCA işe yaramaz bir hisseyi düzenli almayı cazip göstermeyin
4. **İnsan psikolojisi:** Hisse düşünce "daha çok al" dürtüsü DCA'yı bozabilir

> **Kritik nokta:** DCA, iyi bir varlık seçimini değiştirmez. Temelden sorunlu bir şirkete DCA yapmak, kayıplarınızı ortalamanızdan ibaret olacaktır.

## BIST'te DCA: Hangi Varlıklara?

### Endeks Fonları (Önerilen)
BYF (Borsa Yatırım Fonu) veya hisse senedi fonu üzerinden BIST100 veya BIST30'a DCA, bireysel hisse riskini ortadan kaldırır.

### Bireysel Hisseler — Teknik Filtreli DCA
BorsaPusula sinyallerini DCA ile kombine etmek mümkündür:
1. **Sinyal yoksa:** Düzenli yatırımını endeks fonuna yönelt
2. **AL sinyali + düşük giriş maliyeti:** O hisseye DCA'nın bir kısmını yönelt
3. **SAT sinyali:** O hissede DCA'yı durdur, endekse yönelt

### Kur Riski — TL DCA
Türk yatırımcı için TL'nin değer kaybı riski önemlidir. Uzun vadeli DCA stratejisinde döviz bazlı varlıkları (altın, USD fonu) portföyün bir kısmına dahil etmek denge sağlar.

## Uygulama Önerileri

**Başlangıç için:**
- Aylık gelirin %10-20'sini ayır
- İlk hedef: 12 aylık düzenli alım
- Endeks fonu + 1-2 sektör lideri hisse kombinasyonu

**İleri seviye:**
- BorsaPusula'da [AL sinyalinde olan hisselere](/tarama) odaklan
- Yüksek ADX + uzun süredir aktif sinyal → DCA için tercih et
- Quarterly rebalancing: Her çeyrekte portföy dağılımını gözden geçir

> *"Piyasada zaman geçirmek, piyasayı zamanlamaya çalışmaktan daha önemlidir."* — Warren Buffett""",
    "faqs": [
      {"q": "DCA stratejisi nedir?",
       "a": "DCA (Dollar-Cost Averaging veya Düzenli Yatırım), belirli aralıklarla (aylık, haftalık) sabit miktarda yatırım yapma yöntemidir. Fiyat düşükse daha fazla, yüksekse daha az birim alınır ve zamanla ortalama maliyet düzleşir."},
      {"q": "DCA ile ortalama maliyet düşürme aynı mı?",
       "a": "Hayır, farklıdır. DCA, düzenli aralıklarla sabit miktarda alım yapmaktır. 'Ortalama maliyet düşürme' ise fiyat düştükçe daha fazla alarak mevcut maliyetin altına inmektir. DCA önceden planlanmışken, ortalama düşürme genellikle reaktif bir karardır."},
      {"q": "BIST'te DCA uygulamak için hangi hisseleri seçmeliyim?",
       "a": "DCA için en güvenli seçim endeks fonlarıdır (BYF — BIST100 veya BIST30). Bireysel hissede ise sektör lideri, güçlü bilanço ve uzun vadeli büyüme hikayesi olan şirketlere odaklanılmalıdır. BorsaPusula'da uzun süredir AL sinyalinde olan, yüksek ADX'li hisseler teknik açıdan desteklenmiş seçenekler sunar."},
      {"q": "Ne kadar sıklıkla DCA yapmalıyım?",
       "a": "Aylık DCA en yaygın ve pratik yöntemdir. Maaş aldıktan hemen sonra otomatik olarak yatırıma yönlendirmek, psikolojik bariyer oluşturmaz. Haftalık DCA daha küçük miktarlarda da uygulanabilir ancak işlem maliyetleri önemli hale gelebilir."},
      {"q": "DCA piyasa çöküşünde işe yarar mı?",
       "a": "Evet, özellikle piyasa çöküşlerinde DCA en etkili biçimde çalışır. Her düşüş, aynı miktarla daha fazla birim almak anlamına gelir. Uzun vadeli bir varlıksa, toparlanma sonrası ortalama maliyet avantajı belirginleşir. Ancak bunun için sabır ve disiplin gereklidir."}
    ],
    "related_tickers": ['AKBNK', 'THYAO', 'GARAN', 'BIMAS', 'KCHOL']
  },

  # ── Makale 41 ──────────────────────────────────────────────────────
  {
    "slug": "sektor-rotasyonu-nedir",
    "title": "Sektör Rotasyonu Nedir? Hangi Sektöre Ne Zaman Yatırım Yapılır?",
    "cat": "Strateji",
    "date": "01.05.2026",
    "mins": 7,
    "desc": "Ekonomik döngünün farklı evrelerinde hangi sektörlerin öne çıktığını, sektör rotasyonu stratejisini ve BIST'te nasıl uygulandığını öğrenin.",
    "body": """<p>Piyasanın her köşesi aynı anda yükselemez. Faiz döngüsü, ekonomik büyüme ve enflasyon, sektörleri farklı hız ve yönlerde etkiler. Bu gerçeği fırsata dönüştürmenin adı <strong>sektör rotasyonu</strong>'dur.</p>

<h2>Ekonomik Döngü ve Sektörler</h2>
<p>Klasik ekonomik döngü dört evreden oluşur ve her evrede farklı sektörler öne çıkar:</p>

<table>
<thead><tr><th>Döngü Evresi</th><th>Özellikler</th><th>Güçlü Sektörler</th></tr></thead>
<tbody>
<tr><td><strong>Toparlanma</strong></td><td>Düşük faiz, artan talep, yükselen güven</td><td>Teknoloji, Tüketim, Sanayi</td></tr>
<tr><td><strong>Büyüme</strong></td><td>Güçlü büyüme, yükselen gelirler</td><td>Finans, Enerji, Hammadde</td></tr>
<tr><td><strong>Yavaşlama</strong></td><td>Faizler yüksek, büyüme ivme kaybediyor</td><td>Sağlık, Tüketim Zorunluları, Kamu</td></tr>
<tr><td><strong>Resesyon</strong></td><td>Daralma, işsizlik, deflasyon korkusu</td><td>Altın, Nakit, Tahvil</td></tr>
</tbody>
</table>

<h2>BIST'te Sektör Rotasyonu Nasıl İzlenir?</h2>
<p>Türkiye piyasasında sektör rotasyonu, küresel dinamiklerden farklı bir şekilde işler. TCMB faiz politikası, kur hareketleri ve siyasi gelişmeler, sektörlerin performansını küresel döngüden bağımsız biçimde şekillendirebilir.</p>

<h3>1. Bankacılık ve Finans</h3>
<p>Faiz artış dönemlerinde net faiz marjı yükselen bankalar kazanır. Ancak TCMB politika belirsizliğinde bankacılık sektörü yüksek volatilite yaşar. <strong>Net faiz marjı (NIM)</strong> ve <strong>kredi büyüme oranı</strong> izlenmesi gereken temel metriklerdir.</p>

<h3>2. Enerji ve Kimya</h3>
<p>Petrol fiyatları yükseldiğinde BIST'teki enerji hisseleri (TUPRS, BIMAS vb.) öne çıkar. Türkiye net enerji ithalatçısı olduğundan enerji fiyatları aynı zamanda cari açığı etkiler — bu da TL üzerinde baskı yaratabilir.</p>

<h3>3. İhracatçı Sanayi</h3>
<p>Kur yükseldiğinde döviz geliri olan ihracatçı şirketler (FROTO, TOASO, EREGL) kazanır. Bu hisseler TL değer kaybına karşı doğal bir hedge görevi görür.</p>

<h3>4. GYO ve Konut</h3>
<p>Enflasyonun yüksek olduğu dönemlerde gayrimenkul değerlendiği için GYO hisseleri avantajlı konuma geçer. Ancak faiz artışları GYO değerlemelerini baskı altına alabilir.</p>

<h2>Sektör Rotasyonu Stratejisini Nasıl Uygularsınız?</h2>
<ol>
<li><strong>Makro bağlamı belirleyin:</strong> TCMB faizi artırıyor mu, indiriyor mu? Enflasyon yüksekse hangi sektörler korunma sağlar?</li>
<li><strong>Teknik sinyali filtreleyin:</strong> BorsaPusula'da sektör bazlı AL sinyal yoğunluğunu inceleyin. Hangi sektörde AL sinyali veren hisse oranı yüksek?</li>
<li><strong>Relatif güç karşılaştırması:</strong> Sektörün BIST100'e göre relatif performansına bakın. BIST100 düşerken sektör daha az düşüyorsa güçlü görünümdedir.</li>
<li><strong>Rotasyona dikkat:</strong> Haber akışı veya kurumsal yatırımcı hareketleri hangi sektörü ön plana çıkarıyor?</li>
</ol>

<h2>BorsaPusula Sektör Verileri</h2>
<p>BorsaPusula ana sayfasındaki <strong>Sektör filtresi</strong>, tüm sektörlerin güncel AL/SAT/BEKLE sinyal dağılımını anlık gösterir. Kimya/Malzeme ve Enerji gibi sektörlerde AL sinyal yoğunluğu arttığında, bu sektörlere olan kurumsal ilginin arttığına işaret edebilir.</p>

<p><a href="/">Ana sayfada sektör bazlı sinyalleri filtreleyin →</a></p>""",
    "faqs": [
      {"q": "Sektör rotasyonu nedir?",
       "a": "Ekonomik döngünün farklı evrelerinde farklı sektörler öne çıkar — bunu takip ederek öne çıkmakta olan sektörlere yatırımı yönlendirme stratejisine sektör rotasyonu denir."},
      {"q": "BIST'te en güçlü sektörü nasıl bulabilirim?",
       "a": "BorsaPusula ana sayfasındaki sektör filtresi, her sektördeki AL/SAT/BEKLE sinyal dağılımını gösterir. AL sinyal yoğunluğu yüksek sektörler teknik açıdan güçlüdür."},
      {"q": "Bankacılık sektörü ne zaman güçlenir?",
       "a": "Faiz artış dönemlerinde net faiz marjı yükselen bankalar genellikle kazanır. Ancak Türkiye'de TCMB belirsizliği bu ilişkiyi karmaşıklaştırabilir. Kredi büyümesi ve NIM takip edilmesi gereken metriklerdir."},
      {"q": "İhracatçı sektörler ne zaman öne çıkar?",
       "a": "TL değer kaybederken döviz gelirleri olan ihracatçı sanayi şirketleri (otomotiv, çelik, savunma) fayda görür. Bu hisseler aynı zamanda kur riskine karşı bir hedge unsuru olabilir."},
      {"q": "Sektör rotasyonu ETF stratejisiyle uyumlu mu?",
       "a": "BIST'te sektör bazlı ETF seçeneği sınırlı olsa da sektör lider hisselerine küçük pozisyonlar alarak rotasyon stratejisi uygulanabilir. Her yatırım aracında olduğu gibi risk yönetimi önceliklidir."}
    ],
    "related_tickers": ['TUPRS', 'EREGL', 'AKBNK', 'FROTO', 'TOASO']
  },

  # ── Makale 42 ──────────────────────────────────────────────────────
  {
    "slug": "trend-takip-stratejisi",
    "title": "Trend Takip Stratejisi: Trende Ortak Olmak Neden İşe Yarar?",
    "cat": "Strateji",
    "date": "01.05.2026",
    "mins": 6,
    "desc": "Trend takip stratejisi, fiyatın mevcut yönünde devam edeceği varsayımıyla çalışır. Supertrend, EMA ve ADX birleşimi güçlü trendleri nasıl yakalar?",
    "body": """<p>"Trend dostunuzdur." Borsa dünyasının en eski ve en sağlam prensiplerinden biri. Ama trendi doğru tanımlamak, zamanında girmek ve doğru çıkış noktasını belirlemek ayrı birer sanattır.</p>

<h2>Trend Takip Stratejisi Nedir?</h2>
<p><strong>Trend takip (trend following)</strong>, fiyatın mevcut yönünde devam edeceği varsayımıyla alım veya satım pozisyonu almayı içeren bir yaklaşımdır. Temel mantık şudur: <em>Güçlü bir trend başladığında, o trend genellikle beklenen süreden daha uzun sürer.</em></p>

<p>Bu strateji, "dibden al, tepeden sat" mantığına karşı durur. Aksine şöyle der: <em>"Trendin başladığını gördüğünde katıl, bitmediği sürece bekle."</em></p>

<h2>Üç Temel Bileşen</h2>
<p>BorsaPusula'nın sinyal motoru tam da bu prensibe dayanır: Üç indikatörün aynı anda aynı yönü göstermesi.</p>

<h3>1. Supertrend — Trend Yönü</h3>
<p>Supertrend göstergesi, ATR bazlı dinamik destek/direnç çizer. Fiyat bu çizginin üzerindeyken yükseliş trendi, altındayken düşüş trendi devam ediyor demektir. Basit, net, gecikmesi düşük.</p>

<h3>2. ADX ≥ 25 — Trend Gücü</h3>
<p>ADX (Average Directional Index), trendin ne kadar güçlü olduğunu 0-100 arası ölçer. ADX &gt; 25 olduğunda trend "güçlü" kabul edilir. ADX 20'nin altındayken yatay piyasada sinyal üretmek yanıltıcıdır.</p>

<h3>3. EMA12 &gt; EMA99 — Momentum Onayı</h3>
<p>Kısa vadeli hareketli ortalamanın (EMA12) uzun vadeliyi (EMA99) aşması, yükseliş momentumunun yerleştiğini gösterir. Bu iki ortalama arasındaki mesafe büyüdükçe trend güçlenir.</p>

<h2>Neden Üç İndikatörün Aynı Anda Onaylaması?</h2>
<p>Tek bir gösterge her zaman yanıltabilir. Supertrend yanlış kırılım üretebilir; ADX yüksek ama trend tersine dönüyor olabilir; EMA geçişi de bazen gürültülü olabilir. Üç koşulun birlikte sağlanması, yanlış sinyal olasılığını önemli ölçüde azaltır.</p>

<table>
<thead><tr><th>Senaryo</th><th>ST</th><th>ADX</th><th>EMA</th><th>Sonuç</th></tr></thead>
<tbody>
<tr><td>Güçlü AL</td><td>▲ Yeşil</td><td>≥ 25</td><td>12 &gt; 99</td><td>✅ Pozisyon gir</td></tr>
<tr><td>Zayıf Onay</td><td>▲ Yeşil</td><td>&lt; 25</td><td>12 &gt; 99</td><td>⚠️ Bekle</td></tr>
<tr><td>Karışık</td><td>▲ Yeşil</td><td>≥ 25</td><td>12 &lt; 99</td><td>⚠️ Bekle</td></tr>
<tr><td>Güçlü SAT</td><td>▼ Kırmızı</td><td>≥ 25</td><td>12 &lt; 99</td><td>❌ Pozisyondan çık</td></tr>
</tbody>
</table>

<h2>Giriş ve Çıkış Kuralları</h2>
<ul>
<li><strong>Giriş:</strong> Üç koşul aynı anda sağlandığında, ilk kapanıştan sonra giriş. Gecikme riskini azaltmak için ATR bazlı giriş bölgesi kullanılır.</li>
<li><strong>Stop loss:</strong> Supertrend çizgisinin hemen altı — trendin bozulduğunu kanıtlayan seviye.</li>
<li><strong>Kâr alma:</strong> TP1 = 1.5× ATR, TP2 = 3× ATR; ya da Supertrend çizgisi kırıldığında.</li>
<li><strong>Çıkış:</strong> Supertrend SAT'a geçtiğinde veya ADX 20'nin altına indiğinde.</li>
</ul>

<h2>Trend Takibin Zayıf Yönleri</h2>
<p>Hiçbir strateji kusursuz değildir. Trend takibinin bilinen tuzakları:</p>
<ul>
<li><strong>Yatay piyasada yüksek kayıp:</strong> Trend olmayan dönemlerde çok sayıda küçük zararlı sinyal üretilir.</li>
<li><strong>Gecikmeli giriş:</strong> Trend başladıktan bir süre sonra sinyali almak, %20-30 hareketi kaçırmak anlamına gelebilir.</li>
<li><strong>Ani tersine dönüş riski:</strong> Güçlü trend aniden bozulabilir; bu nedenle stop loss kritik önem taşır.</li>
</ul>

<p>BorsaPusula sinyallerinin geçmiş performans analizine <a href="/sinyal-performans">Sinyal Performans sayfasından</a> ulaşabilirsiniz.</p>""",
    "faqs": [
      {"q": "Trend takip stratejisi nedir?",
       "a": "Fiyatın mevcut yönünde devam edeceği varsayımıyla hareket eden bir yatırım yaklaşımıdır. 'Dibe yakın al, tepeye yakın sat' değil; 'trend başladığında katıl, trend bitmeden çık' mantığıyla çalışır."},
      {"q": "ADX neden 25 olarak seçildi?",
       "a": "ADX 25, piyasanın trend mi yoksa yatay mı olduğunu ayırt etmek için yaygın olarak kabul edilen eşik değeridir. 25'in altı genellikle gürültülü, yatay piyasayı işaret eder; 25 ve üzeri trendin gerçekten güçlendiğine işaret eder."},
      {"q": "Supertrend ne zaman yanlış sinyal verir?",
       "a": "Volatilitenin ani arttığı dönemlerde, özellikle yatay piyasada, Supertrend sık sık yön değiştirir. Bu nedenle ADX filtresi kritik önem taşır — trend gücü zayıfken Supertrend sinyalleri güvenilir değildir."},
      {"q": "Stop loss nereye koyulmalı?",
       "a": "Trend takip stratejisinde stop loss tipik olarak Supertrend çizgisinin biraz altına (AL için) veya üstüne (SAT için) yerleştirilir. Bu seviyenin kırılması trendin bozulduğuna işaret eder."},
      {"q": "Kâr alma hedefleri nasıl belirlenir?",
       "a": "BorsaPusula TP1 için ~1.5×ATR, TP2 için ~3×ATR kullanır. Aktif yönetimde ise Supertrend çizgisinin kırılması güçlü bir çıkış sinyali olarak değerlendirilebilir."}
    ],
    "related_tickers": ['AKBNK', 'GARAN', 'THYAO', 'ASELS', 'EREGL']
  },

  # ── Makale 43 ──────────────────────────────────────────────────────
  {
    "slug": "rsi-uyusmazligi-divergence",
    "title": "RSI Uyuşmazlığı (Divergence): Trend Dönüşünü Erkenden Yakalamak",
    "cat": "Teknik Analiz",
    "date": "01.05.2026",
    "mins": 6,
    "desc": "RSI uyuşmazlığı (divergence), fiyat ve momentum arasındaki ayrışmayı gösterir. Gizli uyuşmazlık, açık uyuşmazlık ve pratik kullanım rehberi.",
    "body": """<p>Fiyat yeni zirve yapıyor, ama RSI yapmıyor. Ya da tam tersi. Bu tutarsızlık, trend dönüşünün habercisi olabilir. İşte <strong>RSI uyuşmazlığı (divergence)</strong> adı verilen güçlü sinyal tekniği.</p>

<h2>Uyuşmazlık Nedir?</h2>
<p>Uyuşmazlık, fiyat hareketi ile bir gösterge (burada RSI) arasındaki <em>zıt yönlü hareket</em>'tir. Fiyat bir yöne giderken RSI farklı bir yön izliyorsa, bu momentumun zayıfladığına işaret eder.</p>

<h2>İki Tür Uyuşmazlık</h2>

<h3>1. Açık Uyuşmazlık (Regular Divergence) — Trend Dönüşü Sinyali</h3>
<table>
<thead><tr><th>Tür</th><th>Fiyat</th><th>RSI</th><th>Sinyal</th></tr></thead>
<tbody>
<tr><td><strong>Ayı uyuşmazlığı</strong></td><td>Yeni yüksek ↑</td><td>Daha düşük tepe ↓</td><td>Düşüş uyarısı ⚠️</td></tr>
<tr><td><strong>Boğa uyuşmazlığı</strong></td><td>Yeni düşük ↓</td><td>Daha yüksek dip ↑</td><td>Yükseliş fırsatı 📈</td></tr>
</tbody>
</table>

<p><strong>Ayı uyuşmazlığı örneği:</strong> Fiyat 100'den 110'a çıkarken RSI 70'ten 65'e düşüyorsa, yukarı hareket giderek zayıflıyor demektir. Alıcılar yoruluyor.</p>

<p><strong>Boğa uyuşmazlığı örneği:</strong> Fiyat 50'den 45'e inerken RSI 30'dan 35'e çıkıyorsa, aşağı baskı azalıyor demektir. Satıcılar yoruluyor.</p>

<h3>2. Gizli Uyuşmazlık (Hidden Divergence) — Trend Devamı Sinyali</h3>
<table>
<thead><tr><th>Tür</th><th>Fiyat</th><th>RSI</th><th>Sinyal</th></tr></thead>
<tbody>
<tr><td><strong>Gizli boğa</strong></td><td>Daha yüksek dip ↑</td><td>Daha düşük dip ↓</td><td>Yükseliş devamı ✅</td></tr>
<tr><td><strong>Gizli ayı</strong></td><td>Daha düşük tepe ↓</td><td>Daha yüksek tepe ↑</td><td>Düşüş devamı ✅</td></tr>
</tbody>
</table>

<p>Gizli uyuşmazlık, trendin devam edeceğini gösteren "trend içi düzeltme" sinyalidir. Yükseliş trendinde her dip biraz daha yüksek yapılıyorsa ve RSI daha düşük dip yapıyorsa, bu trend içi alım fırsatı olabilir.</p>

<h2>RSI Uyuşmazlığını Nasıl Tanımlarsınız?</h2>
<ol>
<li>Grafikte iki anlamlı tepe veya dip belirleyin (en az 5-10 bar aralıklı).</li>
<li>RSI'da da aynı noktalardaki değerlere bakın.</li>
<li>Fiyat ile RSI zıt yön gösteriyorsa uyuşmazlık vardır.</li>
<li><strong>Kritik:</strong> Uyuşmazlık tek başına giriş sinyali değildir — destek/direnç kırılımı veya başka bir onay bekleyin.</li>
</ol>

<h2>Güçlü Sinyal için Ek Filtreler</h2>
<p>RSI uyuşmazlığı güçlü bir araç olsa da yanıltabilir. Güvenilirliği artırmak için:</p>
<ul>
<li><strong>Supertrend + RSI divergence:</strong> Supertrend yön değiştirdiğinde uyuşmazlık mevcut mu?</li>
<li><strong>Hacim onayı:</strong> Uyuşmazlık noktasında hacim artışı güveni artırır.</li>
<li><strong>Destek/direnç:</strong> Uyuşmazlık kritik bir seviyede mi oluşuyor?</li>
<li><strong>Zaman dilimi uyumu:</strong> Haftalık grafikte uyuşmazlık + günlük grafikte giriş sinyali en güçlü kombinasyondur.</li>
</ul>

<h2>BorsaPusula'da Uyuşmazlık Nasıl İzlenir?</h2>
<p>Her hisse detay sayfasında RSI değeri ve grafik üzerinde fiyat hareketleri görülebilir. RSI 70 üzerindeyken fiyat yeni zirve yapıyorsa ve RSI önceki zirveyi kıramıyorsa, bu durumu göz önünde bulundurun.</p>

<p>Unutmayın: BorsaPusula sinyali 3 indikatörün <em>hizalanmasını</em> arar — uyuşmazlık bu hizalamayı bozabilir ve sinyali zayıflatabilir. <a href="/">Anlık sinyalleri inceleyin →</a></p>""",
    "faqs": [
      {"q": "RSI uyuşmazlığı (divergence) nedir?",
       "a": "Fiyat yeni zirve ya da dip yaparken RSI aynı hareketi yapmıyorsa bu uyuşmazlık (divergence) olarak adlandırılır. Fiyat ile momentum arasındaki bu ayrışma, olası trend dönüşünün habercisidir."},
      {"q": "Açık ve gizli uyuşmazlık arasındaki fark nedir?",
       "a": "Açık uyuşmazlık olası bir trend dönüşüne işaret ederken, gizli uyuşmazlık mevcut trendin devam ettiğini gösterir. Gizli uyuşmazlık, trend içi geri çekilmelerde pozisyon eklemek için kullanılır."},
      {"q": "RSI uyuşmazlığı her zaman işe yarar mı?",
       "a": "Hayır. Güçlü bir trend sırasında uyuşmazlık uzun süre devam edebilir. Bu nedenle uyuşmazlık tek başına yeterli değildir — destek/direnç kırılımı veya hacim onayı gibi ek filtreler gereklidir."},
      {"q": "Hangi zaman diliminde uyuşmazlığa bakmalıyım?",
       "a": "Yüksek zaman dilimlerindeki (haftalık, günlük) uyuşmazlıklar daha güvenilirdir. Günlük grafikte uyuşmazlık görülüp haftalık grafikte de destekleniyorsa sinyal güçlenir."},
      {"q": "RSI uyuşmazlığı ile Supertrend birlikte kullanılabilir mi?",
       "a": "Evet, bu kombinasyon çok değerlidir. Supertrend yön değiştirdiği anda RSI'da da uyuşmazlık varsa bu iki ayrı kaynaktan gelen trend dönüş sinyalidir ve güvenilirliği artar."}
    ],
    "related_tickers": ['AKBNK', 'GARAN', 'THYAO', 'TUPRS', 'ASELS']
  },

  # ── ARTICLE 44 ─────────────────────────────────────────────────────────────
  {
    "slug": "halka-arz-ipo-nedir",
    "title": "Halka Arz (IPO) Nedir? Nasıl Katılınır?",
    "desc": "Halka arz sürecini, nasıl talep toplama yapıldığını, avantajlarını ve risklerini anlatan kapsamlı rehber. BIST'teki halka arzlara nasıl başvurulur?",
    "cat": "Temel Kavramlar",
    "date": "01.05.2026",
    "mins": 7,
    "body": """
<p>Halka arz (İPO — Initial Public Offering), bir şirketin hisselerini ilk kez kamuya açık olarak piyasaya sürmesidir. Bu süreç, hem şirket hem yatırımcılar için kritik önem taşır.</p>

<h2>Halka Arz Neden Yapılır?</h2>
<p>Şirketler çeşitli amaçlarla halka açılır:</p>
<ul>
  <li><strong>Büyüme finansmanı:</strong> Yeni fabrika, teknoloji yatırımı veya pazar genişlemesi için sermaye toplamak</li>
  <li><strong>Borç ödeme:</strong> Mevcut borçları halka arz gelirleriyle kapatmak</li>
  <li><strong>Marka bilinirliği:</strong> Halka açık şirket statüsü kurumsal itibar sağlar</li>
  <li><strong>Ortaklar için çıkış:</strong> Mevcut hissedarlar kısmen veya tamamen çıkabilir</li>
</ul>

<h2>BIST'te Halka Arz Süreci Nasıl İşler?</h2>
<p>Türkiye'de halka arz süreci şu aşamalardan oluşur:</p>
<ol>
  <li><strong>SPK (Sermaye Piyasası Kurulu) onayı:</strong> Şirket izahname hazırlar, SPK inceler ve onaylar</li>
  <li><strong>Yatırım bankası seçimi:</strong> Aracı kurum işlemi organize eder (talep toplama, fiyat belirleme)</li>
  <li><strong>Talep toplama dönemi:</strong> Yatırımcılar aracı kurumlar üzerinden talep iletir (genellikle 3-5 gün)</li>
  <li><strong>Fiyat tespiti:</strong> Gelen taleplere göre hisse fiyatı belirlenir</li>
  <li><strong>Dağıtım ve borsa kotasyonu:</strong> Hisseler dağıtılır, BIST'te işlem görmeye başlar</li>
</ol>

<h2>Halka Arza Nasıl Talep Verilir?</h2>
<p>Bireysel yatırımcı olarak halka arza katılmak için:</p>
<ul>
  <li>Yatırım hesabınızın olduğu aracı kurumun mobil uygulamasına veya internet şubesine girin</li>
  <li>"Halka Arz" veya "IPO" bölümüne gidin</li>
  <li>Talep miktarını (lot sayısı) ve fiyatı (genellikle sabit fiyat veya fiyat aralığı) girin</li>
  <li>Talep süresinde yeterli bakiyeniz bloke edilir</li>
  <li>Dağıtım sonrası hesabınıza düşen hisseler otomatik yatırılır, artı bakiye iade edilir</li>
</ul>
<div style="background:rgba(59,130,246,.07);border:1px solid rgba(59,130,246,.15);border-radius:8px;padding:14px;margin:16px 0">
  <strong style="color:#58a6ff">💡 Pratik Bilgi:</strong> Yoğun talep gören halka arzlarda oransal dağıtım yapılır. 100 lot talep ettiyseniz, dağıtım oranı %10 ise yalnızca 10 lot alabilirsiniz. Kalan bakiye iade edilir.
</div>

<h2>Halka Arzın Avantajları</h2>
<ul>
  <li><strong>İlk günden potansiyel kazanç:</strong> Talep fazla olan halka arzlarda ilk işlem gününde önemli fiyat artışı yaşanabilir</li>
  <li><strong>Erken aşamada giriş:</strong> Şirkete piyasa değerlendirmesinden önce girilir</li>
  <li><strong>Düşük giriş fiyatı:</strong> Benzer şirketlere göre iskontolu fiyat sunulabilir</li>
</ul>

<h2>Halka Arzın Riskleri</h2>
<p>Her halka arz kazançla sonuçlanmaz. Dikkat edilmesi gereken riskler:</p>
<ul>
  <li><strong>Geçmiş performans garantisi yok:</strong> İlk gün yükselen hisseler sonrasında düşebilir</li>
  <li><strong>Bilgi asimetrisi:</strong> Mevcut hissedarlar şirketi sizden çok daha iyi tanır</li>
  <li><strong>Lock-up süresi sona erince satış baskısı:</strong> Halka arz öncesi ortakların hisselerinin satış kısıtı kalktığında fiyat düşebilir</li>
  <li><strong>Yüksek değerleme:</strong> Spekülatif yüksek fiyatla işlem görme riski</li>
</ul>

<h2>Bir Halka Arza Katılmadan Önce Sorulacak Sorular</h2>
<ul>
  <li>Şirketin iş modeli sürdürülebilir mi?</li>
  <li>Son 3 yıl gelir ve kâr büyümesi nasıl?</li>
  <li>Piyasa değeri / kazanç oranı sektör ortalamasının neresinde?</li>
  <li>Halka arz gelirleri ne için kullanılacak?</li>
  <li>Aracı kurum raporu ve izahname incelendi mi?</li>
</ul>
<div style="background:rgba(248,81,73,.07);border:1px solid rgba(248,81,73,.15);border-radius:8px;padding:14px;margin:16px 0">
  <strong style="color:#f85149">⚠️ Dikkat:</strong> Halka arzlar her zaman kazanç sağlamaz. BIST tarihinde halka arz fiyatının altına düşen birçok hisse mevcuttur. Temel analiz yapmadan yalnızca "halka arz" etiketiyle talep vermek risklidir.
</div>

<h2>Sonuç</h2>
<p>Halka arzlar, seçici yaklaşıldığında portföye değer katabilir. Fiyat iskontosu ve ilk gün prim potansiyeli cezbedici olsa da izahname okumak, şirketin temel değerini anlamak ve piyasa koşullarını değerlendirmek uzun vadeli başarı için zorunludur.</p>
""",
    "faqs": [
      {"q": "Halka arz talep etmek için ne kadar bakiye gerekir?",
       "a": "Asgari talep miktarı halka arza göre değişir; genellikle 1-10 lot (1 lot = 100 hisse) ile başlanabilir. Talep dönemi boyunca bu bakiye bloke kalır."},
      {"q": "Talep verdiğim hisse bana kesin dağıtılır mı?",
       "a": "Hayır. Talep yoğunluğuna göre oransal dağıtım yapılır. Aşırı talep gören halka arzlarda dağıtım oranı %5-20 aralığında kalabilir."},
      {"q": "Halka arzda ne zaman satmalıyım?",
       "a": "Bu tamamen stratejinize bağlıdır. Kısa vadeli yatırımcılar ilk günlerde primli satış yaparken uzun vadeli yatırımcılar şirketin büyüme hikayesini takip eder. Sabit bir kural yoktur."},
      {"q": "Hangi aracı kurumdan halka arza başvurabilirim?",
       "a": "Türkiye'de lisanslı tüm aracı kurumlar üzerinden halka arz talebinde bulunabilirsiniz. Bazı halka arzlar yalnızca belirli aracı kurumlar aracılığıyla yapılır; izahname ve duyurularda belirtilir."}
    ],
    "related_tickers": ['AKBNK', 'THYAO', 'ASELS', 'EREGL', 'FROTO']
  },

  # ── ARTICLE 45 ─────────────────────────────────────────────────────────────
  {
    "slug": "etf-byf-nedir",
    "title": "ETF / BYF Nedir? Borsa Yatırım Fonu Rehberi",
    "desc": "ETF (Exchange Traded Fund) ve BYF (Borsa Yatırım Fonu) nedir, hisse senedinden farkı nedir, BIST'te işlem gören fonlar ve nasıl yatırım yapılır?",
    "cat": "Temel Kavramlar",
    "date": "01.05.2026",
    "mins": 6,
    "body": """
<p>ETF (Exchange Traded Fund — Borsa İşlem Gören Fon), Türkçe'de BYF (Borsa Yatırım Fonu) olarak da bilinir. Hisse senetleri gibi borsada alınıp satılabilen, genellikle bir endeksi veya emtiayı takip eden yatırım araçlarıdır.</p>

<h2>ETF Nasıl Çalışır?</h2>
<p>Bir ETF, içinde birden fazla varlık (hisse, tahvil, emtia vb.) barındıran bir "sepet" gibidir. Siz bu sepeti tek bir işlemle satın alırsınız:</p>
<ul>
  <li><strong>BIST100 ETF:</strong> İçinde BIST100 endeksindeki tüm hisseler oransal ağırlıklarla bulunur</li>
  <li><strong>Altın ETF:</strong> Fiziksel altın fiyatını takip eder</li>
  <li><strong>Temettü ETF:</strong> Yüksek temettü veren hisseleri bir araya getirir</li>
</ul>

<h2>ETF ile Hisse Senedi Arasındaki Farklar</h2>
<table style="width:100%;border-collapse:collapse;font-size:13px;margin:16px 0">
  <thead>
    <tr style="background:#21262d">
      <th style="padding:10px;text-align:left;border:1px solid #30363d">Özellik</th>
      <th style="padding:10px;text-align:left;border:1px solid #30363d">ETF / BYF</th>
      <th style="padding:10px;text-align:left;border:1px solid #30363d">Hisse Senedi</th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <td style="padding:9px;border:1px solid #30363d">Çeşitlendirme</td>
      <td style="padding:9px;border:1px solid #30363d;color:#3fb950">✅ Tek işlemle onlarca hisse</td>
      <td style="padding:9px;border:1px solid #30363d;color:#f85149">❌ Tek şirket riski</td>
    </tr>
    <tr style="background:#1a2030">
      <td style="padding:9px;border:1px solid #30363d">Şirket analizi</td>
      <td style="padding:9px;border:1px solid #30363d;color:#3fb950">✅ Gerekmez</td>
      <td style="padding:9px;border:1px solid #30363d;color:#f85149">❌ Detaylı analiz şart</td>
    </tr>
    <tr>
      <td style="padding:9px;border:1px solid #30363d">Yönetim ücreti</td>
      <td style="padding:9px;border:1px solid #30363d">Yıllık %0.05–0.5</td>
      <td style="padding:9px;border:1px solid #30363d">Yok (sadece alım-satım komisyonu)</td>
    </tr>
    <tr style="background:#1a2030">
      <td style="padding:9px;border:1px solid #30363d">Potansiyel getiri</td>
      <td style="padding:9px;border:1px solid #30363d">Endeks getirisi</td>
      <td style="padding:9px;border:1px solid #30363d">Endeksi aşabilir veya altında kalabilir</td>
    </tr>
    <tr>
      <td style="padding:9px;border:1px solid #30363d">Temettü</td>
      <td style="padding:9px;border:1px solid #30363d">Bazı ETF'ler yansıtır</td>
      <td style="padding:9px;border:1px solid #30363d">Şirkete göre değişir</td>
    </tr>
  </tbody>
</table>

<h2>BIST'te İşlem Gören Önemli ETF'ler</h2>
<ul>
  <li><strong>BIST100 BYF'leri (XU100E, IST100, vb.):</strong> Türk hisse piyasasını takip eder</li>
  <li><strong>Altın BYF'leri (GOLD, AKB, CALTM vb.):</strong> Altın fiyatına endeksli, kur riskini de içerir</li>
  <li><strong>Yabancı endeks ETF'leri:</strong> S&P500 veya NASDAQ'ı Türk lirası cinsinden takip eden ürünler</li>
  <li><strong>Gümüş, petrol BYF'leri:</strong> Emtia fiyatlarını takip eden fonlar</li>
</ul>

<h2>ETF Yatırımının Avantajları</h2>
<ul>
  <li><strong>Anında çeşitlendirme:</strong> Tek bir alım işlemiyle onlarca hisseye sahip olursunuz</li>
  <li><strong>Düşük maliyet:</strong> Aktif yönetilen fonlara göre çok daha düşük yönetim ücreti</li>
  <li><strong>Şeffaflık:</strong> İçerdiği varlıklar her gün açıklanır</li>
  <li><strong>Likidite:</strong> Borsa saatlerinde hisse gibi alınıp satılabilir</li>
  <li><strong>Başlangıç için ideal:</strong> Analiz bilgisi gerekmeden piyasaya girilebilir</li>
</ul>

<h2>ETF Yatırımının Riskleri</h2>
<ul>
  <li>Endeks düşünce ETF de düşer — piyasa geneli riskinden kaçış yoktur</li>
  <li>Yabancı ETF'lerde kur riski ekstra volatilite yaratır</li>
  <li>Dar işlem hacimli ETF'lerde alım-satım spread'i yüksek olabilir</li>
</ul>

<h2>Kimler İçin Uygundur?</h2>
<div style="background:rgba(63,185,80,.07);border:1px solid rgba(63,185,80,.15);border-radius:8px;padding:14px;margin:16px 0">
  <strong style="color:#3fb950">✅ ETF şu yatırımcılar için idealdir:</strong>
  <ul style="margin:8px 0 0 0">
    <li>Borsaya yeni başlayanlar — tek hisse seçme stresini ortadan kaldırır</li>
    <li>Uzun vadeli, pasif yatırımcılar — piyasa getirisini yakalamak yeterli</li>
    <li>Portföyünü çeşitlendirmek isteyenler — mevcut hisselere ETF eklemek dengeler</li>
    <li>Altın, emtia veya yabancı hisselere kolayca ulaşmak isteyenler</li>
  </ul>
</div>
<p>Aktif trader profili için bireysel hisse senetleri ve teknik analiz araçları daha uygun olabilir. BorsaPusula'nın sunduğu sinyal sistemi bu ihtiyacı karşılar.</p>
""",
    "faqs": [
      {"q": "ETF ve yatırım fonu aynı şey midir?",
       "a": "Hayır. Yatırım fonları fon yöneticisi tarafından aktif yönetilir ve günde bir kez fiyatlanır. ETF'ler ise borsada hisse gibi anlık alınıp satılır ve genellikle pasif (endeks takip) yapıdadır. ETF maliyetleri genelde çok daha düşüktür."},
      {"q": "BIST'te ETF alabilmek için ne gerekir?",
       "a": "Herhangi bir aracı kurumda yatırım hesabı açmanız yeterlidir. ETF'ler hisseler gibi lot bazında alınır; minimum 1 lot ile başlanabilir."},
      {"q": "ETF'ler temettü öder mi?",
       "a": "Bazı ETF'ler içerdiği hisselerin temettülerini yatırımcıya yansıtır (temettü dağıtımlı ETF). Bazıları ise temettüleri fona geri yatırır (birikimli ETF). Ürün belgesinden kontrol edilmelidir."},
      {"q": "Altın ETF almak ile fiziksel altın almak arasındaki fark nedir?",
       "a": "Altın ETF elektronik olarak alınır, depolama/güvenlik sorunu yoktur ve borsada anlık satılabilir. Fiziksel altında ise işçilik farkı ve likidite dezavantajı bulunur. Her ikisi de altın fiyatını takip eder."}
    ],
    "related_tickers": ['TUPRS', 'AKBNK', 'GARAN', 'THYAO', 'EREGL']
  },

  # ── ARTICLE 46 ─────────────────────────────────────────────────────────────
  {
    "slug": "borsada-vergi-hisse-senedi-kazanc",
    "title": "Borsada Vergi: Hisse Senedi Kazancı Nasıl Vergilendirilir? (2026)",
    "desc": "BIST hisse senedi alım satım kazançlarında stopaj, temettü vergisi ve yıllık beyan yükümlülüğü. Türkiye'de borsa vergisi rehberi 2026.",
    "cat": "Temel Kavramlar",
    "date": "01.05.2026",
    "mins": 7,
    "body": """
<p>Borsa yatırımlarında vergi konusu bireysel yatırımcılar arasında en çok karışıklığa yol açan konulardan biridir. Bu rehber, Türkiye'de BIST hisse senedi işlemlerinde 2026 itibarıyla geçerli vergilendirme kurallarını özetlemektedir.</p>
<div style="background:rgba(248,81,73,.07);border:1px solid rgba(248,81,73,.15);border-radius:8px;padding:14px;margin:16px 0">
  <strong style="color:#f85149">⚠️ Önemli Uyarı:</strong> Bu içerik genel bilgi amaçlıdır, vergi danışmanlığı değildir. Kişisel durumunuz için mutlaka mali müşavir veya vergi uzmanına başvurun. Vergi mevzuatı değişebilir.
</div>

<h2>BIST Hisse Senedi Alım Satım Kazancı — Stopaj</h2>
<p>Türkiye'de tam mükellef gerçek kişiler için BIST'te kote edilmiş hisse senetlerinde alım satım kazancı üzerinden <strong>%0 stopaj</strong> uygulanmaktadır (Gelir Vergisi Kanunu Geçici Madde 67).</p>
<p>Bu istisna yalnızca BIST'te işlem gören hisseler için geçerlidir. Yabancı borsalarda veya tezgahüstü piyasada işlem gören hisseler farklı kurallara tabidir.</p>

<h2>Temettü Gelirlerinde Vergi</h2>
<p>Türk şirketlerinin dağıttığı temettüler üzerinden <strong>%15 stopaj</strong> kesilir. Bu kesinti aracı kurum tarafından otomatik yapılır ve size net tutar yatırılır.</p>
<ul>
  <li>Temettü geliri yıllık 230.000 TL'yi (2026 tahmini sınır, her yıl güncellenir) aşarsa <strong>beyanname verilmesi</strong> gerekebilir</li>
  <li>Yıllık toplam temettü geliriniz bu sınırın altındaysa ayrıca beyan yükümlülüğünüz yoktur</li>
  <li>Stopaj nihai vergi olarak kabul edilir çoğu durumda</li>
</ul>

<h2>Hisse Senedi Alım Satım Kazancı Beyanı Gerekir mi?</h2>
<p>BIST'te işlem gören hisse senetlerinden elde edilen kazançlar için:</p>
<ul>
  <li>%0 stopaj uygulanır → Aracı kurum otomatik keser (kesilecek bir şey yok)</li>
  <li>Bu kazançlar için yıllık gelir vergisi beyannamesi verilmesi gerekmez</li>
  <li><strong>İstisna:</strong> Aynı yıl hem BIST hem yabancı borsa geliri varsa durum karmaşıklaşabilir</li>
</ul>
<div style="background:rgba(59,130,246,.07);border:1px solid rgba(59,130,246,.15);border-radius:8px;padding:14px;margin:16px 0">
  <strong style="color:#58a6ff">💡 Pratik Not:</strong> Aracı kurumunuz yıl sonunda "yıllık kazanç/kayıp özeti" belgesi düzenler. Bu belgeyi saklayın; olası bir vergi incelemesinde gerekli olabilir.
</div>

<h2>Zarar Mahsubu — Kayıpları Kazançtan Düşmek</h2>
<p>Stopaj matrahı hesaplanırken aynı takvim yılı içindeki kayıplar kazançlardan mahsup edilebilir. Örneğin:</p>
<ul>
  <li>AKBNK'tan 50.000 TL kazandınız, EREGL'den 20.000 TL kaybettiniz → net kazanç 30.000 TL üzerinden stopaj hesaplanır</li>
  <li>Bir yılda toplam zarar ettiyseniz bu zarar sonraki yıla devredilebilir (aynı kategoride)</li>
</ul>

<h2>Kaldıraçlı İşlemler (Forex, Varant) Vergisi</h2>
<p>Bu ürünler BIST hisse senetlerinden farklı vergilendirmeye tabidir:</p>
<ul>
  <li><strong>Vadeli işlem ve opsiyon (VIOP):</strong> %0 stopaj (BIST bünyesinde)</li>
  <li><strong>Forex, CFD:</strong> Farklı uygulama söz konusu olabilir — uzman görüşü alın</li>
  <li><strong>Kripto para:</strong> 2026 itibarıyla kripto varlıklar Türkiye'de ayrı vergi düzenlemesine tabidir</li>
</ul>

<h2>Kurumsal Yatırımcılar İçin Farklı Kurallar</h2>
<p>Bu rehber tam mükellef gerçek kişilere yönelik hazırlanmıştır. Şirket hesabıyla yatırım yapıyorsanız, kurumlar vergisi hükümleri farklı uygulanır; mali müşavirinize danışın.</p>

<h2>Özet Tablo</h2>
<table style="width:100%;border-collapse:collapse;font-size:13px;margin:16px 0">
  <thead>
    <tr style="background:#21262d">
      <th style="padding:10px;text-align:left;border:1px solid #30363d">Gelir Türü</th>
      <th style="padding:10px;text-align:left;border:1px solid #30363d">Stopaj Oranı</th>
      <th style="padding:10px;text-align:left;border:1px solid #30363d">Beyanname</th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <td style="padding:9px;border:1px solid #30363d">BIST hisse alım satım kazancı</td>
      <td style="padding:9px;border:1px solid #30363d;color:#3fb950">%0</td>
      <td style="padding:9px;border:1px solid #30363d">Gerekmez (genel kural)</td>
    </tr>
    <tr style="background:#1a2030">
      <td style="padding:9px;border:1px solid #30363d">Temettü geliri</td>
      <td style="padding:9px;border:1px solid #30363d">%15</td>
      <td style="padding:9px;border:1px solid #30363d">Eşiği aşarsa gerekebilir</td>
    </tr>
    <tr>
      <td style="padding:9px;border:1px solid #30363d">VIOP kazancı</td>
      <td style="padding:9px;border:1px solid #30363d;color:#3fb950">%0</td>
      <td style="padding:9px;border:1px solid #30363d">Gerekmez (genel kural)</td>
    </tr>
    <tr style="background:#1a2030">
      <td style="padding:9px;border:1px solid #30363d">Yabancı borsa kazancı</td>
      <td style="padding:9px;border:1px solid #30363d;color:#f85149">Tabi olabilir</td>
      <td style="padding:9px;border:1px solid #30363d;color:#f85149">Uzman görüşü alın</td>
    </tr>
  </tbody>
</table>
""",
    "faqs": [
      {"q": "BIST'te hisse alım satımından vergi ödenir mi?",
       "a": "Tam mükellef gerçek kişiler için BIST'te kote hisse senetlerinde alım satım kazancı üzerinden stopaj oranı %0'dır (GVK Geçici 67. Madde kapsamında). Ancak mevzuat değişebilir; güncel bilgi için vergi danışmanınıza danışın."},
      {"q": "Temettü almak vergiye tabi mi?",
       "a": "Evet. Dağıtılan temettüler üzerinden %15 stopaj kesilir. Yıllık toplam temettü geliriniz yasal sınırı aşarsa beyanname vermeniz gerekebilir."},
      {"q": "Bir hisseden zarar ettim, başka bir hisseden kazandım. Vergi nasıl hesaplanır?",
       "a": "Aynı yıl içindeki hisse kayıpları kazançlardan mahsup edilebilir. Net kazanç üzerinden stopaj hesaplanır. Yıl sonu kazanç/kayıp özeti için aracı kurumunuzla iletişime geçin."},
      {"q": "Yabancı hisse veya kripto kazançlarım için ne yapmalıyım?",
       "a": "Yabancı borsa kazançları ve kripto para gelirleri BIST hisselerinden farklı kurallara tabidir. Bu konularda mutlaka mali müşavir veya vergi uzmanına danışmanız önerilir."}
    ],
    "related_tickers": ['AKBNK', 'GARAN', 'THYAO', 'KCHOL', 'EREGL']
  },

  # ── ARTICLE 47 ─────────────────────────────────────────────────────────────
  {
    "slug": "yatirim-fonu-mu-hisse-mi",
    "title": "Yatırım Fonu mu, Hisse Senedi mi? Hangisi Daha İyi?",
    "desc": "Yatırım fonu ile hisse senedini karşılaştıran kapsamlı rehber. Başlangıç yatırımcısından deneyimli trader'a kim hangisini tercih etmeli?",
    "cat": "Strateji",
    "date": "01.05.2026",
    "mins": 6,
    "body": """
<p>Borsaya yeni başlayanların ve portföyünü büyütmek isteyenlerin sıkça sorduğu soru: "Yatırım fonu mu alsam, yoksa direkt hisse senedi mi?" Her iki aracın kendine özgü avantajları, riskleri ve uygun kullandığı yatırımcı profilleri vardır.</p>

<h2>Yatırım Fonu Nedir?</h2>
<p>Yatırım fonu, bir fon yöneticisinin birçok yatırımcının parasını bir havuzda toplayıp çeşitli varlıklara (hisse, tahvil, döviz vb.) yatırım yaptığı kolektif bir yapıdır. Türkiye'de TEFAS (Türkiye Elektronik Fon Alım Satım Platformu) üzerinden alınabilir.</p>

<h2>Temel Karşılaştırma</h2>
<table style="width:100%;border-collapse:collapse;font-size:13px;margin:16px 0">
  <thead>
    <tr style="background:#21262d">
      <th style="padding:10px;text-align:left;border:1px solid #30363d">Kriter</th>
      <th style="padding:10px;text-align:left;border:1px solid #30363d">Yatırım Fonu</th>
      <th style="padding:10px;text-align:left;border:1px solid #30363d">Hisse Senedi</th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <td style="padding:9px;border:1px solid #30363d">Yönetim</td>
      <td style="padding:9px;border:1px solid #30363d">Profesyonel yönetici</td>
      <td style="padding:9px;border:1px solid #30363d">Kendiniz yönetirsiniz</td>
    </tr>
    <tr style="background:#1a2030">
      <td style="padding:9px;border:1px solid #30363d">Çeşitlendirme</td>
      <td style="padding:9px;border:1px solid #30363d;color:#3fb950">Otomatik (düzinelerce varlık)</td>
      <td style="padding:9px;border:1px solid #30363d">Manuel — yeterli sermaye gerekir</td>
    </tr>
    <tr>
      <td style="padding:9px;border:1px solid #30363d">Maliyet</td>
      <td style="padding:9px;border:1px solid #30363d">Yıllık yönetim ücreti %1–3</td>
      <td style="padding:9px;border:1px solid #30363d">Yalnızca alım satım komisyonu</td>
    </tr>
    <tr style="background:#1a2030">
      <td style="padding:9px;border:1px solid #30363d">Getiri potansiyeli</td>
      <td style="padding:9px;border:1px solid #30363d">Fona göre değişir, çoğu endeksi geçemez</td>
      <td style="padding:9px;border:1px solid #30363d;color:#3fb950">Endeksi aşabilir</td>
    </tr>
    <tr>
      <td style="padding:9px;border:1px solid #30363d">Zaman gereksinimi</td>
      <td style="padding:9px;border:1px solid #30363d;color:#3fb950">Düşük — fon yöneticisi takip eder</td>
      <td style="padding:9px;border:1px solid #30363d">Yüksek — düzenli takip şart</td>
    </tr>
    <tr style="background:#1a2030">
      <td style="padding:9px;border:1px solid #30363d">Bilgi gereksinimi</td>
      <td style="padding:9px;border:1px solid #30363d;color:#3fb950">Düşük</td>
      <td style="padding:9px;border:1px solid #30363d">Teknik ve/veya temel analiz</td>
    </tr>
    <tr>
      <td style="padding:9px;border:1px solid #30363d">Likidite</td>
      <td style="padding:9px;border:1px solid #30363d">Genellikle T+1 veya T+2 ödeme</td>
      <td style="padding:9px;border:1px solid #30363d;color:#3fb950">Anlık (borsa saatleri içinde)</td>
    </tr>
    <tr style="background:#1a2030">
      <td style="padding:9px;border:1px solid #30363d">Şeffaflık</td>
      <td style="padding:9px;border:1px solid #30363d">Aylık portföy açıklanır</td>
      <td style="padding:9px;border:1px solid #30363d;color:#3fb950">Anlık fiyat görünür</td>
    </tr>
  </tbody>
</table>

<h2>Yatırım Fonu Avantajları</h2>
<ul>
  <li><strong>Başlangıç için idealdir:</strong> Hangi hisseyi seçeceğinizi bilmeden piyasaya girebilirsiniz</li>
  <li><strong>Profesyonel yönetim:</strong> Tecrübeli fon yöneticileri karar alır</li>
  <li><strong>Düşük başlangıç tutarı:</strong> Bazı fonları 100 TL ile bile alabilirsiniz</li>
  <li><strong>Vergi avantajı:</strong> Fon içinde gerçekleşen alım satımlar stopaj doğurmaz; yalnızca fondan çıkışta vergi hesaplanır</li>
</ul>

<h2>Yatırım Fonu Dezavantajları</h2>
<ul>
  <li><strong>Yönetim ücreti bileşik etkisi:</strong> Yıllık %2 ücret uzun vadede ciddi getiri kaybına yol açar</li>
  <li><strong>Çoğu aktif fon endeksi yenemez:</strong> Global araştırmalar, aktif yönetilen fonların büyük çoğunluğunun 10 yıllık vadede endeksin gerisinde kaldığını gösteriyor</li>
  <li><strong>Anlık işlem yapılamaz:</strong> Fon fiyatı günde bir kez hesaplanır</li>
</ul>

<h2>Hisse Senedi Avantajları</h2>
<ul>
  <li><strong>Daha yüksek getiri potansiyeli:</strong> Doğru seçimde endeksi önemli ölçüde aşabilirsiniz</li>
  <li><strong>Tam kontrol:</strong> Ne aldığınızı, ne zaman aldığınızı ve sattığınızı siz belirlersiniz</li>
  <li><strong>Sıfır yönetim ücreti:</strong> Yalnızca alım satımda komisyon ödersiniz</li>
  <li><strong>Teknik analiz araçları:</strong> BorsaPusula gibi platformlarla sinyal takibi yapabilirsiniz</li>
</ul>

<h2>Hisse Senedi Dezavantajları</h2>
<ul>
  <li>Düşük sermayeyle çeşitlendirme zordur — 5-6 hisse yeterli dağılım sağlamayabilir</li>
  <li>Bireysel şirket riski: Tek bir haberde %20 kayıp yaşanabilir</li>
  <li>Sürekli takip gerektirir — bunu karşılayabilecek zaman ve motivasyon olmalı</li>
</ul>

<h2>Kim Hangisini Seçmeli?</h2>
<div style="display:grid;grid-template-columns:1fr 1fr;gap:14px;margin:16px 0">
  <div style="background:rgba(63,185,80,.07);border:1px solid rgba(63,185,80,.15);border-radius:8px;padding:14px">
    <strong style="color:#3fb950">Yatırım Fonu için:</strong>
    <ul style="margin:8px 0 0 0;font-size:13px">
      <li>Borsaya yeni başlayanlar</li>
      <li>Piyasa takibi için zamanı olmayanlar</li>
      <li>Küçük sermaye (%100K altı)</li>
      <li>Pasif, uzun vadeli yatırımcılar</li>
    </ul>
  </div>
  <div style="background:rgba(59,130,246,.07);border:1px solid rgba(59,130,246,.15);border-radius:8px;padding:14px">
    <strong style="color:#58a6ff">Hisse Senedi için:</strong>
    <ul style="margin:8px 0 0 0;font-size:13px">
      <li>Temel/teknik analiz öğrenenler</li>
      <li>Günlük veya haftalık takip edebilecekler</li>
      <li>Aktif strateji uygulayabilecekler</li>
      <li>Endeksi aşmayı hedefleyenler</li>
    </ul>
  </div>
</div>

<h2>Karma Strateji: İkisini Birden Kullanmak</h2>
<p>Pek çok deneyimli yatırımcı her ikisini birden kullanır:</p>
<ul>
  <li>Portföyün %60'ı endeks ETF veya fon → istikrarlı baz</li>
  <li>Portföyün %30'u seçici hisse senetleri → alfa yaratma denemesi</li>
  <li>Portföyün %10'u yüksek risk/ödül fırsatları (swing trade vb.)</li>
</ul>
""",
    "faqs": [
      {"q": "Yatırım fonu mu daha güvenli, hisse senedi mi?",
       "a": "Her iki araç da piyasa riskine tabidir; 'güvenli' değildirler. Yatırım fonu çeşitlendirme sayesinde tek hisse riskini azaltır, ancak piyasa geneli düşünce fon da düşer. Risk toleransınıza ve bilginize göre karar vermelisiniz."},
      {"q": "Kaç TL ile yatırım fonuna başlanabilir?",
       "a": "Türkiye'de TEFAS üzerinden işlem gören birçok fon, 100 TL gibi çok düşük tutarlarla alınabilmektedir. Bu, küçük birikimlerle bile çeşitlendirme yapılmasına olanak tanır."},
      {"q": "Aktif fon yöneticileri neden endeksi geçemez?",
       "a": "Yönetim ücretleri, alım satım maliyetleri ve insan psikolojisinin (kayıptan kaçınma gibi) etkisiyle aktif fonların büyük çoğunluğu uzun vadede endeksin gerisinde kalır. Bu 'aktif yönetim paradoksu' olarak bilinir."},
      {"q": "BorsaPusula'da teknik sinyalleri kullanarak hisse seçmek mantıklı mı?",
       "a": "Evet. BorsaPusula'nın Supertrend + ADX + EMA kombinasyonu, piyasa trendini takip eden sistematik bir yaklaşım sunar. Bu tür algoritmik araçlar, sezgisel kararların önüne geçerek disiplinli yatırım kararlarını destekler."}
    ],
    "related_tickers": ['AKBNK', 'GARAN', 'THYAO', 'TUPRS', 'ASELS']
  },

  # ── ARTICLE 48 ─────────────────────────────────────────────────────────────
  {
    "slug": "aciga-satis-short-selling-nedir",
    "title": "Açığa Satış (Short Selling) Nedir? BIST'te Mümkün mü?",
    "desc": "Açığa satış nedir, nasıl çalışır, BIST hisse senetlerinde short selling yapılabilir mi? Riskleri ve alternatif stratejiler.",
    "cat": "Strateji",
    "date": "01.05.2026",
    "mins": 6,
    "body": """
<p>Açığa satış (short selling), sahip olmadığınız bir hisseyi ödünç alıp sattıktan sonra fiyat düştüğünde geri alarak iade ettiğiniz ve bu fiyat farkından kâr ettiğiniz bir yatırım stratejisidir. Kısaca "düşüşten para kazanmak" olarak da tanımlanır.</p>

<h2>Açığa Satışın Mantığı</h2>
<p>Normal hisse yatırımında mantık şudur: "Ucuzken al, pahalıyken sat." Açığa satışta bu mantık tersine döner: "Pahalıyken sat, ucuzken al."</p>
<ol>
  <li>Bir aracı kurumdan X hissesini ödünç alırsınız (ödünç işlemi günlük faiz içerir)</li>
  <li>Hisseyi piyasada satarsınız (örn. 100 ₺'den)</li>
  <li>Fiyat düştüğünde hisseyi geri alırsınız (örn. 80 ₺'den)</li>
  <li>Ödünç aldığınız hisseyi iade edersiniz</li>
  <li>Kârınız: 100 − 80 = 20 ₺ (faiz ve komisyon düşülmeden)</li>
</ol>

<h2>BIST'te Açığa Satış Yapılabilir mi?</h2>
<p>Türkiye'de BIST bünyesinde açığa satış işlemi teknik olarak mümkündür; ancak uygulamada ciddi kısıtlamalar vardır:</p>
<ul>
  <li><strong>Açığa satış listesi:</strong> SPK ve BIST, açığa satışa izin verilen hisselerin listesini belirler. Bu liste sınırlıdır ve değişkendir</li>
  <li><strong>Ödünç pay bulma zorluğu:</strong> Aracı kurumunuzun ödünç verebileceği pay bulması gerekir; bu her zaman mümkün olmayabilir</li>
  <li><strong>Piyasa yapıcı yokluğu:</strong> Likit olmayan hisselerde açığa satış neredeyse imkânsızdır</li>
  <li><strong>Yüksek maliyet:</strong> Ödünç alma faizi + spread + komisyon kârı eritebilir</li>
</ul>
<div style="background:rgba(248,81,73,.07);border:1px solid rgba(248,81,73,.15);border-radius:8px;padding:14px;margin:16px 0">
  <strong style="color:#f85149">⚠️ Önemli:</strong> BIST'te bireysel yatırımcıların gerçek anlamda açığa satış yapması oldukça kısıtlı ve zordur. Kurumsal yatırımcılar bu araçlara daha kolay erişir.
</div>

<h2>Açığa Satışın Riskleri</h2>
<p>Normal hisse yatırımında maksimum kaybınız yatırdığınız tutardır (hisse sıfıra giderse). Açığa satışta ise teorik olarak kayıp sınırsızdır:</p>
<ul>
  <li><strong>Sınırsız zarar potansiyeli:</strong> Hisse 100 ₺'den 500 ₺'ye çıkarsa, her payda 400 ₺ zarar edersiniz</li>
  <li><strong>Short squeeze riski:</strong> Kitlesel kapanışlarda fiyat hızla yükselir, zararlar katlanır (GameStop örneği)</li>
  <li><strong>Ödünç geri çağrısı:</strong> Ödünç veren aracı kurum hisseyi geri isteyebilir, kötü zamanda pozisyon kapatmak zorunda kalabilirsiniz</li>
  <li><strong>Temettü yükümlülüğü:</strong> Açık pozisyon tutarken temettü dağıtılırsa, temettüyü hisse sahibine ödemek zorunda kalırsınız</li>
</ul>

<h2>BIST'te Düşüşten Kâr Etmenin Alternatifleri</h2>
<p>Bireysel BIST yatırımcıları için açığa satışa alternatifler:</p>
<ul>
  <li><strong>VIOP (Vadeli İşlem ve Opsiyon Piyasası):</strong> Hisse vadeli sözleşmeleri veya put opsiyonları ile düşüş pozisyonu alınabilir. BIST bünyesinde, daha likit ve erişilebilir</li>
  <li><strong>Ters ETF (Inverse ETF):</strong> Endeksin tersine hareket eden fonlar — BIST'te henüz yaygın değil</li>
  <li><strong>Nakit tutmak:</strong> Düşüş beklentisinde en basit strateji: pozisyonu kapatıp nakit beklemek</li>
  <li><strong>Stop loss ile koruma:</strong> Mevcut uzun pozisyonlarda sıkı stop kullanarak aşağı yönlü kayıpları sınırlamak</li>
</ul>

<h2>BorsaPusula'nın Yaklaşımı</h2>
<p>BorsaPusula sinyalleri BIST hisseleri için "AL" (Güçlü Trend) veya "SAT" (Zayıf Trend) sinyali üretir. "SAT" sinyali, hissenin <strong>zayıf trend içinde olduğunu</strong> gösterir ve mevcut pozisyondan çıkış/kaçınma için işaret olarak kullanılır — açığa satış pozisyonu açmak için değil. Bu yaklaşım, bireysel yatırımcılara karmaşık açığa satış mekaniklerini öğrenmeden trend takibi yapma imkânı sunar.</p>
""",
    "faqs": [
      {"q": "BIST'te herkes açığa satış yapabilir mi?",
       "a": "Hayır. Açığa satış yalnızca SPK'nın onayladığı sınırlı sayıda hisse için mümkündür ve ödünç pay bulunması gerekir. Bireysel yatırımcılar için pratikte oldukça kısıtlı bir araçtır."},
      {"q": "SAT sinyali gördüğümde açığa satış yapmalı mıyım?",
       "a": "BorsaPusula'daki SAT (Zayıf Trend) sinyali, açığa satış için tasarlanmamıştır. Bu sinyal, mevcut pozisyondan çıkış veya o hisseden kaçınma işareti olarak değerlendirilmelidir. Açığa satış tamamen farklı risk ve mekanik içerir."},
      {"q": "Açığa satış yerine VIOP kullanmak daha mı iyi?",
       "a": "BIST bireysel yatırımcıları için düşüş pozisyonu almak istiyorsanız VIOP, açığa satıştan genellikle daha erişilebilir ve likittir. Ancak her iki araç da yüksek risk taşır ve kapsamlı bilgi gerektirir."},
      {"q": "Short squeeze nedir?",
       "a": "Çok fazla yatırımcının açık (short) pozisyon tuttuğu bir hissede ani fiyat artışı yaşanırsa, tüm açıklar pozisyonlarını aynı anda kapatmak zorunda kalır. Bu kapanışlar fiyatı daha da yukarı iter, kâr yerine ciddi zarar oluşturur. Bu olaya 'short squeeze' denir."}
    ],
    "related_tickers": ['ASELS', 'EREGL', 'THYAO', 'TUPRS', 'GARAN']
  },

  # ── ARTICLE 49 ─────────────────────────────────────────────────────────────
  {
    "slug": "hisse-bolunmesi-stock-split-nedir",
    "title": "Hisse Bölünmesi (Stock Split) Nedir? Yatırımcıyı Nasıl Etkiler?",
    "desc": "Hisse bölünmesi nedir, şirket neden hisse böler, bölünme sonrası portföy değeri değişir mi? KAP bildirimi ve pratik etkileri.",
    "cat": "Temel Kavramlar",
    "date": "01.05.2026",
    "mins": 5,
    "body": """
<p>Hisse bölünmesi (stock split), bir şirketin mevcut hisselerini daha küçük birimler halinde bölerek toplam hisse sayısını artırdığı kurumsal bir işlemdir. En yaygın form 1:2 veya 1:5 bölünmedir.</p>

<h2>Hisse Bölünmesi Örneği</h2>
<p>Diyelim ki AKBNK hissesi 150 ₺'den işlem görüyor ve 1:5 (beşe bölünme) bölünme yapıyor:</p>
<ul>
  <li><strong>Bölünme öncesi:</strong> 100 hisseniz var, her biri 150 ₺ → Portföy değeri: 15.000 ₺</li>
  <li><strong>Bölünme sonrası:</strong> 500 hisseniz var, her biri 30 ₺ → Portföy değeri: 15.000 ₺</li>
</ul>
<p>Portföy değeri değişmez! Yalnızca hisse adedi artar, birim fiyat düşer.</p>

<h2>Şirket Neden Hisse Böler?</h2>
<ul>
  <li><strong>Erişilebilirliği artırmak:</strong> Çok yükselen hissenin fiyatı küçük yatırımcı için pahalı hale gelir. Bölünme ile daha geniş yatırımcı kitlesine erişilir</li>
  <li><strong>Likiditeyi artırmak:</strong> Düşük fiyatlı hisseler genellikle daha aktif işlem görür</li>
  <li><strong>Psikolojik etki:</strong> Piyasa katılımcıları düşük fiyatlı hisseleri "ucuz" algılar, talep artabilir</li>
  <li><strong>Endeks dahil olma kuralları:</strong> Bazı endeksler maksimum hisse fiyatı sınırı uygulayabilir</li>
</ul>

<h2>Ters Bölünme (Reverse Split) Nedir?</h2>
<p>Ters bölünmede (veya birleşme) hisse adedi azalır, birim fiyat yükselir. Örneğin 5:1 ters bölünmede 500 hisseniz 100 hisseye düşer ama fiyat 5 katına çıkar. Şirketler genellikle borsa kurallarını karşılamak veya kurumsal görünüm için bu yola başvurur. Ters bölünmeler çoğunlukla zayıf şirketlerin özelliğidir — dikkatli olunmalıdır.</p>

<h2>Hisse Bölünmesi Yatırımcıyı Nasıl Etkiler?</h2>
<table style="width:100%;border-collapse:collapse;font-size:13px;margin:16px 0">
  <thead>
    <tr style="background:#21262d">
      <th style="padding:10px;text-align:left;border:1px solid #30363d">Etki</th>
      <th style="padding:10px;text-align:left;border:1px solid #30363d">Açıklama</th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <td style="padding:9px;border:1px solid #30363d">Portföy değeri</td>
      <td style="padding:9px;border:1px solid #30363d;color:#3fb950">Değişmez — matematiksel olarak aynı</td>
    </tr>
    <tr style="background:#1a2030">
      <td style="padding:9px;border:1px solid #30363d">Hisse adedi</td>
      <td style="padding:9px;border:1px solid #30363d">Bölünme oranında artar</td>
    </tr>
    <tr>
      <td style="padding:9px;border:1px solid #30363d">Birim fiyat</td>
      <td style="padding:9px;border:1px solid #30363d">Bölünme oranında düşer</td>
    </tr>
    <tr style="background:#1a2030">
      <td style="padding:9px;border:1px solid #30363d">Vergi</td>
      <td style="padding:9px;border:1px solid #30363d">Bölünme işlemi vergiye tabi değildir</td>
    </tr>
    <tr>
      <td style="padding:9px;border:1px solid #30363d">Stop Loss seviyeleri</td>
      <td style="padding:9px;border:1px solid #30363d;color:#f85149">⚠️ Fiyat ayarlanır — eski stop fiyatlarını güncellemeniz gerekir</td>
    </tr>
    <tr style="background:#1a2030">
      <td style="padding:9px;border:1px solid #30363d">Teknik analiz grafikleri</td>
      <td style="padding:9px;border:1px solid #30363d">Platformlar genellikle tarihi verileri otomatik ayarlar (split-adjusted)</td>
    </tr>
  </tbody>
</table>

<h2>KAP Bildirimi ve Süreç</h2>
<p>BIST'te hisse bölünmesi süreci şu şekilde işler:</p>
<ol>
  <li>Şirket yönetim kurulu bölünme kararı alır</li>
  <li>KAP'ta özel durum bildirimi yayınlanır</li>
  <li>SPK onayı ve genel kurul kararı alınır</li>
  <li>BIST ve Merkezi Kayıt Kuruluşu (MKK) belirlenen tarihte işlemi gerçekleştirir</li>
  <li>Bölünme günü borsada yeni fiyatla açılış yapılır</li>
</ol>
<div style="background:rgba(59,130,246,.07);border:1px solid rgba(59,130,246,.15);border-radius:8px;padding:14px;margin:16px 0">
  <strong style="color:#58a6ff">💡 Pratik İpucu:</strong> KAP bildirimini gördüğünüzde bölünme tarihini not alın. Özellikle stop loss ve hedef fiyat seviyelerini bölünme sonrasına göre yeniden hesaplamanız gerekecektir.
</div>

<h2>Bölünme Sonrası Fiyat Hareketi</h2>
<p>Araştırmalar bölünme duyurusunun kısa vadede pozitif fiyat etkisi yaratabileceğini gösterse de bu etki garantili değildir. Bölünme şirketin temel değerini değiştirmez; uzun vadede performansı şirketin kazanç büyümesi belirler.</p>
""",
    "faqs": [
      {"q": "Hisse bölünmesi portföyümü etkilir mi?",
       "a": "Portföy toplam değeriniz değişmez. Hisse adedi bölünme oranında artarken birim fiyat aynı oranda düşer. Örneğin 1:5 bölünmede 100 hisseniz 500 olur, fiyat 5'te 1'e iner."},
      {"q": "Bölünme tarihinde hisse almak mantıklı mı?",
       "a": "Bölünme haberi fiyata genellikle duyurudan itibaren yansımaya başlar. Bölünme tarihi geldiğinde fiyat zaten ayarlanmış olduğundan 'ucuz' diye alım yapmak anlamsızdır. Şirketin temel değeri ve teknik trendi esas alınmalıdır."},
      {"q": "Bölünme sonrası stop loss ayarlamak gerekiyor mu?",
       "a": "Evet! Bölünme öncesi 150 ₺ için 130 ₺ stop belirlemiş iseniz, 1:5 bölünme sonrası fiyat 30 ₺ olur ve stop seviyeniz 26 ₺ olarak güncellenmeli. Aracı kurum platformları bunu otomatik yapmayabilir."},
      {"q": "Ters bölünme (reverse split) ne anlama gelir?",
       "a": "Ters bölünmede hisse adedi azalır, fiyat yükselir. Şirketler genellikle borsada kalabilmek için minimum fiyat kurallarını sağlamak amacıyla yapar. Ters bölünme çoğunlukla şirketin zayıf performansının işareti olabilir; dikkatli değerlendirme gerektirir."}
    ],
    "related_tickers": ['AKBNK', 'GARAN', 'THYAO', 'SASA', 'EREGL']
  },

  # ── ARTICLE 56 ─────────────────────────────────────────────────────────────
  {
    "slug": "altin-mi-borsa-mi-doviz-mi",
    "title": "Altın mı, Borsa mı, Döviz mi? 2026 Yatırım Karşılaştırması",
    "desc": "Altın, BIST hisseleri ve dolar/euro arasında hangisi daha karlı? Türkiye'de en iyi yatırım aracı nedir? 2026 için kapsamlı karşılaştırma ve strateji rehberi.",
    "cat": "Strateji",
    "date": "01.05.2026",
    "mins": 7,
    "body": """
<p>Türk yatırımcısının en sık sorduğu soru: "Paramı nereye yatırmalıyım?" Altın, borsa ve döviz — her birinin güçlü ve zayıf yönleri var. Bu rehberde her üç seçeneği çeşitli kriterlerle karşılaştırıyor ve 2026 koşullarında değerlendiriyoruz.</p>

<h2>Hızlı Karşılaştırma Tablosu</h2>
<table style="width:100%;border-collapse:collapse;margin:16px 0">
  <thead><tr style="background:#1e2d45">
    <th style="padding:8px 12px;text-align:left;font-size:12px;color:#94a3b8">Kriter</th>
    <th style="padding:8px 12px;text-align:center;font-size:12px;color:#e3b341">🥇 Altın</th>
    <th style="padding:8px 12px;text-align:center;font-size:12px;color:#3fb950">📈 Borsa</th>
    <th style="padding:8px 12px;text-align:center;font-size:12px;color:#58a6ff">💵 Döviz</th>
  </tr></thead>
  <tbody>
    <tr style="border-bottom:1px solid #1e2d45">
      <td style="padding:8px 12px;font-weight:600">Enflasyon Koruması</td>
      <td style="padding:8px 12px;text-align:center;color:#3fb950">✅ Güçlü</td>
      <td style="padding:8px 12px;text-align:center;color:#3fb950">✅ Orta-Güçlü</td>
      <td style="padding:8px 12px;text-align:center;color:#e3b341">⚠️ Değişken</td>
    </tr>
    <tr style="border-bottom:1px solid #1e2d45">
      <td style="padding:8px 12px;font-weight:600">Uzun Vade Getiri Potansiyeli</td>
      <td style="padding:8px 12px;text-align:center;color:#e3b341">⚠️ Orta</td>
      <td style="padding:8px 12px;text-align:center;color:#3fb950">✅ Yüksek</td>
      <td style="padding:8px 12px;text-align:center;color:#f85149">❌ Düşük</td>
    </tr>
    <tr style="border-bottom:1px solid #1e2d45">
      <td style="padding:8px 12px;font-weight:600">Likidite (Paraya Çevirme)</td>
      <td style="padding:8px 12px;text-align:center;color:#e3b341">⚠️ Orta</td>
      <td style="padding:8px 12px;text-align:center;color:#3fb950">✅ Yüksek</td>
      <td style="padding:8px 12px;text-align:center;color:#3fb950">✅ Yüksek</td>
    </tr>
    <tr style="border-bottom:1px solid #1e2d45">
      <td style="padding:8px 12px;font-weight:600">Volatilite / Risk</td>
      <td style="padding:8px 12px;text-align:center;color:#3fb950">Düşük-Orta</td>
      <td style="padding:8px 12px;text-align:center;color:#e3b341">Orta-Yüksek</td>
      <td style="padding:8px 12px;text-align:center;color:#3fb950">Düşük-Orta</td>
    </tr>
    <tr style="border-bottom:1px solid #1e2d45">
      <td style="padding:8px 12px;font-weight:600">Temettü / Düzenli Gelir</td>
      <td style="padding:8px 12px;text-align:center;color:#f85149">❌ Yok</td>
      <td style="padding:8px 12px;text-align:center;color:#3fb950">✅ Var (bazı hisseler)</td>
      <td style="padding:8px 12px;text-align:center;color:#f85149">❌ Yok</td>
    </tr>
    <tr>
      <td style="padding:8px 12px;font-weight:600">Kriz Döneminde Güvenli Liman</td>
      <td style="padding:8px 12px;text-align:center;color:#3fb950">✅ Güçlü</td>
      <td style="padding:8px 12px;text-align:center;color:#f85149">❌ Zayıf</td>
      <td style="padding:8px 12px;text-align:center;color:#3fb950">✅ Güçlü (USD)</td>
    </tr>
  </tbody>
</table>

<h2>Altın: Güvenli Liman mı, Fırsatçı Yatırım mı?</h2>
<p>Türkiye'de altın tarihsel olarak en güvenilen tasarruf aracı olmuştur. TL'deki değer kaybına karşı güçlü bir koruma sağlamıştır.</p>
<ul>
  <li><strong>Avantajları:</strong> Kriz dönemlerinde değer kazanır, global para birimi gibi davranır, enflasyona karşı uzun vadede iyi korur</li>
  <li><strong>Dezavantajları:</strong> Düzenli gelir (temettü/faiz) üretmez, fiziksel saklama maliyeti, kısa vadede negatif getiri dönemleri olabilir</li>
  <li><strong>2026 görünümü:</strong> Yüksek faiz ortamında baskı altında olabilir; jeopolitik riskler ve merkez bankası alımları destek verir</li>
</ul>

<h2>BIST Hisseleri: Yüksek Risk, Yüksek Ödül</h2>
<p>BIST100, uzun vadede Türk yatırımcısının en yüksek reel getiriyi elde ettiği araç olmuştur — ama bu getiri ciddi volatiliteyle gelir.</p>
<ul>
  <li><strong>Avantajları:</strong> Uzun vadede en yüksek getiri potansiyeli, temettü geliri, ekonomik büyümeden pay alma</li>
  <li><strong>Dezavantajları:</strong> Yüksek volatilite, siyasi riskler, TCMB öngörülemezliği, sektörel konsantrasyon</li>
  <li><strong>2026 görünümü:</strong> Güçlü bilanço döngüsü ve ihracatçı şirketler olumlu; faiz riski bankacılık için izlenmeli</li>
</ul>

<h2>Döviz: Korunma mı, Yatırım mı?</h2>
<p>Dolar ve euro Türk tasarrufçu için başlıca hedge aracıdır. Ancak dövizin kendisi üretken bir varlık değildir.</p>
<ul>
  <li><strong>Avantajları:</strong> TL değer kaybına karşı anlık koruma, çok likit, küresel varlıklara kapı</li>
  <li><strong>Dezavantajları:</strong> Reel getiri üretmez, mevduatta düşük faiz, kur müdahalesi riski</li>
  <li><strong>2026 görünümü:</strong> Enflasyon ile değer erozyonu; dolar bazlı yatırımlara kapı açar</li>
</ul>

<h2>Karma Portföy: En Akıllıca Yaklaşım</h2>
<div style="background:rgba(59,130,246,.07);border:1px solid rgba(59,130,246,.15);border-radius:8px;padding:14px;margin:16px 0">
  <strong style="color:#58a6ff">💡 Türk yatırımcısı için örnek karma portföy:</strong>
  <ul style="margin:8px 0 0 0">
    <li>%40 BIST hisseleri (teknik sinyal + temel filtre)</li>
    <li>%25 Altın (kriz tamponu)</li>
    <li>%20 Döviz / Dövizli mevduat</li>
    <li>%15 Nakit / TL araçlar</li>
  </ul>
  <p style="font-size:11px;color:#64748b;margin-top:8px">Bu yalnızca örnek dağılımdır, kişisel mali durumunuza ve risk toleransınıza göre ayarlamalısınız. Yatırım tavsiyesi değildir.</p>
</div>

<h2>BorsaPusula ile BIST Sinyallerini Takip Et</h2>
<p>Portföyünüzün borsa bölümü için BorsaPusula'nın algoritmik sinyal sistemi kullanılabilir. AL sinyalindeki BIST100 hisseleri gerçek zamanlı takip edilir, giriş kalitesi ve SL/TP seviyeleri gösterilir.</p>
""",
    "faqs": [
      {"q": "Türkiye'de en güvenli yatırım aracı hangisi?",
       "a": "Kısa vadede 'en güvenli' genellikle mevduat veya dövizdir. Uzun vadede ise altın ve seçici hisse portföyü tarihsel olarak enflasyonun üzerinde getiri sağlamıştır. Güvenli limana ihtiyaç duyduğunuzda altın ve döviz; büyüme için borsayı değerlendirin."},
      {"q": "Altın mı borsa mı daha çok kazandırır?",
       "a": "20-30 yıllık perspektifte küresel borsa endeksleri genellikle altını geride bırakmıştır. Türkiye özelinde ise kriz dönemlerinde altın çok iyi performans göstermiştir. 'Hangisi daha iyi?' sorusunun cevabı dönemden ve yatırım horizonundan bağımsız değildir."},
      {"q": "Dolar almak hâlâ mantıklı mı?",
       "a": "Dolar TL değer kaybına karşı koruma sağlar ama uzun vadede enflasyon etkisi doların reel değerini de aşındırır. Döviz tutmak bir koruma aracı olarak mantıklıdır; ancak yalnızca dövizde durmak uzun vadede reel getiri açısından zayıf kalabilir."},
      {"q": "BorsaPusula bu kararımda nasıl yardımcı olur?",
       "a": "BorsaPusula portföyünüzün BIST hissesi bölümü için algoritmik sinyal üretir. Altın ve döviz fiyatlarını makro ticker'da, altın ve gümüş teknik analizini /emtialar sayfasında bulabilirsiniz. Kripto varlıklar /kripto sayfasında takip edilmektedir."}
    ],
    "related_tickers": ['AKBNK', 'GARAN', 'THYAO', 'EREGL', 'KCHOL']
  },

  # ── ARTICLE 57 ─────────────────────────────────────────────────────────────
  {
    "slug": "bist100-temettü-hisseleri-2026",
    "title": "BIST100 Temettü Hisseleri 2026: Düzenli Gelir İçin Rehber",
    "desc": "BIST100'de en yüksek temettü verimine sahip hisseler hangileri? Temettü yatırımı nasıl yapılır, ne zaman alınır, vergi avantajları nelerdir? 2026 rehberi.",
    "cat": "Temel Analiz",
    "date": "01.05.2026",
    "mins": 7,
    "body": """
<p>Temettü (dividant) yatırımı, hisse senedini yalnızca fiyat artışından değil, düzenli nakit akışından da kazanmak için kullanılan stratejidir. BIST'te bazı şirketler her yıl yüksek oranlarda kâr payı dağıtır; bu da temettü yatırımcısı için önemli bir gelir kaynağı olur.</p>

<h2>Temettü Verimi Nedir?</h2>
<p>Temettü verimi (dividend yield), hisse başına ödenen yıllık temettünün hisse fiyatına bölünmesiyle hesaplanır:</p>
<div style="background:#1a2438;border:1px solid #1e2d45;border-radius:8px;padding:12px;margin:12px 0;text-align:center;font-size:15px;font-weight:700;color:#58a6ff">
  Temettü Verimi = (Hisse Başı Temettü ÷ Hisse Fiyatı) × 100
</div>
<p>Örnek: Hissesi 50 TL olan bir şirket 5 TL temettü ödüyorsa temettü verimi %10 olur.</p>

<h2>BIST'te Yüksek Temettü Verimiyle Öne Çıkan Sektörler</h2>
<p>BIST'te en yüksek temettü verimini genellikle şu sektörler sunar:</p>
<table style="width:100%;border-collapse:collapse;margin:16px 0">
  <thead><tr style="background:#1e2d45">
    <th style="padding:8px 12px;text-align:left;font-size:12px;color:#94a3b8">Sektör</th>
    <th style="padding:8px 12px;text-align:left;font-size:12px;color:#94a3b8">Temettü Potansiyeli</th>
    <th style="padding:8px 12px;text-align:left;font-size:12px;color:#94a3b8">Önemli Hisseler</th>
  </tr></thead>
  <tbody>
    <tr style="border-bottom:1px solid #1e2d45">
      <td style="padding:8px 12px;font-weight:600">Bankacılık</td>
      <td style="padding:8px 12px;color:#3fb950">Yüksek (BDDK sınırlı yıllarda orta)</td>
      <td style="padding:8px 12px">AKBNK, GARAN, ISCTR</td>
    </tr>
    <tr style="border-bottom:1px solid #1e2d45">
      <td style="padding:8px 12px;font-weight:600">Holding</td>
      <td style="padding:8px 12px;color:#e3b341">Orta-Yüksek</td>
      <td style="padding:8px 12px">KCHOL, SAHOL</td>
    </tr>
    <tr style="border-bottom:1px solid #1e2d45">
      <td style="padding:8px 12px;font-weight:600">Perakende</td>
      <td style="padding:8px 12px;color:#3fb950">Yüksek (büyük zincirler)</td>
      <td style="padding:8px 12px">BIMAS, MGROS</td>
    </tr>
    <tr style="border-bottom:1px solid #1e2d45">
      <td style="padding:8px 12px;font-weight:600">Enerji</td>
      <td style="padding:8px 12px;color:#e3b341">Dönemsel</td>
      <td style="padding:8px 12px">TUPRS, ENJSA</td>
    </tr>
    <tr>
      <td style="padding:8px 12px;font-weight:600">Sanayi / İhracat</td>
      <td style="padding:8px 12px;color:#e3b341">Orta</td>
      <td style="padding:8px 12px">EREGL, FROTO</td>
    </tr>
  </tbody>
</table>

<h2>Temettü Yatırımı Nasıl Yapılır?</h2>

<h3>1. Temettü Tarihleri</h3>
<ul>
  <li><strong>Genel Kurul tarihi:</strong> Temettü dağıtım kararı burada alınır</li>
  <li><strong>Temettü kesim tarihi:</strong> Bu tarihte hisseye sahip olanlar temettü alır</li>
  <li><strong>Temettü ödeme tarihi:</strong> Hesabınıza yatar</li>
  <li>Temettüyü almak için <strong>kesim tarihinden bir gün önce</strong> hisseye sahip olmalısınız</li>
</ul>

<h3>2. Temettü Sonrası Fiyat Düşüşü</h3>
<div style="background:rgba(227,179,65,.07);border:1px solid rgba(227,179,65,.2);border-radius:8px;padding:14px;margin:16px 0">
  <strong style="color:#e3b341">⚠️ Önemli:</strong> Temettü kesim tarihi sabahında hisse fiyatı genellikle ödenen temettü kadar düşer. Örneğin 50 TL'lik hisse 5 TL temettü ödediğinde, ertesi gün ~45 TL'den açılır. Temettü için satın alıp hemen satmak anlamsızdır.
</div>

<h3>3. Temettü Vergi Avantajı</h3>
<p>Türkiye'de gerçek kişilerin BIST hisselerinden aldığı temettü üzerinde <strong>%15 stopaj</strong> uygulanır. Ancak bu stopaj nihaidir; ayrıca beyan gerekmiyor (belirli limitlerde).</p>

<h2>Teknik Sinyal + Temettü Kombinasyonu</h2>
<p>BorsaPusula'nın önerilen yaklaşımı:</p>
<ol>
  <li>Yüksek temettü verimi olan BIST hisselerini temel analiz kısmından listele</li>
  <li>Sinyal "AL" durumuna geçtiğinde giriş noktasını değerlendir</li>
  <li>Güçlü trend + yüksek temettü = dual kaynak: fiyat artışı + temettü geliri</li>
</ol>

<h2>Temettü Yatırımının Riskleri</h2>
<ul>
  <li><strong>Temettü kesme riski:</strong> Şirket kötü yıl geçirirse temettü ödemeyebilir</li>
  <li><strong>Yüksek verim tuzağı:</strong> Çok yüksek temettü verimi bazen şirket sorunlarını yansıtabilir (fiyat çok düşmüş)</li>
  <li><strong>Enflasyon etkisi:</strong> TL temettü, dolar bazında değer kaybedebilir</li>
</ul>
""",
    "faqs": [
      {"q": "Temettü almak için ne kadar süre hisse tutmak gerekiyor?",
       "a": "Sadece temettü kesim tarihinde (T-2 iş günü öncesi) hisseye sahip olmanız yeterlidir. Ertesi gün satsanız da temettü hakkı kazanırsınız. Ancak fiyat genellikle temettü miktarı kadar düşer, bu yüzden kısa vadeli 'temettü avı' pratikte kazançlı değildir."},
      {"q": "BIST'te en yüksek temettü verimine hangi sektörler sahip?",
       "a": "Tarihsel olarak bankacılık (AKBNK, GARAN), perakende zincirler (BIMAS, MGROS) ve büyük holdinglerden (KCHOL) düzenli yüksek temettü ödemeleri gelmiştir. Ancak her yıl değişebilir; güncel KAP bildirimlerini ve analist beklentilerini takip edin."},
      {"q": "Temettü sonrası hisse düşüyor mu?",
       "a": "Evet, temettü kesim tarihi sabahı hisse fiyatı ödenen temettü kadar teorik olarak düşer. Bu 'temettü düzeltmesi'dir ve normaldir. Uzun vadeli yatırımcı için bu düşüş önemli değildir; şirketin temettüyü büyütme kapasitesi daha önemlidir."},
      {"q": "BorsaPusula temettü verilerini nerede görebilirim?",
       "a": "BorsaPusula'da her hisse sayfasında temel analiz bölümünde temettü verimi, hisse başı kazanç ve diğer oranlar görüntülenmektedir. Temettü ödemeleri Bilanço Takvimi sayfasında da yer almaktadır."}
    ],
    "related_tickers": ['AKBNK', 'GARAN', 'BIMAS', 'KCHOL', 'EREGL', 'TUPRS']
  },

  # ── ARTICLE 58 ─────────────────────────────────────────────────────────────
  {
    "slug": "kripto-para-mi-borsa-mi",
    "title": "Kripto Para mı, Borsa mı? Risk ve Getiri Karşılaştırması",
    "desc": "Bitcoin vs BIST hisseleri: hangisi daha karlı, hangisi daha riskli? Volatilite, düzenleme, likidite ve vergi açısından kapsamlı karşılaştırma.",
    "cat": "Strateji",
    "date": "01.05.2026",
    "mins": 6,
    "body": """
<p>Özellikle genç yatırımcılar için "kripto mu, borsa mı?" sorusu giderek daha önemli hale geliyor. Her ikisi de yüksek getiri potansiyeli sunarken çok farklı risk profilleri taşıyor. Bu rehberde iki dünya arasındaki temel farkları ele alıyoruz.</p>

<h2>Temel Karşılaştırma</h2>
<table style="width:100%;border-collapse:collapse;margin:16px 0">
  <thead><tr style="background:#1e2d45">
    <th style="padding:8px 12px;text-align:left;font-size:12px;color:#94a3b8">Kriter</th>
    <th style="padding:8px 12px;text-align:center;font-size:12px;color:#f59e0b">₿ Bitcoin/Kripto</th>
    <th style="padding:8px 12px;text-align:center;font-size:12px;color:#3fb950">📈 BIST Hisseleri</th>
  </tr></thead>
  <tbody>
    <tr style="border-bottom:1px solid #1e2d45">
      <td style="padding:8px 12px;font-weight:600">Volatilite</td>
      <td style="padding:8px 12px;text-align:center;color:#f85149">Çok Yüksek (%50-80 yıllık)</td>
      <td style="padding:8px 12px;text-align:center;color:#e3b341">Yüksek (%20-40 yıllık)</td>
    </tr>
    <tr style="border-bottom:1px solid #1e2d45">
      <td style="padding:8px 12px;font-weight:600">Gerçek Değer</td>
      <td style="padding:8px 12px;text-align:center;color:#e3b341">Tartışmalı (teknoloji değeri)</td>
      <td style="padding:8px 12px;text-align:center;color:#3fb950">Şirketin kazancı, varlıkları</td>
    </tr>
    <tr style="border-bottom:1px solid #1e2d45">
      <td style="padding:8px 12px;font-weight:600">İşlem Saatleri</td>
      <td style="padding:8px 12px;text-align:center;color:#3fb950">7/24</td>
      <td style="padding:8px 12px;text-align:center;color:#e3b341">Hafta içi 10:00-18:00</td>
    </tr>
    <tr style="border-bottom:1px solid #1e2d45">
      <td style="padding:8px 12px;font-weight:600">Düzenleme/Koruma</td>
      <td style="padding:8px 12px;text-align:center;color:#f85149">Düşük (MASAK/SPK yok)</td>
      <td style="padding:8px 12px;text-align:center;color:#3fb950">Yüksek (SPK, MKK, BIST)</td>
    </tr>
    <tr style="border-bottom:1px solid #1e2d45">
      <td style="padding:8px 12px;font-weight:600">Temettü / Pasif Gelir</td>
      <td style="padding:8px 12px;text-align:center;color:#f85149">Yok (staking hariç)</td>
      <td style="padding:8px 12px;text-align:center;color:#3fb950">Var (yüksek temettü hisseleri)</td>
    </tr>
    <tr style="border-bottom:1px solid #1e2d45">
      <td style="padding:8px 12px;font-weight:600">Vergi (Türkiye 2026)</td>
      <td style="padding:8px 12px;text-align:center;color:#f85149">%0 (henüz net değil)</td>
      <td style="padding:8px 12px;text-align:center;color:#3fb950">%0 sermaye kazancı, %15 temettü</td>
    </tr>
    <tr>
      <td style="padding:8px 12px;font-weight:600">Uzun Vade (10 yıl) Getiri</td>
      <td style="padding:8px 12px;text-align:center;color:#3fb950">Çok Yüksek (BTC 2014-2024)</td>
      <td style="padding:8px 12px;text-align:center;color:#3fb950">Yüksek (BIST enflasyon üstü)</td>
    </tr>
  </tbody>
</table>

<h2>Bitcoin Neden Bu Kadar Volatil?</h2>
<p>Bitcoin ve diğer kripto varlıkların yüksek volatilitesinin başlıca nedenleri:</p>
<ul>
  <li>Düzenleyici belirsizlik — bir haber tüm piyasayı sarsabilir</li>
  <li>Piyasa büyüklüğü küçüklüğü — büyük kurumsal satışlar sert düşüş yaratır</li>
  <li>Spekülatif talep — gerçek kullanım değerinden çok beklenti fiyatlanır</li>
  <li>Kaldıraçlı işlem yaygınlığı — zorunlu tasfiyeler (liquidation) ani sert hareketler üretir</li>
</ul>

<h2>BIST Hisselerinin Kripto Karşısındaki Avantajları</h2>
<ul>
  <li><strong>Şirket değeri:</strong> Hisse gerçek bir şirketin varlıklarına ve kazancına dayanır</li>
  <li><strong>SPK düzenlemesi:</strong> Hisse senetleri yasal koruma altındadır</li>
  <li><strong>Teknik analiz:</strong> Piyasa saatleri ve düzenli veri sayesinde teknik analiz daha güvenilir çalışır</li>
  <li><strong>Temettü:</strong> Pasif gelir imkânı sunar</li>
</ul>

<h2>Kriptoya Yatırım Yaparken Dikkat Edilmesi Gerekenler</h2>
<div style="background:rgba(248,81,73,.07);border:1px solid rgba(248,81,73,.15);border-radius:8px;padding:14px;margin:16px 0">
  <strong style="color:#f85149">⚠️ Risk Uyarısı:</strong>
  <ul style="margin:8px 0 0 0">
    <li>Kripto borsası iflasları (FTX, Celsius) tüm bakiyeyi sıfırlayabilir</li>
    <li>Cüzdan şifresi kaybı = kalıcı kayıp</li>
    <li>Sahte projeler (rug pull) yaygındır</li>
    <li>Türkiye'de kripto vergi düzenlemesi hâlâ gelişiyor</li>
  </ul>
</div>

<h2>Dengeli Yaklaşım: İkisini Birlikte Kullanmak</h2>
<p>Birçok deneyimli yatırımcı kripto ve hisseyi kombine kullanır:</p>
<ul>
  <li><strong>%70-80:</strong> Düzenlenmiş varlıklar (BIST, ETF) — temel portföy</li>
  <li><strong>%10-20:</strong> Bitcoin/Ethereum — büyüme ve çeşitlendirme</li>
  <li><strong>%5-10:</strong> Altcoin — yüksek riskli spekülatif pozisyon</li>
</ul>
<p>Bu dağılım kişisel risk toleransına ve yatırım ufkuna göre önemli ölçüde farklılaşabilir.</p>

<h2>BorsaPusula Kripto Teknik Analizi</h2>
<p>BorsaPusula'nın <a href="/kripto">/kripto</a> sayfasında Bitcoin, Ethereum, BNB ve Solana için algoritmik Supertrend + ADX + EMA12/99 sinyalleri takip edilebilir.</p>
""",
    "faqs": [
      {"q": "Bitcoin mi BIST hisseleri mi daha karlı?",
       "a": "2015-2025 dönemine bakıldığında Bitcoin çok daha yüksek nominal getiri sağlamıştır; ancak çok daha yüksek volatilite ve kayıp dönemleriyle. BIST ise yüksek enflasyon dönemlerinde bile düzenlenmiş ve temettü sunan bir piyasadır. Hangisi 'daha karlı' sorusunun cevabı ölçülen döneme göre büyük değişiklik gösterir."},
      {"q": "Türkiye'de kripto vergisi var mı?",
       "a": "2026 itibarıyla kripto para kazancı için Türkiye'de net bir vergi düzenlemesi henüz tam oturtulamamıştır. Düzenlemenin geliştiğini takip edin. BIST hisselerinde ise sermaye kazancı stopajı %0, temettü stopajı %15'tir."},
      {"q": "Kripto borsası güvenli mi?",
       "a": "Merkezi kripto borsaları (Binance, Bitfinex gibi) SPK denetiminde değildir ve siz borsanın iflas riskini taşırsınız. FTX iflasında milyonlarca kullanıcı fonuna erişemedi. Donanım cüzdan kullanmak, güvenilir platformlar seçmek ve yatırım miktarını sınırlandırmak risk azaltmanın yollarıdır."},
      {"q": "BorsaPusula kripto sinyalleri veriyor mu?",
       "a": "Evet. BorsaPusula /kripto sayfasında Bitcoin (BTC), Ethereum (ETH), BNB ve Solana (SOL) için algoritmik Supertrend + ADX + EMA12/99 teknik analiz sinyalleri sunulmaktadır."}
    ],
    "related_tickers": ['AKBNK', 'GARAN', 'THYAO', 'EREGL', 'KCHOL']
  },

  # ── ARTICLE 51 ─────────────────────────────────────────────────────────────
  {
    "slug": "faiz-ve-borsa-iliskisi-tcmb",
    "title": "Faiz ve Borsa İlişkisi: TCMB Kararları BIST'i Nasıl Etkiler?",
    "desc": "Merkez bankası faiz kararları hisse senetlerini nasıl etkiler? Faiz yükselince borsa neden düşer? Türkiye özelinde TCMB-BIST ilişkisi ve yatırımcı stratejisi.",
    "cat": "Makro Ekonomi",
    "date": "01.05.2026",
    "mins": 7,
    "body": """
<p>Faiz oranları ile borsa arasındaki ilişki, yatırımcıların en çok merak ettiği makroekonomik konuların başında gelir. Merkez bankası kararları açıklandığında piyasalar neden sert hareket eder? Bu rehberde Türkiye Cumhuriyet Merkez Bankası (TCMB) kararlarının BIST üzerindeki etkisini ve buna göre nasıl pozisyon alınabileceğini ele alıyoruz.</p>

<h2>Faiz-Borsa İlişkisinin Temel Mekanizması</h2>
<p>Faiz oranları yatırım araçlarının cazibesini doğrudan etkiler. Temel mantık şu şekilde işler:</p>

<table style="width:100%;border-collapse:collapse;margin:16px 0">
  <thead><tr style="background:#1e2d45">
    <th style="padding:8px 12px;text-align:left;font-size:12px;color:#94a3b8">Faiz Hareketi</th>
    <th style="padding:8px 12px;text-align:left;font-size:12px;color:#94a3b8">Borsa Etkisi</th>
    <th style="padding:8px 12px;text-align:left;font-size:12px;color:#94a3b8">Neden?</th>
  </tr></thead>
  <tbody>
    <tr style="border-bottom:1px solid #1e2d45">
      <td style="padding:8px 12px;color:#f85149;font-weight:600">Faiz ↑ (artar)</td>
      <td style="padding:8px 12px;color:#e3b341">Borsa ↓ (genellikle)</td>
      <td style="padding:8px 12px;font-size:12px;color:#94a3b8">Tahvil/mevduat cazip hale gelir, hisseden çıkış başlar</td>
    </tr>
    <tr style="border-bottom:1px solid #1e2d45">
      <td style="padding:8px 12px;color:#3fb950;font-weight:600">Faiz ↓ (düşer)</td>
      <td style="padding:8px 12px;color:#3fb950">Borsa ↑ (genellikle)</td>
      <td style="padding:8px 12px;font-size:12px;color:#94a3b8">Alternatif getirileri düşer, hisseye para akar</td>
    </tr>
    <tr style="border-bottom:1px solid #1e2d45">
      <td style="padding:8px 12px;color:#94a3b8">Sürpriz Artış</td>
      <td style="padding:8px 12px;color:#f85149">Sert satış</td>
      <td style="padding:8px 12px;font-size:12px;color:#94a3b8">Piyasa fiyatlamayan bir şoka tepki verir</td>
    </tr>
    <tr>
      <td style="padding:8px 12px;color:#94a3b8">Beklenti Karşılandı</td>
      <td style="padding:8px 12px;color:#8b949e">Sınırlı hareket</td>
      <td style="padding:8px 12px;font-size:12px;color:#94a3b8">Karar zaten fiyatlanmıştı</td>
    </tr>
  </tbody>
</table>

<h2>Türkiye'ye Özgü Dinamikler: TCMB-BIST İlişkisi</h2>
<p>Türkiye piyasası gelişmiş ülkelerden farklı tepkiler verebilir çünkü TL ve döviz kuru faktörü devreye girer:</p>

<h3>Faiz Artışı Senaryosu</h3>
<ul>
  <li>TCMB faiz artırırsa → TL güçlenir → Yabancı yatırımcı ilgisi artar → BIST dolar bazında yükselir</li>
  <li>Aynı zamanda kredi maliyetleri artar → Şirket karlılığı baskı altına girer → Hisseler TL bazında düşebilir</li>
  <li>Banka hisseleri (<strong>AKBNK, GARAN, ISCTR</strong>) faiz artışından net faiz marjı artacağı için olumlu etkilenebilir</li>
</ul>

<h3>Faiz İndirimi Senaryosu</h3>
<ul>
  <li>TL zayıflar → BIST TL bazında nominal yükselir (kur enflasyonu etkisi) ama dolar bazında düşebilir</li>
  <li>Yabancı yatırımcı çıkışı hızlanır → BIST derinliği azalır</li>
  <li>İhracatçı şirketler (<strong>EREGL, TUPRS, FROTO</strong>) dolar geliri nedeniyle göreceli korunur</li>
</ul>

<h2>Hangi Sektörler Faize En Çok Duyarlıdır?</h2>
<table style="width:100%;border-collapse:collapse;margin:16px 0">
  <thead><tr style="background:#1e2d45">
    <th style="padding:8px 12px;text-align:left;font-size:12px;color:#94a3b8">Sektör</th>
    <th style="padding:8px 12px;text-align:left;font-size:12px;color:#94a3b8">Faiz ↑ Etkisi</th>
    <th style="padding:8px 12px;text-align:left;font-size:12px;color:#94a3b8">Neden?</th>
  </tr></thead>
  <tbody>
    <tr style="border-bottom:1px solid #1e2d45">
      <td style="padding:8px 12px;font-weight:600">Bankacılık</td>
      <td style="padding:8px 12px;color:#3fb950">Potansiyel pozitif</td>
      <td style="padding:8px 12px;font-size:12px;color:#94a3b8">Net faiz marjı artabilir</td>
    </tr>
    <tr style="border-bottom:1px solid #1e2d45">
      <td style="padding:8px 12px;font-weight:600">GYO / Gayrimenkul</td>
      <td style="padding:8px 12px;color:#f85149">Negatif</td>
      <td style="padding:8px 12px;font-size:12px;color:#94a3b8">Mortgage maliyeti artar, talep düşer</td>
    </tr>
    <tr style="border-bottom:1px solid #1e2d45">
      <td style="padding:8px 12px;font-weight:600">Enerji / Altyapı</td>
      <td style="padding:8px 12px;color:#e3b341">Karışık</td>
      <td style="padding:8px 12px;font-size:12px;color:#94a3b8">Borç yükü artabilir ama düzenli nakit akışı koruyucu</td>
    </tr>
    <tr style="border-bottom:1px solid #1e2d45">
      <td style="padding:8px 12px;font-weight:600">İhracatçı Sanayi</td>
      <td style="padding:8px 12px;color:#3fb950">Pozitif (TL zayıflarsa)</td>
      <td style="padding:8px 12px;font-size:12px;color:#94a3b8">Dolar geliri, TL maliyet avantajı</td>
    </tr>
    <tr>
      <td style="padding:8px 12px;font-weight:600">Perakende / Tüketim</td>
      <td style="padding:8px 12px;color:#f85149">Negatif</td>
      <td style="padding:8px 12px;font-size:12px;color:#94a3b8">Tüketici harcamaları kısılır</td>
    </tr>
  </tbody>
</table>

<h2>Faiz Kararı Öncesi ve Sonrası Strateji</h2>
<div style="background:rgba(59,130,246,.07);border:1px solid rgba(59,130,246,.15);border-radius:8px;padding:14px;margin:16px 0">
  <strong style="color:#58a6ff">💡 "Beklenti al, gerçek sat" kuralı:</strong>
  <p style="margin:8px 0 0 0">Piyasalar faiz kararını genellikle haftalar öncesinden fiyatlamaya başlar. Karar açıklandığında büyük hareket çoğu zaman beklenti yönünün tersinedir. Bu nedenle karar gününde ani pozisyon açmak risklidir.</p>
</div>
<ul>
  <li><strong>Karar öncesi:</strong> Konsensüsü takip et. "Sürpriz" ihtimali yüksekse volatilite artar</li>
  <li><strong>Karar sonrası:</strong> İlk tepki genellikle abartılıdır — kalıcı trend 2-3 gün içinde netleşir</li>
  <li><strong>Uzun vade:</strong> Faiz siklus yönü (artış mı, indirim mi?) hisse seçimini şekillendirir</li>
</ul>

<h2>Pratik Takip Listesi</h2>
<p>TCMB kararlarını ve piyasa beklentilerini takip etmek için:</p>
<ul>
  <li><strong>TCMB Para Politikası Kurulu (PPK) takvimi</strong> — yılda 8 toplantı, takvim yıl başında açıklanır</li>
  <li><strong>Bloomberg/Reuters Türkiye haberleri</strong> — beklenti anketleri</li>
  <li><strong>BorsaPusula Bilanço Takvimi</strong> — makro takvim entegrasyonu</li>
  <li><strong>BIST30/BIST100 günlük trend sinyali</strong> — faiz kararı sonrası trend değişimini izle</li>
</ul>
""",
    "faqs": [
      {"q": "Faiz artışı her zaman borsa için kötü mü?",
       "a": "Hayır. Türkiye'de faiz artışı TL'yi güçlendirebilir, yabancı sermaye girişini teşvik edebilir ve BIST'i dolar bazında yükseltebilir. Bankacılık sektörü faiz artışından olumlu etkilenebilir. Etki; sürpriz mi oldu, sektöre göre farklı mı değişiyor, önemlidir."},
      {"q": "TCMB kararı hangi hisseleri en çok etkiler?",
       "a": "En yüksek etki bankacılık (AKBNK, GARAN, ISCTR, VAKBN) ve GYO sektörlerinde görülür. İhracatçı sanayi hisseleri (EREGL, TUPRS, FROTO) kur etkisi nedeniyle daha farklı hareket edebilir."},
      {"q": "Faiz kararı günü işlem yapmalı mıyım?",
       "a": "Deneyimli yatırımcılar bile faiz kararı günü büyük pozisyon açmaktan kaçınır. İlk tepki sert ve yanıltıcı olabilir. Kararın sindirilerek kalıcı trendin netleşmesini beklemek daha sağlıklıdır."},
      {"q": "Enflasyon yüksekken borsa iyi performans gösterebilir mi?",
       "a": "Türkiye'de enflasyon dönemlerinde borsa TL bazında yükselir çünkü hisseler reel varlıklara sahiplik hakkıdır. Ancak dolar bazında getiri ve gerçek satın alma gücü kazancı için enflasyonun üzerinde bir BIST performansı gerekir. Her zaman gerçekleşmez."}
    ],
    "related_tickers": ['AKBNK', 'GARAN', 'ISCTR', 'EREGL', 'TUPRS', 'EKGYO']
  },

  # ── ARTICLE 52 ─────────────────────────────────────────────────────────────
  {
    "slug": "teknik-analiz-mi-temel-analiz-mi",
    "title": "Teknik Analiz mi, Temel Analiz mi? Farklar ve Birlikte Kullanım",
    "desc": "Teknik analiz ile temel analiz arasındaki temel farklar nelerdir? Hangi yatırımcı hangisini kullanmalı? BIST hisseleri için en etkili yaklaşım nedir?",
    "cat": "Strateji",
    "date": "01.05.2026",
    "mins": 6,
    "body": """
<p>Yatırım dünyasındaki en köklü tartışmalardan biri: "Teknik analiz mi yoksa temel analiz mi daha etkili?" Bu sorunun kesin bir cevabı olmasa da her iki yaklaşımı anlamak ve doğru durumda doğru aracı kullanmak, yatırımcıya büyük avantaj sağlar.</p>

<h2>Temel Farklar: Bir Bakışta</h2>
<table style="width:100%;border-collapse:collapse;margin:16px 0">
  <thead><tr style="background:#1e2d45">
    <th style="padding:8px 12px;text-align:left;font-size:12px;color:#94a3b8">Kriter</th>
    <th style="padding:8px 12px;text-align:left;font-size:12px;color:#58a6ff">Teknik Analiz</th>
    <th style="padding:8px 12px;text-align:left;font-size:12px;color:#3fb950">Temel Analiz</th>
  </tr></thead>
  <tbody>
    <tr style="border-bottom:1px solid #1e2d45">
      <td style="padding:8px 12px;font-weight:600;color:#94a3b8">Odak Noktası</td>
      <td style="padding:8px 12px">Fiyat ve hacim hareketi</td>
      <td style="padding:8px 12px">Şirket değeri ve finansallar</td>
    </tr>
    <tr style="border-bottom:1px solid #1e2d45">
      <td style="padding:8px 12px;font-weight:600;color:#94a3b8">Veri Kaynağı</td>
      <td style="padding:8px 12px">Grafik, indikatörler, hacim</td>
      <td style="padding:8px 12px">Bilanço, gelir tablosu, makro</td>
    </tr>
    <tr style="border-bottom:1px solid #1e2d45">
      <td style="padding:8px 12px;font-weight:600;color:#94a3b8">Zaman Ufku</td>
      <td style="padding:8px 12px">Kısa-orta vade (günler–aylar)</td>
      <td style="padding:8px 12px">Uzun vade (aylar–yıllar)</td>
    </tr>
    <tr style="border-bottom:1px solid #1e2d45">
      <td style="padding:8px 12px;font-weight:600;color:#94a3b8">Ana Soru</td>
      <td style="padding:8px 12px">"Ne zaman al/sat?"</td>
      <td style="padding:8px 12px">"Hangi hisse değerli?"</td>
    </tr>
    <tr style="border-bottom:1px solid #1e2d45">
      <td style="padding:8px 12px;font-weight:600;color:#94a3b8">Öğrenme Eğrisi</td>
      <td style="padding:8px 12px">Orta (pratik ağırlıklı)</td>
      <td style="padding:8px 12px">Dik (muhasebe bilgisi gerekir)</td>
    </tr>
    <tr>
      <td style="padding:8px 12px;font-weight:600;color:#94a3b8">Subjektiflik</td>
      <td style="padding:8px 12px">Orta — yoruma açık</td>
      <td style="padding:8px 12px">Yüksek — gelecek tahmin gerekir</td>
    </tr>
  </tbody>
</table>

<h2>Teknik Analizin Güçlü Yönleri</h2>
<ul>
  <li><strong>Zamanlama:</strong> "Ne zaman girilmeli?" sorusuna doğrudan cevap verir</li>
  <li><strong>Disiplin:</strong> Somut giriş/çıkış seviyeleri (SL, TP) belirler</li>
  <li><strong>Hız:</strong> Piyasa değişimlerine hızlı tepki verir</li>
  <li><strong>Evrensellik:</strong> Her piyasada (hisse, forex, kripto) uygulanabilir</li>
  <li><strong>Otomatikleştirilebilir:</strong> Algoritmik sistemlere dönüştürülebilir</li>
</ul>

<h2>Temel Analizin Güçlü Yönleri</h2>
<ul>
  <li><strong>Gerçek değer:</strong> Şirketin gerçekte ne kadar ettiğini anlamayı sağlar</li>
  <li><strong>Uzun vade:</strong> Değer yatırımı için gerekli temel oluşturur</li>
  <li><strong>Güvenlik marjı:</strong> Ucuz hisseleri tespit etmeye yardımcı olur</li>
  <li><strong>Neden anlama:</strong> "Bu şirket neden değerleniyor?" sorusunu cevaplar</li>
</ul>

<h2>Birlikte Kullanım: En Güçlü Yaklaşım</h2>
<div style="background:rgba(63,185,80,.07);border:1px solid rgba(63,185,80,.15);border-radius:8px;padding:14px;margin:16px 0">
  <strong style="color:#3fb950">✅ Kanıtlanmış Strateji: "Temel Analiz + Teknik Zamanlama"</strong>
  <p style="margin:8px 0 0 0">Önce temel analizle "hangi hisse" sorusunu cevapla → Ardından teknik analizle "ne zaman" gireceğini belirle. Bu iki adımlı yaklaşım profesyonel portföy yöneticilerinin büyük çoğunluğunun benimsediği yöntemdir.</p>
</div>

<h3>Örnek Uygulama — AKBNK</h3>
<ol>
  <li><strong>Temel filtre:</strong> Banka karlılığı güçlü, F/K oranı sektör ortalamasının altında, temettü verimi cazip</li>
  <li><strong>Teknik giriş:</strong> BorsaPusula sinyali AL durumuna geçiyor, ADX ≥ 25, Supertrend yeşil</li>
  <li><strong>Karar:</strong> Her iki filtreden geçen hisse için giriş değerlendirilebilir</li>
</ol>

<h2>Kim Hangisini Kullanmalı?</h2>
<table style="width:100%;border-collapse:collapse;margin:16px 0">
  <thead><tr style="background:#1e2d45">
    <th style="padding:8px 12px;text-align:left;font-size:12px;color:#94a3b8">Yatırımcı Tipi</th>
    <th style="padding:8px 12px;text-align:left;font-size:12px;color:#94a3b8">Önerilen Yaklaşım</th>
  </tr></thead>
  <tbody>
    <tr style="border-bottom:1px solid #1e2d45">
      <td style="padding:8px 12px">Aktif trader (günlük-haftalık işlem)</td>
      <td style="padding:8px 12px">Teknik analiz ağırlıklı</td>
    </tr>
    <tr style="border-bottom:1px solid #1e2d45">
      <td style="padding:8px 12px">Swing trader (haftalık-aylık)</td>
      <td style="padding:8px 12px">Teknik + minimal temel filtre</td>
    </tr>
    <tr style="border-bottom:1px solid #1e2d45">
      <td style="padding:8px 12px">Uzun vadeli yatırımcı (1+ yıl)</td>
      <td style="padding:8px 12px">Temel analiz önce, teknik zamanlama</td>
    </tr>
    <tr>
      <td style="padding:8px 12px">Temettü yatırımcısı</td>
      <td style="padding:8px 12px">Temel analiz ağırlıklı</td>
    </tr>
  </tbody>
</table>

<h2>BorsaPusula Yaklaşımı: Hibrit Model</h2>
<p>BorsaPusula sinyal sistemi her ikisini birleştirir:</p>
<ul>
  <li><strong>Teknik katman:</strong> Supertrend + ADX ≥ 25 + EMA12/99 — zamanlama için</li>
  <li><strong>Temel katman:</strong> Her hisse sayfasında F/K, PD/DD, ROE, temettü verimi — değerleme için</li>
  <li><strong>Çok zaman dilimi (MTF):</strong> H4 → Günlük → Haftalık → Aylık trend uyumu — büyük trendle aynı yönde işlem için</li>
</ul>
""",
    "faqs": [
      {"q": "Teknik analiz gerçekten işe yarıyor mu?",
       "a": "Akademik araştırmalar karışık sonuçlar verse de teknik analiz birçok profesyonel trader ve kurum tarafından yaygın kullanılmaktadır. Özellikle trend takip stratejileri ve momentum göstergeleri, belirli koşullarda tutarlı sonuçlar üretebilmektedir. Tek başına mükemmel bir araç değil, bir karar destek sistemidir."},
      {"q": "Temel analiz öğrenmek için ne gerekli?",
       "a": "Temel muhasebe bilgisi (bilanço, gelir tablosu, nakit akışı okuma), sektör dinamiklerini anlama ve makroekonomik değişkenleri takip edebilme gerekir. F/K, PD/DD, ROE gibi temel oranlar başlangıç için iyi bir çıkış noktasıdır."},
      {"q": "Kısa vadede teknik analiz, uzun vadede temel analiz mi?",
       "a": "Bu yaygın bir ezberleme formülü ama tam doğru değil. Uzun vadeli yatırımcılar da teknik sinyallerden giriş zamanlamasında faydalanabilir; kısa vadeli traderlar da temel analizden sektör seçiminde yararlanabilir. Önemli olan yaklaşımların birbirini tamamlaması."},
      {"q": "BorsaPusula hangi analiz yöntemini kullanıyor?",
       "a": "BorsaPusula öncelikli olarak teknik analiz odaklıdır: Supertrend, ADX ve EMA12/99 üçlüsünü kullanır. Hisse sayfalarında temel analiz verileri (F/K, PD/DD, ROE vb.) de sunulur. Sistem, teknik ile temeli aynı ekranda görerek daha bilinçli karar almanızı hedefler."}
    ],
    "related_tickers": ['AKBNK', 'GARAN', 'THYAO', 'EREGL', 'ASELS']
  },

  # ── ARTICLE 53 ─────────────────────────────────────────────────────────────
  {
    "slug": "sp500-nedir-abd-borsasina-yatirim",
    "title": "S&P500 Nedir? ABD Borsasına Yatırım Rehberi 2026",
    "desc": "S&P500 endeksi nedir, hangi şirketler var, Türkiye'den nasıl yatırım yapılır? Nasdaq ile farkı, ETF seçimi ve kur riski. ABD borsasına yatırım rehberi.",
    "cat": "Temel Kavramlar",
    "date": "01.05.2026",
    "mins": 7,
    "body": """
<p>S&P500 (Standard & Poor's 500), ABD borsasında işlem gören en büyük 500 şirketin piyasa değeri ağırlıklı endeksidir. Dünyada en çok takip edilen borsa endekslerinden biridir ve küresel ekonominin nabzı olarak kabul edilir.</p>

<h2>S&P500 Hakkında Temel Bilgiler</h2>
<table style="width:100%;border-collapse:collapse;margin:16px 0">
  <thead><tr style="background:#1e2d45">
    <th style="padding:8px 12px;text-align:left;font-size:12px;color:#94a3b8">Özellik</th>
    <th style="padding:8px 12px;text-align:left;font-size:12px;color:#94a3b8">Detay</th>
  </tr></thead>
  <tbody>
    <tr style="border-bottom:1px solid #1e2d45">
      <td style="padding:8px 12px;font-weight:600">Kuruluş</td>
      <td style="padding:8px 12px">1957, Standard &amp; Poor's</td>
    </tr>
    <tr style="border-bottom:1px solid #1e2d45">
      <td style="padding:8px 12px;font-weight:600">Hisse sayısı</td>
      <td style="padding:8px 12px">~500 (birden fazla hisse sınıfı olan şirketler dahil 503+)</td>
    </tr>
    <tr style="border-bottom:1px solid #1e2d45">
      <td style="padding:8px 12px;font-weight:600">Piyasa değeri</td>
      <td style="padding:8px 12px">~45 trilyon USD (2026 itibarıyla)</td>
    </tr>
    <tr style="border-bottom:1px solid #1e2d45">
      <td style="padding:8px 12px;font-weight:600">Tarihsel yıllık getiri</td>
      <td style="padding:8px 12px">Ortalama ~%10 (temettü dahil, nominal)</td>
    </tr>
    <tr>
      <td style="padding:8px 12px;font-weight:600">İşlem saatleri (TR)</td>
      <td style="padding:8px 12px">16:30 – 23:00 (yaz) / 17:30 – 00:00 (kış)</td>
    </tr>
  </tbody>
</table>

<h2>S&P500 vs Nasdaq: Fark Nedir?</h2>
<p>İkisi de ABD borsasını temsil eder ancak farklı şirket gruplarını kapsar:</p>
<ul>
  <li><strong>S&P500:</strong> 11 sektörden 500 büyük şirket — dengeli ve geniş kapsamlı</li>
  <li><strong>Nasdaq 100:</strong> Teknoloji ağırlıklı 100 şirket (Apple, Microsoft, Amazon, NVIDIA gibi) — daha yüksek getiri potansiyeli, daha yüksek volatilite</li>
  <li><strong>Dow Jones (DJIA):</strong> Sadece 30 büyük şirket — en eski ama en az temsil edici</li>
</ul>

<h2>S&P500'ün En Büyük Bileşenleri (2026)</h2>
<ul>
  <li><strong>Apple (AAPL)</strong> — Teknoloji, piyasa değeri ~$3T</li>
  <li><strong>Microsoft (MSFT)</strong> — Teknoloji/Bulut</li>
  <li><strong>NVIDIA (NVDA)</strong> — Yapay zeka çipları</li>
  <li><strong>Amazon (AMZN)</strong> — E-ticaret/Bulut (AWS)</li>
  <li><strong>Alphabet/Google (GOOGL)</strong> — Reklam/AI</li>
  <li><strong>Meta (META)</strong> — Sosyal medya</li>
  <li>Bu 6 şirket endeksin yaklaşık %30'unu oluşturur</li>
</ul>

<h2>Türkiye'den ABD Borsasına Nasıl Yatırım Yapılır?</h2>

<h3>1. Aracı Kurum (Doğrudan Hisse)</h3>
<p>Midas, Passfolio gibi platformlar veya yurt içi bankaların yabancı hisse platformları aracılığıyla doğrudan AAPL, MSFT, NVDA gibi hisseler alınabilir.</p>
<ul>
  <li>✅ İstediğin hisseyi seç, tam kontrol</li>
  <li>❌ Çeşitlendirme için çok sayıda hisse gerekir</li>
</ul>

<h3>2. ETF ile S&P500 (Önerilen Yöntem)</h3>
<p>SPY, IVV, VOO gibi S&P500 ETF'leri tek alımla 500 şirkete yatırım sağlar. Türkiye'den erişim için yurt dışı platform gerekebilir.</p>
<ul>
  <li>✅ Düşük maliyet, geniş çeşitlendirme</li>
  <li>✅ Yıllık yönetim ücreti 0.03-0.09%</li>
  <li>❌ Belirli bir şirkete odaklanamama</li>
</ul>

<h3>3. Türk BYF (Borsa Yatırım Fonu)</h3>
<p>BIST'te işlem gören, yabancı endekslere yatırım yapan BYF'ler TL ile alınabilir. Kur riski yönetimi için alternatif olabilir.</p>

<h2>Kur Riski: Dolar/TL Etkisi</h2>
<div style="background:rgba(227,179,65,.07);border:1px solid rgba(227,179,65,.2);border-radius:8px;padding:14px;margin:16px 0">
  <strong style="color:#e3b341">⚠️ Kritik Not:</strong>
  <p style="margin:8px 0 0 0">TL'de değer kaybı varsa USD cinsinden aynı kalan bir yatırım TL bazında "artmış" görünür. Bu getiri yanıltıcı olabilir. Gerçek değerlendirme için ABD enflasyonu ve TL/USD paritesini birlikte değerlendirin.</p>
</div>

<h2>BorsaPusula'da ABD Hisse Sinyalleri</h2>
<p>BorsaPusula'nın <a href="/abd">/abd</a> bölümünde S&P500 ve Nasdaq'tan 144 büyük ABD hissesi için algoritmik teknik analiz sinyalleri bulunmaktadır. AAPL, MSFT, NVDA, AMZN gibi hisseler için Supertrend + ADX + EMA sinyalleri takip edilebilir.</p>
""",
    "faqs": [
      {"q": "S&P500'e yatırım yapmak güvenli mi?",
       "a": "Hiçbir yatırım tam anlamıyla güvenli değildir; S&P500 kısa vadede ciddi düşüşler (%30-50) yaşayabilir. Ancak 20-30 yıllık perspektifte tarihsel olarak pozitif getiri sağlamıştır. Uzun vadeli yatırımcı için çeşitlendirilmiş bir araç olarak değerlendirilebilir."},
      {"q": "S&P500 mü Nasdaq mı daha iyi?",
       "a": "Nasdaq son 10 yılda S&P500'ü geride bıraktı, ancak çok daha volatil. S&P500 daha dengeli ve savunmacıdır. Ağır teknoloji tercihiniz varsa Nasdaq, dengeli büyüme istiyorsanız S&P500 uygun olabilir. İkisini karıştırmak da yaygın bir stratejidir."},
      {"q": "Türkiye'den S&P500 ETF'i nasıl alınır?",
       "a": "Yurt içi bankaların yabancı hisse platformları veya Midas gibi uygulamalar aracılığıyla SPY, IVV, VOO gibi ETF'ler alınabilir. Bazı Türk BYF'leri de yabancı endeksleri takip eder. Yatırım yapmadan önce vergi ve düzenleyici koşulları araştırın."},
      {"q": "ABD borsası gece açık olduğunda Türklerden işlem yapılabilir mi?",
       "a": "Evet. NYSE ve Nasdaq'ın işlem saatleri Türkiye saatiyle 16:30-23:00 (yaz) veya 17:30-00:00 (kış) arasındadır. Bu saatlerde aracı kurumunuzun platformu üzerinden işlem yapabilirsiniz."}
    ],
    "related_tickers": ['AAPL', 'MSFT', 'NVDA', 'AMZN', 'GOOGL']
  },

  # ── ARTICLE 54 ─────────────────────────────────────────────────────────────
  {
    "slug": "bireysel-emeklilik-sistemi-bes-nedir",
    "title": "BES Nedir? Bireysel Emeklilik Sistemi Rehberi 2026",
    "desc": "Bireysel Emeklilik Sistemi (BES) nedir, nasıl çalışır, devlet katkısı ne kadar? BES mi yoksa borsa yatırımı mı daha kazançlı? Kapsamlı 2026 rehberi.",
    "cat": "Temel Kavramlar",
    "date": "01.05.2026",
    "mins": 7,
    "body": """
<p>Bireysel Emeklilik Sistemi (BES), devlet desteğiyle uzun vadeli birikim yapmanıza olanak tanıyan gönüllü bir emeklilik tasarruf sistemidir. Türkiye'de milyonlarca kişinin katılımıyla en yaygın yatırım araçlarından biri haline gelmiştir.</p>

<h2>BES Nasıl Çalışır?</h2>
<p>Temelde üç unsuru vardır:</p>
<ol>
  <li><strong>Katılımcı katkısı:</strong> Ayda belirlediğiniz tutarı ödersiniz</li>
  <li><strong>Devlet katkısı (%30):</strong> Devlet, ödediğiniz tutarın %30'unu sisteme ek katkı olarak ekler</li>
  <li><strong>Fon getirisi:</strong> Biriken para yatırım fonlarında değerlendirilir</li>
</ol>

<div style="background:rgba(63,185,80,.07);border:1px solid rgba(63,185,80,.15);border-radius:8px;padding:14px;margin:16px 0">
  <strong style="color:#3fb950">✅ Devlet Katkısı Avantajı:</strong>
  <p style="margin:8px 0 0 0">Aylık 1.000 TL katkı ödüyorsanız devlet 300 TL ekler → 1.300 TL fona yatırılır. Asgari ücretin %25'i kadar olan limit dahilinde katkı için bu oran uygulanır (2026 limitlerini kontrol edin).</p>
</div>

<h2>BES Temel Özellikleri (2026)</h2>
<table style="width:100%;border-collapse:collapse;margin:16px 0">
  <thead><tr style="background:#1e2d45">
    <th style="padding:8px 12px;text-align:left;font-size:12px;color:#94a3b8">Özellik</th>
    <th style="padding:8px 12px;text-align:left;font-size:12px;color:#94a3b8">Detay</th>
  </tr></thead>
  <tbody>
    <tr style="border-bottom:1px solid #1e2d45">
      <td style="padding:8px 12px;font-weight:600">Minimum katılım yaşı</td>
      <td style="padding:8px 12px">18 (otomatik BES'te 18–60 arası çalışanlar)</td>
    </tr>
    <tr style="border-bottom:1px solid #1e2d45">
      <td style="padding:8px 12px;font-weight:600">Devlet katkısı oranı</td>
      <td style="padding:8px 12px">%30 (ek devlet katkısı sistemine göre değişir)</td>
    </tr>
    <tr style="border-bottom:1px solid #1e2d45">
      <td style="padding:8px 12px;font-weight:600">Emeklilik yaşı</td>
      <td style="padding:8px 12px">56 yaş + 10 yıl sistem içi süre</td>
    </tr>
    <tr style="border-bottom:1px solid #1e2d45">
      <td style="padding:8px 12px;font-weight:600">Erken çıkış cezası</td>
      <td style="padding:8px 12px">Devlet katkısının bir kısmı geri alınır, stopaj uygulanabilir</td>
    </tr>
    <tr>
      <td style="padding:8px 12px;font-weight:600">Vergi avantajı</td>
      <td style="padding:8px 12px">Fon getirileri emeklilik hakkı kazanılana kadar vergisiz birikir</td>
    </tr>
  </tbody>
</table>

<h2>BES Fon Seçenekleri</h2>
<p>BES'e yatırdığınız para çeşitli fon türlerinde değerlenebilir:</p>
<ul>
  <li><strong>Hisse senedi fonları:</strong> Yüksek risk, yüksek potansiyel getiri — BIST endeks fonları</li>
  <li><strong>Sabit getirili fonlar:</strong> Tahvil/bono — düşük risk, düşük getiri</li>
  <li><strong>Para piyasası fonları:</strong> Kısa vadeli, likit</li>
  <li><strong>Karma fonlar:</strong> Hisse + tahvil karışımı</li>
  <li><strong>Altın/döviz fonları:</strong> Enflasyon ve kur riskine karşı korunma</li>
</ul>

<h2>BES mi, Borsa Yatırımı mı?</h2>
<div style="background:rgba(59,130,246,.07);border:1px solid rgba(59,130,246,.15);border-radius:8px;padding:14px;margin:16px 0">
  <strong style="color:#58a6ff">💡 Birbirinin Rakibi Değil:</strong>
  <p style="margin:8px 0 0 0">BES ve borsa birbirini tamamlayan araçlardır. BES'in devlet katkısı benzersiz bir avantaj sağlar — bu etkiyi borsada doğrudan yeniden üretemezsiniz. İdeal: BES ile uzun vadeli birikim + BIST sinyalleriyle aktif yönetim bir arada.</p>
</div>

<table style="width:100%;border-collapse:collapse;margin:16px 0">
  <thead><tr style="background:#1e2d45">
    <th style="padding:8px 12px;text-align:left;font-size:12px;color:#94a3b8">Kriter</th>
    <th style="padding:8px 12px;text-align:left;font-size:12px;color:#58a6ff">BES</th>
    <th style="padding:8px 12px;text-align:left;font-size:12px;color:#3fb950">Doğrudan Borsa</th>
  </tr></thead>
  <tbody>
    <tr style="border-bottom:1px solid #1e2d45">
      <td style="padding:8px 12px">Devlet katkısı</td>
      <td style="padding:8px 12px">✅ %30</td>
      <td style="padding:8px 12px">❌ Yok</td>
    </tr>
    <tr style="border-bottom:1px solid #1e2d45">
      <td style="padding:8px 12px">Esneklik</td>
      <td style="padding:8px 12px">Orta (erken çıkış cezalı)</td>
      <td style="padding:8px 12px">✅ İstediğin zaman çıkış</td>
    </tr>
    <tr style="border-bottom:1px solid #1e2d45">
      <td style="padding:8px 12px">Kontrol</td>
      <td style="padding:8px 12px">Sınırlı (fon seçimi)</td>
      <td style="padding:8px 12px">✅ Tam kontrol</td>
    </tr>
    <tr style="border-bottom:1px solid #1e2d45">
      <td style="padding:8px 12px">Risk profili</td>
      <td style="padding:8px 12px">Seçilebilir (düşük → yüksek)</td>
      <td style="padding:8px 12px">Seçilebilir</td>
    </tr>
    <tr>
      <td style="padding:8px 12px">Vergi avantajı</td>
      <td style="padding:8px 12px">✅ Emekliliğe kadar vergisiz</td>
      <td style="padding:8px 12px">%0 stopaj (BIST hisseleri)</td>
    </tr>
  </tbody>
</table>

<h2>BES'te Akıllı Fon Seçimi</h2>
<p>Uzun vadeli BES birikiminde tarihsel olarak en yüksek getiriyi hisse senedi ağırlıklı fonlar sağlamıştır. Ancak yaşınıza göre risk profili ayarlanmalıdır:</p>
<ul>
  <li><strong>20-40 yaş:</strong> Hisse ağırlıklı (%60-80) — uzun vade riski tolere eder</li>
  <li><strong>40-50 yaş:</strong> Dengeli karışım (%40-60 hisse) — koruyucu unsurlar artırılır</li>
  <li><strong>50+ yaş:</strong> Sabit getirili ağırlık artırılır — sermaye koruma önceliği</li>
</ul>
""",
    "faqs": [
      {"q": "BES devlet katkısını almak için ne kadar süre kalmak gerekiyor?",
       "a": "Devlet katkısının tamamını alabilmek için sistemde 10 yıl kalmanız ve 56 yaşında emekliliğe hak kazanmanız gerekir. Erken çıkışta devlet katkısının bir kısmı geri alınır ve stopaj uygulanabilir. Koşullar değişebileceğinden güncel BES mevzuatını kontrol edin."},
      {"q": "BES'te hangi fonlara yatırım yapmalıyım?",
       "a": "Uzun vadede hisse senedi fonları (özellikle endeks fonları) tarihsel olarak en yüksek reel getiriyi sağlamıştır. Ancak bu yüksek kısa vadeli volatilite anlamına gelir. Yaşınıza, risk toleransınıza ve emeklilik hedefinize göre fon dağılımınızı belirleyin."},
      {"q": "BES ve OKS (Otomatik Katılım Sistemi) aynı şey mi?",
       "a": "OKS (eski adıyla Otomatik BES), çalışanların otomatik olarak BES'e dahil edildiği zorunlu katılım sistemidir. Gönüllü BES'te siz katkı tutarını ve fon seçimini belirlersiniz. Her iki sistemde de devlet katkısından faydalanılabilir."},
      {"q": "BES'i borsa sinyalleriyle nasıl entegre edebilirim?",
       "a": "BES'inizdeki hisse senedi fonlarının performansını BIST trendleriyle takip edebilirsiniz. Güçlü boğa trendlerinde hisse ağırlığını artırmak, zayıf dönemlerde sabit getirili fonlara kaymak için BorsaPusula sinyallerini rehber olarak kullanabilirsiniz. Ancak BES fon değişiklikleri aracı kurumunuza göre sınırlandırılmış olabilir."}
    ],
    "related_tickers": ['AKBNK', 'GARAN', 'THYAO', 'EREGL', 'KCHOL']
  },

  # ── ARTICLE 55 ─────────────────────────────────────────────────────────────
  {
    "slug": "sirket-bilancosunu-nasil-okursunuz",
    "title": "Şirket Bilançosu Nasıl Okunur? Yatırımcı İçin Temel Analiz",
    "desc": "Hisse senedi yatırımında bilanço, gelir tablosu ve nakit akışı tablosu nasıl okunur? F/K, PD/DD, ROE oranları ne anlama gelir? Temel analiz başlangıç rehberi.",
    "cat": "Temel Analiz",
    "date": "01.05.2026",
    "mins": 8,
    "body": """
<p>Şirketin finansal tablolarını okuyabilmek, değer yatırımcısının en temel becerisidir. Bilanço, gelir tablosu ve nakit akışı tablosu — bu üç belge bir şirketin mali sağlığını tüm boyutlarıyla ortaya koyar.</p>

<h2>3 Temel Finansal Tablo</h2>

<h3>1. Bilanço (Balance Sheet)</h3>
<p>Şirketin belirli bir tarihteki varlıkları, yükümlülükleri ve öz sermayesini gösterir. Temel denklem:</p>
<div style="background:#1a2438;border:1px solid #1e2d45;border-radius:8px;padding:12px;margin:12px 0;text-align:center;font-size:16px;font-weight:700;color:#58a6ff">
  Varlıklar = Yükümlülükler + Öz Sermaye
</div>
<ul>
  <li><strong>Varlıklar:</strong> Nakit, alacaklar, stoklar, duran varlıklar (fabrika, makine)</li>
  <li><strong>Yükümlülükler:</strong> Kısa vadeli borçlar, uzun vadeli krediler, ödenecekler</li>
  <li><strong>Öz sermaye:</strong> Hissedarların şirketteki payı (Varlıklar − Yükümlülükler)</li>
</ul>

<h3>2. Gelir Tablosu (Income Statement)</h3>
<p>Belirli dönemde (3 ay, 1 yıl) şirketin gelirlerini, maliyetlerini ve kar/zararını gösterir:</p>
<table style="width:100%;border-collapse:collapse;margin:16px 0">
  <thead><tr style="background:#1e2d45">
    <th style="padding:8px 12px;text-align:left;font-size:12px;color:#94a3b8">Kalem</th>
    <th style="padding:8px 12px;text-align:left;font-size:12px;color:#94a3b8">Ne Gösterir?</th>
    <th style="padding:8px 12px;text-align:left;font-size:12px;color:#94a3b8">Önemli Mi?</th>
  </tr></thead>
  <tbody>
    <tr style="border-bottom:1px solid #1e2d45">
      <td style="padding:8px 12px;font-weight:600">Net Satışlar</td>
      <td style="padding:8px 12px">Dönem toplam geliri</td>
      <td style="padding:8px 12px">✅ Büyüme takibi</td>
    </tr>
    <tr style="border-bottom:1px solid #1e2d45">
      <td style="padding:8px 12px;font-weight:600">FAVÖK (EBITDA)</td>
      <td style="padding:8px 12px">Amortisman ve faiz öncesi kar</td>
      <td style="padding:8px 12px">✅ Operasyonel karlılık</td>
    </tr>
    <tr style="border-bottom:1px solid #1e2d45">
      <td style="padding:8px 12px;font-weight:600">Net Kar</td>
      <td style="padding:8px 12px">Tüm kesintiler sonrası nihai kar</td>
      <td style="padding:8px 12px">✅ F/K hesabı için</td>
    </tr>
    <tr>
      <td style="padding:8px 12px;font-weight:600">Hisse Başı Kazanç (EPS)</td>
      <td style="padding:8px 12px">Her hisse için düşen net kar</td>
      <td style="padding:8px 12px">✅ Hisse performansı</td>
    </tr>
  </tbody>
</table>

<h3>3. Nakit Akışı Tablosu</h3>
<p>Şirketin gerçekte ne kadar nakit ürettiğini gösterir. Kar değil, nakit akışı hayatta kalmayı belirler:</p>
<ul>
  <li><strong>Faaliyet nakit akışı:</strong> Asıl işten gelen para — en önemli gösterge</li>
  <li><strong>Yatırım nakit akışı:</strong> Fabrika, ekipman alım satımı</li>
  <li><strong>Finansman nakit akışı:</strong> Borç ödemeleri, temettü, sermaye artışı</li>
</ul>

<h2>En Önemli Finansal Oranlar</h2>
<table style="width:100%;border-collapse:collapse;margin:16px 0">
  <thead><tr style="background:#1e2d45">
    <th style="padding:8px 12px;text-align:left;font-size:12px;color:#94a3b8">Oran</th>
    <th style="padding:8px 12px;text-align:left;font-size:12px;color:#94a3b8">Formül</th>
    <th style="padding:8px 12px;text-align:left;font-size:12px;color:#94a3b8">İdeal Yorum</th>
  </tr></thead>
  <tbody>
    <tr style="border-bottom:1px solid #1e2d45">
      <td style="padding:8px 12px;font-weight:600">F/K (P/E)</td>
      <td style="padding:8px 12px">Fiyat ÷ Hisse Başı Kazanç</td>
      <td style="padding:8px 12px">Düşük = potansiyel ucuz; sektörle karşılaştır</td>
    </tr>
    <tr style="border-bottom:1px solid #1e2d45">
      <td style="padding:8px 12px;font-weight:600">PD/DD (P/B)</td>
      <td style="padding:8px 12px">Piyasa Değeri ÷ Defter Değeri</td>
      <td style="padding:8px 12px">&lt;1 = defter değerinin altında, potansiyel değer</td>
    </tr>
    <tr style="border-bottom:1px solid #1e2d45">
      <td style="padding:8px 12px;font-weight:600">ROE</td>
      <td style="padding:8px 12px">Net Kar ÷ Öz Sermaye</td>
      <td style="padding:8px 12px">&gt;15% genellikle güçlü karlılık</td>
    </tr>
    <tr style="border-bottom:1px solid #1e2d45">
      <td style="padding:8px 12px;font-weight:600">Net Borç/FAVÖK</td>
      <td style="padding:8px 12px">Net Borç ÷ FAVÖK</td>
      <td style="padding:8px 12px">&lt;2x sağlıklı; &gt;4x dikkat</td>
    </tr>
    <tr>
      <td style="padding:8px 12px;font-weight:600">Temettü Verimi</td>
      <td style="padding:8px 12px">Yıllık Temettü ÷ Hisse Fiyatı</td>
      <td style="padding:8px 12px">Yüksek = cazip gelir ama sürdürülebilirlik önemli</td>
    </tr>
  </tbody>
</table>

<h2>Pratik Okuma Rehberi: Adım Adım</h2>
<ol>
  <li><strong>Büyüme var mı?</strong> Net satışlar yıldan yıla artıyor mu?</li>
  <li><strong>Karlı mı?</strong> Faaliyet karı marjı pozitif mi?</li>
  <li><strong>Borç yükü ne kadar?</strong> Net borç/FAVÖK oranına bak</li>
  <li><strong>Nakit üretiyor mu?</strong> Faaliyet nakit akışı sürekli pozitif mi?</li>
  <li><strong>Değerleme makul mü?</strong> F/K ve PD/DD sektör ortalamasıyla karşılaştır</li>
</ol>

<div style="background:rgba(59,130,246,.07);border:1px solid rgba(59,130,246,.15);border-radius:8px;padding:14px;margin:16px 0">
  <strong style="color:#58a6ff">💡 KAP'tan Finansal Tablolara Erişim:</strong>
  <p style="margin:8px 0 0 0">Türkiye'de halka açık şirketlerin tüm finansal tabloları KAP (Kamuyu Aydınlatma Platformu) üzerinden ücretsiz erişilebilir. BorsaPusula'da her hisse sayfasında KAP bildirimi linkine ve temel finansal oranlara doğrudan erişebilirsiniz.</p>
</div>

<h2>Teknik Sinyal + Temel Analiz Kombinasyonu</h2>
<p>BorsaPusula hisse sayfalarında F/K, PD/DD, ROE ve temettü verimi temel verileri canlı olarak sunulmaktadır. Teknik AL sinyali alan bir hissenin temel analiz verilerini kontrol etmek, yatırım kararını güçlendirir.</p>
""",
    "faqs": [
      {"q": "Bilanço okumak için muhasebe bilgisi şart mı?",
       "a": "Derin muhasebe bilgisi gerekmez. Temel kavramları (varlık, borç, öz sermaye, karlılık, nakit akışı) anlamak ve F/K, PD/DD, ROE gibi özet oranları yorumlayabilmek başlangıç için yeterlidir. Zamanla daha derin analize geçilebilir."},
      {"q": "Hangi finansal tablo en önemli?",
       "a": "Nakit akışı tablosu genellikle en az manipüle edilebilen ve en gerçekçi tablodir. 'Kar yazılabilir ama nakit üretmek gerekir' kuralı fintech dünyasında yaygındır. Karlı görünen ama nakit üretemeyen şirketlere dikkat."},
      {"q": "F/K oranı düşük olan hisse ucuz mudur?",
       "a": "Düşük F/K tek başına ucuz anlamına gelmez. Aynı sektördeki rakiplerle karşılaştırmak gerekir. Ayrıca düşük F/K düşük büyüme beklentisini veya şirkete özgü riski yansıtıyor olabilir. Diğer oranlarla birlikte değerlendirilmelidir."},
      {"q": "BIST hisselerinin finansal tablolarına nereden bakabilirim?",
       "a": "KAP (kap.org.tr) üzerinden tüm halka açık Türk şirketlerinin finansal tabloları ücretsiz incelenebilir. BorsaPusula hisse sayfalarında temel oranlar özetlenerek sunulmaktadır. Aracı kurum platformları da genellikle temel verileri gösterir."}
    ],
    "related_tickers": ['AKBNK', 'GARAN', 'EREGL', 'THYAO', 'KCHOL']
  },

  # ── ARTICLE 50 ─────────────────────────────────────────────────────────────
  {
    "slug": "portfoy-rebalancing-yeniden-dengeleme",
    "title": "Portföy Rebalancing: Kârdaki Hisseyi Ne Zaman Satmalısın?",
    "desc": "Portföy yeniden dengeleme (rebalancing) nedir, ne zaman yapılır, kârdaki pozisyonu azaltmak akıllıca mı? Türk yatırımcısı için pratik rehber.",
    "cat": "Strateji",
    "date": "01.05.2026",
    "mins": 6,
    "body": """
<p>Portföy rebalancing (yeniden dengeleme), hedef varlık dağılımınızdan sapan portföyünüzü başlangıçtaki hedef ağırlıklarına geri döndürme işlemidir. Uzun vadeli yatırım disiplininin temel taşlarından biridir.</p>

<h2>Neden Rebalancing Gerekir?</h2>
<p>Portföyünüzü %60 hisse, %30 altın, %10 nakit olarak kurdunuz diyelim. 6 ay sonra hisseler %40 değer kazandıysa:</p>
<ul>
  <li>Yeni dağılım: Hisse %68, Altın %23, Nakit %9 gibi bir yapıya dönmüş olabilir</li>
  <li>Maruziyetiniz değişti: Hisse piyasasına gereğinden fazla bağlandınız</li>
  <li>Risk profiliniz başlangıçta belirlediğinizin üstüne çıktı</li>
</ul>
<p>Rebalancing ile hisselerden kâr alıp altın ve nakit ağırlığını artırarak orijinal %60/%30/%10 dağılımına geri dönersiniz.</p>

<h2>Rebalancing Ne Zaman Yapılmalı?</h2>
<p>İki temel yaklaşım vardır:</p>
<h3>1. Takvim Bazlı Rebalancing</h3>
<p>Belirli aralıklarla (3 ayda bir, 6 ayda bir, yılda bir) portföyü kontrol et ve ağırlıkları düzelt. Avantajı: disiplinli, duygusal kararları engeller. Dezavantajı: trendin ortasında gereksiz işlem yapılabilir.</p>

<h3>2. Eşik Bazlı Rebalancing (Tolerans Bandı)</h3>
<p>Bir varlık hedef ağırlığından belirli bir miktar saptığında (örn. ±5%) müdahale edilir. Örneğin hisselerin hedefi %60 ise ve %65'i aştıysa satış yapılır. Bu yaklaşım daha az işlem üretir ama sürekli takip gerektirir.</p>

<h2>Kârdaki Hisseyi Satmak Akıllıca mı?</h2>
<div style="background:rgba(248,81,73,.07);border:1px solid rgba(248,81,73,.15);border-radius:8px;padding:14px;margin:16px 0">
  <strong style="color:#e3b341">🧠 Psikolojik Tuzak: "Kazanıyorum, neden satayım?"</strong>
  <p style="margin:8px 0 0 0">Yükselen hisseleri elde tutmak doğal hissettirse de portföydeki ağırlığı bozulmuş bir portföy, beklenmedik düşüşlerde çok daha fazla zarar verebilir. Rebalancing disiplini bu tuzağı aşmanızı sağlar.</p>
</div>
<p>Finansal araştırmalar, düzenli rebalancing yapan yatırımcıların:</p>
<ul>
  <li>Uzun vadede daha istikrarlı getiri elde ettiğini</li>
  <li>Büyük düşüşlerde daha az zarar yaşadığını</li>
  <li>Psikolojik baskıya daha dirençli olduğunu göstermektedir</li>
</ul>

<h2>Rebalancing ve Vergi/Maliyet</h2>
<p>BIST hisseleri için alım satım kazancında stopaj %0 olduğundan rebalancing işlemi vergi açısından avantajlıdır. Ancak:</p>
<ul>
  <li>Alım satım komisyonları birikebilir — çok sık rebalancing maliyeti artırır</li>
  <li>Bir yılda çok sayıda işlem yapıyorsanız aracı kurum maliyetlerini hesaba katın</li>
</ul>

<h2>BorsaPusula Sinyalleriyle Rebalancing</h2>
<p>Teknik sinyal sistemi rebalancing kararınızı destekleyebilir:</p>
<ul>
  <li>Hisse "AL" sinyalinde ve hedef ağırlığın üzerindeyse: Kademeli azaltma düşünülebilir</li>
  <li>Hisse "SAT" veya "BEKLE" sinyaline geçtiyse: Rebalancing için iyi bir fırsat noktası olabilir</li>
  <li>Teknik sinyal + ağırlık kontrolü kombinasyonu daha bilinçli karar üretir</li>
</ul>

<h2>Adım Adım Rebalancing Rehberi</h2>
<ol>
  <li><strong>Hedef ağırlıkları belirle:</strong> Başlangıçta net yüzdeler koy (hisse %X, altın %Y, nakit %Z)</li>
  <li><strong>Periyodik kontrol:</strong> 3-6 ayda bir veya büyük piyasa hareketlerinde portföy ağırlıklarını hesapla</li>
  <li><strong>Sapma hesapla:</strong> Her varlığın mevcut ağırlığını hedefle karşılaştır</li>
  <li><strong>±5% tolerans uygula:</strong> Küçük sapmalar için işlem yapma, maliyet tasarrufu sağlar</li>
  <li><strong>Kademeli ayarla:</strong> Tek seferde değil, birkaç işlemde hedef ağırlığa ulaş</li>
  <li><strong>Kayıt tut:</strong> Her rebalancing işlemini tarih, fiyat ve gerekçeyle kaydet</li>
</ol>
""",
    "faqs": [
      {"q": "Rebalancing ne sıklıkla yapılmalı?",
       "a": "Çoğu finansal danışman yılda 1-2 kez veya varlık ağırlığında ±5% sapma yaşandığında rebalancing önerir. Çok sık yapılan işlemler komisyon maliyetlerini artırırken çok nadir yapılan yatırım ciddi riske girer."},
      {"q": "Kârdaki hisseyi satmak psikolojik olarak zor. Ne yapmalıyım?",
       "a": "Bu tamamen normal bir his. Kurallara dayalı bir sistem oluşturun: 'Hisse %X ağırlığı aştığında sat' gibi önceden belirlenmiş kurallar, duygusal kararları engeller. Portföy yönetimi kurallara, hislere göre değil yapılır."},
      {"q": "Eğer piyasa yükseliyorsa neden satayım?",
       "a": "Rebalancing geleceği tahmin etmek değildir. Yükselen piyasada aşırı konumlanmak, düşüşte daha büyük kayba yol açabilir. Hedef ağırlıklara dönmek bir risk yönetimi disiplinidir."},
      {"q": "BorsaPusula sinyalleri rebalancing kararında nasıl kullanılır?",
       "a": "Hisse SAT veya BEKLE sinyaline geçtiğinde portföy ağırlığını da kontrol edin. SAT sinyali + yüksek portföy ağırlığı kombinasyonu, azaltma için güçlü bir gerekçe oluşturabilir. Ancak sinyaller yatırım tavsiyesi değildir."}
    ],
    "related_tickers": ['AKBNK', 'GARAN', 'TUPRS', 'THYAO', 'ASELS']
  },

  # ── ARTICLE 59 ──
  {
    "slug": "borsa-seans-saatleri-2026",
    "title": "Borsa Seans Saatleri 2026: BIST Açılış ve Kapanış Bilgileri",
    "desc": "BIST hisse senetleri kaçta açılır, kaçta kapanır? 2026 güncel seans saatleri, işlem günleri ve tatil takvimi.",
    "date": "2026-05-01",
    "mins": 5,
    "cat": "Temel Kavramlar",
    "body": """
<p>Borsa İstanbul'da (BIST) işlem yapmadan önce bilmeniz gereken en temel bilgilerden biri seans saatleridir. Yanlış saatte emir girilmesi veya beklenmedik tatil günlerinde işlem yapılamayacağı için seans saatlerini ezberlemek, aktif yatırımcılar için zorunluluktur.</p>

<h2>2026 BIST Hisse Senedi Seans Saatleri</h2>
<p>Borsa İstanbul Pay Piyasası (hisse senetleri) şu seans düzenini izler:</p>
<table style="width:100%;border-collapse:collapse;font-size:14px;margin:12px 0">
  <thead>
    <tr style="background:#21262d">
      <th style="padding:8px 12px;text-align:left;color:#8b949e;font-weight:600">Seans</th>
      <th style="padding:8px 12px;text-align:left;color:#8b949e;font-weight:600">Saat</th>
      <th style="padding:8px 12px;text-align:left;color:#8b949e;font-weight:600">Açıklama</th>
    </tr>
  </thead>
  <tbody>
    <tr style="border-top:1px solid #30363d">
      <td style="padding:8px 12px;color:#e6edf3">Sabah Tek Fiyat Seansı</td>
      <td style="padding:8px 12px;color:#3fb950;font-family:monospace;font-weight:600">09:30 – 10:00</td>
      <td style="padding:8px 12px;color:#8b949e">Açılış fiyatı belirlenir, emir toplanır</td>
    </tr>
    <tr style="border-top:1px solid #30363d;background:rgba(255,255,255,.02)">
      <td style="padding:8px 12px;color:#e6edf3">Sürekli Müzayede (Ana Seans)</td>
      <td style="padding:8px 12px;color:#3fb950;font-family:monospace;font-weight:600">10:00 – 18:00</td>
      <td style="padding:8px 12px;color:#8b949e">Emir eşleşmesi anlık gerçekleşir</td>
    </tr>
    <tr style="border-top:1px solid #30363d">
      <td style="padding:8px 12px;color:#e6edf3">Kapanış Tek Fiyat Seansı</td>
      <td style="padding:8px 12px;color:#f0883e;font-family:monospace;font-weight:600">18:00 – 18:10</td>
      <td style="padding:8px 12px;color:#8b949e">Kapanış fiyatı belirlenir, emir toplanır</td>
    </tr>
  </tbody>
</table>
<p><strong>Önemli:</strong> Türkiye saati (TRT/UTC+3) kullanılır. Yaz/kış saati değişiminden etkilenmez çünkü Türkiye saati sabit kaldı.</p>

<h2>Sabah Tek Fiyat Seansı Nasıl Çalışır?</h2>
<p>Saat 09:30-10:00 arasında yatırımcılar emir girebilir ancak eşleşme gerçekleşmez. 10:00'de sistem, girilen tüm emirleri değerlendirerek en fazla işlemi sağlayan "açılış fiyatını" tek seferde belirler. Bu fiyat aynı zamanda gün içindeki ilk işlem fiyatıdır.</p>
<ul>
  <li>Açılış öncesinde girilmiş emirlerin büyük kısmı bu seanstta eşleşir</li>
  <li>Fiyat hareket sınırı: bir önceki kapanışa göre ±%20 (devre kesici mekanizması)</li>
  <li>Haber bekleyen veya bilanço açıklayan hisseler için volatilite yüksek olabilir</li>
</ul>

<h2>Sürekli Müzayede (10:00 – 18:00)</h2>
<p>Ana işlem saatidir. Limit veya piyasa emri girildiğinde eşleşme anlık gerçekleşir. BIST hisselerinde 8 saatlik bu pencere, Avrupa borsalarıyla (Londra, Frankfurt) kısmen örtüşür ancak ABD açılışını (15:30 TRT) da kapsar.</p>

<h2>Kapanış Seansı (18:00 – 18:10)</h2>
<p>Günün kapanış fiyatını belirleyen 10 dakikalık bir "açık artırma" seansıdır. Endeks hesaplamalarında ve bazı türev ürünlerin uzlaşma fiyatında kullanılır. Bu saatte fiyatlar beklenmedik şekilde hareket edebilir — bunu göz önünde bulundurun.</p>

<h2>VİOP (Vadeli İşlemler) Saatleri Farklıdır</h2>
<p>Vadeli işlem ve opsiyon piyasası (VİOP) hisse senedi piyasasından daha uzun süre açıktır:</p>
<ul>
  <li><strong>Sabah seansı:</strong> 09:15 – 18:15</li>
  <li><strong>Akşam seansı:</strong> 19:00 – 23:00 (endeks ve döviz kontratları için)</li>
</ul>

<h2>İşlem Yapılmayan Günler</h2>
<p>Borsa, resmi tatil günlerinde kapalıdır. 2026 yılında borsanın kapalı olacağı başlıca günler şunlardır:</p>
<ul>
  <li>1 Ocak — Yılbaşı</li>
  <li>23 Nisan — Ulusal Egemenlik ve Çocuk Bayramı</li>
  <li>1 Mayıs — Emek ve Dayanışma Günü</li>
  <li>19 Mayıs — Atatürk'ü Anma, Gençlik ve Spor Bayramı</li>
  <li>Ramazan Bayramı (2026: yaklaşık 20-22 Mart)</li>
  <li>Kurban Bayramı (2026: yaklaşık 27-30 Mayıs + arife)</li>
  <li>15 Temmuz — Demokrasi ve Millî Birlik Günü</li>
  <li>30 Ağustos — Zafer Bayramı</li>
  <li>29 Ekim — Cumhuriyet Bayramı</li>
</ul>
<p>Güncel tatil takvimi için Borsa İstanbul'un resmi web sitesini kontrol edin.</p>

<h2>BorsaPusula Sinyalleri Hangi Saatte Güncellenir?</h2>
<p>BorsaPusula algoritması, seans kapatıldıktan sonra (18:00-18:10 kapanış seansı tamamlanınca) günlük bar verilerini işler ve sinyalleri hesaplar. Sinyal güncellemesi genellikle saat 18:30-19:00 arasında tamamlanır. Sabah 10:00'de ana seansa başlamadan önce güncel sinyalleri kontrol etmek idealdir.</p>
""",
    "faqs": [
      {"q": "BIST kaçta açılır, kaçta kapanır?",
       "a": "BIST Pay Piyasası, sabah 09:30'da tek fiyat seansıyla başlar. Ana sürekli müzayede seansı 10:00-18:00 saatleri arasındadır. Kapanış tek fiyat seansı ise 18:00-18:10 arasında gerçekleşir."},
      {"q": "Borsa tatil günlerinde açık mı?",
       "a": "Hayır, Borsa İstanbul resmi tatil günlerinde kapalıdır. Ramazan ve Kurban Bayramları, 23 Nisan, 1 Mayıs, 19 Mayıs, 30 Ağustos ve 29 Ekim'de borsa işlem görmez. Güncel tatil takvimi için Borsa İstanbul resmi sitesine bakın."},
      {"q": "Sabah 10:00'den önce emir girebilir miyim?",
       "a": "Evet. Sabah 09:30-10:00 arasındaki 'Tek Fiyat Seansı'nda emir girebilirsiniz. Bu emirler 10:00'de sistem tarafından eşleştirilir ve açılış fiyatını belirler. Emir eşleşmesi saat 10:00'e kadar gerçekleşmez."},
      {"q": "BorsaPusula sinyalleri ne zaman güncellenir?",
       "a": "Sinyaller, kapanış seansı tamamlandıktan sonra günlük bar verileri işlenerek hesaplanır. Güncelleme genellikle saat 18:30-19:00 arasında tamamlanır. Sabah işlemlerine başlamadan önce güncel sinyalleri kontrol etmenizi öneririz."}
    ],
    "related_tickers": ['AKBNK', 'GARAN', 'THYAO', 'ASELS', 'EREGL']
  },

  # ── ARTICLE 60 ──
  {
    "slug": "tahvil-nedir-borsayla-farki",
    "title": "Tahvil Nedir? Hisse Senediyle Farkı ve 2026 Yatırım Rehberi",
    "desc": "Tahvil ile hisse senedi arasındaki temel farklar, tahvil yatırımının avantajları ve dezavantajları. Türkiye'de tahvil yatırımı nasıl yapılır?",
    "date": "2026-05-01",
    "mins": 7,
    "cat": "Temel Kavramlar",
    "body": """
<p>Yatırım dünyasının iki temel taşı olan <strong>hisse senedi</strong> ve <strong>tahvil</strong>, çoğunlukla birlikte anılır fakat birbirinden çok farklı araçlardır. İkisini doğru anlamak, portföyünüzü nasıl oluşturacağınızı belirler.</p>

<h2>Tahvil Nedir?</h2>
<p>Tahvil (obligasyon), bir şirketin veya devletin <strong>borç para almak için çıkardığı menkul kıymet</strong>tir. Tahvil aldığınızda, ihraçcıya borç vermiş olursunuz. Karşılığında:</p>
<ul>
  <li><strong>Dönemsel faiz (kupon) ödemesi</strong> alırsınız (genellikle yılda 1-4 kez)</li>
  <li><strong>Vade sonunda</strong> ana paranız (nominal değer) geri ödenir</li>
</ul>
<p>Hisse senedinden farklı olarak, tahvilde sabit bir geri ödeme taahhüdü vardır. Şirket zarar etse bile tahvil faizini ödemek zorundadır.</p>

<h2>Hisse Senedi vs Tahvil: Temel Farklar</h2>
<table style="width:100%;border-collapse:collapse;font-size:14px;margin:12px 0">
  <thead>
    <tr style="background:#21262d">
      <th style="padding:8px 12px;text-align:left;color:#8b949e;font-weight:600">Özellik</th>
      <th style="padding:8px 12px;text-align:left;color:#3fb950;font-weight:600">Hisse Senedi</th>
      <th style="padding:8px 12px;text-align:left;color:#f0883e;font-weight:600">Tahvil</th>
    </tr>
  </thead>
  <tbody>
    <tr style="border-top:1px solid #30363d">
      <td style="padding:8px 12px;color:#e6edf3">Ne satın alırsınız?</td>
      <td style="padding:8px 12px;color:#e6edf3">Şirkete ortaklık payı</td>
      <td style="padding:8px 12px;color:#e6edf3">Şirkete/devlete borç hakkı</td>
    </tr>
    <tr style="border-top:1px solid #30363d;background:rgba(255,255,255,.02)">
      <td style="padding:8px 12px;color:#e6edf3">Getiri kaynağı</td>
      <td style="padding:8px 12px;color:#e6edf3">Fiyat artışı + temettü</td>
      <td style="padding:8px 12px;color:#e6edf3">Sabit faiz (kupon)</td>
    </tr>
    <tr style="border-top:1px solid #30363d">
      <td style="padding:8px 12px;color:#e6edf3">Risk seviyesi</td>
      <td style="padding:8px 12px;color:#f85149">Yüksek</td>
      <td style="padding:8px 12px;color:#3fb950">Orta / Düşük (devlet)</td>
    </tr>
    <tr style="border-top:1px solid #30363d;background:rgba(255,255,255,.02)">
      <td style="padding:8px 12px;color:#e6edf3">Oy hakkı</td>
      <td style="padding:8px 12px;color:#e6edf3">Evet (genel kurul)</td>
      <td style="padding:8px 12px;color:#e6edf3">Hayır</td>
    </tr>
    <tr style="border-top:1px solid #30363d">
      <td style="padding:8px 12px;color:#e6edf3">Iflas önceliği</td>
      <td style="padding:8px 12px;color:#f85149">Sonuncu sırada</td>
      <td style="padding:8px 12px;color:#3fb950">Hisse senetlerinden önce</td>
    </tr>
    <tr style="border-top:1px solid #30363d;background:rgba(255,255,255,.02)">
      <td style="padding:8px 12px;color:#e6edf3">Vade</td>
      <td style="padding:8px 12px;color:#e6edf3">Süresiz</td>
      <td style="padding:8px 12px;color:#e6edf3">Belirli (1 ay – 30 yıl)</td>
    </tr>
  </tbody>
</table>

<h2>Türkiye'de Tahvil Türleri</h2>
<h3>Devlet Tahvilleri (DİBS)</h3>
<p>Hazine ve Maliye Bakanlığı tarafından çıkarılır. Türkiye'nin en güvenli borçlanma aracı kabul edilir. İki alt türü vardır:</p>
<ul>
  <li><strong>Devlet Tahvili:</strong> Vadesi 1 yıldan uzun, sabit veya değişken faizli</li>
  <li><strong>Hazine Bonosu:</strong> Vadesi 1 yıldan kısa, genellikle iskontolu satılır</li>
</ul>

<h3>Kira Sertifikası (Sukuk)</h3>
<p>Faizsiz finans ilkeleriyle çalışır. Devlet veya şirketler varlıkları üzerinden ihraç eder. Kurumsal yatırımcılar ve katılım finans müşterileri için cazip bir alternatiftir.</p>

<h3>Özel Sektör Tahvilleri</h3>
<p>Şirketlerin bankadan borç almak yerine doğrudan piyasadan fon toplaması yöntemidir. Devlet tahvillerine göre daha yüksek faiz sunar ama risk de daha yüksektir.</p>

<h2>Enflasyon ve Tahvil İlişkisi</h2>
<p>Yüksek enflasyon dönemlerinde (Türkiye'nin 2021-2023 deneyimi gibi) sabit faizli tahvillerin gerçek getirisi eriyebilir. Bu nedenle:</p>
<ul>
  <li><strong>TÜFE'ye endeksli tahviller:</strong> Enflasyona karşı koruma sağlar, anapara enflasyona göre güncellenir</li>
  <li><strong>Değişken faizli tahviller:</strong> TCMB politika faizine bağlı, faiz artışından yararlanır</li>
  <li><strong>Sabit faizli tahvil:</strong> Enflasyon yüksekse reel kayba yol açabilir</li>
</ul>

<h2>Faiz ile Tahvil Fiyatı Ters Orantılı</h2>
<p>Tahvil yatırımcılarının bilmesi gereken temel kural: <strong>Piyasa faiz oranları yükseldiğinde, mevcut tahvillerin fiyatı düşer.</strong> Tersine, faizler düştüğünde tahvil fiyatları yükselir.</p>
<p>Örnek: 10% faizle aldığınız bir tahvili, piyasa faizleri 12%'ye çıktığında satmak isterseniz, alıcı daha yüksek faizli yeni tahvillere yönelir; bu nedenle tahvilinizi indirimli satmak zorunda kalırsınız.</p>

<h2>Tahvil mi, Hisse mi?</h2>
<p>Her iki araç da portföyde yer alabilir. Genel kural olarak:</p>
<ul>
  <li><strong>Genç / uzun vadeli yatırımcı:</strong> Hisse ağırlığı yüksek (80/20 hisse/tahvil)</li>
  <li><strong>Emekliliğe yakın / kısa vadeli ihtiyaç:</strong> Tahvil ağırlığı artar (40/60 hisse/tahvil)</li>
  <li><strong>Risk toleransı düşük:</strong> Devlet tahvili ile korunmalı portföy</li>
</ul>
<p>Türkiye'de yüksek enflasyon nedeniyle nominal tahvil faizleri cazip görünse de enflasyona karşı korumalı araçları veya kısa vadeli enstrümanları tercih etmek akıllıca olabilir.</p>
""",
    "faqs": [
      {"q": "Tahvil ve hisse senedi arasındaki en temel fark nedir?",
       "a": "Hisse senedi şirkete ortak olmak anlamına gelirken, tahvil şirkete veya devlete borç vermek anlamına gelir. Hisse senedinde getiri sınırsız olabilir ama risk yüksektir. Tahvilde belirli bir faiz getirisi garantilenirken iflas durumunda hisse senedi sahiplerinden daha öncelikli ödeme hakkınız vardır."},
      {"q": "Türkiye'de devlet tahvili nasıl alınır?",
       "a": "Aracı kurumlar veya bankalar üzerinden Hazine Müsteşarlığı'nın DİBS (Devlet İç Borçlanma Senetleri) ihalelerine katılabilirsiniz. Ayrıca ikincil piyasada (Borsa İstanbul Tahvil Piyasası) mevcut tahviller alınıp satılabilir."},
      {"q": "Tahvil fiyatı neden düşer?",
       "a": "Piyasa faiz oranları yükseldiğinde, sabit faizli mevcut tahvillerin çekiciliği azalır ve fiyatları düşer. Bu nedenle faiz artırım dönemlerinde (TCMB sıkılaştırma) uzun vadeli tahvil tutanlar zarar edebilir."},
      {"q": "TÜFE'ye endeksli tahvil ne demek?",
       "a": "Anapara değeri Türkiye tüketici fiyat endeksine (TÜFE) göre güncellenen tahvillerdir. Enflasyon %50 olursa anaparanız da %50 artırılır, böylece enflasyona karşı korunmuş olursunuz. Türkiye Hazinesi bu tür tahviller ihraç etmektedir."}
    ],
    "related_tickers": []
  },

  # ── ARTICLE 61 ──
  {
    "slug": "viop-vadeli-islemler-nedir",
    "title": "VİOP Nedir? Vadeli İşlem ve Opsiyon Piyasası Başlangıç Rehberi",
    "desc": "Borsa İstanbul VİOP (Vadeli İşlem ve Opsiyon Piyasası) nasıl çalışır? Futures ve opsiyon sözleşmelerini yeni başlayanlar için anlatan kapsamlı rehber.",
    "date": "2026-05-01",
    "mins": 8,
    "cat": "Temel Kavramlar",
    "body": """
<p>VİOP (Vadeli İşlem ve Opsiyon Piyasası), Borsa İstanbul bünyesinde türev ürünlerin işlem gördüğü piyasadır. Hisse senedi piyasasından farklı bir mantıkla çalışır ve hem koruma (hedging) hem de kaldıraçlı spekülasyon imkânı sunar. Doğru anlaşılmadan girilmesi halinde büyük kayıplara yol açabileceği için dikkatli bir şekilde öğrenilmesi gerekir.</p>

<h2>Vadeli İşlem Sözleşmesi (Futures) Nedir?</h2>
<p>Vadeli işlem sözleşmesi, belirli bir varlığı <strong>önceden belirlenen fiyat ve tarihte</strong> alıp satma yükümlülüğüdür. İki taraf bu sözleşmeyi imzaladığında, her iki taraf da yükümlülük altına girer.</p>
<p>Örnek: BIST30 endeksi üzerine bir futures sözleşmesi satın aldığınızda, ilerleyen bir tarihte endeksin şimdiki değeri üzerinden hesaplanan tutarı nakit olarak alacağınız veya ödeyeceğiniz bir anlaşma yapıyorsunuz demektir.</p>

<h2>Opsiyon Sözleşmesi Nedir?</h2>
<p>Opsiyon, belirli bir varlığı belirli bir fiyattan <strong>alma (call) veya satma (put) hakkıdır</strong> — ancak yükümlülük değil. Opsiyon alıcısı bu hakkı kullanıp kullanmamakta serbesttir; opsiyon satıcısı ise karşı tarafın kararına uymak zorundadır.</p>
<ul>
  <li><strong>Call Opsiyon:</strong> Belirlenen fiyattan alma hakkı (fiyat yükselişinde kazanılır)</li>
  <li><strong>Put Opsiyon:</strong> Belirlenen fiyattan satma hakkı (fiyat düşüşünde kazanılır)</li>
  <li><strong>Prim:</strong> Bu hakkı satın almak için ödenen ücret</li>
</ul>

<h2>VİOP'ta Ne İşlem Görür?</h2>
<p>Borsa İstanbul VİOP'ta çeşitli dayanak varlıklar üzerine kontratlar bulunur:</p>
<table style="width:100%;border-collapse:collapse;font-size:14px;margin:12px 0">
  <thead>
    <tr style="background:#21262d">
      <th style="padding:8px 12px;text-align:left;color:#8b949e;font-weight:600">Ürün Grubu</th>
      <th style="padding:8px 12px;text-align:left;color:#8b949e;font-weight:600">Örnekler</th>
    </tr>
  </thead>
  <tbody>
    <tr style="border-top:1px solid #30363d">
      <td style="padding:8px 12px;color:#e6edf3">Endeks Futures</td>
      <td style="padding:8px 12px;color:#e6edf3">BIST30 vadeli (XU030 kontratları)</td>
    </tr>
    <tr style="border-top:1px solid #30363d;background:rgba(255,255,255,.02)">
      <td style="padding:8px 12px;color:#e6edf3">Döviz Futures</td>
      <td style="padding:8px 12px;color:#e6edf3">USD/TRY, EUR/TRY, GBP/TRY</td>
    </tr>
    <tr style="border-top:1px solid #30363d">
      <td style="padding:8px 12px;color:#e6edf3">Pay Futures</td>
      <td style="padding:8px 12px;color:#e6edf3">AKBNK, GARAN, THYAO gibi bireysel hisseler</td>
    </tr>
    <tr style="border-top:1px solid #30363d;background:rgba(255,255,255,.02)">
      <td style="padding:8px 12px;color:#e6edf3">Metal/Emtia Futures</td>
      <td style="padding:8px 12px;color:#e6edf3">Altın, Gümüş</td>
    </tr>
    <tr style="border-top:1px solid #30363d">
      <td style="padding:8px 12px;color:#e6edf3">Endeks Opsiyonları</td>
      <td style="padding:8px 12px;color:#e6edf3">BIST30 call/put opsiyonları</td>
    </tr>
  </tbody>
</table>

<h2>Kaldıraç: Avantaj mı, Tuzak mı?</h2>
<p>VİOP'un en dikkat çekici özelliği <strong>kaldıraçtır</strong>. Sözleşmenin toplam değerinin yalnızca küçük bir bölümünü (<em>başlangıç teminatı</em>) yatırarak büyük pozisyon açabilirsiniz.</p>
<p>Örnek: 10:1 kaldıraçla çalışıyorsanız, 10.000₺ ile 100.000₺'lik pozisyon açabilirsiniz. Piyasa %5 lehinize hareket ederse 5.000₺ kazanırsınız (%50 getiri). Ancak %5 aleyhinize hareket ederse 5.000₺ kaybedersiniz (%50 kayıp). Hareket %10'u aşarsa başlangıç teminatınızın tamamını kaybedebilirsiniz.</p>
<p style="background:rgba(248,81,73,.08);border:1px solid rgba(248,81,73,.3);border-radius:6px;padding:10px 14px;color:#f85149;font-size:13px">
⚠️ <strong>Risk Uyarısı:</strong> VİOP yatırımcıların büyük çoğunluğu zarar etmektedir. Kaldıraçlı işlemler hem kazancı hem de kaybı büyütür. Yeterli deneyim ve risk yönetimi olmadan girilmesi ciddi sermaye kaybına yol açabilir.
</p>

<h2>Teminat ve Teminat Tamamlama (Margin Call)</h2>
<p>Pozisyon açmak için hesabınızda başlangıç teminatı bulunmalıdır. Piyasa aleyhinize hareket edip hesap bakiyeniz sürdürme teminatının altına düşerse, aracı kurum ek teminat yatırmanızı (margin call) ister. Yatırmazsanız pozisyonunuz zorla kapatılır.</p>

<h2>VİOP'ta Hedging (Korunma) Nasıl Yapılır?</h2>
<p>Portföyünüzde BIST30 hisseleri taşıyorsanız ve kısa vadeli bir düşüşten korunmak istiyorsanız, BIST30 futures'ı satarak (short) portföyünüzü hedge edebilirsiniz. Bu sayede piyasa düşse bile futures pozisyonunuzdan kazanç sağlarsınız.</p>

<h2>Yeni Başlayanlar İçin Öneriler</h2>
<ul>
  <li>Önce hisse senedi piyasasında en az 1-2 yıl deneyim kazanın</li>
  <li>Kağıt üzerinde (simülasyon) en az 3 ay işlem yapın</li>
  <li>Kaldıraç oranını başlangıçta düşük tutun (3x veya altı)</li>
  <li>Stop loss olmadan hiçbir pozisyon açmayın</li>
  <li>Risk etmek istediğiniz tutarın ötesine geçmeyin</li>
</ul>
""",
    "faqs": [
      {"q": "VİOP ve normal borsa arasındaki fark nedir?",
       "a": "Normal borsada (Pay Piyasası) gerçek hisse senetleri alınıp satılır. VİOP'ta ise hissenin kendisi değil, hissenin veya endeksin gelecekteki fiyatına dair sözleşmeler (türev ürünler) işlem görür. VİOP kaldıraçlı çalışır, bu hem kazanç hem de zarar potansiyelini büyütür."},
      {"q": "VİOP'a başlamak için ne kadar sermaye gerekir?",
       "a": "Aracı kurumlara göre değişmekle birlikte, çoğu aracı kurumda minimum 10.000-20.000 TL ile VİOP işlemine başlanabilir. Ancak kaldıraç riski nedeniyle yeterli bir tampon sermaye bulundurmak önemlidir."},
      {"q": "BIST30 vadeli işlemi nasıl çalışır?",
       "a": "BIST30 futures sözleşmesi, belirli bir vadede XU030 endeksinin belirli bir değerden alınıp satılacağını garanti eder. Endeks 1 yükselirse kontrat başına 10₺ kazanılır (1 kontrat = 10 çarpan). Her gün sonunda kâr/zarar hesabınıza anlık yansır (günlük uzlaşma)."},
      {"q": "VİOP'ta opsiyon ile futures arasındaki temel fark nedir?",
       "a": "Futures sözleşmesinde her iki taraf da yükümlüdür; vade geldiğinde ödeme zorunludur. Opsiyonda ise alıcı yalnızca bir hak satın alır — bu hakkı kullanıp kullanmamakta serbesttir. Futures daha riskli olabilir çünkü iki yönlü yükümlülük doğurur."}
    ],
    "related_tickers": ['AKBNK', 'GARAN', 'THYAO', 'EREGL', 'ASELS']
  },

  # ── ARTICLE 62 ──
  {
    "slug": "limit-emir-piyasa-emri-nedir",
    "title": "Limit Emir ve Piyasa Emri Nedir? Borsa Emir Tipleri Rehberi",
    "desc": "Limit emir, piyasa emri, koşullu emir ve stop emir nedir? BIST'te hangi emir türünü ne zaman kullanmalısınız? Pratik örneklerle açıklama.",
    "date": "2026-05-01",
    "mins": 6,
    "cat": "Temel Kavramlar",
    "body": """
<p>Borsada hisse alıp satmak için bir emir girmek gerekir. Emir türünü yanlış seçmek, beklediğinizden çok daha kötü bir fiyattan işlem yapmanıza ya da hiç işlem gerçekleşmemesine yol açabilir. Bu rehberde BIST'te kullanılan temel emir tiplerini öğreneceksiniz.</p>

<h2>Piyasa Emri (Market Order)</h2>
<p>Piyasa emri, o anda piyasada mevcut en iyi fiyattan <strong>anında işlem gerçekleştirme</strong> talimatıdır. Fiyat belirtmezsiniz; sistem sizi mevcut en iyi alış veya satış fiyatına eşleştirir.</p>
<ul>
  <li><strong>Avantaj:</strong> Anında ve kesinlikle işlem gerçekleşir</li>
  <li><strong>Dezavantaj:</strong> Yüksek volatilite dönemlerinde beklediğinizden çok farklı fiyattan işlem olabilir (slippage)</li>
  <li><strong>Ne zaman kullanılır:</strong> Hızla girmek veya çıkmak istediğinizde; likidite yüksek hisselerde</li>
</ul>
<p>⚠️ Hacmi düşük hisselerde piyasa emri kullanmaktan kaçının. Alış-satış farkı (spread) büyük olduğunda ciddi kayıp yaşatabilir.</p>

<h2>Limit Emir (Limit Order)</h2>
<p>Limit emri, belirlediğiniz fiyattan <strong>veya daha iyi bir fiyattan</strong> işlem gerçekleştirme talimatıdır.</p>
<ul>
  <li><strong>Alım limiti:</strong> "AKBNK'ı en fazla 130₺'den al" — fiyat 130₺ veya altına gelirse işlem olur</li>
  <li><strong>Satım limiti:</strong> "AKBNK'ı en az 140₺'den sat" — fiyat 140₺ veya üstüne çıkarsa işlem olur</li>
</ul>
<p><strong>Avantaj:</strong> Fiyat kontrolü tamamen sizde. Beklediğinizden kötü fiyattan işlem olmaz.</p>
<p><strong>Dezavantaj:</strong> Piyasa belirlediğiniz fiyata ulaşmazsa emir gerçekleşmez, fırsatı kaçırabilirsiniz.</p>

<h2>Stop Emir (Stop Order)</h2>
<p>Stop emir (tetik emri), fiyat belirli bir seviyeye geldiğinde devreye giren emirdir. İki türü vardır:</p>
<ul>
  <li><strong>Stop-Loss:</strong> Zarar kesme emri. "Fiyat 120₺'ye düşerse sat" — fiyat bu seviyeye gelince piyasa emrine dönüşür ve pozisyon kapatılır.</li>
  <li><strong>Stop-Buy (Kır Geç):</strong> Kırılım bekleyen alım. "Fiyat direnç olan 150₺'yi aşarsa al" — trendi teyit eden giriş için kullanılır.</li>
</ul>

<h2>Koşullu Emir (OCO — One Cancels the Other)</h2>
<p>İki emrin aynı anda girildiği; birinin gerçekleşmesi halinde diğerinin otomatik iptal edildiği emir tipidir. Tipik kullanım: "Ya 140₺ hedefe ulaşırsa sat, ya da 120₺ stop seviyesine düşerse sat — ikisinden hangisi önce gerçekleşirse diğeri iptal olsun."</p>

<h2>Hangi Durumda Hangi Emri Kullanmalı?</h2>
<table style="width:100%;border-collapse:collapse;font-size:14px;margin:12px 0">
  <thead>
    <tr style="background:#21262d">
      <th style="padding:8px 12px;text-align:left;color:#8b949e;font-weight:600">Durum</th>
      <th style="padding:8px 12px;text-align:left;color:#8b949e;font-weight:600">Önerilen Emir</th>
    </tr>
  </thead>
  <tbody>
    <tr style="border-top:1px solid #30363d">
      <td style="padding:8px 12px;color:#e6edf3">Açılışta hızlıca girmek istiyorum</td>
      <td style="padding:8px 12px;color:#e6edf3">Piyasa emri (likit hisselerde)</td>
    </tr>
    <tr style="border-top:1px solid #30363d;background:rgba(255,255,255,.02)">
      <td style="padding:8px 12px;color:#e6edf3">Fiyat düşünce almak istiyorum</td>
      <td style="padding:8px 12px;color:#e6edf3">Limit alım emri</td>
    </tr>
    <tr style="border-top:1px solid #30363d">
      <td style="padding:8px 12px;color:#e6edf3">Kırılım sonrası trende girmek istiyorum</td>
      <td style="padding:8px 12px;color:#e6edf3">Stop-buy emri</td>
    </tr>
    <tr style="border-top:1px solid #30363d;background:rgba(255,255,255,.02)">
      <td style="padding:8px 12px;color:#e6edf3">Zarar kesmek istiyorum</td>
      <td style="padding:8px 12px;color:#e6edf3">Stop-loss emri</td>
    </tr>
    <tr style="border-top:1px solid #30363d">
      <td style="padding:8px 12px;color:#e6edf3">Hem hedef hem stop belirlemek istiyorum</td>
      <td style="padding:8px 12px;color:#e6edf3">OCO emri</td>
    </tr>
  </tbody>
</table>

<h2>BorsaPusula Sinyallerinde Stop Loss</h2>
<p>BorsaPusula her hisse için ATR tabanlı bir stop loss seviyesi hesaplar. Bu seviyeyi stop emir olarak girebilirsiniz. Örneğin AKBNK için stop loss 120₺ görünüyorsa, elinizde AKBNK hissesi varken 120₺'lik stop-loss emri girebilirsiniz. Fiyat bu seviyeye düşerse sistem otomatik olarak satış yapar ve büyük zararı önler.</p>
<p>Hisse detay sayfasında SL (Stop Loss) ve TP (Hedef Fiyat) değerlerini görebilir, bunları doğrudan limit veya stop emir olarak aracı kurumunuza girebilirsiniz.</p>
""",
    "faqs": [
      {"q": "Limit emir ile piyasa emri arasındaki fark nedir?",
       "a": "Piyasa emri, o anda en iyi mevcut fiyattan anında işlem gerçekleştirmek için kullanılır. Limit emir ise belirlediğiniz fiyattan veya daha iyi bir fiyattan işlem yapılmasını sağlar; ancak piyasa o fiyata ulaşmazsa emir gerçekleşmez."},
      {"q": "Stop loss emrini nasıl girerim?",
       "a": "Aracı kurum uygulamanızda 'koşullu emir' veya 'stop emir' seçeneğini kullanın. Tetik fiyatı olarak stop loss seviyesini girin. Fiyat bu seviyeye geldiğinde emir devreye girer ve piyasa emrine dönüşerek pozisyonunuz kapatılır."},
      {"q": "BorsaPusula'daki stop loss seviyesini nasıl kullanabilirim?",
       "a": "Hisse detay sayfasında görünen SL (Stop Loss) değerini, aracı kurum uygulamanızda stop emir olarak girebilirsiniz. Bu seviye ATR tabanlı hesaplanmış olup sinyal geçerliyken koruma sağlar. SL seviyesi kırılırsa sinyal da güncellenir."},
      {"q": "Emir iptali nasıl yapılır?",
       "a": "Gün bitmeden gerçekleşmemiş emirler 'günlük emir' olarak ayarlanmışsa günün sonunda otomatik iptal olur. İptal etmek için aracı kurum uygulamanızdaki 'bekleyen emirler' bölümünden manuel iptal de yapabilirsiniz."}
    ],
    "related_tickers": ['AKBNK', 'GARAN', 'THYAO', 'ASELS', 'EREGL']
  },

  # ── ARTICLE 63 ──
  {
    "slug": "borsada-lot-ve-pay-nedir",
    "title": "Lot Nedir? Borsada Lot ve Pay Senedi Alım Rehberi",
    "desc": "Borsada lot kavramı ne demek? Kaç lot almalısınız? Pay senedi, lot adedi ve fraksiyon pay hesaplamalarını pratik örneklerle öğrenin.",
    "date": "2026-05-01",
    "mins": 5,
    "cat": "Temel Kavramlar",
    "body": """
<p>Borsa işlemlerine yeni başlayanların sıkça kafasını karıştıran kavramlardan biri "lot"tur. "1 lot AKBNK alalım" ya da "500 lot GARAN" gibi ifadeler duyduğunuzda ne anlaşılır? Bu rehberde lot kavramını ve pay senedi hesaplamalarını net biçimde açıklıyoruz.</p>

<h2>Lot Nedir?</h2>
<p>Türkiye borsasında (BIST) <strong>1 lot = 1 adet pay senedi</strong> (hisse)dir. Bu tanım 2014'teki Borsa İstanbul reformuyla basitleştirildi. Önceden 1 lot = 1.000 hisse anlamına geliyordu; ancak bu değiştirildi.</p>
<p>Yani AKBNK hissesinden "5 lot" almak istiyorsanız, aslında 5 adet AKBNK pay senedi almak istiyorsunuz demektir. Banka uygulamalarında "adet" veya "pay" olarak da ifade edilebilir.</p>

<h2>Lot Hesabı: Kaç Lira Ödersiniz?</h2>
<p>İşlem maliyeti son derece basit hesaplanır:</p>
<pre style="background:#161b22;border:1px solid #30363d;border-radius:6px;padding:12px;font-size:13px;color:#e6edf3">
Maliyet = Lot Adedi × Hisse Fiyatı × (1 + Komisyon Oranı)

Örnek — AKBNK @ 130₺, 100 lot:
100 × 130 = 13.000₺ (komisyon hariç)
Komisyon %0,03 → 13.000 × 0,0003 = 3,9₺
Toplam ≈ 13.003,90₺
</pre>

<h2>Minimum Lot Miktarı Var mı?</h2>
<p>BIST hisse piyasasında minimum 1 lot (1 adet) ile işlem yapılabilir. Bu, düşük bütçeli yatırımcılar için büyük bir avantajdır. 5 TL'lik bir hisseden 1 lot alabilirsiniz.</p>
<p>Bazı aracı kurumlar minimum işlem tutarı belirlemiş olsa da yasal bir zorunluluk değildir. Büyük çoğunluk minimum tutar uygulamaz.</p>

<h2>Fraksiyon Pay Nedir?</h2>
<p>Belirli kurumsal işlemlerde (sermaye artırımı, bedelsiz pay dağıtımı, bölünme gibi) tam sayı olmayan pay miktarları oluşabilir. Bu durumda <strong>fraksiyon pay</strong> hesabınıza yansır. Örneğin 135 lotunuz varken %10 bedelsiz pay geldiğinde 13,5 pay oluşur; 13 pay hesabınıza girer, 0,5 pay ise para olarak ödenir veya yukarı yuvarlama yapılır (aracı kuruma göre farklılık gösterir).</p>

<h2>Borsa'da Kaç Lot Almalısınız?</h2>
<p>Bütçenizi tek bir hisseye bağlamak yerine portföy çeşitlendirmesi yapmanız önerilir:</p>
<ul>
  <li><strong>Küçük bütçe (1.000-5.000₺):</strong> 1-2 hisse, az lot — önce öğrenmek için</li>
  <li><strong>Orta bütçe (5.000-50.000₺):</strong> 5-10 farklı hisse, pozisyon başı portföyün %10-15'i</li>
  <li><strong>Büyük bütçe (50.000₺+):</strong> 10-20 hisse, sektör çeşitlendirmesi, her pozisyon %5-10</li>
</ul>

<h2>Lot Değişimi — Hisse Bölünmesi (Spliyt)</h2>
<p>Borsa'da bir hisse <strong>bölünmesi (stock split)</strong> gerçekleştiğinde, sahip olduğunuz lot adedi artar ancak toplam değer aynı kalır. Örneğin 2'ye bölünme (1:2 split) olduğunda, elimizdeki 100 lot AKBNK → 200 lot AKBNK'ya dönüşür, ancak her lotun değeri yarıya iner.</p>
<p>Bu durum psikolojik bir yanılgıya yol açabilir: Elinizdeki hisse adedi ikiye katlandığı için daha zenginmiş gibi hissedebilirsiniz, oysa toplam değer değişmez.</p>

<h2>BorsaPusula'da Lot Bazlı Hesaplamalar</h2>
<p>BorsaPusula Portföy sayfasında hisse adedini (lot) girerek portföyünüzün toplam değerini, kâr/zarar durumunu ve stop loss seviyesini izleyebilirsiniz. Örneğin 200 lot ASELS girildiğinde, algoritmik stop loss seviyesine göre maksimum zarar tutarı otomatik hesaplanır.</p>
""",
    "faqs": [
      {"q": "1 lot ne kadar eder?",
       "a": "1 lot, 1 adet hisse senedi (pay senedi) anlamına gelir. Maliyeti hissenin güncel fiyatına eşittir. AKBNK 130₺ ise 1 lot AKBNK = 130₺'dir (komisyon hariç)."},
      {"q": "BIST'te minimum kaç lot alınabilir?",
       "a": "Borsa İstanbul Pay Piyasası'nda minimum 1 lot (1 adet pay) ile işlem yapılabilir. Çoğu aracı kurum minimum tutar belirlememektedir; dolayısıyla 1 adet hisse alabilirsiniz."},
      {"q": "Lot ile pay aynı şey midir?",
       "a": "Evet, Türkiye borsasında 1 lot = 1 pay (hisse) = 1 adet hisse senedidir. 2014 reformundan önce 1 lot 1.000 hisseye eşitti; artık 1:1 oranındadır. Banka uygulamalarında 'lot', 'pay' veya 'adet' kelimeleri aynı anlama gelir."},
      {"q": "Hisse bölünmesi (split) sonrasında lotlarım ne olur?",
       "a": "Split oranında lot adedisi artar, fiyat aynı oranda düşer. Toplam değer değişmez. 2:1 split olduğunda 100 lot → 200 lot olur ama her lot değeri yarıya iner. Portföyünüzün toplam değeri aynı kalır."}
    ],
    "related_tickers": ['AKBNK', 'GARAN', 'THYAO', 'EREGL', 'ASELS']
  },

  # ── ARTICLE 64 ──
  {
    "slug": "yuksek-enflasyonda-yatirim-araclari",
    "title": "Yüksek Enflasyonda Yatırım Araçları: 2026 Türkiye Rehberi",
    "desc": "Yüksek enflasyon döneminde tasarrufları nasıl korunur? Altın, hisse, döviz, TÜFE tahvil ve diğer enflasyon koruyucu araçların karşılaştırması.",
    "date": "2026-05-01",
    "mins": 8,
    "cat": "Strateji",
    "body": """
<p>Türkiye son yıllarda kronik yüksek enflasyonla yaşıyor. Bu ortamda bankada vadeli mevduat bile enflasyonun altında kalan gerçek kayba yol açabiliyor. Peki tasarruflarınızı enflasyona karşı nasıl korursunuz?</p>

<h2>Enflasyon Yatırımcıyı Nasıl Etkiler?</h2>
<p>Enflasyon, paranızın satın alma gücünü eritir. Yılık enflasyon %50 iken bankada %40 faiz alıyorsanız, <em>reel anlamda</em> %10 kaybediyorsunuz demektir. Reel getiri = Nominal getiri − Enflasyon oranı.</p>
<p>Yatırım araçları genellikle iki kategoriye ayrılır:</p>
<ul>
  <li><strong>Reel varlıklar:</strong> Fiyatı enflasyonla birlikte yükselen varlıklar (altın, hisse senedi, gayrimenkul, emtia)</li>
  <li><strong>Nominal varlıklar:</strong> Sabit tutarda geri ödenen araçlar (nakit, sabit faizli mevduat/tahvil)</li>
</ul>
<p>Yüksek enflasyon dönemlerinde reel varlıklara yönelmek mantıklı bir stratejidir.</p>

<h2>Enflasyona Karşı Yatırım Araçları Karşılaştırması</h2>
<table style="width:100%;border-collapse:collapse;font-size:14px;margin:12px 0">
  <thead>
    <tr style="background:#21262d">
      <th style="padding:8px 12px;text-align:left;color:#8b949e;font-weight:600">Araç</th>
      <th style="padding:8px 12px;text-align:left;color:#8b949e;font-weight:600">Enflasyon Koruması</th>
      <th style="padding:8px 12px;text-align:left;color:#8b949e;font-weight:600">Risk</th>
      <th style="padding:8px 12px;text-align:left;color:#8b949e;font-weight:600">Likidite</th>
    </tr>
  </thead>
  <tbody>
    <tr style="border-top:1px solid #30363d">
      <td style="padding:8px 12px;color:#e6edf3">Altın (TL bazlı)</td>
      <td style="padding:8px 12px;color:#3fb950">✅ Güçlü</td>
      <td style="padding:8px 12px;color:#e6edf3">Orta</td>
      <td style="padding:8px 12px;color:#3fb950">Yüksek</td>
    </tr>
    <tr style="border-top:1px solid #30363d;background:rgba(255,255,255,.02)">
      <td style="padding:8px 12px;color:#e6edf3">Hisse Senedi (BIST)</td>
      <td style="padding:8px 12px;color:#3fb950">✅ Orta-Güçlü</td>
      <td style="padding:8px 12px;color:#f85149">Yüksek</td>
      <td style="padding:8px 12px;color:#3fb950">Yüksek</td>
    </tr>
    <tr style="border-top:1px solid #30363d">
      <td style="padding:8px 12px;color:#e6edf3">Döviz (USD/EUR)</td>
      <td style="padding:8px 12px;color:#3fb950">✅ Güçlü (TL depreciation)</td>
      <td style="padding:8px 12px;color:#e6edf3">Orta</td>
      <td style="padding:8px 12px;color:#3fb950">Yüksek</td>
    </tr>
    <tr style="border-top:1px solid #30363d;background:rgba(255,255,255,.02)">
      <td style="padding:8px 12px;color:#e6edf3">TÜFE Tahvil (Hazine)</td>
      <td style="padding:8px 12px;color:#3fb950">✅ Tam</td>
      <td style="padding:8px 12px;color:#e6edf3">Düşük</td>
      <td style="padding:8px 12px;color:#e6edf3">Orta</td>
    </tr>
    <tr style="border-top:1px solid #30363d">
      <td style="padding:8px 12px;color:#e6edf3">Kira Geliri (GYO/BYF)</td>
      <td style="padding:8px 12px;color:#e6edf3">⚠️ Sektöre Bağlı</td>
      <td style="padding:8px 12px;color:#e6edf3">Orta</td>
      <td style="padding:8px 12px;color:#3fb950">Yüksek</td>
    </tr>
    <tr style="border-top:1px solid #30363d;background:rgba(255,255,255,.02)">
      <td style="padding:8px 12px;color:#e6edf3">Sabit Mevduat (TL)</td>
      <td style="padding:8px 12px;color:#f85149">❌ Yetersiz</td>
      <td style="padding:8px 12px;color:#3fb950">Çok Düşük</td>
      <td style="padding:8px 12px;color:#3fb950">Yüksek</td>
    </tr>
    <tr style="border-top:1px solid #30363d">
      <td style="padding:8px 12px;color:#e6edf3">Kripto (BTC)</td>
      <td style="padding:8px 12px;color:#e6edf3">⚠️ Spekülatif</td>
      <td style="padding:8px 12px;color:#f85149">Çok Yüksek</td>
      <td style="padding:8px 12px;color:#3fb950">Yüksek</td>
    </tr>
  </tbody>
</table>

<h2>Altın: Klasik Enflasyon Koruması</h2>
<p>Altın, TL bazında değerlendiğinde uzun vadede enflasyonu genellikle aşar çünkü iki faktör birden altın fiyatını yukarı taşır: hem küresel altın fiyatındaki artış hem de TL'nin USD karşısında değer kaybı.</p>
<p>Fiziksel altın yerine borsa üzerinden işlem gören <a href="/altin">altın</a> takip etmek daha pratiktir. BIST'te gram altın, çeyrek altın ve altın BYF işlem görür.</p>

<h2>Hisse Senedi: Uzun Vadede Enflasyonun Üzerinde</h2>
<p>BIST hisseleri uzun vadede —özellikle güçlü piyasa koşullarında— enflasyonu geçmiştir. Ancak bu uzun vadeli bir ilişkidir; kısa vadede hisseler enflasyondan bağımsız hareket edebilir. Özellikle:</p>
<ul>
  <li><strong>Bankacılık hisseleri:</strong> Yüksek faiz ortamından kâr eden sektör</li>
  <li><strong>Enerji ve emtia:</strong> Ham madde fiyatlarıyla birlikte yükselebilir (EREGL, PETKM, TUPRS)</li>
  <li><strong>GYO (Gayrimenkul Yatırım Ortaklıkları):</strong> Kira geliri + gayrimenkul değer artışı</li>
  <li><strong>Nakit pozisyonu zayıf şirketler:</strong> Yüksek borçluluk oranı, enflasyonda tehlikeli</li>
</ul>

<h2>TÜFE Tahvilleri: Garantili Reel Getiri</h2>
<p>Hazine tarafından ihraç edilen TÜFE'ye endeksli tahvillerde anaparanız enflasyon oranında güncellenir. Ek olarak küçük bir reel faiz de alırsınız. Örneğin %50 enflasyon ile TÜFE tahvil tutuyorsanız, anaparanız %50 büyür; üzerine %2-4 reel faiz de eklenir.</p>
<p>Dezavantajı: Vade öncesi satışta fiyat iskontosu olabilir. En iyisi vadeye kadar tutmaktır.</p>

<h2>Döviz: Basit Ama Dikkatli Olunması Gereken</h2>
<p>TL'nin uzun vadeli değer kaybı tarihi bir gerçektir. Döviz alımı bu nedenle cazip görünür. Ancak:</p>
<ul>
  <li>Döviz mevduatının faizi TL mevduata göre düşüktür</li>
  <li>TCMB müdahale dönemlerinde kur sabitlenebilir, beklenmedik zararlar oluşabilir</li>
  <li>Ani TL güçlenme dönemlerinde döviz tutanlar kayıpla satmak zorunda kalabilir</li>
</ul>

<h2>Pratik Öneriler — 2026 Türkiye için</h2>
<ol>
  <li><strong>Tek araca bağlı kalmayın:</strong> Altın + hisse + TÜFE tahvil kombinasyonu</li>
  <li><strong>Nakit tamponunuzu koruyun:</strong> Portföyün %15-20'si her zaman likit tutun</li>
  <li><strong>Kısa vadeli düşünmeyin:</strong> Enflasyon koruması uzun vadeli bir oyundur</li>
  <li><strong>Borçlanmayın:</strong> Yüksek faiz döneminde borçla yatırım tehlikelidir</li>
  <li><strong>Sinyal takibi yapın:</strong> Hisse seçiminde BorsaPusula gibi teknik analiz araçlarını kullanın</li>
</ol>
""",
    "faqs": [
      {"q": "Enflasyona karşı en iyi yatırım aracı hangisi?",
       "a": "Türkiye'de enflasyona karşı en güçlü araçlar tarihsel olarak altın (TL bazlı), hisse senedi (uzun vadeli) ve TÜFE'ye endeksli tahvillerdir. Tek araca bağlı kalmak yerine çeşitlendirme yapılması önerilir."},
      {"q": "TÜFE tahvili nedir, nasıl alınır?",
       "a": "Hazine'nin ihraç ettiği, anaparası Türkiye enflasyon endeksine (TÜFE) bağlı devlet tahvilidir. Anaparanız enflasyon oranında güncellenir, üzerine küçük bir reel faiz de eklenir. Aracı kurumlar veya bankalar üzerinden satın alınabilir."},
      {"q": "Hisse senedi enflasyona karşı korur mu?",
       "a": "Uzun vadede evet. BIST hisseleri uzun dönemde çoğunlukla enflasyonu aşmıştır. Ancak kısa vadede hisseler enflasyondan bağımsız düşebilir. Özellikle bankacılık ve emtia sektörü hisseleri yüksek faiz ve enflasyon ortamından genellikle olumlu etkilenir."},
      {"q": "Enflasyon döneminde nakit tutmak mantıklı mı?",
       "a": "Yüksek enflasyon döneminde nakit (TL) tutmak alım gücü kaybettirir. Ancak acil fon ve kısa vadeli ihtiyaçlar için mutlaka likit bölüm bulundurun. Uzun vadeli birikimler için enflasyonun üzerinde getiri sağlayan araçlara yönelin."}
    ],
    "related_tickers": ['AKBNK', 'EREGL', 'TUPRS', 'SASA', 'EKGYO']
  },

  # ── ARTICLE 65 ──
  {
    "slug": "bayrak-kanat-ucgen-grafik-formasyonlari",
    "title": "Bayrak, Kanat ve Üçgen Grafik Formasyonları: Devam Sinyalleri",
    "desc": "Teknik analizde bayrak, flama, yükselen/alçalan kanat ve simetrik üçgen formasyonları nasıl tespit edilir ve yorumlanır? Pratik örneklerle rehber.",
    "date": "2026-05-01",
    "mins": 7,
    "cat": "Teknik Analiz",
    "body": """
<p>Grafik formasyonları, fiyat hareketlerindeki tekrar eden kalıplardır. Teknik analistler bu kalıpları kullanarak trendin süreceğini veya tersineceğini tahmin etmeye çalışır. Bu makalede <strong>devam formasyonlarını</strong> öğreneceksiniz: bayrak, flama (kanat) ve üçgen.</p>

<h2>Devam Formasyonu Nedir?</h2>
<p>Devam formasyonu, mevcut trendin bir süre konsolidasyon (duraklama) yapıp aynı yönde devam edeceğine işaret eden grafik kalıplarıdır. Trend yukarıysa yukarı, aşağıysa aşağı devam sinyali verir.</p>
<p>Devam formasyonları, trend takip sistemleriyle (Supertrend, EMA kırılım gibi) birleştirildiğinde daha güvenilir giriş noktaları sunar.</p>

<h2>Bayrak Formasyonu (Flag)</h2>
<p>Bayrak, güçlü bir fiyat hareketi (direk) ardından gelen küçük ve dar bir konsolidasyondan (bayrak bezi) oluşur.</p>
<ul>
  <li><strong>Boğa bayrağı:</strong> Hızlı yükseliş (direk) + küçük aşağı eğimli konsolidasyon → Yukarı kırılım beklenir</li>
  <li><strong>Ayı bayrağı:</strong> Hızlı düşüş (direk) + küçük yukarı eğimli konsolidasyon → Aşağı kırılım beklenir</li>
</ul>
<p>Bayrak formasyonunda hacim önemlidir: Kırılım yüksek hacimle gerçekleşirse formasyon güvenilirliği artar. Hedef fiyat genellikle "direk boyunun" kırılım noktasına eklenmesiyle hesaplanır.</p>

<h2>Flama Formasyonu (Pennant)</h2>
<p>Flama, bayrak formasyonuna benzer ancak konsolidasyon bölümü dikdörtgen değil, giderek daralan üçgen şeklindedir. Bayrak bezindeki konsolidasyon eğimli bir banttan oluşurken, flamada her iki bant da birbirine doğru yaklaşır.</p>
<ul>
  <li>Kısa süre içinde daralan bir konsolidasyon görülür</li>
  <li>Hacim konsolidasyon boyunca azalır, kırılımda artar</li>
  <li>Hedef: direk boyunun kırılım noktasına eklenmesi</li>
</ul>

<h2>Simetrik Üçgen (Symmetrical Triangle)</h2>
<p>Simetrik üçgen, alçalan tepe ve yükselen dip noktalarının oluşturduğu sıkışma formasyonudur. Her iki bant birbirine doğru daralmaktadır.</p>
<ul>
  <li>Yukarı veya aşağı kırılım olabilir (yön belirsiz)</li>
  <li>Kırılım öncesinde hacim düşer, kırılımda artar</li>
  <li>Mevcut trendin yönünde kırılma ihtimali daha yüksektir</li>
  <li>Kırılım olmadan tepe noktasına yaklaşılırsa patlama gücü azalır</li>
</ul>

<h2>Yükselen Üçgen (Ascending Triangle)</h2>
<p>Altta giderek yükselen dip noktaları ve üstte yatay dirençten oluşur. Bu formasyon boğa sinyalidir — yeterli güç toplandığında direnç kırılarak yukarı patlama beklenir.</p>
<p>Bankacılık hisselerinde konsolidasyon sıklıkla yükselen üçgen şeklinde oluşur.</p>

<h2>Alçalan Üçgen (Descending Triangle)</h2>
<p>Üstte alçalan tepe noktaları, altta yatay destekten oluşur. Ayı sinyalidir — destek kırıldığında aşağı patlama beklenir. Teknik satış emirleri genellikle bu kırılım noktasının altına konumlandırılır.</p>

<h2>Formasyonları BorsaPusula Sinyalleriyle Birleştirmek</h2>
<p>BorsaPusula sistemi Supertrend + ADX + EMA kırılımını baz alır; grafik formasyonları ek teyit olarak kullanılabilir:</p>
<ul>
  <li>Hisse AL sinyalindeyken yükselen üçgen üst bandı kırıyorsa → Güçlü alım sinyali</li>
  <li>Hisse BEKLE sinyalindeyken bayrak konsolidasyonundan çıkış görülüyorsa → Önceden takibe al</li>
  <li>Formasyonun hacim desteği varsa → Sinyal güvenilirliği artar</li>
</ul>
<p>Formasyonlar tek başına yeterli değildir. Her zaman trend yönüyle ve hacim verileriyle teyit edin.</p>

<h2>En Sık Yapılan Hatalar</h2>
<ul>
  <li>Formasyon tamamlanmadan pozisyon açmak (kırılımı bekleyin)</li>
  <li>Her konsolidasyonu formasyon olarak yorumlamak</li>
  <li>Düşük hacimdeki kırılımı güvenilir saymak</li>
  <li>Stop loss koymadan formasyon oyunu oynamak</li>
</ul>
""",
    "faqs": [
      {"q": "Bayrak ve flama formasyonu arasındaki fark nedir?",
       "a": "Her ikisi de güçlü bir hareket (direk) sonrası konsolidasyon formasyonudur. Bayrakta konsolidasyon bölümü eğimli paralel bantlar arasında oluşurken, flamada (pennant) konsolidasyon giderek daralan simetrik bir üçgen şeklindedir."},
      {"q": "Simetrik üçgenin kırılımı hangi yönde olur?",
       "a": "Simetrik üçgen tek başına yön belirtmez. Mevcut trendin yönünde kırılma ihtimali genellikle daha yüksektir. Yükselen trendde oluşan simetrik üçgenin yukarı kırılması, alçalan trendde aşağı kırılması daha olasıdır."},
      {"q": "Grafik formasyonları tek başına yatırım kararı için yeterli midir?",
       "a": "Hayır. Grafik formasyonları yardımcı araçlardır; tek başına yeterli değildir. Trend yönü, hacim teyidi ve diğer teknik göstergeler (ADX, Supertrend, RSI) ile birlikte değerlendirildiğinde daha güvenilir sinyaller üretir."},
      {"q": "Kırılımı onaylamak için ne kadar beklenmeli?",
       "a": "Güçlü bir kapanış kırılımın teyidi için en sağlıklı yöntemdir. Tek mumun kırılması yetersiz — ardışık 1-2 kapanış kırılım noktasının üzerinde/altında gerçekleşmesi ve hacmin artması güvenilirliği artırır."}
    ],
    "related_tickers": ['AKBNK', 'ASELS', 'THYAO', 'EREGL', 'GARAN']
  },

  # ── ARTICLE 66 ──
  {
    "slug": "kucuk-sermayeyle-borsaya-baslamak",
    "title": "Küçük Sermayeyle Borsaya Başlamak: 1.000₺ ile Ne Yapılır?",
    "desc": "Az sermayeyle borsaya nasıl başlanır? 1.000-10.000₺ bütçeyle hisse senedi yatırımı yapmanın pratik rehberi ve sık yapılan başlangıç hataları.",
    "date": "2026-05-01",
    "mins": 6,
    "cat": "Temel Kavramlar",
    "body": """
<p>Borsaya girmek için büyük bir sermayeye ihtiyacınız olmadığını biliyor muydunuz? BIST'te 1 adet hisse bile alabilirsiniz — bu da 5₺'dan başlayabileceğiniz anlamına gelir. Ancak küçük sermayeyle verimli bir yatırım yapmak, doğru strateji gerektiriyor.</p>

<h2>1.000₺ – 5.000₺ Arası: Ne Yapmalısınız?</h2>
<p>Bu bütçe aralığında temel hedef <strong>öğrenmek</strong> olmalıdır. Kazanç ikincil plandadır çünkü küçük sermayeyle gerçek kazanç sınırlı olsa da gerçek parayla yaşanan deneyim, hiçbir kitabın veremeyeceği bir eğitim sağlar.</p>

<h3>Yapılacaklar:</h3>
<ul>
  <li>Tek bir likit ve takibi kolay hisse ile başlayın (örn. AKBNK, GARAN, THYAO gibi BIST30 hisseleri)</li>
  <li>Sermayenizin tamamını tek bir hisseye koymayın — en fazla iki hisse seçin</li>
  <li>Her işlemi neden yaptığınızı bir not defterine yazın — sonra geri dönüp okuyun</li>
  <li>Stop loss kullanın, kaybı sınırlayın</li>
  <li>Borsaya acele ettiren haberlere veya sosyal medya yorumlarına inanmayın</li>
</ul>

<h3>Yapılmayacaklar:</h3>
<ul>
  <li>Kaldıraçlı ürünlere (VİOP) girmek — başlangıç sermayesini bir gecede bitirebilir</li>
  <li>Kripto piyasasında margin trading — profesyoneller bile ciddi kayıplar yaşar</li>
  <li>Düşen hisseyi "zarar kesinleşmesin" diye tutmak</li>
  <li>Bir tanıdığın önerisine körü körüne güvenmek</li>
</ul>

<h2>5.000₺ – 20.000₺: Çeşitlendirme Başlar</h2>
<p>Bu aralıkta 3-5 farklı hisseye dağılım yapabilir, sektörel çeşitlendirmeye başlayabilirsiniz. Bankacılık + enerji + savunma gibi farklı sektörlerden seçim yapın.</p>
<p>Her pozisyon için toplam portföyün maksimum %25-30'unu kullanın. Bu sınır, bir hissenin ciddi düşüşünün sizi harabe etmesini engeller.</p>

<h2>Komisyon Maliyetlerine Dikkat</h2>
<p>Küçük sermayeli yatırımcılar için komisyon oranı kritik bir maliyettir. 1.000₺ işlem için %0,15 komisyon = 1,5₺ görünüşte küçük, ancak sık işlem yaparsanız bu maliyet birikir.</p>
<table style="width:100%;border-collapse:collapse;font-size:14px;margin:12px 0">
  <thead>
    <tr style="background:#21262d">
      <th style="padding:8px 12px;text-align:left;color:#8b949e;font-weight:600">Komisyon Oranı</th>
      <th style="padding:8px 12px;text-align:left;color:#8b949e;font-weight:600">1.000₺ işlem</th>
      <th style="padding:8px 12px;text-align:left;color:#8b949e;font-weight:600">Yıllık 50 işlem</th>
    </tr>
  </thead>
  <tbody>
    <tr style="border-top:1px solid #30363d">
      <td style="padding:8px 12px;color:#e6edf3">%0,03 (düşük)</td>
      <td style="padding:8px 12px;color:#e6edf3">0,30₺</td>
      <td style="padding:8px 12px;color:#e6edf3">15₺</td>
    </tr>
    <tr style="border-top:1px solid #30363d;background:rgba(255,255,255,.02)">
      <td style="padding:8px 12px;color:#e6edf3">%0,10 (orta)</td>
      <td style="padding:8px 12px;color:#e6edf3">1₺</td>
      <td style="padding:8px 12px;color:#e6edf3">50₺</td>
    </tr>
    <tr style="border-top:1px solid #30363d">
      <td style="padding:8px 12px;color:#f85149">%0,30 (yüksek)</td>
      <td style="padding:8px 12px;color:#f85149">3₺</td>
      <td style="padding:8px 12px;color:#f85149">150₺</td>
    </tr>
  </tbody>
</table>
<p>Küçük sermayeyle işlem yapanlar için düşük komisyon sunan aracı kurumları araştırın.</p>

<h2>DCA Stratejisi: Küçük Sermayenin En İyi Dostu</h2>
<p>Tek seferde büyük bir yatırım yapmak yerine, her ay düzenli olarak küçük miktarlarda alım yapmak (DCA — Dolar Maliyet Ortalaması) küçük sermayeli yatırımcılar için ideal bir başlangıç stratejisidir.</p>
<ul>
  <li>Her ay 500₺ yatırıyorsanız, bazı aylar ucuza, bazı aylar pahalıya alırsınız</li>
  <li>Uzun vadede maliyet ortalamasını dengeler</li>
  <li>Piyasa zamanlaması yapmaya gerek kalmaz</li>
  <li>Alışkanlık kazandırır — disiplin gelişir</li>
</ul>

<h2>BorsaPusula'yı Küçük Sermayeyle Kullanmak</h2>
<p>Sinyal takip sistemi küçük sermayeli yatırımcılara da tam hizmet verir. <a href="/tarama">Hisse Tarayıcı</a>'da AL sinyali + IDEAL giriş kalitesi filtreleyerek en uygun giriş noktalarındaki hisseleri görüntüleyebilirsiniz. Her hissenin stop loss ve hedef fiyatını görerek risk/ödül oranını hesaplamak kolaylaşır.</p>
""",
    "faqs": [
      {"q": "Borsaya başlamak için minimum ne kadar para gerekir?",
       "a": "BIST'te minimum 1 lot (1 adet hisse) alabilirsiniz. Hissenin fiyatına göre bu 5₺ ile 500₺+ arasında değişebilir. Aracı kurumların çoğunda minimum işlem tutarı yoktur. Ancak gerçek bir öğrenme deneyimi için 1.000-2.000₺ ile başlamanız daha anlamlıdır."},
      {"q": "Küçük sermayeyle kaç hisseye yatırım yapmalıyım?",
       "a": "1.000-5.000₺ arası bütçede 1-2 hisse ile başlamak idealdir. Bu aşama öğrenme aşamasıdır; çeşitlendirme yerine bir hisseyi derinlemesine takip etmek daha değerli bir deneyim kazandırır."},
      {"q": "Küçük sermayeyle VİOP yapılır mı?",
       "a": "Kesinlikle önerilmez. VİOP kaldıraçlı işlemler içerir ve küçük sermayeyi bir gecede sıfıra düşürebilir. Kaldıraçlı ürünlere başlamadan önce en az 2-3 yıl hisse senedi deneyimi kazanılması gerekir."},
      {"q": "DCA stratejisi küçük sermayeyle işe yarar mı?",
       "a": "Evet, DCA (Dolar Maliyet Ortalaması) küçük sermayeli yatırımcılar için en uygun stratejilerden biridir. Her ay düzenli miktarlarda alım yaparak hem piyasa zamanlaması yapmaktan kaçınır hem de portföy birikiminizi sistematik olarak artırırsınız."}
    ],
    "related_tickers": ['AKBNK', 'GARAN', 'THYAO', 'EREGL', 'BIMAS']
  },

  # ── ARTICLE 67 ──
  {
    "slug": "roe-net-kar-marji-sirket-karlilik-analizi",
    "title": "ROE ve Net Kâr Marjı: Şirket Kârlılığını Doğru Okumak",
    "desc": "ROE (özkaynak kârlılığı), ROA ve net kâr marjı nedir? BIST hisseleri için kârlılık oranlarını nasıl yorumlamalısınız? Pratik örneklerle temel analiz rehberi.",
    "date": "2026-05-01",
    "mins": 7,
    "cat": "Temel Analiz",
    "body": """
<p>Bir şirketin gerçekten kârlı olup olmadığını anlamak için fiyat verisine değil, finansal oranlara bakmanız gerekir. Bu oranların başında <strong>ROE (Özkaynak Kârlılığı)</strong> ve <strong>Net Kâr Marjı</strong> gelir. Bu iki metrik, bir şirketin kaynaklarını ne kadar verimli kullandığını gösterir.</p>

<h2>ROE (Return on Equity) Nedir?</h2>
<p>ROE, şirketin <strong>özkaynaklarını kullanarak ne kadar kâr ettiğini</strong> ölçer.</p>
<pre style="background:#161b22;border:1px solid #30363d;border-radius:6px;padding:12px;font-size:13px;color:#e6edf3">
ROE = Net Kâr / Ortalama Özkaynak × 100

Örnek: Net Kâr 1 milyar₺, Özkaynak 5 milyar₺
ROE = 1/5 × 100 = %20
</pre>
<p>Bu, şirketin hissedarlara ait her 100₺ için 20₺ net kâr ürettiği anlamına gelir.</p>

<h3>ROE Nasıl Yorumlanır?</h3>
<table style="width:100%;border-collapse:collapse;font-size:14px;margin:12px 0">
  <thead>
    <tr style="background:#21262d">
      <th style="padding:8px 12px;text-align:left;color:#8b949e;font-weight:600">ROE Değeri</th>
      <th style="padding:8px 12px;text-align:left;color:#8b949e;font-weight:600">Değerlendirme</th>
    </tr>
  </thead>
  <tbody>
    <tr style="border-top:1px solid #30363d">
      <td style="padding:8px 12px;color:#f85149">%0 altı</td>
      <td style="padding:8px 12px;color:#e6edf3">Zarar ediyor — dikkat</td>
    </tr>
    <tr style="border-top:1px solid #30363d;background:rgba(255,255,255,.02)">
      <td style="padding:8px 12px;color:#e6edf3">%0 – %10</td>
      <td style="padding:8px 12px;color:#e6edf3">Düşük kârlılık</td>
    </tr>
    <tr style="border-top:1px solid #30363d">
      <td style="padding:8px 12px;color:#f0883e">%10 – %20</td>
      <td style="padding:8px 12px;color:#e6edf3">Makul, sektöre göre değişir</td>
    </tr>
    <tr style="border-top:1px solid #30363d;background:rgba(255,255,255,.02)">
      <td style="padding:8px 12px;color:#3fb950">%20+</td>
      <td style="padding:8px 12px;color:#e6edf3">Güçlü kârlılık</td>
    </tr>
    <tr style="border-top:1px solid #30363d">
      <td style="padding:8px 12px;color:#3fb950">%30+</td>
      <td style="padding:8px 12px;color:#e6edf3">Excellent — Warren Buffett eşiği</td>
    </tr>
  </tbody>
</table>
<p>⚠️ Önemli: Yüksek borçla çalışan şirketlerde ROE yapay olarak şişebilir. Her zaman borç/özkaynak oranıyla birlikte değerlendirin.</p>

<h2>Net Kâr Marjı Nedir?</h2>
<p>Net kâr marjı, şirketin gelirinin ne kadarını net kâra dönüştürebildiğini gösterir.</p>
<pre style="background:#161b22;border:1px solid #30363d;border-radius:6px;padding:12px;font-size:13px;color:#e6edf3">
Net Kâr Marjı = Net Kâr / Net Satışlar × 100

Örnek: Net Kâr 500M₺, Satışlar 5 milyar₺
Net Kâr Marjı = 500/5000 × 100 = %10
</pre>
<p>Bu, şirketin sattığı her 100₺'lik ürün/hizmetten 10₺ net kâr bıraktığı anlamına gelir.</p>
<p>Sektöre göre "iyi" marj çok farklıdır:</p>
<ul>
  <li><strong>Bankacılık:</strong> %20-40 net kâr marjı normal (faiz gelirleri yüksek)</li>
  <li><strong>Perakende (Bim, Migros):</strong> %2-5 düşük görünür ama hacim ile telafi edilir</li>
  <li><strong>Teknoloji:</strong> %15-40 arasında geniş spektrum</li>
  <li><strong>Petrokimya/Enerji:</strong> Ham madde fiyatına çok duyarlı, döngüsel</li>
</ul>

<h2>ROA (Return on Assets — Aktif Kârlılığı)</h2>
<p>ROA, şirketin tüm varlıklarını (özkaynak + borç) ne kadar verimli kullandığını ölçer.</p>
<pre style="background:#161b22;border:1px solid #30363d;border-radius:6px;padding:12px;font-size:13px;color:#e6edf3">
ROA = Net Kâr / Toplam Aktifler × 100
</pre>
<p>Düşük ROA ama yüksek ROE → Şirket yüksek borç kullanıyor. Kaldıraç hem kazancı hem riski büyütür.</p>

<h2>BIST Hisselerinde Bu Oranları Nerede Bulursunuz?</h2>
<p>BorsaPusula hisse detay sayfalarında P/E oranı, F/K, PD/DD gibi temel veriler gösterilir. Daha detaylı finansal oranlar için:</p>
<ul>
  <li>Şirketin KAP'ta yayımlanan finansal tabloları</li>
  <li>Aracı kurumların hisse analiz sayfaları</li>
  <li>İş Yatırım, Garanti BBVA Yatırım gibi aracı kurumların araştırma raporları</li>
</ul>

<h2>ROE ve Teknik Analizi Birleştirmek</h2>
<p>Yüksek ROE'li bir şirket, güçlü teknik sinyalle birleştiğinde ideal yatırım adayı olabilir. BorsaPusula sinyalleri teknik analizi hızla tarama imkânı sunarken, ROE ve net kâr marjı o hissenin <em>fundamentalinin</em> güçlü olup olmadığını anlamanızı sağlar.</p>
<p>Temel yaklaşım: <strong>Teknik analiz ile giriş zamanlarken, temel analiz ile kalite kontrol yapın.</strong></p>
""",
    "faqs": [
      {"q": "ROE ne anlama gelir ve iyi bir ROE değeri nedir?",
       "a": "ROE (Return on Equity), özkaynak kârlılığı demektir. Şirketin hissedarlara ait sermayeyi ne kadar verimli kullandığını gösterir. Genel kural: %10 altı düşük, %20 üzeri iyi, %30 üzeri mükemmel. Ancak sektöre göre değişir ve borçluluğu da göz önünde bulundurun."},
      {"q": "Net kâr marjı yüksek olan hisse daha mı iyidir?",
       "a": "Yüksek net kâr marjı olumlu bir işarettir, ancak sektörler arası karşılaştırma yaparken dikkatli olun. Bankacılık yüksek marjlı görünürken perakende düşük marjlıdır ama hacim ile telafi eder. Karşılaştırmayı aynı sektördeki rakiplerle yapın."},
      {"q": "ROE ile ROA arasındaki fark nedir?",
       "a": "ROE yalnızca özkaynak üzerinden hesaplanırken, ROA tüm varlıklar (özkaynak + borç) üzerinden hesaplanır. Şirket yüksek borç kullanıyorsa ROE şişebilir. ROA, borç etkisini arındırarak gerçek varlık verimliliğini gösterir."},
      {"q": "BIST hisselerinin ROE değerlerini nereden bulabilirim?",
       "a": "KAP'ta yayımlanan finansal tablolar, aracı kurum araştırma raporları ve Borsa İstanbul veri hizmetlerinden ulaşabilirsiniz. BorsaPusula hisse sayfalarında P/D, F/K gibi temel metrikler gösterilmektedir."}
    ],
    "related_tickers": ['AKBNK', 'GARAN', 'SASA', 'BIMAS', 'ASELS']
  },

  # ── ARTICLE 68 ──
  {
    "slug": "endeks-fonu-mu-bireysel-hisse-mi",
    "title": "Endeks Fonu mu, Bireysel Hisse mi? Hangi Yatırım Stratejisi Daha İyi?",
    "desc": "ETF ve endeks fonlarına yatırım mı, yoksa bireysel hisse seçimi mi daha avantajlı? Risk, getiri ve zaman maliyeti karşılaştırmalı analiz.",
    "date": "2026-05-01",
    "mins": 7,
    "cat": "Strateji",
    "body": """
<p>Borsaya giren çoğu yatırımcı önünde sonunda şu soruyla yüzleşir: "BIST100 endeks fonuna mı yatırsam, yoksa kendi seçtiğim hisselere mi?" Bu iki yaklaşım tamamen farklı zaman, bilgi ve risk profili gerektirir.</p>

<h2>Endeks Fonu (ETF/BYF) Nedir?</h2>
<p>Endeks fonu, belirli bir endeksin (BIST30, BIST100, S&P500 gibi) performansını taklit etmeye çalışan bir yatırım aracıdır. Bir endeks fonuna yatırım yaptığınızda, o endeksteki tüm hisselerden oluşan çeşitlendirilmiş bir sepete sahip olursunuz.</p>
<p>Türkiye'de Borsa İstanbul'da işlem gören BIST30 ve BIST100 borsa yatırım fonları (BYF) mevcuttur. Ayrıca bank portföy yönetim şirketlerinin endeks fonlarına da yatırım yapılabilir.</p>

<h2>İki Yaklaşımın Karşılaştırması</h2>
<table style="width:100%;border-collapse:collapse;font-size:14px;margin:12px 0">
  <thead>
    <tr style="background:#21262d">
      <th style="padding:8px 12px;text-align:left;color:#8b949e;font-weight:600">Özellik</th>
      <th style="padding:8px 12px;text-align:left;color:#3fb950;font-weight:600">Endeks Fonu</th>
      <th style="padding:8px 12px;text-align:left;color:#f0883e;font-weight:600">Bireysel Hisse</th>
    </tr>
  </thead>
  <tbody>
    <tr style="border-top:1px solid #30363d">
      <td style="padding:8px 12px;color:#e6edf3">Çeşitlendirme</td>
      <td style="padding:8px 12px;color:#3fb950">Otomatik (30-100 hisse)</td>
      <td style="padding:8px 12px;color:#e6edf3">Manuel, emek gerektirir</td>
    </tr>
    <tr style="border-top:1px solid #30363d;background:rgba(255,255,255,.02)">
      <td style="padding:8px 12px;color:#e6edf3">Zaman maliyeti</td>
      <td style="padding:8px 12px;color:#3fb950">Çok düşük</td>
      <td style="padding:8px 12px;color:#f85149">Yüksek (araştırma, takip)</td>
    </tr>
    <tr style="border-top:1px solid #30363d">
      <td style="padding:8px 12px;color:#e6edf3">Piyasayı yenme potansiyeli</td>
      <td style="padding:8px 12px;color:#f85149">Yok (endeksin getirisi)</td>
      <td style="padding:8px 12px;color:#3fb950">Var (ama zor)</td>
    </tr>
    <tr style="border-top:1px solid #30363d;background:rgba(255,255,255,.02)">
      <td style="padding:8px 12px;color:#e6edf3">Komisyon maliyeti</td>
      <td style="padding:8px 12px;color:#3fb950">Düşük</td>
      <td style="padding:8px 12px;color:#e6edf3">Her işlemde birikim</td>
    </tr>
    <tr style="border-top:1px solid #30363d">
      <td style="padding:8px 12px;color:#e6edf3">Duygusal stres</td>
      <td style="padding:8px 12px;color:#3fb950">Düşük ("pasif" yaklaşım)</td>
      <td style="padding:8px 12px;color:#f85149">Yüksek (bireysel karar)</td>
    </tr>
    <tr style="border-top:1px solid #30363d;background:rgba(255,255,255,.02)">
      <td style="padding:8px 12px;color:#e6edf3">Öğrenme fırsatı</td>
      <td style="padding:8px 12px;color:#f85149">Düşük</td>
      <td style="padding:8px 12px;color:#3fb950">Yüksek</td>
    </tr>
    <tr style="border-top:1px solid #30363d">
      <td style="padding:8px 12px;color:#e6edf3">Performans (uzun vade)</td>
      <td style="padding:8px 12px;color:#e6edf3">Endeks getirisi</td>
      <td style="padding:8px 12px;color:#e6edf3">Değişken</td>
    </tr>
  </tbody>
</table>

<h2>Akademik Gerçek: Bireysel Hisse Seçmek Zorlu</h2>
<p>ABD'de yapılan araştırmalar, aktif yönetilen fonların büyük çoğunluğunun (%85-90+) uzun vadede ilgili endeksin gerisinde kaldığını göstermektedir. Bu sonuç bireysel yatırımcılar için daha da dramatiktir: Komisyonlar, duygusal kararlar ve yetersiz çeşitlendirme getiriyi büyük ölçüde eritir.</p>
<p>BIST için benzer araştırmalar sınırlı olmakla birlikte, yüksek volatilite ortamında bireysel seçimin başarılı olması için güçlü teknik veya temel analiz becerileri gerekmektedir.</p>

<h2>Hibrit Yaklaşım: En İyisi İkisi Birden</h2>
<p>Çoğu uzman, özellikle yeni başlayanlar için hibrit bir yaklaşım önerir:</p>
<ul>
  <li><strong>Uzun vadeli tasarruf çekirdeği (%60-70):</strong> Endeks fonu — pasif, düşük maliyetli</li>
  <li><strong>Aktif deney bölümü (%30-40):</strong> Bireysel hisse seçimi — öğrenme ve üstün getiri denemesi</li>
</ul>
<p>Bu yapı hem piyasa getirisini güvence altına alırken, hem de bireysel yatırım becerisi geliştirmenizi sağlar.</p>

<h2>BorsaPusula'da Endeks Fonu vs Hisse Dengesi</h2>
<p>Eğer aktif hisse takibine zaman ayırabiliyorsanız, BorsaPusula sinyalleri doğrudan bireysel hisse seçimini destekler. Zaman kısıtınız varsa, portföyünüzün büyük bölümünü endeks fonuna ayırıp geri kalanını takip edebileceğiniz 3-5 BIST100 hissesine yönlendirmek makuldür.</p>
""",
    "faqs": [
      {"q": "Endeks fonu mu daha iyi, bireysel hisse mi?",
       "a": "Her birinin avantajları farklıdır. Endeks fonu otomatik çeşitlendirme ve düşük zaman maliyeti sunar, ancak endeksin üzerinde getiri imkânı yoktur. Bireysel hisse piyasayı yenme fırsatı verir ama derin araştırma, disiplin ve zaman gerektirir."},
      {"q": "Türkiye'de BIST100 endeks fonuna nasıl yatırım yapılır?",
       "a": "Borsa İstanbul'da işlem gören BIST100 BYF'lerine aracı kurum hesabınız üzerinden hisse gibi işlem yapabilirsiniz. Ayrıca bankaların portföy yönetim şirketlerinin endeks fonlarına da yatırım yapılabilir."},
      {"q": "Aktif yönetilen fonlar endeksi geçer mi?",
       "a": "Araştırmalar, aktif yönetilen fonların büyük çoğunluğunun (%85+) uzun vadede ilgili endeksin gerisinde kaldığını göstermektedir. Bunun başlıca nedenleri: yüksek yönetim ücretleri, işlem maliyetleri ve piyasayı sürekli yenmenin zorluğudur."},
      {"q": "Hem endeks fonu hem hisse tutmak mantıklı mı?",
       "a": "Evet, hibrit yaklaşım makuldür. Uzun vadeli tasarrufun büyük bölümü için endeks fonu (güvenli çekirdek), küçük bir kısım için bireysel hisse (öğrenme ve üstün getiri denemesi) kombinasyonu yaygın bir stratejidir."}
    ],
    "related_tickers": ['AKBNK', 'GARAN', 'THYAO', 'EREGL', 'TUPRS']
  },
]

ARTICLES_BY_SLUG = {a["slug"]: a for a in ARTICLES}
CATEGORIES = sorted(set(a["cat"] for a in ARTICLES))
