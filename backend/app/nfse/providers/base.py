from __future__ import annotations

from typing import Any, Protocol


class NfseProviderError(RuntimeError):
    def __init__(
        self, message: str, *, status_code: int = 502, code: str | None = None
    ):
        super().__init__(message)
        self.status_code = status_code
        self.code = code


class NfseProvider(Protocol):
    def issue(self, reference: str, payload: dict[str, Any]) -> dict[str, Any]: ...

    def query(self, reference: str) -> dict[str, Any]: ...

    def cancel(self, reference: str, justification: str) -> dict[str, Any]: ...
