# Müşteri ihtiyaç dokümanı (Eglo Kozmetik, 18.11.2026 e-postası, düz metin)


Deterjan ve Kozmetik Firması İçin Entegre Depo Yönetimi, Sipariş, Sevkiyat, Stok, CRM ve Muhasebe Yazılımı
Bir deterjan ve kozmetik firması için kurulacak yazılımı yalnızca bir depo takip programı olarak düşünmemek gerekir. İhtiyacımız olan sistem; satın almadan ürün kabulüne, stok yönetiminden siparişe, siparişten sevkiyata, müşteri ilişkilerinden tahsilata ve muhasebeleştirmeye kadar bütün süreçleri tek merkezden yönetebilen entegre bir ERP + WMS + CRM sistemi olmalıdır.
Özellikle hem kozmetik hem de temizlik ürünleri satacağınız için yazılımda standart stok takibinin yanında şu özellikler kritik önem taşıyor:

  *   Üretim partisi (LOT) ve SKT (son kullanma tarihi) takibi.
  *   FIFO / FEFO stok yönetimi.
  *   Barkod, koli ve palet bazlı depo yönetimi.
  *   Trendyol, Hepsiburada, web sitesi ve bayi siparişlerinin tek ekranda toplanması.
  *   B2B bayi ve kurumsal müşteri yönetimi.
  *   Otomatik sevkiyat ve kargo entegrasyonu.
  *   E-fatura, e-arşiv, e-irsaliye ve muhasebe entegrasyonu.
  *   Ürün bazında kârlılık, maliyet ve stok devir hızı analizi.
Aşağıda yazılım firmasına doğrudan iletebileceğiniz şekilde kapsamlı bir yazılım ihtiyaç ve süreç dokümanı hazırladım.
1. Yazılımın genel mimarisi
Entegre işletme yönetim sistemi
MERKEZİ YÖNETİM PANELİ
Tüm şirket operasyonlarının yönetildiği ana ekran
Depo / WMS
Raf, palet, LOT, SKT
Stok Yönetimi
Giriş, çıkış, transfer
Sipariş Yönetimi
B2B, B2C, pazaryeri
Sevkiyat Yönetimi
Toplama, paketleme, kargo
CRM
Müşteri, bayi, satış
Muhasebe / Finans
Fatura, tahsilat, ödeme
ENTEGRASYON KATMANI
Trendyol • Hepsiburada • Web sitesi • E-ticaret • Kargo • Banka • E-belge • Muhasebe
RAPORLAMA VE YÖNETİMSEL ANALİZ
Ciro • Kârlılık • Stok • Satış performansı • Nakit akışı • Operasyon verimliliği
Sistemin bütün modülleri aynı veritabanı üzerinden çalışmalı. Örneğin Trendyol'dan bir sipariş geldiğinde sipariş kaydı oluşturulmalı, stok rezerve edilmeli, depo toplama emri açılmalı, ürün sevk edildiğinde stok düşmeli, fatura oluşturulmalı ve muhasebe kaydı meydana gelmelidir.
2. Ürün kartı ve ürün ana veri yönetimi
Bütün operasyonların başlangıcı ürün kartıdır. Her ürünün sistemde standart bir tanımı bulunmalıdır.
2.1. Ürün kartında bulunması gereken bilgiler
Alan
Açıklama
Ürün kodu
Şirkete özel SKU
Barkod
EAN / GTIN
Ürün adı
Ticari ürün adı
Marka
Clerie vb.
Ana kategori
Kozmetik / Temizlik
Alt kategori
Serum, krem, deterjan vb.
Ürün açıklaması
Ürün özellikleri
Birim
Adet, koli, litre, kg
Hacim / ağırlık
100 ml, 750 ml, 3 L vb.
Koli içi adet
Bir kolideki ürün sayısı
Koli barkodu
Koli bazlı tanımlama
Palet kapasitesi
Palet başına koli/adet
Alış maliyeti
Birim tedarik maliyeti
Satış fiyatı
Kanal bazında satış fiyatı
KDV oranı
Muhasebe parametresi
Minimum stok
Alt stok seviyesi
Maksimum stok
Üst stok seviyesi
LOT / SKT
Parti ve son kullanma tarihi
Raf ömrü
Ürün raf ömrü
Depolama koşulu
Isı, ışık, nem vb.
Ürün görseli
Fotoğraf ve ambalaj görseli
2.2. Ürün grupları
Sistem ürünleri farklı kategorilerde yönetebilmelidir:

  *   Kozmetik: Serum, krem, güneş kremi, maske, tonik, temizleme jeli.
  *   Sıvı temizlik ürünleri: Yumuşatıcı, sıvı sabun, çamaşır suyu.
  *   Sprey ürünleri: Oda kokusu, yüzey temizleyici, Arap sabunu spreyi.
  *   Konsantre ürünler.
  *   Numune ve tester ürünleri.
  *   Promosyon ve hediye ürünleri.
  *   Set ve kampanya paketleri.
Önemli: Aynı ürünün tekli, 3'lü set, 6'lı koli ve kampanya paketi gibi farklı satış şekilleri tanımlanabilmeli. Set içindeki ürünlerin stokları ana ürünlerden otomatik düşmeli.
3. Depo yönetim sistemi (WMS)
En kritik modül
Depo yönetimi yalnızca toplam stok adedini görmekten ibaret olmamalı. Hangi ürünün hangi depoda, hangi koridorda, hangi rafta, hangi palet üzerinde ve hangi üretim partisinde bulunduğu takip edilmelidir.
3.1. Depo tanımlamaları
Sistem birden fazla depo ve depo alanı tanımlamayı desteklemelidir.
Örnek depo yapısı:
Depo
Açıklama
Ana depo
Genel ürün stokları
Kozmetik deposu
Kozmetik ürünleri
Temizlik deposu
Deterjan ve sıvı ürünler
Sevkiyat alanı
Siparişi hazırlanmış ürünler
İade alanı
Müşteri iadeleri
Karantina alanı
Kontrol bekleyen ürünler
Hasarlı ürün alanı
Satışa uygun olmayan ürünler
Numune alanı
Tester ve promosyonlar
3.2. Raf ve lokasyon yönetimi
Her depo için aşağıdaki yapı oluşturulmalıdır:

  *   Depo kodu.
  *   Koridor kodu.
  *   Raf kodu.
  *   Kat / göz numarası.
  *   Palet lokasyonu.
  *   Maksimum taşıma kapasitesi.
  *   Maksimum hacim kapasitesi.
  *   Ürün kabul durumu.
  *   Ürün toplama durumu.
