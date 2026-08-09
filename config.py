# -*- coding: utf-8 -*-
"""
BİYOEKONOMİ BÜLTENİ — YAPILANDIRMA
===================================
Sorgular, kategori taksonomisi, kaynak katmanları ve ayarlar burada.
pipeline.py / publish.py / review_app bunları okur.
Yeni sorgu/kaynak eklemek için sadece bu dosyayı düzenle.
"""

import os

# ============================================================
# .env YÜKLEYİCİ
# ------------------------------------------------------------
# Yerelde deneme yaparken anahtarları her seferinde kabuğa yazdırmamak için
# repo kökündeki .env okunur (.gitignore'da — git'e girmez).
# Render'da .env dosyası YOKTUR; değişkenler zaten ortamda tanımlı olduğu
# için bu fonksiyon sessizce çıkar. Üretim davranışı değişmez.
#
# ⚠ Burada duruyor çünkü config, llm ve pipeline'dan ÖNCE import edilen tek
#   modül — o ikisi anahtarları import anında okuyor.
# ⚠ setdefault: gerçek ortam değişkeni her zaman .env'i EZER.
# ============================================================
def _env_yukle(dosya=".env"):
    yol = os.path.join(os.path.dirname(os.path.abspath(__file__)), dosya)
    if not os.path.exists(yol):
        return
    # errors="replace": .env'i Not Defteri ANSI olarak kaydederse Türkçe
    # karakterli yorum satırı yüzünden çökmesin — anahtarlar zaten ASCII.
    with open(yol, encoding="utf-8", errors="replace") as f:
        for satir in f:
            satir = satir.strip()
            if not satir or satir.startswith("#") or "=" not in satir:
                continue
            k, v = satir.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


_env_yukle()


# ============================================================
# YEREL CA PAKETİ (yalnızca TLS'i araya giren antivirüs/proxy varsa)
# ------------------------------------------------------------
# Avast / ESET / Kaspersky gibi araçlar "HTTPS taraması" açıkken trafiği
# çözüp KENDİ kök sertifikalarıyla yeniden imzalıyor. O kök Windows
# sertifika deposunda vardır — tarayıcı sorunsuz çalışır — ama Python'un
# certifi paketinde YOKTUR, dolayısıyla requests şu hatayı verir:
#   CERTIFICATE_VERIFY_FAILED: unable to get local issuer certificate
#
# Çözüm: repo kökünde ca-bundle.local.pem varsa (certifi paketi + araya
# giren aracın kök sertifikası) onu kullan. Dosya .gitignore'dadır ve
# makineye özeldir; Render'da bulunmadığı için üretim etkilenmez.
# ⚠ Doğrulama KAPATILMIYOR — sadece güvenilen kök listesi genişletiliyor.
# ============================================================
_YEREL_CA = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                         "ca-bundle.local.pem")
if os.path.exists(_YEREL_CA) and not os.environ.get("REQUESTS_CA_BUNDLE"):
    os.environ["REQUESTS_CA_BUNDLE"] = _YEREL_CA


