from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
NGINX_CONF = ROOT / "nginx" / "nginx.conf"
SECURITY_HEADERS = ROOT / "nginx" / "includes" / "security-headers.conf"
COMPOSE_PROD = ROOT / "docker-compose.prod.yml"
GITIGNORE = ROOT / ".gitignore"
APP_MOBILE_CONFIG = ROOT / "app-mobile" / "src" / "config.ts"
APP_MOBILE_EAS = ROOT / "app-mobile" / "eas.json"
ECOMMERCE_AUTH_RECOVERY = (
    ROOT / "backend" / "app" / "routes" / "ecommerce_auth_recovery.py"
)
ECOMMERCE_NOTIFY = ROOT / "backend" / "app" / "routes" / "ecommerce_notify_routes.py"


def test_prod_nginx_accepts_corepet_and_legacy_domains():
    nginx_conf = NGINX_CONF.read_text(encoding="utf-8")
    app_locations = (
        ROOT / "nginx" / "includes" / "app-server-locations.conf"
    ).read_text(encoding="utf-8")

    assert "server_name mlprohub.com.br www.mlprohub.com.br;" in nginx_conf
    assert "server_name corepet.com.br www.corepet.com.br;" in nginx_conf

    assert "include /etc/nginx/includes/cloudflare-allowlist.conf;" in nginx_conf
    assert "include /etc/nginx/includes/app-server-locations.conf;" in nginx_conf
    assert "ssl_certificate /etc/nginx/ssl/fullchain.pem;" in nginx_conf
    assert "ssl_certificate /etc/nginx/ssl/corepet/fullchain.pem;" in nginx_conf
    assert "return 301 https://$host$request_uri;" in nginx_conf
    assert "proxy_set_header X-Forwarded-Host $host;" in app_locations
    assert "proxy_set_header X-Forwarded-Host $server_name;" not in app_locations
    assert (
        "server_name mlprohub.com.br www.mlprohub.com.br corepet.com.br "
        "www.corepet.com.br;"
    ) not in nginx_conf


def test_prod_nginx_allows_direct_corepet_without_exposing_legacy_origin():
    nginx_conf = NGINX_CONF.read_text(encoding="utf-8")
    cloudflare_allowlist = (
        ROOT / "nginx" / "includes" / "cloudflare-allowlist.conf"
    ).read_text(encoding="utf-8")

    legacy_https_start = nginx_conf.index(
        "listen 443 ssl;\n        http2 on;\n        server_name mlprohub.com.br www.mlprohub.com.br;"
    )
    corepet_https_start = nginx_conf.index(
        "listen 443 ssl;\n        http2 on;\n        server_name corepet.com.br www.corepet.com.br;"
    )
    legacy_server = nginx_conf[legacy_https_start:corepet_https_start]
    corepet_server = nginx_conf[corepet_https_start:]

    assert "include /etc/nginx/includes/cloudflare-allowlist.conf;" in legacy_server
    assert (
        "include /etc/nginx/includes/cloudflare-allowlist.conf;" not in corepet_server
    )
    assert "deny all;" in cloudflare_allowlist


def test_prod_nginx_only_trusts_cloudflare_client_ip_from_cloudflare_networks():
    nginx_conf = NGINX_CONF.read_text(encoding="utf-8")

    assert 'map "$from_cloudflare:$http_cf_connecting_ip" $client_ip {' in nginx_conf
    assert "~^1:(.+)$ $1;" in nginx_conf
    assert "default $remote_addr;" in nginx_conf
    assert "map $http_cf_connecting_ip $client_ip" not in nginx_conf


def test_prod_nginx_rate_limits_each_final_client_ip():
    nginx_conf = NGINX_CONF.read_text(encoding="utf-8")
    app_locations = (
        ROOT / "nginx" / "includes" / "app-server-locations.conf"
    ).read_text(encoding="utf-8")

    assert "limit_req_zone $client_ip zone=api_limit:10m rate=10r/s;" in nginx_conf
    assert "limit_req_zone $client_ip zone=login_limit:10m rate=5r/m;" in nginx_conf
    assert "limit_req_zone $binary_remote_addr" not in nginx_conf
    assert "location /api/auth/login" not in app_locations
    assert "auth/(?:register|login(?:-multitenant)?|forgot-password|reset-password|verify-email|resend-verification)" in app_locations
    assert "ecommerce/auth/(?:registrar|login|esqueci-senha|resetar-senha)" in app_locations
    assert "limit_req zone=login_limit burst=5 nodelay;" in app_locations


def test_prod_nginx_applies_one_consistent_security_header_policy():
    nginx_conf = NGINX_CONF.read_text(encoding="utf-8")
    app_locations = (
        ROOT / "nginx" / "includes" / "app-server-locations.conf"
    ).read_text(encoding="utf-8")
    image_locations = (
        ROOT / "nginx" / "includes" / "product-image-server-locations.conf"
    ).read_text(encoding="utf-8")
    headers = SECURITY_HEADERS.read_text(encoding="utf-8")

    assert "server_tokens off;" in nginx_conf
    assert 'add_header X-Frame-Options "DENY" always;' in headers
    assert 'add_header X-XSS-Protection "0" always;' in headers
    assert (
        'add_header Referrer-Policy "strict-origin-when-cross-origin" always;'
        in headers
    )
    assert "frame-ancestors 'none'" in headers
    assert "object-src 'none'" in headers
    assert "proxy_hide_header X-Frame-Options;" in headers
    assert "proxy_hide_header Referrer-Policy;" in headers
    assert "SAMEORIGIN" not in app_locations
    assert "no-referrer-when-downgrade" not in app_locations
    assert (
        app_locations.count("include /etc/nginx/includes/security-headers.conf;") == 9
    )
    assert (
        image_locations.count("include /etc/nginx/includes/security-headers.conf;") == 2
    )


