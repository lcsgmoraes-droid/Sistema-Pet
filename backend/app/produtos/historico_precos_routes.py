"""Rotas de historico de precos de produtos."""

from __future__ import annotations

from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, joinedload

from app.auth.dependencies import get_current_user_and_tenant
from app.db import get_session
from app.produtos.schemas import HistoricoPrecoResponse
from app.produtos_models import Produto, ProdutoHistoricoPreco
from app.security.permissions_decorator import require_permission

router = APIRouter()


@router.get(
    "/{produto_id}/historico-precos", response_model=List[HistoricoPrecoResponse]
)
@require_permission("produtos.visualizar")
def listar_historico_precos(
    produto_id: int,
    limit: int = 50,
    offset: int = 0,
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    """
    Lista historico de alteracoes de precos de um produto.
    """
    _current_user, tenant_id = user_and_tenant

    produto = (
        db.query(Produto)
        .filter(Produto.id == produto_id, Produto.tenant_id == tenant_id)
        .first()
    )
    if not produto:
        raise HTTPException(status_code=404, detail="Produto nao encontrado")

    historicos = (
        db.query(ProdutoHistoricoPreco)
        .options(
            joinedload(ProdutoHistoricoPreco.user),
            joinedload(ProdutoHistoricoPreco.nota_entrada),
        )
        .filter(ProdutoHistoricoPreco.produto_id == produto_id)
        .order_by(ProdutoHistoricoPreco.created_at.desc())
        .limit(limit)
        .offset(offset)
        .all()
    )

    resultado = []
    for hist in historicos:
        resultado.append(
            {
                "id": hist.id,
                "data": hist.created_at,
                "preco_custo_anterior": hist.preco_custo_anterior,
                "preco_custo_novo": hist.preco_custo_novo,
                "preco_venda_anterior": hist.preco_venda_anterior,
                "preco_venda_novo": hist.preco_venda_novo,
                "margem_anterior": hist.margem_anterior,
                "margem_nova": hist.margem_nova,
                "variacao_custo_percentual": hist.variacao_custo_percentual,
                "variacao_venda_percentual": hist.variacao_venda_percentual,
                "motivo": hist.motivo,
                "nota_numero": hist.nota_entrada.numero_nota
                if hist.nota_entrada
                else None,
                "nota_data_emissao": hist.nota_entrada.data_emissao
                if hist.nota_entrada
                else None,
                "referencia": hist.referencia,
                "observacoes": hist.observacoes,
                "usuario": hist.user.email if hist.user else None,
            }
        )

    return resultado
