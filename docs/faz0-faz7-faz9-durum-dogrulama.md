# FAZ0/FAZ7/FAZ9 Durum Doğrulaması

**Tarih:** 17.08.2026 · **Kapsam:** Master Dönüşüm Programı'ndaki FAZ 0 (T0.1-T0.10), FAZ 7 (T7.1-T7.4, T7.5 hariç zaten TAMAM) ve FAZ 9 (T9.2-T9.4, T9.1 hariç zaten TAMAM) kalemlerinin canlı kod durumu. **Bu turda yalnız 2 mekanik ölü-kod temizliği yapıldı (`f0f122e`), geri kalan tamamı sınıflandırma/doğrulama — kod değişmedi.**

**Yöntem:** S1/S7/T3.4/T8 disiplini — 3 paralel bağımsız tarama ajanı (biri FAZ0, biri FAZ7, biri FAZ9) → 1 bağımsız kör doğrulama ajanı (3 kritik iddiayı sentezi görmeden sıfırdan SSH ile yeniden üretti). Doğrulama **sıfır anlaşmazlıkla** üç iddianın üçünü de (T0.2 dangling var(), T7.4 boş catch sayısı, T9.4 guard zinciri) birebir doğruladı.

---

## FAZ 0 — Açılış Temizliği (T0.1-T0.10)

Kaynak: tek commit `c57a93b` (07.08.2026, "feat(cpo1321-faz0)"). 9/10 kalem **TAMAM**, doğrulandı.

