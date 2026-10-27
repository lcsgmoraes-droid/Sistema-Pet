"""OPS: consumo de mensagens de WhatsApp por loja (base do repasse de custos da Meta)."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session

from app.models import Tenant
from app.tenancy.context import tenant_context
from app.tenancy.rls import sync_rls_tenant
from app.whatsapp.ledger_service import periodo_do_mes, resumo_do_periodo

LIMITE_DE_LOJAS = 500


def consumo_do_mes(db: Session, mes: str | None) -> dict[str, Any]:
    """Resumo do livro-razao de cada loja (uma loja por vez, respeitando o isolamento)."""
    inicio, fim = periodo_do_mes(mes)
    lojas = db.query(Tenant).order_by(Tenant.name).limit(LIMITE_DE_LOJAS).all()
    itens = []
    totais = {"enviadas": 0, "recebidas": 0, "falhas": 0, "cobraveis": 0}
    for tenant in lojas:
        tenant_id = UUID(str(tenant.id))
        with tenant_context(tenant_id):
            sync_rls_tenant(db, tenant_id)
            resumo = resumo_do_periodo(db, tenant_id, inicio, fim)
        movimento = resumo["totais"]
        if not (movimento["enviadas"] or movimento["recebidas"]):
            continue
        itens.append({"loja_id": str(tenant_id), "loja_nome": tenant.name, **resumo})
        for chave in totais:
            totais[chave] += movimento[chave]
    return {
        "periodo": {"inicio": inicio.isoformat(), "fim": fim.isoformat()},
        "lojas": itens,
        "totais": totais,
    }
