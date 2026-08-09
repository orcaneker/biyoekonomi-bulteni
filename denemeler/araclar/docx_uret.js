/**
 * ÇEVİRİ KIYASI — yan yana (iki sütun) docx üretici
 * ==================================================
 * Yatay A4, solda A modeli, sağda B modeli. Her haber için başlık / özet /
 * tam metin ayrı satırlarda hizalanır ki göz kolay kıyaslasın.
 *
 * Kullanım:
 *   node kiyas/_docx_uret.js A.json B.json "A etiketi" "B etiketi" cikti.docx
 *
 * NOT: docx paketi repoya bulaşmasın diye scratchpad'den yükleniyor.
 */
const path = require("path");
const fs = require("fs");

const MODUL = process.env.DOCX_MODUL || "docx";
const {
  Document, Packer, Paragraph, TextRun, Table, TableRow, TableCell,
  WidthType, ShadingType, PageOrientation, AlignmentType, BorderStyle,
  HeadingLevel, PageBreak,
} = require(MODUL);

const [aYol, bYol, aEtiket, bEtiket, ciktiYol] = process.argv.slice(2);

// ── ölçüler (DXA · 1440 = 1 inç) ──
const KENAR = 720;                     // 0,5"
const SAYFA_GENIS = 16838;             // A4 yatay
const ICERIK = SAYFA_GENIS - 2 * KENAR;
const SUTUN = Math.floor(ICERIK / 2);

const RENK = {
  a: "1F4E5F",        // Sonnet sütunu — koyu petrol
  b: "2E6B3E",        // Terra sütunu — koyu yeşil
  etiket: "E8ECEF",   // bölüm etiketi zemini
  cizgi: "B8C4CC",
};

function govde(yol) {
  const d = JSON.parse(fs.readFileSync(yol, "utf8"));
  return d.taslak && typeof d.taslak === "object" ? d.taslak : d;
}
const A = govde(aYol), B = govde(bYol);

const norm = (u) => (u || "").replace(/\/+$/, "").replace(/^https?:\/\/(www\.)?/, "");
const dizin = (t) => Object.fromEntries(
  (t.stories || []).map((s) => [norm((s.source || {}).url), s]));
const aIdx = dizin(A), bIdx = dizin(B);
const ortak = Object.keys(aIdx).filter((u) => u in bIdx);

