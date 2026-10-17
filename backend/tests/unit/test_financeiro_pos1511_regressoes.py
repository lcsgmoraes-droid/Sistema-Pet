"""Regressoes funcionais de contas manuais, baixas e projecao de caixa."""

import asyncio
from datetime import date
from decimal import Decimal
from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app import contas_receber_criacao_routes as cr_routes
from app import contas_receber_recebimentos_routes as baixas
from app.db import base as _base  # noqa: F401 - registra relacionamentos do ORM
from app.empresa_config_geral_models import EmpresaConfigGeral
from app.contas_receber_schemas import ContaReceberCreate, RecebimentoCreate
from app.dre_plano_contas_models import (
    DRECategoria,
    DRESubcategoria,
    EscopoRateio,
    NaturezaDRE,
    TipoCusto,
)
from app.financeiro import contas_pagar_criacao_routes as cp_routes
from app.financeiro.contas_pagar_schemas import ContaPagarCreate
from app.financeiro.contas_receber_service import ContasReceberService
from app.financeiro.crediario_parcelamento import distribuir_valor_parcelas
from app.financeiro.fluxo_caixa_periodos import _agrupar_por_periodo
from app.financeiro.fluxo_caixa_schemas import FluxoCaixaMovimentacao
from app.financeiro_models import (
    CategoriaFinanceira,
    ContaPagar,
    ContaReceber,
    FormaPagamento,
    LancamentoManual,
    Recebimento,
)
from app.tenancy.context import set_current_tenant


@pytest.fixture
def financeiro(monkeypatch):
    engine = create_engine("sqlite://")
    for model in (
        DRECategoria,
        DRESubcategoria,
        ContaPagar,
        ContaReceber,
        CategoriaFinanceira,
        FormaPagamento,
        LancamentoManual,
        Recebimento,
        EmpresaConfigGeral,
    ):
        model.__table__.create(engine)
    db_session = Session(engine, expire_on_commit=False)
    tenant = uuid4()
    set_current_tenant(tenant)
    categoria = DRECategoria(
        tenant_id=tenant, nome="QA receita", natureza=NaturezaDRE.RECEITA
    )
    db_session.add(categoria)
    db_session.flush()
    sub = DRESubcategoria(
        tenant_id=tenant,
        categoria_id=categoria.id,
        nome="QA manual",
        tipo_custo=TipoCusto.DIRETO,
        escopo_rateio=EscopoRateio.LOJA_FISICA,
    )
    db_session.add(sub)
    db_session.flush()
    monkeypatch.setattr(cr_routes, "atualizar_dre_por_lancamento", lambda **kw: None)
    try:
        yield SimpleNamespace(
            db=db_session, tenant=tenant, user=SimpleNamespace(id=1), sub=sub.id
        )
    finally:
        db_session.close()
        engine.dispose()


@pytest.mark.parametrize("modulo", ["pagar", "receber"])
@pytest.mark.parametrize(
    "total,quantidade,valores",
    [
        (100, 3, [Decimal("33.33"), Decimal("33.33"), Decimal("33.34")]),
        (200, 3, [Decimal("66.67"), Decimal("66.67"), Decimal("66.66")]),
        (354.26, 4, [Decimal("88.57")] * 3 + [Decimal("88.55")]),
        (0.09, 6, [Decimal("0.01")] * 5 + [Decimal("0.04")]),
        (0.10, 6, [Decimal("0.01")] * 5 + [Decimal("0.05")]),
        (0.04, 4, [Decimal("0.01")] * 4),
    ],
)
def test_parcelas_manuais_preservam_total_e_centavos(
    financeiro, modulo, total, quantidade, valores
):
    f = financeiro
    dados = dict(
        descricao="QA parcelas",
        valor_original=total,
        data_emissao=date(2026, 10, 16),
        data_vencimento=date(2026, 11, 10),
        eh_parcelado=True,
        total_parcelas=quantidade,
    )
    if modulo == "pagar":
        payload = ContaPagarCreate(**dados, afeta_dre=False)
        rota, model = cp_routes.criar_conta_pagar, ContaPagar
    else:
        payload = ContaReceberCreate(**dados, dre_subcategoria_id=f.sub)
        rota, model = cr_routes.criar_conta_receber, ContaReceber
    resultado = asyncio.run(
        rota.__wrapped__(
            payload,
            request=SimpleNamespace(),
            db=f.db,
            user_and_tenant=(f.user, f.tenant),
        )
    )
    parcelas = (
        f.db.query(model)
        .filter(model.id.in_(resultado["ids"]))
        .order_by(model.numero_parcela)
        .all()
    )
    assert [p.valor_original for p in parcelas] == valores
    assert sum(p.valor_original for p in parcelas) == Decimal(str(total))
    assert [p.numero_parcela for p in parcelas] == list(range(1, quantidade + 1))
    assert {p.tenant_id for p in parcelas} == {f.tenant}
    principal = f.db.get(model, parcelas[0].conta_principal_id)
    assert principal.valor_original == Decimal(str(total))
    assert principal.status == "parcelado"


