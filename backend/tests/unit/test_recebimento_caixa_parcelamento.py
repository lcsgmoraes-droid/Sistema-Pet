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
from app.contas_receber_schemas import RecebimentoCreate
from app.financeiro.status_contas_receber import status_conta_receber
from app.financeiro_models import (
    ContaReceber,
    MovimentacaoFinanceira,
    Recebimento,
    ContaBancaria,
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
