"""Cancelamento comercial restaura o estoque historico, sem repetir o FIFO atual.

SQLite descartavel exercita o servico completo e a atomicidade do estoque e dos
pagamentos. Concorrencia e locks reais sao cobertos no ensaio PostgreSQL.
"""

from copy import deepcopy
from decimal import Decimal
import json
from types import SimpleNamespace
from uuid import uuid4

from fastapi import HTTPException
import pytest
from sqlalchemy.schema import CreateTable
from sqlalchemy.orm.attributes import flag_modified

from app.financeiro_models import ContaReceber
from app.models import User
import app.produto_identidade_models  # noqa: F401 - FK do modelo de produto
from app.produtos_models import EstoqueMovimentacao, Produto, ProdutoLote
from app.tenancy.context import tenant_context
from app.vendas.cancelamento_service import cancelar_venda
from app.vendas.custo_original import registrar_custo_original_saida
from app.vendas_models import Venda, VendaItem, VendaPagamento
from tests.unit.test_cancelamento_pagamentos_caixa import (
    cancelamento,
    cenario,
)

__all__ = ["cancelamento", "cenario"]


@pytest.fixture
def lotes(cancelamento, monkeypatch):
    c = cancelamento
    # A serializacao de protocolos de recorrencia pertence a outro contrato.
    monkeypatch.setattr(
        Venda, "to_dict", lambda self: {"id": self.id, "status": self.status}
    )
    for model in (Produto, ProdutoLote, EstoqueMovimentacao):
        with c.db.bind.begin() as conn:
            conn.execute(
                CreateTable(model.__table__, include_foreign_key_constraints=[])
            )
    monkeypatch.setattr("app.estoque.service._agenda_sync_bling", lambda *a, **kw: None)
    monkeypatch.setattr(
        "app.estoque.service.EstoqueService._ajustar_estoque_canal_online",
        lambda *a, **kw: None,
    )
    c.product = Produto(
        tenant_id=c.tenant,
        user_id=1,
        codigo="227",
        nome="Produto de teste com lotes",
        tipo="produto",
        tipo_produto="SIMPLES",
        ativo=True,
        estoque_atual=20,
        preco_custo=999,
        preco_venda=142.9,
        preco_app=143.9,
        preco_ecommerce=144.9,
        preco_ifood=154.9,
    )
    c.db.add(c.product)
    c.db.flush()
    c.lots = []
    for name, initial, available, cost, status in (
        ("Origem A", 2, 0, 80, "esgotado"),
        ("Origem B", 19, 16, 100, "ativo"),
        ("Entrada posterior C", 4, 4, 999, "ativo"),
    ):
        row = ProdutoLote(
            tenant_id=c.tenant,
            produto_id=c.product.id,
            nome_lote=name,
            quantidade_inicial=initial,
            quantidade_disponivel=available,
            custo_unitario=cost,
            ordem_entrada=len(c.lots) + 1,
            status=status,
        )
        c.db.add(row)
        c.db.flush()
        c.lots.append(row)
    c.items, c.exits = [], []
    return c


def _exit(c, quantity=5, parts=None, cost=460):
    parts = parts or [(c.lots[0], 2), (c.lots[1], 3)]
    item = VendaItem(
        tenant_id=c.tenant,
        venda_id=c.venda.id,
        produto_id=c.product.id,
        tipo="produto",
        quantidade=quantity,
        preco_unitario=20,
        subtotal=quantity * 20,
        lote_id=parts[0][0].id if len(parts) == 1 else None,
    )
    c.db.add(item)
    c.db.flush()
    movement = EstoqueMovimentacao(
        tenant_id=c.tenant,
        user_id=1,
        produto_id=c.product.id,
        tipo="saida",
        motivo="venda",
        quantidade=quantity,
        quantidade_anterior=21,
        quantidade_nova=21 - quantity,
        custo_unitario=cost / quantity,
        valor_total=cost,
        referencia_id=c.venda.id,
        referencia_tipo="venda",
        lote_id=parts[0][0].id if len(parts) == 1 else None,
        lotes_consumidos=json.dumps(
            [{"lote_id": lot.id, "quantidade": qty} for lot, qty in parts]
        ),
    )
    c.db.add(movement)
    c.db.flush()
    assert registrar_custo_original_saida(
        item,
        [
            {
                "produto_id": c.product.id,
                "movimentacao_id": movement.id,
                "quantidade": quantity,
                "valor_total": cost,
            }
        ],
        c.tenant,
    )
    c.items.append(item)
    c.exits.append(movement)
    c.db.commit()
    return item, movement


