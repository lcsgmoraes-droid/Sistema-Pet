import asyncio
import inspect
from types import SimpleNamespace
from uuid import uuid4

from app.security.jwt_compat import jwt

from app.auth.core import ALGORITHM
from app.api.endpoints.rotas_entrega import (
    DeliveryActor,
    _activate_delivery_actor_tenant,
    _rota_filters_for_actor,
    _validate_ecommerce_entregador_actor,
)
from app.config import JWT_SECRET_KEY
from app.routes.ecommerce_auth import (
    _extract_tenant_id_from_request,
    _get_current_ecommerce_user,
    _get_or_create_cliente_for_user,
    _select_preferred_cliente,
    _serialize_profile,
    _transfer_cliente_relations_for_ecommerce_merge,
    atualizar_perfil,
)
from app.routes import app_mobile_routes
from app.routes.ecommerce_cart import (
    _activate_cart_tenant_context,
    _current_identity as cart_current_identity,
)
from app.routes.ecommerce_checkout import (
    _activate_checkout_tenant_context,
    _current_identity as checkout_current_identity,
    finalizar_checkout,
)
from app.routes.ecommerce_entregador import _get_entregador_cliente
from app.routes.ecommerce_entregador import obter_rota_entregador
from app.routes.ecommerce_notify_routes import _resolve_notify_tenant
from app.routes.ecommerce_public import _get_active_tenant
from app.security.module_access import require_active_module
from app.tenancy.context import clear_current_tenant, get_current_tenant


class _Query:
    def __init__(self, result):
        self.result = result

    def filter(self, *_args, **_kwargs):
        return self

    def order_by(self, *_args, **_kwargs):
        return self

    def first(self):
        return self.result

    def all(self):
        if self.result is None:
            return []
        if isinstance(self.result, list):
            return self.result
        return [self.result]


class _Db:
    def __init__(self, *results):
        self.results = list(results)

    def query(self, *_args, **_kwargs):
        return _Query(self.results.pop(0))


class _TransferQuery:
    def __init__(self, db, model):
        self.db = db
        self.model_name = getattr(model, "__name__", str(model))

    def filter(self, *_args, **_kwargs):
        return self

    def update(self, values, synchronize_session=False):
        self.db.updated_models.append(
            {
                "model": self.model_name,
                "values": values,
                "synchronize_session": synchronize_session,
            }
        )
        return 1


class _TransferDb:
    def __init__(self):
        self.updated_models = []
        self.flushed = False
        self.expired = []

    def query(self, model):
        return _TransferQuery(self, model)

    def flush(self):
        self.flushed = True

    def expire(self, obj, relationship_names):
        self.expired.append((obj, relationship_names))


class _UnorderedFirstQuery:
    def __init__(self, unordered_first, ordered_results):
        self.unordered_first = unordered_first
        self.ordered_results = ordered_results
        self.ordered = False

    def filter(self, *_args, **_kwargs):
        return self

    def order_by(self, *_args, **_kwargs):
        self.ordered = True
        return self

    def first(self):
        return self.unordered_first

    def all(self):
        return self.ordered_results if self.ordered else [self.unordered_first]


class _UnorderedFirstDb:
    def __init__(self, unordered_first, ordered_results):
        self.unordered_first = unordered_first
        self.ordered_results = ordered_results

    def query(self, *_args, **_kwargs):
        return _UnorderedFirstQuery(self.unordered_first, self.ordered_results)


def _token(user_id: int, tenant_id) -> str:
    return jwt.encode(
        {
            "sub": str(user_id),
            "tenant_id": str(tenant_id),
            "token_type": "ecommerce_customer",
        },
        JWT_SECRET_KEY,
        algorithm=ALGORITHM,
    )


def test_extract_tenant_id_from_request_sets_tenant_context():
    tenant_id = uuid4()
    clear_current_tenant()

    request = SimpleNamespace(headers={"X-Tenant-ID": str(tenant_id)})

    assert _extract_tenant_id_from_request(request) == tenant_id
    assert get_current_tenant() == tenant_id


