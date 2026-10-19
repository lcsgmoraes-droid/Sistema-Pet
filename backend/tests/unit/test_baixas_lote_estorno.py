"""Receber, estornar e corrigir um único pagamento rateado entre vendas."""

import asyncio
from datetime import datetime
from decimal import Decimal
from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi import HTTPException
from sqlalchemy import func

from app.caixa.conferencia import totais_dinheiro
from app.caixa_models import Caixa, MovimentacaoCaixa
from app.comissoes_models import ComissaoItem
from app.clientes import financeiro_baixa_lote_routes as routes
from app.clientes.baixas_lote_service import listar_lotes
from app.clientes.financeiro_baixa_lote_historico_routes import (
    EstornoLoteInput,
    estornar_baixa_lote,
)
from app.financeiro_models import ContaReceber, MovimentacaoFinanceira, Recebimento
from app.ia.aba5_models import FluxoCaixa
from app.models import AuditLog, Cliente
from app.vendas.pagamentos_routes import excluir_pagamento
from app.vendas.status_pagamento import calcular_resumo_pagamento_venda
from app.vendas_models import Venda, VendaBaixaLote, VendaBaixaLoteItem, VendaPagamento

pytest_plugins = ["tests.unit.test_finalizacao_recebiveis_atomicidade"]


@pytest.fixture
def lote(cenario, monkeypatch):
    db = cenario.db
    for model in (
        VendaBaixaLote,
        VendaBaixaLoteItem,
        FluxoCaixa,
        MovimentacaoFinanceira,
        ComissaoItem,
    ):
        model.__table__.create(db.bind)
    cliente = Cliente(tenant_id=cenario.tenant, user_id=1, nome="Cliente do lote")
    db.add(cliente)
    db.flush()
    cenario.venda.cliente_id = cliente.id
    cenario.venda.total = cenario.venda.subtotal = Decimal("100")
    cenario.venda.nao_gerar_beneficios = True
    cenario.venda.data_venda = datetime(2026, 9, 1)
    segunda = Venda(
        tenant_id=cenario.tenant,
        numero_venda="TEST-SEGUNDA",
        user_id=1,
        vendedor_id=1,
        cliente_id=cliente.id,
        subtotal=80,
        total=80,
        status="aberta",
        data_venda=datetime(2026, 9, 2),
        nao_gerar_beneficios=True,
    )
    db.add(segunda)
    db.commit()
    monkeypatch.setattr(
        routes, "get_or_build_venda_rentabilidade_snapshot", lambda *a, **kw: {}
    )
    user = SimpleNamespace(id=1, nome="Operadora", email="operadora@example.test")
    cenario.cliente, cenario.segunda, cenario.user = cliente, segunda, user

    def baixar(valor=150, forma="dinheiro", request_id=None):
        dados = {
            "vendas_ids": [cenario.venda.id, segunda.id],
            "valor_total": valor,
            "forma_pagamento": forma,
            "request_id": str(request_id or uuid4()),
        }
        return asyncio.run(
            routes.baixar_vendas_lote(cliente.id, dados, db, (user, cenario.tenant))
        )

    def estornar(lote_id, tenant=None, motivo="Baixa registrada por engano"):
        return estornar_baixa_lote(
            cliente.id,
            lote_id,
            EstornoLoteInput(motivo=motivo),
            db,
            (user, tenant or cenario.tenant),
        )

    cenario.baixar, cenario.estornar = baixar, estornar
    return cenario


def test_lote_e_um_lancamento_com_rateio_e_estorno_integral(lote):
    c = lote
    resultado = c.baixar()
    historico = listar_lotes(c.db, c.tenant, c.cliente.id, 1, 20)
    assert historico["total"] == 1
    assert historico["itens"][0]["valor_total"] == 150
    assert [i["valor_baixado"] for i in historico["itens"][0]["vendas"]] == [100, 50]
    assert c.venda.status == "finalizada"
    assert c.segunda.status == "baixa_parcial"
    assert c.db.query(VendaPagamento).count() == 2
    assert c.db.query(Recebimento).count() == 2
    c.estornar(resultado["lote_id"])
    assert c.db.query(func.sum(VendaPagamento.valor)).scalar() == 0
    assert c.db.query(func.sum(Recebimento.valor_recebido)).scalar() == 0
    assert c.db.query(func.sum(ContaReceber.valor_recebido)).scalar() == 0
    assert (
        c.db.query(func.sum(FluxoCaixa.valor)).filter_by(status="realizado").scalar()
        == 0
    )
    assert (
        c.db.query(func.sum(FluxoCaixa.valor)).filter_by(status="previsto").scalar()
        == 180
    )
    assert c.venda.status == c.segunda.status == "aberta"
    assert c.db.query(VendaPagamento).count() == 4  # Originais preservados.
    assert c.db.query(AuditLog).filter_by(action="estornar_baixa_lote").count() == 1
    assert (
        c.db.query(VendaBaixaLote).one().motivo_estorno == "Baixa registrada por engano"
    )