# ============================================================
# GENEL AYARLAR
# ============================================================
AYARLAR = {
    # Takvim: taslak Pazar 12:00 TSİ hazırlanır, yayın Pazartesi 08:00 TSİ.
    # Render cron (UTC): taslak "0 9 * * 0" · yayın "0 5 * * 1"
    "taslak_gunu": "pazar",
    "yayim_gunu": "pazartesi",
    "yayim_saati_tsi": 8,            # yayın eşiği (geç onay kontrolünde kullanılır)

    "pencere_gun": 7,                # birincil tarama penceresi
    "pencere_genis_gun": 14,         # yetersiz sonuçta genişletilir

    # Bülten hacim hedefleri
    "manset": 1,
    "brief_madde": 5,                # "Bu Hafta 60 Saniyede"
    "one_cikan_min": 8,
    "one_cikan_max": 10,
    "radar_min": 15,
    "radar_max": 30,

    # LLM — sağlayıcı öneki zorunlu: "anthropic:..." veya "openai:..."
    "model_triyaj": "anthropic:claude-haiku-4-5-20251001",
    # Yazım Sonnet 5'te (30 Tem 2026). Kısa geçmiş: Sonnet 4.6 → Luna → Sonnet 5.
    # Luna denendi ve BIRAKILDI: Türkçe akıcılığı iyiydi ama halüsinasyon oranı
    # yüksek, kaynaktaki birçok detayı atlıyordu.
    # Sonnet 5 notları:
    #   · Adaptif düşünme VARSAYILAN OLARAK AÇIK (4.6'da kapalıydı) — düşünme
    #     token'ları max_tokens bütçesinden düşer, limit bu yüzden yükseltildi.
    #   · Yeni tokenizer aynı metni ~%30 daha fazla token sayar.
    #   · temperature/top_p/top_k ve budget_tokens 400 döndürür — llm.py bunları
    #     zaten göndermiyor, ek iş gerekmedi.
    # Geri dönmek için: "anthropic:claude-sonnet-4-6"
    "model_yazim": "anthropic:claude-sonnet-5",
    # NOT: temperature parametresi BİLEREK gönderilmiyor (model uyumsuzluk deneyimi).

    # OpenAI reasoning modelleri (gpt-5.6 ailesi) için akıl yürütme seviyesi:
    # none | low | medium | high | xhigh | max
    # ⚠ Düşünme token'ları ÇIKTI fiyatından faturalanır — seviye yükseldikçe
    # maliyet artar. "low" denendi: çıktı Sonnet'in ~%65'i kadar kaldı, yani
    # kaynaktaki veriyi eleyerek kısaltıyordu. "medium" bu yüzden seçildi.
    # REASONING_EFFORT ortam değişkeni bu ayarı ezer (deneme yaparken pratik).
    # Anthropic modellerinde yok sayılır.
    "reasoning_effort": "medium",
    "triyaj_batch": 40,              # tek seferde triyaja giden aday sayısı
    "model_birlestirme": "anthropic:claude-sonnet-5",   # olay birlestirme
    # ^ girdi kucuk (yalnizca olay ozetleri) -> guclu model ucuza gelir
    "max_tokens_birlestirme": 4000,
    "max_tokens_triyaj": 8000,
    "max_tokens_yazim": 48000,       # 14 haberin TAMAMI yazıldığı için GENİŞ olmalı.
                                     # ⚠ Düşük tutulursa çıktı JSON tamamlanmadan kesilir.
    # Akıl yürüten modellerde (gpt-5.x, Sonnet 5, Opus 4.7+, Fable 5) "düşünme"
    # token'ları da BU bütçeden düşer — görünür metne kalan pay azalır ve JSON
    # ortadan kesilir. Sonnet 5'te ayrıca yeni tokenizer aynı metni ~%30 daha
    # fazla token sayıyor; ölçülen 22,7K çıktı ~29,5K'ya çıkıyor, üstüne düşünme
    # binince 48K sınırı dolabilirdi. Bu modeller 128K çıktı desteklediği için
    # rahat pay bırakıldı — kullanılmayan bütçe ücretlendirilmez.
    "max_tokens_yazim_reasoning": 96000,
    "derin_olay_sayisi": 14,         # tam metinle yazıma giden olay — HEPSİ haber olur
    "toplam_olay_sayisi": 40,        # geri kalanı radar adayı (başlık+link)

    # Exa
    "exa_sonuc_sayisi": 20,          # sorgu başına
    "exa_metin_karakter": 4000,      # çekilen makale metni
    "exa_triyaj_karakter": 700,      # triyaja giden kısa parça (ucuz)
    "yazim_birincil_karakter": 3500, # birincil kaynak derin okunur
    "yazim_destek_karakter": 800,    # destekleyici sadece fark için
    "exa_tip": "auto",

    # Site
    "site_url": "https://biyoekonomi-bulteni.site",
    "cikti_dizini": "docs",          # GitHub Pages sadece / veya /docs kabul eder

    # Sayı numarası: None → otomatik artar (yayınlanan son sayı + 1).
    # Sayaç canlı sitedeki data/state/seen_events.json → issue_no alanında
    # yaşar; publish.py her yayında oraya yazar.
    # Test amacıyla numarayı dondurmak istersen sabit bir sayı ver (ör. 1),
    # ama YAYINA GEÇERKEN None'a geri al — aksi halde her sayı aynı numarayı
    # alır ve arşivde mükerrer görünür.
    "sayi_no_sabit": None,
}