def _cancel(c):
    return cancelar_venda(c.venda.id, "QA recomposicao original", 1, c.tenant, c.db)


def _entries(c):
    return (
        c.db.query(EstoqueMovimentacao)
        .filter_by(
            tenant_id=c.tenant,
            referencia_id=c.venda.id,
            referencia_tipo="venda",
            tipo="entrada",
        )
        .order_by(EstoqueMovimentacao.id)
        .all()
    )


def _snapshot(c):
    c.db.flush()
    result = {}
    for model in (
        Produto,
        ProdutoLote,
        EstoqueMovimentacao,
        Venda,
        VendaItem,
        VendaPagamento,
        ContaReceber,
    ):
        result[model.__tablename__] = [
            {
                column.key: deepcopy(getattr(row, column.key))
                for column in model.__table__.columns
            }
            for row in c.db.query(model).order_by(model.id)
        ]
    return result


def test_cancelamento_multilote_devolve_origens_e_cmv_sem_usar_custo_atual(lotes):
    c = lotes
    item, movement = _exit(c)
    proof = deepcopy(item.custo_original_saida)

    _cancel(c)

    assert c.product.estoque_atual == 25
    assert [lot.quantidade_disponivel for lot in c.lots] == [2, 19, 4]
    assert [lot.status for lot in c.lots] == ["ativo", "ativo", "ativo"]
    assert c.product.preco_custo == 999
    assert [
        c.product.preco_venda,
        c.product.preco_app,
        c.product.preco_ecommerce,
        c.product.preco_ifood,
    ] == [142.9, 143.9, 144.9, 154.9]
    entries = _entries(c)
    assert len(entries) == 1 and entries[0].quantidade == 5
    assert Decimal(str(entries[0].valor_total)) == Decimal("460")
    assert Decimal(str(entries[0].custo_unitario)) == Decimal("92")
    assert {
        part["lote_id"]: part["quantidade"]
        for part in json.loads(entries[0].lotes_consumidos)
    } == {c.lots[0].id: 2, c.lots[1].id: 3}
    assert all(
        part["venda_item_id"] == item.id
        for part in json.loads(entries[0].lotes_consumidos)
    )
    assert item.custo_original_saida == proof
    assert movement.tipo == "saida" and movement.status != "cancelado"
    assert c.venda.status == "cancelada"


def test_sku_repetido_recompoe_cada_linha_pelo_comprovante_proprio(lotes):
    c = lotes
    first, _ = _exit(c, 2, [(c.lots[0], 2)], 160)
    second, _ = _exit(c, 3, [(c.lots[1], 3)], 300)

    _cancel(c)

    assert c.product.estoque_atual == 25
    assert [lot.quantidade_disponivel for lot in c.lots] == [2, 19, 4]
    entries = _entries(c)
    assert len(entries) == 2
    assert sum(Decimal(str(row.valor_total)) for row in entries) == Decimal("460")
    by_item = {
        json.loads(row.lotes_consumidos)[0]["venda_item_id"]: row for row in entries
    }
    assert json.loads(by_item[first.id].lotes_consumidos)[0]["lote_id"] == c.lots[0].id
    assert json.loads(by_item[second.id].lotes_consumidos)[0]["lote_id"] == c.lots[1].id


def test_cancelamento_repetido_nao_cria_entrada_nem_recompoe_duas_vezes(lotes):
    c = lotes
    _exit(c)
    _cancel(c)
    before = _snapshot(c)
    with pytest.raises(HTTPException) as caught:
        _cancel(c)
    assert caught.value.status_code == 400
    assert _snapshot(c) == before


