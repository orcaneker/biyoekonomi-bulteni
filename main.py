#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
BİYOEKONOMİ BÜLTENİ — Otomatik Haftalık Üretim Scripti
========================================================
Akış:
1. sistem-prompt-final.txt dosyasını okur
2. Perplexity API ile haberleri arar (her sorgu ayrı)
3. Claude API ile haberleri işler (seç, Türkçeleştir, puanla, kategorize et)
4. HTML bülteni üretir (şablon + görseller)
5. Netlify'a yükler
6. Sana e-posta raporu gönderir

Çalıştırma: python main.py
Gerekli ortam değişkenleri (GitHub Secrets):
  PERPLEXITY_API_KEY, ANTHROPIC_API_KEY,
  NETLIFY_TOKEN, NETLIFY_SITE_ID,
  GMAIL_USER, GMAIL_APP_PASSWORD
"""

import os
import re
import json
import base64
import smtplib
import datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

import requests

# .env dosyasından API anahtarlarını yükle (PythonAnywhere için)
def load_env_file():
    env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
    if os.path.exists(env_path):
        with open(env_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, _, value = line.partition("=")
                    os.environ.setdefault(key.strip(), value.strip())

load_env_file()

# ============================================================
# AYARLAR — Ortam değişkenlerinden okunur (GitHub Secrets)
# ============================================================
PERPLEXITY_API_KEY = os.environ.get("PERPLEXITY_API_KEY", "")
ANTHROPIC_API_KEY  = os.environ.get("ANTHROPIC_API_KEY", "")
NETLIFY_TOKEN      = os.environ.get("NETLIFY_TOKEN", "")
NETLIFY_SITE_ID    = os.environ.get("NETLIFY_SITE_ID", "")
GMAIL_USER         = os.environ.get("GMAIL_USER", "")
GMAIL_APP_PASSWORD = os.environ.get("GMAIL_APP_PASSWORD", "")

PERPLEXITY_URL = "https://api.perplexity.ai/chat/completions"
ANTHROPIC_URL  = "https://api.anthropic.com/v1/messages"

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROMPT_FILE = os.path.join(SCRIPT_DIR, "sistem-prompt-final.txt")
TEMPLATE_FILE = os.path.join(SCRIPT_DIR, "sablon.html")
IMAGES_DIR = os.path.join(SCRIPT_DIR, "gorseller")


# ============================================================
# 1. SİSTEM PROMPT DOSYASINI OKU
# ============================================================
def load_config():
    """sistem-prompt-final.txt dosyasını okuyup sorguları ve ayarları çıkarır."""
    with open(PROMPT_FILE, "r", encoding="utf-8") as f:
        content = f.read()

    # Perplexity sorgularını çıkar (id: ve sorgu: satırları)
    queries = []
    current_id = None
    current_query_lines = []
    in_query = False

    for line in content.splitlines():
        stripped = line.strip()
        id_match = re.match(r"^- id:\s*(\w+)", stripped)
        if id_match:
            if current_id and current_query_lines:
                queries.append({"id": current_id, "query": " ".join(current_query_lines).strip()})
            current_id = id_match.group(1)
            current_query_lines = []
            in_query = False
        elif stripped.startswith("sorgu:"):
            in_query = True
        elif in_query and stripped and not stripped.startswith("- id:") and not stripped.startswith("aciklama:"):
            # Sorgu içeriği (çok satırlı)
            if stripped.startswith(">") or stripped.startswith("|"):
                continue
            current_query_lines.append(stripped)
        elif stripped.startswith("aciklama:"):
            in_query = False

    if current_id and current_query_lines:
        queries.append({"id": current_id, "query": " ".join(current_query_lines).strip()})

    # Claude sistem promptunu çıkar
    claude_prompt = ""
    if "CLAUDE_SISTEM_PROMPTU:" in content:
        after = content.split("CLAUDE_SISTEM_PROMPTU:", 1)[1]
        # Bir sonraki BÖLÜM'e kadar al
        claude_prompt = after.split("# ===")[0].replace(">", "", 1).strip()

    # E-posta adresini çıkar
    email_to = ""
    email_match = re.search(r"alici:\s*\"?([^\"\n]+)\"?", content)
    if email_match:
        email_to = email_match.group(1).strip().strip('"')

    return {
        "queries": queries,
        "claude_prompt": claude_prompt,
        "email_to": email_to,
    }


# ============================================================
# 2. PERPLEXITY İLE HABERLERİ ARA
# ============================================================
def fetch_url_content(url, max_chars=2500):
    """URL iceriğini gercekten fetch eder. Acilamazsa None doner."""
    try:
        hdrs = {"User-Agent": "Mozilla/5.0 (compatible; NewsBot/1.0)"}
        r = requests.get(url, headers=hdrs, timeout=15, allow_redirects=True)
        if r.status_code != 200:
            return None
        import re as _re
        text = r.text
        text = _re.sub(r"<script[^>]*>.*?</script>", " ", text, flags=_re.DOTALL|_re.IGNORECASE)
        text = _re.sub(r"<style[^>]*>.*?</style>", " ", text, flags=_re.DOTALL|_re.IGNORECASE)
        text = _re.sub(r"<[^>]+>", " ", text)
        text = _re.sub(r"[ \t]+", " ", text).strip()
        text = "\n".join(ln for ln in text.splitlines() if ln.strip())
        return text[:max_chars] if text else None
    except Exception as e:
        return None




def page_is_recent(page_text, url):
    """Sayfanin guncel (2026) olup olmadigini kaba sekilde kontrol eder.
    Eski yil (2017-2024) iceren ve 2026 icermeyen sayfalari eler."""
    import re as _re
    # URL de eski yil varsa direkt ele
    eski_yillar = ["2017", "2018", "2019", "2020", "2021", "2022", "2023", "2024"]
    # URL icinde /2017/ /2018/ gibi tarih varsa ele
    for yil in eski_yillar:
        if f"/{yil}/" in url:
            return False
    # Sayfa metninde 2026 var mi?
    has_2026 = "2026" in page_text
    has_2025_recent = "2025" in page_text
    # 2026 veya 2025 varsa kabul (yakin tarih)
    if has_2026 or has_2025_recent:
        return True
    # Hic 2025/2026 yok, ama eski yil var mi?
    for yil in eski_yillar:
        if yil in page_text:
            return False  # Eski yil var, guncel yok -> ele
    # Hicbir yil yok -> belirsiz, kabul et (Claude tarih kontrolu yapacak)
    return True


def search_perplexity(query_text):
    """Perplexity sonar-pro ile arama yapar. Hem ozet metin hem gercek citations doner."""
    hdrs = {"Authorization": f"Bearer {PERPLEXITY_API_KEY}", "Content-Type": "application/json"}
    payload = {
        "model": "sonar-pro",
        "search_recency_filter": "week",
        "messages": [
            {
                "role": "system",
                "content": (
                    "You are a bioeconomy news assistant. "
                    "Find ONLY developments published in the LAST 7-14 DAYS. "
                    "Ignore old articles, archive pages, and evergreen content. "
                    "Be factual, include publication dates and figures. "
                    "Do NOT invent URLs - your citations will be verified."
                )
            },
            {"role": "user", "content": query_text},
        ],
        "max_tokens": 2000,
    }
    try:
        r = requests.post(PERPLEXITY_URL, headers=hdrs, json=payload, timeout=60)
        r.raise_for_status()
        data = r.json()
        text = data["choices"][0]["message"]["content"]
        citations = data.get("citations", [])
        if not citations:
            citations = data["choices"][0].get("citations", [])
        return text, citations
    except Exception as e:
        print(f"  ! Perplexity hatasi: {e}")
        return "", []


def is_list_or_index_page(url):
    """Liste/duyuru/index sayfasi mi kontrol eder (spesifik makale degil)."""
    u = url.lower().rstrip("/")
    # Bu kaliplarla BITEN URL ler liste sayfasidir, spesifik makale degil
    list_endings = [
        "/news", "/press-releases", "/press", "/events", "/blog",
        "/media", "/publications", "/articles", "/updates", "/newsroom",
        "/press-corner", "/all-news", "/category", "/tag", "/topics"
    ]
    for ending in list_endings:
        if u.endswith(ending):
            return True
    return False


def gather_all_news(queries):
    """Tum sorgulari calistirir. Her sayfayi NUMARALI olarak kendi URL siyle dondurur.
    Claude URL secmez - sadece KAYNAK_NO verir, biz gercek URL yi koyariz."""
    all_summaries = []
    all_citations = []

    for q in queries:
        print(f"  -> Sorgu: {q['id']}")
        ptext, citations = search_perplexity(q["query"])
        if ptext:
            all_summaries.append(f"[GENEL OZET - {q['id']}]\n{ptext[:1200]}")
        for c in citations:
            if c not in all_citations:
                all_citations.append(c)

    print(f"  Perplexity {len(all_citations)} gercek kaynak URL donurdu.")

    SOSYAL = ["instagram.com", "twitter.com", "x.com", "facebook.com",
              "linkedin.com", "youtube.com", "tiktok.com"]

    # url_map: numara -> gercek URL  (Claude bu numarayi kullanacak)
    url_map = {}
    fetched_blocks = []
    kaynak_no = 0

    for url in all_citations[:25]:
        if any(s in url.lower() for s in SOSYAL):
            print(f"    - Atlandi (sosyal medya): {url[:50]}")
            continue
        if is_list_or_index_page(url):
            print(f"    - Atlandi (liste/duyuru sayfasi): {url[:50]}")
            continue
        print(f"    Fetch: {url[:65]}...")
        page = fetch_url_content(url, max_chars=2200)
        if page and len(page) > 150:
            # ESKI TARIH FILTRESI: sayfada 2026 yoksa ama eski yillar varsa ele
            if not page_is_recent(page, url):
                print(f"    - Atlandi (eski tarihli icerik): {url[:50]}")
                continue
            kaynak_no += 1
            url_map[kaynak_no] = url
            fetched_blocks.append(
                f"===== KAYNAK_NO: {kaynak_no} =====\n"
                f"URL: {url}\n"
                f"ICERIK:\n{page}\n"
            )
        else:
            print(f"    ! Acilamadi/bos, atlandi.")

    print(f"  {kaynak_no} kaynak basariyla okundu ve numaralandi.")

    # Genel ozetler + numarali kaynak sayfalari
    summary_block = "\n\n".join(all_summaries)
    sources_block = "\n".join(fetched_blocks)

    combined = (
        "BOLUM 1 - GENEL OZETLER (sadece baglamsal bilgi, URL kaynagi DEGIL):\n"
        + summary_block
        + "\n\n========================================\n"
        + "BOLUM 2 - NUMARALI KAYNAK SAYFALARI (haberler SADECE buradan cikarilacak):\n\n"
        + sources_block
    )

    if len(combined) > 40000:
        combined = combined[:40000] + "\n[veri kisaltildi]"
    print(f"  Toplam ham veri: {len(combined)} karakter")

    return combined, url_map




def is_valid_article_url(url):
    """URL nin spesifik makale linki olup olmadigini kontrol eder."""
    if not url or url == "#":
        return False
    url = url.strip().lower()
    if not url.startswith("http"):
        return False
    social = ["instagram.com", "twitter.com", "x.com", "facebook.com",
              "linkedin.com", "youtube.com", "tiktok.com", "t.me"]
    if any(s in url for s in social):
        return False
    from urllib.parse import urlparse
    try:
        parsed = urlparse(url)
        path = parsed.path.strip("/")
    except Exception:
        return False
    if len(path) < 8:
        return False
    return True


def parse_claude_blocks(text, url_map):
    """Claude dan gelen ##HABER## blok formatini parse eder."""
    import datetime as _dt
    haberler = []
    used_kaynak_no = set()
    blocks = text.split("##HABER_BASLANGIC##")
    for block in blocks[1:]:
        if "##HABER_BITIS##" not in block:
            continue
        block = block.split("##HABER_BITIS##")[0].strip()
        h = {}
        lines = block.splitlines()
        i = 0
        while i < len(lines):
            line = lines[i].strip()
            if line.startswith("BASLIK:"):
                h["title"] = line[7:].strip()
            elif line.startswith("OZET:"):
                h["excerpt"] = line[5:].strip()
            elif line.startswith("DETAY:"):
                detay_lines = [line[6:].strip()]
                i += 1
                while i < len(lines):
                    nxt = lines[i].strip()
                    if nxt.startswith(("KAYNAK:", "URL:", "KATEGORI:", "TARIH:", "ONCELIK:", "OZET:", "BASLIK:")):
                        i -= 1
                        break
                    if nxt:
                        detay_lines.append(nxt)
                    i += 1
                h["detail_raw"] = "\n".join(detay_lines).strip()
            elif line.startswith("KAYNAK:"):
                h["source"] = line[7:].strip()
            elif line.startswith("KAYNAK_NO:"):
                no_str = line[10:].strip()
                try:
                    h["kaynak_no"] = int("".join(ch for ch in no_str if ch.isdigit()))
                except (ValueError, TypeError):
                    h["kaynak_no"] = None
            elif line.startswith("KATEGORI:"):
                cat = line[9:].strip().lower()
                valid = ["mevzuat", "piyasa", "teknoloji", "uluslararasi", "haber", "akademik"]
                h["category"] = cat if cat in valid else "haber"
            elif line.startswith("TARIH:"):
                h["date"] = line[6:].strip()
            elif line.startswith("ONCELIK:"):
                h["priority"] = line[8:].strip()
            i += 1

        if h.get("title"):
            # KAYNAK_NO dan gercek URL yi bul (Claude URL secemez, biz koyariz)
            kno = h.get("kaynak_no")
            if kno is None or kno not in url_map:
                print(f"  - Elendi (gecersiz KAYNAK_NO {kno}): {h.get('title','')[:45]}")
                continue
            if kno in used_kaynak_no:
                print(f"  - Elendi (tekrar KAYNAK_NO {kno}): {h.get('title','')[:45]}")
                continue
            used_kaynak_no.add(kno)
            h["url"] = url_map[kno]
            raw = h.get("detail_raw", h.get("excerpt", ""))
            paragraphs = [p.strip() for p in raw.split("\n") if p.strip()]
            if not paragraphs:
                paragraphs = [raw] if raw else [h.get("excerpt", "")]
            h["detail"] = "".join(f"<p>{p}</p>" for p in paragraphs[:6])
            haberler.append(h)

    if not haberler:
        print("  ! Hic haber parse edilemedi, fallback kullaniliyor")
        return {
            "lead": {
                "title": "Bulten bu hafta uretilemedi",
                "excerpt": "Parse hatasi - loglari kontrol edin.",
                "detail": "<p>Teknik hata olustu.</p>",
                "source": "Sistem", "url": "#",
                "category": "haber",
                "date": str(_dt.date.today())
            },
            "stories": [],
            "rapor": {"bulunan_toplam": 0, "elenen": 0, "yayinlanan": 0, "pencere": "hata"}
        }

    # ONCELIK 1 olan lead olsun
    lead = None
    stories = []
    for h in haberler:
        if h.get("priority") == "1" and lead is None:
            lead = h
        else:
            stories.append(h)
    if lead is None:
        lead = haberler[0]
        stories = haberler[1:]
    stories = stories[:13]

    print(f"  {1 + len(stories)} haber basariyla parse edildi.")
    return {
        "lead": lead,
        "stories": stories,
        "rapor": {
            "bulunan_toplam": len(haberler),
            "elenen": max(0, len(haberler) - 1 - len(stories)),
            "yayinlanan": 1 + len(stories),
            "pencere": "7-14 gun"
        }
    }

