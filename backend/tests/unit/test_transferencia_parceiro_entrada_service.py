from decimal import Decimal
from types import SimpleNamespace

import os
import pytest
from fastapi import HTTPException

os.environ["DATABASE_URL"] = os.environ.get("DATABASE_URL") or "sqlite:///./test.db"
os.environ["DEBUG"] = "false"

from app.estoque.transferencia_parceiro_entrada_service import (
    preparar_itens_entrada_parceiro,
)


def test_preparar_itens_entrada_parceiro_usa_total_lancado_e_soma_divida():
    produtos = {
        10: SimpleNamespace(
            id=10,
            nome="Defenza",
            codigo="DEF",
            codigo_barras="789",
            preco_custo=20,
            estoque_atual=3,
            is_parent=False,
            tipo_produto="SIMPLES",
            tipo_kit=None,
        ),
        11: SimpleNamespace(
            id=11,
            nome="Vermifugo",
            codigo="VER",
            codigo_barras=None,
            preco_custo=25,
            estoque_atual=1,
            is_parent=False,
            tipo_produto="SIMPLES",
            tipo_kit=None,
        ),
    }
    itens = [
        SimpleNamespace(produto_id=10, quantidade=2, custo_unitario=25, valor_total=50),
        SimpleNamespace(produto_id=11, quantidade=1, custo_unitario=None, valor_total=None),
    ]

    processados, total = preparar_itens_entrada_parceiro(produtos, itens)

    assert total == Decimal("75.00")
    assert [(item["produto_id"], item["total_item"]) for item in processados] == [
        (10, 50.0),
        (11, 25.0),
    ]


def test_preparar_itens_entrada_parceiro_rejeita_total_zerado():
    produtos = {
        10: SimpleNamespace(
            id=10,
            nome="Defenza",
            codigo="DEF",
            codigo_barras="789",
            preco_custo=0,
            estoque_atual=3,
            is_parent=False,
            tipo_produto="SIMPLES",
            tipo_kit=None,
        )
    }

    with pytest.raises(HTTPException) as exc_info:
        preparar_itens_entrada_parceiro(
            produtos,
            [SimpleNamespace(produto_id=10, quantidade=1, custo_unitario=0, valor_total=0)],
        )

    assert exc_info.value.status_code == 400
    assert "valor total maior que zero" in exc_info.value.detail.lower()
