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


def test_orders_screen_can_reopen_pending_payment_link():
    source = _read_mobile_source("app-mobile/src/screens/orders/OrdersScreen.tsx")

    assert "Linking.openURL(item.payment_url)" in source
    assert "Pagar agora" in source
    assert "item.status === \"pendente\"" in source


def test_checkout_success_screen_does_not_tell_online_customer_to_pay_on_delivery():
    source = _read_mobile_source("app-mobile/src/screens/shop/CheckoutSucessoScreen.tsx")

    assert "Pague ao receber ou conforme combinado" not in source
    assert "Acompanhe o status em Meus Pedidos" in source
    assert "Compartilhar pedido" in source


def test_app_order_tracking_accepts_app_channel_sales():
    source = _read_mobile_source("backend/app/routes/app_mobile_routes.py")

    assert 'Venda.canal.in_(["ecommerce", "app", "aplicativo"])' in source
