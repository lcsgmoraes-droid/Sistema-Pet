"""Rotas de envio e transicoes de status de pedidos de compra."""

import logging
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from ..auth.dependencies import get_current_user_and_tenant
from ..db import get_session
from ..produtos_models import PedidoCompra
from ..services.email_service import is_email_configured, send_email
from .exportacao import (
    _buscar_fornecedor_pedido,
    _gerar_excel_pedido_bytes,
    _gerar_pdf_pedido_bytes,
    _montar_email_pedido,
    _montar_nome_arquivo_pedido,
    _normalizar_colunas_exportacao_pedido,
)
from .schemas import PedidoCompraEnviarRequest, PedidoCompraEnvioFormatos

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/envio/status")
def status_envio_pedidos(current_user_and_tenant=Depends(get_current_user_and_tenant)):
    """Informa se o servidor está apto a enviar pedidos por e-mail."""
    current_user, tenant_id = current_user_and_tenant
    return {"email_configurado": is_email_configured()}


# ============================================================================
# ENVIAR PEDIDO
# ============================================================================


@router.post("/{pedido_id}/enviar")
def enviar_pedido(
    pedido_id: int,
    request: PedidoCompraEnviarRequest,
    db: Session = Depends(get_session),
    current_user_and_tenant=Depends(get_current_user_and_tenant),
):
    """Marca pedido como enviado"""
    current_user, tenant_id = current_user_and_tenant
    logger.info(f"📤 Enviando pedido {pedido_id}")

    pedido = (
        db.query(PedidoCompra)
        .filter(PedidoCompra.id == pedido_id, PedidoCompra.tenant_id == tenant_id)
        .first()
    )
    if not pedido:
        raise HTTPException(status_code=404, detail="Pedido não encontrado")

    if pedido.status != "rascunho":
        raise HTTPException(
            status_code=400,
            detail=f"Pedido não pode ser enviado no status '{pedido.status}'",
        )

    fornecedor = _buscar_fornecedor_pedido(db, tenant_id, pedido)
    fornecedor_nome = (
        fornecedor.nome if fornecedor else f"Fornecedor {pedido.fornecedor_id}"
    )

    if request.envio_manual:
        pedido.status = "enviado"
        pedido.data_envio = datetime.utcnow()
        pedido.updated_at = datetime.utcnow()
        db.commit()

        logger.info(f"Pedido {pedido.numero_pedido} marcado como enviado manualmente")
        return {
            "message": "Pedido marcado como enviado manualmente",
            "pedido_id": pedido.id,
            "numero_pedido": pedido.numero_pedido,
            "status": pedido.status,
            "tipo_envio": "manual",
        }

    email_destino = (request.email or "").strip()
    if not email_destino:
        raise HTTPException(status_code=400, detail="Informe o e-mail do fornecedor")

    formatos = request.formatos or PedidoCompraEnvioFormatos()
    if not formatos.pdf and not formatos.excel:
        raise HTTPException(
            status_code=400, detail="Selecione pelo menos um formato para envio"
        )

    colunas_exportacao = _normalizar_colunas_exportacao_pedido(
        request.colunas_exportacao
    )

    if not is_email_configured():
        raise HTTPException(
            status_code=503, detail="O envio de e-mail nao esta configurado no servidor"
        )

    anexos = []
    if formatos.pdf:
        nome_pdf = _montar_nome_arquivo_pedido(
            pedido, fornecedor_nome, db, tenant_id, "pdf"
        )
        anexos.append(
            {
                "filename": nome_pdf,
                "content": _gerar_pdf_pedido_bytes(
                    pedido, fornecedor_nome, db, tenant_id, colunas_exportacao
                ),
                "mime_subtype": "pdf",
            }
        )
    if formatos.excel:
        nome_excel = _montar_nome_arquivo_pedido(
            pedido, fornecedor_nome, db, tenant_id, "xlsx"
        )
        anexos.append(
            {
                "filename": nome_excel,
                "content": _gerar_excel_pedido_bytes(
                    pedido, fornecedor_nome, db, tenant_id, colunas_exportacao
                ),
                "mime_subtype": "vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            }
        )

    assunto, html_body, text_body = _montar_email_pedido(
        pedido, fornecedor_nome, colunas_exportacao
    )
    enviado = send_email(
        to=email_destino,
        subject=assunto,
        html_body=html_body,
        text_body=text_body,
        attachments=anexos,
        simulate_if_unconfigured=False,
    )

    if not enviado:
        raise HTTPException(
            status_code=502,
            detail="Nao foi possivel enviar o e-mail do pedido. Revise a configuracao SMTP.",
        )

    pedido.status = "enviado"
    pedido.data_envio = datetime.utcnow()
    pedido.updated_at = datetime.utcnow()

    db.commit()
    logger.info(
        f"Pedido {pedido.numero_pedido} enviado por e-mail para {email_destino}"
    )
    return {
        "message": "Pedido enviado por e-mail com sucesso",
        "pedido_id": pedido.id,
        "numero_pedido": pedido.numero_pedido,
        "status": pedido.status,
        "tipo_envio": "email",
        "email": email_destino,
    }


# ============================================================================
# CONFIRMAR PEDIDO
# ============================================================================


@router.post("/{pedido_id}/confirmar")
def confirmar_pedido(
    pedido_id: int,
    db: Session = Depends(get_session),
    current_user_and_tenant=Depends(get_current_user_and_tenant),
):
    """Confirma pedido (fornecedor confirmou recebimento)"""
    current_user, tenant_id = current_user_and_tenant
    logger.info(f"✅ Confirmando pedido {pedido_id}")

    pedido = (
        db.query(PedidoCompra)
        .filter(PedidoCompra.id == pedido_id, PedidoCompra.tenant_id == tenant_id)
        .first()
    )
    if not pedido:
        raise HTTPException(status_code=404, detail="Pedido não encontrado")

    if pedido.status not in ["rascunho", "enviado"]:
        raise HTTPException(
            status_code=400,
            detail=f"Pedido não pode ser confirmado no status '{pedido.status}'",
        )

    pedido.status = "confirmado"
    pedido.data_confirmacao = datetime.utcnow()
    pedido.updated_at = datetime.utcnow()

    db.commit()

    logger.info(f"✅ Pedido {pedido.numero_pedido} confirmado")

    return {
        "message": "Pedido confirmado com sucesso",
        "pedido_id": pedido.id,
        "numero_pedido": pedido.numero_pedido,
        "status": pedido.status,
    }


# ============================================================================
# CANCELAR PEDIDO
# ============================================================================


@router.post("/{pedido_id}/cancelar")
def cancelar_pedido(
    pedido_id: int,
    motivo: str = Query(..., min_length=10, description="Motivo do cancelamento"),
    db: Session = Depends(get_session),
    current_user_and_tenant=Depends(get_current_user_and_tenant),
):
    """Cancela pedido"""
    current_user, tenant_id = current_user_and_tenant
    logger.info(f"❌ Cancelando pedido {pedido_id}")

    pedido = (
        db.query(PedidoCompra)
        .filter(PedidoCompra.id == pedido_id, PedidoCompra.tenant_id == tenant_id)
        .first()
    )
    if not pedido:
        raise HTTPException(status_code=404, detail="Pedido não encontrado")

    if pedido.status in ["recebido_total", "cancelado"]:
        raise HTTPException(
            status_code=400,
            detail=f"Pedido não pode ser cancelado no status '{pedido.status}'",
        )

    pedido.status = "cancelado"
    pedido.observacoes = f"{pedido.observacoes or ''}\n\nCANCELADO: {motivo}"
    pedido.updated_at = datetime.utcnow()

    # Cancelar todos os itens
    for item in pedido.itens:
        item.status = "cancelado"

    db.commit()

    logger.info(f"❌ Pedido {pedido.numero_pedido} cancelado")

    return {
        "message": "Pedido cancelado com sucesso",
        "pedido_id": pedido.id,
        "numero_pedido": pedido.numero_pedido,
        "status": pedido.status,
    }


@router.post("/{pedido_id}/reverter")
def reverter_status(
    pedido_id: int,
    db: Session = Depends(get_session),
    current_user_and_tenant=Depends(get_current_user_and_tenant),
):
    """Reverte status do pedido (para corrigir cliques acidentais)"""
    current_user, tenant_id = current_user_and_tenant
    pedido = (
        db.query(PedidoCompra)
        .filter(PedidoCompra.id == pedido_id, PedidoCompra.tenant_id == tenant_id)
        .first()
    )

    if not pedido:
        raise HTTPException(status_code=404, detail="Pedido não encontrado")

    # Lógica de reversão
    status_reverso = {
        "enviado": "rascunho",
        "confirmado": "enviado",
        "recebido_parcial": "confirmado",
        "recebido_total": "confirmado",
    }

    if pedido.status not in status_reverso:
        raise HTTPException(
            status_code=400,
            detail=f"Não é possível reverter pedido com status '{pedido.status}'",
        )

    status_anterior = pedido.status
    pedido.status = status_reverso[pedido.status]
    pedido.updated_at = datetime.now()

    db.commit()
    logger.info(
        f"⏪ Pedido {pedido.numero_pedido} revertido: {status_anterior} → {pedido.status}"
    )

    return {
        "message": "Status revertido com sucesso",
        "pedido_id": pedido.id,
        "numero_pedido": pedido.numero_pedido,
        "status_anterior": status_anterior,
        "status_atual": pedido.status,
    }


# ============================================================================
# 💡 SUGESTÃO INTELIGENTE DE PEDIDO
# ============================================================================
