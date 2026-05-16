from pathlib import Path

from ops_api_mcp.config import ServerConfig
from ops_api_mcp.services.command_service import CommandService


def _config(tmp_path: Path, *, allow_prod_actions: bool = False) -> ServerConfig:
    return ServerConfig(
        project_root=tmp_path,
        fluxo_script=tmp_path / "fluxo_unico.ps1",
        allow_prod_actions=allow_prod_actions,
    )


def test_prod_up_is_blocked_by_default(tmp_path):
    result = CommandService(_config(tmp_path)).run_fluxo("prod-up")

    assert result.ok is False
    assert result.exit_code == 126
    assert "bloqueada" in result.stderr


def test_prod_up_requires_exact_confirmation_when_enabled(tmp_path):
    result = CommandService(_config(tmp_path, allow_prod_actions=True)).run_fluxo(
        "prod-up",
        confirmacao="confirmo",
    )

    assert result.ok is False
    assert result.exit_code == 126
    assert "Confirmacao invalida" in result.stderr
