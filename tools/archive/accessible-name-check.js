#!/usr/bin/env node
// tools/accessible-name-check.js — K-AI: ADI OLMAYAN İNTERAKTİF KONTROLLER
// WCAG 2.1 · SC 4.1.2 "Name, Role, Value" (A)
//
// SORU — K-AH'nin TAM TAMAMLAYICISI, daha önce hiç sorulmadı:
//   K-AH "bilgi yalnız fareye açıktı" diye sordu ve `title=` → `[data-tip]`
//   geçişi yaptı. Ama `title` (son çare olarak) BİR ERİŞİLEBİLİR AD KAYNAĞIDIR;
//   `data-tip` DEĞİLDİR — accname spec'inde adı bile geçmez.
//   Yani K-AH'nin çaresi, adı YALNIZCA title'dan gelen bir kontrolün adını
//   SİLMİŞ olabilir. Bu tur o riski de kapsar.
//   Adı olmayan bir düğmeyi ekran okuyucu "düğme" diye okur: kullanıcı ne
//   yaptığını bilemez. Ses komutuyla ("click X") hiç hedeflenemez.
//
// ⛔ ADI KENDİM HESAPLAMIYORUM — TARAYICININ KENDİSİNE SORUYORUM:
//   CDP `Accessibility.getFullAXTree` ile Chromium'un GERÇEK erişilebilirlik
//   ağacını okuyorum. Elle accname implementasyonu yazmak (aria-labelledby
//   zinciri, gizli-referans, ::before içeriği, label/for, <title> in SVG,
//   value fallback'i…) bu betiğin kendi sahte-pozitif kaynağı olurdu.
//   Bonus: AXTree `ignored` olanları zaten dışarıda bırakır (role=presentation,
//   aria-hidden ata, display:none) — görünürlük kapısı YERLEŞİKTİR.
//
// BULGU ÖLÇÜTÜ (taban SIFIR): AX düğümü ignored DEĞİL + rolü interaktif +
//   `name` BOŞ. Ek kapı yok, çünkü ağacın kendisi kapı.
//
// İKİNCİ EKSEN (--img): SC 1.1.1 "Non-text Content" — AX ağacında görsel rolü
//   taşıyan ve adı BOŞ olan düğümler.
//   ⛔ İLK YAZIMIM KENDİ SAHTE-NEGATİFİYDİ: rolü `img` sandım; Chromium AX
//      ağacı bunu **`image`** diye yazar. Bayrak "SC 1.1.1 ölçüldü" diyordu ama
//      SIFIR düğüm ölçüyordu — rol dağılımı dökülünce çıktı (ana sayfada 25
//      `image` düğümü vardı). Bir bayrağın VARLIĞI ölçüm KANITI değildir.
//   duran ve adı BOŞ olan düğümler. Dekoratif bir görsel `aria-hidden`/
//   `role=presentation` ile ağaçtan ZATEN düşer; ağaçta `img` olarak duruyor
//   ama adı yoksa, ekran okuyucu "resim" diye okur ve içerik kaybolur.
//
// AYRI SINIF (bulgu değil, ayrıca sayılır): rolü interaktif ama DEVRE DIŞI
//   (disabled) düğümler — yine de ad taşımalı, ama sınıfı farklı, ayrı sayılır.
//
// POZİTİF KONTROL (--kill-fix): sayfadaki ilk 12 adlandırılmış düğmenin
//   aria-label/metnini siler; dedektör onları YAKALAMAZSA kördür.
//
// Kullanım: node tools/accessible-name-check.js [--base=...] [--w=375,1280]
//           [--only=/a,/b] [--kill-fix] [--json=dosya]
const { chromium } = require('playwright');

const BASE = (process.argv.find(a => a.startsWith('--base=')) || '').split('=')[1] || 'https://borsapusula.com';
const WIDTHS = ((process.argv.find(a => a.startsWith('--w=')) || '').split('=')[1] || '375,1280')
  .split(',').map(s => parseInt(s, 10)).filter(Boolean);
