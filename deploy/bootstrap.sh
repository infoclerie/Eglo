#!/usr/bin/env bash
# Eglo ERP — Ubuntu 22.04/24.04 sunucuya ilk kurulum (tekrar çalıştırılabilir).
# Kullanım (sunucuda):
#   curl -fsSL https://raw.githubusercontent.com/infoclerie/Eglo/main/deploy/bootstrap.sh | sudo bash
# Alan adı vermek için:  ... | sudo DOMAIN=erp.eglokozmetik.com bash
set -euo pipefail

APP_DIR=/opt/eglo-erp
REPO=https://github.com/infoclerie/Eglo.git
PUBLIC_IP=$(curl -fsS4 https://checkip.amazonaws.com || hostname -I | awk '{print $1}')
DOMAIN=${DOMAIN:-$(echo "$PUBLIC_IP" | tr . -).sslip.io}

echo ">> Sistem güncelleniyor"
export DEBIAN_FRONTEND=noninteractive NEEDRESTART_MODE=a
apt-get update -q && apt-get -yq upgrade
apt-get -yq install git ufw fail2ban unattended-upgrades ca-certificates curl

echo ">> Swap (2 GB) — düşük RAM'li sunucuda derleme için"
if ! swapon --show | grep -q /swapfile; then
  fallocate -l 2G /swapfile && chmod 600 /swapfile && mkswap /swapfile && swapon /swapfile
  grep -q /swapfile /etc/fstab || echo '/swapfile none swap sw 0 0' >> /etc/fstab
fi

echo ">> Güvenlik duvarı"
ufw allow OpenSSH && ufw allow 80/tcp && ufw allow 443/tcp && ufw --force enable
systemctl enable --now fail2ban unattended-upgrades

echo ">> Docker"
command -v docker >/dev/null || curl -fsSL https://get.docker.com | sh
id ubuntu >/dev/null 2>&1 && usermod -aG docker ubuntu || true

echo ">> Kod"
if [ -d "$APP_DIR/.git" ]; then git -C "$APP_DIR" pull --ff-only; else git clone "$REPO" "$APP_DIR"; fi
cd "$APP_DIR"

if [ ! -f .env ]; then
  echo ">> .env oluşturuluyor (gizli değerler rastgele üretilir)"
  SECRET=$(openssl rand -base64 48 | tr -d '\n/+=')
  DBPASS=$(openssl rand -base64 24 | tr -d '\n/+=')
  cat > .env <<EOF
DJANGO_SECRET_KEY=$SECRET
DJANGO_DEBUG=false
DJANGO_ALLOWED_HOSTS=$DOMAIN,$PUBLIC_IP,localhost
DJANGO_CSRF_TRUSTED_ORIGINS=https://$DOMAIN
DOMAIN=$DOMAIN
DB_ENGINE=postgres
DB_NAME=erp
DB_USER=erp
DB_PASSWORD=$DBPASS
DB_HOST=db
DB_PORT=5432
EOF
  chmod 600 .env
fi

echo ">> Uygulama başlatılıyor"
docker compose up -d --build

echo ">> Günlük yedek (02:30)"
chmod +x deploy/backup.sh
mkdir -p backups
CRON_LINE="30 2 * * * cd $APP_DIR && ./deploy/backup.sh >> $APP_DIR/backups/backup.log 2>&1"
{ crontab -l 2>/dev/null | grep -v eglo-erp || true; echo "$CRON_LINE"; } | crontab -

echo
echo "=================================================================="
echo " Kurulum tamam. Adres: https://$(grep ^DOMAIN= .env | cut -d= -f2)"
echo " Yönetici kullanıcı oluşturmak için:"
echo "   cd $APP_DIR && sudo docker compose exec web python manage.py createsuperuser"
[ -f /var/run/reboot-required ] && echo " NOT: Çekirdek güncellendi. Kullanıcıyı oluşturduktan sonra: sudo reboot (uygulama kendiliğinden geri açılır)"
echo " Örnek veri (isteğe bağlı):"
echo "   sudo docker compose exec web python manage.py seed_demo"
echo "=================================================================="
