# -*- coding: utf-8 -*-
"""Operacoes secundarias executadas apos o commit da venda."""

import logging
from typing import Any, Dict, List

from sqlalchemy.orm import Session

from app.financeiro import ContasReceberService
from app.vendas.pos_processamento import (
    processar_contas_pagar_entrega,
    processar_contas_pagar_taxas,
)

logger = logging.getLogger(__name__)

__all__ = ["processar_pos_commit_finalizacao"]


def processar_pos_commit_finalizacao(
    *,
    venda: Any,
    pagamentos: List[Dict[str, Any]],
    user_id: int,
    tenant_id: str,
    db: Session,
) -> List[int]:
    # ETAPA 8: OPERAÇÕES PÓS-COMMIT (não abortam se falharem)
    # ============================================================

    # Criar novas contas a receber
    contas_criadas_ids = []
    try:
        resultado_contas = ContasReceberService.criar_de_venda(
            venda=venda, pagamentos=pagamentos, user_id=user_id, db=db
        )
        contas_criadas_ids = resultado_contas["contas_criadas"]
        db.commit()  # Commit separado para contas
        logger.info(
            f"📋 Contas a receber criadas: {resultado_contas['total_contas']} conta(s), "
            f"{len(resultado_contas['lancamentos_criados'])} lançamento(s)"
        )
    except Exception as e:
        logger.error(f"⚠️ Erro ao criar contas a receber: {str(e)}", exc_info=True)
        db.rollback()  # Rollback apenas das contas (venda já commitada)

    # 🚚 Criar contas a pagar de entrega (taxa entregador + custo operacional)
    try:
        resultado_entrega = processar_contas_pagar_entrega(
            venda=venda, user_id=user_id, tenant_id=tenant_id, db=db
        )
        if resultado_entrega["success"]:
            db.commit()  # Commit separado para contas a pagar
            logger.info(
                f"🚚 Contas a pagar de entrega criadas: {resultado_entrega['total_contas']} conta(s), "
                f"R$ {resultado_entrega['valor_total']:.2f}"
            )
    except Exception as e:
        logger.error(
            f"⚠️ Erro ao criar contas a pagar de entrega: {str(e)}",
            exc_info=True,
        )
        db.rollback()  # Rollback apenas das contas (venda já commitada)

    # 💳 Criar contas a pagar de taxas de pagamento
    logger.info(
        f"💳 Iniciando processamento de taxas de pagamento - Venda #{venda.numero_venda}"
    )
    try:
        pagamentos_para_taxas = [
            type(
                "obj",
                (object,),
                {
                    "forma_pagamento": p["forma_pagamento"],
                    "valor": p["valor"],
                    "numero_parcelas": p.get("numero_parcelas", 1),
                },
            )()
            for p in pagamentos
        ]

        logger.info(f"💳 Total de pagamentos a processar: {len(pagamentos_para_taxas)}")
        for pag in pagamentos_para_taxas:
            logger.info(f"  - {pag.forma_pagamento}: R$ {pag.valor}")

        resultado_taxas = processar_contas_pagar_taxas(
            venda=venda,
            pagamentos=pagamentos_para_taxas,
            user_id=user_id,
            tenant_id=tenant_id,
            db=db,
        )

        logger.info(f"💳 Resultado do processamento: {resultado_taxas}")

        if resultado_taxas["success"]:
            db.commit()  # Commit separado para contas a pagar
            logger.info(
                f"💳 Contas a pagar de taxas criadas: {resultado_taxas['total_contas']} conta(s), "
                f"R$ {resultado_taxas['valor_total']:.2f}"
            )
        else:
            logger.warning(
                f"⚠️ Processamento de taxas falhou: {resultado_taxas.get('error', 'Erro desconhecido')}"
            )
            db.rollback()  # Limpa falha secundaria; a venda ja foi commitada antes dos efeitos financeiros
    except Exception as e:
        logger.error(
            f"⚠️ Erro ao criar contas a pagar de taxas: {str(e)}", exc_info=True
        )
        db.rollback()  # Rollback apenas das contas (venda já commitada)

    # 📢 Enfileirar evento de campanha (purchase_completed)
    if venda.status == "finalizada" and venda.cliente_id:
        try:
            from app.campaigns.models import CampaignEventQueue, EventOriginEnum
            import uuid as _uuid

            evento_campanha = CampaignEventQueue(
                tenant_id=_uuid.UUID(str(tenant_id)),
                event_type="purchase_completed",
                event_origin=EventOriginEnum.user_action,
                event_depth=0,
                payload={
                    "customer_id": venda.cliente_id,
                    "venda_id": venda.id,
                    "venda_total": float(venda.total),
                    "canal": venda.canal or "loja_fisica",
                },
            )
            db.add(evento_campanha)
            db.commit()
            logger.info(
                "📢 [Campanhas] purchase_completed enfileirado: "
                "venda=%s cliente_id=%d total=R$%.2f",
                venda.numero_venda,
                venda.cliente_id,
                float(venda.total),
            )
        except Exception as e:
            logger.warning(
                "[Campanhas] Falha ao enfileirar purchase_completed (não crítico): %s",
                e,
            )
            db.rollback()

    return contas_criadas_ids
