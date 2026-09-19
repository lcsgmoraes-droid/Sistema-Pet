import uuid

import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.db import Base
from app.db import base as _base  # noqa: F401 - registra todo o metadata (evita
# InvalidRequestError ao resolver relationship() por nome de outras classes,
# mesmo criando so um subconjunto de tabelas abaixo).
from app.especie_raca_mestre_models import EspecieMestre, RacaMestre
from app.especie_raca_mestre_service import (
    desvincular_especie_mestre,
    desvincular_raca_mestre,
    sugerir_especie_mestre,
    sugerir_raca_mestre,
    vincular_especie_mestre,
    vincular_raca_mestre,
)
from app.grupo_comercial_models import GrupoComercial
from app.models_cadastros import Especie, Raca
from app.tenancy.context import clear_current_tenant, set_current_tenant


TENANT_A = uuid.UUID("11111111-1111-1111-1111-111111111111")
GRUPO_1 = 1
GRUPO_2 = 2
USUARIO_ID = 10


@pytest.fixture()
def db():
    engine = create_engine("sqlite://")
    Base.metadata.create_all(
        engine,
        tables=[
            GrupoComercial.__table__,
            EspecieMestre.__table__,
            RacaMestre.__table__,
            Especie.__table__,
            Raca.__table__,
        ],
    )
    session = Session(engine)
    set_current_tenant(TENANT_A)
    try:
        yield session
    finally:
        session.close()
        clear_current_tenant()


def _criar_especie_local(db, nome="Cão") -> Especie:
    especie = Especie(nome=nome, ativo=True)
    db.add(especie)
    db.commit()
    db.refresh(especie)
    return especie


def _criar_raca_local(db, especie_id: int, nome="Labrador") -> Raca:
    raca = Raca(nome=nome, especie_id=especie_id, ativo=True)
    db.add(raca)
    db.commit()
    db.refresh(raca)
    return raca


def _criar_especie_mestre(db, grupo_id=GRUPO_1, nome="Cão", ativo=True) -> EspecieMestre:
    mestre = EspecieMestre(
        grupo_id=grupo_id, nome=nome, ativo=ativo, criado_por_usuario_id=USUARIO_ID
    )
    db.add(mestre)
    db.commit()
    db.refresh(mestre)
    return mestre


# ---- sugerir_especie_mestre ----


def test_sugerir_especie_mestre_encontra_por_nome_case_insensitive(db):
    mestre = _criar_especie_mestre(db, nome="Cão")
    encontrado = sugerir_especie_mestre(db, GRUPO_1, "cão")
    assert encontrado is not None
    assert encontrado.id == mestre.id


def test_sugerir_especie_mestre_ignora_nome_vazio(db):
    _criar_especie_mestre(db, nome="Cão")
    assert sugerir_especie_mestre(db, GRUPO_1, "   ") is None
    assert sugerir_especie_mestre(db, GRUPO_1, "") is None


def test_sugerir_especie_mestre_ignora_mestre_inativo(db):
    _criar_especie_mestre(db, nome="Cão", ativo=False)
    assert sugerir_especie_mestre(db, GRUPO_1, "Cão") is None


def test_sugerir_especie_mestre_nao_atravessa_grupos(db):
    _criar_especie_mestre(db, grupo_id=GRUPO_1, nome="Cão")
    assert sugerir_especie_mestre(db, GRUPO_2, "Cão") is None


# ---- sugerir_raca_mestre ----


def test_sugerir_raca_mestre_encontra_por_nome_e_especie_mestre(db):
    especie_mestre = _criar_especie_mestre(db, nome="Cão")
    raca_mestre = RacaMestre(
        grupo_id=GRUPO_1,
        especie_mestre_id=especie_mestre.id,
        nome="Labrador",
        criado_por_usuario_id=USUARIO_ID,
    )
    db.add(raca_mestre)
    db.commit()

    encontrado = sugerir_raca_mestre(db, GRUPO_1, especie_mestre.id, "labrador")
    assert encontrado is not None
    assert encontrado.id == raca_mestre.id


