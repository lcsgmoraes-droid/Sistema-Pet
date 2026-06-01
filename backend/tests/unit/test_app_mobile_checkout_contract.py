from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]


def _read_mobile_source(relative_path: str) -> str:
    return (ROOT / relative_path).read_text(encoding="utf-8")


def test_checkout_success_screen_keeps_payment_link_visible_when_available():
    source = _read_mobile_source("app-mobile/src/screens/shop/CheckoutSucessoScreen.tsx")

    assert "pedido.payment_url" in source
    assert "abrirPagamento" in source
    assert "Abrir pagamento" in source
    assert "Linking.openURL(pedido.payment_url)" in source


def test_cart_screen_does_not_depend_only_on_automatic_payment_redirect():
    source = _read_mobile_source("app-mobile/src/screens/shop/CartScreen.tsx")

    assert "Linking.openURL(pedido.payment_url)" in source
    assert "navigation.navigate('CheckoutSucesso', { pedido })" in source
