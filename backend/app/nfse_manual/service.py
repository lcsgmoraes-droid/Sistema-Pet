from __future__ import annotations

import hashlib
import re
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any, Iterable

from fastapi import HTTPException

from app.nfse_manual.models import NfseManualDocument


PRESIDENTE_PRUDENTE_PORTAL = "https://issprudente.sp.gov.br/"
PRIVATE_UPLOAD_ROOT = Path(__file__).resolve().parents[2] / "uploads" / "nfse_manual"
MAX_PDF_BYTES = 10 * 1024 * 1024
MAX_XML_BYTES = 5 * 1024 * 1024


def digits(value: str | None) -> str:
    return re.sub(r"\D", "", value or "")


def _text(value: Any) -> str:
    return str(value or "").strip()


def _money(value: Any) -> Decimal:
    try:
        return Decimal(str(value or 0)).quantize(Decimal("0.01"))
    except (InvalidOperation, ValueError, TypeError):
        return Decimal("0.00")


def _customer_document(customer) -> str:
    cnpj = digits(getattr(customer, "cnpj", None))
    if len(cnpj) == 14:
        return cnpj
    cpf = digits(getattr(customer, "cpf", None))
    return cpf if len(cpf) == 11 else ""


def _missing_fields(*, tenant, customer, fiscal, amount: Decimal, description: str):
    missing: list[str] = []
    checks = (
        (digits(getattr(tenant, "cnpj", None)), "CNPJ da empresa"),
        (getattr(tenant, "razao_social", None), "razão social da empresa"),
        (getattr(tenant, "inscricao_municipal", None), "inscrição municipal"),
        (_customer_document(customer), "CPF ou CNPJ do cliente"),
        (getattr(customer, "nome", None), "nome do cliente"),
        (getattr(customer, "endereco", None), "logradouro do cliente"),
        (getattr(customer, "numero", None), "número do endereço do cliente"),
        (getattr(customer, "bairro", None), "bairro do cliente"),
        (getattr(customer, "cidade", None), "cidade do cliente"),
        (getattr(customer, "estado", None), "UF do cliente"),
        (getattr(customer, "cep", None), "CEP do cliente"),
        (getattr(fiscal, "nfse_item_lista_servico", None), "item da lista de serviços"),
        (getattr(fiscal, "municipio_iss", None), "município de incidência do ISS"),
        (getattr(fiscal, "municipio_iss_codigo", None), "código IBGE do município"),
        (getattr(fiscal, "iss_aliquota", None), "alíquota de ISS"),
        (description, "descrição do serviço"),
    )
    for value, label in checks:
        if value is None or not _text(value):
            missing.append(label)
    if amount <= 0:
        missing.append("valor dos serviços")
    return missing


def build_preparation_snapshot(
    *, tenant, customer, fiscal, consultation, amount: Decimal, description: str
) -> dict[str, Any]:
    missing = _missing_fields(
        tenant=tenant,
        customer=customer,
        fiscal=fiscal,
        amount=amount,
        description=description,
    )
    is_prudente = (
        _text(getattr(tenant, "cidade", None)).lower() == "presidente prudente"
        and _text(getattr(tenant, "uf", None)).upper() == "SP"
    )
    portal_url = _text(getattr(fiscal, "nfse_portal_url", None)) or (
        PRESIDENTE_PRUDENTE_PORTAL if is_prudente else ""
    )
    if not portal_url:
        missing.append("endereço do portal municipal de NFS-e")
    return {
        "portal_url": portal_url or None,
        "ready": not missing,
        "missing_fields": missing,
        "company": {
            "cnpj": digits(getattr(tenant, "cnpj", None)),
            "legal_name": _text(getattr(tenant, "razao_social", None)),
            "municipal_registration": _text(
                getattr(tenant, "inscricao_municipal", None)
            ),
            "city": _text(getattr(tenant, "cidade", None)),
            "state": _text(getattr(tenant, "uf", None)).upper(),
        },
        "customer": {
            "name": _text(
                getattr(customer, "razao_social", None)
                or getattr(customer, "nome", None)
            ),
            "document": _customer_document(customer),
            "email": _text(getattr(customer, "email", None)),
            "phone": _text(
                getattr(customer, "celular", None)
                or getattr(customer, "telefone", None)
            ),
            "address": _text(getattr(customer, "endereco", None)),
            "number": _text(getattr(customer, "numero", None)),
            "complement": _text(getattr(customer, "complemento", None)),
            "district": _text(getattr(customer, "bairro", None)),
            "city": _text(getattr(customer, "cidade", None)),
            "state": _text(getattr(customer, "estado", None)).upper(),
            "postal_code": digits(getattr(customer, "cep", None)),
        },
        "service": {
            "description": description.strip(),
            "amount": float(amount),
            "service_code": _text(getattr(fiscal, "nfse_item_lista_servico", None)),
            "tax_city": _text(getattr(fiscal, "municipio_iss", None)),
            "tax_city_code": digits(getattr(fiscal, "municipio_iss_codigo", None)),
            "cnae": digits(getattr(fiscal, "cnae_principal", None)),
            "iss_rate": (
                float(fiscal.iss_aliquota)
                if getattr(fiscal, "iss_aliquota", None) is not None
                else None
            ),
            "iss_withheld": bool(getattr(fiscal, "iss_retido", False)),
            "operation_nature": _text(
                getattr(fiscal, "nfse_natureza_operacao", None) or "1"
            ),
            "special_tax_regime": _text(
                getattr(fiscal, "nfse_regime_especial_tributacao", None)
            ),
        },
        "origin": {
            "type": "veterinary_consultation",
            "consultation_id": consultation.id,
            "finished_at": (
                consultation.finalizado_em.isoformat()
                if getattr(consultation, "finalizado_em", None)
                else None
            ),
        },
    }


