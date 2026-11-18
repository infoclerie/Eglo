# sales — Sipariş Yönetimi

Bağımlılık: core, catalog, inventory, partners. Müşteri dokümanı §6.

Modeller: SalesOrder (13 durum, kanal, kanal sipariş no, müşteri anlık bilgileri, tutarlar), SalesOrderLine, Campaign, OrderStatusLog.

## Kurallar
- **Mükerrer engeli:** (kanal, kanal sipariş no) benzersiz; `import_channel_order` aynı siparişi ikinci kez açmaz, mevcut olanı döner.
- **Anlık rezervasyon:** `confirm` tüm satırları tek işlemde rezerve eder; bir satır yetmezse hiçbiri ayrılmaz (fazla satış yok).
- **Kredi limiti:** vadeli satışta açık bakiye + sipariş > limit → `request_credit_override` ile yönetici onayı.
- **İptal:** stok ayrılmamış sipariş doğrudan; ayrılmış sipariş yönetici onayıyla iptal edilir, rezervasyon bırakılır. Sevk edilen sipariş iptal edilmez (iade).
- Durum geçmişi ve "bu durumda kaç saattir" bilgisi tutulur.

## Formüller (`services.py` başı)
Birim fiyat = kanal fiyatı (müşterinin fiyat kanalı öncelikli) × (1 − müşteri indirimi %).
Satır net = miktar × birim fiyat − satır indirimi − sepet indirimi payı. KDV satır oranıyla net üzerinden; kargo KDV'si %20.

## Kampanyalar
Sepette %, X al Y öde, N. ürün sabit fiyat, tutar üstü ücretsiz kargo, kupon %. Kanal ve ürün kapsamı, tarih aralığı,
maksimum kullanım, maksimum indirim, minimum sepet.

## Olaylar
Yayınlar: `sales.order_confirmed`, `sales.order_cancelled`, `sales.status_changed`.
Dinler: `shipping.*` (durum ilerletme), `approval.approved.sales.cancel`, `approval.approved.sales.credit_override`.
