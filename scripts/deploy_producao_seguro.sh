#!/usr/bin/env bash
set -Eeuo pipefail

APP_DIR="${APP_DIR:-/opt/petshop}"
REMOTE="${REMOTE:-origin}"
BRANCH="${BRANCH:-main}"
COMPOSE_FILE="${COMPOSE_FILE:-docker-compose.prod.yml}"
RUNTIME_DIST="${RUNTIME_DIST:-runtime/frontend/dist}"
NEXT_RUNTIME_DIST="${NEXT_RUNTIME_DIST:-${RUNTIME_DIST}.next}"
PREV_RUNTIME_DIST="${PREV_RUNTIME_DIST:-${RUNTIME_DIST}.prev}"
PUBLIC_HEALTH_URL="${PUBLIC_HEALTH_URL:-https://mlprohub.com.br/api/health}"
DEPLOY_EVENTS_PATH="${DEPLOY_EVENTS_PATH:-backend/logs/deploy_events.jsonl}"
DEPLOY_STARTED_AT="$(date -u '+%Y-%m-%dT%H:%M:%SZ')"
CURRENT_STEP="inicio"
DEPLOY_EVENT_RECORDED=0
HEAD_BEFORE=""
HEAD_AFTER=""
backup_dir=""
DEPLOY_LOCK_FILE="${DEPLOY_LOCK_FILE:-/tmp/petshop-deploy-in-progress}"

log() {
  printf '\n[%s] %s\n' "$(date '+%Y-%m-%d %H:%M:%S')" "$*"
}

fail() {
  printf '\nERRO: %s\n' "$*" >&2
  write_deploy_event "failed" "$CURRENT_STEP" "$*" || true
  exit 1
}

require_cmd() {
  command -v "$1" >/dev/null 2>&1 || fail "Comando obrigatorio nao encontrado: $1"
}

mark_step() {
  CURRENT_STEP="$1"
}

write_deploy_event() {
  local status="$1"
  local step="${2:-$CURRENT_STEP}"
  local message="${3:-}"
  local event_path="$APP_DIR/$DEPLOY_EVENTS_PATH"

  mkdir -p "$(dirname "$event_path")"

  DEPLOY_EVENT_PATH="$event_path" \
  DEPLOY_STATUS="$status" \
  DEPLOY_STEP="$step" \
  DEPLOY_MESSAGE="$message" \
  DEPLOY_STARTED_AT_VALUE="$DEPLOY_STARTED_AT" \
  DEPLOY_REMOTE="$REMOTE" \
  DEPLOY_BRANCH="$BRANCH" \
  DEPLOY_HEAD_BEFORE="$HEAD_BEFORE" \
  DEPLOY_HEAD_AFTER="$HEAD_AFTER" \
  DEPLOY_RUNTIME_DIST="$RUNTIME_DIST" \
  DEPLOY_PUBLIC_HEALTH_URL="$PUBLIC_HEALTH_URL" \
  DEPLOY_BACKUP_DIR="$backup_dir" \
  DEPLOY_USER_VALUE="${USER:-unknown}" \
  DEPLOY_HOSTNAME_VALUE="$(hostname 2>/dev/null || echo unknown)" \
  python3 - <<'PY'
import datetime
import json
import os

path = os.environ["DEPLOY_EVENT_PATH"]
event = {
    "created_at": datetime.datetime.now(datetime.UTC).isoformat().replace("+00:00", "Z"),
    "started_at": os.environ.get("DEPLOY_STARTED_AT_VALUE"),
    "status": os.environ.get("DEPLOY_STATUS"),
    "step": os.environ.get("DEPLOY_STEP"),
    "message": os.environ.get("DEPLOY_MESSAGE") or None,
    "remote": os.environ.get("DEPLOY_REMOTE"),
    "branch": os.environ.get("DEPLOY_BRANCH"),
    "head_before": os.environ.get("DEPLOY_HEAD_BEFORE") or None,
    "head_after": os.environ.get("DEPLOY_HEAD_AFTER") or None,
    "runtime_dist": os.environ.get("DEPLOY_RUNTIME_DIST"),
    "public_health_url": os.environ.get("DEPLOY_PUBLIC_HEALTH_URL"),
    "backup_dir": os.environ.get("DEPLOY_BACKUP_DIR") or None,
    "user": os.environ.get("DEPLOY_USER_VALUE"),
    "hostname": os.environ.get("DEPLOY_HOSTNAME_VALUE"),
}

with open(path, "a", encoding="utf-8") as file:
    file.write(json.dumps(event, ensure_ascii=False, separators=(",", ":")) + "\n")
PY

  if [[ "$status" == "success" || "$status" == "failed" ]]; then
    DEPLOY_EVENT_RECORDED=1
  fi
}

audit_step() {
  local message="${1:-Etapa iniciada: $CURRENT_STEP}"
  write_deploy_event "running" "$CURRENT_STEP" "$message" || log "Aviso: nao foi possivel auditar etapa $CURRENT_STEP"
}

