#!/usr/bin/env bash
# Eglo ERP — güncelleme paketi oluşturma betiği
# Kullanım: ./deploy/build-update.sh <sürüm> "<açıklama>" <dosya1> [dosya2] ...
# Örnek:   ./deploy/build-update.sh 1.1.0 "Sanal Ofis eklendi" apps/office/ templates/partials/sidebar.html
#
# Not: Bu betik AI veya geliştirici tarafından çalıştırılır, sunucuda değil.
# Çıktı: update-v<sürüm>.zip (mevcut dizine)

set -euo pipefail

if [ $# -lt 3 ]; then
    echo "Kullanım: $0 <sürüm> \"<açıklama>\" <dosya/klasör> [dosya/klasör] ..."
    exit 1
fi

VERSION="$1"
DESC="$2"
shift 2

OUTFILE="update-v${VERSION}.zip"
TMPDIR=$(mktemp -d)
trap 'rm -rf "$TMPDIR"' EXIT

# Dosyaları files/ altına kopyala
mkdir -p "$TMPDIR/files"
FILE_LIST=""
for path in "$@"; do
    if [ -d "$path" ]; then
        # Klasör: içindeki dosyaları kopyala
        find "$path" -type f -not -path "*/__pycache__/*" -not -name "*.pyc" | while read -r f; do
            mkdir -p "$TMPDIR/files/$(dirname "$f")"
            cp "$f" "$TMPDIR/files/$f"
        done
    elif [ -f "$path" ]; then
        mkdir -p "$TMPDIR/files/$(dirname "$path")"
        cp "$path" "$TMPDIR/files/$path"
    else
        echo "UYARI: $path bulunamadı, atlanıyor."
    fi
done

# Dosya listesi
FILE_LIST=$(cd "$TMPDIR/files" && find . -type f | sed 's|^\./||' | sort)
FILE_COUNT=$(echo "$FILE_LIST" | wc -l)

# meta.json oluştur
cat > "$TMPDIR/meta.json" << EOF
{
  "version": "$VERSION",
  "description": "$DESC",
  "created_at": "$(date -Iseconds)",
  "file_count": $FILE_COUNT,
  "files": $(echo "$FILE_LIST" | python3 -c "import sys,json; print(json.dumps([l.strip() for l in sys.stdin if l.strip()]))")
}
EOF

# Zip oluştur
cd "$TMPDIR"
rm -f "$OLDPWD/$OUTFILE"
zip -qr "$OLDPWD/$OUTFILE" meta.json files/

echo "✅ Güncelleme paketi oluşturuldu: $OUTFILE ($FILE_COUNT dosya, sürüm v$VERSION)"
echo "   Açıklama: $DESC"
