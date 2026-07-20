from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi import HTTPException

from app.auth import hash_password
from app.models import Cliente
from app.routes import ecommerce_auth_profiles
from app.routes.ecommerce_auth_profiles import excluir_conta
from app.routes.ecommerce_auth_schemas import EcommerceAccountDeletionRequest
from app.services.lgpd_customer_data import _delete_local_pet_photo


class _Query:
    def __init__(self, db, model):
        self.db = db
        self.model = model

    def filter(self, *_args, **_kwargs):
        return self

    def order_by(self, *_args, **_kwargs):
        return self

    def all(self):
        return self.db.rows.get(self.model, [])

    def update(self, values, synchronize_session=False):
        self.db.updates.append((self.model, values, synchronize_session))
        return 1

    def delete(self, synchronize_session=False):
        self.db.deletes.append((self.model, synchronize_session))
        return 1


class _Db:
    def __init__(self, rows=None):
        self.rows = rows or {}
        self.updates = []
        self.deletes = []
        self.deleted_rows = []
        self.committed = False

    def query(self, model):
        return _Query(self, model)

    def delete(self, row):
        self.deleted_rows.append(row)

    def commit(self):
        self.committed = True


def _user(tenant_id, password="senha-segura"):
    return SimpleNamespace(
        id=77,
        tenant_id=tenant_id,
        email="cliente@example.com",
        hashed_password=hash_password(password),
        is_active=True,
        is_admin=False,
        nome="Cliente Teste",
        telefone="18999999999",
        cpf_cnpj="12345678901",
        foto_url="https://example.com/foto.jpg",
        push_token="push-token",
        vet_calendar_token="calendar-token",
        consent_date=object(),
        consent_version="1",
        privacy_version="1",
        consent_ip="127.0.0.1",
        consent_user_agent="pytest",
        email_verified=True,
        email_verified_at=object(),
        email_verification_token_hash="hash",
        email_verification_token_expires=object(),
        email_verification_sent_at=object(),
        two_factor_enabled=True,
        two_factor_secret="secret",
        backup_codes="[]",
        reset_token="reset",
        reset_token_expires=object(),
        failed_login_attempts=3,
        locked_until=object(),
        last_login_at=object(),
        last_login_ip="127.0.0.1",
        password_changed_at=None,
        oauth_provider="google",
        oauth_id="oauth-id",
        nome_loja="Loja",
        endereco_loja="Endereco",
        telefone_loja="Telefone",
    )


def test_account_deletion_rejects_wrong_password_before_database_changes():
    tenant_id = uuid4()
    user = _user(tenant_id)
    payload = EcommerceAccountDeletionRequest(
        password="senha-errada", confirmation="EXCLUIR"
    )

    with pytest.raises(HTTPException) as exc:
        excluir_conta(
            payload=payload,
            request=SimpleNamespace(headers={}, client=None),
            current_user=user,
            db=_Db(),
        )

    assert exc.value.status_code == 400
    assert user.is_active is True
    assert user.email == "cliente@example.com"


def test_account_deletion_anonymizes_user_and_revokes_access(monkeypatch):
    tenant_id = uuid4()
    user = _user(tenant_id)
    cliente = SimpleNamespace(id=42)
    db = _Db(rows={Cliente: [cliente]})
    calls = []

    class _PrivacyOpsService:
        def __init__(self, service_db, service_tenant_id):
            assert service_db is db
            assert service_tenant_id == str(tenant_id)

        def create_subject_request(self, **kwargs):
            calls.append(("create", kwargs))
            return SimpleNamespace(id=501)

        def anonymize_customer_from_request(self, **kwargs):
            calls.append(("anonymize", kwargs))

    monkeypatch.setattr(
        ecommerce_auth_profiles, "PrivacyOpsService", _PrivacyOpsService
    )

    result = excluir_conta(
        payload=EcommerceAccountDeletionRequest(
            password="senha-segura", confirmation="EXCLUIR"
        ),
        request=SimpleNamespace(
            headers={"user-agent": "pytest"},
            client=SimpleNamespace(host="127.0.0.1"),
        ),
        current_user=user,
        db=db,
    )

    assert result["account_deleted"] is True
    assert result["privacy_request_ids"] == [501]
    assert db.committed is True
    assert user.is_active is False
    assert user.email.startswith("conta-excluida-77-")
    assert user.email.endswith("@deleted.corepet.invalid")
    assert user.nome is None
    assert user.telefone is None
    assert user.cpf_cnpj is None
    assert user.push_token is None
    assert user.email_verified is False
    assert [name for name, _payload in calls] == ["create", "anonymize"]
    assert db.updates
    assert db.deletes


def test_account_deletion_removes_local_pet_photo(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    photo = tmp_path / "uploads" / "pets" / "tenant-1" / "pet.jpg"
    photo.parent.mkdir(parents=True)
    photo.write_bytes(b"photo")

    assert _delete_local_pet_photo("/uploads/pets/tenant-1/pet.jpg") is True
    assert photo.exists() is False
    assert _delete_local_pet_photo("https://example.com/pet.jpg") is False
