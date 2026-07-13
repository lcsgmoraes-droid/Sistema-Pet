#!/usr/bin/env bash
set -Eeuo pipefail

APP_DIR="${APP_DIR:-/opt/petshop}"
COMPOSE_FILE="${COMPOSE_FILE:-docker-compose.prod.yml}"
DISK_GUARD_PATH="${DISK_GUARD_PATH:-/}"
DISK_GUARD_WARNING_PERCENT="${DISK_GUARD_WARNING_PERCENT:-85}"
DISK_GUARD_CRITICAL_PERCENT="${DISK_GUARD_CRITICAL_PERCENT:-90}"
DISK_GUARD_LOG_PATH="${DISK_GUARD_LOG_PATH:-$APP_DIR/backend/logs/disk_guard_events.jsonl}"
LOCK_FILE="${DISK_GUARD_LOCK_FILE:-/tmp/petshop-ops-disk-guard.lock}"

log() {
  printf '[%s] %s\n' "$(date '+%Y-%m-%d %H:%M:%S')" "$*"
}

disk_percent() {
  df -P "$DISK_GUARD_PATH" | awk 'NR == 2 {gsub("%", "", $5); print $5}'
}

write_event() {
  local status="$1"
  local before_percent="$2"
  local after_percent="$3"
  local actions="$4"
  local message="${5:-}"

  mkdir -p "$(dirname "$DISK_GUARD_LOG_PATH")"

  DISK_GUARD_EVENT_PATH="$DISK_GUARD_LOG_PATH" \
  DISK_GUARD_STATUS="$status" \
  DISK_GUARD_BEFORE_PERCENT="$before_percent" \
  DISK_GUARD_AFTER_PERCENT="$after_percent" \
  DISK_GUARD_ACTIONS="$actions" \
  DISK_GUARD_MESSAGE="$message" \
  DISK_GUARD_PATH_VALUE="$DISK_GUARD_PATH" \
  DISK_GUARD_WARNING_VALUE="$DISK_GUARD_WARNING_PERCENT" \
  DISK_GUARD_CRITICAL_VALUE="$DISK_GUARD_CRITICAL_PERCENT" \
  python3 - <<'PY'
import datetime
import json
import os

path = os.environ["DISK_GUARD_EVENT_PATH"]
event = {
    "created_at": datetime.datetime.now(datetime.UTC).isoformat().replace("+00:00", "Z"),
    "status": os.environ.get("DISK_GUARD_STATUS"),
    "path": os.environ.get("DISK_GUARD_PATH_VALUE"),
    "before_percent": int(os.environ.get("DISK_GUARD_BEFORE_PERCENT") or 0),
    "after_percent": int(os.environ.get("DISK_GUARD_AFTER_PERCENT") or 0),
    "warning_percent": int(os.environ.get("DISK_GUARD_WARNING_VALUE") or 0),
    "critical_percent": int(os.environ.get("DISK_GUARD_CRITICAL_VALUE") or 0),
    "actions": [item for item in os.environ.get("DISK_GUARD_ACTIONS", "").split(",") if item],
    "message": os.environ.get("DISK_GUARD_MESSAGE") or None,
}

with open(path, "a", encoding="utf-8") as file:
    file.write(json.dumps(event, ensure_ascii=False, separators=(",", ":")) + "\n")
PY
}

if command -v flock >/dev/null 2>&1; then
  exec 9>"$LOCK_FILE"
  flock -n 9 || exit 0
fi

if ! command -v docker >/dev/null 2>&1; then
  log "Docker nao encontrado; disk guard pulado"
  write_event "skipped" "0" "0" "" "Docker nao encontrado"
  exit 0
fi

if ! command -v python3 >/dev/null 2>&1; then
  log "Python3 nao encontrado; disk guard pulado"
  exit 0
fi

before="$(disk_percent)"
actions=()

if [[ "$before" -lt "$DISK_GUARD_WARNING_PERCENT" ]]; then
  write_event "healthy" "$before" "$before" "" "Uso de disco abaixo do limite de risco"
  log "Disco ok: ${before}%"
  exit 0
fi

log "Disco em risco: ${before}%. Limpando cache Docker seguro."

# Remove somente volumes temporarios identificados pelo restore smoke. Volumes
# ativos sao recusados pelo Docker e nunca entram nesta limpeza.
restore_volumes="$(docker volume ls -q --filter label=com.corepet.purpose=restore-smoke)"
if [[ -n "$restore_volumes" ]]; then
  while IFS= read -r volume_name; do
    [[ -n "$volume_name" ]] || continue
    docker volume rm "$volume_name" >/dev/null 2>&1 || true
  done <<<"$restore_volumes"
  actions+=("docker_restore_volume_prune")
fi

docker builder prune -af || true
actions+=("docker_builder_prune")

current="$(disk_percent)"
if [[ "$current" -ge "$DISK_GUARD_CRITICAL_PERCENT" ]]; then
  docker image prune -af || true
  actions+=("docker_image_prune")
fi

after="$(disk_percent)"

status="cleaned"
message="Limpeza preventiva concluida"
if [[ "$after" -ge "$DISK_GUARD_CRITICAL_PERCENT" ]]; then
  status="still_critical"
  message="Disco segue acima do limite critico apos limpeza preventiva"
elif [[ "$after" -ge "$DISK_GUARD_WARNING_PERCENT" ]]; then
  status="still_warning"
  message="Disco segue acima do limite de alerta apos limpeza preventiva"
fi

write_event "$status" "$before" "$after" "$(IFS=,; echo "${actions[*]}")" "$message"
log "$message: ${before}% -> ${after}%"
