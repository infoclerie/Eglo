# catalog — Ürün Kartları

Bağımlılık: core. Müşteri dokümanı §2.

Modeller: Brand, Category (ağaç), SalesChannel, Product, ProductPrice (kanal fiyatı), KitComponent (set içeriği).

Kurallar:
- SKU, barkod ve koli barkodu benzersiz.
- `kind = kit` ürün fiziksel stok tutmaz; satışta bileşenleri düşer (inventory). Set içine set eklenemez.
- `price_for(channel)` kanal fiyatı yoksa liste fiyatını döner. Fiyatlar KDV hariç.
- Stok parametreleri (min/max/güvenlik stoğu, tedarik süresi) inventory hesaplarında kullanılır.

Sıradaki: Excel ile toplu ürün açılışı ve toplu fiyat güncelleme; fiyat değişikliğinin onaya bağlanması (§12).
