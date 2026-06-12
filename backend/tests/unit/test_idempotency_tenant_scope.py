import json
from datetime import datetime, timedelta
from types import SimpleNamespace
from uuid import UUID

import pytest
from sqlalchemy.orm import Session
from starlette.requests import Request

from app import dre_plano_contas_models  # noqa: F401
from app.idempotency import _cleanup_expired_keys, idempotent
from app.idempotency_models import IdempotencyKey


TENANT_ID = UUID("180d9cbf-5dcb-4676-bf11-dcbd91ed444b")


class _FakeQuery:
    def __init__(self, result=None):
        self.result = result
        self.filters = []
        self.deleted = False

    def filter(self, *criteria):
        self.filters.extend(str(criterion) for criterion in criteria)
        return self

    def first(self):
        return self.result

    def delete(self, synchronize_session=False):
        self.deleted = True
        self.synchronize_session = synchronize_session
        return 0


class _FakeSession(Session):
    def __init__(self):
        super().__init__()
        self.queries = []
        self.added = None
        self.commits = 0

    def query(self, model):
        assert model is IdempotencyKey
        query = _FakeQuery()
        self.queries.append(query)
        return query

    def add(self, obj):
        self.added = obj

    def commit(self):
        self.commits += 1

    def refresh(self, obj):
        obj.id = obj.id or 1


def _request(body: dict) -> Request:
    payload = json.dumps(body).encode("utf-8")

    async def receive():
        return {"type": "http.request", "body": payload, "more_body": False}

    return Request(
        {
            "type": "http",
            "method": "POST",
            "path": "/vendas",
            "headers": [(b"idempotency-key", b"tenant-key-123456")],
            "query_string": b"",
            "path_params": {},
            "server": ("testserver", 80),
            "scheme": "http",
        },
        receive,
    )


@pytest.mark.asyncio
async def test_idempotent_uses_user_and_tenant_dependency_to_create_scoped_key():
    db = _FakeSession()
    user = SimpleNamespace(id=42)

    @idempotent()
    async def endpoint(*, request, db, user_and_tenant):
        return {"ok": True}

    result = await endpoint(
        request=_request({"valor": 10}),
        db=db,
        user_and_tenant=(user, TENANT_ID),
    )

    assert result == {"ok": True}
    assert db.added is not None
    assert db.added.tenant_id == TENANT_ID
    assert db.added.user_id == 42
    assert db.added.chave_idempotencia == "tenant-key-123456"
    assert any("idempotency_keys.tenant_id" in fragment for fragment in db.queries[-1].filters)


def test_cleanup_expired_keys_filters_by_tenant_id():
    db = _FakeSession()

    _cleanup_expired_keys(
        db,
        user_id=42,
        tenant_id=TENANT_ID,
        now=datetime.utcnow() + timedelta(days=2),
    )

    assert db.queries
    assert db.queries[0].deleted is True
    assert any("idempotency_keys.tenant_id" in fragment for fragment in db.queries[0].filters)
