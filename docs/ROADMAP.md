# Yol Haritası

Durum: ✅ tamam · 🟡 kısmi · ⬜ başlanmadı. Sıra müşteri dokümanı §19'a göre.

| # | Modül (kod) | Kapsam | Durum |
|---|---|---|---|
| 0 | Çekirdek (`core`) | modül sistemi, olay yolu, işlem logu, onay akışı, roller, numara serisi, ana panel | ✅ |
| 1 | Ürün kartları (`catalog`) | SKU/barkod, koli/palet, kanal fiyatı, set/kampanya paketi | ✅ (toplu Excel içe aktarma ⬜) |
| 2 | Depo ve stok (`inventory`) | depo/lokasyon, LOT/SKT, FEFO, rezervasyon, transfer, sayım+onay, stok durumları, uyarılar, satın alma önerisi formülü, barkod sorgu | ✅ (palet doluluk raporu, stok yaşlandırma ⬜) |
| 3 | Sipariş (`sales`) + Cari (`partners`) | merkezi sipariş havuzu, kanallar, 13 durum, kampanyalar, mükerrer engeli, kredi limiti, onaylı iptal | ✅ |
| 4 | Sevkiyat (`shipping`) | toplama listesi, barkod doğrulama, paketleme+tartı, sevk, teslim, çoklu toplama, iade (hijyen kuralı, onay) | ✅ (kargo etiketi → entegrasyon) |
| 5 | Cari ve muhasebe (`accounting`) | cari hesap, fatura, tahsilat/ödeme, banka/kasa, hakediş mutabakatı, kârlılık; dış muhasebe programına aktarım | ⬜ |
| 6 | Satın alma (`purchase`) | talep, öneri, teklif karşılaştırma, onaylı sipariş, mal kabul, ortalama maliyet, tutanak, performans | ✅ (fatura eşleştirme → muhasebe) |
| 7 | CRM ve bayi portalı (`crm`, `portal`) | müşteri kartı, fırsat, aktivite, segment, bayi girişi | ⬜ |
| 8 | Üretim ve fason (`production`) | BOM, üretim emri, fason takibi, kalite kontrol → karantina | ⬜ |
| 9 | Raporlama (`reports`) | yönetim paneli, kanal/ürün kârlılığı, Excel/PDF | ⬜ |
| 10 | Entegrasyonlar (`integrations`) | **sihirbaz** ile kurulum; Trendyol, Hepsiburada, Amazon, web, kargo, e-belge, banka; hata/yeniden dene ekranı, senkron logları | ⬜ (sıradaki) |
| — | Bildirimler (`notifications`) | sistem içi + e-posta uyarıları (§15) | ⬜ |

## Açık sorular (müşteriye)
- Mevcut muhasebe programı hangisi? (Logo / Mikro / Luca / Paraşüt …) → `accounting` aktarım biçimi buna bağlı.
- E-belge entegratörü hangisi?
- Dış lojistik deposu kullanılacak mı, API'si var mı?
- El terminali marka/model (Android tarayıcı mı, özel uygulama mı)?

## Arayüz
Ortak tasarım sistemi `static/css/app.css` + `core/templatetags/ui.py` (ikon, durum rozeti). Kenar menüsü modül MANIFEST'lerinden otomatik.
Arka ofis kayıt ekranları şimdilik markalı Django yönetim paneli; sık kullanılan ekranlar (stok, sipariş havuzu, toplama, mal kabul) özel tasarım.
Kurulum gerektiren her şey (entegrasyon, ilk kurulum) adım adım **sihirbaz** olarak yapılacak.
