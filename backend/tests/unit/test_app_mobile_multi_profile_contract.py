from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]


def read_repo(path: str) -> str:
    return (REPO_ROOT / path).read_text(encoding="utf-8")


def test_mobile_types_include_available_profiles():
    source = read_repo("app-mobile/src/types/index.ts")

    assert "AppAccessProfile" in source
    assert "available_profiles" in source
    assert "selected_profile" in source


def test_mobile_auth_service_and_store_can_select_profile():
    service = read_repo("app-mobile/src/services/auth.service.ts")
    store = read_repo("app-mobile/src/store/auth.store.ts")

    assert "selectProfile" in service
    assert "/ecommerce/auth/select-profile" in service
    assert "pendingProfiles" in store
    assert "needsProfileSelection" in store
    assert "selectProfile" in store


def test_mobile_login_and_profile_render_profile_switching_controls():
    login = read_repo("app-mobile/src/screens/auth/LoginScreen.tsx")
    profile = read_repo("app-mobile/src/screens/profile/ProfileScreen.tsx")

    assert "Escolha como entrar" in login
    assert "pendingProfiles" in login
    assert "selectProfile" in login
    assert "Trocar perfil" in profile
    assert "available_profiles" in profile


def test_operational_mobile_navigators_expose_profile_switch_in_header():
    actions_path = REPO_ROOT / "app-mobile/src/components/HeaderProfileActions.tsx"
    assert actions_path.exists(), "operational app headers need an in-session profile switch"

    actions = actions_path.read_text(encoding="utf-8")
    funcionario = read_repo("app-mobile/src/navigation/FuncionarioNavigator.tsx")
    entregador = read_repo("app-mobile/src/navigation/EntregadorNavigator.tsx")
    veterinario = read_repo("app-mobile/src/navigation/VeterinarioNavigator.tsx")

    assert "available_profiles" in actions
    assert "selectProfile" in actions
    assert "Trocar" in actions
    assert "HeaderProfileActions" in funcionario
    assert "HeaderProfileActions" in entregador
    assert "HeaderProfileActions" in veterinario


def test_mobile_profile_switch_is_visible_and_refreshes_profiles_before_alert():
    actions = read_repo("app-mobile/src/components/HeaderProfileActions.tsx")
    home = read_repo("app-mobile/src/screens/HomeScreen.tsx")

    assert "alwaysShowSwitch" in actions
    assert "alwaysShowSwitch = true" in actions
    assert "getProfile" in actions
    assert "updateUser" in actions
    assert "Sem outros acessos" in actions
    assert "HeaderProfileActions" in home
    assert "alwaysShowSwitch" in home