Örnek lokasyon kodu:
A-02-03-01
A
Depo
02
Koridor
03
Raf
01
Kat
Her lokasyon barkodla tanımlanmalı ve el terminalinden okutulabilmelidir.
3.3. Depoya ürün giriş süreci
Ürün girişleri aşağıdaki şekilde ilerlemelidir:

  1.  Satın alma siparişi oluşturulur.
  2.  Tedarikçi ürünleri depoya gönderir.
  3.  Depo personeli irsaliye ve sipariş bilgilerini kontrol eder.
  4.  Gelen ürün barkodları okutulur.
  5.  Ürün adetleri sayılır.
  6.  Üretim LOT numarası kaydedilir.
  7.  SKT bilgisi girilir.
  8.  Hasarlı veya eksik ürünler ayrıştırılır.
  9.  Ürün kabul onayı verilir.
  10. Sistem otomatik olarak stok girişini gerçekleştirir.
  11. Ürünlere raf veya palet lokasyonu atanır.
Ek özellik: Sipariş edilen miktar ile teslim alınan miktar farklıysa sistem uyarı vermeli, fark için tutanak veya eksik/fazla teslim kaydı oluşturmalıdır.
3.4. LOT ve SKT takibi
Kozmetik ürünlerde bu modül çok önemlidir.
Her ürün için aşağıdaki bilgiler saklanmalıdır:

  *   Üretim tarihi.
  *   Son kullanma tarihi.
  *   LOT / parti numarası.
  *   Tedarikçi veya üretici.
  *   Üretim yeri.
  *   Depoya giriş tarihi.
  *   Depoda bulunduğu lokasyon.
  *   Parti bazında giriş ve çıkış miktarı.
Sistem FEFO (son kullanma tarihi en yakın olan önce çıkar) mantığıyla ürün toplama önceliği vermelidir.
Örnek uyarı mekanizması:
Kalan raf ömrü
Sistem uyarısı
180 gün
Bilgilendirme
120 gün
Yaklaşan SKT uyarısı
90 gün
Kritik stok uyarısı
30 gün
Yönetici onayı
SKT geçmiş
Satış ve sevkiyat blokajı
Bu süreler yönetici tarafından değiştirilebilir olmalıdır.
3.5. Stok transfer işlemleri

  *   Depolar arası transfer.
  *   Raflar arası transfer.
  *   Paletler arası transfer.
  *   Ürün toplama alanına transfer.
  *   İade alanına transfer.
  *   Karantina alanına transfer.
Her transfer için kaynak lokasyon, hedef lokasyon, ürün, miktar, işlem yapan personel ve tarih kayıt altına alınmalıdır.
3.6. Sayım yönetimi
Sistem üç farklı sayım yöntemini desteklemelidir:

  1.  Genel depo sayımı.
  2.  Raf bazlı sayım.
  3.  Ürün bazlı dönemsel sayım.
Sayım işlemi el terminali veya barkod okuyucu ile yapılabilmeli.
Sayım sonucu sistem stoğu ile fiziksel stok karşılaştırılmalı; eksik ve fazla stoklar gösterilmeli, farklar yönetici onayından sonra düzeltilmelidir.
3.7. Palet ve koli yönetimi
Palet bazlı çalışma mutlaka bulunmalı.

  *   Palet barkodu oluşturma.
  *   Palete ürün ekleme.
  *   Paletten ürün çıkarma.
  *   Palet transferi.
  *   Palet lokasyonu.
  *   Palet içindeki ürün ve miktar listesi.
  *   Palet doluluk oranı.
  *   Palet geçmişi.
  *   Palet bazında sevkiyat.
Örneğin 80 × 120 cm paletlerin bulunduğu depoda palet adedi, yerleşim kapasitesi ve kullanılabilir alan takip edilebilmelidir. Ancak gerçek kapasite hesaplamasında raf yüksekliği, koridorlar, istifleme güvenliği ve yangın yolları da dikkate alınmalıdır.
4. Stok yönetimi
Stok modülü tüm satış ve depo hareketlerinin merkezinde olmalıdır.
4.1. Stok hareket türleri
Sistemde aşağıdaki stok hareketleri ayrı ayrı tanımlanmalıdır:
İşlem
Stok etkisi
Satın alma girişi
Stok artar
Üretimden giriş
Stok artar
Satış siparişi
Stok rezerve edilir
Sevkiyat
Stok azalır
Müşteri iadesi
Kontrol sonrası stok artar
Tedarikçi iadesi
Stok azalır
Depolar arası transfer
Toplam stok değişmez
Fire / hasar
Stok azalır
Numune çıkışı
Stok azalır
Promosyon çıkışı
Stok azalır
Sayım farkı
Onay sonrası düzeltilir
4.2. Stok durumları
Her ürün için stok aşağıdaki şekilde gösterilmelidir:

  *   Toplam fiziksel stok.
  *   Satışa uygun stok.
  *   Rezerve edilmiş stok.
  *   Siparişe ayrılmış stok.
  *   Sevkiyat bekleyen stok.
  *   İade kontrolündeki stok.
  *   Hasarlı stok.
  *   Karantinadaki stok.
  *   Yoldaki stok.
  *   Satın alma siparişi verilmiş stok.
Örneğin:
Örnek ürün stok ekranı
1.250 adet
Toplam fiziksel stok
Satışa uygun
850
Rezerve
250
Hasarlı / Karantina
100
İade kontrolünde
50
Net satışa uygun stok: 850 adet
4.3. Otomatik stok uyarıları

  *   Minimum stok seviyesinin altına düşme.
  *   Kritik stok seviyesine ulaşma.
  *   Aşırı stok oluşması.
  *   Hareketsiz stok.
  *   SKT yaklaşması.
  *   LOT bazlı stok uyarısı.
  *   Sipariş karşılayamayacak stok durumu.
  *   Depolar arası stok dengesizliği.
4.4. Otomatik satın alma önerisi
Sistem geçmiş satışları ve mevcut stokları dikkate alarak satın alma önerisi oluşturmalıdır.
Örnek:

  *   Günlük ortalama satış: 20 adet.
  *   Tedarik süresi: 15 gün.
  *   Güvenlik stoğu: 100 adet.
  *   Mevcut kullanılabilir stok: 250 adet.
Önerilen ihtiyaç:
\[ (20 \times 15)+100-250=150 \]
Sistem 150 adetlik satın alma önerisi oluşturabilir. Bu öneri otomatik siparişe dönüşmemeli, yetkili onayıyla satın alma siparişine çevrilmelidir.
5. Satın alma ve tedarikçi yönetimi
Yazılımın satın alma modülü de bulunmalıdır. Üreticiden veya tedarikçiden alınan ürünlerin tüm süreci takip edilmelidir.
5.1. Tedarikçi kartı
Her tedarikçi için:

  *   Firma unvanı.
  *   Vergi numarası ve vergi dairesi.
  *   Yetkili kişi.
  *   Telefon ve e-posta.
  *   Adres.
  *   IBAN.
  *   Ödeme vadesi.
  *   Çalışılan ürünler.
  *   Son alış fiyatları.
  *   Teslimat süresi.
  *   Minimum sipariş miktarı.
  *   Sevkiyat koşulları.
  *   Açık siparişler.
  *   Borç bakiyesi.
5.2. Satın alma süreci

  1.  Satın alma talebi
