from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class ServerConfig:
    project_root: Path
    fluxo_script: Path
    default_timeout_seconds: int = 600
    max_output_chars: int = 12000

    @staticmethod
    def load() -> "ServerConfig":
        current = Path(__file__).resolve()
        project_root = current.parents[4]
        fluxo_script = project_root / "scripts" / "fluxo_unico.ps1"
        return ServerConfig(project_root=project_root, fluxo_script=fluxo_script)
