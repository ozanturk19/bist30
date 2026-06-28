# F15 — Dark / Light Tema Tasarım Dokümanı

**Sprint 4 W1** | Effort: S | Kod: sıfır (tasarım + CSS variable map)

---

## 1. Durum Analizi

Site **zaten dark-mode**'da çalışıyor (`:root` bloku = dark palette). F15'in görevi:
- Light mode için tam CSS variable seti tanımla
- `data-theme="light"` toggle mekanizması ekle
- `localStorage` persistence (kullanıcı tercihi kaybolmasın)
- `prefers-color-scheme` auto-detect fallback

---

## 2. Mevcut Dark Mode Palette (Referans)

```css
:root {
  /* Backgrounds */
  --bp-bg:       #0e0e12;
  --bp-surface:  #141416;
  --bp-surface2: #1c1b1f;
  --bp-surface3: #201f21;

  /* Borders */
  --bp-border:   #2a2a2c;
  --bp-border2:  #46464d;

  /* Text */
  --bp-text:     #e5e1e4;   /* primary */
  --bp-text2:    #c7c5cd;   /* secondary */
  --bp-text3:    #909097;   /* muted / caption */

  /* Brand */
  --bp-brand:    #b8c3ff;   /* periwinkle */
  --bp-brand-d:  #0043eb;

  /* Semantic */
  --bp-mint:     #00e290;   /* AL sinyali / pozitif */
  --bp-peri:     #b8c3ff;   /* accent (=brand) */
  --bp-red:      #f85149;   /* SAT sinyali / negatif */
  --bp-gold:     #ffc850;   /* uyarı / nötr vurgu */
}
```

---

## 3. Light Mode Palette

Tasarım ilkesi: renk **semantiği** korunur (yeşil=AL, kırmızı=SAT, mavi=brand), contrast ratio WCAG AA ≥ 4.5:1.

```css
html[data-theme="light"] {
  /* Backgrounds */
  --bp-bg:       #f5f6fa;   /* çok hafif mavi-gri; saf beyaz gözü yorar */
  --bp-surface:  #ffffff;
  --bp-surface2: #eef0f6;
  --bp-surface3: #e6e8f0;

  /* Borders */
  --bp-border:   #d6d8e4;
  --bp-border2:  #b8bcd0;

  /* Text */
  --bp-text:     #0e0e18;   /* dark base, AA-compliant on #f5f6fa */
  --bp-text2:    #2e2e42;
  --bp-text3:    #64647a;   /* muted; ≥4.5:1 on #ffffff */

  /* Brand — periwinkle koyulaştırıldı, light bg'de readable */
  --bp-brand:    #3c4fba;
  --bp-brand-d:  #0035cc;

  /* Semantic — dark bg'deki parlak tonlar light'ta kontrast kaybeder, koyulaştır */
  --bp-mint:     #008f56;   /* AL / pozitif — koyu yeşil */
  --bp-peri:     #3c4fba;
  --bp-red:      #c42020;   /* SAT / negatif — koyu kırmızı */
  --bp-gold:     #b86c00;   /* uyarı — koyu amber */
}
```

### Kontrast Doğrulama (hedef WCAG AA)

| Token | Light değer | Bg | Ratio tahmini |
|---|---|---|---|
| `--bp-text` `#0e0e18` | `#f5f6fa` | ~18:1 ✅ |
| `--bp-text2` `#2e2e42` | `#f5f6fa` | ~10:1 ✅ |
| `--bp-text3` `#64647a` | `#ffffff` | ~5.3:1 ✅ |
| `--bp-brand` `#3c4fba` | `#f5f6fa` | ~6.2:1 ✅ |
| `--bp-mint` `#008f56` | `#ffffff` | ~5.1:1 ✅ |
| `--bp-red` `#c42020` | `#ffffff` | ~5.9:1 ✅ |

---

## 4. CSS Variable Map (Dark → Light)

| CSS Var | Dark | Light | Semantik |
|---|---|---|---|
| `--bp-bg` | `#0e0e12` | `#f5f6fa` | Sayfa arka planı |
| `--bp-surface` | `#141416` | `#ffffff` | Kart / panel yüzeyi |
| `--bp-surface2` | `#1c1b1f` | `#eef0f6` | Hover, input bg |
| `--bp-surface3` | `#201f21` | `#e6e8f0` | Nested panel |
| `--bp-border` | `#2a2a2c` | `#d6d8e4` | Çizgi / divider |
| `--bp-border2` | `#46464d` | `#b8bcd0` | Güçlü sınır |
| `--bp-text` | `#e5e1e4` | `#0e0e18` | Birincil metin |
| `--bp-text2` | `#c7c5cd` | `#2e2e42` | İkincil metin |
| `--bp-text3` | `#909097` | `#64647a` | Muted / caption |
| `--bp-brand` | `#b8c3ff` | `#3c4fba` | Brand accent |
| `--bp-brand-d` | `#0043eb` | `#0035cc` | Brand dark |
| `--bp-mint` | `#00e290` | `#008f56` | Pozitif / AL |
| `--bp-peri` | `#b8c3ff` | `#3c4fba` | Periwinkle accent |
| `--bp-red` | `#f85149` | `#c42020` | Negatif / SAT |
| `--bp-gold` | `#ffc850` | `#b86c00` | Uyarı / nötr |

---

## 5. Toggle Mekanizması

### HTML

```html
<!-- Header nav'a ekle (index.html, hisse.html, diğerleri) -->
<button id="theme-toggle" class="theme-toggle-btn" aria-label="Tema değiştir">
  <!-- JS ile doldurulur: ☀️ veya 🌙 ikonu -->
</button>
```

