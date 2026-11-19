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
