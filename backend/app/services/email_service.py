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
from pathlib import Path
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Iterable, Mapping, Any
from dotenv import load_dotenv

logger = logging.getLogger(__name__)


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


def send_email(
    to: str,
    subject: str,
    html_body: str,
    text_body: str | None = None,
    attachments: Iterable[Mapping[str, Any]] | None = None,
    simulate_if_unconfigured: bool = True,
) -> bool:
    """Envia um e-mail. Retorna True se enviado com sucesso, False caso contrario."""
    if not _smtp_configured():
        if simulate_if_unconfigured:
            logger.info("[EMAIL-SIMULADO] Para: %s | Assunto: %s", to, subject)
            return True
        logger.warning("[EMAIL-NAO-CONFIGURADO] Para: %s | Assunto: %s", to, subject)
        return False

    config = _smtp_settings()
    host = str(config["host"])
    port = int(config["port"])
    user = str(config["user"])
    password = str(config["password"])
    from_addr = str(config["from_addr"])
    use_tls = bool(config["use_tls"])

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = from_addr
    msg["To"] = to

    if text_body:
        msg.attach(MIMEText(text_body, "plain", "utf-8"))
    msg.attach(MIMEText(html_body, "html", "utf-8"))

    for attachment in attachments or []:
        filename = str(attachment.get("filename") or "anexo.bin")
        content = attachment.get("content") or b""
        mime_subtype = str(attachment.get("mime_subtype") or "octet-stream")
        part = MIMEApplication(content, _subtype=mime_subtype)
        part.add_header("Content-Disposition", "attachment", filename=filename)
        msg.attach(part)

    try:
        with smtplib.SMTP(host, port, timeout=10) as server:
            if use_tls:
                server.starttls()
            server.login(user, password)
            server.sendmail(from_addr, [to], msg.as_string())
        logger.info("[EMAIL-ENVIADO] Para: %s | Assunto: %s", to, subject)
        return True
    except Exception as exc:
        logger.error("[EMAIL-ERRO] Para: %s | Erro: %s", to, exc)
        return False


def send_notify_me_email(to: str, product_name: str, store_name: str, store_url: str) -> bool:
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
    text_body = (
        f"{product_name} está disponível em {store_name}!\n"
        f"Acesse: {store_url}"
    )
    return send_email(to, subject, html_body, text_body)
