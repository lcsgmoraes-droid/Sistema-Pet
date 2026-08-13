#!/usr/bin/env bash
set -Eeuo pipefail

APP_DIR="${OPS_COMMAND_AUDIT_APP_DIR:-${APP_DIR:-/opt/petshop}}"
EVENT_LOG_PATH="${OPS_COMMAND_AUDIT_LOG_PATH:-$APP_DIR/backend/logs/ops_command_events.jsonl}"
PYTHON_BIN="${OPS_COMMAND_AUDIT_PYTHON:-python3}"
DOCKER_BIN="${OPS_COMMAND_AUDIT_DOCKER:-docker}"

ACTION=""
REASON=""
LABEL=""
COMMAND=()
STARTED_AT="$(date -u '+%Y-%m-%dT%H:%M:%SZ')"
OPERATION_ID="$(date -u '+%Y%m%dT%H%M%SZ')-$$-${RANDOM:-0}"

usage() {
  cat >&2 <<'EOF'
Uso:
  auditar_comando_producao.sh --action <acao> --reason <motivo> [--label <rotulo>] -- <comando> [args...]

Exemplo:
  bash scripts/auditar_comando_producao.sh \
    --action docker.ps \
    --reason "validacao apos deploy autorizado" \
    --label "docker compose ps" \
    -- docker compose -f docker-compose.prod.yml ps
EOF
}

fail_usage() {
  printf 'ERRO: %s\n\n' "$*" >&2
  usage
  exit 2
}

