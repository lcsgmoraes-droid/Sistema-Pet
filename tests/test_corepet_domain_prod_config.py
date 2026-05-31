from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
NGINX_CONF = ROOT / "nginx" / "nginx.conf"
COMPOSE_PROD = ROOT / "docker-compose.prod.yml"
GITIGNORE = ROOT / ".gitignore"


def test_prod_nginx_accepts_corepet_and_legacy_domains():
    nginx_conf = NGINX_CONF.read_text(encoding="utf-8")
    app_locations = (ROOT / "nginx" / "includes" / "app-server-locations.conf").read_text(
        encoding="utf-8"
    )

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
    cloudflare_allowlist = (ROOT / "nginx" / "includes" / "cloudflare-allowlist.conf").read_text(
        encoding="utf-8"
    )

    legacy_https_start = nginx_conf.index(
        "listen 443 ssl;\n        http2 on;\n        server_name mlprohub.com.br www.mlprohub.com.br;"
    )
    corepet_https_start = nginx_conf.index(
        "listen 443 ssl;\n        http2 on;\n        server_name corepet.com.br www.corepet.com.br;"
    )
    legacy_server = nginx_conf[legacy_https_start:corepet_https_start]
    corepet_server = nginx_conf[corepet_https_start:]

    assert "include /etc/nginx/includes/cloudflare-allowlist.conf;" in legacy_server
    assert "include /etc/nginx/includes/cloudflare-allowlist.conf;" not in corepet_server
    assert "deny all;" in cloudflare_allowlist


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


def test_prod_generates_public_links_with_corepet_domain():
    compose_text = COMPOSE_PROD.read_text(encoding="utf-8")

    assert "SYSTEM_NAME: ${SYSTEM_NAME:-CorePet ERP}" in compose_text
    assert "FRONTEND_URL: ${FRONTEND_URL:-https://corepet.com.br}" in compose_text
    assert "ECOMMERCE_BASE_URL: ${ECOMMERCE_BASE_URL:-https://corepet.com.br}" in compose_text
    assert "SMTP_FROM" not in compose_text


def test_prod_serves_product_images_from_corepet_domain():
    nginx_conf = NGINX_CONF.read_text(encoding="utf-8")
    compose_text = COMPOSE_PROD.read_text(encoding="utf-8")
    image_locations_path = ROOT / "nginx" / "includes" / "product-image-server-locations.conf"

    assert image_locations_path.exists()
    image_locations = image_locations_path.read_text(encoding="utf-8")

    assert "server_name img.corepet.com.br;" in nginx_conf
    assert "ssl_certificate /etc/nginx/ssl/corepet-img/fullchain.pem;" in nginx_conf
    assert "ssl_certificate_key /etc/nginx/ssl/corepet-img/privkey.pem;" in nginx_conf
    assert "include /etc/nginx/includes/product-image-server-locations.conf;" in nginx_conf
    assert "proxy_pass http://backend/public/product-images/produtos/;" in image_locations
    assert 'add_header Access-Control-Allow-Origin "*";' in image_locations
    assert (
        "PRODUCT_IMAGE_S3_PUBLIC_BASE_URL: "
        "${PRODUCT_IMAGE_S3_PUBLIC_BASE_URL:-https://img.corepet.com.br}"
    ) in compose_text
    assert "https://img.mlprohub.com.br" not in compose_text
