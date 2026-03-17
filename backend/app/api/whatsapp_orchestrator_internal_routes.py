"""
WhatsApp Orchestrator Internal Routes

Endpoints internos para integrar WAHA/n8n com o backend sem expor webhook publico.
Seguranca por token interno dedicado.
"""

import os
from typing import Literal, Optional

from fastapi import APIRouter, Depends, Header, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.db import get_session
from app.whatsapp.webhook import normalize_phone, process_incoming_message
from app.whatsapp.handoff_manager import HandoffManager
from app.whatsapp.models import WhatsAppSession


router = APIRouter(prefix="/internal/whatsapp-orchestrator", tags=["whatsapp-orchestrator-internal"])


class InternalIngestRequest(BaseModel):
    phone: str = Field(..., description="Numero do cliente")
    message_type: Literal["text", "audio", "image"] = "text"
    text: Optional[str] = None
    caption: Optional[str] = None
    transcription_text: Optional[str] = None
    media_url: Optional[str] = None
    external_message_id: Optional[str] = None


class InternalIngestResponse(BaseModel):
    success: bool
    status: str
    tenant_id: str
    phone: str
    message_type: str
    accepted_content_preview: str


def _build_message_content(payload: InternalIngestRequest) -> str:
    """Normaliza entrada multimidia em texto para o fluxo atual da Fase 1."""
    text = (payload.text or "").strip()
    caption = (payload.caption or "").strip()
    transcription = (payload.transcription_text or "").strip()

    if payload.message_type == "text":
        return text

    if payload.message_type == "audio":
        if transcription:
            return transcription
        if text:
            return text
        return "Cliente enviou um audio sem transcricao. Solicite texto curto para confirmar o pedido."

    if payload.message_type == "image":
        if caption:
            return f"[Imagem recebida] {caption}"
        if text:
            return f"[Imagem recebida] {text}"
        return "Cliente enviou uma imagem sem legenda. Pergunte o que ele precisa sobre a imagem."

    return text


def _is_explicit_human_request(message_content: str) -> bool:
    """Detecta pedido explícito de atendimento humano no texto."""
    text = (message_content or "").lower()
    triggers = [
        "atendente",
        "atendimento humano",
        "falar com humano",
        "falar com atendente",
        "falar com pessoa",
        "suporte humano",
        "quero humano",
        "quero atendente",
    ]
    return any(trigger in text for trigger in triggers)


def _validate_internal_token(x_internal_token: Optional[str]) -> None:
    expected_token = (os.getenv("WHATSAPP_ORCHESTRATOR_INTERNAL_TOKEN") or "").strip()

    if not expected_token:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Canal interno indisponivel: token interno nao configurado",
        )

    if not x_internal_token or x_internal_token.strip() != expected_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token interno invalido",
        )


@router.post("/{tenant_id}/ingest", response_model=InternalIngestResponse)
async def ingest_message(
    tenant_id: str,
    payload: InternalIngestRequest,
    x_internal_token: Optional[str] = Header(default=None, alias="X-Internal-Token"),
    db: Session = Depends(get_session),
):
    """
    Recebe mensagens do orquestrador (WAHA/n8n) e injeta no pipeline atual.

    Fluxo atual:
    1. Valida token interno.
    2. Normaliza audio/imagem para texto.
    3. Reaproveita processamento padrao ja existente do WhatsApp Agent.
    """
    _validate_internal_token(x_internal_token)

    normalized_phone = normalize_phone(payload.phone)
    if not normalized_phone:
        raise HTTPException(status_code=400, detail="Telefone invalido")

    message_content = _build_message_content(payload)
    if not message_content:
        raise HTTPException(status_code=400, detail="Conteudo vazio")

    whatsapp_msg_id = payload.external_message_id or f"internal_{tenant_id}_{normalized_phone}"

    await process_incoming_message(
        tenant_id=tenant_id,
        phone=normalized_phone,
        message_content=message_content,
        whatsapp_msg_id=whatsapp_msg_id,
        db=db,
    )

    # Fallback operacional: cria handoff direto quando o cliente pedir humano,
    # mesmo se o processor de IA estiver indisponível.
    if _is_explicit_human_request(message_content):
        session = (
            db.query(WhatsAppSession)
            .filter(
                WhatsAppSession.tenant_id == tenant_id,
                WhatsAppSession.phone_number == normalized_phone,
            )
            .order_by(WhatsAppSession.last_message_at.desc())
            .first()
        )

        if session:
            handoff_manager = HandoffManager(db, tenant_id)
            active_handoff = handoff_manager.get_active_handoff(session.id)
            if not active_handoff:
                handoff_manager.create_handoff(
                    session_id=session.id,
                    phone_number=normalized_phone,
                    reason="manual_request",
                    priority="high",
                    reason_details="Pedido explícito via canal interno: atendimento humano",
                )

    return InternalIngestResponse(
        success=True,
        status="accepted",
        tenant_id=tenant_id,
        phone=normalized_phone,
        message_type=payload.message_type,
        accepted_content_preview=message_content[:180],
    )
