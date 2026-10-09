#!/usr/bin/env bash
set -Eeuo pipefail

APP_DIR="${APP_DIR:-/opt/petshop}"
OPERATOR_USER="${OPERATOR_USER:-petdeploy}"
DEPLOY_PUBLIC_KEY_FILE="${DEPLOY_PUBLIC_KEY_FILE:-}"
NODE_MAJOR="${NODE_MAJOR:-22}"

fail() {
  printf 'bootstrap_status=failed\n' >&2
  printf 'bootstrap_error=%s\n' "$*" >&2
  exit 1
}

if [[ "$(id -u)" != "0" ]]; then
  fail "execute como root na VPS nova"
fi

if [[ "${HOSTINGER_BOOTSTRAP_CONFIRM:-}" != "HOSTINGER_BOOTSTRAP" ]]; then
  fail "defina HOSTINGER_BOOTSTRAP_CONFIRM=HOSTINGER_BOOTSTRAP para confirmar o alvo"
fi

if [[ ! -r /etc/os-release ]]; then
  fail "/etc/os-release nao encontrado"
fi

# shellcheck disable=SC1091
source /etc/os-release
if [[ "${ID:-}" != "ubuntu" ]]; then
  fail "este preparador suporta somente Ubuntu"
fi

case "${VERSION_ID:-}" in
  22.04|24.04) ;;
  *) fail "use Ubuntu 22.04 ou 24.04 LTS" ;;
esac

if [[ -n "$DEPLOY_PUBLIC_KEY_FILE" && ! -s "$DEPLOY_PUBLIC_KEY_FILE" ]]; then
  fail "arquivo de chave publica nao encontrado ou vazio"
fi

export DEBIAN_FRONTEND=noninteractive
apt-get update
apt-get -y upgrade
apt-get install -y \
  ca-certificates \
  curl \
  fail2ban \
  git \
  gnupg \
  gzip \
  jq \
  openssl \
  python3 \
  rsync \
  tar \
  ufw \
  unzip

if ! command -v docker >/dev/null 2>&1; then
  install -m 0755 -d /etc/apt/keyrings
  curl -fsSL https://download.docker.com/linux/ubuntu/gpg \
    | gpg --dearmor --yes -o /etc/apt/keyrings/docker.gpg
  chmod a+r /etc/apt/keyrings/docker.gpg
  architecture="$(dpkg --print-architecture)"
  codename="${VERSION_CODENAME:?VERSION_CODENAME ausente}"
  printf '%s\n' \
    "deb [arch=$architecture signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu $codename stable" \
    >/etc/apt/sources.list.d/docker.list
  apt-get update
  apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
fi

node_compatible="false"
if command -v node >/dev/null 2>&1; then
  if node -e 'const [a,b,c]=process.versions.node.split(".").map(Number); process.exit(((a===20&&(b>19||(b===19&&c>=4)))||(a===22&&b>=12)||a>22)?0:1)'; then
    node_compatible="true"
  fi
fi

if [[ "$node_compatible" != "true" ]]; then
  install -m 0755 -d /etc/apt/keyrings
  curl -fsSL https://deb.nodesource.com/gpgkey/nodesource-repo.gpg.key \
    | gpg --dearmor --yes -o /etc/apt/keyrings/nodesource.gpg
  chmod a+r /etc/apt/keyrings/nodesource.gpg
  printf '%s\n' \
    "deb [signed-by=/etc/apt/keyrings/nodesource.gpg] https://deb.nodesource.com/node_${NODE_MAJOR}.x nodistro main" \
    >/etc/apt/sources.list.d/nodesource.list
  apt-get update
  apt-get install -y nodejs
fi

if ! id "$OPERATOR_USER" >/dev/null 2>&1; then
  useradd --create-home --shell /bin/bash "$OPERATOR_USER"
fi
usermod -aG docker "$OPERATOR_USER"

operator_home="$(getent passwd "$OPERATOR_USER" | cut -d: -f6)"
install -d -o "$OPERATOR_USER" -g "$OPERATOR_USER" -m 0700 "$operator_home/.ssh"
if [[ -n "$DEPLOY_PUBLIC_KEY_FILE" ]]; then
  install -o "$OPERATOR_USER" -g "$OPERATOR_USER" -m 0600 \
    "$DEPLOY_PUBLIC_KEY_FILE" "$operator_home/.ssh/authorized_keys"
fi

install -d -o root -g docker -m 0750 "$APP_DIR"
install -d -o root -g root -m 0700 /etc/petshop

timedatectl set-timezone America/Sao_Paulo
systemctl enable --now docker
systemctl enable --now fail2ban

# Nao limpa regras existentes. Apenas garante as portas necessarias.
ufw allow OpenSSH
ufw allow 80/tcp
ufw allow 443/tcp
ufw --force enable

docker --version
docker compose version
node --version
npm --version
ufw status verbose

printf 'bootstrap_status=ok\n'
printf 'bootstrap_operator=%s\n' "$OPERATOR_USER"
printf 'bootstrap_app_dir=%s\n' "$APP_DIR"
printf 'bootstrap_next=clonar origin/main e executar migration_inventory.sh target\n'

