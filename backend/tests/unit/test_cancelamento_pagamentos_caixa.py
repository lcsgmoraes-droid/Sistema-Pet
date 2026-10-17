"""Cancelamento invalida recebimentos ativos sem apagar o historico financeiro."""

from datetime import date, datetime
from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from app.caixa_models import Caixa, MovimentacaoCaixa
from app.caixa_routes import listar_vendas_caixa, obter_resumo_caixa
from app.financeiro_models import ContaReceber, MovimentacaoFinanceira, Recebimento
from app.models import User
from app.rotas_entrega_models import RotaEntregaParada
from app.vendas.cancelamento_service import cancelar_venda
from app.vendas.pagamentos_routes import listar_pagamentos_venda
from app.vendas_devolucoes_models import VendaDevolucao
from app.vendas_models import Venda, VendaPagamento
from tests.unit import test_finalizacao_recebiveis_atomicidade as recebiveis


cenario = recebiveis.cenario


@pytest.fixture
def cancelamento(cenario, monkeypatch):
    c = cenario
    for model in (VendaDevolucao, MovimentacaoFinanceira, RotaEntregaParada, User):
        model.__table__.create(c.db.bind)
    monkeypatch.setattr(
        "app.comissoes_estorno.estornar_comissoes_venda",
        lambda **kw: {"success": True, "comissoes_estornadas": 0},
    )
    monkeypatch.setattr(
        "app.campaigns.coupon_service.reverse_coupon_redemptions_for_sale",
        lambda *a, **kw: {},
    )
    monkeypatch.setattr(
        "app.campaigns.loyalty_service.void_loyalty_stamps_for_sale",
        lambda *a, **kw: {},
    )
    caixa = c.db.get(Caixa, 1)
    caixa.status = "aberto"
    caixa.valor_abertura = 10
    c.venda.status = "finalizada"
    c.venda.total = 100
    c.venda.subtotal = 100
    c.venda.cliente_id = None
    c.venda.data_finalizacao = datetime(2026, 10, 16, 10)
    usuario = SimpleNamespace(id=1, nome="QA caixa")
    c.auth = (usuario, c.tenant)
    c.pagamentos = []
    for forma, forma_id, valor, status in (
        ("PIX", 1, 40, "pendente"),
        ("Dinheiro", 2, 60, "aprovado"),
        ("PIX", 1, 5, "estornado"),
        ("PIX", 1, 7, "recusado"),
    ):
        pagamento = VendaPagamento(
            tenant_id=c.tenant,
            venda_id=c.venda.id,
            caixa_id=caixa.id,
            forma_pagamento=forma,
            forma_pagamento_id=forma_id,
            valor=valor,
            status=status,
            data_pagamento=datetime(2026, 10, 16, 10),
        )
        c.db.add(pagamento)
        c.db.flush()
        c.pagamentos.append(pagamento)
        if status in {"estornado", "recusado"}:
            continue
        conta = ContaReceber(
            tenant_id=c.tenant,
            user_id=1,
            venda_id=c.venda.id,
            descricao="QA recebivel",
            forma_pagamento_id=forma_id,
            dre_subcategoria_id=1,
            canal="loja_fisica",
            valor_original=valor,
            valor_final=valor,
            valor_recebido=valor,
            data_emissao=date.today(),
            data_vencimento=date.today(),
            data_recebimento=date.today(),
            status="recebido",
            observacoes=f"[venda_pagamento:{pagamento.id}]",
        )
        c.db.add(conta)
        c.db.flush()
        c.db.add(
            Recebimento(
                tenant_id=c.tenant,
                user_id=1,
                conta_receber_id=conta.id,
                forma_pagamento_id=forma_id,
                valor_recebido=valor,
                data_recebimento=date.today(),
                observacoes=f"[venda_pagamento:{pagamento.id}]",
            )
        )
    c.db.add(
        MovimentacaoCaixa(
            tenant_id=c.tenant,
            caixa_id=caixa.id,
            venda_id=c.venda.id,
            usuario_id=1,
            usuario_nome=usuario.nome,
            tipo="venda",
            forma_pagamento="Dinheiro",
            valor=60,
        )
    )
    c.db.commit()
    return c


def _cancelar(c):
    return cancelar_venda(c.venda.id, "QA cancelamento local", 1, c.tenant, c.db)


