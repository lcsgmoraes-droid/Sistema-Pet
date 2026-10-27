"""Regressoes de paginação e movimentos da ficha financeira do cliente."""

import asyncio
from datetime import date, datetime, timedelta
from types import SimpleNamespace
from uuid import uuid4

import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool
from sqlalchemy.schema import CreateTable

from app import caixa_models, produtos_models  # noqa: F401 - registra relacionamentos
from app.clientes import financeiro_routes
from app.clientes.historico_compras import status_pagamento_sql
from app.financeiro.cliente_historico import consultar_movimentos_cliente
from app.financeiro_models import ContaReceber, FormaPagamento, Recebimento
from app.models import Cliente, CreditoLog
from app.tenancy.context import clear_current_tenant, set_current_tenant
from app.vendas.status_pagamento import calcular_resumo_pagamento_venda
from app.vendas_models import (
    Venda,
    VendaBaixaLote,
    VendaBaixaLoteItem,
    VendaItem,
    VendaPagamento,
)


@pytest.fixture
def contexto(monkeypatch):
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
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
            VendaBaixaLote,
            VendaBaixaLoteItem,
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


def criar_conta_historico(db, tenant, cliente, venda, recebido=100):
    conta = ContaReceber(
        tenant_id=tenant,
        user_id=1,
        cliente_id=cliente.id,
        venda_id=venda.id,
        descricao="Venda importada",
        canal="loja_fisica",
        dre_subcategoria_id=1,
        valor_original=100,
        valor_final=100,
        valor_recebido=recebido,
        status="vencido",
        data_emissao=date(2026, 9, 15),
        data_vencimento=date(2026, 9, 28),
    )
    db.add(conta)
    db.flush()
    return conta


def api_recebimentos(db, tenant):
    from fastapi import FastAPI
    from app.auth.dependencies import get_current_user_and_tenant
    from app.db import get_session
    from app.vendas.pagamentos_routes import router

    app = FastAPI()
    app.include_router(router, prefix="/vendas")
    app.dependency_overrides[get_session] = lambda: db
    app.dependency_overrides[get_current_user_and_tenant] = lambda: (
        SimpleNamespace(id=1),
        tenant,
    )
    return app