def test_sugerir_raca_mestre_nao_atravessa_especie_mestre(db):
    especie_mestre_a = _criar_especie_mestre(db, nome="Cão")
    especie_mestre_b = EspecieMestre(
        grupo_id=GRUPO_1, nome="Gato", criado_por_usuario_id=USUARIO_ID
    )
    db.add(especie_mestre_b)
    db.commit()
    db.add(
        RacaMestre(
            grupo_id=GRUPO_1,
            especie_mestre_id=especie_mestre_a.id,
            nome="Siamês",
            criado_por_usuario_id=USUARIO_ID,
        )
    )
    db.commit()

    # "Siamês" existe como raça-mestre de Cão (dado de teste esdrúxulo de
    # propósito) - sugerir sob Gato não deve encontrar.
    assert sugerir_raca_mestre(db, GRUPO_1, especie_mestre_b.id, "Siamês") is None


# ---- vincular_especie_mestre ----


def test_vincular_especie_mestre_sem_id_promove_especie_local_a_mestre_novo(db):
    especie = _criar_especie_local(db, nome="Cão")

    mestre = vincular_especie_mestre(
        db,
        especie=especie,
        grupo_id=GRUPO_1,
        usuario_id=USUARIO_ID,
        especie_mestre_id=None,
    )

    assert mestre.nome == "Cão"
    assert mestre.grupo_id == GRUPO_1
    assert mestre.criado_por_usuario_id == USUARIO_ID
    assert especie.especie_mestre_id == mestre.id
    assert db.query(EspecieMestre).count() == 1


def test_vincular_especie_mestre_com_id_liga_a_mestre_existente_sem_duplicar(db):
    mestre_existente = _criar_especie_mestre(db, nome="Cão")
    especie = _criar_especie_local(db, nome="Cachorro")  # nome local diferente

    mestre = vincular_especie_mestre(
        db,
        especie=especie,
        grupo_id=GRUPO_1,
        usuario_id=USUARIO_ID,
        especie_mestre_id=mestre_existente.id,
    )

    assert mestre.id == mestre_existente.id
    assert especie.especie_mestre_id == mestre_existente.id
    assert db.query(EspecieMestre).count() == 1  # nao criou um segundo mestre


def test_vincular_especie_mestre_404_quando_id_e_de_outro_grupo(db):
    mestre_outro_grupo = _criar_especie_mestre(db, grupo_id=GRUPO_2, nome="Cão")
    especie = _criar_especie_local(db, nome="Cão")

    with pytest.raises(HTTPException) as excinfo:
        vincular_especie_mestre(
            db,
            especie=especie,
            grupo_id=GRUPO_1,
            usuario_id=USUARIO_ID,
            especie_mestre_id=mestre_outro_grupo.id,
        )
    assert excinfo.value.status_code == 404


def test_vincular_especie_mestre_404_quando_mestre_esta_inativo(db):
    mestre_inativo = _criar_especie_mestre(db, nome="Cão", ativo=False)
    especie = _criar_especie_local(db, nome="Cão")

    with pytest.raises(HTTPException) as excinfo:
        vincular_especie_mestre(
            db,
            especie=especie,
            grupo_id=GRUPO_1,
            usuario_id=USUARIO_ID,
            especie_mestre_id=mestre_inativo.id,
        )
    assert excinfo.value.status_code == 404


# ---- vincular_raca_mestre ----


def test_vincular_raca_mestre_sem_id_promove_raca_local_a_mestre_novo(db):
    especie_mestre = _criar_especie_mestre(db, nome="Cão")
    especie = _criar_especie_local(db, nome="Cão")
    raca = _criar_raca_local(db, especie.id, nome="Labrador")

    mestre = vincular_raca_mestre(
        db,
        raca=raca,
        grupo_id=GRUPO_1,
        especie_mestre_id=especie_mestre.id,
        usuario_id=USUARIO_ID,
        raca_mestre_id=None,
    )

    assert mestre.nome == "Labrador"
    assert mestre.especie_mestre_id == especie_mestre.id
    assert raca.raca_mestre_id == mestre.id


