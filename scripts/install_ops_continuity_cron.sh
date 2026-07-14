#!/usr/bin/env bash
set -Eeuo pipefail

APP_DIR="${APP_DIR:-/opt/petshop}"
CRON_FILE="${OPS_CONTINUITY_CRON_FILE:-/etc/cron.d/petshop-ops-continuity}"
BACKUP_SCHEDULE="${OPS_BACKUP_CRON_SCHEDULE:-15 3 * * *}"
RESTORE_SCHEDULE="${OPS_RESTORE_CRON_SCHEDULE:-30 4 * * 0}"
EXTERNAL_COPY_SCHEDULE="${OPS_EXTERNAL_COPY_CRON_SCHEDULE:-45 3 * * *}"
EXTERNAL_COPY_CONFIG_FILE="${OPS_EXTERNAL_COPY_CONFIG_FILE:-/etc/petshop/backup-external.env}"
EVENT_LOG_PATH="${OPS_CONTINUITY_EVENT_LOG_PATH:-$APP_DIR/backend/logs/continuity_events.jsonl}"

if [[ "$(id -u)" != "0" ]]; then
  echo "Instalacao do cron exige root. Pulando continuidade operacional." >&2
  exit 0
fi

for required_script in prod_db_backup.sh prod_db_restore_smoke.sh ops_continuity_event.sh; do
  if [[ ! -f "$APP_DIR/scripts/$required_script" ]]; then
    echo "Script nao encontrado: $APP_DIR/scripts/$required_script" >&2
    exit 1
  fi
  chmod +x "$APP_DIR/scripts/$required_script"
done

if [[ -f "$APP_DIR/scripts/prod_db_external_copy.sh" ]]; then
  chmod +x "$APP_DIR/scripts/prod_db_external_copy.sh"
fi

mkdir -p "$APP_DIR/backend/logs" "$APP_DIR/backups/db"
chown 1000:1000 "$APP_DIR/backend/logs" 2>/dev/null || true
chmod 0770 "$APP_DIR/backend/logs" 2>/dev/null || true
chmod 0700 "$APP_DIR/backups/db" 2>/dev/null || true

cat >"$CRON_FILE" <<CRON
SHELL=/bin/bash
PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin

$BACKUP_SCHEDULE root flock -n /tmp/petshop-ops-continuity.lock env APP_DIR=$APP_DIR OPS_CONTINUITY_EVENT_LOG_PATH=$EVENT_LOG_PATH bash $APP_DIR/scripts/prod_db_backup.sh >>$APP_DIR/backend/logs/prod_db_backup.log 2>&1
$RESTORE_SCHEDULE root flock -n /tmp/petshop-ops-continuity.lock env APP_DIR=$APP_DIR OPS_CONTINUITY_EVENT_LOG_PATH=$EVENT_LOG_PATH bash $APP_DIR/scripts/prod_db_restore_smoke.sh >>$APP_DIR/backend/logs/prod_db_restore_smoke.log 2>&1
CRON

if [[ -f "$EXTERNAL_COPY_CONFIG_FILE" && -f "$APP_DIR/scripts/prod_db_external_copy.sh" ]]; then
  cat >>"$CRON_FILE" <<CRON
$EXTERNAL_COPY_SCHEDULE root flock -n /tmp/petshop-ops-continuity.lock env APP_DIR=$APP_DIR OPS_CONTINUITY_EVENT_LOG_PATH=$EVENT_LOG_PATH OPS_EXTERNAL_COPY_CONFIG_FILE=$EXTERNAL_COPY_CONFIG_FILE bash $APP_DIR/scripts/prod_db_external_copy.sh >>$APP_DIR/backend/logs/prod_db_external_copy.log 2>&1
CRON
else
  echo "Copia externa em standby: configuracao segura nao encontrada em $EXTERNAL_COPY_CONFIG_FILE"
fi

chmod 0644 "$CRON_FILE"
echo "Cron de continuidade instalado em $CRON_FILE"
