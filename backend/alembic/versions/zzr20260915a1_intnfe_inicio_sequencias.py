"""Registra o ponto inicial das sequências usadas pelo CorePet.

Revision ID: zzr20260915a1
Revises: zzq20260914a1
Create Date: 2026-09-15
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "zzr20260915a1"
down_revision = "zzq20260914a1"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "intnfe_emission_sequences",
        sa.Column("ambiente_codigo", sa.SmallInteger(), nullable=False),
        sa.Column("modelo", sa.SmallInteger(), nullable=False),
        sa.Column("serie", sa.String(length=3), nullable=False),
        sa.Column("numero_inicial", sa.Integer(), nullable=False),
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
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "tenant_id",
            "ambiente_codigo",
            "modelo",
            name="uq_intnfe_emission_sequence_tenant_environment_model",
        ),
    )
    op.create_index(
        "ix_intnfe_emission_sequences_tenant_id",
        "intnfe_emission_sequences",
        ["tenant_id"],
        unique=False,
    )
    if op.get_bind().dialect.name == "postgresql":
        op.execute(sa.text("""
            WITH historico AS (
                SELECT
                    tenant_id,
                    nfe_ambiente,
                    nfe_modelo,
                    nfe_serie,
                    MIN(nfe_numero) AS numero_inicial,
                    MAX(COALESCE(nfe_data_autorizacao, nfe_data_emissao, data_venda)) AS ultima_emissao
                FROM vendas
                WHERE nfe_provider = 'intnfe'
                  AND nfe_numero IS NOT NULL
                  AND nfe_serie IS NOT NULL
                  AND nfe_ambiente IN (1, 2)
                  AND nfe_modelo IN ('55', '65')
                GROUP BY tenant_id, nfe_ambiente, nfe_modelo, nfe_serie
            ), series_recentes AS (
                SELECT DISTINCT ON (tenant_id, nfe_ambiente, nfe_modelo)
                    tenant_id,
                    nfe_ambiente,
                    nfe_modelo,
                    nfe_serie,
                    numero_inicial
                FROM historico
                ORDER BY tenant_id, nfe_ambiente, nfe_modelo, ultima_emissao DESC
            )
            INSERT INTO intnfe_emission_sequences (
                tenant_id, ambiente_codigo, modelo, serie, numero_inicial
            )
            SELECT
                tenant_id,
                nfe_ambiente,
                CAST(nfe_modelo AS SMALLINT),
                CAST(nfe_serie AS VARCHAR(3)),
                numero_inicial
            FROM series_recentes
            ON CONFLICT (tenant_id, ambiente_codigo, modelo) DO NOTHING
            """))
        guard = "tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::uuid"
        op.execute("ALTER TABLE intnfe_emission_sequences ENABLE ROW LEVEL SECURITY")
        op.execute("ALTER TABLE intnfe_emission_sequences FORCE ROW LEVEL SECURITY")
        op.execute(
            "CREATE POLICY intnfe_emission_sequences_tenant_isolation "
            "ON intnfe_emission_sequences "
            f"USING ({guard}) WITH CHECK ({guard})"
        )


def downgrade():
    op.drop_index(
        "ix_intnfe_emission_sequences_tenant_id",
        table_name="intnfe_emission_sequences",
    )
    op.drop_table("intnfe_emission_sequences")
