from types import SimpleNamespace
from unittest.mock import MagicMock
from uuid import UUID, uuid4

import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from starlette.requests import Request

from app.models import Cliente, Role, Tenant, User, UserTenant
from app.auth import hash_password
from app.routes import ecommerce_auth_public
from app.routes.ecommerce_auth_common import _ensure_active_store_access
from app.routes.ecommerce_auth_public import login_cliente, registrar_cliente
from app.routes.ecommerce_auth_schemas import (
    EcommerceLoginRequest,
    EcommerceRegisterRequest,
)
from app.services.user_account_service import create_tenant_user_account
from app.tenancy.context import set_tenant_context
from app.usuarios_routes import (
    UserDelete,
    _fundir_pessoa_de_cliente_com_operacional,
    _vincular_pessoa_operacional_existente,
    excluir_usuario,
)


def _session():
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Tenant.__table__.create(engine)
    Role.__table__.create(engine)
    User.__table__.create(engine)
    UserTenant.__table__.create(engine)
    return Session(engine)


def test_cadastro_publico_nao_duplica_funcionario_pelo_celular():
    db = _session()
    tenant_id = uuid4()
    db.add(
        Tenant(
            id=str(tenant_id),
            name="Loja Teste",
            name_normalized="loja teste",
            ecommerce_slug="loja-teste",
            status="active",
            plan="pet-start",
        )
    )
    set_tenant_context(UUID(str(tenant_id)))
    db.add(Role(tenant_id=tenant_id, name="Administrador"))
    db.commit()
    role = db.query(Role).first()
    existing, _ = create_tenant_user_account(
        db,
        tenant_id=tenant_id,
        username=None,
        email=None,
        login_phone="(67) 99999-1111",
        password="SenhaForte123",
        role_id=role.id,
        nome="Ana Silva",
    )
    db.commit()

    request = Request(
        {
            "type": "http",
            "headers": [(b"x-tenant-id", str(tenant_id).encode("ascii"))],
        }
    )
    payload = EcommerceRegisterRequest(
        email="ana.app@example.com",
        password="SenhaForte456",
        nome="Ana Silva",
        telefone="+55 (67) 99999-1111",
        cpf="12345678901",
        accepted_terms=True,
        accepted_privacy=True,
    )
    with pytest.raises(HTTPException) as error:
        registrar_cliente(payload, request, db)

    assert error.value.status_code == 409
    assert db.query(User).count() == 1
    assert db.query(User).first().id == existing.id


def test_cadastro_publico_exige_erp_para_ficha_de_funcionario(monkeypatch):
    employee = SimpleNamespace(
        id=1,
        telefone="(67) 99999-1111",
        celular=None,
        auth_user_id=None,
        tipo_cadastro="funcionario",
        is_entregador=False,
        merged_into_id=None,
    )
    db = MagicMock()

    def query_for(model):
        query = MagicMock()
        query.filter.return_value = query
        query.first.return_value = None
        query.all.return_value = [employee] if model is Cliente else []
        return query

    db.query.side_effect = query_for
    monkeypatch.setattr(
        ecommerce_auth_public, "sync_rls_auth_email", lambda *args: None
    )
    monkeypatch.setattr(
        ecommerce_auth_public, "_existing_user_for_phone", lambda *args: None
    )
    tenant_id = uuid4()
    request = Request(
        {
            "type": "http",
            "headers": [(b"x-tenant-id", str(tenant_id).encode())],
        }
    )

    with pytest.raises(HTTPException) as error:
        registrar_cliente(
            EcommerceRegisterRequest(
                email="ana.app@example.com",
                password="SenhaForte456",
                nome="Ana Silva",
                telefone="+55 (67) 99999-1111",
                cpf="12345678901",
                accepted_terms=True,
                accepted_privacy=True,
            ),
            request,
            db,
        )

    assert error.value.status_code == 409
    db.add.assert_not_called()


