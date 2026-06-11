import inspect

from app.auth.dependencies import get_current_user_and_tenant
from app import dre_ia_routes


def _depends_on_dependency(func, dependency, param_name: str = "current_user") -> bool:
    default = inspect.signature(func).parameters[param_name].default
    return getattr(default, "dependency", None) is dependency


def test_dre_tenant_wrapper_uses_current_user_and_tenant():
    assert _depends_on_dependency(
        dre_ia_routes._usuario_dre,
        get_current_user_and_tenant,
        "user_tenant",
    )


def test_dre_routes_that_query_tenant_models_use_tenant_wrapper():
    for func in (
        dre_ia_routes.obter_indices_mercado,
        dre_ia_routes.listar_setores,
        dre_ia_routes.calcular_dre_detalhado,
        dre_ia_routes.calcular_dre_consolidado,
        dre_ia_routes.alocar_despesa,
    ):
        assert _depends_on_dependency(func, dre_ia_routes._usuario_dre), func.__name__
