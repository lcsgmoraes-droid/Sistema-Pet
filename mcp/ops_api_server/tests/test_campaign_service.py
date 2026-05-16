from pathlib import Path

from ops_api_mcp.config import ServerConfig
from ops_api_mcp.services.campaign_service import CampaignService


class FakeDockerService:
    def __init__(self) -> None:
        self.calls = []

    def exec(self, container, cmd, timeout_seconds=20):
        self.calls.append((container, cmd, timeout_seconds))
        sql = cmd[-1]
        if "SELECT id FROM tenants" in sql:
            return {"ok": True, "stdout": "11111111-1111-1111-1111-111111111111\n", "stderr": "", "exit_code": 0}
        return {"ok": True, "stdout": "INSERT 0 1", "stderr": "", "exit_code": 0}


def _service(tmp_path: Path):
    config = ServerConfig(
        project_root=tmp_path,
        fluxo_script=tmp_path / "fluxo_unico.ps1",
        dev_postgres_container="postgres-dev",
        dev_db_user="postgres",
        dev_db_name="petshop_dev",
    )
    docker = FakeDockerService()
    return CampaignService(config, docker), docker


def test_campaign_enqueue_rejects_unknown_event(tmp_path):
    service, _docker = _service(tmp_path)

    result = service.enqueue_test_event("drop_table")

    assert result["ok"] is False
    assert "nao permitido" in result["error"]


def test_campaign_enqueue_rejects_invalid_json(tmp_path):
    service, _docker = _service(tmp_path)

    result = service.enqueue_test_event("purchase_completed", payload_json="{")

    assert result["ok"] is False
    assert "payload_json invalido" in result["error"]


def test_campaign_enqueue_uses_configured_database_user(tmp_path):
    service, docker = _service(tmp_path)

    result = service.enqueue_test_event("purchase_completed", payload_json='{"total":150}')

    assert result["ok"] is True
    container, cmd, _timeout = docker.calls[-1]
    assert container == "postgres-dev"
    assert cmd[:5] == ["psql", "-U", "postgres", "-d", "petshop_dev"]
    assert "'purchase_completed'" in cmd[-1]
    assert "'{\"total\":150}'::jsonb" in cmd[-1]
