"""Conferência financeira antes de editar o valor de uma venda aberta."""

from fastapi import HTTPException
from sqlalchemy.orm.attributes import set_committed_value

from app.financeiro_models import ContaReceber
from app.services.venda_descontos import ZERO, moeda
from app.vendas.pagamento_excedente import (
    snapshot_pagamentos_excedente,
    validar_excesso_pagamento,
)
from app.vendas_models import VendaPagamento


def fotografar_pagamentos_edicao(db, *, venda, tenant_id):
    """Lê valores brutos e deduplicados sob o mesmo lock da edição da venda.

    A baixa direta de parcelas bloqueia a conta, em vez da venda. Travar essas
    contas antes da fotografia também serializa a edição com esse recebimento.
    Atribuir os relacionamentos como dados já carregados não grava pagamentos.
    """
    pagamentos = (
        db.query(VendaPagamento)
        .filter_by(venda_id=venda.id, tenant_id=tenant_id)
        .populate_existing()
        .order_by(VendaPagamento.id)
        .all()
    )
    contas = (
        db.query(ContaReceber)
        .filter_by(venda_id=venda.id, tenant_id=tenant_id)
        .order_by(ContaReceber.id)
        .populate_existing()
        .with_for_update(of=ContaReceber)
        .all()
    )
    set_committed_value(venda, "pagamentos", pagamentos)
    set_committed_value(venda, "contas_receber", contas)
    return snapshot_pagamentos_excedente(db, venda, tenant_id)


def validar_pagamentos_edicao(*, venda, totais, fotografia, dados):
    """Só uma edição que cria ou aumenta excesso exige uma nova exceção."""
    anterior = moeda(venda.total)
    novo = moeda(totais["total"])
    pago = fotografia["total_ja_pago"]
    plano = fotografia["crediario_pendente"]
    reduz = novo < anterior
    if reduz and plano > ZERO and novo < pago + plano:
        raise HTTPException(
            409,
            "A redução do total deixaria o crediário desajustado. Revise as parcelas pelo fluxo normal antes de editar a venda.",
        )
    excesso_antes = max(pago - anterior, ZERO)
    excesso_depois = max(pago - novo, ZERO)
    if excesso_depois <= excesso_antes:
        return None
    if fotografia["creditos_utilizados"] > novo:
        raise HTTPException(
            409,
            "A redução do total deixaria créditos ou cashback acima do valor aplicável. Revise esses benefícios pelo fluxo normal antes de editar a venda.",
        )
    return validar_excesso_pagamento(
        total_venda=novo,
        total_ja_pago=pago,
        total_novos_pagamentos=ZERO,
        crediario_pendente=plano,
        justificativa=getattr(dados, "justificativa_pagamento_excedente", None),
        contexto=getattr(dados, "contexto_pagamento_excedente", None),
    )


def metadados_edicao_excedente(*, venda, totais, fotografia):
    return {
        "antes": {
            "total": float(moeda(venda.total)),
            "desconto_valor": float(moeda(venda.desconto_valor)),
        },
        "depois": {
            "total": float(moeda(totais["total"])),
            "desconto_valor": float(moeda(totais["desconto_valor"])),
        },
        "recebido_monetario": float(fotografia["recebido_monetario"]),
        "creditos_utilizados": float(fotografia["creditos_utilizados"]),
        "crediario_pendente": float(fotografia["crediario_pendente"]),
        "formas_pagamento": fotografia["formas_pagamento"],
    }
