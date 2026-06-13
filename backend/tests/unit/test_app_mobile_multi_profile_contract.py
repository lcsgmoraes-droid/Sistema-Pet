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
