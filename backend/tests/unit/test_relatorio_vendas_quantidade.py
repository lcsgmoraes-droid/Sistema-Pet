from copy import deepcopy
from decimal import Decimal
from types import SimpleNamespace

import pytest

from app import relatorio_vendas_common


def _item(item_id, produto_id, quantidade):
    return SimpleNamespace(
        id=item_id,
        produto_id=produto_id,
        quantidade=Decimal(quantidade),
        produto=None,
    )


@pytest.fixture(autouse=True)
def _sem_calculo_promocional(monkeypatch):
    monkeypatch.setattr(
        relatorio_vendas_common, "_detectar_promocao_item", lambda *args: {}
    )


def _enriquecer(itens, snapshots):
    return relatorio_vendas_common._enriquecer_itens_promocionais(
        SimpleNamespace(itens=itens), snapshots
    )


def test_preserva_tres_casas_da_quantidade_sem_alterar_snapshot_ou_valores():
    snapshots = [
        {
            "venda_item_id": 10,
            "produto_id": 20,
            "quantidade": 0.13,
            "venda_bruta": 2.50,
            "desconto": 0.25,
            "cupom_desconto": 0.10,
            "valor_liquido": 1.95,
        }
    ]
    original = deepcopy(snapshots)

    resultado = _enriquecer([_item(10, 20, "0.125")], snapshots)

    assert resultado == [{**original[0], "quantidade": 0.125}]
    assert snapshots == original
    assert resultado[0] is not snapshots[0]


def test_itens_do_mesmo_produto_fora_de_ordem_casam_pelo_id_do_item():
    itens = [_item(10, 20, "0.125"), _item(11, 20, "0.375")]
    snapshots = [
        {"venda_item_id": 11, "produto_id": 20, "quantidade": 0.38},
        {"venda_item_id": 10, "produto_id": 20, "quantidade": 0.13},
    ]

    resultado = _enriquecer(itens, snapshots)

    assert [item["quantidade"] for item in resultado] == [0.375, 0.125]


def test_id_ausente_no_modelo_nao_usa_outro_item_do_mesmo_produto():
    snapshot = {"venda_item_id": 99, "produto_id": 20, "quantidade": 0.13}

    resultado = _enriquecer([_item(10, 20, "0.375")], [snapshot])

    assert resultado == [snapshot]


def test_snapshot_legado_casa_por_posicao_ou_produto_sem_reutilizar_item():
    itens = [
        _item(10, 20, "0.125"),
        _item(11, 30, "0.375"),
        _item(12, 20, "0.625"),
    ]
    snapshots = [
        {"produto_id": 30, "quantidade": 0.38},
        {"produto_id": 20, "quantidade": 0.13},
        {"produto_id": 20, "quantidade": 0.63},
    ]

    resultado = _enriquecer(itens, snapshots)

    assert [item["quantidade"] for item in resultado] == [0.375, 0.125, 0.625]


def test_preserva_quantidade_do_snapshot_quando_nao_existe_modelo():
    snapshots = [{"produto_id": 20, "quantidade": 0.13}]

    assert _enriquecer([], snapshots) == snapshots


def test_quantidade_original_zero_tambem_e_preservada():
    snapshots = [{"venda_item_id": 10, "produto_id": 20, "quantidade": 0.13}]

    resultado = _enriquecer([_item(10, 20, "0.000")], snapshots)

    assert resultado[0]["quantidade"] == 0


def test_snapshot_legado_recebe_codigo_publico_sem_depender_de_grupo_salvo():
    item = _item(10, 20, "2.000")
    item.produto = SimpleNamespace(codigo="  RACAO-0007  ")
    snapshot = {"venda_item_id": 10, "produto_id": 20, "quantidade": 2}

    resultado = _enriquecer([item], [snapshot])

    assert resultado[0]["produto_codigo"] == "RACAO-0007"
    assert "produto_codigo" not in snapshot


def test_produto_sem_codigo_publico_nunca_exibe_id_interno_como_codigo():
    item = _item(10, 20, "2.000")
    item.produto = SimpleNamespace(id=20, codigo="")
    snapshot = {"venda_item_id": 10, "produto_id": 20, "quantidade": 2}

    assert "produto_codigo" not in _enriquecer([item], [snapshot])[0]
