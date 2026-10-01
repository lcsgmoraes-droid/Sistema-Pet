"""add plan_pet, plan_vet, plan_grooming to tenants

Revision ID: zzzk20261001a1
Revises: zzzj20261001a1
Create Date: 2026-10-01 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "zzzk20261001a1"
down_revision = "zzzj20261001a1"
branch_labels = None
depends_on = None

PLANOS_PET = ("pet-start", "pet-basico", "pet-gestao", "pet-venda-ativa")
PLANOS_VET = ("vet-start", "vet-gestao", "vet-completo")
PLANOS_GROOMING = ("grooming-start", "grooming-gestao", "grooming-completo")


def _columns(table_name: str) -> set[str]:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if not inspector.has_table(table_name):
        return set()
    return {column["name"] for column in inspector.get_columns(table_name)}


def upgrade() -> None:
    columns = _columns("tenants")
    if "plan_pet" not in columns:
        op.add_column("tenants", sa.Column("plan_pet", sa.String(length=50), nullable=True))
    if "plan_vet" not in columns:
        op.add_column("tenants", sa.Column("plan_vet", sa.String(length=50), nullable=True))
    if "plan_grooming" not in columns:
        op.add_column("tenants", sa.Column("plan_grooming", sa.String(length=50), nullable=True))

    # Backfill a partir do `plan` legado: so os 10 codigos reais do catalogo
    # (plan_catalog.py) casam com um segmento. Codigos legado (free/legacy/
    # legado/premium/enterprise/full/completo/basico/basic) ficam com os 3
    # campos NULL ate serem reatribuidos a um plano real via o fluxo de
    # aditivo comercial.
    bind = op.get_bind()
    pet_list = ", ".join(f"'{codigo}'" for codigo in PLANOS_PET)
    vet_list = ", ".join(f"'{codigo}'" for codigo in PLANOS_VET)
    grooming_list = ", ".join(f"'{codigo}'" for codigo in PLANOS_GROOMING)
    bind.execute(sa.text(f"UPDATE tenants SET plan_pet = plan WHERE plan IN ({pet_list})"))
    bind.execute(sa.text(f"UPDATE tenants SET plan_vet = plan WHERE plan IN ({vet_list})"))
    bind.execute(
        sa.text(f"UPDATE tenants SET plan_grooming = plan WHERE plan IN ({grooming_list})")
    )


def downgrade() -> None:
    columns = _columns("tenants")
    if "plan_grooming" in columns:
        op.drop_column("tenants", "plan_grooming")
    if "plan_vet" in columns:
        op.drop_column("tenants", "plan_vet")
    if "plan_pet" in columns:
        op.drop_column("tenants", "plan_pet")
