# Devir Notu — Projeyi devralacak yapay zekâ / geliştirici için

> Bu dosya, proje sahibiyle yapılan ilk geliştirme yazışmasının (18–19 Kasım 2026) özetidir.
> Önce `AGENTS.md`, sonra bu dosya, sonra `docs/ROADMAP.md` okunmalıdır.

## 1. Proje ve kullanıcı
- **Firma:** Eglo Kozmetik (deterjan + kozmetik, markası Clerie). Talep dokümanı: `docs/requirements/musteri-ihtiyac-dokumani.md`.
- **Amaç:** Odoo benzeri, tamamen web tabanlı, modüler ERP + WMS + CRM + muhasebe. Modüller eklenip çıkarılabilir.
- **Kullanıcı:** Teknik olmayan işletme sahibi. **Türkçe**, sade dille konuşulmalı. Kredi/token kullanımına duyarlı: gereksiz
  araştırma ve uzun açıklama yapma, işi bitir ve kısaca raporla.
- **Kullanıcının kalıcı istekleri:**
  - Arayüz şık, kullanıcı dostu, **masaüstü + tablet + telefon** uyumlu (dokunma alanı ≥44px).
  - Kurulum gerektiren her şey (entegrasyonlar) **adım adım sihirbaz** olmalı (bağlantı testi geçmeden etkinleşmez).
  - Her giriş kutusunda **ⓘ açıklama** olmalı → yeni alan eklenince `apps/core/field_help.py`'ye kısa açıklama yaz.
  - Menü/başlık metinleri tek tip, sade Türkçe ("Değiştirmek için X seçin" gibi Django metinleri kullanılmaz).
  - Menü rengi kullanıcı tarafından seçilebilir; ana panel kartları sürükle-bırak ile dizilebilir (yapıldı).
  - Formüller ve süreçler **çalışır ve test edilmiş** olmalı; her şey birbirine entegre (olay yolu).

## 2. Altyapı
- **Kod:** https://github.com/infoclerie/Eglo (main dalı). Kullanıcının Mac'inde kopya: `~/Desktop/Saha Satış Uygulaması/eglo-erp`.
- **Sunucu:** AWS Lightsail, Stockholm (eu-north-1), Ubuntu, 2 GB RAM / 2 vCPU / 60 GB, statik IP **51.21.64.247**.
  Uygulama `/opt/eglo-erp`, Docker Compose (db=PostgreSQL 16, web=gunicorn, **worker**=entegrasyon kuyruğu, caddy=HTTPS).
  Geçici adres: **https://51-21-64-247.sslip.io** (gerçek alan adı gelince: `sudo DOMAIN=erp.eglokozmetik.com bash deploy/bootstrap.sh`).
  Lightsail güvenlik duvarında 22/80/443 açık. Günlük yedek 02:30 (`deploy/backup.sh`, cron).
