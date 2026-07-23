from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from sqlalchemy.orm import Session

from app.services.tenant_onboarding_core import OnboardingResult
from app.services.tenant_onboarding_item_installs import (
    _mapped_template_row_id,
    _record_template_item_install,
)
from app.services.tenant_onboarding_sql import _execute_insert, _scalar
from app.veterinario_models import CatalogoProcedimento

_VET_PROCEDURES_PATH = (
    Path(__file__).resolve().parents[1] / "catalogos" / "vet_procedimentos_v1.json"
)


def load_vet_procedure_templates() -> list[dict[str, Any]]:
    with _VET_PROCEDURES_PATH.open("r", encoding="utf-8") as source:
        return json.load(source)


def vet_procedure_template_status(db: Session, tenant_id) -> dict[str, int]:
    templates = load_vet_procedure_templates()
    template_names = {item["name"].strip().casefold() for item in templates}
    existing_names = {
        str(name or "").strip().casefold()
        for (name,) in (
            db.query(CatalogoProcedimento.nome)
            .filter(
                CatalogoProcedimento.tenant_id == tenant_id,
                CatalogoProcedimento.ativo.is_(True),
            )
            .all()
        )
    }
    installed = len(template_names & existing_names)
    return {
        "total_modelo": len(template_names),
        "ja_disponiveis": installed,
        "disponiveis_para_importar": len(template_names) - installed,
    }


def import_missing_vet_procedure_templates(
    db: Session,
    tenant_id,
) -> dict[str, int]:
    """Explicit tenant action: import or reactivate missing CorePet procedures."""
    templates = load_vet_procedure_templates()
    existing = (
        db.query(CatalogoProcedimento)
        .filter(CatalogoProcedimento.tenant_id == tenant_id)
        .all()
    )
    by_name = {str(item.nome or "").strip().casefold(): item for item in existing}
    created = 0
    reactivated = 0
    skipped = 0

    for template in templates:
        name = str(template["name"]).strip()
        current = by_name.get(name.casefold())
        if current and current.ativo:
            skipped += 1
            continue
        if current:
            current.ativo = True
            current.descricao = current.descricao or template.get("descricao")
            current.categoria = current.categoria or template.get("categoria")
            current.duracao_minutos = current.duracao_minutos or template.get(
                "duracao_minutos"
            )
            current.observacoes = current.observacoes or (
                "Modelo inicial CorePet. Configure preço, insumos e protocolo da clínica."
            )
            reactivated += 1
            continue

        db.add(
            CatalogoProcedimento(
                tenant_id=tenant_id,
                nome=name,
                descricao=template.get("descricao"),
                categoria=template.get("categoria"),
                valor_padrao=None,
                duracao_minutos=template.get("duracao_minutos"),
                requer_anestesia=bool(template.get("requer_anestesia", False)),
                observacoes=(
                    "Modelo inicial CorePet. Configure preço, insumos e "
                    "protocolo da clínica."
                ),
                insumos=None,
                ativo=True,
            )
        )
        created += 1

    db.flush()
    return {
        "criados": created,
        "reativados": reactivated,
        "ignorados": skipped,
    }


def _copy_vet_procedures(
    db: Session,
    items: list[dict[str, Any]],
    tenant_id: str,
    result: OnboardingResult,
) -> None:
    for item in items:
        payload = item["payload"]
        mapped_id = _mapped_template_row_id(
            db,
            tenant_id,
            result,
            item,
            "vet_catalogo_procedimentos",
        )
        if mapped_id:
            result.bump("skipped", "vet_procedures")
            continue

        existing_id = _scalar(
            db,
            """
            SELECT id
            FROM vet_catalogo_procedimentos
            WHERE {tenant_filter}
              AND lower(nome) = lower(:nome)
            LIMIT 1
            """,
            {"nome": payload["nome"]},
            tenant_id,
        )
        if existing_id:
            _record_template_item_install(
                db,
                tenant_id,
                None,
                result,
                item,
                "vet_catalogo_procedimentos",
                existing_id,
            )
            result.bump("skipped", "vet_procedures")
            continue

        if result.dry_run:
            result.bump("would_create", "vet_procedures")
            continue

        _execute_insert(
            db,
            """
            INSERT INTO vet_catalogo_procedimentos (
                tenant_id, nome, descricao, categoria, valor_padrao,
                duracao_minutos, requer_anestesia, observacoes, insumos,
                ativo, created_at, updated_at
            ) VALUES (
                :tenant_id, :nome, :descricao, :categoria, NULL,
                :duracao_minutos, :requer_anestesia, :observacoes, NULL,
                :ativo, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
            )
            """,
            {
                "tenant_id": tenant_id,
                "nome": payload["nome"],
                "descricao": payload.get("descricao"),
                "categoria": payload.get("categoria"),
                "duracao_minutos": payload.get("duracao_minutos"),
                "requer_anestesia": bool(payload.get("requer_anestesia", False)),
                "observacoes": (
                    "Modelo inicial CorePet. Configure preço, insumos e protocolo da clínica."
                ),
                "ativo": True,
            },
            tenant_id,
        )
        created_id = _scalar(
            db,
            """
            SELECT id
            FROM vet_catalogo_procedimentos
            WHERE {tenant_filter}
              AND lower(nome) = lower(:nome)
            LIMIT 1
            """,
            {"nome": payload["nome"]},
            tenant_id,
        )
        _record_template_item_install(
            db,
            tenant_id,
            None,
            result,
            item,
            "vet_catalogo_procedimentos",
            created_id,
        )
        result.bump("created", "vet_procedures")
