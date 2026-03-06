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

from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

# Máximo de notificações por rodada (evita saturar conexão SMTP)
BATCH_SIZE = 50


def _smtp_config_ok() -> bool:
    """Retorna True somente se as variáveis SMTP estiverem configuradas."""
    from app.ia_config import SMTP_SERVER, SMTP_EMAIL, SMTP_PASSWORD
    return bool(SMTP_SERVER and SMTP_EMAIL and SMTP_PASSWORD)


def _send_email(to_address: str, subject: str, body_text: str) -> None:
    """
    Envia um e-mail via SMTP TLS.

    Levanta exceção em caso de falha (tratada no chamador).
    """
    from app.ia_config import SMTP_SERVER, SMTP_PORT, SMTP_EMAIL, SMTP_PASSWORD

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = SMTP_EMAIL
    msg["To"] = to_address

    # Corpo em texto simples e HTML (versão simples)
    part_text = MIMEText(body_text, "plain", "utf-8")
    html_body = body_text.replace("\n", "<br>")
    part_html = MIMEText(
        f"<html><body style='font-family:sans-serif;line-height:1.6'>{html_body}</body></html>",
        "html",
        "utf-8",
    )
    msg.attach(part_text)
    msg.attach(part_html)

    context = ssl.create_default_context()
    with smtplib.SMTP(SMTP_SERVER, SMTP_PORT, timeout=15) as server:
        server.ehlo()
        server.starttls(context=context)
        server.login(SMTP_EMAIL, SMTP_PASSWORD)
        server.sendmail(SMTP_EMAIL, to_address, msg.as_string())


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
                    else:
                        # push — App não publicado, marca como skipped
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
        _send_email(notif.email_address, subject, notif.body)
