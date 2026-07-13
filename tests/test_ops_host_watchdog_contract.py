from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def read(relative_path: str) -> str:
    return (ROOT / relative_path).read_text(encoding="utf-8")


def test_host_watchdog_uses_public_health_and_keeps_deep_check_internal():
    watchdog = read("scripts/ops_host_watchdog.sh")
    installer = read("scripts/install_ops_host_watchdog_cron.sh")
    nginx_locations = read("nginx/includes/app-server-locations.conf")

    public_health = "https://mlprohub.com.br/api/health"
    blocked_public_watchdog = f"{public_health}/watchdog"

    assert f"HOST_WATCHDOG_URL:-{public_health}" in watchdog
    assert f"HOST_WATCHDOG_URL:-{public_health}" in installer
    assert blocked_public_watchdog not in watchdog
    assert blocked_public_watchdog not in installer
    assert "http://127.0.0.1:8000/health/watchdog" in watchdog
    assert "location = /api/health/watchdog" in nginx_locations
    assert "return 404;" in nginx_locations
