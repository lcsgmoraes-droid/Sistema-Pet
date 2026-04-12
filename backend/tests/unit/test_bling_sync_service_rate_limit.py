from app.services.bling_sync_service import (
    _cooldown_rate_limit_segundos,
    _mensagem_rate_limit_bling,
    _secondary_jobs_defer_reason,
)


def test_cooldown_rate_limit_daily_limit_uses_long_retry_window():
    error_message = (
        "Erro na API Bling: 429 Client Error: Too Many Requests for url: "
        "https://api.bling.com.br/Api/v3/estoques - "
        "{'error': {'type': 'TOO_MANY_REQUESTS', 'message': 'Limite de requisições atingido.', "
        "'description': 'O limite de requisições por dia foi atingido, tente novamente amanhã.', "
        "'limit': 120000, 'period': 'day'}}"
    )

    cooldown = _cooldown_rate_limit_segundos(error_message, default=4)

    assert cooldown >= 3600


def test_mensagem_rate_limit_bling_daily_limit_mentions_tomorrow():
    error_message = (
        "Erro na API Bling: 429 Client Error: Too Many Requests - "
        "{'error': {'type': 'TOO_MANY_REQUESTS', 'period': 'day', "
        "'description': 'O limite de requisições por dia foi atingido, tente novamente amanhã.'}}"
    )

    message = _mensagem_rate_limit_bling(error_message, cooldown_seconds=6 * 3600)

    assert "limite diario" in message.lower()
    assert "amanha" in message.lower()


def test_secondary_jobs_defer_when_stock_queue_is_ready():
    reason = _secondary_jobs_defer_reason(
        cooldown_active=False,
        ready_queue=1,
        total_queue=1,
        forced_queue=0,
    )

    assert reason == "stock_queue_ready"


def test_secondary_jobs_defer_when_manual_stock_sync_is_pending():
    reason = _secondary_jobs_defer_reason(
        cooldown_active=False,
        ready_queue=0,
        total_queue=1,
        forced_queue=1,
    )

    assert reason == "manual_stock_sync_pending"


def test_secondary_jobs_do_not_defer_without_pressure():
    reason = _secondary_jobs_defer_reason(
        cooldown_active=False,
        ready_queue=0,
        total_queue=0,
        forced_queue=0,
    )

    assert reason is None
