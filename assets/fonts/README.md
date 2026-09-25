# Sunucu tarafı yazı tipleri (servis edilmez)

`heatmap_image.py` (D-54, ısı haritası paylaşım görseli) Pillow ile bu iki dosyayı kullanır.
Site `static/fonts/*.woff2` ile aynı yazı tipleri, aynı alt küme (Türkçe harfler, `−`, `·`, `₺` dahil);
yalnız kapsayıcı WOFF2 → TrueType çevrildi (glif ve metrik değişmedi). Bu klasör Flask `static/`
dışında olduğu için web'den erişilemez.

| Dosya | Kaynak | Not |
|---|---|---|
| `bricolage-800.ttf` | `static/fonts/bricolage-800.woff2` | Bricolage Grotesque ExtraBold (800), sabit ağırlık |
| `space-grotesk.ttf` | `static/fonts/space-grotesk.woff2` | Space Grotesk, değişken ağırlık 400–700 (`wght`) |

Lisans: ikisi de SIL Open Font License 1.1 (https://openfontlicense.org).
Copyright 2022 The Bricolage Grotesque Project Authors (https://github.com/ateliertriay/bricolage).
Copyright 2020 The Space Grotesk Project Authors (https://github.com/floriankarsten/space-grotesk).

Yeniden üretim (site woff2'si değişirse; fontTools + brotli gerekir):

```
python3 -c "from fontTools.ttLib import TTFont
for n in ('bricolage-800', 'space-grotesk'):
    f = TTFont('static/fonts/%s.woff2' % n); f.flavor = None; f.save('assets/fonts/%s.ttf' % n)"
```
