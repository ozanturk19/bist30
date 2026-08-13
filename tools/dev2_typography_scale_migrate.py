#!/usr/bin/env python3
"""FAZ8 tipografi olcegi genisletme - yari-piksel drift kapatma + 15/22px yeni basamak.

NEDEN (DEV2-078, 13.08.2026):
FAZ8-typography mekanik migrasyonu (2a20aeb) 965 font-size kullanimini var(--bp-text-*)'e
bagladi ama YALNIZCA 9-basamakli olcekle (10/11/12/13/14/16/18/20/24) BIREBIR eslesenleri.
Geriye 104 "off-scale" ham deger kaldi (tokens.css:195-198 DRIFT KAYDI yorumu bunu kismen
onceden belgelemisti: yari-piksel kopyala-yapistir artiklari, "en yakin tam basamaga
cekilecekler" notuyla).

BU TUR KAPSAMI, YALNIZCA templates/*.html (44/104, en net sinirlanan alt-kume):
  A) Yari-piksel artiklari -> EN YAKIN TAM BASAMAK (round-half-up, tasarim karari degil):
     12.5px(11)-> 13 (--bp-text-base)
     13.5px(1) -> 14 (--bp-text-md)
     14.5px(1) -> 15 (--bp-text-15, asagida yeni token)
  B) Sistemik tekrar eden TAM basamaklar, mevcut olcekte bosluk dolduran, YENI token:
     15px(29)  -> --bp-text-15  (md=14 ile lg=16 arasi, toplam 31 kullanimla scale'deki
                                   en yogun 3. deger - base(13)/md(14)'ten sonra)
     22px(19)  -> --bp-text-22  (2xl=20 ile 3xl=24 arasi)

  NOT: 10.5px(1)/11.5px(2) TEMPLATES'TE HIC YOK - yalniz app.py'de (email, asagida
  D bendinde harici tutulan ayni fonksiyon govdesinde). Bu yuzden bu turda kapsama
  alinmadi (sifir kullanim = migre edilecek bir sey yok).

KAPSAM DISI (bu turda dokunulmadi, sonraki tur icin isaretli):
  - 17px(10), 19px(2): mevcut basamaklar arasinda ama tekrar sayisi/baglami netlesmemis
  - 26/28/32/34/36/38/40/42px (~29 kullanim): buyuk "display" boyutlari, per-baglam
    yargı gerektiriyor (hero sayi vs baslik vs istatistik karti) - tek basamaga
    snap etmek payda kaybi riski tasiyor
  - 8/9px (4 kullanim, tokens.css:377 "kismi" rozeti dahil): 2xs(10)'un altinda,
    kasitli mikro-dekoratif, dokunulmadi
  - app.py:2441/2592 (22px/15px, email HTML - _build_welcome_email/_build_signal_email):
    DEV1 alani (push/email) + teknik kisit (CSS custom property e-posta istemcilerinde
    guvenilir degil, Outlook/bazi mobil mail app'ler var() render etmiyor) - iki
    gerekceyle de HARIC, dokunulmadi.

KULLANIM: python3 tools/dev2_typography_scale_migrate.py [--dry-run]
"""
import re
import sys
import pathlib

ROOT = pathlib.Path(__file__).resolve().parent.parent
TOKENS_CSS = ROOT / "static/css/tokens.css"
TEMPLATES = ROOT / "templates"

# (regex-value, token-var, beklenen-sayim) - yalniz templates/*.html kapsaminda
REPLACEMENTS = [
    (r"12\.5px", "var(--bp-text-base)", 11),
    (r"13\.5px", "var(--bp-text-md)", 1),
    (r"14\.5px", "var(--bp-text-15)", 1),
    (r"(?<!\d)15px", "var(--bp-text-15)", 29),
    (r"(?<!\d)22px", "var(--bp-text-22)", 19),
]

OLD_VER = "20260810F"
NEW_VER = "20260810G"


