"""Correção administrativa das observações de vendas finalizadas."""

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.audit_log import log_action
from app.auth.dependencies import get_current_user_and_tenant
from app.db import get_session
from app.vendas.routes_common import _validar_tenant_e_obter_usuario
from app.vendas_models import Venda

router = APIRouter()


class AtualizarObservacoesRequest(BaseModel):
    observacoes: str = Field(default="", max_length=5000)


@router.patch("/{venda_id}/observacoes")
def atualizar_observacoes_venda(
    venda_id: int,
    dados: AtualizarObservacoesRequest,
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    """Corrige a observação sem reabrir a venda ou alterar a nota fiscal."""
    current_user, tenant_id = _validar_tenant_e_obter_usuario(user_and_tenant)
    venda = db.query(Venda).filter_by(id=venda_id, tenant_id=tenant_id).first()
    if not venda:
        raise HTTPException(status_code=404, detail="Venda não encontrada")
    if venda.status not in {"finalizada", "baixa_parcial", "pago_nf"}:
        raise HTTPException(status_code=400, detail="Esta venda não está finalizada")

    venda.observacoes = dados.observacoes.strip() or None
    venda.updated_at = datetime.now()
    db.commit()
    log_action(
        db=db,
        user_id=current_user.id,
        action="update",
        entity_type="venda",
        entity_id=venda.id,
        details=f"Observações administrativas atualizadas na venda {venda.numero_venda}",
    )
    return {"observacoes": venda.observacoes or ""}
