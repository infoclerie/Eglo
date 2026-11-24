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
