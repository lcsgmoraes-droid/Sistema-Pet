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
