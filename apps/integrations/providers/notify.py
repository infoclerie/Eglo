"""
Bildirim sağlayıcıları.
- E-posta (SMTP): her e-posta servisiyle çalışır (şirket maili, Google Workspace, Yandex, Outlook/Office 365...).
- SMS (Netgsm): https://api.netgsm.com.tr/sms/send/get  usercode, password, gsmno, message, msgheader, dil=TR
  Başarılı yanıt "00 <görevno>" veya "01/02 ..." ile başlar; 20/30/40/50/51/70/80/85 hata kodlarıdır.
  NOT: Canlı Netgsm hesabıyla ilk kurulumda doğrulanmalıdır (bu yazılım geliştirilirken hesap yoktu).
  Ticari/pazarlama SMS'leri İYS izni gerektirir; sistem yalnızca bilgilendirme mesajı gönderir.
"""
import smtplib
import socket

import requests
from django.core.mail import EmailMessage, get_connection

from . import Field, Provider

NETGSM_ERRORS = {"20": "Mesaj metni hatalı / çok uzun", "30": "Kullanıcı adı, şifre veya API yetkisi hatalı",
                 "40": "Mesaj başlığı (gönderici adı) sistemde tanımlı değil", "50": "İYS kontrollü gönderim hatası",
                 "51": "İYS marka bilgisi bulunamadı", "70": "Hatalı parametre", "80": "Gönderim sınırı aşıldı",
                 "85": "Aynı numaraya çok sık gönderim"}

# E-posta servis hazır ayarları: sihirbazın ilk adımında kart olarak gösterilir, seçilince sunucu/port/güvenlik dolar.
# (kod, ad, sunucu, port, güvenlik, kullanıcı adı ipucu, kısa not, grup)
MAIL_PRESETS = [
    ("gmail", "Gmail", "smtp.gmail.com", 587, "tls", "",
     "Google hesabında 2 adımlı doğrulamayı açın, sonra myaccount.google.com/apppasswords adresinden 16 haneli 'uygulama şifresi' alıp şifre alanına yazın. Günlük ~500 e-posta sınırı vardır.", "Kişisel / kurumsal"),
    ("workspace", "Google Workspace", "smtp.gmail.com", 587, "tls", "",
     "Şirket alan adlı Google hesabı. Kullanıcı için 2 adımlı doğrulama + uygulama şifresi gerekir (yönetici panelinde izin verilmiş olmalı). Günlük ~2.000 e-posta.", "Kişisel / kurumsal"),
    ("m365", "Microsoft 365 / Outlook (kurumsal)", "smtp.office365.com", 587, "tls", "",
     "Yönetici, Microsoft 365 yönetim merkezinde bu posta kutusu için 'Kimliği doğrulanmış SMTP' iznini açmalıdır. Microsoft, Aralık 2026 sonundan itibaren bu yöntemi varsayılan olarak kapatıyor (yönetici yeniden açabilir); uzun vadede Brevo/SES gibi bir gönderim servisi önerilir.", "Kişisel / kurumsal"),
    ("outlookcom", "Outlook.com / Hotmail (kişisel)", "smtp-mail.outlook.com", 587, "tls", "",
     "Microsoft kişisel hesaplarda şifreyle SMTP girişini büyük ölçüde kapattı; bağlantı başarısız olursa şirket maili veya bir gönderim servisi kullanın.", "Kişisel / kurumsal"),
    ("yandex", "Yandex / Yandex 360", "smtp.yandex.com", 465, "ssl", "",
     "Yandex ID › Güvenlik › Uygulama şifreleri bölümünden 'E-posta' türünde şifre oluşturun. Posta ayarlarında 'IMAP/SMTP ile erişim' açık olmalı.", "Kişisel / kurumsal"),
    ("zoho", "Zoho Mail", "smtppro.zoho.com", 465, "ssl", "",
     "Ücretli kurumsal hesapta smtppro.zoho.com, ücretsiz hesapta smtp.zoho.com; hesabınız AB veri merkezindeyse .eu ile biter (smtppro.zoho.eu). 2 adımlı doğrulama açıksa uygulama şifresi kullanın.", "Kişisel / kurumsal"),
    ("yahoo", "Yahoo Mail", "smtp.mail.yahoo.com", 465, "ssl", "",
     "Hesap güvenliği bölümünden 'uygulama şifresi' oluşturup kullanın.", "Kişisel / kurumsal"),
    ("icloud", "iCloud Mail", "smtp.mail.me.com", 587, "tls", "",
     "appleid.apple.com › Uygulamaya özel parolalar bölümünden parola oluşturun. Kullanıcı adı tam iCloud e-posta adresidir.", "Kişisel / kurumsal"),
    ("hosting", "Hosting firması maili (cPanel / Plesk)", "mail.ALANADINIZ.com", 465, "ssl", "",
     "Natro, Turhost, Güzel Hosting, İsimtescil vb. Sunucu genelde mail.alanadiniz.com'dur; tam bilgiyi hosting panelinizde 'E-posta hesapları › Bağlantı ayarları' altında bulabilirsiniz. Kullanıcı adı tam e-posta adresidir.", "Kişisel / kurumsal"),
    ("brevo", "Brevo (Sendinblue)", "smtp-relay.brevo.com", 587, "tls", "",
     "Brevo panelinde SMTP & API › SMTP sekmesindeki 'Login' kullanıcı adı, 'SMTP key' şifredir. Gönderen alan adınızı Brevo'da doğrulayın.", "Toplu gönderim servisleri"),
    ("ses", "Amazon SES", "email-smtp.eu-north-1.amazonaws.com", 587, "tls", "",
     "SES konsolunda SMTP settings › Create SMTP credentials ile kullanıcı adı/şifre üretin (IAM şifresi değildir). Sunucudaki bölgeyi kendi SES bölgenizle değiştirin. Yeni hesap 'sandbox' modundaysa yalnızca doğrulanmış adreslere gider.", "Toplu gönderim servisleri"),
    ("sendgrid", "SendGrid", "smtp.sendgrid.net", 587, "tls", "apikey",
     "Kullanıcı adı birebir 'apikey' yazılır, şifre olarak SendGrid'de oluşturduğunuz API anahtarını girin.", "Toplu gönderim servisleri"),
    ("mailgun", "Mailgun", "smtp.mailgun.org", 587, "tls", "",
     "Alan adı ayarlarındaki SMTP kullanıcısı ve şifresini girin. Hesabınız AB bölgesindeyse sunucu smtp.eu.mailgun.org olmalı.", "Toplu gönderim servisleri"),
    ("mailjet", "Mailjet", "in-v3.mailjet.com", 587, "tls", "",
     "Kullanıcı adı API Key, şifre Secret Key'dir (Hesap › API anahtarları).", "Toplu gönderim servisleri"),
    ("custom", "Diğer / kendi sunucum", "", 587, "tls", "",
     "Sunucu, port ve güvenlik bilgisini e-posta sağlayıcınızdan veya BT ekibinizden alın.", "Diğer"),
]
PRESET_MAP = {p[0]: p for p in MAIL_PRESETS}


