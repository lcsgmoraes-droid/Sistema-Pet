from datetime import datetime
from types import SimpleNamespace

from app.pets_routes import PetResponse, enriquecer_pet_response


def _pet_legado():
    cliente = SimpleNamespace(
        nome="Ana Demo",
        telefone="18999990000",
        celular=None,
        tenant_id="tenant-demo",
    )
    return SimpleNamespace(
        id=1,
        codigo="DEMO-PET-LEGADO",
        cliente_id=2,
        user_id=3,
        nome="Thor",
        especie="Cao",
        raca="Sem raca definida",
        sexo="macho",
        castrado=False,
        data_nascimento=None,
        idade_aproximada=24,
        peso=18.4,
        cor=None,
        porte="medio",
        microchip=None,
        alergias="Frango; Poeira",
        alergias_lista="Frango; Poeira",
        doencas_cronicas=None,
        condicoes_cronicas_lista=None,
        medicamentos_continuos=None,
        medicamentos_continuos_lista="",
        restricoes_alimentares_lista="Soja, Lactose",
        historico_clinico=None,
        tipo_sanguineo=None,
        pedigree_registro=None,
        castrado_data=None,
        observacoes=None,
        foto_url=None,
        ativo=True,
        created_at=None,
        updated_at=datetime(2026, 8, 14, 10, 0),
        cliente=cliente,
    )


def test_listagem_de_pets_aceita_datas_nulas_e_listas_clinicas_legadas():
    payload = enriquecer_pet_response(_pet_legado())
    response = PetResponse.model_validate(payload)

    assert response.created_at is None
    assert response.alergias_lista == ["Frango", "Poeira"]
    assert response.restricoes_alimentares_lista == ["Soja", "Lactose"]