def test_get_current_ecommerce_user_sets_tenant_context_from_token():
    tenant_id = uuid4()
    user = SimpleNamespace(id=123, tenant_id=tenant_id, is_active=True)
    user_tenant = SimpleNamespace(user_id=user.id, tenant_id=tenant_id, is_active=True)
    tenant = SimpleNamespace(id=tenant_id, status="active")
    credentials = SimpleNamespace(credentials=_token(user.id, tenant_id))
    clear_current_tenant()

    current_user = _get_current_ecommerce_user(
        credentials=credentials, db=_Db(user, user_tenant, tenant)
    )

    assert current_user is user
    assert get_current_tenant() == tenant_id


def test_cart_and_checkout_identity_use_validated_ecommerce_user():
    tenant_id = uuid4()
    user = SimpleNamespace(id=123, tenant_id=tenant_id, is_active=True)
    clear_current_tenant()

    cart_identity = cart_current_identity(current_user=user)

    assert get_current_tenant() == tenant_id
    clear_current_tenant()

    checkout_identity = checkout_current_identity(current_user=user)

    assert get_current_tenant() == tenant_id
    assert cart_identity.user_id == user.id
    assert cart_identity.tenant_id == str(tenant_id)
    assert checkout_identity.user_id == user.id
    assert checkout_identity.tenant_id == str(tenant_id)


def test_cart_routes_can_reactivate_tenant_context_from_identity():
    tenant_id = uuid4()
    identity = SimpleNamespace(user_id=123, tenant_id=str(tenant_id))
    clear_current_tenant()

    resolved_tenant = _activate_cart_tenant_context(identity)

    assert resolved_tenant == str(tenant_id)
    assert get_current_tenant() == tenant_id


def test_checkout_routes_can_reactivate_tenant_context_from_identity():
    tenant_id = uuid4()
    identity = SimpleNamespace(user_id=123, tenant_id=str(tenant_id))
    clear_current_tenant()

    resolved_tenant = _activate_checkout_tenant_context(identity)

    assert resolved_tenant == str(tenant_id)
    assert get_current_tenant() == tenant_id


def test_checkout_finalizar_reactivates_tenant_before_gateway_lookup():
    source = inspect.getsource(finalizar_checkout)

    assert source.index("_activate_checkout_tenant_context(identity)") < source.index(
        "get_active_mercado_pago_runtime_config"
    )


def test_app_mobile_rastreio_entrega_sql_cru_filtra_gps_por_tenant():
    source = " ".join(inspect.getsource(app_mobile_routes.rastreio_entrega).split())

    assert "FROM rotas_entrega WHERE id = :rid AND tenant_id = :tenant" in source
    assert "FROM rotas_entrega_paradas" in source
    assert "WHERE id = :pid AND tenant_id = :tenant" in source
    assert '{"rid": rota.id, "tenant": tenant_id}' in source
    assert '{"pid": p.id, "tenant": tenant_id}' in source


def test_get_entregador_cliente_uses_validated_ecommerce_user_context():
    tenant_id = uuid4()
    user = SimpleNamespace(id=123, tenant_id=tenant_id, is_active=True)
    cliente = SimpleNamespace(
        id=456, tenant_id=str(tenant_id), user_id=user.id, is_entregador=True
    )
    clear_current_tenant()

    entregador = _get_entregador_cliente(current_user=user, db=_Db(cliente))

    assert entregador is cliente
    assert get_current_tenant() == tenant_id


def test_obter_rota_entregador_validates_driver_before_delegating(monkeypatch):
    tenant_id = uuid4()
    cliente = SimpleNamespace(
        id=456, tenant_id=str(tenant_id), user_id=123, is_entregador=True
    )
    rota = SimpleNamespace(id=789, tenant_id=str(tenant_id), entregador_id=cliente.id)
    delegated = {}
    clear_current_tenant()

    from app.api.endpoints import rotas_entrega as rotas_admin

    def fake_obter_rota(*, rota_id, db, actor):
        delegated["args"] = {
            "rota_id": rota_id,
            "db": db,
            "actor": actor,
        }
        return rota

    monkeypatch.setattr(rotas_admin, "obter_rota", fake_obter_rota)

    db = _Db(rota)
    result = obter_rota_entregador(rota_id=rota.id, cliente=cliente, db=db)

    assert result is rota
    assert delegated["args"]["rota_id"] == rota.id
    assert delegated["args"]["db"] is db
    assert delegated["args"]["actor"].user.id == cliente.user_id
    assert delegated["args"]["actor"].tenant_id == tenant_id
    assert delegated["args"]["actor"].entregador is cliente
    assert get_current_tenant() == tenant_id


