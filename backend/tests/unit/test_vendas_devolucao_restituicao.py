"""Rateio e reposição dos saldos originais em devoluções parciais."""

from datetime import datetime, timedelta, timezone
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import MagicMock
from uuid import uuid4

import pytest
from fastapi import HTTPException

from app.campaigns.cashback_wallet import replay_cashback_transactions
from app.campaigns.models import CashbackSourceTypeEnum, CashbackTransaction
from app.vendas import devolucao_restituicao as service
from app.vendas.devolucao_valores import CotacaoDevolucao
from app.vendas.devolucoes_routes import (
    _hash_requisicao_devolucao,
    prever_devolucao,
    registrar_devolucao,
)
from app.vendas_devolucoes_models import VendaDevolucao
from app.vendas_models import Venda, VendaItem
from app.financeiro_models import ContaReceber, LancamentoManual
from app.models import Cliente, CreditoLog
from sqlalchemy import Integer, MetaData, create_engine
from sqlalchemy.orm import Session

NOW = datetime.now(timezone.utc)
TENANT = uuid4()


def pagamento(forma, valor, **kwargs):
    return SimpleNamespace(
        tenant_id=TENANT,
        forma_pagamento=forma,
        valor=Decimal(valor),
        status="aprovado",
        **kwargs,
    )


def venda_com_pagamentos(*pagamentos, total="100"):
    return SimpleNamespace(
        id=8, cliente_id=47, total=Decimal(total), pagamentos=list(pagamentos)
    )


def cotacao(valor, anterior="0"):
    return CotacaoDevolucao(Decimal(valor), Decimal(anterior), (Decimal(valor),))


def tx(
    id, amount, source_type, source_id=None, *, expires_at=None, origin_credit_id=None
):
    return SimpleNamespace(
        id=id,
        amount=Decimal(amount),
        source_type=source_type,
        source_id=source_id,
        tenant_id=TENANT,
        customer_id=47,
        expires_at=expires_at,
        origin_credit_id=origin_credit_id,
        tx_type="credit" if Decimal(amount) >= 0 else "debit",
        created_at=NOW - timedelta(days=3) + timedelta(seconds=id),
    )


def fake_cashback(monkeypatch, transactions):
    db = MagicMock()
    db.query.return_value.filter.return_value.order_by.return_value.all.return_value = (
        transactions
    )
    monkeypatch.setattr(
        service,
        "get_cashback_wallet",
        lambda *_a, **_k: replay_cashback_transactions(transactions, as_of=NOW),
    )
    monkeypatch.setattr(service, "_revoked_campaign_origins", lambda *_a, **_k: set())
    monkeypatch.setattr(service, "lock_cashback_customer", MagicMock())
    return db


@pytest.mark.parametrize(
    "cashback,credito,restante",
    [
        ("20", "30", "50"),
        ("0.01", "0.01", "0.01"),
        ("50", "50", "0"),
        ("100", "0", "0"),
    ],
)
def test_rateio_cumulativo_preserva_centavos_e_nao_diminui_saldo(
    cashback, credito, restante
):
    pesos = tuple(Decimal(v) for v in (cashback, credito, restante))
    anterior = {
        "cashback": Decimal(0),
        "credito_cliente": Decimal(0),
        "valor_restante": Decimal(0),
    }
    for centavos in range(1, int(sum(pesos) * 100) + 1):
        valor = Decimal(centavos) / 100
        atual = service.ratear_restituicao_acumulada(valor, *pesos)
        assert sum(atual.values()) == valor
        assert all(atual[campo] >= anterior[campo] for campo in anterior)
        if pesos[2] == 0:
            assert atual["valor_restante"] == 0
        anterior = atual
    assert tuple(anterior.values()) == pesos