@pytest.mark.parametrize(
    "field,value",
    [
        ("movimentacao_id", 9999),
        ("venda_item_id", 9999),
        ("produto_id", 9999),
        ("tenant_estoque_id", str(uuid4())),
        ("quantidade", "4"),
        ("custo_total", "NaN"),
    ],
)
def test_prova_contraditoria_rejeita_409_sem_alterar_lotes_nem_financeiro(
    lotes, field, value
):
    c = lotes
    item, _ = _exit(c)
    item.custo_original_saida = {**item.custo_original_saida, field: value}
    flag_modified(item, "custo_original_saida")
    c.db.commit()
    before = _snapshot(c)
    with pytest.raises(HTTPException) as caught:
        _cancel(c)
    assert caught.value.status_code == 409
    assert _snapshot(c) == before


@pytest.mark.parametrize(
    "composition",
    [
        "not-json",
        "{}",
        '[{"lote_id":1,"quantidade":"NaN"}]',
        '[{"lote_id":1,"quantidade":-1}]',
    ],
)
def test_composicao_original_invalida_bloqueia_antes_do_estorno(lotes, composition):
    c = lotes
    _, movement = _exit(c)
    movement.lotes_consumidos = composition
    c.db.commit()
    before = _snapshot(c)
    with pytest.raises(HTTPException) as caught:
        _cancel(c)
    assert caught.value.status_code == 409
    assert _snapshot(c) == before


def test_lote_original_ausente_nao_e_substituido_por_entrada_posterior(lotes):
    c = lotes
    _exit(c)
    c.db.delete(c.lots[0])
    c.db.commit()
    before = _snapshot(c)
    with pytest.raises(HTTPException) as caught:
        _cancel(c)
    assert caught.value.status_code == 409
    assert _snapshot(c) == before


def test_lote_de_outra_empresa_nao_e_recomposto(lotes):
    c = lotes
    _, movement = _exit(c)
    foreign_tenant = uuid4()
    with tenant_context(foreign_tenant):
        foreign = ProdutoLote(
            tenant_id=foreign_tenant,
            produto_id=c.product.id,
            nome_lote="Outra empresa",
            quantidade_inicial=2,
            quantidade_disponivel=0,
            custo_unitario=80,
            ordem_entrada=1,
            status="esgotado",
        )
        c.db.add(foreign)
        c.db.flush()
        foreign_id = foreign.id
        c.db.commit()
    with tenant_context(c.tenant):
        movement.lotes_consumidos = json.dumps(
            [{"lote_id": foreign_id, "quantidade": 5}]
        )
        c.db.commit()
        before = _snapshot(c)
        with pytest.raises(HTTPException) as caught:
            _cancel(c)
        assert caught.value.status_code == 409
        assert _snapshot(c) == before
    with tenant_context(foreign_tenant):
        assert c.db.get(ProdutoLote, foreign_id).quantidade_disponivel == 0


def test_falha_posterior_reverte_recomposicao_entradas_e_pagamentos(lotes, monkeypatch):
    c = lotes
    _exit(c)
    before = _snapshot(c)

    def fail(**kw):
        raise RuntimeError("Falha posterior ao retorno dos lotes")

    monkeypatch.setattr("app.comissoes_estorno.estornar_comissoes_venda", fail)
    with pytest.raises(HTTPException) as caught:
        _cancel(c)
    assert caught.value.status_code == 500
    assert _snapshot(c) == before


@pytest.mark.parametrize("status", ["bloqueado", "vencido"])
def test_recomposicao_preserva_bloqueio_ou_vencimento_do_lote(lotes, status):
    c = lotes
    _exit(c)
    c.lots[0].status = status
    c.db.commit()
    _cancel(c)
    assert c.lots[0].quantidade_disponivel == 2
    assert c.lots[0].status == status


def test_custo_ausente_nao_vira_custo_atual_nem_zero_no_retorno(lotes):
    c = lotes
    item, movement = _exit(c)
    item.custo_original_saida = None
    movement.custo_unitario = 0
    movement.valor_total = 0
    c.db.commit()

    _cancel(c)

    assert c.product.estoque_atual == 25
    assert [lot.quantidade_disponivel for lot in c.lots] == [2, 19, 4]
    entry = _entries(c)[0]
    assert entry.custo_unitario is None and entry.valor_total is None
    assert c.product.preco_custo == 999


