"""Entrega concluída permite trocar dinheiro/Pix/crediário sem duplicar efeitos."""

from datetime import date, datetime, timedelta
from decimal import Decimal
from types import SimpleNamespace

import pytest
from sqlalchemy.schema import CreateTable

from app.api.endpoints.rotas_entrega_tracking import (
    _sincronizar_venda_entregue_por_parada,
)
from app.caixa_models import MovimentacaoCaixa
from app.campaigns import cashback_sale_reversal, coupon_service, loyalty_service
from app.campaigns import sale_reopening_service
from app.financeiro_models import ContaReceber, FormaPagamento, Recebimento
from app.models import Cliente
from app.produto_identidade_models import ProdutoIdentidade  # noqa: F401 - FK do produto
from app.produtos_models import (
    EstoqueMovimentacao,
    Produto,
    ProdutoProtocoloRecorrencia,
)
from app.services import crediario_notifications
from app.vendas import finalizacao, status_routes
from app.vendas.pagamentos_routes import excluir_pagamento, listar_pagamentos_venda
from app.vendas_models import VendaItem, VendaPagamento
from tests.unit import test_exclusao_pagamento_atomicidade as exclusoes
from tests.unit import test_finalizacao_recebiveis_atomicidade as recebiveis

cenario = recebiveis.cenario
pagamentos = exclusoes.pagamentos


