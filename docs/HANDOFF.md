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
1. Canlı doğrulama: Hepsiburada (Merchant ID + servis anahtarı + User-Agent), ikas (özel uygulama), Trendyol/HB hakediş çekimi.
   Mevcut Trendyol bağlantısında "Hakediş çek" ayarı kapalı gelir → Ayarları düzenle'den açılmalı.
2. **Kargo firması API'leri** (Yurtiçi, Aras, MNG): gönderi oluşturma + takip no; etiket hazır. Testler kullanıcı tarafından ertelendi.
3. Telefon kamerasıyla barkod okuma (el terminalinin 2. aşaması; şu an USB okuyucu, `static/js/scanner.js`).
4. Amazon, banka hesap hareketleri, pazaryeri iade (claims) çekimi, Trendyol fatura linki.
5. Rapor ekleri: palet doluluk, satın alma performansı; resmi muhasebe fişi aktarımı.

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

## Bildirimler + canlı sohbet (son eklenen)
- notifications modülü: Bildirim merkezi (olay başına ekran/e-posta/SMS seçimi, şablonları kullanıcı yazar). Müşteri bildirimleri kapalı başlar.
- E-posta (SMTP) ve SMS (Netgsm) sağlayıcıları Entegrasyonlar › Yeni bağlantı › Bildirim sihirbazında. Netgsm canlı hesapla doğrulanmadı.
- chat modülü: yoklama (polling) ile çalışır, sunucuya ek kurulum yok. Yeşil/kırmızı nokta = son 60 sn içinde aktif mi.
- Test sayısı: 95.
- E-posta sihirbazı: ilk adımda servis kartları (notify.MAIL_PRESETS: Gmail, Workspace, M365, Outlook.com, Yandex, Zoho, Yahoo, iCloud, hosting/cPanel, Brevo, SES, SendGrid, Mailgun, Mailjet, Diğer). Seçim sunucu/port/güvenliği doldurur, servis notu gösterilir; SMTP hataları friendly_smtp_error ile Türkçeleştirilir. Yeni servis = listeye bir satır. Microsoft 365: Aralık 2026 sonundan itibaren SMTP AUTH (şifreyle giriş) varsayılan kapalı, yönetici açabilir.

## Kasım 2026 (2) eklenenler
- Entegrasyonlar: Hepsiburada, ikas, Trendyol+HB hakediş çekimi (accounting.upsert_settlement). Bkz. apps/integrations/MODULE.md.
- Yeni modüller: production (üretim/fason), reports (raporlar), imports (Excel toplu yükleme). CRM'e İYS uyumlu kampanyalar.
- Yeni rol: "Üretim sorumlusu". Kullanıcı kararı: kampanya kurgusu (Trendyol kampanyaya katılım vb.) pazaryeri panelinde kalır;
  sonuçları (satış, kesinti, hakediş) bu sisteme gelir.
- Test sayısı: 115.
- Ürün fotoğrafları (catalog.ProductImage): mal kabulde telefondan çekilip yüklenir; bkz. apps/catalog/MODULE.md. Test sayısı: 118.
- Kullanıcı kararı: kargo firması testleri en sona bırakıldı.

## Yedekler / taşıma (Kasım 2026)
- `apps/core/backups.py`: yedek = zip (meta.json + data.json [dumpdata, natural foreign keys] + media/). Geri dönüş: flush + loaddata
  tek transaction, sonra fotoğraflar değişir; öncesi otomatik yedek (son 10 saklanır). Ekran: Sistem › Yedekler (süper kullanıcı).
- Test verisi temizliği: her modülün MANIFEST["reset_data"] grupları (modeller + numara serileri). Yeni modülde hareket tablosu
  eklerseniz buraya ekleyin. Ana veriler (ürün, cari, depo, reçete, ayarlar, kullanıcılar) silinmez.
