"""O vendedor usa os perfis atuais de Pessoa, sempre dentro da loja ativa."""

from uuid import UUID

import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.db import Base
from app.db import base as _base  # noqa: F401 - registra os modelos relacionados
from app.models import Cliente
from app.tenancy.context import clear_tenant_context, set_tenant_context
from app.vendas.crud_routes import validar_vendedor_funcionario


LOJA_ATUAL = UUID("11111111-1111-1111-1111-111111111111")
OUTRA_LOJA = UUID("22222222-2222-2222-2222-222222222222")


@pytest.fixture
def db():
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine, tables=[Cliente.__table__])
    with Session(engine) as session:
        set_tenant_context(LOJA_ATUAL)
        try:
            yield session
        finally:
            clear_tenant_context()
    engine.dispose()


def _pessoa(db, **campos):
    # Core permite fixar IDs sem passar pelos guards de criacao da aplicacao.
    dados = {
        "id": 1,
        "user_id": 1,
        "tenant_id": LOJA_ATUAL,
        "nome": "Pessoa QA",
        "ativo": True,
        "is_cliente": False,
        "is_fornecedor": False,
        "is_veterinario": False,
        "is_funcionario": False,
        "parceiro_ativo": False,
        **campos,
    }
    db.execute(Cliente.__table__.insert(), dados)
    db.commit()


@pytest.mark.parametrize(
    "outros_perfis", [{}, {"is_cliente": True, "is_fornecedor": True}]
)
def test_aceita_funcionario_ativo_inclusive_com_outros_perfis(db, outros_perfis):
    _pessoa(db, is_funcionario=True, **outros_perfis)

    validar_vendedor_funcionario(db, LOJA_ATUAL, 1)


def test_preserva_parceiro_ativo_como_vendedor(db):
    _pessoa(db, is_cliente=True, parceiro_ativo=True)

    validar_vendedor_funcionario(db, LOJA_ATUAL, 1)


@pytest.mark.parametrize(
    "campos",
    [
        {"is_cliente": True},
        {"is_funcionario": True, "ativo": False},
        {"is_funcionario": True, "tenant_id": OUTRA_LOJA},
        {"parceiro_ativo": True, "ativo": False},
    ],
)
def test_rejeita_pessoa_sem_perfil_ativo_ou_de_outra_loja(db, campos):
    _pessoa(db, **campos)

    with pytest.raises(HTTPException) as exc:
        validar_vendedor_funcionario(db, LOJA_ATUAL, 1)

    assert exc.value.status_code == 400
    assert exc.value.detail == "Vendedor não encontrado nesta empresa"


def test_rejeita_vendedor_inexistente(db):
    with pytest.raises(HTTPException) as exc:
        validar_vendedor_funcionario(db, LOJA_ATUAL, 999)

    assert exc.value.status_code == 400


def test_sem_vendedor_nao_exige_consulta():
    validar_vendedor_funcionario(None, LOJA_ATUAL, None)
