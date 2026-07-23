"""Importadores de fontes regulatorias para o catalogo veterinario global."""

from __future__ import annotations

import json
import re
import urllib.parse
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Optional

from defusedxml import ElementTree as ET
from sqlalchemy.orm import Session

from app.veterinario_models import ProdutoRegulatorioVet

DAILYMED_SPLS_URL = "https://dailymed.nlm.nih.gov/dailymed/services/v2/spls.json"
DAILYMED_PRODUCT_URL = (
    "https://dailymed.nlm.nih.gov/dailymed/drugInfo.cfm?setid={setid}"
)
DAILYMED_PDF_URL = (
    "https://dailymed.nlm.nih.gov/dailymed/getFile.cfm?setid={setid}&type=pdf"
)
DAILYMED_DOCTYPES = {
    "50578-4": "prescription_animal_drug_label",
    "50577-6": "otc_animal_drug_label",
}
VMD_XML_URL = (
    "https://www.vmd.defra.gov.uk/productinformationdatabase/downloads/"
    "VMD_ProductInformationDatabase.xml"
)
VMD_SOURCE_PAGE = "https://www.vmd.defra.gov.uk/productinformationdatabase"


class RegulatorySourceSchemaError(RuntimeError):
    """A fonte respondeu, mas nao possui o contrato esperado."""


@dataclass
class ImportSummary:
    source: str
    dry_run: bool
    fetched: int = 0
    created: int = 0
    updated: int = 0
    unchanged: int = 0
    rejected: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "source": self.source,
            "dry_run": self.dry_run,
            "fetched": self.fetched,
            "created": self.created,
            "updated": self.updated,
            "unchanged": self.unchanged,
            "rejected": self.rejected,
        }


def _http_json(url: str, timeout_seconds: int = 45) -> dict[str, Any]:
    request = urllib.request.Request(
        url,
        headers={
            "Accept": "application/json",
            "User-Agent": "CorePet/1.0 (catalogo-veterinario; contato@corepet.com.br)",
        },
    )
    with urllib.request.urlopen(request, timeout=timeout_seconds) as response:
        payload = json.load(response)
    if not isinstance(payload, dict):
        raise RegulatorySourceSchemaError("DailyMed retornou payload nao-objeto.")
    return payload


def _http_bytes(url: str, timeout_seconds: int = 90) -> bytes:
    request = urllib.request.Request(
        url,
        headers={
            "Accept": "application/xml",
            "User-Agent": "CorePet/1.0 (catalogo-veterinario; contato@corepet.com.br)",
        },
    )
    with urllib.request.urlopen(request, timeout=timeout_seconds) as response:
        return response.read()


def _parse_dailymed_title(title: str) -> dict[str, Optional[str]]:
    original = re.sub(r"\s+", " ", str(title or "")).strip()
    if not original:
        raise RegulatorySourceSchemaError("DailyMed retornou item sem titulo.")

    manufacturer_match = re.search(r"\[([^\[\]]+)\]\s*$", original)
    manufacturer = manufacturer_match.group(1).strip() if manufacturer_match else None
    without_manufacturer = (
        original[: manufacturer_match.start()].strip()
        if manufacturer_match
        else original
    )

    ingredient_match = re.search(r"\(([^()]+)\)", without_manufacturer)
    ingredient = ingredient_match.group(1).strip() if ingredient_match else None
    commercial = (
        without_manufacturer[: ingredient_match.start()].strip(" -")
        if ingredient_match
        else without_manufacturer
    )
    dosage_form = (
        without_manufacturer[ingredient_match.end() :].strip(" -")
        if ingredient_match
        else None
    )

    return {
        "nome": without_manufacturer[:500],
        "nome_comercial": commercial[:255] or None,
        "principio_ativo": ingredient or None,
        "fabricante": manufacturer[:255] if manufacturer else None,
        "forma_farmaceutica": dosage_form[:150] if dosage_form else None,
    }


def _parse_dailymed_date(value: Any):
    texto = str(value or "").strip()
    if not texto:
        return None
    for pattern in ("%b %d, %Y", "%Y-%m-%d"):
        try:
            return datetime.strptime(texto, pattern).date()
        except ValueError:
            continue
    return None


