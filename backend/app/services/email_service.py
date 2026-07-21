"""Servico de envio de e-mail via SMTP.

Configuração via variáveis de ambiente:
  SMTP_HOST        — ex.: smtp.gmail.com
  SMTP_PORT        — ex.: 587  (padrão)
  SMTP_USER        — endereço de login
  SMTP_PASSWORD    — senha / app password
  SMTP_FROM        — endereço de exibição (padrão: SMTP_USER)
  SMTP_TLS         — 'true' (padrão) ou 'false'

Se nenhuma variável estiver configurada, o envio é apenas simulado
(impresso no log) sem gerar erro.
"""

import logging
import os
import smtplib
import ssl
from email import policy
from pathlib import Path
from email.message import EmailMessage
from email.utils import formataddr, formatdate, make_msgid, parseaddr
from typing import Iterable, Mapping, Any
from dotenv import load_dotenv

from app.utils.correlation import current_correlation_id

logger = logging.getLogger(__name__)
DEFAULT_SENDER_NAME = "CorePet"


for env_path in (Path("/opt/petshop/.env"), Path(".env")):
    if env_path.exists():
        load_dotenv(env_path, override=False)


def _env_first(*keys: str, default: str = "") -> str:
    for key in keys:
        value = os.getenv(key)
        if value:
            return value
    return default


def _smtp_settings() -> dict[str, object]:
    host = _env_first("SMTP_HOST", "SMTP_SERVER", default="smtp.gmail.com")
    user = _env_first("SMTP_USER", "SMTP_EMAIL")
    password = _env_first("SMTP_PASSWORD")
    from_addr = _env_first("SMTP_FROM", "SMTP_EMAIL", "SMTP_USER", default=user)
    port_raw = _env_first("SMTP_PORT", default="587")
    use_tls_raw = _env_first("SMTP_TLS", default="true")

    try:
        port = int(port_raw)
    except (TypeError, ValueError):
        port = 587

    return {
        "host": host,
        "port": port,
        "user": user,
        "password": password,
        "from_addr": from_addr,
        "use_tls": str(use_tls_raw).lower() != "false",
    }


def _smtp_configured() -> bool:
    config = _smtp_settings()
    return bool(config["host"] and config["user"] and config["password"])


def is_email_configured() -> bool:
    return _smtp_configured()


def _normalizar_conteudo_anexo(content: Any) -> bytes:
    if content is None:
        return b""
    if isinstance(content, bytes):
        return content
    if isinstance(content, bytearray):
        return bytes(content)
    if isinstance(content, str):
        return content.encode("utf-8")
    if hasattr(content, "read"):
        return content.read()
    return bytes(content)


def _email_address(value: str) -> str:
    _, address = parseaddr(str(value or ""))
    return address or str(value or "").strip()


def _recipient_addresses(to: str | Iterable[str]) -> list[str]:
    values = [to] if isinstance(to, str) else list(to)
    addresses = []
    seen = set()

    for value in values:
        address = _email_address(str(value))
        key = address.casefold()
        if address and key not in seen:
            addresses.append(address)
            seen.add(key)

    return addresses


def _sender_domain(from_addr: str) -> str | None:
    address = _email_address(from_addr)
    if "@" not in address:
        return None
    domain = address.rsplit("@", 1)[1].strip().strip(">")
    return domain or None


def _format_from_header(from_addr: str) -> str:
    name, address = parseaddr(str(from_addr or ""))
    if address and not name:
        return formataddr((DEFAULT_SENDER_NAME, address))
    return str(from_addr or "").strip()


def _smtp_tls_context() -> ssl.SSLContext:
    context = ssl.create_default_context(purpose=ssl.Purpose.SERVER_AUTH)
    context.minimum_version = ssl.TLSVersion.TLSv1_2
    context.verify_mode = ssl.CERT_REQUIRED
    context.check_hostname = True
    return context


def _build_email_message(
    *,
    from_addr: str,
    to: str,
    subject: str,
    html_body: str,
    text_body: str | None = None,
    attachments: Iterable[Mapping[str, Any]] | None = None,
    correlation_id: str | None = None,
) -> EmailMessage:
    resolved_correlation_id = current_correlation_id(
        "integration.email.smtp",
        reference=f"{to}:{subject}",
        correlation_id=correlation_id,
    )
    msg = EmailMessage(policy=policy.SMTP)
    msg["Subject"] = subject
    msg["From"] = _format_from_header(from_addr)
    msg["To"] = to
    msg["Date"] = formatdate(localtime=True)
    msg["Message-ID"] = make_msgid(domain=_sender_domain(from_addr))
    msg["Reply-To"] = _email_address(from_addr)
    msg["X-Mailer"] = DEFAULT_SENDER_NAME
    msg["X-Correlation-ID"] = resolved_correlation_id

    texto_fallback = (
        text_body or "Seu cliente de e-mail nao exibiu o conteudo HTML desta mensagem."
    )
    msg.set_content(texto_fallback, subtype="plain", charset="utf-8")
    msg.add_alternative(html_body, subtype="html", charset="utf-8")

    for attachment in attachments or []:
        filename = str(attachment.get("filename") or "anexo.bin")
        content = _normalizar_conteudo_anexo(attachment.get("content"))
        mime_subtype = str(attachment.get("mime_subtype") or "octet-stream")
        msg.add_attachment(
            content,
            maintype="application",
            subtype=mime_subtype,
            filename=filename,
        )

    return msg