def build_copy_text(snapshot: dict[str, Any]) -> str:
    company = snapshot.get("company") or {}
    customer = snapshot.get("customer") or {}
    service = snapshot.get("service") or {}
    address = ", ".join(
        part
        for part in (
            customer.get("address"),
            customer.get("number"),
            customer.get("complement"),
            customer.get("district"),
        )
        if part
    )
    city = "/".join(
        part for part in (customer.get("city"), customer.get("state")) if part
    )
    iss_rate = service.get("iss_rate")
    iss_text = "não informado" if iss_rate is None else f"{iss_rate:.2f}%"
    return "\n".join(
        [
            "DADOS PARA EMISSÃO MANUAL DA NFS-e",
            "",
            "PRESTADOR",
            f"Razão social: {company.get('legal_name') or '-'}",
            f"CNPJ: {company.get('cnpj') or '-'}",
            f"Inscrição municipal: {company.get('municipal_registration') or '-'}",
            "",
            "TOMADOR",
            f"Nome/Razão social: {customer.get('name') or '-'}",
            f"CPF/CNPJ: {customer.get('document') or '-'}",
            f"E-mail: {customer.get('email') or '-'}",
            f"Telefone: {customer.get('phone') or '-'}",
            f"Endereço: {address or '-'}",
            f"Cidade/UF: {city or '-'}",
            f"CEP: {customer.get('postal_code') or '-'}",
            "",
            "SERVIÇO",
            f"Descrição: {service.get('description') or '-'}",
            f"Valor: R$ {float(service.get('amount') or 0):.2f}".replace(".", ","),
            f"Item da lista: {service.get('service_code') or '-'}",
            "Município do ISS: "
            f"{service.get('tax_city') or '-'}"
            f" (IBGE {service.get('tax_city_code') or '-'})",
            f"CNAE: {service.get('cnae') or '-'}",
            f"Alíquota ISS: {iss_text.replace('.', ',')}",
            f"ISS retido: {'Sim' if service.get('iss_withheld') else 'Não'}",
        ]
    )


def serialize_document(document: NfseManualDocument) -> dict[str, Any]:
    snapshot = document.preparation_snapshot or {}
    return {
        "id": document.id,
        "reference": document.reference,
        "status": document.status,
        "origin_type": document.origin_type,
        "origin_id": document.origin_id,
        "consultation_id": document.consultation_id,
        "customer_id": document.customer_id,
        "customer_name": (snapshot.get("customer") or {}).get("name"),
        "service_amount": float(document.service_amount),
        "description": document.description,
        "service_code": document.service_code,
        "iss_rate": float(document.iss_rate) if document.iss_rate is not None else None,
        "iss_withheld": bool(document.iss_withheld),
        "invoice_number": document.invoice_number,
        "verification_code": document.verification_code,
        "issued_at": document.issued_at,
        "notes": document.notes,
        "cancelled_at": document.cancelled_at,
        "cancellation_reason": document.cancellation_reason,
        "has_pdf": bool(document.pdf_file_name),
        "has_xml": bool(document.xml_file_name),
        "snapshot": snapshot,
        "copy_text": build_copy_text(snapshot),
        "portal_url": snapshot.get("portal_url"),
        "created_at": document.created_at,
        "updated_at": document.updated_at,
    }


