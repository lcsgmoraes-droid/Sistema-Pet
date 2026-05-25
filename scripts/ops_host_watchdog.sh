#!/usr/bin/env bash
set -Eeuo pipefail

APP_DIR="${APP_DIR:-/opt/petshop}"
COMPOSE_FILE="${COMPOSE_FILE:-docker-compose.prod.yml}"
PUBLIC_WATCHDOG_URL="${HOST_WATCHDOG_URL:-https://mlprohub.com.br/api/health/watchdog}"
INTERNAL_WATCHDOG_URL="${HOST_WATCHDOG_INTERNAL_URL:-http://127.0.0.1:8000/health/watchdog}"
STATE_DIR="${HOST_WATCHDOG_STATE_DIR:-/var/lib/petshop-ops}"
STATE_FILE="${HOST_WATCHDOG_STATE_FILE:-$STATE_DIR/host_watchdog.state}"
EVENT_LOG_PATH="${HOST_WATCHDOG_EVENT_LOG_PATH:-$APP_DIR/backend/logs/host_watchdog_events.jsonl}"
LOCK_FILE="${HOST_WATCHDOG_LOCK_FILE:-/tmp/petshop-ops-host-watchdog.lock}"
DEPLOY_LOCK_FILE="${HOST_WATCHDOG_DEPLOY_LOCK_FILE:-/tmp/petshop-deploy-in-progress}"

HTTP_TIMEOUT_SECONDS="${HOST_WATCHDOG_HTTP_TIMEOUT_SECONDS:-8}"
FAILURE_THRESHOLD="${HOST_WATCHDOG_FAILURE_THRESHOLD:-3}"
RESTART_COOLDOWN_SECONDS="${HOST_WATCHDOG_RESTART_COOLDOWN_SECONDS:-300}"
RESTART_WINDOW_SECONDS="${HOST_WATCHDOG_RESTART_WINDOW_SECONDS:-1800}"
MAX_RESTARTS_PER_WINDOW="${HOST_WATCHDOG_MAX_RESTARTS_PER_WINDOW:-3}"
NGINX_5XX_WINDOW_SECONDS="${HOST_WATCHDOG_NGINX_5XX_WINDOW_SECONDS:-120}"
NGINX_5XX_THRESHOLD="${HOST_WATCHDOG_NGINX_5XX_THRESHOLD:-5}"
LOG_HEALTHY="${HOST_WATCHDOG_LOG_HEALTHY:-false}"

log() {
  printf '[%s] %s\n' "$(date '+%Y-%m-%d %H:%M:%S')" "$*"
}

json_event() {
  local status="$1"
  local message="$2"
  local actions="${3:-}"
  mkdir -p "$(dirname "$EVENT_LOG_PATH")"

  HOST_WATCHDOG_EVENT_LOG_PATH="$EVENT_LOG_PATH" \
  HOST_WATCHDOG_STATUS="$status" \
  HOST_WATCHDOG_MESSAGE="$message" \
  HOST_WATCHDOG_ACTIONS="$actions" \
  HOST_WATCHDOG_PUBLIC_URL="$PUBLIC_WATCHDOG_URL" \
  HOST_WATCHDOG_BACKEND_HEALTH="${backend_health:-unknown}" \
  HOST_WATCHDOG_NGINX_HEALTH="${nginx_health:-unknown}" \
  HOST_WATCHDOG_WORKER_HEALTH="${worker_health:-unknown}" \
  HOST_WATCHDOG_POSTGRES_HEALTH="${postgres_health:-unknown}" \
  HOST_WATCHDOG_PUBLIC_OK="${public_ok:-unknown}" \
  HOST_WATCHDOG_INTERNAL_OK="${internal_ok:-unknown}" \
  HOST_WATCHDOG_NGINX_5XX_COUNT="${nginx_5xx_count:-0}" \
  HOST_WATCHDOG_FAILURES="${failures:-0}" \
  python3 - <<'PY'
import datetime
import json
import os

path = os.environ["HOST_WATCHDOG_EVENT_LOG_PATH"]
actions = [item for item in os.environ.get("HOST_WATCHDOG_ACTIONS", "").split(",") if item]
event = {
    "created_at": datetime.datetime.now(datetime.UTC).isoformat().replace("+00:00", "Z"),
    "status": os.environ.get("HOST_WATCHDOG_STATUS"),
    "message": os.environ.get("HOST_WATCHDOG_MESSAGE") or None,
    "actions": actions,
    "public_url": os.environ.get("HOST_WATCHDOG_PUBLIC_URL"),
    "backend_health": os.environ.get("HOST_WATCHDOG_BACKEND_HEALTH"),
    "nginx_health": os.environ.get("HOST_WATCHDOG_NGINX_HEALTH"),
    "worker_health": os.environ.get("HOST_WATCHDOG_WORKER_HEALTH"),
    "postgres_health": os.environ.get("HOST_WATCHDOG_POSTGRES_HEALTH"),
    "public_ok": os.environ.get("HOST_WATCHDOG_PUBLIC_OK"),
    "internal_ok": os.environ.get("HOST_WATCHDOG_INTERNAL_OK"),
    "nginx_5xx_count": int(os.environ.get("HOST_WATCHDOG_NGINX_5XX_COUNT") or 0),
    "failures": int(os.environ.get("HOST_WATCHDOG_FAILURES") or 0),
    "hostname": os.uname().nodename if hasattr(os, "uname") else None,
}

with open(path, "a", encoding="utf-8") as file:
    file.write(json.dumps(event, ensure_ascii=False, separators=(",", ":")) + "\n")
PY
}

