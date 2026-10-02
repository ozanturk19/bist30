#!/usr/bin/env node
// tools/modal-semantics-check.js — K-S: AÇILABİLİR KATMANIN SEMANTİĞİ (canlı)
//
// NEDEN AYRI BİR ÖLÇÜM
// --------------------
// K-R/K-R2 katmanları AÇTI ama içlerine yalnız GÖRSEL eksenleri (kontrast,
// dokunma hedefi, kırpılma, odak halkası) soktu. Katmanın KENDİ sözleşmesi —
// odak katmana giriyor mu, Tab arkaya kaçıyor mu, Escape kapatıyor mu, kapanışta
// odak tetikleyiciye dönüyor mu, ekran okuyucu arkadaki sayfayı hâlâ görüyor mu,
// katman içinde değişen içerik duyuruluyor mu — hiç ölçülmedi.
// K-R2'nin kendi kapanış notu bunu tarif ediyor:
//   "K-N (canlı bölge) açık katmanda hiç sınanmadı ... mobil sheet ve cloud
//    modal açılınca odak tuzağı/aria-modal davranışı da ölçülmedi."
//
// YÖNTEM: GERÇEK KLAVYE, SENTETİK DEĞİL
// -------------------------------------
// Tab kaçağı `page.keyboard.press('Tab')` ile ölçülür — `el.focus()` ile DEĞİL.
// Sebep: focus-trap.js dinleyicisini KAPSAYICIYA bağlar; odak bir kez dışarı
// kaçtığında tuzak artık hiçbir şey duymaz. Programatik focus() bu kırılmayı
// gizler. Katman tetikleyiciye GERÇEK tıklamayla açılır, çünkü odak iadesinin
// hedefi (`returnEl`) tuzak kurulurken `document.activeElement`ten okunur.
//
// ⛔ ÖLÇÜM SIRASI KATMANIN DURUMUNU BOZAR (bu betiğin ilk koşumunda yakalandı)
// Tek açılışta S1→S2(Tab döngüsü)→S7(yaz)→S3(Esc)→S4 sırayla ölçüldüğünde:
//   · S2'nin 10-19 Tab'ı odağı arama alanından çıkarıyor → S7'nin yazdığı metin
//     input'a HİÇ ulaşmıyor → "canlı bölge güncellenmedi" SAHTE bulgusu (3 sayfa).
//   · nav menüsü Tab-out'ta `focusout` ile KENDİNİ kapatıyor → S3 "Escape çalıştı"
//     sanıyor, S4 de "odak iade edilmedi" diyor; oysa Escape hiç sınanmadı.
// Bu yüzden her eksen KENDİ TEMİZ AÇILIŞINDA ölçülür (faz izolasyonu):
//   FAZ A: S1/S5/S6/S7   FAZ B: S2 (yalnız Tab)   FAZ C: S3/S4 (yalnız Escape)
// Aynı aile: K-O'nun "fare tıklaması :focus-visible'ı zehirler" dersi.
//
// Eksenler (FAIL = sözleşme ihlali, bilgi = kasıtlı olabilir):
//   S1 ODAK-GIRMEDI   açılışta odak katmanın dışında kaldı            (WCAG 2.4.3)
//   S2 TAB-KACAK      Tab ile odak katmandan arka plana çıktı          (2.4.3/2.1.2)
//   S3 ESC-KAPATMIYOR Escape katmanı kapatmadı                         (APG dialog)
//   S4 IADE-YOK       kapanışta odak tetikleyiciye dönmedi             (2.4.3)
//   S5 SEMANTIK       role=dialog / aria-modal / erişilebilir ad eksik (4.1.2)
//   S6 ARKA-PLAN      aria-modal YOK ve arka plan inert/aria-hidden değil
//   S7 SESSIZ-DEGISIM katman içeriği değişiyor ama duyuru yok          (4.1.3)
//
// Kullanım: node tools/modal-semantics-check.js [--base=...] [--w=1280] [--only=/]
const { chromium } = require('playwright');
const fs = require('fs');

const BASE = (process.argv.find(a => a.startsWith('--base=')) || '').split('=')[1] || 'https://borsapusula.com';
const W = parseInt((process.argv.find(a => a.startsWith('--w=')) || '').split('=')[1] || '1280', 10);
const ONLY = (process.argv.find(a => a.startsWith('--only=')) || '').split('=')[1] || '';

