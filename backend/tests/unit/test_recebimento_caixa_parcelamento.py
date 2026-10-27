"""Regressões dos recebimentos, sem alterar dados de empresas reais."""

import asyncio
from datetime import date
from decimal import Decimal
from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi import HTTPException

from app.caixa.escopo import buscar_caixa_para_recebimento
from app.caixa_models import Caixa, MovimentacaoCaixa
from app.clientes import financeiro_baixa_lote_routes as lote_routes
from app.contas_receber_recebimentos_routes import registrar_recebimento
from app.contas_receber_consulta_routes import buscar_conta_receber
from app.contas_receber_schemas import RecebimentoCreate
from app.financeiro.contas_pagar_manutencao_routes import buscar_conta_pagar
from app.financeiro.status_contas_receber import status_conta_receber
from app.financeiro_models import (
    ContaReceber,
    MovimentacaoFinanceira,
    Recebimento,
    ContaBancaria,
    ContaPagar,
    Pagamento,
)
from app.financeiro_models import FormaPagamento, LancamentoManual
from app.ia.aba5_models import FluxoCaixa
from app.models import Cliente
from app.operadoras_models import OperadoraCartao, OperadoraCartaoTaxa
from app.vendas_models import Venda, VendaBaixaLote, VendaBaixaLoteItem

pytest_plugins = ["tests.unit.test_finalizacao_recebiveis_atomicidade"]


@pytest.fixture
def recebimento(cenario):
    c = cenario
    for model in (
        FluxoCaixa,
        ContaBancaria,
        MovimentacaoFinanceira,
        VendaBaixaLote,
        VendaBaixaLoteItem,
    ):
        model.__table__.create(c.db.bind)
    c.usuario = SimpleNamespace(id=1, nome="Operadora", email="teste@example.test")
    c.conta = ContaReceber(
        tenant_id=c.tenant,
        user_id=1,
        descricao="Conta de teste",
        canal="loja_fisica",
        dre_subcategoria_id=1,
        valor_original=100,
        valor_final=100,
        valor_recebido=0,
        status="vencido",
        data_emissao=date(2026, 9, 1),
        data_vencimento=date(2026, 9, 10),
    )
    c.db.add(c.conta)
    c.db.commit()
    return c


def _receber(c, **extras):
    campos = dict(
        valor_recebido=100,
        data_recebimento=date(2026, 10, 26),
        forma_pagamento_id=2,
        caixa_id=2,
        observacoes="Acerto conferido pelo operador",
    )
    campos.update(extras)
    dados = RecebimentoCreate(**campos)
    return asyncio.run(
        registrar_recebimento(c.conta.id, dados, None, c.db, (c.usuario, c.tenant))
    )


@pytest.mark.parametrize("tipo", ["receber", "pagar"])
@pytest.mark.parametrize("codigo", ["1848", None])
def test_detalhe_conta_retorna_codigo_publico_sem_usar_id(
    recebimento, monkeypatch, tipo, codigo
):
    c = recebimento
    pessoa = Cliente(
        tenant_id=c.tenant,
        nome="Pessoa QA código público",
        codigo=codigo,
        user_id=1,
    )
    c.db.add(pessoa)
    c.db.flush()
    if tipo == "receber":
        c.conta.cliente_id = pessoa.id
        conta = c.conta
        buscar = buscar_conta_receber
        chave = "cliente"
        monkeypatch.setattr(
            "app.contas_receber_consulta_routes.carregar_config_encargos",
            lambda *_: None,
        )
    else:
        Pagamento.__table__.create(c.db.bind)
        conta = ContaPagar(
            tenant_id=c.tenant,
            fornecedor_id=pessoa.id,
            user_id=1,
            descricao="Fornecedor QA código público",
            valor_original=100,
            valor_final=100,
            valor_pago=0,
            data_emissao=date(2026, 10, 26),
            data_vencimento=date(2026, 10, 26),
        )
        c.db.add(conta)
        buscar = buscar_conta_pagar
        chave = "fornecedor"
    c.db.commit()

    resultado = buscar(conta.id, c.db, (c.usuario, c.tenant))

    assert resultado[chave]["id"] == pessoa.id
    assert resultado[chave]["codigo"] == codigo
    assert resultado[chave]["codigo"] != str(resultado[chave]["id"])
    assert resultado[chave]["codigo"] is None or isinstance(
        resultado[chave]["codigo"], str
    )


