from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock
from uuid import uuid4

import pytest
from fastapi import HTTPException

from app.financeiro_models import ContaReceber, LancamentoManual
from app.models import Cliente
from app.vendas.devolucoes_routes import _validar_saldo_devolucao, registrar_devolucao
from app.vendas.edicao_estoque import calcular_diferencas_estoque_edicao
from app.vendas_models import Venda, VendaItem


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


def test_credito_devolucao_aceita_cliente_criado_por_outro_funcionario(monkeypatch):
    tenant_id = uuid4()
    atendente = SimpleNamespace(id=22, nome="Atendente")
    cliente = SimpleNamespace(id=47, user_id=11, nome="Cliente", credito=Decimal("0"))
    venda = SimpleNamespace(
        id=8,
        cliente_id=cliente.id,
        numero_venda="VEN-8",
        total=Decimal("100"),
        observacoes="",
        status="finalizada",
    )
    item = SimpleNamespace(
        id=3,
        produto_id=None,
        produto=None,
        quantidade=1,
        preco_unitario=Decimal("59.89"),
        servico_descricao="Item devolvido",
    )
    consultas = {}
    for modelo, resultado in (
        (Venda, venda),
        (VendaItem, [item]),
        (Cliente, cliente),
        (ContaReceber, []),
        (LancamentoManual, []),
    ):
        consulta = MagicMock()
        consulta.filter.return_value = consulta
        consulta.filter_by.return_value = consulta
        consulta.with_for_update.return_value = consulta
        consulta.first.return_value = resultado
        consulta.all.return_value = resultado if isinstance(resultado, list) else []
        consultas[modelo] = consulta

    db = MagicMock()
    db.query.side_effect = lambda modelo: consultas[modelo]
    monkeypatch.setattr(
        "app.vendas.devolucoes_routes.log_action", lambda **_kwargs: None
    )

    resultado = registrar_devolucao(
        venda_id=venda.id,
        dados={
            "itens": [{"item_id": item.id, "quantidade": 1}],
            "motivo": "Tamanho errado",
            "gerar_credito": True,
        },
        db=db,
        user_and_tenant=(atendente, tenant_id),
    )

    consultas[Cliente].filter_by.assert_called_once_with(
        id=cliente.id, tenant_id=tenant_id
    )
    assert cliente.credito == Decimal("59.89")
    assert resultado["credito_cliente"] == 59.89
    db.commit.assert_called_once()


def test_edicao_calcula_estorno_do_removido_e_baixa_do_adicionado():
    itens_antigos = [SimpleNamespace(produto_id=10, quantidade=Decimal("1"))]
    itens_novos = [SimpleNamespace(produto_id=20, quantidade=Decimal("1"))]

    diferencas = calcular_diferencas_estoque_edicao(itens_antigos, itens_novos)

    assert diferencas == {10: -1, 20: 1}
