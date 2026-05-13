# SENECA → CPO Mailbox

Otomatik analiz mesajları. Her mesajın sonunda "Bekliyor: hayır" işareti → cevap zorunlu değil.

---

## MSG-001
**Tarih:** 2026-05-13  
**Konu:** Competitor Pulse #01 — Bigpara  
**Bekliyor:** hayır  

Merhaba,

Periyodik rakip tarama turumun ilk çıktısını dikkatinize sunuyorum. Bu turda **Bigpara** (bigpara.hurriyet.com.tr) analiz edildi — Türkiye'nin en yüksek trafikli finansal portallarından biri.

### Top 3 Öneri (RICE Sıralı)

| # | Öneri | Tip | RICE | Effort |
|---|-------|-----|------|--------|
| 1 | **Sinyal Yaşı Relative Badge** — `signal_bars` verisini renk-kodlu chip olarak göster; raw tarihi tooltip'e taşı | Fine-tuning | **1330** | 0.5 gün |
| 2 | **Sektör Stats Bar** — Sektör filtresi aktifken "X Güçlü / Y Zayıf / Z Belirsiz" istatistik satırı | Mikro feature | **216** | 1.5 gün |
| 3 | **Sinyal Geçmişi Timeline** — Hisse detay sayfasında son 6-8 sinyal geçişini kompakt zaman çizelgesiyle göster | Yeni feature | **98** | 3 gün |

### Dikkatimi Çeken Asıl Fırsat
`signal_bars` verisi zaten API'de mevcut ve tooltip'te "N gün aktif" olarak gösteriliyor. Ancak asıl tabloda ham tarih görünüyor. Bu **0.5 günlük** düzenlemeyle kullanıcıya büyük bir bilişsel kolaylık sağlanabilir: 5 günlük taze sinyal yeşil chip, 25+ günlük eskimiş sinyal kırmızımsı chip. Bigpara bu bağlamı zaten sağlıyor.

### Bigpara vs BorsaPusula Özeti
Bigpara'nın tek üstünlük alanı: Native mobil app ve bottom navigation. Header nav'ın 900px altında tamamen gizlenmesi önemli bir mobil UX açığı — değerlendirmenize bırakıyorum.

**Detaylı rapor:** `~/claude-agents/borsapusula-ux/analyses/competitor-pulse-2026-05-13-01.md`

— SENECA (BorsaPusula UX Ajanı)
