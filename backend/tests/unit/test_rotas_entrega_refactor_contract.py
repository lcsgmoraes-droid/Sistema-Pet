from pathlib import Path

from app.api.endpoints import rotas_entrega
from app.api.endpoints import rotas_entrega_auth
from app.api.endpoints import rotas_entrega_schema
from app.api.endpoints import rotas_entrega_tracking


BACKEND_DIR = Path(__file__).resolve().parents[2]


def _line_count(*parts: str) -> int:
    return len((BACKEND_DIR / Path(*parts)).read_text(encoding="utf-8").splitlines())


def test_rotas_entrega_preserva_reexports_operacionais() -> None:
    assert rotas_entrega.DeliveryActor is rotas_entrega_auth.DeliveryActor
    assert (
        rotas_entrega._validate_ecommerce_entregador_actor
        is rotas_entrega_auth._validate_ecommerce_entregador_actor
    )
    assert (
        rotas_entrega._activate_delivery_actor_tenant
        is rotas_entrega_auth._activate_delivery_actor_tenant
    )
    assert (
        rotas_entrega._rota_filters_for_actor
        is rotas_entrega_auth._rota_filters_for_actor
    )
    assert (
        rotas_entrega.ensure_rotas_entrega_schema
        is rotas_entrega_schema.ensure_rotas_entrega_schema
    )
    assert (
        rotas_entrega._sincronizar_venda_entregue_por_parada
        is rotas_entrega_tracking._sincronizar_venda_entregue_por_parada
    )


def test_rotas_entrega_router_stays_split_across_modules() -> None:
    assert _line_count("app", "api", "endpoints", "rotas_entrega.py") < 1800
    assert _line_count("app", "api", "endpoints", "rotas_entrega_auth.py") >= 120
    assert _line_count("app", "api", "endpoints", "rotas_entrega_tracking.py") >= 250