Depo veya satış departmanı ürün ihtiyacını bildirir.

  1.  Teklif toplama
Tedarikçilerden fiyat, termin ve sevkiyat teklifi alınır.

  1.  Teklif karşılaştırma
Fiyat, ödeme vadesi ve teslim süresi değerlendirilir.

  1.  Yönetici onayı
Satın alma talebi onaylanır.

  1.  Satın alma siparişi
Tedarikçiye resmi sipariş iletilir.

  1.  Mal kabul
Gelen ürünler kontrol edilerek sisteme alınır.

  1.  Fatura eşleştirme
Sipariş, irsaliye ve tedarikçi faturası karşılaştırılır.

  1.  Ödeme ve muhasebe
Borç kaydı oluşturulur ve ödeme planına alınır.
5.3. Satın alma raporları

  *   Tedarikçi bazında alış tutarları.
  *   Ürün bazında son alış fiyatı.
  *   Ortalama alış maliyeti.
  *   Fiyat değişim geçmişi.
  *   Açık satın alma siparişleri.
  *   Termin gecikmeleri.
  *   Tedarikçi performansı.
  *   Vadesi gelen tedarikçi borçları.
6. Sipariş yönetimi
Bu modül şirketin bütün satış kanallarından gelen siparişleri tek merkezde toplamalıdır.
Merkezi sipariş havuzu
6.1. Sipariş kaynakları
Yazılım aşağıdaki kanallardan sipariş alabilmelidir:

  1.  Trendyol.
  2.  Hepsiburada.
  3.  Şirket web sitesi.
  4.  B2B bayi portalı.
  5.  Telefon siparişleri.
  6.  E-posta siparişleri.
  7.  WhatsApp üzerinden alınan siparişler.
  8.  Kurumsal şirket siparişleri.
  9.  Distribütör ve toptancı siparişleri.
  10. Mağaza veya fiziksel satış noktaları.
Her siparişin hangi kanaldan geldiği sistemde kayıtlı olmalıdır.
6.2. Sipariş kartında bulunması gereken bilgiler
Alan
Açıklama
Sipariş numarası
Otomatik numara
Sipariş tarihi
Sipariş oluşturulma zamanı
Satış kanalı
Trendyol, bayi vb.
Müşteri
Cari kart
Ürün kodu
SKU
Barkod
Ürün barkodu
Ürün miktarı
Sipariş adedi
Birim fiyat
Satış fiyatı
İndirim
Kampanya indirimi
KDV
Vergi bilgisi
Kargo bedeli
Varsa
Genel toplam
Sipariş toplamı
Ödeme şekli
Kart, havale vb.
Teslimat adresi
Sevk adresi
Fatura adresi
Fatura bilgisi
Sipariş durumu
Operasyon aşaması
6.3. Sipariş durumları
Sistem siparişleri aşağıdaki aşamalarda takip etmelidir:

  *   Yeni sipariş.
  *   Ödeme bekliyor.
  *   Ödeme onaylandı.
  *   Stok kontrolü.
  *   Stok rezerve edildi.
  *   Depo hazırlığı bekliyor.
  *   Toplama başladı.
  *   Toplama tamamlandı.
  *   Paketleme yapılıyor.
  *   Fatura oluşturuldu.
  *   Sevkiyata hazır.
  *   Kargoya teslim edildi.
  *   Teslim edildi.
  *   İptal edildi.
  *   İade talebi açıldı.
  *   İade tamamlandı.
Her siparişin hangi aşamada beklediği ve ne kadar süredir o aşamada olduğu görüntülenmelidir.
6.4. Siparişin otomatik işlenmesi
Örnek Trendyol sipariş akışı:

  1.  Trendyol'dan sipariş sisteme gelir.
  2.  Ürün SKU ve barkod eşleştirmesi yapılır.
  3.  Müşteri ve teslimat bilgileri alınır.
  4.  Stok kontrolü yapılır.
  5.  Stok varsa ürün rezerve edilir.
  6.  Depo için toplama emri açılır.
  7.  Personel ürünleri raflardan toplar.
  8.  Barkodla ürün doğrulaması yapılır.
  9.  Paketleme gerçekleştirilir.
  10. Kargo etiketi oluşturulur.
  11. E-fatura / e-arşiv süreci işletilir.
  12. Kargo firması teslim alır.
  13. Kargo takip numarası siparişe eklenir.
  14. Sipariş durumu pazaryerine aktarılır.
  15. Teslimat ve iade durumu takip edilir.
Kritik özellik: Aynı siparişin iki defa sisteme alınmasını engelleyen sipariş numarası kontrolü olmalıdır. Aynı anda farklı kanallardan sipariş geldiğinde stokların yanlışlıkla fazla satılmasını önlemek için stok rezervasyonu anlık çalışmalıdır.
6.5. Fiyat ve kampanya yönetimi
Her satış kanalı için ayrı fiyat tanımlanabilmelidir.
Örneğin:
Kanal
Satış fiyatı
Web sitesi
299 TL
Trendyol
329 TL
Hepsiburada
319 TL
Bayi
190 TL
Kurumsal müşteri
210 TL
Bunlar örnek fiyatlardır.
Sistem şu kampanyaları desteklemelidir:

  *   İkinci ürün 1 TL.
  *   Bir alana bir bedava.
  *   3 al 2 öde.
  *   Sepette yüzde indirim.
  *   Belirli tutar üzerinde ücretsiz kargo.
  *   Ürün seti kampanyası.
  *   Kupon tanımlama.
  *   Bayiye özel fiyat.
  *   Müşteriye özel indirim.
  *   Dönemsel kampanya.
Kampanyaların başlangıç ve bitiş tarihi, kullanım adedi, maksimum indirim tutarı ve hangi kanalda geçerli olduğu tanımlanmalıdır.
7. Sevkiyat ve lojistik yönetimi
Bu modül siparişin depodan çıkıp müşteriye ulaşmasına kadar olan süreci yönetmelidir.
7.1. Sevkiyat hazırlama

  *   Siparişler sevkiyat havuzuna düşer.
  *   Sevkiyat önceliği belirlenir.
  *   Aynı bölgeye giden siparişler gruplandırılabilir.
  *   Siparişler toplama listesine dönüştürülür.
  *   Depo personeline görev atanır.
  *   Ürün barkodları okutularak kontrol edilir.
  *   Paketleme ve koli sayımı yapılır.
  *   Kargo etiketi veya sevk irsaliyesi hazırlanır.
  *   Sevkiyat onayı verilir.
7.2. Toplama yöntemleri
Sistem farklı sipariş hacimlerine uygun yöntemler desteklemelidir:
Yöntem
Kullanım
Tekli toplama
Tek sipariş
Çoklu toplama
Birden fazla sipariş
Dalga toplama
Belirli saat aralığındaki siparişler
Bölge bazlı toplama
Depo alanlarına göre
Palet toplama
Toptan ve kurumsal sipariş
7.3. Kargo entegrasyonları
Yazılım birden fazla kargo firmasıyla çalışabilmelidir.

  *   Yurtiçi Kargo.
  *   Aras Kargo.
  *   MNG Kargo.
  *   Sürat Kargo.
  *   PTT Kargo.
  *   Hepsijet.
  *   Trendyol Express.
  *   Diğer anlaşmalı lojistik firmaları.
