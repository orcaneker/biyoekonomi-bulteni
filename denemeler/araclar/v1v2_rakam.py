# -*- coding: utf-8 -*-
"""v1 → v2 RAKAM KAYBI DENETİMİ.

Türkçeleştirme sayı BİLGİSİNİ kaybettirdi mi? Basit digit sayımı yanıltır
($2.5bn → "2,5 milyar dolar" aynı bilgi, farklı karakter). Bu yüzden
sayılar biçimden arındırılıp KÜME olarak kıyaslanır.
"""
import json
import re
import sys


def sayilar(m):
    k = set()
    for h in re.findall(r"\d[\d.,]*", m or ""):
        s = h.rstrip(".,").replace(".", "").replace(",", "")
        if s:
            k.add(s.lstrip("0") or "0")
    return k


def yukle(y):
    d = json.load(open(y, encoding="utf-8"))
    d = d.get("taslak") if isinstance(d.get("taslak"), dict) else d
    return {s["id"]: s for s in d["stories"]}, d


a, da = yukle(sys.argv[1])
b, db = yukle(sys.argv[2])
# id'ler modele göre değişebilir → birincil kaynak URL'iyle eşle
url = lambda s: (s.get("source") or {}).get("url", "").rstrip("/")
ai = {url(s): s for s in a.values()}
bi = {url(s): s for s in b.values()}
ortak = [u for u in ai if u in bi]

print(f"{sys.argv[1]}  →  {sys.argv[2]}")
print(f"eşleşen haber: {len(ortak)}/{len(ai)}\n")
kayip_top = yeni_top = 0
for u in ortak:
    sa, sb = ai[u], bi[u]
    na = sayilar((sa.get("excerpt") or "") + " " + (sa.get("detail") or ""))
    nb = sayilar((sb.get("excerpt") or "") + " " + (sb.get("detail") or ""))
    kayip, yeni = sorted(na - nb), sorted(nb - na)
    kayip_top += len(kayip)
    yeni_top += len(yeni)
    if kayip or yeni:
        print(f"  {sa['id'][:44]:46} v1:{len(na):3} v2:{len(nb):3}")
        if kayip:
            print(f"     v2'de YOK : {', '.join(kayip[:12])}")
        if yeni:
            print(f"     v2'de YENİ: {', '.join(yeni[:12])}")
print(f"\n── toplam: v2'de düşen {kayip_top} sayı · v2'de eklenen {yeni_top} sayı")
