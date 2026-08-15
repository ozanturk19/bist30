import re, sys

path = "templates/index.html"
with open(path, encoding="utf-8") as f:
    src = f.read()

orig = src

replacements = [
    (
        '<div class="gnm-tabs" id="gnmTabs">',
        '<div class="gnm-tabs" id="gnmTabs" role="tablist" aria-label="Gündem sekmeleri">',
    ),
    (
        '<button class="gnm-tab-btn active" id="tabBtnMakro" onclick="switchGnmTab(\'makro\')"><span aria-hidden="true">🌍</span> Makro</button>',
        '<button class="gnm-tab-btn active" id="tabBtnMakro" role="tab" aria-selected="true" aria-controls="gnmPanelMakro" onclick="switchGnmTab(\'makro\')"><span aria-hidden="true">🌍</span> Makro</button>',
    ),
    (
        '<button class="gnm-tab-btn" id="tabBtnHisse" onclick="switchGnmTab(\'hisse\')"><span aria-hidden="true">📈</span> Hisse</button>',
        '<button class="gnm-tab-btn" id="tabBtnHisse" role="tab" aria-selected="false" aria-controls="gnmPanelHisse" onclick="switchGnmTab(\'hisse\')"><span aria-hidden="true">📈</span> Hisse</button>',
    ),
    (
        '<div id="gnmPanelMakro">\n      <div id="macroNewsList" class="macro-news-list">',
        '<div id="gnmPanelMakro" role="tabpanel" aria-labelledby="tabBtnMakro" tabindex="0">\n      <div id="macroNewsList" class="macro-news-list" role="list" aria-label="Makro haberler">',
    ),
    (
        '<div id="gnmPanelHisse" style="display:none">',
        '<div id="gnmPanelHisse" style="display:none" role="tabpanel" aria-labelledby="tabBtnHisse" tabindex="0">',
    ),
    (
        "return `<a href=\"${safeUrl}\" target=\"_blank\" rel=\"noopener\" class=\"macro-news-item\">",
        "return `<a href=\"${safeUrl}\" target=\"_blank\" rel=\"noopener\" class=\"macro-news-item\" role=\"listitem\">",
    ),
    (
        "  if (tab === 'makro') {\n    btnMakro && btnMakro.classList.add('active');\n    btnHisse && btnHisse.classList.remove('active');\n    panelMakro.style.display = 'block';\n    panelHisse.style.display = 'none';\n    if (!_macroLoaded) loadMacroNews();\n  } else {\n    btnHisse && btnHisse.classList.add('active');\n    btnMakro && btnMakro.classList.remove('active');\n    panelHisse.style.display = 'block';\n    panelMakro.style.display = 'none';\n    if (!_hisseLoaded) loadGundem(false);\n  }",
        "  if (tab === 'makro') {\n    btnMakro && btnMakro.classList.add('active');\n    btnHisse && btnHisse.classList.remove('active');\n    btnMakro && btnMakro.setAttribute('aria-selected', 'true');\n    btnHisse && btnHisse.setAttribute('aria-selected', 'false');\n    panelMakro.style.display = 'block';\n    panelHisse.style.display = 'none';\n    if (!_macroLoaded) loadMacroNews();\n  } else {\n    btnHisse && btnHisse.classList.add('active');\n    btnMakro && btnMakro.classList.remove('active');\n    btnHisse && btnHisse.setAttribute('aria-selected', 'true');\n    btnMakro && btnMakro.setAttribute('aria-selected', 'false');\n    panelHisse.style.display = 'block';\n    panelMakro.style.display = 'none';\n    if (!_hisseLoaded) loadGundem(false);\n  }",
    ),
]

report = []
for old, new in replacements:
    n = src.count(old)
    if n != 1:
        report.append(f"FAIL (found {n}x, expected 1x): {old[:70]!r}")
        continue
    src = src.replace(old, new, 1)
    report.append(f"OK: {old[:70]!r}")

if src == orig:
    print("NO CHANGES APPLIED")
    sys.exit(1)

any_fail = any(r.startswith("FAIL") for r in report)
if any_fail:
    print("\n".join(report))
    print("ABORTED — not writing file due to failures above")
    sys.exit(1)

with open(path, "w", encoding="utf-8") as f:
    f.write(src)

print("\n".join(report))
print(f"len before={len(orig)} after={len(src)} delta={len(src)-len(orig)}")
