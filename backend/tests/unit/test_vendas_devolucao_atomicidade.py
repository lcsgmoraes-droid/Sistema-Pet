from decimal import Decimal
from contextlib import contextmanager, nullcontext
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock
from uuid import uuid4

import pytest
from fastapi import HTTPException

from app.financeiro_models import CategoriaFinanceira, ContaReceber, LancamentoManual
from app.models import Cliente
from app.produtos_models import EstoqueMovimentacao, Produto
from app.vendas.devolucoes_routes import (
    _recebivel_exige_conciliacao,
    _validar_estoque_devolucao_seguro,
    _validar_saldo_devolucao,
    prever_devolucao,
    registrar_devolucao,
)
from app.vendas_devolucoes_models import VendaDevolucao
from app.vendas.edicao_estoque import calcular_diferencas_estoque_edicao
from app.vendas_models import Venda, VendaItem

ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture
def preflight_beneficios_mock(monkeypatch):
    """Testes de estoque/recebiveis isolam as regras de campanhas."""
    monkeypatch.setattr(
        "app.campaigns.sale_return_service.preflight_purchase_benefits_on_return",
        lambda *_args, **_kwargs: None,
    )


def _comprovante_custo(item, venda_id, tenant_estoque, custo_total):
    return {
        "versao": 1,
        "origem": "baixa_estoque_venda",
        "venda_id": venda_id,
        "venda_item_id": item.id,
        "produto_id": item.produto_id,
        "tenant_estoque_id": str(tenant_estoque),
        "movimentacao_id": 91,
        "quantidade": str(item.quantidade),
        "custo_total": str(custo_total),
    }


def test_credito_sem_cliente_e_validado_antes_de_movimentar_estoque():
    source = (ROOT / "app" / "vendas" / "devolucoes_routes.py").read_text(
        encoding="utf-8"
    )

    prevalidacao = source.index("if gerar_credito and not venda.cliente_id:")
    processamento = source.index("for indice, item_dev in enumerate(itens_devolucao):")

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


@pytest.mark.parametrize("operacao", [prever_devolucao, registrar_devolucao])
@pytest.mark.parametrize("forma", ["Cashback", "Crédito Cliente", "credito_cliente"])
def test_pagamento_com_beneficio_exige_conciliacao_da_forma_original(operacao, forma):
    tenant_id = uuid4()
    venda = SimpleNamespace(
        id=8,
        status="finalizada",
        pagamentos=[SimpleNamespace(tenant_id=tenant_id, forma_pagamento=forma)],
    )
    consulta_venda = MagicMock()
    consulta_venda.filter_by.return_value.first.return_value = venda
    consulta_venda.filter_by.return_value.with_for_update.return_value.first.return_value = venda
    consulta_evento = MagicMock()
    consulta_evento.filter.return_value.first.return_value = None
    db = MagicMock()
    db.query.side_effect = lambda modelo: (
        consulta_venda if modelo is Venda else consulta_evento
    )

    with pytest.raises(HTTPException) as erro:
        operacao(
            venda_id=8,
            dados={
                "itens": [{"item_id": 3, "quantidade": 1}],
                "motivo": "Teste",
                "chave_operacao": str(uuid4()),
            },
            db=db,
            user_and_tenant=(SimpleNamespace(id=1), tenant_id),
        )

    assert erro.value.status_code == 409
    assert "forma original" in erro.value.detail
    db.add.assert_not_called()
    db.commit.assert_not_called()


@pytest.mark.parametrize("regra_legada", [True, False])
def test_previa_exibe_409_de_regra_legada_antes_da_confirmacao(
    monkeypatch, regra_legada
):
    tenant_id = uuid4()
    venda = SimpleNamespace(
        id=8,
        cliente_id=47,
        status="finalizada",
        total=Decimal("100"),
        pagamentos=[],
    )
    item = SimpleNamespace(id=3)
    consultas = {}
    for modelo, resultado in (
        (Venda, venda),
        (VendaItem, [item]),
        (VendaDevolucao, []),
    ):
        consulta = MagicMock()
        consulta.filter_by.return_value = consulta
        consulta.filter.return_value = consulta
        consulta.first.return_value = resultado
        consulta.all.return_value = resultado if isinstance(resultado, list) else []
        consultas[modelo] = consulta
    db = MagicMock()
    db.query.side_effect = lambda modelo: consultas[modelo]
    monkeypatch.setattr(
        "app.vendas.devolucoes_routes.cotar_devolucao",
        lambda *_args: SimpleNamespace(
            valor_total=Decimal("50"),
            valor_ja_devolvido=Decimal("0"),
            valor_acumulado=Decimal("50"),
            valores_itens=[Decimal("50")],
        ),
    )
    monkeypatch.setattr(
        "app.vendas.devolucoes_routes._validar_recebiveis_liquidados",
        lambda *_args: None,
    )
    monkeypatch.setattr(
        "app.vendas.devolucoes_routes._validar_estoque_devolucao_seguro",
        lambda *_args: None,
    )
    chamadas = []

    def preflight(_db, *, tenant_id, venda, valor_acumulado):
        chamadas.append((tenant_id, venda.id, valor_acumulado))
        if regra_legada:
            raise HTTPException(
                status_code=409,
                detail="Passo historico do cartao fidelidade nao comprovado",
            )

    monkeypatch.setattr(
        "app.campaigns.sale_return_service.preflight_purchase_benefits_on_return",
        preflight,
    )

    if regra_legada:
        with pytest.raises(HTTPException) as erro:
            prever_devolucao(
                venda_id=8,
                dados={"itens": [{"item_id": 3, "quantidade": 1}]},
                db=db,
                user_and_tenant=(SimpleNamespace(id=1), tenant_id),
            )
        assert erro.value.status_code == 409
        assert "historico" in erro.value.detail
    else:
        previa = prever_devolucao(
            venda_id=8,
            dados={"itens": [{"item_id": 3, "quantidade": 1}]},
            db=db,
            user_and_tenant=(SimpleNamespace(id=1), tenant_id),
        )
        assert previa["valor_total_devolucao"] == 50.0
    assert chamadas == [(tenant_id, 8, Decimal("50"))]
    db.add.assert_not_called()
    db.commit.assert_not_called()


