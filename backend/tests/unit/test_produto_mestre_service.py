import uuid

import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.catalogo_mestre_models import CatalogoMestreProduto
from app.db import Base
from app.db import base as _base  # noqa: F401 - registra todo o metadata (evita
# InvalidRequestError ao resolver relationship() por nome de outras classes,
# mesmo criando so um subconjunto de tabelas abaixo).
from app.grupo_comercial_models import GrupoComercial
from app.models import User
from app.produto_mestre_models import (
    CategoriaMestre,
    DepartamentoMestre,
    MarcaMestre,
    ProdutoMestre,
)
from app.produto_mestre_service import (
    desvincular_produto_mestre,
    sugerir_categoria_mestre,
    sugerir_departamento_mestre,
    sugerir_marca_mestre,
    sugerir_produto_mestre,
    vincular_categoria_mestre,
    vincular_departamento_mestre,
    vincular_marca_mestre,
    vincular_produto_mestre,
)
from app.produtos_catalogo_models import Categoria, Departamento, Marca, Produto
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
            CategoriaMestre.__table__,
            MarcaMestre.__table__,
            DepartamentoMestre.__table__,
            ProdutoMestre.__table__,
            Categoria.__table__,
            Marca.__table__,
            Departamento.__table__,
            Produto.__table__,
            User.__table__,
            CatalogoMestreProduto.__table__,
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


def _criar_produto_local(db, usuario_id, nome="Ração Premium 10kg", gtin=None, codigo="SKU-1"):
    produto = Produto(codigo=codigo, nome=nome, user_id=usuario_id, gtin_ean=gtin)
    db.add(produto)
    db.commit()
    db.refresh(produto)
    return produto


def _criar_produto_mestre(db, grupo_id=GRUPO_1, nome="Ração Premium 10kg", gtin=None, ativo=True):
    mestre = ProdutoMestre(
        grupo_id=grupo_id,
        nome=nome,
        gtin_ean=gtin,
        ativo=ativo,
        criado_por_usuario_id=USUARIO_ID_FALLBACK,
    )
    db.add(mestre)
    db.commit()
    db.refresh(mestre)
    return mestre


def _criar_categoria_local(db, usuario_id, nome="Alimentos"):
    categoria = Categoria(nome=nome, user_id=usuario_id)
    db.add(categoria)
    db.commit()
    db.refresh(categoria)
    return categoria


def _criar_marca_local(db, usuario_id, nome="Premier"):
    marca = Marca(nome=nome, user_id=usuario_id)
    db.add(marca)
    db.commit()
    db.refresh(marca)
    return marca


def _criar_departamento_local(db, usuario_id, nome="Pet Shop"):
    departamento = Departamento(nome=nome, user_id=usuario_id)
    db.add(departamento)
    db.commit()
    db.refresh(departamento)
    return departamento


# ---- sugerir_produto_mestre ----


def test_sugerir_produto_mestre_prioriza_gtin_sobre_nome(db):
    por_gtin = _criar_produto_mestre(db, nome="Ração X", gtin="7890000000001")
    _criar_produto_mestre(db, nome="Ração Diferente")

    encontrado = sugerir_produto_mestre(
        db, GRUPO_1, nome="Ração Diferente", gtin="7890000000001"
    )
    assert encontrado.id == por_gtin.id


def test_sugerir_produto_mestre_cai_para_nome_quando_gtin_nao_bate(db):
    por_nome = _criar_produto_mestre(db, nome="Ração X", gtin=None)

    encontrado = sugerir_produto_mestre(db, GRUPO_1, nome="Ração X", gtin="0000000000000")
    assert encontrado.id == por_nome.id


def test_sugerir_produto_mestre_ignora_inativo(db):
    _criar_produto_mestre(db, nome="Ração X", ativo=False)
    assert sugerir_produto_mestre(db, GRUPO_1, nome="Ração X") is None


def test_sugerir_produto_mestre_sem_nome_e_sem_gtin_retorna_none(db):
    _criar_produto_mestre(db, nome="Ração X")
    assert sugerir_produto_mestre(db, GRUPO_1, nome=None, gtin=None) is None


# ---- vincular_produto_mestre ----


