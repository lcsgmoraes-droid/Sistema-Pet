import os
from types import SimpleNamespace

os.environ["DATABASE_URL"] = os.environ.get("DATABASE_URL") or "sqlite:///./test.db"
os.environ["DEBUG"] = "false"

from app.produtos.categorias import (
    _calcular_niveis_categorias,
    _construir_arvore_categorias,
)


def test_calcular_niveis_categorias_monta_hierarquia_em_memoria():
    categorias = {
        1: SimpleNamespace(id=1, categoria_pai_id=None),
        2: SimpleNamespace(id=2, categoria_pai_id=1),
        3: SimpleNamespace(id=3, categoria_pai_id=2),
    }

    assert _calcular_niveis_categorias(categorias) == {1: 1, 2: 2, 3: 3}


def test_calcular_niveis_categorias_interrompe_ciclo():
    categorias = {
        1: SimpleNamespace(id=1, categoria_pai_id=2),
        2: SimpleNamespace(id=2, categoria_pai_id=1),
    }

    assert _calcular_niveis_categorias(categorias) == {1: 2, 2: 2}


def test_construir_arvore_categorias_preserva_ordem_recebida():
    categorias = [
        SimpleNamespace(
            id=1,
            nome="Racoes",
            descricao=None,
            icone="box",
            cor="#fff",
            ordem=1,
            categoria_pai_id=None,
        ),
        SimpleNamespace(
            id=2,
            nome="Gatos",
            descricao="Cat",
            icone=None,
            cor=None,
            ordem=2,
            categoria_pai_id=1,
        ),
        SimpleNamespace(
            id=3,
            nome="Higiene",
            descricao=None,
            icone=None,
            cor=None,
            ordem=3,
            categoria_pai_id=None,
        ),
    ]

    assert _construir_arvore_categorias(categorias) == [
        {
            "id": 1,
            "nome": "Racoes",
            "descricao": None,
            "icone": "box",
            "cor": "#fff",
            "ordem": 1,
            "subcategorias": [
                {
                    "id": 2,
                    "nome": "Gatos",
                    "descricao": "Cat",
                    "icone": None,
                    "cor": None,
                    "ordem": 2,
                    "subcategorias": [],
                }
            ],
        },
        {
            "id": 3,
            "nome": "Higiene",
            "descricao": None,
            "icone": None,
            "cor": None,
            "ordem": 3,
            "subcategorias": [],
        },
    ]
