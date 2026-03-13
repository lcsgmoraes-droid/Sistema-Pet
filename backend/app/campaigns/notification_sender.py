"""
Notification Sender — Despacho de Notificações da Fila
=========================================================

Processa registros pendentes em `notification_queue` e realiza o envio real.

Canais suportados:
  - email : SMTP (via ia_config.SMTP_*)
  - push  : placeholder (App ainda não publicado)

Uso pelo scheduler (a cada 5 minutos):
    from app.campaigns.notification_sender import NotificationSender
    sender = NotificationSender(db_factory=SessionLocal)
    sender.process_batch()
"""

import logging
import smtplib
import ssl
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime

import requests

from sqlalchemy import or_
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

# Máximo de notificações por rodada (evita saturar conexão SMTP)
BATCH_SIZE = 50
EXPO_PUSH_URL = "https://exp.host/--/api/v2/push/send"


def _smtp_config_ok() -> bool:
    """Retorna True somente se as variáveis SMTP estiverem configuradas."""
    from app.ia_config import SMTP_SERVER, SMTP_EMAIL, SMTP_PASSWORD
    return bool(SMTP_SERVER and SMTP_EMAIL and SMTP_PASSWORD)


def _render_email_html(subject: str, body_text: str, campaign_type: str | None = None) -> str:
    """
    Gera HTML bonito para o e-mail, com cor de destaque conforme o tipo de campanha.
    """
    COLOR_MAP = {
        "birthday_customer": ("#e91e8c", "#fff0f7"),
        "birthday_pet":      ("#8e44ad", "#f8f0ff"),
        "welcome_app":       ("#1976d2", "#f0f6ff"),
        "welcome_ecommerce": ("#1976d2", "#f0f6ff"),
        "inactivity":        ("#e67e22", "#fff8f0"),
        "quick_repurchase":  ("#2e7d32", "#f0fff4"),
        "loyalty_stamp":     ("#f9a825", "#fffde7"),
        "cashback":          ("#00838f", "#e0f7fa"),
        "ranking_monthly":   ("#37474f", "#f5f5f5"),
    }
    accent, bg = COLOR_MAP.get(campaign_type or "", ("#1565c0", "#f0f6ff"))

    # Converte texto simples em parágrafos HTML
    paragraphs = ""
    for line in body_text.split("\n"):
        line_stripped = line.strip()
        if line_stripped:
            # Negrito para **texto**
            import re
            line_stripped = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", line_stripped)
            paragraphs += f"<p style='margin:0 0 12px 0;color:#333;font-size:15px;line-height:1.6'>{line_stripped}</p>\n"

    return f"""<!DOCTYPE html>
<html lang="pt-BR">
<head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"></head>
<body style="margin:0;padding:0;background:#f4f4f4;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Arial,sans-serif">
  <table width="100%" cellpadding="0" cellspacing="0" style="background:#f4f4f4;padding:24px 0">
    <tr><td align="center">
      <table width="560" cellpadding="0" cellspacing="0" style="background:#ffffff;border-radius:12px;overflow:hidden;box-shadow:0 2px 8px rgba(0,0,0,0.08)">
        <!-- Header -->
        <tr>
          <td style="background:{accent};padding:28px 32px;text-align:center">
            <h1 style="margin:0;color:#fff;font-size:22px;font-weight:700;letter-spacing:-0.3px">{subject}</h1>
          </td>
        </tr>
        <!-- Body -->
        <tr>
          <td style="padding:28px 32px;background:{bg}">
            {paragraphs}
          </td>
        </tr>
        <!-- Footer -->
        <tr>
          <td style="padding:16px 32px;background:#f9f9f9;border-top:1px solid #eee;text-align:center">
            <p style="margin:0;font-size:12px;color:#999">
              Esta mensagem foi enviada automaticamente pelo sistema de campanhas do seu petshop.
            </p>
          </td>
        </tr>
      </table>
    </td></tr>
  </table>
</body>
</html>"""


def _send_email(to_address: str, subject: str, body_text: str, campaign_type: str | None = None) -> None:
    """
    Envia um e-mail via SMTP TLS com template HTML bonito por tipo de campanha.

    Levanta exceção em caso de falha (tratada no chamador).
    """
    from app.ia_config import SMTP_SERVER, SMTP_PORT, SMTP_EMAIL, SMTP_PASSWORD

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = SMTP_EMAIL
    msg["To"] = to_address

    # Corpo em texto simples e HTML bonito
    part_text = MIMEText(body_text, "plain", "utf-8")
    html_body = _render_email_html(subject, body_text, campaign_type)
    part_html = MIMEText(html_body, "html", "utf-8")
    msg.attach(part_text)
    msg.attach(part_html)

    context = ssl.create_default_context()
    with smtplib.SMTP(SMTP_SERVER, SMTP_PORT, timeout=15) as server:
        server.ehlo()
        server.starttls(context=context)
        server.login(SMTP_EMAIL, SMTP_PASSWORD)
        server.sendmail(SMTP_EMAIL, to_address, msg.as_string())


