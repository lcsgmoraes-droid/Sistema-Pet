"""Cancelamento comercial com nota fiscal independente: estoque e caixa reais."""

from datetime import datetime
from uuid import uuid4
from unittest.mock import MagicMock

import pytest
from fastapi import HTTPException

from app.caixa_models import MovimentacaoCaixa
from app.financeiro_models import ContaReceber, Recebimento
from app.intnfe import emission
from app.intnfe.models import IntNFeEmissionSequence
from app.models import Tenant
from app.produto_identidade_models import ProdutoIdentidade  # noqa: F401 - FK de Produto
from app.produtos_lembretes_variacoes_models import ProdutoProtocoloRecorrencia
from app.produtos_models import (
    EstoqueMovimentacao,
    Produto,
    ProdutoBlingSync,
    ProdutoLote,
)
from app.tenancy.context import set_current_tenant
from app.vendas.cancelamento_service import cancelar_venda
from app.vendas.fiscal_status import pendencia_fiscal_cancelamento
from app.vendas_models import Venda, VendaItem, VendaPagamento
from app.xml_contabilidade_models import XmlContabilidadeConfig
from tests.unit import test_cancelamento_pagamentos_caixa as pagamentos_caixa

cenario = pagamentos_caixa.cenario
cancelamento = pagamentos_caixa.cancelamento


@pytest.fixture
def venda_com_nota(cancelamento):
    c = cancelamento
    for model in (
        Tenant,
        ProdutoIdentidade,
        Produto,
        ProdutoLote,
        ProdutoProtocoloRecorrencia,
        EstoqueMovimentacao,
        ProdutoBlingSync,
        XmlContabilidadeConfig,
        IntNFeEmissionSequence,
    ):
        model.__table__.create(c.db.bind, checkfirst=True)
    c.db.add(
        Tenant(
            id=str(c.tenant), name="Loja QA fiscal", name_normalized="loja qa fiscal"
        )
    )
    c.produto = Produto(
        tenant_id=c.tenant,
        user_id=1,
        codigo="QA-CANCELAMENTO-FISCAL",
        nome="Produto QA cancelamento fiscal",
        tipo="produto",
        tipo_produto="SIMPLES",
        estoque_atual=7,
        preco_venda=100,
        preco_custo=30,
    )
    c.db.add(c.produto)
    c.db.flush()
    c.db.add(
        VendaItem(
            tenant_id=c.tenant,
            venda_id=c.venda.id,
            produto_id=c.produto.id,
            tipo="produto",
            quantidade=3,
            preco_unitario=100 / 3,
            subtotal=100,
        )
    )
    c.venda.status = "pago_nf"
    c.venda.nfe_provider = "intnfe"
    c.venda.nfe_tipo = "nfce"
    c.venda.nfe_modelo = "65"
    c.venda.nfe_numero = 18574
    c.venda.nfe_serie = 1
    c.venda.nfe_chave = "1" * 44
    c.venda.nfe_correlation_id = "emissao-qa-18574"
    c.venda.nfe_protocolo = "protocolo-qa-18574"
    c.venda.nfe_ambiente = 1
    c.venda.nfe_status = "autorizada"
    c.venda.nfe_xml = "<NFe>documento original autorizado</NFe>"
    c.venda.nfe_data_emissao = datetime(2026, 10, 20, 10)
    c.venda.nfe_data_autorizacao = datetime(2026, 10, 20, 10, 1)
    c.db.commit()
    return c


def _documento_original(venda):
    campos = (
        "nfe_provider",
        "nfe_tipo",
        "nfe_modelo",
        "nfe_numero",
        "nfe_serie",
        "nfe_chave",
        "nfe_correlation_id",
        "nfe_protocolo",
        "nfe_ambiente",
        "nfe_status",
        "nfe_xml",
        "nfe_data_emissao",
        "nfe_data_autorizacao",
    )
    return {campo: getattr(venda, campo) for campo in campos}


