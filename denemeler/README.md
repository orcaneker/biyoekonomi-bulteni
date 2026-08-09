# denemeler/

Model ve prompt denemelerinin **kalıcı kaydı**. Amaç: bir kararı ikinci kez
tartışmak gerektiğinde ölçümleri yeniden üretmek zorunda kalmamak.

Geçici çalışma dosyaları buraya değil, `.gitignore`'daki `kiyas/` klasörüne
yazılır. Buraya yalnızca **sonuçlanmış** bir denemenin kaydı taşınır.

| klasör | ne |
|---|---|
| [`model-kiyasi-2026-08/`](model-kiyasi-2026-08/README.md) | Sonnet 5 ↔ GPT-5.6 Terra yazım modeli kıyası. Karar: Sonnet 5'te kalındı. |
| `araclar/` | ölçüm betikleri — repo kökünden çalıştırılır |

## araclar/

| betik | ne ölçer |
|---|---|
| `dil_denetimi.py` | Türkçeleştirme ihlalleri (İngilizce ay adı, `$1.52`, `700,000`, markdown…) |
| `uslup_denetimi.py` | akıcılık: cümle uzunluğu çeşitliliği, ardışık "-yor", dolgu cümlesi, başlık uzunluğu |
| `rakam_denetimi.py` | metindeki her sayı kaynakta gerçekten var mı |
| `v1v2_rakam.py` | iki sürüm arasında sayı kaybı oldu mu |
| `supheli_testi.py` | `gorsel_supheli()` — logo/stok görseli ayırt ediyor mu |
| `yazim_denetimi_testi.py` | `json_ayikla()` kontrol-karakter onarımı + `yazim_eksik()` tamlık denetimi |
| `birlestirme_testi.py` | mükerrer olay birleştirme, gerçek Sayı 2 verisiyle |
| `onizleme.py` | inceleme sayfasını Neon'suz ayağa kaldırır (görsel/kart düzeni denemek için) |
| `docx_uret.js` | iki taslaktan yan yana karşılaştırma dokümanı üretir |

`yollar.py` ortak yol çözümüdür; betikler repo kökünü ve kayıtlı çıktıları
oradan alır.
