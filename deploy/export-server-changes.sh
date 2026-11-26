#!/usr/bin/env bash
# Eglo ERP — sunucudaki (ZIP paketleriyle güncellenmiş) kaynak kodu GitHub'a güvenle aktarır.
#
# Kullanım (sunucuda, root):
#   curl -fsSL https://raw.githubusercontent.com/infoclerie/Eglo/main/deploy/export-server-changes.sh | sudo bash
#   # yalnız arşiv üretmek için (GitHub'a göndermez):  ... | sudo MODE=arsiv bash
#
# Ne yapar:
#   1. /opt/eglo-erp içindeki git'e göre değişmiş / yeni / silinmiş dosyaları bulur.
#   2. Gizli ve müşteri verisi içerebilecek her şeyi ELER: .env*, veritabanı/yedek/döküm dosyaları,
#      media/, backups*/, updates/, staticfiles/, sertifika/anahtar dosyaları, zip/tar, csv/xlsx, loglar,
#      docker-compose.override.yml, 5 MB üzeri dosyalar.
#   3. Kalan dosyalarda şifre/anahtar taraması yapar; şüpheli satır varsa gösterir ve onay ister.
#   4. Sunucudaki çalışan kopyaya DOKUNMAZ: geçici bir klonda "sunucu-aktarim-<tarih>" dalı oluşturur,
#      (MODE=push) GitHub'a bu dala gönderir veya (MODE=arsiv) /root altına .tar.gz bırakır.
#      main dalına doğrudan yazmaz; birleştirme inceleme sonrası yapılır.
set -euo pipefail

PROJECT_DIR="${PROJECT_DIR:-/opt/eglo-erp}"
REMOTE_URL="${REMOTE_URL:-https://github.com/infoclerie/Eglo.git}"
MODE="${MODE:-push}"                       # push | arsiv
STAMP="$(date +%Y%m%d-%H%M)"
BRANCH="${BRANCH:-sunucu-aktarim-$STAMP}"
MAX_BYTES=$((5 * 1024 * 1024))

TTY=/dev/tty
ask() {  # ask "<soru>" -> 0 evet / 1 hayır
  local a=""
  if [ -r "$TTY" ]; then read -r -p "$1 [e/H]: " a < "$TTY" || true; fi
  [[ "$a" =~ ^[eEyY]$ ]]
}

[ -d "$PROJECT_DIR/.git" ] || { echo "HATA: $PROJECT_DIR bir git deposu değil."; exit 1; }
git config --global --add safe.directory "$PROJECT_DIR" 2>/dev/null || true
cd "$PROJECT_DIR"

WORK="$(mktemp -d)"
trap 'rm -rf "$WORK"' EXIT
REPORT="$WORK/rapor.txt"
: > "$REPORT"
r() { echo "$*" | tee -a "$REPORT"; }

BASE="$(git rev-parse HEAD)"
r "== Eglo sunucu aktarımı $STAMP =="
r "Proje: $PROJECT_DIR"
r "Sunucu HEAD: $BASE  ($(git log -1 --format='%ad · %s' --date=format:'%d.%m.%Y %H:%M'))"
r ""

