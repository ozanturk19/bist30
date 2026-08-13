#!/usr/bin/env python3
"""DEV2-079: 17px/19px off-scale font-size gap kapatma.
Explicit, per-site edits (heterojen roller, mekanik regex degil)."""
import sys

ROOT = "/root/bist30-worktrees/faz8-typography-17-19"

EDITS = [
    # (file, old, new, expected_count)
    ("static/css/tokens.css",
     "  --bp-text-lg:   16px;\n  --bp-text-xl:   18px;",
     "  --bp-text-lg:   16px;\n  --bp-text-17:   17px;  /* DEV2-079: lg(16)/xl(18) arasi, ankor bulunamayan 4 kullanim (mc-ticker/mc-price/sec-col-name/header-name) */\n  --bp-text-xl:   18px;",
     1),
    ("static/css/tokens.css",
     """     app.py'deki e-posta üretim fonksiyonları (_build_welcome_email vb.)
     KASITLI HARİÇ: e-posta istemcileri CSS custom property'yi güvenilir
     render etmiyor (Outlook/bazı mobil mail app), o katman ham px kalır.

     Taban 13px""",
     """     app.py'deki e-posta üretim fonksiyonları (_build_welcome_email vb.)
     KASITLI HARİÇ: e-posta istemcileri CSS custom property'yi güvenilir
     render etmiyor (Outlook/bazı mobil mail app), o katman ham px kalır.

     17px KAPANDI (DEV2-079, 14.08.2026): orijinal ölçümdeki 10 kullanım
     heterojendi - mevcut kalıba oturanlar (page-title, close-ikon, h2,
     premium-modal-title) canlı grep ile diğer örneklerle karşılaştırılıp
     en yakın basamağa (lg 16 / xl 18 / 2xl 20) yuvarlandı. Geriye kalan
     4 kullanım (mc-ticker/mc-price/sec-col-name/header-name) hiçbir
     mevcut basamağa net oturmuyordu (kanıtsız yuvarlama riskli) - bu
     4'ü sıfır görsel değişiklikle --bp-text-17'ye tokenize edildi.
     19px KAPANDI: premium-modal-title (index.html + duplike
     _premium_modal.html) 2xl(20)'ye, mobil 480px override'i 17->xl(18)'e
     yuvarlandı.

     Taban 13px""",
     1),

    # blog_article.html: close "x" button -> matches .alert-modal-close/.ap-close convention (xl)
    ("templates/blog_article.html",
     'color:#484f58;font-size:17px;cursor:pointer;line-height:1;padding:2px 4px;"',
     'color:#484f58;font-size:var(--bp-text-xl);cursor:pointer;line-height:1;padding:2px 4px;"',
     1),

    # gizlilik.html: h2 content heading -> matches faq-section-title convention (lg)
    ("templates/gizlilik.html",
     "  h2 { font-size: 17px; font-weight: 700; color: #f0f6fc; margin: 28px 0 10px; padding-bottom: 6px; border-bottom: 1px solid #21262d; }",
     "  h2 { font-size: var(--bp-text-lg); font-weight: 700; color: #f0f6fc; margin: 28px 0 10px; padding-bottom: 6px; border-bottom: 1px solid #21262d; }",
     1),

    # ozet.html: .page-title -> matches gucu_yuksek/kategori/tarama xl convention
    ("templates/ozet.html",
     "  .page-title { font-size: 17px; font-weight: 700; color: var(--bp-text); font-family: 'Space Grotesk', system-ui, sans-serif; }",
     "  .page-title { font-size: var(--bp-text-xl); font-weight: 700; color: var(--bp-text); font-family: 'Space Grotesk', system-ui, sans-serif; }",
     1),

    # sektor_harita.html: .page-title -> same
    ("templates/sektor_harita.html",
     "  .page-title { font-size:17px; font-weight:700; color:var(--bp-text); font-family:'Space Grotesk',system-ui,sans-serif; }",
     "  .page-title { font-size:var(--bp-text-xl); font-weight:700; color:var(--bp-text); font-family:'Space Grotesk',system-ui,sans-serif; }",
     1),

    # sektor_karsilastir.html: .sec-col-name -> no clean anchor, tokenize as-is (17)
    ("templates/sektor_karsilastir.html",
     "  .sec-col-name { font-family:'Space Grotesk',system-ui,sans-serif; font-size:17px; font-weight:700; margin-bottom:6px; }",
     "  .sec-col-name { font-family:'Space Grotesk',system-ui,sans-serif; font-size:var(--bp-text-17); font-weight:700; margin-bottom:6px; }",
     1),

    # varlik.html: .header-name -> no clean anchor, tokenize as-is (17)
    ("templates/varlik.html",
     "  .header-name { font-size:17px; font-weight:700; color:#f0f6fc; white-space:nowrap; overflow:hidden; text-overflow:ellipsis; }",
     "  .header-name { font-size:var(--bp-text-17); font-weight:700; color:#f0f6fc; white-space:nowrap; overflow:hidden; text-overflow:ellipsis; }",
     1),

    # index.html: .mc-ticker / .mc-price -> no clean anchor, tokenize as-is (17), paired
    ("templates/index.html",
     "    font-size:17px; font-weight:800; color: var(--bp-text); line-height:1.2;\n    font-family: 'Space Grotesk', system-ui, sans-serif; letter-spacing: -0.2px;",
     "    font-size:var(--bp-text-17); font-weight:800; color: var(--bp-text); line-height:1.2;\n    font-family: 'Space Grotesk', system-ui, sans-serif; letter-spacing: -0.2px;",
     1),
    ("templates/index.html",
     "  .mc-price  { font-size:17px; font-weight:700; font-variant-numeric:tabular-nums; color: var(--bp-text); line-height:1.3; font-family: 'Space Grotesk', monospace, sans-serif; }",
     "  .mc-price  { font-size:var(--bp-text-17); font-weight:700; font-variant-numeric:tabular-nums; color: var(--bp-text); line-height:1.3; font-family: 'Space Grotesk', monospace, sans-serif; }",
     1),

    # index.html: premium-modal-title base 19->2xl, mobile override 17->xl
    ("templates/index.html",
     "  .premium-modal-title {\n    color: var(--bp-text);\n    font-size: 19px;\n    font-weight: 700;\n    margin: 0 0 8px;\n  }",
     "  .premium-modal-title {\n    color: var(--bp-text);\n    font-size: var(--bp-text-2xl);\n    font-weight: 700;\n    margin: 0 0 8px;\n  }",
     1),
    ("templates/index.html",
     "    .premium-modal-title { font-size: 17px; }",
     "    .premium-modal-title { font-size: var(--bp-text-xl); }",
     1),

    # _premium_modal.html: duplicate block, must match index.html exactly (include-chain lesson, DEV2-078)
    ("templates/_premium_modal.html",
     "  .premium-modal-title {\n    color: var(--bp-text);\n    font-size: 19px; font-weight: 700; margin: 0 0 8px;\n  }",
     "  .premium-modal-title {\n    color: var(--bp-text);\n    font-size: var(--bp-text-2xl); font-weight: 700; margin: 0 0 8px;\n  }",
     1),
    ("templates/_premium_modal.html",
     "    .premium-modal-title { font-size: 17px; }",
     "    .premium-modal-title { font-size: var(--bp-text-xl); }",
     1),
]

def main():
    fails = []
    for relpath, old, new, expected in EDITS:
        path = f"{ROOT}/{relpath}"
        with open(path, "r", encoding="utf-8") as f:
            content = f.read()
        count = content.count(old)
        if count != expected:
            fails.append(f"{relpath}: expected {expected}, found {count} for old-string starting {old[:60]!r}")
            continue
        content = content.replace(old, new)
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
        print(f"OK  {relpath}  ({count}x)")
    if fails:
        print("FAILURES:")
        for f_ in fails:
            print(" -", f_)
        sys.exit(1)
    print("ALL EDITS APPLIED")

if __name__ == "__main__":
    main()