require_cmd() {
  command -v "$1" >/dev/null 2>&1 || {
    printf 'ERRO: comando obrigatorio nao encontrado: %s\n' "$1" >&2
    exit 2
  }
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --action)
      [[ $# -ge 2 ]] || fail_usage "--action requer valor"
      ACTION="$2"
      shift 2
      ;;
    --reason)
      [[ $# -ge 2 ]] || fail_usage "--reason requer valor"
      REASON="$2"
      shift 2
      ;;
    --label)
      [[ $# -ge 2 ]] || fail_usage "--label requer valor"
      LABEL="$2"
      shift 2
      ;;
    --help|-h)
      usage
      exit 0
      ;;
    --)
      shift
      COMMAND=("$@")
      break
      ;;
    *)
      fail_usage "argumento desconhecido: $1"
      ;;
  esac
done

[[ -n "$ACTION" ]] || fail_usage "--action e obrigatorio"
[[ -n "$REASON" ]] || fail_usage "--reason e obrigatorio"
[[ ${#COMMAND[@]} -gt 0 ]] || fail_usage "informe o comando apos --"

require_cmd "$PYTHON_BIN"

git_branch=""
git_head=""
if git -C "$APP_DIR" rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  git_branch="$(git -C "$APP_DIR" rev-parse --abbrev-ref HEAD 2>/dev/null || true)"
  git_head="$(git -C "$APP_DIR" rev-parse HEAD 2>/dev/null || true)"
fi

append_ops_command_event_via_backend() {
  local event_json="$1"
  local logs_prefix="$APP_DIR/backend/logs/"
  local relative_log_path=""

  if [[ "$EVENT_LOG_PATH" != "$logs_prefix"* ]]; then
    printf 'ERRO: fallback seguro aceita apenas logs dentro de %s\n' "$logs_prefix" >&2
    return 1
  fi

  relative_log_path="${EVENT_LOG_PATH#"$logs_prefix"}"
  if [[ ! "$relative_log_path" =~ ^[A-Za-z0-9._-]+$ ]]; then
    printf 'ERRO: nome de log invalido para fallback seguro: %s\n' "$relative_log_path" >&2
    return 1
  fi

  require_cmd "$DOCKER_BIN"
  [[ -f "$APP_DIR/docker-compose.prod.yml" ]] || {
    printf 'ERRO: compose de producao nao encontrado em %s\n' "$APP_DIR" >&2
    return 1
  }

  printf 'AVISO: log sem permissao direta; gravando pelo container backend.\n' >&2
  printf '%s\n' "$event_json" | "$DOCKER_BIN" compose \
    -f "$APP_DIR/docker-compose.prod.yml" \
    exec -T backend sh -c 'umask 0007; cat >> "$1"' sh "/app/logs/$relative_log_path"
}

append_ops_command_event() {
  local event_json="$1"
  local event_log_dir=""

  event_log_dir="$(dirname "$EVENT_LOG_PATH")"
  if [[ "${OPS_COMMAND_AUDIT_FORCE_CONTAINER_APPEND:-0}" != "1" ]] \
    && mkdir -p "$event_log_dir" 2>/dev/null \
    && { [[ -w "$EVENT_LOG_PATH" ]] || [[ ! -e "$EVENT_LOG_PATH" && -w "$event_log_dir" ]]; }; then
    printf '%s\n' "$event_json" >>"$EVENT_LOG_PATH"
    return
  fi

  append_ops_command_event_via_backend "$event_json"
}

write_ops_command_event() {
  local status="$1"
  local exit_code="${2:-}"
  local finished_at="${3:-}"
  local event_json=""

  event_json="$(OPS_COMMAND_STATUS="$status" \
  OPS_COMMAND_EXIT_CODE="$exit_code" \
  OPS_COMMAND_ACTION="$ACTION" \
  OPS_COMMAND_REASON="$REASON" \
  OPS_COMMAND_LABEL="$LABEL" \
  OPS_COMMAND_STARTED_AT="$STARTED_AT" \
  OPS_COMMAND_FINISHED_AT="$finished_at" \
  OPS_COMMAND_OPERATION_ID="$OPERATION_ID" \
  OPS_COMMAND_APP_DIR="$APP_DIR" \
  OPS_COMMAND_GIT_BRANCH="$git_branch" \
  OPS_COMMAND_GIT_HEAD="$git_head" \
  OPS_COMMAND_USER="${SUDO_USER:-${USER:-unknown}}" \
  OPS_COMMAND_HOSTNAME="$(hostname 2>/dev/null || echo unknown)" \
  "$PYTHON_BIN" - "$@" <<'PY'
import datetime
import json
import os
import re
import shlex
import sys


SENSITIVE_KEY_RE = re.compile(
    r"(password|senha|token|secret|jwt|authorization|cookie|api[_-]?key|apikey)",
    re.IGNORECASE,
)


def redact_arg(value: str) -> str:
    if "=" in value:
        key, raw = value.split("=", 1)
        if SENSITIVE_KEY_RE.search(key):
            return f"{key}=***REDACTED***"
        return value

    if ":" in value:
        key, raw = value.split(":", 1)
        if SENSITIVE_KEY_RE.search(key):
            return f"{key}:***REDACTED***"
        return value

    if SENSITIVE_KEY_RE.search(value):
        return "***REDACTED***"

    return value


command_args = sys.argv[1:]
redacted_args = [redact_arg(arg) for arg in command_args]
exit_code_raw = os.environ.get("OPS_COMMAND_EXIT_CODE") or ""
event = {
    "created_at": datetime.datetime.now(datetime.UTC).isoformat().replace("+00:00", "Z"),
    "event_type": "ops_manual_command",
    "operation_id": os.environ.get("OPS_COMMAND_OPERATION_ID"),
    "status": os.environ.get("OPS_COMMAND_STATUS"),
    "action": os.environ.get("OPS_COMMAND_ACTION"),
    "reason": os.environ.get("OPS_COMMAND_REASON"),
    "label": os.environ.get("OPS_COMMAND_LABEL") or None,
    "started_at": os.environ.get("OPS_COMMAND_STARTED_AT"),
    "finished_at": os.environ.get("OPS_COMMAND_FINISHED_AT") or None,
    "exit_code": int(exit_code_raw) if exit_code_raw else None,
    "command_redacted": " ".join(shlex.quote(arg) for arg in redacted_args),
    "app_dir": os.environ.get("OPS_COMMAND_APP_DIR"),
    "git_branch": os.environ.get("OPS_COMMAND_GIT_BRANCH") or None,
    "git_head": os.environ.get("OPS_COMMAND_GIT_HEAD") or None,
    "user": os.environ.get("OPS_COMMAND_USER"),
    "hostname": os.environ.get("OPS_COMMAND_HOSTNAME"),
}

print(json.dumps(event, ensure_ascii=False, separators=(",", ":")))
PY
  )"

  append_ops_command_event "$event_json"
}

write_ops_command_event "started" "" "" "${COMMAND[@]}"

set +e
"${COMMAND[@]}"
exit_code=$?
set -e

finished_at="$(date -u '+%Y-%m-%dT%H:%M:%SZ')"
if [[ "$exit_code" -eq 0 ]]; then
  write_ops_command_event "success" "$exit_code" "$finished_at" "${COMMAND[@]}"
else
  write_ops_command_event "failed" "$exit_code" "$finished_at" "${COMMAND[@]}"
fi

exit "$exit_code"
