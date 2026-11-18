# Yol Haritası

Durum: ✅ tamam · 🟡 kısmi · ⬜ başlanmadı. Sıra müşteri dokümanı §19'a göre.

| # | Modül (kod) | Kapsam | Durum |
|---|---|---|---|
| 0 | Çekirdek (`core`) | modül sistemi, olay yolu, işlem logu, onay akışı, roller, numara serisi, ana panel | ✅ |
| 1 | Ürün kartları (`catalog`) | SKU/barkod, koli/palet, kanal fiyatı, set/kampanya paketi | ✅ (toplu Excel içe aktarma ⬜) |
| 2 | Depo ve stok (`inventory`) | depo/lokasyon, LOT/SKT, FEFO, rezervasyon, transfer, sayım+onay, stok durumları, uyarılar, satın alma önerisi formülü, barkod sorgu | ✅ (palet doluluk raporu, stok yaşlandırma ⬜) |
| 3 | Sipariş (`sales`) | merkezi sipariş havuzu, kanallar, sipariş durumları, kampanya kuralları, mükerrer engeli | ⬜ |
| 4 | Sevkiyat (`shipping`) | toplama yöntemleri, paketleme, barkod doğrulama, araç yükleme, iade/tersine lojistik | ⬜ |
| 5 | Cari ve muhasebe (`accounting`) | cari hesap, fatura, tahsilat/ödeme, banka/kasa, hakediş mutabakatı, kârlılık; dış muhasebe programına aktarım | ⬜ |
| 6 | Satın alma (`purchase`) | talep, teklif karşılaştırma, sipariş, mal kabul eşleştirme, tedarikçi performansı | ⬜ |
| 7 | CRM ve bayi portalı (`crm`, `portal`) | müşteri kartı, fırsat, aktivite, segment, bayi girişi | ⬜ |
| 8 | Üretim ve fason (`production`) | BOM, üretim emri, fason takibi, kalite kontrol → karantina | ⬜ |
| 9 | Raporlama (`reports`) | yönetim paneli, kanal/ürün kârlılığı, Excel/PDF | ⬜ |
| 10 | Entegrasyonlar (`integrations`) | Trendyol, Hepsiburada, Amazon, web, kargo, e-belge entegratörü, banka | ⬜ |
| — | Bildirimler (`notifications`) | sistem içi + e-posta uyarıları (§15) | ⬜ |

## Açık sorular (müşteriye)
- Mevcut muhasebe programı hangisi? (Logo / Mikro / Luca / Paraşüt …) → `accounting` aktarım biçimi buna bağlı.
- E-belge entegratörü hangisi?
- Dış lojistik deposu kullanılacak mı, API'si var mı?
- El terminali marka/model (Android tarayıcı mı, özel uygulama mı)?
