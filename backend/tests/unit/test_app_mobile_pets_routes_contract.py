from datetime import date, datetime
from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from app.routes import app_mobile_pets_routes
from app.routes import app_mobile_routes


EXPECTED_SUBROUTES = {
    ("/pets", "GET"),
    ("/pets", "POST"),
    ("/pets/{pet_id}", "PUT"),
    ("/pets/{pet_id}", "DELETE"),
    ("/pets/{pet_id}/foto", "POST"),
    ("/pets/{pet_id}/carteirinha", "GET"),
}

EXPECTED_PUBLIC_ROUTES = {
    (f"/app{path}", method) for path, method in EXPECTED_SUBROUTES
}


def _route_signatures(router):
    return {
        (route.path, ",".join(sorted(route.methods)))
        for route in router.routes
        if hasattr(route, "methods")
    }


def test_app_mobile_pets_ficam_em_router_dedicado():
    assert EXPECTED_SUBROUTES <= _route_signatures(app_mobile_pets_routes.router)


def test_app_mobile_preserva_caminhos_publicos_de_pets():
    assert EXPECTED_PUBLIC_ROUTES <= _route_signatures(app_mobile_routes.router)


def test_app_mobile_mantem_aliases_de_compatibilidade_de_pets():
    assert app_mobile_routes.PetResponse is app_mobile_pets_routes.PetResponse
    assert app_mobile_routes.PetCreate is app_mobile_pets_routes.PetCreate
    assert app_mobile_routes.listar_pets is app_mobile_pets_routes.listar_pets
    assert (
        app_mobile_routes.obter_carteirinha_pet_app
        is app_mobile_pets_routes.obter_carteirinha_pet_app
    )


def test_app_mobile_pets_upload_destination_usa_mime_e_uuid(tmp_path, monkeypatch):
    upload_base = tmp_path / "pets"
    monkeypatch.setattr(app_mobile_pets_routes, "PET_UPLOAD_DIR", upload_base)

    dest, filename = app_mobile_pets_routes._pet_upload_destination(
        "tenant-a", "image/png"
    )

    assert dest.parent == upload_base / "tenant-a"
    assert filename.startswith("pet-")
    assert filename.endswith(".png")
    assert dest.resolve().parent == (upload_base / "tenant-a").resolve()

    with pytest.raises(HTTPException):
        app_mobile_pets_routes._pet_upload_destination("tenant-a", "text/plain")
    with pytest.raises(HTTPException):
        app_mobile_pets_routes._pet_upload_destination("../tenant-a", "image/png")


def test_app_mobile_pets_upload_antigo_fica_preso_a_base(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(app_mobile_pets_routes, "PET_UPLOAD_DIR", Path("uploads/pets"))

    safe_path = Path("uploads/pets/tenant-a/pet-ok.jpg")
    safe_path.parent.mkdir(parents=True)
    safe_path.write_bytes(b"ok")

    assert (
        app_mobile_pets_routes._local_pet_upload_path_from_public_url(
            "/uploads/pets/tenant-a/pet-ok.jpg"
        )
        == safe_path
    )
    assert (
        app_mobile_pets_routes._local_pet_upload_path_from_public_url(
            "/uploads/pets/tenant-a/../../fora.jpg"
        )
        is None
    )
    assert (
        app_mobile_pets_routes._local_pet_upload_path_from_public_url(
            "/uploads/outro/pet.jpg"
        )
        is None
    )


def test_app_mobile_pets_serializadores_preservam_carteirinha():
    consulta = SimpleNamespace(
        id=7,
        created_at=datetime(2026, 6, 19, 12, 30),
        tipo="retorno",
        status="finalizada",
        diagnostico="ok",
        observacoes_tutor="sem alteracoes",
    )
    exame = SimpleNamespace(
        id=9,
        nome="Hemograma",
        tipo="laboratorial",
        status="disponivel",
        data_resultado=date(2026, 6, 18),
        interpretacao_ia_resumo="normal",
        arquivo_url="/uploads/exame.pdf",
    )

    assert app_mobile_pets_routes._serialize_consultas_carteirinha([consulta]) == [
        {
            "id": 7,
            "data": "2026-06-19T12:30:00",
            "tipo": "retorno",
            "status": "finalizada",
            "diagnostico": "ok",
            "observacoes_tutor": "sem alteracoes",
        }
    ]
    assert app_mobile_pets_routes._serialize_exames_carteirinha([exame]) == [
        {
            "id": 9,
            "nome": "Hemograma",
            "tipo": "laboratorial",
            "status": "disponivel",
            "data_resultado": "2026-06-18",
            "interpretacao_ia_resumo": "normal",
            "arquivo_url": "/uploads/exame.pdf",
        }
    ]