def test_vincular_raca_mestre_com_id_liga_a_mestre_existente(db):
    especie_mestre = _criar_especie_mestre(db, nome="Cão")
    raca_mestre_existente = RacaMestre(
        grupo_id=GRUPO_1,
        especie_mestre_id=especie_mestre.id,
        nome="Labrador",
        criado_por_usuario_id=USUARIO_ID,
    )
    db.add(raca_mestre_existente)
    db.commit()
    especie = _criar_especie_local(db, nome="Cão")
    raca = _criar_raca_local(db, especie.id, nome="Labrador Retriever")

    mestre = vincular_raca_mestre(
        db,
        raca=raca,
        grupo_id=GRUPO_1,
        especie_mestre_id=especie_mestre.id,
        usuario_id=USUARIO_ID,
        raca_mestre_id=raca_mestre_existente.id,
    )

    assert mestre.id == raca_mestre_existente.id
    assert raca.raca_mestre_id == raca_mestre_existente.id
    assert db.query(RacaMestre).count() == 1


def test_vincular_raca_mestre_404_quando_id_e_de_outro_grupo(db):
    especie_mestre_grupo_2 = _criar_especie_mestre(db, grupo_id=GRUPO_2, nome="Cão")
    raca_mestre_outro_grupo = RacaMestre(
        grupo_id=GRUPO_2,
        especie_mestre_id=especie_mestre_grupo_2.id,
        nome="Labrador",
        criado_por_usuario_id=USUARIO_ID,
    )
    db.add(raca_mestre_outro_grupo)
    db.commit()
    especie = _criar_especie_local(db, nome="Cão")
    raca = _criar_raca_local(db, especie.id, nome="Labrador")

    with pytest.raises(HTTPException) as excinfo:
        vincular_raca_mestre(
            db,
            raca=raca,
            grupo_id=GRUPO_1,
            especie_mestre_id=especie_mestre_grupo_2.id,
            usuario_id=USUARIO_ID,
            raca_mestre_id=raca_mestre_outro_grupo.id,
        )
    assert excinfo.value.status_code == 404


# ---- desvincular ----


def test_desvincular_especie_mestre_remove_vinculo_sem_apagar_mestre(db):
    especie = _criar_especie_local(db, nome="Cão")
    mestre = vincular_especie_mestre(
        db,
        especie=especie,
        grupo_id=GRUPO_1,
        usuario_id=USUARIO_ID,
        especie_mestre_id=None,
    )
    assert especie.especie_mestre_id == mestre.id

    desvincular_especie_mestre(db, especie=especie)

    assert especie.especie_mestre_id is None
    mestre_ainda_existe = db.query(EspecieMestre).filter_by(id=mestre.id).one()
    assert mestre_ainda_existe.ativo is True


def test_desvincular_raca_mestre_remove_vinculo_sem_apagar_mestre(db):
    especie_mestre = _criar_especie_mestre(db, nome="Cão")
    especie = _criar_especie_local(db, nome="Cão")
    raca = _criar_raca_local(db, especie.id, nome="Labrador")
    mestre = vincular_raca_mestre(
        db,
        raca=raca,
        grupo_id=GRUPO_1,
        especie_mestre_id=especie_mestre.id,
        usuario_id=USUARIO_ID,
        raca_mestre_id=None,
    )
    assert raca.raca_mestre_id == mestre.id

    desvincular_raca_mestre(db, raca=raca)

    assert raca.raca_mestre_id is None
    mestre_ainda_existe = db.query(RacaMestre).filter_by(id=mestre.id).one()
    assert mestre_ainda_existe.ativo is True
