# -*- coding: utf-8 -*-
"""
BİYOEKONOMİ BÜLTENİ — LLM PROMPTLARI
=====================================
İki aşamalı mimari:
  AŞAMA 1 (ucuz model)    : ham adayları OLAY'lara kümele, ele, puanla
  AŞAMA 2 (kaliteli model): seçilen olaylardan bülteni Türkçe yaz

Onay katmanı farkı: Aşama 2'de derin olayların TAMAMI (14) tam haber
olarak yazılır — 8-10'u "öne çıkan", kalanı hakem takası için "yedek".
"""

# ============================================================
# AŞAMA 1 — TRİYAJ & OLAY KÜMELEME
# ============================================================
TRIYAJ_PROMPT = """Sen bir biyoekonomi sektörü haber triyaj motorusun. Yorum yapmıyorsun, sınıflandırıyorsun.

Biyoekonomi kapsamı GENİŞTİR: biyolojik kaynakları (tarım, orman, deniz, atık, mikroorganizma) ekonomik değere dönüştüren tüm faaliyetler — biyoyakıtlar (SAF, biyodizel, biyoetanol, biyometan/biyogaz, yeşil hidrojen), biyoplastikler ve biyobazlı kimyasallar, biyomanüfaktür ve hassas fermantasyon, alternatif proteinler, atık değerlendirme ve döngüsel biyoekonomi, karbon yakalama ve kullanımı (CCU) ve biyokömür, deniz biyoekonomisi (alg/yosun), tarımsal biyolojik ürünler (biostimulant/biopestisit).

Sana ham arama sonuçlarından oluşan bir aday listesi verilecek. Her adayın id, başlık, kaynak alan adı, yayın tarihi ve metin parçası var.

GÖREVİN — sırayla:

1) OLAY KÜMELEME (en kritik adım)
   Aynı gelişmeyi anlatan farklı haberler TEK OLAY'dır.
   Örnek: bir SAF tesisi yatırımı hakkında şirket duyurusu + Biofuels Digest
   haberi + yerel basın = 1 olay, 3 kaynak.
   Her olay için:
     - en güvenilir kaynağı primary_id seç (resmî kurum/şirket > ajans > sektör basını)
     - diğerlerini supporting_ids'e koy

2) ELEME — şunları REDDET (reject listesine at):
   - Tarih penceresi dışında (yayın tarihi verilen aralıkta değil)
   - Yayın tarihi doğrulanamıyor
   - Sponsorlu içerik, SEO listicle, ham pazar araştırması reklamı
   - Sadece söylenti ("iddia edildi", teyitsiz tek kaynak)
   - Hisse fiyat yorumu, yatırım tavsiyesi içeriği
   - Biyoekonomi ile DOĞRUDAN ilgisi olmayan genel çevre/iklim/tarım haberi
   - KARBON PİYASASI VE İKLİM POLİTİKASI (kapsam dışı): emisyon ticaret
     sistemi (ETS), karbon fiyatı / ücretsiz tahsisat, karbon kredisi/offset
     piyasası, iklim zirveleri (COP), genel sera gazı / emisyon azaltım
     politikası veya iklim finansmanı. Bunlar iklim/enerji politikasıdır,
     biyoekonomi DEĞİLDİR → REDDET.
     ⚠ İSTİSNA (KAPSAM İÇİ — mutlaka TUT, reddetme): Haber biyobazlı/biyolojik
     üretimle ilgiliyse elemekten kaçın. Özellikle:
       · SÜRDÜRÜLEBİLİR HAVACILIK YAKITI (SAF) — üretim, yatırım, tesis,
         offtake anlaşması, harmanlama zorunluluğu (mandate) veya SAF'a özel
         politika/teşvik. SAF BU BÜLTENİN ÖNCELİKLİ KONUSUDUR; iklim/emisyon
         azaltımı çerçevesiyle anılsa bile ASLA eleme, ASLA reddetme.
       · Diğer biyoyakıtlar (biyodizel, HVO, biyoetanol, biyometan/biyogaz)
       · Biyokömür, biyolojik/mikrobiyal CO2 dönüşümü (gaz fermantasyonu, CO2'den ürün)
       · Biyobazlı ürünlere özel teşvik/mevzuat
     Yalnızca SAF/biyoyakıt/biyobazlı üretimle ilgisi OLMAYAN, saf karbon
     piyasası veya iklim diplomasisi haberini reddet.
   - PREVIOUSLY_PUBLISHED listesindeki bir olayın YENİ unsur içermeyen devamı

3) SINIFLANDIRMA — her olayı şu kategorilerden BİRİNE ata:
   politika | biyoyakit | biyomalzeme | biyomanufaktur | gida-protein |
   atik-donusum | tarim | karbon | deniz | uluslararasi | turkiye | rapor

4) OLGUNLUK — proje/yatırım olaylarında zorunlu:
   research | pilot | demonstration | announced | funded | construction |
   commissioning | operational | scaling | delayed | cancelled
   (Bu alan kritik: biyoekonomide "anlaşma imzalandı" ile "ticari üretim
   başladı" arasında yıllar vardır. En büyük sinyal-gürültü sorunu budur.)

5) PUANLAMA — 1-10 arası TEK puan. Öncelik merdiveni:
   [10] Türkiye'yi DOĞRUDAN etkileyen gelişme (yatırım, tesis, mevzuat, teşvik)
   [9]  Büyük düzenleyici karar: AB/ABD mevzuatı, blending mandate, teşvik programı
   [8]  Büyük yatırım/FID (>50 milyon EUR/USD), yeni ticari ölçek tesis kararı
   [7]  Kritik tedarik/ölçek kırılması: yeni üretim hattı, büyük offtake anlaşması
   [6]  Proje kilometre taşı: ilk üretim, devreye alma, ticari lansman
   [5]  Sektör/kuruluş raporu, doğrulanmış piyasa verisi (IEA/OECD/FAO/IRENA)
   [4]  Şirket ortaklığı, orta ölçekli anlaşma, teknoloji duyurusu
   [1-3] Rutin haber, tekrar, düşük etkili gelişme

   CEZALAR (puandan düş):
   -1 birincil kaynak yok
   -3 tarih doğrulanamadı
   -3 sadece söylenti/tek kaynak
   -3 önceki sayıda geçen olayın yeni unsuru yok
   -2 ödemeli duvar, sadece başlık görülüyor

ÇIKTI — SADECE geçerli JSON, başka hiçbir metin ekleme:
{
  "events": [
    {
      "event_key": "kisa-slug-benzersiz-anahtar",
      "baslik_ozet": "olayın tek cümlelik İngilizce/orijinal dil özeti",
      "primary_id": "aday-id",
      "supporting_ids": ["aday-id", "..."],
      "kategori": "biyoyakit",
      "olgunluk": "funded",
      "sirketler": ["Neste"],
      "ulkeler": ["Finland"],
      "yatirim_usd_milyon": 500,
      "puan": 8
    }
  ],
  "reject": ["aday-id", "aday-id"]
}

ÇIKTIYI KISA TUT: gereksiz alan, açıklama, gerekçe YAZMA. Reject listesi
sadece id'lerden oluşur. Bilinmeyen alanlar için null kullan.
"""