@pytest.mark.parametrize("no_campo_lote", [True, False])
def test_recibos_http_mostram_original_lote_sem_duplicar_pagamentos(
    contexto, no_campo_lote
):
    from fastapi.testclient import TestClient

    db, tenant, cliente, engine = contexto
    venda = criar_venda(db, tenant, cliente, 1)
    conta = criar_conta_historico(db, tenant, cliente, venda)
    forma = FormaPagamento(tenant_id=tenant, user_id=1, nome="Pix", tipo="pix")
    db.add(forma)
    db.flush()
    original = "Cliente pagou dia 28/09 - sistema não filtrou o pagamento na data"
    recibo = Recebimento(
        tenant_id=tenant,
        user_id=1,
        conta_receber_id=conta.id,
        valor_recebido=100,
        data_recebimento=date(2026, 10, 26),
        observacoes="Baixa em lote - pix",
    )
    estorno = Recebimento(
        tenant_id=tenant,
        user_id=1,
        conta_receber_id=conta.id,
        valor_recebido=-100,
        data_recebimento=date(2026, 10, 27),
        forma_pagamento_id=forma.id,
        observacoes="Estorno solicitado pelo cliente",
    )
    db.add_all([recibo, estorno])
    db.flush()
    lote = VendaBaixaLote(
        tenant_id=tenant,
        cliente_id=cliente.id,
        caixa_id=1,
        usuario_id=1,
        usuario_nome="QA",
        request_id=str(uuid4()),
        valor_total=100,
        forma_pagamento="Pix",
        data=datetime(2026, 10, 26, 8, 3, 51),
        observacoes=original if no_campo_lote else None,
        requisicao={"observacoes": original},
    )
    db.add(lote)
    db.flush()
    pagamento = VendaPagamento(
        tenant_id=tenant,
        venda_id=venda.id,
        forma_pagamento="Pix",
        valor=100,
        baixa_lote_id=lote.id,
    )
    db.add(pagamento)
    db.flush()
    db.add(
        VendaBaixaLoteItem(
            tenant_id=tenant,
            lote_id=lote.id,
            venda_id=venda.id,
            numero_venda=venda.numero_venda,
            valor=100,
            pagamento_id=pagamento.id,
            efeitos={"recebimento_id": recibo.id, "conta_id": conta.id},
        )
    )
    db.flush()
    consultas = []
    event.listen(
        engine, "before_cursor_execute", lambda *args: consultas.append(args[2])
    )
    with TestClient(api_recebimentos(db, tenant)) as client:
        resposta = client.get(
            f"/vendas/{venda.id}/recebimentos-historico?page=2&per_page=1"
        )
    assert resposta.status_code == 200
    dados = resposta.json()
    assert dados["paginacao"] == {
        "page": 2,
        "per_page": 1,
        "total": 2,
        "total_pages": 2,
    }
    baixa = dados["recebimentos"][0]
    assert baixa["recebimento_id"] == recibo.id
    assert baixa["data_baixa"] == "2026-10-26"
    assert baixa["observacoes"] == original
    assert baixa["observacoes_recebimento"] == "Baixa em lote - pix"
    assert baixa["forma_pagamento"] == "Pix"
    assert baixa["baixa_lote_id"] == lote.id
    assert baixa["status"] == "recebido"
    selects = [sql for sql in consultas if sql.lstrip().upper().startswith("SELECT")]
    assert len(selects) <= 4
    historico, _ = consultar_movimentos_cliente(
        db,
        tenant_id=tenant,
        cliente_id=cliente.id,
        page=1,
        per_page=20,
        tipo="recebimento",
    )
    assert len(historico) == 2
    assert historico[0]["detalhes"]["status_recebimento"] == "estornado"
    assert historico[0]["valor"] == -100
    assert historico[1]["detalhes"]["observacoes"] == original
    assert historico[1]["detalhes"]["forma_pagamento"] == "Pix"
    assert recibo.observacoes == "Baixa em lote - pix"
    assert conta.status == "vencido"


@pytest.mark.parametrize(
    "recebido,esperado", [(0, "em_aberto"), (25, "parcial"), (100, "pago")]
)
def test_financeiro_filtra_status_financeiro_sem_alterar_finalizacao(
    contexto, recebido, esperado
):
    db, tenant, cliente, _ = contexto
    venda = criar_venda(db, tenant, cliente, 1)
    criar_conta_historico(db, tenant, cliente, venda, recebido)
    historico, total = consultar_movimentos_cliente(
        db,
        tenant_id=tenant,
        cliente_id=cliente.id,
        page=1,
        per_page=20,
        tipo="venda",
        status=esperado,
    )
    assert total == 1
    assert historico[0]["status_operacional"] == "finalizada"
    assert historico[0]["status_pagamento"] == esperado
    assert historico[0]["detalhes"]["status_pagamento"] == esperado
    assert venda.status == "finalizada"
    if recebido == 100:
        contas, total = consultar_movimentos_cliente(
            db,
            tenant_id=tenant,
            cliente_id=cliente.id,
            page=1,
            per_page=20,
            tipo="conta_receber",
            status="recebido",
        )
        assert total == 1
        assert contas[0]["status"] == "recebido"


