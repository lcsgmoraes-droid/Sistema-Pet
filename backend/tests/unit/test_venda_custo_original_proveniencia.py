from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from app.vendas.custo_original import registrar_custo_original_saida
from app.vendas.devolucao_dre import custo_original_item_devolvido


def _item(*, item_id=7, produto_id=11, quantidade="2"):
    return SimpleNamespace(
        id=item_id,
        venda_id=123,
        tipo="produto",
        produto_id=produto_id,
        quantidade=Decimal(quantidade),
        custo_original_saida=None,
    )


def _saida(*, produto_id=11, quantidade="2", custo="30", movimento_id=91):
    return {
        "produto_id": produto_id,
        "quantidade": quantidade,
        "valor_total": custo,
        "movimentacao_id": movimento_id,
    }


def _devolver(item, *, quantidade="1", anterior="0", tenant="tenant-venda"):
    venda = SimpleNamespace(id=123, rentabilidade_snapshot={"snapshot_version": 5})
    db = MagicMock()
    resultado = custo_original_item_devolvido(
        db,
        venda,
        item,
        Decimal(quantidade),
        tenant,
        Decimal(anterior),
    )
    db.query.assert_not_called()
    return resultado


def test_comprovante_capturado_apos_baixa_nao_e_sobrescrito_por_custo_atual():
    item = _item()
    assert registrar_custo_original_saida(item, [_saida(custo="30")], "tenant-venda")
    comprovante = dict(item.custo_original_saida)
    assert comprovante["venda_item_id"] == 7
    assert comprovante["movimentacao_id"] == 91
    assert comprovante["custo_total"] == "30.00"

    assert not registrar_custo_original_saida(
        item, [_saida(custo="99", movimento_id=92)], "tenant-venda"
    )
    assert item.custo_original_saida == comprovante
    assert _devolver(item) == (Decimal("15.00"), "baixa_estoque_venda", False)


@pytest.mark.parametrize(
    "resultados",
    [
        [],
        [_saida(custo="0")],
        [_saida(quantidade="3")],
        [_saida(movimento_id=None)],
        [_saida(), _saida(movimento_id=92)],
    ],
)
def test_baixa_sem_prova_inequivoca_nao_grava_comprovante(resultados):
    item = _item()
    assert not registrar_custo_original_saida(item, resultados, "tenant-venda")
    assert item.custo_original_saida is None


def test_snapshot_v5_e_saida_legada_reprocessada_nao_provam_custo_original():
    item = _item()
    assert _devolver(item) == (Decimal("0"), "sem_custo_original", True)


def test_comprovante_de_outra_linha_ou_tenant_e_rejeitado():
    item = _item()
    registrar_custo_original_saida(item, [_saida()], "tenant-venda")
    item.custo_original_saida = dict(item.custo_original_saida, venda_item_id=8)
    assert _devolver(item)[2] is True

    item.custo_original_saida = dict(item.custo_original_saida, venda_item_id=7)
    assert _devolver(item, tenant="outro-tenant")[2] is True


def test_itens_repetidos_tem_comprovantes_independentes():
    primeiro = _item(item_id=7)
    segundo = _item(item_id=8)
    assert registrar_custo_original_saida(
        primeiro, [_saida(custo="10", movimento_id=91)], "tenant-venda"
    )
    assert registrar_custo_original_saida(
        segundo, [_saida(custo="20", movimento_id=92)], "tenant-venda"
    )
    assert _devolver(primeiro)[0] == Decimal("5.00")
    assert _devolver(segundo)[0] == Decimal("10.00")


def test_devolucoes_parciais_preservam_ultimo_centavo():
    item = _item(quantidade="3")
    registrar_custo_original_saida(
        item, [_saida(quantidade="3", custo="0.02")], "tenant-venda"
    )
    parcelas = [_devolver(item, anterior=str(anterior))[0] for anterior in range(3)]
    assert parcelas == [Decimal("0.01"), Decimal("0.00"), Decimal("0.01")]


def test_comprovante_de_estoque_compartilhado_valida_tenant_de_origem():
    item = _item()
    item.estoque_origem_tenant_id = "tenant-estoque"
    registrar_custo_original_saida(item, [_saida()], "tenant-estoque")
    assert _devolver(item, tenant="tenant-venda")[0] == Decimal("15.00")


def test_devolucao_de_servico_nao_reverte_custo_incurrido():
    item = _item()
    item.tipo = "servico"
    assert _devolver(item) == (Decimal("0"), "servico_custo_mantido", False)
