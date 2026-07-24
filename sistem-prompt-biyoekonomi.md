# ============================================================
# BİYOEKONOMİ BÜLTENİ — SİSTEM PROMPT DOSYASI (v1.0)
# ============================================================
# Bu dosya sistemin BEYNİ ve REFERANS BELGESİDİR.
# Kodda karşılıkları:
#   BÖLÜM 1 (sorgular)       → config.py  → SORGULAR
#   BÖLÜM 2 (taksonomi)      → config.py  → KATEGORILER / OLGUNLUK
#   BÖLÜM 3 (LLM promptları) → prompts.py → TRIYAJ_PROMPT / YAZIM_PROMPT
#   BÖLÜM 4 (kaynaklar)      → config.py  → KAYNAK_TIER1/TIER2/...
#   BÖLÜM 5 (onay akışı)     → db.py / review_app / publish.py
#   BÖLÜM 6-8 (şema, ayar)   → config.py  → AYARLAR
#
# Buradaki bir şeyi değiştirdiğinde İLGİLİ KOD DOSYASINI DA GÜNCELLE.
#
# Nükleer enerji bülteninden (orcaneker/nukleer-enerji-bulteni) uyarlanmıştır.
# Eski Perplexity+Netlify sisteminden farkları:
#   1. ARAMA: Perplexity yerine Exa AI (semantik + domain filtreli)
#   2. İKİ AŞAMA: triyaj (Haiku) → yazım (Sonnet) — eskiden tek Claude çağrısı
#   3. ONAY KATMANI: taslak → hakem incelemesi → onay → yayın
#   4. Neon Postgres (taslak/onay durumu) + Resend (e-posta)
#   5. Cron GitHub Actions yerine Render; yayın Netlify yerine GitHub Pages
#   6. Radar + "Bu Hafta 60 Saniyede" + ElevenLabs sesli özet
# ============================================================


# ============================================================
# BÖLÜM 0 — MİMARİ
# ============================================================
#
# CRON 1 — Pazar 12:00 TSİ (Render Cron, UTC "0 9 * * 0")
#   pipeline.py
#   ↓ EXA SEARCH — 12 sorgu × ek sorgu varyasyonları
#   ↓ NORMALİZASYON — UTM/AMP temizliği, başlık hash, görülmüş URL elemesi
#   ↓ DETERMİNİSTİK TARİH FİLTRESİ — pencere dışı/tarihsiz aday LLM'e gitmeden elenir
#   ↓ AŞAMA 1 — triyaj modeli (Haiku): olay kümeleme, eleme, puanlama
#   ↓ AŞAMA 2 — yazım modeli (Sonnet): 14 derin olayın TAMAMI tam haber
#     (8-10 "one_cikan" + kalanı "yedek") + radar + brief
#   ↓ TASLAK → Neon'a kaydet (status=review)
#   ↓ Resend → hakemlere davet e-postası (magic link)
#
# İNCELEME — Render Web Service (FastAPI, sürekli)
#   Hakem linke tıklar → taslağı görür
#   · Haberi çıkar → yedek havuzundan birini yerine koy (takas)
#   · Yedeği doğrudan bültene al / manşeti değiştir / radar maddesi çıkar
#   · "Onayla ve Yayınla" → status=approved  (TEK ONAY YETERLİ)
#   · Onay Pazartesi 08:00 TSİ'den SONRA gelirse yayın ANINDA tetiklenir
#
# CRON 2 — Pazartesi 08:00 TSİ (Render Cron, UTC "0 5 * * 1")
#   publish.py
#   · status=approved → nihai JSON kur (takaslar uygulanmış) → arşiv +
#     state + RSS + ElevenLabs sesli özet → docs/ → GitHub push → Pages
#   · status=review   → Resend hatırlatma e-postası; YAYIN YAPILMAZ
#     (otomatik yayın YOK — onay gelene dek bekler)
#   · Çalışma raporu e-postası (Resend → RAPOR_ALICI)


# ============================================================
# BÖLÜM 1 — EXA ARAMA SORGULARI (12)
# ============================================================
# config.py → SORGULAR. Kısa semantik sorgu + ayrı parametreler
# (tarih, domain, konum). Uzun doğal dil komutu YAZILMAZ.
#
#   politika        biyoekonomi stratejisi, mevzuat, RED III, ESPR, Biotech Act
#   biyoyakit       SAF, biyodizel, HVO, biyoetanol, biyometan/biyogaz, yeşil H2
#   biyomalzeme     biyoplastik (PLA/PHA), biyopolimer, lignin, biyobazlı kimya
#   biyomanufaktur  endüstriyel biyoteknoloji, hassas fermantasyon, enzim, synbio
#   gida-protein    alternatif protein, mikroprotein, alg protein, fermantasyon
#   atik-donusum    atıktan değer, döngüsel biyoekonomi, biyorafineri
#   tarim           biostimulant, biopestisit, tarımsal biyolojik ürünler
#   karbon          CCU, CO2 bazlı yakıt/kimyasal, biyokömür
#   deniz           deniz biyoekonomisi, alg/yosun endüstriyel kullanımı
#   uluslararasi    IEA/IRENA/FAO/OECD/WB/IATA raporları
#   turkiye         Türkiye odaklı gelişmeler (Türkçe + userLocation=tr)
#   asya-global     Çin/Japonya/Kore/ABD gelişmeleri (kategori: rapor)
#
# Tarih penceresi: birincil 7 gün; <40 aday kalırsa 14 güne genişler.
# Türkiye sorgusu userLocation="tr" ile yerel sonuç ağırlığı alır.


