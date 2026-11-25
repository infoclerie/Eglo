# EGLO ERP — Yapay zekâ için proje rehberi

> **Bu dosyayı okuyan yapay zekâya:** Bu, Eglo Kozmetik için yazılmış web tabanlı, modüler bir ERP + depo (WMS) + CRM +
> muhasebe sisteminin TAM tanımıdır. Kaynak kod: https://github.com/infoclerie/Eglo (main dalı).
> Önce "Bölüm 1 · Kurallar" ve "Bölüm 2 · Devir notları"nı okuyun; kod değiştirmeden önce ilgili modülün MODULE.md
> bölümüne bakın. Kullanıcı Türkçe konuşur, teknik olmayan bir işletme sahibidir: cevaplarınız Türkçe, sade ve adım adım olsun.
> Güncelleme: değişiklikleri GitHub main dalına gönderin; kullanıcı Ayarlar › Güncellemeler › «GitHub'dan güncelle» ile uygular
> (SSH gerekmez). GitHub'a erişiminiz yoksa `files/` + `meta.json` içeren zip paketi üretin (bkz. deploy/build-update.sh).
> Şifre / API anahtarı ASLA sohbette istenmez; kullanıcı bunları sistemdeki sihirbazlara kendisi girer.

Oluşturulma: 25.11.2026 17:33 · Dosya sistem tarafından otomatik üretildi (Sistem › Yedekler › "Yapay zekâ rehberini indir").

---

## Bölüm 1 · Kurallar (AGENTS.md)

<!-- kaynak: AGENTS.md -->

# AGENTS.md — Bu projede çalışacak her yapay zekâ ve geliştirici için kurallar

Bu dosyayı **ilk** okuyun. Sonra sırasıyla: `docs/HANDOFF.md` (proje geçmişi, kullanıcı istekleri, sunucu) → `ARCHITECTURE.md` → `docs/ROADMAP.md` → `docs/DECISIONS.md` →
üzerinde çalışacağınız modülün `apps/<modül>/MODULE.md` dosyası. Müşteri ihtiyaçlarının tam metni:
`docs/requirements/musteri-ihtiyac-dokumani.md`.

## Proje
Eglo Kozmetik (deterjan + kozmetik) için web tabanlı, modüler ERP + WMS + CRM + muhasebe.
Örnek alınan ürün: Odoo. Teknoloji: Python 3.12, Django 5.2, PostgreSQL 16, sunucu tarafı HTML (+ ileride HTMX).

## Altın kurallar
1. **Modül sınırı:** Her iş alanı `apps/<kod>/` altında bir Django uygulamasıdır ve `module.py` içinde `MANIFEST` taşır.
   Bir modül başka bir modülün **modellerine yazmaz**. Okuma için o modülün `services.py` fonksiyonlarını,
   tepki için **olayları** (`apps/core/events.py`) kullanır.
2. **Stok sadece `apps/inventory/services.py` ile değişir.** Quant / StockMove / Reservation tablolarına başka yerden yazılmaz.
3. **Onay gerektiren işlemler** (stok düzeltme, fiyat değişikliği, iptal, iade, limit artırma, fatura iptali, fire)
   `apps/core/approvals.request_approval()` ile talep oluşturur; işlem `approval.approved.<kod>` olayında yapılır.
4. **Her formül** bir `services.py` fonksiyonudur, docstring'inde formül yazılıdır ve **testi vardır**
   (müşteri dokümanındaki örnek sayılarla).
5. **Para ve miktar** her zaman `Decimal`; asla `float`.
6. **Dil:** Kod tanımlayıcıları İngilizce, kullanıcıya görünen her metin (verbose_name, mesaj, şablon) Türkçe.
7. **Migration:** Model değişikliğinde `python manage.py makemigrations <modül>`; mevcut migration dosyaları düzenlenmez.
8. **Güvenlik:** Gizli bilgi koda yazılmaz (`.env`). Her görünüm `login_required` + uygun `permission_required` kullanır.
9. **Test:** Değişiklikten sonra `python manage.py test` tamamen geçmeli.
10. **Belge:** Bir modülde davranış değiştiyse aynı committe `MODULE.md`, gerekiyorsa `docs/ROADMAP.md` ve
    önemli tasarım kararıysa `docs/DECISIONS.md` güncellenir.
11. **Arayüz:** Her yeni giriş alanının açıklaması `apps/core/field_help.py`ye (ⓘ simgesi); ekranlar masaüstü/tablet/telefon uyumlu.

## Yeni modül ekleme (kısa)
`docs/MODULE_TEMPLATE.md` dosyasını izleyin: klasör + `module.py` + `apps.py` (label = kod) + `MODULE.md` + testler,
sonra `config/modules.py` listesine ekleyin, `makemigrations`, `migrate`, rollere izin (`apps/core/roles.py`) → `setup_roles`.

## Sık komutlar
```bash
python manage.py test              # tüm testler
python manage.py modules           # açık modüller ve bağımlılıklar
python manage.py seed_demo         # örnek depo/ürün verisi
python manage.py setup_roles       # rol/izin güncelle
```
12. Yeni bir hareket (işlem) tablosu eklerseniz modülün MANIFEST'indeki `reset_data` grubuna ekleyin (Yedekler › Test verilerini temizle).
13. Dokümanlar değişince tek dosyalık rehberi yenileyin: `python manage.py build_ai_context --no-live` (kökteki PROJE_REHBERI_AI.md). Canlı sistemde Yedekler ekranından ve her yedeğin içinden de alınır.

---

## Bölüm 2 · Devir notları ve kaldığımız yer (HANDOFF.md)

<!-- kaynak: docs/HANDOFF.md -->

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

---

## Bölüm 3 · ARCHITECTURE.md

<!-- kaynak: ARCHITECTURE.md -->

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
apps/accounting/   fatura (UBL-TR), cari hareket, tahsilat, hakediş, kârlılık
apps/integrations/ sihirbaz, sağlayıcılar (Uyumsoft), iş kuyruğu, işçi
static/css/        app.css (tasarım sistemi), admin.css (yönetim paneli uyarlaması)
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
| `accounting.invoice_ready/sent/cancelled`, `accounting.incoming_invoice` | accounting | invoice |
| `accounting.send_requested` | accounting | invoice → integrations iş kuyruğuna alır |

Dinleyiciler senkron çalışır ve aynı veritabanı işleminin parçasıdır (biri hata verirse tümü geri alınır).
Dış sistem çağrıları `integrations` iş kuyruğu + arka plan işçisi (`worker` servisi) ile işlem sonrasında yapılır.

## Uçtan uca hedef akış (müşteri dokümanı §1, §17)
Sipariş (sales) → `reserve()` → toplama emri (shipping) → `ship_reserved()` → fatura (accounting) → muhasebe fişi.
Her ok bir olaydır; her modül kendi adımını yapar.

## Kalıcı veri kuralları
- Quant: ürün + lokasyon + LOT + palet başına miktar ve rezerve; veritabanı kısıtları negatif stoğu engeller.
- StockMove: değiştirilemez hareket defteri; düzeltme yeni hareketle yapılır.
- AuditLog: ERP modüllerindeki her kayıt değişikliği otomatik yazılır, panelden silinemez.

---

## Bölüm 4 · docs/ROADMAP.md

<!-- kaynak: docs/ROADMAP.md -->

# Yol Haritası

Durum: ✅ tamam · 🟡 kısmi · ⬜ başlanmadı. Sıra müşteri dokümanı §19'a göre.

