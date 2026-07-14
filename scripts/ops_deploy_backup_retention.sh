#!/usr/bin/env bash
set -Eeuo pipefail

APP_DIR="${APP_DIR:-/opt/petshop}"
BACKUP_ROOT="${DEPLOY_BACKUP_ROOT:-$APP_DIR/backups}"
KEEP="${DEPLOY_BACKUP_KEEP:-20}"

if [[ ! "$KEEP" =~ ^[0-9]+$ ]] || [[ "$KEEP" -lt 2 ]]; then
  printf 'DEPLOY_BACKUP_KEEP deve ser um inteiro maior ou igual a 2.\n' >&2
  exit 2
fi

mkdir -p "$BACKUP_ROOT"

mapfile -t deploy_names < <(
  find "$BACKUP_ROOT" -mindepth 1 -maxdepth 1 -type d -printf '%f\n' \
    | grep -E '^deploy_[0-9]{8}_[0-9]{6}$' \
    | sort -r \
    || true
)

removed=0
for ((index = KEEP; index < ${#deploy_names[@]}; index++)); do
  name="${deploy_names[$index]}"
  [[ "$name" =~ ^deploy_[0-9]{8}_[0-9]{6}$ ]] || continue
  target="$BACKUP_ROOT/$name"
  [[ -d "$target" ]] || continue
  rm -rf -- "$target"
  removed=$((removed + 1))
done

printf 'deploy_backup_retention_status=ok\n'
printf 'deploy_backup_keep=%s\n' "$KEEP"
printf 'deploy_backup_removed=%s\n' "$removed"