def friendly_smtp_error(exc):
    """Teknik SMTP hatasını herkesin anlayacağı açıklamaya çevirir."""
    text = str(exc)
    if isinstance(exc, smtplib.SMTPAuthenticationError) or "5.7.8" in text or "535" in text:
        return "Kullanıcı adı veya şifre kabul edilmedi. Gmail/Yandex/Yahoo/iCloud'da normal şifre değil 'uygulama şifresi' gerekir."
    if "5.7.30" in text or "5.7.139" in text or "SmtpClientAuthentication is disabled" in text:
        return "Microsoft bu hesapta SMTP girişini kapatmış. Yönetici, posta kutusu için 'Kimliği doğrulanmış SMTP'yi açmalı."
    if isinstance(exc, (socket.timeout, TimeoutError)) or "timed out" in text:
        return "Sunucu yanıt vermedi. Sunucu adını ve portu kontrol edin; 465 ise güvenlik 'SSL', 587 ise 'TLS' olmalı."
    if isinstance(exc, socket.gaierror) or "Name or service not known" in text or "nodename nor servname" in text:
        return "Sunucu adı bulunamadı. Yazımı kontrol edin (ör. mail.alanadiniz.com)."
    if isinstance(exc, ConnectionRefusedError) or "refused" in text:
        return "Sunucu bu portta bağlantı kabul etmiyor. 587 (TLS) veya 465 (SSL) deneyin."
    if "SSL" in text or "wrong version number" in text:
        return "Güvenlik türü porta uymuyor: 465 için 'SSL', 587 için 'TLS' seçin."
    return f"E-posta sunucusuna bağlanılamadı: {text}"


