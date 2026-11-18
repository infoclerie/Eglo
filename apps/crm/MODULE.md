# crm — CRM

Bağımlılık: core, partners, sales. Müşteri dokümanı §8.3–8.5.
- **Satış fırsatları** `/crm/`: aşama panosu (sürükle-bırak). Aşamalar: potansiyel → ilk iletişim → ihtiyaç analizi → teklif → pazarlık → kazanıldı/kaybedildi.
  "Teklif gönderildi"ye geçince `crm.quote_followup_days` (3) gün sonrasına otomatik takip görevi.
- **Takiplerim** `/crm/takipler/`: tarihi gelen/gecikmiş aktiviteler (telefon, ziyaret, teklif, numune...), tamamlandı işareti; ana panel kartı.
- **Segmentler** `/crm/segmentler/`: VIP / düzenli / yeni / uzun süredir almayan / potansiyel / aktif (kurallar `services.py` başında).
Sıradaki: SMS/e-posta kampanya gönderimi (İYS izinli), fırsattan sipariş oluşturma.
