# integrations — Entegrasyonlar

Bağımlılık: core, accounting. Müşteri dokümanı §13.

- **Sağlayıcılar** `providers/`: her biri alan listesi (sihirbaz formu otomatik), `test_connection`, `handle(job)`.
  Hazır: **Uyumsoft e-Fatura/e-Arşiv** (`uyumsoft.py`). Kayıtlı ama "Yakında": Trendyol, Hepsiburada, Amazon, web sitesi,
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
**Test ortamında doğrulanacaklar:** e-Arşiv internet satışı bilgisi (InternetSalesInfo) gereksinimi, durum kodlarının eşlemesi,
gelen faturayı "alındı" işaretleme (SetInvoicesTaken).
