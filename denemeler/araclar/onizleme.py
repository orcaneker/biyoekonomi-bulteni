# -*- coding: utf-8 -*-
"""İNCELEME SAYFASI YEREL ÖNİZLEME — Neon'a bağlanmadan.

Gerçek review.html şablonunu servis eder, /api/.../draft isteğini ise
diskteki kayıtlı Sayı 2 taslağıyla karşılar. Böylece görsel bloğu, kart
düzeni ve hata durumları veritabanı olmadan gözle doğrulanabilir.

  python denemeler/araclar/onizleme.py          → http://127.0.0.1:8765/r/test
"""
import copy
import json
import os
import sys

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles

from yollar import KOK, veri   # repo kökünü sys.path'e ekler

SABLON = open(os.path.join(KOK, "review_app", "templates", "review.html"),
              encoding="utf-8").read()
VERI = json.load(open(veri("sayi2-uretim-taslagi-sonnet5.json"), encoding="utf-8"))

# Bellekte tutulan çalışma kopyası — /api/.../image bunu değiştirir, böylece
# "değiştir / kaldır" akışı Neon olmadan uçtan uca denenebilir.
DURUM = copy.deepcopy(VERI)

# Bu taslak, görsel adaylarını kaydeden sürümden ÖNCE üretildi; panelin
# alternatif listesini görebilmek için her habere diğer haberlerin (gerçek,
# yüklenebilir) görselleri aday olarak konuyor. Yalnızca önizleme içindir.
_gercek = [s["image"] for s in DURUM["taslak"]["stories"] if (s.get("image") or {}).get("url")]
for _s in DURUM["taslak"]["stories"]:
    _kendi = (_s.get("image") or {}).get("url")
    _s["gorsel_adaylari"] = [g for g in _gercek if g["url"] != _kendi][:2]

app = FastAPI()
# Dış sunuculara çıkılamayan ortamda görsellerin gerçekten yüklenebilmesi
# için repodaki varlıklar yerelden servis edilir.
app.mount("/assets", StaticFiles(directory=os.path.join(KOK, "assets")),
          name="assets")


@app.get("/r/{token}", response_class=HTMLResponse)
def sayfa(token: str):
    return SABLON.replace("__TOKEN__", token)


@app.get("/api/{token}/draft")
def taslak(token: str):
    """Varsayılan: taslaktaki GERÇEK görsel URL'leri servis edilir.

    YEREL_GORSEL=1 ile URL'ler repodaki dosyalarla değiştirilir. Bu yalnızca
    dışarıya çıkamayan bir tarayıcıda (ör. sandbox) yükleme/hata yollarını
    sınamak içindir — normal önizlemede AÇILMAZ, yoksa ekranda hep aynı
    görsel görünür ve taslağın gerçek görselleri denetlenemez.
    """
    d = copy.deepcopy(DURUM)
    if os.environ.get("YEREL_GORSEL") not in ("1", "true", "evet"):
        return d

    st = d["taslak"]["stories"]
    for s in st[:-2]:                       # (1) yüklenen görsel
        s["image"] = {"url": "/assets/hero.webp",
                      "credit": (s.get("image") or {}).get("credit") or "yerel",
                      "type": "og-sayfa"}
    if st:                                  # (3) 404 → onerror yolu
        st[-1]["image"] = {"url": "/assets/bulunmayan-gorsel.jpg",
                           "credit": "example.invalid", "type": "og"}
    return d                                # (2) görselsiz haber zaten var


@app.post("/api/{token}/image")
async def gorsel_ayarla(token: str, req: Request):
    """review_app.main'deki uç noktanın aynısı — doğrulama dahil, DB yerine
    bellekteki kopyaya yazar."""
    sys.path.insert(0, os.path.join(KOK, "review_app"))
    from main import _gorsel_dogrula          # aynı doğrulama kullanılsın

    v = await req.json()
    st = next((s for s in DURUM["taslak"]["stories"] if s["id"] == v.get("id")), None)
    if not st:
        raise HTTPException(400, "Haber bulunamadı")
    url = (v.get("url") or "").strip()
    if not url:
        st["image"] = {"url": None, "credit": None, "type": None}
    else:
        _gorsel_dogrula(url)
        st["image"] = {"url": url, "credit": url.split("/")[2].replace("www.", ""),
                       "type": "hakem"}
    return {"ok": True, "image": st["image"], "yayinda": False}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8765, log_level="warning")
