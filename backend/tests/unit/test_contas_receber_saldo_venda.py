"""Baixas avulsas não podem ultrapassar a venda nem perder encargos reais."""

import asyncio
from concurrent.futures import ThreadPoolExecutor
from datetime import date
from decimal import Decimal
from threading import Event
from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi import HTTPException
from sqlalchemy import event
from sqlalchemy.orm import Session
from sqlalchemy.schema import CreateTable

from app import contas_receber_recebimentos_routes as rotas
from app.contas_receber_schemas import RecebimentoCreate, RecebimentoLoteCreate
from app.financeiro_models import ContaReceber, Recebimento
from app.vendas_models import Venda, VendaBaixaLoteItem, VendaPagamento
from tests.unit import test_finalizacao_recebiveis_atomicidade as recebiveis

cenario = recebiveis.cenario
DIA = date(2026, 10, 22)


@pytest.fixture
def caso(cenario, monkeypatch):
    cenario.venda.total = 100
    cenario.venda.subtotal = 100
    cenario.db.commit()
    cenario.auth = (SimpleNamespace(id=1, nome="Operador"), cenario.tenant)
    monkeypatch.setattr(rotas, "carregar_config_encargos", lambda *_: None)
    monkeypatch.setattr(rotas, "_gerar_comissao_baixa_lote", lambda *_: None)
    return cenario


def conta(caso, valor=100, recebido=0, **extras):
    dados = dict(
        tenant_id=caso.tenant,
        venda_id=caso.venda.id,
        forma_pagamento_id=1,
        descricao="Previsão Pix da venda",
        valor_original=valor,
        valor_final=valor,
        valor_recebido=recebido,
        valor_juros=0,
        valor_multa=0,
        valor_desconto=0,
        status="parcial" if recebido else "pendente",
        user_id=1,
        dre_subcategoria_id=1,
        canal="loja_fisica",
        data_emissao=DIA,
        data_vencimento=DIA,
    )
    dados.update(extras)
    registro = ContaReceber(**dados)
    caso.db.add(registro)
    caso.db.commit()
    return registro


def pagar(caso, registro, valor, **extras):
    dados = RecebimentoCreate(
        valor_recebido=valor, data_recebimento=DIA, forma_pagamento_id=1, **extras
    )
    return asyncio.run(
        rotas.registrar_recebimento.__wrapped__(
            registro.id, dados, None, caso.db, caso.auth
        )
    )


def lote(caso, registros):
    dados = RecebimentoLoteCreate(
        conta_ids=[c.id for c in registros], data_recebimento=DIA, forma_pagamento_id=1
    )
    return asyncio.run(
        rotas.registrar_recebimentos_lote.__wrapped__(dados, None, caso.db, caso.auth)
    )


def bloquear(chamada):
    with pytest.raises(HTTPException) as erro:
        chamada()
    assert erro.value.status_code == 409
    assert "PDV" in erro.value.detail


def test_previsao_pix_100_desconto_venda_90_bloqueia_100_antes_de_mutar(caso):
    registro = conta(caso)
    caso.venda.total = 90
    caso.venda.desconto_valor = 10
    caso.db.commit()
    bloquear(lambda: pagar(caso, registro, 100))
    assert registro.valor_recebido == 0 and registro.status == "pendente"
    assert registro.valor_final == 100
    assert caso.db.query(Recebimento).count() == 0
    assert not caso.db.dirty


def test_previsao_pix_100_venda_90_aceita_baixa_90(caso):
    registro = conta(caso)
    caso.venda.total = 90
    caso.db.commit()
    resultado = pagar(caso, registro, 90)
    assert resultado["valor_recebido_total"] == 90
    assert registro.status == "parcial"
    bloquear(lambda: pagar(caso, registro, 10))
    assert caso.db.query(Recebimento).count() == 1


def test_baixas_parciais_sucessivas_somam_recebimentos_reais(caso):
    registro = conta(caso, 120)
    pagar(caso, registro, 60)
    pagar(caso, registro, 40)
    bloquear(lambda: pagar(caso, registro, 20))
    assert registro.valor_recebido == 100
    assert caso.db.query(Recebimento).count() == 2