Kargo entegrasyonunda şu özellikler bulunmalıdır:

  *   Otomatik kargo etiketi.
  *   Barkodlu gönderi.
  *   Kargo takip numarası.
  *   Kargo ücreti.
  *   Kargo teslim durumu.
  *   Teslim edilemeyen siparişler.
  *   İade kargo takibi.
  *   Kargo firması performansı.
  *   Kargo faturası kontrolü.
7.4. B2B ve kurumsal sevkiyat
Bayi ve büyük müşteriler için farklı sevkiyat modeli olmalıdır.

  *   Sipariş bazlı koli hazırlama.
  *   Palet bazlı sevkiyat.
  *   Araç yükleme listesi.
  *   İrsaliye oluşturma.
  *   Plaka ve şoför kaydı.
  *   Sevk adresi.
  *   Teslimat randevusu.
  *   Teslim alan kişi.
  *   Teslimat tutanağı.
  *   Eksik ve hasarlı teslimat kaydı.
Özellikle 3 L deterjan, yumuşatıcı ve benzeri ağır ürünlerde koli ve palet bazında ağırlık kontrolü yapılabilmesi gerekir.
7.5. İade ve tersine lojistik
İade süreci bağımsız bir modül olarak bulunmalıdır.

  1.  Müşteri iade talebi oluşturur.
  2.  İade nedeni seçilir.
  3.  İade kargo kodu oluşturulur.
  4.  Ürün depoya gelir.
  5.  Barkod ve sipariş numarası kontrol edilir.
  6.  Ürün kalite kontrolünden geçirilir.
  7.  Satılabilir, hasarlı veya karantinalı olarak sınıflandırılır.
  8.  Uygun ürün yeniden stoğa alınır.
  9.  İade faturası veya diğer gerekli mali belge süreçleri yürütülür.
  10. Müşteri iade ve para iadesi süreci tamamlanır.
Kozmetik ürünlerde açılmış, kullanılmış veya hijyen güvenliği açısından yeniden satışa uygun olmayan ürünlerin otomatik olarak satış stoklarına alınması engellenmelidir.
8. CRM – Müşteri ve bayi ilişkileri yönetimi
CRM modülü sadece müşteri telefonlarını kaydeden bir ekran olmamalı. Satış ekibinin müşteriyi tanıdığı, geçmiş alışverişlerini takip ettiği, teklif hazırladığı ve yeni satış fırsatlarını yönettiği bir sistem olmalıdır.
8.1. Müşteri grupları
Müşteriler aşağıdaki gruplara ayrılmalıdır:

  *   Bireysel müşteriler.
  *   E-ticaret müşterileri.
  *   Eczaneler.
  *   Kozmetik mağazaları.
  *   Marketler.
  *   Temizlik ürünleri satıcıları.
  *   Toptancılar.
  *   Distribütörler.
  *   Bayiler.
  *   Kurumsal şirketler.
  *   Oteller ve işletmeler.
  *   Fabrikalar ve sanayi kuruluşları.
8.2. Müşteri kartı
Her müşteri için:
Bilgi
Açıklama
Cari kod
Benzersiz müşteri kodu
Firma adı
Ticari unvan
Yetkili kişi
İlgili kişi
Telefon
İletişim
E-posta
E-posta adresi
Vergi bilgileri
Vergi dairesi / numarası
Adres
Merkez ve teslimat adresleri
Müşteri grubu
Bayi, toptancı vb.
Satış temsilcisi
Sorumlu personel
Ödeme vadesi
30, 45, 60 gün vb.
Kredi limiti
Tanımlı risk limiti
Cari bakiye
Borç/alacak
Satış geçmişi
Önceki siparişler
İade geçmişi
İade kayıtları
Özel fiyat
Müşteriye özel fiyat listesi
8.3. CRM satış fırsatları
Satış ekibi potansiyel müşterileri aşamalı olarak takip edebilmelidir.
Örnek satış fırsatı akışı

  1.  Potansiyel müşteri
Yeni bayi veya kurumsal müşteri sisteme kaydedilir.

  1.  İlk iletişim
Telefon, e-posta veya ziyaret kaydı oluşturulur.

  1.  İhtiyaç analizi
Ürün grubu, aylık tüketim ve satın alma ihtiyacı belirlenir.

  1.  Teklif gönderildi
Ürün, miktar, fiyat ve ödeme koşulları iletilir.

  1.  Pazarlık / takip
Görüşme ve revizyonlar kaydedilir.

  1.  Sipariş alındı
Fırsat satış siparişine dönüştürülür.

  1.  Müşteri kazanıldı
Satış performansı ve müşteri devamlılığı takip edilir.
8.4. Müşteri aktivite takibi

  *   Telefon görüşmeleri.
  *   E-posta yazışmaları.
  *   WhatsApp görüşme notları.
  *   Firma ziyaretleri.
  *   Toplantı kayıtları.
  *   Teklif gönderimleri.
  *   Numune gönderimleri.
  *   Hatırlatmalar.
  *   Bir sonraki görüşme tarihi.
  *   Satış temsilcisi notları.
Sistem satış temsilcisine otomatik hatırlatma göndermelidir.
Örneğin: Bir bayiye teklif gönderildikten 3 gün sonra dönüş alınmadıysa satış temsilcisine takip görevi oluşturulmalıdır.
8.5. Müşteri segmentasyonu ve pazarlama
Müşteriler alışveriş sıklığı, toplam cirosu, ürün tercihi ve son alışveriş tarihine göre sınıflandırılabilmelidir.

  *   VIP müşteriler.
  *   Düzenli müşteriler.
  *   Yeni müşteriler.
  *   Uzun süredir alışveriş yapmayan müşteriler.
  *   Yüksek cirolu bayiler.
  *   Potansiyel bayiler.
  *   Kampanya müşterileri.
Ayrıca SMS, e-posta ve izinli pazarlama iletişimleri için entegrasyon bulunmalı; KVKK ve ticari elektronik ileti izinleri takip edilmelidir.
8.6. Bayi portalı
Bence sistemin önemli özelliklerinden biri de bayilerin kendilerine ait kullanıcı adı ve şifre ile giriş yapabilecekleri bir bayi portalıdır.
Bayi portalında:

  *   Güncel ürün kataloğu.
  *   Bayiye özel alış fiyatları.
  *   Ürün görselleri.
  *   Ürün açıklamaları.
  *   Stok durumu.
  *   Minimum sipariş miktarı.
  *   Online sipariş oluşturma.
  *   Önceki siparişler.
  *   Fatura ve irsaliye görüntüleme.
  *   Cari hesap ekstresi.
  *   Ödeme ve borç bilgileri.
  *   Kampanyalar.
  *   Sipariş takip.
