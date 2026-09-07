"""Recebiveis da finalizacao, dentro da mesma transacao do pagamento."""

from decimal import Decimal

from app.financeiro import ContasReceberService
from app.financeiro_models import LancamentoManual
from app.vendas_models import VendaPagamento


def criar_recebiveis_dos_novos_pagamentos(
    *, db, venda, tenant_id, user_id, pagamentos_anteriores, valor_ja_baixado=0
):
    """Nunca reapresenta pagamentos antigos, inclusive apos reabertura/desconto.

    O chamador mantem o lock da venda ate o commit. Os IDs anteriores sao lidos
    sob esse lock; a consulta abaixo tambem evita uma relationship em cache.
    Valores ja destinados a contas existentes nao geram outra conta/baixa.
    """
    novos = (
        db.query(VendaPagamento)
        .filter(
            VendaPagamento.tenant_id == tenant_id,
            VendaPagamento.venda_id == venda.id,
            VendaPagamento.id.notin_([p.id for p in pagamentos_anteriores]),
        )
        .order_by(VendaPagamento.id)
        .all()
    )
    absorvido = Decimal(str(valor_ja_baixado))
    pagamentos = []
    for pagamento in novos:
        valor = Decimal(str(pagamento.valor))
        destinado = min(absorvido, valor)
        absorvido -= destinado
        if valor <= destinado:
            continue
        dados = {
            coluna.name: getattr(pagamento, coluna.name)
            for coluna in VendaPagamento.__table__.columns
        }
        dados["valor"] = valor - destinado
        pagamentos.append(dados)
    if not pagamentos:
        return []
    resultado = ContasReceberService.criar_de_venda(
        venda=venda, pagamentos=pagamentos, user_id=user_id, db=db
    )
    return resultado["contas_criadas"]


def cancelar_previsoes_apos_desconto(*, db, venda, tenant_id):
    """Desconto que quita saldo antigo nao representa um novo recebimento."""
    previsoes = (
        db.query(LancamentoManual)
        .filter(
            LancamentoManual.tenant_id == tenant_id,
            LancamentoManual.documento.in_(
                [f"VENDA-{venda.id}", f"VENDA-{venda.id}-SALDO"]
            ),
            LancamentoManual.tipo == "entrada",
            LancamentoManual.status == "previsto",
        )
        .all()
    )
    for previsao in previsoes:
        previsao.status = "cancelado"