def test_devolucao_repetida_de_servico_usa_saldo_dos_eventos():
    tenant_id = uuid4()
    item = SimpleNamespace(
        id=3, produto_id=None, quantidade=Decimal("2"), subtotal=Decimal("100")
    )
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
        consulta.populate_existing.return_value = consulta
        consulta.first.return_value = None if modelo is VendaDevolucao else resultado
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
                "chave_operacao": str(uuid4()),
            },
            db=db,
            user_and_tenant=(SimpleNamespace(id=22), tenant_id),
        )

    assert erro.value.status_code == 400
    assert "Quantidade devolvida fora do saldo vendido" in erro.value.detail
    db.add.assert_not_called()


def test_credito_devolucao_aceita_cliente_criado_por_outro_funcionario(monkeypatch):
    monkeypatch.setattr(
        "app.campaigns.sale_return_service.reconcile_purchase_benefits_on_return",
        lambda *_args, **_kwargs: None,
    )
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
        subtotal=Decimal("59.89"),
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
        consulta.populate_existing.return_value = consulta
        consulta.first.return_value = None if modelo is VendaDevolucao else resultado
        consulta.all.return_value = resultado if isinstance(resultado, list) else []
        consultas[modelo] = consulta

    db = MagicMock()
    db.query.side_effect = lambda modelo: consultas[modelo]
    monkeypatch.setattr(
        "app.vendas.devolucoes_routes.log_action", lambda **_kwargs: None
    )

    dados = {
        "itens": [{"item_id": item.id, "quantidade": 1}],
        "motivo": "Tamanho errado",
        "gerar_credito": True,
        "chave_operacao": str(uuid4()),
    }
    resultado = registrar_devolucao(
        venda_id=venda.id,
        dados=dados,
        db=db,
        user_and_tenant=(atendente, tenant_id),
    )

    consultas[Cliente].filter_by.assert_called_once_with(
        id=cliente.id, tenant_id=tenant_id
    )
    consultas[Cliente].populate_existing.assert_called_once()
    consultas[Cliente].with_for_update.assert_called_once()
    assert cliente.credito == Decimal("59.89")
    assert resultado["credito_cliente"] == 59.89
    assert resultado["status_venda"] == "devolvida_total"
    evento = next(
        call.args[0]
        for call in db.add.call_args_list
        if isinstance(call.args[0], VendaDevolucao)
    )
    assert evento.valor_devolvido == Decimal("59.89")
    assert evento.status_original_venda == "finalizada"
    assert evento.forma_estorno == "credito"
    assert evento.custo_pendente is False
    db.commit.assert_called_once()

    consultas[VendaDevolucao].first.return_value = evento
    operacoes_gravadas = db.add.call_count
    repeticao = registrar_devolucao(
        venda_id=venda.id,
        dados=dados,
        db=db,
        user_and_tenant=(atendente, tenant_id),
    )
    assert repeticao == resultado
    assert cliente.credito == Decimal("59.89")
    assert db.add.call_count == operacoes_gravadas
    db.commit.assert_called_once()

    with pytest.raises(HTTPException) as erro:
        registrar_devolucao(
            venda_id=venda.id,
            dados={**dados, "motivo": "Outra operacao"},
            db=db,
            user_and_tenant=(atendente, tenant_id),
        )
    assert erro.value.status_code == 409
    assert "dados diferentes" in erro.value.detail
    assert db.add.call_count == operacoes_gravadas


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
        subtotal=Decimal("100"),
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
    conta_quitada = SimpleNamespace(
        status="recebido", valor_final=Decimal("100"), valor_recebido=Decimal("100")
    )
    entrada_realizada = SimpleNamespace(
        status="realizado", valor=Decimal("100"), documento="VENDA-8"
    )
    consultas = {}
    for modelo, resultado in (
        (Venda, venda),
        (VendaItem, [item]),
        (VendaDevolucao, []),
        (CategoriaFinanceira, SimpleNamespace(id=9)),
        (ContaReceber, [conta_quitada]),
        (LancamentoManual, [entrada_realizada]),
    ):
        consulta = MagicMock()
        consulta.filter.return_value = consulta
        consulta.filter_by.return_value = consulta
        consulta.with_for_update.return_value = consulta
        consulta.populate_existing.return_value = consulta
        consulta.order_by.return_value = consulta
        consulta.first.return_value = None if modelo is VendaDevolucao else resultado
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
            "chave_operacao": str(uuid4()),
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
    assert evento.custo_servicos_estornado == Decimal("0")
    assert evento.custo_produtos_estornado == 0
    assert evento.itens[0]["custo_original"] == "0"
    assert evento.itens[0]["custo_estornado"] == "0"
    assert evento.itens[0]["origem_custo"] == "servico_custo_mantido"
    assert evento.movimentacao_caixa_id == 17
    assert evento.custo_pendente is False
    assert resultado["status_venda"] == "finalizada_devolucao"
    assert conta_quitada.status == "recebido"
    assert conta_quitada.valor_final == Decimal("100")
    assert entrada_realizada.status == "realizado"
    assert entrada_realizada.valor == Decimal("100")
    db.commit.assert_called_once()


