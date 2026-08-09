# Yazım modeli karşılaştırması — Ağustos 2026

**Sonuç: Sonnet 5'te kalındı.** Terra denendi, ölçüldü, seçilmedi. Bu klasör
denemenin ham çıktılarını saklıyor; geri dönmek istenirse hiçbir şeyi yeniden
çalıştırmaya gerek yok.

## Neden bu deneme yapıldı

Sayı 2 taslağı (9 Ağustos 2026, hafta `2026-H32`) beğenilmedi. İlk teşhis
"çeviri kalitesi" idi; ölçünce iki ayrı sorun olduğu görüldü.

**Sorun 1 — bülten yarım çıktı.** Yazıma 14 derin olay + 26 radar adayı gitti;
model 5 haber yazıp kalanların yerine `__PLACEHOLDER_NOT_USED__` adlı bir yer
tutucu koydu, radar bölümünü hiç açmadı. Çıktı çağrı başına 8,3K token'dı —
tam bülten 29–33K gerektiriyor. Boru hattı bunu fark etmedi, taslak kaydedildi
ve hakemlere davet gitti.

**Sorun 2 — Türkçeleştirme.** Prompt'ta sayı/tarih/kurum adı biçimi için kural
yoktu. Sonnet bunları kültürel yetkinlikle kendiliğinden yapıyordu, Terra
yapmıyordu.

## Ölçümler

Hepsi **aynı 14 olay, aynı kaynaklar, aynı prompt** üzerinde:

| | Sonnet A | Sonnet B | Terra high |
|---|---|---|---|
| haber / radar | 14 / 23 | 14 / 25 | 14 / 25 |
| ort. cümle uzunluğu | 20,8 kelime | 19,8 | **12,7** |
| cümle uzunluğu sapması | 7,6 | 8,1 | **5,0** |
| 12 kelimeden kısa cümle | %9 | %14 | **%51** |
| ardışık "-yor" ile biten | 4 | 4 | **9** |
| dolgu cümlesi | 0 | 0 | **7** |
| kaynağın durumu anlatılmış | 5 | 2 | 3 |
| ort. başlık uzunluğu | 11,0 | 10,8 | **7,5** (hedef 8-14) |
| biçim ihlali | 0 | 0 | 0 |
| yazım maliyeti | 0,53 $ | 0,59 $ | **0,22 $** |

**Karar gerekçesi:** Terra ucuz ve eksiksiz, ama aynı bilgiyi 80 fazla cümleye
bölüyor; yarısı 12 kelimenin altında, art arda dokuz cümle "-yor" ile bitiyor.
Türkçede tekdüze bir tempo çıkıyor. Yöneticinin "Sonnet daha iyi" değerlendirmesi
bu ölçümlerle örtüşüyor. Terra ayrıca prompt'un yasakladığı dolgu cümleleri
üretiyor ve başlıkları hedefin altında kalıyor.

Rakam doğruluğunda fark yok: iki modelde de 54 sayının tamamı kaynaklarda
doğrulandı, sıfır hata.

## Denemenin sonunda kalıcı hale gelen değişiklikler

Terra seçilmedi ama deneme üç kalıcı iyileştirme üretti — üçü de Sonnet'i de
düzeltiyor:

1. **`prompts.py` → TÜRKÇELEŞTİRME bölümü.** Sayı biçimi, para birimi, ay adı,
   kurum adı, yer adlarının çevrilmemesi, birim sözlüğü, markdown yasağı.
   Etki: Terra 126 → 0 ihlal, Sonnet 22 → 0 ihlal (14 haber üzerinde).
2. **`pipeline.py` → `yazim_eksik()` tamlık denetimi.** Haber sayısı derin
   olayların %70'inin altındaysa, yer tutucu üretildiyse ya da radar havuzu
   doluyken radar boş geldiyse yeniden dener; iki denemede de düzelmezse
   çalışma raporunun başına kırmızı bayrak koyar.
3. **`pipeline.py` → `_kontrol_kacir()`.** Sonnet uzun metinlerde dize içine
   kaçışsız satır başı koyabiliyor; `json_repair` bu durumda gövdenin
   tamamını değil ilk birkaç kaydı kurtarıyordu. Artık deterministik ve
   kayıpsız onarım önce denenir.

