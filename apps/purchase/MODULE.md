# purchase — Satın Alma

Bağımlılık: core, catalog, inventory, partners. Müşteri dokümanı §5, §4.4.

Akış: talep (manuel veya `create_suggested_requests` sistem önerisi) → tedarikçi teklifleri → `compare_quotes`
(fiyat ↑, termin ↑, vade ↓) → `order_from_quote` → `submit` (yönetici onayı) → `mark_sent` → `/purchase/<id>/receive/`
mal kabul (LOT/SKT, ağırlıklı ortalama maliyet) → `close` (eksik/fazla teslim tutanağı).

Kurallar: onaysız siparişe mal kabul yapılamaz; siparişten fazla kabul edilemez (`purchase.over_receipt_pct`).
Yoldaki miktar `inventory.collect_incoming` olayıyla stok özetine ve satın alma önerisine yansır.
Raporlar: `supplier_performance`, `last_prices`.
Sıradaki: fatura eşleştirme (sipariş–irsaliye–fatura) muhasebe modülünde.