def test_zero_comprovado_explicitamente_permanece_zero(lotes):
    c = lotes
    item, movement = _exit(c)
    item.custo_original_saida = {**item.custo_original_saida, "custo_total": "0"}
    movement.custo_unitario = 0
    movement.valor_total = 0
    c.db.commit()

    _cancel(c)

    assert c.product.estoque_atual == 25
    entry = _entries(c)[0]
    assert entry.custo_unitario == 0 and entry.valor_total == 0


def test_saida_legada_inequivoca_preserva_valor_historico_sem_comprovante_json(lotes):
    c = lotes
    item, _ = _exit(c)
    item.custo_original_saida = None
    c.db.commit()

    _cancel(c)

    assert c.product.estoque_atual == 25
    assert [lot.quantidade_disponivel for lot in c.lots] == [2, 19, 4]
    entry = _entries(c)[0]
    assert Decimal(str(entry.valor_total)) == Decimal("460")


def test_legado_sem_lotes_nem_historico_devolve_so_saldo_com_custo_desconhecido(lotes):
    c = lotes
    for lot in c.lots:
        c.db.delete(lot)
    c.items.append(
        VendaItem(
            tenant_id=c.tenant,
            venda_id=c.venda.id,
            produto_id=c.product.id,
            tipo="produto",
            quantidade=1,
            preco_unitario=100,
            subtotal=100,
        )
    )
    c.db.add(c.items[0])
    c.db.commit()

    _cancel(c)

    assert c.product.estoque_atual == 21
    entry = _entries(c)[0]
    assert entry.lote_id is None and entry.lotes_consumidos is None
    assert entry.custo_unitario is None and entry.valor_total is None


def test_retorno_anterior_exige_conciliacao_em_vez_de_devolver_a_mesma_saida(lotes):
    c = lotes
    item, _ = _exit(c)
    c.product.estoque_atual = 21
    c.lots[0].quantidade_disponivel = 1
    c.db.add(
        EstoqueMovimentacao(
            tenant_id=c.tenant,
            user_id=1,
            produto_id=c.product.id,
            tipo="entrada",
            motivo="cancelamento_venda",
            quantidade=1,
            quantidade_anterior=20,
            quantidade_nova=21,
            custo_unitario=80,
            valor_total=80,
            referencia_id=c.venda.id,
            referencia_tipo="venda",
            lotes_consumidos=json.dumps(
                [{"lote_id": c.lots[0].id, "venda_item_id": item.id, "quantidade": 1}]
            ),
        )
    )
    c.db.commit()
    before = _snapshot(c)

    with pytest.raises(HTTPException) as caught:
        _cancel(c)

    assert caught.value.status_code == 409
    assert _snapshot(c) == before


def test_fiscal_bling_ja_estornou_nao_devolve_estoque_ou_lotes_novamente(lotes):
    c = lotes
    item, movement = _exit(c)
    item.custo_original_saida = None
    movement.referencia_tipo = "venda_bling"
    movement.status = "cancelado"
    c.product.estoque_atual = 25
    c.lots[0].quantidade_disponivel = 2
    c.lots[1].quantidade_disponivel = 19
    c.venda.nfe_bling_id = 987
    c.venda.nfe_status = "cancelada"
    c.db.commit()

    before = _snapshot(c)
    with pytest.raises(HTTPException) as caught:
        _cancel(c)
    assert caught.value.status_code == 409
    assert _snapshot(c) == before


def test_fiscal_bling_legado_sem_lotes_preserva_abatimento_do_saldo_ja_devolvido(lotes):
    c = lotes
    item, movement = _exit(c)
    item.custo_original_saida = None
    item.lote_id = None
    movement.referencia_tipo = "venda_bling"
    movement.status = "cancelado"
    movement.lote_id = None
    movement.lotes_consumidos = None
    for lot in c.lots:
        c.db.delete(lot)
    c.product.estoque_atual = 25
    c.venda.nfe_bling_id = 987
    c.venda.nfe_status = "cancelada"
    c.db.commit()

    result = _cancel(c)

    assert c.venda.status == "cancelada"
    assert c.venda.nfe_status == "cancelada"
    assert c.product.estoque_atual == 25
    assert _entries(c) == []
    assert result["estornos"]["itens_estornados"] == 0