on_error() {
  local exit_code=$?
  local line="${1:-unknown}"
  if [[ "$DEPLOY_EVENT_RECORDED" != "1" ]]; then
    write_deploy_event "failed" "$CURRENT_STEP" "Falha inesperada na linha ${line}; exit ${exit_code}" || true
  fi
  exit "$exit_code"
}

trap 'on_error $LINENO' ERR

cleanup_deploy_lock() {
  rm -f "$DEPLOY_LOCK_FILE" 2>/dev/null || true
}

trap cleanup_deploy_lock EXIT

wait_for() {
  local label="$1"
  local command="$2"
  local attempts="${3:-24}"
  local delay="${4:-5}"

  for attempt in $(seq 1 "$attempts"); do
    if bash -lc "$command" >/tmp/petshop-deploy-check.out 2>/tmp/petshop-deploy-check.err; then
      cat /tmp/petshop-deploy-check.out
      return 0
    fi

    printf 'Aguardando %s (%s/%s)...\n' "$label" "$attempt" "$attempts"
    sleep "$delay"
  done

  cat /tmp/petshop-deploy-check.err >&2 || true
  fail "Timeout aguardando $label"
}

require_cmd git
require_cmd docker
require_cmd npm
require_cmd curl
require_cmd python3

cd "$APP_DIR"
touch "$DEPLOY_LOCK_FILE" || true

mark_step "validar_repositorio"
audit_step "Validando repositorio de producao antes do deploy"
log "Validando repositorio limpo"
if [[ -n "$(git status --porcelain)" ]]; then
  git status --short
  fail "Repositorio de producao com alteracoes locais. Corrija antes do deploy."
fi

tracked_dist_count="$(git ls-files frontend/dist runtime | wc -l | tr -d ' ')"
if [[ "$tracked_dist_count" != "0" ]]; then
  git ls-files frontend/dist runtime
  fail "Artefatos gerados nao podem estar versionados."
fi

backup_dir="$APP_DIR/backups/deploy_$(date '+%Y%m%d_%H%M%S')"
mkdir -p "$backup_dir"
db_backup_dir="$APP_DIR/backups/db"
mkdir -p "$db_backup_dir"
if getent group docker >/dev/null 2>&1; then
  chgrp docker "$APP_DIR/backups" "$db_backup_dir" || true
  chmod 770 "$APP_DIR/backups" "$db_backup_dir" || true
fi
HEAD_BEFORE="$(git rev-parse HEAD)"
printf '%s\n' "$HEAD_BEFORE" >"$backup_dir/head_before.txt"
docker compose -f "$COMPOSE_FILE" ps >"$backup_dir/docker_ps_before.txt" || true

mark_step "atualizar_codigo"
audit_step "Atualizando codigo em producao"
log "Atualizando codigo para $REMOTE/$BRANCH"
git fetch "$REMOTE" "$BRANCH"
git reset --hard "$REMOTE/$BRANCH"
HEAD_AFTER="$(git rev-parse HEAD)"

if [[ -n "$(git status --porcelain)" ]]; then
  git status --short
  fail "Repositorio ficou sujo apos atualizar codigo."
fi

tracked_dist_count="$(git ls-files frontend/dist runtime | wc -l | tr -d ' ')"
if [[ "$tracked_dist_count" != "0" ]]; then
  git ls-files frontend/dist runtime
  fail "Artefatos gerados voltaram a aparecer no Git."
fi

mark_step "instalar_disk_guard"
audit_step "Instalando ou validando guardiao preventivo de disco"
log "Instalando monitor preventivo de disco"
if [[ -f "$APP_DIR/scripts/install_ops_disk_guard_cron.sh" ]]; then
  bash "$APP_DIR/scripts/install_ops_disk_guard_cron.sh" || log "Aviso: nao foi possivel instalar o cron do disk guard"
fi

if [[ -f "$APP_DIR/scripts/ops_disk_guard.sh" ]]; then
  bash "$APP_DIR/scripts/ops_disk_guard.sh" || log "Aviso: disk guard imediato falhou"
fi

mark_step "instalar_host_watchdog"
audit_step "Instalando ou validando watchdog externo do host"
log "Instalando watchdog externo do host"
if [[ -f "$APP_DIR/scripts/install_ops_host_watchdog_cron.sh" ]]; then
  bash "$APP_DIR/scripts/install_ops_host_watchdog_cron.sh" || log "Aviso: nao foi possivel instalar o cron do host watchdog"
fi

mark_step "preparar_diretorios_persistentes"
audit_step "Preparando diretorios persistentes do backend"
log "Preparando diretorios persistentes do backend"
mkdir -p \
  "$APP_DIR/backend/data/bling_snapshots" \
  "$APP_DIR/backend/uploads/bling_snapshots" \
  "$APP_DIR/backend/logs" \
  "$APP_DIR/backend/secrets"
chown -R 1000:1000 \
  "$APP_DIR/backend/data" \
  "$APP_DIR/backend/uploads/bling_snapshots" \
  "$APP_DIR/backend/logs" \
  "$APP_DIR/backend/secrets" \
  || log "Aviso: nao foi possivel ajustar owner dos diretorios persistentes"
