from types import SimpleNamespace

import pytest
from fastapi import HTTPException
from pydantic import ValidationError

from app.auth import hash_password, verify_password
from app.auth import auth_multitenant_account_routes as routes
from app.auth.auth_multitenant_schemas import ChangePasswordRequest


class FakeDb:
    def __init__(self):
        self.commits = 0

    def commit(self):
        self.commits += 1


def test_change_password_requires_current_password_and_revokes_sessions(monkeypatch):
    user = SimpleNamespace(
        id=17,
        hashed_password=hash_password("SenhaAntiga123"),
        reset_token="old-token",
        reset_token_expires=object(),
    )
    db = FakeDb()
    events = []
    monkeypatch.setattr(
        routes,
        "register_password_changed",
        lambda *_args: events.append("audit"),
    )
    monkeypatch.setattr(
        routes,
        "revoke_all_sessions",
        lambda _db, user_id, reason: events.append((user_id, reason)),
    )

    with pytest.raises(HTTPException, match="Senha atual incorreta"):
        routes.change_password(
            ChangePasswordRequest(senha_atual="errada", nova_senha="NovaSenha123"),
            request=object(),
            db=db,
            current_user=user,
        )
    assert verify_password("SenhaAntiga123", user.hashed_password)
    assert events == []
    assert db.commits == 0

    routes.change_password(
        ChangePasswordRequest(senha_atual="SenhaAntiga123", nova_senha="NovaSenha123"),
        request=object(),
        db=db,
        current_user=user,
    )
    assert verify_password("NovaSenha123", user.hashed_password)
    assert not verify_password("SenhaAntiga123", user.hashed_password)
    assert user.reset_token is None
    assert user.reset_token_expires is None
    assert events == ["audit", (17, "password_change")]
    assert db.commits == 1


def test_change_password_rejects_reused_or_short_password(monkeypatch):
    user = SimpleNamespace(id=17, hashed_password=hash_password("SenhaAtual123"))
    db = FakeDb()
    with pytest.raises(HTTPException, match="diferente da atual"):
        routes.change_password(
            ChangePasswordRequest(
                senha_atual="SenhaAtual123", nova_senha="SenhaAtual123"
            ),
            request=object(),
            db=db,
            current_user=user,
        )
    with pytest.raises(ValidationError):
        ChangePasswordRequest(senha_atual="SenhaAtual123", nova_senha="curta")
    assert db.commits == 0
