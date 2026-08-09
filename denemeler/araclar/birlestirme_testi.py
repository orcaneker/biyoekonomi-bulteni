# -*- coding: utf-8 -*-
"""MÜKERRER BİRLEŞTİRME TESTİ — gerçek Sayı 2 verisiyle.

14 haber + 25 radar maddesinden olay listesi kurar ve yeni birleştirme
adımını çalıştırır. Bilinen mükerrer: Hindistan GOBARdhan kararını anlatan
iki kayıt (eski kod bunları kaçırıyordu: ortak şirket yok, başlık
benzerliği 0,33 < 0,45 eşiği).
"""
import json
import os
import sys

from yollar import KOK, veri  # noqa: F401  (repo kokunu sys.path'e ekler)
import pipeline  # noqa: E402
import llm       # noqa: E402

llm.set_logger(print)

d = json.load(open(veri("14haber-terra-yeni-prompt.json"), encoding="utf-8"))

olaylar = []
for i, s in enumerate(d["stories"]):
    olaylar.append({
        "event_key": s["id"],
        "baslik_ozet": f"{s.get('title')} — {(s.get('excerpt') or '')[:200]}",
        "primary_id": f"p{i}",
        "supporting_ids": [f"s{i}"],
        "kategori": s.get("category"),
        "olgunluk": s.get("maturity"),
        "sirketler": s.get("companies") or [],
        "ulkeler": s.get("countries") or [],
        "yatirim_usd_milyon": ((s.get("investment") or {}) or {}).get("amount_usd_million"),
        "puan": s.get("score") or 5,
    })

n = len(olaylar)
for kume in d.get("radar") or []:
    for m in kume.get("maddeler", []):
        olaylar.append({
            "event_key": f"radar-{n}",
            "baslik_ozet": m.get("title") or "",
            "primary_id": f"p{n}", "supporting_ids": [],
            "kategori": m.get("category"), "olgunluk": None,
            "sirketler": [], "ulkeler": [],
            "yatirim_usd_milyon": None, "puan": 3,
        })
        n += 1

print(f"Girdi: {len(olaylar)} olay ({len(d['stories'])} haber + "
      f"{len(olaylar) - len(d['stories'])} radar)\n")

hindistan = [o["event_key"] for o in olaylar
             if "indistan" in (o["baslik_ozet"] or "")]
print(f"Hindistan geçen kayıtlar: {hindistan}\n")

kalan, notlar = pipeline.olaylari_birlestir(olaylar)

print(f"\nSONUÇ: {len(olaylar)} → {len(kalan)} olay")
kalan_anahtar = {o["event_key"] for o in kalan}
print("\nHindistan kayıtlarının durumu:")
for k in hindistan:
    print(f"  {k:44} {'KALDI' if k in kalan_anahtar else 'BİRLEŞTİRİLDİ'}")
print()
for x in notlar:
    print("  ·", x)

mm, mt = llm.maliyet_raporu()
print(f"\n{mm}")
