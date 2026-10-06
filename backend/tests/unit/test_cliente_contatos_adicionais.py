"""Celulares de familiares devem resolver para o mesmo cadastro no PDV."""

import os
from uuid import uuid4

import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

os.environ.setdefault("DATABASE_URL", "sqlite:///./test.db")

from app.clientes.contatos import (
    salvar_contatos_adicionais,
    validar_contatos_adicionais,
)
from app.clientes.crud_routes import _aplicar_filtro_busca
from app.clientes.schemas import ClienteContatoInput, ClienteResponse
from app.db import Base
from app.models import Cliente, ClienteContato, FornecedorGrupo, Pet
import app.financeiro_models  # noqa: F401  # Registra os relacionamentos de Venda.
import app.produtos_models  # noqa: F401
from app.tenancy.context import tenant_context


@pytest.fixture
def cadastro_db():
    engine = create_engine("sqlite://")
    Base.metadata.create_all(
        engine,
        tables=[
            FornecedorGrupo.__table__,
            Cliente.__table__,
            Pet.__table__,
            ClienteContato.__table__,
        ],
    )
    db = sessionmaker(bind=engine)()
    tenant_id = uuid4()
    with tenant_context(tenant_id):
        yield db, tenant_id
    db.close()
    engine.dispose()


def _pessoa(db, tenant_id, nome, celular):
    pessoa = Cliente(
        tenant_id=tenant_id,
        user_id=1,
        nome=nome,
        celular=celular,
        tipo_cadastro="cliente",
        tipo_pessoa="PF",
    )
    db.add(pessoa)
    db.flush()
    return pessoa


def test_busca_celular_de_familiar_retorna_cadastro_principal(cadastro_db):
    db, tenant_id = cadastro_db
    principal = _pessoa(db, tenant_id, "Maria", "(18) 99999-1111")
    _pessoa(db, tenant_id, "Outra pessoa", "(18) 99999-3333")
    contato = ClienteContatoInput(numero="(18) 99999-2222", vinculo="mãe")
    validar_contatos_adicionais(
        db, tenant_id, principal.id, [contato], principal.celular, None
    )
    salvar_contatos_adicionais(db, principal, [contato])
    db.commit()

    encontrados = _aplicar_filtro_busca(db.query(Cliente), "18999992222").all()
    assert [pessoa.id for pessoa in encontrados] == [principal.id]
    assert encontrados[0].contatos_adicionais[0].vinculo == "mãe"
    resposta = ClienteResponse.model_validate(encontrados[0])
    assert resposta.contatos_adicionais[0].numero == "(18) 99999-2222"


def test_celular_adicional_nao_pode_apontar_para_duas_pessoas(cadastro_db):
    db, tenant_id = cadastro_db
    principal = _pessoa(db, tenant_id, "Maria", "18999991111")
    outra = _pessoa(db, tenant_id, "Joana", "18999993333")
    contato = ClienteContatoInput(numero="18999992222", vinculo="irmã")
    salvar_contatos_adicionais(db, principal, [contato])
    db.commit()

    with pytest.raises(HTTPException) as erro:
        validar_contatos_adicionais(
            db, tenant_id, outra.id, [contato], outra.celular, None
        )
    assert erro.value.status_code == 409


def test_edicao_substitui_celulares_sem_criar_outro_cadastro(cadastro_db):
    db, tenant_id = cadastro_db
    principal = _pessoa(db, tenant_id, "Maria", "18999991111")
    salvar_contatos_adicionais(
        db, principal, [ClienteContatoInput(numero="18999992222", vinculo="mãe")]
    )
    db.commit()
    salvar_contatos_adicionais(
        db, principal, [ClienteContatoInput(numero="18999994444", vinculo="filho")]
    )
    db.commit()

    assert not _aplicar_filtro_busca(db.query(Cliente), "18999992222").all()
    assert [
        p.id for p in _aplicar_filtro_busca(db.query(Cliente), "18999994444").all()
    ] == [principal.id]
    assert db.query(ClienteContato).count() == 1
