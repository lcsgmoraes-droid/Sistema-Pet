from datetime import date, datetime
from decimal import Decimal
from pathlib import Path
from uuid import UUID, uuid4

import pytest

from app.campaigns import models as campaign_models  # noqa: F401
from app.financeiro.fluxo_caixa_routes import (
    _mapa_numeros_venda_por_conta,
    get_fluxo_caixa,
)
from app.financeiro_models import ContaPagar, ContaReceber, LancamentoManual
from app.ia.aba5_models import FluxoCaixa
from app.tenancy.context import set_current_tenant
from app.vendas_models import Venda, VendaPagamento
from app.vendas_devolucoes_models import VendaDevolucao


ROOT = Path(__file__).resolve().parents[2]


def test_fluxo_caixa_routes_exige_filtros_explicitos_de_tenant():
    source = (ROOT / "app" / "financeiro" / "fluxo_caixa_routes.py").read_text(
        encoding="utf-8"
    )

    assert "LancamentoManual.tenant_id == tenant_id" in source
    assert "ContaPagar.tenant_id == tenant_id" in source
    assert "ContaReceber.tenant_id == tenant_id" in source
    assert "FluxoCaixa.tenant_id == tenant_id" in source


def _criar_lancamento_manual(
    db_session,
    *,
    tenant_id,
    user_id: int,
    descricao: str,
    valor: str,
    status: str,
) -> LancamentoManual:
    set_current_tenant(UUID(str(tenant_id)))
    lancamento = LancamentoManual(
        tenant_id=UUID(str(tenant_id)),
        user_id=user_id,
        tipo="entrada",
        valor=Decimal(valor),
        descricao=descricao,
        data_lancamento=date(2026, 6, 10),
        status=status,
    )
    db_session.add(lancamento)
    db_session.flush()
    return lancamento


def _criar_venda_finalizada(
    db_session,
    *,
    tenant_id,
    user_id: int,
    numero_venda: str,
    valor: str,
) -> Venda:
    set_current_tenant(UUID(str(tenant_id)))
    venda = Venda(
        tenant_id=UUID(str(tenant_id)),
        user_id=user_id,
        vendedor_id=user_id,
        numero_venda=numero_venda,
        subtotal=Decimal(valor),
        total=Decimal(valor),
        status="finalizada",
        data_venda=datetime(2026, 6, 10, 10, 0, 0),
        canal="loja_fisica",
    )
    db_session.add(venda)
    db_session.flush()
    return venda


def _criar_conta_pagar_pendente(
    db_session,
    *,
    tenant_id,
    user_id: int,
    descricao: str,
    valor: str,
) -> ContaPagar:
    set_current_tenant(UUID(str(tenant_id)))
    conta = ContaPagar(
        tenant_id=UUID(str(tenant_id)),
        user_id=user_id,
        descricao=descricao,
        valor_original=Decimal(valor),
        valor_pago=Decimal("0.00"),
        valor_desconto=Decimal("0.00"),
        valor_juros=Decimal("0.00"),
        valor_multa=Decimal("0.00"),
        valor_final=Decimal(valor),
        data_emissao=date(2026, 6, 1),
        data_vencimento=date(2026, 6, 20),
        status="pendente",
    )
    db_session.add(conta)
    db_session.flush()
    return conta


def _criar_conta_receber_pendente(
    db_session,
    *,
    tenant_id,
    user_id: int,
    descricao: str,
    valor_final: str,
    valor_recebido: str = "0.00",
    status: str = "pendente",
) -> ContaReceber:
    set_current_tenant(UUID(str(tenant_id)))
    conta = ContaReceber(
        tenant_id=UUID(str(tenant_id)),
        user_id=user_id,
        descricao=descricao,
        cliente_id=None,
        categoria_id=None,
        dre_subcategoria_id=1,
        canal="loja_fisica",
        valor_original=Decimal(valor_final),
        valor_recebido=Decimal(valor_recebido),
        valor_desconto=Decimal("0.00"),
        valor_juros=Decimal("0.00"),
        valor_multa=Decimal("0.00"),
        valor_final=Decimal(valor_final),
        data_emissao=date(2026, 6, 1),
        data_vencimento=date(2026, 6, 18),
        status=status,
    )
    db_session.add(conta)
    db_session.flush()
    return conta