def test_credito_original_volta_parcialmente_sem_converter_em_dinheiro():
    venda = venda_com_pagamentos(
        pagamento("Crédito Cliente", "60"), pagamento("dinheiro", "40")
    )
    primeira = service.cotar_restituicao(
        MagicMock(),
        tenant_id=TENANT,
        venda=venda,
        cotacao=cotacao("25"),
        eventos_anteriores=[],
        devolver_na_origem=True,
    )
    assert primeira.resposta() == {
        "cashback": 0,
        "credito_cliente": 15,
        "valor_restante": 10,
        "cashback_expirado": 0,
    }
    evento = SimpleNamespace(
        valor_devolvido=25, resposta={"restituicao": primeira.resposta()}
    )
    segunda = service.cotar_restituicao(
        MagicMock(),
        tenant_id=TENANT,
        venda=venda,
        cotacao=cotacao("75", "25"),
        eventos_anteriores=[evento],
        devolver_na_origem=True,
    )
    assert segunda.credito_cliente == Decimal("45")
    assert segunda.valor_restante == Decimal("30")


def test_frete_retido_preserva_parcela_original_dos_pagamentos():
    venda = venda_com_pagamentos(
        pagamento("credito_cliente", "50"), pagamento("pix", "50")
    )
    resultado = service.cotar_restituicao(
        MagicMock(),
        tenant_id=TENANT,
        venda=venda,
        cotacao=cotacao("90"),
        eventos_anteriores=[],
        devolver_na_origem=True,
    )
    assert resultado.credito_cliente == Decimal("45")
    assert resultado.valor_restante == Decimal("45")


def test_restituicao_usa_saldo_liquido_apos_estorno_e_nova_baixa():
    venda = venda_com_pagamentos(
        pagamento("credito_cliente", "40"),
        pagamento("pix", "60", baixa_lote_id=99),
        pagamento("pix", "-60", baixa_lote_id=99),
        pagamento("dinheiro", "60", baixa_lote_id=100),
    )

    resultado = service.cotar_restituicao(
        MagicMock(),
        tenant_id=TENANT,
        venda=venda,
        cotacao=cotacao("100"),
        eventos_anteriores=[],
        devolver_na_origem=True,
    )

    assert resultado.credito_cliente == Decimal("40")
    assert resultado.valor_restante == Decimal("60")


def test_pagamento_negativo_sem_lote_comprovado_continua_bloqueado():
    venda = venda_com_pagamentos(pagamento("pix", "-60"))

    with pytest.raises(HTTPException) as erro:
        service.validar_opcao_restituicao(venda, TENANT)

    assert erro.value.status_code == 409


def test_cashback_restituido_guarda_lote_e_validade_original(monkeypatch):
    validade = NOW + timedelta(days=2)
    transacoes = [
        tx(1, "20", CashbackSourceTypeEnum.manual, expires_at=validade),
        tx(2, "-20", CashbackSourceTypeEnum.redemption, 8),
    ]
    db = fake_cashback(monkeypatch, transacoes)
    venda = venda_com_pagamentos(pagamento("Cashback", "20"), pagamento("pix", "80"))
    resultado = service.cotar_restituicao(
        db,
        tenant_id=TENANT,
        venda=venda,
        cotacao=cotacao("50"),
        eventos_anteriores=[],
        devolver_na_origem=True,
        bloquear=True,
    )
    assert resultado.cashback == Decimal("10")
    assert resultado.valor_restante == Decimal("40")
    assert resultado.cashback_expirado == 0
    service.registrar_restituicao_cashback(
        db,
        tenant_id=TENANT,
        venda=venda,
        evento_devolucao=SimpleNamespace(id=12),
        restituicao=resultado,
    )
    linha = db.add.call_args.args[0]
    assert (
        linha.amount,
        linha.source_id,
        linha.origin_credit_id,
        linha.expires_at,
    ) == (Decimal("10"), 2, 1, validade)
    assert linha.tenant_id == TENANT
    service.lock_cashback_customer.assert_called_once_with(
        db, tenant_id=TENANT, customer_id=47
    )
    db.commit.assert_not_called()


