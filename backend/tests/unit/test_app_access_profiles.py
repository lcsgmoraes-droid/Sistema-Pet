from pathlib import Path
from types import SimpleNamespace
import importlib.util


BACKEND_ROOT = Path(__file__).resolve().parents[2]


def read_backend(path: str) -> str:
    return (BACKEND_ROOT / path).read_text(encoding="utf-8")


def load_service_module():
    service_path = BACKEND_ROOT / "app/services/app_access_profile_service.py"
    assert service_path.exists()
    spec = importlib.util.spec_from_file_location(
        "app_access_profile_service_contract", service_path
    )
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


def cliente(**kwargs):
    defaults = {
        "id": 10,
        "nome": "Pessoa Teste",
        "tipo_cadastro": "cliente",
        "ativo": True,
        "is_entregador": False,
        "entregador_ativo": True,
    }
    defaults.update(kwargs)
    return SimpleNamespace(**defaults)


def grant(**kwargs):
    pessoa = kwargs.pop("cliente", cliente(id=99))
    defaults = {
        "profile_type": "cliente",
        "cliente_id": pessoa.id,
        "cliente": pessoa,
        "is_active": True,
    }
    defaults.update(kwargs)
    return SimpleNamespace(**defaults)


def test_app_access_profile_model_and_migration_exist():
    models = read_backend("app/models.py") + read_backend("app/models_authz.py")
    migration = read_backend("alembic/versions/sv20260613a1_app_access_profiles.py")

    assert "class AppAccessProfile" in models
    assert (
        "__tablename__ = 'app_access_profiles'" in models
        or '__tablename__ = "app_access_profiles"' in models
    )
    assert "app_access_profiles" in migration
    assert "profile_type" in migration


def test_app_access_service_derives_and_selects_multiple_profiles():
    service = load_service_module()
    user = SimpleNamespace(id=29, email="william@example.com")
    cliente_app = cliente(id=9900, nome="William", tipo_cadastro="cliente")
    funcionario = cliente(
        id=10467,
        nome="William",
        tipo_cadastro="funcionario",
        is_entregador=True,
    )
    explicit_vet = grant(profile_type="veterinario", cliente=funcionario)

    profiles = service.build_available_profiles_for_clientes(
        user,
        [cliente_app, funcionario],
        explicit_grants=[explicit_vet],
    )

    assert [profile["type"] for profile in profiles] == [
        "cliente",
        "funcionario",
        "entregador",
        "veterinario",
    ]

    selected = service.apply_selected_profile_flags(
        {"id": user.id, "email": user.email},
        profiles,
        "entregador",
    )

    assert selected["perfil_operacional"] == "entregador"
    assert selected["is_entregador"] is True
    assert selected["is_funcionario"] is False
    assert selected["is_veterinario"] is False
    assert selected["funcionario_id"] == funcionario.id


def test_ecommerce_auth_exposes_available_profiles_and_select_profile_endpoint():
    source = read_backend("app/routes/ecommerce_auth_profiles.py")

    assert "available_profiles" in source
    assert "selected_profile" in source
    assert '@router.post("/select-profile")' in source


def test_ecommerce_profile_reload_uses_active_profile_from_token_contract():
    source = read_backend("app/routes/ecommerce_auth_profiles.py")

    assert "_active_app_profile" in source
    assert 'selected_profile=getattr(current_user, "_active_app_profile"' in source


def test_operational_app_gates_use_app_access_profile_service():
    mobile_routes = read_backend("app/routes/app_mobile_routes.py")
    mobile_pdv_routes = read_backend("app/routes/app_mobile_funcionario_pdv_routes.py")
    mobile_pdv_auth = read_backend("app/routes/app_mobile_funcionario_pdv/auth.py")
    vet_routes = read_backend("app/routes/app_vet_routes.py")
    delivery_routes = read_backend("app/api/endpoints/rotas_entrega_auth.py")

    assert (
        "get_cliente_for_app_profile_or_none"
        in mobile_routes + mobile_pdv_routes + mobile_pdv_auth
    )
    assert "get_cliente_for_app_profile_or_none" in vet_routes
    assert "get_cliente_for_app_profile_or_none" in delivery_routes
