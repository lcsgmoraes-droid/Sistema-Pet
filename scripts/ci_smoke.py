from __future__ import annotations

import json
import os
from pathlib import Path
import sqlite3
import sys
from typing import Any
import uuid
from uuid import UUID as PyUUID


ROOT = Path(__file__).resolve().parents[1]
BACKEND_ROOT = ROOT / "backend"
AUDIT_SMOKE_TENANT_ID = PyUUID("11111111-1111-1111-1111-111111111111")
_SQLITE_COMPILERS_INSTALLED = False


class _EmptyQuery:
    def filter(self, *args: Any, **kwargs: Any) -> "_EmptyQuery":
        return self

    def first(self) -> None:
        return None

    def all(self) -> list[Any]:
        return []


class _FakeDbSession:
    def query(self, *args: Any, **kwargs: Any) -> _EmptyQuery:
        return _EmptyQuery()

    def commit(self) -> None:
        return None

    def rollback(self) -> None:
        return None


def ensure_backend_path() -> None:
    backend_path = str(BACKEND_ROOT)
    if backend_path not in sys.path:
        sys.path.insert(0, backend_path)


def install_sqlite_type_support() -> None:
    global _SQLITE_COMPILERS_INSTALLED
    if _SQLITE_COMPILERS_INSTALLED:
        return

    from sqlalchemy.dialects.postgresql import UUID as PGUUID
    from sqlalchemy.ext.compiler import compiles

    sqlite3.register_adapter(PyUUID, lambda value: str(value))

    @compiles(PGUUID, "sqlite")
    def _compile_pg_uuid_for_sqlite(type_, compiler, **kw):
        return "CHAR(36)"

    _SQLITE_COMPILERS_INSTALLED = True


def assert_route_exists(app: Any, path: str, method: str) -> None:
    expected_method = method.upper()
    for route in app.routes:
        if getattr(route, "path", None) == path and expected_method in getattr(route, "methods", set()):
            return
    raise AssertionError(f"Rota obrigatoria ausente: {expected_method} {path}")


def configure_backend_smoke_env() -> None:
    os.environ.setdefault("DATABASE_URL", "sqlite:///./test.db")
    os.environ.setdefault("ENVIRONMENT", "testing")
    os.environ.setdefault("DEBUG", "false")
    os.environ.setdefault("JWT_SECRET_KEY", "ci-smoke-secret-key-with-more-than-32-characters")
    os.environ.setdefault("EMAIL_VERIFICATION_REQUIRED", "false")
    os.environ.setdefault("BLING_SYNC_SCHEDULER_ENABLED", "false")
    os.environ.setdefault("SEFAZ_IMPORTACAO_AUTOMATICA", "false")


def _sqlite_url(db_path: str | Path | None) -> str:
    if db_path is None:
        return "sqlite:///:memory:"
    return f"sqlite:///{Path(db_path).resolve().as_posix()}"


def run_audit_request_id_smoke(
    db_path: str | Path | None = None,
    request_id: str = "ci-smoke-audit-request",
) -> dict[str, Any]:
    configure_backend_smoke_env()
    ensure_backend_path()
    install_sqlite_type_support()

    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    from app.middlewares.request_context import clear_request_context, set_request_id
    from app.models import AuditLog, User
    from app.services.business_audit_service import log_business_event
    from app.tenancy.context import clear_current_tenant, set_current_tenant

    engine = create_engine(_sqlite_url(db_path))
    try:
        User.__table__.create(engine, checkfirst=True)
        AuditLog.__table__.create(engine, checkfirst=True)

        Session = sessionmaker(bind=engine)
        db = Session()
        try:
            set_current_tenant(AUDIT_SMOKE_TENANT_ID)
            set_request_id(request_id)
            try:
                log_business_event(
                    db=db,
                    tenant_id=AUDIT_SMOKE_TENANT_ID,
                    user_id=None,
                    event="smoke.audit_request_id",
                    entity_type="smoke",
                    entity_id=None,
                    metadata={"source": "ci_smoke"},
                    commit=True,
                )
            finally:
                clear_request_context()
                clear_current_tenant()

            row = (
                db.query(AuditLog)
                .filter(AuditLog.action == "business.smoke.audit_request_id")
                .order_by(AuditLog.id.desc())
                .first()
            )
            if row is None:
                raise AssertionError("Evento de auditoria do smoke nao foi gravado")

            payload = json.loads(row.new_value or "{}")
            if payload.get("request_id") != request_id:
                raise AssertionError(
                    f"request_id de auditoria incorreto: {payload.get('request_id')!r}"
                )

            return {
                "action": row.action,
                "request_id": payload["request_id"],
            }
        finally:
            db.close()
    finally:
        engine.dispose()


def run_backend_smoke() -> None:
    configure_backend_smoke_env()
    ensure_backend_path()

    from fastapi.testclient import TestClient

    import app.main as backend_main
    from app.auth_routes_multitenant import get_session as auth_get_session

    app = backend_main.app
    assert_route_exists(app, "/health", "GET")
    assert_route_exists(app, "/auth/login-multitenant", "POST")

    app.dependency_overrides[auth_get_session] = lambda: _FakeDbSession()
    client = TestClient(app)

    health_response = client.get("/health")
    assert health_response.status_code == 200, health_response.text

    auth_payload = {
        "email": "ci-smoke@example.com",
        "pass" + "word": f"invalid-{uuid.uuid4()}",
    }
    auth_response = client.post("/auth/login-multitenant", json=auth_payload)
    assert auth_response.status_code == 401, auth_response.text

    run_audit_request_id_smoke()

    print("Backend smoke OK: /health, /auth/login-multitenant e auditoria com request_id")


def main() -> int:
    run_backend_smoke()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
