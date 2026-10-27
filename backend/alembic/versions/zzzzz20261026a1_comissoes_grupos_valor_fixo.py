"""Grupos de produtos e valor fixo por unidade na comissão."""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from app.tenant_rls_migration import apply_tenant_rls

revision = "zzzzz20261026a1"
down_revision = "zzzzy20261026a1"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "comissoes_configuracao",
        sa.Column("valor_fixo", sa.Numeric(12, 2), nullable=False, server_default="0"),
    )
    op.add_column(
        "comissoes_itens",
        sa.Column("valor_fixo", sa.Numeric(12, 2), nullable=False, server_default="0"),
    )
    op.create_table(
        "comissoes_grupos_produtos",
        sa.Column("id", sa.Integer(), sa.Identity(always=True), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("nome", sa.String(120), nullable=False),
        sa.Column("produto_ids", sa.JSON(), nullable=False),
        sa.Column("ativo", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.UniqueConstraint(
            "tenant_id", "nome", name="uq_comissoes_grupos_tenant_nome"
        ),
    )
    op.create_index(
        "ix_comissoes_grupos_produtos_tenant_id",
        "comissoes_grupos_produtos",
        ["tenant_id"],
    )
    apply_tenant_rls(
        op_module=op,
        sa_module=sa,
        table_names=["comissoes_grupos_produtos"],
        enable=True,
    )


def downgrade():
    bind = op.get_bind()
    op.execute("SET LOCAL row_security = off")
    if bind.execute(sa.text("SELECT 1 FROM comissoes_grupos_produtos LIMIT 1")).first():
        raise RuntimeError("Preserve os grupos salvos antes de remover a tabela.")
    if bind.execute(
        sa.text(
            "SELECT 1 FROM comissoes_configuracao WHERE tipo_calculo = 'fixo' OR valor_fixo <> 0 LIMIT 1"
        )
    ).first():
        raise RuntimeError(
            "Existem comissões por valor fixo; preserve as regras antes de reverter."
        )
    op.drop_table("comissoes_grupos_produtos")
    if bind.execute(
        sa.text("SELECT 1 FROM comissoes_itens WHERE tipo_calculo = 'fixo' LIMIT 1")
    ).first():
        raise RuntimeError(
            "Existem snapshots de comissão fixa; preserve o histórico antes de reverter."
        )
    op.drop_column("comissoes_itens", "valor_fixo")
    op.drop_column("comissoes_configuracao", "valor_fixo")
