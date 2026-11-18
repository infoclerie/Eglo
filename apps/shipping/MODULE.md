# shipping — Sevkiyat ve İade

Bağımlılık: core, catalog, inventory, sales. Müşteri dokümanı §7.

Akış: `sales.order_confirmed` → `create_shipment` (rezervasyonlardan, lokasyon rotasına göre toplama listesi) →
`scan` (barkod/koli barkodu doğrulama, yanlış ürün/fazla okutma engeli) → `pack` (koli adedi + tartı, ağırlık toleransı) →
`ship` (stok burada düşer) → `deliver`. Çoklu/dalga toplama: `batch_pick_list`.

İade: `request_return` → `receive_return` (müşteri → iade kontrol alanı; LOT, sevk edilen LOT'tan) →
`inspect_return` (satır bazında durum) → yönetici onayı → `complete_return` (satılabilir → raf, hasarlı → hasarlı alanı,
karantina → karantina). **Açılmış/kullanılmış ürün asla satılabilir stoğa dönmez.**

Ayar: `shipping.weight_tolerance_pct` (varsayılan 5).
Olaylar: `shipping.shipment_created`, `picking_started`, `picked`, `packed`, `shipped`, `delivered`, `return_requested`, `return_completed`.
Ekran: `/shipping/` kuyruk, `/shipping/<id>/` el terminali ekranı (adım adım).
Sıradaki: kargo firması entegrasyonu (etiket, takip no) — entegrasyon sihirbazı ile.

**Kargo etiketi:** `/shipping/<id>/label/` (koli başına bir 10×15 cm etiket, Code128 barkod = takip no veya sevk no), toplu: kuyruk ekranında seçip yazdır (`/shipping/labels/?ids=`). Kargo firması API'leri (Yurtiçi/Aras/MNG) anlaşma bilgileri gelince `integrations` sağlayıcısı olarak eklenecek; etiket barkodu o zaman firmanın takip numarası olur.
