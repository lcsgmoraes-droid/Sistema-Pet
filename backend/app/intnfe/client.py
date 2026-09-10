"""Cliente de provisionamento. Nao possui rotas de emissao ou rotacao de segredo."""

from __future__ import annotations

import re

import requests

from app.config import settings


BASE_URL = "https://api.intnfe.com.br"


class IntNFeError(Exception):
    def __init__(self, code, *, status=None, correlation=None, uncertain=False):
        super().__init__(code)
        self.code = code
        self.status = status
        self.correlation = (
            correlation
            if re.fullmatch(r"[\w-]{1,128}", str(correlation or ""))
            else None
        )
        self.uncertain = uncertain


def available() -> bool:
    return bool(
        settings.INTNFE_ACTIVATION_ENABLED
        and settings.INTNFE_INTEGRADOR_ID.strip()
        and settings.INTNFE_INTEGRADOR_SECRET.get_secret_value().strip()
    )


class IntNFeClient:
    def __init__(self, session=None):
        if not available():
            raise IntNFeError("IntegracaoNaoConfigurada")
        self.integrador_id = settings.INTNFE_INTEGRADOR_ID.strip()
        self.secret = settings.INTNFE_INTEGRADOR_SECRET.get_secret_value().strip()
        self.session = session or requests.Session()

    def close(self):
        self.session.close()

    def _request(self, method, path, *, token=None, body=None, creating=False):
        headers = {"Accept": "application/json"}
        if token:
            headers["Authorization"] = f"Bearer {token}"
        try:
            response = self.session.request(
                method,
                BASE_URL + path,
                json=body,
                headers=headers,
                timeout=(3, 15),
                allow_redirects=False,
            )
        except requests.RequestException:
            raise IntNFeError("EmissorIndisponivel", uncertain=creating) from None
        correlation = response.headers.get("X-Correlation-Id")
        if not 200 <= response.status_code < 300:
            # Nunca repassar mensagens/corpos externos que possam conter segredos.
            code = {
                401: "CredenciaisInvalidas",
                403: "AcessoNegado",
                404: "NaoEncontrado",
                409: "EmitenteDuplicado",
                422: "DadosRecusados",
                429: "LimiteDeRequisicoes",
            }.get(response.status_code, "EmissorIndisponivel")
            if response.status_code == 422 and path.endswith("/numeracao"):
                try:
                    error = response.json()
                except ValueError:
                    error = None
                if (
                    isinstance(error, dict)
                    and error.get("erro") == "NumeracaoRetrocede"
                ):
                    code = "NumeracaoRetrocede"
            raise IntNFeError(
                code,
                status=response.status_code,
                correlation=correlation,
                uncertain=creating
                and (
                    response.status_code >= 500
                    or response.status_code == 408
                    or 300 <= response.status_code < 400
                ),
            )
        try:
            data = response.json()
        except (ValueError, requests.exceptions.JSONDecodeError):
            raise IntNFeError(
                "RespostaInvalida", correlation=correlation, uncertain=creating
            ) from None
        if not isinstance(data, (dict, list)):
            raise IntNFeError(
                "RespostaInvalida", correlation=correlation, uncertain=creating
            )
        return data

    def integrator_token(self):
        try:
            result = self._request(
                "POST",
                "/integrador/auth/token",
                body={
                    "integradorId": self.integrador_id,
                    "integradorSecret": self.secret,
                },
            )
        except IntNFeError as exc:
            if exc.code in {"CredenciaisInvalidas", "AcessoNegado"}:
                exc.code = "AcessoIntegradorInvalido"
            raise
        return self._token(result)

    @staticmethod
    def _token(result):
        token = result.get("accessToken") if isinstance(result, dict) else None
        if not isinstance(token, str) or not token.strip():
            raise IntNFeError("RespostaInvalida")
        return token

    def list_emitters(self, token):
        result = self._request("GET", "/integrador/emitentes", token=token)
        if not isinstance(result, list) or not all(
            isinstance(row, dict) for row in result
        ):
            raise IntNFeError("RespostaInvalida")
        return result

    def create_emitter(self, token, company):
        result = self._request(
            "POST", "/integrador/emitentes", token=token, body=company, creating=True
        )
        if (
            not isinstance(result, dict)
            or any(
                not isinstance(result.get(field), str)
                or not 1 <= len(result[field]) <= maximum
                for field, maximum in (
                    ("tenantId", 128),
                    ("clientId", 128),
                    ("clientSecret", 4096),
                )
            )
            or result.get("integradorId") != self.integrador_id
        ):
            raise IntNFeError("RespostaInvalida", uncertain=True)
        return result

    def emitter_token(self, client_id, client_secret):
        return self._token(
            self._request(
                "POST",
                "/auth/token",
                body={
                    "clientId": client_id,
                    "clientSecret": client_secret,
                },
            )
        )

    def certificate(self, token):
        try:
            result = self._request("GET", "/certificados", token=token)
        except IntNFeError as exc:
            if exc.status == 404:
                return None
            raise
        if not isinstance(result, dict):
            raise IntNFeError("RespostaInvalida")
        return result

    @staticmethod
    def _numbering_path(emitter_id):
        if not isinstance(emitter_id, str) or not re.fullmatch(
            r"[A-Za-z0-9-]{1,128}", emitter_id
        ):
            raise IntNFeError("RespostaInvalida")
        return f"/integrador/emitentes/{emitter_id}/numeracao"

    def numbering(self, token, emitter_id):
        result = self._request("GET", self._numbering_path(emitter_id), token=token)
        if not isinstance(result, list):
            raise IntNFeError("RespostaInvalida")
        return result

    def set_numbering(self, token, emitter_id, body):
        # Assim como a criacao, um PUT pode ser aplicado antes de perder a resposta.
        return self._request(
            "PUT",
            self._numbering_path(emitter_id),
            token=token,
            body=body,
            creating=True,
        )