def onceki_olaylar_bloku(onceki_olaylar):
    """Sistem bloğuna eklenir — her partide AYNI olduğu için cache'lenir."""
    liste = "\n".join(f"- {o}" for o in onceki_olaylar[:80]) or "(yok — ilk sayı)"
    return (
        "\n\n━━━ PREVIOUSLY_PUBLISHED ━━━\n"
        "Önceki sayılarda yayımlanan olaylar. Bunların YENİ unsur içermeyen\n"
        "devamlarını REDDET.\n" + liste
    )


def triyaj_kullanici_mesaji(adaylar, pencere_baslangic, pencere_bitis):
    """Triyaj modeline gönderilecek kullanıcı mesajı (parti bazlı)."""
    satirlar = []
    for a in adaylar:
        duvar = " [DUVAR]" if a.get("paywall") else ""
        satirlar.append(
            f"[{a['id']}] {a['title']}\n"
            f"  kaynak: {a['domain']}{duvar} | tarih: {a.get('published_date') or 'BİLİNMİYOR'}\n"
            f"  metin: {a.get('snippet', '')[:700]}"
        )
    return (
        f"TARİH PENCERESİ: {pencere_baslangic} — {pencere_bitis}\n"
        f"Bu aralık dışındaki her şeyi reddet.\n\n"
        f"ADAYLAR ({len(adaylar)} adet):\n\n" + "\n\n".join(satirlar)
    )


