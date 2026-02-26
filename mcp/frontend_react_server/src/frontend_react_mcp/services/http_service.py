from __future__ import annotations

from typing import Any

import requests
from requests import Response

from frontend_react_mcp.models import FrontCheckResult


class HttpService:
    def __init__(self, timeout_seconds: int = 15, verify_tls: bool = False) -> None:
        self.timeout_seconds = timeout_seconds
        self.verify_tls = verify_tls

    def front_http_check(self, url: str = "http://localhost:5173") -> FrontCheckResult:
        try:
            response = requests.get(url, timeout=self.timeout_seconds, verify=self.verify_tls)
            ok = response.status_code in {200, 304}
            return FrontCheckResult(
                ok=ok,
                check="front_http_check",
                details={"url": url, "status_code": response.status_code},
            )
        except Exception as exc:
            return FrontCheckResult(
                ok=False,
                check="front_http_check",
                details={"url": url, "error": str(exc)},
            )

    def api_auth_smoke(self, url: str = "https://localhost/api/auth/login-multitenant") -> FrontCheckResult:
        try:
            response = requests.post(
                url,
                json={},
                timeout=self.timeout_seconds,
                verify=self.verify_tls,
            )
            ok = response.status_code in {200, 400, 401, 403, 422}
            return FrontCheckResult(
                ok=ok,
                check="front_api_auth_smoke",
                details={"url": url, "status_code": response.status_code, "body": self._safe_json(response)},
            )
        except Exception as exc:
            return FrontCheckResult(
                ok=False,
                check="front_api_auth_smoke",
                details={"url": url, "error": str(exc)},
            )

    def _safe_json(self, response: Response) -> Any:
        try:
            return response.json()
        except Exception:
            return {"text": response.text[:1000]}