@pytest.mark.parametrize("ajuste", [None, Decimal("0.00"), Decimal("1.25")])
def test_detalhe_conta_pagar_aceita_ajustes_nulos_sem_alterar_valores(
    recebimento, ajuste
):
    c = recebimento
    Pagamento.__table__.create(c.db.bind)
    conta = ContaPagar(
        tenant_id=c.tenant,
        user_id=1,
        descricao="Comissão QA com ajustes opcionais",
        valor_original=Decimal("130.25"),
        valor_final=Decimal("130.25"),
        valor_pago=Decimal("30.10"),
        data_emissao=date(2026, 10, 26),
        data_vencimento=date(2026, 10, 26),
    )
    c.db.add(conta)
    c.db.commit()
    # Persiste NULL após os defaults de INSERT, como nos títulos de comissão
    # criados por SQL direto. A consulta não deve escrever esses ajustes.
    conta.valor_desconto = conta.valor_juros = conta.valor_multa = ajuste
    c.db.commit()

    resultado = buscar_conta_pagar(conta.id, c.db, (c.usuario, c.tenant))

    assert resultado["valores"] == {
        "original": 130.25,
        "pago": 30.10,
        "desconto": float(ajuste or 0),
        "juros": float(ajuste or 0),
        "multa": float(ajuste or 0),
        "final": 130.25,
        "saldo": 100.15,
    }
    c.db.refresh(conta)
    assert conta.valor_desconto == conta.valor_juros == conta.valor_multa == ajuste


def test_recebimento_grava_caixa_observacao_movimento_e_fluxo_na_mesma_transacao(
    recebimento,
):
    c = recebimento
    resultado = _receber(c)
    recibo = c.db.query(Recebimento).one()
    assert c.conta.status == "recebido"
    assert resultado["saldo_restante"] == 0
    assert recibo.caixa_id == 2
    assert recibo.observacoes == "Acerto conferido pelo operador"
    assert recibo.data_recebimento == date(2026, 10, 26)
    movimento = (
        c.db.query(MovimentacaoCaixa)
        .filter_by(documento=f"RECEBIMENTO-{recibo.id}")
        .one()
    )
    assert movimento.caixa_id == 2 and movimento.valor == 100
    fluxo = (
        c.db.query(FluxoCaixa)
        .filter_by(origem_tipo="recebimento", origem_id=recibo.id)
        .one()
    )
    assert fluxo.status == "realizado" and fluxo.valor == Decimal("100")


def test_caixa_fechado_ou_de_outro_tenant_nao_recebe(recebimento):
    c = recebimento
    for ident, tenant in ((1, c.tenant), (2, uuid4())):
        with pytest.raises(HTTPException):
            buscar_caixa_para_recebimento(
                c.db, tenant_id=tenant, usuario_id=1, caixa_id=ident
            )
    assert c.db.query(Recebimento).count() == 0


@pytest.mark.parametrize("forma_id", [1, 2])
def test_pix_dinheiro_descartam_metadados_cartao_nao_validados(recebimento, forma_id):
    c = recebimento
    _receber(
        c,
        forma_pagamento_id=forma_id,
        operadora_id=999999,
        bandeira="visa",
        nsu_cartao="METADADO-DE-OUTRA-OPERACAO",
    )
    recibo = c.db.query(Recebimento).one()
    assert (recibo.operadora_id, recibo.bandeira, recibo.nsu_cartao) == (
        None,
        None,
        None,
    )
    assert c.conta.status == "recebido" and c.conta.valor_recebido == Decimal("100")


