from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
NGINX_CONF = ROOT / "nginx" / "nginx.conf"
COMPOSE_PROD = ROOT / "docker-compose.prod.yml"


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


def test_prod_cors_allows_corepet_and_legacy_domains():
    compose_text = COMPOSE_PROD.read_text(encoding="utf-8")

    assert (
        "ALLOWED_ORIGINS: "
        "https://corepet.com.br,https://www.corepet.com.br,"
        "https://mlprohub.com.br,https://www.mlprohub.com.br"
    ) in compose_text
    assert 'APP_NAME: "CorePet ERP"' in compose_text
    assert 'APP_NAME: "Pet Shop Pro"' not in compose_text
