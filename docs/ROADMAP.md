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
| 7 | Bayi portalı (`portal`) · CRM (`crm`) | bayi portalı ✅; fırsat panosu, aktivite/hatırlatma, segmentler ✅; SMS/e-posta kampanya ⬜ | ✅ |
| 8 | Üretim ve fason (`production`) | BOM, üretim emri, fason takibi, kalite kontrol → karantina | ⬜ |
| 9 | Raporlama (`reports`) | yönetim paneli, kanal/ürün kârlılığı, Excel/PDF | ⬜ |
| 10 | Entegrasyonlar (`integrations`) | sihirbaz, şifreli bilgiler, iş kuyruğu + yeniden deneme + loglar, arka plan işçisi; **Uyumsoft e-Fatura/e-Arşiv** ✅ (test ortamında doğrulandı); **Trendyol** sipariş/stok/fiyat/durum ✅; Hepsiburada, Amazon, web, kargo, banka ⬜ | 🟡 |
| — | Bildirimler (`notifications`) | sistem içi + e-posta uyarıları (§15) | ⬜ |

## Açık sorular (müşteriye)
- Muhasebe/e-belge: **Uyumsoft** (cevaplandı). Uyumsoft canlı kullanıcı bilgileri ve seri ön ekleri müşteriden alınacak.
- Dış lojistik deposu kullanılacak mı, API'si var mı?
- El terminali marka/model (Android tarayıcı mı, özel uygulama mı)?

## Arayüz
Ortak tasarım sistemi `static/css/app.css` + `core/templatetags/ui.py` (ikon, durum rozeti). Kenar menüsü modül MANIFEST'lerinden otomatik.
Arka ofis kayıt ekranları uygulama kabuğuna alınmış Django yönetim paneli (aynı menü/tasarım); sık kullanılan ekranlar (stok, sipariş havuzu, toplama, mal kabul) özel tasarım.
Kurulum gerektiren her şey (entegrasyon, ilk kurulum) adım adım **sihirbaz** olarak yapılacak.
Tüm ekranlar masaüstü, tablet ve telefon için duyarlı; dokunma alanları ≥44px; site ana ekrana uygulama olarak eklenebilir (manifest).
Kullanıcı başına menü rengi (Görünüm) ve sürükle-bırak ana panel düzeni (`core.UserPreference`).
Ana panel: grafikler (ciro, kanal, ürün, stok değeri), kart/grafik seçme paneli, döviz-altın kur şeridi (`core/rates.py`). Tüm listelerde Excel'e aktarma ve filtre çubuğu.