Böylece bayiler telefonla sipariş vermek zorunda kalmadan kendi siparişlerini oluşturabilirler.
9. Muhasebe ve finans yönetimi
ERP entegrasyonu
Muhasebe modülü satış, satın alma, stok ve finans süreçleriyle bağlantılı çalışmalıdır. Amaç aynı verilerin farklı programlara tekrar tekrar girilmesini önlemektir.
9.1. Cari hesap yönetimi
Hem müşteri hem tedarikçi cari hesapları yönetilmelidir.
Müşteri cari hesabında:

  *   Açılış bakiyesi.
  *   Satış faturaları.
  *   Tahsilatlar.
  *   İadeler.
  *   İskontolar.
  *   Vade tarihleri.
  *   Kredi limiti.
  *   Borç ve alacak bakiyesi.
  *   Cari ekstre.
Tedarikçi cari hesabında:

  *   Alış faturaları.
  *   Ödemeler.
  *   Avanslar.
  *   İade faturaları.
  *   Vade tarihleri.
  *   Borç bakiyesi.
  *   Cari ekstre.
9.2. E-fatura ve e-arşiv süreçleri
Yazılım, yetkili bir e-belge entegratörü üzerinden aşağıdaki işlemleri desteklemelidir:

  *   E-fatura oluşturma.
  *   E-arşiv fatura oluşturma.
  *   E-fatura gelen kutusu.
  *   Gelen faturaları görüntüleme.
  *   Fatura reddetme / itiraz süreçleri.
  *   Fatura iptal ve düzeltme süreçleri.
  *   E-irsaliye oluşturma.
  *   E-irsaliye gelen belgeler.
  *   İrsaliye-fatura eşleştirmesi.
  *   Fatura PDF ve XML arşivi.
Belge türü, işlem tarihi ve müşterinin e-belge mükellefiyet durumuna göre doğru belge seçilmelidir.
9.3. Satışın muhasebeleştirilmesi
Örnek satış akışı:

  1.  Sipariş oluşur
Satış kanalı ve sipariş tutarı sisteme kaydedilir.

  1.  Satış faturası oluşturulur
Fatura ilgili müşteri veya mevzuata uygun alıcı bilgileri üzerinden düzenlenir.

  1.  Cari hesap kaydı oluşur
Vadeli satışta alacak, peşin satışta ilgili tahsilat kaydı takip edilir.

  1.  Stok çıkışı gerçekleşir
Ürün maliyeti stoktan düşülür.

  1.  Maliyet ve kârlılık hesaplanır
Satış fiyatı, maliyet, iskonto ve kanal giderleri analiz edilir.

  1.  Tahsilat takip edilir
Banka, kredi kartı veya pazaryeri ödeme kaydı eşleştirilir.
Muhasebe fişlerinin oluşturulması, kullanılan muhasebe yazılımına ve şirketin muhasebe politikalarına göre yapılandırılmalıdır.
9.4. Alış faturası ve satın alma muhasebesi
Tedarikçi faturası geldiğinde:

  1.  Satın alma siparişi ile eşleştirilir.
  2.  Depo mal kabul miktarı kontrol edilir.
  3.  Fatura miktarı ve fiyatı karşılaştırılır.
  4.  KDV kontrolü yapılır.
  5.  Alış faturası kaydedilir.
  6.  Tedarikçi cari hesabına borç kaydedilir.
  7.  Vade ve ödeme planı oluşturulur.
  8.  Ürün maliyetleri güncellenir.
Özellikle faturadaki miktar ile depoya giren miktar uyuşmuyorsa sistem onay vermeden işlemi tamamlamamalıdır.
9.5. Banka ve kasa yönetimi

  *   Banka hesapları.
  *   Kasa hareketleri.
  *   Havale / EFT.
  *   Kredi kartı tahsilatları.
  *   POS tahsilatları.
  *   Pazaryeri ödemeleri.
  *   Banka masrafları.
  *   POS komisyonları.
  *   Banka mutabakatı.
  *   Kredi ve finansman ödemeleri.
9.6. Pazaryeri muhasebeleştirme
Bu bölüm özellikle Trendyol ve Hepsiburada satışları için önemlidir.
Sistem her pazaryerinden gelen hakediş ve ödeme hareketlerini siparişlerle eşleştirebilmelidir.
Örnek:
İşlem
Tutar
Ürün satış tutarı
100.000 TL
Pazaryeri komisyonu
-15.000 TL
Kargo gideri
-3.000 TL
Hizmet / diğer kesintiler
-2.000 TL
Net hakediş
80.000 TL
Bu yalnızca örnek bir hesaplamadır.
Sistem şu işlemleri otomatik takip etmelidir:

  *   Sipariş bazında satış tutarı.
  *   Pazaryeri komisyonu.
  *   Kargo kesintisi.
  *   Reklam giderleri.
  *   Kampanya katkı payları.
  *   İade ve iptal kesintileri.
  *   Hizmet bedelleri.
  *   Hakediş tutarı.
  *   Bankaya yatan tutar.
  *   Ödeme farkları.
En önemli özellik: Pazaryeri raporları ile banka hesabına gelen tutar otomatik karşılaştırılmalı, eksik veya fazla ödeme varsa fark raporu oluşturulmalıdır.
9.7. Gelir-gider ve nakit akışı

  *   Günlük gelir.
  *   Günlük gider.
  *   Haftalık nakit akışı.
  *   Aylık nakit akışı.
  *   Beklenen tahsilatlar.
  *   Vadesi gelen borçlar.
  *   Vadesi geçmiş alacaklar.
  *   Personel giderleri.
  *   Kira ve depo giderleri.
  *   Nakliye giderleri.
  *   Reklam giderleri.
  *   Pazaryeri komisyonları.
  *   Üretim ve tedarik maliyetleri.
9.8. Ürün bazında gerçek kârlılık
Bence yönetim ekranının en önemli raporlarından biri budur.
Bir ürünün satış fiyatından yalnızca alış maliyetini çıkarmak gerçek kârlılığı göstermez.
Sistem aşağıdaki maliyetleri hesaplayabilmelidir:

  *   Ürün alış / üretim maliyeti.
  *   Ambalaj ve etiket maliyeti.
  *   Nakliye maliyeti.
  *   Depolama maliyeti.
  *   Pazaryeri komisyonu.
  *   Kargo gideri.
  *   Reklam maliyeti.
  *   İskonto.
  *   İade maliyeti.
  *   POS komisyonu.