| # | Modül (kod) | Kapsam | Durum |
|---|---|---|---|
| 0 | Çekirdek (`core`) | modül sistemi, olay yolu, işlem logu, onay akışı, roller, numara serisi, ana panel | ✅ |
| 1 | Ürün kartları (`catalog`) | SKU/barkod, koli/palet, kanal fiyatı, set/kampanya paketi | ✅ (toplu Excel içe aktarma ⬜) |
| 2 | Depo ve stok (`inventory`) | depo/lokasyon, LOT/SKT, FEFO, rezervasyon, transfer, sayım+onay, stok durumları, uyarılar, satın alma önerisi formülü, barkod sorgu | ✅ (palet doluluk raporu, stok yaşlandırma ⬜) |
| 3 | Sipariş (`sales`) + Cari (`partners`) | merkezi sipariş havuzu, kanallar, 13 durum, kampanyalar, mükerrer engeli, kredi limiti, onaylı iptal | ✅ |
| 4 | Sevkiyat (`shipping`) | toplama listesi, barkod doğrulama, paketleme+tartı, sevk, teslim, çoklu toplama, iade (hijyen kuralı, onay) | ✅ (yazdırılabilir barkodlu etiket ✅; kargo firması API'leri ⬜) |
| 5 | Muhasebe (`accounting`) | otomatik satış faturası (e-Fatura/e-Arşiv seçimi, GİB numarası, UBL-TR), iade faturası, alış faturası 3'lü eşleştirme, cari hareket/ekstre, tahsilat/ödeme, vadesi geçmiş, nakit akışı, hakediş mutabakatı, ürün kârlılığı, onaylı iptal | ✅ (resmi fiş aktarımı ⬜) |
| 6 | Satın alma (`purchase`) | talep, öneri, teklif karşılaştırma, onaylı sipariş, mal kabul, ortalama maliyet, tutanak, performans | ✅ (fatura eşleştirme → muhasebe) |
| 7 | Bayi portalı (`portal`) · CRM (`crm`) | bayi portalı ✅; fırsat panosu, aktivite/hatırlatma, segmentler ✅; İYS uyumlu e-posta/SMS kampanya ✅ | ✅ |
| 8 | Üretim ve fason (`production`) | BOM, üretim emri, FEFO malzeme ayırma, sarf, fason, karantina + kalite onayı, maliyet | ✅ |
| 9 | Raporlama (`reports`) | stok yaşlandırma, devir hızı, kanal/ürün kârlılığı, SKT; Excel/PDF | ✅ |
| 9b | Toplu yükleme (`imports`) | Excel ile ürün, fiyat, stok (önizleme + hata kontrolü) | ✅ |
| 10 | Entegrasyonlar (`integrations`) | sihirbaz, şifreli bilgiler, iş kuyruğu + yeniden deneme + loglar, arka plan işçisi; **Uyumsoft e-Fatura/e-Arşiv** ✅ (test ortamında doğrulandı); **Trendyol** ✅, **Hepsiburada** ✅, **ikas** ✅ (sipariş/stok/fiyat/durum + hakediş çekimi; HB/ikas canlı doğrulama bekliyor); Amazon, kargo, banka ⬜ | 🟡 |
| — | Bildirimler (`notifications`) · Sohbet (`chat`) | bildirim merkezi, e-posta/SMS sihirbazı, canlı sohbet | ✅ |
| — | Sanal Ofis (`office`) | three.js 3B canlı ofis: departmanlar, gerçek/örnek çalışanlar, tıklanınca canlı veri, iş akışı animasyonları, tam ekran sekme | ✅ |

## Açık sorular (müşteriye)
- Muhasebe/e-belge: **Uyumsoft** (cevaplandı). Uyumsoft canlı kullanıcı bilgileri ve seri ön ekleri müşteriden alınacak.
- Dış lojistik deposu kullanılacak mı, API'si var mı?
- El terminali: bilgisayara bağlı USB okuyucu (klavye modu) — `static/js/scanner.js` (cevaplandı). Telefon kamerasıyla okuma: sonraki aşama.

## Arayüz
Ortak tasarım sistemi `static/css/app.css` + `core/templatetags/ui.py` (ikon, durum rozeti). Kenar menüsü modül MANIFEST'lerinden otomatik.
Arka ofis kayıt ekranları uygulama kabuğuna alınmış Django yönetim paneli (aynı menü/tasarım); sık kullanılan ekranlar (stok, sipariş havuzu, toplama, mal kabul) özel tasarım.
Kurulum gerektiren her şey (entegrasyon, ilk kurulum) adım adım **sihirbaz** olarak yapılacak.
Tüm ekranlar masaüstü, tablet ve telefon için duyarlı; dokunma alanları ≥44px; site ana ekrana uygulama olarak eklenebilir (manifest).
Kullanıcı başına menü rengi (Görünüm) ve sürükle-bırak ana panel düzeni (`core.UserPreference`).
Ana panel: grafikler (ciro, kanal, ürün, stok değeri), kart/grafik seçme paneli, döviz-altın kur şeridi (`core/rates.py`). Tüm listelerde Excel'e aktarma ve filtre çubuğu.

- [x] Bildirim merkezi (e-posta/SMS sihirbazı, düzenlenebilir şablonlar)
- [x] Canlı sohbet (ofis içi + bayi destek, çevrimiçi durumu)
- [x] Yedekler: al / indir / yükle / geri dön, test verilerini temizle, yeni sunucuya taşıma (`deploy/restore.sh`)
- [x] Yapay zekâ asistanı (Claude / OpenAI, salt okunur veri sorguları, yetkiye göre)

---

## Bölüm 5 · docs/DECISIONS.md

<!-- kaynak: docs/DECISIONS.md -->

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

---

## Bölüm 6 · docs/DEPLOY.md

<!-- kaynak: docs/DEPLOY.md -->

# Kurulum

## Hızlı kurulum (tek komut)
```bash
curl -fsSL https://raw.githubusercontent.com/infoclerie/Eglo/main/deploy/bootstrap.sh | sudo bash
# alan adı hazırsa: ... | sudo DOMAIN=erp.eglokozmetik.com bash
```
Alan adı verilmezse geçici olarak `<ip-tireli>.sslip.io` adresi kullanılır (gerçek HTTPS sertifikası alınır).
AWS Lightsail'de ayrıca Networking > IPv4 Firewall'a **HTTPS (443)** kuralı eklenmeli.
Uygulama `/opt/eglo-erp` altındadır; `worker` servisi entegrasyon kuyruğunu çalıştırır; güncelleme: `cd /opt/eglo-erp && sudo git pull && sudo docker compose up -d --build`.

## Sunucu (elle kurulum)
Ubuntu 24.04 LTS · 4 vCPU · 8 GB RAM · 160 GB NVMe (büyüme: 8 vCPU / 16 GB) · sabit IP · alan adı A kaydı.

İlk sertleştirme (root):
```bash
adduser erp && usermod -aG sudo erp          # SSH açık anahtarını /home/erp/.ssh/authorized_keys'e ekle
apt update && apt -y upgrade && apt -y install ufw fail2ban unattended-upgrades git
ufw allow OpenSSH && ufw allow 80,443/tcp && ufw enable
curl -fsSL https://get.docker.com | sh && usermod -aG docker erp
# anahtarla girişi test ettikten sonra /etc/ssh/sshd_config: PermitRootLogin no, PasswordAuthentication no
systemctl restart ssh
```

## Uygulama (erp kullanıcısı)
```bash
git clone <repo-adresi> erp && cd erp
cp .env.example .env && nano .env           # SECRET_KEY, DB_PASSWORD, DOMAIN değerleri
python3 -c "import secrets;print(secrets.token_urlsafe(50))"   # SECRET_KEY üretmek için
docker compose up -d --build
docker compose exec web python manage.py createsuperuser
docker compose exec web python manage.py seed_demo     # isteğe bağlı örnek veri
```
Yedek: `crontab -e` → `30 2 * * * cd /home/erp/erp && ./deploy/backup.sh >> backups/backup.log 2>&1`
Yedekleri ayrıca sunucu dışına (sağlayıcı snapshot / harici depolama) kopyalayın.

## Güncelleme
```bash
cd ~/erp && git pull && docker compose up -d --build     # migrate otomatik çalışır
```

## Yerel geliştirme
```bash
python3 -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt
python manage.py migrate && python manage.py setup_roles && python manage.py seed_demo
python manage.py createsuperuser && python manage.py runserver
```


## Yedekler ve başka sunucuya taşıma

**Ekrandan:** Sistem › Yedekler (yalnız süper kullanıcı): yedek al, indir, bilgisayardan yükle, geri dön, test verilerini temizle.
Yedek = tek `.zip` (tüm veritabanı JSON + ürün fotoğrafları). Geri dönüş tek işlemde yapılır; öncesi otomatik yedeklenir.
Yedekler sunucuda `appbackups` biriminde durur. **Sunucu çökerse içindekiler de gider → önemli yedekleri indirin.**

**Komut satırından:**
```bash
cd /opt/eglo-erp
sudo docker compose exec web python manage.py create_backup --name "Aylık"     # /app/backups_app altına yazar
sudo docker compose cp web:/app/backups_app/DOSYA.zip ./                         # sunucu klasörüne kopyala
```

**Yeni sunucuya taşıma (adım adım):**
1. Eski sistemde Yedekler › "Yedek al" → **İndir**. Eski sunucudaki `/opt/eglo-erp/.env` dosyasının içeriğini de güvenli bir yere
   kopyalayın (içindeki `DJANGO_SECRET_KEY` entegrasyon şifrelerini açan anahtardır; kimseyle paylaşmayın).
2. Yeni sunucuda hızlı kurulum komutunu çalıştırın (yukarıda). Kurulum bitince:
   `sudo nano /opt/eglo-erp/.env` → `DJANGO_SECRET_KEY=` satırını eskisiyle değiştirin (diğer satırlar yeni sunucunun kalsın),
   sonra `cd /opt/eglo-erp && sudo docker compose up -d`.
   (Anahtarı taşımazsanız da sistem çalışır; yalnız entegrasyon şifrelerini sihirbazlardan yeniden girersiniz.)
3. Yedek dosyasını sunucuya kopyalayın (ör. `scp yedek.zip ubuntu@YENI_IP:/tmp/`) ve:
   `cd /opt/eglo-erp && sudo ./deploy/restore.sh /tmp/yedek.zip`
   Süper kullanıcı oluşturmanıza gerek yok: eski kullanıcılar ve şifreler yedekle gelir.
4. Alan adının DNS kaydını yeni sunucunun IP'sine yönlendirin; Lightsail'de 80/443 portlarını açın.
5. Pazaryeri entegrasyonlarında (Trendyol test ortamı vb.) IP yetkisi gerekiyorsa yeni IP'yi bildirin.

Yedek PostgreSQL / SQLite bağımsızdır; aynı veya daha yeni yazılım sürümüne yüklenebilir (önce `git pull` ile güncel kod).

---

## Bölüm 7 · docs/MODULE_TEMPLATE.md

<!-- kaynak: docs/MODULE_TEMPLATE.md -->

# Yeni modül şablonu

```
apps/<kod>/
  __init__.py
  module.py      MANIFEST = {"code": "<kod>", "name": "...", "version": "0.1.0", "depends": ["core", ...],
                             "urls": "apps.<kod>.urls", "menu": [("Etiket", "<kod>:url_adı")]}
  apps.py        class XConfig(AppConfig): name = "apps.<kod>"; label = "<kod>"; verbose_name = "..."
                 def ready(self): from . import handlers   # olay dinleyicisi varsa
  models.py      iş modelleri BaseModel'den türer
  services.py    iş kuralları ve formüller (docstring'de formül)
  handlers.py    @subscribe ile olay dinleyicileri
  dashboard.py   def widgets(request): return [{"title","value","url","level"}]   (isteğe bağlı)
  urls.py, views.py, forms.py, admin.py, templates/<kod>/
  tests/         her formül ve kural için test (müşteri dokümanındaki örnek sayılarla)
  MODULE.md      modeller, servisler, formüller, yayınlanan/dinlenen olaylar, ekranlar
```
Sonra: `config/modules.py` listesine ekle → `makemigrations <kod>` → `migrate` → `apps/core/roles.py` izinleri →
`setup_roles` → `ARCHITECTURE.md` olay tablosu ve `docs/ROADMAP.md` güncelle.

---

## Bölüm 9 · Modüller (her modülün MODULE.md dosyası)

### Modül `accounting`

# accounting — Finans ve Muhasebe

Bağımlılık: core, catalog, inventory, partners, sales, purchase. Müşteri dokümanı §9.

Modeller: Account (kasa/banka/POS/pazaryeri), Invoice + InvoiceLine (giden/gelen, e-Fatura/e-Arşiv, ETTN, UBL XML),
Payment, LedgerEntry (cari hareket), ChannelCostProfile, ProductCostExtra, MarketplaceSettlement.

## Akışlar
- **Satış:** `shipping.shipped` → `create_sales_invoice` → `issue` (GİB biçimli numara: seri+yıl+9 hane, cari borç) →
  `accounting.invoice_ready` (otomatik gönderim açıksa entegrasyon kuyruğa alır). Cari e-fatura mükellefiyse e-Fatura
  (TICARIFATURA/TEMELFATURA), değilse e-Arşiv. Kargo bedeli ayrı hizmet satırı.
- **İade:** `shipping.return_completed` → iade faturası taslağı (orijinal faturaya referanslı, UBL IADE).
- **Alış:** `create_purchase_invoice` 3'lü eşleştirme (faturalanan ≤ teslim alınan, fiyat toleransı) — uymazsa onay.
- **Gelen e-fatura:** entegratörden `record_incoming_invoice` (ETTN ile mükerrer engeli).
- **Tahsilat/ödeme:** `register_payment` (fatura açık bakiyesini aşamaz), cari ekstre, vadesi geçmiş alacaklar, haftalık nakit akışı.
- **İptal:** yönetici onaylı; cari hareket ters kayıtla kapatılır (silinmez).
- **Hakediş:** sipariş verisinden tahmin + bankaya yatanla mutabakat (fark raporu).
- **Kârlılık:** ürün × kanal katkı kârı; maliyet sevk anındaki stok hareketi maliyetinden.

Formüller `services.py` başında. UBL-TR üretici: `ubl.py` (entegratörden bağımsız).
Ayarlar: `accounting.company`, `accounting.series_efatura`, `accounting.series_earsiv`, `accounting.efatura_profile`,
`accounting.auto_invoice_on_ship`, `accounting.price_tolerance_pct`.
Olaylar: yayınlar `accounting.invoice_ready/sent/cancelled`, `accounting.send_requested`, `accounting.incoming_invoice`,
`accounting.purchase_invoice_posted`, `accounting.payment_registered`; dinler `shipping.shipped`, `shipping.return_completed`,
`partners.collect_balance`, onay olayları.
Sıradaki: resmi muhasebe fişi/hesap planı aktarımı (Uyumsoft muhasebe tarafı netleşince), banka ekstresi içe aktarma.

### Modül `assistant`

# assistant — Yapay zekâ asistanı

- Bağlantı: Entegrasyonlar › Yapay zekâ asistanı → Claude (Anthropic) veya OpenAI / OpenAI uyumlu (`integrations/providers/ai.py`).
  Model adı serbest metin; bağlantı testi hesaptaki modelleri listeler. Ayarlar: kişi başı günlük soru sınırı, cevap uzunluğu,
  KVKK (yurt dışı aktarım) onayı — onaysız asistan çalışmaz.
- Çalışma: soru → yapay zekâ `tools.py`'deki SALT OKUNUR sorguları çağırır (en fazla 6 tur) → Türkçe cevap.
  Yapay zekâ veritabanına doğrudan erişmez, kayıt değiştiremez.
- Yetki: her araç Django izni ister (`tools_for(user)`); kullanıcı yalnız görebildiği veriyi sorabilir.
  Asistanı kullanma izni: `assistant.add_assistantmessage` (roller setup_roles ile).
- KVKK: araç çıktılarında müşteri telefon / e-posta / adres / VKN yoktur.
- Yeni veri sorgusu: `TOOLS` listesine (ad, açıklama, şema, izin, fonksiyon) ve `LABELS`'a ekleyin.
- Arayüz: ana panelde soru kutusu, `/assistant/` konuşma ekranı, üst çubukta ✨. Kullanım (token) AssistantMessage'ta tutulur.

### Modül `catalog`

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

### Modül `chat`

# chat — Canlı sohbet

- Ofis içi birebir sohbet + bayi/müşteri (portal kullanıcısı) ↔ "Eglo destek" sohbeti.
- Modeller: Conversation (direct/group/support), Participant (last_read_id), Message, Presence (last_seen).
- Çevrimiçi = son 60 sn içinde sinyal (yeşil nokta), değilse kırmızı.
- Taşıma: kısa aralıklı yoklama (panel açıkken 3 sn, kapalıyken 15 sn) → sunucuya ek kurulum (Redis/WebSocket) gerekmez.
  Kullanıcı sayısı çok artarsa Django Channels + Redis'e geçilebilir; API (`/chat/api/poll|people|start|send/`) aynı kalır.
- Destek ekibi: süper kullanıcılar + "Satış ekibi" + "E-ticaret ekibi" grupları.
- Arayüz: `static/js/chat.js` (sağ alttaki 💬 düğmesi), base.html ve portal/base.html içinde yüklenir.

### Modül `core`

# core — Çekirdek

Her zaman açıktır. Diğer bütün modüllerin kullandığı ortak altyapı.

| Parça | Dosya | Kullanım |
|---|---|---|
| Modül kayıt sistemi | `registry.py` | `module.py → MANIFEST`; bağımlılık kontrolü, URL ve menü toplama |
| Olay yolu | `events.py` | `@subscribe("olay")`, `publish("olay", **yük)` |
| İşlem logu | `audit.py`, `AuditLog` | ERP modüllerindeki her kayıt değişikliği otomatik (kim, ne zaman, ne) |
| Onay akışı | `approvals.py`, `ApprovalRequest` | `request_approval(action, obj, title, user)`; onay → `approval.approved.<action>` olayı. Kendi talebini onaylama yasak; `core.decide_approval` izni gerekir. |
| Numara serisi | `Sequence.next(code, prefix)` | SAY-000001 gibi belge numaraları (kilitli, çakışmasız) |
| Ayarlar | `Setting.get/put` | Yöneticinin değiştirebildiği parametreler |
| Temel model | `BaseModel` | created_at, updated_at, created_by |
| Roller | `roles.py` + `setup_roles` komutu | Doküman §12 rolleri |
| Ana panel | `views.dashboard` | Her modülün `dashboard.py → widgets(request)` kartları |

### Modül `crm`

# crm — CRM

Bağımlılık: core, partners, sales. Müşteri dokümanı §8.3–8.5.
- **Satış fırsatları** `/crm/`: aşama panosu (sürükle-bırak). Aşamalar: potansiyel → ilk iletişim → ihtiyaç analizi → teklif → pazarlık → kazanıldı/kaybedildi.
  "Teklif gönderildi"ye geçince `crm.quote_followup_days` (3) gün sonrasına otomatik takip görevi.
- **Takiplerim** `/crm/takipler/`: tarihi gelen/gecikmiş aktiviteler (telefon, ziyaret, teklif, numune...), tamamlandı işareti; ana panel kartı.
- **Segmentler** `/crm/segmentler/`: VIP / düzenli / yeni / uzun süredir almayan / potansiyel / aktif (kurallar `services.py` başında).
Sıradaki: SMS/e-posta kampanya gönderimi (İYS izinli), fırsattan sipariş oluşturma.

## Kampanyalar (toplu e-posta / SMS — ticari ileti)
- Campaign: kanal, segmentler, il filtresi, alıcı türü (İYS 11 bireysel / 12 tacir), konu, mesaj ({musteri}, {cari_kodu}, {firma}).
- `services.audience` → yalnız `consent_email` / `consent_sms` işaretli cariler; izinsiz ve iletişimsizler atlanır ve kaydedilir.
- `send_campaign`: e-postaya imzalı "abonelikten çık" bağlantısı (+ List-Unsubscribe başlığı) eklenir → `/crm/abonelik/<token>/`
  (giriş gerektirmez, izni kapatır). SMS Netgsm'e `iysfilter` ile gider (Netgsm İYS'de izni olmayanı göndermez).
