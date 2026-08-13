from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]
AUTH_STORE = REPO_ROOT / "app-mobile/src/store/auth.store.ts"
STORE_SELECTION_SCREEN = REPO_ROOT / "app-mobile/src/screens/SelecionarLojaScreen.tsx"
TENANT_STORE = REPO_ROOT / "app-mobile/src/store/tenant.store.ts"


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_mobile_auth_does_not_reapply_stale_operational_role_to_customer_profile():
    source = _read(AUTH_STORE)

    assert "clearOperationalRoleCache(user)" in source
    assert "await clearOperationalRoleCache(freshUser);" in source
    assert "Não sobrescreve cache positivo" not in source
    assert "Nao sobrescreve cache positivo" not in source


def test_mobile_store_location_lookup_uses_fast_cached_position_before_gps_fix():
    source = _read(STORE_SELECTION_SCREEN)

    assert "Location.getLastKnownPositionAsync" in source
    assert "LOCATION_LOOKUP_TIMEOUT_MS" in source
    assert "withTimeout(" in source
    assert "reverseGeocodeAsync(posicao.coords)" in source
    assert "buscarProximas(" in source
    assert "posicao.coords.latitude" in source
    assert "posicao.coords.longitude" in source

    tenant_store = _read(TENANT_STORE)
    assert "limit: '8'" in tenant_store
    assert "/api/ecommerce/tenants/sugerir" in tenant_store
