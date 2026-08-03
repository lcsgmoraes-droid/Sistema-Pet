from __future__ import annotations

import os
from typing import Any
from urllib.parse import quote

import httpx

from app.config import settings
from app.nfse.providers.base import NfseProviderError


FOCUS_NFE_BASE_URLS = {
    "homologacao": "https://homologacao.focusnfe.com.br",
    "producao": "https://api.focusnfe.com.br",
}


def normalize_environment(value: str | None) -> str:
    environment = (value or "homologacao").strip().lower()
    aliases = {
        "homologation": "homologacao",
        "sandbox": "homologacao",
        "production": "producao",
        "prod": "producao",
    }
    environment = aliases.get(environment, environment)
    if environment not in FOCUS_NFE_BASE_URLS:
        raise NfseProviderError(
            "Ambiente da NFS-e deve ser homologacao ou producao.", status_code=503
        )
    return environment


def focus_token(environment: str) -> str:
    normalized = normalize_environment(environment)
    variable = (
        "FOCUS_NFE_TOKEN_PRODUCAO"
        if normalized == "producao"
        else "FOCUS_NFE_TOKEN_HOMOLOGACAO"
    )
    configured = getattr(settings, variable, "")
    return (os.getenv(variable) or configured or "").strip()


def focus_token_is_configured(environment: str) -> bool:
    return bool(focus_token(environment))


def _error_from_response(response: httpx.Response) -> NfseProviderError:
    try:
        payload = response.json()
    except ValueError:
        payload = {}

    messages: list[str] = []
    code: str | None = None
    if isinstance(payload, dict):
        for key in ("mensagem", "message", "mensagem_sefaz", "erro"):
            value = payload.get(key)
            if value:
                messages.append(str(value).strip())
        errors = payload.get("erros") or payload.get("errors")
        if isinstance(errors, list):
            for item in errors[:3]:
                if isinstance(item, dict):
                    code = (
                        code
                        or str(item.get("codigo") or item.get("code") or "")
                        or None
                    )
                    message = item.get("mensagem") or item.get("message")
                    if message:
                        messages.append(str(message).strip())
                elif item:
                    messages.append(str(item).strip())

    message = "; ".join(dict.fromkeys(item for item in messages if item))
    if not message:
        message = "O emissor recusou a operacao de NFS-e."
    status_code = 422 if response.status_code in {400, 404, 409, 422} else 502
    return NfseProviderError(message, status_code=status_code, code=code)


class FocusNfeProvider:
    """Adaptador pequeno para a API v2 de NFS-e da Focus NFe."""

    def __init__(self, environment: str) -> None:
        self.environment = normalize_environment(environment)
        self.token = focus_token(self.environment)
        if not self.token:
            raise NfseProviderError(
                f"Token da Focus NFe nao configurado para {self.environment}.",
                status_code=503,
            )
        self.base_url = FOCUS_NFE_BASE_URLS[self.environment]

    def _request(
        self,
        method: str,
        path: str,
        *,
        payload: dict[str, Any] | None = None,
        params: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        try:
            response = httpx.request(
                method,
                f"{self.base_url}{path}",
                auth=httpx.BasicAuth(self.token, ""),
                headers={
                    "accept": "application/json",
                    "content-type": "application/json",
                },
                json=payload,
                params=params,
                timeout=float(settings.FOCUS_NFE_TIMEOUT_SECONDS),
            )
        except httpx.RequestError as exc:
            raise NfseProviderError(
                "Nao foi possivel conectar ao emissor de NFS-e. Tente sincronizar novamente."
            ) from exc

        if response.status_code >= 400:
            raise _error_from_response(response)
        try:
            data = response.json()
        except ValueError as exc:
            raise NfseProviderError(
                "O emissor devolveu uma resposta invalida."
            ) from exc
        return data if isinstance(data, dict) else {}

    def issue(self, reference: str, payload: dict[str, Any]) -> dict[str, Any]:
        return self._request(
            "POST", "/v2/nfse", payload=payload, params={"ref": reference}
        )

    def query(self, reference: str) -> dict[str, Any]:
        return self._request("GET", f"/v2/nfse/{quote(reference, safe='')}")

    def cancel(self, reference: str, justification: str) -> dict[str, Any]:
        return self._request(
            "DELETE",
            f"/v2/nfse/{quote(reference, safe='')}",
            payload={"justificativa": justification},
        )