def test_dois_caixas_abertos_exigem_escolha_e_aceitam_qualquer_caixa_acessivel(
    recebimento,
):
    c = recebimento
    primeiro = c.db.get(Caixa, 1)
    primeiro.status = "aberto"
    c.db.commit()
    with pytest.raises(HTTPException, match="") as exc:
        buscar_caixa_para_recebimento(c.db, tenant_id=c.tenant, usuario_id=1)
    assert "Selecione" in exc.value.detail
    for ident in (1, 2):
        caixa, _ = buscar_caixa_para_recebimento(
            c.db, tenant_id=c.tenant, usuario_id=1, caixa_id=ident
        )
        assert caixa.id == ident


def test_status_legado_pago_nao_reaparece_como_vencido():
    conta = SimpleNamespace(
        status="pago", valor_final=Decimal("100"), valor_recebido=Decimal("100")
    )
    assert status_conta_receber(conta) == "recebido"
    conta.status, conta.valor_recebido = "baixa_parcial", Decimal("40")
    assert status_conta_receber(conta) == "parcial"


def _cartao(c):
    for model in (OperadoraCartao, OperadoraCartaoTaxa):
        model.__table__.create(c.db.bind)
    c.db.add(
        FormaPagamento(
            id=3,
            tenant_id=c.tenant,
            user_id=1,
            nome="Cartão de crédito",
            tipo="cartao_credito",
            ativo=True,
            permite_parcelamento=True,
            parcelas_maximas=12,
        )
    )
    c.db.add(
        OperadoraCartao(
            id=1,
            tenant_id=c.tenant,
            user_id=1,
            nome="Operadora de teste",
            ativo=True,
            padrao=True,
            max_parcelas=12,
        )
    )
    c.db.add(
        OperadoraCartaoTaxa(
            id=1,
            tenant_id=c.tenant,
            user_id=1,
            operadora_id=1,
            bandeira="visa",
            modalidade="credito",
            parcelas=3,
            taxa_percentual=2,
            taxa_fixa=1,
            prazo_recebimento_dias=30,
            ativo=True,
        )
    )
    c.db.commit()


def test_recebimento_cartao_parcelado_quita_cliente_e_preserva_repasse_da_operadora(
    recebimento,
):
    c = recebimento
    _cartao(c)
    _receber(
        c,
        forma_pagamento_id=3,
        numero_parcelas=3,
        operadora_id=1,
        bandeira="visa",
        nsu_cartao="NSU-TESTE",
    )
    assert c.conta.valor_recebido == Decimal("100") and c.conta.status == "recebido"
    recibo = c.db.query(Recebimento).one()
    assert recibo.numero_parcelas == 3 and recibo.nsu_cartao == "NSU-TESTE"
    repasses = (
        c.db.query(ContaReceber)
        .filter_by(conta_principal_id=c.conta.id)
        .order_by(ContaReceber.numero_parcela)
        .all()
    )
    assert len(repasses) == 3
    assert sum(p.valor_final for p in repasses) == Decimal("100")
    assert sum(p.valor_liquido_estimado for p in repasses) == Decimal("97")
    assert all(p.status == "pendente" and p.venda_id is None for p in repasses)
    assert c.db.query(FluxoCaixa).filter_by(status="realizado").count() == 0


def test_cartao_sem_taxa_desfaz_recebimento_inteiro(recebimento):
    c = recebimento
    _cartao(c)
    with pytest.raises(HTTPException):
        _receber(
            c, forma_pagamento_id=3, numero_parcelas=2, operadora_id=1, bandeira="visa"
        )
    assert c.db.query(Recebimento).count() == 0
    assert c.db.query(MovimentacaoCaixa).count() == 0
    c.db.refresh(c.conta)
    assert c.conta.valor_recebido == 0 and c.conta.status == "vencido"


