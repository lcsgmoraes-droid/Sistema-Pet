"""Cliente minimo e seguro para a iFood Merchant API."""

from __future__ import annotations

import threading
import time
from typing import Any, Literal

import httpx


class IfoodClientError(RuntimeError):
    """Erro sanitizado da integracao, sem token ou segredo na mensagem."""

    def __init__(self, message: str, *, status_code: int | None = None):
        super().__init__(message)
        self.status_code = status_code


class IfoodClient:
    def __init__(
        self,
        *,
        client_id: str,
        client_secret: str,
        base_url: str = "https://merchant-api.ifood.com.br",
        timeout_seconds: int = 15,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        self.client_id = client_id.strip()
        self.client_secret = client_secret.strip()
        self.base_url = base_url.rstrip("/")
        self._client = httpx.Client(
            base_url=self.base_url,
            timeout=max(1, timeout_seconds),
            transport=transport,
        )
        self._access_token: str | None = None
        self._token_expires_at = 0.0
        self._token_lock = threading.Lock()

    def close(self) -> None:
        self._client.close()

    def __enter__(self) -> "IfoodClient":
        return self

    def __exit__(self, *_args: object) -> None:
        self.close()

    def _credentials_ready(self) -> None:
        if not self.client_id or not self.client_secret:
            raise IfoodClientError(
                "Credenciais do aplicativo iFood nao configuradas no servidor."
            )

    def _token(self) -> str:
        self._credentials_ready()
        with self._token_lock:
            if self._access_token and time.monotonic() < self._token_expires_at - 60:
                return self._access_token
            try:
                response = self._client.post(
                    "/authentication/v1.0/oauth/token",
                    data={
                        "grantType": "client_credentials",
                        "clientId": self.client_id,
                        "clientSecret": self.client_secret,
                    },
                )
            except httpx.HTTPError as exc:
                raise IfoodClientError("Nao foi possivel conectar ao iFood.") from exc
            if response.status_code >= 400:
                raise IfoodClientError(
                    "O iFood recusou as credenciais do aplicativo.",
                    status_code=response.status_code,
                )
            try:
                data = response.json()
            except ValueError as exc:
                raise IfoodClientError(
                    "O iFood retornou uma resposta de autenticacao invalida."
                ) from exc
            token = str(data.get("accessToken") or "").strip()
            if not token:
                raise IfoodClientError(
                    "O iFood nao retornou um token de acesso valido."
                )
            try:
                expires_in = max(60, int(data.get("expiresIn") or 300))
            except (TypeError, ValueError):
                expires_in = 300
            self._access_token = token
            self._token_expires_at = time.monotonic() + expires_in
            return token

    def _request(self, method: str, path: str, **kwargs: Any) -> httpx.Response:
        headers = dict(kwargs.pop("headers", {}))
        headers["Authorization"] = f"Bearer {self._token()}"
        try:
            response = self._client.request(method, path, headers=headers, **kwargs)
        except httpx.HTTPError as exc:
            raise IfoodClientError("Nao foi possivel conectar ao iFood.") from exc
        if response.status_code >= 400:
            if response.status_code == 429:
                message = "Limite de processamento do iFood atingido; aguarde a proxima janela."
            elif response.status_code in {401, 403}:
                message = "O aplicativo CorePet nao tem autorizacao para esta operacao no iFood."
            else:
                message = "O iFood recusou a operacao solicitada."
            raise IfoodClientError(message, status_code=response.status_code)
        return response

    def list_merchants(self) -> Any:
        response = self._request("GET", "/merchant/v1.0/merchants")
        try:
            return response.json()
        except ValueError as exc:
            raise IfoodClientError(
                "O iFood retornou uma lista de lojas invalida."
            ) from exc

    def ingest_items(
        self,
        merchant_id: str,
        items: list[dict[str, Any]],
        *,
        method: Literal["POST", "PATCH"],
    ) -> dict[str, Any]:
        if not items:
            raise IfoodClientError("Nenhum item elegivel para enviar ao iFood.")
        path = f"/item/v1.0/ingestion/{merchant_id}"
        params = {"reset": "false"} if method == "POST" else None
        response = self._request(method, path, params=params, json=items)
        result: dict[str, Any] = {"status_code": response.status_code}
        if response.content:
            try:
                result["response"] = response.json()
            except ValueError:
                result["response"] = None
        return result