Örnek kârlılık ekranı:
Açıklama
Tutar
KDV hariç satış geliri
250 TL
Ürün maliyeti
-100 TL
Ambalaj
-10 TL
Pazaryeri komisyonu
-30 TL
Kargo gideri
-20 TL
Reklam gideri
-15 TL
Diğer değişken giderler
-5 TL
Katkı kârı
70 TL
Buradaki örnek, KDV hariç tutarlar üzerinden oluşturulmuştur. Sabit genel giderler de dağıtıldığında ürünün tam maliyet ve net kârlılık raporu elde edilmelidir.
10. Üretim ve fason üretim yönetimi
Deterjan ve kozmetik firması açısından bu modül de oldukça önemlidir. Üretimi kendi tesisinizde veya fason üreticilerde yaptırmanız durumunda kullanılmalıdır.
10.1. Üretim planlama

  *   Ürün reçeteleri.
  *   Hammadde listesi.
  *   Ambalaj ve şişe listesi.
  *   Etiket ve koli ihtiyacı.
  *   Üretim miktarı.
  *   Üretim tarihi.
  *   Üretim partisi.
  *   Üretim maliyeti.
  *   Üretim fireleri.
10.2. Reçete yönetimi (BOM)
Örneğin 1.000 adet sıvı sabun üretimi için:
Girdi
İhtiyaç
Sıvı sabun ana karışımı
Reçeteye göre
Şişe
1.000 adet
Kapak
1.000 adet
Etiket
1.000 adet
Koli
Koli kapasitesine göre
Ambalaj malzemesi
Planlanan miktar
Sistem üretim öncesi eksik hammaddeleri göstermelidir.
10.3. Fason üretici takibi

  *   Üretici firma kartı.
  *   Üretim siparişi.
  *   Üreticiye gönderilen ambalajlar.
  *   Üreticiye gönderilen hammaddeler.
  *   Üretim miktarı.
  *   Üretim kayıpları.
  *   Gelen mamul miktarı.
  *   Üretim partisi.
  *   Kalite kontrol belgeleri.
  *   Üretim maliyeti.
  *   Üretim faturası.
10.4. Kalite kontrol
Kozmetik ve deterjan ürünleri için ürün bazlı kalite kontrol formları olmalıdır.
Örneğin:

  *   Ambalaj kontrolü.
  *   Kapak sızdırmazlık kontrolü.
  *   Etiket kontrolü.
  *   Görsel kontrol.
  *   Ağırlık / hacim kontrolü.
  *   Parti numarası kontrolü.
  *   Gerekli ürünlerde pH kontrolü.
  *   Gerekli analiz ve sertifika kayıtları.
Uygunsuz ürünler otomatik olarak karantina stoklarına alınmalıdır.
11. Yönetim paneli ve raporlama
Şirket sahibi veya yöneticisi sisteme giriş yaptığında bütün şirketin durumunu tek ekranda görebilmelidir.
11.1. Ana gösterge paneli
Yönetim Dashboard
Örnek ekran
Günlük satış
185.400 TL
Yeni sipariş
126
Toplam stok değeri
2,4 Mn TL
Sevkiyat bekleyen
34
Satış kanallarına göre dağılım
Tamamen örnek verilerle oluşturulmuştur.
B2B / Bayi
Hepsiburada
Trendyol
Amazon
Web sitesi
Operasyonel uyarılar

  *   12 ürün kritik stok seviyesinde.
  *   8 sipariş sevkiyat bekliyor.
  *   5 müşteri ödemesi gecikmiş.
  *   3 ürünün SKT kontrolü gerekiyor.
Yukarıdaki rakamlar ve dağılımlar yalnızca örnek gösterimdir.
11.2. Yönetim raporları
Rapor
Sağladığı bilgi
Günlük satış raporu
Günlük ciro ve adet
Aylık satış raporu
Aylık performans
Kanal bazlı satış
Trendyol, HB, B2B vb.
Ürün bazlı satış
En çok satan ürünler
Kârlılık raporu
Ürün ve kanal kârı
Stok raporu
Depodaki mevcut stok
Stok yaşlandırma
Ne kadar süredir depoda
SKT raporu
Tarihi yaklaşan ürünler
Sipariş raporu
Siparişlerin durumu
Sevkiyat raporu
Hazırlanan ve teslim edilen
İade raporu
İade oranları ve nedenleri
Cari raporu
Müşteri borç ve alacakları
Tahsilat raporu
Beklenen ve gerçekleşen
Tedarikçi raporu
Alış ve performans
Personel raporu
Kullanıcı işlem performansı
12. Kullanıcı, yetki ve onay yönetimi
Herkesin her işlemi yapabildiği bir yazılım kesinlikle tercih edilmemelidir.
Kullanıcı
Yetki
Şirket yöneticisi
Tüm modüller
Depo müdürü
Depo ve stok yönetimi
Depo personeli
Mal kabul, toplama, sayım
Satın alma
Tedarikçi ve sipariş
Satış ekibi
CRM, teklif, satış siparişi
E-ticaret ekibi
Pazaryeri ve web siparişleri
Finans
Cari, tahsilat, ödeme
Muhasebe
Fatura ve muhasebe kayıtları
Sevkiyat personeli
Paketleme ve sevkiyat
Raporlama kullanıcısı
Sadece görüntüleme
Özellikle aşağıdaki işlemler yönetici onayı gerektirmelidir:

  *   Stok düzeltme.
  *   Stok silme.
  *   Fiyat değişikliği.
  *   İskonto tanımlama.
  *   Sipariş iptali.
  *   İade onayı.
  *   Cari limit artırma.
  *   Vadeli satış onayı.
  *   Alış ve satış faturası iptali.
  *   Fire ve hasar kaydı.
Sistem her işlemin kim tarafından, hangi tarihte, hangi saatte yapıldığını kayıt altında tutmalıdır.
13. Entegrasyonlar ve otomatik veri aktarımı
Yazılımın farklı programlarla haberleşebilmesi gerekiyor.
Entegrasyon
İstenen özellik
Trendyol
Sipariş, stok, fiyat, fatura, iade
Hepsiburada
Sipariş, stok, fiyat, fatura, iade
Web sitesi
Sipariş, müşteri, stok, ödeme
Kargo firmaları
Etiket, takip, teslimat
E-fatura entegratörü
E-fatura, e-arşiv, e-irsaliye
Muhasebe programı
Cari, fatura, fiş, tahsilat
Bankalar
Hesap hareketleri, mutabakat
POS sistemleri
Tahsilat ve komisyon
SMS / e-posta
Bildirim ve müşteri iletişimi
WhatsApp Business
Müşteri iletişimi
Barkod cihazları
Depo işlemleri
E-ticaret altyapısı
Ürün ve sipariş aktarımı
Teknik olarak mutlaka istenmesi gerekenler:

  *   API desteği.
  *   Otomatik veri senkronizasyonu.
  *   Hata kayıt ekranı.
  *   Başarısız entegrasyon işlemlerini yeniden çalıştırma.
  *   Sipariş ve stok senkronizasyon logları.
  *   Mükerrer kayıt engelleme.
  *   Yetkilendirilmiş API erişimi.
  *   Veri yedekleme.
  *   Mobil uyumlu kullanım.
