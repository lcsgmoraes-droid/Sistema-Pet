"""Filtros compartilhados para vendas disponiveis na operacao de entrega."""

from sqlalchemy import or_

from app.vendas_models import Venda


def filtros_venda_entrega_operacional(tenant_id):
    """Restringe consultas a entregas abertas e a vendas nao canceladas."""
    return (
        Venda.tenant_id == tenant_id,
        Venda.status != "cancelada",
        Venda.tem_entrega.is_(True),
        or_(
            Venda.status_entrega.in_(["pendente", "pronto"]),
            Venda.status_entrega.is_(None),
        ),
        Venda.endereco_entrega.isnot(None),
    )
