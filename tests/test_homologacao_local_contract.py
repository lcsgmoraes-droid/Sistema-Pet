from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def test_homologacao_uses_isolated_production_like_stack():
    compose = _read("docker-compose.homolog.yml")

    assert "name: corepet-homolog" in compose
    assert "image: postgres:14-alpine" in compose
    assert "dockerfile: Dockerfile.prod" in compose
    assert "ENVIRONMENT: staging" in compose
    assert 'DEBUG: "false"' in compose
    assert "condition: service_completed_successfully" in compose
    assert '"127.0.0.1:18080:80"' in compose
    assert "container_name:" not in compose


def test_homologacao_disables_external_writes_and_real_alerts():
    compose = _read("docker-compose.homolog.yml")

    expected_disabled = [
        'BLING_SYNC_SCHEDULER_ENABLED: "false"',
        'IFOOD_CATALOG_WRITE_ENABLED: "false"',
        'IFOOD_ORDER_OPERATIONS_ENABLED: "false"',
        'IFOOD_ORDER_POLLING_ENABLED: "false"',
        'ECOMMERCE_PAYMENT_GATEWAY_ENABLED: "false"',
        'SEFAZ_ENABLED: "false"',
        'SEFAZ_IMPORTACAO_AUTOMATICA: "false"',
        'OPS_ALERT_WEBHOOK_URL: ""',
        'OPS_ALERT_EMAIL_TO: ""',
    ]
    for setting in expected_disabled:
        assert setting in compose

    assert "corepet.com.br" not in compose
    assert "mlprohub.com.br" not in compose


def test_homologacao_proxy_keeps_api_on_the_same_local_origin():
    nginx = _read("nginx/homolog.local.conf")

    assert "server_name localhost 127.0.0.1" in nginx
    assert "location /api/" in nginx
    assert "proxy_pass http://backend:8000/;" in nginx
    assert "try_files $uri $uri/ /index.html;" in nginx


def test_homologacao_script_protects_reset_and_production():
    script = _read("scripts/homologacao_local.ps1")

    assert "$projectName = 'corepet-homolog'" in script
    assert "if (-not $ConfirmarReset)" in script
    assert "down', '--volumes'" in script
    assert "$env:E2E_ALLOW_PRODUCTION = 'false'" in script
    assert "http://127.0.0.1:18080/api" in script
    assert "sem exibir credenciais" in script
    assert "Show-HomologDiagnostics" in script
    assert "logs --no-color --tail 240 migrate backend" in script


def test_local_secret_file_is_ignored_and_documented():
    gitignore = _read(".gitignore")
    docs = _read("docs/HOMOLOGACAO_LOCAL_ISOLADA.md")

    assert ".env.*.local" in gitignore
    assert ".env.homolog.local" in docs
    assert "Nunca restaurar backup de produção" in docs
    assert "dados pessoais" in docs


def test_homologacao_workflow_uses_disposable_data_without_production_secrets():
    workflow = _read(".github/workflows/homologacao-isolada.yml")

    assert "name: Homologacao Isolada" in workflow
    assert "./scripts/homologacao_local.ps1 -Acao subir" in workflow
    assert "./scripts/homologacao_local.ps1 -Acao validar" in workflow
    assert "-Acao resetar -ConfirmarReset" in workflow
    assert "secrets." not in workflow
    assert "deploy" not in workflow.lower()
