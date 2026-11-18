# inventory — Depo ve Stok (WMS)

Bağımlılık: core, catalog. Müşteri dokümanı: §3, §4, §14.

## Modeller
Warehouse · Location (tür: raf, mal kabul, sevkiyat, iade kontrol, karantina, hasarlı, numune, yolda + sanal türler) ·
Lot (LOT no, üretim tarihi, SKT, üretici) · Pallet · Quant (anlık stok) · StockMove (hareket defteri) ·
Reservation · StockCount / StockCountLine.

## Servisler (`services.py`) — stoğu değiştiren TEK yer
| Fonksiyon | Ne yapar |
|---|---|
| `receive(product, qty, location, lot_no, expiry_date, production_date, ...)` | Mal kabul / üretimden giriş. SKT yoksa üretim tarihi + raf ömrü. |
| `move_stock(...)` | Temel hareket; tüm kurallar burada (negatif stok yok, LOT zorunlu, SKT geçmiş ürün satışa uygun alana giremez). |
| `transfer`, `scrap` | Lokasyonlar arası transfer, fire/hasar çıkışı. |
| `reserve(product, qty, reference, warehouse=None, allow_near_expiry=False)` | FEFO ile ayırır; yetmezse hiç ayırmaz (fazla satış engeli). Set → bileşenler. |
| `release(reference)` / `ship_reserved(reference)` | Rezervasyonu bırak / müşteriye sevk et (stok düşer). |
| `stock_summary(product)` | fiziksel, satışa uygun, rezerve, karantina, hasarlı, iade kontrol, SKT geçmiş, yoldaki. |
| `expiry_status(lot)` | ok / info / warning / critical / approval / expired. |
| `low_stock_products()`, `expiring_lots()` | Uyarı listeleri (ana panel kartları). |
| `suggest_purchase_qty`, `purchase_suggestion(product)` | Satın alma önerisi. |
| `start_count` → `submit_count` → (onay) → `apply_count` | Sayım ve onaylı düzeltme. |

## Formüller
- **Satışa uygun stok** = Σ(miktar − rezerve) [satışa uygun lokasyonlar, SKT'si geçmemiş LOT'lar]
- **Set satılabilir adet** = min(⌊bileşen satışa uygun / set içi miktar⌋)
- **SKT durumu** (kalan gün, varsayılan eşik): <0 expired (blokaj) · ≤30 approval · ≤90 critical · ≤120 warning · ≤180 info
- **Satın alma önerisi** = günlük ort. satış × tedarik süresi + güvenlik stoğu − satışa uygun − yoldaki, en az 0
  (örnek: 20×15+100−250 = 150). Günlük ort. satış = (son 90 gün satış − müşteri iadesi) / 90.
  Öneri otomatik siparişe dönmez.

## Olaylar
Yayınlar: `inventory.stock_moved`, `inventory.reserved`, `inventory.released`, `inventory.shipped`,
`inventory.count_applied`, `inventory.collect_incoming` (purchase modülü yoldaki miktarı döndürecek).
Dinler: `approval.approved.inventory.count_adjust`, `approval.rejected.inventory.count_adjust`.

## Ekranlar
`/inventory/` stok durumu · `/inventory/scan/` barkod sorgu (el terminali) · `/inventory/receive/` mal kabul ·
`/inventory/transfer/` transfer · Yönetim panelinde depo, lokasyon, LOT, palet, sayım; Quant/hareketler salt okunur.

## Bilinen sınırlar / sıradaki
Sayım düzeltmesi onay anındaki farkı uygular (sayım ile onay arasındaki hareketler için sayım öncesi lokasyon kilidi eklenecek).
Palet doluluk oranı, stok yaşlandırma raporu, depolar arası dengesizlik uyarısı ⬜.
