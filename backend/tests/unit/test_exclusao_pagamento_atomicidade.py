"""Regressoes do ciclo receber/reabrir/excluir e dos pagamentos mistos."""

from datetime import date, datetime
from decimal import Decimal
from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi import HTTPException
from sqlalchemy import func
from sqlalchemy.schema import CreateTable

from app.caixa_models import Caixa, MovimentacaoCaixa
from app.financeiro_models import (
    ContaReceber,
    FormaPagamento,
    LancamentoManual,
    MovimentacaoFinanceira,
    Recebimento,
)
from app.financeiro.fluxo_caixa_vendas import valores_entradas_venda_realizadas
from app.ia.aba5_models import FluxoCaixa
from app.models import AuditLog, Cliente, CreditoLog
from app.veterinario_models import VetPartnerLink
from app.vendas import exclusao_pagamento, finalizacao
from app.vendas.pagamentos_routes import excluir_pagamento
from app.vendas_models import VendaPagamento

pytest_plugins = ["tests.unit.test_finalizacao_recebiveis_atomicidade"]


@pytest.fixture
def pagamentos(cenario):
    db = cenario.db
    for model in (CreditoLog, MovimentacaoFinanceira, FluxoCaixa, VetPartnerLink):
        if db.bind.dialect.name == "postgresql":
            with db.bind.begin() as conn:
                conn.execute(
                    CreateTable(model.__table__, include_foreign_key_constraints=[])
                )
        else:
            model.__table__.create(db.bind)
    db.get(Caixa, 1).status = "aberto"
    db.commit()
    usuario = SimpleNamespace(id=1, nome="Operadora")

    def receber(*itens):
        return finalizacao.finalizar_venda(
            venda_id=1,
            pagamentos=[
                dict(forma_pagamento=f, forma_pagamento_id=i, valor=v)
                for f, i, v in itens
            ],
            user_id=1,
            user_nome=usuario.nome,
            tenant_id=cenario.tenant,
            db=db,
            processar_baixa_estoque_item=lambda **kw: [],
        )

    def excluir(pagamento_id, tenant=None):
        cenario.venda.status = "aberta"
        db.commit()
        return excluir_pagamento(
            pagamento_id, db=db, user_and_tenant=(usuario, tenant or cenario.tenant)
        )

    cenario.receber, cenario.excluir = receber, excluir
    return cenario


def _entrada_financeira(cenario):
    lancamentos = cenario.db.query(LancamentoManual).filter_by(status="realizado").all()
    valores = valores_entradas_venda_realizadas(
        cenario.db, cenario.tenant, lancamentos, date.today()
    )
    return sum(
        (valores.get(lancamento.id, lancamento.valor) for lancamento in lancamentos),
        Decimal("0"),
    )


def _credito(cenario):
    cliente = Cliente(
        tenant_id=cenario.tenant, user_id=1, nome="Cliente", credito=Decimal("4.90")
    )
    cenario.db.add(cliente)
    cenario.db.add(
        FormaPagamento(
            id=3,
            tenant_id=cenario.tenant,
            user_id=1,
            nome="Crédito Cliente",
            tipo="credito_cliente",
            prazo_dias=0,
            ativo=True,
        )
    )
    cenario.db.flush()
    cenario.venda.cliente_id = cliente.id
    cenario.db.commit()
    assert (
        cenario.db.query(Cliente)
        .filter_by(id=cliente.id, tenant_id=cenario.tenant)
        .first()
        is not None
    )
    assert cenario.db.get(type(cenario.venda), 1).cliente_id == cliente.id
    return cliente


def test_tres_recebimentos_com_exclusoes_mantem_uma_entrada(pagamentos):
    c = pagamentos
    for rodada in range(3):
        c.receber(("Dinheiro", 2, 135))
        assert c.db.query(MovimentacaoCaixa).count() == 1
        assert (
            c.db.query(ContaReceber).filter(ContaReceber.status != "cancelado").count()
            == 1
        )
        assert c.db.query(Recebimento).count() == 1
        assert _entrada_financeira(c) == Decimal("135")
        assert c.db.query(LancamentoManual).filter_by(status="previsto").count() == 0
        if rodada < 2:
            pagamento_id = c.db.query(VendaPagamento).one().id
            resultado = c.excluir(pagamento_id)
            assert resultado["total_pago"] == 0
            assert c.db.query(MovimentacaoCaixa).count() == 0
            assert c.db.query(Recebimento).count() == 0
    assert c.db.query(func.sum(MovimentacaoCaixa.valor)).scalar() == 135