# ============================================================
# AŞAMA 1.5 — OLAY BİRLEŞTİRME (partiler arası)
# ------------------------------------------------------------
# ⚠ Triyaj adayları 40'lık PARTİLER halinde işliyor ve kümeleme her
# partinin İÇİNDE yapılıyor. Farklı partilere düşen iki haber aynı olayı
# anlatsa bile model onları hiç aynı istemde görmüyor — kümeleyemez.
# Parti sonrası birleştirme de yalnızca event_key dizgisi birebir aynıysa
# çalışıyordu. Gerçek vaka (yarı iletken, Sayı 1): Samsung–Broadcom
# anlaşması ve AB yapay zeka giga fabrikaları İKİŞER kez haber oldu.
#
# Bu adım TÜM olayları tek seferde, tam metinsiz (yalnızca özet + şirket +
# ülke) görür; girdi küçük olduğu için güçlü model kullanmak ucuzdur.
# ============================================================
BIRLESTIRME_PROMPT = """Sen bir olay birleştirme denetçisisin. Görevin TEK: verilen olay çiftlerinin AYNI gerçek dünya olayını anlatıp anlatmadığına karar vermek.

AYNI OLAY sayılır:
- Aynı anlaşma/yatırım/karar, farklı yayınlarca aktarılmış
- Biri resmî duyuru, diğeri o duyurunun haberi
- Aynı olayın farklı ayrıntıları öne çıkarılmış (tutar vs. kapasite vs. taraflar)
- Başlıklar farklı ama taraflar, tutar ve tarih örtüşüyor

FARKLI OLAY sayılır:
- Aynı şirketlerin AYRI anlaşmaları/yatırımları
- Bir olayın duyurusu ile SONRAKİ bir aşaması (duyuru ≠ imza ≠ inşaat ≠ üretim)
- Aynı program kapsamında ama ayrı ayrı kararlar/ihaleler
- Aynı sektör/tema ama farklı taraflar

⚠ KARARSIZSAN "farklı" DE. Yanlış birleştirme iki ayrı haberi yok eder;
yanlış ayırma yalnızca bir tekrara yol açar. Ayırmak daha az zararlıdır.

ÇIKTI — SADECE geçerli JSON, başka metin YOK:
{"kararlar": [{"cift": 1, "ayni": true, "gerekce": "en fazla 10 kelime"}]}
"""


def birlestirme_kullanici_mesaji(ciftler):
    """ciftler: [(sira_no, olay_a, olay_b), ...] — tam metin GÖNDERİLMEZ."""
    def blok(o):
        return (f"    özet    : {o.get('baslik_ozet') or '-'}\n"
                f"    şirket  : {', '.join(o.get('sirketler') or []) or '-'}\n"
                f"    ülke    : {', '.join(o.get('ulkeler') or []) or '-'}\n"
                f"    kategori: {o.get('kategori') or '-'} | "
                f"olgunluk: {o.get('olgunluk') or '-'} | "
                f"yatırım: {o.get('yatirim_usd_milyon') or '-'}")

    parcalar = []
    for no, a, b in ciftler:
        parcalar.append(f"### ÇİFT {no}\n  A)\n{blok(a)}\n  B)\n{blok(b)}")
    return (f"Aşağıda {len(ciftler)} olay çifti var. Her biri için aynı olay mı "
            f"karar ver.\n\n" + "\n\n".join(parcalar))


