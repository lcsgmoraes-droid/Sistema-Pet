from app.veterinario_routes import router


def _method_routes() -> list[tuple[str, str]]:
    routes: list[tuple[str, str]] = []
    for route in router.routes:
        methods = getattr(route, "methods", None)
        if not methods:
            continue
        for method in methods:
            routes.append((route.path, method))
    return routes


def test_vet_router_preserva_endpoints_movidos():
    routes = set(_method_routes())

    assert ("/vet/veterinarios", "GET") in routes
    assert ("/vet/agendamentos", "GET") in routes
    assert ("/vet/agendamentos", "POST") in routes
    assert ("/vet/agenda/calendario", "GET") in routes
    assert ("/vet/internacoes", "GET") in routes
    assert ("/vet/internacoes/config", "GET") in routes
    assert ("/vet/internacoes/procedimentos-agenda", "GET") in routes
    assert ("/vet/ia/assistente", "POST") in routes
    assert ("/vet/ia/conversas", "GET") in routes
    assert ("/vet/exames/{exame_id}/chat", "POST") in routes


def test_vet_router_nao_duplica_metodo_e_path():
    routes = _method_routes()

    assert len(routes) == len(set(routes))


def test_rotas_estaticas_de_internacao_vem_antes_da_dinamica():
    paths = [route.path for route in router.routes if hasattr(route, "path")]

    assert paths.index("/vet/internacoes/config") < paths.index("/vet/internacoes/{internacao_id}")
    assert paths.index("/vet/internacoes/procedimentos-agenda") < paths.index("/vet/internacoes/{internacao_id}")