@pytest.mark.parametrize(
    ("custo_comprovado", "custo_esperado"),
    [(True, Decimal("15.00")), (False, Decimal("0.00"))],
)
def test_entrada_de_estoque_usa_custo_original_ou_zero_provisorio(
    monkeypatch, custo_comprovado, custo_esperado
):
    tenant_id = uuid4()
    atendente = SimpleNamespace(id=22, nome="Atendente")
    cliente = SimpleNamespace(id=47, nome="Cliente", credito=Decimal("0"))
    produto = SimpleNamespace(id=11, nome="Produto", preco_custo=Decimal("99"))
    item = SimpleNamespace(
        id=3,
        produto_id=produto.id,
        produto=produto,
        tipo="produto",
        quantidade=Decimal("2"),
        preco_unitario=Decimal("50"),
        subtotal=Decimal("100"),
    )
    venda = SimpleNamespace(
        id=8,
        cliente_id=cliente.id,
        cliente=cliente,
        numero_venda="VEN-8",
        total=Decimal("100"),
        taxa_entrega=Decimal("0"),
        observacoes="",
        status="finalizada",
        itens=[item],
        rentabilidade_snapshot={
            "snapshot_version": 5,
            "itens": [
                {
                    "produto_id": produto.id,
                    "quantidade": 2,
                    "preco_unitario": 50,
                    "custo_total": 30,
                }
            ],
        },
    )
    if custo_comprovado:
        item.custo_original_saida = _comprovante_custo(
            item, venda.id, tenant_id, "30.00"
        )
    consultas = {}
    for modelo, resultado in (
        (Venda, venda),
        (VendaItem, [item]),
        (VendaDevolucao, []),
        (Cliente, cliente),
        (ContaReceber, []),
    ):
        consulta = MagicMock()
        consulta.filter.return_value = consulta
        consulta.filter_by.return_value = consulta
        consulta.with_for_update.return_value = consulta
        consulta.populate_existing.return_value = consulta
        consulta.first.return_value = None if modelo is VendaDevolucao else resultado
        consulta.all.return_value = resultado if isinstance(resultado, list) else []
        consultas[modelo] = consulta
    consulta_agregada = MagicMock()
    consulta_agregada.filter.return_value = consulta_agregada
    consulta_agregada.scalar.return_value = 0
    db = MagicMock()
    db.query.side_effect = lambda modelo: consultas.get(modelo, consulta_agregada)

    entradas = []
    monkeypatch.setattr(
        "app.vendas.devolucoes_routes._validar_estoque_devolucao_seguro",
        lambda *_args: None,
    )
    monkeypatch.setattr(
        "app.vendas.devolucoes_routes.resolver_tenant_estoque_item",
        lambda *_args: (tenant_id, False),
    )
    monkeypatch.setattr(
        "app.vendas.devolucoes_routes.contexto_tenant_estoque",
        lambda *_args: nullcontext(tenant_id),
    )
    monkeypatch.setattr(
        "app.vendas.devolucoes_routes.EstoqueService.estornar_estoque",
        lambda **kwargs: entradas.append(kwargs),
    )
    monkeypatch.setattr(
        "app.vendas.devolucoes_routes.log_action", lambda **_kwargs: None
    )
    registrar_devolucao(
        venda_id=venda.id,
        dados={
            "itens": [{"item_id": item.id, "quantidade": 1}],
            "motivo": "Troca",
            "gerar_credito": True,
            "chave_operacao": str(uuid4()),
        },
        db=db,
        user_and_tenant=(atendente, tenant_id),
    )

    evento = next(
        call.args[0]
        for call in db.add.call_args_list
        if isinstance(call.args[0], VendaDevolucao)
    )
    assert produto.preco_custo == Decimal("99")
    assert evento.custo_produtos_estornado == custo_esperado
    assert evento.custo_pendente is (not custo_comprovado)
    assert evento.itens[0]["custo_pendente"] is (not custo_comprovado)
    assert entradas[0]["custo_unitario_override"] == float(custo_esperado)
    assert entradas[0]["valor_total_override"] == float(custo_esperado)
    db.commit.assert_called_once()