read_state() {
  failures=0
  last_action_at=0
  restart_times_csv=""
  if [[ -f "$STATE_FILE" ]]; then
    # shellcheck disable=SC1090
    source "$STATE_FILE"
    failures="${HOST_WATCHDOG_FAILURES:-0}"
    last_action_at="${HOST_WATCHDOG_LAST_ACTION_AT:-0}"
    restart_times_csv="${HOST_WATCHDOG_RESTART_TIMES:-}"
  fi
}

write_state() {
  mkdir -p "$STATE_DIR"
  cat >"$STATE_FILE" <<STATE
HOST_WATCHDOG_FAILURES=$failures
HOST_WATCHDOG_LAST_ACTION_AT=$last_action_at
HOST_WATCHDOG_RESTART_TIMES="$restart_times_csv"
STATE
}

compose() {
  docker compose -f "$COMPOSE_FILE" "$@"
}

container_health() {
  local name="$1"
  docker inspect -f '{{if .State.Health}}{{.State.Health.Status}}{{else}}{{.State.Status}}{{end}}' "$name" 2>/dev/null || echo "missing"
}

curl_ok() {
  local url="$1"
  curl -fsS --max-time "$HTTP_TIMEOUT_SECONDS" "$url" >/tmp/petshop-host-watchdog-curl.out 2>/tmp/petshop-host-watchdog-curl.err
}

internal_watchdog_ok() {
  compose exec -T backend curl -fsS --max-time "$HTTP_TIMEOUT_SECONDS" "$INTERNAL_WATCHDOG_URL" >/tmp/petshop-host-watchdog-internal.out 2>/tmp/petshop-host-watchdog-internal.err
}

restart_count_in_window=0

prune_restart_times() {
  local now="$1"
  local kept=()
  local item
  IFS=',' read -r -a current_restarts <<<"$restart_times_csv"
  for item in "${current_restarts[@]}"; do
    [[ -n "$item" ]] || continue
    if (( now - item <= RESTART_WINDOW_SECONDS )); then
      kept+=("$item")
    fi
  done
  restart_times_csv="$(IFS=,; echo "${kept[*]}")"
  restart_count_in_window="${#kept[@]}"
}

append_restart_time() {
  local now="$1"
  if [[ -n "$restart_times_csv" ]]; then
    restart_times_csv="$restart_times_csv,$now"
  else
    restart_times_csv="$now"
  fi
}

if [[ -f "$DEPLOY_LOCK_FILE" ]]; then
  log "Deploy em andamento; host watchdog pulado"
  exit 0
fi

if command -v flock >/dev/null 2>&1; then
  exec 9>"$LOCK_FILE"
  flock -n 9 || exit 0
fi

if [[ ! -d "$APP_DIR" ]]; then
  log "APP_DIR inexistente: $APP_DIR"
  exit 0
fi

if ! command -v docker >/dev/null 2>&1 || ! command -v curl >/dev/null 2>&1 || ! command -v python3 >/dev/null 2>&1; then
  log "Dependencias ausentes; host watchdog pulado"
  exit 0
fi

cd "$APP_DIR"
read_state

