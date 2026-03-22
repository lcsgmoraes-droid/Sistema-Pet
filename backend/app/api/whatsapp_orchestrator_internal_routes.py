"""
WhatsApp Orchestrator Internal Routes

Endpoints internos para integrar WAHA/n8n com o backend sem expor webhook publico.
Seguranca por token interno dedicado.
"""

import os
import io
import asyncio
from typing import Literal, Optional

import httpx
from fastapi import APIRouter, Depends, Header, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from openai import OpenAI

from app.db import get_session
from app.whatsapp.webhook import normalize_phone, process_incoming_message
from app.whatsapp.handoff_manager import HandoffManager
from app.whatsapp.models import WhatsAppSession, TenantWhatsAppConfig


router = APIRouter(prefix="/internal/whatsapp-orchestrator", tags=["whatsapp-orchestrator-internal"])


class InternalIngestRequest(BaseModel):
    phone: str = Field(..., description="Numero do cliente")
    message_type: Literal["text", "audio", "image"] = "text"
    text: Optional[str] = None
    caption: Optional[str] = None
    transcription_text: Optional[str] = None
    image_analysis_text: Optional[str] = None
    media_url: Optional[str] = None
    external_message_id: Optional[str] = None


class InternalIngestResponse(BaseModel):
    success: bool
    status: str
    tenant_id: str
    phone: str
    message_type: str
    accepted_content_preview: str


def _resolve_openai_api_key(db: Session, tenant_id: str) -> str:
    config = (
        db.query(TenantWhatsAppConfig)
        .filter(TenantWhatsAppConfig.tenant_id == tenant_id)
        .first()
    )
    if config and config.openai_api_key:
        return config.openai_api_key.strip()
    return (os.getenv("OPENAI_API_KEY") or "").strip()


async def _transcribe_audio_from_media_url(media_url: str, api_key: str) -> str:
    if not media_url or not api_key:
        return ""

    try:
        async with httpx.AsyncClient(timeout=20.0) as client:
            response = await client.get(media_url)
            response.raise_for_status()
            audio_bytes = response.content
    except Exception:
        return ""

    if not audio_bytes:
        return ""

    def _run_transcription() -> str:
        client = OpenAI(api_key=api_key)
        stream = io.BytesIO(audio_bytes)
        stream.name = "audio.ogg"
        result = client.audio.transcriptions.create(
            model="gpt-4o-mini-transcribe",
            file=stream,
            language="pt"
        )
        text = getattr(result, "text", "") or ""
        return text.strip()

    try:
        return await asyncio.to_thread(_run_transcription)
    except Exception:
        return ""


async def _analyze_image_from_media_url(media_url: str, caption: str, api_key: str) -> str:
    if not media_url or not api_key:
        return ""

    prompt = (
        "Analise a imagem enviada no WhatsApp e retorne um resumo curto em portugues, "
        "focado em identificar produto pet, marca, sabor, peso/tamanho, quantidade e texto visivel. "
        "Se nao houver dados claros, diga isso de forma objetiva."
    )
    if caption:
        prompt += f" Legenda do cliente: {caption}"

    def _run_image_analysis() -> str:
        client = OpenAI(api_key=api_key)
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {"type": "image_url", "image_url": {"url": media_url}},
                    ],
                }
            ],
            temperature=0.2,
            max_tokens=250,
        )
        content = response.choices[0].message.content or ""
        return str(content).strip()

    try:
        return await asyncio.to_thread(_run_image_analysis)
    except Exception:
        return ""


def _build_message_content(payload: InternalIngestRequest) -> str:
    """Normaliza entrada multimidia em texto para o fluxo atual da Fase 1."""
    text = (payload.text or "").strip()
    caption = (payload.caption or "").strip()
    transcription = (payload.transcription_text or "").strip()
    image_analysis = (payload.image_analysis_text or "").strip()

    if payload.message_type == "text":
        return text

    if payload.message_type == "audio":
        if transcription:
            return f"[Audio do cliente] {transcription}"
        if text:
            return text
        return "Cliente enviou um audio sem transcricao. Solicite texto curto para confirmar o pedido."

    if payload.message_type == "image":
        if image_analysis and caption:
            return f"[Imagem recebida] {caption}. Analise da imagem: {image_analysis}"
        if image_analysis:
            return f"[Imagem recebida] {image_analysis}"
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

    # Tenta enriquecer audio/imagem com IA quando o orquestrador nao enviou transcricao/analise.
    api_key = _resolve_openai_api_key(db, tenant_id)
    if payload.message_type == "audio" and not (payload.transcription_text or "").strip():
        payload.transcription_text = await _transcribe_audio_from_media_url(
            media_url=(payload.media_url or "").strip(),
            api_key=api_key,
        )
    if payload.message_type == "image" and not (payload.image_analysis_text or "").strip():
        payload.image_analysis_text = await _analyze_image_from_media_url(
            media_url=(payload.media_url or "").strip(),
            caption=(payload.caption or "").strip(),
            api_key=api_key,
        )

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
