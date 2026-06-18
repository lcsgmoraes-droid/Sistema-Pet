"""
Rotas de edicao e exclusao de movimentacoes de estoque.
"""

from typing import Optional
import logging

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user_and_tenant
from app.bling_estoque_sync import sincronizar_bling_background
from app.db import get_session
from app.produtos_models import (
    EstoqueMovimentacao,
    Produto,
    ProdutoKitComponente,
    ProdutoLote,
)


logger = logging.getLogger(__name__)

router = APIRouter(prefix="/estoque", tags=["Estoque"])


@router.delete("/movimentacoes/{movimentacao_id}")
def excluir_movimentacao(
    movimentacao_id: int,
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    """
    Exclui uma movimentacao de estoque e reverte o efeito no produto.
    """
    current_user, tenant_id = user_and_tenant
    try:
        movimentacao = (
            db.query(EstoqueMovimentacao)
            .filter(
                EstoqueMovimentacao.id == movimentacao_id,
                EstoqueMovimentacao.tenant_id == tenant_id,
            )
            .first()
        )

        if not movimentacao:
            raise HTTPException(status_code=404, detail="Movimentação não encontrada")

        produto = (
            db.query(Produto)
            .filter(
                Produto.id == movimentacao.produto_id,
                Produto.tenant_id == tenant_id,
            )
            .first()
        )
        if not produto:
            raise HTTPException(status_code=404, detail="Produto não encontrado")

        logger.info(
            "Excluindo movimentacao %s - Tipo: %s, Qtd: %s",
            movimentacao_id,
            movimentacao.tipo,
            movimentacao.quantidade,
        )

        componentes_estornados = []
        if produto.tipo_produto == "KIT" and produto.tipo_kit == "FISICO":
            componentes_kit = (
                db.query(ProdutoKitComponente)
                .filter(
                    ProdutoKitComponente.kit_id == produto.id,
                )
                .all()
            )

            if componentes_kit:
                logger.info("KIT FISICO detectado - Estornando componentes...")

                for comp in componentes_kit:
                    componente_produto = (
                        db.query(Produto)
                        .filter(
                            Produto.id == comp.produto_componente_id,
                            Produto.tenant_id == tenant_id,
                        )
                        .first()
                    )
                    if componente_produto:
                        quantidade_componente = (
                            comp.quantidade * movimentacao.quantidade
                        )
                        estoque_ant_comp = componente_produto.estoque_atual

                        if movimentacao.tipo == "entrada":
                            componente_produto.estoque_atual += quantidade_componente
                            logger.info(
                                "%s: %s -> %s (+%s) [devolvido]",
                                componente_produto.nome,
                                estoque_ant_comp,
                                componente_produto.estoque_atual,
                                quantidade_componente,
                            )
                            componentes_estornados.append(
                                {
                                    "nome": componente_produto.nome,
                                    "quantidade": quantidade_componente,
                                    "estoque_anterior": estoque_ant_comp,
                                    "estoque_novo": componente_produto.estoque_atual,
                                    "acao": "devolvido",
                                }
                            )
                        elif (
                            movimentacao.tipo == "saida"
                            and movimentacao.observacao
                            and "componentes retornados"
                            in movimentacao.observacao.lower()
                        ):
                            componente_produto.estoque_atual -= quantidade_componente
                            logger.info(
                                "%s: %s -> %s (-%s) [estornando retorno]",
                                componente_produto.nome,
                                estoque_ant_comp,
                                componente_produto.estoque_atual,
                                quantidade_componente,
                            )
                            componentes_estornados.append(
                                {
                                    "nome": componente_produto.nome,
                                    "quantidade": quantidade_componente,
                                    "estoque_anterior": estoque_ant_comp,
                                    "estoque_novo": componente_produto.estoque_atual,
                                    "acao": "estornado",
                                }
                            )

                logger.info(
                    "KIT FISICO: %s componentes estornados", len(componentes_estornados)
                )

        estoque_anterior = produto.estoque_atual
        if movimentacao.tipo == "entrada":
            produto.estoque_atual -= movimentacao.quantidade
            logger.info(
                "Estoque %s: %s -> %s (-%s)",
                produto.nome,
                estoque_anterior,
                produto.estoque_atual,
                movimentacao.quantidade,
            )
        elif movimentacao.tipo == "saida":
            produto.estoque_atual += movimentacao.quantidade
            logger.info(
                "Estoque %s: %s -> %s (+%s)",
                produto.nome,
                estoque_anterior,
                produto.estoque_atual,
                movimentacao.quantidade,
            )

        if movimentacao.lote_id:
            lote = (
                db.query(ProdutoLote)
                .filter(ProdutoLote.id == movimentacao.lote_id)
                .first()
            )
            if lote:
                if movimentacao.tipo == "entrada":
                    lote.quantidade_disponivel -= movimentacao.quantidade
                    if lote.quantidade_disponivel <= 0:
                        lote.status = "esgotado"
                elif movimentacao.tipo == "saida":
                    lote.quantidade_disponivel += movimentacao.quantidade
                    lote.status = "ativo"

        db.delete(movimentacao)
        db.commit()

        logger.info("Movimentacao excluida")

        try:
            sincronizar_bling_background(
                produto.id, produto.estoque_atual, "exclusao_movimentacao"
            )
        except Exception as e_sync:
            logger.warning(
                "[BLING-SYNC] Erro ao agendar sync (exclusao_mov): %s", e_sync
            )

        return {
            "message": "Movimentação excluída com sucesso",
            "componentes_estornados": componentes_estornados,
        }

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error("Erro ao excluir movimentacao: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


class UpdateMovimentacaoRequest(BaseModel):
    quantidade: Optional[float] = None
    custo_unitario: Optional[float] = None
    observacao: Optional[str] = None


@router.patch("/movimentacoes/{movimentacao_id}")
def editar_movimentacao(
    movimentacao_id: int,
    dados: UpdateMovimentacaoRequest,
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    """
    Edita uma movimentacao existente.
    """
    current_user, tenant_id = user_and_tenant
    try:
        movimentacao = (
            db.query(EstoqueMovimentacao)
            .filter(
                EstoqueMovimentacao.id == movimentacao_id,
                EstoqueMovimentacao.tenant_id == tenant_id,
            )
            .first()
        )

        if not movimentacao:
            raise HTTPException(status_code=404, detail="Movimentação não encontrada")

        produto = (
            db.query(Produto)
            .filter(
                Produto.id == movimentacao.produto_id,
                Produto.tenant_id == tenant_id,
            )
            .first()
        )
        if not produto:
            raise HTTPException(status_code=404, detail="Produto não encontrado")

        if dados.quantidade is not None and dados.quantidade != movimentacao.quantidade:
            diferenca = dados.quantidade - movimentacao.quantidade

            if movimentacao.tipo == "entrada":
                produto.estoque_atual += diferenca
                if movimentacao.lote_id:
                    lote = (
                        db.query(ProdutoLote)
                        .filter(ProdutoLote.id == movimentacao.lote_id)
                        .first()
                    )
                    if lote:
                        lote.quantidade_disponivel += diferenca
            elif movimentacao.tipo == "saida":
                produto.estoque_atual -= diferenca
                if movimentacao.lote_id:
                    lote = (
                        db.query(ProdutoLote)
                        .filter(ProdutoLote.id == movimentacao.lote_id)
                        .first()
                    )
                    if lote:
                        lote.quantidade_disponivel -= diferenca

            movimentacao.quantidade = dados.quantidade
            movimentacao.quantidade_nova = produto.estoque_atual

        if dados.custo_unitario is not None:
            movimentacao.custo_unitario = dados.custo_unitario
            movimentacao.valor_total = movimentacao.quantidade * dados.custo_unitario

        if dados.observacao is not None:
            movimentacao.observacao = dados.observacao

        db.commit()
        db.refresh(movimentacao)

        logger.info("Movimentacao editada")

        if dados.quantidade is not None:
            try:
                sincronizar_bling_background(
                    produto.id, produto.estoque_atual, "edicao_movimentacao"
                )
            except Exception as e_sync:
                logger.warning(
                    "[BLING-SYNC] Erro ao agendar sync (edicao_mov): %s", e_sync
                )

        return {
            "id": movimentacao.id,
            "quantidade": movimentacao.quantidade,
            "custo_unitario": movimentacao.custo_unitario,
            "observacao": movimentacao.observacao,
            "estoque_atual_produto": produto.estoque_atual,
        }

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error("Erro ao editar movimentacao: %s", e)
        raise HTTPException(status_code=500, detail=str(e))