def test_cadastro_publico_nao_duplica_conta_do_outro_canal():
    db = _session()
    tenant_id = uuid4()
    set_tenant_context(tenant_id)
    db.add(
        Tenant(
            id=str(tenant_id),
            name="Loja Teste",
            name_normalized="loja teste",
            ecommerce_slug="loja-teste",
            status="active",
            plan="pet-start",
        )
    )
    db.add(
        User(
            tenant_id=tenant_id,
            email="ana.site@example.com",
            telefone="+55 (67) 99999-1111",
            hashed_password="hash",
            is_active=True,
        )
    )
    db.commit()
    request = Request(
        {
            "type": "http",
            "headers": [(b"x-tenant-id", str(tenant_id).encode())],
        }
    )

    with pytest.raises(HTTPException) as error:
        registrar_cliente(
            EcommerceRegisterRequest(
                email="ana.app@example.com",
                password="SenhaForte456",
                nome="Ana Silva",
                telefone="(67) 99999-1111",
                cpf="12345678901",
                accepted_terms=True,
                accepted_privacy=True,
            ),
            request,
            db,
        )

    assert error.value.status_code == 409
    assert db.query(User).count() == 1


def test_promocao_reaproveita_ficha_operacional_liberada():
    person = SimpleNamespace(
        id=10,
        celular="(67) 99999-1111",
        telefone=None,
        cpf="123.456.789-01",
        auth_user_id=None,
    )
    user = SimpleNamespace(
        id=99,
        login_phone="67999991111",
        telefone="67999991111",
        cpf_cnpj="12345678901",
    )
    db = MagicMock()
    query = MagicMock()
    query.filter.return_value = query
    query.all.return_value = [person]
    db.query.return_value = query

    assert (
        _vincular_pessoa_operacional_existente(db, tenant_id=uuid4(), user=user) is True
    )
    assert person.auth_user_id == user.id


def test_promocao_funde_ficha_cliente_na_ficha_operacional(monkeypatch):
    cliente = SimpleNamespace(
        id=20,
        is_cliente=True,
        is_funcionario=False,
        is_veterinario=False,
        is_entregador=False,
        ativo=True,
    )
    operacional = SimpleNamespace(
        id=10,
        celular="67999991111",
        telefone=None,
        cpf="12345678901",
    )
    user = SimpleNamespace(
        id=99, login_phone=None, telefone="(67) 99999-1111", cpf_cnpj="12345678901"
    )
    query_cliente = MagicMock()
    query_cliente.filter.return_value = query_cliente
    query_cliente.first.return_value = cliente
    query_operacional = MagicMock()
    query_operacional.filter.return_value = query_operacional
    query_operacional.all.return_value = [operacional]
    db = MagicMock()
    db.query.side_effect = [query_cliente, query_operacional]
    merges = []
    monkeypatch.setattr(
        "app.usuarios_routes.executar_fusao_pessoas",
        lambda *args, **kwargs: merges.append(kwargs),
    )
    tenant_id = uuid4()

    assert (
        _fundir_pessoa_de_cliente_com_operacional(
            db, tenant_id=tenant_id, user=user, actor_user_id=7
        )
        is True
    )
    assert merges[0]["principal_id"] == operacional.id
    assert merges[0]["duplicado_id"] == cliente.id
    assert merges[0]["commit"] is False


def test_cadastro_publico_funde_fichas_de_cliente_com_mesmo_telefone(monkeypatch):
    people = [
        SimpleNamespace(
            id=1,
            codigo="1",
            telefone="67999991111",
            celular=None,
            auth_user_id=None,
            tipo_cadastro="cliente",
            is_entregador=False,
            merged_into_id=None,
            cpf="12345678901",
            email=None,
            ativo=True,
            nome="Ana Silva",
        ),
        SimpleNamespace(
            id=2,
            codigo="2",
            telefone=None,
            celular="(67) 99999-1111",
            auth_user_id=None,
            tipo_cadastro="cliente",
            is_entregador=False,
            merged_into_id=None,
            cpf="12345678901",
            email=None,
            ativo=True,
            nome="Ana Silva",
        ),
    ]
    db = MagicMock()

    def query_for(model):
        query = MagicMock()
        query.filter.return_value = query
        query.first.return_value = None
        query.all.return_value = people if model is Cliente else []
        return query

    def add(item):
        if isinstance(item, User):
            item.id = 99

    db.query.side_effect = query_for
    db.add.side_effect = add
    merges = []
    monkeypatch.setattr(
        ecommerce_auth_public, "sync_rls_auth_email", lambda *args: None
    )
    monkeypatch.setattr(
        ecommerce_auth_public, "_existing_user_for_phone", lambda *args: None
    )
    monkeypatch.setattr(
        ecommerce_auth_public,
        "executar_fusao_pessoas",
        lambda *args, **kwargs: merges.append(kwargs),
    )
    monkeypatch.setattr(
        ecommerce_auth_public, "_ensure_active_store_access", lambda *args: None
    )
    monkeypatch.setattr(
        ecommerce_auth_public, "register_account_created", lambda *args: None
    )
    monkeypatch.setattr(
        ecommerce_auth_public, "_send_email_verification", lambda *args: True
    )
    monkeypatch.setattr(
        ecommerce_auth_public,
        "_create_ecommerce_session_tokens",
        lambda *args: {"access_token": "ok"},
    )
    monkeypatch.setattr(
        ecommerce_auth_public, "_serialize_profile", lambda *args: {"id": 99}
    )
    tenant_id = uuid4()
    request = Request(
        {
            "type": "http",
            "headers": [(b"x-tenant-id", str(tenant_id).encode())],
        }
    )

    response = registrar_cliente(
        EcommerceRegisterRequest(
            email="ana.app@example.com",
            password="SenhaForte456",
            nome="Ana Silva",
            telefone="+55 (67) 99999-1111",
            cpf="12345678901",
            accepted_terms=True,
            accepted_privacy=True,
        ),
        request,
        db,
    )

    assert response["user"]["id"] == 99
    assert people[0].auth_user_id == 99
    assert len(merges) == 1
    assert merges[0]["principal_id"] == 1
    assert merges[0]["duplicado_id"] == 2


