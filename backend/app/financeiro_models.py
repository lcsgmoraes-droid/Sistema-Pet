"""Compatibility facade for finance ORM models.

The concrete model groups live under ``app.financeiro`` so this historic module
can stay small while existing imports such as ``from app.financeiro_models import
ContaReceber`` keep working.
"""

from app.financeiro.models_caixa import (
    ContaBancaria,
    LancamentoManual,
    LancamentoRecorrente,
    MovimentacaoFinanceira,
)
from app.financeiro.models_catalogos import (
    CategoriaFinanceira,
    FormaPagamento,
    TipoDespesa,
)
from app.financeiro.models_conciliacao import (
    ExtratoBancario,
    MovimentacaoBancaria,
    ProvisaoAutomatica,
    RegraConciliacao,
    TemplateAdquirente,
)
from app.financeiro.models_contas import (
    ContaPagar,
    ContaReceber,
    Pagamento,
    Recebimento,
)

__all__ = [
    "CategoriaFinanceira",
    "FormaPagamento",
    "TipoDespesa",
    "ContaPagar",
    "ContaReceber",
    "Pagamento",
    "Recebimento",
    "ContaBancaria",
    "MovimentacaoFinanceira",
    "LancamentoManual",
    "LancamentoRecorrente",
    "ExtratoBancario",
    "MovimentacaoBancaria",
    "RegraConciliacao",
    "ProvisaoAutomatica",
    "TemplateAdquirente",
]
