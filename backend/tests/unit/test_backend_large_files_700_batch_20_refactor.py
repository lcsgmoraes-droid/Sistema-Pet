from pathlib import Path

from app import veterinario_agenda_routes as facade
from app.veterinario_agenda_routes_parts import (
    agendamentos_routes,
    cadastros_routes,
    calendario_routes,
    pets_routes,
)


def _route_pairs(router):
    return {
        (method, route.path)
        for route in router.routes
        for method in getattr(route, "methods", set())
    }


def test_veterinario_agenda_routes_preserva_endpoints_publicos():
    paths = _route_pairs(facade.router)

    assert ("GET", "/veterinarios") in paths
    assert ("GET", "/consultorios") in paths
    assert ("POST", "/consultorios") in paths
    assert ("PATCH", "/consultorios/{consultorio_id}") in paths
    assert ("DELETE", "/consultorios/{consultorio_id}") in paths
    assert ("GET", "/pets") in paths
    assert ("GET", "/agenda/calendario") in paths
    assert ("POST", "/agenda/calendario/token") in paths
    assert ("GET", "/agenda/calendario.ics") in paths
    assert ("GET", "/agenda/feed/{token}.ics") in paths
    assert ("GET", "/agendamentos") in paths
    assert ("POST", "/agendamentos") in paths
    assert ("GET", "/agendamentos/{agendamento_id}/push-diagnostico") in paths
    assert ("PATCH", "/agendamentos/{agendamento_id}") in paths
    assert ("DELETE", "/agendamentos/{agendamento_id}") in paths
    assert ("POST", "/agendamentos/{agendamento_id}/desfazer-inicio") in paths


def test_veterinario_agenda_routes_preserva_reexports_legados():
    assert facade.listar_veterinarios is cadastros_routes.listar_veterinarios
    assert facade.listar_consultorios is cadastros_routes.listar_consultorios
    assert facade.criar_consultorio is cadastros_routes.criar_consultorio
    assert facade.listar_pets_vet is pets_routes.listar_pets_vet
    assert (
        facade.obter_calendario_agenda_vet
        is calendario_routes.obter_calendario_agenda_vet
    )
    assert facade.listar_agendamentos is agendamentos_routes.listar_agendamentos
    assert facade.criar_agendamento is agendamentos_routes.criar_agendamento
    assert facade.atualizar_agendamento is agendamentos_routes.atualizar_agendamento
    assert facade.remover_agendamento is agendamentos_routes.remover_agendamento
    assert (
        facade.desfazer_inicio_agendamento
        is agendamentos_routes.desfazer_inicio_agendamento
    )


def test_veterinario_agenda_routes_fachada_e_modulos_abaixo_de_700_linhas():
    files = [
        Path(facade.__file__),
        Path(cadastros_routes.__file__),
        Path(pets_routes.__file__),
        Path(calendario_routes.__file__),
        Path(agendamentos_routes.__file__),
    ]

    for path in files:
        assert len(path.read_text(encoding="utf-8").splitlines()) < 700

    facade_source = Path(facade.__file__).read_text(encoding="utf-8")
    assert "@router.get" not in facade_source
    assert "@router.post" not in facade_source
    assert "router.include_router(cadastros_router)" in facade_source
    assert "router.include_router(pets_router)" in facade_source
    assert "router.include_router(calendario_router)" in facade_source
    assert "router.include_router(agendamentos_router)" in facade_source