def _cancelar(c):
    return cancelar_venda(
        c.venda.id,
        "Cliente desistiu da compra; regularizar documento fiscal.",
        1,
        c.tenant,
        c.db,
    )


@pytest.mark.parametrize("situacao", ["autorizada", "processando", "inconclusiva"])
def test_cancelamento_comercial_preserva_documento_e_estorna_financeiro_uma_vez(
    venda_com_nota, situacao
):
    c = venda_com_nota
    c.venda.nfe_status = situacao
    c.db.commit()
    documento = _documento_original(c.venda)
    ids_pagamentos = [pagamento.id for pagamento in c.pagamentos]

    resultado = _cancelar(c)

    assert resultado["venda"]["status"] == "cancelada"
    assert resultado["venda"]["pendencia_fiscal_cancelamento"] is True
    assert c.venda.nfe_cancelamento_status == "pendente"
    assert _documento_original(c.venda) == documento
    assert c.db.get(Produto, c.produto.id).estoque_atual == 10
    movimentos = c.db.query(EstoqueMovimentacao).all()
    assert len(movimentos) == 1
    assert movimentos[0].tipo == "entrada"
    assert movimentos[0].quantidade == 3
    assert movimentos[0].tenant_id == c.tenant
    assert [c.db.get(VendaPagamento, i).status for i in ids_pagamentos] == [
        "cancelado",
        "cancelado",
        "estornado",
        "recusado",
    ]
    assert {conta.status for conta in c.db.query(ContaReceber).all()} == {"cancelado"}
    assert c.db.query(Recebimento).count() == 2
    assert c.db.query(MovimentacaoCaixa).count() == 0

    with pytest.raises(HTTPException, match="já está cancelada"):
        _cancelar(c)
    assert c.db.get(Produto, c.produto.id).estoque_atual == 10
    assert c.db.query(EstoqueMovimentacao).count() == 1
    assert c.db.query(Recebimento).count() == 2


def test_confirmacao_fiscal_posterior_nao_repete_estornos_nem_reativa_venda(
    venda_com_nota,
):
    c = venda_com_nota
    _cancelar(c)
    assert pendencia_fiscal_cancelamento(c.venda) is True
    ids_pagamentos = [pagamento.id for pagamento in c.pagamentos]
    api = MagicMock()
    api.document_status.return_value = {"status": 5, "numero": 18574}
    api.document_events.return_value = []

    for _ in range(2):
        emission.reconcile(c.db, c.venda, api, connection=object(), token="token-qa")

    assert c.venda.status == "cancelada"
    assert c.venda.nfe_status == "cancelada"
    assert pendencia_fiscal_cancelamento(c.venda) is False
    assert c.venda.nfe_cancelamento_status == "confirmado"
    assert c.db.get(Produto, c.produto.id).estoque_atual == 10
    assert c.db.query(EstoqueMovimentacao).count() == 1
    assert c.db.query(MovimentacaoCaixa).count() == 0
    assert c.db.query(Recebimento).count() == 2
    assert [c.db.get(VendaPagamento, i).status for i in ids_pagamentos] == [
        "cancelado",
        "cancelado",
        "estornado",
        "recusado",
    ]
    assert c.venda.nfe_chave == "1" * 44
    assert c.venda.nfe_xml == "<NFe>documento original autorizado</NFe>"


