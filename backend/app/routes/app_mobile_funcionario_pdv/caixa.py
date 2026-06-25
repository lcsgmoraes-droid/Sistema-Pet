"""Consulta do caixa ERP usado pelo PDV mobile."""

from typing import Optional

from fastapi import APIRouter, Depends
from sqlalchemy import case
from sqlalchemy.orm import Session

from app.caixa_models import Caixa
from app.db import get_session
from app.models import User
from app.routes.ecommerce_auth import _get_current_ecommerce_user

from .auth import _get_funcionario_operacional_or_403
from .schemas import FuncionarioPdvCaixaResponse

router = APIRouter()


def _obter_caixa_aberto_funcionario_pdv(
    db: Session, tenant_id: str, current_user: User
) -> Optional[Caixa]:
    prioridade_usuario_atual = case((Caixa.usuario_id == current_user.id, 0), else_=1)
    return (
        db.query(Caixa)
        .filter(
            Caixa.tenant_id == tenant_id,
            Caixa.status == "aberto",
        )
        .order_by(prioridade_usuario_atual.asc(), Caixa.id.desc())
        .first()
    )


@router.get("/funcionario/pdv/caixa/aberto", response_model=FuncionarioPdvCaixaResponse)
def obter_caixa_aberto_funcionario_pdv(
    current_user: User = Depends(_get_current_ecommerce_user),
    db: Session = Depends(get_session),
):
    _funcionario, tenant_id = _get_funcionario_operacional_or_403(db, current_user)
    caixa = _obter_caixa_aberto_funcionario_pdv(db, tenant_id, current_user)
    if not caixa:
        return {
            "aberto": False,
            "caixa_id": None,
            "numero_caixa": None,
            "mensagem": "Abra um caixa no ERP web antes de vender pelo app.",
        }
    return {
        "aberto": True,
        "caixa_id": caixa.id,
        "numero_caixa": caixa.numero_caixa,
        "mensagem": "Caixa aberto.",
    }