- Önce "deneme gönder", sonra onaylı toplu gönderim; gönderilen kampanya tekrar gönderilmez. İletim: entegrasyon iş kuyruğu.

### Modül `imports`

# imports — Excel ile toplu yükleme (§16)

- Türler (`services.KINDS`): ürün kartları (ekle/güncelle), fiyatlar (liste, maliyet, her kanal için "Fiyat: <kanal>" sütunu),
  stok girişi (lokasyon + LOT + SKT; `inventory.receive`, hareket türü sayım farkı/açılış).
- Akış: şablon indir → yükle → önizleme (satır satır hata) → onay. Hata olan dosyada HİÇBİR şey yazılmaz (tek transaction).
- Türkçe sayı (1.234,56) ve tarih (gg.aa.yyyy) kabul edilir; seçim sütunlarında kod veya Türkçe ad yazılabilir.
- Ürün güncellemede boş hücre mevcut değeri değiştirmez. Dosya önizleme ile onay arasında oturumda (base64) tutulur, en fazla 8 MB.
- İzin: `imports.add_importpermission`.

### Modül `integrations`

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

## Pazaryeri / e-ticaret sağlayıcıları (Kasım 2026)
- Ortak yardımcılar `providers/common.py` (ürün eşleştirme, KDV dönüşümü, sipariş kaydı, stok satırları).
- **Hepsiburada** (`providers/hepsiburada.py`): Basic (Merchant ID : servis anahtarı) + User-Agent (entegratör adı).
  oms-external (sipariş, paket, kargoda, teslim), listing-external (inventory-uploads), mpfinance-external (transactions → hakediş).
  Akış: toplama başlayınca HB'de paket oluşur; "kendi kargom" açıksa sevkte takip no (intransit), teslimde deliver gönderilir.
- **ikas** (`providers/ikas.py`): özel uygulama client_credentials → Admin GraphQL v2. Sipariş (listOrder), stok (saveVariantStocks),
  fiyat (updateVariantPrices), sevkte fulfillOrder (müşteriye takip bilgisi). Kanal: "web" veya ayrı "ikas".
- **Hakediş**: Trendyol `/finance/che/sellers/{id}/settlements` + `otherfinancials` (PaymentOrder = bankaya yatan),
  Hepsiburada `/transactions` → `accounting.services.upsert_settlement` (haftalık dönem, Pzt–Paz). Ayarlardan "Hakediş çek".
- Trendyol "kendi kargom" açıksa takip no `/shipment-packages/{id}/tracking-details` ile gider (kargo kodları handlers.TRENDYOL_CARGO).
- Bu üç sağlayıcının canlı hesapla ilk doğrulaması yapılmalı (alan adları resmi dokümandan; test edilmedi).

## Kanal paneli ve ikas ürün aktarımı
- Sol menüde "Satış kanalları" grubu (`nav.py`, MANIFEST `nav_hook`): her aktif pazaryeri / e-ticaret bağlantısı için
  `/integrations/kanal/<id>/` paneli: bugünkü/aylık sipariş, sevk bekleyen, stok ayrılamayan, eşleşen ürün sayısı, son hata
  (eşleşmeyen ürün çözüm bağlantısıyla), otomatik ayarların açık/kapalı durumu, son siparişler, son işlemler, hızlı işlemler
  (sipariş çek, stok gönder, hakediş çek, test).
- ikas: "Ürünleri ikas'tan aktar" (`ikas.import_products`): her varyant ayrı ürün kartı; SKU (yoksa barkod) eşleşirse günceller;
  fiyat KDV dahil → liste fiyatı KDV hariç, indirimli fiyat kanal fiyatı; isteğe bağlı açılış stoğu (yalnız stoğu sıfır ürünlere).

### Modül `inventory`

# inventory — Depo ve Stok (WMS)

Bağımlılık: core, catalog. Müşteri dokümanı: §3, §4, §14.

## Modeller
Warehouse · Location (tür: raf, mal kabul, sevkiyat, iade kontrol, karantina, hasarlı, numune, yolda + sanal türler) ·
Lot (LOT no, üretim tarihi, SKT, üretici) · Pallet · Quant (anlık stok) · StockMove (hareket defteri) ·
Reservation · StockCount / StockCountLine.

## Servisler (`services.py`) — stoğu değiştiren TEK yer
| Fonksiyon | Ne yapar |
|---|---|
| `receive(product, qty, location, lot_no, expiry_date, production_date, ...)` | Mal kabul / üretimden giriş. SKT yoksa üretim tarihi + raf ömrü. |
| `move_stock(...)` | Temel hareket; tüm kurallar burada (negatif stok yok, LOT zorunlu, SKT geçmiş ürün satışa uygun alana giremez). |
| `transfer`, `scrap` | Lokasyonlar arası transfer, fire/hasar çıkışı. |
| `reserve(product, qty, reference, warehouse=None, allow_near_expiry=False)` | FEFO ile ayırır; yetmezse hiç ayırmaz (fazla satış engeli). Set → bileşenler. |
| `release(reference)` / `ship_reserved(reference)` | Rezervasyonu bırak / müşteriye sevk et (stok düşer). |
| `stock_summary(product)` | fiziksel, satışa uygun, rezerve, karantina, hasarlı, iade kontrol, SKT geçmiş, yoldaki. |
| `expiry_status(lot)` | ok / info / warning / critical / approval / expired. |
| `low_stock_products()`, `expiring_lots()` | Uyarı listeleri (ana panel kartları). |
| `suggest_purchase_qty`, `purchase_suggestion(product)` | Satın alma önerisi. |
| `start_count` → `submit_count` → (onay) → `apply_count` | Sayım ve onaylı düzeltme. |

## Formüller
- **Satışa uygun stok** = Σ(miktar − rezerve) [satışa uygun lokasyonlar, SKT'si geçmemiş LOT'lar]
- **Set satılabilir adet** = min(⌊bileşen satışa uygun / set içi miktar⌋)
- **SKT durumu** (kalan gün, varsayılan eşik): <0 expired (blokaj) · ≤30 approval · ≤90 critical · ≤120 warning · ≤180 info
- **Satın alma önerisi** = günlük ort. satış × tedarik süresi + güvenlik stoğu − satışa uygun − yoldaki, en az 0
  (örnek: 20×15+100−250 = 150). Günlük ort. satış = (son 90 gün satış − müşteri iadesi) / 90.
  Öneri otomatik siparişe dönmez.

## Olaylar
Yayınlar: `inventory.stock_moved`, `inventory.reserved`, `inventory.released`, `inventory.shipped`,
`inventory.count_applied`, `inventory.collect_incoming` (purchase modülü yoldaki miktarı döndürecek).
Dinler: `approval.approved.inventory.count_adjust`, `approval.rejected.inventory.count_adjust`.

## Ekranlar
`/inventory/` stok durumu · `/inventory/scan/` barkod sorgu (el terminali) · `/inventory/receive/` mal kabul ·
`/inventory/transfer/` transfer · Yönetim panelinde depo, lokasyon, LOT, palet, sayım; Quant/hareketler salt okunur.

## Bilinen sınırlar / sıradaki
Sayım düzeltmesi onay anındaki farkı uygular (sayım ile onay arasındaki hareketler için sayım öncesi lokasyon kilidi eklenecek).
Palet doluluk oranı, stok yaşlandırma raporu, depolar arası dengesizlik uyarısı ⬜.

### Modül `notifications`

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

### Modül `office`

# Sanal Ofis (office)

Şirketin 3B canlı ofis görünümü (three.js r170, `static/vendor/three/`, MIT lisansı — ücretsiz, CDN yok).

- `/office/` — tam sayfa, kenar menüsüz; menüden **yeni sekmede** açılır (MANIFEST menü öğesinin 4. elemanı `"new_tab"`).
  Düğmeler: Panele dön · Tam ekran · Tur (otomatik kamera) · canlı saat.
- `/office/api/` — `services.snapshot()` JSON'u; sayfa 30 sn'de bir yeniler.
- Departmanlar: Yönetim, Satış, Depo, Sevkiyat ve Kargo, Satın Alma, Finans ve Muhasebe, Üretim ve Kalite,
  ve her aktif pazaryeri/e-ticaret hesabı için bir masa (Trendyol, Hepsiburada, ikas…).
- Çalışanlar: ilgili rol grubundaki gerçek kullanıcılar (en çok 5, son 5 dk etkinse "çevrimiçi").
  Grup boşsa örnek unvanlar gösterilir ("örnek" etiketi). Gerçek kişi görmek için kullanıcıyı rol grubuna atayın.
- Tıklama: kişi/masa/zemin → o departmanın canlı göstergeleri (ilgili ekrana bağlantılı), çalışanlar, son işler.
- Animasyon: iş varsa ekranlar parlar ve kişiler yazar; kargo varsa kurye depodan kamyona paket taşır;
  satış→depo, satın alma→muhasebe, e-ticaret→kargo evrak taşıyan kişiler yürür.
- Model yok; yalnızca diğer modüllerin verisini okur.

### Modül `partners`

# partners — Cari Kartlar

Bağımlılık: core, catalog. Müşteri dokümanı §5.1, §8.1, §8.2.

Tek model `Partner`: müşteri, bayi, tedarikçi, fason üretici (tür + grup). Kod otomatik (C-000001 müşteri, T-000001 tedarikçi).
Müşteriye özel indirim, fiyat kanalı (bayi/kurumsal fiyat listesi), vade, kredi limiti, İYS/KVKK izinleri.