def test_fluxo_caixa_filtra_lancamentos_manuais_pelo_tenant(
    db_session, tenant_factory, user_factory
):
    FluxoCaixa.__table__.create(bind=db_session.get_bind(), checkfirst=True)

    tenant_atacadao = tenant_factory(nome="Atacadao")
    usuario_atacadao = user_factory(
        tenant_id=tenant_atacadao.id, email="atacadao.test@example.com"
    )
    funcionario_atacadao = user_factory(
        tenant_id=tenant_atacadao.id, email="funcionario.atacadao.test@example.com"
    )
    tenant_clinica = tenant_factory(nome="Clinica Sao Jose")
    usuario_clinica = user_factory(
        tenant_id=tenant_clinica.id, email="clinica.test@example.com"
    )

    _criar_lancamento_manual(
        db_session,
        tenant_id=tenant_atacadao.id,
        user_id=usuario_atacadao.id,
        descricao="Entrada Atacadao realizada",
        valor="100.00",
        status="realizado",
    )
    _criar_lancamento_manual(
        db_session,
        tenant_id=tenant_atacadao.id,
        user_id=usuario_atacadao.id,
        descricao="Entrada Atacadao prevista",
        valor="50.00",
        status="previsto",
    )
    _criar_lancamento_manual(
        db_session,
        tenant_id=tenant_atacadao.id,
        user_id=funcionario_atacadao.id,
        descricao="Entrada funcionario Atacadao",
        valor="25.00",
        status="realizado",
    )
    _criar_lancamento_manual(
        db_session,
        tenant_id=tenant_clinica.id,
        user_id=usuario_clinica.id,
        descricao="Entrada Clinica realizada",
        valor="999.00",
        status="realizado",
    )
    _criar_lancamento_manual(
        db_session,
        tenant_id=tenant_clinica.id,
        user_id=usuario_clinica.id,
        descricao="Entrada Clinica prevista",
        valor="77.00",
        status="previsto",
    )

    set_current_tenant(UUID(str(tenant_atacadao.id)))
    resposta = get_fluxo_caixa(
        data_inicio="2026-06-01",
        data_fim="2026-06-30",
        db=db_session,
        current_user_and_tenant=(usuario_atacadao, UUID(str(tenant_atacadao.id))),
    )

    descricoes = {mov.descricao for mov in resposta.movimentacoes}

    assert "Entrada Atacadao realizada" in descricoes
    assert "Entrada Atacadao prevista" in descricoes
    assert "Entrada funcionario Atacadao" in descricoes
    assert "Entrada Clinica realizada" not in descricoes
    assert "Entrada Clinica prevista" not in descricoes
    assert resposta.total_realizado_entradas == 125.0
    assert resposta.total_previsto_entradas == 50.0


def test_fluxo_caixa_nao_duplica_venda_quando_existe_lancamento_manual(
    db_session, tenant_factory, user_factory
):
    FluxoCaixa.__table__.create(bind=db_session.get_bind(), checkfirst=True)

    tenant = tenant_factory(nome="Atacadao")
    usuario = user_factory(tenant_id=tenant.id, email="fluxo.duplicidade@test.com")

    venda_com_lancamento = _criar_venda_finalizada(
        db_session,
        tenant_id=tenant.id,
        user_id=usuario.id,
        numero_venda="202606100001",
        valor="100.00",
    )
    _criar_lancamento_manual(
        db_session,
        tenant_id=tenant.id,
        user_id=usuario.id,
        descricao="Venda 202606100001 - A receber",
        valor="100.00",
        status="realizado",
    ).documento = f"VENDA-{venda_com_lancamento.id}"

    venda_sem_lancamento = _criar_venda_finalizada(
        db_session,
        tenant_id=tenant.id,
        user_id=usuario.id,
        numero_venda="202606100002",
        valor="80.00",
    )

    db_session.flush()
    set_current_tenant(UUID(str(tenant.id)))

    resposta = get_fluxo_caixa(
        data_inicio="2026-06-01",
        data_fim="2026-06-30",
        db=db_session,
        current_user_and_tenant=(usuario, UUID(str(tenant.id))),
    )

    movimentos_por_origem = {
        (mov.origem_tipo, mov.origem_id): mov for mov in resposta.movimentacoes
    }

    assert ("venda", venda_com_lancamento.id) not in movimentos_por_origem
    assert any(
        mov.origem_tipo == "lancamento_manual" and mov.valor == 100.0
        for mov in resposta.movimentacoes
    )
    assert ("venda", venda_sem_lancamento.id) in movimentos_por_origem
    assert resposta.total_realizado_entradas == 180.0