def test_get_or_create_cliente_for_user_sets_tenant_context_before_query():
    tenant_id = uuid4()
    user = SimpleNamespace(
        id=123,
        tenant_id=tenant_id,
        is_active=True,
        cpf_cnpj=None,
        email="cliente@example.com",
        telefone=None,
        nome="Cliente Teste",
    )
    cliente = SimpleNamespace(
        id=456,
        tenant_id=str(tenant_id),
        user_id=user.id,
        cpf=None,
        email=user.email,
        telefone=None,
        nome=user.nome,
    )
    clear_current_tenant()

    result = _get_or_create_cliente_for_user(_Db([cliente], []), user)

    assert result is cliente
    assert get_current_tenant() == tenant_id


def test_get_or_create_cliente_for_user_prefers_operational_profile_by_email():
    tenant_id = uuid4()
    user = SimpleNamespace(
        id=123,
        tenant_id=tenant_id,
        is_active=True,
        cpf_cnpj="40888076851",
        email="funcionario@example.com",
        telefone="18996691730",
        nome="Funcionario Teste",
    )
    cliente_vinculado = SimpleNamespace(
        id=456,
        tenant_id=str(tenant_id),
        user_id=user.id,
        cpf=user.cpf_cnpj,
        email=user.email,
        telefone=user.telefone,
        nome="Cliente Teste",
        tipo_cadastro="cliente",
        ativo=True,
        is_entregador=False,
    )
    funcionario_por_email = SimpleNamespace(
        id=789,
        tenant_id=str(tenant_id),
        user_id=999,
        cpf=None,
        email=user.email,
        telefone=None,
        nome="Funcionario Teste",
        tipo_cadastro="funcionario",
        ativo=True,
        is_entregador=False,
    )
    clear_current_tenant()

    result = _get_or_create_cliente_for_user(
        _Db([cliente_vinculado], [funcionario_por_email]), user
    )

    assert result is funcionario_por_email
    assert funcionario_por_email.user_id == user.id
    assert get_current_tenant() == tenant_id


def test_get_or_create_cliente_for_user_prefers_active_linked_customer():
    tenant_id = uuid4()
    user = SimpleNamespace(
        id=123,
        tenant_id=tenant_id,
        is_active=True,
        cpf_cnpj="23068780802",
        email="cliente@example.com",
        telefone="18996691730",
        nome="Cliente Teste",
    )
    inactive_duplicate = SimpleNamespace(
        id=456,
        tenant_id=str(tenant_id),
        user_id=user.id,
        cpf=user.cpf_cnpj,
        email=user.email,
        telefone=user.telefone,
        nome="Cliente Inativo",
        tipo_cadastro="cliente",
        ativo=False,
        is_entregador=False,
    )
    active_customer = SimpleNamespace(
        id=789,
        tenant_id=str(tenant_id),
        user_id=user.id,
        cpf=user.cpf_cnpj,
        email=user.email,
        telefone=user.telefone,
        nome="Cliente Ativo",
        tipo_cadastro="cliente",
        ativo=True,
        is_entregador=False,
    )
    clear_current_tenant()

    result = _get_or_create_cliente_for_user(
        _Db([inactive_duplicate, active_customer], []), user
    )

    assert result is active_customer
    assert get_current_tenant() == tenant_id


def test_get_or_create_cliente_for_user_reactivates_old_erp_customer_when_all_matches_are_inactive():
    tenant_id = uuid4()
    user = SimpleNamespace(
        id=123,
        tenant_id=tenant_id,
        is_active=True,
        cpf_cnpj="23068780802",
        email="lcsgmoraes@gmail.com",
        telefone="18997401641",
        nome="Lucas Guerra de Moraes",
    )
    erp_customer = SimpleNamespace(
        id=5794,
        codigo="1",
        tenant_id=str(tenant_id),
        user_id=user.id,
        cpf=user.cpf_cnpj,
        email=user.email,
        telefone=user.telefone,
        celular=user.telefone,
        nome="Lucas Guerra de Moraes",
        tipo_cadastro="cliente",
        ativo=False,
        is_entregador=False,
        created_at=None,
    )
    ecommerce_duplicate = SimpleNamespace(
        id=10000,
        codigo="10163",
        tenant_id=str(tenant_id),
        user_id=user.id,
        cpf=user.cpf_cnpj,
        email=user.email,
        telefone=user.telefone,
        celular=None,
        nome="Lucas",
        tipo_cadastro="cliente",
        ativo=False,
        is_entregador=False,
        created_at=None,
    )
    clear_current_tenant()

    result = _get_or_create_cliente_for_user(
        _Db([ecommerce_duplicate, erp_customer], []), user
    )

    assert result is erp_customer
    assert erp_customer.ativo is True
    assert ecommerce_duplicate.ativo is False
    assert get_current_tenant() == tenant_id