chmod -R u+rwX,g+rwX \
  "$APP_DIR/backend/data" \
  "$APP_DIR/backend/uploads/bling_snapshots" \
  "$APP_DIR/backend/logs" \
  "$APP_DIR/backend/secrets" \
  || log "Aviso: nao foi possivel ajustar permissao dos diretorios persistentes"

mark_step "build_frontend"
audit_step "Gerando build do frontend"
log "Gerando frontend em $NEXT_RUNTIME_DIST"
rm -rf "$NEXT_RUNTIME_DIST"
mkdir -p "$NEXT_RUNTIME_DIST"
(
  cd frontend
  npm ci
  npm run build -- --outDir "../$NEXT_RUNTIME_DIST" --emptyOutDir
)

[[ -s "$NEXT_RUNTIME_DIST/index.html" ]] || fail "Build do frontend nao gerou index.html em $NEXT_RUNTIME_DIST"

mark_step "validar_compose"
audit_step "Validando docker compose de producao"
log "Validando docker compose"
docker compose -f "$COMPOSE_FILE" config --quiet

mark_step "build_backend"
audit_step "Reconstruindo backend e worker"
log "Reconstruindo backend e imagem do worker"
docker compose -f "$COMPOSE_FILE" build backend

mark_step "subir_postgres"
audit_step "Garantindo Postgres ativo antes das migrations"
log "Garantindo Postgres ativo"
docker compose -f "$COMPOSE_FILE" up -d postgres

wait_for \
  "Postgres" \
  "cd '$APP_DIR' && docker compose -f '$COMPOSE_FILE' exec -T postgres pg_isready -U petshop_admin -d petshop_prod" \
  24 \
  5

mark_step "migrar_banco"
audit_step "Aplicando migrations Alembic"
log "Aplicando migrations Alembic"
docker compose -f "$COMPOSE_FILE" run --rm --no-deps backend alembic upgrade head

mark_step "subir_servicos"
audit_step "Subindo backend e worker"
log "Subindo backend e worker"
docker compose -f "$COMPOSE_FILE" up -d backend worker-bling

mark_step "publicar_frontend"
audit_step "Publicando frontend gerado"
log "Publicando frontend em $RUNTIME_DIST"
rm -rf "$PREV_RUNTIME_DIST"
if [[ -d "$RUNTIME_DIST" ]]; then
  mv "$RUNTIME_DIST" "$PREV_RUNTIME_DIST"
fi
mv "$NEXT_RUNTIME_DIST" "$RUNTIME_DIST"

log "Recriando nginx para renovar DNS interno do backend e servir o novo frontend"
docker compose -f "$COMPOSE_FILE" up -d --force-recreate --no-deps nginx

mark_step "validar_watchdog"
audit_step "Validando watchdog interno do backend"
log "Aguardando watchdog interno"
wait_for \
  "backend watchdog" \
  "cd '$APP_DIR' && docker compose -f '$COMPOSE_FILE' exec -T backend curl -fsS --max-time 8 http://127.0.0.1:8000/health/watchdog" \
  30 \
  5

mark_step "validar_worker_bling"
audit_step "Validando heartbeat do worker Bling"
log "Aguardando worker Bling"
wait_for \
  "worker Bling" \
  "cd '$APP_DIR' && docker compose -f '$COMPOSE_FILE' exec -T worker-bling test -f /tmp/bling_worker_heartbeat" \
  24 \
  5

mark_step "validar_health_publico"
audit_step "Validando health publico"
log "Aguardando health publico"
wait_for "health publico" "curl -fsS --max-time 10 '$PUBLIC_HEALTH_URL'" 12 5

mark_step "checar_estado_final"
audit_step "Checando estado final dos containers"
log "Checando estado final"
docker compose -f "$COMPOSE_FILE" ps

mark_step "disk_guard_final"
audit_step "Rodando verificacao final de disco"
log "Rodando verificacao final de disco"
if [[ -f "$APP_DIR/scripts/ops_disk_guard.sh" ]]; then
  bash "$APP_DIR/scripts/ops_disk_guard.sh" || log "Aviso: disk guard final falhou"
fi

mark_step "host_watchdog_final"
audit_step "Rodando verificacao final do watchdog externo"
log "Rodando verificacao final do watchdog externo"
cleanup_deploy_lock
if [[ -f "$APP_DIR/scripts/ops_host_watchdog.sh" ]]; then
  bash "$APP_DIR/scripts/ops_host_watchdog.sh" || log "Aviso: host watchdog final falhou"
fi

if [[ -n "$(git status --porcelain)" ]]; then
  git status --short
  fail "Deploy terminou com Git sujo. Investigue antes de considerar concluido."
fi

git rev-parse HEAD >"$backup_dir/head_after.txt"
docker compose -f "$COMPOSE_FILE" ps >"$backup_dir/docker_ps_after.txt" || true

mark_step "concluido"
write_deploy_event "success" "$CURRENT_STEP" "Deploy concluido com repositorio limpo"

log "Deploy concluido com repositorio limpo"
printf 'Backup operacional: %s\n' "$backup_dir"
