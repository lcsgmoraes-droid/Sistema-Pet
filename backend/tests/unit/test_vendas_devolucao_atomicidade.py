from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from app.vendas.devolucoes_routes import _validar_saldo_devolucao
from app.vendas.edicao_estoque import calcular_diferencas_estoque_edicao


ROOT = Path(__file__).resolve().parents[2]


def test_credito_sem_cliente_e_validado_antes_de_movimentar_estoque():
    source = (ROOT / "app" / "vendas" / "devolucoes_routes.py").read_text(
        encoding="utf-8"
    )

    prevalidacao = source.index("if gerar_credito and not venda.cliente_id:")
    processamento = source.index("for item_dev in itens_devolucao:")

    assert prevalidacao < processamento


def test_erros_de_devolucao_desfazem_a_transacao_e_auditoria_nao_commita_no_meio():
    source = (ROOT / "app" / "vendas" / "devolucoes_routes.py").read_text(
        encoding="utf-8"
    )

    assert "except HTTPException:\n        db.rollback()\n        raise" in source
    assert source.count("commit=False") >= 3


def test_devolucao_repetida_acima_do_saldo_vendido_e_bloqueada():
    with pytest.raises(HTTPException) as exc:
        _validar_saldo_devolucao(
            quantidade_vendida=1,
            quantidade_ja_devolvida=1,
            quantidade_solicitada=1,
        )

    assert exc.value.status_code == 400
    assert "excede o saldo vendido" in exc.value.detail


def test_edicao_calcula_estorno_do_removido_e_baixa_do_adicionado():
    itens_antigos = [SimpleNamespace(produto_id=10, quantidade=Decimal("1"))]
    itens_novos = [SimpleNamespace(produto_id=20, quantidade=Decimal("1"))]

    diferencas = calcular_diferencas_estoque_edicao(itens_antigos, itens_novos)

    assert diferencas == {10: -1, 20: 1}
