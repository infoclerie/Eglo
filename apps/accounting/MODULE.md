# accounting — Finans ve Muhasebe

Bağımlılık: core, catalog, inventory, partners, sales, purchase. Müşteri dokümanı §9.

Modeller: Account (kasa/banka/POS/pazaryeri), Invoice + InvoiceLine (giden/gelen, e-Fatura/e-Arşiv, ETTN, UBL XML),
Payment, LedgerEntry (cari hareket), ChannelCostProfile, ProductCostExtra, MarketplaceSettlement.

## Akışlar
- **Satış:** `shipping.shipped` → `create_sales_invoice` → `issue` (GİB biçimli numara: seri+yıl+9 hane, cari borç) →
  `accounting.invoice_ready` (otomatik gönderim açıksa entegrasyon kuyruğa alır). Cari e-fatura mükellefiyse e-Fatura
  (TICARIFATURA/TEMELFATURA), değilse e-Arşiv. Kargo bedeli ayrı hizmet satırı.
- **İade:** `shipping.return_completed` → iade faturası taslağı (orijinal faturaya referanslı, UBL IADE).
- **Alış:** `create_purchase_invoice` 3'lü eşleştirme (faturalanan ≤ teslim alınan, fiyat toleransı) — uymazsa onay.
- **Gelen e-fatura:** entegratörden `record_incoming_invoice` (ETTN ile mükerrer engeli).
- **Tahsilat/ödeme:** `register_payment` (fatura açık bakiyesini aşamaz), cari ekstre, vadesi geçmiş alacaklar, haftalık nakit akışı.
- **İptal:** yönetici onaylı; cari hareket ters kayıtla kapatılır (silinmez).
- **Hakediş:** sipariş verisinden tahmin + bankaya yatanla mutabakat (fark raporu).
- **Kârlılık:** ürün × kanal katkı kârı; maliyet sevk anındaki stok hareketi maliyetinden.

Formüller `services.py` başında. UBL-TR üretici: `ubl.py` (entegratörden bağımsız).
Ayarlar: `accounting.company`, `accounting.series_efatura`, `accounting.series_earsiv`, `accounting.efatura_profile`,
`accounting.auto_invoice_on_ship`, `accounting.price_tolerance_pct`.
Olaylar: yayınlar `accounting.invoice_ready/sent/cancelled`, `accounting.send_requested`, `accounting.incoming_invoice`,
`accounting.purchase_invoice_posted`, `accounting.payment_registered`; dinler `shipping.shipped`, `shipping.return_completed`,
`partners.collect_balance`, onay olayları.
Sıradaki: resmi muhasebe fişi/hesap planı aktarımı (Uyumsoft muhasebe tarafı netleşince), banka ekstresi içe aktarma.
