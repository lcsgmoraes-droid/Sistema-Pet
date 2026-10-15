#!/usr/bin/env bash
set -Eeuo pipefail

ROLE="${1:-}"
APP_DIR="${APP_DIR:-/opt/petshop}"
COMPOSE_FILE="${COMPOSE_FILE:-docker-compose.prod.yml}"
POSTGRES_SERVICE="${POSTGRES_SERVICE:-postgres}"
POSTGRES_DB="${POSTGRES_DB:-petshop_prod}"
POSTGRES_USER="${POSTGRES_USER:-petshop_admin}"
errors=0
warnings=0

usage() {
  printf 'Uso: bash scripts/migration_inventory.sh source|target\n'
}

error() {
  errors=$((errors + 1))
  printf 'ERROR %s\n' "$*" >&2
}

warn() {
  warnings=$((warnings + 1))
  printf 'WARN %s\n' "$*" >&2
}

value() {
  printf '%s=%s\n' "$1" "$2"
}

command_version() {
  local name="$1"
  shift
  if command -v "$name" >/dev/null 2>&1; then
    value "${name}_version" "$($@ 2>&1 | sed -n '1p')"
  else
    error "comando ausente: $name"
  fi
}

directory_inventory() {
  local path="$1"
  local label="$2"
  if [[ -d "$path" ]]; then
    value "${label}_bytes" "$(du -sb "$path" | awk '{print $1}')"
    value "${label}_files" "$(find "$path" -type f | wc -l | tr -d '[:space:]')"
  else
    warn "diretorio ausente: $path"
  fi
}

if [[ "$ROLE" != "source" && "$ROLE" != "target" ]]; then
  usage
  exit 2
fi

value inventory_role "$ROLE"
value inventory_at "$(date --iso-8601=seconds)"
value hostname "$(hostname)"
value kernel "$(uname -srmo)"

if [[ -r /etc/os-release ]]; then
  # shellcheck disable=SC1091
  source /etc/os-release
  value os "${PRETTY_NAME:-unknown}"
fi

cpu_count="$(nproc)"
memory_kb="$(awk '/MemTotal:/ {print $2}' /proc/meminfo)"
root_available_kb="$(df -Pk / | awk 'NR==2 {print $4}')"
value cpu_count "$cpu_count"
value memory_kb "$memory_kb"
value root_available_kb "$root_available_kb"

if [[ "$ROLE" == "target" ]]; then
  if (( cpu_count < 2 )); then
    error "alvo com menos de 2 CPUs disponiveis"
  fi
  if (( memory_kb < 7500000 )); then
    error "alvo com menos de aproximadamente 8 GB de RAM"
  fi
  if (( root_available_kb < 40000000 )); then
    error "alvo com menos de aproximadamente 40 GB livres em disco"
  fi
elif (( root_available_kb < 2000000 )); then
  error "origem com menos de aproximadamente 2 GB livres para gerar o dump final"
fi

command_version git git --version
command_version docker docker --version
if command -v docker >/dev/null 2>&1; then
  value docker_compose_version "$(docker compose version 2>&1 | sed -n '1p')"
fi
command_version node node --version
command_version openssl openssl version
command_version rsync rsync --version

if command -v ufw >/dev/null 2>&1; then
  value ufw_status "$(ufw status 2>/dev/null | sed -n '1p' || true)"
else
  warn "ufw ausente"
fi
if command -v systemctl >/dev/null 2>&1; then
  value fail2ban_status "$(systemctl is-active fail2ban 2>/dev/null || true)"
fi

if [[ ! -d "$APP_DIR" ]]; then
  error "diretorio da aplicacao ausente: $APP_DIR"
else
  value app_dir "$APP_DIR"
fi

if [[ -d "$APP_DIR/.git" || -f "$APP_DIR/.git" ]]; then
  value git_commit "$(git -C "$APP_DIR" rev-parse HEAD 2>/dev/null || true)"
  value git_branch "$(git -C "$APP_DIR" branch --show-current 2>/dev/null || true)"
  dirty_count="$(git -C "$APP_DIR" status --porcelain 2>/dev/null | wc -l | tr -d '[:space:]')"
  value git_dirty_count "$dirty_count"
  if [[ "$dirty_count" != "0" ]]; then
    error "repositorio da aplicacao tem alteracoes locais"
  fi
else
  error "repositorio Git ausente em $APP_DIR"
fi

