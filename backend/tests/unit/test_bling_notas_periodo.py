from unittest.mock import Mock

import pytest

from app.bling_integration import BlingAPI


@pytest.mark.parametrize(
    "metodo,endpoint", [("listar_nfes", "/nfe"), ("listar_nfces", "/nfce")]
)
def test_periodo_enviado_nos_parametros_documentados(metodo, endpoint):
    api = object.__new__(BlingAPI)
    api._request = Mock(return_value={"data": []})
    getattr(api, metodo)("2026-09-08", "2026-09-09", "5")
    api._request.assert_called_once_with(
        "GET",
        endpoint,
        data={
            "dataEmissaoInicial": "2026-09-08 00:00:00",
            "dataEmissaoFinal": "2026-09-09 23:59:59",
            "situacao": "5",
        },
    )
