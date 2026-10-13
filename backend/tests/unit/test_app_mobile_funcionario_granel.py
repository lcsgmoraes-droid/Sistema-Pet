import os

from fastapi import HTTPException
import pytest
from sqlalchemy import select
from sqlalchemy.dialects import postgresql


os.environ.setdefault("DATABASE_URL", "sqlite:///./test.db")

from app.produtos_models import Produto
from app.routes.app_mobile_funcionario_pdv.granel import (
    _filtrar_produtos_com_vinculo_granel,
    buscar_produto_granel_funcionario_barcode,
)


def _sql_busca_vinculada(etapa: str, produto_origem_id: int | None = None) -> str:
    query = _filtrar_produtos_com_vinculo_granel(
        select(Produto.__table__),
        "180d9cbf-5dcb-4676-bf11-dcbd91ed444b",
        etapa,
        produto_origem_id,
    )
    return str(query.compile(dialect=postgresql.dialect()))


def test_busca_de_pai_usa_exists_sem_distinct_sobre_colunas_json():
    sql = _sql_busca_vinculada("origem")

    assert "EXISTS" in sql
    assert "produto_granel_vinculos.produto_origem_id = produtos.id" in sql
    assert "SELECT DISTINCT" not in sql


def test_busca_de_granel_limita_vinculo_ao_produto_pai():
    sql = _sql_busca_vinculada("granel", produto_origem_id=227)

    assert "EXISTS" in sql
    assert "produto_granel_vinculos.produto_granel_id = produtos.id" in sql
    assert "produto_granel_vinculos.produto_origem_id" in sql
    assert "SELECT DISTINCT" not in sql


def test_bipagem_de_granel_monta_filtro_sql_valido(monkeypatch):
    from app.routes.app_mobile_funcionario_pdv import granel

    class QueryFake:
        def __init__(self):
            self.statement = select(Produto.__table__)

        def filter(self, *conditions):
            self.statement = self.statement.filter(*conditions)
            return self

        def first(self):
            return None

    class SessionFake:
        def __init__(self):
            self.query_fake = QueryFake()

        def query(self, model):
            assert model is Produto
            return self.query_fake

    monkeypatch.setattr(
        granel,
        "_get_funcionario_operacional_or_403",
        lambda db, user: (None, "180d9cbf-5dcb-4676-bf11-dcbd91ed444b"),
    )
    db = SessionFake()
    with pytest.raises(HTTPException) as exc:
        buscar_produto_granel_funcionario_barcode(
            "7891234567890", etapa="origem", current_user=object(), db=db
        )

    assert exc.value.status_code == 404
    sql = str(db.query_fake.statement.compile(dialect=postgresql.dialect()))
    assert " OR " in sql
    assert "produtos.codigo_barras" in sql