def migrate_tokens_css(dry_run):
    src = TOKENS_CSS.read_text(encoding="utf-8")
    if "--bp-text-15" in src or "--bp-text-22" in src:
        print("HATA: tokens.css zaten --bp-text-15/22 iceriyor, tekrar calistirilmis olabilir.")
        sys.exit(1)

    old_block = (
        "  --bp-text-2xs:  10px;\n"
        "  --bp-text-xs:   11px;\n"
        "  --bp-text-sm:   12px;\n"
        "  --bp-text-base: 13px;\n"
        "  --bp-text-md:   14px;\n"
        "  --bp-text-lg:   16px;\n"
        "  --bp-text-xl:   18px;\n"
        "  --bp-text-2xl:  20px;\n"
        "  --bp-text-3xl:  24px;\n"
    )
    new_block = (
        "  --bp-text-2xs:  10px;\n"
        "  --bp-text-xs:   11px;\n"
        "  --bp-text-sm:   12px;\n"
        "  --bp-text-base: 13px;\n"
        "  --bp-text-md:   14px;\n"
        "  --bp-text-15:   15px;  /* DEV2-078: md(14)/lg(16) arasi bosluk - 30 kullanim */\n"
        "  --bp-text-lg:   16px;\n"
        "  --bp-text-xl:   18px;\n"
        "  --bp-text-2xl:  20px;\n"
        "  --bp-text-22:   22px;  /* DEV2-078: 2xl(20)/3xl(24) arasi bosluk - 19 kullanim */\n"
        "  --bp-text-3xl:  24px;\n"
    )
    if old_block not in src:
        print("HATA: beklenen font-size token blogu tokens.css'te birebir bulunamadi.")
        sys.exit(1)
    src = src.replace(old_block, new_block, 1)

    old_comment = (
        "     DRIFT KAYDI: yarım-piksel değerler canlıda mevcut —\n"
        "       12.5px:10  11.5px:8  10.5px:8  14.5px:1  13.5px:1  (28 kullanım)\n"
        "     Bunlar tasarım kararı değil kopyala-yapıştır artığı; token\n"
        "     yok, T1.5'te en yakın tam basamağa çekilecekler.\n"
    )
    new_comment = (
        "     DRIFT KAYDI KAPANDI - templates/ (DEV2-078, 13.08.2026): yarım-piksel\n"
        "     değerler en yakın tam basamağa çekildi (12.5->base 13.5->md 14.5->15,\n"
        "     round-half-up). Ayrıca 15px/22px sistemik boşluk-doldurucu değerler\n"
        "     için 2 yeni basamak eklendi (bkz. yukarıdaki --bp-text-15/22).\n"
        "     app.py'deki e-posta üretim fonksiyonları (_build_welcome_email vb.)\n"
        "     KASITLI HARİÇ: e-posta istemcileri CSS custom property'yi güvenilir\n"
        "     render etmiyor (Outlook/bazı mobil mail app), o katman ham px kalır.\n"
    )
    if old_comment not in src:
        print("UYARI: eski DRIFT KAYDI yorumu birebir bulunamadi (kod formatlanmis olabilir), yorum guncellenmedi.")
    else:
        src = src.replace(old_comment, new_comment, 1)

    if not dry_run:
        TOKENS_CSS.write_text(src, encoding="utf-8")
    print("tokens.css: 2 yeni token eklendi (--bp-text-15, --bp-text-22)" + (" [dry-run]" if dry_run else ""))


def migrate_templates(dry_run):
    total_replaced = 0
    per_pattern_count = {p: 0 for p, _, _ in REPLACEMENTS}
    files_touched = 0

    for f in sorted(TEMPLATES.glob("*.html")):
        src = f.read_text(encoding="utf-8")
        new_src = src
        file_replaced = 0
        for pattern, token, _expected in REPLACEMENTS:
            regex = re.compile(r"(font-size:\s*)" + pattern + r"(?!px)")
            def _sub(m, token=token):
                return m.group(1) + token
            new_src, n = regex.subn(_sub, new_src)
            per_pattern_count[pattern] += n
            file_replaced += n
        if file_replaced:
            files_touched += 1
            total_replaced += file_replaced
            if not dry_run:
                f.write_text(new_src, encoding="utf-8")
            # cache-bust: bu dosya tokens.css'e link veriyorsa versiyonu ilerlet
            if "tokens.css?v=" + OLD_VER in new_src:
                bumped = new_src.replace("tokens.css?v=" + OLD_VER, "tokens.css?v=" + NEW_VER)
                if not dry_run:
                    f.write_text(bumped, encoding="utf-8")
                new_src = bumped

    print(f"templates: {files_touched} dosya, {total_replaced} degisim" + (" [dry-run]" if dry_run else ""))
    ok = True
    for pattern, token, expected in REPLACEMENTS:
        got = per_pattern_count[pattern]
        status = "OK" if got == expected else "MISMATCH"
        if got != expected:
            ok = False
        print(f"  {pattern:12s} -> {token:24s} beklenen={expected:3d} bulunan={got:3d}  {status}")
    return ok


def main():
    dry_run = "--dry-run" in sys.argv
    migrate_tokens_css(dry_run)
    ok = migrate_templates(dry_run)
    if not ok:
        print("\nEN AZ BIR PATTERN SAYISI BEKLENENDEN FARKLI - manuel incele.")
        sys.exit(1)
    print("\nTumu beklenen sayimla eslesti." + (" [DRY-RUN - dosya yazilmadi]" if dry_run else " Dosyalar yazildi."))


if __name__ == "__main__":
    main()