const ONLY = (process.argv.find(a => a.startsWith('--only=')) || '').split('=')[1] || '';
const JSON_OUT = (process.argv.find(a => a.startsWith('--json=')) || '').split('=')[1] || '';
const KILL_FIX = process.argv.includes('--kill-fix');
// --sim-title-strip: K-AH'nin (commit 4b1faf0, HENÜZ CANLIDA DEĞİL) dönüşümünün
//   ÜST SINIRINI canlı sayfada simüle eder: her `title` → `data-tip`.
//   `title` accname spec'inde SON ÇARE bir ad kaynağıdır, `data-tip` HİÇBİR
//   kaynak değildir. Bu koşum "K-AH bir kontrolün ADINI sildi mi?" sorusunun
//   yanıtıdır. Üst sınır: K-AH aslında 64 title'ın 45'ini dönüştürdü, hepsini
//   değil — bu yüzden çıkan bulgular diff'le ELLE kesiştirilir.
const SIM_STRIP = process.argv.includes('--sim-title-strip');
// --interact: ⛔ AÇILIŞ DURUMU BİR KAPSAM YALANIDIR. Gizli bir açılır katman,
//   modal, gizli sekme paneli veya kapalı <details> içindeki kontrol AX ağacında
//   `ignored` gelir ve ÖLÇÜLMEZ — ama kullanıcı onu açar ve odaklanır.
//   Bu faz sayfadaki bilinen katman dillerini AÇAR, sonra ölçer.
const INTERACT = process.argv.includes('--interact');
const IMG_AXIS = process.argv.includes('--img');
// --sim-fix: K-AI fix'inin CANLI sayfadaki pozitif kontrolü. Fix henüz deploy
//   edilmediği için, şablonlarda yapılan işaretlemeyi sayfa içinde uygular:
//   ad kaynağı OLMAYAN her <svg> -> aria-hidden. Adsız `image` sayısı SIFIRA
//   inmiyorsa çare yanlış yerdedir.
const SIM_FIX = process.argv.includes('--sim-fix');

// reduced-motion / text-clip / focus-obscured / title-tooltip ile AYNI envanter.
const PAGES = [
  '/', '/ozet', '/tarama', '/gundem', '/hisseler', '/sektor-harita',
  '/hisse/ASELS', '/hisse/GARAN', '/karsilastir', '/portfolio',
  '/bilanco-takvimi', '/temettu-takvimi', '/blog', '/blog/rsi-gostergesi-nedir',
  '/metodoloji', '/hakkinda', '/iletisim', '/profil', '/yasal', '/gizlilik',
];
const EXPECT_4XX = new Set(['/profil']);

// SC 4.1.2 ad ZORUNLU olan roller (widget rolleri + link/img değil:
// img ayrı bir SC'nin — 1.1.1 — alanı, bu turda karıştırmıyorum).
const NAMED_ROLES = new Set([
  'button', 'link', 'checkbox', 'radio', 'textbox', 'combobox', 'listbox',
  'searchbox', 'slider', 'spinbutton', 'switch', 'tab', 'menuitem',
  'menuitemcheckbox', 'menuitemradio', 'option', 'treeitem',
]);