def test_cancelamento_estoque_compartilhado_recompoe_somente_empresa_de_origem(lotes):
    c = lotes
    source_tenant = uuid4()
    with tenant_context(source_tenant):
        user = User(
            tenant_id=source_tenant,
            email="origem-estoque@teste.invalid",
            nome="Origem",
            is_active=True,
        )
        c.db.add(user)
        c.db.flush()
        source = Produto(
            tenant_id=source_tenant,
            user_id=user.id,
            codigo="ORIGEM-227",
            nome="Produto origem",
            tipo="produto",
            tipo_produto="SIMPLES",
            estoque_atual=16,
            preco_custo=999,
            preco_venda=200,
            ativo=True,
        )
        c.db.add(source)
        c.db.flush()
        source_lot = ProdutoLote(
            tenant_id=source_tenant,
            produto_id=source.id,
            nome_lote="Lote origem",
            quantidade_inicial=21,
            quantidade_disponivel=16,
            custo_unitario=92,
            ordem_entrada=1,
            status="ativo",
        )
        c.db.add(source_lot)
        c.db.flush()
        movement = EstoqueMovimentacao(
            tenant_id=source_tenant,
            user_id=user.id,
            produto_id=source.id,
            tipo="saida",
            motivo="venda",
            quantidade=5,
            quantidade_anterior=21,
            quantidade_nova=16,
            custo_unitario=92,
            valor_total=460,
            referencia_id=c.venda.id,
            referencia_tipo="venda",
            lote_id=source_lot.id,
            lotes_consumidos=json.dumps([{"lote_id": source_lot.id, "quantidade": 5}]),
        )
        c.db.add(movement)
        c.db.flush()
        c.db.commit()
        source_id, source_lot_id, source_user_id = source.id, source_lot.id, user.id
    with tenant_context(c.tenant):
        item = VendaItem(
            tenant_id=c.tenant,
            venda_id=c.venda.id,
            produto_id=source_id,
            estoque_origem_tenant_id=source_tenant,
            tipo="produto",
            quantidade=5,
            preco_unitario=20,
            subtotal=100,
            lote_id=source_lot_id,
        )
        c.db.add(item)
        c.db.flush()
        assert registrar_custo_original_saida(
            item,
            [
                {
                    "produto_id": source_id,
                    "movimentacao_id": movement.id,
                    "quantidade": 5,
                    "valor_total": 460,
                }
            ],
            source_tenant,
        )
        c.db.commit()
        local_stock = c.product.estoque_atual
        local_lots = [lot.quantidade_disponivel for lot in c.lots]
        _cancel(c)
        assert c.product.estoque_atual == local_stock
        assert [lot.quantidade_disponivel for lot in c.lots] == local_lots
        assert _entries(c) == []
    with tenant_context(source_tenant):
        assert c.db.get(Produto, source_id).estoque_atual == 21
        assert c.db.get(ProdutoLote, source_lot_id).quantidade_disponivel == 21
        entry = (
            c.db.query(EstoqueMovimentacao)
            .filter_by(
                tenant_id=source_tenant,
                produto_id=source_id,
                tipo="entrada",
                referencia_id=c.venda.id,
            )
            .one()
        )
        assert entry.valor_total == 460 and entry.user_id == source_user_id


def test_pedido_online_sem_baixa_nao_cria_entrada_fisica_ao_cancelar(lotes):
    c = lotes
    item = VendaItem(
        tenant_id=c.tenant,
        venda_id=c.venda.id,
        produto_id=c.product.id,
        tipo="produto",
        quantidade=1,
        preco_unitario=100,
        subtotal=100,
    )
    c.db.add(item)
    c.venda.canal = "ecommerce"
    c.venda.status = "aberta"
    c.db.commit()

    _cancel(c)

    assert c.venda.status == "cancelada"
    assert c.product.estoque_atual == 20
    assert [lot.quantidade_disponivel for lot in c.lots] == [0, 16, 4]
    assert _entries(c) == []


