from pathlib import Path

from frontend_react_mcp.config import ServerConfig
from frontend_react_mcp.services.frontend_service import FrontendService


def test_dev_smoke_blocks_unapproved_host(tmp_path: Path):
    service = FrontendService(
        ServerConfig(
            project_root=tmp_path,
            frontend_root=tmp_path / "frontend",
            allowed_dev_hosts=("127.0.0.1",),
        )
    )

    result = service.run_dev_smoke(host="0.0.0.0")

    assert result.ok is False
    assert result.exit_code == 126
    assert "Host nao permitido" in result.stderr
