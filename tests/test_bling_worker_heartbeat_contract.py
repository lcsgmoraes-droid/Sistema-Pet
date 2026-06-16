from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
COMPOSE_PROD = ROOT / "docker-compose.prod.yml"
PROD_DEPLOY_SCRIPT = ROOT / "scripts" / "deploy_producao_seguro.sh"
BLING_WORKER_SCRIPT = ROOT / "backend" / "scripts" / "run_bling_worker.py"

LEGACY_PUBLIC_TMP_HEARTBEAT = "/".join(("", "tmp", "bling_worker_heartbeat"))
PROD_HEARTBEAT_PATH = "/app/data/bling_worker_heartbeat"


def test_bling_worker_heartbeat_uses_app_data_not_public_tmp():
    worker_source = BLING_WORKER_SCRIPT.read_text(encoding="utf-8")
    compose_source = COMPOSE_PROD.read_text(encoding="utf-8")
    deploy_source = PROD_DEPLOY_SCRIPT.read_text(encoding="utf-8")

    assert LEGACY_PUBLIC_TMP_HEARTBEAT not in worker_source
    assert LEGACY_PUBLIC_TMP_HEARTBEAT not in compose_source
    assert LEGACY_PUBLIC_TMP_HEARTBEAT not in deploy_source

    assert (
        'DEFAULT_HEARTBEAT_PATH = ROOT_DIR / "data" / "bling_worker_heartbeat"'
        in worker_source
    )
    assert (
        f"BLING_WORKER_HEARTBEAT_PATH: ${{BLING_WORKER_HEARTBEAT_PATH:-{PROD_HEARTBEAT_PATH}}}"
        in compose_source
    )
    assert PROD_HEARTBEAT_PATH in compose_source
    assert PROD_HEARTBEAT_PATH in deploy_source