@pytest.mark.parametrize("em_dinheiro", [True, False])
def test_fluxo_caixa_preserva_entrada_apos_devolucao_integral(
    db_session, tenant_factory, user_factory, em_dinheiro
):
    FluxoCaixa.__table__.create(bind=db_session.get_bind(), checkfirst=True)
    tenant = tenant_factory(nome="Retorno caixa")
    usuario = user_factory(tenant_id=tenant.id, email="retorno.caixa@test.com")
    venda = _criar_venda_finalizada(
        db_session,
        tenant_id=tenant.id,
        user_id=usuario.id,
        numero_venda="202606100003",
        valor="100.00",
    )
    venda.data_finalizacao = datetime(2026, 6, 10, 10, 5)
    venda.status = "devolvida_total"
    db_session.add(
        VendaPagamento(
            tenant_id=tenant.id,
            venda_id=venda.id,
            forma_pagamento="pix",
            valor=Decimal("100.00"),
            data_pagamento=datetime(2026, 6, 10, 10),
        )
    )
    if em_dinheiro:
        saida = _criar_lancamento_manual(
            db_session,
            tenant_id=tenant.id,
            user_id=usuario.id,
            descricao="Devolução da venda",
            valor="100.00",
            status="realizado",
        )
        saida.tipo = "saida"
        saida.documento = f"DEVOLUCAO-{venda.id}"
    db_session.flush()

    resposta = get_fluxo_caixa(
        data_inicio="2026-06-01",
        data_fim="2026-06-30",
        db=db_session,
        current_user_and_tenant=(usuario, UUID(str(tenant.id))),
    )

    entradas_venda = [
        mov
        for mov in resposta.movimentacoes
        if mov.origem_tipo == "venda" and mov.origem_id == venda.id
    ]
    assert len(entradas_venda) == 1
    assert entradas_venda[0].valor == 100.0
    assert resposta.total_realizado_entradas == 100.0
    assert resposta.total_realizado_saidas == (100.0 if em_dinheiro else 0.0)


def test_fluxo_caixa_nao_inventa_entrada_integral_para_baixa_parcial_devolvida(
    db_session, tenant_factory, user_factory
):
    FluxoCaixa.__table__.create(bind=db_session.get_bind(), checkfirst=True)
    tenant = tenant_factory(nome="Retorno parcial")
    usuario = user_factory(tenant_id=tenant.id, email="retorno.parcial@test.com")
    venda = _criar_venda_finalizada(
        db_session,
        tenant_id=tenant.id,
        user_id=usuario.id,
        numero_venda="202606100004",
        valor="100.00",
    )
    venda.status = "finalizada_devolucao"
    venda.data_finalizacao = datetime(2026, 6, 10, 10, 5)
    db_session.add(
        VendaDevolucao(
            tenant_id=tenant.id,
            venda_id=venda.id,
            chave_operacao=str(uuid4()),
            requisicao_hash="0" * 64,
            resposta={},
            user_id=usuario.id,
            data_competencia=date(2026, 6, 10),
            canal="loja_fisica",
            status_original_venda="baixa_parcial",
            forma_estorno="dinheiro",
            motivo="Teste de caixa",
            valor_devolvido=Decimal("50.00"),
            custo_produtos_estornado=Decimal("0.00"),
            custo_servicos_estornado=Decimal("0.00"),
            custo_pendente=False,
            itens=[],
        )
    )
    db_session.add(
        VendaPagamento(
            tenant_id=tenant.id,
            venda_id=venda.id,
            forma_pagamento="pix",
            valor=Decimal("50.00"),
            data_pagamento=datetime(2026, 6, 10, 10),
        )
    )
    db_session.flush()

    resposta = get_fluxo_caixa(
        data_inicio="2026-06-01",
        data_fim="2026-06-30",
        db=db_session,
        current_user_and_tenant=(usuario, UUID(str(tenant.id))),
    )
    assert not any(
        mov.origem_tipo == "venda" and mov.origem_id == venda.id
        for mov in resposta.movimentacoes
    )