def test_nsu_usado_em_outra_conta_nao_quita_segunda_divida(recebimento):
    c = recebimento
    _cartao(c)
    _receber(
        c,
        forma_pagamento_id=3,
        numero_parcelas=3,
        operadora_id=1,
        bandeira="visa",
        nsu_cartao="MESMO-NSU",
    )
    segunda = ContaReceber(
        tenant_id=c.tenant,
        user_id=1,
        descricao="Segunda dívida",
        canal="loja_fisica",
        dre_subcategoria_id=1,
        valor_original=100,
        valor_final=100,
        valor_recebido=0,
        status="pendente",
        data_emissao=date.today(),
        data_vencimento=date.today(),
    )
    c.db.add(segunda)
    c.db.commit()
    c.conta = segunda
    with pytest.raises(HTTPException) as exc:
        _receber(
            c,
            forma_pagamento_id=3,
            numero_parcelas=3,
            operadora_id=1,
            bandeira="visa",
            nsu_cartao="  mesmo-nsu  ",
        )
    assert "duplicado" in exc.value.detail
    assert c.db.query(Recebimento).count() == 1
    c.db.refresh(segunda)
    assert segunda.valor_recebido == 0


def test_cartao_na_baixa_lote_nao_antecipa_entrada_no_fluxo(recebimento, monkeypatch):
    c = recebimento
    _cartao(c)
    cliente = Cliente(tenant_id=c.tenant, user_id=1, nome="Cliente cartão lote")
    c.db.add(cliente)
    c.db.flush()
    c.venda.cliente_id = cliente.id
    c.venda.total = c.venda.subtotal = Decimal("40")
    c.venda.nao_gerar_beneficios = True
    segunda = Venda(
        tenant_id=c.tenant,
        numero_venda="QA-SEGUNDA",
        user_id=1,
        vendedor_id=1,
        cliente_id=cliente.id,
        total=60,
        subtotal=60,
        status="aberta",
        nao_gerar_beneficios=True,
    )
    c.db.add(segunda)
    c.db.commit()
    c.db.autoflush = False
    monkeypatch.setattr(
        lote_routes, "get_or_build_venda_rentabilidade_snapshot", lambda *a, **kw: {}
    )
    asyncio.run(
        lote_routes.baixar_vendas_lote(
            cliente.id,
            {
                "vendas_ids": [c.venda.id, segunda.id],
                "valor_total": 100,
                "forma_pagamento": "cartao_credito",
                "forma_pagamento_id": 3,
                "operadora_id": 1,
                "bandeira": "visa",
                "numero_parcelas": 3,
                "caixa_id": 2,
                "request_id": str(uuid4()),
                "nsu_cartao": "LOTE-CARTAO",
            },
            c.db,
            (c.usuario, c.tenant),
        )
    )
    assert c.db.query(Recebimento).count() == 2
    assert c.db.query(FluxoCaixa).filter_by(status="realizado").count() == 0
    previstos = c.db.query(FluxoCaixa).filter_by(status="previsto").all()
    assert len(previstos) == 6 and sum(p.valor for p in previstos) == Decimal("100")
    espelho = (
        c.db.query(LancamentoManual).filter_by(documento=f"VENDA-{c.venda.id}").one()
    )
    assert espelho.status == "cancelado"


def test_baixa_lote_preserva_observacao_e_status_canonico(recebimento, monkeypatch):
    c = recebimento
    cliente = Cliente(tenant_id=c.tenant, user_id=1, nome="Cliente do lote")
    c.db.add(cliente)
    c.db.flush()
    c.venda.cliente_id = cliente.id
    c.venda.total = c.venda.subtotal = Decimal("100")
    c.venda.nao_gerar_beneficios = True
    c.db.commit()
    monkeypatch.setattr(
        lote_routes, "get_or_build_venda_rentabilidade_snapshot", lambda *a, **kw: {}
    )
    asyncio.run(
        lote_routes.baixar_vendas_lote(
            cliente.id,
            {
                "vendas_ids": [c.venda.id],
                "valor_total": 100,
                "forma_pagamento": "dinheiro",
                "caixa_id": 2,
                "observacoes": "Observação real da baixa",
                "request_id": str(uuid4()),
            },
            c.db,
            (c.usuario, c.tenant),
        )
    )
    conta = c.db.query(ContaReceber).filter_by(venda_id=c.venda.id).one()
    assert conta.status == "recebido"
    recibo = c.db.query(Recebimento).filter_by(conta_receber_id=conta.id).one()
    assert "Observação real da baixa" in recibo.observacoes
    assert recibo.caixa_id == 2