def _validate_dailymed_page(payload: dict[str, Any]) -> tuple[list[dict], int]:
    metadata = payload.get("metadata")
    data = payload.get("data")
    if not isinstance(metadata, dict) or not isinstance(data, list):
        raise RegulatorySourceSchemaError(
            "Contrato DailyMed invalido: metadata/data ausentes."
        )
    try:
        total_pages = int(metadata["total_pages"])
    except (KeyError, TypeError, ValueError) as exc:
        raise RegulatorySourceSchemaError(
            "Contrato DailyMed invalido: total_pages ausente."
        ) from exc
    return data, max(total_pages, 1)


def _build_dailymed_row(item: dict[str, Any], doctype: str) -> dict[str, Any]:
    setid = str(item.get("setid") or "").strip()
    title = str(item.get("title") or "").strip()
    if not setid or not title:
        raise RegulatorySourceSchemaError(
            "Item DailyMed sem setid ou title; item colocado em quarentena."
        )
    parsed = _parse_dailymed_title(title)
    return {
        "fonte": "dailymed",
        "fonte_id": setid,
        "jurisdicao": "US",
        "status_regulatorio": "rotulo_publicado_status_aprovacao_nao_verificado",
        "tipo_documento": DAILYMED_DOCTYPES[doctype],
        **parsed,
        "especies_indicadas": None,
        "bula_url": DAILYMED_PDF_URL.format(setid=urllib.parse.quote(setid)),
        "pagina_fonte_url": DAILYMED_PRODUCT_URL.format(
            setid=urllib.parse.quote(setid)
        ),
        "publicado_em": _parse_dailymed_date(item.get("published_date")),
        "atualizado_na_fonte_em": datetime.now(timezone.utc),
        "metadados_fonte": {
            "spl_version": item.get("spl_version"),
            "published_date_raw": item.get("published_date"),
            "title_raw": title,
            "doctype": doctype,
        },
        "ativo": True,
    }


def _changed(existing: ProdutoRegulatorioVet, row: dict[str, Any]) -> bool:
    compared_fields = (
        "jurisdicao",
        "status_regulatorio",
        "tipo_documento",
        "nome",
        "nome_comercial",
        "principio_ativo",
        "fabricante",
        "forma_farmaceutica",
        "especies_indicadas",
        "bula_url",
        "pagina_fonte_url",
        "publicado_em",
        "metadados_fonte",
        "ativo",
    )
    return any(getattr(existing, field) != row[field] for field in compared_fields)


def _xml_text(element, tag: str) -> Optional[str]:
    node = element.find(tag)
    value = (
        re.sub(r"\s+", " ", str(node.text or "")).strip() if node is not None else ""
    )
    return value or None


def _split_vmd_species(value: Optional[str]) -> Optional[list[str]]:
    if not value:
        return None
    species = []
    for item in re.split(r"[,;/]|\band\b", value, flags=re.IGNORECASE):
        normalized = re.sub(r"\s+", " ", item).strip(" .")
        if normalized and normalized.casefold() not in {
            current.casefold() for current in species
        }:
            species.append(normalized)
    return species or None


def _build_vmd_row(element) -> dict[str, Any]:
    source_id = _xml_text(element, "VMDProductNo")
    name = _xml_text(element, "Name")
    spc_url = _xml_text(element, "SPC_Link")
    if not source_id or not name or not spc_url:
        raise RegulatorySourceSchemaError(
            "Item VMD sem identificador, nome ou SPC oficial."
        )
    issue_date = _parse_dailymed_date(_xml_text(element, "DateOfIssue"))
    territory = _xml_text(element, "Territory")
    return {
        "fonte": "vmd_uk",
        "fonte_id": source_id,
        "jurisdicao": "GB",
        "status_regulatorio": "autorizado_vmd",
        "tipo_documento": "summary_of_product_characteristics",
        "nome": name[:500],
        "nome_comercial": name[:255],
        "principio_ativo": _xml_text(element, "ActiveSubstances"),
        "fabricante": (_xml_text(element, "MAHolder") or "")[:255] or None,
        "forma_farmaceutica": (
            (_xml_text(element, "PharmaceuticalForm") or "")[:150] or None
        ),
        "especies_indicadas": _split_vmd_species(_xml_text(element, "TargetSpecies")),
        "bula_url": spc_url,
        "pagina_fonte_url": VMD_SOURCE_PAGE,
        "publicado_em": issue_date,
        "atualizado_na_fonte_em": datetime.now(timezone.utc),
        "metadados_fonte": {
            "vm_number": _xml_text(element, "VMNo"),
            "territory": territory,
            "authorisation_route": _xml_text(element, "AuthorisationRoute"),
            "distribution_category": _xml_text(element, "DistributionCategory"),
            "therapeutic_group": _xml_text(element, "TherapeuticGroup"),
            "controlled_drug": _xml_text(element, "ControlledDrug"),
            "ukpar_url": _xml_text(element, "UKPAR_Link"),
            "paar_url": _xml_text(element, "PAAR_Link"),
        },
        "ativo": True,
    }


