"""Salvar/excluir pagamento não substituem a finalização da venda reaberta."""

from decimal import Decimal
from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi import HTTPException
from sqlalchemy import Enum
from sqlalchemy.schema import CreateTable

from app.financeiro_models import ContaReceber, MovimentacaoFinanceira, Recebimento
from app.grupo_comercial_models import (
    GrupoComercial,
    GrupoComercialEstoqueCompartilhado,
    GrupoComercialMembro,
)
from app.ia.aba5_models import FluxoCaixa
from app.vendas import VendaService, crud_routes, finalizacao, pagamentos_routes
from app.vendas import status_routes
from app.vendas.schemas import CriarVendaRequest
from app.vendas_models import VendaPagamento
from app.veterinario_models import VetPartnerLink
from tests.unit import test_finalizacao_recebiveis_atomicidade as recebiveis

cenario = recebiveis.cenario


def _usuario(cenario):
    return SimpleNamespace(id=1, nome="Teste", email="teste@localhost"), cenario.tenant


def _status(cenario, status="finalizada", tenant=None):
    usuario, tenant_id = _usuario(cenario)
    return status_routes.atualizar_status_venda(
        1, {"status": status}, cenario.db, (usuario, tenant or tenant_id)
    )


@pytest.fixture
def spies(cenario, monkeypatch):
    eventos, cupons, comissoes = [], [], []
    monkeypatch.setattr(
        finalizacao, "publicar_eventos_finalizacao", lambda **kw: eventos.append(kw)
    )
    monkeypatch.setattr(
        finalizacao, "consumir_cupom_finalizacao", lambda **kw: cupons.append(kw)
    )
    monkeypatch.setattr(status_routes, "log_action", lambda *a, **kw: None)
    monkeypatch.setattr(
        status_routes,
        "_gerar_comissoes_pendentes_venda",
        lambda **kw: comissoes.append(kw),
    )
    monkeypatch.setattr(VendaService, "_processar_baixa_estoque_item", lambda **kw: [])
    return SimpleNamespace(eventos=eventos, cupons=cupons, comissoes=comissoes)


def test_put_com_funcionario_e_recebimentos_suficientes_mantem_aberta(
    cenario, spies, monkeypatch
):
    # A serialização do vendedor executa a política de compartilhamento no PG.
    # O catálogo vazio fica no schema descartável, nunca no catálogo público.
    if cenario.db.get_bind().dialect.name == "postgresql":
        with cenario.db.get_bind().begin() as conn:
            for model in (
                VetPartnerLink,
                GrupoComercial,
                GrupoComercialMembro,
                GrupoComercialEstoqueCompartilhado,
            ):
                conn.execute(
                    CreateTable(model.__table__, include_foreign_key_constraints=[])
                )
    cenario.finalizar(135)
    cenario.venda.status = "aberta"
    cenario.venda.funcionario_id = 77
    cenario.venda.vendedor_funcionario_id = 77
    cenario.db.commit()
    spies.eventos.clear()
    spies.cupons.clear()
    monkeypatch.setattr(crud_routes, "log_action", lambda *a, **kw: None)
    monkeypatch.setattr(crud_routes, "validar_vendedor_funcionario", lambda *a: None)
    monkeypatch.setattr(crud_routes, "ajustar_estoque_edicao_venda", lambda **kw: {})
    monkeypatch.setattr(crud_routes, "atualizar_itens_venda_aberta", lambda **kw: {})
    dados = CriarVendaRequest(
        funcionario_id=77,
        vendedor_funcionario_id=77,
        desconto_venda_valor=0,
        itens=[
            {
                "tipo": "produto",
                "produto_id": 1,
                "quantidade": 1,
                "preco_unitario": 100,
                "subtotal": 100,
                "ignorar_recorrencia": True,
            }
        ],
    )
    with pytest.raises(HTTPException) as erro:
        crud_routes.atualizar_venda(1, dados, cenario.db, _usuario(cenario))
    assert erro.value.status_code == 409
    dados.justificativa_pagamento_excedente = (
        "Desconto autorizado após recebimento; excedente será conferido pelo gestor."
    )
    dados.contexto_pagamento_excedente = erro.value.detail[
        "contexto_pagamento_excedente"
    ]
    resultado = crud_routes.atualizar_venda(1, dados, cenario.db, _usuario(cenario))
    assert resultado["status"] == cenario.venda.status == "aberta"
    assert cenario.venda.total == Decimal("100")
    assert cenario.db.query(VendaPagamento).count() == 1
    assert not spies.eventos and not spies.cupons and not spies.comissoes
    assert _status(cenario) == {"success": True, "status": "finalizada"}
    assert len(spies.eventos) == len(spies.cupons) == len(spies.comissoes) == 1


