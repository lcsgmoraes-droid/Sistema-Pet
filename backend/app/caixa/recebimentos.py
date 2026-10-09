"""Escopo do recebimento, independente do caixa de origem da venda."""

from sqlalchemy import and_, func

from app.caixa.conferencia import FORMAS_PAGAMENTO_A_PRAZO, moeda
from app.vendas_models import Venda, VendaPagamento


def filtro_pagamentos_validos():
    return func.lower(func.trim(func.coalesce(VendaPagamento.status, ""))).notin_(
        ["estornado", "recusado", "cancelado", "cancelada"]
    )


def filtro_pagamentos_caixa(caixa):
    # Nunca inferir pelo caixa original da venda: após a reabertura esse intervalo
    # muda. Legados só entram quando a migração conseguiu atribuí-los com segurança.
    return and_(
        VendaPagamento.caixa_id == caixa.id,
        filtro_pagamentos_validos(),
    )


def filtro_recebimentos_caixa(caixa):
    """Planos a prazo ficam na composição da venda, fora das entradas efetivas."""
    return and_(
        filtro_pagamentos_caixa(caixa),
        func.lower(func.trim(VendaPagamento.forma_pagamento)).notin_(
            sorted(FORMAS_PAGAMENTO_A_PRAZO)
        ),
    )


def carregar_pagamentos_vendas(db, *, venda_ids, tenant_id):
    """Histórico da venda, sem atribuir seu recebimento ao caixa de origem."""
    if not venda_ids:
        return {}
    pagamentos = (
        db.query(VendaPagamento)
        .join(Venda, VendaPagamento.venda_id == Venda.id)
        .filter(
            Venda.id.in_(venda_ids),
            Venda.tenant_id == tenant_id,
            VendaPagamento.tenant_id == tenant_id,
        )
        .order_by(
            VendaPagamento.venda_id,
            VendaPagamento.data_pagamento,
            VendaPagamento.id,
        )
        .all()
    )
    por_venda = {}
    for pagamento in pagamentos:
        por_venda.setdefault(pagamento.venda_id, []).append(pagamento.to_dict())
    return por_venda


def resumir_pagamentos_vendas_caixa(db, *, caixa_id, tenant_id):
    """Composição registrada nas vendas; não representa recebimento no caixa.

    Inclui planos a prazo e registros legados sem caixa. Um pagamento em dinheiro
    sem vínculo pode ter seu recebimento comprovado por MovimentacaoCaixa; este
    indicador apenas identifica a ausência do vínculo no registro do pagamento.
    """
    grupos = (
        db.query(
            VendaPagamento.forma_pagamento,
            VendaPagamento.caixa_id.is_(None).label("sem_caixa"),
            func.count(VendaPagamento.id).label("quantidade"),
            func.sum(VendaPagamento.valor).label("total"),
        )
        .join(Venda, VendaPagamento.venda_id == Venda.id)
        .filter(
            Venda.caixa_id == caixa_id,
            Venda.tenant_id == tenant_id,
            Venda.status.in_(["finalizada", "baixa_parcial", "pago_nf"]),
            VendaPagamento.tenant_id == tenant_id,
            filtro_pagamentos_validos(),
        )
        .group_by(VendaPagamento.forma_pagamento, VendaPagamento.caixa_id.is_(None))
        .order_by(VendaPagamento.forma_pagamento)
        .all()
    )
    por_forma = {}
    sem_caixa = {"quantidade": 0, "total": 0.0, "por_forma_pagamento": {}}
    for forma, sem_vinculo, quantidade, total in grupos:
        destinos = [por_forma]
        if sem_vinculo:
            destinos.append(sem_caixa["por_forma_pagamento"])
            sem_caixa["quantidade"] += int(quantidade)
            sem_caixa["total"] = float(moeda(sem_caixa["total"]) + moeda(total))
        for destino in destinos:
            item = destino.setdefault(
                forma, {"quantidade": 0, "total": 0.0, "tipo_contagem": "pagamento"}
            )
            item["quantidade"] += int(quantidade)
            item["total"] = float(moeda(item["total"]) + moeda(total))
    return {
        "pagamentos_vendas_por_forma_pagamento": por_forma,
        "pagamentos_vendas_sem_caixa": sem_caixa,
    }
