"""Cliente HTTP da IntNFe para provisionamento e emissão fiscal."""

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

    def _request(
        self,
        method,
        path,
        *,
        token=None,
        body=None,
        data=None,
        files=None,
        creating=False,
        expect_empty=False,
        extra_headers=None,
    ):
        headers = {"Accept": "application/json"}
        if token:
            headers["Authorization"] = f"Bearer {token}"
        headers.update(extra_headers or {})
        request_args = {
            "headers": headers,
            "timeout": (3, 30) if files else (3, 15),
            "allow_redirects": False,
        }
        if files:
            request_args["data"] = data
            request_args["files"] = files
        else:
            request_args["json"] = body
        try:
            response = self.session.request(
                method,
                BASE_URL + path,
                **request_args,
            )
        except requests.RequestException:
            raise IntNFeError("EmissorIndisponivel", uncertain=creating) from None
        correlation = response.headers.get("X-Correlation-Id")
        if not 200 <= response.status_code < 300:
            # Nunca repassar mensagens/corpos externos que possam conter segredos.
            code = {
                400: "DadosInvalidos",
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
            if response.status_code == 422 and path.endswith("/certificado"):
                try:
                    error = response.json()
                except ValueError:
                    error = None
                remote_code = error.get("erro") if isinstance(error, dict) else None
                if remote_code in {
                    "DadosInvalidos",
                    "CertificadoExpirado",
                    "CertificadoAindaNaoValido",
                    "CnpjDivergente",
                }:
                    code = remote_code
            if path.startswith(("/nfe", "/nfce")):
                try:
                    error = response.json()
                except ValueError:
                    error = None
                remote_code = error.get("erro") if isinstance(error, dict) else None
                if isinstance(remote_code, str) and re.fullmatch(
                    r"[A-Za-z][A-Za-z0-9_-]{1,79}", remote_code
                ):
                    code = remote_code
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
        if expect_empty:
            if response.status_code != 204:
                raise IntNFeError(
                    "RespostaInvalida", correlation=correlation, uncertain=creating
                )
            return None
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

    def _binary_request(self, method, path, *, token, accept):
        headers = {"Accept": accept, "Authorization": f"Bearer {token}"}
        try:
            response = self.session.request(
                method,
                BASE_URL + path,
                headers=headers,
                timeout=(3, 30),
                allow_redirects=False,
            )
        except requests.RequestException:
            raise IntNFeError("EmissorIndisponivel") from None
        correlation = response.headers.get("X-Correlation-Id")
        if not 200 <= response.status_code < 300:
            code = {
                401: "CredenciaisInvalidas",
                403: "AcessoNegado",
                404: "NaoEncontrado",
                409: "DocumentoAindaNaoDisponivel",
                422: "DadosRecusados",
                429: "LimiteDeRequisicoes",
            }.get(response.status_code, "EmissorIndisponivel")
            raise IntNFeError(
                code, status=response.status_code, correlation=correlation
            )
        if not response.content:
            raise IntNFeError("RespostaInvalida", correlation=correlation)
        return response.content

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

    def emitter_certificate(self, token, emitter_id):
        try:
            result = self._request(
                "GET",
                self._emitter_path(emitter_id, "certificado"),
                token=token,
            )
        except IntNFeError as exc:
            if exc.status == 404:
                return None
            raise
        if not isinstance(result, dict):
            raise IntNFeError("RespostaInvalida")
        return result

    def upload_emitter_certificate(
        self, token, emitter_id, *, filename, content, password
    ):
        result = self._request(
            "POST",
            self._emitter_path(emitter_id, "certificado"),
            token=token,
            data={"Senha": password},
            files={"Arquivo": (filename, content, "application/x-pkcs12")},
            creating=True,
        )
        if not isinstance(result, dict):
            raise IntNFeError("RespostaInvalida", uncertain=True)
        return result

    @staticmethod
    def _emitter_path(emitter_id, resource):
        if not isinstance(emitter_id, str) or not re.fullmatch(
            r"[A-Za-z0-9-]{1,128}", emitter_id
        ):
            raise IntNFeError("RespostaInvalida")
        return f"/integrador/emitentes/{emitter_id}/{resource}"

    @classmethod
    def _numbering_path(cls, emitter_id):
        return cls._emitter_path(emitter_id, "numeracao")

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

    def csc(self, token, emitter_id):
        result = self._request(
            "GET", self._emitter_path(emitter_id, "csc"), token=token
        )
        if not isinstance(result, dict):
            raise IntNFeError("RespostaInvalida")
        return result

    def set_csc(self, token, emitter_id, body):
        # O segredo nunca volta pela API. Um timeout pode ocorrer depois da gravacao.
        return self._request(
            "PUT",
            self._emitter_path(emitter_id, "csc"),
            token=token,
            body=body,
            creating=True,
            expect_empty=True,
        )

    def fiscal_registration(self, token, emitter_id):
        try:
            result = self._request(
                "GET", self._emitter_path(emitter_id, "cadastro"), token=token
            )
        except IntNFeError as exc:
            if exc.status == 404:
                return None
            raise
        if not isinstance(result, dict):
            raise IntNFeError("RespostaInvalida")
        return result

    def set_fiscal_registration(self, token, emitter_id, body):
        result = self._request(
            "PATCH",
            self._emitter_path(emitter_id, "cadastro"),
            token=token,
            body=body,
            creating=True,
        )
        if not isinstance(result, dict):
            raise IntNFeError("RespostaInvalida", uncertain=True)
        return result

    def emitter_environment(self, token, emitter_id):
        result = self._request(
            "GET", self._emitter_path(emitter_id, "ambiente"), token=token
        )
        if not isinstance(result, dict):
            raise IntNFeError("RespostaInvalida")
        return result

    def create_production_credentials(self, token, emitter_id):
        result = self._request(
            "POST",
            self._emitter_path(emitter_id, "credencial-producao"),
            token=token,
            body={},
            creating=True,
        )
        if not isinstance(result, dict) or not all(
            isinstance(result.get(field), str) and result[field].strip()
            for field in ("clientId", "clientSecret")
        ):
            raise IntNFeError("RespostaInvalida", uncertain=True)
        return result

    def activate_emitter_environment(self, token, emitter_id, environment):
        return self._request(
            "POST",
            self._emitter_path(emitter_id, "ambiente/ativar"),
            token=token,
            body={"ambienteCodigo": environment},
            creating=True,
            expect_empty=True,
        )

    @staticmethod
    def _document_path(document_type, correlation_id=None, resource=None):
        if document_type not in {"nfe", "nfce"}:
            raise IntNFeError("RespostaInvalida")
        path = f"/{document_type}"
        if correlation_id is not None:
            if not isinstance(correlation_id, str) or not re.fullmatch(
                r"[A-Za-z0-9_-]{1,128}", correlation_id
            ):
                raise IntNFeError("RespostaInvalida")
            path += f"/{correlation_id}"
        if resource:
            path += f"/{resource}"
        return path

    def issue_document(self, token, document_type, body, idempotency_key):
        try:
            result = self._request(
                "POST",
                self._document_path(document_type),
                token=token,
                body=body,
                creating=True,
                extra_headers={"Idempotency-Key": idempotency_key},
            )
        except IntNFeError as exc:
            if exc.status == 409:
                exc.uncertain = True
            raise
        if not isinstance(result, dict) or not isinstance(
            result.get("correlationId"), str
        ):
            raise IntNFeError("RespostaInvalida", uncertain=True)
        return result

    def document_status(self, token, document_type, correlation_id):
        result = self._request(
            "GET", self._document_path(document_type, correlation_id), token=token
        )
        if not isinstance(result, dict):
            raise IntNFeError("RespostaInvalida")
        return result

    def document_xml(self, token, document_type, correlation_id):
        return self._binary_request(
            "GET",
            self._document_path(document_type, correlation_id, "xml"),
            token=token,
            accept="application/xml, text/xml",
        )

    def document_danfe(self, token, document_type, correlation_id):
        return self._binary_request(
            "GET",
            self._document_path(document_type, correlation_id, "danfe")
            + "?formato=pdf",
            token=token,
            accept="application/pdf",
        )

    def cancel_document(self, token, document_type, correlation_id, justification):
        result = self._request(
            "POST",
            self._document_path(document_type, correlation_id, "cancelar"),
            token=token,
            body={"justificativa": justification},
            creating=True,
        )
        if not isinstance(result, dict):
            raise IntNFeError("RespostaInvalida", uncertain=True)
        return result
