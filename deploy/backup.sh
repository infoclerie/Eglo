#!/usr/bin/env bash
# Günlük veritabanı yedeği. cron örneği (her gece 02:30):
#   30 2 * * * cd /home/erp/erp && ./deploy/backup.sh >> backups/backup.log 2>&1
set -euo pipefail
cd "$(dirname "$0")/.."
set -a; source .env; set +a
mkdir -p backups
FILE="backups/erp_$(date +%Y%m%d_%H%M).sql.gz"
docker compose exec -T db pg_dump -U "$DB_USER" "$DB_NAME" | gzip > "$FILE"
find backups -name 'erp_*.sql.gz' -mtime +30 -delete   # 30 günden eskileri sil
echo "$(date) yedek alındı: $FILE"
# Geri yükleme: gunzip -c DOSYA | docker compose exec -T db psql -U $DB_USER $DB_NAME
