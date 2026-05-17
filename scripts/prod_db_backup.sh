#!/usr/bin/env bash
set -Eeuo pipefail

APP_DIR="${APP_DIR:-/opt/petshop}"
COMPOSE_FILE="${COMPOSE_FILE:-docker-compose.prod.yml}"
POSTGRES_SERVICE="${POSTGRES_SERVICE:-postgres}"
POSTGRES_DB="${POSTGRES_DB:-petshop_prod}"
POSTGRES_USER="${POSTGRES_USER:-petshop_admin}"
BACKUP_DIR="${BACKUP_DIR:-$APP_DIR/backups/db}"
BACKUP_RETENTION_DAYS="${BACKUP_RETENTION_DAYS:-14}"
TIMESTAMP="$(date '+%Y%m%d_%H%M%S')"
BACKUP_NAME="${BACKUP_NAME:-petshop_prod_$TIMESTAMP}"

fail() {
  printf 'backup_status=failed\n' >&2
  printf 'backup_error=%s\n' "$*" >&2
  exit 1
}

require_cmd() {
  command -v "$1" >/dev/null 2>&1 || fail "missing command: $1"
}

case "$BACKUP_NAME" in
  ""|*[!a-zA-Z0-9_.-]*)
    fail "invalid BACKUP_NAME; use only letters, numbers, dot, dash and underscore"
    ;;
esac

require_cmd docker
require_cmd gzip
require_cmd sha256sum

cd "$APP_DIR"
mkdir -p "$BACKUP_DIR"
chmod 700 "$BACKUP_DIR" || true

tmp_file="$BACKUP_DIR/${BACKUP_NAME}.dump.gz.tmp"
backup_file="$BACKUP_DIR/${BACKUP_NAME}.dump.gz"
checksum_file="$backup_file.sha256"

cleanup_tmp() {
  rm -f "$tmp_file" 2>/dev/null || true
}

trap cleanup_tmp EXIT

if [[ -e "$backup_file" ]]; then
  fail "backup already exists: $backup_file"
fi

docker compose -f "$COMPOSE_FILE" ps "$POSTGRES_SERVICE" >/dev/null

docker compose -f "$COMPOSE_FILE" exec -T "$POSTGRES_SERVICE" \
  pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" -F c \
  | gzip -c >"$tmp_file"

if [[ ! -s "$tmp_file" ]]; then
  fail "backup file was not created or is empty"
fi

chmod 600 "$tmp_file" || true
mv "$tmp_file" "$backup_file"
sha256sum "$backup_file" | awk '{print $1}' >"$checksum_file"
chmod 600 "$checksum_file" || true

if [[ "$BACKUP_RETENTION_DAYS" =~ ^[0-9]+$ && "$BACKUP_RETENTION_DAYS" -gt 0 ]]; then
  find "$BACKUP_DIR" -type f -name '*.dump.gz' -mtime +"$BACKUP_RETENTION_DAYS" -delete
  find "$BACKUP_DIR" -type f -name '*.dump.gz.sha256' -mtime +"$BACKUP_RETENTION_DAYS" -delete
fi

backup_bytes="$(wc -c <"$backup_file" | tr -d '[:space:]')"
backup_sha256="$(cat "$checksum_file")"

printf 'backup_status=ok\n'
printf 'backup_file=%s\n' "$backup_file"
printf 'backup_bytes=%s\n' "$backup_bytes"
printf 'backup_sha256=%s\n' "$backup_sha256"
