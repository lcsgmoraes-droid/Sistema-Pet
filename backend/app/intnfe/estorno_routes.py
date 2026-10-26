"""Ações fiscais explícitas e restritas ao administrador do tenant da venda."""

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from pydantic import BaseModel, ConfigDict, Field, StrictBool
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user_and_tenant
from app.db import get_session
from app.intnfe.client import IntNFeClient, IntNFeError
from app.intnfe.emission import DirectEmissionError
from app.intnfe import estorno_service
from app.intnfe.estorno_builder import EstornoError
from app.tenancy.context import set_current_tenant
from app.vendas_models import Venda

router = APIRouter(prefix="/nfe/vendas/{venda_id}/estorno", tags=["NF-e de estorno"])


class EstornoRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    motivo: str = Field(min_length=15, max_length=500)
    declaracao_operacao_nao_realizada: StrictBool
    destinatario_proprio_emitente: StrictBool = False
    destinatario: dict | None = None


def _venda(db, venda_id, context):
    user, tenant = context
    set_current_tenant(tenant)
    if not user.is_admin:
        raise HTTPException(
            403, "A emissão de estorno exige um administrador da empresa."
        )
    venda = (
        db.query(Venda).filter(Venda.id == venda_id, Venda.tenant_id == tenant).first()
    )
    if not venda:
        raise HTTPException(404, "Venda não encontrada.")
    return venda, user


def _client():
    try:
        api = IntNFeClient()
    except IntNFeError:
        raise HTTPException(503, "A integração fiscal está indisponível.") from None
    try:
        yield api
    finally:
        api.close()


def _failure(exc):
    return HTTPException(
        exc.status, {"codigo": getattr(exc, "code", None), "mensagem": str(exc)}
    )


@router.get("")
def previa(
    venda_id: int,
    destinatario_proprio_emitente: bool = Query(False),
    db: Session = Depends(get_session),
    context=Depends(get_current_user_and_tenant),
):
    venda, _ = _venda(db, venda_id, context)
    return estorno_service.preview(
        db, venda, destinatario_proprio_emitente=destinatario_proprio_emitente
    )


@router.post("")
def emitir(
    venda_id: int,
    body: EstornoRequest,
    db: Session = Depends(get_session),
    context=Depends(get_current_user_and_tenant),
    api=Depends(_client),
):
    venda, user = _venda(db, venda_id, context)
    try:
        return estorno_service.create(
            db, venda, api, user_id=user.id, **body.model_dump()
        )
    except (EstornoError, DirectEmissionError) as exc:
        raise _failure(exc) from None


@router.post("/consultar")
def consultar(
    venda_id: int,
    db: Session = Depends(get_session),
    context=Depends(get_current_user_and_tenant),
    api=Depends(_client),
):
    venda, user = _venda(db, venda_id, context)
    try:
        return estorno_service.reconcile(db, venda, api, user_id=user.id)
    except (EstornoError, DirectEmissionError) as exc:
        raise _failure(exc) from None


def _download(venda_id, db, context, api, kind):
    venda, _ = _venda(db, venda_id, context)
    try:
        content, record = estorno_service.download(db, venda, api, kind)
    except (EstornoError, DirectEmissionError) as exc:
        raise _failure(exc) from None
    except IntNFeError:
        raise HTTPException(
            503,
            {
                "mensagem": "Não foi possível baixar o documento do estorno. Tente consultar novamente."
            },
        ) from None
    media = "application/xml" if kind == "xml" else "application/pdf"
    extension = "xml" if kind == "xml" else "pdf"
    return Response(
        content=content,
        media_type=media,
        headers={
            "Content-Disposition": f'attachment; filename="estorno-{record.numero}.{extension}"',
            "Cache-Control": "no-store",
        },
    )


@router.get("/xml")
def xml(
    venda_id: int,
    db: Session = Depends(get_session),
    context=Depends(get_current_user_and_tenant),
    api=Depends(_client),
):
    return _download(venda_id, db, context, api, "xml")


@router.get("/danfe")
def danfe(
    venda_id: int,
    db: Session = Depends(get_session),
    context=Depends(get_current_user_and_tenant),
    api=Depends(_client),
):
    return _download(venda_id, db, context, api, "danfe")
