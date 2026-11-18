# notifications — Bildirim merkezi

- `events.py`: olay kataloğu (EVENTS). Her olay: etiket, hedef (customer/staff), yer tutucular, varsayılan konu/metin/SMS.
- `NotificationRule`: olay başına kanal seçimi (ekran içi / e-posta / SMS), grup, aktif, kullanıcı tarafından düzenlenen şablon.
  Müşteri kuralları KAPALI başlar; personel kuralları ekran içi açık başlar. `setup_notifications` eksik kuralları oluşturur.
- `services.notify(event, fields, url, customer, once_key)`: şablonu doldurur, zil bildirimi yazar, e-posta/SMS işini
  `integrations` kuyruğuna atar (`notify.email` / `notify.sms`, sağlayıcı: SMTP / Netgsm sihirbazdan kurulur).
- `handlers.py`: diğer modüllerin olaylarını dinler (sipariş, sevkiyat, fatura, tahsilat, onay, düşük stok, entegrasyon hatası, yeni cari).
- Ekranlar: `/notifications/` (bildirimlerim), `/notifications/merkez/` (kanal seçimi), `/notifications/merkez/<id>/` (şablon + önizleme).
- Yeni olay eklemek: EVENTS'e ekle → handler'da `notify()` çağır → `setup_notifications`.
- SMS yalnız işlemsel (İYS onayı gerektiren pazarlama SMS'i burada yok).