def test_recibos_http_isolam_tenant_e_nao_inferem_vinculo_por_texto_data_valor(
    contexto,
):
    from fastapi.testclient import TestClient

    db, tenant, cliente, _ = contexto
    venda = criar_venda(db, tenant, cliente, 1)
    conta = criar_conta_historico(db, tenant, cliente, venda)
    recibo = Recebimento(
        tenant_id=tenant,
        user_id=1,
        conta_receber_id=conta.id,
        valor_recebido=100,
        data_recebimento=date(2026, 10, 26),
        observacoes="Baixa em lote - pix",
    )
    db.add_all(
        [
            recibo,
            VendaPagamento(
                tenant_id=tenant, venda_id=venda.id, forma_pagamento="Pix", valor=100
            ),
        ]
    )
    db.flush()
    outro_tenant = uuid4()
    set_current_tenant(outro_tenant)
    outra_venda = criar_venda(db, outro_tenant, cliente, 99)
    outra_forma = FormaPagamento(
        tenant_id=outro_tenant, user_id=1, nome="Forma da outra empresa", tipo="pix"
    )
    outro_lote = VendaBaixaLote(
        tenant_id=outro_tenant,
        cliente_id=cliente.id,
        caixa_id=1,
        usuario_id=1,
        usuario_nome="QA",
        request_id=str(uuid4()),
        valor_total=100,
        forma_pagamento="Forma confidencial",
        data=datetime(2026, 10, 26),
        observacoes="Observação confidencial",
        requisicao={},
    )
    db.add_all([outro_lote, outra_forma])
    db.flush()
    db.add_all(
        [
            VendaBaixaLoteItem(
                tenant_id=outro_tenant,
                lote_id=outro_lote.id,
                venda_id=venda.id,
                numero_venda="1",
                valor=100,
                pagamento_id=999,
                efeitos={"recebimento_id": recibo.id, "conta_id": conta.id},
            ),
            Recebimento(
                tenant_id=outro_tenant,
                user_id=1,
                conta_receber_id=conta.id,
                valor_recebido=100,
                data_recebimento=date(2026, 10, 26),
            ),
        ]
    )
    db.flush()
    set_current_tenant(tenant)
    recibo.forma_pagamento_id = outra_forma.id
    db.flush()
    with TestClient(api_recebimentos(db, tenant)) as client:
        resposta = client.get(f"/vendas/{venda.id}/recebimentos-historico")
        negada = client.get(f"/vendas/{outra_venda.id}/recebimentos-historico")
        invalida = client.get(f"/vendas/{venda.id}/recebimentos-historico?per_page=101")
    assert resposta.status_code == 200
    assert negada.status_code == 404
    assert invalida.status_code == 422
    dados = resposta.json()
    assert dados["paginacao"]["total"] == 1
    baixa = dados["recebimentos"][0]
    assert baixa["origem"] == "recebimento"
    assert baixa["baixa_lote_id"] is None
    assert baixa["forma_pagamento"] == "Não informado"
    assert baixa["observacoes"] == "Baixa em lote - pix"
    assert "confidencial" not in resposta.text


@pytest.mark.parametrize(
    "forma,esperado", [("Cartão crédito", "pago"), ("Crediário", "em_aberto")]
)
def test_financeiro_nao_confunde_repasse_cartao_com_parcela_cliente(
    contexto, forma, esperado
):
    db, tenant, cliente, _ = contexto
    venda = criar_venda(db, tenant, cliente, 1)
    criar_conta_historico(db, tenant, cliente, venda, recebido=0)
    db.add(
        VendaPagamento(
            tenant_id=tenant, venda_id=venda.id, forma_pagamento=forma, valor=100
        )
    )
    db.flush()
    itens, total = consultar_movimentos_cliente(
        db,
        tenant_id=tenant,
        cliente_id=cliente.id,
        page=1,
        per_page=20,
        tipo="venda",
        status=esperado,
    )
    assert total == 1
    assert itens[0]["status_pagamento"] == esperado


def test_financeiro_cancelado_preserva_status_operacional_e_filtro(contexto):
    db, tenant, cliente, _ = contexto
    venda = criar_venda(db, tenant, cliente, 1)
    venda.status = "cancelada"
    db.add(
        VendaPagamento(
            tenant_id=tenant, venda_id=venda.id, forma_pagamento="Pix", valor=100
        )
    )
    db.flush()
    itens, total = consultar_movimentos_cliente(
        db,
        tenant_id=tenant,
        cliente_id=cliente.id,
        page=1,
        per_page=20,
        status="cancelado",
    )
    assert total == 1
    assert itens[0]["status_pagamento"] == "cancelado"
    assert itens[0]["status_operacional"] == "cancelada"
    assert venda.status == "cancelada"


