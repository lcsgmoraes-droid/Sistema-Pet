#!/usr/bin/env bash
set -Eeuo pipefail

APP_DIR="${APP_DIR:-/opt/petshop}"
COMPOSE_FILE="${COMPOSE_FILE:-docker-compose.prod.yml}"
POSTGRES_SERVICE="${POSTGRES_SERVICE:-postgres}"
POSTGRES_DB="${POSTGRES_DB:-petshop_prod}"
POSTGRES_USER="${POSTGRES_USER:-petshop_admin}"
BACKUP_DIR="${BACKUP_DIR:-$APP_DIR/backups/db}"
POSTGRES_RESTORE_IMAGE="${POSTGRES_RESTORE_IMAGE:-postgres:14-alpine}"
RESTORE_DB="${RESTORE_DB:-restore_smoke}"
RESTORE_USER="${RESTORE_USER:-restore_smoke}"
RESTORE_PASSWORD="${RESTORE_PASSWORD:-restore_smoke_password}"
TIMESTAMP="$(date '+%Y%m%d_%H%M%S')"
RESTORE_CONTAINER_NAME="${RESTORE_CONTAINER_NAME:-petshop-restore-smoke-$TIMESTAMP}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# shellcheck source=ops_continuity_event.sh
source "$SCRIPT_DIR/ops_continuity_event.sh"

continuity_event_recorded="false"

record_restore_event() {
  continuity_event_recorded="true"
  record_ops_continuity_event \
    "restore" "$1" "${2:-}" "" "" "${3:-}" "${4:-}"
}

record_unexpected_restore_failure() {
  if [[ "$continuity_event_recorded" != "true" ]]; then
    record_restore_event "failed" "${backup_file:-}" || true
  fi
}

trap record_unexpected_restore_failure ERR

fail() {
  record_restore_event "failed" "${backup_file:-}" || true
  printf 'restore_smoke_status=failed\n' >&2
  printf 'restore_smoke_error=%s\n' "$*" >&2
  exit 1
}

require_cmd() {
  command -v "$1" >/dev/null 2>&1 || fail "missing command: $1"
}

usage() {
  cat <<'EOF'
Usage:
  bash scripts/prod_db_restore_smoke.sh [backup_file.dump.gz]

When no backup file is provided, the script first creates a fresh production
dump with scripts/prod_db_backup.sh, then restores it into a disposable
Postgres container with no published ports.
EOF
}

if [[ "${1:-}" == "-h" || "${1:-}" == "--help" ]]; then
  usage
  exit 0
fi

require_cmd docker
require_cmd gzip

cd "$APP_DIR"

backup_file="${1:-}"
created_backup="false"

if [[ -z "$backup_file" ]]; then
  backup_name="${BACKUP_NAME:-restore_smoke_$TIMESTAMP}"
  backup_output="$(
    APP_DIR="$APP_DIR" \
    COMPOSE_FILE="$COMPOSE_FILE" \
    POSTGRES_SERVICE="$POSTGRES_SERVICE" \
    POSTGRES_DB="$POSTGRES_DB" \
    POSTGRES_USER="$POSTGRES_USER" \
    BACKUP_DIR="$BACKUP_DIR" \
    BACKUP_NAME="$backup_name" \
    bash "$APP_DIR/scripts/prod_db_backup.sh"
  )"
  printf '%s\n' "$backup_output"
  backup_file="$(printf '%s\n' "$backup_output" | awk -F= '/^backup_file=/{print $2}' | tail -n 1)"
  created_backup="true"
fi

case "$backup_file" in
  /*) ;;
  *) backup_file="$APP_DIR/$backup_file" ;;
esac

if [[ ! -s "$backup_file" ]]; then
  fail "backup file not found or empty: $backup_file"
fi

cleanup_container() {
  docker rm -f "$RESTORE_CONTAINER_NAME" >/dev/null 2>&1 || true
}

trap cleanup_container EXIT

docker rm -f "$RESTORE_CONTAINER_NAME" >/dev/null 2>&1 || true

docker run -d --rm \
  --name "$RESTORE_CONTAINER_NAME" \
  -e POSTGRES_DB="$RESTORE_DB" \
  -e POSTGRES_USER="$RESTORE_USER" \
  -e POSTGRES_PASSWORD="$RESTORE_PASSWORD" \
  "$POSTGRES_RESTORE_IMAGE" >/dev/null

ready="false"
for _ in $(seq 1 30); do
  if docker exec "$RESTORE_CONTAINER_NAME" pg_isready -U "$RESTORE_USER" -d "$RESTORE_DB" >/dev/null 2>&1; then
    ready="true"
    break
  fi
  sleep 2
done

if [[ "$ready" != "true" ]]; then
  fail "temporary restore Postgres did not become ready"
fi

gzip -dc "$backup_file" | docker exec -i "$RESTORE_CONTAINER_NAME" \
  pg_restore -U "$RESTORE_USER" -d "$RESTORE_DB" --no-owner --no-acl

public_tables="$(
  docker exec "$RESTORE_CONTAINER_NAME" psql -U "$RESTORE_USER" -d "$RESTORE_DB" -tAc \
    "select count(*) from information_schema.tables where table_schema = 'public';" \
    | tr -d '[:space:]'
)"

alembic_rows="$(
  docker exec "$RESTORE_CONTAINER_NAME" psql -U "$RESTORE_USER" -d "$RESTORE_DB" -tAc \
    "select count(*) from alembic_version;" \
    | tr -d '[:space:]'
)"

if [[ -z "$public_tables" || "$public_tables" -lt 1 ]]; then
  fail "restore completed but no public tables were found"
fi

if [[ -z "$alembic_rows" || "$alembic_rows" -lt 1 ]]; then
  fail "restore completed but alembic_version was not found"
fi

record_restore_event "ok" "$backup_file" "$public_tables" "$alembic_rows"

printf 'restore_smoke_status=ok\n'
printf 'backup_file=%s\n' "$backup_file"
printf 'created_backup=%s\n' "$created_backup"
printf 'public_tables=%s\n' "$public_tables"
printf 'alembic_rows=%s\n' "$alembic_rows"
printf 'restore_container_removed=true\n'
