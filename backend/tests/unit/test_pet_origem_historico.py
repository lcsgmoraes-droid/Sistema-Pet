from uuid import uuid4

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.db import Base
from app.db import base as _base  # noqa: F401 - registra todo o metadata
from app.grupo_comercial_models import GrupoComercial, GrupoComercialMembro
from app.models_cadastros import Pet, PetHistoricoAlteracao
from app.veterinario_models import VetPartnerLink
from app.services.pet_historico_service import registrar_alteracoes_pet
from app.tenancy.context import clear_current_tenant, set_current_tenant


@pytest.fixture()
def db():
    engine = create_engine("sqlite://")
    Base.metadata.create_all(
        engine,
        tables=[
            PetHistoricoAlteracao.__table__,
            Pet.__table__,
            VetPartnerLink.__table__,
            GrupoComercial.__table__,
            GrupoComercialMembro.__table__,
        ],
    )
    session = Session(engine)
    try:
        yield session
    finally:
        session.close()


def test_origem_do_pet_nao_pode_ser_trocada():
    loja = uuid4()
    pet = Pet(tenant_id=loja, nome="Rex", especie="cao")
    pet.origem_tenant_id = loja
    with pytest.raises(ValueError):
        pet.origem_tenant_id = uuid4()


def test_historico_do_pet_ignora_campos_de_saude(db):
    loja = uuid4()
    total = registrar_alteracoes_pet(
        db,
        pet_id=3,
        tenant_id=loja,
        user_id=1,
        antes={"nome": "Rex", "alergias": "nenhuma", "porte": "medio"},
        depois={"nome": "Rex II", "alergias": "frango", "porte": "grande"},
    )
    db.commit()
    set_current_tenant(loja)
    campos = {r.campo for r in db.query(PetHistoricoAlteracao).all()}
    clear_current_tenant()
    assert total == 2
    assert campos == {"nome", "porte"}
