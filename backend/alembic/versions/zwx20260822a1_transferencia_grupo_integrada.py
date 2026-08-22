"""create atomic transfers between companies in a group

Revision ID: zwx20260822a1
Revises: zww20260822a1
"""

from alembic import op
import sqlalchemy as sa


revision = "zwx20260822a1"
down_revision = "zww20260822a1"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tabelas = set(inspector.get_table_names())

    if "empresa_grupo_membros" in tabelas:
        colunas = {
            coluna["name"] for coluna in inspector.get_columns("empresa_grupo_membros")
        }
        if "usuario_referencia_id" not in colunas:
            op.add_column(
                "empresa_grupo_membros",
                sa.Column("usuario_referencia_id", sa.Integer(), nullable=True),
            )

    if "empresa_grupo_transferencias" in tabelas:
        return

    op.create_table(
        "empresa_grupo_transferencias",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("grupo_id", sa.Integer(), nullable=False),
        sa.Column("empresa_origem_id", sa.String(length=36), nullable=False),
        sa.Column("empresa_destino_id", sa.String(length=36), nullable=False),
        sa.Column("usuario_origem_id", sa.Integer(), nullable=False),
        sa.Column("usuario_destino_id", sa.Integer(), nullable=True),
        sa.Column("chave_idempotencia", sa.String(length=36), nullable=False),
        sa.Column("documento", sa.String(length=100), nullable=False),
        sa.Column(
            "status", sa.String(length=20), server_default="processando", nullable=False
        ),
        sa.Column("conta_receber_origem_id", sa.Integer(), nullable=True),
        sa.Column("conta_pagar_destino_id", sa.Integer(), nullable=True),
        sa.Column("itens_snapshot", sa.JSON(), nullable=False),
        sa.Column("resultado", sa.JSON(), nullable=True),
        sa.Column(
            "criado_em",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("concluido_em", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "empresa_origem_id <> empresa_destino_id",
            name="ck_empresa_grupo_transferencias_empresas_distintas",
        ),
        sa.CheckConstraint(
            "status IN ('processando', 'concluida')",
            name="ck_empresa_grupo_transferencias_status",
        ),
        sa.ForeignKeyConstraint(
            ["empresa_destino_id"], ["tenants.id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(
            ["empresa_origem_id"], ["tenants.id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(
            ["grupo_id"], ["empresa_grupos.id"], ondelete="RESTRICT"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "empresa_origem_id",
            "chave_idempotencia",
            name="uq_empresa_grupo_transferencia_idempotencia",
        ),
    )
    op.create_index(
        "ix_empresa_grupo_transferencias_grupo_criado",
        "empresa_grupo_transferencias",
        ["grupo_id", "criado_em"],
    )
    op.create_index(
        "ix_empresa_grupo_transferencias_destino_criado",
        "empresa_grupo_transferencias",
        ["empresa_destino_id", "criado_em"],
    )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tabelas = set(inspector.get_table_names())
    if "empresa_grupo_transferencias" in tabelas:
        op.drop_table("empresa_grupo_transferencias")
    if "empresa_grupo_membros" in tabelas:
        colunas = {
            coluna["name"] for coluna in inspector.get_columns("empresa_grupo_membros")
        }
        if "usuario_referencia_id" in colunas:
            op.drop_column("empresa_grupo_membros", "usuario_referencia_id")
