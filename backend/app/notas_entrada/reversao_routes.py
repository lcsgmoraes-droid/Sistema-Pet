from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, joinedload

from app.auth.dependencies import get_current_user_and_tenant
from app.db import get_session
from app.financeiro_models import ContaPagar
from app.notas_entrada.processamento_routes import (
    _carregar_acoes_processamento_nota,
    _reverter_historicos_precos_nota,
)
from app.produtos_models import (
    EstoqueMovimentacao,
    NotaEntrada,
    NotaEntradaItem,
    ProdutoHistoricoPreco,
    ProdutoLote,
)

logger = logging.getLogger(__name__)
router = APIRouter()


# ============================================================================
# REVERTER/ESTORNAR ENTRADA NO ESTOQUE
# ============================================================================


@router.post("/{nota_id}/reverter")
def reverter_entrada_estoque(
    nota_id: int,
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    """
    Reverte a entrada no estoque de uma nota jÃ¡ processada
    Remove estoque, exclui lotes, movimentaÃ§Ãµes e contas a pagar
    Reverte preÃ§os de custo dos produtos
    """
    current_user, tenant_id = user_and_tenant

    logger.info(f"ðŸ”„ Revertendo entrada no estoque - Nota {nota_id}")

    nota = (
        db.query(NotaEntrada)
        .options(joinedload(NotaEntrada.itens).joinedload(NotaEntradaItem.produto))
        .filter(NotaEntrada.id == nota_id, NotaEntrada.tenant_id == tenant_id)
        .first()
    )

    if not nota:
        raise HTTPException(status_code=404, detail="Nota nÃ£o encontrada")

    if not nota.entrada_estoque_realizada and nota.status != "processada":
        raise HTTPException(
            status_code=400, detail="Esta nota ainda nÃ£o foi processada"
        )

    acoes_nota = _carregar_acoes_processamento_nota(nota)

    # REVERTER CONTAS A PAGAR vinculadas a esta nota
    logger.info("ðŸ’° Excluindo contas a pagar vinculadas...")
    contas_pagar = (
        db.query(ContaPagar)
        .filter(
            ContaPagar.nota_entrada_id == nota.id, ContaPagar.tenant_id == tenant_id
        )
        .all()
    )

    contas_excluidas = 0
    for conta in contas_pagar:
        if conta.status != "pago":
            db.delete(conta)
            contas_excluidas += 1
            logger.info(
                f"   âœ… Conta excluÃ­da: {conta.descricao} - R$ {float(conta.valor_final):.2f}"
            )
        else:
            logger.warning(
                f"   âš ï¸ Conta JÃ PAGA nÃ£o pode ser excluÃ­da: {conta.descricao}"
            )

    if contas_excluidas > 0:
        logger.info(f"âœ… Total de contas excluÃ­das: {contas_excluidas}")

    itens_revertidos = []
    produtos_precos_revertidos = set()

    try:
        # Reverter cada item
        for item in nota.itens:
            if not item.produto_id:
                continue

            try:
                produto = item.produto
                if (
                    acoes_nota["atualizar_custo"] or acoes_nota["atualizar_preco_venda"]
                ) and produto.id not in produtos_precos_revertidos:
                    _reverter_historicos_precos_nota(
                        produto=produto,
                        nota=nota,
                        db=db,
                        tenant_id=tenant_id,
                    )
                    produtos_precos_revertidos.add(produto.id)

                # Buscar lotes criados para esta entrada. Notas podem ter mais de um
                # rastro/lote para o mesmo item do XML.
                lotes = (
                    db.query(ProdutoLote)
                    .join(
                        EstoqueMovimentacao,
                        EstoqueMovimentacao.lote_id == ProdutoLote.id,
                    )
                    .filter(
                        ProdutoLote.produto_id == produto.id,
                        ProdutoLote.tenant_id == tenant_id,
                        EstoqueMovimentacao.referencia_tipo == "nota_entrada",
                        EstoqueMovimentacao.referencia_id == nota.id,
                        EstoqueMovimentacao.produto_id == produto.id,
                        EstoqueMovimentacao.tenant_id == tenant_id,
                    )
                    .distinct()
                    .all()
                )

                if not lotes:
                    nome_lote = (
                        item.lote
                        if item.lote
                        else f"NF{nota.numero_nota}-{item.numero_item}"
                    )
                    lote_fallback = (
                        db.query(ProdutoLote)
                        .filter(
                            ProdutoLote.produto_id == produto.id,
                            ProdutoLote.nome_lote == nome_lote,
                            ProdutoLote.tenant_id == tenant_id,
                        )
                        .first()
                    )
                    lotes = [lote_fallback] if lote_fallback else []

                if lotes:
                    quantidade_lancada = float(
                        sum(lote.quantidade_inicial or 0 for lote in lotes)
                    )
                    lote_base = lotes[0]

                    # REVERTER PREÇO DE CUSTO se foi alterado
                    try:
                        historico_preco = (
                            db.query(ProdutoHistoricoPreco)
                            .filter(
                                ProdutoHistoricoPreco.produto_id == produto.id,
                                ProdutoHistoricoPreco.nota_entrada_id == nota.id,
                                ProdutoHistoricoPreco.motivo.in_(
                                    ["nfe_entrada", "nfe_revisao_precos"]
                                ),
                                ProdutoHistoricoPreco.tenant_id == tenant_id,
                            )
                            .first()
                        )

                        if historico_preco:
                            # Reverter preços anteriores (com fallback para 0 se None)
                            preco_custo_revertido = float(
                                historico_preco.preco_custo_anterior or 0
                            )
                            preco_venda_revertido = float(
                                historico_preco.preco_venda_anterior or 0
                            )

                            try:
                                logger.info(
                                    f"  💰 Revertendo preço de custo: R$ {float(produto.preco_custo or 0):.2f} → R$ {preco_custo_revertido:.2f}"
                                )
                            except Exception:
                                logger.info(
                                    f"  💰 Revertendo preços do produto {produto.id}"
                                )

                            produto.preco_custo = preco_custo_revertido
                            produto.preco_venda = preco_venda_revertido

                            # Excluir histórico
                            db.delete(historico_preco)
                    except Exception as e:
                        logger.warning(f"  ⚠️ Erro ao reverter preços: {str(e)}")

                    # Remover quantidade do estoque
                    estoque_anterior = produto.estoque_atual or 0
                    produto.estoque_atual = max(
                        0, estoque_anterior - quantidade_lancada
                    )

                    # Registrar movimentação de estorno (sem referência ao lote que será deletado)
                    try:
                        movimentacao_estorno = EstoqueMovimentacao(
                            produto_id=produto.id,
                            lote_id=None,  # Não referenciar o lote que será deletado
                            tipo="saida",
                            motivo="ajuste",
                            quantidade=quantidade_lancada,
                            quantidade_anterior=float(estoque_anterior),
                            quantidade_nova=float(produto.estoque_atual or 0),
                            custo_unitario=float(
                                lote_base.custo_unitario or item.valor_unitario or 0
                            ),
                            valor_total=float(
                                quantidade_lancada
                                * float(
                                    lote_base.custo_unitario or item.valor_unitario or 0
                                )
                            ),
                            documento=nota.chave_acesso or "",
                            referencia_tipo="estorno_nota_entrada",
                            referencia_id=nota.id,
                            observacao=f"Estorno NF-e {nota.numero_nota} - {item.descricao or ''}",
                            user_id=current_user.id,
                            tenant_id=tenant_id,
                        )
                        db.add(movimentacao_estorno)
                    except Exception as e:
                        logger.warning(f"  ⚠️ Erro ao criar movimentação: {str(e)}")

                    for lote in lotes:
                        # Excluir movimentações de estoque vinculadas ao lote (antes de deletar o lote)
                        movimentacoes_lote = (
                            db.query(EstoqueMovimentacao)
                            .filter(
                                EstoqueMovimentacao.lote_id == lote.id,
                                EstoqueMovimentacao.tenant_id == tenant_id,
                            )
                            .all()
                        )

                        for mov in movimentacoes_lote:
                            db.delete(mov)

                        if movimentacoes_lote:
                            logger.info(
                                f"  🗑️  {len(movimentacoes_lote)} movimentações do lote excluídas"
                            )

                        # Excluir lote
                        db.delete(lote)

                    # Adicionar à lista de revertidos
                    itens_revertidos.append(
                        {
                            "produto_id": produto.id,
                            "produto_nome": produto.nome,
                            "quantidade_removida": quantidade_lancada,
                            "estoque_atual": float(produto.estoque_atual or 0),
                        }
                    )

                    logger.info(
                        f"  ↩️  {produto.nome}: -{quantidade_lancada} unidades "
                        f"(estoque: {estoque_anterior} → {produto.estoque_atual})"
                    )

                # Restaurar status do item
                item.status = "vinculado"

            except Exception as e:
                logger.error(f"  ❌ Erro ao reverter item {item.id}: {str(e)}")
                # Continuar com próximo item ao invés de parar tudo

        # Atualizar status da nota
        nota.status = "pendente"
        nota.entrada_estoque_realizada = False
        nota.processada_em = None
        nota.processamento_contexto = None
        nota.processamento_acoes = None

        db.commit()

        # SINCRONIZAR ESTOQUE COM BLING para todos os itens revertidos
        try:
            from app.bling_estoque_sync import sincronizar_bling_background

            for item_rev in itens_revertidos:
                sincronizar_bling_background(
                    item_rev["produto_id"], item_rev["estoque_atual"], "estorno_nfe"
                )
        except Exception as e_sync:
            logger.warning(f"[BLING-SYNC] Erro ao agendar sync (estorno_nfe): {e_sync}")

        logger.info(f"âœ… Entrada revertida: {len(itens_revertidos)} produtos")

        return {
            "message": "Entrada no estoque revertida com sucesso",
            "nota_id": nota.id,
            "numero_nota": nota.numero_nota,
            "itens_revertidos": len(itens_revertidos),
            "detalhes": itens_revertidos,
        }

    except Exception as e:
        db.rollback()
        logger.error(f"âŒ Erro ao reverter entrada: {str(e)}")
        raise HTTPException(
            status_code=500, detail=f"Erro ao reverter entrada: {str(e)}"
        )
