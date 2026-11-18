# Mimari Karar Günlüğü

Yeni karar en alta eklenir: tarih, karar, neden, alternatif.

**2026-11-18 · Django + PostgreSQL.** Yaygın, okunması kolay, Odoo ile aynı dil (Python). Yönetim paneli, ORM,
migration ve yetki sistemi hazır. Alternatif: Node/NestJS + React (daha fazla kod, iki ayrı proje).

**2026-11-18 · Sunucu tarafı HTML, SPA yok.** Daha az kod ve bakım; el terminali ve bayi portalı mobil uyumlu web.
Etkileşim gereken ekranlarda HTMX eklenecek. Başlangıçta arka ofis ekranları Django yönetim paneli üzerinden.

**2026-11-18 · Modüller arası iletişim olay yolu ile, senkron.** Stok/fatura tutarlılığı için tüm tepkiler aynı
transaction içinde. Dış sistem çağrıları outbox ile işlem sonrasına alınacak.

**2026-11-18 · Odoo benzeri Quant + StockMove modeli.** Anlık stok (Quant) ve değiştirilemez hareket defteri (StockMove).
Sanal lokasyonlar (tedarikçi, müşteri, üretim, sayım farkı, fire) stok tutmaz, hareketin karşı tarafıdır.

**2026-11-18 · FEFO + SKT blokajı.** Rezervasyon SKT'si en yakın LOT'tan başlar; SKT geçmiş LOT satılamaz/sevk edilemez,
satışa uygun lokasyona alınamaz; onay penceresindeki (varsayılan 30 gün) LOT yalnızca `allow_near_expiry=True` ile satılır.
Eşikler `Sistem ayarları > inventory.expiry_thresholds` ile değiştirilebilir.

**2026-11-18 · Set ürün fiziksel stok tutmaz.** Set satışında bileşenler rezerve edilir ve düşer; set için satılabilir
adet = min(bileşen stoğu / set içi miktar).

**2026-11-18 · Muhasebe hem içeride hem dışa aktarım.** Cari, fatura, tahsilat ve kârlılık sistemin içinde;
resmi defter için mevcut muhasebe programına fiş/fatura aktarımı (müşteri kararı).

**2026-11-19 · Tek `Partner` cari modeli.** Müşteri, bayi, tedarikçi ve fason üretici aynı tabloda (tür + grup); muhasebe cari hesabı buna bağlanır.

**2026-11-19 · Stok sevkte düşer.** Onayda rezerve, `shipping.ship` anında `ship_reserved` ile düşer; paketlenmiş ama sevk edilmemiş ürün stokta görünür (rezerve).

**2026-11-19 · Ortak arayüz tasarım sistemi + sihirbazlar.** Tek CSS dosyası ve ikon/rozet etiketleri; kurulum gerektiren işler adım adım sihirbaz.

**2026-11-19 · Uyumsoft için elle SOAP (requests).** WSDL'den kod üretimi yerine UBL-TR'yi kendimiz üretip SendInvoice zarfına koyuyoruz; bağımlılık az, test edilebilir (sahte HTTP ile).

**2026-11-19 · Dış sistem işleri kuyrukta.** Fatura kesme işlemi entegratör kapalıyken de tamamlanır; gönderim kuyrukta yeniden denenir.

**2026-11-19 · Arayüz her cihazda Türkçe.** LocaleMiddleware kaldırıldı; tarayıcı dili ne olursa olsun Türkçe.
