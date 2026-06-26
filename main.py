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
def search_perplexity(query_text):
    """Tek bir sorguyu Perplexity'ye gönderir, özet liste döner (max 5 haber)."""
    headers = {
        "Authorization": f"Bearer {PERPLEXITY_API_KEY}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": "sonar",
        "messages": [
            {
                "role": "system",
                "content": (
                    "You are a research assistant. Find the 5 most important recent news items "
                    "from the last 7-14 days only. For each item output EXACTLY this format:\n"
                    "TITLE: [headline]\n"
                    "SUMMARY: [2 sentence summary]\n"
                    "SOURCE: [source name]\n"
                    "DATE: [publication date]\n"
                    "URL: [url]\n"
                    "---\n"
                    "Be concise. No extra text."
                )
            },
            {"role": "user", "content": query_text},
        ],
        "max_tokens": 1500,
    }
    try:
        r = requests.post(PERPLEXITY_URL, headers=headers, json=payload, timeout=60)
        r.raise_for_status()
        data = r.json()
        return data["choices"][0]["message"]["content"]
    except Exception as e:
        print(f"  ! Perplexity hatası ({e})")
        return ""


def gather_all_news(queries):
    """Tüm sorguları çalıştırır, sonuçları birleştirir. Max 5 haber/sorgu."""
    all_results = []
    for q in queries:
        print(f"  → Sorgu: {q['id']}")
        result = search_perplexity(q["query"])
        if result:
            # Her sorgu sonucunu 2000 karakterle sınırla
            trimmed = result[:2000]
            all_results.append(f"[ALAN: {q['id']}]\n{trimmed}")
    combined = "\n\n---\n\n".join(all_results)
    # Toplam veriyi 15000 karakterle sınırla
    if len(combined) > 15000:
        combined = combined[:15000] + "\n[...veri kısaltıldı...]"
    print(f"  Toplam ham veri: {len(combined)} karakter")
    return combined


# ============================================================
# 3. CLAUDE İLE İŞLE
# ============================================================
def process_with_claude(raw_news, claude_prompt):
    """Ham haberleri Claude'a gönderir, işlenmiş JSON döner."""
    today = datetime.date.today()
    week_ago = today - datetime.timedelta(days=7)

    full_prompt = f"""{claude_prompt}

BUGÜNÜN TARİHİ: {today.strftime('%d %B %Y')}
ÖNCELİKLİ PENCERE: {week_ago.strftime('%d %B %Y')} - {today.strftime('%d %B %Y')}

Aşağıda farklı kaynaklardan toplanmış ham haberler var. Bunları işle:

{raw_news}

KRITIK JSON KURALLARI:
1. Ciktini SADECE gecerli JSON olarak ver, baska hicbir sey yazma
2. Tum string degerlerinde tek tirnak veya ozel karakter KULLANMA
3. URL alanlarini bos birak veya tam URL yaz - asla virgul veya tirnak icermesin
4. detail alani sadece duz metin paragraflar: <p>metin</p> - icinde tirnak olmamali
5. Tum Turkce karakterler (a, i, o, u, s, g, c ve buyukleri) JSON'da gecerlidir

JSON FORMAT (bu formata tam uy):
{{"lead": {{"title":"baslik", "excerpt":"kisa ozet", "detail":"<p>detay</p>", "source":"kaynak adi", "url":"https://example.com", "category":"mevzuat", "date":"2026-06-23"}},
  "stories": [{{"title":"baslik2", "excerpt":"ozet2", "detail":"<p>detay2</p>", "source":"kaynak2", "url":"https://example2.com", "category":"piyasa", "date":"2026-06-22"}}],
  "rapor": {{"bulunan_toplam": 20, "elenen": 8, "yayinlanan": 12, "pencere": "7 gun"}}}}

category SADECE su degerlerden biri olmali: mevzuat, piyasa, teknoloji, uluslararasi, haber, akademik"""

    headers = {
        "x-api-key": ANTHROPIC_API_KEY,
        "anthropic-version": "2023-06-01",
        "content-type": "application/json",
    }
    payload = {
        "model": "claude-sonnet-4-6",
        "max_tokens": 6000,
        "messages": [{"role": "user", "content": full_prompt}],
    }
    try:
        r = requests.post(ANTHROPIC_URL, headers=headers, json=payload, timeout=300)
        r.raise_for_status()
        data = r.json()
        text = "".join(block.get("text", "") for block in data["content"] if block.get("type") == "text")
        print(f"  Claude yanit uzunlugu: {len(text)} karakter")

        # JSON ayikla
        clean = text.strip()
        if "```json" in clean:
            clean = clean.split("```json", 1)[1].split("```")[0].strip()
        elif "```" in clean:
            clean = clean.split("```", 1)[1].split("```")[0].strip()

        start = clean.find("{")
        end = clean.rfind("}") + 1
        if start >= 0 and end > start:
            clean = clean[start:end]

        try:
            return json.loads(clean)
        except json.JSONDecodeError as je:
            print(f"  ! JSON parse hatasi: {je}")
            print(f"  ! Sorunlu bolge: ...{clean[max(0,je.pos-100):je.pos+100]}...")
            # Claude'u tekrar cagir - sadece JSON duzelt
            print("  Yeniden deneniyor: Claude'dan JSON duzeltmesi isteniyor...")
            fix_prompt = f"""Asagidaki metin gecersiz JSON iceriyor. Lutfen sadece duzgun JSON dondu, baska hicbir sey yazma.
Tum string degerlerindeki ozel karakterleri, ic icge tirnaklari ve URL icerisindeki sorunlu karakterleri duzelt.

BOZUK JSON:
{clean[:8000]}

Yukaridaki JSON'u duzelt ve SADECE gecerli JSON dondur."""
            fix_payload = {{
                "model": "claude-sonnet-4-6",
                "max_tokens": 6000,
                "messages": [{{"role": "user", "content": fix_prompt}}],
            }}
            try:
                r2 = requests.post(ANTHROPIC_URL, headers=headers, json=fix_payload, timeout=180)
                r2.raise_for_status()
                data2 = r2.json()
                text2 = "".join(b.get("text","") for b in data2["content"] if b.get("type")=="text")
                clean2 = text2.strip()
                if "```" in clean2:
                    clean2 = clean2.split("```json",1)[-1].split("```")[0].strip() if "```json" in clean2 else clean2.split("```",1)[1].split("```")[0].strip()
                s2 = clean2.find("{")
                e2 = clean2.rfind("}") + 1
                if s2 >= 0 and e2 > s2:
                    clean2 = clean2[s2:e2]
                result = json.loads(clean2)
                print("  Yeniden deneme basarili!")
                return result
            except Exception as e2:
                print(f"  ! Yeniden deneme de basarisiz: {e2}")
                return {{
                    "lead": {{
                        "title": "Bulten bu hafta uretilemedi",
                        "excerpt": "Otomatik uretimde hata olustu, lutfen loglari kontrol edin.",
                        "detail": "<p>Bu hafta otomatik bulten uretiminde teknik sorun yasandi.</p>",
                        "source": "Sistem", "url": "#",
                        "category": "haber",
                        "date": str(datetime.date.today())
                    }},
                    "stories": [],
                    "rapor": {{"bulunan_toplam": 0, "elenen": 0, "yayinlanan": 0, "pencere": "hata"}}
                }}
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
    raw_news = gather_all_news(config["queries"])
    print(f"   Ham veri toplandı ({len(raw_news)} karakter).\n")

    print("3. Claude ile işleniyor...")
    processed = process_with_claude(raw_news, config["claude_prompt"])
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
