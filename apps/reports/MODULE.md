# reports — Raporlar (§11)

- `registry.py` → REPORTS: stok yaşlandırma, devir hızı, kanal kârlılığı, ürün kârlılığı, SKT raporu.
- Yeni rapor: fonksiyon yaz (params → columns/rows/totals/chart/note) ve REPORTS'a ekle; ekran, Excel ve yazdırma otomatik.
- Excel: `?format=xlsx` (openpyxl, biçimli). PDF: tarayıcıda "PDF / Yazdır" (A4 yatay yazdırma stili app.css'te).
- Kârlılık hesabı `accounting.services.product_profitability` (kanal maliyet profilleri) kullanır.
- İzin: `reports.view_report` (veri tutmayan model).
