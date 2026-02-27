"""Serviço de envio de e-mail via SMTP.

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
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

logger = logging.getLogger(__name__)


def _smtp_configured() -> bool:
    return bool(os.getenv("SMTP_HOST") and os.getenv("SMTP_USER") and os.getenv("SMTP_PASSWORD"))


def send_email(to: str, subject: str, html_body: str, text_body: str | None = None) -> bool:
    """Envia um e-mail. Retorna True se enviado com sucesso, False caso contrário."""
    if not _smtp_configured():
        logger.info("[EMAIL-SIMULADO] Para: %s | Assunto: %s", to, subject)
        return True  # Simula sucesso para não quebrar o fluxo

    host = os.getenv("SMTP_HOST", "")
    port = int(os.getenv("SMTP_PORT", "587"))
    user = os.getenv("SMTP_USER", "")
    password = os.getenv("SMTP_PASSWORD", "")
    from_addr = os.getenv("SMTP_FROM", user)
    use_tls = os.getenv("SMTP_TLS", "true").lower() != "false"

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = from_addr
    msg["To"] = to

    if text_body:
        msg.attach(MIMEText(text_body, "plain", "utf-8"))
    msg.attach(MIMEText(html_body, "html", "utf-8"))

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
