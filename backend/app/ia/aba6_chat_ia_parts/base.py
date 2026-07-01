"""Base compartilhada do servico de chat IA."""

from datetime import date, datetime
import os
from typing import Optional
import unicodedata

from sqlalchemy.orm import Session

from app.utils.logger import logger


class ChatIABase:
    def __init__(self, db: Session):
        self.db = db
        self.openai_api_key = os.getenv("OPENAI_API_KEY")

    def _resolver_tenant_id(
        self, usuario_id: int, tenant_id: Optional[str]
    ) -> Optional[str]:
        """Resolve tenant_id para consultas seguras de dados."""
        if tenant_id:
            return str(tenant_id)

        try:
            from app.models import UserTenant

            user_tenant = (
                self.db.query(UserTenant)
                .filter(UserTenant.user_id == usuario_id)
                .order_by(UserTenant.id.desc())
                .first()
            )
            return str(user_tenant.tenant_id) if user_tenant else None
        except Exception as e:
            logger.warning(f"Não foi possível resolver tenant_id no chat IA: {e}")
            return None

    def _date_bounds_for_today() -> tuple[datetime, datetime]:
        hoje = date.today()
        inicio = datetime.combine(hoje, datetime.min.time())
        fim = datetime.combine(hoje, datetime.max.time())
        return inicio, fim

    def _date_bounds_for_current_month() -> tuple[datetime, datetime]:
        hoje = date.today()
        inicio = datetime(hoje.year, hoje.month, 1)
        fim = datetime.combine(hoje, datetime.max.time())
        return inicio, fim

    def _normalizar_texto(texto: str) -> str:
        texto = unicodedata.normalize("NFKD", texto or "")
        texto = "".join(ch for ch in texto if not unicodedata.combining(ch))
        return texto.lower().strip()
