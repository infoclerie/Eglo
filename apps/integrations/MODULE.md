# integrations — Entegrasyonlar

Bağımlılık: core, accounting. Müşteri dokümanı §13.

- **Sağlayıcılar** `providers/`: her biri alan listesi (sihirbaz formu otomatik), `test_connection`, `handle(job)`.
  Hazır: **Uyumsoft e-Fatura/e-Arşiv** (`uyumsoft.py`), **Trendyol** (`trendyol.py`). Kayıtlı ama "Yakında": Hepsiburada, Amazon, web sitesi,
  Yurtiçi/Aras/MNG kargo, banka.
- **Sihirbaz** `/integrations/new/`: bağlantı bilgileri → şirket bilgileri → bağlantı testi (başarısızsa ilerlenmez) →
  ayarlar → özet → etkinleştir. Düzenleme aynı sihirbazla (`?edit=<id>`).
- **Şifreler** veritabanında Fernet ile şifreli (anahtar DJANGO_SECRET_KEY'den). SECRET_KEY değişirse şifreler yeniden girilmeli.
- **İş kuyruğu** `IntegrationJob`: tekillik anahtarı (mükerrer engeli), 2^n dakika aralıkla yeniden deneme, en fazla 5 deneme,
  başarısız işler ekrandan "Yeniden dene". Her işlem `SyncLog`'a yazılır.
- **İşçi:** `python manage.py run_jobs --loop` (docker-compose `worker` servisi). Periyodik: gelen e-fatura çekme, gönderilen
  faturaların durum sorgusu.

## Uyumsoft
Uç noktalar: test `https://efatura-test.uyumsoft.com.tr/Services/Integration` (Uyumsoft/Uyumsoft), canlı `https://efatura.uyumsoft.com.tr/Services/Integration`.
SOAP 1.1 + WS-Security UsernameToken. Metotlar: GetSystemDate, IsEInvoiceUser, SendInvoice (InvoiceInfo: Invoice UBL-TR,
TargetCustomer, EArchiveInvoiceInfo DeliveryType=Electronic, Scenario eInvoice|eArchive), GetInboxInvoiceList, QueryOutboxInvoiceStatus.
**Test ortamında doğrulandı (19.11.2026):** kimlik doğrulama (UsernameToken+Timestamp), GetSystemDate (soapAction `ICustomerServiceBase`), IsEInvoiceUser, GetInboxInvoiceList (her fatura bir `<Items>`; InvoiceId = numara, DocumentId = ETTN), SendInvoice e-Arşiv (bizim UBL-TR'miz kabul edildi; test hesabı VKN 9000068418). Durum kodları: 1000 Approved, 2000 Error.
**Hâlâ doğrulanacaklar:** e-Arşiv internet satışı bilgisi (InternetSalesInfo) gereksinimi, durum kodlarının eşlemesi,
gelen faturayı "alındı" işaretleme (SetInvoicesTaken).

## Trendyol
Kaynak: developers.trendyol.com (Kasım 2026). Taban `https://apigw.trendyol.com/integration` (stage: `stageapigw`, IP yetkisi ister).
Basic auth (API Key/Secret) + `User-Agent: {SatıcıId} - SelfIntegration` (yoksa 403).
- `trendyol.import_orders`: `GET /order/sellers/{id}/v2/orders?status=Created` (v2 zorunlu; en fazla 2 hafta pencere, son 1 ay, sayfa ≤200).
  Her paket = bir sipariş (`external_ref` = shipmentPackageId → mükerrer yok). Fiyat KDV dahil gelir → KDV hariçe çevrilir.
  Ürün eşleşmezse iş hata verir (ekranda görünür); `/integrations/<id>/listings/` ile eşleştirilip yeniden denenir.
  Stok yetmezse sipariş "Yeni" kalır (havuzda görünür), iş başarısız olmaz.
- `trendyol.push_stock`: `POST /inventory/sellers/{id}/products/price-and-inventory` (≤1000/istek). Miktar = satışa uygun − güvenlik payı;
  fiyat = Trendyol kanal fiyatı × (1+KDV). Periyodik + stok değişiminde (dakikada en fazla bir) tetiklenir.
- `trendyol.update_status`: toplama başlayınca `Picking`, fatura kesilince `Invoiced` (params.invoiceNumber).
Sıradaki: kargo takip numarası bildirimi (`/tracking-details`), iade (claims), fatura linki gönderimi, hakediş raporu.
