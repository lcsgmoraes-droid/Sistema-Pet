"""Cria o piloto de orcamentos das empresas do grupo.

Revision ID: zzt20260915a1
Revises: zzs20260915a1
Create Date: 2026-09-15
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "zzt20260915a1"
down_revision = "zzs20260915a1"
branch_labels = None
depends_on = None


ORCAMENTOS_GRUPO_TABLES = (
    "orcamento_grupo_configuracoes",
    "orcamento_grupo_empresas",
    "orcamentos_grupo",
    "orcamento_grupo_itens",
    "orcamento_grupo_cotacoes",
)
TENANT_GUARD = "tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::uuid"


def _colunas_base():
    return (
        sa.Column("id", sa.Integer(), sa.Identity(always=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )


def _habilitar_rls(tabela: str) -> None:
    if op.get_bind().dialect.name != "postgresql":
        return
    politica = f"{tabela}_tenant_isolation"
    op.execute(f"ALTER TABLE {tabela} ENABLE ROW LEVEL SECURITY")
    op.execute(f"ALTER TABLE {tabela} FORCE ROW LEVEL SECURITY")
    op.execute(f"DROP POLICY IF EXISTS {politica} ON {tabela}")
    op.execute(
        f"CREATE POLICY {politica} ON {tabela} "
        f"USING ({TENANT_GUARD}) WITH CHECK ({TENANT_GUARD})"
    )


def upgrade():
    op.create_table(
        "orcamento_grupo_configuracoes",
        sa.Column(
            "percentual_minimo",
            sa.Numeric(5, 2),
            server_default="10",
            nullable=False,
        ),
        sa.Column(
            "percentual_maximo",
            sa.Numeric(5, 2),
            server_default="30",
            nullable=False,
        ),
        sa.Column(
            "quantidade_empresas", sa.Integer(), server_default="2", nullable=False
        ),
        sa.Column("validade_dias", sa.Integer(), server_default="15", nullable=False),
        sa.Column("observacoes_padrao", sa.Text(), nullable=True),
        *_colunas_base(),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "tenant_id", name="uq_orcamento_grupo_configuracoes_tenant"
        ),
    )
    op.create_index(
        "ix_orcamento_grupo_configuracoes_tenant_id",
        "orcamento_grupo_configuracoes",
        ["tenant_id"],
    )

    op.create_table(
        "orcamento_grupo_empresas",
        sa.Column("cliente_id", sa.Integer(), nullable=False),
        sa.Column("ativo", sa.Boolean(), server_default=sa.true(), nullable=False),
        sa.Column(
            "fixada_padrao", sa.Boolean(), server_default=sa.false(), nullable=False
        ),
        sa.Column("observacoes", sa.Text(), nullable=True),
        *_colunas_base(),
        sa.ForeignKeyConstraint(["cliente_id"], ["clientes.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "tenant_id",
            "cliente_id",
            name="uq_orcamento_grupo_empresas_tenant_cliente",
        ),
    )
    op.create_index(
        "ix_orcamento_grupo_empresas_tenant_id",
        "orcamento_grupo_empresas",
        ["tenant_id"],
    )
    op.create_index(
        "ix_orcamento_grupo_empresas_cliente_id",
        "orcamento_grupo_empresas",
        ["cliente_id"],
    )
    op.create_index(
        "ix_orcamento_grupo_empresas_tenant_ativo",
        "orcamento_grupo_empresas",
        ["tenant_id", "ativo"],
    )

    op.create_table(
        "orcamentos_grupo",
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("numero", sa.String(40), nullable=True),
        sa.Column("titulo", sa.String(255), server_default="Orcamento", nullable=False),
        sa.Column("destinatario", sa.String(255), nullable=True),
        sa.Column("data_emissao", sa.Date(), nullable=False),
        sa.Column("validade_dias", sa.Integer(), server_default="15", nullable=False),
        sa.Column("percentual_minimo", sa.Numeric(5, 2), nullable=False),
        sa.Column("percentual_maximo", sa.Numeric(5, 2), nullable=False),
        sa.Column("observacoes", sa.Text(), nullable=True),
        sa.Column("status", sa.String(30), server_default="emitido", nullable=False),
        sa.Column("total_base", sa.Numeric(14, 2), server_default="0", nullable=False),
        *_colunas_base(),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "tenant_id", "numero", name="uq_orcamentos_grupo_tenant_numero"
        ),
    )
    op.create_index("ix_orcamentos_grupo_tenant_id", "orcamentos_grupo", ["tenant_id"])
    op.create_index("ix_orcamentos_grupo_user_id", "orcamentos_grupo", ["user_id"])
    op.create_index(
        "ix_orcamentos_grupo_tenant_emissao",
        "orcamentos_grupo",
        ["tenant_id", "data_emissao"],
    )

    op.create_table(
        "orcamento_grupo_itens",
        sa.Column("orcamento_id", sa.Integer(), nullable=False),
        sa.Column("ordem", sa.Integer(), server_default="0", nullable=False),
        sa.Column("descricao", sa.String(500), nullable=False),
        sa.Column("quantidade", sa.Numeric(12, 3), server_default="1", nullable=False),
        sa.Column("unidade", sa.String(30), nullable=True),
        sa.Column(
            "preco_unitario_base", sa.Numeric(14, 2), server_default="0", nullable=False
        ),
        sa.Column("total_base", sa.Numeric(14, 2), server_default="0", nullable=False),
        *_colunas_base(),
        sa.ForeignKeyConstraint(
            ["orcamento_id"], ["orcamentos_grupo.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_orcamento_grupo_itens_tenant_id",
        "orcamento_grupo_itens",
        ["tenant_id"],
    )
    op.create_index(
        "ix_orcamento_grupo_itens_orcamento_id",
        "orcamento_grupo_itens",
        ["orcamento_id"],
    )
    op.create_index(
        "ix_orcamento_grupo_itens_tenant_orcamento",
        "orcamento_grupo_itens",
        ["tenant_id", "orcamento_id"],
    )

    op.create_table(
        "orcamento_grupo_cotacoes",
        sa.Column("orcamento_id", sa.Integer(), nullable=False),
        sa.Column("empresa_grupo_id", sa.Integer(), nullable=True),
        sa.Column("ordem", sa.Integer(), server_default="0", nullable=False),
        sa.Column(
            "emissor_principal", sa.Boolean(), server_default=sa.false(), nullable=False
        ),
        sa.Column("fixada", sa.Boolean(), server_default=sa.false(), nullable=False),
        sa.Column(
            "percentual_acrescimo", sa.Numeric(5, 2), server_default="0", nullable=False
        ),
        sa.Column("empresa_snapshot", sa.JSON(), nullable=False),
        sa.Column("itens_snapshot", sa.JSON(), nullable=False),
        sa.Column("total", sa.Numeric(14, 2), server_default="0", nullable=False),
        *_colunas_base(),
        sa.ForeignKeyConstraint(
            ["orcamento_id"], ["orcamentos_grupo.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["empresa_grupo_id"],
            ["orcamento_grupo_empresas.id"],
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_orcamento_grupo_cotacoes_tenant_id",
        "orcamento_grupo_cotacoes",
        ["tenant_id"],
    )
    op.create_index(
        "ix_orcamento_grupo_cotacoes_orcamento_id",
        "orcamento_grupo_cotacoes",
        ["orcamento_id"],
    )
    op.create_index(
        "ix_orcamento_grupo_cotacoes_empresa_grupo_id",
        "orcamento_grupo_cotacoes",
        ["empresa_grupo_id"],
    )
    op.create_index(
        "ix_orcamento_grupo_cotacoes_tenant_orcamento",
        "orcamento_grupo_cotacoes",
        ["tenant_id", "orcamento_id"],
    )

    if op.get_bind().dialect.name == "postgresql":
        # A migracao possui lock exclusivo e desliga a RLS apenas durante o seed.
        op.execute("ALTER TABLE feature_flags DISABLE ROW LEVEL SECURITY")
        op.execute(
            sa.text("""
                INSERT INTO feature_flags (tenant_id, feature_key, enabled)
                SELECT DISTINCT u.tenant_id, 'ORCAMENTOS_GRUPO', TRUE
                FROM users u
                WHERE lower(trim(u.email)) = 'corepeterp@gmail.com'
                ON CONFLICT (tenant_id, feature_key)
                DO UPDATE SET enabled = EXCLUDED.enabled
            """)
        )
        op.execute("ALTER TABLE feature_flags ENABLE ROW LEVEL SECURITY")
        op.execute("ALTER TABLE feature_flags FORCE ROW LEVEL SECURITY")

    for tabela in ORCAMENTOS_GRUPO_TABLES:
        _habilitar_rls(tabela)


def downgrade():
    if op.get_bind().dialect.name == "postgresql":
        op.execute("ALTER TABLE feature_flags DISABLE ROW LEVEL SECURITY")
        op.execute(
            sa.text("""
                DELETE FROM feature_flags ff
                USING users u
                WHERE ff.tenant_id = u.tenant_id
                  AND ff.feature_key = 'ORCAMENTOS_GRUPO'
                  AND lower(trim(u.email)) = 'corepeterp@gmail.com'
            """)
        )
        op.execute("ALTER TABLE feature_flags ENABLE ROW LEVEL SECURITY")
        op.execute("ALTER TABLE feature_flags FORCE ROW LEVEL SECURITY")

    for tabela in reversed(ORCAMENTOS_GRUPO_TABLES):
        if op.get_bind().dialect.name == "postgresql":
            op.execute(f"ALTER TABLE {tabela} NO FORCE ROW LEVEL SECURITY")
            op.execute(f"DROP POLICY IF EXISTS {tabela}_tenant_isolation ON {tabela}")
            op.execute(f"ALTER TABLE {tabela} DISABLE ROW LEVEL SECURITY")
        op.drop_table(tabela)
