#!/usr/bin/env bash
# Eglo ERP — sunucu tarafı güncelleme betiği (root crontab, her dakika):
#   * * * * * /opt/eglo-erp/deploy/auto-update.sh >/dev/null 2>&1
#
# Web arayüzü (Ayarlar › Güncellemeler) sadece talep bırakır:
#   updates/request.json      → GitHub'dan güncelle (git pull)
#   updates/pending/*.zip     → zip paketini uygula
# Bu betik talebi işler, adım adım updates/progress.json ve updates/update.log'a yazar;
# sayfa bu dosyaları 2 sn'de bir okuyarak canlı ilerleme gösterir.
set -uo pipefail

PROJECT_DIR="/opt/eglo-erp"
U="${PROJECT_DIR}/updates"
LOG="$U/update.log"
PROGRESS="$U/progress.json"
STATUS="$U/status.json"
REQ="$U/request.json"
mkdir -p "$U/pending" "$U/applied" "$U/rejected"
chmod 777 "$U" "$U/pending" "$U/applied" "$U/rejected" 2>/dev/null

exec 200>"$U/.update.lock"
flock -n 200 || exit 0

TOTAL=5
log() { echo "$(date '+%H:%M:%S') $*" >> "$LOG"; }
step() {  # step <no> <etiket>
  printf '{"running": true, "step": %s, "total": %s, "label": "%s", "started": "%s"}\n' \
    "$1" "$TOTAL" "$2" "$STARTED" > "$PROGRESS"
  log "[$1/$TOTAL] $2"
}
finish() {  # finish <success|error> <mesaj> <sürüm>
  printf '{"running": false, "step": %s, "total": %s, "label": "%s", "result": "%s"}\n' \
    "$TOTAL" "$TOTAL" "$2" "$1" > "$PROGRESS"
  python3 - "$1" "$2" "$3" "$STATUS" <<'PY'
import json, sys, datetime
s, msg, ver, path = sys.argv[1:5]
json.dump({"status": s, "message": msg, "current_version": ver,
           "last_update": datetime.datetime.now().strftime("%d.%m.%Y %H:%M")},
          open(path, "w"), ensure_ascii=False, indent=2)
PY
  chmod 666 "$PROGRESS" "$STATUS" "$LOG" 2>/dev/null
  log "$2"
}

run() {
  STARTED="$(date '+%H:%M:%S')"
  : > "$LOG"
  cd "$PROJECT_DIR"
  local ZIP="" VERSION=""
  shopt -s nullglob; zips=("$U"/pending/*.zip); shopt -u nullglob
  [ ${#zips[@]} -gt 0 ] && ZIP="${zips[0]}"

  step 1 "Talep alındı, hazırlanıyor"
  if [ -f "$REQ" ]; then
    rm -f "$REQ"
    step 2 "GitHub'dan son kod çekiliyor"
    if ! git diff --quiet; then
      log "Sunucudaki yerel değişiklikler kenara alındı (git stash)."
      git stash push -m "auto-update $(date -Iseconds)" >> "$LOG" 2>&1
    fi
    if ! git pull --ff-only origin main >> "$LOG" 2>&1; then
      finish error "GitHub'dan çekilemedi — ayrıntı günlükte" "$(git rev-parse --short HEAD)"; return
    fi
    VERSION="$(git log -1 --format='%h · %s' | cut -c1-80 | tr -d '"\\')"
  elif [ -n "$ZIP" ]; then
    step 2 "Zip paketi açılıyor: $(basename "$ZIP")"
    TMP=$(mktemp -d)
    if ! unzip -q "$ZIP" -d "$TMP" || [ ! -f "$TMP/meta.json" ]; then
      mv "$ZIP" "$U/rejected/"; rm -rf "$TMP"
      finish error "Zip bozuk veya meta.json yok" "?"; return
    fi
    VERSION=$(python3 -c "import json;print(json.load(open('$TMP/meta.json')).get('version','?'))")
    (cd "$TMP/files" && find . -type f) | while read -r f; do
      mkdir -p "$(dirname "$PROJECT_DIR/${f#./}")"
      cp "$TMP/files/$f" "$PROJECT_DIR/${f#./}" && log "  → ${f#./}"
    done
    rm -rf "$TMP"; mv "$ZIP" "$U/applied/"
  else
    rm -f "$PROGRESS"; return
  fi

  step 3 "Uygulama yeniden derleniyor (1-3 dk sürebilir)"
  if ! docker compose build web worker >> "$LOG" 2>&1; then
    finish error "Derleme başarısız — ayrıntı günlükte" "$VERSION"; return
  fi
  step 4 "Servisler yeniden başlatılıyor (veritabanı güncelleniyor)"
  docker compose up -d >> "$LOG" 2>&1
  step 5 "Sistemin açılması bekleniyor"
  for i in $(seq 1 30); do
    docker compose exec -T web python -c "import urllib.request as u,urllib.error as e;exec('try:u.urlopen(\"http://127.0.0.1:8000/\",timeout=3)\nexcept e.HTTPError:pass')" >/dev/null 2>&1 && break
    sleep 3
  done
  finish success "Güncelleme tamamlandı" "$VERSION"
}

# Bir dakika boyunca 3 sn'de bir talep kontrol et (cron dakikalık olduğu için bekleme kısa olur)
for i in $(seq 1 19); do
  if [ -f "$REQ" ] || compgen -G "$U/pending/*.zip" >/dev/null; then run; fi
  sleep 3
done