def test_fluxo_caixa_preserva_venda_legada_sem_data_finalizacao_apos_devolucao(
    db_session, tenant_factory, user_factory
):
    FluxoCaixa.__table__.create(bind=db_session.get_bind(), checkfirst=True)
    tenant = tenant_factory(nome="Venda legada devolvida")
    usuario = user_factory(tenant_id=tenant.id, email="legada.devolvida@test.com")
    venda = _criar_venda_finalizada(
        db_session,
        tenant_id=tenant.id,
        user_id=usuario.id,
        numero_venda="202606100011",
        valor="100.00",
    )
    venda.status = "devolvida_total"
    db_session.add(
        VendaDevolucao(
            tenant_id=tenant.id,
            venda_id=venda.id,
            chave_operacao=str(uuid4()),
            requisicao_hash="0" * 64,
            resposta={},
            user_id=usuario.id,
            data_competencia=date(2026, 6, 10),
            canal="loja_fisica",
            status_original_venda="finalizada",
            forma_estorno="dinheiro",
            motivo="Teste de caixa",
            valor_devolvido=Decimal("100.00"),
            custo_produtos_estornado=Decimal("0.00"),
            custo_servicos_estornado=Decimal("0.00"),
            custo_pendente=False,
            itens=[],
        )
    )
    saida = _criar_lancamento_manual(
        db_session,
        tenant_id=tenant.id,
        user_id=usuario.id,
        descricao="Devolução legada",
        valor="100.00",
        status="realizado",
    )
    saida.tipo = "saida"
    saida.documento = f"DEVOLUCAO-{venda.id}"
    db_session.flush()

    resposta = get_fluxo_caixa(
        data_inicio="2026-06-01",
        data_fim="2026-06-30",
        db=db_session,
        current_user_and_tenant=(usuario, UUID(str(tenant.id))),
    )
    assert resposta.total_realizado_entradas == 100.0
    assert resposta.total_realizado_saidas == 100.0


def test_fluxo_caixa_aceita_pagamento_integral_comprovado_sem_status_original(
    db_session, tenant_factory, user_factory
):
    FluxoCaixa.__table__.create(bind=db_session.get_bind(), checkfirst=True)
    tenant = tenant_factory(nome="Pagamento legado")
    usuario = user_factory(tenant_id=tenant.id, email="pagamento.legado@test.com")
    venda = _criar_venda_finalizada(
        db_session,
        tenant_id=tenant.id,
        user_id=usuario.id,
        numero_venda="202606100012",
        valor="100.00",
    )
    venda.status = "devolvida_total"
    db_session.add(
        VendaPagamento(
            tenant_id=tenant.id,
            venda_id=venda.id,
            forma_pagamento="pix",
            valor=Decimal("100.00"),
            data_pagamento=datetime(2026, 6, 10, 10),
        )
    )
    db_session.flush()

    resposta = get_fluxo_caixa(
        data_inicio="2026-06-01",
        data_fim="2026-06-30",
        db=db_session,
        current_user_and_tenant=(usuario, UUID(str(tenant.id))),
    )
    assert resposta.total_realizado_entradas == 100.0


@pytest.mark.parametrize("credito,entrada_esperada", [("100.00", 0.0), ("40.00", 60.0)])
def test_fluxo_caixa_exclui_credito_cliente_do_lancamento_de_venda(
    db_session, tenant_factory, user_factory, credito, entrada_esperada
):
    FluxoCaixa.__table__.create(bind=db_session.get_bind(), checkfirst=True)
    tenant = tenant_factory(nome="Crédito cliente")
    usuario = user_factory(tenant_id=tenant.id, email="credito.fluxo@test.com")
    venda = _criar_venda_finalizada(
        db_session,
        tenant_id=tenant.id,
        user_id=usuario.id,
        numero_venda="202606100005",
        valor="100.00",
    )
    venda.data_finalizacao = datetime(2026, 6, 10, 10, 5)
    lancamento = _criar_lancamento_manual(
        db_session,
        tenant_id=tenant.id,
        user_id=usuario.id,
        descricao="Venda recebida",
        valor="100.00",
        status="realizado",
    )
    lancamento.documento = f"VENDA-{venda.id}"
    db_session.add(
        VendaPagamento(
            tenant_id=tenant.id,
            venda_id=venda.id,
            forma_pagamento="Crédito Cliente",
            valor=Decimal(credito),
            data_pagamento=datetime(2026, 6, 10, 10, 0),
        )
    )
    if credito != "100.00":
        db_session.add(
            VendaPagamento(
                tenant_id=tenant.id,
                venda_id=venda.id,
                forma_pagamento="pix",
                valor=Decimal("60.00"),
                data_pagamento=datetime(2026, 6, 10, 10, 0),
            )
        )
    db_session.flush()

    resposta = get_fluxo_caixa(
        data_inicio="2026-06-01",
        data_fim="2026-06-30",
        db=db_session,
        current_user_and_tenant=(usuario, UUID(str(tenant.id))),
    )
    assert resposta.total_realizado_entradas == entrada_esperada
    assert not any(mov.origem_tipo == "venda" for mov in resposta.movimentacoes)


