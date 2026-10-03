#!/usr/bin/env bash
set -euo pipefail

APP_DIR="${APP_DIR:-/opt/petshop}"
NGINX_CONTAINER="${NGINX_CONTAINER:-petshop-prod-nginx}"

install_certificate() {
  local certificate_name="$1"
  local destination="$2"
  local source="/etc/letsencrypt/live/${certificate_name}"

  install -d -m 755 "${destination}"
  install -m 644 "${source}/fullchain.pem" "${destination}/fullchain.pem"
  install -m 600 "${source}/privkey.pem" "${destination}/privkey.pem"
}

install_certificate "mlprohub.com.br" "${APP_DIR}/nginx/ssl"
install_certificate "corepet.com.br" "${APP_DIR}/nginx/ssl/corepet"
install_certificate "corepet-img" "${APP_DIR}/nginx/ssl/corepet-img"

docker exec "${NGINX_CONTAINER}" nginx -t
docker exec "${NGINX_CONTAINER}" nginx -s reload
