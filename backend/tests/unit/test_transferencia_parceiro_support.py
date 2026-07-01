from types import SimpleNamespace

import os

os.environ["DATABASE_URL"] = os.environ.get("DATABASE_URL") or "sqlite:///./test.db"
os.environ["DEBUG"] = "false"

from app.estoque.transferencia_parceiro_support import (
    _detectar_modo_baixa_transferencia,
    _origem_conta_pagar_compensacao,
)


def test_origem_conta_pagar_compensacao_identifica_entradas_e_acertos():
    assert _origem_conta_pagar_compensacao(
        SimpleNamespace(canal="transferencia_parceiro_entrada")
    ) == ("entrada_parceiro", "Entrada do parceiro")
    assert _origem_conta_pagar_compensacao(
        SimpleNamespace(canal="transferencia_parceiro")
    ) == ("acerto_direto", "Acerto direto")
    assert _origem_conta_pagar_compensacao(SimpleNamespace(canal="compras")) == (
        "financeiro",
        "Financeiro",
    )


def test_detectar_modo_baixa_identifica_produto_devolvido_sem_recebimento():
    assert _detectar_modo_baixa_transferencia(
        None,
        observacoes_conta="Produto devolvido 01/07/2026: R$ 100.00",
    ) == ("produto_devolvido", "Produto devolvido")