def test_fluxo_caixa_credito_cliente_em_baixa_parcial_entre_meses(
    db_session, tenant_factory, user_factory
):
    FluxoCaixa.__table__.create(bind=db_session.get_bind(), checkfirst=True)
    tenant = tenant_factory(nome="Baixas em meses")
    usuario = user_factory(tenant_id=tenant.id, email="baixa.meses@test.com")
    venda = _criar_venda_finalizada(
        db_session,
        tenant_id=tenant.id,
        user_id=usuario.id,
        numero_venda="202606100006",
        valor="100.00",
    )
    venda.data_finalizacao = datetime(2026, 7, 1, 10, 5)
    parcial = _criar_lancamento_manual(
        db_session,
        tenant_id=tenant.id,
        user_id=usuario.id,
        descricao="Venda recebida parcialmente",
        valor="50.00",
        status="realizado",
    )
    parcial.documento = f"VENDA-{venda.id}-REALIZADO"
    final = _criar_lancamento_manual(
        db_session,
        tenant_id=tenant.id,
        user_id=usuario.id,
        descricao="Saldo recebido",
        valor="50.00",
        status="realizado",
    )
    final.documento = f"VENDA-{venda.id}"
    final.data_lancamento = date(2026, 7, 1)
    db_session.add_all(
        [
            VendaPagamento(
                tenant_id=tenant.id,
                venda_id=venda.id,
                forma_pagamento="pix",
                valor=Decimal("50.00"),
                data_pagamento=datetime(2026, 6, 10, 10, 0),
            ),
            VendaPagamento(
                tenant_id=tenant.id,
                venda_id=venda.id,
                forma_pagamento="credito_cliente",
                valor=Decimal("50.00"),
                data_pagamento=datetime(2026, 7, 1, 10, 0),
            ),
        ]
    )
    db_session.flush()

    def fluxo(inicio, fim):
        return get_fluxo_caixa(
            data_inicio=inicio,
            data_fim=fim,
            db=db_session,
            current_user_and_tenant=(usuario, UUID(str(tenant.id))),
        )

    junho = fluxo("2026-06-01", "2026-06-30")
    julho = fluxo("2026-07-01", "2026-07-31")
    assert junho.total_realizado_entradas == 50.0
    assert julho.total_realizado_entradas == 0.0


def test_fluxo_caixa_baixas_parciais_cumulativas_nao_repetem_pix(
    db_session, tenant_factory, user_factory
):
    FluxoCaixa.__table__.create(bind=db_session.get_bind(), checkfirst=True)
    tenant = tenant_factory(nome="Baixas cumulativas")
    usuario = user_factory(tenant_id=tenant.id, email="baixa.cumulativa@test.com")
    venda = _criar_venda_finalizada(
        db_session,
        tenant_id=tenant.id,
        user_id=usuario.id,
        numero_venda="202606100007",
        valor="100.00",
    )
    venda.data_finalizacao = datetime(2026, 7, 1, 10, 5)
    for valor, data_lancamento in (
        ("50.00", date(2026, 6, 10)),
        ("70.00", date(2026, 6, 20)),
    ):
        parcial = _criar_lancamento_manual(
            db_session,
            tenant_id=tenant.id,
            user_id=usuario.id,
            descricao="Baixa cumulativa",
            valor=valor,
            status="realizado",
        )
        parcial.documento = f"VENDA-{venda.id}-REALIZADO"
        parcial.data_lancamento = data_lancamento
    final = _criar_lancamento_manual(
        db_session,
        tenant_id=tenant.id,
        user_id=usuario.id,
        descricao="Saldo final",
        valor="30.00",
        status="realizado",
    )
    final.documento = f"VENDA-{venda.id}"
    final.data_lancamento = date(2026, 7, 1)
    for forma, valor, data_pagamento in (
        ("pix", "50.00", datetime(2026, 6, 10, 10)),
        ("credito_cliente", "20.00", datetime(2026, 6, 20, 10)),
        ("pix", "30.00", datetime(2026, 7, 1, 10)),
    ):
        db_session.add(
            VendaPagamento(
                tenant_id=tenant.id,
                venda_id=venda.id,
                forma_pagamento=forma,
                valor=Decimal(valor),
                data_pagamento=data_pagamento,
            )
        )
    db_session.flush()

    def entradas(inicio, fim):
        resposta = get_fluxo_caixa(
            data_inicio=inicio,
            data_fim=fim,
            db=db_session,
            current_user_and_tenant=(usuario, UUID(str(tenant.id))),
        )
        return resposta.total_realizado_entradas

    assert entradas("2026-06-01", "2026-06-30") == 50.0
    assert entradas("2026-07-01", "2026-07-31") == 30.0


