from types import SimpleNamespace
from unittest.mock import Mock

from app.services.produto_sku_service import (
    buscar_produto_por_sku,
    buscar_produtos_por_skus,
)


def _produto(**overrides):
    dados = {
        "codigo": "647",
        "codigo_barras": "7898349701213",
        "codigos_barras_alternativos": '["ATC647"]',
    }
    dados.update(overrides)
    return SimpleNamespace(**dados)


def test_buscar_produto_por_sku_encontra_codigo_alternativo_exato():
    produto = _produto()
    consulta_exata = Mock()
    consulta_exata.filter.return_value.all.return_value = []
    consulta_alias = Mock()
    consulta_alias.filter.return_value.all.return_value = [produto]
    db = Mock()
    db.query.side_effect = [consulta_exata, consulta_alias]

    encontrado = buscar_produto_por_sku(
        db,
        tenant_id="tenant-1",
        sku="atc647",
    )

    assert encontrado is produto


def test_buscar_produtos_por_skus_nao_aceita_substring_do_codigo_alternativo():
    produto = _produto(codigos_barras_alternativos='["ATC647-OUTRO"]')
    consulta_exata = Mock()
    consulta_exata.filter.return_value.all.return_value = []
    consulta_alias = Mock()
    consulta_alias.filter.return_value.all.return_value = [produto]
    db = Mock()
    db.query.side_effect = [consulta_exata, consulta_alias]

    encontrados = buscar_produtos_por_skus(
        db,
        tenant_id="tenant-1",
        skus=["ATC647"],
    )

    assert encontrados == {}