# ============================================================
# FİYATLANDIRMA (USD / 1 milyon token) — maliyet TAHMİNİ için
# ⚠ Fiyatlar değişebilir; console.anthropic.com / platform.openai.com'dan doğrula.
# ============================================================
FIYAT = {
    "anthropic:claude-sonnet-4-6":         {"in": 3.00, "out": 15.00, "cache_w": 3.75, "cache_r": 0.30},
    "anthropic:claude-haiku-4-5-20251001": {"in": 1.00, "out":  5.00, "cache_w": 1.25, "cache_r": 0.10},
    "openai:gpt-5-mini":                   {"in": 0.25, "out":  2.00, "cache_w": 0.25, "cache_r": 0.025},
    "openai:gpt-5.1":                      {"in": 1.25, "out": 10.00, "cache_w": 1.25, "cache_r": 0.125},
    # GPT-5.6 ailesi (Temmuz 2026): Sol (amiral) · Terra (dengeli) · Luna (ucuz).
    # ⚠ Reasoning modelidir: "düşünme" token'ları ÇIKTI fiyatından faturalanır.
    # Bu yüzden aşağıdaki "reasoning_effort" ayarı maliyeti doğrudan etkiler.
    # ⚠ OpenAI'de cache YAZMA ücretsizdir (cache_w = normal girdi fiyatı);
    #    okuma girdinin %10'u. 30 Tem 2026 fiyat indirimi sonrası liste fiyatları:
    "openai:gpt-5.6-sol":                  {"in": 5.00, "out": 30.00, "cache_w": 5.00, "cache_r": 0.50},
    "openai:gpt-5.6-terra":                {"in": 2.00, "out": 12.00, "cache_w": 2.00, "cache_r": 0.20},
    "openai:gpt-5.6-luna":                 {"in": 0.20, "out":  1.20, "cache_w": 0.20, "cache_r": 0.02},
    # ⚠ Sonnet 5 liste fiyatı 4.6 ile AYNI ($3/$15) ama 31 Ağustos 2026'ya kadar
    # tanıtım fiyatı $2/$10. Aşağıda LİSTE fiyatı yazılı — maliyet raporu böylece
    # olduğundan düşük görünmez. Tanıtım bitince satır zaten doğru kalır.
    "anthropic:claude-sonnet-5":           {"in": 3.00, "out": 15.00, "cache_w": 3.75, "cache_r": 0.30},
}

# ============================================================
# EXA ARAMA FİYATI (USD) — maliyet TAHMİNİ için
# ⚠ exa.ai/pricing'den doğrula; değişebilir.
# Model: istek başına taban ücret İLK 10 SONUCU kapsar (sayfa içeriği dahil,
# Mart 2026 güncellemesi); 10'un üzerindeki her sonuç ayrıca ücretlenir.
# Bizim sorgular 15-25 sonuç istediği için EK SONUÇ kalemi baskındır.
# ============================================================
EXA_FIYAT = {
    "arama": 7.00 / 1000,      # $7 / 1.000 istek (ilk 10 sonuç dahil)
    "ek_sonuc": 1.00 / 1000,   # 10'un üzerindeki her sonuç için $1 / 1.000
}