async function run() {
  const browser = await chromium.launch();
  const pages = ONLY ? ONLY.split(',') : PAGES;
  const findings = [], disabledFindings = [], errors = [];
  let measured = 0;

  for (const w of WIDTHS) {
    const ctx = await browser.newContext({ viewport: { width: w, height: 900 } });
    for (const p of pages) {
      const page = await ctx.newPage();
      try {
        const res = await page.goto(BASE + p, { waitUntil: 'networkidle', timeout: 45000 });
        const st = res ? res.status() : 0;
        if (st >= 400 && !EXPECT_4XX.has(p)) { errors.push(`${p} @${w}: HTTP ${st}`); await page.close(); continue; }
        await page.waitForTimeout(1200);

        if (INTERACT) {
          await page.evaluate(() => {
            // 1) tüm <details> (SSS akordeonu = sitenin 4. açılır dili, K-AC)
            document.querySelectorAll('details').forEach(d => { d.open = true; });
            // 2) tüm sekme panellerini görünür kıl (gizli panel = ölçülmeyen kontrol, K-T)
            document.querySelectorAll('[role="tabpanel"],.tab-panel,[id^="panel-"]').forEach(el => {
              el.hidden = false; el.removeAttribute('hidden');
              el.style.setProperty('display', 'block', 'important');
              el.style.setProperty('visibility', 'visible', 'important');
              el.classList.add('active'); el.setAttribute('aria-hidden', 'false');
            });
          });
          // 3) bilinen katman tetikleyicileri — tıkla, ölçüme kat, KAPATMA
          //    (hepsi aynı anda açık: bu fazın amacı ad ölçmek, isabet değil)
          const TRIGGERS = ['.header-search-btn', '.bp-nav-more-btn', '.da-search-trigger',
            '.bp-mobile-menu-btn', '.mobile-nav-toggle', '[aria-haspopup]'];
          for (const t of TRIGGERS) {
            const els = await page.$$(t);
            for (const el of els.slice(0, 2)) {
              try { await el.click({ timeout: 1500, force: true }); await page.waitForTimeout(250); } catch (e) {}
            }
          }
          await page.waitForTimeout(600);
        }
        if (SIM_FIX) {
          await page.evaluate(() => {
            for (const el of document.querySelectorAll('svg')) {
              if (el.hasAttribute('aria-hidden') || el.hasAttribute('aria-label') ||
                  el.getAttribute('role') === 'img') continue;
              el.setAttribute('aria-hidden', 'true');
            }
          });
          await page.waitForTimeout(300);
        }
        if (SIM_STRIP) {
          await page.evaluate(() => {
            for (const el of document.querySelectorAll('[title]')) {
              if (el.tagName === 'IFRAME') continue;
              el.setAttribute('data-tip', el.getAttribute('title'));
              el.removeAttribute('title');
            }
          });
          await page.waitForTimeout(200);
        }
        if (KILL_FIX) {
          await page.evaluate(() => {
            const els = [...document.querySelectorAll('button, a[href]')].slice(0, 12);
            for (const el of els) { el.removeAttribute('aria-label'); el.removeAttribute('title');
              [...el.childNodes].forEach(n => { if (n.nodeType === 3) n.textContent = ''; });
              [...el.querySelectorAll('*')].forEach(n => { if (n.tagName !== 'SVG' && n.tagName !== 'svg') n.textContent = ''; }); }
          });
          await page.waitForTimeout(200);
        }

        const cdp = await ctx.newCDPSession(page);
        const { nodes } = await cdp.send('Accessibility.getFullAXTree');
        for (const n of nodes) {
          if (n.ignored) continue;
          const role = n.role && n.role.value;
          if (!(NAMED_ROLES.has(role) || (IMG_AXIS && (role === 'image' || role === 'img')))) continue;
          measured++;
          const name = ((n.name && n.name.value) || '').replace(/\s+/g, ' ').trim();
          if (name) continue;
          // Hangi elemandı? — seçici üret
          let sel = '(çözülemedi)';
          try {
            const { object } = await cdp.send('DOM.resolveNode', { backendNodeId: n.backendDOMNodeId });
            const r = await cdp.send('Runtime.callFunctionOn', {
              objectId: object.objectId, returnByValue: true,
              functionDeclaration: `function(){
                const id=this.id?'#'+this.id:'';
                /* ⛔ SVG'de this.className bir SVGAnimatedString'dir, STRING DEĞİL:
                   typeof kontrolu onu sessizce atlar ve her SVG bulgusu ayirt
                   edilemez "svg" diye raporlanir. getAttribute tek dogru yol. */
                const rawCls=(this.getAttribute&&this.getAttribute('class'))||'';
                const cls=rawCls.trim()?'.'+rawCls.trim().split(/\\s+/).slice(0,2).join('.'):'';
                const par=this.parentElement;
                const pc=par?(par.tagName.toLowerCase()+(par.id?'#'+par.id:'')+(((par.getAttribute&&par.getAttribute('class'))||'').trim()?'.'+par.getAttribute('class').trim().split(/\\s+/)[0]:'')):'';
                const on=(this.getAttribute&&this.getAttribute('onclick')||'').slice(0,40);
                const h=(this.getAttribute&&this.getAttribute('href')||'').slice(0,40);
                const dt=(this.getAttribute&&this.getAttribute('data-tip')||'').slice(0,50);
                const box=this.getBoundingClientRect?this.getBoundingClientRect():{width:0,height:0};
                return this.tagName.toLowerCase()+id+cls
                  +(on?' [onclick='+on+']':'')+(h?' [href='+h+']':'')
                  +(dt?' [data-tip='+dt+']':'')+(pc?' <in '+pc+'>':'')
                  +' {'+Math.round(box.width)+'x'+Math.round(box.height)+'}';
              }`,
            });
            sel = r.result.value || sel;
          } catch (e) { /* düğüm koptu */ }
          const disabled = (n.properties || []).some(pr => pr.name === 'disabled' && pr.value && pr.value.value === true);
          (disabled ? disabledFindings : findings).push({ page: p, w, role, sel });
        }
        await cdp.detach().catch(() => {});
      } catch (e) {
        errors.push(`${p} @${w}: ${e.message.split('\n')[0]}`);
      }
      await page.close();
    }
    await ctx.close();
  }
  await browser.close();

  console.log(`\n=== K-AI · ADI OLMAYAN KONTROLLER (SC 4.1.2) — base=${BASE}${KILL_FIX ? ' [KILL-FIX]' : ''}${SIM_STRIP ? ' [SIM: K-AH title-strip]' : ''}${INTERACT ? ' [INTERACT: katmanlar açık]' : ''}${IMG_AXIS ? ' [+img ekseni SC 1.1.1]' : ''}${SIM_FIX ? ' [SIM-FIX: poz. kontrol]' : ''} ===`);
  console.log(`Ölçülen adlandırılabilir düğüm: ${measured} · Sayfa: ${pages.length} × ${WIDTHS.length} genişlik`);
  if (errors.length) { console.log(`\n⛔ ÖLÇÜLEMEDİ (${errors.length}) — kapsam yalanı riski:`); errors.forEach(e => console.log('   ' + e)); }
  const key = f => `${f.page}|${f.role}|${f.sel}`;
  const uniq = m => { const s = new Map(); for (const f of m) { const k = key(f); if (!s.has(k)) s.set(k, { ...f, ws: [f.w] }); else s.get(k).ws.push(f.w); } return [...s.values()]; };
  const u = uniq(findings), ud = uniq(disabledFindings);
  console.log(`\n🔴 ADSIZ (${u.length} benzersiz / ${findings.length} ölçüm):`);
  u.forEach(f => console.log(`   [${f.page} @${f.ws.join(',')}] role=${f.role}  ${f.sel}`));
  if (ud.length) { console.log(`\n⚪ AYRI SINIF — devre dışı & adsız (${ud.length}):`); ud.forEach(f => console.log(`   [${f.page} @${f.ws.join(',')}] role=${f.role}  ${f.sel}`)); }
  if (JSON_OUT) require('fs').writeFileSync(JSON_OUT, JSON.stringify({ measured, findings: u, disabled: ud, errors }, null, 2));
  console.log(u.length === 0 && errors.length === 0 ? '\n✅ TABAN SIFIR' : '');
  process.exit(u.length || errors.length ? 1 : 0);
}
run();
