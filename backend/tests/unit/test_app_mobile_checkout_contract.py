import re
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
    assert 'statusKey === "pendente"' in source


def test_checkout_success_screen_does_not_tell_online_customer_to_pay_on_delivery():
    source = _read_mobile_source(
        "app-mobile/src/screens/shop/CheckoutSucessoScreen.tsx"
    )

    assert "Pague ao receber ou conforme combinado" not in source
    assert "Acompanhe o status em Meus Pedidos" in source
    assert "Compartilhar pedido" in source


def test_app_order_tracking_accepts_app_channel_sales():
    source = _read_mobile_source("backend/app/routes/app_mobile_rastreio_routes.py")

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


def test_android_manifest_removes_unused_store_sensitive_permissions():
    manifest = _read_mobile_source(
        "app-mobile/android/app/src/main/AndroidManifest.xml"
    )

    assert 'android.permission.RECORD_AUDIO" tools:node="remove"' in manifest
    assert 'android.permission.SYSTEM_ALERT_WINDOW" tools:node="remove"' in manifest


def test_mobile_orders_screen_shows_channel_label_and_order_push_navigates_to_orders():
    orders = _read_mobile_source("app-mobile/src/screens/orders/OrdersScreen.tsx")
    hook = _read_mobile_source("app-mobile/src/hooks/usePushNotifications.ts")
    types = _read_mobile_source("app-mobile/src/types/index.ts")

    assert "canal_label" in types
    assert "canal_label" in orders
    assert "App mobile" in orders
    assert 'data.source === "order"' in hook
    assert 'navigateWhenReady("Pedidos"' in hook


def test_mobile_orders_screen_polls_pending_orders_until_webhook_updates_status():
    orders = _read_mobile_source("app-mobile/src/screens/orders/OrdersScreen.tsx")

    assert "PENDING_ORDER_POLL_MS" in orders
    assert "setInterval(carregar, PENDING_ORDER_POLL_MS)" in orders
    assert 'getPedidoStatusKey(pedido) === "pendente"' in orders
    assert "hasOpenFulfillmentOrder" in orders
    assert "clearInterval(interval)" in orders


def test_mobile_orders_screen_shows_pickup_person_and_delivery_summary():
    orders = _read_mobile_source("app-mobile/src/screens/orders/OrdersScreen.tsx")

    assert "A retirar" in orders
    assert "Compra com entrega" in orders
    assert "Retirado por" in orders


def test_mobile_orders_screen_does_not_show_completed_sales_as_pending_payment():
    orders = _read_mobile_source("app-mobile/src/screens/orders/OrdersScreen.tsx")

    assert "finalizada:" in orders
    assert "pago_nf:" in orders
    assert "finalizada_devolucao" in orders
    assert "devolvida_total" in orders
    assert "desconhecido:" in orders
    assert "?? STATUS_CONFIG.desconhecido" in orders


def test_mobile_orders_screen_handles_sales_without_checkout_pedido_id():
    orders = _read_mobile_source("app-mobile/src/screens/orders/OrdersScreen.tsx")
    types = _read_mobile_source("app-mobile/src/types/index.ts")

    assert "historico_id?: string | null" in types
    assert "numero?: string | null" in types
    assert "pedido_id?: string | null" in types
    assert "function getPedidoRenderKey" in orders
    assert "function getPedidoTitulo" in orders
    assert "item.pedido_id.slice" not in orders
    assert "keyExtractor={(item, index) => getPedidoRenderKey(item, index)}" in orders
    assert "const pedidoKey = getPedidoRenderKey(item)" in orders
    assert "item.pedido_id &&" in orders


def test_mobile_orders_screen_shows_friendly_empty_and_error_states():
    orders = _read_mobile_source("app-mobile/src/screens/orders/OrdersScreen.tsx")

    assert "erroPedidos" in orders
    assert "setErroPedidos" in orders
    assert "Nao foi possivel carregar seus pedidos" in orders
    assert "Nenhum pedido feito" in orders
    assert "Tentar novamente" in orders


def test_mobile_orders_screen_is_defensive_with_malformed_order_history():
    orders = _read_mobile_source("app-mobile/src/screens/orders/OrdersScreen.tsx")
    service = _read_mobile_source("app-mobile/src/services/shop.service.ts")

    assert "function safeText" in orders
    assert "function getPedidoStatusKey" in orders
    assert "function getPedidoItens" in orders
    assert "const itens = getPedidoItens(item)" in orders
    assert "const totalItens = getPedidoItens(pedido).length" in orders
    assert "const retiradoPor = safeText(item.retirado_por).trim()" in orders
    assert "pedido.itens.length" not in orders
    assert "item.itens?.slice" not in orders
    assert ".pedido_id.slice" not in orders
    assert ".filter(isPedidoRecord)" in service
    assert "Array.isArray(pedido.itens)" in service