def test_recusa_fiscal_501_posterior_mantem_nota_autorizada_e_estornos_comerciais(
    venda_com_nota,
):
    c = venda_com_nota
    _cancelar(c)
    api = MagicMock()
    api.document_status.return_value = {"status": 3, "numero": 18574, "serie": 1}
    api.document_events.return_value = [
        {
            "tipoEvento": "Cancelamento",
            "tipoEventoCodigo": 110111,
            "autorizado": False,
            "protocolo": None,
            "codigoRetorno": "501",
            "motivoRetorno": "NFC-e autorizada há mais de 30 minutos",
            "criadoEm": "2026-10-20T16:52:06.447Z",
            "xmlEvento": None,
        }
    ]
    for _ in range(2):
        emission.reconcile(c.db, c.venda, api, connection=object(), token="token-qa")
    assert c.venda.status == "cancelada"
    assert c.venda.nfe_status == "autorizada"
    assert c.venda.nfe_cancelamento_status == "recusado"
    assert c.venda.nfe_cancelamento_codigo == "501"
    assert "30 minutos" in c.venda.nfe_cancelamento_motivo
    assert pendencia_fiscal_cancelamento(c.venda) is True
    assert c.db.get(Produto, c.produto.id).estoque_atual == 10
    assert c.db.query(EstoqueMovimentacao).count() == 1
    assert c.db.query(MovimentacaoCaixa).count() == 0
    assert {conta.status for conta in c.db.query(ContaReceber).all()} == {"cancelado"}
    assert c.db.query(Recebimento).count() == 2
    assert c.venda.nfe_chave == "1" * 44
    assert c.venda.nfe_xml == "<NFe>documento original autorizado</NFe>"


@pytest.mark.parametrize(
    ("estado_anterior", "estado_esperado"),
    [
        (None, "pendente"),
        ("solicitado", "solicitado"),
        ("recusado", "recusado"),
        ("confirmado", "pendente"),
    ],
)
def test_cancelamento_comercial_preserva_tentativa_fiscal_existente(
    venda_com_nota, estado_anterior, estado_esperado
):
    c = venda_com_nota
    c.venda.nfe_cancelamento_status = estado_anterior
    c.venda.nfe_cancelamento_codigo = "501" if estado_anterior == "recusado" else None
    c.venda.nfe_cancelamento_motivo = (
        "Prazo ultrapassado" if estado_anterior == "recusado" else None
    )
    c.venda.nfe_cancelamento_solicitado_em = (
        datetime(2026, 10, 20, 10, 30)
        if estado_anterior in {"recusado", "solicitado"}
        else None
    )
    c.db.commit()

    _cancelar(c)

    assert c.venda.status == "cancelada"
    assert c.venda.nfe_status == "autorizada"
    assert c.venda.nfe_cancelamento_status == estado_esperado
    assert pendencia_fiscal_cancelamento(c.venda) is True
    if estado_anterior == "recusado":
        assert c.venda.nfe_cancelamento_codigo == "501"
        assert c.venda.nfe_cancelamento_motivo == "Prazo ultrapassado"
    if estado_anterior in {"recusado", "solicitado"}:
        assert c.venda.nfe_cancelamento_solicitado_em is not None


def test_falha_posterior_reverte_estoque_pagamentos_e_pendencia_fiscal(
    venda_com_nota, monkeypatch
):
    c = venda_com_nota
    documento = _documento_original(c.venda)
    tentativa_antes = c.venda.nfe_cancelamento_status
    ids_pagamentos = [pagamento.id for pagamento in c.pagamentos]

    def falhar(**_kwargs):
        raise RuntimeError("Falha QA após estornar estoque e caixa")

    monkeypatch.setattr("app.comissoes_estorno.estornar_comissoes_venda", falhar)
    with pytest.raises(HTTPException) as erro:
        _cancelar(c)

    assert erro.value.status_code == 500
    c.db.expire_all()
    assert c.db.get(Venda, c.venda.id).status == "pago_nf"
    assert c.db.get(Produto, c.produto.id).estoque_atual == 7
    assert c.db.query(EstoqueMovimentacao).count() == 0
    assert [c.db.get(VendaPagamento, i).status for i in ids_pagamentos] == [
        "pendente",
        "aprovado",
        "estornado",
        "recusado",
    ]
    assert {conta.status for conta in c.db.query(ContaReceber).all()} == {"recebido"}
    assert c.db.query(MovimentacaoCaixa).count() == 1
    assert c.db.query(Recebimento).count() == 2
    assert c.venda.nfe_cancelamento_status == tentativa_antes
    assert _documento_original(c.venda) == documento


