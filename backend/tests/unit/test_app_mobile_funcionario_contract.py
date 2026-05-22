from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]
APP_ROOT = REPO_ROOT / "app-mobile/src"


def _source(path: str) -> str:
    return (APP_ROOT / path).read_text(encoding="utf-8")


def test_mobile_routes_funcionario_to_dedicated_navigator():
    source = _source("navigation/AppNavigator.tsx")

    assert "FuncionarioNavigator" in source
    assert 'perfil_operacional === "funcionario"' in source
    assert "user?.is_funcionario" in source


def test_mobile_auth_cache_preserves_funcionario_role():
    source = _source("store/auth.store.ts")

    assert "is_funcionario" in source
    assert '"funcionario"' in source
    assert "cached?.is_veterinario || cached?.is_entregador || cached?.is_funcionario" in source


def test_mobile_user_type_accepts_funcionario_profile():
    source = _source("types/index.ts")

    assert "is_funcionario?: boolean" in source
    assert '"cliente" | "entregador" | "veterinario" | "funcionario"' in source


def test_funcionario_mobile_files_define_local_pdv_flow():
    assert (APP_ROOT / "navigation/FuncionarioNavigator.tsx").exists()
    assert (APP_ROOT / "types/funcionarioNavigation.ts").exists()
    assert (APP_ROOT / "services/funcionario.service.ts").exists()
    assert (APP_ROOT / "store/funcionarioPdv.store.ts").exists()
    assert (APP_ROOT / "screens/funcionario/FuncionarioConsultaScreen.tsx").exists()
    assert (APP_ROOT / "screens/funcionario/FuncionarioScannerScreen.tsx").exists()
    assert (APP_ROOT / "screens/funcionario/FuncionarioCarrinhoScreen.tsx").exists()


def test_funcionario_pdv_store_does_not_use_ecommerce_cart_endpoints():
    source = _source("store/funcionarioPdv.store.ts")

    assert "ShopService" not in source
    assert "/carrinho" not in source
    assert "adicionarProduto" in source
    assert "atualizarQuantidade" in source
    assert "limpar" in source
