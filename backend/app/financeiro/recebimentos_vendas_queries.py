"""Fontes comprovadas dos recebimentos comerciais, sem somar seus espelhos."""

from sqlalchemy import String, and_, cast, func, literal, or_

from app.conciliacao_recebimento_models import ConciliacaoRecebimento
from app.financeiro_models import (
    ContaReceber,
    FormaPagamento,
    LancamentoManual,
    Recebimento,
)
from app.models import Cliente
from app.vendas_models import Venda


def _venda_valida(tenant_id, canal):
    filtros = [
        Venda.tenant_id == tenant_id,
        or_(Venda.status.is_(None), Venda.status != "cancelada"),
    ]
    if canal:
        filtros.append(Venda.canal == canal)
    return filtros


def _contexto_conta(query, tenant_id, forma_id):
    return (
        query.join(
            Venda, and_(Venda.id == ContaReceber.venda_id, Venda.tenant_id == tenant_id)
        )
        .outerjoin(
            Cliente,
            and_(Cliente.id == Venda.cliente_id, Cliente.tenant_id == tenant_id),
        )
        .outerjoin(
            FormaPagamento,
            and_(FormaPagamento.id == forma_id, FormaPagamento.tenant_id == tenant_id),
        )
    )


def carregar_fontes_recebimentos(db, tenant_id, inicio, fim, canal=None):
    """Datas inclusivas. Todos os vínculos são limitados à empresa autenticada."""
    conciliacao_confirmada = (
        db.query(ConciliacaoRecebimento.id)
        .filter(
            ConciliacaoRecebimento.tenant_id == tenant_id,
            ConciliacaoRecebimento.id == ContaReceber.conciliacao_recebimento_id,
            ConciliacaoRecebimento.venda_id == ContaReceber.venda_id,
            ConciliacaoRecebimento.validado.is_(True),
            ConciliacaoRecebimento.amarrado.is_(True),
        )
        .exists()
    )
    campos = (
        ContaReceber,
        Venda,
        Cliente.nome,
        FormaPagamento.nome,
        FormaPagamento.tipo,
    )
    baixas = (
        _contexto_conta(
            db.query(Recebimento, *campos).join(
                ContaReceber,
                and_(
                    ContaReceber.id == Recebimento.conta_receber_id,
                    ContaReceber.tenant_id == tenant_id,
                ),
            ),
            tenant_id,
            func.coalesce(
                Recebimento.forma_pagamento_id, ContaReceber.forma_pagamento_id
            ),
        )
        .filter(
            Recebimento.tenant_id == tenant_id,
            Recebimento.data_recebimento >= inicio,
            Recebimento.data_recebimento <= fim,
            ~conciliacao_confirmada,
            *_venda_valida(tenant_id, canal),
        )
        .all()
    )

    # Algumas importações antigas/conciliações guardam a baixa somente na conta.
    # Só há fallback quando não existe NENHUMA baixa individual, em qualquer mês.
    tem_baixa = (
        db.query(Recebimento.id)
        .filter(
            Recebimento.tenant_id == tenant_id,
            Recebimento.conta_receber_id == ContaReceber.id,
        )
        .exists()
    )
    data_conta = func.coalesce(
        ContaReceber.data_liquidacao, ContaReceber.data_recebimento
    )
    contas = (
        _contexto_conta(
            db.query(*campos).select_from(ContaReceber),
            tenant_id,
            ContaReceber.forma_pagamento_id,
        )
        .filter(
            ContaReceber.tenant_id == tenant_id,
            ContaReceber.valor_recebido > 0,
            ContaReceber.status.in_(["recebido", "pago", "parcial", "estornada"]),
            data_conta >= inicio,
            data_conta <= fim,
            ~tem_baixa,
            ~conciliacao_confirmada,
            *_venda_valida(tenant_id, canal),
        )
        .all()
    )

    conciliacoes = (
        db.query(ConciliacaoRecebimento, Venda, Cliente.nome)
        .join(
            Venda,
            and_(
                Venda.id == ConciliacaoRecebimento.venda_id,
                Venda.tenant_id == tenant_id,
            ),
        )
        .outerjoin(
            Cliente,
            and_(Cliente.id == Venda.cliente_id, Cliente.tenant_id == tenant_id),
        )
        .filter(
            ConciliacaoRecebimento.tenant_id == tenant_id,
            ConciliacaoRecebimento.validado.is_(True),
            ConciliacaoRecebimento.amarrado.is_(True),
            ConciliacaoRecebimento.data_recebimento >= inicio,
            ConciliacaoRecebimento.data_recebimento <= fim,
            *_venda_valida(tenant_id, canal),
        )
        .all()
    )
    # O fluxo oficial registra DEVOLUCAO apenas para dinheiro devolvido.
    # Crédito gerado para uso futuro não produz essa saída.
    devolucoes = (
        db.query(LancamentoManual, Venda, Cliente.nome)
        .join(
            Venda,
            and_(
                LancamentoManual.documento
                == literal("DEVOLUCAO-") + cast(Venda.id, String),
                Venda.tenant_id == tenant_id,
            ),
        )
        .outerjoin(
            Cliente,
            and_(Cliente.id == Venda.cliente_id, Cliente.tenant_id == tenant_id),
        )
        .filter(
            LancamentoManual.tenant_id == tenant_id,
            LancamentoManual.tipo == "saida",
            LancamentoManual.status == "realizado",
            LancamentoManual.data_lancamento >= inicio,
            LancamentoManual.data_lancamento <= fim,
            *_venda_valida(tenant_id, canal),
        )
        .all()
    )
    return baixas, contas, conciliacoes, devolucoes