# ============================================================
# KATEGORİ TAKSONOMİSİ (12)
# Kod → (Görünen ad, Öne Çıkanlar kota hedefi)
# ============================================================
KATEGORILER = {
    "politika":       {"ad": "Politika & Mevzuat",              "kota": 2},
    "biyoyakit":      {"ad": "Biyoyakıt & Biyoenerji",          "kota": 2},
    "biyomalzeme":    {"ad": "Biyobazlı Malzeme & Kimya",       "kota": 2},
    "biyomanufaktur": {"ad": "Biyomanüfaktür & Fermantasyon",   "kota": 1},
    "gida-protein":   {"ad": "Gıda & Alternatif Protein",       "kota": 1},
    "atik-donusum":   {"ad": "Atık Değerlendirme & Döngüsel",   "kota": 1},
    "tarim":          {"ad": "Tarım & Biostimulant",            "kota": 0},
    "karbon":         {"ad": "Biyokömür & Biyolojik Karbon",     "kota": 1},
    "deniz":          {"ad": "Deniz Biyoekonomisi & Alg",       "kota": 0},
    "uluslararasi":   {"ad": "Uluslararası Kuruluşlar",         "kota": 1},
    "turkiye":        {"ad": "Türkiye",                         "kota": 1},
    "rapor":          {"ad": "Rapor & Piyasa Verisi",           "kota": 1},
}

# ⚠ KOTA NEDEN VAR: Biyoyakıt/SAF ve alternatif protein anlaşma haberleri akışı
# domine edebilir. Kota olmadan bültenin yarısı SAF duyurusu olur.

# Değer zinciri etiketleri (site navigasyonunun omurgası)
# Biyoekonomi: hammaddeden (biyokütle) nihai ürüne uzanan zincir.
DEGER_ZINCIRI = [
    "biyokutle", "on-isleme", "donusum-fermantasyon",
    "urun-uretim", "kullanim", "atik-geri-donusum",
]

# ============================================================
# OLGUNLUK ÖLÇEĞİ — biyoekonomi projeleri için
# "Niyet mektubu" ile "ticari üretim" arasında uçurum var; biyobazlı
# tesislerde laboratuvardan ölçeklemeye geçiş en büyük sinyal-gürültü sorunudur.
# ============================================================
OLGUNLUK = [
    "research",        # araştırma / laboratuvar kavram kanıtı
    "pilot",           # pilot tesis
    "demonstration",   # demo / ön-ticari ölçek
    "announced",       # niyet/anlaşma duyuruldu
    "funded",          # finansman kapandı / nihai yatırım kararı (FID)
    "construction",    # tesis inşaatı sürüyor
    "commissioning",   # devreye alma
    "operational",     # ticari işletmede / üretim başladı
    "scaling",         # kapasite artışı / yeni hat
    "delayed",
    "cancelled",
]

# ============================================================
# KAYNAK KATMANLARI
# tier 1 = birincil (resmî kurum, şirket newsroom)
# tier 2 = güvenilir haber ajansı / sektör basını
# ============================================================
KAYNAK_TIER1 = [
    # AB kurumları
    "ec.europa.eu", "environment.ec.europa.eu",
    "single-market-economy.ec.europa.eu", "eur-lex.europa.eu",
    "cordis.europa.eu", "cbe.europa.eu",     # Circular Bio-based Europe JU
    # Uluslararası kuruluşlar
    "iea.org", "irena.org", "fao.org", "oecd.org", "worldbank.org",
    "iata.org", "unep.org", "ellenmacarthurfoundation.org",
    # ABD & ulusal kurumlar
    "energy.gov", "usda.gov", "epa.gov", "nrel.gov", "ornl.gov",
    "bioenergy.inl.gov", "gov.uk",
    # Sektör birlikleri
    "europabio.org", "bio.org", "worldbiogasassociation.org",
    "biofuels.org", "ebb-eu.org", "european-biogas.eu",
    "plasticseurope.org",
    # Şirket newsroom — biyoyakıt / biyobazlı üreticiler
    "neste.com", "totalenergies.com", "shell.com", "bp.com",
    "lanzatech.com", "lanzajet.com", "gevo.com", "amyris.com",
    "novonesis.com", "novozymes.com", "dsm-firmenich.com",
    "corbion.com", "cargill.com", "adm.com", "basf.com",
    "braskem.com", "avantium.com", "borregaard.com", "upmbiochemicals.com",
    "clariant.com", "genomatica.com", "solugen.com",
    "perfectday.com", "formonutrition.com", "airprotein.com",
    "vestas.com", "topsoe.com",
]