def test_tenant_incorreto_nao_cancela_nem_estorna_venda_com_nf(venda_com_nota):
    c = venda_com_nota
    with pytest.raises(HTTPException) as erro:
        cancelar_venda(
            c.venda.id, "Tenant diferente não pode cancelar.", 1, uuid4(), c.db
        )
    assert erro.value.status_code == 404
    set_current_tenant(c.tenant)
    c.db.expire_all()
    assert c.db.get(Venda, c.venda.id).status == "pago_nf"
    assert c.db.get(Produto, c.produto.id).estoque_atual == 7
    assert c.db.query(EstoqueMovimentacao).count() == 0
    assert c.db.query(MovimentacaoCaixa).count() == 1


@pytest.mark.asyncio
async def test_excluir_tentativa_rejeitada_sem_autorizacao_nao_reativa_venda_cancelada(
    venda_com_nota,
):
    from app.nfe.operacional_routes import excluir_nota

    c = venda_com_nota
    c.venda.nfe_status = "rejeitada"
    c.venda.nfe_data_autorizacao = None
    c.db.commit()
    _cancelar(c)

    resultado = await excluir_nota(c.venda.id, db=c.db, user_and_tenant=c.auth)

    assert resultado["success"] is True
    assert c.venda.status == "cancelada"
    assert c.venda.nfe_status is None
    assert c.venda.nfe_correlation_id is None
    assert c.venda.nfe_chave is None
    assert pendencia_fiscal_cancelamento(c.venda) is False
    assert c.db.get(Produto, c.produto.id).estoque_atual == 10
    assert c.db.query(EstoqueMovimentacao).count() == 1


@pytest.mark.asyncio
async def test_nao_apaga_documento_pendente_de_venda_comercial_cancelada(
    venda_com_nota,
):
    from app.nfe.operacional_routes import excluir_nota

    c = venda_com_nota
    c.venda.nfe_status = "pendente"
    c.db.commit()
    _cancelar(c)
    documento = _documento_original(c.venda)

    with pytest.raises(HTTPException) as erro:
        await excluir_nota(c.venda.id, db=c.db, user_and_tenant=c.auth)

    assert erro.value.status_code == 409
    assert "pendência fiscal" in erro.value.detail
    assert c.venda.status == "cancelada"
    assert _documento_original(c.venda) == documento
    assert pendencia_fiscal_cancelamento(c.venda) is True
    assert c.db.get(Produto, c.produto.id).estoque_atual == 10
    assert c.db.query(EstoqueMovimentacao).count() == 1


@pytest.mark.parametrize(
    "novo_status", ["aberta", "finalizada", "pago_nf", "cancelada"]
)
def test_patch_status_nao_reativa_venda_cancelada_nem_repete_estornos(
    venda_com_nota, novo_status
):
    from app.vendas.status_routes import atualizar_status_venda

    c = venda_com_nota
    _cancelar(c)
    documento = _documento_original(c.venda)
    if novo_status == "cancelada":
        resultado = atualizar_status_venda(
            c.venda.id, {"status": novo_status}, db=c.db, user_and_tenant=c.auth
        )
        assert resultado == {"success": True, "status": "cancelada"}
    else:
        with pytest.raises(HTTPException) as erro:
            atualizar_status_venda(
                c.venda.id, {"status": novo_status}, db=c.db, user_and_tenant=c.auth
            )
        assert erro.value.status_code == 400
        assert "não pode ser reativada" in erro.value.detail
    assert c.venda.status == "cancelada"
    assert _documento_original(c.venda) == documento
    assert c.db.get(Produto, c.produto.id).estoque_atual == 10
    assert c.db.query(EstoqueMovimentacao).count() == 1
    assert c.db.query(MovimentacaoCaixa).count() == 0
