"""Seleção explícita do ambiente usado nas emissões da empresa."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.intnfe.client import IntNFeError
from app.intnfe.models import IntNFeConnection
from app.intnfe.numbering import emitter_access


class EnvironmentInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    ambiente_codigo: Literal[1, 2]
    serie_nfe: str = Field(default="1", pattern=r"^[0-9]{1,3}$")
    serie_nfce: str = Field(default="1", pattern=r"^[0-9]{1,3}$")

    @field_validator("ambiente_codigo", mode="before")
    @classmethod
    def strict_environment(cls, value):
        if type(value) is not int:
            raise ValueError("Código de ambiente deve ser inteiro.")
        return value

    @field_validator("serie_nfe", "serie_nfce")
    @classmethod
    def normalize_series(cls, value):
        if int(value) > 889:
            raise ValueError("Série fora da faixa permitida.")
        return str(int(value))


class EnvironmentView(BaseModel):
    habilitada: bool
    ambiente_codigo: Literal[1, 2]
    ambiente: str
    serie_nfe: str
    serie_nfce: str
    credencial_homologacao: bool
    credencial_producao: bool
    mensagem: str


class EnvironmentError(Exception):
    def __init__(self, message, *, status=409, code=None, correlation=None):
        super().__init__(message)
        self.status = status
        self.code = code
        self.correlation = correlation


def _view(connection, message=None):
    environment = 1 if connection.emission_environment == 1 else 2
    enabled = bool(connection.emission_enabled)
    if message is None:
        message = (
            f"Emissão direta ativa em {'produção' if environment == 1 else 'homologação'}."
            if enabled
            else "Escolha o ambiente para liberar a emissão direta pelo CorePet."
        )
    return EnvironmentView(
        habilitada=enabled,
        ambiente_codigo=environment,
        ambiente="producao" if environment == 1 else "homologacao",
        serie_nfe=str(connection.nfe_series or "1"),
        serie_nfce=str(connection.nfce_series or "1"),
        credencial_homologacao=bool(
            connection.client_id and connection.client_secret_encrypted
        ),
        credencial_producao=bool(
            connection.production_client_id
            and connection.production_client_secret_encrypted
        ),
        mensagem=message,
    )


def read_environment(db, tenant_id, api):
    connection, _token = emitter_access(db, tenant_id, api)
    return _view(connection)


def configure_environment(db, tenant_id, api, request, audit):
    connection, integrator_token = emitter_access(db, tenant_id, api)
    connection = (
        db.query(IntNFeConnection)
        .filter(IntNFeConnection.id == connection.id)
        .with_for_update()
        .populate_existing()
        .one()
    )
    environment = request.ambiente_codigo
    certificate_end = connection.certificado_valido_ate
    if certificate_end is None:
        raise EnvironmentError(
            "Envie e valide o certificado A1 antes de liberar a emissão.", status=422
        )
    if certificate_end.tzinfo is None:
        certificate_end = certificate_end.replace(tzinfo=timezone.utc)
    if certificate_end <= datetime.now(timezone.utc):
        raise EnvironmentError(
            "O certificado A1 está vencido. Envie o certificado renovado.", status=422
        )

    if environment == 1 and not (
        connection.production_client_id
        and connection.production_client_secret_encrypted
    ):
        if connection.production_credentials_pending:
            raise EnvironmentError(
                "Uma criação anterior da credencial de produção ficou sem confirmação. Solicite a conferência do emissor.",
                status=409,
                code="ResultadoNaoConfirmado",
            )
        connection.production_credentials_pending = True
        db.commit()
        try:
            audit(connection.id, "credencial_producao_solicitada", {"ambiente": 1})
        except EnvironmentError:
            connection.production_credentials_pending = False
            db.commit()
            raise
        try:
            credentials = api.create_production_credentials(
                integrator_token, connection.emitente_id
            )
            connection.production_client_id = credentials["clientId"].strip()
            connection.production_client_secret = credentials["clientSecret"].strip()
            connection.production_credentials_created_at = datetime.now(timezone.utc)
            connection.production_credentials_pending = False
            db.commit()
            audit(connection.id, "credencial_producao_confirmada", {"ambiente": 1})
        except IntNFeError as exc:
            if not exc.uncertain:
                connection.production_credentials_pending = False
                db.commit()
            audit(
                connection.id,
                "credencial_producao_nao_confirmada"
                if exc.uncertain
                else "credencial_producao_recusada",
                {"ambiente": 1, "codigo": exc.code},
            )
            if exc.uncertain:
                raise EnvironmentError(
                    "A criação da credencial de produção ficou sem confirmação. Não tente novamente; solicite a conferência do emissor.",
                    status=503,
                    code=exc.code,
                    correlation=exc.correlation,
                ) from None
            raise EnvironmentError(
                "Não foi possível preparar a credencial de produção.",
                status=422 if exc.status == 422 else 503,
                code=exc.code,
                correlation=exc.correlation,
            ) from None

    client_id = (
        connection.production_client_id if environment == 1 else connection.client_id
    )
    client_secret = (
        connection.production_client_secret
        if environment == 1
        else connection.client_secret
    )
    try:
        # Confirma que a credencial pertence ao ambiente escolhido antes de ativá-lo.
        api.emitter_token(client_id, client_secret)
    except IntNFeError as exc:
        raise EnvironmentError(
            "A credencial do ambiente escolhido não foi aceita pela IntNFe.",
            status=422,
            code=exc.code,
            correlation=exc.correlation,
        ) from None

    try:
        api.activate_emitter_environment(
            integrator_token, connection.emitente_id, environment
        )
    except IntNFeError as exc:
        # A ativação é um POST e pode ter sido aplicada antes de uma resposta se
        # perder. Consulte o estado remoto antes de declarar falha ou repetir.
        remote_environment = None
        if exc.uncertain:
            try:
                remote_environment = api.emitter_environment(
                    integrator_token, connection.emitente_id
                ).get("ambienteAtivo")
            except (AttributeError, IntNFeError):
                remote_environment = None
        if remote_environment != environment:
            raise EnvironmentError(
                "Não foi possível ativar o ambiente escolhido na IntNFe.",
                status=503 if exc.uncertain else (422 if exc.status == 422 else 503),
                code=exc.code,
                correlation=exc.correlation,
            ) from None

    connection.emission_environment = environment
    connection.nfe_series = request.serie_nfe
    connection.nfce_series = request.serie_nfce
    connection.emission_enabled = True
    db.commit()
    audit(
        connection.id,
        "emissao_direta_ativada",
        {
            "ambiente": environment,
            "serie_nfe": request.serie_nfe,
            "serie_nfce": request.serie_nfce,
        },
    )
    return _view(
        connection,
        f"Emissão direta ativada em {'produção' if environment == 1 else 'homologação'}.",
    )


def disable_environment(db, tenant_id, api, audit):
    connection, _token = emitter_access(db, tenant_id, api)
    connection.emission_enabled = False
    db.commit()
    audit(connection.id, "emissao_direta_desativada", {})
    return _view(connection, "Emissão direta desativada para esta empresa.")
