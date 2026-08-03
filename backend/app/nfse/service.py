from __future__ import annotations

import hashlib
import json
import re
import unicodedata
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any
from zoneinfo import ZoneInfo

from app.models import Tenant
from app.models_cadastros import Cliente
from app.nfse.models import NfseDocument, NfseTenantConfig


PRESIDENTE_PRUDENTE_IBGE = "3541406"


def digits(value: str | None) -> str:
    return re.sub(r"\D", "", value or "")


def _valid_cpf(value: str) -> bool:
    if len(value) != 11 or len(set(value)) == 1:
        return False
    for length in (9, 10):
        total = sum(int(value[index]) * (length + 1 - index) for index in range(length))
        check_digit = (total * 10) % 11
        if check_digit == 10:
            check_digit = 0
        if check_digit != int(value[length]):
            return False
    return True


def _valid_cnpj(value: str) -> bool:
    if len(value) != 14 or len(set(value)) == 1:
        return False
    weights = (
        (5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2),
        (6, 5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2),
    )
    base = value[:12]
    for weight in weights:
        total = sum(
            int(number) * multiplier for number, multiplier in zip(base, weight)
        )
        remainder = total % 11
        base += str(0 if remainder < 2 else 11 - remainder)
    return base == value


def _normalized_text(value: str | None) -> str:
    normalized = unicodedata.normalize("NFKD", value or "")
    return "".join(
        char for char in normalized if not unicodedata.combining(char)
    ).lower()


def is_presidente_prudente(city: str | None, state: str | None) -> bool:
    return (
        _normalized_text(city).strip() == "presidente prudente"
        and (state or "").upper() == "SP"
    )


def configuration_missing_fields(
    tenant: Tenant,
    config: NfseTenantConfig,
    *,
    token_configured: bool,
) -> list[str]:
    missing: list[str] = []
    if not _valid_cnpj(digits(tenant.cnpj)):
        missing.append("CNPJ da clinica")
    if not (tenant.razao_social or "").strip():
        missing.append("razao social da clinica")
    if not (tenant.inscricao_municipal or "").strip():
        missing.append("inscricao municipal da clinica")
    if not is_presidente_prudente(tenant.cidade, tenant.uf):
        missing.append("municipio Presidente Prudente/SP no cadastro da clinica")
    if config.municipality_code != PRESIDENTE_PRUDENTE_IBGE:
        missing.append("codigo IBGE 3541406")
    service_item = (config.service_list_item or "").strip()
    if not re.fullmatch(r"\d{1,2}\.\d{2}", service_item):
        missing.append("item da lista de servicos da LC 116")
    if config.iss_rate is None:
        missing.append("aliquota de ISS validada pela contabilidade")
    if not token_configured:
        missing.append(f"token Focus NFe de {config.environment}")
    return missing


def infer_customer_municipality_code(
    customer: Cliente, informed_code: str | None
) -> str | None:
    if informed_code and len(digits(informed_code)) == 7:
        return digits(informed_code)
    if is_presidente_prudente(customer.cidade, customer.estado):
        return PRESIDENTE_PRUDENTE_IBGE
    return None


def customer_document(customer: Cliente) -> str:
    cnpj = digits(customer.cnpj)
    if _valid_cnpj(cnpj):
        return cnpj
    cpf = digits(customer.cpf)
    if _valid_cpf(cpf):
        return cpf
    return ""


def customer_missing_fields(
    customer: Cliente, municipality_code: str | None
) -> list[str]:
    missing: list[str] = []
    document = customer_document(customer)
    if len(document) not in {11, 14}:
        missing.append("CPF ou CNPJ do tutor")
    for field, label in (
        (customer.endereco, "logradouro do tutor"),
        (customer.numero, "numero do endereco do tutor"),
        (customer.bairro, "bairro do tutor"),
        (customer.cidade, "cidade do tutor"),
        (customer.estado, "UF do tutor"),
        (customer.cep, "CEP do tutor"),
    ):
        if not (field or "").strip():
            missing.append(label)
    if not municipality_code:
        missing.append("codigo IBGE do municipio do tutor")
    return missing


