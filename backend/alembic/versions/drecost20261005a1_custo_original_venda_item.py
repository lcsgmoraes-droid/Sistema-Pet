"""Guarda comprovante prospectivo do custo de saida por item de venda.

Revision ID: drecost20261005a1
Revises: dredev20261005a1
"""

from alembic import op
import sqlalchemy as sa


revision = "drecost20261005a1"
down_revision = "dredev20261005a1"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "venda_itens", sa.Column("custo_original_saida", sa.JSON(), nullable=True)
    )
    if op.get_bind().dialect.name == "postgresql":
        op.execute(
            """
            CREATE FUNCTION venda_item_custo_original_write_once() RETURNS trigger AS $$
            BEGIN
              IF OLD.custo_original_saida IS NOT NULL
                 AND OLD.custo_original_saida::text IS DISTINCT FROM NEW.custo_original_saida::text
              THEN
                RAISE EXCEPTION 'custo_original_saida de venda_item e imutavel';
              END IF;
              RETURN NEW;
            END;
            $$ LANGUAGE plpgsql
            """
        )
        op.execute(
            """
            CREATE TRIGGER trg_venda_item_custo_original_write_once
            BEFORE UPDATE OF custo_original_saida ON venda_itens
            FOR EACH ROW EXECUTE FUNCTION venda_item_custo_original_write_once()
            """
        )


def downgrade() -> None:
    if op.get_bind().dialect.name == "postgresql":
        op.execute(
            "DROP TRIGGER IF EXISTS trg_venda_item_custo_original_write_once ON venda_itens"
        )
        op.execute("DROP FUNCTION IF EXISTS venda_item_custo_original_write_once()")
    op.drop_column("venda_itens", "custo_original_saida")