@pytest.mark.parametrize("modulo", ["pagar", "receber"])
@pytest.mark.parametrize(
    "primeira,esperadas",
    [
        (
            date(2026, 10, 31),
            [date(2026, 10, 31), date(2026, 11, 30), date(2026, 12, 31)],
        ),
        (date(2027, 1, 31), [date(2027, 1, 31), date(2027, 2, 28), date(2027, 3, 31)]),
        (date(2028, 1, 31), [date(2028, 1, 31), date(2028, 2, 29), date(2028, 3, 31)]),
    ],
)
def test_parcelas_manuais_ajustam_mes_curto_sem_perder_dia_original(
    financeiro, modulo, primeira, esperadas
):
    f = financeiro
    dados = dict(
        descricao="QA fim mes",
        valor_original=90,
        data_emissao=primeira,
        data_vencimento=primeira,
        eh_parcelado=True,
        total_parcelas=3,
    )
    if modulo == "pagar":
        payload, rota, model = (
            ContaPagarCreate(**dados, afeta_dre=False),
            cp_routes.criar_conta_pagar,
            ContaPagar,
        )
    else:
        payload, rota, model = (
            ContaReceberCreate(**dados, dre_subcategoria_id=f.sub),
            cr_routes.criar_conta_receber,
            ContaReceber,
        )
    resultado = asyncio.run(
        rota.__wrapped__(
            payload,
            request=SimpleNamespace(),
            db=f.db,
            user_and_tenant=(f.user, f.tenant),
        )
    )
    parcelas = (
        f.db.query(model)
        .filter(model.id.in_(resultado["ids"]))
        .order_by(model.numero_parcela)
        .all()
    )
    assert [p.data_vencimento for p in parcelas] == esperadas


def _cr(f, status, *, tenant=None, recebido=0):
    conta = ContaReceber(
        tenant_id=tenant or f.tenant,
        user_id=1,
        descricao="QA baixa",
        dre_subcategoria_id=f.sub,
        canal="loja_fisica",
        valor_original=100,
        valor_final=100,
        valor_recebido=recebido,
        status=status,
        data_emissao=date(2026, 10, 1),
        data_vencimento=date(2026, 10, 10),
    )
    f.db.add(conta)
    f.db.commit()
    return conta


@pytest.mark.parametrize("status", ["cancelado", "cancelada", "pago", "recebido"])
def test_baixa_individual_fechada_nao_ressuscita_conta_nem_grava_recebimento(
    financeiro, status
):
    f = financeiro
    conta = _cr(f, status)
    with pytest.raises(HTTPException) as erro:
        asyncio.run(
            baixas.registrar_recebimento.__wrapped__(
                conta.id,
                RecebimentoCreate(
                    valor_recebido=100, data_recebimento=date(2026, 10, 16)
                ),
                request=SimpleNamespace(),
                db=f.db,
                user_and_tenant=(f.user, f.tenant),
            )
        )
    assert erro.value.status_code == 400
    f.db.expire_all()
    assert conta.status == status
    assert conta.valor_recebido == 0
    assert f.db.query(Recebimento).filter_by(conta_receber_id=conta.id).count() == 0


def test_baixa_individual_parcial_quita_saldo_e_bloqueia_excesso_e_outro_tenant(
    financeiro,
):
    f = financeiro
    conta = _cr(f, "parcial", recebido=30)
    payload = RecebimentoCreate(valor_recebido=71, data_recebimento=date(2026, 10, 16))
    with pytest.raises(HTTPException) as erro:
        asyncio.run(
            baixas.registrar_recebimento.__wrapped__(
                conta.id,
                payload,
                request=SimpleNamespace(),
                db=f.db,
                user_and_tenant=(f.user, f.tenant),
            )
        )
    assert erro.value.status_code == 400
    assert conta.valor_recebido == 30
    with pytest.raises(HTTPException) as erro:
        asyncio.run(
            baixas.registrar_recebimento.__wrapped__(
                conta.id,
                payload,
                request=SimpleNamespace(),
                db=f.db,
                user_and_tenant=(f.user, uuid4()),
            )
        )
    assert erro.value.status_code == 404
    payload = RecebimentoCreate(valor_recebido=70, data_recebimento=date(2026, 10, 16))
    asyncio.run(
        baixas.registrar_recebimento.__wrapped__(
            conta.id,
            payload,
            request=SimpleNamespace(),
            db=f.db,
            user_and_tenant=(f.user, f.tenant),
        )
    )
    f.db.expire_all()
    assert conta.status == "recebido"
    assert conta.valor_original == conta.valor_final == conta.valor_recebido == 100
    assert (
        f.db.query(Recebimento)
        .filter_by(conta_receber_id=conta.id)
        .one()
        .valor_recebido
        == 70
    )


