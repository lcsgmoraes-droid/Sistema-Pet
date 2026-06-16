import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
WATCHDOG_SCRIPT = ROOT / "scripts" / "ops_host_watchdog.sh"


def _watchdog_script_text() -> str:
    return WATCHDOG_SCRIPT.read_text(encoding="utf-8")


def test_host_watchdog_counts_only_http_status_5xx_not_response_size():
    script = _watchdog_script_text()
    status_pattern = re.compile(r'" 50[0-9] ')
    response_200_with_500_bytes = (
        "203.0.113.10 - - [25/May/2026:21:00:05 +0000] "
        '"POST /api/formas-pagamento/analisar-venda HTTP/2.0" 200 500 "-" "-" "-"'
    )
    real_502_response = (
        "203.0.113.10 - - [25/May/2026:21:02:13 +0000] "
        '"GET /api/produtos HTTP/2.0" 502 559 "-" "-" "-"'
    )

    assert "docker logs --since" in script
    assert "petshop-prod-nginx" in script
    assert "awk '/ 50[0-9] / {count++} END {print count + 0}'" not in script
    assert 'match($0, /" 50[0-9] /)' in script
    assert status_pattern.search(response_200_with_500_bytes) is None
    assert status_pattern.search(real_502_response) is not None


def test_host_watchdog_does_not_restart_for_historical_5xx_when_health_is_ok():
    script = _watchdog_script_text()

    assert "web_health_failed=false" in script
    assert "web_health_failed=true" in script
    assert (
        'if [[ "$web_health_failed" == "true" '
        '&& "$nginx_5xx_count" -ge "$NGINX_5XX_THRESHOLD" ]]; then'
    ) in script
    assert "5xx recentes sem falha ativa; sem restart" in script
