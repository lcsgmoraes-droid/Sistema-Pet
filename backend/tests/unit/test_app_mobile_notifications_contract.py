from pathlib import Path


BACKEND_ROOT = Path(__file__).resolve().parents[2]
REPO_ROOT = BACKEND_ROOT.parent


def test_app_mobile_notification_model_and_routes_contract():
    models_source = (BACKEND_ROOT / "app/models.py").read_text(encoding="utf-8")
    routes_source = (BACKEND_ROOT / "app/routes/app_mobile_routes.py").read_text(
        encoding="utf-8"
    )

    assert "class AppNotification(BaseTenantModel)" in models_source
    assert '__tablename__ = "app_notifications"' in models_source
    assert "idempotency_key" in models_source
    assert "cleared_at" in models_source
    assert "read_at" in models_source
    assert "payload" in models_source

    assert '@router.get("/notificacoes")' in routes_source
    assert '@router.post("/notificacoes/{notificacao_id}/lida")' in routes_source
    assert '@router.delete("/notificacoes")' in routes_source
    assert "AppNotification.cleared_at.is_(None)" in routes_source
    assert "_activate_user_tenant_context(current_user)" in routes_source


def test_stock_waitlist_push_creates_app_notification_with_product_payload():
    source = (BACKEND_ROOT / "app/services/pendencia_estoque_service.py").read_text(
        encoding="utf-8"
    )

    assert "criar_notificacao_estoque_app" in source
    assert '"source": "stock_waitlist"' in source
    assert '"kind": "stock_available"' in source
    assert '"produto_id": getattr(produto, "id", None)' in source
    assert '"pendencia_id": getattr(pendencia, "id", None)' in source


def test_stock_waitlist_app_notification_allows_new_record_each_stock_cycle():
    source = (BACKEND_ROOT / "app/services/app_notifications.py").read_text(
        encoding="utf-8"
    )
    stock_function = source[source.index("def criar_notificacao_estoque_app(") :]
    stock_function = stock_function[
        : stock_function.index("def registrar_resultado_push_notificacao_app(")
    ]

    assert "stock_waitlist:{pendencia_id}" not in stock_function
    assert "idempotency_key=None" in stock_function


def test_ecommerce_notify_me_push_uses_product_payload_and_app_notification():
    source = (BACKEND_ROOT / "app/routes/ecommerce_notify_routes.py").read_text(
        encoding="utf-8"
    )

    assert "criar_notificacao_app" in source
    assert '"source": "stock_waitlist"' in source
    assert '"kind": "stock_available"' in source
    assert '"produto_id": product_id' in source
    assert '"product_id": product_id' in source
    assert '"type": "stock_available"' in source


def test_mobile_app_exposes_notifications_center_and_stock_push_navigation():
    navigator_source = (
        REPO_ROOT / "app-mobile/src/navigation/MainNavigator.tsx"
    ).read_text(encoding="utf-8")
    hook_source = (
        REPO_ROOT / "app-mobile/src/hooks/usePushNotifications.ts"
    ).read_text(encoding="utf-8")
    product_detail_source = (
        REPO_ROOT / "app-mobile/src/screens/shop/ProductDetailScreen.tsx"
    ).read_text(encoding="utf-8")

    assert "NotificationsScreen" in navigator_source
    assert 'name="Notificacoes"' in navigator_source
    assert "stockNotificationToProductId" in hook_source
    assert 'screen: "DetalhesProduto"' in hook_source
    assert "getLastNotificationResponseAsync" in hook_source
    assert "produtoId" in product_detail_source
    assert "buscarProdutoPorId" in product_detail_source


def test_campaign_push_notifications_create_app_center_payloads():
    helper_source = (BACKEND_ROOT / "app/campaigns/app_push.py").read_text(
        encoding="utf-8"
    )
    birthday_source = (BACKEND_ROOT / "app/campaigns/handlers/birthday.py").read_text(
        encoding="utf-8"
    )
    welcome_source = (BACKEND_ROOT / "app/campaigns/handlers/welcome.py").read_text(
        encoding="utf-8"
    )
    inactivity_source = (
        BACKEND_ROOT / "app/campaigns/handlers/inactivity.py"
    ).read_text(encoding="utf-8")
    cashback_source = (BACKEND_ROOT / "app/campaigns/handlers/cashback.py").read_text(
        encoding="utf-8"
    )
    ranking_source = (BACKEND_ROOT / "app/campaigns/handlers/ranking.py").read_text(
        encoding="utf-8"
    )
    quick_repurchase_source = (
        BACKEND_ROOT / "app/campaigns/handlers/quick_repurchase.py"
    ).read_text(encoding="utf-8")
    loyalty_source = (BACKEND_ROOT / "app/campaigns/loyalty_rewards.py").read_text(
        encoding="utf-8"
    )
    retorno_source = (
        BACKEND_ROOT / "app/banho_tosa_retornos_notificacoes.py"
    ).read_text(encoding="utf-8")

    assert 'source="campaign"' in helper_source
    assert '"target": "benefits"' in helper_source
    assert "enqueue_campaign_push" in birthday_source
    assert '"birthday_customer"' in birthday_source
    assert '"birthday_pet"' in birthday_source
    assert "notification_customer_id=dono.id" in birthday_source
    assert "customer_id=notification_customer_id" in birthday_source
    assert "enqueue_campaign_push" in welcome_source
    assert '"welcome_app"' in welcome_source
    assert "enqueue_campaign_push" in inactivity_source
    assert '"inactivity"' in inactivity_source
    assert "enqueue_campaign_push" in cashback_source
    assert '"cashback"' in cashback_source
    assert "enqueue_campaign_push" in ranking_source
    assert '"ranking_upgrade"' in ranking_source
    assert "enqueue_campaign_push" in quick_repurchase_source
    assert '"quick_repurchase"' in quick_repurchase_source
    assert "enqueue_campaign_push" in loyalty_source
    assert '"loyalty_reward"' in loyalty_source
    assert 'source="campaign" if canal == "app" else None' in retorno_source
    assert '"kind": "banho_tosa_retorno"' in retorno_source


def test_ecommerce_public_exposes_product_detail_endpoint_for_mobile_deeplink():
    public_source = (BACKEND_ROOT / "app/routes/ecommerce_public.py").read_text(
        encoding="utf-8"
    )

    assert '@router.get("/products/{produto_id}")' in public_source
    assert "Produto.id == produto_id" in public_source
    assert "resolver_preco_publico_produto" in public_source


def test_app_mobile_product_detail_endpoint_includes_unavailable_app_products():
    routes_source = (BACKEND_ROOT / "app/routes/app_mobile_routes.py").read_text(
        encoding="utf-8"
    )
    service_source = (REPO_ROOT / "app-mobile/src/services/shop.service.ts").read_text(
        encoding="utf-8"
    )

    assert '@router.get("/produto/{produto_id}"' in routes_source
    assert (
        "Produto.anunciar_app.is_(True)"
        not in routes_source[
            routes_source.index("def buscar_produto_app_por_id(") : routes_source.index(
                '@router.get("/produto-barcode/{barcode}"'
            )
        ]
    )
    assert '"anunciar_app"' in routes_source
    assert '"anunciar_ecommerce"' in routes_source
    assert '"disponivel_app"' in routes_source
    assert '"disponivel_ecommerce"' in routes_source
    assert 'float(getattr(produto, "estoque_atual", 0) or 0) > 0' in routes_source
    assert "api.get<Produto>(`/app/produto/${id}`)" in service_source
