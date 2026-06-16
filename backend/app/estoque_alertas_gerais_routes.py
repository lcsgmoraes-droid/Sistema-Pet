"""
Rotas de alertas gerais de estoque.
"""

from datetime import datetime, timedelta
import logging

from fastapi import APIRouter, Depends
from sqlalchemy import or_
from sqlalchemy.orm import Session, joinedload

from app.auth.dependencies import get_current_user_and_tenant
from app.db import get_session
from app.produtos_models import Produto, ProdutoLote


logger = logging.getLogger(__name__)

router = APIRouter(prefix="/estoque", tags=["Estoque"])


@router.get("/alertas")
def alertas_estoque(
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    """
    Alertas de estoque.

    Retorna:
    - Produtos zerados
    - Produtos abaixo do minimo
    - Lotes vencendo em 30 dias
    - Lotes vencidos
    """
    _current_user, tenant_id = user_and_tenant
    logger.info("Consultando alertas de estoque")

    hoje = datetime.now().date()
    daqui_30_dias = hoje + timedelta(days=30)

    zerados = db.query(Produto).filter(
        or_(
            Produto.estoque_atual == 0,
            Produto.estoque_atual.is_(None),
        ),
        Produto.tipo == "produto",
        Produto.status == "ativo",
        Produto.tenant_id == tenant_id,
    ).all()

    abaixo_minimo = db.query(Produto).filter(
        Produto.estoque_atual <= Produto.estoque_minimo,
        Produto.estoque_atual > 0,
        Produto.estoque_minimo > 0,
        Produto.tipo == "produto",
        Produto.status == "ativo",
        Produto.tenant_id == tenant_id,
    ).all()

    lotes_vencendo = db.query(ProdutoLote).join(Produto).filter(
        ProdutoLote.data_validade.between(hoje, daqui_30_dias),
        ProdutoLote.quantidade > 0,
        ProdutoLote.status == "disponivel",
        Produto.status == "ativo",
        Produto.tenant_id == tenant_id,
    ).options(joinedload(ProdutoLote.produto)).all()

    lotes_vencidos = db.query(ProdutoLote).join(Produto).filter(
        ProdutoLote.data_validade < hoje,
        ProdutoLote.quantidade > 0,
        Produto.status == "ativo",
        Produto.tenant_id == tenant_id,
    ).options(joinedload(ProdutoLote.produto)).all()

    return {
        "zerados": {
            "total": len(zerados),
            "produtos": [
                {
                    "id": p.id,
                    "sku": p.sku,
                    "nome": p.nome,
                    "categoria": p.categoria.nome if p.categoria else None,
                }
                for p in zerados[:20]
            ],
        },
        "abaixo_minimo": {
            "total": len(abaixo_minimo),
            "produtos": [
                {
                    "id": p.id,
                    "sku": p.sku,
                    "nome": p.nome,
                    "estoque_atual": p.estoque_atual,
                    "estoque_minimo": p.estoque_minimo,
                    "diferenca": p.estoque_minimo - p.estoque_atual,
                }
                for p in abaixo_minimo[:20]
            ],
        },
        "lotes_vencendo": {
            "total": len(lotes_vencendo),
            "lotes": [
                {
                    "id": lote.id,
                    "produto_id": lote.produto_id,
                    "produto_nome": lote.produto.nome,
                    "numero_lote": lote.numero_lote,
                    "quantidade": lote.quantidade,
                    "data_validade": lote.data_validade.isoformat(),
                    "dias_restantes": (lote.data_validade - hoje).days,
                }
                for lote in lotes_vencendo[:20]
            ],
        },
        "lotes_vencidos": {
            "total": len(lotes_vencidos),
            "lotes": [
                {
                    "id": lote.id,
                    "produto_id": lote.produto_id,
                    "produto_nome": lote.produto.nome,
                    "numero_lote": lote.numero_lote,
                    "quantidade": lote.quantidade,
                    "data_validade": lote.data_validade.isoformat(),
                    "dias_vencido": (hoje - lote.data_validade).days,
                }
                for lote in lotes_vencidos[:20]
            ],
        },
    }