# ============================================================
# BÖLÜM 2 — KATEGORİ TAKSONOMİSİ (12) ve KOTALAR
# ============================================================
# config.py → KATEGORILER. "kota" = Öne Çıkanlar'da hedef sayı (katı değil).
# Kota olmadan biyoyakıt/SAF ve alternatif protein akışı domine eder.
#
#   politika (2) · biyoyakit (2) · biyomalzeme (2) · biyomanufaktur (1) ·
#   gida-protein (1) · atik-donusum (1) · tarim (0) · karbon (1) ·
#   deniz (0) · uluslararasi (1) · turkiye (1) · rapor (1)
#
# OLGUNLUK (config.py → OLGUNLUK) — biyoekonomi projelerinde ZORUNLU:
#   research → pilot → demonstration → announced → funded →
#   construction → commissioning → operational → scaling (+ delayed/cancelled)
# "Anlaşma imzalandı" ile "ticari üretim başladı" arasında yıllar var —
# en büyük sinyal-gürültü sorunu budur, aşama net belirtilir.
#
# DEĞER ZİNCİRİ (config.py → DEGER_ZINCIRI):
#   biyokutle → on-isleme → donusum-fermantasyon → urun-uretim →
#   kullanim → atik-geri-donusum


# ============================================================
# BÖLÜM 3 — LLM PROMPTLARI
# ============================================================
# prompts.py → TRIYAJ_PROMPT (Haiku) + YAZIM_PROMPT (Sonnet).
#
# TRİYAJ: sınıflandırır, YORUM YAPMAZ. Olay kümeler (aynı gelişmenin farklı
#   haberleri = 1 olay), eler (tarih dışı, söylenti, SEO, ilgisiz), 1-10 puanlar.
# YAZIM: Türkçeleştirir, SOMUT VERİYİ (tutar, kapasite, hammadde, takvim, yer,
#   teknoloji) eksiksiz çıkarır. ANALİZ/YORUM YASAK. Kaynağın durumunu ASLA
#   anlatmaz. Derin olayların TAMAMINI yazar (hakem takası için).


# ============================================================
# BÖLÜM 4 — KAYNAK KATMANLARI
# ============================================================
# config.py → KAYNAK_TIER1 (birincil: resmî kurum/şirket newsroom),
#   KAYNAK_TIER2 (sektör basını/ajans), KAYNAK_AKADEMIK, KAYNAK_TURKIYE.
# ÖDEME DUVARI: KAYNAK_ODEME_DUVARI'ndaki kaynaklar asla birincil olmaz;
#   tek kaynak duvarlıysa olay Radar'a düşer, teyit araması erişilebilir
#   kaynak bulmaya çalışır. DIŞLANANLAR: sosyal medya, PR wire, SEO pazar
#   araştırma siteleri (config.py → KAYNAK_DISLA).
# ⚠ reuters.com / bloomberg.com Exa includeDomains'e EKLENMEZ (403).


# ============================================================
# BÖLÜM 5 — ONAY AKIŞI
# ============================================================
# db.py (Neon) issue durumları: review → approved → published.
# TEK hakem onayı yeterli. Onay Pazartesi 08:00'den önceyse cron 2 yayınlar;
# sonraysa inceleme servisi publish.yayinla()'yı anında çağırır.
# Hakem ekleme: python db.py --seed "Ad Soyad" mail@ornek.com


# ============================================================
# BÖLÜM 6 — GENEL AYARLAR (config.py → AYARLAR)
# ============================================================
#   haber (Öne Çıkanlar) : 8-10  ·  derin olay: 14  ·  radar: 15-30
#   pencere: 7 gün (yetersizse 14) ·  brief: 5 madde
#   yayım: Pazartesi 08:00 TSİ  ·  taslak: Pazar 12:00 TSİ
#   model_triyaj: anthropic:claude-haiku-4-5-20251001
#   model_yazim:  anthropic:claude-sonnet-4-6
#   site_url: https://orcaneker.github.io/biyoekonomi-bulteni
#
# ⚠ İlk yayın öncesi: AYARLAR["sayi_no_sabit"] = None yapın
#   (test için 1'de sabitli; None → sayı otomatik artar).