| # | Durum | Kanıt özeti |
|---|---|---|
| T0.1 | TAMAM | SON_KARARLAR.md'de eski tier kararı üstü-çizili + İPTAL notu (CPO-1321) |
| T0.2 | TAMAM | 6 dangling var() (`--bp-peri/mint/red/line/accent`, `--container-max`) → 0 kullanım, yeni tokenlar yaygın |
| T0.3 | TAMAM | blog_content.py emir kipi → bilgilendirme diline çevrilmiş |
| T0.4 | TAMAM* | kripto_gate.html silinmiş, .bak dosyaları 0 (*attic'e taşınma git-tracked olmadığı için izlenemiyor, ama kabul ölçütü sağlanmış) |
| T0.5 | TAMAM | `/karsilastir?tickers=` noindex,follow + robots.txt 6 satır |
| T0.6 | TAMAM | `/sektor` → 301 → `/sektor-harita` canlı |
| T0.7 | TAMAM | `/nasdaq`/`/sp500` kanonik döngü ters çevrilmiş, `/dow`/`/djia` → 404 |
| T0.8 | TAMAM | sitemap.xml'de 90 adet `/ozet/<tarih>` kaydı |
| **T0.9** | **AÇIK — kod-dışı** | Canlı HTTP testinde CF hâlâ zstd'yi brotli'nin üstünde sunuyor. **Kod erişimiyle çözülemez** — Cloudflare dashboard → Speed/Compression ayarı, tek adımlık panel işlemi. Ozan/CPO'nun CF panelinden yapması gerekiyor. |
| T0.10 | TAMAM | Cache-bust (`?v=`) tutarlı, çift `<link>` font zaten bilinçli preconnect+preload deseni |

## FAZ 7 — Güven Tasarımı (T7.1-T7.4)

| # | Durum | Kanıt özeti |
|---|---|---|
| **T7.1** | **AÇIK — ama doküman muhtemelen bayat** | Ana sayfa rozeti win_rate/avg_ret değil Sharpe/Profit Factor/En iyi getiri gösteriyor. `git log -S'btWinRate'` → **Ozan'ın kendisi** `7b021a2` (02.05.2026, master programdan 3 ay ÖNCE) ile win_rate'i bilinçli kaldırmış ("risk-adjusted metrikler trend-following için daha anlamlı"). Master programın T7.1 kabul ölçütü bu kararla çelişiyor. **CPO kararı gerekiyor: doküman güncellensin mi (kod zaten doğru) yoksa yeniden mi açılsın.** Ölü kod (`wr`/`ar` — hiç markup elementi yoktu) bu turda temizlendi (`f0f122e`). |
| T7.2 | KISMEN | İnsan-dili bayat-veri formatı ("27 sa 53 dk önce") TAMAM, `/hisse` çift bildirim dedup TAMAM. Ama **satır-bazlı tazelik göstergesi hiç yok** (`last_fresh_ts` grep 0 sonuç) — gerçek eksik, ayrı iş kalemi olarak değerlendirilmeli (UX/tasarım kararı gerektirir, bu turda dokunulmadı). |
| T7.3 | TAMAM | MACD/EMA26 çelişkisi 0, `/metodoloji` tek kaynak |
| T7.4 | KISMEN (94%) | 68 boş catch'in 64'ü dolduruldu (DEV2-118, 15.08). Kalan 4 (`hisse.html:2557/2600`, `index.html:3758`, `kategori.html:361`) zaten CPO/Ozan karar kuyruğunda bekliyor, kasıtlı dokunulmadı. Ek bulgu: `static/*.js`'de 11 ayrı boş catch daha var (T7.4'ün 68'lik taraması yalnız `templates/` kapsamındaydı) — style-guard.py'nin K-D ratchet tabanı (15 = 4+11) bunu doğruluyor, ayrı kapsam genişletmesi gerektirir. |

## FAZ 9 — Otomasyon (T9.2-T9.4)

| # | Durum | Kanıt özeti |
|---|---|---|
| T9.2 | TAMAM | format-lint v2 (`tools/style-guard.py` + `tools/lint_scope.py`) `tools/pre-deploy-check.sh` üzerinden deploy'a bloklayıcı bağlı, 8/8 PASS canlı çalıştırıldı |
| **T9.3** | **AÇIK** | VR baseline **54 gün bayat** (`06960c2`, 24.06.2026). Otomasyon/cron yok, "her faz sonunda" disiplini fiilen uygulanmıyor. Bu daha önce bilinen bir durum (DEV2 bilerek yeniden yakalamadı, CPO'nun "ne zaman baseline alınsın" tercihini bekliyor) — yeni bir aksiyon değil, güncel durumun teyidi. |
| T9.4 | TAMAM | 5 guard (K-A/B/C/D + lint_scope) canlı çalıştırıldı, hepsi PASS/ratchet-sabit. Görev talimatındaki `predeploy_lint.sh` isim karışıklığı gerçek kodda da vardı — kökteki dosya bağlantısız/ölüydü, bu turda silindi (`f0f122e`). |

---

## Bu turda yapılan kod değişikliği (`f0f122e`, tek commit, deploy edildi)

1. `templates/index.html` — `wr`/`ar` (`getElementById('btWinRate')`/`btAvgRet`) ölü kod silindi: hiçbir markup elementi bu id'lere sahip değildi, sonuç hiçbir yerde kullanılmıyordu. Görsel/davranışsal etki sıfır.
2. Kökteki `predeploy_lint.sh` silindi — hiçbir script/cron tarafından çağrılmıyordu (yalnız eski `PROJE-DURUM-2026-05.md` dokümanında geçiyordu), gerçek guard zinciri `tools/pre-deploy-check.sh` + `tools/style-guard.py` + `tools/lint_scope.py`.

`pre-deploy-check.sh` 8/8 PASS, `node --check` OK.

## Karar kuyruğuna eklenmesi gereken yeni kalemler

1. **T7.1** — doküman mı güncellensin, kod mu yeniden açılsın (Ozan'ın kendi 02.05 kararıyla çelişki)
2. **T0.9** — CF zstd/brotli önceliği, Ozan'ın CF dashboard'undan manuel yapması gerekiyor (kod erişimi yetersiz)
3. **T7.2 kalan parça** — satır-bazlı tazelik göstergesi (last_fresh_ts hiç kullanılmıyor), UX kararı gerektirir