# ⚠ reuters.com ve bloomberg.com Exa'nın includeDomains filtresinde KABUL
# EDİLMİYOR (lisans kısıtı, 403). Listeye EKLEME — filtresiz aramalarda
# ve diğer sitelerin alıntılarında dolaylı yakalanıyor.
KAYNAK_TIER2 = [
    "biofuelsdigest.com", "bioenergy-news.com", "biomarketinsights.com",
    "renewable-carbon.eu", "bioplasticsnews.com", "bioplasticsmagazine.com",
    "biobasedpress.eu", "biofuelinternational.com", "ethanolproducer.com",
    "biodieselmagazine.com", "biomassmagazine.com", "labiotech.eu",
    "agfundernews.com", "greenqueen.com.hk", "foodnavigator.com",
    "foodingredientsfirst.com", "just-food.com", "vegconomist.com",
    "chemistryworld.com", "chemanager-online.com", "icis.com",
    "argusmedia.com", "spglobal.com", "montelnews.com",
    "euractiv.com", "edie.net", "sustainability-times.com",
    "greenbiz.com", "canarymedia.com", "cnbc.com", "ft.com",
    "asia.nikkei.com", "wsj.com",
]

KAYNAK_AKADEMIK = [
    "nature.com", "science.org", "cell.com", "arxiv.org", "biorxiv.org",
    "sciencedirect.com", "pubs.acs.org", "pnas.org", "onlinelibrary.wiley.com",
    "tandfonline.com", "mdpi.com", "frontiersin.org", "rsc.org",
]

KAYNAK_TURKIYE = [
    "sanayi.gov.tr", "enerji.gov.tr", "tarimorman.gov.tr", "ticaret.gov.tr",
    "tubitak.gov.tr", "tuba.gov.tr", "sbb.gov.tr", "resmigazete.gov.tr",
    "kalkinmaajanslari.gov.tr", "epdk.gov.tr", "cevre.gov.tr",
    "aa.com.tr", "dunya.com", "ekonomim.com", "bloomberght.com",
    "enerjigunlugu.net", "enerjiportali.com", "yesilekonomi.com",
    "tarimdanhaber.com", "gidahatti.com",
]

# ============================================================
# ÖDEME DUVARLI KAYNAKLAR
# Dışlanmazlar ama asla birincil kaynak olmazlar; tek kaynaklarsa olay
# yazılmaz, Radar'a düşer.
# ============================================================
KAYNAK_ODEME_DUVARI = [
    "ft.com", "wsj.com", "asia.nikkei.com", "economist.com",
    "argusmedia.com", "montelnews.com", "spglobal.com",
    "icis.com", "woodmac.com", "just-food.com",
]

ODEME_DUVARI_IZLERI = [
    "subscribe to read", "subscribers only", "members only",
    "sign in to continue", "log in to read", "register to continue",
    "this content is for", "paywall", "premium content",
    "abone olun", "üyelere özel", "içeriğin tamamını okumak",
]
ODEME_DUVARI_MIN_KARAKTER = 500   # bundan kısa metin → içi boş, duvarlı say

