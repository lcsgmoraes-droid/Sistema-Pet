from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from types import SimpleNamespace

import httpx
import pytest

from app.nfse.models import NfseDocument, NfseTenantConfig
from app.nfse.providers.base import NfseProviderError
from app.nfse.providers.focus_nfe import FocusNfeProvider
from app.nfse.routes import router as nfse_router
from app.nfse.service import (
    PRESIDENTE_PRUDENTE_IBGE,
    build_focus_payload,
    configuration_missing_fields,
    customer_missing_fields,
    infer_customer_municipality_code,
    request_fingerprint,
)


def _tenant(**overrides):
    data = {
        "cnpj": "11.222.333/0001-81",
        "razao_social": "Clinica Veterinaria Sao Jose Ltda",
        "inscricao_municipal": "12345",
        "cidade": "Presidente Prudente",
        "uf": "SP",
    }
    data.update(overrides)
    return SimpleNamespace(**data)


def _config(**overrides):
    data = {
        "environment": "homologacao",
        "municipality_code": PRESIDENTE_PRUDENTE_IBGE,
        "service_list_item": "5.01",
        "cnae_code": "7500100",
        "iss_rate": Decimal("2.00"),
        "iss_withheld": False,
        "operation_nature": "1",
        "special_tax_regime": "6",
        "simple_national": True,
        "cultural_incentive": False,
    }
    data.update(overrides)
    return SimpleNamespace(**data)


def _customer(**overrides):
    data = {
        "cpf": "123.456.789-09",
        "cnpj": None,
        "nome": "Tutor Teste",
        "razao_social": None,
        "endereco": "Rua das Flores",
        "numero": "100",
        "complemento": None,
        "bairro": "Centro",
        "cidade": "Presidente Prudente",
        "estado": "SP",
        "cep": "19010-000",
        "telefone": None,
        "celular": "18 99999-9999",
        "email": "tutor@example.com",
    }
    data.update(overrides)
    return SimpleNamespace(**data)


def test_models_are_tenant_scoped_and_reference_is_unique_per_tenant():
    assert NfseTenantConfig.__table__.c.tenant_id.nullable is False
    assert NfseDocument.__table__.c.tenant_id.nullable is False
    constraints = {constraint.name for constraint in NfseDocument.__table__.constraints}
    assert "uq_nfse_documents_tenant_reference" in constraints


def test_nfse_router_exposes_pilot_configuration_and_consultation_flow():
    routes = {
        (method, route.path)
        for route in nfse_router.routes
        for method in (route.methods or set())
    }
    assert ("GET", "/nfse/configuracao") in routes
    assert ("PUT", "/nfse/configuracao") in routes
    assert ("POST", "/nfse/configuracao/pre-validar") in routes
    assert ("POST", "/nfse/consultas/{consultation_id}/emitir") in routes
    assert ("GET", "/nfse/consultas/{consultation_id}") in routes
    assert ("POST", "/nfse/documentos/{document_id}/sincronizar") in routes
    assert ("POST", "/nfse/documentos/{document_id}/cancelar") in routes


def test_presidente_prudente_configuration_reports_only_real_pending_fields():
    missing = configuration_missing_fields(_tenant(), _config(), token_configured=True)
    assert missing == []

    missing = configuration_missing_fields(
        _tenant(inscricao_municipal=None),
        _config(service_list_item=None),
        token_configured=False,
    )
    assert "inscricao municipal da clinica" in missing
    assert "item da lista de servicos da LC 116" in missing
    assert "token Focus NFe de homologacao" in missing


def test_customer_requires_document_full_address_and_ibge_code():
    customer = _customer(cpf=None, numero=None, cidade="Outra cidade")
    municipality_code = infer_customer_municipality_code(customer, None)
    missing = customer_missing_fields(customer, municipality_code)
    assert "CPF ou CNPJ do tutor" in missing
    assert "numero do endereco do tutor" in missing
    assert "codigo IBGE do municipio do tutor" in missing


def test_valid_cpf_is_used_when_stale_cnpj_is_invalid():
    customer = _customer(cnpj="12.345", cpf="123.456.789-09")
    payload = build_focus_payload(
        tenant=_tenant(),
        config=_config(),
        customer=customer,
        customer_municipality_code=PRESIDENTE_PRUDENTE_IBGE,
        service_amount=Decimal("50.00"),
        description="Consulta veterinaria",
        issued_at=datetime.fromisoformat("2026-08-03T10:30:00-03:00"),
    )
    assert payload["tomador"]["cpf"] == "12345678909"


def test_focus_payload_matches_presidente_prudente_contract_and_is_stable():
    customer = _customer()
    municipality_code = infer_customer_municipality_code(customer, None)
    payload = build_focus_payload(
        tenant=_tenant(),
        config=_config(),
        customer=customer,
        customer_municipality_code=municipality_code,
        service_amount=Decimal("150.50"),
        description="Consulta veterinaria",
        issued_at=datetime.fromisoformat("2026-08-03T10:30:00-03:00"),
    )

    assert payload["prestador"] == {
        "cnpj": "11222333000181",
        "inscricao_municipal": "12345",
        "codigo_municipio": 3541406,
    }
    assert payload["tomador"]["cpf"] == "12345678909"
    assert payload["tomador"]["endereco"]["codigo_municipio"] == 3541406
    assert payload["servico"]["item_lista_servico"] == "5.01"
    assert payload["servico"]["valor_servicos"] == 150.5
    assert request_fingerprint(payload) == request_fingerprint(dict(payload))


def test_focus_provider_uses_homologation_basic_auth(monkeypatch):
    monkeypatch.setenv("FOCUS_NFE_TOKEN_HOMOLOGACAO", "token-teste")
    captured = {}

    def fake_request(method, url, **kwargs):
        captured.update(method=method, url=url, **kwargs)
        return httpx.Response(
            201,
            json={"status": "processando_autorizacao"},
            request=httpx.Request(method, url),
        )

    monkeypatch.setattr("app.nfse.providers.focus_nfe.httpx.request", fake_request)
    response = FocusNfeProvider("homologacao").issue("corepet-vet-1", {"teste": True})

    assert response["status"] == "processando_autorizacao"
    assert captured["method"] == "POST"
    assert captured["url"] == "https://homologacao.focusnfe.com.br/v2/nfse"
    assert captured["params"] == {"ref": "corepet-vet-1"}
    assert captured["auth"]._auth_header == "Basic dG9rZW4tdGVzdGU6"


def test_focus_provider_translates_validation_error(monkeypatch):
    monkeypatch.setenv("FOCUS_NFE_TOKEN_HOMOLOGACAO", "token-teste")

    def fake_request(method, url, **_kwargs):
        return httpx.Response(
            422,
            json={"mensagem": "Item da lista de servico invalido"},
            request=httpx.Request(method, url),
        )

    monkeypatch.setattr("app.nfse.providers.focus_nfe.httpx.request", fake_request)
    with pytest.raises(NfseProviderError) as exc_info:
        FocusNfeProvider("homologacao").issue("corepet-vet-1", {})

    assert exc_info.value.status_code == 422
    assert "Item da lista" in str(exc_info.value)
