from __future__ import annotations

from typing import Any

import requests
from requests import Response

from frontend_react_mcp.config import ServerConfig
from frontend_react_mcp.models import FrontCheckResult
from frontend_react_mcp.security import redact_text, validate_local_http_url


class HttpService:
    def __init__(self, config: ServerConfig, timeout_seconds: int = 15, verify_tls: bool = False) -> None:
        self.config = config
        self.timeout_seconds = timeout_seconds
        self.verify_tls = verify_tls

    def front_http_check(self, url: str) -> FrontCheckResult:
        try:
            safe_url = validate_local_http_url(url, self.config.allowed_http_hosts)
            response = requests.get(safe_url, timeout=self.timeout_seconds, verify=self.verify_tls)
            ok = response.status_code in {200, 304}
            return FrontCheckResult(
                ok=ok,
                check="front_http_check",
                details={"url": safe_url, "status_code": response.status_code},
            )
        except Exception as exc:
            return FrontCheckResult(
                ok=False,
                check="front_http_check",
                details={"url": url, "error": redact_text(str(exc))},
            )

    def api_auth_smoke(self, url: str) -> FrontCheckResult:
        try:
            safe_url = validate_local_http_url(url, self.config.allowed_http_hosts)
            response = requests.post(
                safe_url,
                json={},
                timeout=self.timeout_seconds,
                verify=self.verify_tls,
            )
            ok = response.status_code in {200, 400, 401, 403, 422}
            return FrontCheckResult(
                ok=ok,
                check="front_api_auth_smoke",
                details={"url": safe_url, "status_code": response.status_code, "body": self._safe_json(response)},
            )
        except Exception as exc:
            return FrontCheckResult(
                ok=False,
                check="front_api_auth_smoke",
                details={"url": url, "error": redact_text(str(exc))},
            )

    def _safe_json(self, response: Response) -> Any:
        try:
            return response.json()
        except Exception:
            return {"text": redact_text(response.text[:1000])}
