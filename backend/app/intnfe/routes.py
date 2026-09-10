"""Ativacao restrita ao tenant autenticado e a configuracoes.editar."""

from datetime import datetime
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException
from fastapi.exceptions import RequestValidationError
from fastapi.routing import APIRoute
from pydantic import BaseModel, ConfigDict, SecretStr
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError

from app.audit_log import log_action
from app.auth.dependencies import get_current_user_and_tenant
from app.config import settings
from app.db import get_session
from app.intnfe.client import IntNFeClient, IntNFeError
from app.intnfe.presentation import public_status
from app.intnfe.numbering import (
    NumberingError,
    NumberingInput,
    NumberingUpdateView,
    NumberingView,
    advance_numbering,
    read_numbering,
)
from app.intnfe.repository import ActivationError, get_connection, get_tenant
from app.intnfe.service import activate, bind_existing
from app.security.permissions_decorator import require_permission_dependency
from app.tenancy.context import set_current_tenant


class SafeInputRoute(APIRoute):
    def get_route_handler(self):
        original = super().get_route_handler()

        async def handler(request):
            try:
                return await original(request)
            except RequestValidationError:
                # Erros de schema nao devem devolver o corpo que contem o segredo.
                raise HTTPException(
                    422, "Dados inválidos. Confira os campos informados."
                ) from None

        return handler


can_configure = require_permission_dependency("configuracoes.editar")
router = APIRouter(
    prefix="/intnfe",
    tags=["IntNFe - Ativação"],
    route_class=SafeInputRoute,
    dependencies=[Depends(can_configure)],
)


class ExistingCredentials(BaseModel):
    model_config = ConfigDict(extra="forbid")
    client_id: str
    client_secret: SecretStr


class CompanyView(BaseModel):
    cnpj: str | None
    razao_social: str | None
    nome_fantasia: str


class ActivationView(BaseModel):
    status: str
    mensagem: str
    empresa: CompanyView
    pendencias: list[str]
    vinculado: bool
    ambiente: Literal["homologacao"]
    emissao_disponivel: Literal[False]
    pode_ativar: bool
    pode_consultar: bool
    pode_vincular: bool
    pode_configurar_numeracao: bool
    certificado_valido_ate: datetime | None
    codigo: str | None
    protocolo_suporte: str | None


def get_client():
    try:
        client = IntNFeClient()
    except IntNFeError:
        raise HTTPException(
            503, "A ativação de notas ainda não foi liberada neste ambiente."
        ) from None
    try:
        yield client
    finally:
        client.close()


def _view(db, tenant_id):
    return public_status(
        get_tenant(db, tenant_id),
        get_connection(db, tenant_id),
        settings.INTNFE_INTEGRADOR_ID.strip(),
    )


@router.get("/status", response_model=ActivationView)
def status(
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    _user, tenant_id = user_and_tenant
    set_current_tenant(tenant_id)
    try:
        return _view(db, tenant_id)
    except ActivationError as exc:
        raise HTTPException(exc.status, str(exc)) from None


def _run(db, user_and_tenant, operation, action):
    user, tenant_id = user_and_tenant
    set_current_tenant(tenant_id)
    try:
        connection = action(tenant_id)
        log_action(
            db,
            user_id=user.id,
            tenant_id=tenant_id,
            action=operation,
            entity_type="intnfe_connection",
            entity_id=connection.id,
            new_value={
                "status": connection.status,
                "codigo": connection.ultimo_codigo,
                "correlation_id": connection.correlation_id,
            },
        )
        return _view(db, tenant_id)
    except ActivationError as exc:
        raise HTTPException(exc.status, str(exc)) from None


@router.post("/ativar", response_model=ActivationView)
def activate_route(
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
    api=Depends(get_client),
):
    return _run(
        db, user_and_tenant, "intnfe_ativar", lambda tenant: activate(db, tenant, api)
    )


@router.post("/consultar", response_model=ActivationView)
def consult_route(
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
    api=Depends(get_client),
):
    return _run(
        db,
        user_and_tenant,
        "intnfe_consultar",
        lambda tenant: activate(db, tenant, api, consult_only=True),
    )


@router.post("/vincular", response_model=ActivationView)
def bind_route(
    body: ExistingCredentials,
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
    api=Depends(get_client),
):
    return _run(
        db,
        user_and_tenant,
        "intnfe_vincular",
        lambda tenant: bind_existing(
            db,
            tenant,
            api,
            body.client_id,
            body.client_secret.get_secret_value(),
        ),
    )


def _numbering_failure(exc):
    return HTTPException(
        exc.status,
        {
            "codigo": exc.code,
            "mensagem": str(exc),
            "protocolo_suporte": exc.correlation,
            "exige_consulta": exc.refresh,
        },
    )


@router.get("/numeracao", response_model=NumberingView)
def numbering_route(
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
    api=Depends(get_client),
):
    _user, tenant_id = user_and_tenant
    set_current_tenant(tenant_id)
    try:
        return read_numbering(db, tenant_id, api)
    except NumberingError as exc:
        raise _numbering_failure(exc) from None
    except ActivationError as exc:
        raise HTTPException(exc.status, str(exc)) from None


@router.put("/numeracao", response_model=NumberingUpdateView)
def advance_numbering_route(
    body: NumberingInput,
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
    api=Depends(get_client),
):
    user, tenant_id = user_and_tenant
    set_current_tenant(tenant_id)

    def audit(connection_id, result, last, change, error=None):
        try:
            log_action(
                db,
                user_id=user.id,
                tenant_id=tenant_id,
                action="intnfe_numeracao",
                entity_type="intnfe_connection",
                entity_id=connection_id,
                old_value={"ultimoNumero": last},
                new_value={
                    **change,
                    "resultado": result,
                    "codigo": error.code if error else None,
                    "correlation_id": error.correlation if error else None,
                },
                commit=False,
            )
            db.commit()
        except SQLAlchemyError:
            db.rollback()
            raise NumberingError(
                "AuditoriaIndisponivel"
                if result == "solicitado"
                else "ResultadoNaoConfirmado",
                "Não foi possível registrar o ajuste; nenhuma alteração foi enviada."
                if result == "solicitado"
                else "O ajuste pode ter sido aplicado. Consulte a numeração antes de tentar novamente.",
                status=503,
            ) from None

    try:
        return advance_numbering(db, tenant_id, api, body, audit)
    except NumberingError as exc:
        raise _numbering_failure(exc) from None
    except ActivationError as exc:
        raise HTTPException(exc.status, str(exc)) from None