@pytest.mark.parametrize("agrupamento", ["dia", "semana", "mes"])
def test_projecao_carrega_previstos_entre_periodos_e_mantem_realizado(agrupamento):
    movimentos = [
        FluxoCaixaMovimentacao(
            data=date(2026, 10, 1),
            tipo="entrada",
            valor=20,
            status="previsto",
            descricao="QA previsto",
            categoria="QA",
            origem_tipo="lancamento_manual",
        ),
        FluxoCaixaMovimentacao(
            data=date(2026, 11, 1),
            tipo="entrada",
            valor=10,
            status="realizado",
            descricao="QA realizado",
            categoria="QA",
            origem_tipo="lancamento_manual",
        ),
    ]
    periodos = _agrupar_por_periodo(
        movimentos, date(2026, 10, 1), date(2026, 11, 2), agrupamento, 100
    )
    assert periodos[0].previsto_saldo == 120
    assert periodos[-1].realizado_saldo == 110
    assert periodos[-1].previsto_saldo == 130


@pytest.mark.parametrize("modulo", ["pagar", "receber"])
@pytest.mark.parametrize(
    "total,quantidade",
    [(0.02, 4), (0.03, 6), (0, 3), (-1, 3), (float("nan"), 3), (float("inf"), 3)],
)
def test_parcelamento_invalido_retorna400_antes_de_flush(
    financeiro, monkeypatch, modulo, total, quantidade
):
    f = financeiro
    flushed = []
    original_flush = f.db.flush

    def flush(*args, **kwargs):
        flushed.append(True)
        return original_flush(*args, **kwargs)

    monkeypatch.setattr(f.db, "flush", flush)
    dados = dict(
        descricao="QA minimo",
        valor_original=total,
        data_emissao=date(2026, 10, 16),
        data_vencimento=date(2026, 11, 10),
        eh_parcelado=True,
        total_parcelas=quantidade,
    )
    if modulo == "pagar":
        payload, rota, model = (
            ContaPagarCreate(**dados, afeta_dre=False),
            cp_routes.criar_conta_pagar,
            ContaPagar,
        )
    else:
        payload, rota, model = (
            ContaReceberCreate(**dados, dre_subcategoria_id=f.sub),
            cr_routes.criar_conta_receber,
            ContaReceber,
        )
    with pytest.raises(HTTPException) as erro:
        asyncio.run(
            rota.__wrapped__(
                payload,
                request=SimpleNamespace(),
                db=f.db,
                user_and_tenant=(f.user, f.tenant),
            )
        )
    assert erro.value.status_code == 400
    assert not flushed
    assert not [row for row in f.db.new if isinstance(row, model)]


@pytest.mark.parametrize(
    "valor",
    [
        Decimal("NaN"),
        Decimal("Infinity"),
        Decimal("-Infinity"),
        Decimal("0"),
        Decimal("-1"),
    ],
)
def test_helper_parcelamento_rejeita_valor_nao_positivo_ou_nao_finito(valor):
    with pytest.raises(ValueError, match="finito e maior que zero"):
        distribuir_valor_parcelas(valor, 3)


def test_pdv_parcelamento_insuficiente_vira400_antes_de_gravar():
    added = []
    db = SimpleNamespace(add=added.append, flush=lambda: None)
    with pytest.raises(HTTPException) as erro:
        ContasReceberService._criar_contas_parceladas(
            venda=SimpleNamespace(id=1, tenant_id=uuid4(), numero_venda="QA"),
            pagamento=SimpleNamespace(valor=Decimal("0.02")),
            forma_pag=SimpleNamespace(tipo="crediario"),
            numero_parcelas=4,
            categoria_receitas=SimpleNamespace(id=1),
            user_id=1,
            db=db,
        )
    assert erro.value.status_code == 400
    assert not added
