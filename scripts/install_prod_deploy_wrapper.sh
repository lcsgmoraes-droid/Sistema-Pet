#!/usr/bin/env bash
set -Eeuo pipefail

WRAPPER_PATH="${DEPLOY_WRAPPER_PATH:-/usr/local/sbin/petshop-deploy-producao}"
SUDOERS_FILE="${DEPLOY_SUDOERS_FILE:-/etc/sudoers.d/petshop-deploy}"
OPERATOR_USER="${DEPLOY_OPERATOR_USER:-petdeploy}"

if [[ "$(id -u)" != "0" ]]; then
  echo "Instalacao do wrapper de deploy exige root." >&2
  exit 1
fi

command -v visudo >/dev/null 2>&1 || {
  echo "visudo nao encontrado; wrapper nao instalado." >&2
  exit 1
}
id "$OPERATOR_USER" >/dev/null 2>&1 || {
  echo "Usuario operacional nao encontrado: $OPERATOR_USER" >&2
  exit 1
}

wrapper_tmp="$(mktemp)"
sudoers_tmp="$(mktemp)"
cleanup() {
  rm -f "$wrapper_tmp" "$sudoers_tmp"
}
trap cleanup EXIT

cat >"$wrapper_tmp" <<'WRAPPER'
#!/usr/bin/env bash
set -Eeuo pipefail

if [[ "$#" -ne 0 ]]; then
  echo "Este wrapper nao aceita argumentos." >&2
  exit 2
fi

# Trava independente do checkout: protege inclusive o primeiro deploy de um host.
python3 - <<'PY'
import ipaddress
import socket
import subprocess
import sys

domain = "corepet.com.br"
local = {
    str(ipaddress.ip_address(value))
    for value in subprocess.check_output(["hostname", "-I"], text=True).split()
}
resolved = {
    str(ipaddress.ip_address(item[4][0]))
    for item in socket.getaddrinfo(domain, 443, type=socket.SOCK_STREAM)
}
matched = local & resolved
if not matched:
    sys.exit(
        "Deploy bloqueado: servidor errado. "
        f"{domain} aponta para {sorted(resolved)}, mas este host possui {sorted(local)}."
    )
print(f"Destino de producao confirmado: {domain} -> {', '.join(sorted(matched))}")
PY

operator_user="${SUDO_USER:-unknown}"
cd /opt/petshop
exec env -i \
  PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin \
  HOME=/root USER=root LOGNAME=root SUDO_USER="$operator_user" \
  APP_DIR=/opt/petshop DEPLOY_PUBLIC_DOMAIN=corepet.com.br \
  PUBLIC_HEALTH_URL=https://corepet.com.br/api/health \
  bash scripts/auditar_comando_producao.sh \
  --action deploy.production \
  --reason publicar-main-validada \
  --label deploy-seguro-corepet \
  -- bash scripts/deploy_producao_seguro.sh
WRAPPER

printf '%s ALL=(root) NOPASSWD: %s\n' "$OPERATOR_USER" "$WRAPPER_PATH" >"$sudoers_tmp"
chmod 0440 "$sudoers_tmp"
visudo -cf "$sudoers_tmp" >/dev/null

install -o root -g root -m 0755 "$wrapper_tmp" "$WRAPPER_PATH"
install -o root -g root -m 0440 "$sudoers_tmp" "$SUDOERS_FILE"
visudo -cf "$SUDOERS_FILE" >/dev/null

echo "Wrapper de deploy instalado em $WRAPPER_PATH"