def test_entrega_concluida_troca_dinheiro_por_pix_e_crediario(pagamentos, monkeypatch):
    c = pagamentos
    db = c.db
    assert db.get_bind().dialect.name == "sqlite", "Este cenário usa somente SQLite."
    for model in (Produto, ProdutoProtocoloRecorrencia, EstoqueMovimentacao):
        with db.get_bind().begin() as conexao:
            conexao.execute(
                CreateTable(model.__table__, include_foreign_key_constraints=[])
            )

    # Benefícios e notificações não participam desta regressão. Reabertura,
    # recebimentos, exclusões, caixa e contas usam os serviços reais.
    for modulo, nome, retorno in (
        (coupon_service, "reverse_coupon_redemptions_for_sale", {}),
        (loyalty_service, "void_loyalty_stamps_for_sale", {}),
        (sale_reopening_service, "void_quick_repurchase_coupons_for_sale", 0),
        (cashback_sale_reversal, "reverse_cashback_for_sale", None),
        (crediario_notifications, "criar_notificacoes_parcelas_crediario", 0),
    ):
        monkeypatch.setattr(modulo, nome, lambda *a, _retorno=retorno, **kw: _retorno)

    usuario = SimpleNamespace(id=1, nome="Operadora")
    autenticacao = (usuario, c.tenant)
    cliente = Cliente(tenant_id=c.tenant, user_id=1, nome="Cliente da entrega")
    entregador = Cliente(tenant_id=c.tenant, user_id=1, nome="Entregador teste")
    produto = Produto(
        tenant_id=c.tenant,
        user_id=1,
        codigo="TESTE-ENTREGA",
        nome="Produto já separado para entrega",
        preco_venda=135,
        estoque_atual=9,
        estoque_fisico=9,
    )
    db.add_all([cliente, entregador, produto])
    db.flush()
    c.venda.cliente_id = cliente.id
    c.venda.tem_entrega = True
    c.venda.entregador_id = entregador.id
    c.venda.endereco_entrega = "Rua do teste, 100"
    c.venda.status_entrega = "em_rota"
    c.venda.pagamento_entrega_previsto = {"forma": "dinheiro"}
    c.venda.nao_gerar_beneficios = True
    db.add(
        FormaPagamento(
            id=3,
            tenant_id=c.tenant,
            user_id=1,
            nome="Crediário",
            tipo="crediario",
            prazo_dias=30,
            ativo=True,
        )
    )
    item = VendaItem(
        tenant_id=c.tenant,
        venda_id=c.venda.id,
        produto_id=produto.id,
        tipo="produto",
        quantidade=1,
        preco_unitario=135,
        subtotal=135,
    )
    # A venda aberta já retirou o produto na criação; pagar/reabrir não pode
    # retirar uma segunda unidade nem recriar esta movimentação.
    movimento = EstoqueMovimentacao(
        tenant_id=c.tenant,
        produto_id=produto.id,
        tipo="saida",
        motivo="venda",
        quantidade=1,
        quantidade_anterior=10,
        quantidade_nova=9,
        referencia_id=c.venda.id,
        referencia_tipo="venda",
        documento=c.venda.numero_venda,
        user_id=1,
    )
    db.add_all([item, movimento])
    db.commit()

    entrega_em = datetime(2026, 10, 23, 15, 30)
    parada = SimpleNamespace(venda_id=c.venda.id, status="em_rota", data_entrega=None)
    _sincronizar_venda_entregue_por_parada(db, parada, c.tenant, entrega_em)
    db.commit()
    assert parada.status == c.venda.status_entrega == "entregue"
    assert c.venda.status == "aberta"

    def conferir_entrega_e_estoque():
        db.refresh(c.venda)
        db.refresh(produto)
        assert c.venda.status_entrega == "entregue"
        assert c.venda.data_entrega == entrega_em
        assert c.venda.entregador_id == entregador.id
        assert produto.estoque_atual == produto.estoque_fisico == 9
        assert db.query(EstoqueMovimentacao).one().id == movimento.id

    def receber(dados):
        def nao_baixar_estoque(**kwargs):
            pytest.fail(
                "Trocar a forma de pagamento não pode baixar estoque novamente."
            )

        resultado = finalizacao.finalizar_venda(
            venda_id=c.venda.id,
            pagamentos=[dados],
            user_id=usuario.id,
            user_nome=usuario.nome,
            tenant_id=c.tenant,
            db=db,
            processar_baixa_estoque_item=nao_baixar_estoque,
        )
        assert resultado["venda"]["status"] == "finalizada"
        assert resultado["operacoes"]["estoque_baixado"] == []
        conferir_entrega_e_estoque()

    for forma, forma_id in (("Dinheiro", 2), ("PIX", 1)):
        receber(
            {"forma_pagamento": forma, "forma_pagamento_id": forma_id, "valor": 135}
        )
        pagamento = db.query(VendaPagamento).one()
        assert pagamento.forma_pagamento_id == forma_id
        assert db.query(Recebimento).one().valor_recebido == Decimal("135")
        contas = db.query(ContaReceber).filter(ContaReceber.status != "cancelado").all()
        assert len(contas) == 1
        assert contas[0].status == "recebido"
        resumo = listar_pagamentos_venda(c.venda.id, db, autenticacao)
        assert resumo["total_recebido"] == 135
        assert resumo["valor_restante"] == 0
        assert db.query(MovimentacaoCaixa).count() == (forma == "Dinheiro")

        reaberta = status_routes.reabrir_venda(c.venda.id, db, autenticacao)
        assert reaberta["status"] == "aberta"
        assert reaberta["entrega"]["status_entrega"] == "entregue"
        assert db.query(VendaPagamento).count() == 1
        resultado = excluir_pagamento(pagamento.id, db, autenticacao)
        assert resultado["total_pago"] == 0
        assert db.query(VendaPagamento).count() == 0
        assert db.query(Recebimento).count() == 0
        assert db.query(MovimentacaoCaixa).count() == 0
        assert (
            db.query(ContaReceber).filter(ContaReceber.status != "cancelado").count()
            == 0
        )
        conferir_entrega_e_estoque()

    vencimento = date.today() + timedelta(days=30)
    receber(
        {
            "forma_pagamento": "Crediário",
            "forma_pagamento_id": 3,
            "valor": 135,
            "numero_parcelas": 1,
            "data_recebimento_prevista": vencimento,
        }
    )
    plano = db.query(VendaPagamento).one()
    assert plano.forma_pagamento_id == 3
    assert plano.valor == Decimal("135")
    pendente = db.query(ContaReceber).filter(ContaReceber.status != "cancelado").one()
    assert pendente.forma_pagamento_id == 3
    assert pendente.status == "pendente"
    assert pendente.valor_final == Decimal("135")
    assert pendente.valor_recebido == 0
    assert pendente.data_vencimento == vencimento
    assert db.query(ContaReceber).filter_by(status="cancelado").count() == 2
    assert db.query(Recebimento).count() == 0
    assert db.query(MovimentacaoCaixa).count() == 0
    resumo = listar_pagamentos_venda(c.venda.id, db, autenticacao)
    assert resumo["total_recebido"] == 0
    assert resumo["crediario_pendente"] == 135
    assert resumo["valor_restante"] == 135