backend_health="$(container_health petshop-prod-backend)"
nginx_health="$(container_health petshop-prod-nginx)"
worker_health="$(container_health petshop-prod-worker-bling)"
postgres_health="$(container_health petshop-prod-postgres)"

public_ok=false
if curl_ok "$PUBLIC_WATCHDOG_URL"; then
  public_ok=true
fi

internal_ok=false
if [[ "$backend_health" == "healthy" || "$backend_health" == "running" ]]; then
  if internal_watchdog_ok; then
    internal_ok=true
  fi
fi

nginx_5xx_count="$(
  { docker logs --since "${NGINX_5XX_WINDOW_SECONDS}s" petshop-prod-nginx 2>&1 || true; } \
    | awk 'match($0, /" 50[0-9] /) {count++} END {print count + 0}'
)"

healthy=true
reasons=()

if [[ "$backend_health" != "healthy" ]]; then
  healthy=false
  reasons+=("backend_${backend_health}")
fi
if [[ "$nginx_health" != "healthy" ]]; then
  healthy=false
  reasons+=("nginx_${nginx_health}")
fi
if [[ "$worker_health" != "healthy" ]]; then
  healthy=false
  reasons+=("worker_${worker_health}")
fi
if [[ "$postgres_health" != "healthy" ]]; then
  healthy=false
  reasons+=("postgres_${postgres_health}")
fi
if [[ "$public_ok" != "true" ]]; then
  healthy=false
  reasons+=("public_watchdog_failed")
fi
if [[ "$internal_ok" != "true" ]]; then
  healthy=false
  reasons+=("internal_watchdog_failed")
fi
if (( nginx_5xx_count >= NGINX_5XX_THRESHOLD )); then
  healthy=false
  reasons+=("nginx_5xx_${nginx_5xx_count}")
fi

if [[ "$healthy" == "true" ]]; then
  if (( failures > 0 )) || [[ "$LOG_HEALTHY" == "true" ]]; then
    json_event "healthy" "Health recuperado/normal"
  fi
  failures=0
  write_state
  log "Health ok"
  exit 0
fi

failures=$((failures + 1))
reason_text="$(IFS=,; echo "${reasons[*]}")"

if (( failures < FAILURE_THRESHOLD )); then
  json_event "warning" "Falha detectada (${failures}/${FAILURE_THRESHOLD}): $reason_text"
  write_state
  log "Falha detectada (${failures}/${FAILURE_THRESHOLD}): $reason_text"
  exit 0
fi

now="$(date +%s)"
prune_restart_times "$now"
restart_count="$restart_count_in_window"

if (( now - last_action_at < RESTART_COOLDOWN_SECONDS )); then
  json_event "cooldown" "Falha persiste, mas restart em cooldown: $reason_text"
  write_state
  log "Cooldown ativo; sem restart"
  exit 0
fi

if (( restart_count >= MAX_RESTARTS_PER_WINDOW )); then
  json_event "restart_loop_guard" "Limite de restarts atingido; aguardando acao humana: $reason_text"
  write_state
  log "Limite de restarts atingido; sem nova acao"
  exit 0
fi

actions=()

if [[ "$postgres_health" != "healthy" ]]; then
  actions+=("postgres_unhealthy_no_auto_restart")
else
  if [[ "$backend_health" != "healthy" || "$public_ok" != "true" || "$internal_ok" != "true" || "$nginx_5xx_count" -ge "$NGINX_5XX_THRESHOLD" ]]; then
    log "Reiniciando backend por falha: $reason_text"
    compose restart backend
    actions+=("restart_backend")
    sleep 20
  fi

  if ! curl_ok "$PUBLIC_WATCHDOG_URL" || [[ "$nginx_health" != "healthy" || "$nginx_5xx_count" -ge "$NGINX_5XX_THRESHOLD" ]]; then
    log "Reiniciando nginx por falha publica/nginx"
    compose restart nginx
    actions+=("restart_nginx")
  fi

  if [[ "$worker_health" != "healthy" ]]; then
    log "Reiniciando worker-bling por health ruim"
    compose restart worker-bling
    actions+=("restart_worker_bling")
  fi
fi

last_action_at="$now"
append_restart_time "$now"
failures=0
write_state

json_event "recovery_action" "Acoes automaticas executadas por falha: $reason_text" "$(IFS=,; echo "${actions[*]}")"
log "Acoes executadas: $(IFS=,; echo "${actions[*]}")"
