"""Consulta paginada das compras, sem buscar o cadastro de cada produto."""

from sqlalchemy import and_, case, func, or_, select
from sqlalchemy.orm import aliased

from app.financeiro_models import ContaReceber
from app.vendas_models import Venda, VendaPagamento


def status_pagamento_sql(tenant_id):
    """Equivalente ao resumo de pagamento para filtrar antes de paginar.

    O plano de crediario nao representa dinheiro recebido. Somente as baixas
    das parcelas correspondentes entram no saldo, como no resumo do PDV.
    """
    pagamento = aliased(VendaPagamento)
    conta = aliased(ContaReceber)
    valido = func.lower(func.trim(func.coalesce(pagamento.status, ""))).notin_(
        ("estornado", "recusado", "cancelado", "cancelada")
    )
    crediario = or_(
        func.lower(func.trim(pagamento.forma_pagamento)).in_(
            ("crediario", "crediário")
        ),
        func.coalesce(pagamento.intervalo_crediario, "") != "",
    )
    pagamentos = (
        select(
            pagamento.venda_id.label("venda_id"),
            func.count(pagamento.id).label("total"),
            func.sum(case((valido, 1), else_=0)).label("validos"),
            func.sum(case((and_(valido, crediario), 1), else_=0)).label("crediarios"),
            func.sum(
                case(
                    (
                        and_(
                            valido, crediario, pagamento.forma_pagamento_id.isnot(None)
                        ),
                        1,
                    ),
                    else_=0,
                )
            ).label("formas_crediario"),
            func.sum(case((and_(valido, ~crediario), pagamento.valor), else_=0)).label(
                "imediatos"
            ),
            func.sum(case((and_(valido, crediario), pagamento.valor), else_=0)).label(
                "valor_crediario"
            ),
        )
        .where(pagamento.tenant_id == tenant_id)
        .group_by(pagamento.venda_id)
        .subquery()
    )
    forma_crediario = (
        select(pagamento.id)
        .where(
            pagamento.tenant_id == tenant_id,
            pagamento.venda_id == conta.venda_id,
            valido,
            crediario,
            pagamento.forma_pagamento_id == conta.forma_pagamento_id,
        )
        .correlate(conta)
        .exists()
    )
    recebido = case((conta.valor_recebido > 0, conta.valor_recebido), else_=0)
    contas = (
        select(
            conta.venda_id.label("venda_id"),
            func.sum(recebido).label("recebido"),
            func.sum(case((forma_crediario, recebido), else_=0)).label(
                "recebido_crediario"
            ),
        )
        .where(
            conta.tenant_id == tenant_id,
            func.lower(func.trim(func.coalesce(conta.status, ""))).notin_(
                ("cancelada", "cancelado")
            ),
        )
        .group_by(conta.venda_id)
        .subquery()
    )
    recebido_crediario = case(
        (
            and_(
                pagamentos.c.formas_crediario == 0,
                pagamentos.c.crediarios == pagamentos.c.validos,
            ),
            func.coalesce(contas.c.recebido, 0),
        ),
        else_=func.coalesce(contas.c.recebido_crediario, 0),
    )
    limite_crediario = case(
        (pagamentos.c.valor_crediario > 0, pagamentos.c.valor_crediario), else_=0
    )
    recebido_crediario = case(
        (recebido_crediario < limite_crediario, recebido_crediario),
        else_=limite_crediario,
    )
    pago = case(
        (
            pagamentos.c.total > 0,
            func.coalesce(pagamentos.c.imediatos, 0) + recebido_crediario,
        ),
        else_=func.coalesce(contas.c.recebido, 0),
    )
    pago = case((pago > 0, pago), else_=0)
    total = case((Venda.total > 0, Venda.total), else_=0)
    status = case(
        (Venda.status == "cancelada", "cancelada"),
        (pago >= total, "pago"),
        (pago > 0, "parcial"),
        else_="em_aberto",
    )
    return pagamentos, contas, status