def _send_push(push_token: str, title: str, body_text: str, data: dict | None = None) -> None:
    """Envia push usando Expo Push API."""
    if not push_token:
        raise ValueError("Notificação sem push_token")

    payload = {
        "to": push_token,
        "title": title,
        "body": body_text,
        "sound": "default",
        "data": data or {},
    }

    response = requests.post(EXPO_PUSH_URL, json=payload, timeout=10)
    response.raise_for_status()
    body_json = response.json()

    data_obj = body_json.get("data") if isinstance(body_json, dict) else None
    if not isinstance(data_obj, dict):
        return

    status = data_obj.get("status")
    if status and status != "ok":
        detail = data_obj.get("details")
        raise RuntimeError(f"Falha no push Expo: status={status} details={detail}")


class NotificationSender:
    """Processa lotes de notificações pendentes da fila."""

    def __init__(self, db_factory):
        self.db_factory = db_factory

    def process_batch(self, batch_size: int = BATCH_SIZE) -> dict:
        """
        Processa até `batch_size` notificações pendentes.

        Retorna: { "processed": int, "sent": int, "failed": int, "skipped": int }
        """
        from app.campaigns.models import NotificationQueue, NotificationStatusEnum

        db: Session = self.db_factory()
        stats = {"processed": 0, "sent": 0, "failed": 0, "skipped": 0}

        try:
            pending = (
                db.query(NotificationQueue)
                .filter(NotificationQueue.status == NotificationStatusEnum.pending)
                .filter(
                    or_(
                        NotificationQueue.scheduled_at.is_(None),
                        NotificationQueue.scheduled_at <= datetime.now(),
                    )
                )
                .with_for_update(skip_locked=True)
                .order_by(NotificationQueue.created_at.asc())
                .limit(batch_size)
                .all()
            )

            if not pending:
                return stats

            for notif in pending:
                stats["processed"] += 1
                try:
                    if notif.channel.value == "email":
                        self._dispatch_email(notif)
                        notif.status = NotificationStatusEnum.sent
                        stats["sent"] += 1
                    elif notif.channel.value == "push":
                        self._dispatch_push(notif)
                        notif.status = NotificationStatusEnum.sent
                        stats["sent"] += 1
                    else:
                        # Canal não suportado no sender atual
                        notif.status = NotificationStatusEnum.skipped
                        stats["skipped"] += 1
                except Exception as exc:
                    notif.retry_count += 1
                    if notif.retry_count >= notif.max_retries:
                        notif.status = NotificationStatusEnum.failed
                        logger.error(
                            "[NotifSender] Falha definitiva id=%d: %s", notif.id, exc
                        )
                    else:
                        logger.warning(
                            "[NotifSender] Tentativa %d/%d falhou id=%d: %s",
                            notif.retry_count, notif.max_retries, notif.id, exc,
                        )
                    stats["failed"] += 1

            db.commit()
            if stats["processed"]:
                logger.info("[NotifSender] %s", stats)

        except Exception as exc:
            db.rollback()
            logger.exception("[NotifSender] Erro ao processar lote: %s", exc)
        finally:
            db.close()

        return stats

    def _dispatch_email(self, notif) -> None:
        if not notif.email_address:
            # Sem endereço de e-mail — não há o que enviar
            raise ValueError("Notificação sem email_address")

        if not _smtp_config_ok():
            # SMTP não configurado — não falha, apenas pula silenciosamente
            logger.debug(
                "[NotifSender] SMTP não configurado — notif id=%d pulada", notif.id
            )
            # Levanta para que seja contado como skipped pelo chamador?
            # Não — marca como sent para não poluir retries quando não há config.
            return

        subject = notif.subject or "Mensagem especial para você"
        # Infere o tipo de campanha pelo prefixo da chave de idempotência para selecionar o template
        ikey = notif.idempotency_key or ""
        _KEY_TYPE_MAP = {
            "bday": "birthday_customer",
            "birthday": "birthday_customer",
            "pet_bday": "birthday_pet",
            "loyalty": "loyalty_stamp",
            "cashback": "cashback",
            "inactivity": "inactivity",
            "welcome": "welcome_app",
            "quick": "quick_repurchase",
            "sorteio": "drawing",
            "destaque": "ranking_monthly",
        }
        campaign_type = None
        for prefix, ctype in _KEY_TYPE_MAP.items():
            if ikey.startswith(prefix):
                campaign_type = ctype
                break
        _send_email(notif.email_address, subject, notif.body, campaign_type)

    def _dispatch_push(self, notif) -> None:
        if not notif.push_token:
            raise ValueError("Notificação sem push_token")

        subject = notif.subject or "Sistema Pet"
        _send_push(
            push_token=notif.push_token,
            title=subject,
            body_text=notif.body,
            data={"idempotency_key": notif.idempotency_key},
        )