// ── Katman reçeteleri ──────────────────────────────────────────────────────
// trigger  : GERÇEK tıklanacak seçici (odak iadesinin hedefi budur)
// container: katmanın kökü
// isOpen   : katman açık mı (sayfa bağlamında çalışır)
// modal    : true → S5/S6 dialog sözleşmesi uygulanır; false → menü (S2/S6 muaf)
// mutate   : opsiyonel, katman içeriğini değiştiren eylem (S7 için)
const LAYERS = [
  {
    name: 'arama-overlay',
    pages: ['/', '/tarama', '/hisse/ASELS', '/portfolio'],
    trigger: '.header-search-btn',
    container: '#bpSearchModal',
    isOpen: () => {
      const o = document.getElementById('bpSearchOverlay');
      return !!o && o.classList.contains('open');
    },
    modal: true,
    mutate: async (page) => { await page.keyboard.type('AS'); await page.waitForTimeout(700); },
  },
  {
    name: 'nav-daha-menusu',
    pages: ['/', '/tarama', '/hisse/ASELS'],
    minW: 1000,
    trigger: '.bp-nav-more-btn',
    container: '.bp-nav-more-menu',
    isOpen: () => {
      const m = document.querySelector('.bp-nav-more-menu');
      return !!m && m.classList.contains('open');
    },
    modal: false,
  },
  {
    name: 'mobil-sheet',
    pages: ['/', '/tarama', '/hisse/ASELS'],
    maxW: 768,
    trigger: '#mbn-bell-btn',
    container: '#mbnSheet',
    isOpen: () => {
      const s = document.getElementById('mbnSheet');
      return !!s && s.classList.contains('open');
    },
    modal: true,
  },
  {
    name: 'cloud-modal',
    pages: ['/portfolio'],
    trigger: '#cloudBtn',
    container: '#cloudModalDialog',
    isOpen: () => {
      const m = document.getElementById('cloudModal');
      return !!m && getComputedStyle(m).display !== 'none';
    },
    modal: true,
  },
];

const inside = (containerSel) => {
  const c = document.querySelector(containerSel);
  const a = document.activeElement;
  return !!(c && a && (c === a || c.contains(a)));
};

const describe = (el) => {
  if (!el) return '(yok)';
  return el.tagName.toLowerCase() +
    (el.id ? '#' + el.id : '') +
    (el.className && typeof el.className === 'string' ? '.' + el.className.trim().split(/\s+/).slice(0, 2).join('.') : '') +
    ' "' + (el.textContent || el.getAttribute('aria-label') || '').trim().slice(0, 30) + '"';
};

