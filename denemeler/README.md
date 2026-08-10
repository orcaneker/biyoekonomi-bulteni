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
| `olu_baglanti_testi.py` | `_olu_baglanti()` — ölü bağlantıyı bot engelinden ayırt ediyor mu (çevrimdışı) |
| `yazim_denetimi_testi.py` | `json_ayikla()` kontrol-karakter onarımı + `yazim_eksik()` tamlık denetimi |
| `birlestirme_testi.py` | mükerrer olay birleştirme, gerçek Sayı 2 verisiyle |
| `onizleme.py` | inceleme sayfasını Neon'suz ayağa kaldırır (görsel/kart düzeni denemek için) |
| `docx_uret.js` | iki taslaktan yan yana karşılaştırma dokümanı üretir |

`yollar.py` ortak yol çözümüdür; betikler repo kökünü ve kayıtlı çıktıları
oradan alır.

## Çevrimdışı testler

Aşağıdaki betikler **ağ, API anahtarı ve ücret gerektirmez** — ağ
çağrıları taklit edilir. İddia üretir ve çıkış kodu dönerler, dolayısıyla
her kod değişikliğinden sonra saniyeler içinde koşulabilirler.

Hepsini birden koşturmak için:

    cd denemeler/araclar
    python birim_testleri.py

| betik | neyi doğrular | iddia |
|---|---|---|
| `birlestirme_birim_testi.py` | üç katmanlı mükerrer birleştirmenin karar mantığı; sayı parmak izi, ortak sinyal emniyeti, grup boyutu sınırı | 38 |
| `govde_metni_birim_testi.py` | `_govde_metni()` çıkarımı; script/menü/footer sızdırmıyor, zengin metni bozmuyor | 16 |
| `tarih_okuma_birim_testi.py` | `_tarih_ayikla()` katman sırası; görünür tarih okunuyor, "ilgili haberler" tarihine atlanmıyor | 11 |
| `gorsel_denetim_birim_testi.py` | `gorsel_erisilebilir()`; hotlink engelli görsel elenip sıradaki adaya düşülüyor | 10 |
| `kaynak_sabitleme_birim_testi.py` | `kaynaklari_sabitle()`; yanlış URL düzeltiliyor, kaynaksız haber yayına girmiyor | 6 |
| `tarih_raporu_birim_testi.py` | tarihi doğrulanamayan haber sayacı; elenmiyor ama raporda görünüyor | 6 |
| `olu_baglanti_testi.py` | `_olu_baglanti()`; 404/410 ölü sayılıyor, 403/503 bot engeli ölü SAYILMIYOR | 9 |
| `supheli_testi.py` | `gorsel_supheli()`; logo ve stok görseli geri plana atılıyor | 8 |
| `yazim_denetimi_testi.py` | `json_ayikla` kontrol-karakter onarımı + `yazim_eksik` tamlık denetimi | 10 |

⚠ Adlandırmaya güvenilmez: `olu_baglanti_testi.py`, `supheli_testi.py` ve
`yazim_denetimi_testi.py` "birim" eki taşımadıkları hâlde ÇEVRİMDIŞIDIR —
sahte yanıt nesneleri kullanır, iddia üretir, çıkış kodu döner. Bir dönem
yalnızca ada bakıldığı için bunlar hiç koşulmuyordu; artık koşuluyorlar.

CANLI test, `birim_testleri.py` içindeki açık listeyle dışarıda tutulur.
Şu an tek canlı betik `birlestirme_testi.py` (gerçek sayı verisiyle gerçek
LLM çağrısı — ücretli, sonucunu insan okur). Yeni test eklerken: gerçek
ağ/LLM çağrısı yapıyorsa o listeye ekleyin, yapmıyorsa bir şey yapmanız
gerekmez, kendiliğinden koşulur.
