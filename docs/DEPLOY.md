# Kurulum

## Hızlı kurulum (tek komut)
```bash
curl -fsSL https://raw.githubusercontent.com/infoclerie/Eglo/main/deploy/bootstrap.sh | sudo bash
# alan adı hazırsa: ... | sudo DOMAIN=erp.eglokozmetik.com bash
```
Alan adı verilmezse geçici olarak `<ip-tireli>.sslip.io` adresi kullanılır (gerçek HTTPS sertifikası alınır).
AWS Lightsail'de ayrıca Networking > IPv4 Firewall'a **HTTPS (443)** kuralı eklenmeli.
Uygulama `/opt/eglo-erp` altındadır; `worker` servisi entegrasyon kuyruğunu çalıştırır; güncelleme: `cd /opt/eglo-erp && sudo git pull && sudo docker compose up -d --build`.

## Sunucu (elle kurulum)
Ubuntu 24.04 LTS · 4 vCPU · 8 GB RAM · 160 GB NVMe (büyüme: 8 vCPU / 16 GB) · sabit IP · alan adı A kaydı.

İlk sertleştirme (root):
```bash
adduser erp && usermod -aG sudo erp          # SSH açık anahtarını /home/erp/.ssh/authorized_keys'e ekle
apt update && apt -y upgrade && apt -y install ufw fail2ban unattended-upgrades git
ufw allow OpenSSH && ufw allow 80,443/tcp && ufw enable
curl -fsSL https://get.docker.com | sh && usermod -aG docker erp
# anahtarla girişi test ettikten sonra /etc/ssh/sshd_config: PermitRootLogin no, PasswordAuthentication no
systemctl restart ssh
```

## Uygulama (erp kullanıcısı)
```bash
git clone <repo-adresi> erp && cd erp
cp .env.example .env && nano .env           # SECRET_KEY, DB_PASSWORD, DOMAIN değerleri
python3 -c "import secrets;print(secrets.token_urlsafe(50))"   # SECRET_KEY üretmek için
docker compose up -d --build
docker compose exec web python manage.py createsuperuser
docker compose exec web python manage.py seed_demo     # isteğe bağlı örnek veri
```
Yedek: `crontab -e` → `30 2 * * * cd /home/erp/erp && ./deploy/backup.sh >> backups/backup.log 2>&1`
Yedekleri ayrıca sunucu dışına (sağlayıcı snapshot / harici depolama) kopyalayın.

## Güncelleme
```bash
cd ~/erp && git pull && docker compose up -d --build     # migrate otomatik çalışır
```

## Yerel geliştirme
```bash
python3 -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt
python manage.py migrate && python manage.py setup_roles && python manage.py seed_demo
python manage.py createsuperuser && python manage.py runserver
```


## Yedekler ve başka sunucuya taşıma

**Ekrandan:** Sistem › Yedekler (yalnız süper kullanıcı): yedek al, indir, bilgisayardan yükle, geri dön, test verilerini temizle.
Yedek = tek `.zip` (tüm veritabanı JSON + ürün fotoğrafları). Geri dönüş tek işlemde yapılır; öncesi otomatik yedeklenir.
Yedekler sunucuda `appbackups` biriminde durur. **Sunucu çökerse içindekiler de gider → önemli yedekleri indirin.**

**Komut satırından:**
```bash
cd /opt/eglo-erp
sudo docker compose exec web python manage.py create_backup --name "Aylık"     # /app/backups_app altına yazar
sudo docker compose cp web:/app/backups_app/DOSYA.zip ./                         # sunucu klasörüne kopyala
```

**Yeni sunucuya taşıma (adım adım):**
1. Eski sistemde Yedekler › "Yedek al" → **İndir**. Eski sunucudaki `/opt/eglo-erp/.env` dosyasının içeriğini de güvenli bir yere
   kopyalayın (içindeki `DJANGO_SECRET_KEY` entegrasyon şifrelerini açan anahtardır; kimseyle paylaşmayın).
2. Yeni sunucuda hızlı kurulum komutunu çalıştırın (yukarıda). Kurulum bitince:
   `sudo nano /opt/eglo-erp/.env` → `DJANGO_SECRET_KEY=` satırını eskisiyle değiştirin (diğer satırlar yeni sunucunun kalsın),
   sonra `cd /opt/eglo-erp && sudo docker compose up -d`.
   (Anahtarı taşımazsanız da sistem çalışır; yalnız entegrasyon şifrelerini sihirbazlardan yeniden girersiniz.)
3. Yedek dosyasını sunucuya kopyalayın (ör. `scp yedek.zip ubuntu@YENI_IP:/tmp/`) ve:
   `cd /opt/eglo-erp && sudo ./deploy/restore.sh /tmp/yedek.zip`
   Süper kullanıcı oluşturmanıza gerek yok: eski kullanıcılar ve şifreler yedekle gelir.
4. Alan adının DNS kaydını yeni sunucunun IP'sine yönlendirin; Lightsail'de 80/443 portlarını açın.
5. Pazaryeri entegrasyonlarında (Trendyol test ortamı vb.) IP yetkisi gerekiyorsa yeni IP'yi bildirin.

Yedek PostgreSQL / SQLite bağımsızdır; aynı veya daha yeni yazılım sürümüne yüklenebilir (önce `git pull` ile güncel kod).