# ── TEYİT ARAMASI (corroboration search) ──────────────────
# Tüm kaynakları duvarlı olan olay için ikinci bir Exa araması yapılır;
# erişilebilir kaynak bulunursa olay "bildirildi" diliyle yazılabilir olur.
TEYIT = {
    "aktif": True,
    "max_olay": 12,
    "sonuc": 6,
    "min_benzerlik": 0.20,
    "min_ortak_kelime": 2,
    "min_metin": 700,
    "gun_toleransi": 3,
}

# Başlık karşılaştırmasında yok sayılacak kelimeler
DURAK_KELIMELER = {
    "the", "and", "for", "with", "from", "that", "this", "will", "have", "has",
    "into", "over", "amid", "says", "said", "new", "its", "not", "but", "are",
    "was", "were", "been", "more", "than", "after", "before", "report", "reports",
    "reportedly", "according", "sources", "source", "bio", "based", "biobased",
    "green", "sustainable", "renewable", "production", "company",
    "ile", "için", "olarak", "yeni", "bir", "bu", "de", "da", "ve",
}

# Asla kullanılmayacak / sponsorlu-SEO ağırlıklı kaynaklar
KAYNAK_DISLA = [
    "linkedin.com", "facebook.com", "x.com", "twitter.com", "reddit.com",
    "medium.com", "quora.com", "youtube.com", "pinterest.com",
    "prnewswire.com", "globenewswire.com", "businesswire.com",
    "marketresearchfuture.com", "marketsandmarkets.com",
    "researchandmarkets.com", "verifiedmarketresearch.com",
    "grandviewresearch.com", "fortunebusinessinsights.com",
    "openpr.com", "einpresswire.com", "issuewire.com",
]