def test_fluxo_caixa_fallback_sem_lancamento_exclui_credito_cliente(
    db_session, tenant_factory, user_factory
):
    FluxoCaixa.__table__.create(bind=db_session.get_bind(), checkfirst=True)
    tenant = tenant_factory(nome="Fallback crédito")
    usuario = user_factory(tenant_id=tenant.id, email="fallback.credito@test.com")
    venda = _criar_venda_finalizada(
        db_session,
        tenant_id=tenant.id,
        user_id=usuario.id,
        numero_venda="202606100008",
        valor="100.00",
    )
    db_session.add(
        VendaPagamento(
            tenant_id=tenant.id,
            venda_id=venda.id,
            forma_pagamento="Crédito Cliente",
            valor=Decimal("100.00"),
            data_pagamento=datetime(2026, 6, 10, 10),
        )
    )
    db_session.flush()

    resposta = get_fluxo_caixa(
        data_inicio="2026-06-01",
        data_fim="2026-06-30",
        db=db_session,
        current_user_and_tenant=(usuario, UUID(str(tenant.id))),
    )
    assert resposta.total_realizado_entradas == 0.0


@pytest.mark.parametrize(
    "cashback,entrada_esperada", [("100.00", 0.0), ("40.00", 60.0)]
)
def test_fluxo_caixa_cashback_nao_cria_entrada_nem_saida_ficticias(
    db_session, tenant_factory, user_factory, cashback, entrada_esperada
):
    FluxoCaixa.__table__.create(bind=db_session.get_bind(), checkfirst=True)
    tenant = tenant_factory(nome="Cashback no caixa")
    usuario = user_factory(tenant_id=tenant.id, email="cashback.fluxo@test.com")
    venda = _criar_venda_finalizada(
        db_session,
        tenant_id=tenant.id,
        user_id=usuario.id,
        numero_venda="202606100009",
        valor="100.00",
    )
    venda.data_finalizacao = datetime(2026, 6, 10, 10, 5)
    entrada = _criar_lancamento_manual(
        db_session,
        tenant_id=tenant.id,
        user_id=usuario.id,
        descricao="Venda recebida",
        valor="100.00",
        status="realizado",
    )
    entrada.documento = f"VENDA-{venda.id}"
    espelho = _criar_lancamento_manual(
        db_session,
        tenant_id=tenant.id,
        user_id=usuario.id,
        descricao="Cashback resgatado na venda",
        valor=cashback,
        status="realizado",
    )
    espelho.tipo = "saida"
    espelho.documento = f"CASHBACK-{venda.numero_venda}"
    espelho.gerado_automaticamente = True
    db_session.add(
        VendaPagamento(
            tenant_id=tenant.id,
            venda_id=venda.id,
            forma_pagamento="Cashback",
            valor=Decimal(cashback),
            data_pagamento=datetime(2026, 6, 10, 10),
        )
    )
    if cashback != "100.00":
        db_session.add(
            VendaPagamento(
                tenant_id=tenant.id,
                venda_id=venda.id,
                forma_pagamento="pix",
                valor=Decimal("60.00"),
                data_pagamento=datetime(2026, 6, 10, 10),
            )
        )
    db_session.flush()

    resposta = get_fluxo_caixa(
        data_inicio="2026-06-01",
        data_fim="2026-06-30",
        db=db_session,
        current_user_and_tenant=(usuario, UUID(str(tenant.id))),
    )
    assert resposta.total_realizado_entradas == entrada_esperada
    assert resposta.total_realizado_saidas == 0.0