def test_cashback_vencido_aparece_na_previa_e_nao_renova_validade(monkeypatch):
    validade = NOW - timedelta(days=1)
    transacoes = [
        tx(1, "20", CashbackSourceTypeEnum.manual, expires_at=validade),
        tx(2, "-20", CashbackSourceTypeEnum.redemption, 8),
    ]
    db = fake_cashback(monkeypatch, transacoes)
    venda = venda_com_pagamentos(pagamento("Cashback", "100"), total="100")
    venda.pagamentos[0].valor = Decimal("20")
    venda.total = Decimal("20")
    resultado = service.cotar_restituicao(
        db,
        tenant_id=TENANT,
        venda=venda,
        cotacao=cotacao("20"),
        eventos_anteriores=[],
        devolver_na_origem=True,
    )
    assert resultado.cashback_expirado == Decimal("20")
    assert resultado.valor_restante == 0
    lote = resultado.lotes[0]
    restaurada = tx(
        3,
        "20",
        CashbackSourceTypeEnum.reversal,
        2,
        expires_at=lote["expires_at"],
        origin_credit_id=lote["origem_id"],
    )
    restaurada.created_at = NOW
    assert (
        replay_cashback_transactions([*transacoes, restaurada], as_of=NOW).available
        == 0
    )


def test_segunda_devolucao_cashback_restitui_so_saldo_sem_duplicar_lote(monkeypatch):
    validade = NOW + timedelta(days=2)
    transacoes = [
        tx(1, "20", CashbackSourceTypeEnum.manual, expires_at=validade),
        tx(2, "-20", CashbackSourceTypeEnum.redemption, 8),
        tx(
            3,
            "10",
            CashbackSourceTypeEnum.reversal,
            2,
            expires_at=validade,
            origin_credit_id=1,
        ),
    ]
    db = fake_cashback(monkeypatch, transacoes)
    evento = SimpleNamespace(
        valor_devolvido=50,
        resposta={
            "restituicao": {"cashback": 10, "credito_cliente": 0, "valor_restante": 40}
        },
    )
    venda = venda_com_pagamentos(pagamento("Cashback", "20"), pagamento("pix", "80"))
    resultado = service.cotar_restituicao(
        db,
        tenant_id=TENANT,
        venda=venda,
        cotacao=cotacao("50", "50"),
        eventos_anteriores=[evento],
        devolver_na_origem=True,
    )
    assert resultado.cashback == 10
    assert sum(lote["valor"] for lote in resultado.lotes) == 10


def test_cashback_refinalizado_ignora_resgate_integralmente_compensado(monkeypatch):
    transacoes = [
        tx(1, "20", CashbackSourceTypeEnum.manual),
        tx(2, "-20", CashbackSourceTypeEnum.redemption, 8),
        tx(3, "20", CashbackSourceTypeEnum.reversal, 2, origin_credit_id=1),
        tx(4, "-20", CashbackSourceTypeEnum.redemption, 8),
    ]
    db = fake_cashback(monkeypatch, transacoes)
    venda = venda_com_pagamentos(pagamento("Cashback", "20"), total="20")
    resultado = service.cotar_restituicao(
        db,
        tenant_id=TENANT,
        venda=venda,
        cotacao=cotacao("20"),
        eventos_anteriores=[],
        devolver_na_origem=True,
    )
    assert resultado.cashback == 20
    assert [lote["resgate_id"] for lote in resultado.lotes] == [4]


@pytest.mark.parametrize(
    "transacoes", [[], [tx(2, "-20", CashbackSourceTypeEnum.redemption, 8)]]
)
def test_cashback_sem_resgate_ou_lotes_comprovados_bloqueia_antes_de_escrever(
    monkeypatch, transacoes
):
    db = fake_cashback(monkeypatch, transacoes)
    venda = venda_com_pagamentos(pagamento("Cashback", "20"), total="20")
    with pytest.raises(HTTPException) as erro:
        service.cotar_restituicao(
            db,
            tenant_id=TENANT,
            venda=venda,
            cotacao=cotacao("20"),
            eventos_anteriores=[],
            devolver_na_origem=True,
        )
    assert erro.value.detail["acao"] == "abrir_beneficios"
    db.add.assert_not_called()


