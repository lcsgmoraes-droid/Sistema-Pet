"""add group product links and integrated transfer cancellation status

Revision ID: zwy20260823a1
Revises: zwx20260822a1
"""

from alembic import op
import sqlalchemy as sa


revision = "zwy20260823a1"
down_revision = "zwx20260822a1"
branch_labels = None
depends_on = None


def _tenant_id_type(inspector: sa.Inspector) -> sa.types.TypeEngine:
    for coluna in inspector.get_columns("tenants"):
        if coluna["name"] == "id":
            return coluna["type"].copy()
    raise RuntimeError("Coluna tenants.id nao encontrada")


def _substituir_status_transferencia(*, incluir_cancelada: bool) -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "empresa_grupo_transferencias" not in inspector.get_table_names():
        return

    expressao = (
        "status IN ('processando', 'concluida', 'cancelada')"
        if incluir_cancelada
        else "status IN ('processando', 'concluida')"
    )
    contexto = (
        op.batch_alter_table("empresa_grupo_transferencias", recreate="always")
        if bind.dialect.name == "sqlite"
        else op.batch_alter_table("empresa_grupo_transferencias")
    )
    with contexto as batch_op:
        batch_op.drop_constraint(
            "ck_empresa_grupo_transferencias_status", type_="check"
        )
        batch_op.create_check_constraint(
            "ck_empresa_grupo_transferencias_status", expressao
        )


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tabelas = set(inspector.get_table_names())
    _substituir_status_transferencia(incluir_cancelada=True)

    if "empresa_grupo_produto_vinculos" in tabelas:
        return

    tenant_id_type = _tenant_id_type(inspector)
    op.create_table(
        "empresa_grupo_produto_vinculos",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("grupo_id", sa.Integer(), nullable=False),
        sa.Column("empresa_a_id", tenant_id_type.copy(), nullable=False),
        sa.Column("produto_a_id", sa.Integer(), nullable=False),
        sa.Column("empresa_b_id", tenant_id_type.copy(), nullable=False),
        sa.Column("produto_b_id", sa.Integer(), nullable=False),
        sa.Column(
            "status", sa.String(length=20), server_default="ativo", nullable=False
        ),
        sa.Column("criado_por_empresa_id", tenant_id_type.copy(), nullable=False),
        sa.Column("criado_por_usuario_id", sa.Integer(), nullable=False),
        sa.Column(
            "criado_em",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "atualizado_em",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("removido_em", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "empresa_a_id <> empresa_b_id",
            name="ck_empresa_grupo_produto_vinculos_empresas_distintas",
        ),
        sa.CheckConstraint(
            "produto_a_id > 0 AND produto_b_id > 0",
            name="ck_empresa_grupo_produto_vinculos_produtos_positivos",
        ),
        sa.CheckConstraint(
            "status IN ('ativo', 'removido')",
            name="ck_empresa_grupo_produto_vinculos_status",
        ),
        sa.ForeignKeyConstraint(
            ["criado_por_empresa_id"], ["tenants.id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(["empresa_a_id"], ["tenants.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["empresa_b_id"], ["tenants.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(
            ["grupo_id"], ["empresa_grupos.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "grupo_id",
            "empresa_a_id",
            "produto_a_id",
            "empresa_b_id",
            "produto_b_id",
            name="uq_empresa_grupo_produto_vinculo_par",
        ),
    )
    op.create_index(
        "ix_empresa_grupo_produto_vinculos_grupo_status",
        "empresa_grupo_produto_vinculos",
        ["grupo_id", "status"],
    )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tabelas = set(inspector.get_table_names())
    if "empresa_grupo_produto_vinculos" in tabelas:
        op.drop_table("empresa_grupo_produto_vinculos")
    if "empresa_grupo_transferencias" in tabelas:
        bind.execute(
            sa.text(
                "UPDATE empresa_grupo_transferencias "
                "SET status = 'concluida' WHERE status = 'cancelada'"
            )
        )
    _substituir_status_transferencia(incluir_cancelada=False)
