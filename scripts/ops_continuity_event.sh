#!/usr/bin/env bash

# Shared append-only telemetry for production backup and restore checks.
# The payload intentionally contains metadata only, never database content.

record_ops_continuity_event() {
  local operation="$1"
  local status="$2"
  local backup_file="${3:-}"
  local backup_bytes="${4:-}"
  local backup_sha256="${5:-}"
  local public_tables="${6:-}"
  local alembic_rows="${7:-}"
  local event_path="${OPS_CONTINUITY_EVENT_LOG_PATH:-$APP_DIR/backend/logs/continuity_events.jsonl}"
  local created_at

  case "$operation:$status" in
    backup:ok|backup:failed|external_copy:ok|external_copy:failed|restore:ok|restore:failed) ;;
    *) return 1 ;;
  esac

  backup_file="$(basename -- "$backup_file" 2>/dev/null || true)"
  backup_file="${backup_file//[^a-zA-Z0-9_.-]/_}"
  backup_bytes="${backup_bytes//[^0-9]/}"
  backup_sha256="${backup_sha256//[^a-fA-F0-9]/}"
  public_tables="${public_tables//[^0-9]/}"
  alembic_rows="${alembic_rows//[^0-9]/}"
  created_at="$(date -u '+%Y-%m-%dT%H:%M:%SZ')"

  mkdir -p "$(dirname -- "$event_path")"
  umask 077

  if command -v flock >/dev/null 2>&1; then
    (
      flock -x 9
      printf '{"created_at":"%s","operation":"%s","status":"%s","backup_file":"%s","backup_bytes":"%s","backup_sha256":"%s","public_tables":"%s","alembic_rows":"%s"}\n' \
        "$created_at" "$operation" "$status" "$backup_file" "$backup_bytes" \
        "$backup_sha256" "$public_tables" "$alembic_rows" >&9
    ) 9>>"$event_path"
  else
    printf '{"created_at":"%s","operation":"%s","status":"%s","backup_file":"%s","backup_bytes":"%s","backup_sha256":"%s","public_tables":"%s","alembic_rows":"%s"}\n' \
      "$created_at" "$operation" "$status" "$backup_file" "$backup_bytes" \
      "$backup_sha256" "$public_tables" "$alembic_rows" >>"$event_path"
  fi

  chmod 0640 "$event_path" 2>/dev/null || true
  if [[ "$(id -u)" == "0" ]]; then
    chown "${OPS_RUNTIME_UID:-1000}:${OPS_RUNTIME_GID:-1000}" "$event_path" \
      2>/dev/null || true
  fi
}
