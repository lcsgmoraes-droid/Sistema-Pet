from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
COMPOSE_PROD = ROOT / "docker-compose.prod.yml"
PROD_DEPLOY_SCRIPT = ROOT / "scripts" / "deploy_producao_seguro.sh"
BLING_WORKER_SCRIPT = ROOT / "backend" / "scripts" / "run_bling_worker.py"
BACKEND_REQUIREMENTS = ROOT / "backend" / "requirements.txt"
GITIGNORE = ROOT / ".gitignore"

LEGACY_PUBLIC_TMP_HEARTBEAT = "/".join(("", "tmp", "bling_worker_heartbeat"))
PROD_HEARTBEAT_PATH = "/app/data/bling_worker_heartbeat"


def test_bling_worker_heartbeat_uses_app_data_not_public_tmp():
    worker_source = BLING_WORKER_SCRIPT.read_text(encoding="utf-8")
    compose_source = COMPOSE_PROD.read_text(encoding="utf-8")
    deploy_source = PROD_DEPLOY_SCRIPT.read_text(encoding="utf-8")
    gitignore_source = GITIGNORE.read_text(encoding="utf-8")
    deploy_runtime_source = deploy_source.replace('\\"', '"').replace("\\$", "$")

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
    assert (
        'test -n "$BLING_WORKER_HEARTBEAT_PATH" && '
        'test -f "$BLING_WORKER_HEARTBEAT_PATH"'
    ) in deploy_runtime_source
    assert PROD_HEARTBEAT_PATH in compose_source
    assert "backend/data/*" in gitignore_source


def test_bling_worker_declares_tzlocal_runtime_dependency():
    requirements_source = BACKEND_REQUIREMENTS.read_text(encoding="utf-8")

    assert "APScheduler" in requirements_source
    assert "tzlocal==5.3.1" in requirements_source
    assert "tzlocal==5.4.1" not in requirements_source