## Güvenilirlik notu — Sonnet 5

Üç koşuda gözlenen:

| koşu | haber | JSON |
|---|---|---|
| Pazar (üretim) | 5/14 | onarılamadı |
| Deneme A | 14/14 | bozuk → onarıldı |
| Deneme B | 14/14 | temiz |

Erken bırakma 3'te 1, bozuk JSON 3'te 2 kez görüldü. Üç koşu az bir örneklem;
kesin oran değil. Yukarıdaki 2. ve 3. maddeler tam olarak bu iki kusur için
eklendi. Arıza tekrar ederse sıradaki adım **haber başına ayrı çağrı** —
her haberin JSON'u küçük olur, biri bozulsa yalnızca o haber yeniden yazılır;
maliyet yaklaşık iki katına çıkar.

## Terra'ya dönmek istenirse

Kod değişikliği gerekmez, model adı ortam değişkeniyle geçilebilir:

```bash
MODEL_YAZIM=openai:gpt-5.6-terra REASONING_EFFORT=high python pipeline.py --dry-run
```

Kalıcı geçiş için `config.py` → `AYARLAR["model_yazim"]` satırını
`"openai:gpt-5.6-terra"` yapmak ve `reasoning_effort` değerini `"high"`
bırakmak yeterli. `OPENAI_API_KEY` Render'daki ortak değişken grubunda zaten
tanımlı. Fiyat satırı `config.py` → `FIYAT` içinde hazır.

⚠ Terra'ya dönülürse yukarıdaki tabloda kırmızı görünen kalemler geri gelir:
kısa ve tekdüze cümleler, dolgu paragrafları, kısa başlıklar. Bunları prompt'la
kapatmak denenmedi.

## Klasördeki dosyalar

### `ciktilar/` — ham model çıktıları (taslak JSON biçimi)
| dosya | ne |
|---|---|
| `sayi2-uretim-taslagi-sonnet5.json` | Pazar günkü ÜRETİM taslağı — 5 haber, 0 radar (arızanın kendisi) |
| `5haber-terra-eski-prompt.json` | aynı 5 haber, Terra, Türkçeleştirme kuralları eklenmeden |
| `5haber-terra-yeni-prompt.json` | aynı 5 haber, Terra, kurallar eklendikten sonra |
| `14haber-terra-eski-prompt.json` | tam akış, 14 haber + 25 radar, eski prompt |
| `14haber-terra-yeni-prompt.json` | tam akış, 14 haber + 25 radar, yeni prompt |
| `14haber-sonnet5-A.json` | aynı 14 olay, Sonnet 5, birinci deneme |
| `14haber-sonnet5-B.json` | aynı 14 olay, Sonnet 5, ikinci deneme |

### `kiyas/` — okunabilir karşılaştırmalar
| dosya | ne |
|---|---|
| `5haber-sonnet5-vs-terra.txt` | yan yana, 5 haber |
| `14haber-sonnet5-vs-terra.txt` | yan yana, 14 haber — **asıl kıyas** |
| `14haber-terra-prompt-etkisi.txt` | Terra eski/yeni prompt |
| `Ceviri-Kiyasi-Sayi2.docx` | yöneticiye gönderilen iki sütunlu doküman |

## Yeniden ölçmek için

`denemeler/araclar/` altındaki betikler repo kökünden çalıştırılır:

```bash
python denemeler/araclar/dil_denetimi.py denemeler/model-kiyasi-2026-08/ciktilar/*.json
```

```bash
python denemeler/araclar/uslup_denetimi.py denemeler/model-kiyasi-2026-08/ciktilar/14haber-sonnet5-A.json
```

Yeni bir model denemek için (Exa araması ve triyaj TEKRAR ÇALIŞMAZ, aynı
haberler aynı kaynaklardan yeniden yazılır):

```bash
python yeniden_yaz.py --girdi denemeler/model-kiyasi-2026-08/ciktilar/14haber-sonnet5-A.json --model openai:gpt-5.6-terra --effort high --cikti kiyas/deneme
```