def test_mobile_wishlist_empty_state_stops_loading_when_no_favorites():
    wishlist = _read_mobile_source("app-mobile/src/screens/shop/WishlistScreen.tsx")

    assert "Nenhum favorito ainda" in wishlist
    assert "finally" in wishlist
    assert "setCarregando(false)" in wishlist
    assert "const wishlistIds = useWishlistStore.getState().ids" in wishlist
    assert not re.search(
        r"if\s*\(ids\.length === 0\)\s*{\s*setProdutos\(\[\]\);\s*return;",
        wishlist,
        re.S,
    )


def test_mobile_home_prioritizes_shopping_and_compacts_scan_feature():
    home = _read_mobile_source("app-mobile/src/screens/HomeScreen.tsx")

    assert "Comprar por pet" in home
    assert "scannerCardCompacto" in home
    assert "iconName" in home
    assert "Veterinário" in home
    assert "Banho & Tosa" in home
    assert "Pedidos" in home
    assert "Benefícios" in home
    assert 'iconText="VET"' not in home
    assert 'iconText="Ped"' not in home
    assert 'iconText="Pts"' not in home


def test_mobile_notification_button_reflects_permission_state():
    actions = _read_mobile_source("app-mobile/src/components/HeaderProfileActions.tsx")

    assert 'import * as Notifications from "expo-notifications"' in actions
    assert "Notifications.getPermissionsAsync" in actions
    assert "notificacoesAtivadas" in actions
    assert 'name={notificacoesAtivadas ? "notifications" : "notifications-outline"}' in actions


def test_mobile_catalog_uses_customer_filter_modal_instead_of_admin_chips():
    catalog = _read_mobile_source("app-mobile/src/screens/shop/CatalogScreen.tsx")
    service = _read_mobile_source("app-mobile/src/services/shop.service.ts")
    ecommerce = _read_mobile_source("backend/app/routes/ecommerce_public.py")

    assert "Modal" in catalog
    assert "modalFiltrosVisivel" in catalog
    assert "useSafeAreaInsets" in catalog
    assert "insets.bottom" in catalog
    assert "contentContainerStyle={[" in catalog
    assert "paddingBottom: 120 + insets.bottom" in catalog
    assert "style={styles.modalScroll}" in catalog
    assert "Espécie" in catalog
    assert "Peso da embalagem" in catalog
    assert "Marca" in catalog
    assert "buscaMarca" in catalog
    assert "setBuscaMarca" in catalog
    assert "Buscar marca" in catalog
    assert "marcasFiltradas" in catalog
    assert "pesosEmbalagemDisponiveis" in catalog
    assert "formatarPesoEmbalagemFiltro" in catalog
    assert "selecionarPesoEmbalagem" in catalog
    assert "limit: filtrosAtivos > 0 ? 500 : undefined" in catalog
    assert "aplicarFiltrosCatalogo" in catalog
    assert "peso_embalagem_kg" in catalog
    assert "Cão" in catalog
    assert "Gato" in catalog
    assert "listarOpcoesFiltrosCatalogo" in service
    assert "pesoEmbalagemKg" in service
    assert "pesos_embalagem_kg" in service
    assert "marca: str | None = Query(default=None)" in ecommerce
    assert "peso_embalagem_kg: float | None = Query(default=None)" in ecommerce
    assert "@router.get(\"/produtos/filtros\")" in ecommerce
    assert "distinct(Produto.peso_embalagem)" in ecommerce
    assert "PESO_EMBALAGEM_OPTIONS" not in catalog
    assert "Até 1 kg" not in catalog
    assert "Até 3 kg" not in catalog
    assert "Até 10 kg" not in catalog
    assert "Até 15 kg" not in catalog
    assert "Peso do pet" not in catalog
    assert "Em estoque" not in catalog
    assert "Com foto" not in catalog
    assert "Mais prontos" not in catalog


def test_pet_photo_flow_guides_crop_and_protects_unsaved_photo():
    pet_form = _read_mobile_source("app-mobile/src/screens/pets/PetFormScreen.tsx")

    assert "ImagePicker.launchImageLibraryAsync" in pet_form
    assert "allowsEditing: true" in pet_form
    assert "Cortar" in pet_form
    assert "navigation.addListener('beforeRemove'" in pet_form
    assert "fotoPendente" in pet_form
    assert "Salvar alterações" in pet_form
    assert "Sair sem salvar" in pet_form
    assert "Salvar foto" in pet_form


def test_profile_points_card_wraps_without_overflow_on_narrow_mobile():
    profile = _read_mobile_source("app-mobile/src/screens/profile/ProfileScreen.tsx")

    assert 'flexWrap: "wrap"' in profile
    assert "minWidth: 0" in profile
    assert "flexShrink: 1" in profile
    assert "pontosInfoSpacer" in profile
    assert "pontosInfoTextoLinha" in profile


def test_push_registration_handles_firebase_errors_from_native_setup_steps():
    service = _read_mobile_source(
        "app-mobile/src/services/pushNotifications.service.ts"
    )

    assert "function firebaseNotConfiguredResult" in service
    assert "return firebaseNotConfiguredResult();" in service
    assert re.search(
        r"try\s*{.*?await ensureAndroidChannel\(\);"
        r".*?Notifications\.getPermissionsAsync\(\)"
        r".*?Notifications\.getExpoPushTokenAsync",
        service,
        re.S,
    )