(async () => {
  const browser = await chromium.launch();
  const ctx = await browser.newContext({
    viewport: { width: W, height: 900 },
    isMobile: W <= 768, hasTouch: W <= 768,
  });
  const findings = [];
  const rows = [];
  const INS = inside.toString(), DSC = describe.toString();

  // sayfayi yukle + katmani GERCEK tiklamayla ac. Her faz bunu yeniden cagirir
  // (faz izolasyonu: onceki eksenin biraktigi odak/durum tasinmaz).
  const freshOpen = async (L, p) => {
    const page = await ctx.newPage();
    const resp = await page.goto(BASE + p, { waitUntil: 'networkidle', timeout: 45000 });
    if (resp && resp.status() >= 400) { await page.close(); return { skip: `HTTP ${resp.status()}` }; }
    await page.waitForTimeout(1200);
    const trig = await page.$(L.trigger);
    if (!trig) { await page.close(); return { skip: `tetikleyici yok (${L.trigger})` }; }
    await trig.click();
    await page.waitForTimeout(700);
    if (!(await page.evaluate(L.isOpen))) { await page.close(); return { skip: 'katman acilmadi' }; }
    return { page };
  };

  for (const L of LAYERS) {
    if (L.minW && W < L.minW) continue;
    if (L.maxW && W > L.maxW) continue;
    for (const p of L.pages) {
      if (ONLY && p !== ONLY) continue;
      const tag = `${p} [${L.name}] @${W}px`;
      const add = (code, detail) => { findings.push({ page: p, layer: L.name, w: W, code, detail }); };
      const rec = { page: p, layer: L.name, w: W };
      try {
        // ── FAZ A: S1 odak girisi · S5 semantik · S6 arka plan · S7 duyuru ──
        const A = await freshOpen(L, p);
        if (A.skip) { console.log(`${tag}  ATLA (${A.skip})`); continue; }
        {
          const page = A.page;
          const s1 = await page.evaluate(([sel, ins, d]) => {
            const fi = new Function('c', 'return (' + ins + ')(c)');
            const fd = new Function('el', 'return (' + d + ')(el)');
            return { inside: fi(sel), active: fd(document.activeElement) };
          }, [L.container, INS, DSC]);
          if (!s1.inside) add('S1-ODAK-GIRMEDI', `odak: ${s1.active}`);
          rec.s1 = s1;

          const sem = await page.evaluate((sel) => {
            const c = document.querySelector(sel);
            if (!c) return null;
            const top = [...document.body.children].filter(e =>
              !e.contains(c) && e !== c && e.tagName !== 'SCRIPT' && e.tagName !== 'STYLE' &&
              e.getBoundingClientRect().height > 0);
            const bgOpen = top.filter(e => !e.hasAttribute('inert') && e.getAttribute('aria-hidden') !== 'true');
            return {
              role: c.getAttribute('role') || '', modal: c.getAttribute('aria-modal') || '',
              name: c.getAttribute('aria-label') || c.getAttribute('aria-labelledby') || '',
              bgTotal: top.length, bgOpen: bgOpen.length,
              bgList: bgOpen.slice(0, 4).map(e => e.tagName.toLowerCase() + (e.id ? '#' + e.id : (e.className && typeof e.className === 'string' ? '.' + e.className.trim().split(/\s+/)[0] : ''))),
            };
          }, L.container);
          rec.sem = sem;
          if (L.modal && sem) {
            const miss = [];
            if (sem.role !== 'dialog' && sem.role !== 'alertdialog') miss.push('role=dialog yok (' + (sem.role || '-') + ')');
            if (sem.modal !== 'true') miss.push('aria-modal yok');
            if (!sem.name) miss.push('erisilebilir ad yok');
            if (miss.length) add('S5-SEMANTIK', miss.join(' · '));
            if (sem.modal !== 'true' && sem.bgOpen > 0) add('S6-ARKA-PLAN', `aria-modal yok, ${sem.bgOpen}/${sem.bgTotal} ust duzey blok AT'ye acik: ${sem.bgList.join(', ')}`);
          }

          if (L.mutate) {
            const snap = (sel) => {
              const c = document.querySelector(sel);
              const live = [...c.querySelectorAll('[aria-live],[role="status"],[role="alert"]')];
              return {
                liveN: live.length, texts: live.map(e => (e.textContent || '').trim()),
                bodyLen: (c.textContent || '').length,
                atomicBig: live.filter(e => e.getAttribute('aria-atomic') !== 'false' &&
                  e.querySelectorAll('a[href],button').length > 1)
                  .map(e => (e.id || e.className) + ':' + e.querySelectorAll('a[href],button').length),
              };
            };
            const before = await page.evaluate(snap, L.container);
            await L.mutate(page);
            const after = await page.evaluate(snap, L.container);
            rec.live = { before, after };
            const contentChanged = before.bodyLen !== after.bodyLen;
            const liveChanged = JSON.stringify(before.texts) !== JSON.stringify(after.texts);
            if (!contentChanged) add('S7-OLCUM-SUPHELI', 'katman icerigi hic degismedi — mutate etkisiz, S7 olculemedi');
            else if (!after.liveN) add('S7-SESSIZ-DEGISIM', 'katmanda canli bolge YOK, icerik degisiyor');
            else if (!liveChanged) add('S7-SESSIZ-DEGISIM', `${after.liveN} canli bolge var, icerik degisti (${before.bodyLen}->${after.bodyLen} krk) ama duyuru metni AYNI: ${JSON.stringify(after.texts)}`);
            if (after.atomicBig.length) add('S7-ATOMIK-BUYUK', `canli bolge >1 denetim tasiyor: ${after.atomicBig.join(', ')}`);
          }
          await page.close();
        }

        // ── FAZ B: S2 Tab kacagi (TEMIZ acilis, baska hicbir eksen yok) ────
        const B = await freshOpen(L, p);
        if (!B.skip) {
          const page = B.page;
          const nFoc = await page.evaluate((sel) => {
            const c = document.querySelector(sel);
            if (!c) return 0;
            return [...c.querySelectorAll('a[href],button:not([disabled]),input:not([disabled]),select:not([disabled]),textarea:not([disabled]),[tabindex]:not([tabindex="-1"])')]
              .filter(e => e.offsetParent !== null || getComputedStyle(e).position === 'fixed').length;
          }, L.container);
          let escapedAt = -1, escapedTo = '', closedAt = -1;
          const steps = Math.min(Math.max(nFoc * 2 + 3, 8), 40);
          for (let i = 0; i < steps; i++) {
            await page.keyboard.press('Tab');
            await page.waitForTimeout(60);
            const st = await page.evaluate(([sel, ins, d, io]) => {
              const fi = new Function('c', 'return (' + ins + ')(c)');
              const fd = new Function('el', 'return (' + d + ')(el)');
              const fo = new Function('return (' + io + ')()');
              return { open: fo(), inside: fi(sel), active: fd(document.activeElement) };
            }, [L.container, INS, DSC, L.isOpen.toString()]);
            if (!st.open) { closedAt = i + 1; rec.tabOutFocus = st.active; break; }
            if (!st.inside) { escapedAt = i + 1; escapedTo = st.active; break; }
          }
          rec.nFoc = nFoc; rec.escapedAt = escapedAt; rec.closedAt = closedAt;
          if (escapedAt > 0) add('S2-TAB-KACAK', `${escapedAt}. Tab'ta odak disari cikti (katman ACIK): ${escapedTo}  [katmanda ${nFoc} odaklanabilir]`);
          else if (closedAt > 0 && !L.modal) {
            // menu Tab-out'ta kendini kapatiyor: kabul, ama odagin NEREYE dustugu onemli
            rec.note = `menu ${closedAt}. Tab'ta kendini kapatti, odak: ${rec.tabOutFocus}`;
          }
          await page.close();
        }

        // ── FAZ C: S3 Escape · S4 odak iadesi (TEMIZ acilis, Tab YOK) ─────
        const C = await freshOpen(L, p);
        if (!C.skip) {
          const page = C.page;
          const trigDesc = await page.evaluate(([sel, d]) => {
            const fd = new Function('el', 'return (' + d + ')(el)');
            return fd(document.querySelector(sel));
          }, [L.trigger, DSC]);
          await page.keyboard.press('Escape');
          await page.waitForTimeout(500);
          const stillOpen = await page.evaluate(L.isOpen);
          rec.closedByEsc = !stillOpen;
          if (stillOpen) add('S3-ESC-KAPATMIYOR', 'Escape sonrasi katman hala acik');
          else {
            const s4 = await page.evaluate(([sel, d]) => {
              const fd = new Function('el', 'return (' + d + ')(el)');
              const t = document.querySelector(sel);
              return { ok: document.activeElement === t, active: fd(document.activeElement) };
            }, [L.trigger, DSC]);
            rec.s4 = s4;
            if (!s4.ok) add('S4-IADE-YOK', `tetikleyici: ${trigDesc} → odak: ${s4.active}`);
          }
          await page.close();
        }

        rows.push(rec);
        const mine = findings.filter(f => f.page === p && f.layer === L.name);
        console.log(`${tag}  odaklanabilir:${rec.nFoc}  S1:${rec.s1 && rec.s1.inside ? 'ok' : 'FAIL'} S2:${rec.escapedAt > 0 ? 'FAIL@' + rec.escapedAt : 'ok'} S3:${rec.closedByEsc ? 'ok' : 'FAIL'} S4:${rec.s4 ? (rec.s4.ok ? 'ok' : 'FAIL') : '-'}  bulgu:${mine.length}`);
        if (rec.note) console.log(`    (bilgi) ${rec.note}`);
        for (const f of mine) console.log(`    [${f.code}] ${f.detail}`);
      } catch (e) {
        console.log(`${tag}  HATA: ${e.message.split('\n')[0]}`);
      }
    }
  }
  await browser.close();
  const out = '/tmp/ks-modal-' + W + '.json';
  fs.writeFileSync(out, JSON.stringify({ findings, rows }, null, 2));
  console.log(`\nTOPLAM @${W}px — ihlal: ${findings.length}  (ayrinti: ${out})`);
  const byCode = {};
  findings.forEach(f => { byCode[f.code] = (byCode[f.code] || 0) + 1; });
  Object.entries(byCode).forEach(([k, v]) => console.log(`  ${k}: ${v}`));
  process.exit(findings.length > 0 ? 1 : 0);
})();
