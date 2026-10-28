"""Embalagens comerciais compartilham o estoque da variacao unitaria."""

from types import SimpleNamespace
from unittest.mock import MagicMock
from uuid import UUID

import pytest
from fastapi import HTTPException

from app.produtos_models import Produto, ProdutoKitComponente
from app.vendas import cancelamento_estoque, edicao_estoque, estoque_baixa
from app.vendas.devolucoes_routes import _validar_produto_devolucao


TENANT = UUID("11111111-1111-1111-1111-111111111111")


def _produto(tipo_produto="VARIACAO", tipo_kit="VIRTUAL"):
    return SimpleNamespace(
        id=10,
        nome="Churu Atum - embalagem",
        tipo_produto=tipo_produto,
        tipo_kit=tipo_kit,
        controlar_estoque=True,
        estoque_atual=100,
        situacao=True,
    )


def _db_componente(kit, fator):
    componente = SimpleNamespace(
        id=20,
        nome="Churu Atum - tubo",
        tipo_produto="VARIACAO",
        tipo_kit=None,
        situacao=True,
    )
    relacao = SimpleNamespace(produto_componente_id=20, quantidade=fator)
    query_produto = MagicMock()
    query_produto.filter.return_value.first.side_effect = [kit, componente]
    query_relacao = MagicMock()
    query_relacao.filter.return_value.all.return_value = [relacao]
    db = MagicMock()
    db.query.side_effect = lambda model: {
        Produto: query_produto,
        ProdutoKitComponente: query_relacao,
    }[model]
    return db, query_produto, query_relacao


@pytest.mark.parametrize("fator", [4, 24])
def test_venda_variacao_virtual_baixa_tubos_e_edicao_reduzida_devolve_tubos(
    monkeypatch, fator
):
    kit = _produto()
    db, query_produto, query_relacao = _db_componente(kit, fator)
    saldos = {kit.id: 0, 20: 240}

    def baixar(**dados):
        produto_id, quantidade = dados["produto_id"], dados["quantidade"]
        anterior = saldos[produto_id]
        saldos[produto_id] -= quantidade
        return {
            "produto_nome": "Churu Atum - tubo",
            "estoque_anterior": anterior,
            "estoque_novo": saldos[produto_id],
        }

    def estornar(**dados):
        assert dados["tenant_id"] == TENANT
        saldos[dados["produto_id"]] += dados["quantidade"]

    monkeypatch.setattr(estoque_baixa.EstoqueService, "baixar_estoque", baixar)
    monkeypatch.setattr(edicao_estoque.EstoqueService, "estornar_estoque", estornar)
    resultados = estoque_baixa.processar_baixa_estoque_item(
        produto=kit,
        quantidade_vendida=2,
        venda_id=30,
        user_id=40,
        tenant_id=TENANT,
        db=db,
        product_variation_id=kit.id,
    )
    assert resultados[0]["produto_id"] == 20
    assert resultados[0]["quantidade"] == 2 * fator
    assert saldos == {10: 0, 20: 240 - 2 * fator}

    edicao_estoque._estornar_quantidade_reduzida(
        produto=kit,
        quantidade=1,
        venda=SimpleNamespace(id=30, numero_venda="V30"),
        user_id=40,
        tenant_id=TENANT,
        db=db,
    )
    assert saldos == {10: 0, 20: 240 - fator}
    filtros_variacao = query_produto.filter.call_args_list[0].args
    assert any(
        "produtos.tenant_id" in str(filtro) and filtro.right.value == TENANT
        for filtro in filtros_variacao
    )
    filtros_relacao = query_relacao.filter.call_args.args
    assert any(
        "produto_kit_componentes.tenant_id" in str(filtro)
        and filtro.right.value == TENANT
        for filtro in filtros_relacao
    )


@pytest.mark.parametrize(
    "tipo_produto,tipo_kit",
    [("SIMPLES", None), ("VARIACAO", None), ("VARIACAO", "FISICO"), ("KIT", "FISICO")],
)
def test_variacao_comum_e_kit_fisico_usam_saldo_proprio(
    monkeypatch, tipo_produto, tipo_kit
):
    produto = _produto(tipo_produto, tipo_kit)
    baixar = MagicMock(
        return_value={
            "produto_nome": produto.nome,
            "estoque_anterior": 100,
            "estoque_novo": 98,
        }
    )
    estornar = MagicMock()
    monkeypatch.setattr(estoque_baixa.EstoqueService, "baixar_estoque", baixar)
    monkeypatch.setattr(edicao_estoque.EstoqueService, "estornar_estoque", estornar)
    db = MagicMock()
    estoque_baixa.processar_baixa_estoque_item(
        produto=produto,
        quantidade_vendida=2,
        venda_id=30,
        user_id=40,
        tenant_id=TENANT,
        db=db,
    )
    assert baixar.call_args.kwargs["produto_id"] == produto.id
    assert baixar.call_args.kwargs["quantidade"] == 2
    edicao_estoque._estornar_quantidade_reduzida(
        produto=produto,
        quantidade=1,
        venda=SimpleNamespace(id=30, numero_venda="V30"),
        user_id=40,
        tenant_id=TENANT,
        db=db,
    )
    assert estornar.call_args.kwargs["produto_id"] == produto.id
    assert estornar.call_args.kwargs["quantidade"] == 1
    db.query.assert_not_called()
    _validar_produto_devolucao(produto)


@pytest.mark.parametrize("tipo_produto", ["KIT", "VARIACAO"])
def test_estornos_completos_virtuais_exigem_prova_dos_componentes(tipo_produto):
    produto = _produto(tipo_produto)
    with pytest.raises(HTTPException) as erro:
        _validar_produto_devolucao(produto)
    assert erro.value.status_code == 409

    db = MagicMock()
    db.query.return_value.filter_by.return_value.with_for_update.return_value.populate_existing.return_value.one_or_none.return_value = produto
    with pytest.raises(HTTPException) as erro:
        cancelamento_estoque._preparar_grupo(
            db,
            SimpleNamespace(id=30),
            [],
            TENANT,
            TENANT,
            produto.id,
        )
    assert erro.value.status_code == 409
    db.add.assert_not_called()


def test_variacao_ausente_no_tenant_nao_baixa_o_produto_recebido(monkeypatch):
    db = MagicMock()
    consulta = db.query.return_value.filter.return_value
    consulta.first.return_value = None
    baixar = MagicMock()
    monkeypatch.setattr(estoque_baixa.EstoqueService, "baixar_estoque", baixar)
    with pytest.raises(ValueError, match="tenant do estoque"):
        estoque_baixa.processar_baixa_estoque_item(
            produto=_produto("SIMPLES", None),
            quantidade_vendida=1,
            venda_id=30,
            user_id=40,
            tenant_id=TENANT,
            db=db,
            product_variation_id=99,
        )
    baixar.assert_not_called()
