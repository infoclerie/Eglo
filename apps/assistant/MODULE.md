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
