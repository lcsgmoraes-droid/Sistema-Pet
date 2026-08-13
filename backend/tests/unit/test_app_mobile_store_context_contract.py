from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]


def _read(relative_path: str) -> str:
    return (REPO_ROOT / relative_path).read_text(encoding="utf-8")


def test_current_store_is_visible_on_home_and_navigation_headers():
    home = _read("app-mobile/src/screens/HomeScreen.tsx")
    navigator = _read("app-mobile/src/navigation/MainNavigator.tsx")

    assert "<StoreContextBadge />" in home
    assert "<StoreContextBadge compact />" in navigator
    assert "headerRight: StoreHeaderBadge" in navigator


def test_store_switch_clears_cart_and_session_before_tenant():
    source = _read("app-mobile/src/hooks/useStoreSwitch.ts")

    assert "await limparCarrinho()" in source
    assert "limparCarrinhoLocal()" in source
    assert "await logout()" in source
    assert "await limparTenant()" in source


def test_checkout_confirmation_identifies_store_and_address():
    source = _read("app-mobile/src/screens/shop/CartScreen.tsx")

    assert "const lojaLabel = tenant" in source
    assert '"Confirmar compra"' in source
    assert "tenant.nome" in source
    assert "Confirme que esta comprando na loja correta" in source


def test_relative_tenant_logo_is_resolved_against_public_api_host():
    source = _read("app-mobile/src/store/tenant.store.ts")

    assert "resolveTenantAssetUrl" in source
    assert "apiPublicBaseUrl()" in source
