from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class ServerConfig:
    project_root: Path
    frontend_root: Path
    default_timeout_seconds: int = 600
    max_output_chars: int = 12000

    @staticmethod
    def load() -> "ServerConfig":
        current = Path(__file__).resolve()
        project_root = current.parents[4]
        frontend_root = project_root / "frontend"
        return ServerConfig(project_root=project_root, frontend_root=frontend_root)
