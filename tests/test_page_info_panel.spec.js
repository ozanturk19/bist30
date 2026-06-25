/**
 * PageInfoPanel — Manual Smoke Test Instructions
 *
 * No jest/vitest configured. Run these checks in browser DevTools console
 * after loading a page that includes page-info-panel.js via <script> tag.
 *
 * Quick load (standalone test):
 *   1. Open any BorsaPusula page in browser
 *   2. In DevTools console, load the script:
 *      const s = document.createElement('script'); s.src = '/static/js/page-info-panel.js'; document.head.appendChild(s);
 *   3. Run the test block below (copy-paste into console)
 */

/*
=== MANUAL SMOKE TEST BLOCK (paste into DevTools console) ===

const panel = new PageInfoPanel(
  'test',
  'Test Başlığı',
  '<p>Açıklama metni. <a data-term="ema">EMA</a> ve <a data-term="rsi">RSI</a> terimleri.</p>'
);

// 1. render() — DOM element oluşturuldu mu?
const el = panel.render();
console.assert(el instanceof HTMLElement, 'FAIL: render() HTMLElement dönmeli');
console.assert(el.classList.contains('bp-info-panel'), 'FAIL: bp-info-panel class yok');
document.body.prepend(el);
console.log('PASS: render + DOM inject');

// 2. Jargon linkler /metodoloji#X'e gidiyor mu?
const links = el.querySelectorAll('.bp-jargon-link');
console.assert(links.length === 2, `FAIL: 2 jargon link beklendi, ${links.length} bulundu`);
console.assert(links[0].href.includes('/metodoloji#ema'), 'FAIL: EMA link yanlış');
console.assert(links[1].href.includes('/metodoloji#rsi'), 'FAIL: RSI link yanlış');
console.log('PASS: jargon-term linkler');

// 3. Default açık
const body = el.querySelector('.bp-info-panel__body');
console.assert(body.style.opacity !== '0', 'FAIL: default kapalı olmamalı');
console.log('PASS: default açık');

// 4. toggleCollapse() — kapatır
panel.toggleCollapse();
console.assert(body.style.opacity === '0', 'FAIL: toggle sonrası kapalı olmalı');
console.assert(panel.collapsed === true, 'FAIL: collapsed flag true olmalı');

// 5. localStorage kayıt
const stored = localStorage.getItem('bp_page_info_test');
console.assert(stored === 'collapsed', `FAIL: localStorage 'collapsed' beklendi, '${stored}' bulundu`);
console.log('PASS: toggleCollapse + localStorage');

// 6. toggleCollapse() — açar
panel.toggleCollapse();
console.assert(panel.collapsed === false, 'FAIL: ikinci toggle sonrası açık olmalı');
console.assert(localStorage.getItem('bp_page_info_test') === 'open', 'FAIL: localStorage open olmalı');
console.log('PASS: re-open + localStorage');

// 7. CSS transition 200ms kontrol (manuel gözlem)
// DevTools Elements > .bp-info-panel__body > Computed > transition
// Beklenen: max-height 0.2s ease, opacity 0.2s ease
console.log('MANUAL CHECK: .bp-info-panel__body transition 0.2s (not 0.3s+) gözlemle');

// 8. attachToHeader() — page header'ın hemen altına eklendi mi?
const panel2 = new PageInfoPanel('test2', 'Header Testi', '<p>İçerik</p>');
panel2.attachToHeader();
console.assert(document.querySelector('[data-page-key="test2"]'), 'FAIL: attachToHeader DOM ekleme yok');
console.log('PASS: attachToHeader');

// 9. localStorage persistence — yeni instance aynı key'i okuyor mu?
const panel3 = new PageInfoPanel('test', 'Reload Sim', '<p>x</p>');
panel3.render(); // render tetikler loadFromLocalStorage
// collapsed = false (son state open), yani collapsed flag false olmalı
console.assert(panel3.collapsed === false, 'FAIL: localStorage persistence yanlış');
console.log('PASS: localStorage persistence');

// Temizlik
document.querySelectorAll('[data-page-key]').forEach(e => e.remove());
localStorage.removeItem('bp_page_info_test');
localStorage.removeItem('bp_page_info_test2');
console.log('=== TÜM SMOKE TESTLER PASS ===');
*/
