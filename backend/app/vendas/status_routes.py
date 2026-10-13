"""Rotas de reabertura e alteracao de status de vendas."""

import logging
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.audit_log import log_action
from app.auth.dependencies import get_current_user_and_tenant
from app.db import get_session
from app.services.venda_rentabilidade_snapshot_service import (
    get_or_build_venda_rentabilidade_snapshot,
    invalidate_venda_rentabilidade_snapshot,
)
from app.utils.logger import logger as struct_logger
from app.vendas.comissoes import (
    _contar_comissoes_venda,
    _gerar_comissoes_pendentes_venda,
    _remover_comissoes_venda,
)
from app.vendas.routes_common import (
    _remover_provisoes_comissao_venda,
    _validar_tenant_e_obter_usuario,
)
from app.vendas_models import Venda

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/{venda_id}/reabrir")
def reabrir_venda(
    venda_id: int,
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    """Reabre uma venda finalizada (muda status para aberta)"""
    current_user, tenant_id = _validar_tenant_e_obter_usuario(user_and_tenant)

    venda = (
        db.query(Venda)
        .filter_by(id=venda_id, tenant_id=tenant_id)
        .populate_existing()
        .with_for_update()
        .first()
    )

    if not venda:
        raise HTTPException(status_code=404, detail="Venda não encontrada")

    # Impedir reabertura de vendas com NF emitida
    if venda.status == "pago_nf":
        raise HTTPException(
            status_code=400,
            detail="Não é possível reabrir uma venda com NF-e emitida. Cancele a nota fiscal primeiro.",
        )

    # Permitir reabrir vendas finalizadas ou parcialmente pagas
    if venda.status not in ["finalizada", "baixa_parcial"]:
        raise HTTPException(
            status_code=400,
            detail="Apenas vendas finalizadas ou com baixa parcial podem ser reabertas",
        )

    # Guardar status anterior para log
    status_anterior = venda.status

    # ============================================================================
    # 🧹 CANCELAR/REMOVER COMISSÕES EXISTENTES
    # ============================================================================
    comissoes_removidas = 0
    if venda.funcionario_id:
        try:
            # Contar comissões antes de remover
            comissoes_removidas = _contar_comissoes_venda(db, venda.id, tenant_id)

            if comissoes_removidas > 0:
                struct_logger.info(
                    event="COMMISSION_CANCEL_START",
                    message=f"Cancelando {comissoes_removidas} comissões por reabertura de venda",
                    venda_id=venda.id,
                    funcionario_id=venda.funcionario_id,
                    count=comissoes_removidas,
                )

                # Cancelar primeiro as provisões e reverter o DRE enquanto os
                # vínculos com as comissões ainda existem.
                _remover_provisoes_comissao_venda(db, venda.id, tenant_id)

                # Remover os snapshots somente depois da reversão financeira.
                _remover_comissoes_venda(db, venda.id, tenant_id)

                struct_logger.info(
                    event="COMMISSION_CANCELLED",
                    message="Comissões canceladas com sucesso",
                    venda_id=venda.id,
                    count=comissoes_removidas,
                )
            else:
                logger.info(f"ℹ️  Venda #{venda.id} não tinha comissões para cancelar")

        except HTTPException:
            db.rollback()
            raise
        except Exception as e:
            db.rollback()
            logger.error(
                f"❌ Erro ao cancelar comissões da venda {venda.id}: {e}", exc_info=True
            )
            struct_logger.error(
                event="COMMISSION_CANCEL_ERROR",
                message=f"Erro ao cancelar comissões: {str(e)}",
                venda_id=venda.id,
                error=str(e),
            )
            raise HTTPException(
                status_code=500,
                detail="Não foi possível cancelar as comissões antes de reabrir a venda.",
            ) from e

    # ℹ️  NOTA: NÃO devolvemos estoque ao reabrir!
    # O estoque só é devolvido ao:
    # 1. EDITAR venda e remover produtos
    # 2. EXCLUIR/CANCELAR venda completamente
    # Reabrir serve apenas para alterar forma de pagamento, não mexe em produtos

    # Mudar status para aberta
    venda.status = "aberta"
    venda.data_finalizacao = None
    venda.updated_at = datetime.now()
    invalidate_venda_rentabilidade_snapshot(venda)

    from app.campaigns.coupon_service import reverse_coupon_redemptions_for_sale
    from app.campaigns.cashback_sale_reversal import reverse_cashback_for_sale
    from app.campaigns.loyalty_service import void_loyalty_stamps_for_sale
    from app.campaigns.sale_reopening_service import (
        void_quick_repurchase_coupons_for_sale,
    )
    from app.vendas.cashback_financeiro import (
        cancelar_despesas_cashback_venda,
        remover_pagamentos_cashback_venda,
    )
    from app.services.business_audit_service import (
        build_sale_reopened_metadata,
        log_business_event,
    )

    coupon_reversal_result = reverse_coupon_redemptions_for_sale(
        db,
        tenant_id=tenant_id,
        venda_id=venda.id,
        reason="Venda reaberta para edicao",
    )

    loyalty_void_result = void_loyalty_stamps_for_sale(
        db,
        tenant_id=tenant_id,
        venda_id=venda.id,
        reason="Venda reaberta para edicao",
    )
    void_quick_repurchase_coupons_for_sale(db, tenant_id=tenant_id, venda_id=venda.id)
    remover_pagamentos_cashback_venda(db, tenant_id=tenant_id, venda_id=venda.id)
    if venda.cliente_id:
        reverse_cashback_for_sale(
            db,
            tenant_id=tenant_id,
            sale_id=venda.id,
            customer_id=venda.cliente_id,
        )
    cancelar_despesas_cashback_venda(
        db, tenant_id=tenant_id, numero_venda=venda.numero_venda
    )

    log_business_event(
        db=db,
        tenant_id=tenant_id,
        user_id=current_user.id,
        event="sale.reopened",
        entity_type="vendas",
        entity_id=venda.id,
        old_value={"status": status_anterior},
        metadata=build_sale_reopened_metadata(
            venda=venda,
            previous_status=status_anterior,
            commissions_removed=comissoes_removidas,
            coupon_reversal=coupon_reversal_result,
            loyalty_void=loyalty_void_result,
        ),
        details=f"Venda #{venda.id} reaberta para edicao",
        commit=False,
    )

    db.commit()
    db.refresh(venda)

    log_action(
        db=db,
        user_id=current_user.id,
        action="update",
        entity_type="vendas",
        entity_id=venda.id,
        details=f"Venda #{venda.id} reaberta (status: {status_anterior} → aberta, comissões canceladas: {comissoes_removidas})",
    )

    return venda.to_dict()


@router.patch(
    "/{venda_id}/status",
    responses={
        400: {"description": "Status inválido ou reativação de venda cancelada"},
        404: {"description": "Venda não encontrada"},
    },
)
def atualizar_status_venda(
    venda_id: int,
    status_data: dict,
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    """Atualiza status; o fechamento executa a finalização completa."""
    current_user, tenant_id = _validar_tenant_e_obter_usuario(user_and_tenant)

    # Buscar a venda
    venda = (
        db.query(Venda)
        .filter_by(id=venda_id, tenant_id=tenant_id)
        .populate_existing()
        .with_for_update()
        .first()
    )

    if not venda:
        raise HTTPException(status_code=404, detail="Venda não encontrada")

    # Extrair status do body
    novo_status = status_data.get("status")
    if not novo_status:
        raise HTTPException(status_code=400, detail="Status não informado")

    status_anterior = venda.status
    status_cashback_ativos = {"finalizada", "baixa_parcial", "pago_nf"}
    if status_anterior == "cancelada" and novo_status in status_cashback_ativos:
        raise HTTPException(
            status_code=400,
            detail="Venda cancelada não pode ser reativada como paga.",
        )

    if novo_status == "finalizada":
        # Compatibilidade com clientes que restauram uma venda reaberta via
        # PATCH: fechar precisa reaplicar cupons e benefícios, sem novo pagamento.
        if status_anterior == "finalizada":
            return {"success": True, "status": "finalizada"}
        if venda.tem_entrega and not venda.entregador_id:
            raise HTTPException(
                status_code=400,
                detail="Entregador é obrigatório quando a venda tem entrega. Atribua um entregador antes de finalizar.",
            )

        from app.vendas import VendaService

        resultado = VendaService.finalizar_venda(
            venda_id=venda_id,
            pagamentos=[],
            user_id=current_user.id,
            user_nome=getattr(current_user, "nome", None)
            or getattr(current_user, "username", None)
            or getattr(current_user, "email", None)
            or "Usuário",
            tenant_id=tenant_id,
            cupom_code=venda.cupom_code,
            cupom_discount_applied=venda.cupom_discount_applied,
            nao_gerar_beneficios=bool(venda.nao_gerar_beneficios),
            justificativa_nao_gerar_beneficios=venda.justificativa_nao_gerar_beneficios,
            db=db,
        )
        venda = db.query(Venda).filter_by(id=venda_id, tenant_id=tenant_id).first()
        if venda.funcionario_id:
            try:
                _gerar_comissoes_pendentes_venda(
                    db=db,
                    venda=venda,
                    tenant_id=tenant_id,
                    trigger="status_change",
                )
            except Exception:
                logger.exception("Erro ao gerar comissões da venda %s", venda_id)
        db.commit()
        log_action(
            db=db,
            user_id=current_user.id,
            action="update",
            entity_type="vendas",
            entity_id=venda_id,
            details=f"Status da venda #{venda_id} alterado: {status_anterior} → finalizada",
        )
        return {"success": True, "status": resultado["venda"]["status"]}

    venda.status = novo_status
    venda.updated_at = datetime.now()

    if novo_status in ["finalizada", "baixa_parcial"]:
        get_or_build_venda_rentabilidade_snapshot(
            venda,
            db,
            tenant_id,
            persist_if_missing=True,
            force_refresh=True,
        )
    if (
        status_anterior in status_cashback_ativos
        and novo_status not in status_cashback_ativos
    ):
        from app.campaigns.coupon_service import reverse_coupon_redemptions_for_sale
        from app.campaigns.loyalty_service import void_loyalty_stamps_for_sale
        from app.campaigns.sale_reopening_service import (
            void_quick_repurchase_coupons_for_sale,
        )

        reverse_coupon_redemptions_for_sale(
            db,
            tenant_id=tenant_id,
            venda_id=venda.id,
            reason=f"Status alterado para {novo_status}",
        )
        void_loyalty_stamps_for_sale(
            db,
            tenant_id=tenant_id,
            venda_id=venda.id,
            reason=f"Status alterado para {novo_status}",
        )
        if novo_status == "aberta":
            void_quick_repurchase_coupons_for_sale(
                db, tenant_id=tenant_id, venda_id=venda.id
            )
    if novo_status not in status_cashback_ativos:
        from app.campaigns.cashback_sale_reversal import reverse_cashback_for_sale
        from app.vendas.cashback_financeiro import (
            cancelar_despesas_cashback_venda,
            remover_pagamentos_cashback_venda,
        )

        remover_pagamentos_cashback_venda(db, tenant_id=tenant_id, venda_id=venda.id)
        if venda.cliente_id:
            reverse_cashback_for_sale(
                db,
                tenant_id=tenant_id,
                sale_id=venda.id,
                customer_id=venda.cliente_id,
            )
        cancelar_despesas_cashback_venda(
            db, tenant_id=tenant_id, numero_venda=venda.numero_venda
        )
        invalidate_venda_rentabilidade_snapshot(venda)
    db.commit()
    db.refresh(venda)

    log_action(
        db=db,
        user_id=current_user.id,
        action="update",
        entity_type="vendas",
        entity_id=venda.id,
        details=f"Status da venda #{venda.id} alterado: {status_anterior} → {novo_status}",
    )

    return {"success": True, "status": novo_status}
