import os
from inspect import signature

from tests.route_contract_helpers import method_routes

os.environ.setdefault("DATABASE_URL", "sqlite:///./test.db")
os.environ.setdefault("ENV", "test")

from app.routes.app_vet_routes import router


def _method_routes() -> set[tuple[str, str]]:
    return set(method_routes(router))


def test_app_vet_router_exposes_mobile_veterinary_mvp_routes():
    routes = _method_routes()

    assert ("/app/vet/resumo", "GET") in routes
    assert ("/app/vet/pets", "GET") in routes
    assert ("/app/vet/consultorios", "GET") in routes
    assert ("/app/vet/agendamentos", "GET") in routes
    assert ("/app/vet/agendamentos", "POST") in routes
    assert ("/app/vet/internacoes", "GET") in routes
    assert ("/app/vet/internacoes/{internacao_id}", "GET") in routes
    assert ("/app/vet/procedimentos-agenda", "GET") in routes
    assert (
        "/app/vet/internacoes/{internacao_id}/procedimentos-agenda",
        "POST",
    ) in routes
    assert ("/app/vet/procedimentos-agenda/{agenda_id}/concluir", "PATCH") in routes
    assert ("/app/vet/catalogo/medicamentos", "GET") in routes


def test_app_vet_agendamentos_accepts_day_and_range_filters():
    route = next(
        route
        for route in router.routes
        if route.path == "/app/vet/agendamentos" and "GET" in route.methods
    )
    dependant = getattr(route, "dependant", None)

    query_params = {param.name for param in dependant.query_params}

    assert {"data", "data_inicio", "data_fim"}.issubset(query_params)


def test_app_vet_agendamento_post_accepts_consulta_payload():
    route = next(
        route
        for route in router.routes
        if route.path == "/app/vet/agendamentos" and "POST" in route.methods
    )
    dependant = getattr(route, "dependant", None)
    body_param = dependant.body_params[0]
    body_type = signature(route.endpoint).parameters[body_param.name].annotation
    fields = set(body_type.model_fields)

    assert {
        "pet_id",
        "data_hora",
        "duracao_minutos",
        "consultorio_id",
        "motivo",
    }.issubset(fields)


def test_app_vet_router_is_registered_in_main_app():
    from app.main import app

    routes = set(method_routes(app.router))

    assert ("/app/vet/resumo", "GET") in routes
