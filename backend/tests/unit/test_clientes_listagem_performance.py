"""A pagina de pessoas deve serializar relacionamentos sem consultas por pessoa."""

from types import SimpleNamespace
from uuid import uuid4

import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker

import app.db.base  # noqa: F401 - registra os relacionamentos antes de usar o ORM.
from app.clientes import crud_routes as clientes_routes
from app.clientes.crud_routes import list_clientes
from app.db import Base
from app.models import (
    AppAccessProfile,
    Cliente,
    ClienteContato,
    FornecedorGrupo,
    Pet,
    User,
)
from app.tenancy.context import tenant_context


@pytest.fixture
def pessoas_listagem_db(monkeypatch):
    # Helpers de parceria/grupo usam UUIDs como strings no PostgreSQL. Aqui
    # fixamos o escopo da loja, mantendo os UUIDs nativos exigidos pelo SQLite;
    # a query da rota e todos os filtros ORM de tenant continuam reais.
    monkeypatch.setattr(
        clientes_routes, "get_all_accessible_tenant_ids", lambda _db, tenant: [tenant]
    )
    monkeypatch.setattr(
        clientes_routes, "listar_empresas_do_grupo", lambda _db, tenant: [tenant]
    )
    engine = create_engine("sqlite://")
    Base.metadata.create_all(
        engine,
        tables=[
            User.__table__,
            FornecedorGrupo.__table__,
            Cliente.__table__,
            ClienteContato.__table__,
            Pet.__table__,
            AppAccessProfile.__table__,
        ],
    )
    tenant_id, outro_tenant_id = uuid4(), uuid4()
    grupos = [
        {"id": indice, "tenant_id": tenant_id, "nome": f"Grupo {indice:02d}"}
        for indice in range(1, 21)
    ]
    pessoas = [
        {
            "id": indice,
            "tenant_id": tenant_id,
            "user_id": 1,
            "codigo": str(indice),
            "nome": f"Pessoa {indice:02d}",
            "tipo_pessoa": "PF",
            "is_cliente": True,
            "fornecedor_grupo_id": indice,
        }
        for indice in range(1, 21)
    ]
    pessoas.append(
        {
            **pessoas[0],
            "id": 100,
            "tenant_id": outro_tenant_id,
            "nome": "Pessoa de outra loja",
            "fornecedor_grupo_id": None,
        }
    )
    pets = [
        {
            "id": indice,
            "tenant_id": tenant_id,
            "cliente_id": indice,
            "user_id": 1,
            "codigo": f"PET-{indice}",
            "nome": f"Pet {indice:02d}",
            "especie": "cao",
        }
        for indice in range(1, 21)
    ]
    contatos = [
        {
            "id": indice,
            "tenant_id": tenant_id,
            "cliente_id": indice,
            "numero": f"1899999{indice:04d}",
            "numero_digitos": f"1899999{indice:04d}",
            "vinculo": "Familiar",
        }
        for indice in range(1, 21)
    ]
    # Inclui filhos de outra loja ligados ao mesmo ID de pessoa para testar
    # o filtro real de tenant tambem nos carregamentos dos relacionamentos.
    for indice, cliente_id in [(100, 100), (101, 1)]:
        pets.append(
            {
                **pets[0],
                "id": indice,
                "tenant_id": outro_tenant_id,
                "cliente_id": cliente_id,
                "codigo": f"PET-OUTRO-{indice}",
                "nome": "Pet de outra loja",
            }
        )
        contatos.append(
            {
                **contatos[0],
                "id": indice,
                "tenant_id": outro_tenant_id,
                "cliente_id": cliente_id,
                "numero": f"1199999{indice:04d}",
                "numero_digitos": f"1199999{indice:04d}",
                "vinculo": "Contato de outra loja",
            }
        )
    with engine.begin() as connection:
        connection.execute(
            User.__table__.insert(),
            {
                "id": 1,
                "tenant_id": tenant_id,
                "username": "operador",
                "nome": "Operador",
            },
        )
        connection.execute(FornecedorGrupo.__table__.insert(), grupos)
        connection.execute(Cliente.__table__.insert(), pessoas)
        connection.execute(Pet.__table__.insert(), pets)
        connection.execute(ClienteContato.__table__.insert(), contatos)

    yield engine, tenant_id
    engine.dispose()


def _listar_com_contagem_de_consultas(engine, tenant_id, limite):
    consultas = []

    def contar_select(_connection, _cursor, statement, _parameters, _context, _many):
        if statement.lstrip().upper().startswith("SELECT"):
            consultas.append(statement)

    event.listen(engine, "before_cursor_execute", contar_select)
    try:
        # Sessoes novas impedem que o identity map esconda carregamentos lazy.
        with sessionmaker(bind=engine, autoflush=False)() as db:
            with tenant_context(tenant_id):
                # Autorizacao tem testes proprios; preservamos a rota e os
                # filtros ORM reais, isolando apenas o decorator de permissao.
                resposta = list_clientes.__wrapped__(
                    db=db,
                    user_and_tenant=(SimpleNamespace(id=1), tenant_id),
                    search="Pessoa",
                    skip=0,
                    limit=limite,
                    visao_dashboard=None,
                )
                dados = resposta.model_dump()
        return dados, len(consultas)
    finally:
        event.remove(engine, "before_cursor_execute", contar_select)


def test_listagem_serializa_pagina_sem_consultas_por_pessoa(pessoas_listagem_db):
    engine, tenant_id = pessoas_listagem_db
    pequena, consultas_pequena = _listar_com_contagem_de_consultas(engine, tenant_id, 1)
    pagina, consultas_pagina = _listar_com_contagem_de_consultas(engine, tenant_id, 20)

    assert pequena["total"] == pagina["total"] == 20
    assert len(pequena["items"]) == 1
    assert len(pagina["items"]) == 20
    assert pagina["skip"] == 0
    assert pagina["limit"] == 20
    assert consultas_pagina <= consultas_pequena + 1, (
        "Aumentar a pagina de 1 para 20 pessoas nao deve consultar cada pessoa: "
        f"{consultas_pequena} -> {consultas_pagina} SELECTs"
    )

    for indice, pessoa in enumerate(pagina["items"], start=1):
        assert pessoa["id"] == indice
        assert pessoa["nome"] == f"Pessoa {indice:02d}"
        assert pessoa["fornecedor_grupo_nome"] == f"Grupo {indice:02d}"
        assert pessoa["criado_por_nome"] == "Operador"
        assert [pet["nome"] for pet in pessoa["pets"]] == [f"Pet {indice:02d}"]
        assert [contato["numero"] for contato in pessoa["contatos_adicionais"]] == [
            f"1899999{indice:04d}"
        ]
        assert pessoa["contatos_adicionais"][0]["vinculo"] == "Familiar"