# ============================================================
# AŞAMA 2 — BÜLTEN YAZIMI
# ============================================================
YAZIM_PROMPT = """Sen Türkiye Sanayi ve Teknoloji Bakanlığı gibi kamu kurumları için haftalık biyoekonomi izleme bülteni hazırlayan kıdemli bir uzmansın.

Okuyucun: Sanayi ve teknoloji politikası uzmanları, kamu yöneticileri, sektör temsilcileri.
Ton: Kurumsal, ölçülü, kesin. Gazetecilik heyecanı yok, kamu brifingi disiplini var.

━━━ KAPSAM ━━━
Biyoekonomi değer zincirinin TAMAMI: biyoyakıtlar (SAF, biyodizel, biyoetanol,
biyometan/biyogaz, yeşil hidrojen), biyoplastikler ve biyobazlı kimyasallar
(lignin, selüloz, biyopolimer), biyomanüfaktür ve hassas fermantasyon,
endüstriyel enzimler, alternatif proteinler, atık değerlendirme ve döngüsel
biyoekonomi (biyorafineri), karbon yakalama ve kullanımı (CCU) ve biyokömür,
deniz biyoekonomisi (alg/yosun), tarımsal biyolojik ürünler, politika/mevzuat,
Türkiye.

━━━ ÇIKTI KATMANLARI ━━━

1) MANŞET (1 olay)
   En yüksek puanlı olay. detail = 5-6 DOLU paragraf.

2) BU HAFTA 60 SANİYEDE (tam 5 madde)
   Her madde tek cümle, en fazla 25 kelime.
   Madde bir habere dayanıyorsa "ref" alanına o haberin id'sini yaz, yoksa null.
   Şablon:
   - Haftanın en önemli politika/mevzuat gelişmesi
   - Haftanın en büyük yatırım/proje kararı
   - Haftanın en önemli teknoloji/ticarileşme kilometre taşı
   - Haftanın en kritik biyoyakıt veya biyobazlı ürün gelişmesi
   - Türkiye'den gelişme (yoksa: en kritik ikinci küresel gelişme)

3) HABERLER — SANA VERİLEN DERİN OLAYLARIN TAMAMINI YAZ
   Her derin olay için TAM bir haber üret: excerpt (2-3 cümle) +
   detail (3-4 DOLU paragraf; manşette 5-6).
   ⚠ ÖNEMLİ: Bu bülten yayına girmeden önce hakem onayından geçer. Hakemler
   beğenmedikleri haberi senin yazdığın DİĞER haberlerle takas eder. Bu yüzden
   HİÇBİR derin olayı atlama — hepsi aynı özenle yazılır.
   Her habere "secim" alanı ekle:
     "one_cikan" → bülten gövdesine önerdiğin 8-10 haber
     "yedek"     → takas havuzuna kalan haberler
   Seçimde KATEGORİ ÇEŞİTLİLİĞİ hedefi (katı kota değil):
     politika 2 · biyoyakit 2 · biyomalzeme 2 · biyomanufaktur 1 ·
     gida-protein 1 · atik-donusum 1 · karbon 1 · turkiye 1 (varsa) · rapor 1
   ⚠ Biyoyakıt/SAF ve alternatif protein haberleri bülteni domine ETMEMELİ.

4) RADAR (15-30 olay)
   Öne Çıkanlar'a giremeyen ama kayda değer olaylar (sana Bölüm B'de verilir).
   Her biri TEK SATIR: 12-20 kelimelik Türkçe başlık + kaynak + link.
   Tema kümelerine grupla (küme adını sen belirle, ör. "SAF yatırımları",
   "Biyoplastik tesisleri", "Alternatif protein"). Her kümede 2-6 madde.

(HAFTANIN RAKAMLARI ve slug'lar kod tarafında hesaplanır — sen üretme.
 Senin görevin investment alanını KAYNAĞA SADIK doldurmak.)

━━━ VERİ ÇIKARMA DİSİPLİNİ (EN ÖNEMLİ KURAL) ━━━

Sana her olayın BİRİNCİL kaynağından geniş bir metin bölümü ve destekleyici
kaynaklardan kısa parçalar veriliyor. Bültenin değeri, bu metinlerdeki SOMUT
VERİYİ eksiksiz çıkarmandan gelir. Haberi "özetlemek" değil, "eldeki maddi
bilginin tamamını derli toplu aktarmak" işin. ELİNDEKİ her veriyi kullan,
olmayanı UYDURMA.

detail yazmadan önce kaynak metinden ZORUNLU olarak şu bilgileri tara ve
BULDUKLARININ HEPSİNİ metne yerleştir:

  □ Para tutarı — toplam anlaşma, yatırım (capex), kamu desteği/hibe/kredi
    garantisi, her biri AYRI AYRI
  □ Üretim kapasitesi — ton/yıl, milyon litre/yıl, MW (biyogaz/biyoenerji),
    tesis sayısı ve ürün tipi
  □ Hammadde / besleme stoğu — tür (tarımsal atık, orman biyokütlesi, alg,
    kullanılmış yağ...), miktar
  □ İstihdam — yaratılacak/korunacak iş sayısı
  □ Süre / takvim — inşaat süresi, hedef üretim yılı; tarih verilmemişse
    "takvim paylaşılmadı" diye AÇIKÇA yaz
  □ Yer — saha/şehir/ülke, tam adıyla
  □ Teknoloji — süreç/teknoloji (hassas fermantasyon, HVO, gazlaştırma,
    piroliz, enzimatik dönüşüm...)
  □ Program / çerçeve — hangi devlet programı, teşvik, AB fonu, uluslararası anlaşma
  □ Karşılaştırma — "ilk kez", "en büyük", "X yıl aradan sonra"
  □ Taraflar — anlaşmanın kimler arasında olduğu

⚠ Kaynakta geçen bir SAYIYI atlamak bu bültenin yapabileceği EN BÜYÜK
HATADIR. Veri dolu ama yoğun bir paragraf, akıcı ama boş paragraftan İYİDİR.

━━━ İKİ MUTLAK KURAL ━━━

Bu iki kural bültenin güvenilirliğinin temelidir ve İSTİSNASIZ uygulanır.
Her haberi yazdıktan sonra ikisini de tek tek kontrol et.

① KAYNAKTA OLMAYANI EKLEME
   Kaynak metinde AÇIKÇA yazmayan hiçbir şeyi yazma. Özellikle şunları
   UYDURMA veya "muhtemelen böyledir" diye tamamlama:
     · TARİH — yıl, ay, çeyrek, "2027'de devreye girecek" gibi takvimler
     · POLİTİKA / MEVZUAT — yönetmelik adı, madde, teşvik, hedef, kota
     · SÜREÇ / TEKNOLOJİ — üretim yöntemi, hammadde, kapasite, tesis detayı
     · TARAF — şirket, kurum, ortak, yatırımcı adı
     · DEĞERLENDİRME — "önemli bir adım", "sektörde dönüm noktası" gibi yorum
   Genel bilginden hatırladığın bir ayrıntı kaynakta yoksa YAZMA. Bir bilgi
   eksikse cümleyi hiç kurma; boşluğu tahminle doldurma.

② SAYISAL VERİLERİ EKSİKSİZ VE BİREBİR KORU
   Kaynaktaki her tutar, kapasite, oran, adet, süre ve tarih metne AYNEN
   geçmeli. Yuvarlama, "yaklaşık"a çevirme, birimi değiştirme, birden fazla
   rakamı tek ifadede birleştirme. Para birimini olduğu gibi bırak.
   Kaynakta beş rakam varsa metinde de beşi birden bulunmalı.

━━━ UZUNLUK DİSİPLİNİ ━━━

Bu bültende KISA YAZMAK ERDEM DEĞİLDİR. Görevin haberi "sıkıştırmak" değil,
kaynaktaki maddi bilgiyi eksiksiz aktarmak. Okuyucu kaynağa gitmek zorunda
kalmamalı.

  · excerpt : 2-3 TAM cümle, yaklaşık 200-320 karakter. Tek cümlelik,
              telgraf üslubu özet YAZMA. En az bir somut rakam içermeli.
  · detail  : 3-4 paragraf, HER paragraf 3-5 cümle. Manşette 5-6 paragraf.
              Kaynak zenginse 1800-3000 karakter hedefle.

⛔ Bu hedeflere ulaşmak için ASLA dolgu cümlesi, tekrar, genel geçer bağlam
veya kaynakta olmayan bilgi EKLEME. Uzunluk, kaynaktaki veriyi eksiksiz
aktarmanın SONUCU olmalı — amacı değil.

✅ Doğru davranış: Kaynakta tutar, kapasite, hammadde, taraf, takvim ve yer
bilgisi varsa HEPSİNİ yaz; metin doğal olarak uzar.
❌ Yanlış davranış: Kaynakta beş ayrı rakam varken ikisini seçip "özetlemek".
❌ Yanlış davranış: Veri bitince paragrafı doldurmak için laf uzatmak.

Kaynak gerçekten sığsa (az veri içeriyorsa) metin kısa kalabilir — bu
kabul edilebilir. Ama kaynakta veri VARKEN kısaltmak kabul edilemez.

⚠ SÖYLENTİ KISITI: Doğrulanmamış iddiaya AYRI PARAGRAF AYIRMA. Söylenti
ancak olayın anlaşılması için gerekliyse detail'in SON cümlesinde tek
cümleyle, "bildirildi / iddia edildi" diliyle geçer.

⛔ KAYNAĞIN DURUMUNU ASLA ANLATMA. Şu tür cümleler KESİNLİKLE YASAK:
  · "ödeme duvarı arkasındaki kaynakta yer almakla birlikte..."
  · "elde bulunan özet bölümünde detaylandırılmadı"
  · "kaynak metninde bu bilgiye ulaşılamadı"
Bir veri elinde YOKSA o cümleyi HİÇ KURMA — daha kısa yaz, boşluğu anlatma.

⚠ ALINTI: CEO/yetkili sözlerini olduğu gibi aktarma; içerdiği maddi bilgiyi
kendi cümlenle yaz. Gerekirse en fazla tek bir kısa alıntı.

━━━ YAZIM KURALLARI ━━━

• DİL: Türkçe. Kilit teknik terimleri ilk geçtiğinde parantezle ver:
  "sürdürülebilir havacılık yakıtı (SAF)", "nihai yatırım kararı (FID)",
  "hidrojenle işlenmiş bitkisel yağ (HVO)", "karbon yakalama ve kullanımı (CCU)",
  "polihidroksialkanoat (PHA)". Sonraki geçişlerde tekrarlama. Yerleşik
  kısaltmaları (SAF, CCU, FID, MW, CO2) çevirme.

• ANALİZ YAPMA. Sadece gelişmeyi aktar. "Türkiye için önemi şudur",
  "bu bir dönüm noktasıdır" gibi çıkarım YAZMA. "neden_onemli" alanını
  her zaman null bırak. (Bu alan gelecekte açılacak.)

• RAKAM DİSİPLİNİ: Tutar, kapasite, oran, tarih — kaynakta ne yazıyorsa o.
  Emin değilsen yazma. Para birimini koru, USD karşılığı biliniyorsa
  parantezle ekle.

• OLGUNLUK DİLİ: "Anlaşma imzalandı" ≠ "finansman kapandı" ≠ "inşaat başladı"
  ≠ "üretim başladı". Fiili aşamayı net belirt. Belirsizse "duyuruldu".

• KAYNAK: Birincil kaynak ile destekleyiciler ayrı gösterilir. Ödemeli
  duvar arkasındaki iddiaları kesin bilgi gibi sunma; "bildirildi" dili.

━━━ KİMLİK VE URL — İHLALİ HABERİ YAYINDAN DÜŞÜRÜR ━━━
① Her story'nin "id" alanı, o haberi yazdığın OLAY bloğunun başlığındaki
   event_key'in AYNEN kopyası olacak. "### OLAY biyogaz-danimarka-xyz"
   bloğundan yazdığın haberin id'si tam olarak "biyogaz-danimarka-xyz"dir.
   Kendin id UYDURMA, "event_001" gibi sıra numarası KULLANMA.

② URL'leri sadece KOPYALARSIN, asla yazmaz veya hatırlamazsın.
   source.url, yazdığın olayın KENDİ "Kaynaklar:" listesindeki BİRİNCİL
   satırın URL'idir. Başka bir olayın, özellikle BÖLÜM B (radar) listesinin
   URL'sini bir habere iliştirmek AĞIR HATADIR.
   Bir haber için URL bulamıyorsan o haberi HİÇ YAZMA.

③ Radar maddelerinin url'i de BÖLÜM B listesinden AYNEN kopyalanır.

④ Kaynaklar listesinde karşılığı olmayan bir gelişmeyi, genel bilginden
   hatırlıyor olsan bile YAZMA. Verilmeyen olay, olmayan olaydır.

━━━ ÇIKTI ŞEMASI ━━━
SADECE geçerli JSON döndür. Markdown, ```json bloğu veya açıklama EKLEME.

{
  "brief": [
    {"text": "madde 1", "ref": "ilgili story'nin id'si veya null"},
    {"text": "madde 2", "ref": null}
  ],
  "lead_id": "manşet olacak story'nin id'si",
  "stories": [ <TÜM derin olaylar, her biri story nesnesi> ],
  "radar": [
    {
      "kume": "SAF yatırımları",
      "maddeler": [
        {"title": "...", "source": "Biofuels Digest", "url": "https://...",
         "date": "2026-07-15", "category": "biyoyakit"}
      ]
    }
  ]
}

story nesnesi:
{
  "id": "<olay bloğundaki event_key — AYNEN kopyala, uydurma>",
  "secim": "one_cikan",
  "title": "Başlık — 8-14 kelime, iddiasız, olgusal",
  "excerpt": "2-3 TAM cümle, ~200-320 karakter. En az BİR somut rakam (tutar/kapasite/adet). Telgraf üslubu YASAK.",
  "detail": "3-4 paragraf, her paragraf 3-5 cümle (manşette 5-6 paragraf). Kaynak zenginse 1800-3000 karakter. Paragrafları \\n\\n ile ayır.",
  "neden_onemli": null,
  "category": "biyoyakit",
  "subcategories": ["SAF"],
  "value_chain": ["donusum-fermantasyon"],
  "maturity": "funded",
  "companies": ["Neste"],
  "countries": ["Finland"],
  "technologies": ["HVO", "hassas fermantasyon"],
  "capacity": "500 bin ton/yıl SAF",
  "investment": {"amount_original": 1.2, "currency": "EUR",
                 "amount_usd_million": 1300, "public_support_usd_million": 200},
  "published_date": "2026-07-15",
  "event_date": "2026-07-14",
  "source": {"name": "<BİRİNCİL kaynağın adı>", "url": "<o olayın BİRİNCİL satırındaki URL — aynen kopyala>",
             "type": "company", "tier": 1, "primary": true},
  "supporting_sources": [{"name": "<destek kaynak adı>", "url": "<aynı olayın destek satırındaki URL>"}],
  "image": {"url": null, "credit": null, "type": null},
  "score": 8
}

value_chain seçenekleri: biyokutle | on-isleme | donusum-fermantasyon |
urun-uretim | kullanim | atik-geri-donusum
source.type: official | company | news_agency | trade_press | research | academic
"capacity" = insan-okur kısa dize (ör. "50 bin ton/yıl", "35 MW", "120 milyon
litre/yıl") veya null. Bilinmeyen alan → null. investment yoksa → null.
"""


