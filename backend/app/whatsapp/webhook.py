"""
WhatsApp Webhook Receiver (360dialog)

Recebe mensagens do 360dialog via webhook.
Valida assinatura, identifica tenant, enfileira processamento.

Endpoints:
- POST /webhook/whatsapp/{tenant_id} - Recebe mensagens
- GET /webhook/whatsapp/{tenant_id} - Validação inicial (Meta)
"""

from fastapi import APIRouter, HTTPException, Request, BackgroundTasks, Depends, Query
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
import hashlib
import hmac
import logging
from typing import Dict, Any
from datetime import datetime, timedelta

from app.db import get_session as get_db
from app.whatsapp.models import TenantWhatsAppConfig, WhatsAppSession, WhatsAppMessage
from app.whatsapp.tenant_context import whatsapp_tenant_context
from app.whatsapp.customer_lookup import SITUACAO_AMBIGUO, resolver_tutor_por_telefone

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/webhook/whatsapp", tags=["WhatsApp Webhook"])

WHATSAPP_WEBHOOK_TOKEN_HEADER = "X-CorePet-Webhook-Token"


# ============================================================================
# WEBHOOK VALIDATION (360dialog)
# ============================================================================


def validate_webhook_signature(payload: bytes, signature: str, secret: str) -> bool:
    """
    Valida HMAC-SHA256 de uma conexão direta compatível.

    Para 360dialog, o caminho preferencial é o token em cabeçalho personalizado.
    """
    normalized_secret = str(secret or "").strip()
    normalized_signature = str(signature or "").strip()
    if not normalized_secret or not normalized_signature:
        return False

    if normalized_signature.lower().startswith("sha256="):
        normalized_signature = normalized_signature.split("=", 1)[1].strip()
    if len(normalized_signature) != 64:
        return False

    try:
        bytes.fromhex(normalized_signature)
        expected_signature = hmac.new(
            normalized_secret.encode("utf-8"), payload, hashlib.sha256
        ).hexdigest()
        return hmac.compare_digest(normalized_signature.lower(), expected_signature)
    except (TypeError, ValueError):
        return False


def validate_webhook_authentication(
    payload: bytes,
    *,
    signature: str | None,
    static_token: str | None,
    secret: str,
) -> bool:
    """Accept a provider HMAC or the custom header supported by 360dialog."""

    normalized_secret = str(secret or "").strip()
    normalized_token = str(static_token or "").strip()
    if not normalized_secret:
        return False
    if normalized_token and hmac.compare_digest(normalized_token, normalized_secret):
        return True
    return validate_webhook_signature(payload, signature or "", normalized_secret)


# ============================================================================
# GET WEBHOOK (Verificação Meta)
# ============================================================================


@router.get("/{tenant_id}")
async def webhook_verification(
    tenant_id: str,
    hub_mode: str = Query(None, alias="hub.mode"),
    hub_challenge: str = Query(None, alias="hub.challenge"),
    hub_verify_token: str = Query(None, alias="hub.verify_token"),
    db: Session = Depends(get_db),
):
    """
    GET webhook para verificação inicial da Meta.

    Meta/360dialog envia GET com:
    - hub.mode=subscribe
    - hub.challenge=random_string
    - hub.verify_token=seu_token

    Você deve retornar hub.challenge se verify_token estiver correto.
    """
    logger.info("Verificacao webhook recebida")

    # Buscar config do tenant
    with whatsapp_tenant_context(tenant_id):
        config = (
            db.query(TenantWhatsAppConfig)
            .filter(TenantWhatsAppConfig.tenant_id == tenant_id)
            .first()
        )

    if not config or not config.webhook_secret:
        logger.warning("Tenant sem configuracao WhatsApp")
        raise HTTPException(status_code=404, detail="Configuração não encontrada")

    # Validar verify token
    if hub_mode == "subscribe" and hub_verify_token == config.webhook_secret:
        logger.info("Webhook verificado com sucesso")
        return int(hub_challenge)  # Meta espera número

    logger.warning("❌ Falha na verificação: token inválido")
    raise HTTPException(status_code=403, detail="Verificação falhou")


# ============================================================================
# POST WEBHOOK (Recebe Mensagens)
# ============================================================================


