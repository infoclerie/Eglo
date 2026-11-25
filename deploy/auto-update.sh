#!/usr/bin/env bash
# Eglo ERP — otomatik güncelleme betiği
# Cron ile her dakika çalıştırılır:
#   * * * * * /opt/eglo-erp/deploy/auto-update.sh >> /opt/eglo-erp/updates/update.log 2>&1
#
# Akış:
#   1. updates/pending/ dizininde yeni .zip arar
#   2. meta.json'dan dosya listesini okur
#   3. Dosyaları proje dizinine çıkarır
#   4. docker compose up -d --build
#   5. Zip'i updates/applied/ dizinine taşır
#   6. Sonucu updates/status.json'a yazar

set -euo pipefail

PROJECT_DIR="/opt/eglo-erp"
UPDATES_DIR="${PROJECT_DIR}/updates"
PENDING="${UPDATES_DIR}/pending"
APPLIED="${UPDATES_DIR}/applied"
STATUS="${UPDATES_DIR}/status.json"
LOCKFILE="${UPDATES_DIR}/.update.lock"

mkdir -p "$PENDING" "$APPLIED"

# Kilit: aynı anda iki güncelleme çalışmasın
exec 200>"$LOCKFILE"
flock -n 200 || { echo "$(date -Iseconds) Başka bir güncelleme çalışıyor, atlanıyor."; exit 0; }

# Bekleyen güncelleme var mı?
shopt -s nullglob
zips=("$PENDING"/*.zip)
shopt -u nullglob

if [ ${#zips[@]} -eq 0 ]; then
    exit 0
fi

# İlk bekleyen zip'i al (en eski)
ZIP="${zips[0]}"
ZIPNAME=$(basename "$ZIP")

echo "$(date -Iseconds) Güncelleme başlıyor: $ZIPNAME"

# Geçici dizine çıkar
TMPDIR=$(mktemp -d)
trap 'rm -rf "$TMPDIR"' EXIT

unzip -q "$ZIP" -d "$TMPDIR"

# meta.json oku
if [ ! -f "$TMPDIR/meta.json" ]; then
    echo "$(date -Iseconds) HATA: meta.json bulunamadı"
    mv "$ZIP" "${UPDATES_DIR}/rejected/"
    cat > "$STATUS" << STATUSEOF
{
  "last_update": "$(date -Iseconds)",
  "status": "error",
  "message": "meta.json bulunamadı: $ZIPNAME",
  "filename": "$ZIPNAME"
}
STATUSEOF
    exit 1
fi

VERSION=$(python3 -c "import json; print(json.load(open('$TMPDIR/meta.json')).get('version','?'))")
echo "$(date -Iseconds) Sürüm: $VERSION"

# Dosyaları proje dizinine kopyala
if [ -d "$TMPDIR/files" ]; then
    cd "$TMPDIR/files"
    find . -type f | while read -r f; do
        dest="${PROJECT_DIR}/${f#./}"
        mkdir -p "$(dirname "$dest")"
        cp "$f" "$dest"
        echo "  → $dest"
    done
    cd "$PROJECT_DIR"
fi

# Docker rebuild
echo "$(date -Iseconds) Docker yeniden oluşturuluyor..."
cd "$PROJECT_DIR"
docker compose up -d --build 2>&1 | tail -5

# Başarılı: zip'i applied'a taşı
mv "$ZIP" "$APPLIED/"

# Durum dosyasını güncelle
cat > "$STATUS" << STATUSEOF
{
  "last_update": "$(date -Iseconds)",
  "status": "success",
  "current_version": "$VERSION",
  "message": "Güncelleme başarıyla uygulandı: $ZIPNAME",
  "filename": "$ZIPNAME"
}
STATUSEOF

echo "$(date -Iseconds) Güncelleme tamamlandı: v$VERSION"