def test_filtro_recebido_reune_venda_paga_conta_zerada_e_recibo(contexto):
    db, tenant, cliente, _ = contexto
    venda = criar_venda(db, tenant, cliente, 1)
    conta = criar_conta_historico(db, tenant, cliente, venda)
    db.add(
        Recebimento(
            tenant_id=tenant,
            user_id=1,
            conta_receber_id=conta.id,
            valor_recebido=100,
            data_recebimento=date(2026, 10, 26),
        )
    )
    db.flush()
    itens, total = consultar_movimentos_cliente(
        db,
        tenant_id=tenant,
        cliente_id=cliente.id,
        page=1,
        per_page=20,
        status="recebido",
    )
    assert total == 3
    assert {item["tipo"] for item in itens} == {"venda", "conta_receber", "recebimento"}
    assert (
        next(item for item in itens if item["tipo"] == "venda")["status_pagamento"]
        == "pago"
    )
    assert (
        next(item for item in itens if item["tipo"] == "conta_receber")["status"]
        == "recebido"
    )
    assert (
        next(item for item in itens if item["tipo"] == "recebimento")["detalhes"][
            "status_recebimento"
        ]
        == "recebido"
    )
    assert conta.status == "vencido"


@pytest.mark.parametrize(
    "status_original,recebido,situacao",
    [
        ("pendente", 0, "em_aberto"),
        ("aberto", 0, "em_aberto"),
        ("aberta", 0, "em_aberto"),
        (" PENDENTE ", 0, "em_aberto"),
        ("pendente", 25, "parcial"),
        ("baixa_parcial", 25, "parcial"),
        ("vencido", 25, "vencido"),
        ("vencida", 25, "vencido"),
        ("vencido", 100, "recebido"),
        ("pago", 0, "recebido"),
        ("cancelada", 100, "cancelado"),
        ("cancelado", 0, "cancelado"),
        ("pendente", -25, "em_aberto"),
    ],
)
def test_estado_conta_exibido_e_filtrado_sem_alterar_registro(
    contexto, status_original, recebido, situacao
):
    db, tenant, cliente, _ = contexto
    venda = criar_venda(db, tenant, cliente, 1)
    conta = criar_conta_historico(db, tenant, cliente, venda, recebido)
    conta.status = status_original
    db.commit()
    argumentos = dict(
        tenant_id=tenant,
        cliente_id=cliente.id,
        page=1,
        per_page=20,
        tipo="conta_receber",
    )
    itens, total = consultar_movimentos_cliente(db, **argumentos, status=situacao)
    assert total == 1
    assert itens[0]["detalhes"]["conta_receber_id"] == conta.id
    assert itens[0]["status"] == situacao
    divergente = "recebido" if situacao != "recebido" else "em_aberto"
    assert consultar_movimentos_cliente(db, **argumentos, status=divergente) == ([], 0)
    db.expire_all()
    assert conta.status == status_original
    assert conta.valor_recebido == recebido


def test_normalizacao_conta_nao_oculta_nem_reclassifica_estorno(contexto):
    db, tenant, cliente, _ = contexto
    venda = criar_venda(db, tenant, cliente, 1)
    conta = criar_conta_historico(db, tenant, cliente, venda, recebido=-25)
    conta.status = "pendente"
    recibo = Recebimento(
        tenant_id=tenant,
        user_id=1,
        conta_receber_id=conta.id,
        valor_recebido=-25,
        data_recebimento=date(2026, 10, 26),
        observacoes="Estorno QA preservado",
    )
    db.add(recibo)
    db.commit()
    itens, total = consultar_movimentos_cliente(
        db,
        tenant_id=tenant,
        cliente_id=cliente.id,
        page=1,
        per_page=20,
        status="estornado",
    )
    assert total == 1
    assert itens[0]["valor"] == -25
    assert itens[0]["status"] == "estornado"
    assert itens[0]["detalhes"]["status_recebimento"] == "estornado"
    assert itens[0]["detalhes"]["observacoes"] == "Estorno QA preservado"
    db.expire_all()
    assert conta.status == "pendente"
    assert conta.valor_recebido == -25