def test_servico_de_catalogo_com_produto_id_devolve_sem_movimentar_estoque(
    monkeypatch, preflight_beneficios_mock
):
    monkeypatch.setattr(
        "app.campaigns.sale_return_service.reconcile_purchase_benefits_on_return",
        lambda *_args, **_kwargs: None,
    )
    tenant_id = uuid4()
    atendente = SimpleNamespace(id=22, nome="Atendente")
    cliente = SimpleNamespace(id=47, nome="Cliente", credito=Decimal("0"))
    produto = SimpleNamespace(
        id=11, nome="Banho", tipo_produto="SERVICO", controlar_estoque=False
    )
    item = SimpleNamespace(
        id=3,
        produto_id=produto.id,
        produto=produto,
        tipo="servico",
        quantidade=Decimal("2"),
        preco_unitario=Decimal("50"),
        subtotal=Decimal("100"),
        servico_descricao="Banho",
    )
    venda = SimpleNamespace(
        id=8,
        cliente_id=cliente.id,
        cliente=cliente,
        numero_venda="VEN-8",
        total=Decimal("100"),
        taxa_entrega=Decimal("0"),
        observacoes="",
        status="finalizada",
        itens=[item],
        rentabilidade_snapshot={
            "snapshot_version": 5,
            "itens": [
                {
                    "produto_id": produto.id,
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
        (Cliente, cliente),
        (ContaReceber, []),
    ):
        consulta = MagicMock()
        consulta.filter.return_value = consulta
        consulta.filter_by.return_value = consulta
        consulta.with_for_update.return_value = consulta
        consulta.populate_existing.return_value = consulta
        consulta.first.return_value = None if modelo is VendaDevolucao else resultado
        consulta.all.return_value = resultado if isinstance(resultado, list) else []
        consultas[modelo] = consulta
    db = MagicMock()
    db.query.side_effect = lambda modelo: consultas[modelo]

    def sem_estoque(*_args, **_kwargs):
        raise AssertionError("Serviço não deve acessar estoque")

    monkeypatch.setattr(
        "app.vendas.devolucoes_routes.resolver_tenant_estoque_item", sem_estoque
    )
    monkeypatch.setattr(
        "app.vendas.devolucoes_routes.EstoqueService.estornar_estoque", sem_estoque
    )
    monkeypatch.setattr(
        "app.vendas.devolucoes_routes.log_action", lambda **_kwargs: None
    )
    itens = [{"item_id": item.id, "quantidade": 1}]

    previa = prever_devolucao(
        venda_id=venda.id,
        dados={"itens": itens},
        db=db,
        user_and_tenant=(atendente, tenant_id),
    )
    resultado = registrar_devolucao(
        venda_id=venda.id,
        dados={
            "itens": itens,
            "motivo": "Troca",
            "gerar_credito": True,
            "valor_previsto": previa["valor_total_devolucao"],
            "chave_operacao": str(uuid4()),
        },
        db=db,
        user_and_tenant=(atendente, tenant_id),
    )

    evento = next(
        call.args[0]
        for call in db.add.call_args_list
        if isinstance(call.args[0], VendaDevolucao)
    )
    assert previa["valor_total_devolucao"] == 50
    assert resultado["valor_total_devolucao"] == 50
    assert cliente.credito == Decimal("50")
    assert evento.custo_servicos_estornado == Decimal("0")
    assert evento.custo_produtos_estornado == 0
    assert evento.itens[0]["custo_original"] == "0"
    assert evento.itens[0]["custo_estornado"] == "0"
    db.commit.assert_called_once()


@pytest.mark.parametrize(
    "status,valor_final,valor_recebido",
    [
        ("pendente", "100", "0"),
        ("parcial", "100", "50"),
        ("vencido", "100", "0"),
        ("recebido", "100", "90"),
    ],
)
def test_recebivel_aberto_exige_conciliacao_antes_de_reembolso(
    status, valor_final, valor_recebido
):
    conta = SimpleNamespace(
        status=status,
        valor_final=Decimal(valor_final),
        valor_recebido=Decimal(valor_recebido),
    )

    assert _recebivel_exige_conciliacao(conta) is True


def test_recebivel_quitado_preserva_a_entrada_historica():
    conta = SimpleNamespace(
        status="recebido",
        valor_final=Decimal("100"),
        valor_recebido=Decimal("100"),
    )

    assert _recebivel_exige_conciliacao(conta) is False


@pytest.mark.parametrize("operacao", [prever_devolucao, registrar_devolucao])
def test_previa_e_registro_bloqueiam_reembolso_com_recebivel_aberto(
    operacao, preflight_beneficios_mock
):
    tenant_id = uuid4()
    venda = SimpleNamespace(
        id=8,
        cliente_id=47,
        numero_venda="VEN-8",
        total=Decimal("100"),
        status="finalizada",
    )
    item = SimpleNamespace(id=3, produto_id=None, quantidade=1, subtotal=Decimal("100"))
    conta = SimpleNamespace(
        status="pendente", valor_final=Decimal("100"), valor_recebido=Decimal("0")
    )
    consultas = {}
    for modelo, resultado in (
        (Venda, venda),
        (VendaItem, [item]),
        (VendaDevolucao, []),
        (ContaReceber, [conta]),
    ):
        consulta = MagicMock()
        consulta.filter.return_value = consulta
        consulta.filter_by.return_value = consulta
        consulta.with_for_update.return_value = consulta
        consulta.populate_existing.return_value = consulta
        consulta.first.return_value = None if modelo is VendaDevolucao else resultado
        consulta.all.return_value = resultado if isinstance(resultado, list) else []
        consultas[modelo] = consulta
    db = MagicMock()
    db.query.side_effect = lambda modelo: consultas[modelo]

    with pytest.raises(HTTPException) as erro:
        operacao(
            venda_id=venda.id,
            dados={
                "itens": [{"item_id": item.id, "quantidade": 1}],
                "motivo": "Teste",
                "gerar_credito": True,
                "chave_operacao": str(uuid4()),
            },
            db=db,
            user_and_tenant=(SimpleNamespace(id=22), tenant_id),
        )

    assert erro.value.status_code == 409
    assert "recebivel em aberto" in erro.value.detail
    db.add.assert_not_called()


@pytest.mark.parametrize(
    "tipo_produto,tipo_kit,lote_id,controlar_estoque,erro_esperado",
    [
        ("KIT", "VIRTUAL", None, True, "KIT virtual"),
        ("SIMPLES", None, 12, True, "item com lote"),
        ("SIMPLES", None, None, False, "nao controla estoque"),
    ],
)
def test_estoque_nao_recompoe_kit_virtual_ou_lote_sem_conciliacao(
    monkeypatch, tipo_produto, tipo_kit, lote_id, controlar_estoque, erro_esperado
):
    item = SimpleNamespace(
        id=3,
        produto_id=11,
        quantidade=1,
        lote_id=lote_id,
        produto=SimpleNamespace(
            tipo_produto=tipo_produto,
            tipo_kit=tipo_kit,
            controlar_estoque=controlar_estoque,
        ),
    )
    monkeypatch.setattr(
        "app.vendas.devolucoes_routes.resolver_tenant_estoque_item",
        lambda *_args: ("estoque", False),
    )
    monkeypatch.setattr(
        "app.vendas.devolucoes_routes._produto_estoque_original",
        lambda _db, item_venda, _tenant: (item_venda.produto, "estoque"),
    )
    db = MagicMock()

    with pytest.raises(HTTPException) as erro:
        _validar_estoque_devolucao_seguro(
            db, 8, "tenant", [item], [{"item_id": 3, "quantidade": 1}]
        )

    assert erro.value.status_code == 409
    assert erro_esperado in erro.value.detail
    db.query.assert_not_called()


@pytest.mark.parametrize(
    "lotes_consumidos,quantidade_saida,tipo_produto,erro_esperado",
    [
        ('[{"lote_id": 12, "quantidade": 1}]', 1, "SIMPLES", "item com lote"),
        (None, 0.5, "SIMPLES", "Saida original"),
        (None, 1, "SIMPLES", None),
        (None, 1, "KIT", None),
    ],
)
def test_estoque_exige_saida_original_sem_fifo_de_lote(
    monkeypatch, lotes_consumidos, quantidade_saida, tipo_produto, erro_esperado
):
    item = SimpleNamespace(
        id=3,
        produto_id=11,
        quantidade=1,
        lote_id=None,
        produto=SimpleNamespace(
            tipo_produto=tipo_produto,
            tipo_kit="FISICO" if tipo_produto == "KIT" else None,
        ),
    )
    saida = SimpleNamespace(
        quantidade=quantidade_saida, lotes_consumidos=lotes_consumidos
    )
    db = MagicMock()
    db.query.return_value.filter.return_value.all.return_value = [saida]
    monkeypatch.setattr(
        "app.vendas.devolucoes_routes.resolver_tenant_estoque_item",
        lambda *_args: ("estoque", False),
    )
    monkeypatch.setattr(
        "app.vendas.devolucoes_routes._produto_estoque_original",
        lambda _db, item_venda, _tenant: (item_venda.produto, "estoque"),
    )
    monkeypatch.setattr(
        "app.vendas.devolucoes_routes.contexto_tenant_estoque",
        lambda *_args: nullcontext("estoque"),
    )

    if erro_esperado:
        with pytest.raises(HTTPException) as erro:
            _validar_estoque_devolucao_seguro(
                db, 8, "tenant", [item], [{"item_id": 3, "quantidade": 1}]
            )
        assert erro.value.status_code == 409
        assert erro_esperado in erro.value.detail
    else:
        _validar_estoque_devolucao_seguro(
            db, 8, "tenant", [item], [{"item_id": 3, "quantidade": 1}]
        )


def test_previa_e_registro_aceitam_produto_de_estoque_compartilhado(monkeypatch):
    tenant_venda = uuid4()
    tenant_estoque = uuid4()
    usuario = SimpleNamespace(id=22, nome="Atendente")
    produto = SimpleNamespace(
        id=11,
        nome="Produto do grupo",
        controlar_estoque=True,
        tipo_produto="SIMPLES",
    )
    item = SimpleNamespace(
        id=3,
        produto_id=produto.id,
        produto=None,
        tipo="produto",
        lote_id=None,
        estoque_origem_tenant_id=tenant_estoque,
        quantidade=Decimal("1"),
        preco_unitario=Decimal("50"),
        subtotal=Decimal("50"),
        servico_descricao=None,
    )
    cliente = SimpleNamespace(id=47, nome="Cliente", credito=Decimal("0"))
    venda = SimpleNamespace(
        id=8,
        cliente_id=cliente.id,
        cliente=cliente,
        numero_venda="VEN-8",
        total=Decimal("50"),
        taxa_entrega=Decimal("0"),
        observacoes="",
        status="finalizada",
        itens=[item],
        rentabilidade_snapshot={
            "snapshot_version": 5,
            "itens": [
                {
                    "produto_id": produto.id,
                    "quantidade": 1,
                    "preco_unitario": 50,
                    "custo_total": 15,
                }
            ],
        },
    )
    item.custo_original_saida = _comprovante_custo(
        item, venda.id, tenant_estoque, "15.00"
    )
    consultas = {}
    for modelo, resultado in (
        (Venda, venda),
        (VendaItem, [item]),
        (VendaDevolucao, []),
        (Cliente, cliente),
        (ContaReceber, []),
    ):
        consulta = MagicMock()
        consulta.filter.return_value = consulta
        consulta.filter_by.return_value = consulta
        consulta.with_for_update.return_value = consulta
        consulta.populate_existing.return_value = consulta
        consulta.first.return_value = None if modelo is VendaDevolucao else resultado
        consulta.all.return_value = resultado if isinstance(resultado, list) else []
        consultas[modelo] = consulta

    tenant_ativo = {"valor": None}
    contextos = []

    @contextmanager
    def contexto_estoque(origem, venda_tenant):
        assert str(origem) == str(tenant_estoque)
        assert str(venda_tenant) == str(tenant_venda)
        contextos.append(str(origem))
        tenant_ativo["valor"] = str(origem)
        try:
            yield tenant_estoque
        finally:
            tenant_ativo["valor"] = None

    consulta_produto = MagicMock()
    consulta_produto.filter.return_value = consulta_produto
    consulta_produto.first.side_effect = lambda: (
        produto if tenant_ativo["valor"] == str(tenant_estoque) else None
    )
    consulta_saida = MagicMock()
    consulta_saida.filter.return_value = consulta_saida
    consulta_saida.all.return_value = [
        SimpleNamespace(quantidade=1, lotes_consumidos=None)
    ]
    consulta_agregada = MagicMock()
    consulta_agregada.filter.return_value = consulta_agregada
    consulta_agregada.scalar.return_value = 0
    db = MagicMock()

    def consultar(modelo):
        if modelo is Produto:
            assert tenant_ativo["valor"] == str(tenant_estoque)
            return consulta_produto
        if modelo is EstoqueMovimentacao:
            assert tenant_ativo["valor"] == str(tenant_estoque)
            return consulta_saida
        return consultas.get(modelo, consulta_agregada)

    db.query.side_effect = consultar
    entradas = []
    monkeypatch.setattr(
        "app.vendas.devolucoes_routes.contexto_tenant_estoque", contexto_estoque
    )
    monkeypatch.setattr(
        "app.vendas.devolucoes_routes.EstoqueService.estornar_estoque",
        lambda **kwargs: entradas.append(kwargs) or {"produto_nome": produto.nome},
    )
    monkeypatch.setattr(
        "app.vendas.devolucoes_routes.log_action", lambda **_kwargs: None
    )
    itens = [{"item_id": item.id, "quantidade": 1}]

    previa = prever_devolucao(
        venda_id=venda.id,
        dados={"itens": itens},
        db=db,
        user_and_tenant=(usuario, tenant_venda),
    )
    resultado = registrar_devolucao(
        venda_id=venda.id,
        dados={
            "itens": itens,
            "motivo": "Troca",
            "gerar_credito": True,
            "valor_previsto": previa["valor_total_devolucao"],
            "chave_operacao": str(uuid4()),
        },
        db=db,
        user_and_tenant=(usuario, tenant_venda),
    )

    assert previa["valor_total_devolucao"] == 50
    assert resultado["valor_total_devolucao"] == 50
    assert resultado["itens_devolvidos"][0]["produto_nome"] == produto.nome
    assert cliente.credito == Decimal("50")
    assert entradas[0]["tenant_id"] == tenant_estoque
    assert entradas[0]["user_id"] == 0
    assert entradas[0]["valor_total_override"] == 15.0
    assert item.produto is None
    assert len(consulta_produto.filter.call_args_list) == 2
    for chamada in consulta_produto.filter.call_args_list:
        assert chamada.args[0].right.value == produto.id
        assert str(chamada.args[1].right.value) == str(tenant_estoque)
    assert len(contextos) >= 4


@pytest.mark.parametrize("operacao", [prever_devolucao, registrar_devolucao])
@pytest.mark.parametrize(
    "tipo_produto,tipo_kit,lote_id",
    [("KIT", "VIRTUAL", None), ("SIMPLES", None, 12)],
)
def test_previa_e_registro_bloqueiam_estoque_que_nao_pode_ser_recomposto(
    monkeypatch, operacao, tipo_produto, tipo_kit, lote_id, preflight_beneficios_mock
):
    tenant_id = uuid4()
    venda = SimpleNamespace(
        id=8,
        cliente_id=47,
        numero_venda="VEN-8",
        total=Decimal("100"),
        status="finalizada",
    )
    item = SimpleNamespace(
        id=3,
        produto_id=11,
        produto=SimpleNamespace(tipo_produto=tipo_produto, tipo_kit=tipo_kit),
        lote_id=lote_id,
        quantidade=1,
        subtotal=Decimal("100"),
    )
    consultas = {}
    for modelo, resultado in (
        (Venda, venda),
        (VendaItem, [item]),
        (VendaDevolucao, []),
        (ContaReceber, []),
    ):
        consulta = MagicMock()
        consulta.filter.return_value = consulta
        consulta.filter_by.return_value = consulta
        consulta.with_for_update.return_value = consulta
        consulta.populate_existing.return_value = consulta
        consulta.first.return_value = None if modelo is VendaDevolucao else resultado
        consulta.all.return_value = resultado if isinstance(resultado, list) else []
        consultas[modelo] = consulta
    db = MagicMock()
    db.query.side_effect = lambda modelo: consultas[modelo]
    monkeypatch.setattr(
        "app.vendas.devolucoes_routes.resolver_tenant_estoque_item",
        lambda *_args: ("estoque", False),
    )
    monkeypatch.setattr(
        "app.vendas.devolucoes_routes._produto_estoque_original",
        lambda _db, item_venda, _tenant: (item_venda.produto, "estoque"),
    )

    with pytest.raises(HTTPException) as erro:
        operacao(
            venda_id=venda.id,
            dados={
                "itens": [{"item_id": item.id, "quantidade": 1}],
                "motivo": "Teste",
                "gerar_credito": True,
                "chave_operacao": str(uuid4()),
            },
            db=db,
            user_and_tenant=(SimpleNamespace(id=22), tenant_id),
        )

    assert erro.value.status_code == 409
    db.add.assert_not_called()


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
                "chave_operacao": str(uuid4()),
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
        (ContaReceber, []),
    ):
        consulta = MagicMock()
        consulta.filter.return_value = consulta
        consulta.filter_by.return_value = consulta
        consulta.with_for_update.return_value = consulta
        consulta.populate_existing.return_value = consulta
        consulta.first.return_value = None if modelo is VendaDevolucao else resultado
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
                "chave_operacao": str(uuid4()),
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
        subtotal=Decimal("120"),
        servico_descricao="Serviço",
    )
    evento_anterior = SimpleNamespace(
        valor_devolvido=Decimal("60"),
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
        consulta.populate_existing.return_value = consulta
        consulta.first.return_value = None if modelo is VendaDevolucao else resultado
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
                "chave_operacao": str(uuid4()),
            },
            db=db,
            user_and_tenant=(SimpleNamespace(id=22), tenant_id),
        )

    assert erro.value.status_code == 400
    assert "total pago" in erro.value.detail
    db.add.assert_not_called()
    db.commit.assert_not_called()