Servisler: `open_balance(partner)` — `partners.collect_balance` olayından (muhasebe modülü doldurur);
`credit_check(partner, amount)` — limit 0 ise kontrol yok.

### Modül `portal`

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

### Modül `production`

# production — Üretim ve fason (§10)

- Reçete (BillOfMaterials + BomLine): mamul, parti büyüklüğü, malzeme miktarı, fire payı %. Yönetim › Reçeteler.
- Üretim emri akışı (`services.py`):
  taslak → `confirm` (malzemeyi FEFO ile AYIRIR; eksik varsa hiçbir şey ayırmaz) → `start` (sarf: `production_consume`;
  fason ise "Fasoncuda") → `finish(üretilen)` (mamul KARANTİNA lokasyonuna LOT + SKT ile girer, `production_in`)
  → `quality_check(onay)` karantinadan rafa / `red` karantinada kalır. `cancel` ayrılanı serbest bırakır.
- Formüller: ihtiyaç = reçete miktarı × (planlanan ÷ parti) × (1 + fire%/100), yukarı yuvarlanır.
  birim maliyet = (sarf edilen malzeme maliyeti + fason işçilik × üretilen) ÷ üretilen. Kayıp % = (planlanan − üretilen) ÷ planlanan.
- Açık emirlerin planlanan miktarı stok ekranında "gelecek" olarak görünür (`inventory.collect_incoming`).
- Olaylar: production.confirmed / started / finished / completed / rejected. `production.completed` pazaryeri stok gönderimini tetikler.
- Hammadde (tür: Hammadde / Ambalaj) satış kanallarına gönderilmez. Hammaddede yakın SKT'li parti kullanılabilir (süresi geçmiş olamaz).

### Modül `purchase`

# purchase — Satın Alma

Bağımlılık: core, catalog, inventory, partners. Müşteri dokümanı §5, §4.4.

Akış: talep (manuel veya `create_suggested_requests` sistem önerisi) → tedarikçi teklifleri → `compare_quotes`
(fiyat ↑, termin ↑, vade ↓) → `order_from_quote` → `submit` (yönetici onayı) → `mark_sent` → `/purchase/<id>/receive/`
mal kabul (LOT/SKT, ağırlıklı ortalama maliyet) → `close` (eksik/fazla teslim tutanağı).

Kurallar: onaysız siparişe mal kabul yapılamaz; siparişten fazla kabul edilemez (`purchase.over_receipt_pct`).
Yoldaki miktar `inventory.collect_incoming` olayıyla stok özetine ve satın alma önerisine yansır.
Raporlar: `supplier_performance`, `last_prices`.
Sıradaki: fatura eşleştirme (sipariş–irsaliye–fatura) muhasebe modülünde.

### Modül `reports`

# reports — Raporlar (§11)