def test_cashback_revogado_nao_recria_beneficio(monkeypatch):
    transacoes = [
        tx(1, "20", CashbackSourceTypeEnum.campaign, 9),
        tx(2, "-20", CashbackSourceTypeEnum.redemption, 8),
    ]
    db = fake_cashback(monkeypatch, transacoes)
    monkeypatch.setattr(service, "_revoked_campaign_origins", lambda *_a, **_k: {1})
    with pytest.raises(HTTPException) as erro:
        service.cotar_restituicao(
            db,
            tenant_id=TENANT,
            venda=venda_com_pagamentos(pagamento("Cashback", "20"), total="20"),
            cotacao=cotacao("20"),
            eventos_anteriores=[],
            devolver_na_origem=True,
        )
    assert "revogado" in erro.value.detail["mensagem"]
    db.add.assert_not_called()


def test_pagamentos_de_outro_tenant_e_recusados_nao_criam_restituicao():
    outro = pagamento("Cashback", "100")
    outro.tenant_id = uuid4()
    recusado = pagamento("Crédito Cliente", "100")
    recusado.status = "recusado"
    venda = venda_com_pagamentos(outro, recusado, pagamento("pix", "100"))
    db = MagicMock()
    resultado = service.cotar_restituicao(
        db, tenant_id=TENANT, venda=venda, cotacao=cotacao("50"), eventos_anteriores=[]
    )
    assert resultado.valor_restante == 50
    db.query.assert_not_called()


@pytest.mark.parametrize(
    "evento",
    [
        SimpleNamespace(valor_devolvido=50, resposta={}),
        SimpleNamespace(
            valor_devolvido=50,
            resposta={
                "restituicao": {
                    "cashback": 0,
                    "credito_cliente": 10,
                    "valor_restante": 10,
                }
            },
        ),
    ],
)
def test_historico_anterior_sem_rateio_confiavel_nao_gera_credito(evento):
    with pytest.raises(HTTPException) as erro:
        service.cotar_restituicao(
            MagicMock(),
            tenant_id=TENANT,
            venda=venda_com_pagamentos(pagamento("credito_cliente", "100")),
            cotacao=cotacao("50", "50"),
            eventos_anteriores=[evento],
            devolver_na_origem=True,
        )
    assert erro.value.detail["codigo"] == "DEVOLUCAO_ORIGEM_INCONSISTENTE"


def test_flag_origem_integra_hash_e_preserva_hash_legado_sem_flag():
    dados = {
        "itens": [{"item_id": 3, "quantidade": 1}],
        "motivo": "Troca",
        "gerar_credito": True,
    }
    sem = _hash_requisicao_devolucao(8, dados, dados["itens"])
    assert (
        _hash_requisicao_devolucao(
            8, {**dados, "devolver_na_origem": False}, dados["itens"]
        )
        == sem
    )
    assert (
        _hash_requisicao_devolucao(
            8, {**dados, "devolver_na_origem": True}, dados["itens"]
        )
        != sem
    )


def _db_rota(venda, item, cliente, eventos):
    consultas = {}
    for modelo, resultado in (
        (Venda, venda),
        (VendaItem, [item]),
        (VendaDevolucao, eventos),
        (Cliente, cliente),
        (ContaReceber, []),
    ):
        consulta = MagicMock()
        consulta.filter_by.return_value = consulta
        consulta.filter.return_value = consulta
        consulta.with_for_update.return_value = consulta
        consulta.populate_existing.return_value = consulta
        consulta.first.return_value = (
            resultado if not isinstance(resultado, list) else None
        )
        consulta.all.side_effect = lambda resultado=resultado: (
            list(resultado) if isinstance(resultado, list) else []
        )
        consultas[modelo] = consulta
    db = MagicMock()
    db.query.side_effect = lambda modelo: consultas[modelo]

    def add(obj):
        if isinstance(obj, VendaDevolucao):
            obj.id = len(eventos) + 1
            eventos.append(obj)

    db.add.side_effect = add
    consultas[VendaDevolucao].first.side_effect = lambda: (
        eventos[0] if eventos else None
    )
    return db