def process_with_claude(raw_news, claude_prompt, url_map):
    """Ham haberleri Claude'a gönderir, işlenmiş JSON döner."""
    today = datetime.date.today()
    week_ago = today - datetime.timedelta(days=7)

    full_prompt = f"""{claude_prompt}

BUGÜNÜN TARİHİ: {today.strftime('%d %B %Y')}
ÖNCELİKLİ PENCERE: {week_ago.strftime('%d %B %Y')} - {today.strftime('%d %B %Y')}

Asagida iki tur veri var:
1. [ALAN: ...] bloklari: Perplexity ozet metinleri
2. [KAYNAK_URL: https://...] bloklari: Gercekten fetch edilmis web sayfasi icerikleri

ONEMLI: KAYNAK_URL bloklarindaki URL ler GERCEK ve DOGRULANMIS kaynaklardir.
Bu URL leri haber icin URL alani olarak kullan.
Haberleri bu gercek iceriklere dayandır, UYDURMA.

Ham veri:

{raw_news}

CIKTI FORMATI - Her haber icin su blok yapısını kullan, JSON DEGIL:
##HABER_BASLANGIC##
BASLIK: [aciklayici haber basligi, 10-15 kelime]
OZET: [2-3 cumlelik kisa ozet, kartta gorunecek]
DETAY: [En az 4 paragraf, her paragraf 3-5 cumle. Gelismenin tum detaylarini, rakamlari, tarihleri, ilgili kurumlari ve baglami acikla. Her paragrafi yeni satirda yaz.]
KAYNAK: [kaynak adi ve tarih]
KAYNAK_NO: [bu haberin cikarildigi sayfanin KAYNAK_NO numarasi - SADECE numara yaz]
KATEGORI: [mevzuat veya piyasa veya teknoloji veya uluslararasi veya haber veya akademik]
TARIH: [YYYY-MM-DD formatinda]
ONCELIK: [1=manset, 2=normal]
##HABER_BITIS##

ZORUNLU KURALLAR (KESINLIKLE UYULACAK):

KAYNAK KURALI (EN ONEMLI):
- Haberleri SADECE "BOLUM 2 - NUMARALI KAYNAK SAYFALARI" icindeki sayfalardan cikar.
- Her haber icin KAYNAK_NO alanina, haberin cikarildigi sayfanin numarasini yaz.
- BOLUM 1 (genel ozetler) SADECE baglam icindir; oradan haber cikarma, URL alma.
- Bir sayfadan haber cikariyorsan, o sayfanin KAYNAK_NO numarasini DOGRU yaz.
KAYNAK KURALI (EN ONEMLI):
- Haberleri SADECE "BOLUM 2 - NUMARALI KAYNAK SAYFALARI" icindeki sayfalardan cikar.
- Her haber icin KAYNAK_NO alanina, haberin cikarildigi sayfanin numarasini yaz.
- BOLUM 1 (genel ozetler) SADECE baglam icindir; oradan haber cikarma, URL alma.
- Bir sayfadan haber cikariyorsan, o sayfanin KAYNAK_NO numarasini DOGRU yaz.
- Ayni KAYNAK_NO yu birden fazla habere verme (her sayfa bir habere karsilik gelir).
- Liste sayfasi veya genel tanitim sayfasindan (orn: sirket "hakkinda" sayfasi)
  haber CIKARMA - sayfada somut, tarihli bir gelisme/bilgi olmasi sart.

ETKINLIK VE TAKVIM HABERLERI (ONEMLI - DIKKATLI OKU):
- Fuar, konferans, kongre gibi etkinlik haberleri GECERLI haber konusudur,
  DAHIL EDILEBILIR. Etkinligi haber yapmaktan KACINMA.
- TEK KURAL: Sayfada ne yaziyorsa O ZAMAN KIPINI KULLAN. Baska hicbir sey
  degistirme.
  * Sayfa "etkinlik 24-26 Haziran'da duzenlenecek" diyorsa: SEN DE gelecek
    zaman kullan ("duzenlenecek", "ele alinacak", "bir araya getirecek").
  * Sayfa "etkinlik duzenlendi, sunlar konusuldu" diyorsa: SEN DE gecmis
    zaman kullan ("duzenlendi", "ele alindi").
  * Sayfada sadece etkinlik programi/gundemi varsa (henuz sonuc yok):
    "sunlar ele alinacak/tartisilacak" gibi yaz, "sunlar tartisildi/
    sonucuna varildi" gibi YAZMA.
- YASAK: Sayfada olmayan bir sonuc, karar veya cikti UYDURMA. Sayfa sadece
  "program" veya "gundem" veriyorsa, sen de sadece program/gundemi aktar.

YORUM YASAGI:
- KESINLIKLE kendi yorumunu, cikariminizi veya sonucunu EKLEME.
- Su cumleler YASAK: "...yansitiyor", "...gosteriyor", "...one cikiyor",
  "...isaret ediyor", "...vurguluyor", "Bu gelisme...".
- Sadece kaynakta ACIKCA yazilan bilgileri aktar.

BIRLESTIRME YASAGI:
- Iki AYRI gelismeyi tek haberde BIRLESTIRME.
- Biyoekonomi ile DOGRUDAN ilgili olmayan haberleri DAHIL ETME.
- Suphede kaldiginda haberi dahil etme (az ama dogru daha iyi).

TARIH KURALI (COK ONEMLI):
- Her sayfanin ICERIGINDE gercek yayin/duyuru tarihini ARA ve bul.
- Sayfada acik bir tarih varsa onu TARIH alanina yaz (YYYY-MM-DD).
- Sayfada tarih BULAMIYORSAN, TARIH alanina "belirtilmemis" yaz. ASLA bugunun
  tarihini veya tahmini tarih UYDURMA.
- Eger sayfa 2025 veya daha eski bir YAYIN tarihi tasiyorsa (orn: 2017,
  2023), o haberi KESINLIKLE DAHIL ETME. (Not: gelecege donuk bir etkinligin
  2026 icinde gerceklesecek olmasi bu kuralla CELISMEZ - burada bahsedilen
  sayfanin YAYINLANMA tarihidir, etkinligin gerceklesme tarihi degil.)
- Bir sayfanin eski oldugundan suphelenirsen, dahil etme.

ICERIK:
- Turkiye ile ilgili en onemli haberi ONCELIK:1 yap.
- Her gercek kaynak sayfasindan en fazla 1 haber cikar.
- DETAY bolumu kaynaktaki bilgilerle DOLU olmali: 3-4 paragraf, sadece olgular.
- Her DETAY paragrafini ayri satirda yaz.
- Sadece GERCEKTEN biyoekonomi ile ilgili, GUNCEL ve KAYNAGI DOGRULANMIS
  haberleri ver. Az ama kesin dogru haber, cok ama suvpheli haberden iyidir."""

    headers = {
        "x-api-key": ANTHROPIC_API_KEY,
        "anthropic-version": "2023-06-01",
        "content-type": "application/json",
    }
    payload = {
        "model": "claude-sonnet-5",
        "max_tokens": 8000,
        "temperature": 0,
        "messages": [{"role": "user", "content": full_prompt}],
    }
    try:
        r = requests.post(ANTHROPIC_URL, headers=headers, json=payload, timeout=300)
        r.raise_for_status()
        data = r.json()
        text = "".join(block.get("text", "") for block in data["content"] if block.get("type") == "text")
        print(f"  Claude yanit uzunlugu: {len(text)} karakter")
        return parse_claude_blocks(text, url_map)
    except Exception as e:
        print(f"  ! Claude API hatasi: {e}")
        raise