@pytest.mark.parametrize("em_lote", [False, True])
@pytest.mark.parametrize(
    "parcelas,prazo,modalidade",
    [(1, 0, "credito"), (1, 0, "debito"), (1, 0, "link"), (3, 30, "credito")],
)
def test_repasse_cartao_so_realiza_fluxo_ao_liquidar_inclusive_prazo_zero(
    recebimento, monkeypatch, em_lote, parcelas, prazo, modalidade
):
    c = recebimento
    _cartao(c)
    forma = c.db.query(FormaPagamento).filter_by(id=3).one()
    forma.tipo = "link_pagamento" if modalidade == "link" else f"cartao_{modalidade}"
    forma.nome = forma.tipo
    if parcelas == 1:
        c.db.add(
            OperadoraCartaoTaxa(
                tenant_id=c.tenant,
                operadora_id=1,
                bandeira="visa",
                modalidade=modalidade,
                parcelas=1,
                user_id=1,
                taxa_percentual=2,
                taxa_fixa=1,
                prazo_recebimento_dias=prazo,
                ativo=True,
            )
        )
        c.db.commit()
    if em_lote:
        cliente = Cliente(tenant_id=c.tenant, user_id=1, nome="Cliente repasse prazo")
        c.db.add(cliente)
        c.db.flush()
        c.venda.cliente_id = cliente.id
        c.venda.total = c.venda.subtotal = Decimal("100")
        c.venda.nao_gerar_beneficios = True
        c.db.commit()
        monkeypatch.setattr(
            lote_routes,
            "get_or_build_venda_rentabilidade_snapshot",
            lambda *a, **kw: {},
        )
        resultado = asyncio.run(
            lote_routes.baixar_vendas_lote(
                cliente.id,
                {
                    "vendas_ids": [c.venda.id],
                    "valor_total": 100,
                    "forma_pagamento": "cartao_credito",
                    "forma_pagamento_id": 3,
                    "operadora_id": 1,
                    "bandeira": "visa",
                    "numero_parcelas": parcelas,
                    "caixa_id": 2,
                    "request_id": str(uuid4()),
                    "nsu_cartao": "REPASSE-PRAZO",
                },
                c.db,
                (c.usuario, c.tenant),
            )
        )
        item = (
            c.db.query(VendaBaixaLoteItem).filter_by(lote_id=resultado["lote_id"]).one()
        )
        repasses = (
            c.db.query(ContaReceber)
            .filter(ContaReceber.id.in_(item.efeitos["repasse_ids"]))
            .all()
        )
    else:
        _receber(
            c,
            forma_pagamento_id=3,
            numero_parcelas=parcelas,
            operadora_id=1,
            bandeira="visa",
            nsu_cartao="REPASSE-PRAZO",
        )
        repasses = (
            c.db.query(ContaReceber).filter_by(conta_principal_id=c.conta.id).all()
        )
    assert len(repasses) == parcelas
    assert all(
        repasse.status == "pendente" and repasse.valor_recebido == 0
        for repasse in repasses
    )
    assert c.db.query(Recebimento).count() == 1
    assert c.db.query(FluxoCaixa).filter_by(status="realizado").count() == 0
    previstos = c.db.query(FluxoCaixa).filter_by(status="previsto").all()
    assert sum(Decimal(str(fluxo.valor)) for fluxo in previstos) == Decimal("100")

    for repasse in repasses:
        asyncio.run(
            registrar_recebimento(
                repasse.id,
                RecebimentoCreate(
                    valor_recebido=repasse.valor_final,
                    data_recebimento=date.today(),
                    forma_pagamento_id=1,
                    caixa_id=2,
                ),
                None,
                c.db,
                (c.usuario, c.tenant),
            )
        )
    assert c.db.query(Recebimento).count() == 1 + parcelas
    assert all(repasse.status == "recebido" for repasse in repasses)
    assert c.db.query(FluxoCaixa).filter_by(status="previsto").count() == 0
    realizados = c.db.query(FluxoCaixa).filter_by(status="realizado").all()
    assert len(realizados) == parcelas
    assert sum(Decimal(str(fluxo.valor)) for fluxo in realizados) == Decimal("100")
