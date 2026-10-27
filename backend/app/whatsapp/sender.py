"""
WhatsApp Message Sender (360dialog)

Envia mensagens via API do 360dialog.
Trata erros, retries, registra no banco.
"""

import os

import httpx
import logging
from typing import Optional, Dict, Any
from datetime import datetime
from sqlalchemy.orm import Session

from app.utils.correlation import current_correlation_id
from app.whatsapp import ledger_service
from app.whatsapp.meta_cloud import MetaCloudClient
from app.whatsapp.models import TenantWhatsAppConfig, WhatsAppSession, WhatsAppMessage
from app.whatsapp.tenant_context import whatsapp_tenant_context

logger = logging.getLogger(__name__)


def _resolve_provider(config: Optional[TenantWhatsAppConfig], tenant_id: str) -> str:
    if not config:
        fallback_provider = os.getenv("WHATSAPP_DEFAULT_PROVIDER", "waha").lower()
        logger.warning(
            "Tenant %s sem configuração WhatsApp; usando fallback provider=%s",
            tenant_id,
            fallback_provider,
        )
        return fallback_provider

    return (config.provider or "360dialog").lower()


def _build_whatsapp_client(db: Session, tenant_id: str) -> Optional[Any]:
    config = (
        db.query(TenantWhatsAppConfig)
        .filter(TenantWhatsAppConfig.tenant_id == tenant_id)
        .first()
    )

    provider = _resolve_provider(config, tenant_id)
    if provider == "meta_cloud":
        token = config.meta_access_token if config else ""
        numero_id = (config.meta_phone_number_id if config else "") or ""
        if not token or not numero_id:
            logger.error(
                "Tenant %s com API oficial da Meta sem token ou ID do numero", tenant_id
            )
            return None
        return MetaCloudClient(
            access_token=token,
            phone_number_id=numero_id,
            waba_id=config.meta_waba_id,
        )
    if provider == "waha":
        waha_url = os.getenv("WAHA_BASE_URL", "http://waha:3000")
        waha_key = os.getenv("WAHA_API_KEY", "")
        return WahaClient(api_key=waha_key, base_url=waha_url)

    api_key_360 = (config.api_key if config else None) or os.getenv(
        "WHATSAPP_360DIALOG_API_KEY", ""
    )
    if not api_key_360:
        logger.error(f"Tenant {tenant_id} sem API key configurada")
        return None

    return Dialog360Client(api_key=api_key_360)


async def _send_api_message(
    client_obj: Any,
    session: WhatsAppSession,
    message: str,
    message_type: str,
    image_url: Optional[str],
) -> Dict[str, Any]:
    if message_type == "image" and image_url:
        return await client_obj.send_image_message(
            to=session.phone_number,
            image_url=image_url,
            caption=message,
        )

    return await client_obj.send_text_message(
        to=session.phone_number,
        message=message,
    )


# ============================================================================
# CLIENT 360DIALOG
# ============================================================================


