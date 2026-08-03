from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal
from types import SimpleNamespace
from uuid import uuid4

import httpx
import pytest
from cryptography import x509
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives.serialization import BestAvailableEncryption, pkcs12
from cryptography.x509.oid import NameOID

from app.nfse.models import NfseDocument, NfseTenantConfig
from app.nfse.providers.base import NfseProviderError
from app.nfse.providers.focus_nfe import FocusNfeCompanyProvider, FocusNfeProvider
from app.nfse.routes import router as nfse_router
from app.nfse.secrets import decrypt_nfse_secret, encrypt_nfse_secret
from app.nfse.service import (
    PRESIDENTE_PRUDENTE_IBGE,
    build_focus_payload,
    configuration_missing_fields,
    customer_missing_fields,
    infer_customer_municipality_code,
    request_fingerprint,
    validate_certificate_for_cnpj,
)
from app.services.sefaz_tenant_config_service import SefazTenantConfigService


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


def _integration(**overrides):
    data = {
        "environment": "homologacao",
        "provider_onboarding_completed_at": datetime.fromisoformat(
            "2026-08-03T10:00:00-03:00"
        ),
    }
    data.update(overrides)
    return SimpleNamespace(**data)


def _fiscal(**overrides):
    data = {
        "regime_tributario": "Simples Nacional",
        "simples_ativo": True,
        "municipio_iss_codigo": PRESIDENTE_PRUDENTE_IBGE,
        "nfse_item_lista_servico": "5.01",
        "cnae_principal": "7500100",
        "iss_aliquota": Decimal("2.00"),
        "iss_retido": False,
        "nfse_natureza_operacao": "1",
        "nfse_regime_especial_tributacao": "6",
        "nfse_incentivador_cultural": False,
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
    assert ("PUT", "/nfse/credenciais-municipais") in routes
    assert ("PUT", "/nfse/credenciais-focus") in routes
    assert ("POST", "/nfse/vinculacao-focus") in routes
    assert ("POST", "/nfse/configuracao/pre-validar") in routes
    assert ("POST", "/nfse/consultas/{consultation_id}/emitir") in routes
    assert ("GET", "/nfse/consultas/{consultation_id}") in routes
    assert ("POST", "/nfse/documentos/{document_id}/sincronizar") in routes
    assert ("POST", "/nfse/documentos/{document_id}/cancelar") in routes


def test_presidente_prudente_configuration_reports_only_real_pending_fields():
    missing = configuration_missing_fields(
        _tenant(), _fiscal(), _integration(), token_configured=True
    )
    assert missing == []

    missing = configuration_missing_fields(
        _tenant(inscricao_municipal=None),
        _fiscal(nfse_item_lista_servico=None),
        _integration(),
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
        fiscal=_fiscal(),
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
        fiscal=_fiscal(),
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


def test_focus_company_provider_uses_master_token_and_dry_run(monkeypatch):
    monkeypatch.setenv("FOCUS_NFE_MASTER_TOKEN", "token-master")
    captured = {}

    def fake_request(method, url, **kwargs):
        captured.update(method=method, url=url, **kwargs)
        return httpx.Response(
            200,
            json={"id": 123},
            request=httpx.Request(method, url),
        )

    monkeypatch.setattr("app.nfse.providers.focus_nfe.httpx.request", fake_request)
    response = FocusNfeCompanyProvider().create(
        {"cnpj": "11222333000181"}, dry_run=True
    )

    assert response == {"id": 123}
    assert captured["url"] == "https://api.focusnfe.com.br/v2/empresas"
    assert captured["params"] == {"dry_run": 1}
    assert captured["auth"]._auth_header == "Basic dG9rZW4tbWFzdGVyOg=="


def test_municipal_credentials_are_prefixed_and_never_saved_as_plaintext(monkeypatch):
    monkeypatch.setattr("app.nfse.secrets.is_encryption_enabled", lambda: True)
    monkeypatch.setattr(
        "app.nfse.secrets.encrypt_data", lambda value: f"cipher-{value}"
    )
    monkeypatch.setattr(
        "app.nfse.secrets.decrypt_data", lambda value: value.removeprefix("cipher-")
    )

    stored = encrypt_nfse_secret("senha-municipal")
    assert stored == "fernet:cipher-senha-municipal"
    assert "senha-municipal" != stored
    assert decrypt_nfse_secret(stored) == "senha-municipal"


def test_existing_a1_is_validated_against_expiry_and_company_cnpj(tmp_path):
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    subject = x509.Name(
        [
            x509.NameAttribute(NameOID.COMMON_NAME, "Clinica Teste:11222333000181"),
            x509.NameAttribute(NameOID.SERIAL_NUMBER, "11222333000181"),
        ]
    )
    now = datetime.now(timezone.utc)
    certificate = (
        x509.CertificateBuilder()
        .subject_name(subject)
        .issuer_name(subject)
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now - timedelta(days=1))
        .not_valid_after(now + timedelta(days=30))
        .sign(key, hashes.SHA256())
    )
    pfx_path = tmp_path / "empresa.pfx"
    pfx_path.write_bytes(
        pkcs12.serialize_key_and_certificates(
            b"empresa",
            key,
            certificate,
            None,
            BestAvailableEncryption(b"senha-segura"),
        )
    )

    valid, message = validate_certificate_for_cnpj(
        str(pfx_path), "senha-segura", "11.222.333/0001-81"
    )
    wrong_company, _ = validate_certificate_for_cnpj(
        str(pfx_path), "senha-segura", "11.444.777/0001-61"
    )

    assert valid is True
    assert "valido ate" in message
    assert wrong_company is False


def test_sefaz_certificate_password_is_encrypted_at_rest(tmp_path, monkeypatch):
    monkeypatch.setattr(SefazTenantConfigService, "BASE_DIR", tmp_path)
    monkeypatch.setattr(
        "app.services.sefaz_tenant_config_service.is_encryption_enabled", lambda: True
    )
    monkeypatch.setattr(
        "app.services.sefaz_tenant_config_service.encrypt_data",
        lambda _value: "opaque-ciphertext",
    )
    monkeypatch.setattr(
        "app.services.sefaz_tenant_config_service.decrypt_data",
        lambda _value: "senha-a1",
    )
    tenant_id = uuid4()

    SefazTenantConfigService.save_config(
        tenant_id, {"cert_path": "cert.pfx", "cert_password": "senha-a1"}
    )
    stored = SefazTenantConfigService._config_path(tenant_id).read_text(
        encoding="utf-8"
    )

    assert "senha-a1" not in stored
    assert "fernet:opaque-ciphertext" in stored
    assert (
        SefazTenantConfigService.load_config(tenant_id)["cert_password"] == "senha-a1"
    )