def test_excluir_um_pagamento_misto_preserva_o_outro_e_seu_recebivel(pagamentos):
    c = pagamentos
    c.receber(("Dinheiro", 2, 100), ("PIX", 1, 35))
    dinheiro = c.db.query(VendaPagamento).filter_by(forma_pagamento="Dinheiro").one()
    pix = c.db.query(VendaPagamento).filter_by(forma_pagamento="PIX").one()
    conta_pix = c.db.query(ContaReceber).filter_by(forma_pagamento_id=1).one()
    c.excluir(dinheiro.id)
    assert c.db.get(VendaPagamento, pix.id) is not None
    assert c.db.get(ContaReceber, conta_pix.id).status == "recebido"
    assert c.db.query(Recebimento).one().valor_recebido == Decimal("35")
    assert c.db.query(MovimentacaoCaixa).count() == 0
    assert _entrada_financeira(c) == Decimal("35")
    assert c.db.query(LancamentoManual).filter_by(
        status="previsto"
    ).one().valor == Decimal("100")
    c.receber(("Dinheiro", 2, 100))
    assert c.db.query(Recebimento).count() == 2
    assert _entrada_financeira(c) == Decimal("135")


def test_excluir_credito_retorna_saldo_e_retira_entrada_nao_monetaria(pagamentos):
    c = pagamentos
    cliente = _credito(c)
    c.receber(
        ("Crédito Cliente", 3, Decimal("4.90")), ("Dinheiro", 2, Decimal("130.10"))
    )
    credito = c.db.query(VendaPagamento).filter_by(forma_pagamento_id=3).one()
    assert cliente.credito == 0
    assert _entrada_financeira(c) == Decimal("130.10")
    c.excluir(credito.id)
    assert cliente.credito == Decimal("4.90")
    assert [
        registro.tipo for registro in c.db.query(CreditoLog).order_by(CreditoLog.id)
    ] == [
        "uso_venda",
        "estorno_venda",
    ]
    assert c.db.query(Recebimento).one().valor_recebido == Decimal("130.10")
    assert _entrada_financeira(c) == Decimal("130.10")
    assert c.db.query(LancamentoManual).filter_by(
        status="previsto"
    ).one().valor == Decimal("4.90")


def test_exclusao_repetida_nao_devolve_credito_duas_vezes(pagamentos):
    c = pagamentos
    cliente = _credito(c)
    c.receber(("Crédito Cliente", 3, Decimal("4.90")))
    pagamento_id = c.db.query(VendaPagamento).one().id
    primeiro = c.excluir(pagamento_id)
    assert c.excluir(pagamento_id) == primeiro
    assert cliente.credito == Decimal("4.90")
    assert c.db.query(CreditoLog).filter_by(tipo="estorno_venda").count() == 1


def test_baixas_mistas_em_conta_existente_desfazem_apenas_pagamento_escolhido(
    pagamentos,
):
    c = pagamentos
    conta = ContaReceber(
        tenant_id=c.tenant,
        venda_id=1,
        descricao="Conta inicial",
        dre_subcategoria_id=1,
        canal="loja_fisica",
        valor_original=135,
        valor_final=135,
        valor_recebido=0,
        status="pendente",
        user_id=1,
        data_emissao=date.today(),
        data_vencimento=date.today(),
    )
    c.db.add(conta)
    c.db.commit()
    c.receber(("Dinheiro", 2, 100), ("PIX", 1, 35))
    assert c.db.query(ContaReceber).count() == 1
    dinheiro = c.db.query(VendaPagamento).filter_by(forma_pagamento_id=2).one()
    c.excluir(dinheiro.id)
    assert conta.valor_recebido == Decimal("35")
    assert conta.status == "parcial"
    assert c.db.query(Recebimento).one().forma_pagamento_id == 1
    assert c.db.query(Recebimento).one().valor_recebido == Decimal("35")


