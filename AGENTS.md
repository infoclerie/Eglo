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