# ============================================================
# 4. HTML ÜRET
# ============================================================
def img_to_base64(filename):
    """Görseli base64 data URI'ye çevirir. Yoksa boş döner."""
    path = os.path.join(IMAGES_DIR, filename)
    if not os.path.exists(path):
        return ""
    with open(path, "rb") as f:
        return "data:image/png;base64," + base64.b64encode(f.read()).decode()


def build_html(processed):
    """İşlenmiş haberlerden HTML bülteni üretir."""
    with open(TEMPLATE_FILE, "r", encoding="utf-8") as f:
        template = f.read()

    today = datetime.date.today()
    week_ago = today - datetime.timedelta(days=7)
    tr_months = ["", "Ocak", "Şubat", "Mart", "Nisan", "Mayıs", "Haziran",
                 "Temmuz", "Ağustos", "Eylül", "Ekim", "Kasım", "Aralık"]
    date_range = f"{week_ago.day} – {today.day} {tr_months[today.month]} {today.year}"

    # Görselleri yükle
    logo_src = img_to_base64("logo.png")
    banner_src = img_to_base64("banner.png")
    cat_images = {
        "mevzuat": img_to_base64("mevzuat.png"),
        "piyasa": img_to_base64("piyasa.png"),
        "teknoloji": img_to_base64("teknoloji.png"),
        "uluslararasi": img_to_base64("uluslararasi.png"),
        "haber": img_to_base64("haber.png"),
        "akademik": img_to_base64("akademik.png"),
    }

    cat_labels = {
        "mevzuat": "Mevzuat & Politika",
        "piyasa": "Piyasa & Yatırım",
        "teknoloji": "Teknoloji & Ar-Ge",
        "uluslararasi": "Uluslararası Kuruluşlar",
        "haber": "Haber & Basın",
        "akademik": "Akademik",
    }

    lead = processed["lead"]
    stories = processed["stories"]
    total = 1 + len(stories)

    # Image store (gizli) — kategorilere göre
    img_store = ""
    for cat, src in cat_images.items():
        if src:
            img_store += f'<img id="img-{cat}" src="{src}" alt="">\n'

    # Lead HTML
    lead_cat = lead.get("category", "haber")
    lead_img = cat_images.get(lead_cat, "")
    lead_visual = ""
    if lead_img:
        lead_visual = f'<div class="lead-visual"><img src="{lead_img}" alt=""/><div class="lead-visual-overlay"></div></div>'

    # Stories JS data
    stories_js = {"hero": {
        "cat": lead_cat,
        "title": lead.get("title", ""),
        "src": lead.get("source", "") + (" · " + lead.get("date", "") if lead.get("date") else ""),
        "lead": lead.get("excerpt", ""),
        "detail": lead.get("detail", ""),
        "url": lead.get("url", "#"),
        "imgId": f"img-{lead_cat}" if lead_img else None,
    }}

    stories_html = ""
    for i, s in enumerate(stories):
        key = f"s{i}"
        scat = s.get("category", "haber")
        clabel = cat_labels.get(scat, "Haber & Basın")
        stories_html += f'''
    <article class="story" data-cat="{scat}" onclick="openModal('{key}')">
      <div class="story-cat cat-{scat}">{clabel}</div>
      <h2 class="story-title">{s.get("title","")}</h2>
      <p class="story-excerpt">{s.get("excerpt","")}</p>
      <div class="story-meta"><span class="story-src">{s.get("source","")}</span><span class="story-arrow">→</span></div>
    </article>'''
        stories_js[key] = {
            "cat": scat,
            "title": s.get("title", ""),
            "src": s.get("source", "") + (" · " + s.get("date", "") if s.get("date") else ""),
            "lead": s.get("excerpt", ""),
            "detail": s.get("detail", ""),
            "url": s.get("url", "#"),
            "imgId": f"img-{scat}" if cat_images.get(scat) else None,
        }

    # Şablondaki yer tutucuları doldur
    html = template
    html = html.replace("{{LOGO_SRC}}", logo_src)
    html = html.replace("{{BANNER_SRC}}", banner_src)
    html = html.replace("{{IMG_STORE}}", img_store)
    html = html.replace("{{DATE_RANGE}}", date_range)
    html = html.replace("{{NEWS_COUNT}}", str(total))
    html = html.replace("{{LEAD_CAT}}", lead_cat)
    html = html.replace("{{LEAD_CAT_LABEL}}", cat_labels.get(lead_cat, ""))
    html = html.replace("{{LEAD_TITLE}}", lead.get("title", ""))
    html = html.replace("{{LEAD_EXCERPT}}", lead.get("excerpt", ""))
    html = html.replace("{{LEAD_SRC}}", stories_js["hero"]["src"])
    html = html.replace("{{LEAD_VISUAL}}", lead_visual)
    html = html.replace("{{STORIES_HTML}}", stories_html)
    html = html.replace("{{STORIES_JS}}", json.dumps(stories_js, ensure_ascii=False))

    return html


