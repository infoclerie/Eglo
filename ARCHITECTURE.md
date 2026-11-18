# Mimari

## Katmanlar
```
Tarayıcı (masaüstü, el terminali, bayi portalı)
   │  HTTPS (Caddy, otomatik sertifika)
Django (gunicorn)  ── apps/<modül>/views.py  →  services.py (iş kuralları)  →  models.py
   │                         │                         │
   │                    olay yolu (core.events) ←──────┘   modüller arası tek iletişim yolu
PostgreSQL (tek ortak veritabanı)
```

## Dizin yapısı
```
config/            settings, urls, modules.py (açık modül listesi)
apps/core/         modül kayıt sistemi, olay yolu, işlem logu, onay akışı, numara serileri, ayarlar, roller, ana panel
apps/catalog/      ürün kartı, marka, kategori, satış kanalı, kanal fiyatı, set bileşenleri
apps/inventory/    depo, lokasyon, LOT/SKT, palet, anlık stok (Quant), hareket, rezervasyon (FEFO), sayım
apps/partners/     cari kartlar (müşteri, bayi, tedarikçi)
apps/sales/        sipariş havuzu, kampanyalar, kanal siparişi içe alma
apps/shipping/     toplama, paketleme, sevk, teslim, iade
apps/purchase/     talep, teklif, satın alma siparişi, mal kabul
static/css/app.css ortak arayüz tasarım sistemi
templates/         ortak şablon (base.html)
deploy/            Caddyfile, yedekleme betiği
docs/              yol haritası, kararlar, kurulum, müşteri ihtiyaç dokümanı, modül şablonu
```

## Modül sistemi
- `config/modules.py` → `DEFAULT_MODULES` veya `ERP_MODULES` ortam değişkeni hangi modüllerin açık olduğunu belirler.
- Her modülün `module.py` dosyası: `code, name, version, depends, menu, urls`.
- Açılışta `core.registry.check_dependencies()` bağımlılıkları doğrular; eksikse sistem başlamaz.
- Modülün URL'leri `/<kod>/` altına, menüsü üst menüye, `dashboard.py → widgets()` kartları ana panele otomatik eklenir.
- Modül kapatılınca `handlers.py` yüklenmez; o modülün olay tepkileri devreden çıkar.

## Olaylar (şu ana kadar)
| Olay | Yayınlayan | Yük |
|---|---|---|
| `approval.requested` | core | request |
| `approval.approved.<action>` / `approval.rejected.<action>` | core | request, user |
| `inventory.stock_moved` | inventory | move |
| `inventory.reserved` / `inventory.released` | inventory | reference, product, quantity |
| `inventory.shipped` | inventory | reference, moves |
| `inventory.count_applied` | inventory | count |
| `inventory.collect_incoming` (sorgu olayı) | inventory | product → purchase yoldaki miktarı döner |
| `partners.collect_balance` (sorgu olayı) | partners | partner → muhasebe açık bakiyeyi döner |
| `sales.order_confirmed` / `sales.order_cancelled` / `sales.status_changed` | sales | order (, status) |
| `shipping.shipment_created/picking_started/picked/packed/shipped/delivered` | shipping | order, shipment |
| `shipping.return_requested` / `shipping.return_completed` | shipping | order, return_request |
| `purchase.order_sent` / `purchase.goods_received` | purchase | order (, line, move) |

Dinleyiciler senkron çalışır ve aynı veritabanı işleminin parçasıdır (biri hata verirse tümü geri alınır).
Dış sistem çağrıları (pazaryeri, kargo, e-belge) ileride **outbox** tablosu + arka plan işçisi ile yapılacak.

## Uçtan uca hedef akış (müşteri dokümanı §1, §17)
Sipariş (sales) → `reserve()` → toplama emri (shipping) → `ship_reserved()` → fatura (accounting) → muhasebe fişi.
Her ok bir olaydır; her modül kendi adımını yapar.

## Kalıcı veri kuralları
- Quant: ürün + lokasyon + LOT + palet başına miktar ve rezerve; veritabanı kısıtları negatif stoğu engeller.
- StockMove: değiştirilemez hareket defteri; düzeltme yeni hareketle yapılır.
- AuditLog: ERP modüllerindeki her kayıt değişikliği otomatik yazılır, panelden silinemez.