### CSS (toggle button style)

```css
.theme-toggle-btn {
  background: var(--bp-surface2);
  border: 1px solid var(--bp-border);
  border-radius: 6px;
  color: var(--bp-text2);
  width: 32px; height: 32px;
  cursor: pointer;
  display: flex; align-items: center; justify-content: center;
  font-size: 16px;
  transition: background 150ms, border-color 150ms;
}
.theme-toggle-btn:hover { background: var(--bp-surface3); }
```

### JavaScript (snippet — her template'e eklenecek)

```javascript
(function () {
  const STORAGE_KEY = 'bp-theme';
  const root = document.documentElement;

  function applyTheme(theme) {
    if (theme === 'light') {
      root.setAttribute('data-theme', 'light');
    } else {
      root.removeAttribute('data-theme');
    }
    const btn = document.getElementById('theme-toggle');
    if (btn) btn.textContent = theme === 'light' ? '🌙' : '☀️';
  }

  function getInitialTheme() {
    const stored = localStorage.getItem(STORAGE_KEY);
    if (stored) return stored;
    return window.matchMedia('(prefers-color-scheme: light)').matches ? 'light' : 'dark';
  }

  applyTheme(getInitialTheme());

  document.addEventListener('DOMContentLoaded', function () {
    const btn = document.getElementById('theme-toggle');
    if (!btn) return;
    btn.addEventListener('click', function () {
      const current = root.getAttribute('data-theme') === 'light' ? 'dark' : 'light';
      localStorage.setItem(STORAGE_KEY, current);
      applyTheme(current);
    });
  });
})();
```

---

## 6. Chart (lightweight-charts) Adaptasyonu

Lightweight-charts canvas'ı DOM CSS variable'lardan haberdar değil — her tema değişiminde `applyOptions` çağrılmalı.

```javascript
const CHART_DARK = {
  layout:     { background: { color: '#0e0e12' }, textColor: '#909097' },
  grid:       { vertLines: { color: '#2a2a2c' }, horzLines: { color: '#2a2a2c' } },
  crosshair:  { vertLine: { color: '#b8c3ff' }, horzLine: { color: '#b8c3ff' } },
};
const CHART_LIGHT = {
  layout:     { background: { color: '#f5f6fa' }, textColor: '#64647a' },
  grid:       { vertLines: { color: '#d6d8e4' }, horzLines: { color: '#d6d8e4' } },
  crosshair:  { vertLine: { color: '#3c4fba' }, horzLine: { color: '#3c4fba' } },
};

// applyTheme() içine ekle:
if (window._bpChart) {
  window._bpChart.applyOptions(theme === 'light' ? CHART_LIGHT : CHART_DARK);
}
```

Mum renkleri:
```javascript
candleSeries.applyOptions({
  upColor:          theme === 'light' ? '#008f56' : '#00e290',
  downColor:        theme === 'light' ? '#c42020' : '#f85149',
  borderUpColor:    theme === 'light' ? '#008f56' : '#00e290',
  borderDownColor:  theme === 'light' ? '#c42020' : '#f85149',
  wickUpColor:      theme === 'light' ? '#008f56' : '#00e290',
  wickDownColor:    theme === 'light' ? '#c42020' : '#f85149',
});
```

---

## 7. Dark Mode Kural Listesi (Implementasyon Checklist)

1. **CSS öncelik**: `html[data-theme="light"]` bloğu `:root` bloğundan **sonra** tanımlanmalı (override için)
2. **Etkilenen template'ler**: `index.html`, `hisse.html`, `backtest.html`, `sektor.html`, `virtual-portfolio.html` — tümüne toggle JS snippet ekle
3. **Inline hardcode renkler**: `#0e0e12` gibi sabit renk varsa `var(--bp-bg)` ile değiştir (grep: `grep -rn '#[0-9a-f]\{6\}' templates/`)
4. **Rgba referanslar**: `rgba(184,195,255,.1)` gibi sabit alpha'lar light'ta görünmeyebilir → `rgba(var(--bp-brand-rgb), .1)` pattern'ına geçiş (veya ayrı light var)
5. **Chart adaptasyonu**: Theme toggle'da `_bpChart.applyOptions()` çağrısı (bkz. §6)
6. **Sinyal rozetleri**: AL=`--bp-mint`, SAT=`--bp-red`, NÖTR=`--bp-text3` — token kullanıyorsa otomatik adapt
7. **Skeleton loader**: `--bp-surface2` → `--bp-surface3` shimmer animation — light'ta da çalışır
8. **Scrollbar**: `scrollbar-color: var(--bp-border2) var(--bp-bg)` ekle (Firefox/Chrome)
9. **localStorage**: `'bp-theme'` key, default=dark (sistemde light olsa bile site dark'ta açılır, ilk değişime kadar)
10. **SSR/FOUC önlemi**: Toggle JS'ini `<head>`'in sonuna inline ekle (DOMContentLoaded DEĞIL), böylece sayfa flash olmaz

---

## 8. Implementasyon Sırası (Sprint 4 W1)

| Adım | İş | Süre |
|---|---|---|
| 1 | CSS variable bloğu (`:root` + `html[data-theme="light"]`) tüm template'lere ekle | 30dk |
| 2 | Toggle button HTML + CSS + JS snippet | 30dk |
| 3 | Chart adapter (hisse.html `_bpChart`) | 20dk |
| 4 | Hardcode renk grep + fix | 20dk |
| 5 | QA: 3 hisse + 3 sayfa × light + dark, mobil + desktop | 30dk |

**Toplam**: ~2.5 saat implementasyon + 30dk QA = ~3 saat.
