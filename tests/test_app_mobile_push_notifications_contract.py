from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def test_app_mobile_push_registration_has_manual_profile_action():
    service_path = ROOT / "app-mobile/src/services/pushNotifications.service.ts"
    assert service_path.exists(), (
        "Create a dedicated push notification registration service"
    )

    service = service_path.read_text(encoding="utf-8")
    hook = read("app-mobile/src/hooks/usePushNotifications.ts")
    profile = read("app-mobile/src/screens/profile/ProfileScreen.tsx")

    assert "ensurePushNotificationsRegistered" in service
    assert 'status: "expo_go"' in service
    assert 'status: "permission_denied"' in service
    assert 'status: "firebase_not_configured"' in service
    assert "Firebase/FCM" in service
    assert 'status: "registered"' in service
    assert "expo-device" in service
    assert "buildPushDeviceMetadata" in service
    assert "registerPushToken(tokenData.data, buildPushDeviceMetadata())" in service
    assert "device_name" in service
    assert "device_model" in service
    assert "app_version" in service

    assert "ensurePushNotificationsRegistered" in hook
    assert "requestPermissionsAsync" not in hook
    assert "getExpoPushTokenAsync" not in hook

    assert "ativarNotificacoes" in profile
    assert "Notificacoes de pedidos" in profile
    assert "ensurePushNotificationsRegistered" in profile


def test_push_devices_migration_backfills_existing_user_tokens():
    migration = read("backend/alembic/versions/ua20260621a1_create_user_push_devices.py")

    assert "create_table(" in migration
    assert '"user_push_devices"' in migration
    assert "INSERT INTO user_push_devices" in migration
    assert "FROM users" in migration
    assert "push_token IS NOT NULL" in migration
    assert "Dispositivo registrado anteriormente" in migration