env_file="$APP_DIR/.env"
if [[ -f "$env_file" ]]; then
  value env_owner "$(stat -c '%U:%G' "$env_file")"
  value env_mode "$(stat -c '%a' "$env_file")"
  for key in POSTGRES_PASSWORD JWT_SECRET_KEY PAYMENT_CONFIG_ENCRYPTION_KEY BLING_CLIENT_ID BLING_CLIENT_SECRET; do
    if grep -Eq "^${key}=.+" "$env_file"; then
      value "env_${key}" configured
    else
      error "variavel obrigatoria ausente ou vazia: $key"
    fi
  done
else
  error "arquivo seguro ausente: $env_file"
fi

compose_path="$APP_DIR/$COMPOSE_FILE"
if [[ -f "$compose_path" ]]; then
  if (cd "$APP_DIR" && docker compose -f "$COMPOSE_FILE" config --quiet); then
    value compose_config ok
  else
    error "docker compose config falhou"
  fi
else
  error "compose de producao ausente: $compose_path"
fi

if [[ "$ROLE" == "source" ]]; then
  if (cd "$APP_DIR" && docker compose -f "$COMPOSE_FILE" ps --status running --services 2>/dev/null | grep -qx "$POSTGRES_SERVICE"); then
    db_bytes="$(cd "$APP_DIR" && docker compose -f "$COMPOSE_FILE" exec -T "$POSTGRES_SERVICE" \
      psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -tAc \
      'select pg_database_size(current_database());' | tr -d '[:space:]')"
    table_count="$(cd "$APP_DIR" && docker compose -f "$COMPOSE_FILE" exec -T "$POSTGRES_SERVICE" \
      psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -tAc \
      "select count(*) from information_schema.tables where table_schema='public';" | tr -d '[:space:]')"
    value database_bytes "$db_bytes"
    value database_public_tables "$table_count"
    value alembic_revision "$(cd "$APP_DIR" && docker compose -f "$COMPOSE_FILE" exec -T "$POSTGRES_SERVICE" \
      psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -tAc \
      'select version_num from alembic_version order by version_num;' | paste -sd, -)"
  else
    error "PostgreSQL de origem nao esta acessivel pelo Compose"
  fi

  directory_inventory "$APP_DIR/backend/uploads" uploads
  directory_inventory "$APP_DIR/backend/data" backend_data
  directory_inventory "$APP_DIR/backend/secrets" backend_secrets
  directory_inventory "$APP_DIR/nginx/ssl" nginx_ssl
  directory_inventory "$APP_DIR/backups/db" database_backups

  latest_backup="$(find "$APP_DIR/backups/db" -maxdepth 1 -type f -name '*.dump.gz' -printf '%T@ %p\n' 2>/dev/null | sort -nr | sed -n '1p' | cut -d' ' -f2-)"
  if [[ -n "$latest_backup" ]]; then
    value latest_backup "$latest_backup"
    value latest_backup_bytes "$(stat -c '%s' "$latest_backup")"
  else
    error "nenhum backup .dump.gz encontrado"
  fi

  while IFS= read -r cert_file; do
    cert_label="$(printf '%s' "$cert_file" | sed 's#[^a-zA-Z0-9]#_#g')"
    value "certificate_${cert_label}" "$(openssl x509 -in "$cert_file" -noout -subject -enddate 2>/dev/null | paste -sd';' - || true)"
  done < <(find "$APP_DIR/nginx/ssl" -type f -name 'fullchain.pem' 2>/dev/null | sort)

  value petshop_cron_count "$(find /etc/cron.d -maxdepth 1 -type f -name 'petshop-*' 2>/dev/null | wc -l | tr -d '[:space:]')"
  value petshop_wrapper_count "$(find /usr/local/sbin -maxdepth 1 -type f -name 'petshop-*' 2>/dev/null | wc -l | tr -d '[:space:]')"
fi

if [[ "$ROLE" == "target" ]]; then
  if [[ -f "$compose_path" ]] && (cd "$APP_DIR" && docker compose -f "$COMPOSE_FILE" ps >/dev/null 2>&1); then
    value target_compose_access ok
  else
    warn "aplicacao ainda nao esta pronta para validacao no alvo"
  fi
fi

value inventory_warnings "$warnings"
value inventory_errors "$errors"
if (( errors > 0 )); then
  value inventory_status failed
  exit 1
fi
value inventory_status ok