def test_fluxo_caixa_nao_omite_saida_cashback_sem_pagamento_do_tenant(
    db_session, tenant_factory, user_factory
):
    FluxoCaixa.__table__.create(bind=db_session.get_bind(), checkfirst=True)
    tenant = tenant_factory(nome="Cashback sem comprovante")
    usuario = user_factory(tenant_id=tenant.id, email="cashback.sem.prova@test.com")
    outro_tenant = tenant_factory(nome="Outro cashback")
    outro_usuario = user_factory(
        tenant_id=outro_tenant.id, email="cashback.outro@test.com"
    )
    venda = _criar_venda_finalizada(
        db_session,
        tenant_id=tenant.id,
        user_id=usuario.id,
        numero_venda="202606100010",
        valor="100.00",
    )
    outra_venda = _criar_venda_finalizada(
        db_session,
        tenant_id=outro_tenant.id,
        user_id=outro_usuario.id,
        numero_venda=venda.numero_venda,
        valor="100.00",
    )
    espelho_sem_prova = _criar_lancamento_manual(
        db_session,
        tenant_id=tenant.id,
        user_id=usuario.id,
        descricao="Saída legada a conciliar",
        valor="100.00",
        status="realizado",
    )
    espelho_sem_prova.tipo = "saida"
    espelho_sem_prova.documento = f"CASHBACK-{venda.numero_venda}"
    espelho_sem_prova.gerado_automaticamente = True
    set_current_tenant(UUID(str(outro_tenant.id)))
    db_session.add(
        VendaPagamento(
            tenant_id=outro_tenant.id,
            venda_id=outra_venda.id,
            forma_pagamento="cashback",
            valor=Decimal("100.00"),
            data_pagamento=datetime(2026, 6, 10, 10),
        )
    )
    db_session.flush()
    set_current_tenant(UUID(str(tenant.id)))

    resposta = get_fluxo_caixa(
        data_inicio="2026-06-01",
        data_fim="2026-06-30",
        db=db_session,
        current_user_and_tenant=(usuario, UUID(str(tenant.id))),
    )
    assert resposta.total_realizado_saidas == 100.0


def test_fluxo_caixa_inclui_contas_pagar_do_tenant_mesmo_de_outro_usuario(
    db_session, tenant_factory, user_factory
):
    FluxoCaixa.__table__.create(bind=db_session.get_bind(), checkfirst=True)

    tenant = tenant_factory(nome="Atacadao")
    gestor = user_factory(tenant_id=tenant.id, email="gestor.fluxo@test.com")
    financeiro = user_factory(tenant_id=tenant.id, email="financeiro.fluxo@test.com")
    outro_tenant = tenant_factory(nome="Clinica Sao Jose")
    usuario_outro = user_factory(
        tenant_id=outro_tenant.id, email="financeiro.outro@test.com"
    )

    conta_tenant = _criar_conta_pagar_pendente(
        db_session,
        tenant_id=tenant.id,
        user_id=financeiro.id,
        descricao="Fornecedor do Atacadao",
        valor="321.45",
    )
    _criar_conta_pagar_pendente(
        db_session,
        tenant_id=outro_tenant.id,
        user_id=usuario_outro.id,
        descricao="Fornecedor de outro tenant",
        valor="999.99",
    )

    set_current_tenant(UUID(str(tenant.id)))
    resposta = get_fluxo_caixa(
        data_inicio="2026-06-01",
        data_fim="2026-06-30",
        db=db_session,
        current_user_and_tenant=(gestor, UUID(str(tenant.id))),
    )

    movimentos_por_origem = {
        (mov.origem_tipo, mov.origem_id): mov for mov in resposta.movimentacoes
    }

    assert ("conta_pagar", conta_tenant.id) in movimentos_por_origem
    assert movimentos_por_origem[("conta_pagar", conta_tenant.id)].valor == 321.45
    assert all(mov.valor != 999.99 for mov in resposta.movimentacoes)


