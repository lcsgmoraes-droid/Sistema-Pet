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
from app.models_cadastros import Cliente, Pet
from app.pet_mestre_models import PetMestre
from app.pet_mestre_service import (
    desvincular_pet_mestre,
    sugerir_pet_mestre,
    vincular_pet_mestre,
)
from app.tenancy.context import clear_current_tenant, set_current_tenant
from app.veterinario_models import PerfilComportamental


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
            PetMestre.__table__,
            Pet.__table__,
            Cliente.__table__,
            User.__table__,
            PerfilComportamental.__table__,
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


@pytest.fixture()
def cliente(db, usuario) -> Cliente:
    cliente = Cliente(user_id=usuario.id, nome="Tutor Teste")
    db.add(cliente)
    db.commit()
    db.refresh(cliente)
    return cliente


def _criar_pet_local(
    db, usuario_id, cliente_id, nome="Rex", especie="cão", microchip=None, codigo="PET-1"
):
    pet = Pet(
        codigo=codigo,
        nome=nome,
        especie=especie,
        cliente_id=cliente_id,
        user_id=usuario_id,
        microchip=microchip,
    )
    db.add(pet)
    db.commit()
    db.refresh(pet)
    return pet


def _criar_pet_mestre(
    db, grupo_id=GRUPO_1, nome="Rex", especie="cão", microchip=None, ativo=True
):
    mestre = PetMestre(
        grupo_id=grupo_id,
        nome=nome,
        especie=especie,
        microchip=microchip,
        ativo=ativo,
        criado_por_usuario_id=USUARIO_ID_FALLBACK,
    )
    db.add(mestre)
    db.commit()
    db.refresh(mestre)
    return mestre


# ---- sugerir_pet_mestre ----


def test_sugerir_pet_mestre_prioriza_microchip_sobre_nome(db):
    por_microchip = _criar_pet_mestre(db, nome="Rex", microchip="ABC123")
    _criar_pet_mestre(db, nome="Rex Diferente")

    encontrado = sugerir_pet_mestre(db, GRUPO_1, microchip="ABC123", nome="Rex Diferente")
    assert encontrado.id == por_microchip.id


def test_sugerir_pet_mestre_cai_para_nome_quando_microchip_nao_bate(db):
    por_nome = _criar_pet_mestre(db, nome="Rex", microchip=None)

    encontrado = sugerir_pet_mestre(db, GRUPO_1, microchip="XYZ999", nome="Rex")
    assert encontrado.id == por_nome.id


def test_sugerir_pet_mestre_ignora_inativo(db):
    _criar_pet_mestre(db, nome="Rex", ativo=False)
    assert sugerir_pet_mestre(db, GRUPO_1, nome="Rex") is None


def test_sugerir_pet_mestre_sem_nome_e_sem_microchip_retorna_none(db):
    _criar_pet_mestre(db, nome="Rex")
    assert sugerir_pet_mestre(db, GRUPO_1, microchip=None, nome=None) is None


# ---- vincular_pet_mestre ----


def test_vincular_pet_mestre_sem_id_promove_pet_local_copiando_campos(db, usuario, cliente):
    pet = _criar_pet_local(db, usuario.id, cliente.id, nome="Rex", microchip="ABC123")

    mestre = vincular_pet_mestre(
        db, pet=pet, grupo_id=GRUPO_1, usuario_id=usuario.id, pet_mestre_id=None
    )

    assert mestre.nome == "Rex"
    assert mestre.especie == "cão"
    assert mestre.microchip == "ABC123"
    assert mestre.criado_por_usuario_id == usuario.id
    assert pet.pet_mestre_id == mestre.id


def test_vincular_pet_mestre_copia_perfil_comportamental_quando_existe(db, usuario, cliente):
    pet = _criar_pet_local(db, usuario.id, cliente.id, nome="Rex")
    perfil = PerfilComportamental(
        pet_id=pet.id,
        user_id=usuario.id,
        temperamento="calmo",
        reacao_animais="amigavel",
        medo_secador="nao",
    )
    db.add(perfil)
    db.commit()

    mestre = vincular_pet_mestre(
        db, pet=pet, grupo_id=GRUPO_1, usuario_id=usuario.id, pet_mestre_id=None
    )

    assert mestre.temperamento == "calmo"
    assert mestre.reacao_animais == "amigavel"
    assert mestre.medo_secador == "nao"


def test_vincular_pet_mestre_sem_perfil_comportamental_nao_quebra(db, usuario, cliente):
    pet = _criar_pet_local(db, usuario.id, cliente.id, nome="Rex")

    mestre = vincular_pet_mestre(
        db, pet=pet, grupo_id=GRUPO_1, usuario_id=usuario.id, pet_mestre_id=None
    )

    assert mestre.temperamento is None


def test_vincular_pet_mestre_com_id_liga_a_existente_sem_duplicar(db, usuario, cliente):
    mestre_existente = _criar_pet_mestre(db, nome="Rex")
    pet = _criar_pet_local(db, usuario.id, cliente.id, nome="Rex Nome Local Diferente")

    mestre = vincular_pet_mestre(
        db, pet=pet, grupo_id=GRUPO_1, usuario_id=usuario.id, pet_mestre_id=mestre_existente.id
    )

    assert mestre.id == mestre_existente.id
    assert pet.pet_mestre_id == mestre_existente.id
    assert db.query(PetMestre).count() == 1


def test_vincular_pet_mestre_404_quando_id_e_de_outro_grupo(db, usuario, cliente):
    mestre_outro_grupo = _criar_pet_mestre(db, grupo_id=GRUPO_2)
    pet = _criar_pet_local(db, usuario.id, cliente.id)

    with pytest.raises(HTTPException) as excinfo:
        vincular_pet_mestre(
            db,
            pet=pet,
            grupo_id=GRUPO_1,
            usuario_id=usuario.id,
            pet_mestre_id=mestre_outro_grupo.id,
        )
    assert excinfo.value.status_code == 404


def test_vincular_pet_mestre_404_quando_mestre_inativo(db, usuario, cliente):
    mestre_inativo = _criar_pet_mestre(db, ativo=False)
    pet = _criar_pet_local(db, usuario.id, cliente.id)

    with pytest.raises(HTTPException) as excinfo:
        vincular_pet_mestre(
            db,
            pet=pet,
            grupo_id=GRUPO_1,
            usuario_id=usuario.id,
            pet_mestre_id=mestre_inativo.id,
        )
    assert excinfo.value.status_code == 404


def test_desvincular_pet_mestre_remove_vinculo_sem_apagar_mestre(db, usuario, cliente):
    pet = _criar_pet_local(db, usuario.id, cliente.id)
    mestre = vincular_pet_mestre(
        db, pet=pet, grupo_id=GRUPO_1, usuario_id=usuario.id, pet_mestre_id=None
    )

    desvincular_pet_mestre(db, pet=pet)

    assert pet.pet_mestre_id is None
    ainda_existe = db.query(PetMestre).filter_by(id=mestre.id).one()
    assert ainda_existe.ativo is True