def test_sku_repetido_sem_origem_individual_nao_adivinha_quais_lotes_devolver(lotes):
    c = lotes
    first, _ = _exit(c, 2, [(c.lots[0], 1), (c.lots[1], 1)], 180)
    second, _ = _exit(c, 3, [(c.lots[0], 1), (c.lots[1], 2)], 280)
    first.custo_original_saida = second.custo_original_saida = None
    c.db.commit()
    before = _snapshot(c)

    with pytest.raises(HTTPException) as caught:
        _cancel(c)

    assert caught.value.status_code == 409
    assert _snapshot(c) == before


def test_prova_de_apenas_uma_das_linhas_repetidas_exige_conciliacao(lotes):
    c = lotes
    _exit(c, 2, [(c.lots[0], 2)], 160)
    second, _ = _exit(c, 3, [(c.lots[1], 3)], 300)
    second.custo_original_saida = None
    c.db.commit()
    before = _snapshot(c)

    with pytest.raises(HTTPException) as caught:
        _cancel(c)

    assert caught.value.status_code == 409
    assert _snapshot(c) == before


def test_custo_unitario_da_saida_contraditorio_nao_e_reescrito_com_custo_atual(lotes):
    c = lotes
    _, movement = _exit(c)
    movement.custo_unitario = 200
    c.db.commit()
    before = _snapshot(c)

    with pytest.raises(HTTPException) as caught:
        _cancel(c)

    assert caught.value.status_code == 409
    assert _snapshot(c) == before


def test_quantidade_fracionada_e_custo_original_nao_perdem_saldo_no_retorno(lotes):
    c = lotes
    _exit(c, 1.5, [(c.lots[0], 1.5)], 100)

    _cancel(c)

    assert c.product.estoque_atual == 21.5
    assert c.lots[0].quantidade_disponivel == 1.5
    assert c.lots[1].quantidade_disponivel == 16
    entry = _entries(c)[0]
    assert Decimal(str(entry.quantidade)) == Decimal("1.5")
    assert Decimal(str(entry.valor_total)) == Decimal("100")


def test_legado_repetido_com_lote_por_linha_preserva_cada_custo_da_saida(lotes):
    c = lotes
    first, _ = _exit(c, 2, [(c.lots[0], 2)], 160)
    second, _ = _exit(c, 3, [(c.lots[1], 3)], 300)
    first.custo_original_saida = second.custo_original_saida = None
    c.db.commit()

    _cancel(c)

    by_item = {
        json.loads(row.lotes_consumidos)[0]["venda_item_id"]: row for row in _entries(c)
    }
    assert Decimal(str(by_item[first.id].valor_total)) == Decimal("160")
    assert Decimal(str(by_item[second.id].valor_total)) == Decimal("300")
    assert c.product.estoque_atual == 25


def test_legado_repetido_com_custo_individual_ambiguo_nao_inventa_rateio(lotes):
    c = lotes
    first, _ = _exit(c, 1, [(c.lots[0], 1)], 80)
    second, _ = _exit(c, 1, [(c.lots[0], 1)], 100)
    first.custo_original_saida = second.custo_original_saida = None
    c.db.commit()

    _cancel(c)

    assert c.product.estoque_atual == 22
    assert c.lots[0].quantidade_disponivel == 2
    entries = _entries(c)
    assert len(entries) == 2
    assert all(
        row.custo_unitario is None and row.valor_total is None for row in entries
    )


def test_legado_sem_lotes_duas_saidas_mesma_quantidade_custos_distintos_fica_desconhecido(
    lotes,
):
    c = lotes
    first, first_move = _exit(c, 1, [(c.lots[0], 1)], 80)
    second, second_move = _exit(c, 1, [(c.lots[0], 1)], 100)
    for item in (first, second):
        item.custo_original_saida = None
        item.lote_id = None
    for movement in (first_move, second_move):
        movement.lote_id = None
        movement.lotes_consumidos = None
    for lot in c.lots:
        c.db.delete(lot)
    c.db.commit()

    _cancel(c)

    assert c.product.estoque_atual == 22
    entries = _entries(c)
    assert len(entries) == 2
    assert all(
        row.custo_unitario is None and row.valor_total is None for row in entries
    )


