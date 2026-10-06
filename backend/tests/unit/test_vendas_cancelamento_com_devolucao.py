"""Cancelamento não pode desfazer uma venda já devolvida."""

from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest
from fastapi import HTTPException

from app.dre_canais import agregacao
from app.vendas.cancelamento_service import cancelar_venda
from app.vendas_devolucoes_models import VendaDevolucao
from app.vendas_models import Venda


def test_cancelamento_com_devolucao_bloqueia_antes_de_estoque_dre_e_caixa(monkeypatch):
    tenant_id = uuid4()
    venda = SimpleNamespace(id=12, numero_venda="VEN-12", status="finalizada_devolucao")
    evento = SimpleNamespace(
        tenant_id=tenant_id,
        venda_id=venda.id,
        canal="loja_fisica",
        valor_devolvido=Decimal("20.00"),
        custo_produtos_estornado=Decimal("8.00"),
        custo_servicos_estornado=Decimal("0"),
        custo_pendente=False,
    )
    estoque = SimpleNamespace(quantidade=10)
    caixa = SimpleNamespace(valor=Decimal("20.00"))

    consulta_venda = MagicMock()
    consulta_venda.filter_by.return_value = consulta_venda
    consulta_venda.with_for_update.return_value = consulta_venda
    consulta_venda.first.return_value = venda
    consulta_evento = MagicMock()
    consulta_evento.filter_by.return_value = consulta_evento
    consulta_evento.first.return_value = evento
    db = MagicMock()

    def consultar(modelo):
        if modelo is Venda:
            return consulta_venda
        if modelo is VendaDevolucao:
            return consulta_evento
        raise AssertionError(f"Consulta com efeito posterior ao bloqueio: {modelo}")

    db.query.side_effect = consultar
    monkeypatch.setattr("app.tenancy.context.set_tenant_context", lambda *_args: None)
    monkeypatch.setattr(
        agregacao,
        "_devolucoes_periodo_query",
        lambda *_args: SimpleNamespace(all=lambda: [evento]),
    )

    with patch("app.estoque.service.EstoqueService.estornar_estoque") as estornar:
        with pytest.raises(HTTPException) as erro:
            cancelar_venda(
                venda_id=venda.id,
                motivo="Teste",
                user_id=7,
                tenant_id=tenant_id,
                db=db,
            )

    assert erro.value.status_code == 409
    assert "devolucao registrada" in erro.value.detail
    consulta_venda.filter_by.assert_called_once_with(id=venda.id, tenant_id=tenant_id)
    consulta_venda.with_for_update.assert_called_once()
    consulta_evento.filter_by.assert_called_once_with(
        tenant_id=tenant_id, venda_id=venda.id
    )
    assert [call.args[0] for call in db.query.call_args_list] == [Venda, VendaDevolucao]
    estornar.assert_not_called()
    db.add.assert_not_called()
    db.delete.assert_not_called()
    db.flush.assert_not_called()
    db.commit.assert_not_called()
    db.rollback.assert_called_once()
    assert venda.status == "finalizada_devolucao"
    assert estoque.quantidade == 10
    assert caixa.valor == Decimal("20.00")

    dados_dre = {}
    agregacao.agregar_devolucoes_por_canal(db, 10, 2026, tenant_id, dados_dre)
    assert dados_dre["loja_fisica"]["devolucoes"] == Decimal("20.00")
    assert dados_dre["loja_fisica"]["cmv"] == Decimal("-8.00")
