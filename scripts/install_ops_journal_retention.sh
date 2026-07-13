#!/usr/bin/env bash
set -Eeuo pipefail

CONFIG_DIR="${JOURNAL_CONFIG_DIR:-/etc/systemd/journald.conf.d}"
CONFIG_FILE="${JOURNAL_CONFIG_FILE:-$CONFIG_DIR/corepet-retention.conf}"
SYSTEM_MAX_USE="${JOURNAL_SYSTEM_MAX_USE:-768M}"
SYSTEM_KEEP_FREE="${JOURNAL_SYSTEM_KEEP_FREE:-3G}"
MAX_RETENTION="${JOURNAL_MAX_RETENTION:-30day}"

if [[ "$(id -u)" != "0" ]]; then
  echo "Instalacao da retencao do journal exige root." >&2
  exit 1
fi

for required_command in install journalctl systemctl; do
  command -v "$required_command" >/dev/null 2>&1 || {
    echo "Comando obrigatorio nao encontrado: $required_command" >&2
    exit 1
  }
done

if [[ ! "$SYSTEM_MAX_USE" =~ ^[0-9]+[KMG]$ ]]; then
  echo "JOURNAL_SYSTEM_MAX_USE invalido: $SYSTEM_MAX_USE" >&2
  exit 1
fi
if [[ ! "$SYSTEM_KEEP_FREE" =~ ^[0-9]+[KMG]$ ]]; then
  echo "JOURNAL_SYSTEM_KEEP_FREE invalido: $SYSTEM_KEEP_FREE" >&2
  exit 1
fi
if [[ ! "$MAX_RETENTION" =~ ^[0-9]+(s|min|h|day|week|month|year)$ ]]; then
  echo "JOURNAL_MAX_RETENTION invalido: $MAX_RETENTION" >&2
  exit 1
fi

config_tmp="$(mktemp)"
cleanup() {
  rm -f "$config_tmp"
}
trap cleanup EXIT

cat >"$config_tmp" <<CONFIG
[Journal]
SystemMaxUse=$SYSTEM_MAX_USE
SystemKeepFree=$SYSTEM_KEEP_FREE
MaxRetentionSec=$MAX_RETENTION
Compress=yes
CONFIG

install -d -o root -g root -m 0755 "$CONFIG_DIR"
install -o root -g root -m 0644 "$config_tmp" "$CONFIG_FILE"

systemctl restart systemd-journald
journalctl --rotate
journalctl --vacuum-time="$MAX_RETENTION" --vacuum-size="$SYSTEM_MAX_USE"

echo "Retencao do journal instalada em $CONFIG_FILE"
journalctl --disk-usage
