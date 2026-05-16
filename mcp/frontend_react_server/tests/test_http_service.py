from pathlib import Path

from frontend_react_mcp.config import ServerConfig
from frontend_react_mcp.services.http_service import HttpService


def test_http_service_blocks_external_url(tmp_path: Path):
    service = HttpService(
        ServerConfig(
            project_root=tmp_path,
            frontend_root=tmp_path / "frontend",
            allowed_http_hosts=("localhost",),
        )
    )

    result = service.front_http_check("https://example.com")

    assert result.ok is False
    assert "Host nao permitido" in result.details["error"]