# ============================================================
# 5. NETLIFY'A YÜKLE
# ============================================================
def deploy_to_netlify(html):
    """HTML'i Netlify sitesine deploy eder."""
    import hashlib

    # Netlify file digest deploy yöntemi
    content = html.encode("utf-8")
    sha1 = hashlib.sha1(content).hexdigest()

    headers = {"Authorization": f"Bearer {NETLIFY_TOKEN}", "Content-Type": "application/json"}
    deploy_payload = {"files": {"/index.html": sha1}}

    r = requests.post(
        f"https://api.netlify.com/api/v1/sites/{NETLIFY_SITE_ID}/deploys",
        headers=headers, json=deploy_payload, timeout=60,
    )
    r.raise_for_status()
    deploy = r.json()
    deploy_id = deploy["id"]

    # Dosyayı yükle
    upload_headers = {"Authorization": f"Bearer {NETLIFY_TOKEN}", "Content-Type": "application/octet-stream"}
    up = requests.put(
        f"https://api.netlify.com/api/v1/deploys/{deploy_id}/files/index.html",
        headers=upload_headers, data=content, timeout=60,
    )
    up.raise_for_status()
    return deploy.get("ssl_url") or deploy.get("url", "")


# ============================================================
# 6. E-POSTA RAPORU GÖNDER
# ============================================================
def send_report(email_to, rapor, lead, stories, site_url):
    """Sana özel istatistik raporunu e-posta ile gönderir."""
    if not (GMAIL_USER and GMAIL_APP_PASSWORD and email_to):
        print("  ! E-posta ayarları eksik, rapor gönderilmedi.")
        return

    today = datetime.date.today()
    top3 = [lead] + stories[:2]
    top3_text = "\n".join(f"  {i+1}. {s.get('title','')}" for i, s in enumerate(top3))

    body = f"""Biyoekonomi Bülteni — {today.strftime('%d.%m.%Y')} Çalışma Raporu
─────────────────────────────────
Bulunan toplam haber: {rapor.get('bulunan_toplam','?')}
Mükerrer/elenen: {rapor.get('elenen','?')}
Bültene giren: {rapor.get('yayinlanan', 1 + len(stories))}
Tarama penceresi: {rapor.get('pencere','7 gün')}
─────────────────────────────────
En önemli 3 haber:
{top3_text}
─────────────────────────────────
Bülten yayında: {site_url}
"""

    msg = MIMEMultipart()
    msg["From"] = GMAIL_USER
    msg["To"] = email_to
    msg["Subject"] = f"Biyoekonomi Bülteni — Haftalık Çalışma Raporu ({today.strftime('%d.%m.%Y')})"
    msg.attach(MIMEText(body, "plain", "utf-8"))

    try:
        server = smtplib.SMTP("smtp.gmail.com", 587)
        server.starttls()
        server.login(GMAIL_USER, GMAIL_APP_PASSWORD)
        server.send_message(msg)
        server.quit()
        print("  ✓ Rapor e-postası gönderildi.")
    except Exception as e:
        print(f"  ! E-posta hatası: {e}")


