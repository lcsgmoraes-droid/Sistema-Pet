from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
NGINX_CONF = ROOT / "nginx" / "nginx.conf"
COMPOSE_PROD = ROOT / "docker-compose.prod.yml"


def test_prod_nginx_accepts_corepet_and_legacy_domains():
    nginx_conf = NGINX_CONF.read_text(encoding="utf-8")

    expected_server_name = (
        "server_name mlprohub.com.br www.mlprohub.com.br "
        "corepet.com.br www.corepet.com.br;"
    )

    assert nginx_conf.count(expected_server_name) == 2
    assert "return 301 https://$host$request_uri;" in nginx_conf
    assert "proxy_set_header X-Forwarded-Host $host;" in nginx_conf
    assert "proxy_set_header X-Forwarded-Host $server_name;" not in nginx_conf


def test_prod_cors_allows_corepet_and_legacy_domains():
    compose_text = COMPOSE_PROD.read_text(encoding="utf-8")

    assert (
        "ALLOWED_ORIGINS: "
        "https://corepet.com.br,https://www.corepet.com.br,"
        "https://mlprohub.com.br,https://www.mlprohub.com.br"
    ) in compose_text
    assert 'APP_NAME: "CorePet ERP"' in compose_text
    assert 'APP_NAME: "Pet Shop Pro"' not in compose_text