@pytest.mark.parametrize("forma", ["dinheiro", "pix"])
def test_caixa_original_fechado_fica_preservado_e_correta_pode_ser_recebida(
    forma, lote
):
    c = lote
    resultado = c.baixar(forma=forma)
    caixa_original = c.db.get(Caixa, 2)
    valores_antes = [
        (p.id, p.valor) for p in c.db.query(VendaPagamento).filter_by(caixa_id=2)
    ]
    caixa_original.status = "fechado"
    caixa_original.valor_esperado = 280
    caixa_atual = Caixa(
        tenant_id=c.tenant,
        numero_caixa=3,
        usuario_id=1,
        usuario_nome="Operadora",
        status="aberto",
        valor_abertura=280,
    )
    c.db.add(caixa_atual)
    c.db.commit()
    c.estornar(resultado["lote_id"])
    assert valores_antes == [
        (p.id, p.valor) for p in c.db.query(VendaPagamento).filter_by(caixa_id=2)
    ]
    assert caixa_original.status == "fechado" and caixa_original.valor_esperado == 280
    assert (
        c.db.query(func.sum(VendaPagamento.valor))
        .filter_by(caixa_id=caixa_atual.id)
        .scalar()
        == -150
    )
    movimentos = c.db.query(MovimentacaoCaixa).filter_by(caixa_id=caixa_atual.id).all()
    assert totais_dinheiro(280, movimentos)["saldo_atual"] == (
        130 if forma == "dinheiro" else 280
    )
    novo = c.baixar(valor=180, forma=forma)
    assert novo["lote_id"] != resultado["lote_id"]
    # Expira a coleção previamente lida pelo endpoint de baixa.
    c.db.expire(c.venda, ["pagamentos"])
    resumo = calcular_resumo_pagamento_venda(
        total=c.venda.total, pagamentos=c.venda.pagamentos
    )
    assert resumo["valor_pago"] == 100
    assert c.db.query(func.sum(VendaPagamento.valor)).scalar() == 180


def test_repeticao_de_baixa_e_estorno_nao_duplica_valores(lote):
    c = lote
    chave = uuid4()
    primeiro = c.baixar(request_id=chave)
    assert c.baixar(request_id=chave) == primeiro
    assert c.db.query(VendaPagamento).count() == 2
    c.estornar(primeiro["lote_id"])
    caixa = c.db.get(Caixa, 2)
    caixa.status = "fechado"
    c.db.commit()
    assert c.estornar(primeiro["lote_id"])["status"] == "estornado"
    assert c.baixar(request_id=chave) == primeiro
    assert c.db.query(VendaPagamento).count() == 4
    with pytest.raises(HTTPException) as erro:
        c.baixar(valor=120, request_id=chave)
    assert erro.value.status_code == 409


def test_falha_na_segunda_venda_reverte_todo_o_estorno(lote):
    c = lote
    resultado = c.baixar()
    conta = c.db.query(ContaReceber).filter_by(venda_id=c.segunda.id).one()
    conta.conciliado = True
    c.db.commit()
    with pytest.raises(HTTPException) as erro:
        c.estornar(resultado["lote_id"])
    assert erro.value.status_code == 409
    assert c.db.query(VendaBaixaLote).one().status == "confirmado"
    assert c.db.query(VendaPagamento).count() == 2
    assert c.db.query(func.sum(ContaReceber.valor_recebido)).scalar() == 150


