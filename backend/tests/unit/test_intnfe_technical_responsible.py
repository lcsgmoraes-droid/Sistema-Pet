from types import SimpleNamespace

import pytest

from app import nfe_routes
from app.intnfe import emission


def _rejected_sale():
    return SimpleNamespace(
        id=30,
        tenant_id="tenant-a",
        nfe_provider="intnfe",
        nfe_status="rejeitada",
        nfe_codigo_erro="974",
        nfe_correlation_id="tentativa-30",
        nfe_ambiente=2,
        nfe_tipo="nfe",
    )


def test_consulta_cnpj_tecnico_da_rejeicao_sem_alterar_venda(monkeypatch):
    sale = _rejected_sale()
    db = SimpleNamespace()
    connection = SimpleNamespace()
    seen = []
    monkeypatch.setattr(
        emission, "_connection", lambda *args, **kwargs: connection
    )

    def access_token(api, actual_connection, environment):
        seen.append((actual_connection, environment))
        return "token-teste"

    monkeypatch.setattr(emission, "_access_token", access_token)
    api = SimpleNamespace(
        document_xml=lambda token, kind, correlation: (
            seen.append((token, kind, correlation))
            or b"<NFe><infNFe><dest><CPF>12345678909</CPF></dest>"
            b"<infRespTec><CNPJ>12345678000195</CNPJ></infRespTec>"
            b"</infNFe></NFe>"
        )
    )

    assert emission.rejected_technical_responsible_cnpj(db, sale, api) == (
        "12345678000195"
    )
    assert seen == [
        (connection, 2),
        ("token-teste", "nfe", "tentativa-30"),
    ]


def test_consulta_cnpj_tecnico_exige_rejeicao_974():
    sale = _rejected_sale()
    sale.nfe_codigo_erro = "386"

    with pytest.raises(emission.DirectEmissionError, match="rejeição 974"):
        emission.rejected_technical_responsible_cnpj(
            SimpleNamespace(), sale, SimpleNamespace()
        )


def test_rota_consulta_venda_dentro_do_tenant(monkeypatch):
    sale = _rejected_sale()
    seen = []
    monkeypatch.setattr(
        nfe_routes,
        "_buscar_venda_para_nfe",
        lambda db, sale_id, tenant_id: (
            seen.append((sale_id, tenant_id)) or sale
        ),
    )
    monkeypatch.setattr(nfe_routes, "_intnfe_client", lambda: SimpleNamespace(close=lambda: None))
    monkeypatch.setattr(
        nfe_routes,
        "rejected_technical_responsible_cnpj",
        lambda db, actual_sale, api: "12345678000195",
    )

    result = nfe_routes.responsavel_tecnico_intnfe_venda(
        30,
        db=SimpleNamespace(),
        user_and_tenant=(SimpleNamespace(id=1), "tenant-a"),
    )

    assert seen == [(30, "tenant-a")]
    assert result == {"cnpj": "12345678000195"}