def test_exclusao_erp_recusa_proprio_acesso():
    with pytest.raises(HTTPException) as error:
        excluir_usuario.__wrapped__(
            user_id=7,
            payload=UserDelete(confirmacao="EXCLUIR"),
            db=MagicMock(),
            user_and_tenant=(SimpleNamespace(id=7), uuid4()),
        )
    assert error.value.status_code == 400


def test_app_aceita_celular_do_usuario_criado_no_erp(monkeypatch):
    db = _session()
    tenant_id = uuid4()
    set_tenant_context(tenant_id)
    db.add(
        Tenant(
            id=str(tenant_id),
            name="Loja Teste",
            name_normalized="loja teste",
            ecommerce_slug="loja-teste",
            status="active",
            plan="pet-start",
        )
    )
    role = Role(tenant_id=tenant_id, name="Administrador")
    db.add(role)
    db.commit()
    user, _ = create_tenant_user_account(
        db,
        tenant_id=tenant_id,
        username=None,
        email=None,
        login_phone="67999991111",
        password="SenhaForte123",
        role_id=role.id,
    )
    db.commit()
    monkeypatch.setattr(
        "app.routes.ecommerce_auth_public.register_successful_login", lambda *args: None
    )
    monkeypatch.setattr(
        "app.routes.ecommerce_auth_public._create_ecommerce_session_tokens",
        lambda *args: {"access_token": "ok"},
    )
    monkeypatch.setattr(
        "app.routes.ecommerce_auth_public._get_or_create_cliente_for_user",
        lambda *args: SimpleNamespace(id=1),
    )
    monkeypatch.setattr(
        "app.routes.ecommerce_auth_public._serialize_profile",
        lambda target, *args: {"id": target.id},
    )
    request = Request(
        {
            "type": "http",
            "headers": [(b"x-tenant-id", str(tenant_id).encode("ascii"))],
        }
    )

    response = login_cliente(
        EcommerceLoginRequest(
            identifier="+55 (67) 99999-1111", password="SenhaForte123"
        ),
        request,
        db,
    )
    assert response["user"]["id"] == user.id


