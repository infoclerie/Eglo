"""
Bildirim sağlayıcıları.
- E-posta (SMTP): her e-posta servisiyle çalışır (şirket maili, Google Workspace, Yandex, Outlook/Office 365...).
- SMS (Netgsm): https://api.netgsm.com.tr/sms/send/get  usercode, password, gsmno, message, msgheader, dil=TR
  Başarılı yanıt "00 <görevno>" veya "01/02 ..." ile başlar; 20/30/40/50/51/70/80/85 hata kodlarıdır.
  NOT: Canlı Netgsm hesabıyla ilk kurulumda doğrulanmalıdır (bu yazılım geliştirilirken hesap yoktu).
  Ticari/pazarlama SMS'leri İYS izni gerektirir; sistem yalnızca bilgilendirme mesajı gönderir.
"""
import requests
from django.core.mail import EmailMessage, get_connection

from . import Field, Provider

NETGSM_ERRORS = {"20": "Mesaj metni hatalı / çok uzun", "30": "Kullanıcı adı, şifre veya API yetkisi hatalı",
                 "40": "Mesaj başlığı (gönderici adı) sistemde tanımlı değil", "50": "İYS kontrollü gönderim hatası",
                 "51": "İYS marka bilgisi bulunamadı", "70": "Hatalı parametre", "80": "Gönderim sınırı aşıldı",
                 "85": "Aynı numaraya çok sık gönderim"}


class SmtpEmail(Provider):
    code = "smtp_email"
    name = "E-posta (SMTP)"
    category = "notify_email"
    description = "Bildirimleri ve müşteri bilgilendirmelerini şirket e-posta hesabınızdan gönderir."
    color = "#2563c9"
    icon = "inbox"
    steps = [("credentials", "Sunucu bilgileri"), ("test", "Bağlantı testi"), ("settings", "Ayarlar"), ("summary", "Özet ve etkinleştir")]
    fields = [
        Field("host", "SMTP sunucusu", help="Örn: smtp.gmail.com, smtp.yandex.com, smtp.office365.com, mail.sirketiniz.com"),
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
            return False, f"E-posta sunucusuna bağlanılamadı: {exc}"

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
