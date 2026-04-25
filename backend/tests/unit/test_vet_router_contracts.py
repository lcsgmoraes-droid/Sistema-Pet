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
    assert ("/vet/consultas", "GET") in routes
    assert ("/vet/consultas", "POST") in routes
    assert ("/vet/consultas/{consulta_id}/timeline", "GET") in routes
    assert ("/vet/consultas/{consulta_id}/prescricoes", "GET") in routes
    assert ("/vet/prescricoes", "POST") in routes
    assert ("/vet/exames", "GET") in routes
    assert ("/vet/exames", "POST") in routes
    assert ("/vet/exames/{exame_id}/arquivo", "POST") in routes
    assert ("/vet/catalogo/procedimentos", "GET") in routes
    assert ("/vet/procedimentos", "POST") in routes
    assert ("/vet/catalogo/medicamentos", "GET") in routes
    assert ("/vet/catalogo/protocolos-vacinas", "GET") in routes
    assert ("/vet/pets/{pet_id}/vacinas", "GET") in routes
    assert ("/vet/vacinas", "POST") in routes
    assert ("/vet/pets/{pet_id}/peso", "GET") in routes
    assert ("/vet/pets/{pet_id}/perfil-comportamental", "GET") in routes
    assert ("/vet/catalogo/calendario-preventivo", "GET") in routes
    assert ("/vet/dashboard", "GET") in routes
    assert ("/vet/relatorios/clinicos", "GET") in routes
    assert ("/vet/relatorios/clinicos/export.csv", "GET") in routes
    assert ("/vet/consultas/{consulta_id}/prontuario.pdf", "GET") in routes
    assert ("/vet/parceiros", "GET") in routes
    assert ("/vet/relatorios/repasse", "GET") in routes
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