def test_falha_de_beneficio_apos_primeira_contrapartida_faz_rollback_total(
    lote, monkeypatch
):
    c = lote
    resultado = c.baixar()
    itens = c.db.query(VendaBaixaLoteItem).order_by(VendaBaixaLoteItem.venda_id).all()
    for item in itens:
        item.efeitos = {**item.efeitos, "evento_id": item.venda_id}
    c.db.commit()
    chamadas = []

    def beneficios(db, tenant, venda_id, evento_id, motivo):
        chamadas.append(venda_id)
        if venda_id == c.segunda.id:
            # A contrapartida da primeira venda já existe nesta transação.
            assert db.query(VendaPagamento).count() == 3
            raise HTTPException(409, "Cupom da segunda venda já utilizado")

    monkeypatch.setattr(
        "app.campaigns.baixa_lote_reversal.estornar_beneficios_baixa_lote", beneficios
    )
    with pytest.raises(HTTPException):
        c.estornar(resultado["lote_id"])
    assert chamadas == [c.venda.id, c.segunda.id]
    assert c.db.query(VendaPagamento).count() == 2
    assert c.db.query(Recebimento).count() == 2
    assert c.db.query(MovimentacaoCaixa).count() == 2
    assert c.db.query(VendaBaixaLote).one().status == "confirmado"
    assert c.db.query(func.sum(ContaReceber.valor_recebido)).scalar() == 150


def test_outro_tenant_nao_consulta_nem_estorna_lote(lote):
    c = lote
    resultado = c.baixar()
    outro = uuid4()
    assert listar_lotes(c.db, outro, c.cliente.id, 1, 20)["total"] == 0
    with pytest.raises(HTTPException) as erro:
        c.estornar(resultado["lote_id"], tenant=outro)
    assert erro.value.status_code == 404
    assert c.db.query(VendaPagamento).count() == 2


def test_nao_permite_excluir_rateio_individual(lote):
    c = lote
    c.baixar()
    pagamento = c.db.query(VendaPagamento).first()
    with pytest.raises(HTTPException) as erro:
        excluir_pagamento(pagamento.id, c.db, (c.user, c.tenant))
    assert erro.value.status_code == 409
    assert "lote" in erro.value.detail


def test_estornar_lote_anterior_preserva_recebimento_posterior(lote):
    c = lote
    primeiro = c.baixar(valor=40)
    segundo = c.baixar(valor=50)
    c.estornar(primeiro["lote_id"])
    assert c.db.query(func.sum(VendaPagamento.valor)).scalar() == 50
    assert (
        c.db.query(VendaBaixaLote).filter_by(id=segundo["lote_id"]).one().status
        == "confirmado"
    )
    assert c.db.query(func.sum(ContaReceber.valor_recebido)).scalar() == 50
    c.estornar(segundo["lote_id"])
    assert c.db.query(func.sum(ContaReceber.valor_recebido)).scalar() == 0


def test_comissao_do_pagamento_bloqueia_estorno_sem_mexer_nas_anteriores(lote):
    c = lote
    primeiro = c.baixar(valor=40)
    segundo = c.baixar(valor=50)
    comissao = ComissaoItem(
        tenant_id=c.tenant,
        venda_id=c.venda.id,
        funcionario_id=c.cliente.id,
        data_venda=c.venda.data_venda.date(),
        parcela_numero=2,
        valor_comissao_gerada=5,
        status="pendente",
    )
    c.db.add(comissao)
    c.db.commit()
    with pytest.raises(HTTPException) as erro:
        c.estornar(segundo["lote_id"])
    assert erro.value.status_code == 409
    assert "comissão" in erro.value.detail
    c.estornar(primeiro["lote_id"])
    assert c.db.query(func.sum(VendaPagamento.valor)).scalar() == 50
    assert c.db.get(ComissaoItem, comissao.id).status == "pendente"
    comissao.status = "estornado"
    c.db.commit()
    c.estornar(segundo["lote_id"])
    assert c.db.query(func.sum(VendaPagamento.valor)).scalar() == 0


@pytest.mark.parametrize("valor", ["NaN", "Infinity", -1, 0])
def test_valor_invalido_nao_cria_lote_nem_movimento(valor, lote):
    with pytest.raises(HTTPException):
        lote.baixar(valor=valor)
    assert lote.db.query(VendaBaixaLote).count() == 0
    assert lote.db.query(VendaPagamento).count() == 0
