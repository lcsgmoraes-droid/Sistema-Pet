#!/usr/bin/env bash
set -Eeuo pipefail

APP_DIR="${APP_DIR:-/opt/petshop}"
STATUS_PATH="${OPS_TLS_STATUS_PATH:-$APP_DIR/backend/logs/tls_status.json}"
DOMAINS="${OPS_TLS_DOMAINS:-corepet.com.br,www.corepet.com.br,img.corepet.com.br}"
WARNING_DAYS="${OPS_TLS_WARNING_DAYS:-30}"
CRITICAL_DAYS="${OPS_TLS_CRITICAL_DAYS:-7}"
TIMEOUT_SECONDS="${OPS_TLS_TIMEOUT_SECONDS:-10}"

mkdir -p "$(dirname "$STATUS_PATH")"

OPS_TLS_STATUS_PATH="$STATUS_PATH" \
OPS_TLS_DOMAINS="$DOMAINS" \
OPS_TLS_WARNING_DAYS="$WARNING_DAYS" \
OPS_TLS_CRITICAL_DAYS="$CRITICAL_DAYS" \
OPS_TLS_TIMEOUT_SECONDS="$TIMEOUT_SECONDS" \
python3 - <<'PY'
import datetime
import json
import os
import socket
import ssl
from pathlib import Path

status_path = Path(os.environ["OPS_TLS_STATUS_PATH"])
domains = [item.strip() for item in os.environ["OPS_TLS_DOMAINS"].split(",") if item.strip()]
warning_days = max(1, int(os.environ["OPS_TLS_WARNING_DAYS"]))
critical_days = max(0, int(os.environ["OPS_TLS_CRITICAL_DAYS"]))
timeout_seconds = max(1, int(os.environ["OPS_TLS_TIMEOUT_SECONDS"]))
now = datetime.datetime.now(datetime.UTC)
context = ssl.create_default_context()
certificates = []

for domain in domains:
    item = {"domain": domain}
    try:
        with socket.create_connection((domain, 443), timeout=timeout_seconds) as raw_socket:
            with context.wrap_socket(raw_socket, server_hostname=domain) as tls_socket:
                certificate = tls_socket.getpeercert()
        expires_at = datetime.datetime.fromtimestamp(
            ssl.cert_time_to_seconds(certificate["notAfter"]), datetime.UTC
        )
        days_remaining = max(0, int((expires_at - now).total_seconds() // 86400))
        if expires_at <= now or days_remaining <= critical_days:
            status = "critical"
        elif days_remaining <= warning_days:
            status = "warning"
        else:
            status = "healthy"
        item.update(
            {
                "status": status,
                "expires_at": expires_at.isoformat().replace("+00:00", "Z"),
                "days_remaining": days_remaining,
            }
        )
    except Exception as exc:
        item.update({"status": "failed", "error_type": type(exc).__name__})
    certificates.append(item)

statuses = {item["status"] for item in certificates}
if not certificates or "failed" in statuses or "critical" in statuses:
    overall_status = "critical"
elif "warning" in statuses:
    overall_status = "warning"
else:
    overall_status = "healthy"

payload = {
    "generated_at": now.isoformat().replace("+00:00", "Z"),
    "status": overall_status,
    "warning_days": warning_days,
    "critical_days": critical_days,
    "certificates": certificates,
}
temporary_path = status_path.with_suffix(status_path.suffix + ".tmp")
temporary_path.write_text(
    json.dumps(payload, ensure_ascii=False, separators=(",", ":")) + "\n",
    encoding="utf-8",
)
os.chmod(temporary_path, 0o644)
os.replace(temporary_path, status_path)
PY

echo "Status TLS atualizado em $STATUS_PATH"