// ── dil ihlali sayacı (dokümandaki özet tablo için) ──
const KURALLAR = [
  /\b(January|February|March|April|June|July|August|September|October|November|December)\b/gi,
  /\b(million|billion|thousand|tonnes|per cent)\b/gi,
  /(?:US\$|CA\$|A\$|\$|€|£)\s?\d+(?:[.,]\d+)?\s?(?:bn|m\b|k\b)?/gi,
  /\b\d{1,3},\d{3}\b/g,
  /\bFY\s?\d{4}/gi,
  /(?:^|\n)\s*[*\-#]\s|\*\*/g,
  /\b(EUR|USD|GBP|DKK|ZAR|SEK|NOK|CHF|JPY|CNY|INR)\s?\d/gi,
];
function ihlal(t) {
  const m = (t.stories || [])
    .map((s) => `${s.title}\n${s.excerpt}\n${s.detail}`).join("\n");
  return KURALLAR.reduce((n, k) => n + ((m.match(k) || []).length), 0);
}
const ort = (t, alan) => {
  const d = (t.stories || []).map((s) => (s[alan] || "").length);
  return d.length ? Math.round(d.reduce((x, y) => x + y, 0) / d.length) : 0;
};

// ── yazı yardımcıları ──
const P = (metin, o = {}) => new Paragraph({
  spacing: { after: o.after ?? 100, line: o.line ?? 264 },
  alignment: o.align,
  children: [new TextRun({
    text: metin,
    bold: o.bold, italics: o.italics, color: o.color,
    size: o.size ?? 21,                       // yarım punto → 21 = 10,5pt
    font: o.font ?? "Calibri",
  })],
});

const hucre = (cocuklar, o = {}) => new TableCell({
  width: { size: o.span ? ICERIK : SUTUN, type: WidthType.DXA },
  columnSpan: o.span,
  shading: o.fill
    ? { type: ShadingType.CLEAR, color: "auto", fill: o.fill } : undefined,
  margins: { top: 90, bottom: 90, left: 130, right: 130 },
  children: cocuklar.length ? cocuklar : [P("—", { color: "999999" })],
});

// metni paragraflara böl (\n\n) — docx'te \n kullanılmaz
const paragraflar = (metin, o = {}) =>
  (metin || "").split(/\n{2,}/).map((s) => s.trim()).filter(Boolean)
    .map((s) => P(s, o));

function etiketSatiri(baslik) {
  return new TableRow({
    children: [hucre([P(baslik, { bold: true, size: 17, color: "44555F" })],
      { span: 2, fill: RENK.etiket })],
  });
}

// ── belge içeriği ──
const cocuklar = [];

cocuklar.push(
  new Paragraph({
    heading: HeadingLevel.HEADING_1,
    spacing: { after: 60 },
    children: [new TextRun({
      text: "Biyoekonomi Bülteni — Çeviri Modeli Karşılaştırması",
      bold: true, size: 34, font: "Calibri", color: "1F4E5F",
    })],
  }),
  P(`Sayı ${(A.issue || {}).number ?? 2} · ${(A.issue || {}).hafta ?? ""} · `
    + `kapsam ${(A.issue || {}).coverage_start ?? ""} – ${(A.issue || {}).coverage_end ?? ""}`,
    { size: 20, color: "5A6B75", after: 200 }),
  P("Aşağıdaki haberlerin tamamı AYNI kaynaklardan, AYNI talimatlarla, iki farklı "
    + "yapay zekâ modeline yazdırılmıştır. Haberler, kaynaklar ve sıralama birebir "
    + "aynıdır; değişen tek unsur metni yazan modeldir.", { after: 120 }),
  P("Değerlendirirken bakılabilecek noktalar: Türkçe akıcılığı, sayı ve para "
    + "birimlerinin yazımı, teknik terimlerin karşılanması, kaynaktaki verilerin "
    + "eksiksiz aktarılıp aktarılmadığı, paragraf düzeni.", { after: 240 }),
);

// özet tablo — sütun genişlikleri tabloyla birebir toplanmalı (docx kuralı)
const OZET_SUTUN = [4200, 2200, 2900, 2900, ICERIK - 4200 - 2200 - 2900 - 2900];

const ozetHucre = (i, cocuklar, fill) => new TableCell({
  width: { size: OZET_SUTUN[i], type: WidthType.DXA },
  shading: fill ? { type: ShadingType.CLEAR, color: "auto", fill } : undefined,
  margins: { top: 90, bottom: 90, left: 130, right: 130 },
  children: cocuklar,
});

const olcumSatir = (etiket, t, renk) => new TableRow({
  children: [
    [P(etiket, { bold: true, color: renk })],
    [P(`${(t.stories || []).length}`)],
    [P(`${ort(t, "excerpt")} karakter`)],
    [P(`${ort(t, "detail")} karakter`)],
    [P(`${ihlal(t)}`, { bold: true, color: ihlal(t) === 0 ? "2E6B3E" : "A03028" })],
  ].map((c, i) => ozetHucre(i, c)),
});

cocuklar.push(
  P("Genel görünüm", { bold: true, size: 24, color: "1F4E5F", after: 100 }),
  new Table({
    columnWidths: OZET_SUTUN,
    width: { size: ICERIK, type: WidthType.DXA },
    rows: [
      new TableRow({
        tableHeader: true,
        children: ["Model", "Haber", "Ort. özet", "Ort. metin",
          "Türkçe yazım kuralı ihlali"].map((b, i) => ozetHucre(
            i, [P(b, { bold: true, color: "FFFFFF", size: 19 })], "1F4E5F")),
      }),
      olcumSatir(aEtiket, A, RENK.a),
      olcumSatir(bEtiket, B, RENK.b),
    ],
  }),
  P("“Türkçe yazım kuralı ihlali” = metinde Türkçeleştirilmeden bırakılmış "
    + "İngilizce ay adı, büyüklük ifadesi (million/billion), İngiliz tipi ondalık "
    + "ayırıcı ($1.52), binlik ayırıcı (700,000) veya biçimlendirme işareti sayısı.",
    { size: 17, italics: true, color: "5A6B75", after: 0 }),
  new Paragraph({ children: [new PageBreak()] }),
);

// ── haberler ──
ortak.forEach((u, n) => {
  const a = aIdx[u], b = bIdx[u];
  const kat = a.category || "";
  const manset = a.id === A.lead_id ? "  ★ MANŞET" : "";

  cocuklar.push(
    P(`HABER ${n + 1}${manset}`,
      { bold: true, size: 26, color: "1F4E5F", after: 40 }),
    P(`Kategori: ${kat}   ·   Kaynak: ${(a.source || {}).url || ""}`,
      { size: 16, color: "6B7A84", after: 120 }),
    new Table({
      columnWidths: [SUTUN, SUTUN],
      width: { size: ICERIK, type: WidthType.DXA },
      borders: {
        insideHorizontal: { style: BorderStyle.SINGLE, size: 4, color: RENK.cizgi },
        insideVertical: { style: BorderStyle.SINGLE, size: 8, color: RENK.cizgi },
        top: { style: BorderStyle.SINGLE, size: 4, color: RENK.cizgi },
        bottom: { style: BorderStyle.SINGLE, size: 4, color: RENK.cizgi },
        left: { style: BorderStyle.SINGLE, size: 4, color: RENK.cizgi },
        right: { style: BorderStyle.SINGLE, size: 4, color: RENK.cizgi },
      },
      rows: [
        new TableRow({
          tableHeader: true,
          children: [
            hucre([P(aEtiket, { bold: true, color: "FFFFFF", size: 20 })],
              { fill: RENK.a }),
            hucre([P(bEtiket, { bold: true, color: "FFFFFF", size: 20 })],
              { fill: RENK.b }),
          ],
        }),
        etiketSatiri("BAŞLIK"),
        new TableRow({
          children: [
            hucre([P(a.title || "", { bold: true, size: 22 })]),
            hucre([P(b.title || "", { bold: true, size: 22 })]),
          ],
        }),
        etiketSatiri("ÖZET  (bültende kartta görünen)"),
        new TableRow({
          children: [
            hucre(paragraflar(a.excerpt)),
            hucre(paragraflar(b.excerpt)),
          ],
        }),
        etiketSatiri("TAM METİN"),
        new TableRow({
          children: [
            hucre(paragraflar(a.detail)),
            hucre(paragraflar(b.detail)),
          ],
        }),
      ],
    }),
  );
  if (n < ortak.length - 1) {
    cocuklar.push(new Paragraph({ children: [new PageBreak()] }));
  }
});

const doc = new Document({
  creator: "Biyoekonomi Bülteni",
  title: "Çeviri Modeli Karşılaştırması",
  sections: [{
    properties: {
      page: {
        size: { orientation: PageOrientation.LANDSCAPE },
        margin: { top: KENAR, right: KENAR, bottom: KENAR, left: KENAR },
      },
    },
    children: cocuklar,
  }],
});

Packer.toBuffer(doc).then((buf) => {
  fs.writeFileSync(ciktiYol, buf);
  console.log(`yazıldı: ${ciktiYol}  (${ortak.length} haber, ${buf.length} bayt)`);
});
