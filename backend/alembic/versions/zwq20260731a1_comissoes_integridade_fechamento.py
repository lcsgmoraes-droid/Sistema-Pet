"""commission closure integrity and tenant-scoped settings

Revision ID: zwq20260731a1
Revises: zwp20260731a1
Create Date: 2026-07-31
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from app.tenant_rls_migration import apply_tenant_rls


revision = "zwq20260731a1"
down_revision = "zwp20260731a1"
branch_labels = None
depends_on = None

CONFIG_TABLE = "comissoes_configuracoes_sistema"


def upgrade() -> None:
    op.add_column(
        "comissoes_itens",
        sa.Column("data_fechamento", sa.Date(), nullable=True),
    )
    op.create_index(
        "ix_comissoes_itens_data_fechamento",
        "comissoes_itens",
        ["data_fechamento"],
        unique=False,
    )

    op.execute(
        """
        UPDATE comissoes_itens
        SET data_fechamento = COALESCE(
            data_pagamento,
            CAST(data_atualizacao AS DATE),
            data_venda
        )
        WHERE status IN (
            'fechada',
            'pago',
            'paga',
            'pago_com_compensacao',
            'compensado_integralmente'
        )
          AND data_fechamento IS NULL
        """
    )

    op.execute(
        """
        UPDATE comissoes_itens
        SET status = 'pago'
        WHERE status IN ('paga', 'pago_com_compensacao', 'compensado_integralmente')
        """
    )

    op.create_table(
        CONFIG_TABLE,
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "tenant_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column(
            "gerar_comissao_venda_parcial",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("true"),
        ),
        sa.Column(
            "percentual_imposto_padrao",
            sa.Numeric(5, 2),
            nullable=False,
            server_default=sa.text("7.00"),
        ),
        sa.Column(
            "dias_vencimento_padrao",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("30"),
        ),
        sa.Column("email_assunto_template", sa.String(255), nullable=True),
        sa.Column("email_corpo_template", sa.Text(), nullable=True),
        sa.Column(
            "pdf_formato_padrao",
            sa.String(30),
            nullable=False,
            server_default=sa.text("'A4'"),
        ),
        sa.Column(
            "data_atualizacao",
            sa.DateTime(),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.UniqueConstraint("tenant_id", name="uq_comissoes_config_sistema_tenant"),
    )
    op.create_index(
        "ix_comissoes_configuracoes_sistema_tenant_id",
        CONFIG_TABLE,
        ["tenant_id"],
        unique=True,
    )
    apply_tenant_rls(
        op_module=op,
        sa_module=sa,
        table_names=(CONFIG_TABLE,),
        enable=True,
    )


def downgrade() -> None:
    apply_tenant_rls(
        op_module=op,
        sa_module=sa,
        table_names=(CONFIG_TABLE,),
        enable=False,
    )
    op.drop_index(
        "ix_comissoes_configuracoes_sistema_tenant_id",
        table_name=CONFIG_TABLE,
    )
    op.drop_table(CONFIG_TABLE)

    op.execute(
        "UPDATE comissoes_itens SET status = 'pendente' WHERE status = 'fechada'"
    )
    op.drop_index(
        "ix_comissoes_itens_data_fechamento",
        table_name="comissoes_itens",
    )
    op.drop_column("comissoes_itens", "data_fechamento")