class Dialog360Client:
    """
    Cliente HTTP para 360dialog API.

    Docs: https://docs.360dialog.com/whatsapp-api/whatsapp-api
    """

    BASE_URL = "https://waba.360dialog.io/v1"

    def __init__(self, api_key: str):
        self.api_key = api_key
        self.headers = {"D360-API-KEY": api_key, "Content-Type": "application/json"}

    def _headers_with_correlation(self, reference: str | None = None) -> Dict[str, str]:
        correlation_id = current_correlation_id(
            "integration.whatsapp.360dialog", reference=reference
        )
        headers = dict(self.headers)
        headers["X-Correlation-ID"] = correlation_id
        headers["X-Request-ID"] = correlation_id
        return headers

    async def send_text_message(self, to: str, message: str) -> Dict[str, Any]:
        """
        Envia mensagem de texto.

        Args:
            to: Número com código do país (ex: 5511999999999)
            message: Texto da mensagem

        Returns:
            Response da API com message_id
        """
        payload = {
            "recipient_type": "individual",
            "to": to,
            "type": "text",
            "text": {"body": message},
        }

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{self.BASE_URL}/messages",
                headers=self._headers_with_correlation(to),
                json=payload,
            )

            response.raise_for_status()
            return response.json()

    async def send_image_message(
        self, to: str, image_url: str, caption: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Envia imagem com legenda opcional.

        Args:
            to: Número com código do país
            image_url: URL pública da imagem
            caption: Legenda (opcional, máx 1024 caracteres)
        """
        payload = {
            "recipient_type": "individual",
            "to": to,
            "type": "image",
            "image": {"link": image_url},
        }

        if caption:
            payload["image"]["caption"] = caption[:1024]

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{self.BASE_URL}/messages",
                headers=self._headers_with_correlation(to),
                json=payload,
            )

            response.raise_for_status()
            return response.json()

    async def send_template_message(
        self,
        to: str,
        template_name: str,
        language_code: str = "pt_BR",
        parameters: Optional[list] = None,
    ) -> Dict[str, Any]:
        """
        Envia template aprovado (para iniciar conversa fora da janela 24h).

        Args:
            to: Número com código do país
            template_name: Nome do template aprovado pela Meta
            language_code: Código do idioma (pt_BR, en_US, etc)
            parameters: Lista de parâmetros do template
        """
        payload = {
            "recipient_type": "individual",
            "to": to,
            "type": "template",
            "template": {"name": template_name, "language": {"code": language_code}},
        }

        if parameters:
            payload["template"]["components"] = [
                {
                    "type": "body",
                    "parameters": [
                        {"type": "text", "text": str(p)} for p in parameters
                    ],
                }
            ]

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{self.BASE_URL}/messages",
                headers=self._headers_with_correlation(to),
                json=payload,
            )

            response.raise_for_status()
            return response.json()


# ============================================================================
# CLIENT WAHA (piloto local)
# ============================================================================


class WahaClient:
    """
    Cliente HTTP para WAHA (WhatsApp HTTP API - piloto local).
    """

    def __init__(self, api_key: str, base_url: str, session: str = "default"):
        self.session = session
        self.headers = {"X-Api-Key": api_key, "Content-Type": "application/json"}
        self.base_url = base_url.rstrip("/")

    def _headers_with_correlation(self, reference: str | None = None) -> Dict[str, str]:
        correlation_id = current_correlation_id(
            "integration.whatsapp.waha", reference=reference
        )
        headers = dict(self.headers)
        headers["X-Correlation-ID"] = correlation_id
        headers["X-Request-ID"] = correlation_id
        return headers

    async def send_text_message(self, to: str, message: str) -> Dict[str, Any]:
        # WAHA espera número no formato "XXXXXXXXXXX@c.us"
        chat_id = to if "@" in to else f"{to}@c.us"
        payload = {
            "chatId": chat_id,
            "text": message,
            "session": self.session,
        }
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{self.base_url}/api/sendText",
                headers=self._headers_with_correlation(to),
                json=payload,
            )
            response.raise_for_status()
            # WAHA retorna 201 com corpo vazio
            return response.json() if response.content else {"status": "sent"}

    async def send_image_message(
        self, to: str, image_url: str, caption: Optional[str] = None
    ) -> Dict[str, Any]:
        chat_id = to if "@" in to else f"{to}@c.us"
        payload = {
            "chatId": chat_id,
            "file": {"url": image_url},
            "caption": caption or "",
            "session": self.session,
        }
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{self.base_url}/api/sendImage",
                headers=self._headers_with_correlation(to),
                json=payload,
            )
            response.raise_for_status()
            return response.json() if response.content else {"status": "sent"}


# ============================================================================
# SEND MESSAGE (HIGH-LEVEL)
# ============================================================================


async def send_whatsapp_message(
    db: Session,
    tenant_id: str,
    session_id: str,
    message: str,
    message_type: str = "text",
    image_url: Optional[str] = None,
    sent_by_user_id: Optional[str] = None,
) -> Optional[WhatsAppMessage]:
    with whatsapp_tenant_context(tenant_id):
        return await _send_whatsapp_message_with_context(
            db=db,
            tenant_id=tenant_id,
            session_id=session_id,
            message=message,
            message_type=message_type,
            image_url=image_url,
            sent_by_user_id=sent_by_user_id,
        )


async def _send_whatsapp_message_with_context(
    db: Session,
    tenant_id: str,
    session_id: str,
    message: str,
    message_type: str = "text",
    image_url: Optional[str] = None,
    sent_by_user_id: Optional[str] = None,
) -> Optional[WhatsAppMessage]:
    """
    Envia mensagem via WhatsApp e registra no banco.

    Args:
        db: Database session
        tenant_id: ID do tenant
        session_id: ID da sessão
        message: Conteúdo da mensagem
        message_type: "text", "image", "notificacao_sistema"
        image_url: URL da imagem (se type=image)
        sent_by_user_id: ID do usuário (se enviada por humano)

    Returns:
        WhatsAppMessage criada ou None se falhar
    """
    client_obj = None
    session = None
    origem = ledger_service.origem_do_envio(message_type, sent_by_user_id)
    try:
        # 1. Buscar config/cliente e sessão
        client_obj = _build_whatsapp_client(db, tenant_id)
        if not client_obj:
            return None

        session = db.query(WhatsAppSession).get(session_id)
        if not session:
            logger.error(f"Sessão {session_id} não encontrada")
            return None

        # 2. Enviar via API
        response = await _send_api_message(
            client_obj=client_obj,
            session=session,
            message=message,
            message_type=message_type,
            image_url=image_url,
        )

        # 3. Extrair message_id da resposta
        whatsapp_message_id = response.get("messages", [{}])[0].get("id")

        # 4. Registrar no banco
        db_message = WhatsAppMessage(
            session_id=session_id,
            tenant_id=tenant_id,
            tipo="enviada",
            conteudo=message,
            whatsapp_message_id=whatsapp_message_id,
            sent_by_user_id=sent_by_user_id,
            created_at=datetime.utcnow(),
        )

        db.add(db_message)

        # 5. Atualizar sessão
        session.message_count += 1
        session.last_message_at = datetime.utcnow()

        db.commit()
        db.refresh(db_message)

        logger.info(f"✅ Mensagem enviada: {whatsapp_message_id}")

        # 6. Livro-razao (controle de entrega e custo). Nunca atrapalha o envio.
        ledger_service.anotar_envio(
            db,
            tenant_id=tenant_id,
            provedor=ledger_service.provedor_do_cliente(client_obj),
            session=session,
            message_row=db_message,
            wa_message_id=whatsapp_message_id,
            origem=origem,
            tipo_conteudo="imagem" if message_type == "image" else "texto",
        )

        return db_message

    except httpx.HTTPStatusError as e:
        logger.error(
            f"❌ Erro HTTP ao enviar mensagem: {e.response.status_code} - {e.response.text}"
        )
        db.rollback()
        ledger_service.anotar_falha_de_envio(
            db,
            tenant_id=tenant_id,
            provedor=ledger_service.provedor_do_cliente(client_obj),
            session=session,
            session_id=session_id,
            origem=origem,
            erro_codigo=e.response.status_code,
            erro_mensagem=f"HTTP {e.response.status_code}",
        )
        return None

    except Exception as e:
        logger.error(f"❌ Erro ao enviar mensagem: {e}")
        db.rollback()
        if client_obj is not None:
            ledger_service.anotar_falha_de_envio(
                db,
                tenant_id=tenant_id,
                provedor=ledger_service.provedor_do_cliente(client_obj),
                session=session,
                session_id=session_id,
                origem=origem,
                erro_codigo=getattr(e, "codigo", None),
                erro_mensagem=getattr(e, "mensagem", None) or type(e).__name__,
            )
        return None


# ============================================================================
# ENVIO DE MODELO APROVADO (mensagem proativa, fora da janela de 24h)
# ============================================================================

CATEGORIAS_DE_MODELO = ("marketing", "utility", "authentication")


async def send_whatsapp_template(
    db: Session,
    tenant_id: str,
    session_id: str,
    template_name: str,
    categoria: str,
    parameters: Optional[list] = None,
    language_code: str = "pt_BR",
    origem: str = "automacao",
    texto_para_chat: Optional[str] = None,
) -> Optional[WhatsAppMessage]:
    """Envia um modelo aprovado pela Meta e registra no chat e no livro-razao.

    A categoria (marketing, utility ou authentication) e a que o modelo tem na Meta:
    e ela que define o preco cobrado, entao e gravada para a conferencia de custos.
    Respeita quem recusou mensagens; o bloqueio tambem fica registrado.
    """
    if categoria not in CATEGORIAS_DE_MODELO:
        raise ValueError(f"Categoria de modelo inválida: {categoria}")
    with whatsapp_tenant_context(tenant_id):
        return await _send_whatsapp_template_with_context(
            db=db,
            tenant_id=tenant_id,
            session_id=session_id,
            template_name=template_name,
            categoria=categoria,
            parameters=parameters,
            language_code=language_code,
            origem=origem,
            texto_para_chat=texto_para_chat,
        )


async def _send_whatsapp_template_with_context(
    *,
    db: Session,
    tenant_id: str,
    session_id: str,
    template_name: str,
    categoria: str,
    parameters: Optional[list],
    language_code: str,
    origem: str,
    texto_para_chat: Optional[str],
) -> Optional[WhatsAppMessage]:
    from app.whatsapp.consent_service import pode_enviar_whatsapp

    client_obj = None
    session = None
    try:
        client_obj = _build_whatsapp_client(db, tenant_id)
        if not client_obj:
            return None
        session = db.query(WhatsAppSession).get(session_id)
        if not session:
            logger.error(f"Sessão {session_id} não encontrada")
            return None
        provedor = ledger_service.provedor_do_cliente(client_obj)

        permitido, motivo = pode_enviar_whatsapp(
            db, tenant_id, session.phone_number, session.cliente_id
        )
        if not permitido:
            ledger_service.anotar_falha_de_envio(
                db,
                tenant_id=tenant_id,
                provedor=provedor,
                session=session,
                session_id=session_id,
                origem=origem,
                erro_codigo="bloqueado",
                erro_mensagem=f"Envio bloqueado: {motivo}",
                tipo_conteudo="modelo",
            )
            return None

        response = await client_obj.send_template_message(
            to=session.phone_number,
            template_name=template_name,
            language_code=language_code,
            parameters=parameters,
        )
        whatsapp_message_id = response.get("messages", [{}])[0].get("id")

        conteudo = texto_para_chat or f"[Modelo: {template_name}]"
        db_message = WhatsAppMessage(
            session_id=session_id,
            tenant_id=tenant_id,
            tipo="enviada",
            conteudo=conteudo,
            whatsapp_message_id=whatsapp_message_id,
            created_at=datetime.utcnow(),
        )
        db.add(db_message)
        session.message_count += 1
        session.last_message_at = datetime.utcnow()
        db.commit()
        db.refresh(db_message)

        ledger_service.anotar_envio(
            db,
            tenant_id=tenant_id,
            provedor=provedor,
            session=session,
            message_row=db_message,
            wa_message_id=whatsapp_message_id,
            origem=origem,
            tipo_conteudo="modelo",
            template_nome=template_name,
            template_categoria=categoria,
        )
        return db_message
    except Exception as erro:
        logger.error("Erro ao enviar modelo %s: %s", template_name, type(erro).__name__)
        db.rollback()
        if client_obj is not None:
            ledger_service.anotar_falha_de_envio(
                db,
                tenant_id=tenant_id,
                provedor=ledger_service.provedor_do_cliente(client_obj),
                session=session,
                session_id=session_id,
                origem=origem,
                erro_codigo=getattr(erro, "codigo", None),
                erro_mensagem=getattr(erro, "mensagem", None) or type(erro).__name__,
                tipo_conteudo="modelo",
            )
        return None