def test_vincular_produto_mestre_sem_id_promove_produto_local_copiando_campos(db, usuario):
    produto = _criar_produto_local(db, usuario.id, nome="Ração Premium 10kg", gtin="123")

    mestre = vincular_produto_mestre(
        db, produto=produto, grupo_id=GRUPO_1, usuario_id=usuario.id, produto_mestre_id=None
    )

    assert mestre.nome == "Ração Premium 10kg"
    assert mestre.gtin_ean == "123"
    assert mestre.criado_por_usuario_id == usuario.id
    assert produto.produto_mestre_id == mestre.id


def test_vincular_produto_mestre_com_id_liga_a_existente_sem_duplicar(db, usuario):
    mestre_existente = _criar_produto_mestre(db, nome="Ração Premium 10kg")
    produto = _criar_produto_local(db, usuario.id, nome="Nome Local Diferente")

    mestre = vincular_produto_mestre(
        db,
        produto=produto,
        grupo_id=GRUPO_1,
        usuario_id=usuario.id,
        produto_mestre_id=mestre_existente.id,
    )

    assert mestre.id == mestre_existente.id
    assert produto.produto_mestre_id == mestre_existente.id
    assert db.query(ProdutoMestre).count() == 1


def test_vincular_produto_mestre_404_quando_id_e_de_outro_grupo(db, usuario):
    mestre_outro_grupo = _criar_produto_mestre(db, grupo_id=GRUPO_2)
    produto = _criar_produto_local(db, usuario.id)

    with pytest.raises(HTTPException) as excinfo:
        vincular_produto_mestre(
            db,
            produto=produto,
            grupo_id=GRUPO_1,
            usuario_id=usuario.id,
            produto_mestre_id=mestre_outro_grupo.id,
        )
    assert excinfo.value.status_code == 404


def test_vincular_produto_mestre_404_quando_mestre_inativo(db, usuario):
    mestre_inativo = _criar_produto_mestre(db, ativo=False)
    produto = _criar_produto_local(db, usuario.id)

    with pytest.raises(HTTPException) as excinfo:
        vincular_produto_mestre(
            db,
            produto=produto,
            grupo_id=GRUPO_1,
            usuario_id=usuario.id,
            produto_mestre_id=mestre_inativo.id,
        )
    assert excinfo.value.status_code == 404


def test_desvincular_produto_mestre_remove_vinculo_sem_apagar_mestre(db, usuario):
    produto = _criar_produto_local(db, usuario.id)
    mestre = vincular_produto_mestre(
        db, produto=produto, grupo_id=GRUPO_1, usuario_id=usuario.id, produto_mestre_id=None
    )

    desvincular_produto_mestre(db, produto=produto)

    assert produto.produto_mestre_id is None
    ainda_existe = db.query(ProdutoMestre).filter_by(id=mestre.id).one()
    assert ainda_existe.ativo is True


# ---- categoria/marca/departamento mestre (mesmo helper generico) ----


def test_sugerir_categoria_mestre_delega_para_taxonomia_generica(db):
    mestre = CategoriaMestre(
        grupo_id=GRUPO_1, nome="Alimentos", criado_por_usuario_id=USUARIO_ID_FALLBACK
    )
    db.add(mestre)
    db.commit()
    encontrado = sugerir_categoria_mestre(db, GRUPO_1, "alimentos")
    assert encontrado.id == mestre.id


def test_sugerir_marca_mestre_delega_para_taxonomia_generica(db):
    mestre = MarcaMestre(
        grupo_id=GRUPO_1, nome="Premier", criado_por_usuario_id=USUARIO_ID_FALLBACK
    )
    db.add(mestre)
    db.commit()
    encontrado = sugerir_marca_mestre(db, GRUPO_1, "premier")
    assert encontrado.id == mestre.id


def test_sugerir_departamento_mestre_delega_para_taxonomia_generica(db):
    mestre = DepartamentoMestre(
        grupo_id=GRUPO_1, nome="Pet Shop", criado_por_usuario_id=USUARIO_ID_FALLBACK
    )
    db.add(mestre)
    db.commit()
    encontrado = sugerir_departamento_mestre(db, GRUPO_1, "pet shop")
    assert encontrado.id == mestre.id