def test_cancelar_invalida_pagamentos_e_caixa_sem_apagar_recebiveis(cancelamento):
    c = cancelamento
    antes = obter_resumo_caixa(1, db=c.db, current_user_and_tenant=c.auth)
    assert antes["total_recebido"] == 100
    assert antes["totais"]["saldo_atual"] == 70
    ids = [p.id for p in c.pagamentos]

    _cancelar(c)

    assert c.venda.status == "cancelada"
    assert [c.db.get(VendaPagamento, i).status for i in ids] == [
        "cancelado",
        "cancelado",
        "estornado",
        "recusado",
    ]
    assert [c.db.get(VendaPagamento, i).valor for i in ids] == [40, 60, 5, 7]
    assert c.db.query(ContaReceber).count() == 2
    assert {r.status for r in c.db.query(ContaReceber).all()} == {"cancelado"}
    assert c.db.query(Recebimento).count() == 2
    assert c.db.query(MovimentacaoCaixa).count() == 0
    depois = obter_resumo_caixa(1, db=c.db, current_user_and_tenant=c.auth)
    assert depois["total_recebido"] == 0
    assert depois["totais"]["saldo_atual"] == 10
    historico = listar_vendas_caixa(1, db=c.db, current_user_and_tenant=c.auth)
    assert len(historico) == 1
    assert historico[0]["status"] == "cancelada"
    assert historico[0]["valor_nesta_forma"] == 0
    assert (
        listar_vendas_caixa(
            1, forma_pagamento="PIX", db=c.db, current_user_and_tenant=c.auth
        )
        == []
    )
    resumo = listar_pagamentos_venda(c.venda.id, c.db, c.auth)
    assert resumo["status_pagamento"] == "cancelado"
    assert resumo["valor_restante"] == 0
    assert len(resumo["pagamentos"]) == 4

    with pytest.raises(HTTPException) as exc:
        _cancelar(c)
    assert exc.value.status_code == 400
    assert c.db.query(Recebimento).count() == 2
    assert c.db.query(VendaPagamento).count() == 4


def test_falha_posterior_reverte_pagamentos_contas_e_caixa(cancelamento, monkeypatch):
    c = cancelamento

    def falhar(**kw):
        raise RuntimeError("QA falha posterior a invalidacao do pagamento")

    monkeypatch.setattr("app.comissoes_estorno.estornar_comissoes_venda", falhar)
    with pytest.raises(HTTPException) as exc:
        _cancelar(c)
    assert exc.value.status_code == 500
    assert c.db.get(Venda, c.venda.id).status == "finalizada"
    assert [c.db.get(VendaPagamento, p.id).status for p in c.pagamentos] == [
        "pendente",
        "aprovado",
        "estornado",
        "recusado",
    ]
    assert {r.status for r in c.db.query(ContaReceber).all()} == {"recebido"}
    assert c.db.query(Recebimento).count() == 2
    assert c.db.query(MovimentacaoCaixa).count() == 1


def test_resumo_pagamentos_cancelada_legada_nao_mostra_saldo_cobravel(cancelamento):
    c = cancelamento
    c.venda.status = "cancelada"
    c.db.commit()

    resumo = listar_pagamentos_venda(c.venda.id, c.db, c.auth)

    assert resumo["status_pagamento"] == "cancelado"
    assert resumo["total_pago"] == 0
    assert resumo["total_recebido"] == 0
    assert resumo["valor_restante"] == 0
    assert len(resumo["pagamentos"]) == 4
    assert [p.status for p in c.pagamentos][:2] == ["pendente", "aprovado"]


def test_cancelamento_preserva_recebimento_de_outra_venda(cancelamento):
    c = cancelamento
    outra = Venda(
        tenant_id=c.tenant,
        user_id=1,
        vendedor_id=1,
        caixa_id=2,
        numero_venda="QA-OUTRA-VENDA",
        subtotal=25,
        total=25,
        status="finalizada",
        data_venda=datetime(2026, 10, 16, 11),
    )
    c.db.add(outra)
    c.db.flush()
    pagamento = VendaPagamento(
        tenant_id=c.tenant,
        venda_id=outra.id,
        caixa_id=2,
        forma_pagamento="PIX",
        valor=25,
        status="pendente",
    )
    c.db.add(pagamento)
    c.db.commit()

    _cancelar(c)

    assert c.db.get(Venda, outra.id).status == "finalizada"
    assert c.db.get(VendaPagamento, pagamento.id).status == "pendente"
    assert (
        obter_resumo_caixa(2, db=c.db, current_user_and_tenant=c.auth)["total_recebido"]
        == 25
    )