- Komutlar: `create_backup`, `restore_backup <zip> --yes`; sunucuda `deploy/restore.sh` (taşıma adımları docs/DEPLOY.md).
- Entegrasyon şifreleri DJANGO_SECRET_KEY'den türeyen anahtarla şifreli → taşımada .env'deki anahtar da taşınmalı (meta'da parmak izi).
- Yedekten dönünce bekleyen entegrasyon işleri durdurulur (`core.restored` olayı). PostgreSQL ve SQLite'da test edildi. Test: 122.

## Yapay zekâ asistanı (Kasım 2026)
- assistant modülü + integrations/providers/ai.py (Claude, OpenAI uyumlu). Bkz. apps/assistant/MODULE.md. Canlı API anahtarıyla henüz denenmedi (istek biçimleri sahte yanıtlarla test edildi). Test: 128.

## Kasım 2026 (3)
- Kanal paneli sadeleştirildi: "Şimdi güncelle" (sipariş + açıksa stok + hakediş), otomatik işler tablosu, sayfa 5 dk'da yenilenir.
- Ürün aktarımı ortak: `providers/common.upsert_product` (ikas, Trendyol `/product/sellers/{id}/products/approved`), fotoğraf
  indirme (`fetch_image`, kaynak adresiyle tekrar indirmez), HTML açıklama temizliği. Hepsiburada: listing → SKU eşleştirme
  (HB API ürün adı/görsel vermez). ikas görsel adresi `cdn.myikas.com/images/{merchantId}/{imageId}/image_1080.webp` —
  dokümanda yok, canlıda doğrulanmalı.
- İşlem geçmişi `/islem-gecmisi/` (core.activity): AuditLog + 'core.collect_activity' olayıyla entegrasyon/stok/sipariş satırları.
  Gürültülü teknik modeller audit.SKIP_MODELS'ta.
- Fatura: notlar (yazıyla tutar "Yalnız #…#", e-Arşiv'de "İrsaliye yerine geçer."), alıcı ilçe/il adresin son satırından,
  boş TCKN → 11111111111. Önizleme `/accounting/invoices/<id>/onizleme/` (GİB görünümüne yakın, yazdırılabilir, "Doğru, gönder").
  Uyumsoft'ta "otomatik gönder" kapatılırsa her fatura önizlenip elle gönderilir. Gönderilmiş faturada Uyumsoft doğrulama linki.
- Ana panel: aktif ürün, stoktaki ürün/adet, kanal başına "bugün sipariş" kartları; boş grafiklerde açıklama; TL biçimi (core/formats.py).
- Test: 135.

- Aktif kullanıcılar `/ayarlar/aktif-kullanicilar/` (core.UserActivity + UserActivityMiddleware; IP = X-Forwarded-For ilk değeri, Caddy arkasında). ikas stok: v2 `listProductStockLocation`. Test: 137.

## Sanal Ofis (Kasım 2026)
- Kullanıcı isteği: "şirketi 3B ofis olarak göster, çalışanlar masada/iş akışında hareket etsin, tıklayınca canlı veri; ayrı sekmede tam ekran izleyeyim".
- `apps/office` + `static/vendor/three/` (three.js r170, MIT). Menüde "Sanal ofis (3B) ↗" yeni sekmede açılır.
- Kişi sayısı rol gruplarındaki gerçek kullanıcılardan gelir; boşsa örnek unvanlar. Ayrıntı: `apps/office/MODULE.md`.

## Yol haritası + güncelleme sistemi (25 Kasım 2026)
- Kaynak: kullanıcının `EGLO_ERP_Gelistirme_Yol_Haritasi.docx` dosyası (katalog, depo, cari, satış/muhasebe).
- Katalog: kendi ekranları (`/catalog/`): liste, detay, yeni/düzenle; fotoğraf ilk ekrandan, set (kit) bileşenleri, bağlı
  kategori (`alt-kategoriler/` AJAX), kanal fiyatları. Cari: `/partners/` liste/detay/yeni/düzenle, VKN (10) / TCKN (11) doğrulama.
- Depo: `python manage.py check_critical_stock [--email ...] [--dry-run]` — min. stok altı + SKT yaklaşan LOT raporu,
  alıcılar `Setting inventory.critical_stock_emails` (virgüllü), gönderim aktif e-posta entegrasyonu kuyruğuyla.
- Satış: sipariş havuzunda kanal çipleri, `/sales/<id>/` sipariş detay (satırlar, durum geçmişi, müşteri).
- YAPILMADI (sıradaki): cari çoklu e-posta + PDF ek + koşullu onay + otomatik gönderim; koli barkodlu transfer ekranı;
  kanal bazlı sipariş→tahsilat (hakediş eşleştirme) raporu; kritik stok komutunu zamanlanmış işe bağlama.
- Güncelleme sistemi (Ayarlar › Güncellemeler): web yalnız talep bırakır (`updates/request.json` veya `updates/pending/*.zip`);
  host'ta root crontab `* * * * * /opt/eglo-erp/deploy/auto-update.sh` git pull / zip açma → `docker compose build` → `up -d`
  yapar, adımları `updates/progress.json` + `update.log`'a yazar; sayfa `/ayarlar/guncellemeler/durum/` ile 2 sn'de bir izler.
  Neden: web container `app` kullanıcısıyla çalışır, kod imajın içindedir → web'den dosya yazarak güncelleme yapılamaz.
  Zip, `unzip` yerine Python ile açılır (sunucuda unzip yok). `updates/` git dışıdır.
- Rehber (PROJE_REHBERI_AI.md / Yedekler › Rehberi indir) her indirmede canlı üretilir ve `updates/changelog.md`
  (auto-update.sh'nin yazdığı son 40 commit) "Son değişiklikler" bölümü olarak eklenir. Yeni iş bitince bu dosyaya not düşün.
