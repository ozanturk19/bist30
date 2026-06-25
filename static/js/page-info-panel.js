/**
 * PageInfoPanel — SPEC-015 v3 standalone component
 * Collapsible info panel for page-level explanations with jargon-term links.
 * Integrated into templates only after Ozan vize+FFF approval (3 pages: tarama, gucu, sinyal).
 */

class PageInfoPanel {
  constructor(pageKey, title, bodyHTML) {
    this.pageKey = pageKey;
    this.title = title;
    this.bodyHTML = bodyHTML;
    this.storageKey = `bp_page_info_${pageKey}`;
    this.collapsed = false; // default: open
    this._el = null;
  }

  render() {
    const panel = document.createElement('div');
    panel.className = 'bp-info-panel';
    panel.dataset.pageKey = this.pageKey;

    const header = document.createElement('div');
    header.className = 'bp-info-panel__header';
    header.innerHTML = `
      <span class="bp-info-panel__title">${this.title}</span>
      <button class="bp-info-panel__toggle" aria-label="Aç/Kapat" aria-expanded="true">&#x25B2;</button>
    `;
    header.querySelector('.bp-info-panel__toggle').addEventListener('click', () => this.toggleCollapse());

    const body = document.createElement('div');
    body.className = 'bp-info-panel__body';
    body.innerHTML = this.bodyHTML;

    panel.appendChild(header);
    panel.appendChild(body);

    this._applyJargonLinks(body);
    this._injectStyles();
    this._el = panel;

    const savedCollapsed = this.loadFromLocalStorage();
    if (savedCollapsed) this._setCollapsed(true, false);

    return panel;
  }

  attachToHeader() {
    if (!this._el) this.render();
    const header = document.querySelector('.page-header, header, h1');
    if (header && header.parentNode) {
      header.parentNode.insertBefore(this._el, header.nextSibling);
    } else {
      document.body.insertBefore(this._el, document.body.firstChild);
    }
  }

  toggleCollapse() {
    this._setCollapsed(!this.collapsed, true);
  }

  _setCollapsed(collapsed, save) {
    this.collapsed = collapsed;
    if (!this._el) return;

    const body = this._el.querySelector('.bp-info-panel__body');
    const btn = this._el.querySelector('.bp-info-panel__toggle');

    if (collapsed) {
      body.style.maxHeight = '0';
      body.style.opacity = '0';
      btn.innerHTML = '&#x25BC;';
      btn.setAttribute('aria-expanded', 'false');
    } else {
      body.style.maxHeight = body.scrollHeight + 'px';
      body.style.opacity = '1';
      btn.innerHTML = '&#x25B2;';
      btn.setAttribute('aria-expanded', 'true');
    }

    if (save) this.saveToLocalStorage();
  }

  loadFromLocalStorage() {
    try {
      const val = localStorage.getItem(this.storageKey);
      return val === 'collapsed';
    } catch (_) {
      return false;
    }
  }

  saveToLocalStorage() {
    try {
      localStorage.setItem(this.storageKey, this.collapsed ? 'collapsed' : 'open');
    } catch (_) {}
  }

  _applyJargonLinks(container) {
    // Jargon-term links: <a class="bp-jargon-link" data-term="ema"> → /metodoloji#ema
    container.querySelectorAll('a[data-term]').forEach(link => {
      const term = link.dataset.term;
      if (term) {
        link.href = `/metodoloji#${term}`;
        link.target = '_blank';
        link.rel = 'noopener';
        link.classList.add('bp-jargon-link');
      }
    });
  }

  _injectStyles() {
    if (document.getElementById('bp-info-panel-styles')) return;
    const style = document.createElement('style');
    style.id = 'bp-info-panel-styles';
    style.textContent = `
      .bp-info-panel {
        background: var(--color-surface, #1e2530);
        border: 1px solid var(--color-border, #2d3748);
        border-radius: 6px;
        margin: 12px 0;
        overflow: hidden;
      }
      .bp-info-panel__header {
        display: flex;
        align-items: center;
        justify-content: space-between;
        padding: 10px 14px;
        cursor: pointer;
        user-select: none;
      }
      .bp-info-panel__title {
        font-size: 0.875rem;
        font-weight: 600;
        color: var(--color-text-secondary, #a0aec0);
        text-transform: uppercase;
        letter-spacing: 0.05em;
      }
      .bp-info-panel__toggle {
        background: none;
        border: none;
        color: var(--color-text-muted, #718096);
        cursor: pointer;
        font-size: 0.75rem;
        padding: 2px 4px;
        line-height: 1;
      }
      .bp-info-panel__body {
        padding: 0 14px;
        max-height: 600px;
        opacity: 1;
        overflow: hidden;
        transition: max-height 0.2s ease, opacity 0.2s ease, padding 0.2s ease;
      }
      .bp-info-panel__body > *:first-child { margin-top: 0; padding-top: 10px; }
      .bp-info-panel__body > *:last-child { margin-bottom: 0; padding-bottom: 10px; }
      .bp-jargon-link {
        color: var(--color-accent, #f6c90e);
        text-decoration: none;
        border-bottom: 1px dashed currentColor;
      }
      .bp-jargon-link:hover { text-decoration: underline; }
    `;
    document.head.appendChild(style);
  }
}

if (typeof module !== 'undefined') module.exports = { PageInfoPanel };