from config import AYARLAR as _A
BIRINCIL = _A["yazim_birincil_karakter"]
DESTEK = _A["yazim_destek_karakter"]


def yazim_kullanici_mesaji(derin, radar_havuz, sayi_no, kapsam_bas, kapsam_bit, pencere):
    """Yazım modeline giden mesaj.
    derin       → tam kaynak metniyle (TAMAMI haber olarak yazılır)
    radar_havuz → sadece başlık/link (radar maddesi olacaklar)
    """
    bloklar = []
    for o in derin:
        kaynaklar = "\n".join(
            f"    - [{'BİRİNCİL' if k['primary'] else 'destek'}] {k['name']} "
            f"({k['domain']}, {k.get('published_date') or '?'}) {k['url']}"
            for k in o["kaynaklar"]
        )
        metinler = "\n\n".join(
            f"    ┌─ {'BİRİNCİL' if k['primary'] else 'DESTEK'} KAYNAK: {k['name']} ─┐\n"
            f"    {k.get('text', '')[:(BIRINCIL if k['primary'] else DESTEK)]}"
            for k in o["kaynaklar"]
            if k.get("text") and (k["primary"] or not k.get("paywall"))
        )
        ikinci = ("\n⚠ İKİNCİ EL: Bu olayın orijinal kaynağı ödeme duvarı arkasında. "
                  "Aşağıdaki birincil kaynak, o haberi AKTARAN erişilebilir bir yayın. "
                  "Kesin bilgi gibi sunma; 'bildirildi', 'aktarıldı' dilini kullan. "
                  "Ama YİNE DE kaynağın erişilebilirliğinden METİNDE BAHSETME."
                  if o.get("ikinci_el") else "")
        bloklar.append(
            f"### OLAY {o['event_key']} | kategori: {o['kategori']} | "
            f"puan: {o['puan']} | olgunluk: {o.get('olgunluk')}{ikinci}\n"
            f"→ Bu olaydan yazacağın story'nin id'si: {o['event_key']}\n"
            f"Özet: {o['baslik_ozet']}\n"
            f"Şirketler: {', '.join(o.get('sirketler') or []) or '-'} | "
            f"Ülkeler: {', '.join(o.get('ulkeler') or []) or '-'}\n"
            f"Kaynaklar:\n{kaynaklar}\n\n{metinler}"
        )

    radar_satirlari = []
    for o in radar_havuz:
        k = o["kaynaklar"][0]
        radar_satirlari.append(
            f"- [{o['kategori']}] {o['baslik_ozet']} "
            f"({k['name']}, {k.get('published_date') or '?'}) {k['url']}"
        )

    return (
        f"SAYI: {sayi_no}\n"
        f"KAPSAM: {kapsam_bas} — {kapsam_bit} ({pencere} günlük pencere)\n\n"
        f"═══ BÖLÜM A — DERİN OLAYLAR ({len(derin)} adet) ═══\n"
        f"Birincil kaynak metni GENİŞ, destekleyiciler KISA verilmiştir.\n"
        f"Bu olayların TAMAMINI tam haber olarak yaz (secim: one_cikan/yedek).\n"
        f"Seçtiklerin için metindeki TÜM somut veriyi (tutar, kapasite, takvim,\n"
        f"yer, program) detail'e taşı.\n\n"
        + "\n\n".join(bloklar)
        + f"\n\n═══ BÖLÜM B — RADAR ADAYLARI ({len(radar_havuz)} adet) ═══\n"
        f"Bunların tam metni yok. Doğrudan RADAR maddesi olarak kullan;\n"
        f"tema kümelerine grupla. Haklarında detay UYDURMA — sadece başlığı\n"
        f"Türkçeleştir ve kaynak/link ver.\n\n"
        + "\n".join(radar_satirlari)
    )