def test_rota_credito_original_sem_caixa_e_replay_nao_duplica_saldo(monkeypatch):
    monkeypatch.setattr(
        "app.campaigns.sale_return_service.preflight_purchase_benefits_on_return",
        lambda *_a, **_k: None,
    )
    monkeypatch.setattr(
        "app.campaigns.sale_return_service.reconcile_purchase_benefits_on_return",
        lambda *_a, **_k: None,
    )
    cliente = SimpleNamespace(id=47, nome="Cliente", credito=Decimal("5"))
    venda = venda_com_pagamentos(pagamento("Crédito Cliente", "100"))
    venda.status = "finalizada"
    venda.numero_venda = "VEN-8"
    venda.observacoes = ""
    item = SimpleNamespace(
        id=3,
        tipo="servico",
        produto_id=None,
        produto=None,
        servico_descricao="Serviço",
        quantidade=2,
        subtotal=Decimal("100"),
        preco_unitario=Decimal("50"),
    )
    eventos = []
    db = _db_rota(venda, item, cliente, eventos)
    dados = {
        "itens": [{"item_id": 3, "quantidade": 1}],
        "motivo": "Troca",
        "gerar_credito": False,
        "devolver_na_origem": True,
        "chave_operacao": str(uuid4()),
    }
    user = SimpleNamespace(id=22, nome="Atendente")
    previa = prever_devolucao(8, dados, db=db, user_and_tenant=(user, TENANT))
    assert previa["restituicao"]["credito_cliente"] == 50
    assert previa["restituicao"]["valor_restante"] == 0
    db.add.assert_not_called()
    dados["restituicao_prevista"] = previa["restituicao"]
    primeira = registrar_devolucao(
        8,
        {**dados, "valor_previsto": previa["valor_total_devolucao"]},
        db=db,
        user_and_tenant=(user, TENANT),
    )
    assert cliente.credito == Decimal("55")
    assert primeira["tipo_devolucao"] == "Restituição na origem"
    assert eventos[0].forma_estorno == "origem"
    assert (
        sum(isinstance(call.args[0], CreditoLog) for call in db.add.call_args_list) == 1
    )
    assert not any(
        isinstance(call.args[0], LancamentoManual) for call in db.add.call_args_list
    )
    repetida = registrar_devolucao(8, dados, db=db, user_and_tenant=(user, TENANT))
    assert repetida == primeira
    assert cliente.credito == Decimal("55")
    db.commit.assert_called_once()


def test_reutilizar_chave_com_nova_flag_nao_restitui_saldo(monkeypatch):
    venda = venda_com_pagamentos(pagamento("credito_cliente", "100"))
    venda.status = "finalizada"
    item = SimpleNamespace(id=3)
    cliente = SimpleNamespace(id=47, credito=Decimal("0"))
    dados = {
        "itens": [{"item_id": 3, "quantidade": 1}],
        "motivo": "Troca",
        "gerar_credito": True,
        "chave_operacao": str(uuid4()),
    }
    evento = SimpleNamespace(
        venda_id=8,
        requisicao_hash=_hash_requisicao_devolucao(8, dados, dados["itens"]),
        resposta={},
    )
    db = _db_rota(venda, item, cliente, [evento])
    with pytest.raises(HTTPException) as erro:
        registrar_devolucao(
            8,
            {**dados, "devolver_na_origem": True},
            db=db,
            user_and_tenant=(SimpleNamespace(id=22, nome="Atendente"), TENANT),
        )
    assert "dados diferentes" in erro.value.detail
    assert cliente.credito == 0
    db.add.assert_not_called()
    db.rollback.assert_called_once()


@pytest.mark.parametrize(
    "prevista",
    [
        None,
        {},
        {
            "cashback": 0,
            "credito_cliente": 0,
            "valor_restante": 50,
            "cashback_expirado": 0,
        },
        {
            "cashback": 0,
            "credito_cliente": "NaN",
            "valor_restante": 0,
            "cashback_expirado": 0,
        },
    ],
)
def test_confirmacao_rejeita_divisao_diferente_ou_ausente(prevista):
    with pytest.raises(HTTPException) as erro:
        service.validar_restituicao_prevista(
            service.RestituicaoDevolucao(credito_cliente=Decimal("50")),
            prevista,
            exigir=True,
        )
    assert erro.value.detail["codigo"] == "DEVOLUCAO_PREVIA_ALTERADA"