def test_login_por_celular_reutiliza_conta_criada_no_ecommerce(monkeypatch):
    db = _session()
    tenant_id = uuid4()
    set_tenant_context(tenant_id)
    db.add(
        Tenant(
            id=str(tenant_id),
            name="Loja Teste",
            name_normalized="loja teste",
            ecommerce_slug="loja-teste",
            status="active",
            plan="pet-start",
        )
    )
    db.add(
        User(
            tenant_id=tenant_id,
            email="ana.antiga@example.com",
            login_phone="67999991111",
            hashed_password=hash_password("SenhaAntiga123"),
            is_active=False,
        )
    )
    user = User(
        tenant_id=tenant_id,
        email="ana@example.com",
        telefone="+55 (67) 99999-1111",
        hashed_password=hash_password("SenhaForte123"),
        is_active=True,
        email_verified=True,
    )
    db.add(user)
    db.commit()
    monkeypatch.setattr(
        ecommerce_auth_public, "_ensure_active_store_access", lambda *args: None
    )
    monkeypatch.setattr(
        ecommerce_auth_public, "register_successful_login", lambda *args: None
    )
    monkeypatch.setattr(
        ecommerce_auth_public,
        "_create_ecommerce_session_tokens",
        lambda *args: {"access_token": "ok"},
    )
    monkeypatch.setattr(
        ecommerce_auth_public,
        "_get_or_create_cliente_for_user",
        lambda *args: SimpleNamespace(id=1),
    )
    monkeypatch.setattr(
        ecommerce_auth_public,
        "_serialize_profile",
        lambda target, *args: {"id": target.id},
    )
    request = Request(
        {
            "type": "http",
            "headers": [(b"x-tenant-id", str(tenant_id).encode("ascii"))],
        }
    )

    response = login_cliente(
        EcommerceLoginRequest(identifier="(67) 99999-1111", password="SenhaForte123"),
        request,
        db,
    )
    assert response["user"]["id"] == user.id


def test_app_nao_reativa_acesso_desativado_no_erp():
    db = _session()
    tenant_id = uuid4()
    set_tenant_context(tenant_id)
    db.add(
        Tenant(
            id=str(tenant_id),
            name="Loja Teste",
            name_normalized="loja teste",
            ecommerce_slug="loja-teste",
            status="active",
            plan="pet-start",
        )
    )
    role = Role(tenant_id=tenant_id, name="Administrador")
    db.add(role)
    db.commit()
    user, _ = create_tenant_user_account(
        db,
        tenant_id=tenant_id,
        username=None,
        email=None,
        login_phone="67999991111",
        password="SenhaForte123",
        role_id=role.id,
    )
    vinculo = db.query(UserTenant).filter(UserTenant.user_id == user.id).one()
    vinculo.is_active = False
    db.commit()

    with pytest.raises(HTTPException) as error:
        _ensure_active_store_access(db, user, str(tenant_id))
    assert error.value.status_code == 403
    assert vinculo.is_active is False
    assert vinculo.role_id == role.id


def test_exclusao_erp_libera_identificadores_e_remove_vinculo(monkeypatch):
    user = SimpleNamespace(id=8, email="ana@example.com", login_phone="67999991111")
    vinculo = SimpleNamespace(user_id=8)
    db = MagicMock()

    def query_for(*models):
        query = MagicMock()
        query.join.return_value = query
        query.filter.return_value = query
        if len(models) == 2:
            query.first.return_value = (user, vinculo)
        elif models[0] is UserTenant.id:
            query.first.return_value = None
        else:
            query.all.return_value = []
        return query

    db.query.side_effect = query_for
    tenant_id = uuid4()
    db.execute.return_value.all.return_value = [(tenant_id,)]
    monkeypatch.setattr("app.usuarios_routes.log_business_event", lambda **kwargs: None)

    result = excluir_usuario.__wrapped__(
        user_id=8,
        payload=UserDelete(confirmacao="EXCLUIR"),
        db=db,
        user_and_tenant=(SimpleNamespace(id=7), tenant_id),
    )

    assert result["status"] == "ok"
    assert user.login_phone is None
    assert user.email.endswith("@deleted.corepet.invalid")
    assert user.is_active is False
    db.delete.assert_called_once_with(vinculo)
    db.commit.assert_called_once()


def test_exclusao_erp_preserva_conta_vinculada_a_outra_loja():
    tenant_id = uuid4()
    user = SimpleNamespace(id=8, email="ana@example.com", login_phone="67999991111")
    db = MagicMock()
    query = MagicMock()
    query.join.return_value = query
    query.filter.return_value = query
    query.first.return_value = (user, SimpleNamespace(user_id=8))
    db.query.return_value = query
    db.execute.return_value.all.return_value = [(tenant_id,), (uuid4(),)]

    with pytest.raises(HTTPException) as error:
        excluir_usuario.__wrapped__(
            user_id=8,
            payload=UserDelete(confirmacao="EXCLUIR"),
            db=db,
            user_and_tenant=(SimpleNamespace(id=7), tenant_id),
        )

    assert error.value.status_code == 409
    assert user.email == "ana@example.com"
    db.delete.assert_not_called()