@router.post("/{tenant_id}")
async def receive_webhook(
    tenant_id: str,
    request: Request,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    """
    POST webhook para receber mensagens do 360dialog.

    Fluxo:
    1. Valida assinatura (segurança)
    2. Parseia payload
    3. Identifica cliente
    4. Enfileira processamento em background
    5. Retorna 200 OK imediatamente
    """
    # 1. Buscar config do tenant
    with whatsapp_tenant_context(tenant_id):
        config = (
            db.query(TenantWhatsAppConfig)
            .filter(TenantWhatsAppConfig.tenant_id == tenant_id)
            .first()
        )

    if not config:
        logger.warning("Tenant sem configuracao WhatsApp")
        raise HTTPException(status_code=404, detail="Tenant não configurado")

    # 2. Validar assinatura de forma fail-closed antes de interpretar o payload.
    body = await request.body()
    signature = request.headers.get("X-Hub-Signature-256", "")
    static_token = request.headers.get(WHATSAPP_WEBHOOK_TOKEN_HEADER, "")

    if not config.webhook_secret:
        logger.error("Webhook WhatsApp sem segredo configurado para o tenant")
        raise HTTPException(
            status_code=503,
            detail="Webhook não configurado com segurança",
        )

    if not validate_webhook_authentication(
        body,
        signature=signature,
        static_token=static_token,
        secret=config.webhook_secret,
    ):
        logger.warning("Autenticacao ausente ou invalida no webhook WhatsApp")
        raise HTTPException(status_code=403, detail="Autenticação inválida")

    # 3. Parsear payload JSON
    try:
        payload = await request.json()
    except Exception as e:
        logger.error(f"Erro ao parsear payload: {e}")
        raise HTTPException(status_code=400, detail="Payload inválido")

    # 4. Processar mensagens
    try:
        processed_count = await process_webhook_payload(
            tenant_id=tenant_id,
            payload=payload,
            background_tasks=background_tasks,
            db=db,
        )

        logger.info(f"✅ Webhook processado: {processed_count} mensagens")

        # Retornar 200 OK rapidamente (WhatsApp espera resposta em <500ms)
        return {"status": "received", "messages_processed": processed_count}

    except Exception as e:
        logger.error(f"Erro ao processar webhook: {e}")
        # Retornar 200 mesmo com erro interno (para não reenviar)
        return {"status": "error", "message": str(e)}


# ============================================================================
# PROCESSAMENTO DO PAYLOAD
# ============================================================================


async def process_webhook_payload(
    tenant_id: str,
    payload: Dict[str, Any],
    background_tasks: BackgroundTasks,
    db: Session,
) -> int:
    """
    Processa payload do 360dialog.

    Estrutura 360dialog:
    {
        "object": "whatsapp_business_account",
        "entry": [{
            "id": "account_id",
            "changes": [{
                "value": {
                    "messaging_product": "whatsapp",
                    "metadata": {...},
                    "messages": [
                        {
                            "from": "5511999999999",
                            "id": "wamid.xxx",
                            "timestamp": "1234567890",
                            "type": "text",
                            "text": {"body": "Olá"}
                        }
                    ]
                },
                "field": "messages"
            }]
        }]
    }
    """
    processed = 0

    # Iterar entries
    for entry in payload.get("entry", []):
        for change in entry.get("changes", []):
            value = change.get("value", {})
            messages = value.get("messages", [])

            # Processar cada mensagem
            for msg in messages:
                try:
                    # Extrair dados
                    phone = msg.get("from")
                    whatsapp_msg_id = msg.get("id")
                    msg_type = msg.get("type")

                    # Suportar apenas texto por enquanto
                    if msg_type != "text":
                        logger.info(f"Tipo {msg_type} não suportado (ainda)")
                        continue

                    text_content = msg.get("text", {}).get("body", "")

                    if not phone or not text_content:
                        logger.warning("Mensagem sem phone ou conteúdo")
                        continue

                    # Enfileirar processamento
                    background_tasks.add_task(
                        process_incoming_message,
                        tenant_id=tenant_id,
                        phone=phone,
                        message_content=text_content,
                        whatsapp_msg_id=whatsapp_msg_id,
                        db=db,
                    )

                    processed += 1

                except Exception as e:
                    logger.error(f"Erro ao processar mensagem individual: {e}")
                    continue

    return processed


# ============================================================================
# PROCESSAR MENSAGEM INDIVIDUAL
# ============================================================================


def _normalize_provider_message_id(value: Any) -> str | None:
    normalized = str(value or "").strip()
    return normalized or None


def _find_message_by_provider_id(
    db: Session,
    *,
    tenant_id: str,
    provider_message_id: str | None,
) -> WhatsAppMessage | None:
    if not provider_message_id:
        return None
    with whatsapp_tenant_context(tenant_id):
        return (
            db.query(WhatsAppMessage)
            .filter(
                WhatsAppMessage.tenant_id == tenant_id,
                WhatsAppMessage.whatsapp_message_id == provider_message_id,
            )
            .first()
        )


def _duplicate_message_result(
    provider_message_id: str, existing: WhatsAppMessage
) -> Dict[str, Any]:
    return {
        "status": "duplicate",
        "whatsapp_message_id": provider_message_id,
        "message_id": existing.id,
    }


async def process_incoming_message(
    tenant_id: str,
    phone: str,
    message_content: str,
    whatsapp_msg_id: str | None,
    db: Session,
) -> Dict[str, Any]:
    with whatsapp_tenant_context(tenant_id):
        return await _process_incoming_message_with_context(
            tenant_id=tenant_id,
            phone=phone,
            message_content=message_content,
            whatsapp_msg_id=whatsapp_msg_id,
            db=db,
        )


async def _process_incoming_message_with_context(
    tenant_id: str,
    phone: str,
    message_content: str,
    whatsapp_msg_id: str | None,
    db: Session,
) -> Dict[str, Any]:
    """
    Processa mensagem individual (roda em background).

    Fluxo:
    1. Normalizar telefone
    2. Buscar/criar sessão
    3. Salvar mensagem recebida
    4. [PRÓXIMO SPRINT] Processar com IA
    5. [PRÓXIMO SPRINT] Enviar resposta
    """
    try:
        logger.info(f"📨 Processando mensagem: tenant={tenant_id}, phone={phone}")

        provider_message_id = _normalize_provider_message_id(whatsapp_msg_id)
        existing = _find_message_by_provider_id(
            db,
            tenant_id=tenant_id,
            provider_message_id=provider_message_id,
        )
        if existing and provider_message_id:
            logger.info(
                "Mensagem WhatsApp duplicada ignorada: tenant=%s provider_id=%s",
                tenant_id,
                provider_message_id,
            )
            return _duplicate_message_result(provider_message_id, existing)

        # 1. Normalizar telefone (remover caracteres especiais)
        phone_normalized = normalize_phone(phone)

        # 2. Buscar ou criar sessão
        session = get_or_create_session(
            db=db, tenant_id=tenant_id, phone=phone_normalized
        )

        # 3. Salvar mensagem recebida
        message = WhatsAppMessage(
            session_id=session.id,
            tenant_id=tenant_id,
            tipo="recebida",
            conteudo=message_content,
            whatsapp_message_id=provider_message_id,
            created_at=datetime.utcnow(),
        )

        db.add(message)

        # Atualizar sessão
        session.message_count += 1
        session.last_message_at = datetime.utcnow()

        try:
            db.commit()
        except IntegrityError:
            db.rollback()
            existing = _find_message_by_provider_id(
                db,
                tenant_id=tenant_id,
                provider_message_id=provider_message_id,
            )
            if existing and provider_message_id:
                logger.info(
                    "Concorrencia de mensagem WhatsApp duplicada bloqueada: "
                    "tenant=%s provider_id=%s",
                    tenant_id,
                    provider_message_id,
                )
                return _duplicate_message_result(provider_message_id, existing)
            raise

        logger.info(f"✅ Mensagem salva: session={session.id}")

        await _avisar_nova_mensagem(tenant_id, session, message, message_content)

        # CRM etapa 0.1: com atendimento humano ativo ou aguardando, a IA nao
        # responde. A mensagem ja foi salva para o atendente ver.
        if atendimento_humano_ativo(session):
            logger.info(
                "IA pausada (atendimento humano): session=%s status=%s",
                session.id,
                session.status,
            )
            aviso_enviado = await _avisar_espera_atendente(db, tenant_id, session)
            return {
                "status": "processed",
                "whatsapp_message_id": provider_message_id,
                "message_id": message.id,
                "processor_result": {
                    "action": "skipped_human_handling",
                    "session_status": session.status,
                    "waiting_notice_sent": aviso_enviado,
                },
            }

        # 4. Processar com IA
        processor_result = None
        try:
            from app.whatsapp.processor import MessageProcessor

            with whatsapp_tenant_context(tenant_id):
                processor = MessageProcessor(db=db, tenant_id=tenant_id)
                processor_result = await processor.process_message(
                    session_id=session.id,
                    message_id=message.id,
                    message_content=message_content,
                )

            logger.info(
                "✅ Processamento concluído: %s",
                processor_result.get("action"),
            )

        except Exception as proc_error:
            logger.error(f"Erro no processor (não-bloqueante): {proc_error}")
            # Não falha se processor der erro

        return {
            "status": "processed",
            "whatsapp_message_id": provider_message_id,
            "message_id": message.id,
            "processor_result": processor_result,
        }

    except Exception as e:
        logger.error(f"❌ Erro ao processar mensagem: {e}")
        db.rollback()
        raise


# ============================================================================
# HELPERS
# ============================================================================


# Estados de sessao em que a IA nao deve responder (atendente humano no comando).
STATUS_ATENDIMENTO_HUMANO = ("human", "waiting_human")


def atendimento_humano_ativo(session: Any) -> bool:
    """True quando a conversa esta com humano ou aguardando um atendente."""
    return getattr(session, "status", None) in STATUS_ATENDIMENTO_HUMANO


AVISO_ESPERA_ATENDENTE = (
    "Recebemos sua mensagem. Um atendente da loja vai conversar com você em breve."
)
# Evita repetir o aviso a cada mensagem enquanto o tutor espera.
JANELA_AVISO_ESPERA_MINUTOS = 30


async def _avisar_nova_mensagem(
    tenant_id: str, session: Any, message: Any, conteudo: str
) -> None:
    """Avisa em tempo real os atendentes da loja sobre a mensagem do tutor."""
    try:
        from app.whatsapp.websocket import emit_new_message

        await emit_new_message(
            str(session.id),
            {
                "id": str(message.id),
                "session_id": str(session.id),
                "tipo": "recebida",
                "sender_type": "customer",
                "content": conteudo,
                "conteudo": conteudo,
                "timestamp": datetime.utcnow().isoformat(),
                "read": False,
            },
            str(tenant_id),
        )
    except Exception as erro:
        logger.warning("Falha ao avisar nova mensagem em tempo real: %s", erro)


async def _avisar_espera_atendente(db: Session, tenant_id: str, session: Any) -> bool:
    """Avisa o tutor que um atendente vai falar com ele, no maximo 1 vez por janela.

    So vale para conversa aguardando atendente. Quando o atendente ja assumiu
    (status human) ele mesmo conversa, entao nao ha aviso. Falha no envio nunca
    derruba o processamento da mensagem recebida.
    """
    if getattr(session, "status", None) != "waiting_human":
        return False
    try:
        limite = datetime.utcnow() - timedelta(minutes=JANELA_AVISO_ESPERA_MINUTOS)
        ja_avisado = (
            db.query(WhatsAppMessage)
            .filter(
                WhatsAppMessage.session_id == session.id,
                WhatsAppMessage.tipo == "enviada",
                WhatsAppMessage.conteudo == AVISO_ESPERA_ATENDENTE,
                WhatsAppMessage.created_at >= limite,
            )
            .first()
        )
        if ja_avisado:
            return False

        from app.whatsapp.sender import send_whatsapp_message

        enviada = await send_whatsapp_message(
            db=db,
            tenant_id=tenant_id,
            session_id=session.id,
            message=AVISO_ESPERA_ATENDENTE,
        )
        return enviada is not None
    except Exception as erro:
        logger.warning("Falha ao avisar espera de atendente: %s", erro)
        return False


def normalize_phone(phone: str) -> str:
    """
    Normaliza identificador de telefone/chat do WhatsApp.

    - Para formato @lid (novo identificador interno do WhatsApp):
      mantém o sufixo @lid, ex: "266915104710838@lid"
    - Para demais formatos (@c.us, etc.): retorna apenas dígitos.
    """
    import re

    if "@lid" in phone:
        digits = re.sub(r"[^\d]", "", phone.split("@")[0])
        return f"{digits}@lid"
    return re.sub(r"[^\d]", "", phone)


def get_or_create_session(db: Session, tenant_id: str, phone: str) -> WhatsAppSession:
    with whatsapp_tenant_context(tenant_id):
        return _get_or_create_session_with_context(db, tenant_id, phone)


def _get_or_create_session_with_context(
    db: Session, tenant_id: str, phone: str
) -> WhatsAppSession:
    """
    Busca sessão ativa ou cria nova.

    Sessão ativa = status 'bot' ou 'human' (não 'closed')
    """
    # Buscar sessão ativa
    session = (
        db.query(WhatsAppSession)
        .filter(
            WhatsAppSession.tenant_id == tenant_id,
            WhatsAppSession.phone_number == phone,
            WhatsAppSession.status.in_(["bot", "human", "waiting_human"]),
        )
        .order_by(WhatsAppSession.last_message_at.desc())
        .first()
    )

    if session:
        return session

    # Identificar o tutor pelo telefone com a regra unica do atendimento
    # (exatamente um cadastro compativel; ambiguo ou ausente = sem vinculo).
    cliente_id = None
    try:
        resolucao = resolver_tutor_por_telefone(db, tenant_id, phone)
        cliente_id = resolucao.cliente_id
        if resolucao.situacao == SITUACAO_AMBIGUO:
            logger.warning(
                "Telefone ligado a mais de um cadastro; sessao sem vinculo: "
                "tenant=%s candidatos=%s",
                tenant_id,
                list(resolucao.candidatos),
            )
    except Exception as cliente_lookup_error:
        logger.warning(
            f"Falha ao identificar cliente por telefone: {cliente_lookup_error}"
        )
        cliente_id = None

    # Criar nova sessão
    session = WhatsAppSession(
        tenant_id=tenant_id,
        cliente_id=cliente_id,
        phone_number=phone,
        status="bot",
        started_at=datetime.utcnow(),
        last_message_at=datetime.utcnow(),
    )

    db.add(session)
    db.flush()

    logger.info(f"🆕 Nova sessão criada: {session.id}")

    return session