- **Güncelleme (sunucuda):** `cd /opt/eglo-erp && sudo git pull && sudo docker compose up -d --build` (migrate + roller otomatik).
- **Notlar:** Canlıya geçmeden 8 GB plana çıkılmalı. Sunucu AB'de → KVKK yurt dışı aktarım konusu hukukçuya danışılmalı (kullanıcıya söylendi).
- Yönetici kullanıcı adı Türkçe klavye yüzünden **`admın`** (noktasız ı) olarak oluşturuldu.
- Şifre/API anahtarı asla sohbete veya koda yazılmaz; sihirbazdan girilir, veritabanında şifreli (Fernet, SECRET_KEY'den) tutulur.

## 3. Yapılanlar (hepsi testli — `python manage.py test`, 74 test)
core (modül sistemi, olay yolu, işlem logu, onay akışı, roller, numara serisi, görünüm/tema, panel düzeni) · catalog · inventory
(LOT/SKT/FEFO, rezervasyon, sayım, satın alma önerisi) · partners · sales (kampanyalar, mükerrer engeli, kredi limiti) ·
shipping (barkodlu toplama, tartı, sevk, iade) · purchase (teklif, onay, mal kabul, ortalama maliyet) · accounting (otomatik
e-Fatura/e-Arşiv faturası, UBL-TR, cari, tahsilat, hakediş, kârlılık) · integrations (sihirbaz, iş kuyruğu, Uyumsoft, Trendyol) · portal (bayi portalı) · crm · kargo etiketi · ana panel grafikleri/kur şeridi · Excel'e aktarma.
Ayrıntılar her modülün `apps/<modül>/MODULE.md` dosyasında.

## 4. Gerçek sistemlerde doğrulanan bilgiler (değiştirmeden önce oku)
- **Uyumsoft** (kullanıcının muhasebe/e-belge entegratörü): `apps/integrations/MODULE.md` "Uyumsoft" bölümü. Test ortamında
  kendi UBL-TR e-Arşiv faturamız **kabul edildi**. Test hesabı Uyumsoft/Uyumsoft, VKN 9000068418. `GetSystemDate` soapAction'ı
  `ICustomerServiceBase` altında. Gelen listede InvoiceId = numara, DocumentId = ETTN. Kullanıcı sihirbazı test ortamında başarıyla bağladı.
- **Trendyol:** v2 sipariş uç noktası zorunlu (15.10.2026), User-Agent `{SatıcıId} - SelfIntegration`. Henüz gerçek mağazaya
  bağlanmadı. İlk canlı bağlantıda **stok/fiyat gönderimi kapalı** başlatılmalı (kullanıcıya söylendi).

## 5. Sıradaki işler (öncelik sırası)
1. Trendyol canlı bağlantı kontrolü; kargo takip no bildirimi (`/tracking-details`), iadeler (claims), fatura linki.
2. **Hepsiburada** sağlayıcısı (`providers/` altında Trendyol örneğiyle aynı yapı + sihirbaz alanları).
3. **Kargo firması API'leri** (Yurtiçi, Aras, MNG): gönderi oluşturma + takip no; yazdırılabilir etiket hazır (`shipping`). Firma anlaşma/API bilgileri kullanıcıdan alınacak.
4. CRM ve bayi portalı hazır; kalan: SMS/e-posta kampanya gönderimi (İYS).
5. **Üretim / fason** (§10): reçete (BOM), üretim emri, hammadde sarfı (`production_consume` hareket türü hazır), kalite kontrol → karantina.
6. **Raporlar** (§11): Excel/PDF, stok yaşlandırma, devir hızı, kanal ciro grafikleri; bildirimler (§15, e-posta).
7. Excel ile toplu ürün/fiyat/stok içe aktarma (§16).

## 6. Çalışma şekli
- Kurallar `AGENTS.md`'de. Kısaca: modül sınırı, stok sadece `inventory/services.py`'den, onaylı işlemler `approvals`, formül + test,
  Decimal, Türkçe arayüz, her değişiklikte `MODULE.md`/`ROADMAP.md` güncelle, testler geçmeden gönderme.
- Değişiklik GitHub'a gönderilir → kullanıcı sunucuda güncelleme komutunu çalıştırır.
- Arayüzde yeni ekran: `templates/base.html`'i genişlet, `static/css/app.css` sınıflarını kullan (`page-head`, `card`, `table`,
  `badge`, `btn`, `steps`, `form`). Yönetim paneli ekranları otomatik aynı görünümü alır.

## 7. Dikkat: Türkçe sayı biçimi
Şablonlarda sayılar "54,00" (virgüllü) görünür. Form `value` alanlarına sayı basarken `|unlocalize` kullanın; kullanıcı girdisinde virgülü noktaya çevirin.

## 8. Ek arayüz altyapısı
- Ana panele grafik eklemek: modülün `dashboard.py` dosyasına `charts(request)` → `[{key,title,type(line|bar|doughnut),labels,data,wide}]`.
- Yönetim listeleri: filtre çubuğu `static/js/admin-grid.js`, Excel `apps/core/export.py` (`?_export=xlsx` ve 'Seçilenleri Excel'e aktar').
- Uygulama tabloları: `static/js/tables.js` sütun filtresi + CSV (Excel uyumlu) otomatik eklenir (`data-grid="off"` ile kapatılır).
- Kurlar: `apps/core/rates.py` (truncgil + TCMB yedek, 5 dk önbellek).
