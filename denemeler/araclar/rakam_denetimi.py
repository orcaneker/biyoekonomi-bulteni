# -*- coding: utf-8 -*-
"""RAKAM DENETİMİ — iki modelin yazdığı her sayıyı kaynak metinde arar.

Yöntem: haberin kaynak metinlerini (birincil TAM + destekler) tek havuzda
topla, sayıları biçimden arındır (1,52 → 152 · 1.52 → 152 · 23.731 → 23731),
sonra modelin metnindeki her sayıyı bu havuzda ara.

⚠ "Bulunamadı" = kaynakta karşılığı YOK demek DEĞİL: yıl, yüzde ve
birleştirilmiş ifadeler (700 bin ← 700,000) yanlış alarm verebilir.
Amaç, elle bakılacak listeyi kısaltmak.
"""
import json
import os
import re
import sys

from yollar import KOK, veri  # noqa: F401  (repo kokunu sys.path'e ekler)
import yeniden_yaz as y   # noqa: E402


def sayilar(metin):
    """Metindeki sayıları biçimden arındırılmış dizge kümesi olarak döndür."""
    ham = re.findall(r"\d[\d.,]*", metin or "")
    k = set()
    for h in ham:
        s = h.rstrip(".,")
        k.add(s.replace(".", "").replace(",", ""))     # 1,52→152 · 23.731→23731
        k.add(s.replace(",", "").replace(".", ""))
    return {x for x in k if x}


def havuz(story, metinler):
    """Birincil TAM metin + destek kaynakların modele giden payı."""
    p = [metinler.get(y.url_normalize(story["source"]["url"]), {}).get("text", "")]
    for d in story.get("supporting_sources") or []:
        p.append(metinler.get(y.url_normalize(d["url"]), {}).get("text", "")[:800])
    t = " ".join(p)
    # 700,000 → 700 bin · 8.4 million → 84 gibi Türkçe karşılıkları da yakala
    return sayilar(t) | {s[:-3] for s in sayilar(t) if s.endswith("000")}


def denetle(yol, etiket, metinler, kaynaklar):
    d = json.load(open(yol, encoding="utf-8"))
    d = d.get("taslak") if isinstance(d.get("taslak"), dict) else d
    print(f"\n{'=' * 66}\n{etiket}\n{'=' * 66}")
    toplam = supheli = 0
    for s in d["stories"]:
        kaynak = kaynaklar.get(s["id"])
        if not kaynak:
            continue
        yazilan = sayilar((s.get("excerpt") or "") + " " + (s.get("detail") or ""))
        bulunamayan = sorted(x for x in yazilan if x not in kaynak and len(x) > 1)
        toplam += len(yazilan)
        supheli += len(bulunamayan)
        isaret = "✓" if not bulunamayan else "⚠"
        print(f"  {isaret} {s['id'][:42]:44} {len(yazilan):3} sayı")
        if bulunamayan:
            print(f"      kaynakta bulunamadı: {', '.join(bulunamayan)}")
    print(f"  ── toplam {toplam} sayı · {supheli} şüpheli")


ana = json.load(open(veri("sayi2-uretim-taslagi-sonnet5.json"), encoding="utf-8"))["taslak"]
urls = []
for s in ana["stories"]:
    urls.append(s["source"]["url"])
    urls += [x["url"] for x in (s.get("supporting_sources") or [])]
metinler = y.kaynak_metinleri_cek(list(dict.fromkeys(urls)))
kaynaklar = {s["id"]: havuz(s, metinler) for s in ana["stories"]}

denetle(veri("sayi2-uretim-taslagi-sonnet5.json"), "SONNET 5", metinler, kaynaklar)
denetle(veri("5haber-terra-eski-prompt.json"), "TERRA HIGH", metinler, kaynaklar)
