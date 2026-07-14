#!/usr/bin/env bash
set -Eeuo pipefail

APP_DIR="${APP_DIR:-/opt/petshop}"
BACKUP_DIR="${BACKUP_DIR:-$APP_DIR/backups/db}"
CONFIG_FILE="${OPS_EXTERNAL_COPY_CONFIG_FILE:-/etc/petshop/backup-external.env}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# shellcheck source=ops_continuity_event.sh
source "$SCRIPT_DIR/ops_continuity_event.sh"

event_recorded="false"

record_external_copy_event() {
  event_recorded="true"
  record_ops_continuity_event "external_copy" "$1" "${2:-}" "${3:-}" "${4:-}"
}

record_unexpected_failure() {
  if [[ "$event_recorded" != "true" ]]; then
    record_external_copy_event "failed" || true
  fi
}

trap record_unexpected_failure ERR

fail() {
  record_external_copy_event "failed" "${2:-}" "${3:-}" "${4:-}" || true
  printf 'external_copy_status=failed\n' >&2
  printf 'external_copy_error=%s\n' "$1" >&2
  exit 1
}

require_cmd() {
  command -v "$1" >/dev/null 2>&1 || fail "missing command: $1"
}

if [[ ! -f "$CONFIG_FILE" ]]; then
  fail "configuration file not found: $CONFIG_FILE"
fi

config_owner="$(stat -c '%u' "$CONFIG_FILE" 2>/dev/null || true)"
config_mode="$(stat -c '%a' "$CONFIG_FILE" 2>/dev/null || true)"
if [[ "$config_owner" != "0" || ! "$config_mode" =~ ^[0-7]00$ ]]; then
  fail "configuration file must belong to root and deny group/other access"
fi

set -a
# O arquivo e root-owned e nunca deve ser versionado.
# shellcheck disable=SC1090
source "$CONFIG_FILE"
set +a

: "${OPS_BACKUP_S3_BUCKET:?OPS_BACKUP_S3_BUCKET is required}"
: "${OPS_BACKUP_S3_ENDPOINT_URL:?OPS_BACKUP_S3_ENDPOINT_URL is required}"
: "${AWS_ACCESS_KEY_ID:?AWS_ACCESS_KEY_ID is required}"
: "${AWS_SECRET_ACCESS_KEY:?AWS_SECRET_ACCESS_KEY is required}"

OPS_BACKUP_S3_REGION="${OPS_BACKUP_S3_REGION:-auto}"
OPS_BACKUP_S3_PREFIX="${OPS_BACKUP_S3_PREFIX:-corepet/database}"
OPS_BACKUP_S3_PREFIX="${OPS_BACKUP_S3_PREFIX#/}"
OPS_BACKUP_S3_PREFIX="${OPS_BACKUP_S3_PREFIX%/}"

case "$OPS_BACKUP_S3_BUCKET" in
  ""|*[!a-zA-Z0-9._-]*) fail "invalid bucket name" ;;
esac

case "$OPS_BACKUP_S3_PREFIX" in
  ""|*[!a-zA-Z0-9._/-]*) fail "invalid object prefix" ;;
esac

require_cmd aws
require_cmd sha256sum
require_cmd stat

backup_file="$(
  find "$BACKUP_DIR" -maxdepth 1 -type f -name '*.dump.gz' -printf '%T@ %p\n' \
    | sort -nr | sed -n '1p' | cut -d' ' -f2-
)"

if [[ -z "$backup_file" || ! -f "$backup_file" ]]; then
  fail "no database backup found in $BACKUP_DIR"
fi

backup_name="$(basename -- "$backup_file")"
checksum_file="$backup_file.sha256"
if [[ ! "$backup_name" =~ ^[a-zA-Z0-9_.-]+\.dump\.gz$ ]]; then
  fail "invalid backup filename" "$backup_file"
fi

if [[ ! -f "$checksum_file" ]]; then
  fail "checksum file not found" "$backup_file"
fi

expected_sha256="$(tr -d '[:space:]' <"$checksum_file")"
actual_sha256="$(sha256sum "$backup_file" | awk '{print $1}')"
if [[ ! "$expected_sha256" =~ ^[a-fA-F0-9]{64}$ || "$actual_sha256" != "$expected_sha256" ]]; then
  fail "local backup checksum mismatch" "$backup_file"
fi

backup_bytes="$(stat -c '%s' "$backup_file")"
object_key="$OPS_BACKUP_S3_PREFIX/$backup_name"
checksum_key="$object_key.sha256"
aws_args=(--endpoint-url "$OPS_BACKUP_S3_ENDPOINT_URL" --region "$OPS_BACKUP_S3_REGION")

aws "${aws_args[@]}" s3api put-object \
  --bucket "$OPS_BACKUP_S3_BUCKET" \
  --key "$object_key" \
  --body "$backup_file" \
  --metadata "sha256=$actual_sha256" \
  --no-cli-pager >/dev/null

aws "${aws_args[@]}" s3api put-object \
  --bucket "$OPS_BACKUP_S3_BUCKET" \
  --key "$checksum_key" \
  --body "$checksum_file" \
  --content-type 'text/plain' \
  --no-cli-pager >/dev/null

remote_bytes="$(
  aws "${aws_args[@]}" s3api head-object \
    --bucket "$OPS_BACKUP_S3_BUCKET" \
    --key "$object_key" \
    --query 'ContentLength' --output text --no-cli-pager
)"
remote_sha256="$(
  aws "${aws_args[@]}" s3api head-object \
    --bucket "$OPS_BACKUP_S3_BUCKET" \
    --key "$object_key" \
    --query 'Metadata.sha256' --output text --no-cli-pager
)"

if [[ "$remote_bytes" != "$backup_bytes" || "$remote_sha256" != "$actual_sha256" ]]; then
  fail "remote backup validation failed" "$backup_file" "$backup_bytes" "$actual_sha256"
fi

record_external_copy_event "ok" "$backup_file" "$backup_bytes" "$actual_sha256"

printf 'external_copy_status=ok\n'
printf 'external_copy_file=%s\n' "$backup_name"
printf 'external_copy_bytes=%s\n' "$backup_bytes"
printf 'external_copy_sha256=%s\n' "$actual_sha256"
printf 'external_copy_object=%s\n' "$object_key"
