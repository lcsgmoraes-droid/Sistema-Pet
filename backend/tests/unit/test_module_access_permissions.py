import importlib.util
import inspect
from pathlib import Path

from app.banho_tosa_routes import router as banho_tosa_router
from app.services.default_roles_service import (
    CAIXA_PERMISSIONS,
    GERENTE_PERMISSIONS,
)
from app.veterinario_routes import router as veterinario_router


def _declared_permissions(route) -> set[str]:
    permissions = set()
    for dependency in route.dependant.dependencies:
        call = dependency.call
        if not callable(call):
            continue
        permission = inspect.getclosurevars(call).nonlocals.get("permission")
        if permission:
            permissions.add(permission)
    return permissions


def _effective_routes(router):
    pending = list(router.routes)
    while pending:
        candidate = pending.pop()
        effective_candidates = getattr(candidate, "effective_candidates", None)
        if callable(effective_candidates):
            pending.extend(effective_candidates())
        elif hasattr(candidate, "dependant"):
            yield candidate


def test_caixa_does_not_receive_clinical_modules_by_default():
    assert "veterinario.acessar" not in CAIXA_PERMISSIONS
    assert "banho_tosa.acessar" not in CAIXA_PERMISSIONS
    assert "veterinario.acessar" in GERENTE_PERMISSIONS
    assert "banho_tosa.acessar" in GERENTE_PERMISSIONS


def test_banho_tosa_api_requires_explicit_module_permission():
    routes = list(_effective_routes(banho_tosa_router))

    assert routes
    assert all("banho_tosa.acessar" in _declared_permissions(route) for route in routes)


def test_veterinario_api_requires_permission_except_public_calendar_feed():
    routes = list(_effective_routes(veterinario_router))
    public_path = "/vet/agenda/feed/{token}.ics"

    assert any(route.path == public_path for route in routes)
    for route in routes:
        permissions = _declared_permissions(route)
        if route.path == public_path:
            assert "veterinario.acessar" not in permissions
        else:
            assert "veterinario.acessar" in permissions, route.path


def test_module_permission_migration_preserves_admin_and_operational_roles():
    migration_path = (
        Path(__file__).resolve().parents[2]
        / "alembic"
        / "versions"
        / "zxm20260828a1_module_access_permissions.py"
    )
    spec = importlib.util.spec_from_file_location(
        "module_access_migration", migration_path
    )
    migration = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(migration)

    permission_codes = {code for code, _description in migration.MODULE_PERMISSIONS}

    assert permission_codes == {"banho_tosa.acessar", "veterinario.acessar"}
    assert "administrador" in migration.ROLE_NAMES_BY_PERMISSION["banho_tosa.acessar"]
    assert "administrador" in migration.ROLE_NAMES_BY_PERMISSION["veterinario.acessar"]
    assert "gerente" in migration.ROLE_NAMES_BY_PERMISSION["banho_tosa.acessar"]
    assert "gerente" in migration.ROLE_NAMES_BY_PERMISSION["veterinario.acessar"]