@pytest.mark.parametrize("taxa_entrega", [Decimal("0"), Decimal("10")])
def test_devolucoes_parciais_com_desconto_pagam_liquido_e_fecham_venda(
    monkeypatch, preflight_beneficios_mock, taxa_entrega
):
    monkeypatch.setattr(
        "app.campaigns.sale_return_service.reconcile_purchase_benefits_on_return",
        lambda *_args, **_kwargs: None,
    )
    tenant_id = uuid4()
    atendente = SimpleNamespace(id=22, nome="Atendente")
    cliente = SimpleNamespace(id=47, nome="Cliente", credito=Decimal("0"))
    venda = SimpleNamespace(
        id=8,
        cliente_id=cliente.id,
        numero_venda="VEN-8",
        total=Decimal("90") + taxa_entrega,
        taxa_entrega=taxa_entrega,
        observacoes="",
        status="finalizada",
    )
    item = SimpleNamespace(
        id=3,
        tipo="servico",
        produto_id=None,
        produto=None,
        quantidade=2,
        preco_unitario=Decimal("50"),
        subtotal=Decimal("100"),
        servico_descricao="Serviço",
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
        consulta.populate_existing.return_value = consulta
        consulta.first.return_value = None if modelo is VendaDevolucao else resultado
        consulta.all.return_value = resultado if isinstance(resultado, list) else []
        consultas[modelo] = consulta
    db = MagicMock()
    db.query.side_effect = lambda modelo: consultas[modelo]
    monkeypatch.setattr(
        "app.vendas.devolucoes_routes.log_action", lambda **_kwargs: None
    )

    dados = {
        "itens": [{"item_id": 3, "quantidade": 1}],
        "motivo": "Ajuste",
        "gerar_credito": True,
        "chave_operacao": str(uuid4()),
    }
    primeira_previa = prever_devolucao(
        venda_id=8,
        dados=dados,
        db=db,
        user_and_tenant=(atendente, tenant_id),
    )
    assert primeira_previa["valor_total_devolucao"] == 45.0
    dados["valor_previsto"] = primeira_previa["valor_total_devolucao"]
    primeira = registrar_devolucao(
        venda_id=8,
        dados=dados,
        db=db,
        user_and_tenant=(atendente, tenant_id),
    )
    evento_primeiro = next(
        call.args[0]
        for call in db.add.call_args_list
        if isinstance(call.args[0], VendaDevolucao)
    )
    assert primeira["status_venda"] == "finalizada_devolucao"
    assert primeira["valor_total_devolucao"] == 45.0
    assert evento_primeiro.valor_devolvido == Decimal("45.00")
    consultas[VendaDevolucao].all.return_value = [evento_primeiro]

    segunda_previa = prever_devolucao(
        venda_id=8,
        dados=dados,
        db=db,
        user_and_tenant=(atendente, tenant_id),
    )
    assert segunda_previa["valor_total_devolucao"] == 45.0
    assert segunda_previa["valor_acumulado"] == 90.0
    dados["valor_previsto"] = segunda_previa["valor_total_devolucao"]
    dados["chave_operacao"] = str(uuid4())
    segunda = registrar_devolucao(
        venda_id=8,
        dados=dados,
        db=db,
        user_and_tenant=(atendente, tenant_id),
    )

    assert segunda["status_venda"] == "devolvida_total"
    assert segunda["valor_total_devolucao"] == 45.0
    assert "Tipo: Devolução total dos itens" in venda.observacoes
    assert cliente.credito == Decimal("90")
    assert db.commit.call_count == 2


def test_registro_rejeita_valor_diferente_da_previa_antes_do_credito(
    preflight_beneficios_mock,
):
    tenant_id = uuid4()
    venda = SimpleNamespace(
        id=8,
        status="finalizada",
        cliente_id=47,
        numero_venda="VEN-8",
        total=Decimal("90"),
    )
    item = SimpleNamespace(
        id=3,
        tipo="servico",
        produto_id=None,
        quantidade=2,
        preco_unitario=Decimal("50"),
        subtotal=Decimal("100"),
    )
    consultas = {}
    for modelo, resultado in (
        (Venda, venda),
        (VendaItem, [item]),
        (VendaDevolucao, []),
        (ContaReceber, []),
    ):
        consulta = MagicMock()
        consulta.filter.return_value = consulta
        consulta.filter_by.return_value = consulta
        consulta.with_for_update.return_value = consulta
        consulta.populate_existing.return_value = consulta
        consulta.first.return_value = None if modelo is VendaDevolucao else resultado
        consulta.all.return_value = resultado if isinstance(resultado, list) else []
        consultas[modelo] = consulta
    db = MagicMock()
    db.query.side_effect = lambda modelo: consultas[modelo]

    previa = prever_devolucao(
        venda_id=8,
        dados={"itens": [{"item_id": 3, "quantidade": 1}]},
        db=db,
        user_and_tenant=(SimpleNamespace(id=22), tenant_id),
    )
    assert previa["valor_total_devolucao"] == 45.0

    with pytest.raises(HTTPException) as erro:
        registrar_devolucao(
            venda_id=8,
            dados={
                "itens": [{"item_id": 3, "quantidade": 1}],
                "motivo": "Ajuste",
                "gerar_credito": True,
                "valor_previsto": 50,
                "chave_operacao": str(uuid4()),
            },
            db=db,
            user_and_tenant=(SimpleNamespace(id=22), tenant_id),
        )

    assert erro.value.status_code == 409
    db.add.assert_not_called()
    db.commit.assert_not_called()


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
        subtotal=Decimal("20"),
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
        consulta.populate_existing.return_value = consulta
        consulta.first.return_value = None if modelo is VendaDevolucao else resultado
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
                "chave_operacao": str(uuid4()),
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
