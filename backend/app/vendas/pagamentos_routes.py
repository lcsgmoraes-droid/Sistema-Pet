"""Rotas de pagamentos vinculadas a vendas."""

import logging
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.audit_log import log_action
from app.auth.dependencies import get_current_user_and_tenant
from app.db import get_session
from app.financeiro_models import ContaReceber
from app.services.venda_rentabilidade_snapshot_service import (
    get_or_build_venda_rentabilidade_snapshot,
    invalidate_venda_rentabilidade_snapshot,
)
from app.vendas.routes_common import _validar_tenant_e_obter_usuario
from app.vendas_models import Venda, VendaPagamento

router = APIRouter()
logger = logging.getLogger(__name__)


@router.patch("/{venda_id}/pagamento/{pagamento_id}/nsu")
def atualizar_nsu_pagamento(
    venda_id: int,
    pagamento_id: int,
    nsu_data: dict,
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    """
    Atualiza apenas o NSU de um pagamento em cartão.
    Usado pela tela de conciliação para preencher NSU manualmente.
    """
    current_user, tenant_id = _validar_tenant_e_obter_usuario(user_and_tenant)

    # Buscar a venda
    venda = db.query(Venda).filter_by(id=venda_id, tenant_id=tenant_id).first()

    if not venda:
        raise HTTPException(status_code=404, detail="Venda não encontrada")

    # Buscar o pagamento
    pagamento = (
        db.query(VendaPagamento)
        .filter_by(id=pagamento_id, venda_id=venda_id, tenant_id=tenant_id)
        .first()
    )

    if not pagamento:
        raise HTTPException(status_code=404, detail="Pagamento não encontrado")

    # Extrair NSU do body
    novo_nsu = nsu_data.get("nsu_cartao", "").strip()
    if not novo_nsu:
        raise HTTPException(status_code=400, detail="NSU não informado")

    # VALIDAR NSU DUPLICADO (mesma lógica do VendaService)
    if pagamento.operadora_id:
        nsu_duplicado = (
            db.query(VendaPagamento)
            .filter(
                VendaPagamento.tenant_id == tenant_id,
                VendaPagamento.nsu_cartao == novo_nsu,
                VendaPagamento.operadora_id == pagamento.operadora_id,
                VendaPagamento.id != pagamento_id,  # Excluir o próprio pagamento
            )
            .first()
        )

        if nsu_duplicado:
            venda_duplicada = (
                db.query(Venda).filter_by(id=nsu_duplicado.venda_id).first()
            )
            raise HTTPException(
                status_code=400,
                detail=f"❌ NSU DUPLICADO: O NSU '{novo_nsu}' já está vinculado à "
                f"Venda {venda_duplicada.numero_venda if venda_duplicada else nsu_duplicado.venda_id}. "
                f"Cada NSU deve ser usado apenas uma vez por operadora.",
            )

    # Atualizar NSU
    nsu_anterior = pagamento.nsu_cartao
    pagamento.nsu_cartao = novo_nsu
    pagamento.updated_at = datetime.now()

    db.commit()
    db.refresh(pagamento)

    log_action(
        db=db,
        user_id=current_user.id,
        action="update",
        entity_type="venda_pagamento",
        entity_id=pagamento.id,
        details=f"NSU do pagamento atualizado: {nsu_anterior} → {novo_nsu} (Venda {venda.numero_venda})",
    )

    return {
        "success": True,
        "nsu_cartao": novo_nsu,
        "mensagem": f"NSU atualizado para {novo_nsu}",
    }


@router.get("/{venda_id}/pagamentos")
def listar_pagamentos_venda(
    venda_id: int,
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    """Lista todos os pagamentos de uma venda"""
    current_user, tenant_id = _validar_tenant_e_obter_usuario(user_and_tenant)

    venda = db.query(Venda).filter_by(id=venda_id, tenant_id=tenant_id).first()

    if not venda:
        raise HTTPException(status_code=404, detail="Venda não encontrada")

    pagamentos = (
        db.query(VendaPagamento)
        .filter_by(venda_id=venda.id)
        .order_by(VendaPagamento.data_pagamento)
        .all()
    )

    total_pago = sum(float(p.valor) for p in pagamentos)
    valor_restante = float(venda.total) - total_pago

    return {
        "venda_id": venda.id,
        "numero_venda": venda.numero_venda,
        "total_venda": float(venda.total),
        "total_pago": total_pago,
        "valor_restante": max(0, valor_restante),
        "status": venda.status,
        "pagamentos": [p.to_dict() for p in pagamentos],
    }


@router.delete("/pagamentos/{pagamento_id}")
def excluir_pagamento(
    pagamento_id: int,
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    """Excluir um pagamento de uma venda"""
    current_user, tenant_id = _validar_tenant_e_obter_usuario(user_and_tenant)

    # 🔒 SEGURANÇA: Buscar o pagamento validando que a venda pertence ao usuário
    # Primeiro buscamos o pagamento, depois validamos a venda
    pagamento = db.query(VendaPagamento).filter_by(id=pagamento_id).first()

    if not pagamento:
        raise HTTPException(status_code=404, detail="Pagamento não encontrado")

    # 🔒 SEGURANÇA: Validar que a venda do pagamento pertence ao tenant
    venda = (
        db.query(Venda).filter_by(id=pagamento.venda_id, tenant_id=tenant_id).first()
    )

    if not venda:
        raise HTTPException(status_code=404, detail="Venda não encontrada")

    # Impedir exclusão de pagamento em vendas com NF emitida
    if venda.status == "pago_nf":
        raise HTTPException(
            status_code=400,
            detail="Não é possível excluir pagamentos de uma venda com NF-e emitida. Cancele a nota fiscal primeiro.",
        )

    # ⚠️ IMPORTANTE: Se venda está finalizada/baixa_parcial, não pode excluir pagamento
    # Usuário deve REABRIR a venda primeiro!
    if venda.status in ["finalizada", "baixa_parcial"]:
        raise HTTPException(
            status_code=400,
            detail='Não é possível excluir pagamentos de uma venda finalizada. Reabra a venda primeiro através do botão "Reabrir Venda".',
        )

    # Registrar auditoria
    try:
        log_action(
            db=db,
            user_id=current_user.id,
            action="delete",
            entity_type="venda_pagamentos",
            entity_id=pagamento.id,
            details=f"Excluído pagamento de R$ {pagamento.valor} ({pagamento.forma_pagamento}) da venda #{venda.id}",
        )
    except Exception as e:
        logger.info(f"⚠️ Erro ao registrar auditoria: {e}")

    # Sincronizar exclusão com contas a receber e lançamentos manuais
    try:
        contas = db.query(ContaReceber).filter(ContaReceber.venda_id == venda.id).all()

        for conta in contas:
            # Deletar conta a receber
            try:
                db.delete(conta)
                logger.info(f"🗑️ Conta a receber {conta.id} excluída")
            except Exception as e:
                logger.info(f"⚠️ Erro ao deletar conta: {e}")
    except Exception as e:
        logger.info(f"⚠️ Erro ao buscar contas a receber: {e}")

    # Excluir o pagamento
    db.delete(pagamento)
    db.flush()  # Garantir que o delete seja processado antes da query

    # Recalcular total pago
    pagamentos_restantes = db.query(VendaPagamento).filter_by(venda_id=venda.id).all()
    total_pago = sum(float(p.valor) for p in pagamentos_restantes)
    total_venda = float(venda.total)

    logger.info(
        f"DEBUG excluir_pagamento: total_pago={total_pago}, total_venda={total_venda}"
    )

    # Atualizar status da venda
    if total_pago == 0:
        venda.status = "aberta"
        logger.info("DEBUG: Mudou status para ABERTA (total_pago = 0)")
        invalidate_venda_rentabilidade_snapshot(venda)
    elif total_pago >= total_venda:
        venda.status = "finalizada"
        logger.info("DEBUG: Mudou status para FINALIZADA (total_pago >= total_venda)")
        get_or_build_venda_rentabilidade_snapshot(
            venda,
            db,
            tenant_id,
            persist_if_missing=True,
            force_refresh=True,
        )
    else:
        venda.status = "baixa_parcial"
        logger.info("DEBUG: Mudou status para BAIXA_PARCIAL")
        get_or_build_venda_rentabilidade_snapshot(
            venda,
            db,
            tenant_id,
            persist_if_missing=True,
            force_refresh=True,
        )

    db.commit()

    return {
        "message": "Pagamento excluído com sucesso",
        "venda_id": venda.id,
        "novo_status": venda.status,
        "total_pago": total_pago,
        "valor_restante": max(0, total_venda - total_pago),
    }
