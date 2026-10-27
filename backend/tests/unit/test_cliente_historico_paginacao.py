"""Regressoes de paginação e movimentos da ficha financeira do cliente."""

import asyncio
from datetime import date, datetime, timedelta
from types import SimpleNamespace
from uuid import uuid4

import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session
from sqlalchemy.schema import CreateTable

from app import caixa_models, produtos_models  # noqa: F401 - registra relacionamentos
from app.clientes import financeiro_routes
from app.clientes.historico_compras import status_pagamento_sql
from app.financeiro.cliente_historico import consultar_movimentos_cliente
from app.financeiro_models import ContaReceber, FormaPagamento, Recebimento
from app.models import Cliente, CreditoLog
from app.tenancy.context import clear_current_tenant, set_current_tenant
from app.vendas.status_pagamento import calcular_resumo_pagamento_venda
from app.vendas_models import Venda, VendaItem, VendaPagamento


@pytest.fixture
def contexto(monkeypatch):
    engine = create_engine("sqlite://")
    with engine.begin() as connection:
        for modelo in (
            Cliente,
            Venda,
            VendaItem,
            VendaPagamento,
            ContaReceber,
            Recebimento,
            FormaPagamento,
            CreditoLog,
        ):
            connection.execute(
                CreateTable(modelo.__table__, include_foreign_key_constraints=[])
            )
    tenant = uuid4()
    set_current_tenant(tenant)
    with Session(engine) as db:
        cliente = Cliente(
            tenant_id=tenant,
            user_id=1,
            nome="Cliente com histórico extenso",
            codigo="2292",
        )
        db.add(cliente)
        db.flush()
        monkeypatch.setattr(
            financeiro_routes, "_obter_cliente_ou_404", lambda *_: cliente
        )
        try:
            yield db, tenant, cliente, engine
        finally:
            clear_current_tenant()
    engine.dispose()


def criar_venda(db, tenant, cliente, numero, **kwargs):
    venda = Venda(
        tenant_id=tenant,
        user_id=1,
        vendedor_id=1,
        cliente_id=cliente.id,
        numero_venda=str(numero),
        subtotal=100,
        total=100,
        status="finalizada",
        data_venda=datetime(2026, 10, 1) + timedelta(minutes=numero),
        **kwargs,
    )
    db.add(venda)
    db.flush()
    return venda


def test_compras_paginam_no_banco_com_totais_globais_e_consultas_limitadas(contexto):
    db, tenant, cliente, engine = contexto
    for numero in range(45):
        venda = criar_venda(db, tenant, cliente, numero)
        db.add(
            VendaItem(
                tenant_id=tenant,
                venda_id=venda.id,
                tipo="servico",
                servico_descricao="Consulta",
                quantidade=1,
                preco_unitario=100,
                subtotal=100,
            )
        )
    db.flush()
    outro_tenant = uuid4()
    set_current_tenant(outro_tenant)
    criar_venda(db, outro_tenant, cliente, 99)
    set_current_tenant(tenant)
    db.commit()
    consultas = []
    event.listen(
        engine, "before_cursor_execute", lambda *args: consultas.append(args[2])
    )
    resultado = asyncio.run(
        financeiro_routes.get_historico_compras(
            cliente.id,
            page=2,
            per_page=20,
            status_pagamento=None,
            incluir_detalhes=False,
            db=db,
            user_and_tenant=(SimpleNamespace(id=1), tenant),
        )
    )
    assert len(resultado["vendas"]) == 20
    assert resultado["vendas"][0]["numero_venda"] == "24"
    assert resultado["total_compras"] == 45
    assert resultado["valor_total_gasto"] == 4500
    assert resultado["paginacao"]["total_paginas"] == 3
    assert all(
        venda["total_itens"] == 1 and venda["itens"] == []
        for venda in resultado["vendas"]
    )
    selects = [sql for sql in consultas if sql.lstrip().upper().startswith("SELECT")]
    assert len(selects) <= 7
    assert any("LIMIT" in sql.upper() and "FROM vendas" in sql for sql in selects)
    assert not any("FROM produtos" in sql for sql in selects)


