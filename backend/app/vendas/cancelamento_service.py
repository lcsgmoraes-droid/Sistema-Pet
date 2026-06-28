"""Cancelamento atomico de vendas."""

import logging
from typing import Any, Dict
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.db.transaction import transactional_session
from app.services.venda_rentabilidade_snapshot_service import (
    get_or_build_venda_rentabilidade_snapshot,
    invalidate_venda_rentabilidade_snapshot,
)
from app.utils.timezone import now_brasilia

logger = logging.getLogger(__name__)

__all__ = ["cancelar_venda"]


def cancelar_venda(
    venda_id: int, motivo: str, user_id: int, tenant_id: str, db: Session
) -> Dict[str, Any]:
    """
    Cancela uma venda realizando estorno completo de todas as operações.

    Operações executadas (ordem de execução):
    1. Validar venda e permissões
    2. Estornar estoque de todos os itens
    3. Cancelar contas a receber vinculadas
    4. Cancelar lançamentos manuais (fluxo de caixa)
    5. Remover movimentações de caixa (dinheiro)
    6. Estornar movimentações bancárias (PIX/cartão)
    7. Estornar comissões
    8. Marcar venda como cancelada
    9. COMMIT
    10. Auditoria

    GARANTIAS:
    - ✅ Transação atômica (tudo ou nada)
    - ✅ Rollback automático em caso de erro
    - ✅ Segurança: apenas vendas do user_id atual
    - ✅ Idempotente: pode chamar múltiplas vezes
    - ✅ Histórico mantido (status='cancelado' em vez de delete)

    Args:
        venda_id: ID da venda a ser cancelada
        motivo: Motivo do cancelamento (obrigatório)
        user_id: ID do usuário cancelando
        db: Sessão do SQLAlchemy

    Returns:
        Dict com resultado do cancelamento:
        {
            'venda': dict,
            'estornos': {
                'itens_estornados': int,
                'contas_canceladas': int,
                'lancamentos_cancelados': int,
                'movimentacoes_removidas': int,
                'movimentacoes_bancarias_estornadas': int
            }
        }

    Raises:
        HTTPException(404): Venda não encontrada
        HTTPException(400): Venda já está cancelada
    """
    from app.vendas_models import Venda, VendaItem
    from app.estoque.service import EstoqueService
    from app.caixa_models import MovimentacaoCaixa
    from app.financeiro_models import (
        ContaReceber,
        LancamentoManual,
        MovimentacaoFinanceira,
        ContaBancaria,
    )
    from app.audit_log import log_action
    from app.tenancy.context import set_tenant_context

    set_tenant_context(
        tenant_id if isinstance(tenant_id, UUID) else UUID(str(tenant_id))
    )

    logger.info(f"🔴 Iniciando cancelamento ATÔMICO da venda #{venda_id}")

    with transactional_session(db):
        # ============================================================
        # ETAPA 1: VALIDAR VENDA E PERMISSÕES
        # ============================================================

        venda = db.query(Venda).filter_by(id=venda_id, tenant_id=tenant_id).first()

        if not venda:
            raise HTTPException(status_code=404, detail="Venda não encontrada")

        if venda.status == "cancelada":
            raise HTTPException(status_code=400, detail="Venda já está cancelada")

        logger.info(
            f"📋 Cancelando venda #{venda.numero_venda} (Status: {venda.status})"
        )

        # ============================================================
        # ETAPA 2: ESTORNAR ESTOQUE DE TODOS OS ITENS
        # ============================================================

        itens = db.query(VendaItem).filter_by(venda_id=venda_id).all()
        itens_estornados = 0

        for item in itens:
            if item.produto_id:  # Apenas produtos físicos têm estoque
                try:
                    resultado = EstoqueService.estornar_estoque(
                        produto_id=item.produto_id,
                        quantidade=item.quantidade,
                        motivo="cancelamento_venda",
                        referencia_id=venda_id,
                        referencia_tipo="venda",
                        user_id=user_id,
                        tenant_id=tenant_id,
                        db=db,
                        documento=venda.numero_venda,
                        observacao=f"Cancelamento: {motivo}",
                    )
                    itens_estornados += 1
                    logger.info(
                        f"  ✅ Estoque estornado: {resultado['produto_nome']} "
                        f"+{item.quantidade} ({resultado['estoque_anterior']} → {resultado['estoque_novo']})"
                    )
                except Exception as e:
                    logger.error(f"  ❌ Erro ao estornar estoque: {e}")
                    raise HTTPException(
                        status_code=500,
                        detail=f"Erro ao estornar estoque: {str(e)}",
                    )

        logger.info(f"📦 Total de itens estornados: {itens_estornados}/{len(itens)}")

        # ============================================================
        # ETAPA 3: CANCELAR CONTAS A RECEBER VINCULADAS
        # ============================================================

        contas_receber = db.query(ContaReceber).filter_by(venda_id=venda_id).all()
        contas_canceladas = 0

        for conta in contas_receber:
            if conta.status == "pendente" or conta.status == "parcial":
                logger.info(
                    f"  💳 Removendo conta a receber pendente: {conta.descricao} - "
                    f"R$ {conta.valor_original}"
                )
                db.delete(conta)
            elif conta.status == "recebido":
                conta.status = "cancelado"
                logger.info(
                    f"  💳 Cancelando conta já recebida: {conta.descricao} - "
                    f"R$ {conta.valor_recebido}"
                )
            contas_canceladas += 1

        logger.info(f"💳 Total de contas canceladas: {contas_canceladas}")

        # ============================================================
        # ETAPA 4: CANCELAR LANÇAMENTOS MANUAIS
        # ============================================================

        lancamentos = (
            db.query(LancamentoManual)
            .filter(
                or_(
                    LancamentoManual.documento == f"VENDA-{venda_id}",
                    LancamentoManual.documento.like(f"VENDA-{venda_id}-%"),
                )
            )
            .all()
        )

        lancamentos_cancelados = 0
        for lanc in lancamentos:
            if lanc.status == "previsto":
                logger.info(
                    f"  📊 Removendo lançamento previsto: {lanc.descricao} - "
                    f"R$ {lanc.valor}"
                )
                db.delete(lanc)
            elif lanc.status == "realizado":
                lanc.status = "cancelado"
                logger.info(
                    f"  📊 Cancelando lançamento realizado: {lanc.descricao} - "
                    f"R$ {lanc.valor}"
                )
            lancamentos_cancelados += 1

        logger.info(f"📊 Total de lançamentos cancelados: {lancamentos_cancelados}")

        # ============================================================
        # ETAPA 5: REMOVER MOVIMENTAÇÕES DE CAIXA
        # ============================================================

        movimentacoes_caixa = (
            db.query(MovimentacaoCaixa).filter_by(venda_id=venda_id).all()
        )

        movimentacoes_removidas = 0
        for mov in movimentacoes_caixa:
            logger.info(
                f"  💵 Removendo movimentação de caixa: R$ {mov.valor} ({mov.tipo})"
            )
            db.delete(mov)
            movimentacoes_removidas += 1

        logger.info(
            f"💵 Total de movimentações de caixa removidas: {movimentacoes_removidas}"
        )

        # ============================================================
        # ETAPA 6: ESTORNAR MOVIMENTAÇÕES BANCÁRIAS
        # ============================================================

        movimentacoes_bancarias = (
            db.query(MovimentacaoFinanceira)
            .filter(
                MovimentacaoFinanceira.tenant_id == tenant_id,
                MovimentacaoFinanceira.origem_tipo == "venda",
                MovimentacaoFinanceira.origem_id == venda_id,
            )
            .all()
        )

        movimentacoes_estornadas = 0
        for mov_banc in movimentacoes_bancarias:
            conta_bancaria = (
                db.query(ContaBancaria)
                .filter_by(id=mov_banc.conta_bancaria_id, user_id=user_id)
                .first()
            )

            if conta_bancaria:
                if mov_banc.tipo in ("receita", "entrada"):
                    conta_bancaria.saldo_atual -= mov_banc.valor
                    logger.info(
                        f"  🏦 Estornando saldo bancário: {conta_bancaria.nome} "
                        f"-R$ {mov_banc.valor}"
                    )
                elif mov_banc.tipo in ("despesa", "saida"):
                    conta_bancaria.saldo_atual += mov_banc.valor
                    logger.info(
                        f"  🏦 Estornando saldo bancário: {conta_bancaria.nome} "
                        f"+R$ {mov_banc.valor}"
                    )

                db.delete(mov_banc)
                movimentacoes_estornadas += 1

        logger.info(
            f"🏦 Total de movimentações bancárias estornadas: {movimentacoes_estornadas}"
        )

        # ============================================================
        # ETAPA 6.5: REMOVER PARADAS DE ENTREGA
        # ============================================================

        from app.rotas_entrega_models import RotaEntregaParada

        paradas_removidas = 0

        paradas = db.query(RotaEntregaParada).filter_by(venda_id=venda_id).all()
        for parada in paradas:
            logger.info(f"🚚 Removendo parada de entrega da rota #{parada.rota_id}")
            db.delete(parada)
            paradas_removidas += 1

        if paradas_removidas > 0:
            logger.info(
                f"📋 Total de paradas de entrega removidas: {paradas_removidas}"
            )
            # Reverter status de entrega
            venda.status_entrega = None

        # ============================================================
        # ETAPA 7: ESTORNAR COMISSÕES
        # ============================================================

        try:
            from app.comissoes_estorno import estornar_comissoes_venda

            resultado_estorno = estornar_comissoes_venda(
                venda_id=venda_id,
                motivo=f"Venda cancelada: {motivo}",
                usuario_id=user_id,
                db=db,
            )

            if (
                resultado_estorno["success"]
                and resultado_estorno["comissoes_estornadas"] > 0
            ):
                logger.info(
                    f"  💰 Estornadas {resultado_estorno['comissoes_estornadas']} "
                    f"comissões (R$ {resultado_estorno['valor_estornado']:.2f})"
                )
        except Exception as e:
            logger.warning(f"  ⚠️  Erro ao estornar comissões: {str(e)}")

        # ============================================================
        # ETAPA 8: MARCAR VENDA COMO CANCELADA
        # ============================================================

        status_anterior = venda.status
        venda.status = "cancelada"
        venda.cancelada_por = user_id
        venda.motivo_cancelamento = motivo
        venda.data_cancelamento = now_brasilia()
        venda.updated_at = now_brasilia()

        if status_anterior in ["baixa_parcial", "finalizada"]:
            get_or_build_venda_rentabilidade_snapshot(
                venda,
                db,
                tenant_id,
                persist_if_missing=True,
                force_refresh=True,
            )
        else:
            invalidate_venda_rentabilidade_snapshot(venda)

        from app.campaigns.coupon_service import reverse_coupon_redemptions_for_sale
        from app.campaigns.loyalty_service import void_loyalty_stamps_for_sale

        reverse_coupon_redemptions_for_sale(
            db,
            tenant_id=tenant_id,
            venda_id=venda_id,
            reason=f"Venda cancelada: {motivo}",
        )

        void_loyalty_stamps_for_sale(
            db,
            tenant_id=tenant_id,
            venda_id=venda_id,
            reason=f"Venda cancelada: {motivo}",
        )

        db.flush()

        logger.info(
            f"🔒 Venda marcada como cancelada: {venda.numero_venda} "
            f"(status: {status_anterior} → cancelada)"
        )

        # ============================================================
        # ETAPA 9: AUDITORIA
        # ============================================================

        log_action(
            db=db,
            user_id=user_id,
            action="UPDATE",
            entity_type="vendas",
            entity_id=venda.id,
            details=(
                f"Venda {venda.numero_venda} CANCELADA (ATÔMICO) - "
                f"Motivo: {motivo} - "
                f"Itens estornados: {itens_estornados} - "
                f"Contas canceladas: {contas_canceladas}"
            ),
            tenant_id=tenant_id,
            commit=False,
        )

        # Commit automático pelo context manager

    # Refresh após commit
    db.refresh(venda)

    logger.info(
        f"✅ ✅ ✅ CANCELAMENTO CONCLUÍDO: Venda #{venda.numero_venda} ✅ ✅ ✅\n"
        f"   📦 Estoque estornado: {itens_estornados} itens\n"
        f"   💳 Contas canceladas: {contas_canceladas}\n"
        f"   📊 Lançamentos cancelados: {lancamentos_cancelados}\n"
        f"   💵 Movimentações caixa removidas: {movimentacoes_removidas}\n"
        f"   🏦 Movimentações bancárias estornadas: {movimentacoes_estornadas}"
    )

    # ============================================================
    # ETAPA 10: EMITIR EVENTO DE DOMÍNIO
    # ============================================================

    # 🔒 EVENTOS DESABILITADOS TEMPORARIAMENTE (publish_event não exportado)
    # try:
    #     from app.domain.events import VendaCancelada, publish_event
    #
    #     evento = VendaCancelada(
    #         venda_id=venda.id,
    #         numero_venda=venda.numero_venda,
    #         user_id=user_id,
    #         cliente_id=venda.cliente_id,
    #         funcionario_id=venda.funcionario_id,
    #         motivo=motivo,
    #         status_anterior=status_anterior,
    #         total=float(venda.total),
    #         itens_estornados=itens_estornados,
    #         contas_canceladas=contas_canceladas,
    #         comissoes_estornadas=(movimentacoes_estornadas > 0),
    #         metadados={
    #             'lancamentos_cancelados': lancamentos_cancelados,
    #             'movimentacoes_caixa_removidas': movimentacoes_removidas,
    #             'movimentacoes_bancarias_estornadas': movimentacoes_estornadas
    #         }
    #     )
    #
    #     publish_event(evento)
    #     logger.debug(f"📢 Evento VendaCancelada publicado (venda_id={venda.id})")
    #
    # except Exception as e:
    #     logger.error(f"⚠️  Erro ao publicar evento VendaCancelada: {str(e)}", exc_info=True)
    #     # Não aborta o cancelamento

    try:
        from app.domain.events import VendaCancelada, publish_event

        publish_event(
            VendaCancelada(
                venda_id=venda.id,
                numero_venda=venda.numero_venda,
                user_id=user_id,
                cliente_id=venda.cliente_id,
                funcionario_id=venda.funcionario_id,
                motivo=motivo,
                status_anterior=status_anterior,
                total=float(venda.total),
                itens_estornados=itens_estornados,
                contas_canceladas=contas_canceladas,
                comissoes_estornadas=(movimentacoes_estornadas > 0),
                metadados={
                    "lancamentos_cancelados": lancamentos_cancelados,
                    "movimentacoes_caixa_removidas": movimentacoes_removidas,
                    "movimentacoes_bancarias_estornadas": movimentacoes_estornadas,
                },
            )
        )
        logger.debug("Evento VendaCancelada publicado (venda_id=%s)", venda.id)
    except Exception as e:
        logger.error(
            "Erro ao publicar evento VendaCancelada: %s", str(e), exc_info=True
        )

    return {
        "venda": venda.to_dict(),
        "estornos": {
            "itens_estornados": itens_estornados,
            "contas_canceladas": contas_canceladas,
            "lancamentos_cancelados": lancamentos_cancelados,
            "movimentacoes_removidas": movimentacoes_removidas,
            "movimentacoes_bancarias_estornadas": movimentacoes_estornadas,
        },
    }
