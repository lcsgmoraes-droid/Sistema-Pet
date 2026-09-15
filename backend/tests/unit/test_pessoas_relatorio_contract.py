from fastapi import HTTPException
import pytest

from app.clientes.relatorio_routes import _validar_tipos_relatorio


def test_relatorio_aceita_tipos_validos_sem_repeticao():
    assert _validar_tipos_relatorio(["Cliente", "cliente", "fornecedor"]) == [
        "cliente",
        "fornecedor",
    ]


def test_relatorio_rejeita_tipo_desconhecido():
    with pytest.raises(HTTPException) as exc_info:
        _validar_tipos_relatorio(["cliente", "desconhecido"])

    assert exc_info.value.status_code == 422


def test_rota_de_relatorio_fica_antes_da_rota_de_detalhe():
    from app import clientes_routes

    paths = [route.path for route in clientes_routes.router.routes]

    assert "/clientes/relatorio/pessoas" in paths
    assert paths.index("/clientes/relatorio/pessoas") < paths.index(
        "/clientes/{cliente_id}"
    )
