"""granel source product links

Revision ID: nu20260507a1
Revises: nt20260507a1
Create Date: 2026-05-07 15:55:00.000000
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "nu20260507a1"
down_revision = "nt20260507a1"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tabelas = set(inspector.get_table_names())

    if "produto_granel_vinculos" not in tabelas:
        op.create_table(
            "produto_granel_vinculos",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("produto_origem_id", sa.Integer(), nullable=False),
            sa.Column("produto_granel_id", sa.Integer(), nullable=False),
            sa.Column("ativo", sa.Boolean(), nullable=False, server_default=sa.text("true")),
            sa.Column("observacao", sa.Text(), nullable=True),
            sa.Column("user_id", sa.Integer(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=True, server_default=sa.text("now()")),
            sa.Column("updated_at", sa.DateTime(), nullable=True, server_default=sa.text("now()")),
            sa.ForeignKeyConstraint(["produto_origem_id"], ["produtos.id"]),
            sa.ForeignKeyConstraint(["produto_granel_id"], ["produtos.id"]),
            sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint(
                "tenant_id",
                "produto_origem_id",
                "produto_granel_id",
                name="uq_produto_granel_vinculo_origem_granel",
            ),
        )
        op.create_index(
            "idx_produto_granel_vinculo_origem",
            "produto_granel_vinculos",
            ["tenant_id", "produto_origem_id"],
        )
        op.create_index(
            "idx_produto_granel_vinculo_granel",
            "produto_granel_vinculos",
            ["tenant_id", "produto_granel_id"],
        )

    if "produto_kit_componentes" in tabelas:
        bind.execute(sa.text("""
            INSERT INTO produto_granel_vinculos (
                tenant_id,
                produto_origem_id,
                produto_granel_id,
                ativo,
                observacao,
                created_at,
                updated_at
            )
            SELECT DISTINCT
                c.tenant_id,
                c.produto_componente_id,
                c.kit_id,
                true,
                'Migrado da composicao de kit granel',
                now(),
                now()
            FROM produto_kit_componentes c
            JOIN produtos g ON g.id = c.kit_id AND g.tenant_id = c.tenant_id
            JOIN produtos o ON o.id = c.produto_componente_id AND o.tenant_id = c.tenant_id
            WHERE (COALESCE(g.e_granel, false) = true OR lower(COALESCE(g.nome, '')) LIKE '%granel%')
              AND c.produto_componente_id IS NOT NULL
            ON CONFLICT (tenant_id, produto_origem_id, produto_granel_id)
            DO UPDATE SET ativo = true, updated_at = now()
        """))

        bind.execute(sa.text("""
            DELETE FROM produto_kit_componentes c
            USING produtos g
            WHERE g.id = c.kit_id
              AND g.tenant_id = c.tenant_id
              AND (COALESCE(g.e_granel, false) = true OR lower(COALESCE(g.nome, '')) LIKE '%granel%')
        """))

    bind.execute(sa.text("""
        UPDATE produtos
           SET e_granel = true,
               unidade = 'KG',
               tipo_produto = 'SIMPLES',
               tipo_kit = NULL
         WHERE COALESCE(e_granel, false) = true
            OR lower(COALESCE(nome, '')) LIKE '%granel%'
    """))


def downgrade() -> None:
    op.drop_index("idx_produto_granel_vinculo_granel", table_name="produto_granel_vinculos")
    op.drop_index("idx_produto_granel_vinculo_origem", table_name="produto_granel_vinculos")
    op.drop_table("produto_granel_vinculos")
