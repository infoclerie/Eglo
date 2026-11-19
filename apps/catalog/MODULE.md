# catalog — Ürün Kartları

Bağımlılık: core. Müşteri dokümanı §2.

Modeller: Brand, Category (ağaç), SalesChannel, Product, ProductPrice (kanal fiyatı), KitComponent (set içeriği).

Kurallar:
- SKU, barkod ve koli barkodu benzersiz.
- `kind = kit` ürün fiziksel stok tutmaz; satışta bileşenleri düşer (inventory). Set içine set eklenemez.
- `price_for(channel)` kanal fiyatı yoksa liste fiyatını döner. Fiyatlar KDV hariç.
- Stok parametreleri (min/max/güvenlik stoğu, tedarik süresi) inventory hesaplarında kullanılır.

Sıradaki: Excel ile toplu ürün açılışı ve toplu fiyat güncelleme; fiyat değişikliğinin onaya bağlanması (§12).

## Ürün fotoğrafları
- `ProductImage` (çoklu, ana görsel). `services.add_image`: doğrular, telefon yönüne göre döndürür, 1600 px JPEG + 360 px önizleme.
- Yükleme yerleri: Mal kabul formu, satın alma mal kabul (satır başına), `/catalog/<id>/fotograflar/` (ana görsel / sil),
  barkod sorgu ekranından bağlantı. Ortak seçici `templates/partials/photo_input.html` (telefonda kamera açar) + `static/js/photos.js`.
- Gösterim: ürün listesi küçük resim, ürün kartı, barkod sorgu, toplama ekranı, bayi portalı kataloğu.
- Canlıda dosyalar `media` biriminde; Caddy `/media/*` yolunu doğrudan sunar; `media-init` servisi klasör sahipliğini düzeltir.
  Yedek: backup.sh pazar günleri media arşivi alır.
