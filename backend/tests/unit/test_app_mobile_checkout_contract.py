from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]


def _read_mobile_source(relative_path: str) -> str:
    return (ROOT / relative_path).read_text(encoding="utf-8")


def test_checkout_success_screen_keeps_payment_link_visible_when_available():
    source = _read_mobile_source(
        "app-mobile/src/screens/shop/CheckoutSucessoScreen.tsx"
    )

    assert "pedido.payment_url" in source
    assert "abrirPagamento" in source
    assert "Abrir pagamento" in source
    assert "Linking.openURL(pedido.payment_url)" in source


def test_cart_screen_does_not_depend_only_on_automatic_payment_redirect():
    source = _read_mobile_source("app-mobile/src/screens/shop/CartScreen.tsx")

    assert "Linking.openURL(pedido.payment_url)" in source
    assert "navigation.navigate('CheckoutSucesso', { pedido })" in source


def test_cart_screen_preserves_success_navigation_when_payment_link_fails_to_open():
    source = _read_mobile_source("app-mobile/src/screens/shop/CartScreen.tsx")

    assert "void Linking.openURL(pedido.payment_url).catch" in source
    assert "Nao consegui abrir o pagamento automaticamente" in source


def test_orders_screen_can_reopen_pending_payment_link():
    source = _read_mobile_source("app-mobile/src/screens/orders/OrdersScreen.tsx")

    assert "Linking.openURL(item.payment_url)" in source
    assert "Pagar agora" in source
    assert 'item.status === "pendente"' in source


def test_checkout_success_screen_does_not_tell_online_customer_to_pay_on_delivery():
    source = _read_mobile_source(
        "app-mobile/src/screens/shop/CheckoutSucessoScreen.tsx"
    )

    assert "Pague ao receber ou conforme combinado" not in source
    assert "Acompanhe o status em Meus Pedidos" in source
    assert "Compartilhar pedido" in source


def test_app_order_tracking_accepts_app_channel_sales():
    source = _read_mobile_source("backend/app/routes/app_mobile_routes.py")

    assert 'Venda.canal.in_(["ecommerce", "app", "aplicativo"])' in source


def test_app_linking_returns_payment_to_orders_without_store_picker():
    navigator = _read_mobile_source("app-mobile/src/navigation/AppNavigator.tsx")
    tenant_store = _read_mobile_source("app-mobile/src/store/tenant.store.ts")
    app_return = _read_mobile_source("frontend/src/pages/AppPaymentReturn.jsx")
    app_return_links = _read_mobile_source(
        "frontend/src/utils/appPaymentReturnLinks.js"
    )

    assert '"corepet://app"' in navigator
    assert 'ListaPedidos: "pedidos"' in navigator
    assert "Linking.getInitialURL" in tenant_store
    assert "extractStoreSlug(initialUrl" in tenant_store
    assert "buildAppPaymentReturnLinks" in app_return
    assert "corepet://app/pedidos" in app_return_links
    assert "intent://app/pedidos" in app_return_links
    assert "loja" in app_return_links


def test_android_manifest_accepts_corepet_payment_return_deep_link():
    manifest = _read_mobile_source(
        "app-mobile/android/app/src/main/AndroidManifest.xml"
    )

    assert "android.intent.action.VIEW" in manifest
    assert "android.intent.category.BROWSABLE" in manifest
    assert 'android:scheme="corepet"' in manifest
