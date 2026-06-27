"""Rotas de email e PDF das pendencias de compras."""

from datetime import datetime
from io import BytesIO
from urllib.parse import quote

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from .auth.dependencies import get_current_user_and_tenant
from .compras_pendencias_constants import (
    PENDENCIA_STATUS_AGUARDANDO,
    PENDENCIA_STATUS_FINAIS,
)
from .compras_pendencias_documentos import (
    _html_email_pendencia,
    _pdf_pendencia_bytes,
)
from .compras_pendencias_schemas import RegistrarEmailPayload
from .compras_pendencias_serializacao import (
    _adicionar_historico,
    _buscar_pendencia,
    _serializar_pendencia,
)
from .compras_pendencias_utils import _normalizar_texto
from .db import get_session
from .services.email_service import is_email_configured, send_email

router = APIRouter()


@router.post("/{pendencia_id}/registrar-email")
def registrar_email_pendencia(
    pendencia_id: int,
    payload: RegistrarEmailPayload,
    db: Session = Depends(get_session),
    current_user_and_tenant=Depends(get_current_user_and_tenant),
):
    current_user, tenant_id = current_user_and_tenant
    pendencia = _buscar_pendencia(db, tenant_id, pendencia_id)
    status_anterior = pendencia.status

    pendencia.email_destinatario = (
        _normalizar_texto(payload.email_destinatario) or pendencia.email_destinatario
    )
    pendencia.email_assunto = (
        _normalizar_texto(payload.email_assunto) or pendencia.email_assunto
    )
    pendencia.email_mensagem = payload.email_mensagem.strip()
    pendencia.email_enviado_em = datetime.utcnow()
    if pendencia.status not in PENDENCIA_STATUS_FINAIS:
        pendencia.status = PENDENCIA_STATUS_AGUARDANDO
    pendencia.updated_at = datetime.utcnow()

    _adicionar_historico(
        pendencia,
        "email_registrado",
        current_user.id,
        payload.observacao or "Contato com fornecedor registrado.",
        status_anterior,
        pendencia.status,
    )
    db.commit()
    pendencia = _buscar_pendencia(db, tenant_id, pendencia_id)
    return _serializar_pendencia(pendencia, incluir_itens=True, incluir_historico=True)


@router.post("/{pendencia_id}/enviar-email")
def enviar_email_pendencia(
    pendencia_id: int,
    payload: RegistrarEmailPayload,
    db: Session = Depends(get_session),
    current_user_and_tenant=Depends(get_current_user_and_tenant),
):
    current_user, tenant_id = current_user_and_tenant
    pendencia = _buscar_pendencia(db, tenant_id, pendencia_id)

    email_destino = (
        _normalizar_texto(payload.email_destinatario) or pendencia.email_destinatario
    )
    assunto = _normalizar_texto(payload.email_assunto) or pendencia.email_assunto
    mensagem = payload.email_mensagem.strip()

    if not email_destino:
        raise HTTPException(status_code=400, detail="Informe o e-mail do fornecedor.")
    if not assunto:
        raise HTTPException(status_code=400, detail="Informe o assunto do e-mail.")
    if not is_email_configured():
        raise HTTPException(
            status_code=503,
            detail="O envio de e-mail nao esta configurado no servidor.",
        )

    pdf_content = _pdf_pendencia_bytes(pendencia)
    filename = f"pendencia_fornecedor_{pendencia.codigo or pendencia.id}.pdf"
    enviado = send_email(
        to=email_destino,
        subject=assunto,
        html_body=_html_email_pendencia(pendencia, mensagem),
        text_body=mensagem,
        attachments=[
            {
                "filename": filename,
                "content": pdf_content,
                "mime_subtype": "pdf",
            }
        ],
        simulate_if_unconfigured=False,
    )

    if not enviado:
        raise HTTPException(
            status_code=502,
            detail="Nao foi possivel enviar o e-mail. Revise a configuracao SMTP.",
        )

    status_anterior = pendencia.status
    pendencia.email_destinatario = email_destino
    pendencia.email_assunto = assunto
    pendencia.email_mensagem = mensagem
    pendencia.email_enviado_em = datetime.utcnow()
    pendencia.pdf_gerado_em = datetime.utcnow()
    if pendencia.status not in PENDENCIA_STATUS_FINAIS:
        pendencia.status = PENDENCIA_STATUS_AGUARDANDO
    pendencia.updated_at = datetime.utcnow()
    _adicionar_historico(
        pendencia,
        "email_enviado",
        current_user.id,
        payload.observacao or "E-mail enviado ao fornecedor com o PDF de divergencias.",
        status_anterior,
        pendencia.status,
    )
    db.commit()
    pendencia = _buscar_pendencia(db, tenant_id, pendencia_id)
    return _serializar_pendencia(pendencia, incluir_itens=True, incluir_historico=True)


@router.get("/{pendencia_id}/email-texto")
def obter_email_pendencia(
    pendencia_id: int,
    db: Session = Depends(get_session),
    current_user_and_tenant=Depends(get_current_user_and_tenant),
):
    _, tenant_id = current_user_and_tenant
    pendencia = _buscar_pendencia(db, tenant_id, pendencia_id)
    return {
        "email_destinatario": pendencia.email_destinatario,
        "email_assunto": pendencia.email_assunto,
        "email_mensagem": pendencia.email_mensagem,
    }


@router.get("/{pendencia_id}/pdf")
def baixar_pdf_pendencia(
    pendencia_id: int,
    db: Session = Depends(get_session),
    current_user_and_tenant=Depends(get_current_user_and_tenant),
):
    _, tenant_id = current_user_and_tenant
    pendencia = _buscar_pendencia(db, tenant_id, pendencia_id)
    content = _pdf_pendencia_bytes(pendencia)
    pendencia.pdf_gerado_em = datetime.utcnow()
    db.commit()

    filename = f"pendencia_fornecedor_{pendencia.codigo or pendencia.id}.pdf"
    return StreamingResponse(
        BytesIO(content),
        media_type="application/pdf",
        headers={
            "Content-Disposition": f"attachment; filename*=UTF-8''{quote(filename)}"
        },
    )