@pytest.mark.parametrize("origem", ["aberta", "baixa_parcial"])
def test_patch_finalizada_executa_orquestrador_sem_duplicar_recebimentos(
    cenario, spies, origem
):
    cenario.db.add(
        VendaPagamento(
            venda_id=1,
            tenant_id=cenario.tenant,
            forma_pagamento="PIX",
            forma_pagamento_id=1,
            valor=135,
        )
    )
    cenario.venda.status = origem
    cenario.venda.funcionario_id = 77
    cenario.venda.cupom_code = "CUPOM-HISTORICO"
    cenario.venda.cupom_discount_applied = 5
    cenario.db.commit()
    assert _status(cenario) == {"success": True, "status": "finalizada"}
    assert cenario.venda.data_finalizacao is not None
    assert cenario.db.query(VendaPagamento).count() == 1
    assert len(spies.eventos) == len(spies.cupons) == len(spies.comissoes) == 1
    assert spies.cupons[0]["cupom_code"] == "CUPOM-HISTORICO"
    assert spies.cupons[0]["cupom_discount_applied"] == 5
    assert spies.comissoes[0]["tenant_id"] == cenario.tenant
    assert _status(cenario) == {"success": True, "status": "finalizada"}
    assert len(spies.eventos) == len(spies.cupons) == len(spies.comissoes) == 1


@pytest.mark.parametrize("valor", [0, 100])
def test_patch_finalizada_com_saldo_pendente_nao_fecha_nem_reaplica_beneficios(
    cenario, spies, valor
):
    if valor:
        cenario.db.add(
            VendaPagamento(
                venda_id=1,
                tenant_id=cenario.tenant,
                forma_pagamento="PIX",
                forma_pagamento_id=1,
                valor=valor,
            )
        )
    cenario.db.commit()
    with pytest.raises(HTTPException) as erro:
        _status(cenario)
    assert erro.value.status_code == 400
    assert cenario.venda.status == "aberta"
    assert not spies.eventos and not spies.cupons and not spies.comissoes


def test_patch_finalizada_nao_reativa_cancelada(cenario, spies):
    cenario.venda.status = "cancelada"
    cenario.db.commit()
    with pytest.raises(HTTPException) as erro:
        _status(cenario)
    assert erro.value.status_code == 400
    assert cenario.venda.status == "cancelada"
    assert not spies.eventos and not spies.cupons and not spies.comissoes


def test_patch_finalizada_nao_acessa_venda_de_outro_tenant(cenario, spies):
    with pytest.raises(HTTPException) as erro:
        _status(cenario, tenant=uuid4())
    assert erro.value.status_code == 404
    assert not spies.eventos and not spies.cupons and not spies.comissoes


def test_patch_finalizada_preserva_entregador_obrigatorio(cenario, spies):
    cenario.venda.tem_entrega = True
    cenario.db.commit()
    with pytest.raises(HTTPException) as erro:
        _status(cenario)
    assert erro.value.status_code == 400
    assert cenario.venda.status == "aberta"
    assert not spies.eventos and not spies.cupons and not spies.comissoes


