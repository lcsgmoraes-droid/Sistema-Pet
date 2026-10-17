"""Regressoes encontradas na copia local: busca, identidade e dados clinicos."""

from datetime import datetime
from types import SimpleNamespace
from uuid import UUID

import pytest
from fastapi import HTTPException
from pydantic import ValidationError
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.clientes import crud_routes
from app.clientes.schemas import ClienteUpdate
from app.db import Base
from app.db import base as _base  # noqa: F401 - registra as FKs
from app.grupo_comercial_models import GrupoComercial, GrupoComercialMembro
from app.models import Cliente, ClienteContato, Pet
from app.models_cadastros import PetRegistroClinico
from app.produtos.schemas import ProdutoCreate, ProdutoResponse, ProdutoUpdate
from app.services import pet_registros_clinicos_service as registros
from app.tenancy.context import clear_current_tenant, set_current_tenant
from app.veterinario_models import VetPartnerLink
from app.veterinario_schemas import AgendamentoCreate, AgendamentoUpdate


TENANT = UUID("11111111-1111-1111-1111-111111111111")


@pytest.fixture
def db():
    engine = create_engine("sqlite://")
    Base.metadata.create_all(
        engine,
        tables=[
            Cliente.__table__,
            ClienteContato.__table__,
            Pet.__table__,
            PetRegistroClinico.__table__,
            VetPartnerLink.__table__,
            GrupoComercial.__table__,
            GrupoComercialMembro.__table__,
        ],
    )
    set_current_tenant(TENANT)
    with Session(engine) as session:
        try:
            yield session
        finally:
            clear_current_tenant()
    engine.dispose()


def pessoa(db, **extras):
    db.execute(
        Cliente.__table__.insert(),
        {
            "id": 1,
            "tenant_id": TENANT,
            "user_id": 1,
            "codigo": "QA001",
            "nome": "Pessoa QA",
            "ativo": True,
            "is_cliente": True,
            "celular": "11970167701",
            **extras,
        },
    )
    db.commit()
    return db.query(Cliente).filter(Cliente.id == 1).one()


@pytest.mark.parametrize(
    "campo,documento,busca",
    [
        ("cpf", "71610260925", "716.102.609-25"),
        ("cpf", "716.102.609-25", "71610260925"),
        ("cnpj", "70462198000139", "70.462.198/0001-39"),
        ("cnpj", "70.462.198/0001-39", "70462198000139"),
    ],
)
def test_busca_documento_com_ou_sem_mascara(db, campo, documento, busca):
    pessoa(db, **{campo: documento})
    resultado = crud_routes._aplicar_filtro_busca(db.query(Cliente), busca).all()
    assert [item.id for item in resultado] == [1]


def test_codigo_alfanumerico_nao_ganha_filtro_de_documento_por_digitos(db):
    pessoa(db, cpf="71610260925")
    assert not crud_routes._aplicar_filtro_busca(
        db.query(Cliente), "INEXISTENTE-60925"
    ).all()


@pytest.mark.parametrize("campo", ["celular", "telefone"])
def test_update_parcial_rejeita_numero_principal_igual_ao_adicional(
    db, monkeypatch, campo
):
    cliente = pessoa(db)
    db.add(
        ClienteContato(
            tenant_id=TENANT,
            cliente_id=cliente.id,
            numero="(11) 97016-7703",
            numero_digitos="11970167703",
            vinculo="Responsavel QA",
        )
    )
    db.commit()
    monkeypatch.setattr(crud_routes, "_obter_cliente_ou_404", lambda *_: cliente)
    with pytest.raises(HTTPException) as erro:
        crud_routes.update_cliente(
            cliente_id=cliente.id,
            cliente_data=ClienteUpdate(**{campo: "11970167703"}),
            db=db,
            user_and_tenant=(SimpleNamespace(id=1), TENANT),
        )
    assert erro.value.status_code == 409
    db.expire_all()
    assert cliente.celular == "11970167701"
    assert len(cliente.contatos_adicionais) == 1


@pytest.mark.parametrize("valor", [None, -2, 0, float("inf"), float("nan")])
def test_pesagem_invalida_nao_e_gravada(db, valor):
    with pytest.raises(HTTPException) as erro:
        registros.criar_registro(
            db, pet_id=1, tenant_id=TENANT, user_id=1, tipo="peso", valor=valor
        )
    assert erro.value.status_code == 422
    assert db.query(PetRegistroClinico).count() == 0


def test_peso_atual_prefere_historico_e_edicao_so_da_data_preserva_valor(db):
    pet = SimpleNamespace(id=1, peso=8.0)
    assert registros.obter_peso_atual(db, pet) == 8.0
    registro = registros.criar_registro(
        db,
        pet_id=1,
        tenant_id=TENANT,
        user_id=1,
        tipo="peso",
        valor=13.7,
        registrado_em=datetime(2026, 10, 15, 12),
    )
    db.commit()
    assert registros.obter_peso_atual(db, pet) == 13.7
    registros.atualizar_registro(
        db,
        registro_id=registro.id,
        pet_id=1,
        tenant_id=TENANT,
        registrado_em=datetime(2026, 10, 16, 12),
    )
    db.commit()
    assert registros.obter_peso_atual(db, pet) == 13.7
    with pytest.raises(HTTPException) as erro:
        registros.atualizar_registro(
            db, registro_id=registro.id, pet_id=1, tenant_id=TENANT, valor=-1
        )
    assert erro.value.status_code == 422
    db.expire_all()
    assert db.query(PetRegistroClinico).one().valor == 13.7


@pytest.mark.parametrize("schema", [ProdutoCreate, ProdutoUpdate])
@pytest.mark.parametrize("preco", [-1, float("inf"), float("nan")])
def test_produto_rejeita_preco_venda_invalido_na_entrada(schema, preco):
    with pytest.raises(ValidationError):
        schema(codigo="QA-PROD", nome="Produto QA", preco_venda=preco)


def test_produto_pai_e_edicao_sem_preco_continuam_compativeis():
    assert (
        ProdutoCreate(codigo="QA-PAI", nome="Pai QA", tipo_produto="PAI").preco_venda
        is None
    )
    assert ProdutoUpdate(nome="Nome novo").model_dump(exclude_unset=True) == {
        "nome": "Nome novo"
    }
    # Validacao de escrita nao pode impedir a leitura de dados legados a corrigir.
    legado = ProdutoResponse(
        id=1,
        codigo="QA-LEGADO",
        nome="Legado a corrigir",
        preco_venda=-1,
        ativo=True,
        created_at=datetime(2026, 10, 15),
        updated_at=datetime(2026, 10, 15),
    )
    assert legado.preco_venda == -1


@pytest.mark.parametrize("schema", [AgendamentoCreate, AgendamentoUpdate])
@pytest.mark.parametrize("duracao", [-15, 0])
def test_agenda_rejeita_duracao_nao_positiva(schema, duracao):
    with pytest.raises(ValidationError):
        schema(pet_id=1, data_hora=datetime(2026, 10, 15, 12), duracao_minutos=duracao)


def test_agenda_preserva_duracao_padrao_e_update_parcial():
    assert (
        AgendamentoCreate(
            pet_id=1, data_hora=datetime(2026, 10, 15, 12)
        ).duracao_minutos
        == 30
    )
    assert AgendamentoUpdate(observacoes="QA").model_dump(exclude_unset=True) == {
        "observacoes": "QA"
    }
