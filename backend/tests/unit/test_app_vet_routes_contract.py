from app.routes.app_vet_routes import router


def _method_routes() -> set[tuple[str, str]]:
    routes: set[tuple[str, str]] = set()
    for route in router.routes:
        methods = getattr(route, "methods", None)
        if not methods:
            continue
        for method in methods:
            routes.add((route.path, method))
    return routes


def test_app_vet_router_exposes_mobile_veterinary_mvp_routes():
    routes = _method_routes()

    assert ("/app/vet/resumo", "GET") in routes
    assert ("/app/vet/agendamentos", "GET") in routes
    assert ("/app/vet/internacoes", "GET") in routes
    assert ("/app/vet/procedimentos-agenda", "GET") in routes
    assert ("/app/vet/procedimentos-agenda/{agenda_id}/concluir", "PATCH") in routes
    assert ("/app/vet/catalogo/medicamentos", "GET") in routes


def test_app_vet_router_is_registered_in_main_app():
    from app.main import app

    routes = set()
    for route in app.router.routes:
        methods = getattr(route, "methods", None)
        if not methods:
            continue
        for method in methods:
            routes.add((route.path, method))

    assert ("/app/vet/resumo", "GET") in routes