def build_focus_payload(
    *,
    tenant: Tenant,
    config: NfseTenantConfig,
    customer: Cliente,
    customer_municipality_code: str,
    service_amount: Decimal,
    description: str,
    customer_email: str | None = None,
    issued_at: datetime | None = None,
) -> dict[str, Any]:
    document = customer_document(customer)
    customer_document_payload = {"cpf" if len(document) == 11 else "cnpj": document}
    issue_time = issued_at or datetime.now(ZoneInfo("America/Sao_Paulo"))
    if issue_time.tzinfo is None:
        issue_time = issue_time.replace(tzinfo=ZoneInfo("America/Sao_Paulo"))

    taker: dict[str, Any] = {
        **customer_document_payload,
        "razao_social": (customer.razao_social or customer.nome).strip(),
        "endereco": {
            "logradouro": (customer.endereco or "").strip(),
            "numero": (customer.numero or "").strip(),
            "bairro": (customer.bairro or "").strip(),
            "codigo_municipio": int(customer_municipality_code),
            "uf": (customer.estado or "").upper(),
            "cep": digits(customer.cep),
        },
    }
    if customer.complemento:
        taker["endereco"]["complemento"] = customer.complemento.strip()
    if customer.telefone or customer.celular:
        taker["telefone"] = digits(customer.telefone or customer.celular)
    email = (customer_email or customer.email or "").strip()
    if email:
        taker["email"] = email

    service: dict[str, Any] = {
        "discriminacao": description.strip(),
        "valor_servicos": float(service_amount),
        "aliquota": float(config.iss_rate or 0),
        "item_lista_servico": (config.service_list_item or "").strip(),
        "iss_retido": bool(config.iss_withheld),
    }
    if config.cnae_code:
        service["codigo_cnae"] = digits(config.cnae_code)

    payload: dict[str, Any] = {
        "data_emissao": issue_time.isoformat(),
        "natureza_operacao": int(config.operation_nature),
        "optante_simples_nacional": bool(config.simple_national),
        "incentivador_cultural": bool(config.cultural_incentive),
        "prestador": {
            "cnpj": digits(tenant.cnpj),
            "inscricao_municipal": (tenant.inscricao_municipal or "").strip(),
            "codigo_municipio": int(config.municipality_code),
        },
        "tomador": taker,
        "servico": service,
    }
    if config.special_tax_regime:
        payload["regime_especial_tributacao"] = int(config.special_tax_regime)
    return payload


def request_fingerprint(payload: dict[str, Any]) -> str:
    canonical = json.dumps(
        payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _first(payload: dict[str, Any], *keys: str) -> Any:
    for key in keys:
        value = payload.get(key)
        if value not in (None, ""):
            return value
    return None


def apply_provider_response(document: NfseDocument, payload: dict[str, Any]) -> None:
    provider_status = str(_first(payload, "status", "status_nfse") or "").lower()
    status_map = {
        "processando_autorizacao": "processing",
        "processando": "processing",
        "autorizado": "authorized",
        "autorizada": "authorized",
        "cancelado": "cancelled",
        "cancelada": "cancelled",
        "erro_autorizacao": "authorization_error",
        "erro_cancelamento": "cancellation_error",
    }
    document.provider_status = provider_status or document.provider_status
    document.status = status_map.get(provider_status, document.status)
    document.invoice_number = (
        str(
            _first(payload, "numero", "numero_nfse", "numero_nota")
            or document.invoice_number
            or ""
        )
        or None
    )
    document.verification_code = (
        str(
            _first(payload, "codigo_verificacao", "codigo_verificacao_nfse")
            or document.verification_code
            or ""
        )
        or None
    )
    document.access_key = (
        str(_first(payload, "chave_nfse", "chave_acesso") or document.access_key or "")
        or None
    )
    document.pdf_url = (
        str(
            _first(payload, "url", "url_danfse", "caminho_danfe")
            or document.pdf_url
            or ""
        )
        or None
    )
    document.xml_url = (
        str(
            _first(payload, "caminho_xml_nota_fiscal", "url_xml", "caminho_xml")
            or document.xml_url
            or ""
        )
        or None
    )
    document.error_code = str(_first(payload, "codigo_erro", "codigo") or "") or None
    document.error_message = (
        str(_first(payload, "mensagem", "mensagem_sefaz", "erro") or "") or None
    )
    document.provider_response = payload
    now = datetime.now(timezone.utc)
    if document.status == "authorized" and document.authorized_at is None:
        document.authorized_at = now
    if document.status == "cancelled" and document.cancelled_at is None:
        document.cancelled_at = now


def serialize_document(document: NfseDocument) -> dict[str, Any]:
    return {
        "id": document.id,
        "reference": document.reference,
        "status": document.status,
        "provider_status": document.provider_status,
        "environment": document.environment,
        "origin_type": document.origin_type,
        "origin_id": document.origin_id,
        "consultation_id": document.consultation_id,
        "service_amount": float(document.service_amount),
        "description": document.description,
        "invoice_number": document.invoice_number,
        "verification_code": document.verification_code,
        "access_key": document.access_key,
        "pdf_url": document.pdf_url,
        "xml_url": document.xml_url,
        "error_code": document.error_code,
        "error_message": document.error_message,
        "created_at": document.created_at,
        "updated_at": document.updated_at,
        "authorized_at": document.authorized_at,
        "cancelled_at": document.cancelled_at,
    }
