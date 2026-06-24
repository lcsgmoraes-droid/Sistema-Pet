from pathlib import Path


BACKEND_ROOT = Path(__file__).resolve().parents[2]

EXPECTED_HELPERS = (
    "_montar_payload_pedido",
    "_normalizar_canal",
    "_normalizar_item_payload",
    "_payload_principal",
    "_pedido_tem_nf_deterministica",
    "_resolver_canal_pedido",
    "_resumir_ultima_nf_do_pedido_bling",
    "_resumir_ultima_nf_webhook",
    "_serializar_itens_pedido",
    "_serializar_pedido_bling",
    "_situacao_codigo_bling",
    "_ultima_nf_payload_efetiva",
)

EXPECTED_ROUTES = {
    ("GET", "/integracoes/bling/pedidos"),
    ("POST", "/integracoes/bling/pedidos/reconciliar-status"),
    ("POST", "/integracoes/bling/pedidos/reconciliar-duplicidades"),
    ("POST", "/integracoes/bling/pedidos/{pedido_id}/consolidar-duplicidade"),
    ("POST", "/integracoes/bling/pedidos/{pedido_id}/reconciliar-fluxo"),
    ("POST", "/integracoes/bling/pedidos/{pedido_id}/confirmar-manual"),
    ("POST", "/integracoes/bling/pedidos/{pedido_id}/cancelar"),
    ("POST", "/integracoes/bling/pedidos/reprocessar-sem-itens"),
    ("POST", "/integracoes/bling/pedido"),
}


def _method_paths(router):
    paths = set()
    for route in router.routes:
        for method in getattr(route, "methods", set()):
            paths.add((method, getattr(route, "path", None)))
    return paths


def test_payload_helpers_ficam_em_modulo_dedicado_com_reexports_legados():
    from app import integracao_bling_pedido_payload
    from app import integracao_bling_pedido_routes

    for name in EXPECTED_HELPERS:
        assert getattr(integracao_bling_pedido_routes, name) is getattr(
            integracao_bling_pedido_payload, name
        )


def test_integracao_bling_pedido_routes_preserva_paths_publicos():
    from app.integracao_bling_pedido_routes import router

    assert EXPECTED_ROUTES.issubset(_method_paths(router))


def test_integracao_bling_pedido_routes_mantem_corte_grande():
    routes_source = (BACKEND_ROOT / "app/integracao_bling_pedido_routes.py").read_text(
        encoding="utf-8"
    )
    payload_source = (
        BACKEND_ROOT / "app/integracao_bling_pedido_payload.py"
    ).read_text(encoding="utf-8")

    assert "def _serializar_pedido_bling(" not in routes_source
    assert "def _resolver_canal_pedido(" not in routes_source
    assert len(routes_source.splitlines()) < 1800
    assert len(payload_source.splitlines()) < 700
