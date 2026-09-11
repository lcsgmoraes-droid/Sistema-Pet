"""Upload e leitura segura do certificado A1 pelo integrador."""

from __future__ import annotations

from datetime import datetime, timezone
from math import ceil
from pathlib import PurePath

from pydantic import BaseModel, ConfigDict, ValidationError
from sqlalchemy.exc import SQLAlchemyError

from app.intnfe.client import IntNFeError
from app.intnfe.numbering import emitter_access
from app.intnfe.presentation import certificate_state

MAX_CERTIFICATE_BYTES = 512 * 1024
MAX_PASSWORD_LENGTH = 1024


class RemoteCertificate(BaseModel):
    model_config = ConfigDict(extra="ignore")

    razaoSocial: str | None = None
    cnpj: str
    thumbprint: str | None = None
    nomeArquivo: str | None = None
    validoDe: datetime
    validoAte: datetime
    expirado: bool = False
    atualizadoEm: datetime | None = None


class CertificateView(BaseModel):
    tem_certificado: bool
    situacao: str
    mensagem: str
    valido_de: datetime | None = None
    valido_ate: datetime | None = None
    dias_para_expirar: int | None = None
    alerta_vencimento: bool = False


class CertificateError(Exception):
    def __init__(self, code, message, *, status=422, correlation=None, refresh=False):
        super().__init__(message)
        self.code = code
        self.status = status
        self.correlation = correlation
        self.refresh = refresh


def _remote(raw):
    if raw is None:
        return None
    try:
        return RemoteCertificate.model_validate(raw)
    except (ValidationError, ValueError, TypeError):
        raise IntNFeError("RespostaInvalida") from None


def _view(raw, expected_cnpj):
    certificate = _remote(raw)
    if certificate is None:
        return CertificateView(
            tem_certificado=False,
            situacao="pendente",
            mensagem="Envie o certificado A1 da empresa para continuar.",
        )
    state, expires = certificate_state(certificate.model_dump(), expected_cnpj)
    starts = certificate.validoDe
    now = datetime.now(timezone.utc)
    days = ceil((expires - now).total_seconds() / 86400) if expires else None
    if state != "certificado_validado":
        situation = "expirado" if expires and expires <= now else "invalido"
        message = (
            "O certificado venceu. Envie o A1 renovado."
            if situation == "expirado"
            else "O certificado não é válido para este CNPJ ou período."
        )
    elif days is not None and days <= 30:
        situation = "expirando"
        message = f"O certificado vence em {max(days, 0)} dia(s). Prepare a renovação."
    else:
        situation = "valido"
        message = "Certificado A1 válido e pronto para assinar documentos."
    return CertificateView(
        tem_certificado=True,
        situacao=situation,
        mensagem=message,
        valido_de=starts,
        valido_ate=expires,
        dias_para_expirar=days,
        alerta_vencimento=situation in {"expirando", "expirado", "invalido"},
    )


def _cache(db, connection, view):
    connection.certificado_valido_ate = view.valido_ate
    connection.status = (
        "certificado_validado"
        if view.situacao in {"valido", "expirando"}
        else (
            "certificado_pendente"
            if view.situacao == "pendente"
            else "certificado_invalido"
        )
    )
    connection.ultimo_codigo = None
    connection.correlation_id = None
    db.commit()
    db.refresh(connection)


def _provider_error(exc):
    if exc.uncertain:
        return CertificateError(
            "ResultadoNaoConfirmado",
            "O certificado pode ter sido recebido. Consulte a situação antes de enviar novamente.",
            status=503,
            correlation=exc.correlation,
            refresh=True,
        )
    messages = {
        "DadosInvalidos": "A senha não confere ou o arquivo A1 está inválido.",
        "CnpjDivergente": "O CNPJ do certificado é diferente do CNPJ desta empresa.",
        "CertificadoExpirado": "O certificado está vencido. Envie o A1 renovado.",
        "CertificadoAindaNaoValido": "O certificado ainda não entrou no período de validade.",
    }
    if exc.code in messages:
        return CertificateError(
            exc.code, messages[exc.code], status=422, correlation=exc.correlation
        )
    if exc.status == 404:
        return CertificateError(
            "EmitenteNaoEncontrado",
            "O emitente não foi encontrado na IntNFe. Consulte o vínculo.",
            status=404,
            correlation=exc.correlation,
            refresh=True,
        )
    return CertificateError(
        exc.code,
        "Não foi possível consultar ou enviar o certificado. Tente novamente ou acione o suporte.",
        status=503,
        correlation=exc.correlation,
        refresh=True,
    )


def read_certificate(db, tenant_id, api):
    try:
        connection, token = emitter_access(db, tenant_id, api)
        view = _view(
            api.emitter_certificate(token, connection.emitente_id), connection.cnpj
        )
        _cache(db, connection, view)
        return view
    except SQLAlchemyError:
        db.rollback()
        raise CertificateError(
            "ResultadoNaoConfirmado",
            "O certificado foi consultado, mas a situação local não pôde ser atualizada.",
            status=503,
            refresh=True,
        ) from None
    except IntNFeError as exc:
        raise _provider_error(exc) from None


def upload_certificate(db, tenant_id, api, *, filename, content, password, audit):
    clean_name = PurePath(str(filename or "")).name
    if PurePath(clean_name).suffix.lower() not in {".pfx", ".p12"}:
        raise CertificateError(
            "ArquivoInvalido", "Selecione um certificado A1 em formato .pfx ou .p12."
        )
    if not 1 <= len(content) <= MAX_CERTIFICATE_BYTES:
        raise CertificateError(
            "ArquivoInvalido", "O certificado deve ter no máximo 512 KB."
        )
    if not 1 <= len(password) <= MAX_PASSWORD_LENGTH:
        raise CertificateError("SenhaInvalida", "Informe a senha do certificado A1.")

    attempted = False
    try:
        connection, token = emitter_access(db, tenant_id, api)
        public_change = {
            "tamanho_bytes": len(content),
            "formato": PurePath(clean_name).suffix.lower(),
        }
        audit(connection.id, "solicitado", public_change)
        attempted = True
        raw = api.upload_emitter_certificate(
            token,
            connection.emitente_id,
            filename=clean_name,
            content=content,
            password=password,
        )
        view = _view(raw, connection.cnpj)
        if view.situacao not in {"valido", "expirando"}:
            raise IntNFeError("RespostaInvalida", uncertain=True)
        try:
            _cache(db, connection, view)
        except SQLAlchemyError:
            db.rollback()
            uncertain = IntNFeError("ResultadoNaoConfirmado", uncertain=True)
            audit(connection.id, "nao_confirmado", public_change, uncertain)
            raise CertificateError(
                "ResultadoNaoConfirmado",
                "O certificado foi recebido, mas a situação local não pôde ser atualizada. Consulte antes de enviar novamente.",
                status=503,
                refresh=True,
            ) from None
        audit(connection.id, "confirmado", public_change)
        return view
    except CertificateError:
        raise
    except IntNFeError as exc:
        if attempted and exc.status not in {401, 403, 404, 409, 422, 429}:
            exc.uncertain = True
        if attempted:
            audit(
                connection.id,
                "nao_confirmado" if exc.uncertain else "recusado",
                public_change,
                exc,
            )
        raise _provider_error(exc) from None
