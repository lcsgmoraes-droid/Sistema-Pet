from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def test_catalog_worker_is_deployed_in_safe_disabled_mode():
    compose = read("docker-compose.prod.yml")
    runner = read("backend/scripts/run_catalogo_mestre_worker.py")

    assert "worker-catalogo:" in compose
    assert "petshop-prod-worker-catalogo" in compose
    assert "CATALOGO_MESTRE_WORKER_ENABLED:-false" in compose
    assert "CATALOGO_MESTRE_WORKER_APPLY_ENABLED:-false" in compose
    assert "CATALOGO_MESTRE_WORKER_DAILY_LIMIT:-25" in compose
    assert "OPENAI_API_KEY: ${OPENAI_API_KEY:-}" in compose
    assert "catalogo_mestre_worker_heartbeat" in compose
    assert "catalogo_mestre_worker_heartbeat" in runner


def test_deploy_waits_for_catalog_worker_heartbeat():
    deploy = read("scripts/deploy_producao_seguro.sh")
    runtime_source = deploy.replace('\\"', '"').replace("\\$", "$")

    assert "up -d backend worker-bling worker-catalogo" in deploy
    assert 'test -n "$CATALOGO_MESTRE_WORKER_HEARTBEAT_PATH"' in runtime_source
    assert 'test -f "$CATALOGO_MESTRE_WORKER_HEARTBEAT_PATH"' in runtime_source


def test_operations_monitor_catalog_worker():
    status = read("scripts/prod_status.sh")
    watchdog = read("scripts/ops_host_watchdog.sh")

    assert "postgres backend worker-bling worker-catalogo nginx" in status
    assert "container_health petshop-prod-worker-catalogo" in watchdog
    assert "compose restart worker-catalogo" in watchdog