class SmtpEmail(Provider):
    code = "smtp_email"
    name = "E-posta"
    category = "notify_email"
    description = "Gmail, Outlook/Microsoft 365, Yandex, Zoho, hosting maili, Brevo, Amazon SES, SendGrid... her e-posta servisiyle bildirim gönderir."
    presets = MAIL_PRESETS
    color = "#2563c9"
    icon = "inbox"
    steps = [("service", "E-posta servisi"), ("credentials", "Hesap bilgileri"), ("test", "Bağlantı testi"), ("settings", "Ayarlar"), ("summary", "Özet ve etkinleştir")]
    fields = [
        Field("host", "SMTP sunucusu (giden posta)", help="Servis seçiminde otomatik dolar. Örn: smtp.gmail.com, smtp.yandex.com, smtp.office365.com, mail.sirketiniz.com"),
        Field("port", "Port", kind="int", default=587, help="Genelde 587 (TLS) veya 465 (SSL)."),
        Field("security", "Güvenlik", kind="choice", default="tls", choices=[("tls", "TLS (587)"), ("ssl", "SSL (465)"), ("none", "Yok")]),
        Field("username", "Kullanıcı adı (e-posta adresi)"),
        Field("password", "Şifre / uygulama şifresi", kind="password", secret=True,
              help="Gmail/Outlook'ta normal şifre yerine 'uygulama şifresi' oluşturmanız gerekir."),
        Field("from_email", "Gönderen adresi", step="settings", kind="email", help="Örn: bildirim@eglokozmetik.com"),
        Field("from_name", "Gönderen adı", step="settings", default="Eglo Kozmetik"),
        Field("test_to", "Test e-postası gidecek adres", step="settings", kind="email", required=False),
    ]

    def _conn(self, config, secrets):
        sec = config.get("security", "tls")
        return get_connection("django.core.mail.backends.smtp.EmailBackend", host=config.get("host"),
                              port=int(config.get("port") or 587), username=config.get("username"),
                              password=secrets.get("password", ""), use_tls=sec == "tls", use_ssl=sec == "ssl", timeout=15)

    def test_connection(self, config, secrets, environment):
        try:
            c = self._conn(config, secrets)
            c.open()
            c.close()
            return True, f"{config.get('host')} sunucusuna giriş yapıldı."
        except Exception as exc:  # noqa: BLE001
            return False, friendly_smtp_error(exc)

    def on_activate(self, account):
        to = account.config.get("test_to")
        if to:
            from apps.integrations.services import enqueue
            enqueue(account, "notify.email", "test", {"to": to, "subject": "Eglo ERP test e-postası",
                                                       "body": "E-posta bildirimleri başarıyla kuruldu."}, key=f"{account.pk}:email-test:{to}")

    def handle(self, account, job):
        c = account.config
        sender = f"{c.get('from_name', '')} <{c.get('from_email') or c.get('username')}>"
        msg = EmailMessage(job.payload.get("subject", ""), job.payload.get("body", ""), sender, [job.payload["to"]],
                           connection=self._conn(c, account.get_secrets()))
        msg.send(fail_silently=False)
        return {"sent_to": job.payload["to"]}


class NetgsmSms(Provider):
    code = "netgsm_sms"
    name = "SMS (Netgsm)"
    category = "notify_sms"
    description = "Kargo bilgilendirmesi ve personel uyarılarını SMS olarak gönderir."
    color = "#0e7490"
    icon = "alert"
    steps = [("credentials", "Hesap bilgileri"), ("test", "Bağlantı testi"), ("settings", "Ayarlar"), ("summary", "Özet ve etkinleştir")]
    URL = "https://api.netgsm.com.tr/sms/send/get"
    fields = [
        Field("usercode", "Netgsm kullanıcı adı (abone no)", help="Netgsm panelindeki kullanıcı adınız, genelde 850XXXXXXX."),
        Field("password", "API şifresi", kind="password", secret=True, help="Netgsm › Ayarlar › API kullanıcısı bölümünden."),
        Field("header", "Mesaj başlığı (gönderici adı)", step="settings", help="Netgsm'de onaylı başlık, ör. EGLOKOZMTK"),
        Field("test_to", "Test SMS'i gidecek numara", step="settings", required=False, help="5XXXXXXXXX"),
    ]

    def _send(self, config, secrets, to, text):
        r = requests.get(self.URL, timeout=20, params={"usercode": config.get("usercode"), "password": secrets.get("password", ""),
                                                       "gsmno": to, "message": text, "msgheader": config.get("header", ""), "dil": "TR"})
        code = r.text.strip().split(" ")[0]
        if code in ("00", "01", "02"):
            return r.text.strip()
        raise ValueError(f"Netgsm {code}: {NETGSM_ERRORS.get(code, r.text.strip()[:100])}")

    def test_connection(self, config, secrets, environment):
        try:
            r = requests.get("https://api.netgsm.com.tr/balance/list/get", timeout=15,
                             params={"usercode": config.get("usercode"), "password": secrets.get("password", ""), "tip": 1})
            text = r.text.strip()
            if text.split(" ")[0] in ("30", "40", "70"):
                return False, f"Netgsm: {NETGSM_ERRORS.get(text.split(' ')[0], text)}"
            return True, f"Netgsm hesabına bağlanıldı (bakiye yanıtı: {text[:60]})."
        except requests.RequestException as exc:
            return False, f"Netgsm'e bağlanılamadı: {exc}"

    def on_activate(self, account):
        to = account.config.get("test_to")
        if to:
            from apps.integrations.services import enqueue
            enqueue(account, "notify.sms", "test", {"to": to, "text": "Eglo ERP SMS bildirimleri kuruldu."}, key=f"{account.pk}:sms-test:{to}")

    def handle(self, account, job):
        return {"result": self._send(account.config, account.get_secrets(), job.payload["to"], job.payload["text"])}
