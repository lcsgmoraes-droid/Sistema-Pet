import pytest
from fastapi import HTTPException

from app.pedidos_compra.envio_routes import _normalizar_emails_destino


def test_normaliza_destinatarios_separados_por_ponto_e_virgula_ou_virgula():
    assert _normalizar_emails_destino(
        "compras@example.com; vendedor@example.com, financeiro@example.com"
    ) == [
        "compras@example.com",
        "vendedor@example.com",
        "financeiro@example.com",
    ]


def test_normaliza_destinatarios_remove_repetidos():
    assert _normalizar_emails_destino("Compras@example.com; compras@example.com") == [
        "Compras@example.com"
    ]


def test_normaliza_destinatarios_rejeita_email_invalido():
    with pytest.raises(HTTPException) as exc_info:
        _normalizar_emails_destino("compras@example.com; email-invalido")

    assert exc_info.value.status_code == 400
    assert exc_info.value.detail == "E-mail inválido: email-invalido"