def test_prod_nginx_preserves_frontend_redirects_from_api_routes():
    app_locations = (
        ROOT / "nginx" / "includes" / "app-server-locations.conf"
    ).read_text(encoding="utf-8")

    assert (
        "proxy_redirect http://localhost:8000/ https://$http_host/api/;"
        in app_locations
    )
    assert (
        "proxy_redirect http://backend:8000/ https://$http_host/api/;" in app_locations
    )
    assert (
        "proxy_redirect http://$http_host/ https://$http_host/api/;"
        not in app_locations
    )
    assert (
        "proxy_redirect https://$http_host/ https://$http_host/api/;"
        not in app_locations
    )


def test_prod_nginx_mounts_certbot_webroot_for_corepet_renewal():
    compose_text = COMPOSE_PROD.read_text(encoding="utf-8")

    assert "./runtime/certbot/www:/var/www/certbot:ro" in compose_text


def test_prod_ssl_certificates_are_not_tracked_by_git():
    gitignore_lines = {
        line.strip()
        for line in GITIGNORE.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    }

    assert "nginx/ssl/" in gitignore_lines


def test_prod_cors_allows_corepet_and_legacy_domains():
    compose_text = COMPOSE_PROD.read_text(encoding="utf-8")

    assert (
        "ALLOWED_ORIGINS: "
        "https://corepet.com.br,https://www.corepet.com.br,"
        "https://mlprohub.com.br,https://www.mlprohub.com.br"
    ) in compose_text
    assert 'APP_NAME: "CorePet ERP"' in compose_text
    assert 'APP_NAME: "Pet Shop Pro"' not in compose_text
    assert "TRUSTED_PROXY_CIDRS:" in compose_text
    assert "172.16.0.0/12" in compose_text


def test_prod_generates_public_links_with_corepet_domain():
    compose_text = COMPOSE_PROD.read_text(encoding="utf-8")

    assert "SYSTEM_NAME: ${SYSTEM_NAME:-CorePet ERP}" in compose_text
    assert "FRONTEND_URL: ${FRONTEND_URL:-https://corepet.com.br}" in compose_text
    assert (
        "ECOMMERCE_BASE_URL: ${ECOMMERCE_BASE_URL:-https://corepet.com.br}"
        in compose_text
    )
    assert "SMTP_FROM" not in compose_text


def test_runtime_defaults_use_corepet_domain():
    mobile_config = APP_MOBILE_CONFIG.read_text(encoding="utf-8")
    eas_config = json.loads(APP_MOBILE_EAS.read_text(encoding="utf-8"))
    ecommerce_auth_recovery = ECOMMERCE_AUTH_RECOVERY.read_text(encoding="utf-8")
    ecommerce_notify = ECOMMERCE_NOTIFY.read_text(encoding="utf-8")

    assert "const DEFAULT_PROD_API_URL = 'https://corepet.com.br/api';" in mobile_config
    assert "https://mlprohub.com.br/api" not in mobile_config

    assert (
        eas_config["build"]["preview"]["env"]["EXPO_PUBLIC_API_URL"]
        == "https://corepet.com.br/api"
    )
    assert (
        eas_config["build"]["production"]["env"]["EXPO_PUBLIC_API_URL"]
        == "https://corepet.com.br/api"
    )

    assert 'or "https://corepet.com.br"' in ecommerce_auth_recovery
    assert 'or "https://mlprohub.com.br"' not in ecommerce_auth_recovery
    assert '"https://corepet.com.br"' in ecommerce_notify
    assert '"https://mlprohub.com.br"' not in ecommerce_notify


def test_prod_serves_product_images_from_corepet_domain():
    nginx_conf = NGINX_CONF.read_text(encoding="utf-8")
    compose_text = COMPOSE_PROD.read_text(encoding="utf-8")
    image_locations_path = (
        ROOT / "nginx" / "includes" / "product-image-server-locations.conf"
    )

    assert image_locations_path.exists()
    image_locations = image_locations_path.read_text(encoding="utf-8")

    assert "server_name img.corepet.com.br;" in nginx_conf
    assert "ssl_certificate /etc/nginx/ssl/corepet-img/fullchain.pem;" in nginx_conf
    assert "ssl_certificate_key /etc/nginx/ssl/corepet-img/privkey.pem;" in nginx_conf
    assert (
        "include /etc/nginx/includes/product-image-server-locations.conf;" in nginx_conf
    )
    assert (
        "proxy_pass http://backend/public/product-images/produtos/;" in image_locations
    )
    assert 'add_header Access-Control-Allow-Origin "*";' in image_locations
    assert (
        "PRODUCT_IMAGE_S3_PUBLIC_BASE_URL: "
        "${PRODUCT_IMAGE_S3_PUBLIC_BASE_URL:-https://img.corepet.com.br}"
    ) in compose_text
    assert "https://img.mlprohub.com.br" not in compose_text
