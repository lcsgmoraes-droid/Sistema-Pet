from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]


def read_repo(path: str) -> str:
    return (REPO_ROOT / path).read_text(encoding="utf-8")


def test_gestor_route_is_read_only_and_checks_active_profile():
    source = read_repo("backend/app/routes/app_mobile_gestor_routes.py")

    assert '@router.get("/resumo"' in source
    assert "_get_current_ecommerce_user" in source
    assert 'active_profile != "gestor"' in source
    assert "resolve_user_app_profiles" in source
    assert "user_has_gestor_permissions" not in source
    assert "tenant_id" in source
    assert "@router.post" not in source
    assert "@router.put" not in source
    assert "@router.delete" not in source


def test_gestor_summary_reuses_financial_sources_of_truth():
    source = read_repo("backend/app/routes/app_mobile_gestor_routes.py")

    assert "_valores_operacionais_venda" in source
    assert "_total_recebido_venda" in source
    assert "get_fluxo_caixa" in source
    assert "gerar_dre_por_canais" in source
    assert "ContaPagar" in source
    assert "ContaReceber" in source


def test_mobile_gestor_screen_has_requested_periods_and_indicators():
    screen = read_repo("app-mobile/src/screens/gestor/GestorDashboardScreen.tsx")
    utils = read_repo("app-mobile/src/screens/gestor/GestorDashboardUtils.ts")
    service = read_repo("app-mobile/src/services/gestor.service.ts")

    for label in ["Hoje", "Ontem", "7 dias", "Este mes", "Mes anterior"]:
        assert label in utils
    for label in [
        "Bruto",
        "Liquido",
        "Recebido",
        "Vendas",
        "Unidades",
        "Fluxo de caixa de hoje",
        "Contas a receber",
        "Contas a pagar",
        "Resultado da DRE",
    ]:
        assert label in screen
    assert '"/app/gestor/resumo"' in service


def test_app_navigator_routes_gestor_to_dedicated_navigation():
    navigator = read_repo("app-mobile/src/navigation/AppNavigator.tsx")

    assert "GestorNavigator" in navigator
    assert 'perfil_operacional === "gestor"' in navigator


def test_gestor_is_manually_granted_only_by_app_access_administrators():
    service = read_repo("backend/app/services/app_access_profile_service.py")
    clientes = read_repo("backend/app/clientes/crud_routes.py")
    funcionarios = read_repo("backend/app/funcionarios/base_routes.py")
    customer_access = read_repo(
        "frontend/src/components/clientes/ClientesNovoAcessoAppCard.jsx"
    )
    employee_page = read_repo("frontend/src/pages/RH/Funcionarios.jsx")
    access_helper = read_repo("frontend/src/utils/appAccessProfiles.js")

    assert '"gestor"' in service
    assert "include_gestor" not in service
    assert '"usuarios.manage"' in clientes
    assert '"usuarios.manage"' in funcionarios
    assert 'value: "gestor"' in customer_access
    assert '["gestor", "Gestor"]' in employee_page
    assert 'permissions.includes("usuarios.manage")' in access_helper