# ============================================================
# EXA SORGULARI (12)
# Kısa semantik sorgu + ayrı parametreler. Uzun doğal dil komutu YAZILMAZ.
# ============================================================
SORGULAR = [
    {
        "id": "politika",
        "kategori": "politika",
        "sorgu": "bioeconomy strategy policy and regulation",
        "ek_sorgular": [
            "EU bioeconomy strategy bio-based economy regulation",
            "ESPR biobased requirement RED III biomass mandate decision",
            "EU Biotech Act sustainable carbon cycle policy",
            "biofuel blending mandate sustainable aviation fuel policy",
        ],
        "domain_seti": ["tier1", "tier2"],
        "sonuc": 25,
    },
    {
        "id": "biyoyakit",
        "kategori": "biyoyakit",
        "sorgu": "sustainable aviation fuel biofuel and biomethane project",
        "ek_sorgular": [
            "SAF sustainable aviation fuel plant offtake agreement investment",
            "biomethane biogas renewable natural gas facility",
            "renewable diesel HVO bioethanol production capacity",
            "green hydrogen from biomass bio-LNG project",
        ],
        "domain_seti": ["tier1", "tier2"],
        "sonuc": 25,
    },
    {
        "id": "biyomalzeme",
        "kategori": "biyomalzeme",
        "sorgu": "bioplastics and bio-based chemicals commercial launch",
        "ek_sorgular": [
            "bioplastic PLA PHA biopolymer new facility production",
            "bio-based chemicals lignin valorization cellulose materials",
            "bio-based textile construction material commercial",
            "biodegradable packaging bio-based coating investment",
        ],
        "domain_seti": ["tier1", "tier2"],
        "sonuc": 25,
    },
    {
        "id": "biyomanufaktur",
        "kategori": "biyomanufaktur",
        "sorgu": "industrial biotechnology and precision fermentation scale-up",
        "ek_sorgular": [
            "biomanufacturing precision fermentation commercial facility funding",
            "industrial enzymes synthetic biology commercial scale",
            "fermentation bioreactor capacity expansion milestone",
        ],
        "domain_seti": ["tier1", "tier2", "akademik"],
        "sonuc": 20,
    },
    {
        "id": "gida-protein",
        "kategori": "gida-protein",
        "sorgu": "alternative protein and precision fermentation food",
        "ek_sorgular": [
            "alternative protein mycoprotein algae protein commercial deal",
            "precision fermentation dairy protein regulatory approval",
            "cultivated meat fermentation food ingredient scale-up",
        ],
        "domain_seti": ["tier1", "tier2"],
        "sonuc": 20,
    },
    {
        "id": "atik-donusum",
        "kategori": "atik-donusum",
        "sorgu": "circular bioeconomy waste to value biorefinery",
        "ek_sorgular": [
            "agri-food waste valorization high-value product biorefinery",
            "circular bioeconomy residue feedstock project investment",
            "food waste to bioplastic chemical facility",
        ],
        "domain_seti": ["tier1", "tier2"],
        "sonuc": 20,
    },
    {
        "id": "tarim",
        "kategori": "tarim",
        "sorgu": "biostimulant biopesticide and agricultural biologicals",
        "ek_sorgular": [
            "biostimulant biopesticide regulatory approval commercial launch",
            "agricultural biologicals microbial seed treatment deal",
        ],
        "domain_seti": ["tier1", "tier2", "akademik"],
        "sonuc": 15,
    },
    {
        # ⚠ ODAK: yalnızca BİYOLOJİK/biyobazlı karbon. Jenerik "carbon capture"
        # (CCS) ve karbon PİYASASI (ETS/kredi) BİLEREK dışarıda — Exa semantik
        # aramada bu ifadeler ETS/COP gürültüsü çekiyordu. Triyaj promptu da
        # karbon piyasası/iklim politikasını ayrıca eler.
        "id": "karbon",
        "kategori": "karbon",
        "sorgu": "biochar and biological CO2 conversion to products",
        "ek_sorgular": [
            "gas fermentation microbial CO2 to fuel or chemical commercial plant",
            "biochar production facility investment biomass carbon",
            "CO2-based materials biomanufacturing bioconversion deployment",
        ],
        "domain_seti": ["tier1", "tier2"],
        "sonuc": 15,
    },
    {
        "id": "deniz",
        "kategori": "deniz",
        "sorgu": "marine bioeconomy seaweed and algae industrial cultivation",
        "ek_sorgular": [
            "seaweed algae cultivation industrial use commercial project",
            "marine biomass ocean-based bioeconomy regulation",
        ],
        "domain_seti": ["tier1", "tier2", "akademik"],
        "sonuc": 15,
    },
    {
        "id": "uluslararasi",
        "kategori": "uluslararasi",
        "sorgu": "bioeconomy and bioenergy outlook report",
        "ek_sorgular": [
            "IEA IRENA FAO OECD bioenergy bioeconomy report forecast",
            "World Bank IATA biofuel sustainable fuel data outlook",
        ],
        "domain_seti": ["tier1", "tier2"],
        "sonuc": 15,
    },
    {
        "id": "turkiye",
        "kategori": "turkiye",
        "sorgu": "Türkiye biyoekonomi biyoyakıt biyogaz gelişme yatırım",
        "ek_sorgular": [
            "Türkiye biyoplastik biyobazlı kimya atıktan değer yatırım",
            "Türkiye SAF sürdürülebilir havacılık yakıtı biyometan tesis",
            "Türkiye alternatif protein döngüsel ekonomi mevzuat teşvik",
            "Turkey bioeconomy biofuel biogas investment plant",
        ],
        "domain_seti": ["turkiye", "tier1", "tier2"],
        "sonuc": 25,
        "kullanici_konumu": "tr",
    },
    {
        "id": "asya-global",
        "kategori": "rapor",
        "sorgu": "bioeconomy biomanufacturing news Asia and United States",
        "ek_sorgular": [
            "China Japan South Korea bioeconomy biomanufacturing investment policy",
            "United States bio-based technology biofuel corporate investment",
        ],
        "domain_seti": ["tier1", "tier2"],
        "sonuc": 15,
    },
]