def test_lote_soma_duas_contas_da_mesma_venda_e_e_atomico(caso):
    primeira, segunda = conta(caso, 60), conta(caso, 50)
    bloquear(lambda: lote(caso, [primeira, segunda]))
    assert primeira.valor_recebido == segunda.valor_recebido == 0
    assert caso.db.query(Recebimento).count() == 0


def test_lote_duas_contas_da_mesma_venda_aceita_total_correto(caso):
    primeira, segunda = conta(caso, 60), conta(caso, 40)
    assert lote(caso, [segunda, primeira])["valor_total"] == 100
    assert caso.db.query(Recebimento).count() == 2


def test_lote_com_conta_invalida_nao_altera_a_primeira(caso):
    primeira, segunda = conta(caso, 50), conta(caso, 50, status="cancelado")
    with pytest.raises(HTTPException) as erro:
        lote(caso, [primeira, segunda])
    assert erro.value.status_code == 400
    assert primeira.valor_recebido == 0
    assert caso.db.query(Recebimento).count() == 0


def test_conta_sem_venda_preserva_fluxo_financeiro_independente(caso):
    registro = conta(caso, 200, venda_id=None)
    assert pagar(caso, registro, 200)["valor_recebido_total"] == 200


def test_venda_cancelada_nao_ressuscita_recebimento(caso):
    registro = conta(caso)
    caso.venda.status = "cancelada"
    caso.db.commit()
    bloquear(lambda: pagar(caso, registro, 100))
    assert caso.db.query(Recebimento).count() == 0


@pytest.mark.parametrize("em_lote", [False, True])
def test_isolamento_tenant_na_conta_e_no_lote(caso, em_lote, tenant_context):
    propria = conta(caso, 50)
    outro_tenant = uuid4()
    tenant_context(outro_tenant)
    alheia = conta(caso, 50, tenant_id=outro_tenant, venda_id=None)
    tenant_context(caso.tenant)
    with pytest.raises(HTTPException) as erro:
        lote(caso, [propria, alheia]) if em_lote else pagar(caso, alheia, 50)
    assert erro.value.status_code == 404
    assert propria.valor_recebido == 0
    assert caso.db.query(Recebimento).count() == 0


def test_juros_10_em_venda_100_permite_receber_110(caso):
    registro = conta(caso)
    assert pagar(caso, registro, 110, valor_juros=10)["valor_recebido_total"] == 110
    assert registro.valor_juros == 10
    assert registro.valor_final == 110


def test_encargos_persistidos_substituidos_pela_previa_sem_duplicar(caso):
    registro = conta(caso, valor_juros=10, valor_final=110)
    outra = conta(caso, 10)
    pagar(caso, registro, 110)
    bloquear(lambda: pagar(caso, outra, 10))
    assert caso.db.query(Recebimento).count() == 1


def test_desconto_financeiro_10_permite_90_e_nao_libera_mais_10(caso):
    registro = conta(caso)
    outra = conta(caso, 10)
    pagar(caso, registro, 90, valor_desconto=10)
    bloquear(lambda: pagar(caso, outra, 10))
    assert registro.valor_desconto == 10 and registro.valor_final == 90


def test_encargos_automaticos_preservam_calculo_incremental(caso, monkeypatch):
    registro = conta(caso, data_vencimento=date(2026, 9, 22))
    registro.forma_pagamento.tipo = "crediario"
    caso.db.commit()
    config = SimpleNamespace(
        crediario_encargos_automaticos=True,
        crediario_multa_percentual=2,
        crediario_juros_mensal_percentual=1,
        dias_tolerancia_atraso=0,
    )
    monkeypatch.setattr(rotas, "carregar_config_encargos", lambda *_: config)
    resultado = pagar(caso, registro, 103, aplicar_encargos_automaticos=True)
    assert resultado["valor_recebido_total"] == 103
    assert registro.valor_juros == 1 and registro.valor_multa == 2
    assert registro.data_ultimo_calculo_encargos == DIA


