"""
Rotas de relatorios de estoque.
"""

from typing import Optional
import logging

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user_and_tenant
from app.db import get_session
from app.produtos_models import Produto


logger = logging.getLogger(__name__)

router = APIRouter(prefix="/estoque", tags=["Estoque"])


@router.get("/relatorio/valorizado")
def relatorio_estoque_valorizado(
    data_referencia: Optional[str] = None,
    categoria_id: Optional[int] = None,
    marca_id: Optional[int] = None,
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    """
    Relatorio de estoque valorizado.

    Calcula valor total do estoque baseado no preco de custo.
    """
    _current_user, tenant_id = user_and_tenant
    logger.info("Gerando relatorio de estoque valorizado")

    query = db.query(
        Produto.id,
        Produto.sku,
        Produto.nome,
        Produto.estoque_atual,
        Produto.preco_custo,
        (Produto.estoque_atual * Produto.preco_custo).label("valor_total"),
    ).filter(
        Produto.tipo == "produto",
        Produto.status == "ativo",
        Produto.estoque_atual > 0,
        Produto.tenant_id == tenant_id,
    )

    if categoria_id:
        query = query.filter(Produto.categoria_id == categoria_id)
    if marca_id:
        query = query.filter(Produto.marca_id == marca_id)

    produtos = query.all()

    valor_total = sum(p.valor_total for p in produtos if p.valor_total)
    total_itens = sum(p.estoque_atual for p in produtos if p.estoque_atual)

    return {
        "resumo": {
            "valor_total": valor_total,
            "total_produtos": len(produtos),
            "total_itens": total_itens,
            "custo_medio_unitario": valor_total / total_itens if total_itens > 0 else 0,
        },
        "produtos": [
            {
                "id": p.id,
                "sku": p.sku,
                "nome": p.nome,
                "quantidade": p.estoque_atual,
                "custo_unitario": p.preco_custo,
                "valor_total": p.valor_total,
            }
            for p in produtos
        ],
    }
