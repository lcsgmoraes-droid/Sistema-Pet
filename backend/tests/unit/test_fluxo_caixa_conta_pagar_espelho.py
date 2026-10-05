"""Fluxo de caixa usa vencimento e baixas, sem contar o espelho da emissão."""

from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from app.campaigns import models as _campaigns_models  # noqa: F401 - registra FK no SQLite
from app.financeiro.fluxo_caixa_routes import get_fluxo_caixa
from app.financeiro_models import ContaPagar, LancamentoManual, Pagamento
from app.ia.aba5_models import FluxoCaixa
from app.tenancy.context import set_current_tenant


def _conta(db, tenant, usuario, *, valor="100.00", vencimento=date(2026, 11, 10)):
    set_current_tenant(UUID(str(tenant.id)))
    conta = ContaPagar(
        tenant_id=tenant.id,
        user_id=usuario.id,
        descricao="Despesa de teste",
        valor_original=Decimal(valor),
        valor_final=Decimal(valor),
        valor_pago=Decimal("0.00"),
        data_emissao=date(2026, 10, 5),
        data_vencimento=vencimento,
        status="pendente",
    )
    db.add(conta)
    db.flush()
    return conta


def _espelho(db, tenant, usuario, conta, *, status="previsto", documento=None):
    set_current_tenant(UUID(str(tenant.id)))
    lancamento = LancamentoManual(
        tenant_id=tenant.id,
        user_id=usuario.id,
        tipo="saida",
        valor=conta.valor_original,
        descricao="Espelho da conta",
        data_lancamento=conta.data_emissao,
        data_competencia=conta.data_vencimento,
        status=status,
        documento=documento or f"CONTA-PAGAR-{conta.id}",
        observacoes=f"Gerado automaticamente da conta a pagar #{conta.id}",
        gerado_automaticamente=True,
    )
    db.add(lancamento)
    db.flush()
    return lancamento


def _pagamento(db, tenant, usuario, conta, valor, quando):
    set_current_tenant(UUID(str(tenant.id)))
    db.add(
        Pagamento(
            tenant_id=tenant.id,
            user_id=usuario.id,
            conta_pagar_id=conta.id,
            valor_pago=Decimal(valor),
            data_pagamento=quando,
        )
    )
    db.flush()


def _fluxo(db, tenant, usuario, inicio, fim):
    set_current_tenant(UUID(str(tenant.id)))
    return get_fluxo_caixa(
        data_inicio=inicio,
        data_fim=fim,
        db=db,
        current_user_and_tenant=(usuario, UUID(str(tenant.id))),
    )


def test_previsao_da_conta_fica_no_vencimento_sem_espelho_na_emissao(
    db_session, tenant_factory, user_factory
):
    FluxoCaixa.__table__.create(bind=db_session.get_bind(), checkfirst=True)
    tenant = tenant_factory(nome="Fluxo vencimento")
    usuario = user_factory(tenant_id=tenant.id, email="fluxo.vencimento@test.com")
    conta_novembro = _conta(db_session, tenant, usuario)
    _espelho(db_session, tenant, usuario, conta_novembro)
    conta_outubro = _conta(
        db_session, tenant, usuario, valor="30.00", vencimento=date(2026, 10, 20)
    )
    _espelho(db_session, tenant, usuario, conta_outubro, documento="BOLETO-LEGADO")
    db_session.add(
        LancamentoManual(
            tenant_id=tenant.id,
            user_id=usuario.id,
            tipo="saida",
            valor=Decimal("5.00"),
            descricao="Despesa manual independente",
            data_lancamento=date(2026, 10, 12),
            status="previsto",
            documento=f"CONTA-PAGAR-{conta_novembro.id}",
            gerado_automaticamente=False,
        )
    )
    db_session.flush()

    outubro = _fluxo(db_session, tenant, usuario, "2026-10-01", "2026-10-31")
    novembro = _fluxo(db_session, tenant, usuario, "2026-11-01", "2026-11-30")

    assert outubro.total_previsto_saidas == 35.0
    assert novembro.total_previsto_saidas == 100.0
    assert len(outubro.movimentacoes) == 2
    assert any(
        m.origem_tipo == "conta_pagar" and m.origem_id == conta_outubro.id
        for m in outubro.movimentacoes
    )
    assert any(
        m.origem_tipo == "lancamento_manual"
        and m.descricao == "Despesa manual independente"
        for m in outubro.movimentacoes
    )
    assert [(m.origem_tipo, m.origem_id) for m in novembro.movimentacoes] == [
        ("conta_pagar", conta_novembro.id)
    ]


