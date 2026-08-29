#!/usr/bin/env bash
set -Eeuo pipefail

if [[ "$#" -ne 0 ]]; then
  echo "O status de producao nao aceita argumentos." >&2
  exit 2
fi

APP_DIR="${APP_DIR:-/opt/petshop}"
COMPOSE_FILE="${COMPOSE_FILE:-docker-compose.prod.yml}"
STATUS_PUBLIC_DOMAIN="${STATUS_PUBLIC_DOMAIN:-corepet.com.br}"
PUBLIC_HEALTH_URL="${PUBLIC_HEALTH_URL:-https://${STATUS_PUBLIC_DOMAIN}/api/health}"
PUBLIC_WATCHDOG_URL="${PUBLIC_WATCHDOG_URL:-https://${STATUS_PUBLIC_DOMAIN}/health/watchdog}"
PUBLIC_RELEASE_URL="${PUBLIC_RELEASE_URL:-https://${STATUS_PUBLIC_DOMAIN}/release-commit.txt}"

fail() {
  printf 'STATUS PRODUCAO: FALHOU - %s\n' "$*" >&2
  exit 1
}

require_cmd() {
  command -v "$1" >/dev/null 2>&1 || fail "comando obrigatorio ausente: $1"
}

require_service_healthy() {
  local service="$1"
  local container_id=""
  local state=""

  container_id="$(docker compose -f "$COMPOSE_FILE" ps -q "$service")"
  [[ -n "$container_id" ]] || fail "servico sem container: $service"

  state="$(
    docker inspect \
      --format '{{if .State.Health}}{{.State.Health.Status}}{{else}}{{.State.Status}}{{end}}' \
      "$container_id"
  )"
  [[ "$state" == "healthy" || "$state" == "running" ]] \
    || fail "servico $service em estado $state"
  printf 'service_%s=%s\n' "$service" "$state"
}

require_cmd curl
require_cmd docker
require_cmd git
require_cmd python3
[[ -d "$APP_DIR/.git" ]] || fail "repositorio nao encontrado em $APP_DIR"
[[ -f "$APP_DIR/$COMPOSE_FILE" ]] || fail "compose de producao nao encontrado"

cd "$APP_DIR"
python3 scripts/validate_deploy_target.py \
  --domain "$STATUS_PUBLIC_DOMAIN" \
  --health-url "$PUBLIC_HEALTH_URL"

branch="$(git rev-parse --abbrev-ref HEAD)"
head_commit="$(git rev-parse HEAD)"
[[ "$branch" == "main" ]] || fail "branch servida nao e main: $branch"
[[ -z "$(git status --porcelain)" ]] || fail "repositorio possui alteracoes locais"

printf 'git_branch=%s\n' "$branch"
printf 'git_commit=%s\n' "$head_commit"
docker compose -f "$COMPOSE_FILE" ps

for service in postgres backend worker-bling worker-catalogo nginx; do
  require_service_healthy "$service"
done

alembic_current="$(docker compose -f "$COMPOSE_FILE" exec -T backend alembic current 2>&1)"
printf '%s\n' "$alembic_current"
grep -q '(head)' <<<"$alembic_current" || fail "banco nao esta na migration head"

health_payload="$(curl -fsS --max-time 20 "$PUBLIC_HEALTH_URL")"
HEALTH_PAYLOAD="$health_payload" python3 - <<'PY'
import json
import os

payload = json.loads(os.environ["HEALTH_PAYLOAD"])
if payload.get("status") != "ok":
    raise SystemExit("health publico nao retornou status ok")
PY

watchdog_payload="$(curl -fsS --max-time 20 "$PUBLIC_WATCHDOG_URL")"
[[ "$watchdog_payload" == "healthy" ]] \
  || fail "watchdog publico nao retornou healthy"

public_commit="$(curl -fsS --max-time 20 "$PUBLIC_RELEASE_URL" | tr -d '\r\n')"
[[ "$public_commit" == "$head_commit" ]] \
  || fail "dominio serve $public_commit, mas o servidor esta em $head_commit"

printf 'public_health=%s\n' "$health_payload"
printf 'public_watchdog=%s\n' "$watchdog_payload"
printf 'public_commit=%s\n' "$public_commit"
printf 'STATUS PRODUCAO: OK\n'
