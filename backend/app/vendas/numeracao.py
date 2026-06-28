"""Numeracao sequencial de vendas por tenant."""

from sqlalchemy import desc
from sqlalchemy.orm import Session

from app.utils.timezone import now_brasilia

__all__ = ["gerar_numero_venda"]


def gerar_numero_venda(db: Session, tenant_id: str, user_id: int | None = None) -> str:
    """
    Gera um número sequencial para a venda no formato YYYYMMDDNNNN.

    Args:
        db: Sessão do SQLAlchemy
        user_id: ID do usuário

    Returns:
        String no formato YYYYMMDDNNNN (ex: 202501230001)
    """
    from app.vendas_models import Venda

    hoje = now_brasilia()
    prefixo = hoje.strftime("%Y%m%d")

    # A numeracao pode repetir entre tenants, mas nunca dentro do mesmo tenant.
    ultima_venda = (
        db.query(Venda)
        .filter(Venda.numero_venda.like(f"{prefixo}%"), Venda.tenant_id == tenant_id)
        .order_by(desc(Venda.numero_venda))
        .first()
    )

    if ultima_venda:
        try:
            seq = int(ultima_venda.numero_venda[-4:]) + 1
        except (TypeError, ValueError):
            seq = 1
    else:
        seq = 1

    return f"{prefixo}{seq:04d}"