# --- Yasaklı yollar (gizli bilgi / müşteri verisi / üretilen dosyalar) ---
is_blocked() {
  local p="$1" b; b="$(basename "$p")"
  case "$p" in
    .git/*|.venv/*|venv/*|*/__pycache__/*|__pycache__/*|node_modules/*) return 0 ;;
    media/*|*/media/*|backups/*|backups_app/*|*/backups/*|updates/*|staticfiles/*|data/*|pgdata/*|postgres-data/*) return 0 ;;
  esac
  case "$b" in
    .env.example) return 1 ;;
    .env|.env.*|*.env|docker-compose.override.yml|docker-compose.override.yaml) return 0 ;;
    *.sqlite3|*.sqlite|*.db|*.sql|*.sql.gz|*.dump|*.bak|*.backup) return 0 ;;
    *.zip|*.tar|*.tar.gz|*.tgz|*.gz|*.7z|*.rar) return 0 ;;
    *.pem|*.key|*.p12|*.pfx|*.crt|*.cer|*.jks|*.keystore|id_rsa*|id_ed25519*|*.ppk) return 0 ;;
    *.csv|*.xls|*.xlsx|*.ods|*.log|*.pyc|*.swp|*~) return 0 ;;
    request.json|progress.json|status.json|celerybeat-schedule*) return 0 ;;
  esac
  return 1
}

# --- Değişiklikleri topla (.gitignore zaten updates/, .env, media, yedekleri dışarıda bırakır) ---
INCLUDED="$WORK/dahil.txt"; EXCLUDED="$WORK/haric.txt"; DELETED="$WORK/silinen.txt"
: > "$INCLUDED"; : > "$EXCLUDED"; : > "$DELETED"
while IFS= read -r -d '' entry; do
  st="${entry:0:2}"; path="${entry:3}"
  if [[ "$st" == R* || "$st" == C* ]]; then IFS= read -r -d '' _old || true; fi
  if [[ "$st" == *D* ]]; then
    is_blocked "$path" || echo "$path" >> "$DELETED"; continue
  fi
  if [ -d "$path" ]; then continue; fi
  if is_blocked "$path"; then echo "$path  (güvenlik kuralı)" >> "$EXCLUDED"; continue; fi
  if [ -L "$path" ]; then echo "$path  (sembolik bağ)" >> "$EXCLUDED"; continue; fi
  if [ "$(stat -c %s "$path")" -gt "$MAX_BYTES" ]; then echo "$path  (5 MB üstü)" >> "$EXCLUDED"; continue; fi
  echo "$path" >> "$INCLUDED"
done < <(git status --porcelain=v1 -z --untracked-files=all)

r "Aktarılacak dosya : $(wc -l < "$INCLUDED")"
r "Silinecek dosya   : $(wc -l < "$DELETED")"
r "Dışarıda bırakılan: $(wc -l < "$EXCLUDED")"
if [ -s "$EXCLUDED" ]; then r "-- Dışarıda bırakılanlar (GitHub'a GİTMEZ):"; sed 's/^/   /' "$EXCLUDED" | tee -a "$REPORT"; fi

STASHES="$(git stash list | wc -l)"
if [ "$STASHES" -gt 0 ]; then
  r ""
  r "UYARI: $STASHES adet git stash var (auto-update 'GitHub'dan güncelle' öncesi yerel değişiklikleri buraya alır):"
  git stash list | sed 's/^/   /' | tee -a "$REPORT"
  r "   Bunlar otomatik aktarılmaz; içerikleri arşive (stash-*.patch) yazılır."
fi
if [ -d updates/applied ]; then
  r ""; r "Uygulanmış ZIP paketleri (bilgi):"; ls -1 updates/applied 2>/dev/null | sed 's/^/   /' | tee -a "$REPORT" || true
fi

if [ ! -s "$INCLUDED" ] && [ ! -s "$DELETED" ]; then
  r ""; r "Sunucuda git'e göre kod değişikliği yok — aktarılacak bir şey bulunamadı."
  [ "$STASHES" -gt 0 ] || exit 0
fi

# --- Geçici klonda dal oluştur (çalışan sisteme dokunulmaz) ---
git clone -q --no-hardlinks "$PROJECT_DIR" "$WORK/repo"
git -C "$WORK/repo" checkout -q -b "$BRANCH" "$BASE"
while IFS= read -r f; do
  mkdir -p "$WORK/repo/$(dirname "$f")"; cp -p "$f" "$WORK/repo/$f"
done < "$INCLUDED"
while IFS= read -r f; do git -C "$WORK/repo" rm -q --ignore-unmatch -- "$f"; done < "$DELETED"
git -C "$WORK/repo" add -A
mkdir -p "$WORK/stash"
for i in $(seq 0 $((STASHES - 1))); do git stash show -p --include-untracked "stash@{$i}" > "$WORK/stash/stash-$i.patch" 2>/dev/null || git stash show -p "stash@{$i}" > "$WORK/stash/stash-$i.patch"; done

# --- Gizli bilgi taraması (yalnız aktarılacak içerikte) ---
SCAN="$WORK/tarama.txt"
PATTERN='-----BEGIN [A-Z ]*PRIVATE KEY|AKIA[0-9A-Z]{16}|ghp_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{30,}|sk-[A-Za-z0-9_-]{20,}|xox[abpr]-[A-Za-z0-9-]{10,}|AIza[0-9A-Za-z_-]{35}|(password|passwd|parola|sifre|şifre|secret|api_?key|apikey|token|client_secret)["'"'"']?[[:space:]]*[:=][[:space:]]*["'"'"'][^"'"'"'[:space:]]{6,}["'"'"']'
( cd "$WORK/repo" && git diff --cached --name-only -z --diff-filter=AM | xargs -0 -r grep -nIiE -- "$PATTERN" 2>/dev/null ) \
  | sed -E 's/(["'"'"'])[^"'"'"']{3}[^"'"'"']*(["'"'"'])/\1***\2/g' > "$SCAN" || true
cat "$SCAN" "$WORK"/stash/*.patch 2>/dev/null | grep -nIiE -- "$PATTERN" >/dev/null 2>&1 && STASH_SECRET=1 || STASH_SECRET=0

r ""
if [ -s "$SCAN" ]; then
  r "!! ŞÜPHELİ SATIRLAR (değerler maskelendi) — gerçek şifre/anahtar olmadığından emin olun:"
  sed 's/^/   /' "$SCAN" | tee -a "$REPORT"
  ask "Bunlar gerçek şifre DEĞİL, devam edilsin mi?" || { echo "İptal edildi. Hiçbir şey gönderilmedi."; exit 1; }
else
  r "Gizli bilgi taraması: şüpheli satır bulunmadı."
fi

git -C "$WORK/repo" -c user.name="Eglo Sunucu" -c user.email="sunucu@eglo.invalid" \
  commit -q -m "Sunucudaki ZIP güncellemeleriyle gelen kod ($STAMP, taban ${BASE:0:7})" || true
r ""; r "Oluşan commit:"; git -C "$WORK/repo" show --stat --format='%h %s' HEAD | tee -a "$REPORT"

ARCHIVE="/root/eglo-aktarim-$STAMP.tar.gz"
make_archive() {
  git -C "$WORK/repo" bundle create "$WORK/aktarim.bundle" "$BASE..$BRANCH" 2>/dev/null || true
  local items=(rapor.txt dahil.txt haric.txt silinen.txt stash)
  [ -s "$WORK/aktarim.bundle" ] && items+=(aktarim.bundle)
  tar -czf "$ARCHIVE" -C "$WORK" "${items[@]}"
  chmod 600 "$ARCHIVE"
  echo; echo "Arşiv: $ARCHIVE  (yalnız kod; .env/veritabanı/müşteri verisi içermez)"
}

if [ "$MODE" = "arsiv" ]; then make_archive; exit 0; fi

echo
echo "GitHub'a '$BRANCH' dalı olarak gönderilecek (main değişmez). Depo HERKESE AÇIK."
ask "Gönderilsin mi?" || { make_archive; echo "Gönderilmedi; arşiv bırakıldı."; exit 0; }

echo "GitHub erişim anahtarı (fine-grained token, yalnız infoclerie/Eglo, Contents: Read and write)."
echo "Anahtar ekranda görünmez ve hiçbir yere kaydedilmez."
GT=""; read -r -s -p "Token: " GT < "$TTY" || true; echo
[ -n "$GT" ] || { make_archive; echo "Token girilmedi; arşiv bırakıldı."; exit 0; }
printf '#!/bin/sh\ncase "$1" in *sername*) echo x-access-token;; *) echo "$EGLO_GT";; esac\n' > "$WORK/askpass"
chmod 700 "$WORK/askpass"
if EGLO_GT="$GT" GIT_ASKPASS="$WORK/askpass" GIT_TERMINAL_PROMPT=0 \
     git -C "$WORK/repo" -c credential.helper= push "$REMOTE_URL" "$BRANCH:refs/heads/$BRANCH"; then
  unset GT
  [ "$STASHES" -gt 0 ] && make_archive
  echo; echo "✅ Gönderildi: dal '$BRANCH'. Claude'a bu dal adını söyleyin; inceleyip main'e birleştirecek."
  [ "$STASH_SECRET" = 1 ] && echo "Not: stash yamalarında şüpheli satır var; arşivi paylaşmadan önce kontrol edin."
else
  unset GT; make_archive; echo "Gönderim başarısız; arşiv bırakıldı."; exit 1
fi
