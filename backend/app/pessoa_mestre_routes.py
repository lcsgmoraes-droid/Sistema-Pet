"""Rotas de pessoa-mestre — camada geral do grupo comercial, Checkpoint 4.
Aditivo: não altera nenhuma rota existente de cadastro de cliente.
"""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user_and_tenant
from app.db import get_session
from app.grupo_comercial_contexto import obter_grupo_id_ativo
from app.models_cadastros import Cliente
from app.pessoa_mestre_service import (
    desvincular_pessoa_mestre,
    sugerir_pessoa_mestre,
    vincular_pessoa_mestre,
)

router = APIRouter(prefix="/pessoa-mestre", tags=["Pessoa mestre"])


class PessoaMestreSugestaoResponse(BaseModel):
    id: int
    nome: str
    tipo_cadastro: Optional[str] = None


class VincularPessoaMestreRequest(BaseModel):
    mestre_id: Optional[int] = None
    """Vincula a esta pessoa-mestre existente do grupo; se omitido, promove
    o próprio cliente local a uma pessoa-mestre nova."""


@router.get("/sugestao", response_model=Optional[PessoaMestreSugestaoResponse])
def sugerir_mestre_pessoa(
    cpf: Optional[str] = None,
    cnpj: Optional[str] = None,
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    """Só sugere por CPF/CNPJ — nunca por nome (comum demais pra ser
    confiável em dado pessoal)."""
    _current_user, tenant_id = user_and_tenant
    grupo_id = obter_grupo_id_ativo(db, tenant_id)
    if grupo_id is None:
        return None
    return sugerir_pessoa_mestre(db, grupo_id, cpf=cpf, cnpj=cnpj)


@router.post("/{cliente_id}/vincular", response_model=PessoaMestreSugestaoResponse)
def vincular_mestre_pessoa(
    cliente_id: int,
    payload: VincularPessoaMestreRequest,
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    """Vínculo é sempre uma confirmação explícita do usuário — nunca
    acionado automaticamente pela sugestão."""
    current_user, tenant_id = user_and_tenant
    cliente = (
        db.query(Cliente)
        .filter(Cliente.id == cliente_id, Cliente.tenant_id == tenant_id)
        .first()
    )
    if not cliente:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Cliente não encontrado"
        )
    grupo_id = obter_grupo_id_ativo(db, tenant_id)
    if grupo_id is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Esta loja não tem grupo comercial ativo.",
        )
    return vincular_pessoa_mestre(
        db,
        cliente=cliente,
        grupo_id=grupo_id,
        usuario_id=current_user.id,
        pessoa_mestre_id=payload.mestre_id,
    )


@router.delete("/{cliente_id}/vincular", status_code=status.HTTP_204_NO_CONTENT)
def remover_vinculo_mestre_pessoa(
    cliente_id: int,
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    _current_user, tenant_id = user_and_tenant
    cliente = (
        db.query(Cliente)
        .filter(Cliente.id == cliente_id, Cliente.tenant_id == tenant_id)
        .first()
    )
    if not cliente:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Cliente não encontrado"
        )
    desvincular_pessoa_mestre(db, cliente=cliente)
    return None
