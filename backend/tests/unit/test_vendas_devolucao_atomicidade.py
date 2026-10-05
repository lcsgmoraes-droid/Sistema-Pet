from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock
from uuid import uuid4

import pytest
from fastapi import HTTPException

from app.financeiro_models import CategoriaFinanceira, ContaReceber, LancamentoManual
from app.models import Cliente
from app.vendas.devolucoes_routes import _validar_saldo_devolucao, registrar_devolucao
from app.vendas_devolucoes_models import VendaDevolucao
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


def test_venda_cancelada_nao_gera_evento_de_devolucao():
    db = MagicMock()
    db.query.return_value.filter_by.return_value.with_for_update.return_value.first.return_value = SimpleNamespace(
        id=8, status="cancelada"
    )

    with pytest.raises(HTTPException) as erro:
        registrar_devolucao(
            venda_id=8,
            dados={"itens": [{"item_id": 3, "quantidade": 1}], "motivo": "Teste"},
            db=db,
            user_and_tenant=(SimpleNamespace(id=1), uuid4()),
        )

    assert erro.value.status_code == 400
    db.add.assert_not_called()
    db.commit.assert_not_called()


def test_devolucao_repetida_de_servico_usa_saldo_dos_eventos():
    tenant_id = uuid4()
    item = SimpleNamespace(id=3, produto_id=None, quantidade=Decimal("2"))
    venda = SimpleNamespace(
        id=8,
        cliente_id=47,
        numero_venda="VEN-8",
        total=Decimal("100"),
        status="finalizada_devolucao",
    )
    evento_anterior = SimpleNamespace(
        itens=[{"venda_item_id": 3, "quantidade": "1.5", "is_componente_kit": False}]
    )
    consultas = {}
    for modelo, resultado in (
        (Venda, venda),
        (VendaItem, [item]),
        (VendaDevolucao, [evento_anterior]),
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

    with pytest.raises(HTTPException) as erro:
        registrar_devolucao(
            venda_id=venda.id,
            dados={
                "itens": [{"item_id": 3, "quantidade": 1}],
                "motivo": "Ajuste",
                "gerar_credito": True,
            },
            db=db,
            user_and_tenant=(SimpleNamespace(id=22), tenant_id),
        )

    assert erro.value.status_code == 400
    assert "saldo deste item" in erro.value.detail
    db.add.assert_not_called()


def test_credito_devolucao_aceita_cliente_criado_por_outro_funcionario(monkeypatch):
    tenant_id = uuid4()
    atendente = SimpleNamespace(id=22, nome="Atendente")
    cliente = SimpleNamespace(id=47, user_id=11, nome="Cliente", credito=Decimal("0"))
    venda = SimpleNamespace(
        id=8,
        cliente_id=cliente.id,
        numero_venda="VEN-8",
        total=Decimal("59.89"),
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
        (VendaDevolucao, []),
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
    assert resultado["status_venda"] == "devolvida_total"
    evento = next(
        call.args[0]
        for call in db.add.call_args_list
        if isinstance(call.args[0], VendaDevolucao)
    )
    assert evento.valor_devolvido == Decimal("59.89")
    assert evento.forma_estorno == "credito"
    assert evento.custo_pendente is True
    db.commit.assert_called_once()


def test_devolucao_parcial_em_dinheiro_registra_deducao_e_custo_servico(monkeypatch):
    tenant_id = uuid4()
    atendente = SimpleNamespace(id=22, nome="Atendente")
    item = SimpleNamespace(
        id=3,
        produto_id=None,
        produto=None,
        tipo="servico",
        quantidade=Decimal("2"),
        preco_unitario=Decimal("50"),
        servico_descricao="Serviço",
        desconto_item=Decimal("0"),
    )
    venda = SimpleNamespace(
        id=8,
        cliente_id=None,
        cliente=None,
        numero_venda="VEN-8",
        total=Decimal("100"),
        observacoes="",
        status="finalizada",
        canal="loja_fisica",
        itens=[item],
        rentabilidade_snapshot={
            "snapshot_version": 5,
            "itens": [
                {
                    "produto_id": None,
                    "quantidade": 2,
                    "preco_unitario": 50,
                    "custo_total": 30,
                }
            ],
        },
    )
    consultas = {}
    for modelo, resultado in (
        (Venda, venda),
        (VendaItem, [item]),
        (VendaDevolucao, []),
        (CategoriaFinanceira, SimpleNamespace(id=9)),
        (ContaReceber, []),
        (LancamentoManual, []),
    ):
        consulta = MagicMock()
        consulta.filter.return_value = consulta
        consulta.filter_by.return_value = consulta
        consulta.with_for_update.return_value = consulta
        consulta.order_by.return_value = consulta
        consulta.first.return_value = resultado
        consulta.all.return_value = resultado if isinstance(resultado, list) else []
        consultas[modelo] = consulta
    db = MagicMock()
    db.query.side_effect = lambda modelo: consultas[modelo]
    monkeypatch.setattr(
        "app.vendas.devolucoes_routes.log_action", lambda **_kwargs: None
    )
    monkeypatch.setattr(
        "app.vendas.devolucoes_routes.buscar_caixa_acessivel",
        lambda *_args, **_kwargs: (SimpleNamespace(status="aberto"), None),
    )
    monkeypatch.setattr(
        "app.vendas.devolucoes_routes.CaixaService.registrar_devolucao",
        lambda **_kwargs: {"movimentacao_id": 17},
    )

    resultado = registrar_devolucao(
        venda_id=venda.id,
        dados={
            "caixa_id": 1,
            "itens": [{"item_id": item.id, "quantidade": 1}],
            "motivo": "Ajuste",
            "gerar_credito": False,
        },
        db=db,
        user_and_tenant=(atendente, tenant_id),
    )

    evento = next(
        call.args[0]
        for call in db.add.call_args_list
        if isinstance(call.args[0], VendaDevolucao)
    )
    assert evento.valor_devolvido == Decimal("50.00")
    assert evento.custo_servicos_estornado == Decimal("15.00")
    assert evento.custo_produtos_estornado == 0
    assert evento.movimentacao_caixa_id == 17
    assert evento.custo_pendente is False
    assert resultado["status_venda"] == "finalizada_devolucao"
    db.commit.assert_called_once()


@pytest.mark.parametrize("preco_unitario,quantidade", [(20, 1), (1000, 99)])
def test_componente_de_kit_sem_preco_original_comprovado_nao_gera_credito(
    preco_unitario, quantidade
):
    db = MagicMock()
    db.query.return_value.filter_by.return_value.with_for_update.return_value.first.return_value = SimpleNamespace(
        id=8,
        status="finalizada",
        cliente_id=47,
        numero_venda="VEN-8",
        total=Decimal("20"),
    )

    with pytest.raises(HTTPException) as erro:
        registrar_devolucao(
            venda_id=8,
            dados={
                "itens": [
                    {
                        "is_componente_kit": True,
                        "kit_item_id": 3,
                        "produto_id": 11,
                        "quantidade": quantidade,
                        "preco_unitario": preco_unitario,
                    }
                ],
                "motivo": "Componente devolvido",
                "gerar_credito": True,
            },
            db=db,
            user_and_tenant=(SimpleNamespace(id=22), uuid4()),
        )

    assert erro.value.status_code == 400
    assert "preço original" in erro.value.detail
    db.add.assert_not_called()
    db.commit.assert_not_called()


@pytest.mark.parametrize("tipo,produto_id", [("servico", None), ("produto", 11)])
def test_venda_com_devolucao_historica_sem_valor_rastreavel_e_bloqueada(
    tipo, produto_id
):
    tenant_id = uuid4()
    venda = SimpleNamespace(
        id=8,
        status="finalizada_devolucao",
        cliente_id=47,
        numero_venda="VEN-8",
        total=Decimal("100"),
    )
    item = SimpleNamespace(id=3, tipo=tipo, produto_id=produto_id, quantidade=2)
    consultas = {}
    for modelo, resultado in (
        (Venda, venda),
        (VendaItem, [item]),
        (VendaDevolucao, []),
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

    with pytest.raises(HTTPException) as erro:
        registrar_devolucao(
            venda_id=venda.id,
            dados={
                "itens": [{"item_id": item.id, "quantidade": 1}],
                "motivo": "Ajuste",
                "gerar_credito": True,
            },
            db=db,
            user_and_tenant=(SimpleNamespace(id=22), tenant_id),
        )

    assert erro.value.status_code == 400
    assert "Concilie manualmente" in erro.value.detail
    db.add.assert_not_called()
    db.commit.assert_not_called()


def test_valor_acumulado_das_devolucoes_nao_excede_total_pago():
    tenant_id = uuid4()
    venda = SimpleNamespace(
        id=8,
        status="finalizada_devolucao",
        cliente_id=47,
        numero_venda="VEN-8",
        total=Decimal("100"),
    )
    item = SimpleNamespace(
        id=3,
        tipo="servico",
        produto_id=None,
        produto=None,
        quantidade=2,
        preco_unitario=Decimal("60"),
        servico_descricao="Serviço",
    )
    evento_anterior = SimpleNamespace(
        valor_devolvido=Decimal("50"),
        itens=[{"venda_item_id": 3, "quantidade": "1", "is_componente_kit": False}],
    )
    consultas = {}
    for modelo, resultado in (
        (Venda, venda),
        (VendaItem, [item]),
        (VendaDevolucao, [evento_anterior]),
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

    with pytest.raises(HTTPException) as erro:
        registrar_devolucao(
            venda_id=8,
            dados={
                "itens": [{"item_id": 3, "quantidade": 1}],
                "motivo": "Ajuste",
                "gerar_credito": True,
            },
            db=db,
            user_and_tenant=(SimpleNamespace(id=22), tenant_id),
        )

    assert erro.value.status_code == 400
    assert "total pago" in erro.value.detail
    db.add.assert_not_called()
    db.commit.assert_not_called()


def test_devolucoes_parciais_acumuladas_marcam_venda_totalmente_devolvida(monkeypatch):
    tenant_id = uuid4()
    atendente = SimpleNamespace(id=22, nome="Atendente")
    cliente = SimpleNamespace(id=47, nome="Cliente", credito=Decimal("0"))
    venda = SimpleNamespace(
        id=8,
        cliente_id=cliente.id,
        numero_venda="VEN-8",
        total=Decimal("100"),
        observacoes="",
        status="finalizada_devolucao",
    )
    item = SimpleNamespace(
        id=3,
        tipo="servico",
        produto_id=None,
        produto=None,
        quantidade=2,
        preco_unitario=Decimal("50"),
        servico_descricao="Serviço",
    )
    evento_anterior = SimpleNamespace(
        valor_devolvido=Decimal("50"),
        itens=[{"venda_item_id": 3, "quantidade": "1", "is_componente_kit": False}],
    )
    consultas = {}
    for modelo, resultado in (
        (Venda, venda),
        (VendaItem, [item]),
        (VendaDevolucao, [evento_anterior]),
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
        venda_id=8,
        dados={
            "itens": [{"item_id": 3, "quantidade": 1}],
            "motivo": "Ajuste",
            "gerar_credito": True,
        },
        db=db,
        user_and_tenant=(atendente, tenant_id),
    )

    assert resultado["status_venda"] == "devolvida_total"
    assert resultado["valor_total_devolucao"] == 50.0
    assert cliente.credito == Decimal("50")
    db.commit.assert_called_once()


def test_falha_ao_gravar_evento_impede_credito_ao_cliente():
    tenant_id = uuid4()
    atendente = SimpleNamespace(id=22, nome="Atendente")
    cliente = SimpleNamespace(id=47, user_id=11, nome="Cliente", credito=Decimal("0"))
    venda = SimpleNamespace(
        id=8,
        cliente_id=cliente.id,
        numero_venda="VEN-8",
        total=Decimal("20"),
        observacoes="",
        status="finalizada",
    )
    item = SimpleNamespace(
        id=3,
        produto_id=None,
        produto=None,
        quantidade=1,
        preco_unitario=Decimal("20"),
        servico_descricao="Serviço",
    )
    consultas = {}
    for modelo, resultado in (
        (Venda, venda),
        (VendaItem, [item]),
        (VendaDevolucao, []),
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
    db.flush.side_effect = RuntimeError("falha no evento")

    with pytest.raises(HTTPException) as erro:
        registrar_devolucao(
            venda_id=venda.id,
            dados={
                "itens": [{"item_id": item.id, "quantidade": 1}],
                "motivo": "Ajuste",
                "gerar_credito": True,
            },
            db=db,
            user_and_tenant=(atendente, tenant_id),
        )

    assert erro.value.status_code == 500
    assert cliente.credito == 0
    db.rollback.assert_called_once()
    db.commit.assert_not_called()


def test_edicao_calcula_estorno_do_removido_e_baixa_do_adicionado():
    itens_antigos = [SimpleNamespace(produto_id=10, quantidade=Decimal("1"))]
    itens_novos = [SimpleNamespace(produto_id=20, quantidade=Decimal("1"))]

    diferencas = calcular_diferencas_estoque_edicao(itens_antigos, itens_novos)

    assert diferencas == {10: -1, 20: 1}
