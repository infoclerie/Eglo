# Kurulum

## Sunucu
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
