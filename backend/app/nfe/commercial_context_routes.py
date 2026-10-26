"""Revisão dos dados comerciais antes da primeira emissão fiscal."""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict
from sqlalchemy.orm import Session

from app.audit_log import log_action
from app.auth.dependencies import get_current_user_and_tenant
from app.db import get_session
from app.intnfe.commercial_context import (
    CommercialContextError,
    CommercialData,
    can_edit,
    context_data,
)
from app.intnfe.emission import (
    DirectEmissionError,
    _additional_information,
    _crediario_installments,
)
from app.vendas_models import Venda

router = APIRouter(tags=["NF-e"])


class CommercialContextRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    dados: CommercialData


def _sale(db, tenant_id, venda_id, *, lock=False):
    query = db.query(Venda).filter(Venda.id == venda_id, Venda.tenant_id == tenant_id)
    if lock:
        query = query.populate_existing().with_for_update()
    venda = query.first()
    if venda is None:
        raise HTTPException(404, "Venda não encontrada nesta empresa.")
    return venda


def _view(venda, *, data=None):
    try:
        return {
            "dados": data if data is not None else context_data(venda),
            "pode_editar": can_edit(venda),
            "informacoes_adicionais": _additional_information(
                venda, _crediario_installments(venda), commercial_data=data
            ),
        }
    except (CommercialContextError, DirectEmissionError) as exc:
        raise HTTPException(exc.status, str(exc)) from None


@router.get("/vendas/{venda_id}/dados-adicionais")
def get_commercial_context(
    venda_id: int,
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    _, tenant_id = user_and_tenant
    return _view(_sale(db, tenant_id, venda_id))


@router.put("/vendas/{venda_id}/dados-adicionais")
def update_commercial_context(
    venda_id: int,
    body: CommercialContextRequest,
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    user, tenant_id = user_and_tenant
    venda = _sale(db, tenant_id, venda_id, lock=True)
    if not can_edit(venda):
        raise HTTPException(
            409,
            "Esta venda já possui uma tentativa fiscal. Consulte ou descarte com segurança a tentativa rejeitada antes de editar os dados da próxima nota.",
        )
    data = body.dados.model_dump()
    result = _view(venda, data=data)  # Valida também o limite final de 5000 caracteres.
    previous = venda.nfe_contexto_comercial
    venda.nfe_contexto_comercial = data
    log_action(
        db,
        user.id,
        "nfe_dados_comerciais_editar",
        "venda",
        venda.id,
        old_value={"dados": previous},
        new_value={"dados": data},
        tenant_id=tenant_id,
        commit=False,
    )
    db.commit()
    return result
