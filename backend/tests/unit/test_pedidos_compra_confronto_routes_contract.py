from pathlib import Path


EXPECTED_CONFRONTO_PATHS = {
    "/{pedido_id}/notas-candidatas",
    "/{pedido_id}/vincular-nota/{nota_id}",
    "/{pedido_id}/confronto",
    "/{pedido_id}/confronto/csv",
    "/{pedido_id}/confronto/pdf",
    "/{pedido_id}/confronto/email-texto",
    "/{pedido_id}/finalizar-confronto",
    "/{pedido_id}/sugerir-pedido-complementar",
}
EXPECTED_PEDIDOS_COMPRA_CONFRONTO_PATHS = {
    f"/pedidos-compra{path}" for path in EXPECTED_CONFRONTO_PATHS
}


def _route_paths(router):
    return {getattr(route, "path", None) for route in router.routes}


def test_pedidos_compra_confronto_routes_ficam_em_subrouter_dedicado():
    from app.pedidos_compra.confronto_routes import router

    assert EXPECTED_CONFRONTO_PATHS.issubset(_route_paths(router))


def test_pedidos_compra_router_inclui_confronto_sem_mudar_paths():
    from app.pedidos_compra_routes import router

    assert EXPECTED_PEDIDOS_COMPRA_CONFRONTO_PATHS.issubset(_route_paths(router))


def test_pedidos_compra_confronto_fica_dividido_em_modulos_focados():
    from app import pedidos_compra_routes
    from app.pedidos_compra import confronto_calculo
    from app.pedidos_compra import confronto_exportacao
    from app.pedidos_compra import confronto_vinculos
    from app.pedidos_compra import confronto_routes

    assert (
        pedidos_compra_routes._realizar_confronto
        is confronto_calculo._realizar_confronto
    )
    assert confronto_routes._realizar_confronto is confronto_calculo._realizar_confronto
    assert confronto_routes._carregar_confronto_exportacao is (
        confronto_exportacao._carregar_confronto_exportacao
    )
    assert confronto_routes._obter_notas_vinculadas is (
        confronto_vinculos._obter_notas_vinculadas
    )


def test_pedidos_compra_confronto_modulos_ficam_abaixo_de_700_linhas():
    backend_root = Path(__file__).resolve().parents[2]
    limites = {
        "app/pedidos_compra/confronto_routes.py": 700,
        "app/pedidos_compra/confronto_calculo.py": 700,
        "app/pedidos_compra/confronto_exportacao.py": 700,
        "app/pedidos_compra/confronto_vinculos.py": 700,
    }

    for rel_path, limite in limites.items():
        path = backend_root / rel_path
        linhas = path.read_text(encoding="utf-8").splitlines()
        assert len(linhas) <= limite, f"{rel_path} tem {len(linhas)} linhas"
