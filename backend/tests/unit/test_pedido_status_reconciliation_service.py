from datetime import datetime, timedelta, timezone

from app.services import pedido_status_reconciliation_service as service


def test_mensagem_rate_limit_diario_detecta_resposta_do_bling():
    mensagem = (
        "Erro na API Bling: 429 Client Error: Too Many Requests - "
        "{'error': {'type': 'TOO_MANY_REQUESTS', 'description': "
        "'O limite de requisições por dia foi atingido, tente novamente amanhã.', "
        "'period': 'day'}}"
    )

    assert service._mensagem_rate_limit_diario(mensagem) is True


def test_registrar_bloqueio_rate_limit_diario_define_janela_futura(monkeypatch):
    fake_now = datetime(2026, 4, 12, 17, 30, tzinfo=timezone(timedelta(hours=-3)))

    class FakeDateTime(datetime):
        @classmethod
        def now(cls, tz=None):
            if tz is None:
                return fake_now
            return fake_now.astimezone(tz)

    monkeypatch.setattr(service, "datetime", FakeDateTime)
    monkeypatch.setattr(service, "_RATE_LIMIT_DIARIO_BLOQUEADO_ATE", None)

    bloqueado_ate = service._registrar_bloqueio_rate_limit_diario()

    assert bloqueado_ate > fake_now.astimezone(timezone.utc)
    assert bloqueado_ate.astimezone(fake_now.tzinfo).hour == 0
    assert bloqueado_ate.astimezone(fake_now.tzinfo).minute == 5


def test_rate_limit_diario_ativo_respeita_bloqueio(monkeypatch):
    monkeypatch.setattr(
        service,
        "_RATE_LIMIT_DIARIO_BLOQUEADO_ATE",
        datetime.now(timezone.utc) + timedelta(minutes=10),
    )

    assert service._rate_limit_diario_ativo() is True
