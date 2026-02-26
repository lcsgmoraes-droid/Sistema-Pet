from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Dict


@dataclass
class CommandResult:
    ok: bool
    action: str
    exit_code: int
    stdout: str
    stderr: str
    duration_ms: int

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class ApiResult:
    ok: bool
    operation: str
    status_code: int | None
    url: str
    details: Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
