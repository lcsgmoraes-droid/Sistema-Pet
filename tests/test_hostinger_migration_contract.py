from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def read(relative_path: str) -> str:
    return (ROOT / relative_path).read_text(encoding="utf-8")


def test_migration_runbook_covers_public_surfaces_and_persistent_data():
    source = read("docs/MIGRACAO_DIGITALOCEAN_HOSTINGER.md")

    for expected in (
        "corepet.com.br",
        "www.corepet.com.br",
        "img.corepet.com.br",
        "mlprohub.com.br",
        "Registro.br",
        "Cloudflare",
        "app mobile",
        "ecommerce",
        "/opt/petshop/.env",
        "/opt/petshop/backend/uploads/",
        "/opt/petshop/backend/data/",
        "/opt/petshop/backend/secrets/",
        "PAYMENT_CONFIG_ENCRYPTION_KEY",
        "Rollback",
    ):
        assert expected in source


def test_bootstrap_requires_explicit_target_confirmation_and_avoids_cleanup():
    source = read("scripts/bootstrap_hostinger_vps.sh")

    assert "HOSTINGER_BOOTSTRAP_CONFIRM" in source
    assert "HOSTINGER_BOOTSTRAP" in source
    assert "ufw --force reset" not in source
    assert "docker system prune" not in source
    assert "rm -rf" not in source
    assert "git push" not in source
    assert "192.241.150.121" not in source


def test_inventory_is_read_only_and_does_not_print_env_contents():
    source = read("scripts/migration_inventory.sh")

    assert "source|target" in source
    assert "pg_database_size" in source
    assert "backend/uploads" in source
    assert "fullchain.pem" in source
    assert 'cat "$env_file"' not in source
    assert "docker compose up" not in source
    assert "docker compose stop" not in source


def test_target_smoke_uses_resolve_without_changing_dns():
    source = read("scripts/test_hostinger_target.ps1")

    assert "--resolve" in source
    assert "corepet.com.br" in source
    assert "www.corepet.com.br" in source
    assert "img.corepet.com.br" in source
    assert "Resolve-DnsName" not in source
    assert "Set-Dns" not in source


def test_certbot_hook_installs_all_certificates_and_reloads_nginx():
    source = read("scripts/certbot_deploy_nginx.sh")

    assert "/etc/letsencrypt/live/${certificate_name}" in source
    assert 'install_certificate "mlprohub.com.br"' in source
    assert 'install_certificate "corepet.com.br"' in source
    assert 'install_certificate "corepet-img"' in source
    assert 'nginx -t' in source
    assert 'nginx -s reload' in source
    assert "rm -rf" not in source
