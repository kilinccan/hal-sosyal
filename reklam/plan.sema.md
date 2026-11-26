# reklam/plan.json şeması

`{"reklamlar": [ÖĞE, ...]}`. Kimlik `ad`'dır (benzersiz, sonradan değişmez).

| alan | zorunlu | değer |
|---|---|---|
| `ad` | evet | `^[a-z0-9-]{3,40}$` |
| `medya_id` | biri zorunlu | yayınlanmış IG gönderi id'si |
| `kuyruk` | biri zorunlu | `YYYY-MM-DD-HHMM` (kuyruk dosyası adı; gönderi o saatten sonraki 3 saatte yayınlanmış olmalı) |
| `hedef` | evet | `profil_ziyareti`, `etkilesim`, `erisim` veya `app_store` |
| `link` | yalnız `app_store`'da, zorunlu | `https://kilinccan.github.io/hal/` (+ basit sorgu); sonradan değişmez |
| `gunluk_tl` | evet | sayı, `MIN_GUNLUK_TL` <= x <= 100 |
| `baslangic`, `bitis` | evet | `YYYY-MM-DD` (TR günü, ikisi dahil); en çok 7 gün |
| `durum` | evet | `aktif` veya `durdur` |
| `yas_min`, `yas_max` | hayır | 18-65 |

Ülke yalnız TR (alan yok). Sonradan değişebilenler: `gunluk_tl`, `bitis`, `durum`. `medya_id`/`kuyruk`/`hedef`/`baslangic` değiştirmek yerine yeni `ad` aç.

Örnek öğe:

```json
{"ad": "tanitim-1", "medya_id": "17900000000000000", "hedef": "profil_ziyareti", "gunluk_tl": 50,
 "baslangic": "2026-11-25", "bitis": "2026-11-28", "durum": "aktif", "yas_min": 18, "yas_max": 45}
```
