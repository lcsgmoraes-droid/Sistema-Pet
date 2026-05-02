#!/usr/bin/env bash
set -Eeuo pipefail

APP_DIR="${APP_DIR:-/opt/petshop}"
REMOTE="${REMOTE:-origin}"
BRANCH="${BRANCH:-main}"
COMPOSE_FILE="${COMPOSE_FILE:-docker-compose.prod.yml}"
RUNTIME_DIST="${RUNTIME_DIST:-runtime/frontend/dist}"
PUBLIC_HEALTH_URL="${PUBLIC_HEALTH_URL:-https://mlprohub.com.br/api/health}"

log() {
  printf '\n[%s] %s\n' "$(date '+%Y-%m-%d %H:%M:%S')" "$*"
}

fail() {
  printf '\nERRO: %s\n' "$*" >&2
  exit 1
}

require_cmd() {
  command -v "$1" >/dev/null 2>&1 || fail "Comando obrigatorio nao encontrado: $1"
}

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

cd "$APP_DIR"

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
git rev-parse HEAD >"$backup_dir/head_before.txt"
docker compose -f "$COMPOSE_FILE" ps >"$backup_dir/docker_ps_before.txt" || true

log "Atualizando codigo para $REMOTE/$BRANCH"
git fetch "$REMOTE" "$BRANCH"
git reset --hard "$REMOTE/$BRANCH"

if [[ -n "$(git status --porcelain)" ]]; then
  git status --short
  fail "Repositorio ficou sujo apos atualizar codigo."
fi

tracked_dist_count="$(git ls-files frontend/dist runtime | wc -l | tr -d ' ')"
if [[ "$tracked_dist_count" != "0" ]]; then
  git ls-files frontend/dist runtime
  fail "Artefatos gerados voltaram a aparecer no Git."
fi

log "Gerando frontend em $RUNTIME_DIST"
mkdir -p "$RUNTIME_DIST"
(
  cd frontend
  npm ci
  npm run build -- --outDir "../$RUNTIME_DIST" --emptyOutDir
)

[[ -s "$RUNTIME_DIST/index.html" ]] || fail "Build do frontend nao gerou index.html em $RUNTIME_DIST"

log "Validando docker compose"
docker compose -f "$COMPOSE_FILE" config --quiet

log "Reconstruindo backend"
docker compose -f "$COMPOSE_FILE" build backend

log "Subindo servicos principais"
docker compose -f "$COMPOSE_FILE" up -d postgres backend nginx

log "Aguardando watchdog interno"
wait_for \
  "backend watchdog" \
  "cd '$APP_DIR' && docker compose -f '$COMPOSE_FILE' exec -T backend curl -fsS --max-time 8 http://127.0.0.1:8000/health/watchdog" \
  30 \
  5

log "Aguardando health publico"
wait_for "health publico" "curl -fsS --max-time 10 '$PUBLIC_HEALTH_URL'" 12 5

log "Checando estado final"
docker compose -f "$COMPOSE_FILE" ps

if [[ -n "$(git status --porcelain)" ]]; then
  git status --short
  fail "Deploy terminou com Git sujo. Investigue antes de considerar concluido."
fi

git rev-parse HEAD >"$backup_dir/head_after.txt"
docker compose -f "$COMPOSE_FILE" ps >"$backup_dir/docker_ps_after.txt" || true

log "Deploy concluido com repositorio limpo"
printf 'Backup operacional: %s\n' "$backup_dir"
