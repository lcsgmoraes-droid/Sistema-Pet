"""billing_offers: plan_pet/vet/grooming_code, plan_code/plan_name nullable

Revision ID: zzzl20261001a1
Revises: zzzk20261001a1
Create Date: 2026-10-01 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "zzzl20261001a1"
down_revision = "zzzk20261001a1"
branch_labels = None
depends_on = None


def _columns(table_name: str) -> set[str]:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if not inspector.has_table(table_name):
        return set()
    return {column["name"] for column in inspector.get_columns(table_name)}


def upgrade() -> None:
    columns = _columns("billing_offers")
    if "plan_pet_code" not in columns:
        op.add_column(
            "billing_offers", sa.Column("plan_pet_code", sa.String(length=50), nullable=True)
        )
    if "plan_vet_code" not in columns:
        op.add_column(
            "billing_offers", sa.Column("plan_vet_code", sa.String(length=50), nullable=True)
        )
    if "plan_grooming_code" not in columns:
        op.add_column(
            "billing_offers",
            sa.Column("plan_grooming_code", sa.String(length=50), nullable=True),
        )
    # Ofertas antigas ja tem plan_code/plan_name preenchidos (1 plano so).
    # Backfill: joga esse plano unico no campo de segmento correspondente,
    # pra ofertas antigas continuarem exibindo o plano certo nos getters
    # novos (que agora leem so os 3 campos de segmento).
    bind = op.get_bind()
    pet_list = "'pet-start','pet-basico','pet-gestao','pet-venda-ativa'"
    vet_list = "'vet-start','vet-gestao','vet-completo'"
    grooming_list = "'grooming-start','grooming-gestao','grooming-completo'"
    bind.execute(
        sa.text(f"UPDATE billing_offers SET plan_pet_code = plan_code WHERE plan_code IN ({pet_list})")
    )
    bind.execute(
        sa.text(f"UPDATE billing_offers SET plan_vet_code = plan_code WHERE plan_code IN ({vet_list})")
    )
    bind.execute(
        sa.text(
            f"UPDATE billing_offers SET plan_grooming_code = plan_code WHERE plan_code IN ({grooming_list})"
        )
    )
    op.alter_column("billing_offers", "plan_code", nullable=True)
    op.alter_column("billing_offers", "plan_name", nullable=True)


def downgrade() -> None:
    op.alter_column("billing_offers", "plan_name", nullable=False)
    op.alter_column("billing_offers", "plan_code", nullable=False)
    columns = _columns("billing_offers")
    if "plan_grooming_code" in columns:
        op.drop_column("billing_offers", "plan_grooming_code")
    if "plan_vet_code" in columns:
        op.drop_column("billing_offers", "plan_vet_code")
    if "plan_pet_code" in columns:
        op.drop_column("billing_offers", "plan_pet_code")
