"""
Bildirim olayları kataloğu. Her olay: etiket, alıcı türü (müşteri / personel), kullanılabilir alanlar ve varsayılan taslaklar.
Taslaklarda {alan} yazılır; gönderimde gerçek değerle değişir. Yeni olay eklemek: buraya ekle + handlers.py'de tetikle.
"""
EVENTS = {
    # ---------------------------------------------------------------- müşteriye gidenler
    "partner_created": {
        "label": "Yeni cari açıldığında (hoş geldiniz)", "audience": "customer",
        "fields": {"musteri": "Cari adı", "cari_kodu": "Cari kodu", "firma": "Şirketimizin adı"},
        "subject": "{firma} ailesine hoş geldiniz", "sms": "Sayın {musteri}, {firma} ailesine hoş geldiniz. Cari kodunuz: {cari_kodu}",
        "body": "Sayın {musteri},\n\n{firma} ile çalışmaya başladığınız için teşekkür ederiz. Cari kodunuz: {cari_kodu}.\n\nSaygılarımızla,\n{firma}"},
    "order_received": {
        "label": "Sipariş alındığında", "audience": "customer",
        "fields": {"musteri": "Müşteri adı", "siparis_no": "Sipariş no", "tutar": "Sipariş tutarı", "kanal": "Satış kanalı", "firma": "Şirketimizin adı"},
        "subject": "Siparişiniz alındı: {siparis_no}", "sms": "Sayın {musteri}, {siparis_no} nolu {tutar} TL siparişiniz alınmıştır. {firma}",
        "body": "Sayın {musteri},\n\n{siparis_no} numaralı siparişiniz ({tutar} TL) alınmış ve hazırlanmaya başlanmıştır.\n\n{firma}"},
    "order_shipped": {
        "label": "Sipariş kargoya verildiğinde", "audience": "customer",
        "fields": {"musteri": "Müşteri adı", "siparis_no": "Sipariş no", "kargo": "Kargo firması", "takip_no": "Takip no", "firma": "Şirketimizin adı"},
        "subject": "Siparişiniz kargoya verildi: {siparis_no}", "sms": "Sayın {musteri}, {siparis_no} nolu siparişiniz {kargo} ile kargoya verildi. Takip no: {takip_no}. {firma}",
        "body": "Sayın {musteri},\n\n{siparis_no} numaralı siparişiniz {kargo} ile kargoya verilmiştir.\nTakip numarası: {takip_no}\n\n{firma}"},
    "order_delivered": {
        "label": "Sipariş teslim edildiğinde", "audience": "customer",
        "fields": {"musteri": "Müşteri adı", "siparis_no": "Sipariş no", "firma": "Şirketimizin adı"},
        "subject": "Siparişiniz teslim edildi", "sms": "Sayın {musteri}, {siparis_no} nolu siparişiniz teslim edilmiştir. Bizi tercih ettiğiniz için teşekkürler. {firma}",
        "body": "Sayın {musteri},\n\n{siparis_no} numaralı siparişiniz teslim edilmiştir. Bizi tercih ettiğiniz için teşekkür ederiz.\n\n{firma}"},
    "invoice_issued": {
        "label": "Fatura kesildiğinde", "audience": "customer",
        "fields": {"musteri": "Müşteri adı", "fatura_no": "Fatura no", "tutar": "Fatura tutarı", "vade": "Vade tarihi", "firma": "Şirketimizin adı"},
        "subject": "Faturanız düzenlendi: {fatura_no}", "sms": "Sayın {musteri}, {fatura_no} nolu {tutar} TL faturanız düzenlenmiştir. Vade: {vade}. {firma}",
        "body": "Sayın {musteri},\n\n{fatura_no} numaralı {tutar} TL tutarlı faturanız düzenlenmiştir. Vade tarihi: {vade}.\n\n{firma}"},
    "payment_received": {
        "label": "Tahsilat alındığında", "audience": "customer",
        "fields": {"musteri": "Müşteri adı", "tutar": "Tahsilat tutarı", "tarih": "Tarih", "bakiye": "Kalan bakiye", "firma": "Şirketimizin adı"},
        "subject": "Ödemeniz alındı", "sms": "Sayın {musteri}, {tarih} tarihli {tutar} TL ödemeniz alınmıştır. Güncel bakiye: {bakiye} TL. {firma}",
        "body": "Sayın {musteri},\n\n{tarih} tarihli {tutar} TL ödemeniz hesabınıza işlenmiştir. Güncel bakiyeniz: {bakiye} TL.\n\nTeşekkür ederiz,\n{firma}"},
    # ---------------------------------------------------------------- personele gidenler
    "order_new": {
        "label": "Yeni sipariş geldiğinde", "audience": "staff",
        "fields": {"siparis_no": "Sipariş no", "musteri": "Müşteri", "tutar": "Tutar", "kanal": "Kanal"},
        "subject": "Yeni sipariş: {siparis_no} ({kanal})", "sms": "Yeni sipariş {siparis_no} {kanal} {tutar} TL", "body": "{musteri} · {tutar} TL"},
    "order_cancelled": {
        "label": "Sipariş iptal edildiğinde", "audience": "staff", "fields": {"siparis_no": "Sipariş no", "musteri": "Müşteri"},
        "subject": "Sipariş iptal: {siparis_no}", "sms": "Sipariş iptal: {siparis_no}", "body": "{musteri}"},
    "approval_requested": {
        "label": "Onay bekleyen işlem olduğunda", "audience": "staff", "fields": {"baslik": "İşlem", "talep_eden": "Talep eden"},
        "subject": "Onay bekliyor: {baslik}", "sms": "Onay bekliyor: {baslik}", "body": "Talep eden: {talep_eden}"},
    "low_stock": {
        "label": "Ürün kritik stoğa düştüğünde", "audience": "staff", "fields": {"urun": "Ürün", "stok": "Satışa uygun stok", "minimum": "Minimum stok"},
        "subject": "Kritik stok: {urun}", "sms": "Kritik stok: {urun} ({stok}/{minimum})", "body": "Satışa uygun {stok}, minimum {minimum}"},
    "integration_failed": {
        "label": "Entegrasyon hatası olduğunda", "audience": "staff", "fields": {"baglanti": "Bağlantı", "is": "İş", "hata": "Hata"},
        "subject": "Entegrasyon hatası: {baglanti}", "sms": "Entegrasyon hatası: {baglanti} {is}", "body": "{is}: {hata}"},
}

CUSTOMER_EVENTS = [k for k, v in EVENTS.items() if v["audience"] == "customer"]
STAFF_EVENTS = [k for k, v in EVENTS.items() if v["audience"] == "staff"]
