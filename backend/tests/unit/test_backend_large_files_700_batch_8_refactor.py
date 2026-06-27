from pathlib import Path


BACKEND_ROOT = Path(__file__).resolve().parents[2]
TARGETS = [
    "app/auth_routes_multitenant.py",
    "app/auth/auth_multitenant_account_routes.py",
    "app/auth/auth_multitenant_recovery_routes.py",
    "app/auth/auth_multitenant_session_routes.py",
    "app/auth/auth_multitenant_support.py",
]


def _line_count(relative: str) -> int:
    return len((BACKEND_ROOT / relative).read_text(encoding="utf-8").splitlines())


def test_auth_multitenant_batch_8_modules_ficam_abaixo_de_700_linhas():
    assert {relative: _line_count(relative) for relative in TARGETS} == {
        relative: count
        for relative in TARGETS
        if (count := _line_count(relative)) <= 700
    }


def test_auth_multitenant_facade_agrega_subrouters_extraidos():
    source = (BACKEND_ROOT / "app/auth_routes_multitenant.py").read_text(
        encoding="utf-8"
    )

    assert "router.include_router(account_router)" in source
    assert "router.include_router(recovery_router)" in source
    assert "router.include_router(session_router)" in source


def test_auth_multitenant_rotas_publicas_permanecem_no_router_principal():
    from app import auth_routes_multitenant

    routes = {
        (route.path, method)
        for route in auth_routes_multitenant.router.routes
        for method in getattr(route, "methods", set())
    }

    assert ("/auth/register", "POST") in routes
    assert ("/auth/login-multitenant", "POST") in routes
    assert ("/auth/refresh", "POST") in routes
    assert ("/auth/verify-email", "POST") in routes
    assert ("/auth/resend-verification", "POST") in routes
    assert ("/auth/forgot-password", "POST") in routes
    assert ("/auth/reset-password", "POST") in routes
    assert ("/auth/select-tenant", "POST") in routes
    assert ("/auth/me-multitenant", "GET") in routes
    assert ("/auth/logout-multitenant", "POST") in routes


def test_auth_multitenant_imports_publicos_continuam_compativeis():
    from app import auth_routes_multitenant
    from app.auth import auth_multitenant_schemas

    assert auth_routes_multitenant.LoginRequest is auth_multitenant_schemas.LoginRequest
    assert (
        auth_routes_multitenant.RegisterRequest
        is auth_multitenant_schemas.RegisterRequest
    )
    assert (
        auth_routes_multitenant.LoginResponse is auth_multitenant_schemas.LoginResponse
    )
    assert callable(auth_routes_multitenant.register)
    assert callable(auth_routes_multitenant.login_multitenant)
    assert callable(auth_routes_multitenant.select_tenant)
