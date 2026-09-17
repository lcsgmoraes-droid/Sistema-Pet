"""Torna o modulo fiscal uma contratacao explicita por tenant.

Revision ID: zzv20260917a1
Revises: zzu20260917a1
Create Date: 2026-09-17
"""

import json
import re
import unicodedata

import sqlalchemy as sa
from alembic import op


revision = "zzv20260917a1"
down_revision = "zzu20260917a1"
branch_labels = None
depends_on = None


def _normalizar_nome(value: str | None) -> str:
    sem_acentos = "".join(
        caractere
        for caractere in unicodedata.normalize("NFKD", str(value or ""))
        if not unicodedata.combining(caractere)
    )
    return re.sub(r"[^a-z0-9]", "", sem_acentos.lower())


def _modulos(raw: str | None) -> list[str]:
    try:
        value = json.loads(raw) if raw else []
    except (TypeError, json.JSONDecodeError):
        value = []
    return [item for item in value if isinstance(item, str)] if isinstance(value, list) else []


def upgrade() -> None:
    connection = op.get_bind()
    tenants = connection.execute(
        sa.text("SELECT id, name, name_normalized, modulos_ativos FROM tenants")
    ).mappings()

    for tenant in tenants:
        nome = tenant.get("name_normalized") or tenant.get("name")
        modules = _modulos(tenant.get("modulos_ativos"))
        modules = [module for module in modules if module != "fiscal"]
        aumigos_pet = _normalizar_nome(nome).startswith("aumigospet")
        if not aumigos_pet:
            modules.append("fiscal")

        connection.execute(
            sa.text(
                "UPDATE tenants SET modulos_ativos = :modules WHERE id = :tenant_id"
            ),
            {
                "tenant_id": tenant["id"],
                "modules": json.dumps(sorted(set(modules))),
            },
        )

        if aumigos_pet:
            connection.execute(
                sa.text(
                    """
                    UPDATE assinaturas_modulos
                    SET status = 'cancelado'
                    WHERE CAST(tenant_id AS TEXT) = CAST(:tenant_id AS TEXT)
                      AND modulo = 'fiscal'
                      AND status = 'ativo'
                    """
                ),
                {"tenant_id": tenant["id"]},
            )


def downgrade() -> None:
    connection = op.get_bind()
    tenants = connection.execute(
        sa.text("SELECT id, modulos_ativos FROM tenants")
    ).mappings()

    for tenant in tenants:
        modules = [
            module
            for module in _modulos(tenant.get("modulos_ativos"))
            if module != "fiscal"
        ]
        connection.execute(
            sa.text(
                "UPDATE tenants SET modulos_ativos = :modules WHERE id = :tenant_id"
            ),
            {
                "tenant_id": tenant["id"],
                "modules": json.dumps(sorted(set(modules))),
            },
        )