def test_recebimento_mirror_vp_nao_duplica_e_baixa_independente_conta(caso):
    pagamento = VendaPagamento(
        tenant_id=caso.tenant, venda_id=1, forma_pagamento="Pix", valor=30
    )
    caso.db.add(pagamento)
    caso.db.commit()
    espelho = conta(caso, 30, 30, observacoes=f"[venda_pagamento:{pagamento.id}]")
    caso.db.add(
        Recebimento(
            tenant_id=caso.tenant,
            conta_receber_id=espelho.id,
            forma_pagamento_id=1,
            valor_recebido=30,
            data_recebimento=DIA,
            user_id=1,
            observacoes=f"[venda_pagamento:{pagamento.id}]",
        )
    )
    caso.db.commit()
    independente = conta(caso, 80)
    pagar(caso, independente, 70)
    bloquear(lambda: pagar(caso, independente, 10))
    assert independente.valor_recebido == 70


def test_espelho_lote_por_id_nao_depende_de_nome_valor_ou_hora(caso):
    engine = caso.db.get_bind()
    with engine.begin() as conn:
        conn.execute(
            CreateTable(
                VendaBaixaLoteItem.__table__, include_foreign_key_constraints=[]
            )
        )
    pagamento = VendaPagamento(
        tenant_id=caso.tenant,
        venda_id=1,
        forma_pagamento="Pix",
        valor=30,
        baixa_lote_id=1,
    )
    caso.db.add(pagamento)
    caso.db.commit()
    espelho = conta(caso, 30, 30)
    recibo = Recebimento(
        tenant_id=caso.tenant,
        conta_receber_id=espelho.id,
        forma_pagamento_id=1,
        valor_recebido=30,
        data_recebimento=DIA,
        user_id=1,
    )
    caso.db.add(recibo)
    caso.db.flush()
    caso.db.add(
        VendaBaixaLoteItem(
            tenant_id=caso.tenant,
            lote_id=1,
            venda_id=1,
            numero_venda=caso.venda.numero_venda,
            valor=30,
            pagamento_id=pagamento.id,
            efeitos={"recebimento_id": recibo.id},
        )
    )
    caso.db.commit()
    independente = conta(caso, 70)
    assert pagar(caso, independente, 70)["valor_recebido_total"] == 70


def test_beneficio_aplicado_tambem_ocupa_saldo_da_venda(caso):
    caso.db.add(
        VendaPagamento(
            tenant_id=caso.tenant,
            venda_id=1,
            forma_pagamento="Crédito Cliente",
            valor=10,
        )
    )
    caso.db.commit()
    registro = conta(caso)
    bloquear(lambda: pagar(caso, registro, 100))
    assert pagar(caso, registro, 90)["valor_recebido_total"] == 90


def test_duas_baixas_concorrentes_na_mesma_venda_revalidam_saldo(caso):
    engine = caso.db.get_bind()
    if engine.dialect.name != "postgresql":
        pytest.skip("Locks concorrentes exigem PostgreSQL DEV descartável")
    primeira, segunda = conta(caso, 60), conta(caso, 60)
    ids = [primeira.id, segunda.id]
    tenant, auth = caso.tenant, caso.auth
    esperando = Event()

    def consulta(_conn, _cursor, sql, _params, _context, _many):
        if "FROM vendas" in sql and "FOR UPDATE" in sql:
            esperando.set()

    def receber(ident):
        from app.tenancy.context import clear_current_tenant, set_current_tenant

        set_current_tenant(tenant)
        try:
            with Session(engine) as db:
                try:
                    asyncio.run(
                        rotas.registrar_recebimento.__wrapped__(
                            ident,
                            RecebimentoCreate(
                                valor_recebido=60,
                                data_recebimento=DIA,
                                forma_pagamento_id=1,
                            ),
                            None,
                            db,
                            auth,
                        )
                    )
                    return 200
                except HTTPException as erro:
                    db.rollback()
                    return erro.status_code
        finally:
            clear_current_tenant()

    event.listen(engine, "before_cursor_execute", consulta)
    try:
        with Session(engine) as trava:
            trava.query(Venda).filter_by(id=1, tenant_id=tenant).with_for_update().one()
            with ThreadPoolExecutor(max_workers=2) as executor:
                resultados = [executor.submit(receber, ident) for ident in ids]
                assert esperando.wait(8)
                trava.commit()
                assert sorted(f.result(timeout=8) for f in resultados) == [200, 409]
    finally:
        event.remove(engine, "before_cursor_execute", consulta)
    assert caso.db.query(Recebimento).count() == 1
    assert caso.db.query(Recebimento).one().valor_recebido == Decimal("60")