def test_vincular_categoria_mestre_sem_id_promove_categoria_local_a_mestre_novo(db, usuario):
    categoria = _criar_categoria_local(db, usuario.id, nome="Alimentos")

    mestre = vincular_categoria_mestre(
        db, categoria=categoria, grupo_id=GRUPO_1, usuario_id=usuario.id, mestre_id=None
    )

    assert mestre.nome == "Alimentos"
    assert categoria.categoria_mestre_id == mestre.id


def test_vincular_categoria_mestre_com_id_liga_a_existente_sem_duplicar(db, usuario):
    mestre_existente = CategoriaMestre(
        grupo_id=GRUPO_1, nome="Alimentos", criado_por_usuario_id=USUARIO_ID_FALLBACK
    )
    db.add(mestre_existente)
    db.commit()
    categoria = _criar_categoria_local(db, usuario.id, nome="Ração e Petiscos")

    mestre = vincular_categoria_mestre(
        db,
        categoria=categoria,
        grupo_id=GRUPO_1,
        usuario_id=usuario.id,
        mestre_id=mestre_existente.id,
    )

    assert mestre.id == mestre_existente.id
    assert db.query(CategoriaMestre).count() == 1


def test_vincular_categoria_mestre_404_quando_id_e_de_outro_grupo(db, usuario):
    mestre_outro_grupo = CategoriaMestre(
        grupo_id=GRUPO_2, nome="Alimentos", criado_por_usuario_id=USUARIO_ID_FALLBACK
    )
    db.add(mestre_outro_grupo)
    db.commit()
    categoria = _criar_categoria_local(db, usuario.id, nome="Alimentos")

    with pytest.raises(HTTPException) as excinfo:
        vincular_categoria_mestre(
            db,
            categoria=categoria,
            grupo_id=GRUPO_1,
            usuario_id=usuario.id,
            mestre_id=mestre_outro_grupo.id,
        )
    assert excinfo.value.status_code == 404


def test_vincular_marca_mestre_sem_id_promove_marca_local_a_mestre_novo(db, usuario):
    marca = _criar_marca_local(db, usuario.id, nome="Premier")

    mestre = vincular_marca_mestre(
        db, marca=marca, grupo_id=GRUPO_1, usuario_id=usuario.id, mestre_id=None
    )

    assert mestre.nome == "Premier"
    assert marca.marca_mestre_id == mestre.id


def test_vincular_marca_mestre_com_id_liga_a_existente_sem_duplicar(db, usuario):
    mestre_existente = MarcaMestre(
        grupo_id=GRUPO_1, nome="Premier", criado_por_usuario_id=USUARIO_ID_FALLBACK
    )
    db.add(mestre_existente)
    db.commit()
    marca = _criar_marca_local(db, usuario.id, nome="Premier Pet")

    mestre = vincular_marca_mestre(
        db, marca=marca, grupo_id=GRUPO_1, usuario_id=usuario.id, mestre_id=mestre_existente.id
    )

    assert mestre.id == mestre_existente.id
    assert db.query(MarcaMestre).count() == 1


def test_vincular_departamento_mestre_sem_id_promove_departamento_local_a_mestre_novo(
    db, usuario
):
    departamento = _criar_departamento_local(db, usuario.id, nome="Pet Shop")

    mestre = vincular_departamento_mestre(
        db, departamento=departamento, grupo_id=GRUPO_1, usuario_id=usuario.id, mestre_id=None
    )

    assert mestre.nome == "Pet Shop"
    assert departamento.departamento_mestre_id == mestre.id


def test_vincular_departamento_mestre_com_id_liga_a_existente_sem_duplicar(db, usuario):
    mestre_existente = DepartamentoMestre(
        grupo_id=GRUPO_1, nome="Pet Shop", criado_por_usuario_id=USUARIO_ID_FALLBACK
    )
    db.add(mestre_existente)
    db.commit()
    departamento = _criar_departamento_local(db, usuario.id, nome="Petshop e Veterinária")

    mestre = vincular_departamento_mestre(
        db,
        departamento=departamento,
        grupo_id=GRUPO_1,
        usuario_id=usuario.id,
        mestre_id=mestre_existente.id,
    )

    assert mestre.id == mestre_existente.id
    assert db.query(DepartamentoMestre).count() == 1