@pytest.mark.parametrize(
    "pagamentos,contas,status_venda",
    [
        ([], [], "finalizada"),
        ([{"forma_pagamento": "pix", "valor": 100}], [], "finalizada"),
        ([{"forma_pagamento": "dinheiro", "valor": 30}], [], "finalizada"),
        (
            [{"forma_pagamento": "pix", "valor": 100, "status": "estornado"}],
            [],
            "finalizada",
        ),
        (
            [{"forma_pagamento": "crediario", "forma_pagamento_id": 5, "valor": 100}],
            [{"forma_pagamento_id": 5, "valor_recebido": 25}],
            "finalizada",
        ),
        (
            [{"forma_pagamento": "crediario", "valor": 100}],
            [{"valor_recebido": 100}],
            "finalizada",
        ),
        (
            [{"forma_pagamento": "Crediário", "valor": 100, "numero_parcelas": 1}],
            [],
            "finalizada",
        ),
        (
            [
                {"forma_pagamento": "crediario", "forma_pagamento_id": 5, "valor": 70},
                {"forma_pagamento": "pix", "valor": 30},
            ],
            [
                {"forma_pagamento_id": 5, "valor_recebido": 20},
                {"forma_pagamento_id": 6, "valor_recebido": 30},
            ],
            "finalizada",
        ),
        ([], [{"valor_recebido": 100}], "finalizada"),
        ([], [{"valor_recebido": 100, "status": "cancelada"}], "finalizada"),
        ([{"forma_pagamento": "pix", "valor": 100}], [], "cancelada"),
    ],
)
def test_filtro_sql_preserva_resumo_financeiro(
    contexto, pagamentos, contas, status_venda
):
    db, tenant, cliente, _ = contexto
    venda = criar_venda(db, tenant, cliente, 1)
    venda.status = status_venda
    for campos in pagamentos:
        db.add(VendaPagamento(tenant_id=tenant, venda_id=venda.id, **campos))
    for indice, campos in enumerate(contas):
        db.add(
            ContaReceber(
                canal="loja_fisica",
                dre_subcategoria_id=1,
                tenant_id=tenant,
                user_id=1,
                cliente_id=cliente.id,
                venda_id=venda.id,
                descricao="Parcela",
                valor_original=100,
                valor_final=100,
                data_emissao=date(2026, 10, 1),
                data_vencimento=date(2026, 10, 26),
                **({"status": "pendente"} | campos),
            )
        )
    db.flush()
    db.expire(venda)
    esperado = calcular_resumo_pagamento_venda(
        total=venda.total,
        pagamentos=venda.pagamentos,
        contas_receber=venda.contas_receber,
    )["status_pagamento"]
    if status_venda == "cancelada":
        esperado = "cancelada"
    p, c, expressao = status_pagamento_sql(tenant)
    observado = (
        db.query(expressao)
        .select_from(Venda)
        .outerjoin(p, p.c.venda_id == Venda.id)
        .outerjoin(c, c.c.venda_id == Venda.id)
        .filter(Venda.id == venda.id)
        .scalar()
    )
    assert observado == esperado


def test_financeiro_inclui_baixa_com_data_observacao_e_paginacao(contexto):
    db, tenant, cliente, _ = contexto
    venda = criar_venda(db, tenant, cliente, 1)
    conta = ContaReceber(
        canal="loja_fisica",
        dre_subcategoria_id=1,
        tenant_id=tenant,
        user_id=1,
        cliente_id=cliente.id,
        venda_id=venda.id,
        descricao="Venda em aberto",
        valor_original=100,
        valor_final=100,
        valor_recebido=100,
        status="recebido",
        data_emissao=date(2026, 10, 1),
        data_vencimento=date(2026, 10, 25),
    )
    db.add(conta)
    db.flush()
    db.add(
        Recebimento(
            tenant_id=tenant,
            user_id=1,
            conta_receber_id=conta.id,
            valor_recebido=100,
            data_recebimento=date(2026, 10, 26),
            observacoes="Baixa em lote: pagamento balcão",
        )
    )
    db.flush()
    outro_tenant = uuid4()
    set_current_tenant(outro_tenant)
    db.add(
        Recebimento(
            tenant_id=outro_tenant,
            user_id=1,
            conta_receber_id=conta.id,
            valor_recebido=999,
            data_recebimento=date(2026, 10, 26),
        )
    )
    db.flush()
    set_current_tenant(tenant)
    historico, total = consultar_movimentos_cliente(
        db, tenant_id=tenant, cliente_id=cliente.id, page=1, per_page=1
    )
    assert total == 3
    assert len(historico) == 1
    baixa = historico[0]
    assert baixa["tipo"] == "recebimento"
    assert baixa["valor"] == 100
    assert baixa["data"] == "2026-10-26T00:00:00"
    assert baixa["detalhes"]["data_baixa"] == "2026-10-26"
    assert baixa["detalhes"]["observacoes"] == "Baixa em lote: pagamento balcão"
    filtrado, total = consultar_movimentos_cliente(
        db,
        tenant_id=tenant,
        cliente_id=cliente.id,
        page=1,
        per_page=20,
        tipo="recebimento",
        data_inicio=date(2026, 10, 26),
        data_fim=date(2026, 10, 27),
    )
    assert total == 1
    assert filtrado[0]["tipo"] == "recebimento"


def test_resumos_nao_cobram_do_cliente_o_repasse_de_cartao(contexto):
    from app.financeiro.cliente_routes import (
        get_historico_financeiro_cliente,
        get_resumo_financeiro_cliente,
    )

    db, tenant, cliente, _ = contexto
    forma = FormaPagamento(
        tenant_id=tenant, user_id=1, nome="Cartão crédito", tipo="cartao_credito"
    )
    db.add(forma)
    db.flush()
    for valor, status, forma_id in [
        (100, "pendente", forma.id),
        (25, "baixa_parcial", None),
    ]:
        db.add(
            ContaReceber(
                tenant_id=tenant,
                user_id=1,
                cliente_id=cliente.id,
                descricao="Parcela",
                canal="loja_fisica",
                dre_subcategoria_id=1,
                valor_original=valor,
                valor_final=valor,
                status=status,
                forma_pagamento_id=forma_id,
                data_emissao=date.today(),
                data_vencimento=date.today() - timedelta(days=1),
            )
        )
    db.flush()
    args = {"db": db, "user_and_tenant": (SimpleNamespace(id=1), tenant)}
    completo = asyncio.run(get_historico_financeiro_cliente(cliente.id, **args))
    resumo = asyncio.run(
        get_resumo_financeiro_cliente(
            cliente.id, db=db, current_user_and_tenant=args["user_and_tenant"]
        )
    )
    assert completo["resumo"]["total_em_aberto"] == 25
    assert resumo["resumo"]["total_em_aberto"] == 25
    assert resumo["resumo"]["total_vencido"] == 25
