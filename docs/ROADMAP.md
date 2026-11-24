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
