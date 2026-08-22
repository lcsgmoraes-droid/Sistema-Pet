"""Ajustes de estoque feitos durante a edição de uma venda aberta."""

import logging
from collections import defaultdict

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.audit_log import log_action
from app.estoque.service import EstoqueService
from app.produtos_models import Produto, ProdutoKitComponente
from app.vendas.estoque_baixa import processar_baixa_estoque_item

logger = logging.getLogger(__name__)


def calcular_diferencas_estoque_edicao(itens_antigos, itens_novos) -> dict[int, float]:
    quantidades_antigas = defaultdict(float)
    quantidades_novas = defaultdict(float)
    for item in itens_antigos:
        if item.produto_id:
            quantidades_antigas[item.produto_id] += float(item.quantidade or 0)
    for item in itens_novos:
        if item.produto_id:
            quantidades_novas[item.produto_id] += float(item.quantidade or 0)

    return {
        produto_id: quantidades_novas[produto_id] - quantidades_antigas[produto_id]
        for produto_id in set(quantidades_antigas) | set(quantidades_novas)
        if abs(quantidades_novas[produto_id] - quantidades_antigas[produto_id]) > 1e-9
    }


def _estornar_quantidade_reduzida(
    *,
    produto,
    quantidade: float,
    venda,
    current_user,
    tenant_id,
    db: Session,
) -> None:
    if produto.tipo_produto == "KIT" and produto.tipo_kit == "VIRTUAL":
        componentes = (
            db.query(ProdutoKitComponente)
            .filter(ProdutoKitComponente.kit_id == produto.id)
            .all()
        )
        if not componentes:
            raise ValueError(
                f"KIT VIRTUAL '{produto.nome}' não possui componentes cadastrados"
            )
        for componente in componentes:
            EstoqueService.estornar_estoque(
                produto_id=componente.produto_componente_id,
                quantidade=quantidade * float(componente.quantidade),
                motivo="ajuste",
                referencia_id=venda.id,
                referencia_tipo="venda_editada",
                user_id=current_user.id,
                tenant_id=tenant_id,
                db=db,
                documento=venda.numero_venda,
                observacao=(
                    f"Componente devolvido na edição do KIT '{produto.nome}' "
                    f"na venda #{venda.id}"
                ),
            )
        return

    EstoqueService.estornar_estoque(
        produto_id=produto.id,
        quantidade=quantidade,
        motivo="ajuste",
        referencia_id=venda.id,
        referencia_tipo="venda_editada",
        user_id=current_user.id,
        tenant_id=tenant_id,
        db=db,
        documento=venda.numero_venda,
        observacao=f"Quantidade reduzida na venda #{venda.id}",
    )


def ajustar_estoque_edicao_venda(
    *,
    venda,
    itens_antigos,
    itens_novos,
    current_user,
    tenant_id,
    db: Session,
) -> None:
    diferencas = calcular_diferencas_estoque_edicao(itens_antigos, itens_novos)
    for produto_id, diferenca in diferencas.items():
        produto = (
            db.query(Produto)
            .filter(Produto.id == produto_id, Produto.tenant_id == tenant_id)
            .first()
        )
        if not produto:
            raise HTTPException(
                status_code=404,
                detail=f"Produto ID {produto_id} não encontrado",
            )

        if not getattr(produto, "controlar_estoque", True):
            continue

        try:
            if diferenca < 0:
                quantidade_estorno = abs(diferenca)
                logger.info(
                    "Devolvendo estoque na edição: Produto %s +%s",
                    produto_id,
                    quantidade_estorno,
                )
                _estornar_quantidade_reduzida(
                    produto=produto,
                    quantidade=quantidade_estorno,
                    venda=venda,
                    current_user=current_user,
                    tenant_id=tenant_id,
                    db=db,
                )
                detalhe = (
                    f"Estorno (+{quantidade_estorno}) - Quantidade reduzida "
                    f"na venda #{venda.id}"
                )
            else:
                logger.info(
                    "Baixando estoque na edição: Produto %s -%s",
                    produto_id,
                    diferenca,
                )
                processar_baixa_estoque_item(
                    produto=produto,
                    quantidade_vendida=diferenca,
                    venda_id=venda.id,
                    user_id=current_user.id,
                    tenant_id=tenant_id,
                    db=db,
                    venda_codigo=venda.numero_venda,
                )
                detalhe = (
                    f"Baixa (-{diferenca}) - Quantidade adicionada na venda #{venda.id}"
                )

            log_action(
                db=db,
                user_id=current_user.id,
                action="update",
                entity_type="produtos",
                entity_id=produto_id,
                details=detalhe,
                commit=False,
            )
        except ValueError as error:
            logger.error("Erro ao ajustar estoque na edição: %s", error)
            raise HTTPException(status_code=400, detail=str(error)) from error