def send_email(
    to: str | Iterable[str],
    subject: str,
    html_body: str,
    text_body: str | None = None,
    attachments: Iterable[Mapping[str, Any]] | None = None,
    simulate_if_unconfigured: bool = True,
) -> bool:
    """Envia um e-mail. Retorna True se enviado com sucesso, False caso contrario."""
    recipients = _recipient_addresses(to)
    if not recipients:
        logger.warning("[EMAIL-SEM-DESTINATARIO] Envio ignorado")
        return False

    to_header = ", ".join(recipients)
    correlation_id = current_correlation_id(
        "integration.email.smtp", reference=f"{to_header}:{subject}"
    )
    if not _smtp_configured():
        if simulate_if_unconfigured:
            logger.info(
                "[EMAIL-SIMULADO] Destinatarios: %s | correlation_id=%s",
                len(recipients),
                correlation_id,
            )
            return True
        logger.warning(
            "[EMAIL-NAO-CONFIGURADO] Destinatarios: %s | correlation_id=%s",
            len(recipients),
            correlation_id,
        )
        return False

    config = _smtp_settings()
    host = str(config["host"])
    port = int(config["port"])
    user = str(config["user"])
    password = str(config["password"])
    from_addr = str(config["from_addr"])
    use_tls = bool(config["use_tls"])
    envelope_from = _email_address(from_addr) or user

    msg = _build_email_message(
        from_addr=from_addr,
        to=to_header,
        subject=subject,
        html_body=html_body,
        text_body=text_body,
        attachments=attachments,
        correlation_id=correlation_id,
    )

    try:
        with smtplib.SMTP(host, port, timeout=10) as server:
            server.ehlo()
            if use_tls:
                server.starttls(context=_smtp_tls_context())
                server.ehlo()
            server.login(user, password)
            server.sendmail(envelope_from, recipients, msg.as_bytes(policy=policy.SMTP))
        logger.info(
            "[EMAIL-ENVIADO] Destinatarios: %s | correlation_id=%s",
            len(recipients),
            correlation_id,
        )
        return True
    except Exception as exc:
        logger.error(
            "[EMAIL-ERRO] Destinatarios: %s | Erro: %s | correlation_id=%s",
            len(recipients),
            exc,
            correlation_id,
        )
        return False


def send_notify_me_email(
    to: str, product_name: str, store_name: str, store_url: str
) -> bool:
    """Envia aviso de produto voltou ao estoque."""
    subject = f"🐾 {product_name} está disponível na {store_name}!"
    html_body = f"""
    <html><body style="font-family:Arial,sans-serif;color:#333;max-width:600px;margin:0 auto;">
      <div style="background:#6366f1;padding:20px;border-radius:8px 8px 0 0;">
        <h1 style="color:#fff;margin:0;font-size:22px;">Produto disponível! 🎉</h1>
      </div>
      <div style="padding:24px;border:1px solid #e5e7eb;border-top:none;border-radius:0 0 8px 8px;">
        <p>Olá! Você pediu para ser avisado quando o produto ficasse disponível.</p>
        <h2 style="color:#6366f1;">{product_name}</h2>
        <p>O produto voltou ao estoque em <strong>{store_name}</strong>. Corra antes que acabe!</p>
        <a href="{store_url}"
           style="display:inline-block;background:#6366f1;color:#fff;padding:12px 24px;
                  border-radius:6px;text-decoration:none;font-weight:bold;margin-top:8px;">
          Comprar agora
        </a>
        <hr style="margin-top:32px;border:none;border-top:1px solid #e5e7eb;">
        <p style="font-size:12px;color:#9ca3af;">
          Você recebeu este e-mail porque solicitou um aviso de disponibilidade.
        </p>
      </div>
    </body></html>
    """
    text_body = f"{product_name} está disponível em {store_name}!\nAcesse: {store_url}"
    return send_email(to, subject, html_body, text_body)
