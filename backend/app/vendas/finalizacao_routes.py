"""Rota de finalizacao de vendas e pos-processamentos imediatos."""

import logging

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.audit_log import log_action
from app.auth.dependencies import get_current_user_and_tenant
from app.db import get_session
from app.idempotency import idempotent
from app.services.opportunity_background_processor import get_opportunity_processor
from app.utils.logger import logger as struct_logger, set_user_id
from app.vendas.comissoes import _gerar_comissoes_pendentes_venda
from app.vendas.routes_common import _validar_tenant_e_obter_usuario
from app.vendas.schemas import FinalizarVendaRequest
from app.vendas_models import Venda

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/{venda_id}/finalizar")
@idempotent()  # 🔒 IDEMPOTÊNCIA: evita finalização duplicada
async def finalizar_venda(
    venda_id: int,
    dados: FinalizarVendaRequest,
    request: Request,
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    """
    Finaliza uma venda com os pagamentos.

    REFATORADO: Utiliza VendaService.finalizar_venda() para orquestração atômica.
    Esta rota agora é um thin wrapper que apenas processa comissões e lembretes pós-commit.
    """
    current_user, tenant_id = _validar_tenant_e_obter_usuario(user_and_tenant)

    # 🔒 HARDENING 1: Logs estruturados e validação de estado
    set_user_id(current_user.id)
    struct_logger.info(
        event="FINALIZE_START",
        message=f"Iniciando finalização da venda #{venda_id}",
        venda_id=venda_id,
        total_pagamentos=len(dados.pagamentos) if dados and dados.pagamentos else 0,
    )

    # ========================================
    # 🔒 VALIDAÇÃO: ENTREGADOR OBRIGATÓRIO QUANDO TEM ENTREGA
    # ========================================
    venda_temp = db.query(Venda).filter_by(id=venda_id, tenant_id=tenant_id).first()
    if venda_temp and venda_temp.tem_entrega and not venda_temp.entregador_id:
        raise HTTPException(
            status_code=400,
            detail="❌ Não é possível finalizar. Entregador é obrigatório quando a venda tem entrega. Atribua um entregador antes de finalizar.",
        )

    # ============================================================
    # 🔥 ORQUESTRAÇÃO ATÔMICA VIA VendaService
    # ============================================================

    from app.vendas import VendaService

    # Converter pagamentos do request para formato do service
    pagamentos_list = (
        [
            {
                "forma_pagamento": p.forma_pagamento,
                "valor": p.valor,
                "numero_parcelas": p.numero_parcelas,
                "bandeira": getattr(p, "bandeira", None),
                "nsu_cartao": getattr(p, "nsu_cartao", None),
                "operadora_id": getattr(
                    p, "operadora_id", None
                ),  # 🆕 Capturar operadora
            }
            for p in dados.pagamentos
        ]
        if dados.pagamentos
        else []
    )

    # Executar finalização com transação atômica única
    resultado = VendaService.finalizar_venda(
        venda_id=venda_id,
        pagamentos=pagamentos_list,
        user_id=current_user.id,
        user_nome=current_user.nome or current_user.email or "Usuário",
        tenant_id=tenant_id,
        cupom_code=dados.cupom_code,
        cupom_discount_applied=dados.cupom_discount_applied,
        db=db,
    )

    # Log de sucesso
    struct_logger.info(
        event="FINALIZE_SUCCESS",
        message="Venda finalizada com sucesso",
        venda_id=venda_id,
        numero_venda=resultado["venda"]["numero_venda"],
        status=resultado["venda"]["status"],
        total_pago=resultado["venda"]["total_pago"],
    )

    # ============================================================
    # ETAPA PÓS-COMMIT: COMISSÕES E LEMBRETES (operações secundárias)
    # ============================================================

    # Recarregar venda para ter dados atualizados após commit
    venda = db.query(Venda).filter_by(id=venda_id, tenant_id=tenant_id).first()
    if not venda:
        raise HTTPException(
            status_code=404, detail="Venda não encontrada após finalização"
        )

    if venda.funcionario_id:
        try:
            resultado_comissoes = _gerar_comissoes_pendentes_venda(
                db=db,
                venda=venda,
                tenant_id=tenant_id,
                trigger="finalize_sale",
            )
            if resultado_comissoes["comissoes_geradas"] > 0:
                logger.info(
                    "Comissoes geradas ao finalizar venda %s: %s - Total: R$ %.2f",
                    venda.id,
                    resultado_comissoes["comissoes_geradas"],
                    resultado_comissoes["total_comissoes"],
                )
                struct_logger.info(
                    event="COMMISSION_GENERATED_ON_FINALIZE",
                    message="Comissoes geradas ao finalizar venda",
                    venda_id=venda.id,
                    funcionario_id=venda.funcionario_id,
                    total_comissoes=resultado_comissoes["total_comissoes"],
                )
            else:
                logger.info("Nenhuma comissao nova gerada ao finalizar venda")
        except Exception as e:
            logger.error(
                "Erro ao gerar comissoes ao finalizar venda %s: %s",
                venda.id,
                str(e),
                exc_info=True,
            )
            # Nao abortar a finalizacao da venda por erro nas comissoes.
    else:
        logger.info("Venda sem funcionario - comissoes nao geradas")

    db.commit()

    log_action(
        db,
        current_user.id,
        "UPDATE",
        "vendas",
        venda.id,
        details=f"Venda {venda.numero_venda} finalizada - Total: R$ {float(venda.total):.2f}",
    )

    # ============================================================================
    # 💾 INVALIDAR CACHE DE OPORTUNIDADES (venda finalizada)
    # ============================================================================
    try:
        from uuid import UUID

        session_id = f"venda_{venda.id}"
        processor = get_opportunity_processor(
            tenant_id=UUID(str(tenant_id)), session_id=session_id
        )
        processor.cleanup()  # Limpa processador e invalida cache
    except Exception as e:
        logger.debug(f"Cache cleanup (finalizar): {str(e)}")
        pass

    # ✅ LOG DE SUCESSO ESTRUTURADO
    total_pago = (
        sum(float(p.valor) for p in venda.pagamentos) if venda.pagamentos else 0
    )
    recurrence_result = (resultado.get("pos_commit") or {}).get("lembretes") or {}
    lembretes_criados = recurrence_result.get("created") or []
    lembretes_atualizados = recurrence_result.get("completed") or []
    struct_logger.info(
        event="FINALIZE_COMPLETE",
        message="Venda finalizada completamente (com comissões e lembretes)",
        venda_id=venda_id,
        numero_venda=venda.numero_venda,
        status_final=venda.status,
        total_venda=float(venda.total),
        total_pagamentos=total_pago,
        forma_pagamento=dados.pagamentos[0].forma_pagamento
        if dados.pagamentos
        else None,
        lembretes_criados=len(lembretes_criados),
        lembretes_atualizados=len(lembretes_atualizados),
    )

    # Adicionar informações de lembretes no retorno
    venda_dict = venda.to_dict()
    if lembretes_criados or lembretes_atualizados:
        venda_dict["lembretes"] = {
            "criados": lembretes_criados,
            "atualizados": lembretes_atualizados,
        }

    # Adicionar dados do resultado do VendaService (se disponível)
    if "operacoes" in resultado:
        venda_dict["resultado_operacoes"] = resultado["operacoes"]

    # ============================================================
    # 🎯 CAMPANHAS — Publicar evento purchase_completed na fila
    # Nunca bloqueia a venda em caso de falha
    # ============================================================
    if venda.cliente_id:
        try:
            from app.campaigns.models import CampaignEventQueue, EventOriginEnum

            canal_venda = venda.canal or "loja_fisica"
            evento_campanha = CampaignEventQueue(
                tenant_id=tenant_id,
                event_type="purchase_completed",
                event_origin=EventOriginEnum.user_action,
                event_depth=0,
                payload={
                    "customer_id": venda.cliente_id,
                    "venda_id": venda.id,
                    "venda_total": float(venda.total or 0),
                    "canal": canal_venda,
                },
            )
            db.add(evento_campanha)
            db.commit()
            logger.info(
                "[Campanhas] purchase_completed publicado venda_id=%d cliente_id=%d",
                venda.id,
                venda.cliente_id,
            )
        except Exception as e_camp:
            logger.error("[Campanhas] Erro ao publicar purchase_completed: %s", e_camp)

    return venda_dict