14. Mobil depo uygulaması ve el terminali
Depo personelinin bilgisayar başında işlem yapmak zorunda kalmaması gerekir.
Mobil uygulama veya Android el terminali üzerinden aşağıdaki işlemler yapılabilmelidir:

  1.  Ürün barkodu okutma.
  2.  Mal kabul.
  3.  Raf yerleştirme.
  4.  Stok sorgulama.
  5.  Palet oluşturma.
  6.  Palet transferi.
  7.  Sipariş toplama.
  8.  Paketleme kontrolü.
  9.  Sevkiyat onayı.
  10. İade kabulü.
  11. Sayım.
  12. Hasarlı ürün kaydı.
Örneğin personel el terminalinden bir ürün barkodunu okuttuğunda ürünün hangi lokasyonda bulunduğunu, kaç adet olduğunu, hangi LOT'a ait olduğunu ve SKT'sini görebilmelidir.
15. Otomatik bildirim ve uyarı sistemi
Sistem yalnızca veri göstermemeli, gerekli durumlarda ilgili kişileri uyarmalıdır.
Olay
Bildirim alacak kişi
Kritik stok
Depo müdürü / satın alma
Yeni sipariş
E-ticaret ekibi
Sevkiyat gecikmesi
Lojistik sorumlusu
SKT yaklaşması
Depo müdürü
Sipariş iptali
Satış ekibi
Müşteri borcu gecikmesi
Finans
Tedarikçi termin gecikmesi
Satın alma
Pazaryeri ödeme farkı
Finans
Sayım farkı
Depo müdürü
Kârlılık düşüşü
Yönetici
Bildirimler sistem içinden, e-posta veya uygun entegrasyon üzerinden gönderilebilmelidir.
16. Yazılımda bulunması gereken ek özellikler
Bunlar ilk bakışta temel modüller kadar önemli görünmeyebilir ancak işletme büyüdükçe ciddi fayda sağlar.

  *   Çoklu şirket yönetimi.
  *   Çoklu depo yönetimi.
  *   Çoklu kullanıcı.
  *   Çoklu para birimi.
  *   Dövizli alış ve satış.
  *   Farklı fiyat listeleri.
  *   Müşteriye özel fiyatlandırma.
  *   Otomatik iskonto.
  *   Kredi limiti kontrolü.
  *   Satış temsilcisi prim hesaplama.
  *   Depo personeli performans takibi.
  *   Ürün hareket geçmişi.
  *   Evrak ve belge arşivi.
  *   Excel içe ve dışa aktarma.
  *   Toplu ürün açılışı.
  *   Toplu fiyat güncelleme.
  *   Toplu stok güncelleme.
  *   QR kod desteği.
  *   Barkod etiket basımı.
  *   Kullanıcı işlem geçmişi.
  *   Otomatik yedekleme.
  *   Yetkilendirme ve veri güvenliği.
17. Baştan sona tüm işletme süreçlerinin birbirine bağlanması
Yazılım firmasına özellikle aşağıdaki bütünleşik iş akışını anlatmanızı öneriyorum.
Şirketin uçtan uca operasyon akışı

  1.  SATIN ALMA
İhtiyaç belirleme → Teklif → Onay → Tedarikçi siparişi

  1.  ÜRÜN KABUL
İrsaliye → Sayım → Barkod → LOT / SKT → Mal kabul

  1.  DEPO
Palet → Raf → Lokasyon → Stok → Sayım

  1.  SATIŞ
Müşteri → Teklif → Sipariş → Fiyat / kampanya → Ödeme kontrolü

  1.  SİPARİŞ HAZIRLAMA
Stok rezervasyonu → Toplama → Barkod kontrolü → Paketleme

  1.  SEVKİYAT
İrsaliye → Kargo / araç → Teslimat → Takip

  1.  FİNANS VE MUHASEBE
Fatura → Cari hesap → Tahsilat → Banka → Muhasebe

  1.  CRM VE SATIŞ SONRASI
Müşteri memnuniyeti → İade → Tekrar sipariş → Kampanya

  1.  YÖNETİM RAPORLAMA
Ciro → Maliyet → Kârlılık → Nakit akışı → Performans
18. Yazılım firmasıyla paylaşılması gereken teknik ve operasyonel şartlar
Yazılımı yaptırırken yalnızca özellik listesi istemeyin. Aşağıdaki kriterleri de sözleşme ve proje kapsamına dahil edin.
Konu
Talep edilmesi gereken özellik
Kullanım
Web tabanlı ve mobil uyumlu
Depo
Barkod ve el terminali
Veritabanı
Merkezi ve güvenli
Entegrasyon
API altyapısı
Kullanıcı
Rol bazlı yetkilendirme
Log
Tüm işlemlerin kayıt altında olması
Yedekleme
Otomatik ve düzenli
Raporlama
Excel ve PDF
Hız
Çoklu sipariş işlem kapasitesi
Güvenlik
Kullanıcı ve veri erişim kontrolleri
Destek
Teknik destek ve SLA
Eğitim
Personel ve yönetici eğitimi
Test
Canlıya geçiş öncesi test ortamı
Güncelleme
Sistem ve entegrasyon bakımı
Ayrıca yazılım firmasından şu sorulara yazılı cevap alın:

  *   Yazılımın kaynak kodu ve veritabanı kimin kontrolünde olacak?
  *   Veri dışa aktarımı mümkün mü?
  *   Kullanıcı sayısına göre ek ücret var mı?
  *   Depo ve sipariş hacmine göre performans sınırı var mı?
  *   API kullanımı ücretli mi?
  *   Yeni pazaryeri entegrasyonu ne kadar sürede yapılabiliyor?
  *   Hatalı stok veya sipariş hareketleri nasıl geri alınabiliyor?
  *   Sistem kesintisinde siparişler nasıl korunuyor?
  *   Teknik destek hangi saatlerde sağlanıyor?
19. Yazılımın devreye alınma aşamaları
Bütün modülleri aynı anda devreye almak yerine aşamalı ilerlemek daha sağlıklı olacaktır.
Aşama
Kapsam
Öncelik
1
Ürün kartları ve depo tanımları
Çok yüksek
2
Stok, LOT, SKT ve barkod
Çok yüksek
3
Sipariş ve pazaryeri entegrasyonları
Çok yüksek
4
Toplama, paketleme ve sevkiyat
Çok yüksek
5
Cari hesap ve muhasebe
Çok yüksek
6
Satın alma ve tedarikçi yönetimi
Yüksek
7
CRM ve bayi portalı
Yüksek
8
Üretim ve fason üretim
Orta-yüksek
9
Gelişmiş raporlama ve kârlılık
Yüksek
10
Otomasyon ve gelişmiş analiz
Orta
20. Yazılım firmasına gönderilecek resmi ihtiyaç ve teklif talebi
Kısacası deterjan ve kozmetik sektöründeki faaliyetleri kapsamında; depo, stok, sipariş, sevkiyat, satın alma, müşteri ilişkileri (CRM), finans ve muhasebe süreçlerinin tek bir merkezi sistem üzerinden yönetilmesini hedefleniyor.
1. Ürün ve Stok Yönetimi

  *   Ürün kartları, barkod ve SKU yönetimi.
  *   Ürün kategori ve alt kategori tanımlamaları.
  *   LOT / parti ve SKT takibi.
  *   FIFO / FEFO stok yönetimi.
  *   Minimum ve maksimum stok uyarıları.
  *   Depolar arası transfer.
  *   Sayım ve stok mutabakatı.
  *   Palet, koli, raf ve lokasyon yönetimi.
