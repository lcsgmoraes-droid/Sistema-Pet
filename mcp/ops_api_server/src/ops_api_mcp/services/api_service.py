from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import requests
from requests import Response

from ops_api_mcp.config import ServerConfig
from ops_api_mcp.models import ApiResult
from ops_api_mcp.security import redact_text, redact_value, validate_local_http_url


@dataclass(frozen=True)
class ApiDefaults:
    timeout_seconds: int = 15
    verify_tls: bool = False


class ApiService:
    def __init__(self, config: ServerConfig, defaults: ApiDefaults | None = None) -> None:
        self.config = config
        self.defaults = defaults or ApiDefaults()

    def health_check(self, url: str) -> ApiResult:
        try:
            safe_url = validate_local_http_url(url, self.config.allowed_http_hosts)
            response = requests.get(
                safe_url,
                timeout=self.defaults.timeout_seconds,
                verify=self.defaults.verify_tls,
            )
            return ApiResult(
                ok=response.status_code == 200,
                operation="health_check",
                status_code=response.status_code,
                url=safe_url,
                details={"body": self._safe_json(response)},
            )
        except Exception as exc:
            return ApiResult(
                ok=False,
                operation="health_check",
                status_code=None,
                url=url,
                details={"error": redact_text(str(exc))},
            )

    def auth_route_smoke(self, url: str) -> ApiResult:
        try:
            safe_url = validate_local_http_url(url, self.config.allowed_http_hosts)
            response = requests.post(
                safe_url,
                json={},
                timeout=self.defaults.timeout_seconds,
                verify=self.defaults.verify_tls,
            )
            ok = response.status_code in {200, 400, 401, 403, 422}
            return ApiResult(
                ok=ok,
                operation="auth_route_smoke",
                status_code=response.status_code,
                url=safe_url,
                details={"body": self._safe_json(response)},
            )
        except Exception as exc:
            return ApiResult(
                ok=False,
                operation="auth_route_smoke",
                status_code=None,
                url=url,
                details={"error": redact_text(str(exc))},
            )

    def validate_tabs_permissions(
        self,
        base_url: str,
        email: str,
        password: str,
        required_permissions: list[str] | None = None,
    ) -> ApiResult:
        required = required_permissions or [
            "financeiro.dashboard",
            "relatorios.financeiro",
            "cadastros.cargos",
            "configuracoes.editar",
        ]

        try:
            safe_base_url = validate_local_http_url(base_url.rstrip("/"), self.config.allowed_http_hosts)
            login_url = f"{safe_base_url}/auth/login-multitenant"
            select_url = f"{safe_base_url}/auth/select-tenant"
            me_url = f"{safe_base_url}/auth/me-multitenant"

            login_response = requests.post(
                login_url,
                json={"email": email, "password": password},
                timeout=self.defaults.timeout_seconds,
                verify=self.defaults.verify_tls,
            )

            if login_response.status_code != 200:
                return ApiResult(
                    ok=False,
                    operation="validate_tabs_permissions",
                    status_code=login_response.status_code,
                    url=login_url,
                    details={"step": "login", "body": self._safe_json(login_response)},
                )

            login_data = self._raw_json(login_response)
            temp_token = login_data.get("access_token")
            tenants = login_data.get("tenants") or []

            if not temp_token or not tenants:
                return ApiResult(
                    ok=False,
                    operation="validate_tabs_permissions",
                    status_code=login_response.status_code,
                    url=login_url,
                    details={"step": "login", "error": "token ou tenants ausentes"},
                )

            tenant_id = tenants[0].get("id")
            select_response = requests.post(
                select_url,
                json={"tenant_id": tenant_id},
                headers={"Authorization": f"Bearer {temp_token}"},
                timeout=self.defaults.timeout_seconds,
                verify=self.defaults.verify_tls,
            )

            if select_response.status_code != 200:
                return ApiResult(
                    ok=False,
                    operation="validate_tabs_permissions",
                    status_code=select_response.status_code,
                    url=select_url,
                    details={"step": "select_tenant", "body": self._safe_json(select_response)},
                )

            final_token = self._raw_json(select_response).get("access_token")
            if not final_token:
                return ApiResult(
                    ok=False,
                    operation="validate_tabs_permissions",
                    status_code=select_response.status_code,
                    url=select_url,
                    details={"step": "select_tenant", "error": "access_token final ausente"},
                )

            me_response = requests.get(
                me_url,
                headers={"Authorization": f"Bearer {final_token}"},
                timeout=self.defaults.timeout_seconds,
                verify=self.defaults.verify_tls,
            )

            if me_response.status_code != 200:
                return ApiResult(
                    ok=False,
                    operation="validate_tabs_permissions",
                    status_code=me_response.status_code,
                    url=me_url,
                    details={"step": "me", "body": self._safe_json(me_response)},
                )

            me_data = self._raw_json(me_response)
            permissions = set(me_data.get("permissions") or [])
            missing = [perm for perm in required if perm not in permissions]

            return ApiResult(
                ok=len(missing) == 0,
                operation="validate_tabs_permissions",
                status_code=200,
                url=me_url,
                details={
                    "tenant_id": tenant_id,
                    "permissions_count": len(permissions),
                    "required_permissions": required,
                    "missing_permissions": missing,
                    "user_email": me_data.get("email"),
                },
            )

        except Exception as exc:
            return ApiResult(
                ok=False,
                operation="validate_tabs_permissions",
                status_code=None,
                url=base_url,
                details={"error": redact_text(str(exc))},
            )

    def _safe_json(self, response: Response) -> Any:
        try:
            return redact_value(response.json())
        except Exception:
            return {"text": redact_text(response.text[:2000])}

    def _raw_json(self, response: Response) -> Any:
        try:
            return response.json()
        except Exception:
            return {}