def test_pagamento_parcialmente_absorvido_desfaz_baixa_e_conta_propria(pagamentos):
    c = pagamentos
    conta = ContaReceber(
        tenant_id=c.tenant,
        venda_id=1,
        descricao="Saldo anterior",
        dre_subcategoria_id=1,
        canal="loja_fisica",
        valor_original=60,
        valor_final=60,
        valor_recebido=0,
        status="pendente",
        user_id=1,
        data_emissao=date.today(),
        data_vencimento=date.today(),
    )
    c.db.add(conta)
    c.db.commit()
    c.receber(("Dinheiro", 2, 100))
    dinheiro_id = c.db.query(VendaPagamento).one().id
    assert c.db.query(ContaReceber).count() == 2
    c.receber(("PIX", 1, 35))
    conta_pix = c.db.query(ContaReceber).filter_by(forma_pagamento_id=1).one()
    c.excluir(dinheiro_id)
    assert conta.valor_recebido == 0
    assert conta.status == "pendente"
    assert conta_pix.valor_recebido == Decimal("35")
    assert conta_pix.status == "recebido"
    assert c.db.query(Recebimento).one().valor_recebido == Decimal("35")
    assert c.db.query(ContaReceber).filter_by(
        status="cancelado"
    ).one().valor_original == Decimal("40")
    c.receber(("Dinheiro", 2, 100))
    assert c.db.query(func.sum(Recebimento.valor_recebido)).scalar() == Decimal("135")
    assert c.db.query(func.sum(MovimentacaoCaixa.valor)).scalar() == 100
    assert _entrada_financeira(c) == Decimal("135")


@pytest.mark.parametrize(
    "forma,valor", [("Dinheiro", 135), ("Crédito Cliente", Decimal("4.90"))]
)
def test_falha_apos_estornos_faz_rollback_de_todos_os_efeitos(
    pagamentos, monkeypatch, forma, valor
):
    c = pagamentos
    cliente = _credito(c) if forma == "Crédito Cliente" else None
    c.receber((forma, 3 if cliente else 2, valor))
    pagamento_id = c.db.query(VendaPagamento).one().id
    antes_auditoria = c.db.query(AuditLog).count()
    original = exclusao_pagamento._sincronizar_espelhos

    def falhar(*args):
        original(*args)
        raise RuntimeError("Falha depois de alterar os espelhos")

    monkeypatch.setattr(exclusao_pagamento, "_sincronizar_espelhos", falhar)
    with pytest.raises(HTTPException) as exc:
        c.excluir(pagamento_id)
    assert exc.value.status_code == 500
    assert c.db.get(VendaPagamento, pagamento_id) is not None
    assert c.db.query(Recebimento).count() == 1
    assert c.db.query(AuditLog).count() == antes_auditoria
    if cliente:
        assert cliente.credito == 0
        assert c.db.query(CreditoLog).filter_by(tipo="estorno_venda").count() == 0
    else:
        assert c.db.query(MovimentacaoCaixa).count() == 1


def test_exclusao_nao_acessa_pagamento_de_outro_tenant(pagamentos, tenant_context):
    c = pagamentos
    c.receber(("Dinheiro", 2, 135))
    pagamento_id = c.db.query(VendaPagamento).one().id
    with pytest.raises(HTTPException) as exc:
        c.excluir(pagamento_id, tenant=uuid4())
    assert exc.value.status_code == 404
    tenant_context(c.tenant)
    assert c.db.query(MovimentacaoCaixa).count() == 1
    assert c.db.query(VendaPagamento).count() == 1


def test_caixa_fechado_bloqueia_sem_alterar_lancamentos(pagamentos):
    c = pagamentos
    c.receber(("Dinheiro", 2, 135))
    c.db.get(Caixa, 1).status = "fechado"
    c.db.commit()
    with pytest.raises(HTTPException) as exc:
        c.excluir(c.db.query(VendaPagamento).one().id)
    assert exc.value.status_code == 409
    assert "caixa fechado" in exc.value.detail
    assert c.db.query(MovimentacaoCaixa).count() == 1


