#!/usr/bin/env bash
# Günlük veritabanı yedeği. cron örneği (her gece 02:30):
#   30 2 * * * cd /home/erp/erp && ./deploy/backup.sh >> backups/backup.log 2>&1
set -euo pipefail
cd "$(dirname "$0")/.."
set -a; source .env; set +a
mkdir -p backups
FILE="backups/erp_$(date +%Y%m%d_%H%M).sql.gz"
docker compose exec -T db pg_dump -U "$DB_USER" "$DB_NAME" | gzip > "$FILE"
# Ürün fotoğrafları (media birimi) — haftada bir tam kopya (pazar)
if [ "$(date +%u)" = "7" ]; then
  docker compose exec -T web tar czf - -C /app media > "backups/media_$(date +%Y%m%d).tar.gz"
fi
find backups -name 'erp_*.sql.gz' -mtime +30 -delete   # 30 günden eskileri sil
find backups -name 'media_*.tar.gz' -mtime +60 -delete
echo "$(date) yedek alındı: $FILE"
# Geri yükleme: gunzip -c DOSYA | docker compose exec -T db psql -U $DB_USER $DB_NAME
