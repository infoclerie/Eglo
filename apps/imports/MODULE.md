# imports — Excel ile toplu yükleme (§16)

- Türler (`services.KINDS`): ürün kartları (ekle/güncelle), fiyatlar (liste, maliyet, her kanal için "Fiyat: <kanal>" sütunu),
  stok girişi (lokasyon + LOT + SKT; `inventory.receive`, hareket türü sayım farkı/açılış).
- Akış: şablon indir → yükle → önizleme (satır satır hata) → onay. Hata olan dosyada HİÇBİR şey yazılmaz (tek transaction).
- Türkçe sayı (1.234,56) ve tarih (gg.aa.yyyy) kabul edilir; seçim sütunlarında kod veya Türkçe ad yazılabilir.
- Ürün güncellemede boş hücre mevcut değeri değiştirmez. Dosya önizleme ile onay arasında oturumda (base64) tutulur, en fazla 8 MB.
- İzin: `imports.add_importpermission`.