def test_cashback_que_expira_entre_previa_e_confirmacao_exige_reconfirmacao():
    atual = service.RestituicaoDevolucao(
        cashback=Decimal("20"), cashback_expirado=Decimal("20")
    )
    previa = {
        "cashback": 20,
        "credito_cliente": 0,
        "valor_restante": 0,
        "cashback_expirado": 0,
    }
    with pytest.raises(HTTPException) as erro:
        service.validar_restituicao_prevista(atual, previa, exigir=True)
    assert erro.value.detail["acao"] == "atualizar_previa"


def test_rota_mista_restitui_credito_original_e_apenas_parcela_comum_no_caixa(
    monkeypatch,
):
    monkeypatch.setattr(
        "app.campaigns.sale_return_service.preflight_purchase_benefits_on_return",
        lambda *_a, **_k: None,
    )
    monkeypatch.setattr(
        "app.campaigns.sale_return_service.reconcile_purchase_benefits_on_return",
        lambda *_a, **_k: None,
    )
    monkeypatch.setattr(
        "app.vendas.devolucoes_routes.buscar_caixa_acessivel",
        lambda *_a, **_k: (SimpleNamespace(status="aberto"), None),
    )
    monkeypatch.setattr(
        "app.vendas.devolucoes_routes._buscar_categoria_devolucoes",
        lambda *_a, **_k: SimpleNamespace(id=18),
    )
    registrar_caixa = MagicMock(return_value={"movimentacao_id": 44})
    monkeypatch.setattr(
        "app.vendas.devolucoes_routes.CaixaService.registrar_devolucao", registrar_caixa
    )
    cliente = SimpleNamespace(id=47, nome="Cliente", credito=Decimal("5"))
    venda = venda_com_pagamentos(
        pagamento("credito_cliente", "40"), pagamento("pix", "60")
    )
    venda.status = "finalizada"
    venda.numero_venda = "VEN-8"
    venda.observacoes = ""
    venda.cliente = cliente
    item = SimpleNamespace(
        id=3,
        tipo="servico",
        produto_id=None,
        produto=None,
        servico_descricao="Serviço",
        quantidade=2,
        subtotal=Decimal("100"),
        preco_unitario=Decimal("50"),
    )
    eventos = []
    db = _db_rota(venda, item, cliente, eventos)
    dados = {
        "itens": [{"item_id": 3, "quantidade": 1}],
        "motivo": "Troca",
        "caixa_id": 9,
        "gerar_credito": False,
        "devolver_na_origem": True,
        "chave_operacao": str(uuid4()),
    }
    user = SimpleNamespace(id=22, nome="Atendente")
    previa = prever_devolucao(8, dados, db=db, user_and_tenant=(user, TENANT))
    dados["valor_previsto"] = previa["valor_total_devolucao"]
    dados["restituicao_prevista"] = previa["restituicao"]
    resultado = registrar_devolucao(8, dados, db=db, user_and_tenant=(user, TENANT))
    assert cliente.credito == Decimal("25")
    assert registrar_caixa.call_args.kwargs["valor"] == Decimal("30")
    lancamento = next(
        call.args[0]
        for call in db.add.call_args_list
        if isinstance(call.args[0], LancamentoManual)
    )
    assert lancamento.valor == Decimal("30")
    credito_log = next(
        call.args[0]
        for call in db.add.call_args_list
        if isinstance(call.args[0], CreditoLog)
    )
    assert credito_log.valor == Decimal("20")
    assert eventos[0].valor_devolvido == Decimal("50")
    assert eventos[0].movimentacao_caixa_id == 44
    assert resultado["movimentacao_caixa_id"] == 44
    assert (
        registrar_devolucao(8, dados, db=db, user_and_tenant=(user, TENANT))
        == resultado
    )
    registrar_caixa.assert_called_once()
    db.commit.assert_called_once()


