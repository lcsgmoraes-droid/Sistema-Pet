from uuid import uuid4

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

import app.db.base  # noqa: F401
from app.clientes.search import _aplicar_filtro_busca, _ordenar_query_listagem
from app.db import Base
from app.grupo_comercial_models import GrupoComercial, GrupoComercialMembro
from app.models import Cliente, ClienteContato
from app.tenancy.context import tenant_context
from app.veterinario_models import VetPartnerLink


@pytest.fixture
def base_busca():
    engine = create_engine("sqlite://")
    Base.metadata.create_all(
        engine,
        tables=[
            modelo.__table__
            for modelo in (
                Cliente,
                ClienteContato,
                GrupoComercial,
                GrupoComercialMembro,
                VetPartnerLink,
            )
        ],
    )
    tenant = uuid4()
    with tenant_context(tenant), Session(engine) as db:
        for indice, codigo, nome in [
            (1, "0001", "Ana AB123"),
            (2, "AB1234", "Zulu"),
            (3, "AB1239", "Zeca"),
            (4, "AB123", "Pessoa exata"),
            (5, "0005", "Joao da Silva"),
            (6, "0006", "Joao Pereira"),
            (987654, "0007", "Outra pessoa"),
        ]:
            db.execute(
                Cliente.__table__.insert().values(
                    id=indice,
                    tenant_id=tenant,
                    user_id=1,
                    codigo=codigo,
                    nome=nome,
                    is_cliente=True,
                    ativo=True,
                )
            )
        db.commit()
        yield db, tenant
    engine.dispose()


def resultado(base_busca, termo):
    db, tenant = base_busca
    query = db.query(Cliente.id, Cliente.codigo).filter(Cliente.tenant_id == tenant)
    return _ordenar_query_listagem(_aplicar_filtro_busca(query, termo), termo).all()


def test_codigo_alfanumerico_exato_e_prefixos_antes_de_nome_parcial(base_busca):
    encontrados = resultado(base_busca, "AB123")
    assert [row.codigo for row in encontrados] == ["AB123", "AB1239", "AB1234", "0001"]


def test_palavras_em_ordem_diferente_sao_combinadas_sem_incluir_nome_incompleto(
    base_busca,
):
    assert [row.codigo for row in resultado(base_busca, "Silva Joao")] == ["0005"]


def test_busca_por_codigo_nao_retorna_id_interno_como_se_fosse_publico(base_busca):
    assert resultado(base_busca, "987654") == []