def parse_vmd_current_products(xml_payload: bytes) -> list[dict[str, Any]]:
    """Parse the official VMD snapshot, keeping only currently authorised products."""
    try:
        root = ET.fromstring(xml_payload)
    except ET.ParseError as exc:
        raise RegulatorySourceSchemaError("VMD retornou XML invalido.") from exc

    rows = []
    for element in root.findall("./CurrentAuthorisedProducts"):
        try:
            rows.append(_build_vmd_row(element))
        except RegulatorySourceSchemaError:
            continue
    if not rows:
        raise RegulatorySourceSchemaError(
            "VMD nao retornou produtos atualmente autorizados."
        )
    return rows


def import_vmd_authorised_products(
    db: Session,
    *,
    dry_run: bool = True,
    xml_payload: Optional[bytes] = None,
    limit: Optional[int] = None,
) -> dict[str, Any]:
    """Import official UK veterinary products and SPC links under OGL v3."""
    summary = ImportSummary(source="vmd_uk", dry_run=dry_run)
    rows = parse_vmd_current_products(xml_payload or _http_bytes(VMD_XML_URL))
    if limit is not None:
        rows = rows[: max(1, int(limit))]

    for row in rows:
        summary.fetched += 1
        if dry_run:
            continue
        existing = (
            db.query(ProdutoRegulatorioVet)
            .filter(
                ProdutoRegulatorioVet.fonte == row["fonte"],
                ProdutoRegulatorioVet.fonte_id == row["fonte_id"],
            )
            .first()
        )
        if existing is None:
            db.add(ProdutoRegulatorioVet(**row))
            summary.created += 1
        elif _changed(existing, row):
            for field, value in row.items():
                setattr(existing, field, value)
            summary.updated += 1
        else:
            summary.unchanged += 1

    if not dry_run:
        db.flush()
    return summary.to_dict()


def import_dailymed_animal_labels(
    db: Session,
    *,
    dry_run: bool = True,
    max_pages: Optional[int] = None,
) -> dict[str, Any]:
    """Importa metadados e links de bulas; nao afirma aprovacao sem validar o SPL."""

    summary = ImportSummary(source="dailymed", dry_run=dry_run)

    for doctype in DAILYMED_DOCTYPES:
        page = 1
        total_pages = 1
        while page <= total_pages:
            if max_pages is not None and page > max_pages:
                break
            query = urllib.parse.urlencode(
                {"doctype": doctype, "pagesize": 100, "page": page}
            )
            payload = _http_json(f"{DAILYMED_SPLS_URL}?{query}")
            items, total_pages = _validate_dailymed_page(payload)
            for item in items:
                summary.fetched += 1
                try:
                    row = _build_dailymed_row(item, doctype)
                except RegulatorySourceSchemaError:
                    summary.rejected += 1
                    continue

                if dry_run:
                    continue

                existing = (
                    db.query(ProdutoRegulatorioVet)
                    .filter(
                        ProdutoRegulatorioVet.fonte == row["fonte"],
                        ProdutoRegulatorioVet.fonte_id == row["fonte_id"],
                    )
                    .first()
                )
                if existing is None:
                    db.add(ProdutoRegulatorioVet(**row))
                    summary.created += 1
                elif _changed(existing, row):
                    for field, value in row.items():
                        setattr(existing, field, value)
                    summary.updated += 1
                else:
                    summary.unchanged += 1

            if not dry_run:
                db.flush()
            page += 1

    return summary.to_dict()