def test_select_preferred_cliente_prefers_erp_code_over_newer_ecommerce_duplicate():
    tenant_id = uuid4()
    erp_customer = SimpleNamespace(
        id=5794,
        codigo="1",
        tenant_id=str(tenant_id),
        cpf="23068780802",
        email="lcsgmoraes@gmail.com",
        telefone=None,
        celular="18997401641",
        tipo_cadastro="cliente",
        ativo=False,
        is_entregador=False,
    )
    ecommerce_duplicate = SimpleNamespace(
        id=10000,
        codigo="10163",
        tenant_id=str(tenant_id),
        cpf="23068780802",
        email="lcsgmoraes@gmail.com",
        telefone="18997401641",
        celular=None,
        tipo_cadastro="cliente",
        ativo=True,
        is_entregador=False,
    )

    result = _select_preferred_cliente(
        [ecommerce_duplicate, erp_customer],
        email="lcsgmoraes@gmail.com",
        cpf="230.687.808-02",
        telefone="(18) 99740-1641",
    )

    assert result is erp_customer


def test_ecommerce_profile_merge_transfers_customer_relations_before_detaching_duplicate():
    source = inspect.getsource(_transfer_cliente_relations_for_ecommerce_merge)

    assert "transferir_referencias_pessoa" in source
    assert "transferidos_genericos" in source
    assert "db.expire(previous_cliente" in source
    assert "getattr(previous_cliente, relationship_name" not in source


def test_atualizar_perfil_detaches_duplicate_customer_instead_of_deleting_history():
    source = inspect.getsource(atualizar_perfil)

    assert "_transfer_cliente_relations_for_ecommerce_merge" in source
    assert "previous_cliente.ativo = False" in source
    assert "db.delete(previous_cliente)" not in source


def test_ecommerce_profile_merge_uses_generic_reference_transfer_before_detaching_duplicate(
    monkeypatch,
):
    calls = {}

    def fake_transferir_referencias_pessoa(
        db, *, tenant_id, principal_id, duplicado_id
    ):
        calls["args"] = {
            "db": db,
            "tenant_id": tenant_id,
            "principal_id": principal_id,
            "duplicado_id": duplicado_id,
        }
        return {
            "transferidos_especiais": {"produto_fornecedores": 1},
            "transferidos_genericos": [
                {"tabela": "vendas", "campo": "cliente_id", "total": 2},
                {"tabela": "campaign_coupons", "campo": "customer_id", "total": 3},
            ],
        }

    monkeypatch.setattr(
        "app.routes.ecommerce_auth.transferir_referencias_pessoa",
        fake_transferir_referencias_pessoa,
    )
    db = _TransferDb()
    previous_cliente = SimpleNamespace(id=10, tenant_id="tenant-1")
    target_cliente = SimpleNamespace(id=20, tenant_id="tenant-1")

    transferred = _transfer_cliente_relations_for_ecommerce_merge(
        db,
        previous_cliente,
        target_cliente,
    )

    assert calls["args"]["tenant_id"] == "tenant-1"
    assert calls["args"]["principal_id"] == target_cliente.id
    assert calls["args"]["duplicado_id"] == previous_cliente.id
    assert db.flushed is True
    assert transferred == 6