# ============================================================
# ANA AKIŞ
# ============================================================
def main():
    print("═══ BİYOEKONOMİ BÜLTENİ — Otomatik Üretim ═══\n")

    print("1. Yapılandırma okunuyor...")
    config = load_config()
    print(f"   {len(config['queries'])} sorgu bulundu.\n")

    print("2. Perplexity ile haberler aranıyor...")
    raw_news, url_map = gather_all_news(config["queries"])
    print(f"   Ham veri toplandı ({len(raw_news)} karakter, {len(url_map)} kaynak).\n")

    print("3. Claude ile işleniyor...")
    processed = process_with_claude(raw_news, config["claude_prompt"], url_map)
    rapor = processed.get("rapor", {})
    print(f"   {rapor.get('yayinlanan','?')} haber seçildi.\n")

    print("4. HTML üretiliyor...")
    html = build_html(processed)
    # Yerel kopya kaydet
    with open(os.path.join(SCRIPT_DIR, "index.html"), "w", encoding="utf-8") as f:
        f.write(html)
    print("   HTML hazır.\n")

    print("5. Netlify'a yükleniyor...")
    site_url = deploy_to_netlify(html)
    print(f"   Yayında: {site_url}\n")

    print("6. Rapor e-postası gönderiliyor...")
    send_report(config["email_to"], rapor, processed["lead"], processed["stories"], site_url)

    print("\n═══ TAMAMLANDI ═══")


if __name__ == "__main__":
    main()
