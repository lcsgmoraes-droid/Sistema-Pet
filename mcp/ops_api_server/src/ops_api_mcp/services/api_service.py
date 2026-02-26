from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import requests
from requests import Response

from ops_api_mcp.models import ApiResult


@dataclass(frozen=True)
class ApiDefaults:
    timeout_seconds: int = 15
    verify_tls: bool = False


class ApiService:
    def __init__(self, defaults: ApiDefaults | None = None) -> None:
        self.defaults = defaults or ApiDefaults()

    def health_check(self, url: str) -> ApiResult:
        try:
            response = requests.get(
                url,
                timeout=self.defaults.timeout_seconds,
                verify=self.defaults.verify_tls,
            )
            return ApiResult(
                ok=response.status_code == 200,
                operation="health_check",
                status_code=response.status_code,
                url=url,
                details={"body": self._safe_json(response)},
            )
        except Exception as exc:
            return ApiResult(
                ok=False,
                operation="health_check",
                status_code=None,
                url=url,
                details={"error": str(exc)},
            )

    def auth_route_smoke(self, url: str) -> ApiResult:
        try:
            response = requests.post(
                url,
                json={},
                timeout=self.defaults.timeout_seconds,
                verify=self.defaults.verify_tls,
            )
            ok = response.status_code in {200, 400, 401, 403, 422}
            return ApiResult(
                ok=ok,
                operation="auth_route_smoke",
                status_code=response.status_code,
                url=url,
                details={"body": self._safe_json(response)},
            )
        except Exception as exc:
            return ApiResult(
                ok=False,
                operation="auth_route_smoke",
                status_code=None,
                url=url,
                details={"error": str(exc)},
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

        login_url = f"{base_url.rstrip('/')}/auth/login-multitenant"
        select_url = f"{base_url.rstrip('/')}/auth/select-tenant"
        me_url = f"{base_url.rstrip('/')}/auth/me-multitenant"

        try:
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

            login_data = self._safe_json(login_response)
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

            final_token = self._safe_json(select_response).get("access_token")
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

            me_data = self._safe_json(me_response)
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
                details={"error": str(exc)},
            )

    def _safe_json(self, response: Response) -> Any:
        try:
            return response.json()
        except Exception:
            return {"text": response.text[:2000]}