def test_app_mobile_cliente_helper_uses_profile_resolution_for_duplicate_customer_rows(
    monkeypatch,
):
    tenant_id = uuid4()
    user = SimpleNamespace(
        id=123,
        tenant_id=tenant_id,
        is_active=True,
        cpf_cnpj="23068780802",
        email="cliente@example.com",
        telefone=None,
        nome="Lucas Guerra de Moraes",
    )
    cliente_ativo = SimpleNamespace(
        id=456,
        tenant_id=str(tenant_id),
        user_id=user.id,
        cpf=user.cpf_cnpj,
        email=user.email,
        telefone=None,
        nome=user.nome,
        tipo_cadastro="cliente",
        ativo=True,
        is_entregador=False,
    )
    cliente_inativo = SimpleNamespace(
        id=789,
        tenant_id=str(tenant_id),
        user_id=user.id,
        cpf=user.cpf_cnpj,
        email=user.email,
        telefone=None,
        nome="Lucas",
        tipo_cadastro="cliente",
        ativo=False,
        is_entregador=False,
    )
    monkeypatch.setattr(
        "app.routes.ecommerce_auth._find_operational_cliente_match",
        lambda *_args, **_kwargs: None,
    )
    clear_current_tenant()

    result = app_mobile_routes._get_cliente_or_404(
        _UnorderedFirstDb(cliente_inativo, [cliente_ativo, cliente_inativo]),
        user,
    )

    assert result is cliente_ativo
    assert get_current_tenant() == tenant_id


def test_serialize_profile_marks_veterinario_as_mobile_operational_profile():
    user = SimpleNamespace(
        id=123,
        email="vet@example.com",
        email_verified=True,
        nome="Dra Teste",
        telefone=None,
        cpf_cnpj=None,
    )
    cliente = SimpleNamespace(
        id=456,
        tipo_cadastro="veterinario",
        ativo=True,
        is_entregador=True,
        telefone=None,
        cpf=None,
        cep=None,
        endereco=None,
        numero=None,
        complemento=None,
        bairro=None,
        cidade=None,
        estado=None,
        endereco_entrega=None,
        enderecos_adicionais=None,
    )

    profile = _serialize_profile(user, cliente)

    assert profile["is_veterinario"] is True
    assert profile["veterinario_id"] == cliente.id
    assert profile["perfil_operacional"] == "veterinario"


def test_get_active_public_tenant_sets_tenant_context():
    tenant_id = uuid4()
    tenant = SimpleNamespace(id=tenant_id, status="active")
    clear_current_tenant()

    active_tenant = _get_active_tenant(_Db(tenant), ("id", str(tenant_id)))

    assert active_tenant is tenant
    assert get_current_tenant() == tenant_id


def test_notify_tenant_resolver_accepts_slug_without_uuid_query_error():
    tenant_id = uuid4()
    tenant = SimpleNamespace(id=tenant_id, status="active", ecommerce_slug="loja-teste")

    resolved = _resolve_notify_tenant(_Db(tenant), "loja-teste")

    assert resolved is tenant


def test_delivery_module_gate_allows_ecommerce_customer_token_without_admin_jti():
    tenant_id = uuid4()
    credentials = SimpleNamespace(credentials=_token(123, tenant_id))
    dependency = require_active_module("entregas", allow_ecommerce_customer=True)

    asyncio.run(dependency(credentials=credentials, db=object()))


def test_delivery_actor_ecommerce_token_sets_tenant_context():
    tenant_id = uuid4()
    user = SimpleNamespace(id=123, tenant_id=tenant_id, is_active=True)
    user_tenant = SimpleNamespace(user_id=user.id, tenant_id=tenant_id, is_active=True)
    tenant = SimpleNamespace(id=tenant_id, status="active")
    cliente = SimpleNamespace(
        id=456, tenant_id=str(tenant_id), user_id=user.id, is_entregador=True
    )
    credentials = SimpleNamespace(credentials=_token(user.id, tenant_id))
    clear_current_tenant()

    actor = _validate_ecommerce_entregador_actor(
        credentials=credentials,
        db=_Db(user, user_tenant, tenant, cliente),
    )

    assert actor.user is user
    assert actor.tenant_id == tenant_id
    assert actor.entregador is cliente
    assert get_current_tenant() == tenant_id


def test_delivery_route_helpers_reactivate_tenant_context_from_actor():
    tenant_id = uuid4()
    actor = DeliveryActor(
        user=SimpleNamespace(id=123), tenant_id=tenant_id, entregador=None
    )
    clear_current_tenant()

    assert _activate_delivery_actor_tenant(actor) == tenant_id
    assert get_current_tenant() == tenant_id

    clear_current_tenant()
    filters = _rota_filters_for_actor(actor, 202)

    assert filters
    assert get_current_tenant() == tenant_id
