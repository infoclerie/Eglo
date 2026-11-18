# portal — Bayi Portalı

Bağımlılık: core, catalog, inventory, partners, sales, accounting. Müşteri dokümanı §8.6. Adres: `/portal/`.

- **Kullanıcı:** Yönetim › Bayi Portalı › Bayi kullanıcıları › Ekle (cari + kullanıcı adı + ilk şifre). Bayi personel değildir
  (is_staff=False), "Bayi" grubundadır; ana sayfaya girince portala yönlenir, iç ekranlar 403 verir.
- **Katalog:** bayiye özel fiyat (`sales.unit_price` — bayinin fiyat kanalı + iskonto, KDV hariç), stok etiketi
  (Stokta / Az stok ≤ min. stok / Tükendi), koli içi adet, aktif kampanyalar, güncel bakiye.
- **Sepet → sipariş:** `services.place_order` vadeli sipariş açar ve onaylar (stok ayrılır, toplamaya düşer, sevkte fatura).
  Kredi limiti aşılırsa sipariş "Yeni" kalır + otomatik onay talebi; stok yetmezse "Yeni" kalır. Minimum tutar: `portal.min_order_amount`.
- **Siparişlerim / Faturalarım (XML) / Cari ekstre:** yalnızca kendi carisi (başka bayinin kaydı 404).
Sıradaki: fatura PDF görünümü, tekrar sipariş ("aynısını sipariş et"), bayiye özel duyurular.