def test_patch_finalizada_preserva_opcao_sem_beneficios(cenario, spies, monkeypatch):
    cenario.venda.nao_gerar_beneficios = True
    cenario.venda.justificativa_nao_gerar_beneficios = "Venda de consumo interno"
    cenario.db.commit()
    chamadas = []

    def finalizar(**kwargs):
        chamadas.append(kwargs)
        cenario.venda.status = "finalizada"
        return {"venda": {"status": "finalizada"}}

    monkeypatch.setattr(VendaService, "finalizar_venda", finalizar)
    _status(cenario)
    assert chamadas[0]["nao_gerar_beneficios"] is True
    assert (
        chamadas[0]["justificativa_nao_gerar_beneficios"] == "Venda de consumo interno"
    )
    assert cenario.venda.nao_gerar_beneficios is True


@pytest.mark.parametrize("valor_restante", [0, 100, 135, 200])
def test_excluir_pagamento_mantem_venda_aberta_independente_do_saldo(
    cenario, monkeypatch, valor_restante
):
    monkeypatch.setattr(pagamentos_routes, "log_action", lambda *a, **kw: None)
    excluido = VendaPagamento(
        venda_id=1,
        tenant_id=cenario.tenant,
        forma_pagamento="PIX",
        forma_pagamento_id=1,
        valor=20,
    )
    cenario.db.add(excluido)
    if valor_restante:
        cenario.db.add(
            VendaPagamento(
                venda_id=1,
                tenant_id=cenario.tenant,
                forma_pagamento="PIX",
                forma_pagamento_id=1,
                valor=valor_restante,
            )
        )
    cenario.venda.rentabilidade_snapshot = {"snapshot_version": 6}
    cenario.db.flush()
    # A exclusão segura exige a partida do pagamento; esta fixture testa o
    # estado da venda sem depender de vínculos financeiros antigos ambíguos.
    conta = ContaReceber(
        tenant_id=cenario.tenant,
        venda_id=1,
        forma_pagamento_id=1,
        descricao="Recebível do pagamento a excluir",
        valor_original=20,
        valor_final=20,
        valor_recebido=20,
        status="recebido",
        user_id=1,
        dre_subcategoria_id=1,
        canal="loja_fisica",
        data_emissao=excluido.data_pagamento.date(),
        data_vencimento=excluido.data_pagamento.date(),
        observacoes=f"[venda_pagamento:{excluido.id}]",
    )
    cenario.db.add(conta)
    cenario.db.flush()
    cenario.db.add(
        Recebimento(
            tenant_id=cenario.tenant,
            conta_receber_id=conta.id,
            forma_pagamento_id=1,
            valor_recebido=20,
            data_recebimento=excluido.data_pagamento.date(),
            user_id=1,
            observacoes=f"[venda_pagamento:{excluido.id}]",
        )
    )
    engine = cenario.db.get_bind()
    for model in (MovimentacaoFinanceira, FluxoCaixa):
        for coluna in model.__table__.columns:
            if isinstance(coluna.type, Enum):
                coluna.type.create(engine, checkfirst=True)
        with engine.begin() as connection:
            connection.execute(
                CreateTable(model.__table__, include_foreign_key_constraints=[])
            )
    cenario.db.commit()
    resultado = pagamentos_routes.excluir_pagamento(
        excluido.id, cenario.db, _usuario(cenario)
    )
    assert resultado["novo_status"] == cenario.venda.status == "aberta"
    assert resultado["total_pago"] == valor_restante
    assert cenario.venda.rentabilidade_snapshot is None
    assert cenario.db.query(VendaPagamento).count() == bool(valor_restante)


def test_excluir_pagamento_nao_reativa_venda_cancelada(cenario, monkeypatch):
    pagamento = VendaPagamento(
        venda_id=1,
        tenant_id=cenario.tenant,
        forma_pagamento="PIX",
        forma_pagamento_id=1,
        valor=135,
    )
    cenario.db.add(pagamento)
    cenario.venda.status = "cancelada"
    cenario.db.commit()
    with pytest.raises(HTTPException) as erro:
        pagamentos_routes.excluir_pagamento(pagamento.id, cenario.db, _usuario(cenario))
    assert erro.value.status_code == 400
    assert cenario.venda.status == "cancelada"
    assert cenario.db.query(VendaPagamento).count() == 1