def test_sqlite_cashback_parcial_preserva_lotes_tenant_e_rollback(tenant_context):
    """Exercita consultas/inserts reais; adapta apenas tipos/defaults de SQLite."""
    tenant_context(TENANT)
    engine = create_engine("sqlite://")
    metadata = MetaData()
    tabela = CashbackTransaction.__table__.to_metadata(metadata)
    tabela.c.id.type = Integer()
    tabela.c.created_at.server_default = None
    tabela.create(engine)
    validade = NOW + timedelta(days=2)
    outro_tenant = uuid4()
    with Session(engine) as db:
        for id, amount, tipo, tenant, origem in (
            (1, 20, "manual", TENANT, None),
            (2, -20, "redemption", TENANT, 8),
            (3, 70, "manual", outro_tenant, None),
            (4, -70, "redemption", outro_tenant, 8),
        ):
            db.execute(
                tabela.insert().values(
                    id=id,
                    tenant_id=tenant,
                    customer_id=47,
                    amount=amount,
                    source_type=tipo,
                    source_id=origem,
                    expires_at=validade if amount > 0 else None,
                    tx_type="credit" if amount > 0 else "debit",
                    created_at=NOW - timedelta(days=3) + timedelta(seconds=id),
                )
            )
        db.commit()
        venda = venda_com_pagamentos(
            pagamento("cashback", "20"), pagamento("pix", "80")
        )
        primeira = service.cotar_restituicao(
            db,
            tenant_id=TENANT,
            venda=venda,
            cotacao=cotacao("50"),
            eventos_anteriores=[],
            devolver_na_origem=True,
        )
        # SQLite não implementa clock_timestamp(); o listener mantém o relógio
        # de inserção e a ordem reais, sem mudar as consultas ou a carteira.
        from sqlalchemy import event

        def data_insercao(_mapper, _connection, obj):
            obj.created_at = datetime.now(timezone.utc)

        event.listen(CashbackTransaction, "before_insert", data_insercao)
        try:
            service.registrar_restituicao_cashback(
                db,
                tenant_id=TENANT,
                venda=venda,
                evento_devolucao=SimpleNamespace(id=1),
                restituicao=primeira,
            )
            db.commit()
            carteira = service.get_cashback_wallet(db, tenant_id=TENANT, customer_id=47)
            assert carteira.available == Decimal("10")
            assert (
                service.get_cashback_wallet(
                    db, tenant_id=outro_tenant, customer_id=47
                ).available
                == 0
            )
            evento = SimpleNamespace(
                valor_devolvido=50, resposta={"restituicao": primeira.resposta()}
            )
            segunda = service.cotar_restituicao(
                db,
                tenant_id=TENANT,
                venda=venda,
                cotacao=cotacao("50", "50"),
                eventos_anteriores=[evento],
                devolver_na_origem=True,
            )
            service.registrar_restituicao_cashback(
                db,
                tenant_id=TENANT,
                venda=venda,
                evento_devolucao=SimpleNamespace(id=2),
                restituicao=segunda,
            )
            assert service.get_cashback_wallet(
                db, tenant_id=TENANT, customer_id=47
            ).available == Decimal("20")
            db.rollback()
            assert service.get_cashback_wallet(
                db, tenant_id=TENANT, customer_id=47
            ).available == Decimal("10")
            segunda = service.cotar_restituicao(
                db,
                tenant_id=TENANT,
                venda=venda,
                cotacao=cotacao("50", "50"),
                eventos_anteriores=[evento],
                devolver_na_origem=True,
            )
            service.registrar_restituicao_cashback(
                db,
                tenant_id=TENANT,
                venda=venda,
                evento_devolucao=SimpleNamespace(id=2),
                restituicao=segunda,
            )
            db.commit()
            restauradas = (
                db.query(CashbackTransaction)
                .filter(
                    CashbackTransaction.tenant_id == TENANT,
                    CashbackTransaction.source_type == CashbackSourceTypeEnum.reversal,
                )
                .all()
            )
            assert sum(row.amount for row in restauradas) == Decimal("20")
            assert all(
                row.origin_credit_id == 1
                and row.expires_at.replace(tzinfo=timezone.utc) == validade
                for row in restauradas
            )
        finally:
            event.remove(CashbackTransaction, "before_insert", data_insercao)
    engine.dispose()
