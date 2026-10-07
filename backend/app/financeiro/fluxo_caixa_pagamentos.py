"""Baixas de contas a pagar exibidas no fluxo de caixa."""

from datetime import date

from sqlalchemy.orm import Session, joinedload

from app.financeiro.fluxo_caixa_schemas import FluxoCaixaMovimentacao
from app.financeiro_models import ContaPagar, Pagamento


def movimentacoes_pagamentos_contas_pagar(
    db: Session, tenant_id, dt_inicio: date, dt_fim: date
) -> list[FluxoCaixaMovimentacao]:
    """Usa cada baixa como saída e mantém contas históricas pagas sem baixa."""
    movimentacoes = []
    pagamentos = (
        db.query(Pagamento)
        .join(ContaPagar, Pagamento.conta_pagar_id == ContaPagar.id)
        .options(joinedload(Pagamento.conta).joinedload(ContaPagar.fornecedor))
        .filter(
            Pagamento.tenant_id == tenant_id,
            ContaPagar.tenant_id == tenant_id,
            Pagamento.data_pagamento >= dt_inicio,
            Pagamento.data_pagamento <= dt_fim,
        )
        .all()
    )
    for pagamento in pagamentos:
        fornecedor_nome = (
            pagamento.conta.fornecedor.nome
            if pagamento.conta.fornecedor
            else "Fornecedor"
        )
        movimentacoes.append(
            FluxoCaixaMovimentacao(
                data=pagamento.data_pagamento,
                tipo="saida",
                descricao=f"Pagamento - {fornecedor_nome}",
                categoria="Fornecedores",
                valor=float(pagamento.valor_pago),
                origem_tipo="conta_pagar",
                origem_id=pagamento.conta_pagar_id,
                status="realizado",
            )
        )

    contas_pagas = (
        db.query(ContaPagar)
        .options(joinedload(ContaPagar.fornecedor))
        .filter(
            ContaPagar.tenant_id == tenant_id,
            ContaPagar.data_pagamento >= dt_inicio,
            ContaPagar.data_pagamento <= dt_fim,
            ContaPagar.status == "pago",
        )
        .all()
    )
    ids_contas_pagas = [conta.id for conta in contas_pagas]
    contas_com_pagamentos = set()
    if ids_contas_pagas:
        contas_com_pagamentos = {
            conta_id
            for (conta_id,) in db.query(Pagamento.conta_pagar_id)
            .filter(
                Pagamento.tenant_id == tenant_id,
                Pagamento.conta_pagar_id.in_(ids_contas_pagas),
            )
            .all()
        }

    for conta in contas_pagas:
        if conta.id in contas_com_pagamentos:
            continue
        fornecedor_nome = conta.fornecedor.nome if conta.fornecedor else "Fornecedor"
        movimentacoes.append(
            FluxoCaixaMovimentacao(
                data=conta.data_pagamento,
                tipo="saida",
                descricao=f"Pagamento - {fornecedor_nome}",
                categoria="Fornecedores",
                valor=float(conta.valor_pago or 0),
                origem_tipo="conta_pagar",
                origem_id=conta.id,
                status="realizado",
            )
        )

    return movimentacoes