2. Depo Yönetimi (WMS)

  *   Mal kabul ve ürün giriş işlemleri.
  *   Barkod okuyucu ve el terminali desteği.
  *   Raf ve lokasyon bazlı stok takibi.
  *   Sipariş toplama ve paketleme.
  *   Palet bazlı sevkiyat.
  *   İade, hasarlı ürün ve karantina yönetimi.
3. Sipariş ve Satış Yönetimi

  *   Trendyol ve Hepsiburada entegrasyonları.
  *   Web sitesi ve B2B sipariş entegrasyonu.
  *   Telefon ve manuel sipariş girişi.
  *   Merkezi sipariş havuzu.
  *   Stok rezervasyonu.
  *   Kanal bazlı fiyat ve kampanya yönetimi.
  *   Sipariş durumlarının anlık takibi.
4. Sevkiyat ve Lojistik

  *   Kargo firmalarıyla entegrasyon.
  *   Otomatik kargo etiketi ve takip numarası.
  *   Sevkiyat ve araç yükleme planlaması.
  *   İrsaliye yönetimi.
  *   Teslimat takibi.
  *   İade ve tersine lojistik.
5. Satın Alma ve Tedarikçi Yönetimi

  *   Tedarikçi kartları.
  *   Satın alma talepleri ve siparişleri.
  *   Teklif karşılaştırma.
  *   Termin ve teslimat takibi.
  *   Alış fiyatı geçmişi.
  *   Tedarikçi performans raporları.
6. CRM ve Müşteri Yönetimi

  *   Bireysel, bayi, toptancı ve kurumsal müşteri kartları.
  *   Müşteri satış geçmişi.
  *   Teklif ve satış fırsatı yönetimi.
  *   Satış temsilcisi aktivite takibi.
  *   Müşteri segmentasyonu.
  *   Bayiye özel fiyatlandırma.
  *   Online bayi sipariş portalı.
7. Finans ve Muhasebe

  *   Cari hesap yönetimi.
  *   E-fatura, e-arşiv ve e-irsaliye entegrasyonu.
  *   Alış ve satış faturaları.
  *   Banka ve kasa hareketleri.
  *   POS ve pazaryeri hakediş takibi.
  *   Tahsilat ve ödeme planlaması.
  *   Gelir-gider yönetimi.
  *   Ürün ve kanal bazında kârlılık analizi.
  *   Muhasebe programı entegrasyonu.
8. Raporlama ve Yönetim Paneli

  *   Günlük, haftalık ve aylık satış raporları.
  *   Kanal bazlı ciro ve kârlılık.
  *   Ürün bazlı satış performansı.
  *   Stok yaşlandırma ve stok devir hızı.
  *   SKT raporları.
  *   Sipariş ve sevkiyat performansı.
  *   Müşteri ve tedarikçi cari raporları.
  *   Nakit akışı ve finansal raporlar.
Yukarıdaki modüllere ek olarak sistemin API altyapısına sahip olması, mobil cihazlardan kullanılabilmesi, kullanıcı bazlı yetkilendirme sunması ve tüm işlemleri kayıt altında tutması bizim için önemlidir.
Bu kapsamda tarafımıza aşağıdaki konuları içeren detaylı bir teklif iletilmesini rica ederiz:

  1.  Yazılımın modül bazlı kapsamı ve özellikleri.
  2.  Standart olarak sunulan ve özel geliştirme gerektiren özellikler.
  3.  Kurulum ve devreye alma maliyeti.
  4.  Aylık / yıllık lisans ve kullanım bedelleri.
  5.  Kullanıcı ve depo sayısına göre fiyatlandırma.
  6.  Pazaryeri, kargo ve muhasebe entegrasyon maliyetleri.
  7.  Proje teslim süresi ve uygulama takvimi.
  8.  Eğitim, teknik destek ve bakım koşulları.
  9.  Veri yedekleme ve güvenlik altyapısı.
  10. Demo veya test ortamı kullanım imkânı.
Amacımız yalnızca stok takip sistemi kurmak değil; satın alma, depo, satış, sevkiyat, CRM ve muhasebe süreçlerini birbirine entegre ederek şirketimizin tüm operasyonlarını merkezi olarak yönetebileceğimiz sürdürülebilir bir altyapı oluşturmaktır.
Konuya ilişkin çözüm önerilerinizi, varsa benzer sektörlerdeki uygulama örneklerinizi ve detaylı fiyat teklifinizi paylaşmanızı rica ederiz.
İyi çalışmalar dileriz.
21. Benim önerdiğim en önemli 10 özellik
Yazılım geliştirirken bütün özellikler eşit önemde değildir. Özellikle ilk etapta şu 10 özelliğin eksiksiz çalışmasını koşabiliriz
Tek merkezden stok yönetimi
Bütün satış kanallarında gerçek zamanlı stok.
LOT ve SKT takibi
Kozmetik ve kimyasal ürünlerin parti bazlı izlenmesi.
Palet ve lokasyon yönetimi
Depodaki her ürünün fiziksel konumu.
Otomatik sipariş aktarımı
Trendyol, Hepsiburada  amazon ve web sitesi.
Barkodlu depo operasyonu
Mal kabul, toplama ve sevkiyat doğrulaması.
Otomatik faturalama
Sipariş ve muhasebe süreçlerinin entegrasyonu.
Pazaryeri hakediş kontrolü
Komisyon, kargo ve banka ödemelerinin mutabakatı.
Ürün bazlı gerçek kârlılık
Tüm değişken maliyetleri dikkate alan analiz.
CRM ve bayi portalı
Müşteri, satış fırsatı ve tekrar sipariş yönetimi.
Yönetim dashboard'u
Şirketin tüm operasyonlarını tek ekranda izleme.
22. Projeyi netleştirmek için üç önemli konu
Bu sistemi şirketinizin gerçek operasyonlarına göre şekillendirmek için özellikle üç konuya karar vermek gerekiyor.
1. Üretim modeliniz nasıl?
Hem kendi üretimimiz hem fason üretimimiz var.
2. Depo yapılanmanız nasıl olacak?
Birden fazla depo.
Kendi depomuz + dış lojistik deposu. opsiyonel
3. Muhasebe sisteminiz nasıl çalışacak?
Muhasebe de aynı yazılımın içinde olsun.
Mevcut muhasebe programımızla entegre çalışsın.
4. Hangi satış kanallarını kullanıyoruz?
Trendyol
Hepsiburada
B2B bayi
Web sitesi
Amazon
Eczane kanalı
Kurumsal satış





[cid:image001.png@01DD7765.5625C120]