def test_fluxo_caixa_inclui_contas_receber_abertas_sem_duplicar_fluxo_previsto(
    db_session, tenant_factory, user_factory
):
    FluxoCaixa.__table__.create(bind=db_session.get_bind(), checkfirst=True)

    tenant = tenant_factory(nome="Atacadao")
    gestor = user_factory(tenant_id=tenant.id, email="gestor.receber.fluxo@test.com")
    financeiro = user_factory(
        tenant_id=tenant.id, email="financeiro.receber.fluxo@test.com"
    )
    outro_tenant = tenant_factory(nome="Clinica Sao Jose")
    usuario_outro = user_factory(
        tenant_id=outro_tenant.id, email="financeiro.receber.outro@test.com"
    )

    conta_tenant = _criar_conta_receber_pendente(
        db_session,
        tenant_id=tenant.id,
        user_id=financeiro.id,
        descricao="Cliente Atacadao parcial",
        valor_final="210.00",
        valor_recebido="60.00",
        status="parcial",
    )
    conta_ja_lancada = _criar_conta_receber_pendente(
        db_session,
        tenant_id=tenant.id,
        user_id=financeiro.id,
        descricao="Cliente Atacadao ja no fluxo",
        valor_final="50.00",
    )
    _criar_conta_receber_pendente(
        db_session,
        tenant_id=outro_tenant.id,
        user_id=usuario_outro.id,
        descricao="Cliente de outro tenant",
        valor_final="999.99",
    )

    set_current_tenant(UUID(str(tenant.id)))
    db_session.add(
        FluxoCaixa(
            tenant_id=UUID(str(tenant.id)),
            usuario_id=financeiro.id,
            tipo="entrada",
            categoria="Recebimentos",
            descricao="Previsao ja existente",
            valor=50.0,
            data_prevista=datetime(2026, 6, 18, 10, 0, 0),
            status="previsto",
            origem_tipo="conta_receber",
            origem_id=conta_ja_lancada.id,
        )
    )
    db_session.flush()

    set_current_tenant(UUID(str(tenant.id)))
    resposta = get_fluxo_caixa(
        data_inicio="2026-06-01",
        data_fim="2026-06-30",
        db=db_session,
        current_user_and_tenant=(gestor, UUID(str(tenant.id))),
    )

    movimentos_por_origem = [
        mov for mov in resposta.movimentacoes if mov.origem_tipo == "conta_receber"
    ]
    movimentos_chave = {
        (mov.origem_tipo, mov.origem_id): mov for mov in movimentos_por_origem
    }

    assert ("conta_receber", conta_tenant.id) in movimentos_chave
    assert movimentos_chave[("conta_receber", conta_tenant.id)].valor == 150.0
    assert movimentos_chave[("conta_receber", conta_tenant.id)].status == "previsto"
    assert movimentos_chave[("conta_receber", conta_tenant.id)].tipo == "entrada"
    assert (
        sum(1 for mov in movimentos_por_origem if mov.origem_id == conta_ja_lancada.id)
        == 1
    )
    assert all(mov.valor != 999.99 for mov in resposta.movimentacoes)


def test_fluxo_caixa_busca_numeros_de_venda_das_contas_em_lote_e_por_tenant(
    db_session, tenant_factory, user_factory
):
    tenant = tenant_factory(nome="Atacadao")
    usuario = user_factory(tenant_id=tenant.id, email="fluxo.lote@test.com")
    outro_tenant = tenant_factory(nome="Clinica Sao Jose")
    usuario_outro = user_factory(
        tenant_id=outro_tenant.id, email="fluxo.lote.outro@test.com"
    )

    venda = _criar_venda_finalizada(
        db_session,
        tenant_id=tenant.id,
        user_id=usuario.id,
        numero_venda="VENDA-LOTE-1",
        valor="50.00",
    )
    conta = _criar_conta_receber_pendente(
        db_session,
        tenant_id=tenant.id,
        user_id=usuario.id,
        descricao="Conta com venda",
        valor_final="50.00",
    )
    conta.venda_id = venda.id

    venda_outro = _criar_venda_finalizada(
        db_session,
        tenant_id=outro_tenant.id,
        user_id=usuario_outro.id,
        numero_venda="VENDA-OUTRO-TENANT",
        valor="70.00",
    )
    conta_outro = _criar_conta_receber_pendente(
        db_session,
        tenant_id=outro_tenant.id,
        user_id=usuario_outro.id,
        descricao="Conta de outro tenant",
        valor_final="70.00",
    )
    conta_outro.venda_id = venda_outro.id
    db_session.flush()

    set_current_tenant(UUID(str(tenant.id)))
    mapa = _mapa_numeros_venda_por_conta(
        db_session, tenant.id, [conta.id, conta_outro.id]
    )

    assert mapa == {conta.id: "VENDA-LOTE-1"}
