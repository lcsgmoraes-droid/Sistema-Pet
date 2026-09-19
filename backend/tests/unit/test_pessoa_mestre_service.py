import uuid

import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.db import Base
from app.db import base as _base  # noqa: F401 - registra todo o metadata (evita
# InvalidRequestError ao resolver relationship() por nome de outras classes,
# mesmo criando so um subconjunto de tabelas abaixo).
from app.grupo_comercial_models import GrupoComercial
from app.models import User
from app.models_cadastros import Cliente
from app.pessoa_mestre_models import PessoaMestre
from app.pessoa_mestre_service import (
    desvincular_pessoa_mestre,
    sugerir_pessoa_mestre,
    vincular_pessoa_mestre,
)
from app.tenancy.context import clear_current_tenant, set_current_tenant


TENANT_A = uuid.UUID("11111111-1111-1111-1111-111111111111")
GRUPO_1 = 1
GRUPO_2 = 2
USUARIO_ID_FALLBACK = 999


@pytest.fixture()
def db():
    engine = create_engine("sqlite://")
    Base.metadata.create_all(
        engine,
        tables=[
            GrupoComercial.__table__,
            PessoaMestre.__table__,
            Cliente.__table__,
            User.__table__,
        ],
    )
    session = Session(engine)
    set_current_tenant(TENANT_A)
    try:
        yield session
    finally:
        session.close()
        clear_current_tenant()


@pytest.fixture()
def usuario(db) -> User:
    user = User(
        email="operador@example.com",
        hashed_password="hash",
        nome="Operador",
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def _criar_cliente_local(db, usuario_id, nome="Maria Tutora", cpf=None, cnpj=None):
    cliente = Cliente(user_id=usuario_id, nome=nome, cpf=cpf, cnpj=cnpj)
    db.add(cliente)
    db.commit()
    db.refresh(cliente)
    return cliente


def _criar_pessoa_mestre(
    db, grupo_id=GRUPO_1, nome="Maria Tutora", cpf=None, cnpj=None, ativo=True
):
    mestre = PessoaMestre(
        grupo_id=grupo_id,
        nome=nome,
        cpf=cpf,
        cnpj=cnpj,
        ativo=ativo,
        criado_por_usuario_id=USUARIO_ID_FALLBACK,
    )
    db.add(mestre)
    db.commit()
    db.refresh(mestre)
    return mestre


# ---- sugerir_pessoa_mestre ----


def test_sugerir_pessoa_mestre_encontra_por_cpf_normalizado(db):
    mestre = _criar_pessoa_mestre(db, cpf="12345678900")
    encontrado = sugerir_pessoa_mestre(db, GRUPO_1, cpf="123.456.789-00")
    assert encontrado.id == mestre.id


def test_sugerir_pessoa_mestre_cai_para_cnpj_quando_cpf_nao_informado(db):
    mestre = _criar_pessoa_mestre(db, nome="Fornecedor LTDA", cnpj="12345678000199")
    encontrado = sugerir_pessoa_mestre(db, GRUPO_1, cnpj="12.345.678/0001-99")
    assert encontrado.id == mestre.id


def test_sugerir_pessoa_mestre_nunca_busca_por_nome_sozinho(db):
    # documento e sempre exigido - nome sozinho e comum demais pra ser
    # confiavel em dado pessoal (ver docstring do modulo).
    _criar_pessoa_mestre(db, nome="Maria Tutora", cpf="12345678900")
    assert sugerir_pessoa_mestre(db, GRUPO_1, cpf=None, cnpj=None) is None


def test_sugerir_pessoa_mestre_ignora_inativo(db):
    _criar_pessoa_mestre(db, cpf="12345678900", ativo=False)
    assert sugerir_pessoa_mestre(db, GRUPO_1, cpf="12345678900") is None


def test_sugerir_pessoa_mestre_nao_atravessa_grupos(db):
    _criar_pessoa_mestre(db, grupo_id=GRUPO_1, cpf="12345678900")
    assert sugerir_pessoa_mestre(db, GRUPO_2, cpf="12345678900") is None


# ---- vincular_pessoa_mestre ----


def test_vincular_pessoa_mestre_sem_id_promove_cliente_local_copiando_e_normalizando_documento(
    db, usuario
):
    cliente = _criar_cliente_local(db, usuario.id, nome="Maria Tutora", cpf="123.456.789-00")

    mestre = vincular_pessoa_mestre(
        db, cliente=cliente, grupo_id=GRUPO_1, usuario_id=usuario.id, pessoa_mestre_id=None
    )

    assert mestre.nome == "Maria Tutora"
    assert mestre.cpf == "12345678900"  # normalizado, sem pontuacao
    assert mestre.criado_por_usuario_id == usuario.id
    assert cliente.pessoa_mestre_id == mestre.id


def test_vincular_pessoa_mestre_com_id_liga_a_existente_sem_duplicar(db, usuario):
    mestre_existente = _criar_pessoa_mestre(db, cpf="12345678900")
    cliente = _criar_cliente_local(db, usuario.id, nome="Nome Local Diferente")

    mestre = vincular_pessoa_mestre(
        db,
        cliente=cliente,
        grupo_id=GRUPO_1,
        usuario_id=usuario.id,
        pessoa_mestre_id=mestre_existente.id,
    )

    assert mestre.id == mestre_existente.id
    assert cliente.pessoa_mestre_id == mestre_existente.id
    assert db.query(PessoaMestre).count() == 1


def test_vincular_pessoa_mestre_404_quando_id_e_de_outro_grupo(db, usuario):
    mestre_outro_grupo = _criar_pessoa_mestre(db, grupo_id=GRUPO_2, cpf="12345678900")
    cliente = _criar_cliente_local(db, usuario.id)

    with pytest.raises(HTTPException) as excinfo:
        vincular_pessoa_mestre(
            db,
            cliente=cliente,
            grupo_id=GRUPO_1,
            usuario_id=usuario.id,
            pessoa_mestre_id=mestre_outro_grupo.id,
        )
    assert excinfo.value.status_code == 404


def test_vincular_pessoa_mestre_404_quando_mestre_inativo(db, usuario):
    mestre_inativo = _criar_pessoa_mestre(db, cpf="12345678900", ativo=False)
    cliente = _criar_cliente_local(db, usuario.id)

    with pytest.raises(HTTPException) as excinfo:
        vincular_pessoa_mestre(
            db,
            cliente=cliente,
            grupo_id=GRUPO_1,
            usuario_id=usuario.id,
            pessoa_mestre_id=mestre_inativo.id,
        )
    assert excinfo.value.status_code == 404


def test_desvincular_pessoa_mestre_remove_vinculo_sem_apagar_mestre(db, usuario):
    cliente = _criar_cliente_local(db, usuario.id, cpf="12345678900")
    mestre = vincular_pessoa_mestre(
        db, cliente=cliente, grupo_id=GRUPO_1, usuario_id=usuario.id, pessoa_mestre_id=None
    )

    desvincular_pessoa_mestre(db, cliente=cliente)

    assert cliente.pessoa_mestre_id is None
    ainda_existe = db.query(PessoaMestre).filter_by(id=mestre.id).one()
    assert ainda_existe.ativo is True