@pytest.mark.parametrize("fiscal_ja_retornou", [False, True])
def test_legado_sem_composicao_nao_adivinha_retorno_quando_produto_tem_lotes(
    lotes, fiscal_ja_retornou
):
    c = lotes
    item, movement = _exit(c)
    item.custo_original_saida = None
    item.lote_id = None
    movement.lote_id = None
    movement.lotes_consumidos = None
    if fiscal_ja_retornou:
        movement.referencia_tipo = "venda_bling"
        movement.status = "cancelado"
        c.venda.nfe_status = "cancelada"
        c.venda.nfe_bling_id = 987
        c.product.estoque_atual = 25
        c.lots[0].quantidade_disponivel = 2
        c.lots[1].quantidade_disponivel = 19
    c.db.commit()
    before = _snapshot(c)

    with pytest.raises(HTTPException) as caught:
        _cancel(c)

    assert caught.value.status_code == 409
    assert _snapshot(c) == before


def test_saida_sem_lote_comprovada_nao_recompoe_lotes_recebidos_depois(lotes):
    c = lotes
    _, movement = _exit(c)
    movement.lote_id = None
    movement.lotes_consumidos = None
    c.db.commit()

    _cancel(c)

    assert c.product.estoque_atual == 25
    assert [lot.quantidade_disponivel for lot in c.lots] == [0, 16, 4]
    entry = _entries(c)[0]
    assert entry.lote_id is None and entry.lotes_consumidos is None
    assert entry.valor_total == 460


@pytest.mark.parametrize("physical", [None, float("nan"), float("inf"), -float("inf")])
def test_saldo_fisico_desconhecido_ou_nao_finito_bloqueia_toda_transacao(
    lotes, physical
):
    c = lotes
    _exit(c)
    c.product.estoque_atual = physical
    c.db.commit()
    # SQLite normaliza NaN para NULL; o ensaio PostgreSQL cobre NaN nativo.
    c.db.expire_all()
    before = _snapshot(c)

    with pytest.raises(HTTPException) as caught:
        _cancel(c)

    assert caught.value.status_code == 409
    assert _snapshot(c) == before


def test_saldo_negativo_conhecido_pode_ser_corrigido_pelo_retorno_original(lotes):
    c = lotes
    _exit(c)
    c.product.estoque_atual = -1
    c.db.commit()

    _cancel(c)

    assert c.product.estoque_atual == 4
    assert [lot.quantidade_disponivel for lot in c.lots] == [2, 19, 4]
    assert _entries(c)[0].quantidade_anterior == -1
    assert _entries(c)[0].quantidade_nova == 4


@pytest.mark.parametrize("quantity", [0, -1, float("inf"), -float("inf")])
def test_quantidade_invalida_no_legado_sem_historico_nao_gera_entrada(lotes, quantity):
    c = lotes
    for lot in c.lots:
        c.db.delete(lot)
    item = VendaItem(
        tenant_id=c.tenant,
        venda_id=c.venda.id,
        produto_id=c.product.id,
        tipo="produto",
        quantidade=quantity,
        preco_unitario=100,
        subtotal=100,
    )
    c.db.add(item)
    c.db.commit()
    c.db.expire_all()
    before = _snapshot(c)

    with pytest.raises(HTTPException) as caught:
        _cancel(c)

    assert caught.value.status_code == 409
    assert _snapshot(c) == before


def test_preflight_recusa_quantidade_nan_antes_de_consultar_historico_ou_escrever(
    lotes,
):
    from app.vendas.cancelamento_estoque import preparar_cancelamento_estoque

    c = lotes
    before = _snapshot(c)
    # SQLite nao persiste NaN em DECIMAL NOT NULL. Este contrato testa o mesmo
    # valor que PostgreSQL pode devolver, usando a entrada publica do preflight.
    item = SimpleNamespace(
        id=99,
        tenant_id=c.tenant,
        venda_id=c.venda.id,
        produto_id=c.product.id,
        tipo="produto",
        quantidade=Decimal("NaN"),
        estoque_origem_tenant_id=None,
        product_variation_id=None,
    )

    with pytest.raises(HTTPException) as caught:
        preparar_cancelamento_estoque(c.db, c.venda, [item], c.tenant)

    assert caught.value.status_code == 409
    assert _snapshot(c) == before