def test_pagamento_parcial_e_integral_usam_baixas_sem_repetir_espelhos(
    db_session, tenant_factory, user_factory
):
    FluxoCaixa.__table__.create(bind=db_session.get_bind(), checkfirst=True)
    tenant = tenant_factory(nome="Fluxo parcial")
    usuario = user_factory(tenant_id=tenant.id, email="fluxo.parcial@test.com")
    conta = _conta(db_session, tenant, usuario)
    _espelho(db_session, tenant, usuario, conta, status="realizado")
    conta.status = "parcial"
    conta.valor_pago = Decimal("40.00")
    _pagamento(db_session, tenant, usuario, conta, "40.00", date(2026, 10, 15))
    db_session.add_all(
        [
            FluxoCaixa(
                tenant_id=tenant.id,
                usuario_id=usuario.id,
                tipo="saida",
                categoria="Fornecedores",
                descricao="Espelho realizado antigo",
                valor=40.0,
                data_movimentacao=datetime(2026, 10, 15),
                status="realizado",
                origem_tipo="conta_pagar",
                origem_id=conta.id,
            ),
            FluxoCaixa(
                tenant_id=tenant.id,
                usuario_id=usuario.id,
                tipo="saida",
                categoria="Fornecedores",
                descricao="Previsão antiga sem desconto da baixa",
                valor=100.0,
                data_prevista=datetime(2026, 11, 10),
                status="previsto",
                origem_tipo="conta_pagar",
                origem_id=conta.id,
            ),
        ]
    )
    db_session.flush()

    outubro = _fluxo(db_session, tenant, usuario, "2026-10-01", "2026-10-31")
    novembro = _fluxo(db_session, tenant, usuario, "2026-11-01", "2026-11-30")
    assert outubro.total_realizado_saidas == 40.0
    assert outubro.movimentacoes[0].data == date(2026, 10, 15)
    assert novembro.total_previsto_saidas == 60.0
    assert len(novembro.movimentacoes) == 1

    conta.status = "pago"
    conta.valor_pago = Decimal("100.00")
    conta.data_pagamento = date(2026, 11, 8)
    _pagamento(db_session, tenant, usuario, conta, "60.00", date(2026, 11, 8))

    outubro = _fluxo(db_session, tenant, usuario, "2026-10-01", "2026-10-31")
    novembro = _fluxo(db_session, tenant, usuario, "2026-11-01", "2026-11-30")
    assert outubro.total_realizado_saidas == 40.0
    assert novembro.total_realizado_saidas == 60.0
    assert novembro.total_previsto_saidas == 0.0
    assert len(novembro.movimentacoes) == 1
    assert novembro.movimentacoes[0].data == date(2026, 11, 8)


def test_conta_historica_paga_sem_baixa_preserva_saida_uma_vez(
    db_session, tenant_factory, user_factory
):
    FluxoCaixa.__table__.create(bind=db_session.get_bind(), checkfirst=True)
    tenant = tenant_factory(nome="Fluxo histórico")
    usuario = user_factory(tenant_id=tenant.id, email="fluxo.historico@test.com")
    conta = _conta(
        db_session, tenant, usuario, valor="50.00", vencimento=date(2026, 10, 20)
    )
    conta.status = "pago"
    conta.valor_pago = Decimal("50.00")
    conta.data_pagamento = date(2026, 10, 21)
    _espelho(db_session, tenant, usuario, conta, status="realizado")

    outubro = _fluxo(db_session, tenant, usuario, "2026-10-01", "2026-10-31")
    assert outubro.total_realizado_saidas == 50.0
    assert len(outubro.movimentacoes) == 1
    assert outubro.movimentacoes[0].data == date(2026, 10, 21)


def test_parcial_legado_com_fluxo_realizado_nao_repete_espelho_manual(
    db_session, tenant_factory, user_factory
):
    FluxoCaixa.__table__.create(bind=db_session.get_bind(), checkfirst=True)
    tenant = tenant_factory(nome="Fluxo parcial legado")
    usuario = user_factory(tenant_id=tenant.id, email="fluxo.parcial.legado@test.com")
    conta = _conta(db_session, tenant, usuario)
    conta.status = "parcial"
    conta.valor_pago = Decimal("40.00")
    _espelho(db_session, tenant, usuario, conta, status="realizado")
    db_session.add(
        FluxoCaixa(
            tenant_id=tenant.id,
            usuario_id=usuario.id,
            tipo="saida",
            categoria="Fornecedores",
            descricao="Baixa parcial legada",
            valor=40.0,
            data_movimentacao=datetime(2026, 10, 15),
            status="realizado",
            origem_tipo="conta_pagar",
            origem_id=conta.id,
        )
    )
    db_session.flush()

    outubro = _fluxo(db_session, tenant, usuario, "2026-10-01", "2026-10-31")
    novembro = _fluxo(db_session, tenant, usuario, "2026-11-01", "2026-11-30")
    assert outubro.total_realizado_saidas == 40.0
    assert len(outubro.movimentacoes) == 1
    assert outubro.movimentacoes[0].data == date(2026, 10, 15)
    assert novembro.total_previsto_saidas == 60.0


def test_espelho_so_e_ignorado_quando_a_conta_pertence_ao_mesmo_tenant(
    db_session, tenant_factory, user_factory
):
    FluxoCaixa.__table__.create(bind=db_session.get_bind(), checkfirst=True)
    tenant_a = tenant_factory(nome="Fluxo A")
    usuario_a = user_factory(tenant_id=tenant_a.id, email="fluxo.a@test.com")
    tenant_b = tenant_factory(nome="Fluxo B")
    usuario_b = user_factory(tenant_id=tenant_b.id, email="fluxo.b@test.com")
    conta_b = _conta(
        db_session, tenant_b, usuario_b, valor="999.00", vencimento=date(2026, 10, 20)
    )
    set_current_tenant(UUID(str(tenant_a.id)))
    db_session.add(
        LancamentoManual(
            tenant_id=tenant_a.id,
            user_id=usuario_a.id,
            tipo="saida",
            valor=Decimal("7.00"),
            descricao="Registro órfão de A",
            data_lancamento=date(2026, 10, 5),
            status="previsto",
            documento=f"CONTA-PAGAR-{conta_b.id}",
            gerado_automaticamente=True,
        )
    )
    db_session.flush()

    outubro_a = _fluxo(db_session, tenant_a, usuario_a, "2026-10-01", "2026-10-31")
    assert outubro_a.total_previsto_saidas == 7.0
    assert len(outubro_a.movimentacoes) == 1
    assert outubro_a.movimentacoes[0].descricao == "Registro órfão de A"