def test_duplicidade_historica_de_caixa_exige_conferencia(pagamentos):
    c = pagamentos
    c.receber(("Dinheiro", 2, 135))
    c.db.add(
        MovimentacaoCaixa(
            tenant_id=c.tenant,
            caixa_id=1,
            venda_id=1,
            tipo="venda",
            valor=135,
            forma_pagamento="Dinheiro",
            usuario_id=1,
            usuario_nome="Operadora",
            data_movimento=datetime.now(),
        )
    )
    c.db.commit()
    with pytest.raises(HTTPException) as exc:
        c.excluir(c.db.query(VendaPagamento).one().id)
    assert exc.value.status_code == 409
    assert c.db.query(MovimentacaoCaixa).count() == 2
    assert c.db.query(Recebimento).count() == 1


def test_vinculo_legado_inequivoco_pode_ser_excluido(pagamentos):
    c = pagamentos
    c.receber(("Dinheiro", 2, 135))
    c.db.query(MovimentacaoCaixa).one().documento = None
    c.db.query(ContaReceber).one().observacoes = None
    c.db.query(Recebimento).one().observacoes = "Recebimento automatico"
    c.db.commit()
    c.excluir(c.db.query(VendaPagamento).one().id)
    assert c.db.query(MovimentacaoCaixa).count() == 0
    assert c.db.query(Recebimento).count() == 0


def test_pagamentos_legados_iguais_nao_excluem_recebivel_por_chute(pagamentos):
    c = pagamentos
    c.receber(("PIX", 1, 50), ("PIX", 1, 50))
    for conta in c.db.query(ContaReceber):
        conta.observacoes = None
    for baixa in c.db.query(Recebimento):
        baixa.observacoes = None
    c.db.commit()
    with pytest.raises(HTTPException) as exc:
        c.excluir(c.db.query(VendaPagamento).first().id)
    assert exc.value.status_code == 409
    assert c.db.query(Recebimento).count() == 2
    assert c.db.query(ContaReceber).filter_by(status="recebido").count() == 2


def test_parcelas_legadas_sem_flag_explicita_tem_associacao_unica(pagamentos):
    from app.vendas.finalizacao_recebiveis import criar_recebiveis_dos_novos_pagamentos

    c = pagamentos
    forma = c.db.get(FormaPagamento, 1)
    forma.tipo = "cartao_credito"
    forma.prazo_dias = 7
    pagamento = VendaPagamento(
        tenant_id=c.tenant,
        venda_id=1,
        caixa_id=1,
        forma_pagamento_id=1,
        forma_pagamento="PIX",
        valor=135,
        numero_parcelas=3,
        data_pagamento=datetime.now(),
        prazo_recebimento_dias=7,
    )
    c.db.add(pagamento)
    c.db.flush()
    criar_recebiveis_dos_novos_pagamentos(
        db=c.db,
        venda=c.venda,
        tenant_id=c.tenant,
        user_id=1,
        pagamentos_anteriores=[],
    )
    for conta in c.db.query(ContaReceber):
        conta.observacoes = None
        conta.eh_parcelado = False
    c.db.commit()
    c.excluir(pagamento.id)
    assert c.db.query(ContaReceber).filter_by(status="cancelado").count() == 3
    assert c.db.query(VendaPagamento).count() == 0


def test_excluir_pix_preserva_dinheiro_anterior_em_caixa_fechado(pagamentos):
    c = pagamentos
    c.receber(("Dinheiro", 2, 100))
    c.db.get(Caixa, 1).status = "fechado"
    c.db.commit()
    # O caixa novo ja existe no fixture; este pagamento ocorre nele.
    c.venda.status = "aberta"
    c.db.commit()
    finalizacao.finalizar_venda(
        venda_id=1,
        pagamentos=[dict(forma_pagamento="PIX", forma_pagamento_id=1, valor=35)],
        caixa_id=2,
        tenant_id=c.tenant,
        user_id=1,
        user_nome="Operadora",
        db=c.db,
        processar_baixa_estoque_item=lambda **kw: [],
    )
    pix = c.db.query(VendaPagamento).filter_by(forma_pagamento_id=1).one()
    # O mock legado de validar_caixa_aberto sempre fornece 1.
    pix.caixa_id = 2
    c.db.commit()
    c.excluir(pix.id)
    assert c.db.query(MovimentacaoCaixa).one().valor == 100
    assert c.db.query(Recebimento).one().valor_recebido == Decimal("100")
