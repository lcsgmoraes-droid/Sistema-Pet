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