def _local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1].lower()


def _first_xml_text(root: ET.Element, names: Iterable[str]) -> str | None:
    wanted = {name.lower() for name in names}
    for element in root.iter():
        if _local_name(element.tag) in wanted and _text(element.text):
            return _text(element.text)
    return None


def _parse_xml_datetime(value: str | None) -> datetime | None:
    if not value:
        return None
    normalized = value.strip().replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError:
        try:
            parsed = datetime.strptime(normalized[:10], "%Y-%m-%d")
        except ValueError:
            return None
    return parsed.replace(tzinfo=parsed.tzinfo or timezone.utc)


def parse_nfse_xml(content: bytes) -> dict[str, Any]:
    upper = content[:4096].upper()
    if b"<!DOCTYPE" in upper or b"<!ENTITY" in upper:
        raise HTTPException(status_code=422, detail="XML com estrutura não permitida.")
    try:
        root = ET.fromstring(content)
    except ET.ParseError as exc:
        raise HTTPException(
            status_code=422, detail="O arquivo XML é inválido."
        ) from exc

    amount_text = _first_xml_text(root, ("vServ", "ValorServicos", "ValorServico"))
    amount = None
    if amount_text:
        try:
            normalized_amount = (
                amount_text.replace(".", "").replace(",", ".")
                if "," in amount_text
                else amount_text
            )
            amount = Decimal(normalized_amount)
        except InvalidOperation:
            amount = None
    invoice_number = _first_xml_text(
        root, ("nNFSe", "NumeroNfse", "NumeroNFSe", "NumeroNota")
    )
    if not invoice_number:
        for element in root.iter():
            if _local_name(element.tag) == "infnfse":
                invoice_number = _first_xml_text(element, ("Numero",))
                if invoice_number:
                    break
    return {
        "invoice_number": invoice_number,
        "verification_code": _first_xml_text(
            root, ("CodigoVerificacao", "CodigoDeVerificacao", "cVerif")
        ),
        "issued_at": _parse_xml_datetime(
            _first_xml_text(root, ("dhEmi", "DataEmissao", "dEmi"))
        ),
        "service_amount": amount,
    }


def validate_attachment(kind: str, filename: str | None, content: bytes) -> None:
    if kind not in {"pdf", "xml"}:
        raise HTTPException(status_code=404, detail="Tipo de anexo inválido.")
    if not content:
        raise HTTPException(status_code=422, detail="O arquivo está vazio.")
    suffix = Path(filename or "").suffix.lower()
    if suffix != f".{kind}":
        raise HTTPException(status_code=422, detail=f"Envie um arquivo {kind.upper()}.")
    limit = MAX_PDF_BYTES if kind == "pdf" else MAX_XML_BYTES
    if len(content) > limit:
        raise HTTPException(
            status_code=413,
            detail=f"O {kind.upper()} ultrapassa o limite permitido.",
        )
    if kind == "pdf" and not content.startswith(b"%PDF"):
        raise HTTPException(status_code=422, detail="O conteúdo não é um PDF válido.")
    if kind == "xml":
        parse_nfse_xml(content)


def store_attachment(*, tenant_id, document_id: int, kind: str, content: bytes) -> str:
    folder = PRIVATE_UPLOAD_ROOT / str(tenant_id) / str(document_id)
    folder.mkdir(parents=True, exist_ok=True)
    filename = f"nfse.{kind}"
    (folder / filename).write_bytes(content)
    return filename


def attachment_path(*, tenant_id, document_id: int, filename: str | None) -> Path:
    if filename not in {"nfse.pdf", "nfse.xml"}:
        raise HTTPException(status_code=404, detail="Anexo não encontrado.")
    path = PRIVATE_UPLOAD_ROOT / str(tenant_id) / str(document_id) / filename
    if not path.is_file():
        raise HTTPException(status_code=404, detail="Anexo não encontrado.")
    return path


def sha256_hex(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()
