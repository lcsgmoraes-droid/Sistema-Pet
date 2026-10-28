"""Operações explícitas sobre uma nova nota, separadas da venda original."""

from typing import Literal
from decimal import InvalidOperation
from xml.etree.ElementTree import ParseError

import requests
from defusedxml.common import DefusedXmlException

from fastapi import APIRouter, Depends, HTTPException, Response
from pydantic import BaseModel, ConfigDict
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user_and_tenant
from app.db import get_session
from app.intnfe.client import IntNFeClient, IntNFeError
from app.intnfe.emission import DirectEmissionError, _access_token, _connection
from app.intnfe.repository import ActivationError
from app.nfe import clone_service as service
from app.nfe.clone_models import NotaFiscalClone
from app.nfe.danfe_nfce import gerar_danfe_nfce

router = APIRouter(prefix="/clones")


class Source(BaseModel):
    model_config = ConfigDict(extra="ignore")
    provedor: Literal["intnfe", "bling"]
    venda_id: int | None = None
    nfe_id: str | int | None = None
    id: str | int | None = None
    modelo: int | None = None


class Create(BaseModel):
    origem: Source
    dados: dict


class Update(BaseModel):
    dados: dict


class Cancel(BaseModel):
    justificativa: str


def client():
    try:
        api = IntNFeClient()
    except IntNFeError:
        raise HTTPException(
            503, "O emissor fiscal ainda não está disponível neste ambiente."
        ) from None
    try:
        yield api
    finally:
        api.close()


def run(operation):
    try:
        return operation()
    except (DirectEmissionError, ActivationError) as exc:
        raise HTTPException(exc.status, str(exc)) from None
    except IntNFeError:
        raise HTTPException(
            503, "Não foi possível consultar o emissor. Tente novamente em instantes."
        ) from None
    except (
        ParseError,
        DefusedXmlException,
        InvalidOperation,
        UnicodeDecodeError,
        ValueError,
        TypeError,
    ):
        raise HTTPException(
            422,
            "Os dados da nota original estão incompletos ou inválidos para clonagem.",
        ) from None
    except requests.RequestException:
        raise HTTPException(
            502,
            "Não foi possível obter o documento original. Tente novamente em instantes.",
        ) from None


@router.post("/preparar")
def prepare(
    body: Source,
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
    api=Depends(client),
):
    _, tenant_id = user_and_tenant
    return run(lambda: service.prepare(db, tenant_id, api, body.model_dump())[0])


@router.get("")
def list_clones(
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    _, tenant_id = user_and_tenant
    rows = (
        db.query(NotaFiscalClone)
        .filter(NotaFiscalClone.tenant_id == tenant_id)
        .order_by(NotaFiscalClone.created_at.desc(), NotaFiscalClone.id.desc())
        .limit(100)
        .all()
    )
    return {"rascunhos": [service.view(row) for row in rows]}


@router.post("")
def create(
    body: Create,
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
    api=Depends(client),
):
    user, tenant_id = user_and_tenant
    return run(
        lambda: service.create(
            db, tenant_id, user.id, api, body.origem.model_dump(), body.dados
        )
    )


@router.get("/{clone_id}")
def get(
    clone_id: int,
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    _, tenant_id = user_and_tenant
    return service.view(service.get_clone(db, tenant_id, clone_id))


@router.put("/{clone_id}")
def update(
    clone_id: int,
    body: Update,
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    user, tenant_id = user_and_tenant
    return service.update(db, tenant_id, user.id, clone_id, body.dados)


@router.post("/{clone_id}/emitir")
def issue(
    clone_id: int,
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
    api=Depends(client),
):
    user, tenant_id = user_and_tenant
    return run(lambda: service.issue(db, tenant_id, user.id, clone_id, api))


@router.post("/{clone_id}/consultar")
def consult(
    clone_id: int,
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
    api=Depends(client),
):
    _, tenant_id = user_and_tenant
    return run(lambda: service.consult(db, tenant_id, clone_id, api))


@router.post("/{clone_id}/cancelar")
def cancel(
    clone_id: int,
    body: Cancel,
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
    api=Depends(client),
):
    user, tenant_id = user_and_tenant
    return run(
        lambda: service.cancel(
            db, tenant_id, user.id, clone_id, api, body.justificativa
        )
    )


@router.get("/{clone_id}/xml")
def xml(
    clone_id: int,
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    _, tenant_id = user_and_tenant
    row = service.get_clone(db, tenant_id, clone_id)
    if not row.xml:
        raise HTTPException(
            409, "O XML fica disponível após a autorização da nota clonada."
        )
    return Response(
        row.xml,
        media_type="application/xml",
        headers={
            "Content-Disposition": f'attachment; filename="nota-clonada-{row.numero}.xml"'
        },
    )


@router.get("/{clone_id}/danfe")
def danfe(
    clone_id: int,
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
    api=Depends(client),
):
    _, tenant_id = user_and_tenant
    row = service.get_clone(db, tenant_id, clone_id)
    if row.status != "autorizada" or not row.xml:
        raise HTTPException(
            409, "O DANFE fica disponível após a autorização da nota clonada."
        )

    def download():
        if row.modelo == 65:
            content = gerar_danfe_nfce(row.xml.encode("utf-8"), row.chave)
        else:
            connection = _connection(db, tenant_id, require_enabled=False)
            content = api.document_danfe(
                _access_token(api, connection, row.dados["ambienteCodigo"]),
                "nfe",
                row.correlation_id,
            )
            if not content.startswith(b"%PDF-"):
                raise HTTPException(
                    502, "O emissor não disponibilizou um DANFE válido."
                )
        return Response(
            content,
            media_type="application/pdf",
            headers={
                "Content-Disposition": f'attachment; filename="danfe-clonada-{row.numero}.pdf"'
            },
        )

    return run(download)
