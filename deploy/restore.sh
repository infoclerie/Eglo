#!/usr/bin/env bash
# Yedek dosyasını (.zip) bu sunucuya yükler — yeni sunucuya taşıma veya felaket sonrası kurtarma.
# Kullanım:  cd /opt/eglo-erp && sudo ./deploy/restore.sh /root/yedek.zip
set -euo pipefail
cd "$(dirname "$0")/.."
FILE="${1:?Kullanım: sudo ./deploy/restore.sh YEDEK.zip}"
[ -f "$FILE" ] || { echo "Dosya bulunamadı: $FILE"; exit 1; }
docker compose up -d
echo ">> Uygulamanın açılması bekleniyor..."
for i in $(seq 1 60); do docker compose exec -T web python manage.py check >/dev/null 2>&1 && break; sleep 3; done
docker compose cp "$FILE" web:/tmp/restore.zip
docker compose exec -T web python manage.py restore_backup /tmp/restore.zip --yes
docker compose exec -T web rm -f /tmp/restore.zip
docker compose restart worker
echo ">> Tamam. Eski kullanıcı adı ve şifrelerle giriş yapabilirsiniz."
