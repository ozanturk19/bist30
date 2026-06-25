# Daemon Corruption Fixture Corpus v1

**Spec ref:** Phase 3 #2 Paket 5 — daemon corruption guard genişletme  
**Oluşturulma:** 2026-06-25  
**Toplam fixture:** 20 (4 kategori × 5)

## Kullanım

```bash
# Paket 5 implementasyonu sırasında:
pytest tests/test_guards.py --fixture tools/test-fixtures/corruption-corpus/

# Sadece bir kategori:
pytest tests/test_guards.py -k fundamentals

# manifest.json — tüm fixture metadata:
cat tools/test-fixtures/corruption-corpus/manifest.json | python3 -m json.tool
```

## Kategoriler

### 1. `fundamentals-corrupt/` — `_is_valid_fundamentals()`

| Fixture | Guard Ref | Beklenen Sonuç | Açıklama |
|---------|-----------|----------------|----------|
| missing_pe_ratio.json | Paket 5 #F1 | `InvalidData` | PE_ratio field eksik |
| null_eps.json | Paket 5 #F2 | `InvalidData` | EPS null (sıfıra bölme riski) |
| negative_market_cap.json | Paket 5 #F3 | `InvalidData` | market_cap < 0 |
| string_price_type.json | Paket 5 #F4 | `InvalidData` | last_price string "43,25" |
| empty_object.json | Paket 5 #F5 | `InvalidData` | Tüm field'lar eksik |

### 2. `chart-corrupt/` — `_is_valid_chart()`

| Fixture | Guard Ref | Beklenen Sonuç | Açıklama |
|---------|-----------|----------------|----------|
| low_ohlc_count.json | Paket 5 #C1 | `InvalidData` | ohlc_count=42 (min 100 gerekli) |
| empty_volume_array.json | Paket 5 #C2 | `InvalidData` | volume array boş / null |
| mismatched_timestamps.json | Paket 5 #C3 | `InvalidData` | Timestamp sırası descending |
| negative_ohlc_value.json | Paket 5 #C4 | `InvalidData` | OHLC içinde negatif fiyat |

### 3. `macro-corrupt/` — `_is_valid_macro()`

| Fixture | Guard Ref | Beklenen Sonuç | Açıklama |
|---------|-----------|----------------|----------|
| xu030_null.json | Paket 5 #M1 | `InvalidData` | XU030=null |
| usdtry_string_type.json | Paket 5 #M2 | `InvalidData` | USDTRY="38,42" (string) |
| missing_last_price.json | Paket 5 #M3 | `InvalidData` | XU030 nested ama last_price eksik |
| stale_timestamp.json | Paket 5 #M4 | `StaleData` | 72 saat eski timestamp |
| empty_macro.json | Paket 5 #M5 | `InvalidData` | Boş dict |

### 4. `disk-cache-corrupt/` — `_is_valid_disk_cache()`

| Fixture | Guard Ref | Beklenen Sonuç | Açıklama |
|---------|-----------|----------------|----------|
| missing_data_field.json | Paket 5 #D1 | `InvalidData` | 'data' key yok |
| json_parse_error.txt | Paket 5 #D2 | `JSONDecodeError` | Truncated JSON (partial write) |
| partial_write.json | Paket 5 #D3 | `InvalidData` | data var ama chart nested eksik |
| wrong_version.json | Paket 5 #D4 | `SchemaMismatch` | version="1.0" (beklenen "3.x") |
| empty_data_value.json | Paket 5 #D5 | `InvalidData` | "data": null |

## Paket 5 Implementasyon Notu

Paket 5 implementasyonu sırasında her `_is_valid_X()` fonksiyonu şu imzayı almalı:

```python
def _is_valid_fundamentals(data: dict) -> tuple[bool, str]:
    """Returns (is_valid, reason)."""
    ...

def _is_valid_chart(data: dict) -> tuple[bool, str]:
    ...

def _is_valid_macro(data: dict) -> tuple[bool, str]:
    ...

def _is_valid_disk_cache(raw: str | dict) -> tuple[bool, str]:
    # raw str ise json.loads() dene, JSONDecodeError yakala
    ...
```

Her fixture bu fonksiyonlara inject edilerek `is_valid == False` ve uygun `reason` dönmesi doğrulanır.
