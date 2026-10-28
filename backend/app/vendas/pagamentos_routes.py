"""Rotas de pagamentos vinculadas a vendas."""

import logging
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session, selectinload

from app.audit_log import log_action
from app.auth.dependencies import get_current_user_and_tenant
from app.db import get_session
from app.services.venda_descontos import moeda
from app.vendas.routes_common import _validar_tenant_e_obter_usuario
from app.vendas.pagamento_excedente import snapshot_pagamentos_excedente
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

    venda = (
        db.query(Venda)
        .options(selectinload(Venda.pagamentos), selectinload(Venda.contas_receber))
        .filter_by(id=venda_id, tenant_id=tenant_id)
        .populate_existing()
        .first()
    )

    if not venda:
        raise HTTPException(status_code=404, detail="Venda não encontrada")

    pagamentos = (
        db.query(VendaPagamento)
        .filter_by(venda_id=venda.id, tenant_id=tenant_id)
        .order_by(VendaPagamento.data_pagamento)
        .populate_existing()
        .all()
    )

    total = moeda(venda.total)
    recebido = monetario = beneficios = crediario = moeda(0)
    status_pagamento = "cancelado"
    if str(venda.status or "").strip().lower() in {"cancelada", "cancelado"}:
        total_pago = valor_restante = moeda(0)
    else:
        fotografia = snapshot_pagamentos_excedente(db, venda, tenant_id)
        recebido = fotografia["total_ja_pago"]
        monetario = fotografia["recebido_monetario"]
        beneficios = fotografia["creditos_utilizados"]
        crediario = fotografia["crediario_pendente"]
        total_pago = min(recebido, total)
        valor_restante = max(total - total_pago, moeda(0))
        status_pagamento = (
            "pago"
            if valor_restante == 0
            else "parcial"
            if total_pago > 0
            else "em_aberto"
        )

    return {
        "venda_id": venda.id,
        "numero_venda": venda.numero_venda,
        "total_venda": float(total),
        "total_pago": float(total_pago),
        "total_recebido": float(recebido),
        "recebido_monetario": float(monetario),
        "creditos_utilizados": float(beneficios),
        "crediario_pendente": float(crediario),
        "valor_restante": float(valor_restante),
        "status": venda.status,
        "status_pagamento": status_pagamento,
        "pagamentos": [p.to_dict() for p in pagamentos],
    }


@router.get(
    "/{venda_id}/recebimentos-historico",
    responses={404: {"description": "Venda não encontrada na empresa atual."}},
)
def listar_recebimentos_historico_venda(
    venda_id: int,
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    """Recibos efetivos e estornos, sem repetir os espelhos em pagamentos."""
    from app.financeiro.recebimentos_historico import consultar_recebimentos_venda

    _, tenant_id = _validar_tenant_e_obter_usuario(user_and_tenant)
    venda = db.query(Venda.id).filter_by(id=venda_id, tenant_id=tenant_id).first()
    if not venda:
        raise HTTPException(status_code=404, detail="Venda não encontrada")
    return consultar_recebimentos_venda(
        db, tenant_id=tenant_id, venda_id=venda_id, page=page, per_page=per_page
    )


@router.delete("/pagamentos/{pagamento_id}")
def excluir_pagamento(
    pagamento_id: int,
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    """Excluir o pagamento junto com caixa, credito, baixas e auditoria."""
    current_user, tenant_id = _validar_tenant_e_obter_usuario(user_and_tenant)
    from app.vendas.exclusao_pagamento import excluir_pagamento_atomico

    try:
        resultado = excluir_pagamento_atomico(
            db=db,
            pagamento_id=pagamento_id,
            tenant_id=tenant_id,
            current_user=current_user,
        )
        db.commit()
        return resultado
    except HTTPException:
        db.rollback()
        raise
    except Exception:
        db.rollback()
        logger.exception("Erro ao excluir pagamento %s", pagamento_id)
        raise HTTPException(
            500, "Nao foi possivel excluir o pagamento. Nenhum valor foi alterado."
        )