- `registry.py` → REPORTS: stok yaşlandırma, devir hızı, kanal kârlılığı, ürün kârlılığı, SKT raporu.
- Yeni rapor: fonksiyon yaz (params → columns/rows/totals/chart/note) ve REPORTS'a ekle; ekran, Excel ve yazdırma otomatik.
- Excel: `?format=xlsx` (openpyxl, biçimli). PDF: tarayıcıda "PDF / Yazdır" (A4 yatay yazdırma stili app.css'te).
- Kârlılık hesabı `accounting.services.product_profitability` (kanal maliyet profilleri) kullanır.
- İzin: `reports.view_report` (veri tutmayan model).

### Modül `sales`

# sales — Sipariş Yönetimi

Bağımlılık: core, catalog, inventory, partners. Müşteri dokümanı §6.

Modeller: SalesOrder (13 durum, kanal, kanal sipariş no, müşteri anlık bilgileri, tutarlar), SalesOrderLine, Campaign, OrderStatusLog.

## Kurallar
- **Mükerrer engeli:** (kanal, kanal sipariş no) benzersiz; `import_channel_order` aynı siparişi ikinci kez açmaz, mevcut olanı döner.
- **Anlık rezervasyon:** `confirm` tüm satırları tek işlemde rezerve eder; bir satır yetmezse hiçbiri ayrılmaz (fazla satış yok).
- **Kredi limiti:** vadeli satışta açık bakiye + sipariş > limit → `request_credit_override` ile yönetici onayı.
- **İptal:** stok ayrılmamış sipariş doğrudan; ayrılmış sipariş yönetici onayıyla iptal edilir, rezervasyon bırakılır. Sevk edilen sipariş iptal edilmez (iade).
- Durum geçmişi ve "bu durumda kaç saattir" bilgisi tutulur.

## Formüller (`services.py` başı)
Birim fiyat = kanal fiyatı (müşterinin fiyat kanalı öncelikli) × (1 − müşteri indirimi %).
Satır net = miktar × birim fiyat − satır indirimi − sepet indirimi payı. KDV satır oranıyla net üzerinden; kargo KDV'si %20.

## Kampanyalar
Sepette %, X al Y öde, N. ürün sabit fiyat, tutar üstü ücretsiz kargo, kupon %. Kanal ve ürün kapsamı, tarih aralığı,
maksimum kullanım, maksimum indirim, minimum sepet.

## Olaylar
Yayınlar: `sales.order_confirmed`, `sales.order_cancelled`, `sales.status_changed`.
Dinler: `shipping.*` (durum ilerletme), `approval.approved.sales.cancel`, `approval.approved.sales.credit_override`.

### Modül `shipping`

# shipping — Sevkiyat ve İade

Bağımlılık: core, catalog, inventory, sales. Müşteri dokümanı §7.

Akış: `sales.order_confirmed` → `create_shipment` (rezervasyonlardan, lokasyon rotasına göre toplama listesi) →
`scan` (barkod/koli barkodu doğrulama, yanlış ürün/fazla okutma engeli) → `pack` (koli adedi + tartı, ağırlık toleransı) →
`ship` (stok burada düşer) → `deliver`. Çoklu/dalga toplama: `batch_pick_list`.

İade: `request_return` → `receive_return` (müşteri → iade kontrol alanı; LOT, sevk edilen LOT'tan) →
`inspect_return` (satır bazında durum) → yönetici onayı → `complete_return` (satılabilir → raf, hasarlı → hasarlı alanı,
karantina → karantina). **Açılmış/kullanılmış ürün asla satılabilir stoğa dönmez.**

Ayar: `shipping.weight_tolerance_pct` (varsayılan 5).
Olaylar: `shipping.shipment_created`, `picking_started`, `picked`, `packed`, `shipped`, `delivered`, `return_requested`, `return_completed`.
Ekran: `/shipping/` kuyruk, `/shipping/<id>/` el terminali ekranı (adım adım).
Sıradaki: kargo firması entegrasyonu (etiket, takip no) — entegrasyon sihirbazı ile.

**Kargo etiketi:** `/shipping/<id>/label/` (koli başına bir 10×15 cm etiket, Code128 barkod = takip no veya sevk no), toplu: kuyruk ekranında seçip yazdır (`/shipping/labels/?ids=`). Kargo firması API'leri (Yurtiçi/Aras/MNG) anlaşma bilgileri gelince `integrations` sağlayıcısı olarak eklenecek; etiket barkodu o zaman firmanın takip numarası olur.

---

## Bölüm 10 · Müşterinin ilk ihtiyaç dokümanı

# Müşteri ihtiyaç dokümanı (Eglo Kozmetik, 18.11.2026 e-postası, düz metin)


Deterjan ve Kozmetik Firması İçin Entegre Depo Yönetimi, Sipariş, Sevkiyat, Stok, CRM ve Muhasebe Yazılımı
Bir deterjan ve kozmetik firması için kurulacak yazılımı yalnızca bir depo takip programı olarak düşünmemek gerekir. İhtiyacımız olan sistem; satın almadan ürün kabulüne, stok yönetiminden siparişe, siparişten sevkiyata, müşteri ilişkilerinden tahsilata ve muhasebeleştirmeye kadar bütün süreçleri tek merkezden yönetebilen entegre bir ERP + WMS + CRM sistemi olmalıdır.
Özellikle hem kozmetik hem de temizlik ürünleri satacağınız için yazılımda standart stok takibinin yanında şu özellikler kritik önem taşıyor:

  *   Üretim partisi (LOT) ve SKT (son kullanma tarihi) takibi.
  *   FIFO / FEFO stok yönetimi.
  *   Barkod, koli ve palet bazlı depo yönetimi.
  *   Trendyol, Hepsiburada, web sitesi ve bayi siparişlerinin tek ekranda toplanması.
  *   B2B bayi ve kurumsal müşteri yönetimi.
  *   Otomatik sevkiyat ve kargo entegrasyonu.
  *   E-fatura, e-arşiv, e-irsaliye ve muhasebe entegrasyonu.
  *   Ürün bazında kârlılık, maliyet ve stok devir hızı analizi.
Aşağıda yazılım firmasına doğrudan iletebileceğiniz şekilde kapsamlı bir yazılım ihtiyaç ve süreç dokümanı hazırladım.
1. Yazılımın genel mimarisi
Entegre işletme yönetim sistemi
MERKEZİ YÖNETİM PANELİ
Tüm şirket operasyonlarının yönetildiği ana ekran
Depo / WMS
Raf, palet, LOT, SKT
Stok Yönetimi
Giriş, çıkış, transfer
Sipariş Yönetimi
B2B, B2C, pazaryeri
Sevkiyat Yönetimi
Toplama, paketleme, kargo
CRM
Müşteri, bayi, satış
Muhasebe / Finans
Fatura, tahsilat, ödeme
ENTEGRASYON KATMANI
Trendyol • Hepsiburada • Web sitesi • E-ticaret • Kargo • Banka • E-belge • Muhasebe
RAPORLAMA VE YÖNETİMSEL ANALİZ
Ciro • Kârlılık • Stok • Satış performansı • Nakit akışı • Operasyon verimliliği
Sistemin bütün modülleri aynı veritabanı üzerinden çalışmalı. Örneğin Trendyol'dan bir sipariş geldiğinde sipariş kaydı oluşturulmalı, stok rezerve edilmeli, depo toplama emri açılmalı, ürün sevk edildiğinde stok düşmeli, fatura oluşturulmalı ve muhasebe kaydı meydana gelmelidir.
2. Ürün kartı ve ürün ana veri yönetimi
Bütün operasyonların başlangıcı ürün kartıdır. Her ürünün sistemde standart bir tanımı bulunmalıdır.
2.1. Ürün kartında bulunması gereken bilgiler
Alan
Açıklama
Ürün kodu
Şirkete özel SKU
Barkod
EAN / GTIN
Ürün adı
Ticari ürün adı
Marka
Clerie vb.
Ana kategori
Kozmetik / Temizlik
Alt kategori
Serum, krem, deterjan vb.
Ürün açıklaması
Ürün özellikleri
Birim
Adet, koli, litre, kg
Hacim / ağırlık
100 ml, 750 ml, 3 L vb.
Koli içi adet
Bir kolideki ürün sayısı
Koli barkodu
Koli bazlı tanımlama
Palet kapasitesi
Palet başına koli/adet
Alış maliyeti
Birim tedarik maliyeti
Satış fiyatı
Kanal bazında satış fiyatı
KDV oranı
Muhasebe parametresi
Minimum stok
Alt stok seviyesi
Maksimum stok
Üst stok seviyesi
LOT / SKT
Parti ve son kullanma tarihi
Raf ömrü
Ürün raf ömrü
Depolama koşulu
Isı, ışık, nem vb.
Ürün görseli
Fotoğraf ve ambalaj görseli
2.2. Ürün grupları
Sistem ürünleri farklı kategorilerde yönetebilmelidir:

  *   Kozmetik: Serum, krem, güneş kremi, maske, tonik, temizleme jeli.
  *   Sıvı temizlik ürünleri: Yumuşatıcı, sıvı sabun, çamaşır suyu.
  *   Sprey ürünleri: Oda kokusu, yüzey temizleyici, Arap sabunu spreyi.
  *   Konsantre ürünler.
  *   Numune ve tester ürünleri.
  *   Promosyon ve hediye ürünleri.
  *   Set ve kampanya paketleri.
Önemli: Aynı ürünün tekli, 3'lü set, 6'lı koli ve kampanya paketi gibi farklı satış şekilleri tanımlanabilmeli. Set içindeki ürünlerin stokları ana ürünlerden otomatik düşmeli.
3. Depo yönetim sistemi (WMS)
En kritik modül
Depo yönetimi yalnızca toplam stok adedini görmekten ibaret olmamalı. Hangi ürünün hangi depoda, hangi koridorda, hangi rafta, hangi palet üzerinde ve hangi üretim partisinde bulunduğu takip edilmelidir.
3.1. Depo tanımlamaları
Sistem birden fazla depo ve depo alanı tanımlamayı desteklemelidir.
Örnek depo yapısı:
Depo
Açıklama
Ana depo
Genel ürün stokları
Kozmetik deposu
Kozmetik ürünleri
Temizlik deposu
Deterjan ve sıvı ürünler
Sevkiyat alanı
Siparişi hazırlanmış ürünler
İade alanı
Müşteri iadeleri
Karantina alanı
Kontrol bekleyen ürünler
Hasarlı ürün alanı
Satışa uygun olmayan ürünler
Numune alanı
Tester ve promosyonlar
3.2. Raf ve lokasyon yönetimi
Her depo için aşağıdaki yapı oluşturulmalıdır:

  *   Depo kodu.
  *   Koridor kodu.
  *   Raf kodu.
  *   Kat / göz numarası.
  *   Palet lokasyonu.
  *   Maksimum taşıma kapasitesi.
  *   Maksimum hacim kapasitesi.
  *   Ürün kabul durumu.
  *   Ürün toplama durumu.
Örnek lokasyon kodu:
A-02-03-01
A
Depo
02
Koridor
03
Raf
01
Kat
Her lokasyon barkodla tanımlanmalı ve el terminalinden okutulabilmelidir.
3.3. Depoya ürün giriş süreci
Ürün girişleri aşağıdaki şekilde ilerlemelidir:

  1.  Satın alma siparişi oluşturulur.
  2.  Tedarikçi ürünleri depoya gönderir.
  3.  Depo personeli irsaliye ve sipariş bilgilerini kontrol eder.
  4.  Gelen ürün barkodları okutulur.
  5.  Ürün adetleri sayılır.
  6.  Üretim LOT numarası kaydedilir.
  7.  SKT bilgisi girilir.
  8.  Hasarlı veya eksik ürünler ayrıştırılır.
  9.  Ürün kabul onayı verilir.
  10. Sistem otomatik olarak stok girişini gerçekleştirir.
  11. Ürünlere raf veya palet lokasyonu atanır.
Ek özellik: Sipariş edilen miktar ile teslim alınan miktar farklıysa sistem uyarı vermeli, fark için tutanak veya eksik/fazla teslim kaydı oluşturmalıdır.
3.4. LOT ve SKT takibi
Kozmetik ürünlerde bu modül çok önemlidir.
Her ürün için aşağıdaki bilgiler saklanmalıdır:

  *   Üretim tarihi.
  *   Son kullanma tarihi.
  *   LOT / parti numarası.
  *   Tedarikçi veya üretici.
  *   Üretim yeri.
  *   Depoya giriş tarihi.
  *   Depoda bulunduğu lokasyon.
  *   Parti bazında giriş ve çıkış miktarı.
Sistem FEFO (son kullanma tarihi en yakın olan önce çıkar) mantığıyla ürün toplama önceliği vermelidir.
Örnek uyarı mekanizması:
Kalan raf ömrü
Sistem uyarısı
180 gün
Bilgilendirme
120 gün
Yaklaşan SKT uyarısı
90 gün
Kritik stok uyarısı
30 gün
Yönetici onayı
SKT geçmiş
Satış ve sevkiyat blokajı
Bu süreler yönetici tarafından değiştirilebilir olmalıdır.
3.5. Stok transfer işlemleri

  *   Depolar arası transfer.
  *   Raflar arası transfer.
  *   Paletler arası transfer.
  *   Ürün toplama alanına transfer.
  *   İade alanına transfer.
  *   Karantina alanına transfer.
Her transfer için kaynak lokasyon, hedef lokasyon, ürün, miktar, işlem yapan personel ve tarih kayıt altına alınmalıdır.
3.6. Sayım yönetimi
Sistem üç farklı sayım yöntemini desteklemelidir:

  1.  Genel depo sayımı.
  2.  Raf bazlı sayım.
  3.  Ürün bazlı dönemsel sayım.
Sayım işlemi el terminali veya barkod okuyucu ile yapılabilmeli.
Sayım sonucu sistem stoğu ile fiziksel stok karşılaştırılmalı; eksik ve fazla stoklar gösterilmeli, farklar yönetici onayından sonra düzeltilmelidir.
3.7. Palet ve koli yönetimi
Palet bazlı çalışma mutlaka bulunmalı.

  *   Palet barkodu oluşturma.
  *   Palete ürün ekleme.
  *   Paletten ürün çıkarma.
  *   Palet transferi.
  *   Palet lokasyonu.
  *   Palet içindeki ürün ve miktar listesi.
  *   Palet doluluk oranı.
  *   Palet geçmişi.
  *   Palet bazında sevkiyat.
Örneğin 80 × 120 cm paletlerin bulunduğu depoda palet adedi, yerleşim kapasitesi ve kullanılabilir alan takip edilebilmelidir. Ancak gerçek kapasite hesaplamasında raf yüksekliği, koridorlar, istifleme güvenliği ve yangın yolları da dikkate alınmalıdır.
4. Stok yönetimi
Stok modülü tüm satış ve depo hareketlerinin merkezinde olmalıdır.
4.1. Stok hareket türleri
Sistemde aşağıdaki stok hareketleri ayrı ayrı tanımlanmalıdır:
İşlem
Stok etkisi
Satın alma girişi
Stok artar
Üretimden giriş
Stok artar
Satış siparişi
Stok rezerve edilir
Sevkiyat
Stok azalır
Müşteri iadesi
Kontrol sonrası stok artar
Tedarikçi iadesi
Stok azalır
Depolar arası transfer
Toplam stok değişmez
Fire / hasar
Stok azalır
Numune çıkışı
Stok azalır
Promosyon çıkışı
Stok azalır
Sayım farkı
Onay sonrası düzeltilir
4.2. Stok durumları
Her ürün için stok aşağıdaki şekilde gösterilmelidir:

  *   Toplam fiziksel stok.
  *   Satışa uygun stok.
  *   Rezerve edilmiş stok.
  *   Siparişe ayrılmış stok.
  *   Sevkiyat bekleyen stok.
  *   İade kontrolündeki stok.
  *   Hasarlı stok.
  *   Karantinadaki stok.
  *   Yoldaki stok.
  *   Satın alma siparişi verilmiş stok.
Örneğin:
Örnek ürün stok ekranı
1.250 adet
Toplam fiziksel stok
Satışa uygun
850
Rezerve
250
Hasarlı / Karantina
100
İade kontrolünde
50
Net satışa uygun stok: 850 adet
4.3. Otomatik stok uyarıları

  *   Minimum stok seviyesinin altına düşme.
  *   Kritik stok seviyesine ulaşma.
  *   Aşırı stok oluşması.
  *   Hareketsiz stok.
  *   SKT yaklaşması.
  *   LOT bazlı stok uyarısı.
  *   Sipariş karşılayamayacak stok durumu.
  *   Depolar arası stok dengesizliği.
4.4. Otomatik satın alma önerisi
Sistem geçmiş satışları ve mevcut stokları dikkate alarak satın alma önerisi oluşturmalıdır.
Örnek:

  *   Günlük ortalama satış: 20 adet.
  *   Tedarik süresi: 15 gün.
  *   Güvenlik stoğu: 100 adet.
  *   Mevcut kullanılabilir stok: 250 adet.
Önerilen ihtiyaç:
\[ (20 \times 15)+100-250=150 \]
Sistem 150 adetlik satın alma önerisi oluşturabilir. Bu öneri otomatik siparişe dönüşmemeli, yetkili onayıyla satın alma siparişine çevrilmelidir.
5. Satın alma ve tedarikçi yönetimi
Yazılımın satın alma modülü de bulunmalıdır. Üreticiden veya tedarikçiden alınan ürünlerin tüm süreci takip edilmelidir.
5.1. Tedarikçi kartı
Her tedarikçi için:

  *   Firma unvanı.
  *   Vergi numarası ve vergi dairesi.
  *   Yetkili kişi.
  *   Telefon ve e-posta.
  *   Adres.
  *   IBAN.
  *   Ödeme vadesi.
  *   Çalışılan ürünler.
  *   Son alış fiyatları.
  *   Teslimat süresi.
  *   Minimum sipariş miktarı.
  *   Sevkiyat koşulları.
  *   Açık siparişler.
  *   Borç bakiyesi.
5.2. Satın alma süreci

  1.  Satın alma talebi
Depo veya satış departmanı ürün ihtiyacını bildirir.

  1.  Teklif toplama
Tedarikçilerden fiyat, termin ve sevkiyat teklifi alınır.

  1.  Teklif karşılaştırma
Fiyat, ödeme vadesi ve teslim süresi değerlendirilir.

  1.  Yönetici onayı
Satın alma talebi onaylanır.

  1.  Satın alma siparişi
Tedarikçiye resmi sipariş iletilir.

  1.  Mal kabul
Gelen ürünler kontrol edilerek sisteme alınır.

  1.  Fatura eşleştirme
Sipariş, irsaliye ve tedarikçi faturası karşılaştırılır.

  1.  Ödeme ve muhasebe
Borç kaydı oluşturulur ve ödeme planına alınır.
5.3. Satın alma raporları

  *   Tedarikçi bazında alış tutarları.
  *   Ürün bazında son alış fiyatı.
  *   Ortalama alış maliyeti.
  *   Fiyat değişim geçmişi.
  *   Açık satın alma siparişleri.
  *   Termin gecikmeleri.
  *   Tedarikçi performansı.
  *   Vadesi gelen tedarikçi borçları.
6. Sipariş yönetimi
Bu modül şirketin bütün satış kanallarından gelen siparişleri tek merkezde toplamalıdır.
Merkezi sipariş havuzu
6.1. Sipariş kaynakları
Yazılım aşağıdaki kanallardan sipariş alabilmelidir:

  1.  Trendyol.
  2.  Hepsiburada.
  3.  Şirket web sitesi.
  4.  B2B bayi portalı.
  5.  Telefon siparişleri.
  6.  E-posta siparişleri.
  7.  WhatsApp üzerinden alınan siparişler.
  8.  Kurumsal şirket siparişleri.
  9.  Distribütör ve toptancı siparişleri.
  10. Mağaza veya fiziksel satış noktaları.
Her siparişin hangi kanaldan geldiği sistemde kayıtlı olmalıdır.
6.2. Sipariş kartında bulunması gereken bilgiler
Alan
Açıklama
Sipariş numarası
Otomatik numara
Sipariş tarihi
Sipariş oluşturulma zamanı
Satış kanalı
Trendyol, bayi vb.
Müşteri
Cari kart
Ürün kodu
SKU
Barkod
Ürün barkodu
Ürün miktarı
Sipariş adedi
Birim fiyat
Satış fiyatı
İndirim
Kampanya indirimi
KDV
Vergi bilgisi
Kargo bedeli
Varsa
Genel toplam
Sipariş toplamı
Ödeme şekli
Kart, havale vb.
Teslimat adresi
Sevk adresi
Fatura adresi
Fatura bilgisi
Sipariş durumu
Operasyon aşaması
6.3. Sipariş durumları
Sistem siparişleri aşağıdaki aşamalarda takip etmelidir:

  *   Yeni sipariş.
  *   Ödeme bekliyor.
  *   Ödeme onaylandı.
  *   Stok kontrolü.
  *   Stok rezerve edildi.
  *   Depo hazırlığı bekliyor.
  *   Toplama başladı.
  *   Toplama tamamlandı.
  *   Paketleme yapılıyor.
  *   Fatura oluşturuldu.
  *   Sevkiyata hazır.
  *   Kargoya teslim edildi.
  *   Teslim edildi.
  *   İptal edildi.
  *   İade talebi açıldı.
  *   İade tamamlandı.
Her siparişin hangi aşamada beklediği ve ne kadar süredir o aşamada olduğu görüntülenmelidir.
6.4. Siparişin otomatik işlenmesi
Örnek Trendyol sipariş akışı:

  1.  Trendyol'dan sipariş sisteme gelir.
  2.  Ürün SKU ve barkod eşleştirmesi yapılır.
  3.  Müşteri ve teslimat bilgileri alınır.
  4.  Stok kontrolü yapılır.
  5.  Stok varsa ürün rezerve edilir.
  6.  Depo için toplama emri açılır.
  7.  Personel ürünleri raflardan toplar.
  8.  Barkodla ürün doğrulaması yapılır.
  9.  Paketleme gerçekleştirilir.
  10. Kargo etiketi oluşturulur.
  11. E-fatura / e-arşiv süreci işletilir.
  12. Kargo firması teslim alır.
  13. Kargo takip numarası siparişe eklenir.
  14. Sipariş durumu pazaryerine aktarılır.
  15. Teslimat ve iade durumu takip edilir.
Kritik özellik: Aynı siparişin iki defa sisteme alınmasını engelleyen sipariş numarası kontrolü olmalıdır. Aynı anda farklı kanallardan sipariş geldiğinde stokların yanlışlıkla fazla satılmasını önlemek için stok rezervasyonu anlık çalışmalıdır.
6.5. Fiyat ve kampanya yönetimi
Her satış kanalı için ayrı fiyat tanımlanabilmelidir.
Örneğin:
Kanal
Satış fiyatı
Web sitesi
299 TL
Trendyol
329 TL
Hepsiburada
319 TL
Bayi
190 TL
Kurumsal müşteri
210 TL
Bunlar örnek fiyatlardır.
Sistem şu kampanyaları desteklemelidir:

  *   İkinci ürün 1 TL.
  *   Bir alana bir bedava.
  *   3 al 2 öde.
  *   Sepette yüzde indirim.
  *   Belirli tutar üzerinde ücretsiz kargo.
  *   Ürün seti kampanyası.
  *   Kupon tanımlama.
  *   Bayiye özel fiyat.
  *   Müşteriye özel indirim.
  *   Dönemsel kampanya.
Kampanyaların başlangıç ve bitiş tarihi, kullanım adedi, maksimum indirim tutarı ve hangi kanalda geçerli olduğu tanımlanmalıdır.
7. Sevkiyat ve lojistik yönetimi
Bu modül siparişin depodan çıkıp müşteriye ulaşmasına kadar olan süreci yönetmelidir.
7.1. Sevkiyat hazırlama

  *   Siparişler sevkiyat havuzuna düşer.
  *   Sevkiyat önceliği belirlenir.
  *   Aynı bölgeye giden siparişler gruplandırılabilir.
  *   Siparişler toplama listesine dönüştürülür.
  *   Depo personeline görev atanır.
  *   Ürün barkodları okutularak kontrol edilir.
  *   Paketleme ve koli sayımı yapılır.
  *   Kargo etiketi veya sevk irsaliyesi hazırlanır.
  *   Sevkiyat onayı verilir.
7.2. Toplama yöntemleri
Sistem farklı sipariş hacimlerine uygun yöntemler desteklemelidir:
Yöntem
Kullanım
Tekli toplama
Tek sipariş
Çoklu toplama
Birden fazla sipariş
Dalga toplama
Belirli saat aralığındaki siparişler
Bölge bazlı toplama
Depo alanlarına göre
Palet toplama
Toptan ve kurumsal sipariş
7.3. Kargo entegrasyonları
Yazılım birden fazla kargo firmasıyla çalışabilmelidir.

  *   Yurtiçi Kargo.
  *   Aras Kargo.
  *   MNG Kargo.
  *   Sürat Kargo.
  *   PTT Kargo.
  *   Hepsijet.
  *   Trendyol Express.
  *   Diğer anlaşmalı lojistik firmaları.
Kargo entegrasyonunda şu özellikler bulunmalıdır:

  *   Otomatik kargo etiketi.
  *   Barkodlu gönderi.
  *   Kargo takip numarası.
  *   Kargo ücreti.
  *   Kargo teslim durumu.
  *   Teslim edilemeyen siparişler.
  *   İade kargo takibi.
  *   Kargo firması performansı.
  *   Kargo faturası kontrolü.
7.4. B2B ve kurumsal sevkiyat
Bayi ve büyük müşteriler için farklı sevkiyat modeli olmalıdır.

  *   Sipariş bazlı koli hazırlama.
  *   Palet bazlı sevkiyat.
  *   Araç yükleme listesi.
  *   İrsaliye oluşturma.
  *   Plaka ve şoför kaydı.
  *   Sevk adresi.
  *   Teslimat randevusu.
  *   Teslim alan kişi.
  *   Teslimat tutanağı.
  *   Eksik ve hasarlı teslimat kaydı.
Özellikle 3 L deterjan, yumuşatıcı ve benzeri ağır ürünlerde koli ve palet bazında ağırlık kontrolü yapılabilmesi gerekir.
7.5. İade ve tersine lojistik
İade süreci bağımsız bir modül olarak bulunmalıdır.

  1.  Müşteri iade talebi oluşturur.
  2.  İade nedeni seçilir.
  3.  İade kargo kodu oluşturulur.
  4.  Ürün depoya gelir.
  5.  Barkod ve sipariş numarası kontrol edilir.
  6.  Ürün kalite kontrolünden geçirilir.
  7.  Satılabilir, hasarlı veya karantinalı olarak sınıflandırılır.
  8.  Uygun ürün yeniden stoğa alınır.
  9.  İade faturası veya diğer gerekli mali belge süreçleri yürütülür.
  10. Müşteri iade ve para iadesi süreci tamamlanır.
Kozmetik ürünlerde açılmış, kullanılmış veya hijyen güvenliği açısından yeniden satışa uygun olmayan ürünlerin otomatik olarak satış stoklarına alınması engellenmelidir.
8. CRM – Müşteri ve bayi ilişkileri yönetimi
CRM modülü sadece müşteri telefonlarını kaydeden bir ekran olmamalı. Satış ekibinin müşteriyi tanıdığı, geçmiş alışverişlerini takip ettiği, teklif hazırladığı ve yeni satış fırsatlarını yönettiği bir sistem olmalıdır.
8.1. Müşteri grupları
Müşteriler aşağıdaki gruplara ayrılmalıdır:

  *   Bireysel müşteriler.
  *   E-ticaret müşterileri.
  *   Eczaneler.
  *   Kozmetik mağazaları.
  *   Marketler.
  *   Temizlik ürünleri satıcıları.
  *   Toptancılar.
  *   Distribütörler.
  *   Bayiler.
  *   Kurumsal şirketler.
  *   Oteller ve işletmeler.
  *   Fabrikalar ve sanayi kuruluşları.
8.2. Müşteri kartı
Her müşteri için:
Bilgi
Açıklama
Cari kod
Benzersiz müşteri kodu
Firma adı
Ticari unvan
Yetkili kişi
İlgili kişi
Telefon
İletişim
E-posta
E-posta adresi
Vergi bilgileri
Vergi dairesi / numarası
Adres
Merkez ve teslimat adresleri
Müşteri grubu
Bayi, toptancı vb.
Satış temsilcisi
Sorumlu personel
Ödeme vadesi
30, 45, 60 gün vb.
Kredi limiti
Tanımlı risk limiti
Cari bakiye
Borç/alacak
Satış geçmişi
Önceki siparişler
İade geçmişi
İade kayıtları
Özel fiyat
Müşteriye özel fiyat listesi
8.3. CRM satış fırsatları
Satış ekibi potansiyel müşterileri aşamalı olarak takip edebilmelidir.
Örnek satış fırsatı akışı

  1.  Potansiyel müşteri
Yeni bayi veya kurumsal müşteri sisteme kaydedilir.

  1.  İlk iletişim
Telefon, e-posta veya ziyaret kaydı oluşturulur.

  1.  İhtiyaç analizi
Ürün grubu, aylık tüketim ve satın alma ihtiyacı belirlenir.

  1.  Teklif gönderildi
Ürün, miktar, fiyat ve ödeme koşulları iletilir.

  1.  Pazarlık / takip
Görüşme ve revizyonlar kaydedilir.

  1.  Sipariş alındı
Fırsat satış siparişine dönüştürülür.

  1.  Müşteri kazanıldı
Satış performansı ve müşteri devamlılığı takip edilir.
8.4. Müşteri aktivite takibi

  *   Telefon görüşmeleri.
  *   E-posta yazışmaları.
  *   WhatsApp görüşme notları.
  *   Firma ziyaretleri.
  *   Toplantı kayıtları.
  *   Teklif gönderimleri.
  *   Numune gönderimleri.
  *   Hatırlatmalar.
  *   Bir sonraki görüşme tarihi.
  *   Satış temsilcisi notları.
Sistem satış temsilcisine otomatik hatırlatma göndermelidir.
Örneğin: Bir bayiye teklif gönderildikten 3 gün sonra dönüş alınmadıysa satış temsilcisine takip görevi oluşturulmalıdır.
8.5. Müşteri segmentasyonu ve pazarlama
Müşteriler alışveriş sıklığı, toplam cirosu, ürün tercihi ve son alışveriş tarihine göre sınıflandırılabilmelidir.

  *   VIP müşteriler.
  *   Düzenli müşteriler.
  *   Yeni müşteriler.
  *   Uzun süredir alışveriş yapmayan müşteriler.
  *   Yüksek cirolu bayiler.
  *   Potansiyel bayiler.
  *   Kampanya müşterileri.
Ayrıca SMS, e-posta ve izinli pazarlama iletişimleri için entegrasyon bulunmalı; KVKK ve ticari elektronik ileti izinleri takip edilmelidir.
8.6. Bayi portalı
Bence sistemin önemli özelliklerinden biri de bayilerin kendilerine ait kullanıcı adı ve şifre ile giriş yapabilecekleri bir bayi portalıdır.
Bayi portalında:

  *   Güncel ürün kataloğu.
  *   Bayiye özel alış fiyatları.
  *   Ürün görselleri.
  *   Ürün açıklamaları.
  *   Stok durumu.
  *   Minimum sipariş miktarı.
  *   Online sipariş oluşturma.
  *   Önceki siparişler.
  *   Fatura ve irsaliye görüntüleme.
  *   Cari hesap ekstresi.
  *   Ödeme ve borç bilgileri.
  *   Kampanyalar.
  *   Sipariş takip.
Böylece bayiler telefonla sipariş vermek zorunda kalmadan kendi siparişlerini oluşturabilirler.
9. Muhasebe ve finans yönetimi
ERP entegrasyonu
Muhasebe modülü satış, satın alma, stok ve finans süreçleriyle bağlantılı çalışmalıdır. Amaç aynı verilerin farklı programlara tekrar tekrar girilmesini önlemektir.
9.1. Cari hesap yönetimi
Hem müşteri hem tedarikçi cari hesapları yönetilmelidir.
Müşteri cari hesabında:

  *   Açılış bakiyesi.
  *   Satış faturaları.
  *   Tahsilatlar.
  *   İadeler.
  *   İskontolar.
  *   Vade tarihleri.
  *   Kredi limiti.
  *   Borç ve alacak bakiyesi.
  *   Cari ekstre.
Tedarikçi cari hesabında:

  *   Alış faturaları.
  *   Ödemeler.
  *   Avanslar.
  *   İade faturaları.
  *   Vade tarihleri.
  *   Borç bakiyesi.
  *   Cari ekstre.
9.2. E-fatura ve e-arşiv süreçleri
Yazılım, yetkili bir e-belge entegratörü üzerinden aşağıdaki işlemleri desteklemelidir:

  *   E-fatura oluşturma.
  *   E-arşiv fatura oluşturma.
  *   E-fatura gelen kutusu.
  *   Gelen faturaları görüntüleme.
  *   Fatura reddetme / itiraz süreçleri.
  *   Fatura iptal ve düzeltme süreçleri.
  *   E-irsaliye oluşturma.
  *   E-irsaliye gelen belgeler.
  *   İrsaliye-fatura eşleştirmesi.
  *   Fatura PDF ve XML arşivi.
Belge türü, işlem tarihi ve müşterinin e-belge mükellefiyet durumuna göre doğru belge seçilmelidir.
9.3. Satışın muhasebeleştirilmesi
Örnek satış akışı:

  1.  Sipariş oluşur
Satış kanalı ve sipariş tutarı sisteme kaydedilir.

  1.  Satış faturası oluşturulur
Fatura ilgili müşteri veya mevzuata uygun alıcı bilgileri üzerinden düzenlenir.

  1.  Cari hesap kaydı oluşur
Vadeli satışta alacak, peşin satışta ilgili tahsilat kaydı takip edilir.

  1.  Stok çıkışı gerçekleşir
Ürün maliyeti stoktan düşülür.

  1.  Maliyet ve kârlılık hesaplanır
Satış fiyatı, maliyet, iskonto ve kanal giderleri analiz edilir.

  1.  Tahsilat takip edilir
Banka, kredi kartı veya pazaryeri ödeme kaydı eşleştirilir.
Muhasebe fişlerinin oluşturulması, kullanılan muhasebe yazılımına ve şirketin muhasebe politikalarına göre yapılandırılmalıdır.
9.4. Alış faturası ve satın alma muhasebesi
Tedarikçi faturası geldiğinde:

  1.  Satın alma siparişi ile eşleştirilir.
  2.  Depo mal kabul miktarı kontrol edilir.
  3.  Fatura miktarı ve fiyatı karşılaştırılır.
  4.  KDV kontrolü yapılır.
  5.  Alış faturası kaydedilir.
  6.  Tedarikçi cari hesabına borç kaydedilir.
  7.  Vade ve ödeme planı oluşturulur.
  8.  Ürün maliyetleri güncellenir.
Özellikle faturadaki miktar ile depoya giren miktar uyuşmuyorsa sistem onay vermeden işlemi tamamlamamalıdır.
9.5. Banka ve kasa yönetimi

  *   Banka hesapları.
  *   Kasa hareketleri.
  *   Havale / EFT.
  *   Kredi kartı tahsilatları.
  *   POS tahsilatları.
  *   Pazaryeri ödemeleri.
  *   Banka masrafları.
  *   POS komisyonları.
  *   Banka mutabakatı.
  *   Kredi ve finansman ödemeleri.
9.6. Pazaryeri muhasebeleştirme
Bu bölüm özellikle Trendyol ve Hepsiburada satışları için önemlidir.
Sistem her pazaryerinden gelen hakediş ve ödeme hareketlerini siparişlerle eşleştirebilmelidir.
Örnek:
İşlem
Tutar
Ürün satış tutarı
100.000 TL
Pazaryeri komisyonu
-15.000 TL
Kargo gideri
-3.000 TL
Hizmet / diğer kesintiler
-2.000 TL
Net hakediş
80.000 TL
Bu yalnızca örnek bir hesaplamadır.
Sistem şu işlemleri otomatik takip etmelidir:

  *   Sipariş bazında satış tutarı.
  *   Pazaryeri komisyonu.
  *   Kargo kesintisi.
  *   Reklam giderleri.
  *   Kampanya katkı payları.
  *   İade ve iptal kesintileri.
  *   Hizmet bedelleri.
  *   Hakediş tutarı.
  *   Bankaya yatan tutar.
  *   Ödeme farkları.
En önemli özellik: Pazaryeri raporları ile banka hesabına gelen tutar otomatik karşılaştırılmalı, eksik veya fazla ödeme varsa fark raporu oluşturulmalıdır.
9.7. Gelir-gider ve nakit akışı

  *   Günlük gelir.
  *   Günlük gider.
  *   Haftalık nakit akışı.
  *   Aylık nakit akışı.
  *   Beklenen tahsilatlar.
  *   Vadesi gelen borçlar.
  *   Vadesi geçmiş alacaklar.
  *   Personel giderleri.
  *   Kira ve depo giderleri.
  *   Nakliye giderleri.
  *   Reklam giderleri.
  *   Pazaryeri komisyonları.
  *   Üretim ve tedarik maliyetleri.
9.8. Ürün bazında gerçek kârlılık
Bence yönetim ekranının en önemli raporlarından biri budur.
Bir ürünün satış fiyatından yalnızca alış maliyetini çıkarmak gerçek kârlılığı göstermez.
Sistem aşağıdaki maliyetleri hesaplayabilmelidir:

  *   Ürün alış / üretim maliyeti.
  *   Ambalaj ve etiket maliyeti.
  *   Nakliye maliyeti.
  *   Depolama maliyeti.
  *   Pazaryeri komisyonu.
  *   Kargo gideri.
  *   Reklam maliyeti.
  *   İskonto.
  *   İade maliyeti.
  *   POS komisyonu.
Örnek kârlılık ekranı:
Açıklama
Tutar
KDV hariç satış geliri
250 TL
Ürün maliyeti
-100 TL
Ambalaj
-10 TL
Pazaryeri komisyonu
-30 TL
Kargo gideri
-20 TL
Reklam gideri
-15 TL
Diğer değişken giderler
-5 TL
Katkı kârı
70 TL
Buradaki örnek, KDV hariç tutarlar üzerinden oluşturulmuştur. Sabit genel giderler de dağıtıldığında ürünün tam maliyet ve net kârlılık raporu elde edilmelidir.
10. Üretim ve fason üretim yönetimi
Deterjan ve kozmetik firması açısından bu modül de oldukça önemlidir. Üretimi kendi tesisinizde veya fason üreticilerde yaptırmanız durumunda kullanılmalıdır.
10.1. Üretim planlama

  *   Ürün reçeteleri.
  *   Hammadde listesi.
  *   Ambalaj ve şişe listesi.
  *   Etiket ve koli ihtiyacı.
  *   Üretim miktarı.
  *   Üretim tarihi.
  *   Üretim partisi.
  *   Üretim maliyeti.
  *   Üretim fireleri.
10.2. Reçete yönetimi (BOM)
Örneğin 1.000 adet sıvı sabun üretimi için:
Girdi
İhtiyaç
Sıvı sabun ana karışımı
Reçeteye göre
Şişe
1.000 adet
Kapak
1.000 adet
Etiket
1.000 adet
Koli
Koli kapasitesine göre
Ambalaj malzemesi
Planlanan miktar
Sistem üretim öncesi eksik hammaddeleri göstermelidir.
10.3. Fason üretici takibi

  *   Üretici firma kartı.
  *   Üretim siparişi.
  *   Üreticiye gönderilen ambalajlar.
  *   Üreticiye gönderilen hammaddeler.
  *   Üretim miktarı.
  *   Üretim kayıpları.
  *   Gelen mamul miktarı.
  *   Üretim partisi.
  *   Kalite kontrol belgeleri.
  *   Üretim maliyeti.
  *   Üretim faturası.
10.4. Kalite kontrol
Kozmetik ve deterjan ürünleri için ürün bazlı kalite kontrol formları olmalıdır.
Örneğin:

  *   Ambalaj kontrolü.
  *   Kapak sızdırmazlık kontrolü.
  *   Etiket kontrolü.
  *   Görsel kontrol.
  *   Ağırlık / hacim kontrolü.
  *   Parti numarası kontrolü.
  *   Gerekli ürünlerde pH kontrolü.
  *   Gerekli analiz ve sertifika kayıtları.
Uygunsuz ürünler otomatik olarak karantina stoklarına alınmalıdır.
11. Yönetim paneli ve raporlama
Şirket sahibi veya yöneticisi sisteme giriş yaptığında bütün şirketin durumunu tek ekranda görebilmelidir.
11.1. Ana gösterge paneli
Yönetim Dashboard
Örnek ekran
Günlük satış
185.400 TL
Yeni sipariş
126
Toplam stok değeri
2,4 Mn TL
Sevkiyat bekleyen
34
Satış kanallarına göre dağılım
Tamamen örnek verilerle oluşturulmuştur.
B2B / Bayi
Hepsiburada
Trendyol
Amazon
Web sitesi
Operasyonel uyarılar

  *   12 ürün kritik stok seviyesinde.
  *   8 sipariş sevkiyat bekliyor.
  *   5 müşteri ödemesi gecikmiş.
  *   3 ürünün SKT kontrolü gerekiyor.
Yukarıdaki rakamlar ve dağılımlar yalnızca örnek gösterimdir.
11.2. Yönetim raporları
Rapor
Sağladığı bilgi
Günlük satış raporu
Günlük ciro ve adet
Aylık satış raporu
Aylık performans
Kanal bazlı satış
Trendyol, HB, B2B vb.
Ürün bazlı satış
En çok satan ürünler
Kârlılık raporu
Ürün ve kanal kârı
Stok raporu
Depodaki mevcut stok
Stok yaşlandırma
Ne kadar süredir depoda
SKT raporu
Tarihi yaklaşan ürünler
Sipariş raporu
Siparişlerin durumu
Sevkiyat raporu
Hazırlanan ve teslim edilen
İade raporu
İade oranları ve nedenleri
Cari raporu
Müşteri borç ve alacakları
Tahsilat raporu
Beklenen ve gerçekleşen
Tedarikçi raporu
Alış ve performans
Personel raporu
Kullanıcı işlem performansı
12. Kullanıcı, yetki ve onay yönetimi
Herkesin her işlemi yapabildiği bir yazılım kesinlikle tercih edilmemelidir.
Kullanıcı
Yetki
Şirket yöneticisi
Tüm modüller
Depo müdürü
Depo ve stok yönetimi
Depo personeli
Mal kabul, toplama, sayım
Satın alma
Tedarikçi ve sipariş
Satış ekibi
CRM, teklif, satış siparişi
E-ticaret ekibi
Pazaryeri ve web siparişleri
Finans
Cari, tahsilat, ödeme
Muhasebe
Fatura ve muhasebe kayıtları
Sevkiyat personeli
Paketleme ve sevkiyat
Raporlama kullanıcısı
Sadece görüntüleme
Özellikle aşağıdaki işlemler yönetici onayı gerektirmelidir:

  *   Stok düzeltme.
  *   Stok silme.
  *   Fiyat değişikliği.
  *   İskonto tanımlama.
  *   Sipariş iptali.
  *   İade onayı.
  *   Cari limit artırma.
  *   Vadeli satış onayı.
  *   Alış ve satış faturası iptali.
  *   Fire ve hasar kaydı.
Sistem her işlemin kim tarafından, hangi tarihte, hangi saatte yapıldığını kayıt altında tutmalıdır.
13. Entegrasyonlar ve otomatik veri aktarımı
Yazılımın farklı programlarla haberleşebilmesi gerekiyor.
Entegrasyon
İstenen özellik
Trendyol
Sipariş, stok, fiyat, fatura, iade
Hepsiburada
Sipariş, stok, fiyat, fatura, iade
Web sitesi
Sipariş, müşteri, stok, ödeme
Kargo firmaları
Etiket, takip, teslimat
E-fatura entegratörü
E-fatura, e-arşiv, e-irsaliye
Muhasebe programı
Cari, fatura, fiş, tahsilat
Bankalar
Hesap hareketleri, mutabakat
POS sistemleri
Tahsilat ve komisyon
SMS / e-posta
Bildirim ve müşteri iletişimi
WhatsApp Business
Müşteri iletişimi
Barkod cihazları
Depo işlemleri
E-ticaret altyapısı
Ürün ve sipariş aktarımı
Teknik olarak mutlaka istenmesi gerekenler:

  *   API desteği.
  *   Otomatik veri senkronizasyonu.
  *   Hata kayıt ekranı.
  *   Başarısız entegrasyon işlemlerini yeniden çalıştırma.
  *   Sipariş ve stok senkronizasyon logları.
  *   Mükerrer kayıt engelleme.
  *   Yetkilendirilmiş API erişimi.
  *   Veri yedekleme.
  *   Mobil uyumlu kullanım.
14. Mobil depo uygulaması ve el terminali
Depo personelinin bilgisayar başında işlem yapmak zorunda kalmaması gerekir.
Mobil uygulama veya Android el terminali üzerinden aşağıdaki işlemler yapılabilmelidir:

  1.  Ürün barkodu okutma.
  2.  Mal kabul.
  3.  Raf yerleştirme.
  4.  Stok sorgulama.
  5.  Palet oluşturma.
  6.  Palet transferi.
  7.  Sipariş toplama.
  8.  Paketleme kontrolü.
  9.  Sevkiyat onayı.
  10. İade kabulü.
  11. Sayım.
  12. Hasarlı ürün kaydı.
Örneğin personel el terminalinden bir ürün barkodunu okuttuğunda ürünün hangi lokasyonda bulunduğunu, kaç adet olduğunu, hangi LOT'a ait olduğunu ve SKT'sini görebilmelidir.
15. Otomatik bildirim ve uyarı sistemi
Sistem yalnızca veri göstermemeli, gerekli durumlarda ilgili kişileri uyarmalıdır.
Olay
Bildirim alacak kişi
Kritik stok
Depo müdürü / satın alma
Yeni sipariş
E-ticaret ekibi
Sevkiyat gecikmesi
Lojistik sorumlusu
SKT yaklaşması
Depo müdürü
Sipariş iptali
Satış ekibi
Müşteri borcu gecikmesi
Finans
Tedarikçi termin gecikmesi
Satın alma
Pazaryeri ödeme farkı
Finans
Sayım farkı
Depo müdürü
Kârlılık düşüşü
Yönetici
Bildirimler sistem içinden, e-posta veya uygun entegrasyon üzerinden gönderilebilmelidir.
16. Yazılımda bulunması gereken ek özellikler
Bunlar ilk bakışta temel modüller kadar önemli görünmeyebilir ancak işletme büyüdükçe ciddi fayda sağlar.

  *   Çoklu şirket yönetimi.
  *   Çoklu depo yönetimi.
  *   Çoklu kullanıcı.
  *   Çoklu para birimi.
  *   Dövizli alış ve satış.
  *   Farklı fiyat listeleri.
  *   Müşteriye özel fiyatlandırma.
  *   Otomatik iskonto.
  *   Kredi limiti kontrolü.
  *   Satış temsilcisi prim hesaplama.
  *   Depo personeli performans takibi.
  *   Ürün hareket geçmişi.
  *   Evrak ve belge arşivi.
  *   Excel içe ve dışa aktarma.
  *   Toplu ürün açılışı.
  *   Toplu fiyat güncelleme.
  *   Toplu stok güncelleme.
  *   QR kod desteği.
  *   Barkod etiket basımı.
  *   Kullanıcı işlem geçmişi.
  *   Otomatik yedekleme.
  *   Yetkilendirme ve veri güvenliği.
17. Baştan sona tüm işletme süreçlerinin birbirine bağlanması
Yazılım firmasına özellikle aşağıdaki bütünleşik iş akışını anlatmanızı öneriyorum.
Şirketin uçtan uca operasyon akışı

  1.  SATIN ALMA
İhtiyaç belirleme → Teklif → Onay → Tedarikçi siparişi

  1.  ÜRÜN KABUL
İrsaliye → Sayım → Barkod → LOT / SKT → Mal kabul

  1.  DEPO
Palet → Raf → Lokasyon → Stok → Sayım

  1.  SATIŞ
Müşteri → Teklif → Sipariş → Fiyat / kampanya → Ödeme kontrolü

  1.  SİPARİŞ HAZIRLAMA
Stok rezervasyonu → Toplama → Barkod kontrolü → Paketleme

  1.  SEVKİYAT
İrsaliye → Kargo / araç → Teslimat → Takip

  1.  FİNANS VE MUHASEBE
Fatura → Cari hesap → Tahsilat → Banka → Muhasebe

  1.  CRM VE SATIŞ SONRASI
Müşteri memnuniyeti → İade → Tekrar sipariş → Kampanya

  1.  YÖNETİM RAPORLAMA
Ciro → Maliyet → Kârlılık → Nakit akışı → Performans
18. Yazılım firmasıyla paylaşılması gereken teknik ve operasyonel şartlar
Yazılımı yaptırırken yalnızca özellik listesi istemeyin. Aşağıdaki kriterleri de sözleşme ve proje kapsamına dahil edin.
Konu
Talep edilmesi gereken özellik
Kullanım
Web tabanlı ve mobil uyumlu
Depo
Barkod ve el terminali
Veritabanı
Merkezi ve güvenli
Entegrasyon
API altyapısı
Kullanıcı
Rol bazlı yetkilendirme
Log
Tüm işlemlerin kayıt altında olması
Yedekleme
Otomatik ve düzenli
Raporlama
Excel ve PDF
Hız
Çoklu sipariş işlem kapasitesi
Güvenlik
Kullanıcı ve veri erişim kontrolleri
Destek
Teknik destek ve SLA
Eğitim
Personel ve yönetici eğitimi
Test
Canlıya geçiş öncesi test ortamı
Güncelleme
Sistem ve entegrasyon bakımı
Ayrıca yazılım firmasından şu sorulara yazılı cevap alın:

  *   Yazılımın kaynak kodu ve veritabanı kimin kontrolünde olacak?
  *   Veri dışa aktarımı mümkün mü?
  *   Kullanıcı sayısına göre ek ücret var mı?
  *   Depo ve sipariş hacmine göre performans sınırı var mı?
  *   API kullanımı ücretli mi?
  *   Yeni pazaryeri entegrasyonu ne kadar sürede yapılabiliyor?
  *   Hatalı stok veya sipariş hareketleri nasıl geri alınabiliyor?
  *   Sistem kesintisinde siparişler nasıl korunuyor?
  *   Teknik destek hangi saatlerde sağlanıyor?
19. Yazılımın devreye alınma aşamaları
Bütün modülleri aynı anda devreye almak yerine aşamalı ilerlemek daha sağlıklı olacaktır.
Aşama
Kapsam
Öncelik
1
Ürün kartları ve depo tanımları
Çok yüksek
2
Stok, LOT, SKT ve barkod
Çok yüksek
3
Sipariş ve pazaryeri entegrasyonları
Çok yüksek
4
Toplama, paketleme ve sevkiyat
Çok yüksek
5
Cari hesap ve muhasebe
Çok yüksek
6
Satın alma ve tedarikçi yönetimi
Yüksek
7
CRM ve bayi portalı
Yüksek
8
Üretim ve fason üretim
Orta-yüksek
9
Gelişmiş raporlama ve kârlılık
Yüksek
10
Otomasyon ve gelişmiş analiz
Orta
20. Yazılım firmasına gönderilecek resmi ihtiyaç ve teklif talebi
Kısacası deterjan ve kozmetik sektöründeki faaliyetleri kapsamında; depo, stok, sipariş, sevkiyat, satın alma, müşteri ilişkileri (CRM), finans ve muhasebe süreçlerinin tek bir merkezi sistem üzerinden yönetilmesini hedefleniyor.
1. Ürün ve Stok Yönetimi

  *   Ürün kartları, barkod ve SKU yönetimi.
  *   Ürün kategori ve alt kategori tanımlamaları.
  *   LOT / parti ve SKT takibi.
  *   FIFO / FEFO stok yönetimi.
  *   Minimum ve maksimum stok uyarıları.
  *   Depolar arası transfer.
  *   Sayım ve stok mutabakatı.
  *   Palet, koli, raf ve lokasyon yönetimi.
2. Depo Yönetimi (WMS)

  *   Mal kabul ve ürün giriş işlemleri.
  *   Barkod okuyucu ve el terminali desteği.
  *   Raf ve lokasyon bazlı stok takibi.
  *   Sipariş toplama ve paketleme.
  *   Palet bazlı sevkiyat.
  *   İade, hasarlı ürün ve karantina yönetimi.
3. Sipariş ve Satış Yönetimi

  *   Trendyol ve Hepsiburada entegrasyonları.
  *   Web sitesi ve B2B sipariş entegrasyonu.
  *   Telefon ve manuel sipariş girişi.
  *   Merkezi sipariş havuzu.
  *   Stok rezervasyonu.
  *   Kanal bazlı fiyat ve kampanya yönetimi.
  *   Sipariş durumlarının anlık takibi.
4. Sevkiyat ve Lojistik

  *   Kargo firmalarıyla entegrasyon.
  *   Otomatik kargo etiketi ve takip numarası.
  *   Sevkiyat ve araç yükleme planlaması.
  *   İrsaliye yönetimi.
  *   Teslimat takibi.
  *   İade ve tersine lojistik.
5. Satın Alma ve Tedarikçi Yönetimi

  *   Tedarikçi kartları.
  *   Satın alma talepleri ve siparişleri.
  *   Teklif karşılaştırma.
  *   Termin ve teslimat takibi.
  *   Alış fiyatı geçmişi.
  *   Tedarikçi performans raporları.
6. CRM ve Müşteri Yönetimi

  *   Bireysel, bayi, toptancı ve kurumsal müşteri kartları.
  *   Müşteri satış geçmişi.
  *   Teklif ve satış fırsatı yönetimi.
  *   Satış temsilcisi aktivite takibi.
  *   Müşteri segmentasyonu.
  *   Bayiye özel fiyatlandırma.
  *   Online bayi sipariş portalı.
7. Finans ve Muhasebe

  *   Cari hesap yönetimi.
  *   E-fatura, e-arşiv ve e-irsaliye entegrasyonu.
  *   Alış ve satış faturaları.
  *   Banka ve kasa hareketleri.
  *   POS ve pazaryeri hakediş takibi.
  *   Tahsilat ve ödeme planlaması.
  *   Gelir-gider yönetimi.
  *   Ürün ve kanal bazında kârlılık analizi.
  *   Muhasebe programı entegrasyonu.
8. Raporlama ve Yönetim Paneli

  *   Günlük, haftalık ve aylık satış raporları.
  *   Kanal bazlı ciro ve kârlılık.
  *   Ürün bazlı satış performansı.
  *   Stok yaşlandırma ve stok devir hızı.
  *   SKT raporları.
  *   Sipariş ve sevkiyat performansı.
  *   Müşteri ve tedarikçi cari raporları.
  *   Nakit akışı ve finansal raporlar.
Yukarıdaki modüllere ek olarak sistemin API altyapısına sahip olması, mobil cihazlardan kullanılabilmesi, kullanıcı bazlı yetkilendirme sunması ve tüm işlemleri kayıt altında tutması bizim için önemlidir.
Bu kapsamda tarafımıza aşağıdaki konuları içeren detaylı bir teklif iletilmesini rica ederiz:

  1.  Yazılımın modül bazlı kapsamı ve özellikleri.
  2.  Standart olarak sunulan ve özel geliştirme gerektiren özellikler.
  3.  Kurulum ve devreye alma maliyeti.
  4.  Aylık / yıllık lisans ve kullanım bedelleri.
  5.  Kullanıcı ve depo sayısına göre fiyatlandırma.
  6.  Pazaryeri, kargo ve muhasebe entegrasyon maliyetleri.
  7.  Proje teslim süresi ve uygulama takvimi.
  8.  Eğitim, teknik destek ve bakım koşulları.
  9.  Veri yedekleme ve güvenlik altyapısı.
  10. Demo veya test ortamı kullanım imkânı.
Amacımız yalnızca stok takip sistemi kurmak değil; satın alma, depo, satış, sevkiyat, CRM ve muhasebe süreçlerini birbirine entegre ederek şirketimizin tüm operasyonlarını merkezi olarak yönetebileceğimiz sürdürülebilir bir altyapı oluşturmaktır.
Konuya ilişkin çözüm önerilerinizi, varsa benzer sektörlerdeki uygulama örneklerinizi ve detaylı fiyat teklifinizi paylaşmanızı rica ederiz.
İyi çalışmalar dileriz.
21. Benim önerdiğim en önemli 10 özellik
Yazılım geliştirirken bütün özellikler eşit önemde değildir. Özellikle ilk etapta şu 10 özelliğin eksiksiz çalışmasını koşabiliriz
Tek merkezden stok yönetimi
Bütün satış kanallarında gerçek zamanlı stok.
LOT ve SKT takibi
Kozmetik ve kimyasal ürünlerin parti bazlı izlenmesi.
Palet ve lokasyon yönetimi
Depodaki her ürünün fiziksel konumu.
Otomatik sipariş aktarımı
Trendyol, Hepsiburada  amazon ve web sitesi.
Barkodlu depo operasyonu
Mal kabul, toplama ve sevkiyat doğrulaması.
Otomatik faturalama
Sipariş ve muhasebe süreçlerinin entegrasyonu.
Pazaryeri hakediş kontrolü
Komisyon, kargo ve banka ödemelerinin mutabakatı.
Ürün bazlı gerçek kârlılık
Tüm değişken maliyetleri dikkate alan analiz.
CRM ve bayi portalı
Müşteri, satış fırsatı ve tekrar sipariş yönetimi.
Yönetim dashboard'u
Şirketin tüm operasyonlarını tek ekranda izleme.
22. Projeyi netleştirmek için üç önemli konu
Bu sistemi şirketinizin gerçek operasyonlarına göre şekillendirmek için özellikle üç konuya karar vermek gerekiyor.
1. Üretim modeliniz nasıl?
Hem kendi üretimimiz hem fason üretimimiz var.
2. Depo yapılanmanız nasıl olacak?
Birden fazla depo.
Kendi depomuz + dış lojistik deposu. opsiyonel
3. Muhasebe sisteminiz nasıl çalışacak?
Muhasebe de aynı yazılımın içinde olsun.
Mevcut muhasebe programımızla entegre çalışsın.
4. Hangi satış kanallarını kullanıyoruz?
Trendyol
Hepsiburada
B2B bayi
Web sitesi
Amazon
Eczane kanalı
Kurumsal satış





[cid:image001.png@01DD7765.5625C120]
