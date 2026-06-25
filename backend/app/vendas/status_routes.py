"""Rotas de reabertura e alteracao de status de vendas."""

import logging
from datetime import datetime
from decimal import Decimal

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
    _listar_pagamentos_venda_para_comissao,
    _parcelas_com_comissao_funcionario,
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

    venda = db.query(Venda).filter_by(id=venda_id, tenant_id=tenant_id).first()

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

                # Remover comissões
                _remover_comissoes_venda(db, venda.id, tenant_id)

                # Também remover provisões de comissão em contas_pagar
                _remover_provisoes_comissao_venda(db, venda.id, tenant_id)

                struct_logger.info(
                    event="COMMISSION_CANCELLED",
                    message="Comissões canceladas com sucesso",
                    venda_id=venda.id,
                    count=comissoes_removidas,
                )
            else:
                logger.info(f"ℹ️  Venda #{venda.id} não tinha comissões para cancelar")

        except Exception as e:
            logger.error(
                f"❌ Erro ao cancelar comissões da venda {venda.id}: {e}", exc_info=True
            )
            struct_logger.error(
                event="COMMISSION_CANCEL_ERROR",
                message=f"Erro ao cancelar comissões: {str(e)}",
                venda_id=venda.id,
                error=str(e),
            )
            # Prosseguir com reabertura mesmo se falhar cancelamento de comissões

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
    from app.campaigns.loyalty_service import void_loyalty_stamps_for_sale
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


@router.patch("/{venda_id}/status")
def atualizar_status_venda(
    venda_id: int,
    status_data: dict,
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    """Atualiza apenas o status da venda"""
    current_user, tenant_id = _validar_tenant_e_obter_usuario(user_and_tenant)

    # Buscar a venda
    venda = db.query(Venda).filter_by(id=venda_id, tenant_id=tenant_id).first()

    if not venda:
        raise HTTPException(status_code=404, detail="Venda não encontrada")

    # Extrair status do body
    novo_status = status_data.get("status")
    if not novo_status:
        raise HTTPException(status_code=400, detail="Status não informado")

    status_anterior = venda.status
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
    elif novo_status == "aberta":
        invalidate_venda_rentabilidade_snapshot(venda)

    if status_anterior in ["finalizada", "baixa_parcial"] and novo_status not in [
        "finalizada",
        "baixa_parcial",
    ]:
        from app.campaigns.coupon_service import reverse_coupon_redemptions_for_sale
        from app.campaigns.loyalty_service import void_loyalty_stamps_for_sale

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
    # 🆕 GERAR COMISSÕES se estiver finalizando a venda (apenas se funcionário/veterinário foi selecionado)
    if (
        novo_status == "finalizada"
        and status_anterior != "finalizada"
        and venda.funcionario_id
    ):
        try:
            from app.comissoes_service import gerar_comissoes_venda

            struct_logger.info(
                event="COMMISSION_START",
                message=f"Gerando comissões via PATCH /status (status: {status_anterior} → {novo_status})",
                venda_id=venda.id,
                funcionario_id=venda.funcionario_id,
                trigger="status_change",
            )

            # 🔍 BUSCAR TODOS OS PAGAMENTOS DA VENDA
            # Precisamos gerar comissões para TODOS os pagamentos que ainda não têm comissão
            todos_pagamentos = _listar_pagamentos_venda_para_comissao(
                db, venda.id, tenant_id
            )

            if not todos_pagamentos:
                logger.info("ℹ️  Nenhum pagamento encontrado na venda")
            else:
                # 🔢 Verificar quais pagamentos já têm comissão
                parcelas_com_comissao = _parcelas_com_comissao_funcionario(
                    db,
                    venda.id,
                    venda.funcionario_id,
                    tenant_id,
                )
                logger.info(
                    f"📊 Pagamentos: {len(todos_pagamentos)} total, {len(parcelas_com_comissao)} já com comissão"
                )

                # 🔄 GERAR UMA COMISSÃO PARA CADA PAGAMENTO SEM COMISSÃO
                comissoes_geradas = 0
                total_comissoes = Decimal("0")

                for idx, pagamento_row in enumerate(todos_pagamentos, start=1):
                    parcela_numero = idx

                    # Pular se já tem comissão
                    if parcela_numero in parcelas_com_comissao:
                        logger.info(
                            f"⏭️  Parcela {parcela_numero} já tem comissão - pulando"
                        )
                        continue

                    valor_pagamento = Decimal(str(pagamento_row[2]))
                    forma_pagamento = pagamento_row[1]

                    struct_logger.info(
                        event="COMMISSION_START",
                        message="Gerando comissão para pagamento",
                        venda_id=venda.id,
                        funcionario_id=venda.funcionario_id,
                        valor_pago=float(valor_pagamento),
                        forma_pagamento=forma_pagamento,
                        parcela_numero=parcela_numero,
                    )

                    resultado = gerar_comissoes_venda(
                        venda_id=venda.id,
                        funcionario_id=venda.funcionario_id,
                        valor_pago=valor_pagamento,
                        forma_pagamento=forma_pagamento,
                        parcela_numero=parcela_numero,
                        db=db,
                    )

                    if resultado and resultado.get("success"):
                        if not resultado.get("duplicated"):
                            comissoes_geradas += 1
                            total_comissoes += Decimal(
                                str(resultado.get("total_comissao", 0))
                            )
                            struct_logger.info(
                                event="COMMISSION_GENERATED",
                                message="Comissão gerada com sucesso",
                                venda_id=venda.id,
                                parcela_numero=parcela_numero,
                                total_comissao=float(
                                    resultado.get("total_comissao", 0)
                                ),
                            )

                if comissoes_geradas > 0:
                    logger.info(
                        f"✅ {comissoes_geradas} comissões geradas - Total: R$ {total_comissoes:.2f}"
                    )
                else:
                    logger.info(
                        "ℹ️  Nenhuma comissão nova gerada (todas já existiam ou sem configuração)"
                    )

        except Exception as e:
            logger.error(
                f"❌ Erro ao gerar comissões para venda {venda.id}: {str(e)}",
                exc_info=True,
            )
            struct_logger.error(
                event="COMMISSION_ERROR",
                message=f"Erro ao gerar comissões: {str(e)}",
                venda_id=venda.id,
                error=str(e),
                trigger="status_change",
            )
            # Não abortar a atualização por erro nas comissões

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

    return {"message": "Status atualizado com sucesso", "status": venda.status}
