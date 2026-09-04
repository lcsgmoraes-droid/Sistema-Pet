"""adiciona protocolos flexiveis de recorrencia por produto

Revision ID: zzc20260903a1
Revises: zzb20260903a1
Create Date: 2026-09-03
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "zzc20260903a1"
down_revision = "zzb20260903a1"
branch_labels = None
depends_on = None


_TENANT_GUARD = "tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::uuid"


def _criar_politica_rls(tabela: str) -> None:
    if op.get_bind().dialect.name != "postgresql":
        return
    politica = f"{tabela}_tenant_isolation"
    op.execute(f"ALTER TABLE {tabela} ENABLE ROW LEVEL SECURITY")
    op.execute(f"ALTER TABLE {tabela} FORCE ROW LEVEL SECURITY")
    op.execute(f"DROP POLICY IF EXISTS {politica} ON {tabela}")
    op.execute(
        f"CREATE POLICY {politica} ON {tabela} "
        f"USING ({_TENANT_GUARD}) WITH CHECK ({_TENANT_GUARD})"
    )


def upgrade() -> None:
    op.create_table(
        "produto_protocolos_recorrencia",
        sa.Column("produto_id", sa.Integer(), nullable=False),
        sa.Column("nome", sa.String(length=160), nullable=False),
        sa.Column("tipo", sa.String(length=30), nullable=False),
        sa.Column(
            "especie_compativel",
            sa.String(length=20),
            server_default="both",
            nullable=False,
        ),
        sa.Column(
            "fase_vida", sa.String(length=20), server_default="all", nullable=False
        ),
        sa.Column("intervalo_recompra_dias", sa.Integer(), nullable=True),
        sa.Column(
            "ajustar_ao_historico",
            sa.Boolean(),
            server_default=sa.true(),
            nullable=False,
        ),
        sa.Column("reiniciar_apos_dias", sa.Integer(), nullable=True),
        sa.Column("observacoes", sa.Text(), nullable=True),
        sa.Column("ativo", sa.Boolean(), server_default=sa.true(), nullable=False),
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
        sa.ForeignKeyConstraint(["produto_id"], ["produtos.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_produto_protocolos_recorrencia_tenant_id",
        "produto_protocolos_recorrencia",
        ["tenant_id"],
    )
    op.create_index(
        "ix_produto_protocolos_recorrencia_produto_id",
        "produto_protocolos_recorrencia",
        ["produto_id"],
    )
    op.create_index(
        "ix_produto_protocolos_recorrencia_tenant_produto_ativo",
        "produto_protocolos_recorrencia",
        ["tenant_id", "produto_id", "ativo"],
    )

    op.create_table(
        "produto_protocolo_doses",
        sa.Column("protocolo_id", sa.Integer(), nullable=False),
        sa.Column("numero_dose", sa.Integer(), nullable=False),
        sa.Column("dias_desde_inicio", sa.Integer(), nullable=False),
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
        sa.ForeignKeyConstraint(
            ["protocolo_id"],
            ["produto_protocolos_recorrencia.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "protocolo_id",
            "numero_dose",
            name="uq_produto_protocolo_dose_numero",
        ),
    )
    op.create_index(
        "ix_produto_protocolo_doses_tenant_id",
        "produto_protocolo_doses",
        ["tenant_id"],
    )
    op.create_index(
        "ix_produto_protocolo_doses_protocolo_id",
        "produto_protocolo_doses",
        ["protocolo_id"],
    )

    op.add_column(
        "lembretes",
        sa.Column("protocolo_recorrencia_id", sa.Integer(), nullable=True),
    )
    op.add_column(
        "lembretes", sa.Column("data_inicio_protocolo", sa.DateTime(), nullable=True)
    )
    op.add_column(
        "lembretes",
        sa.Column(
            "tipo_lembrete",
            sa.String(length=30),
            server_default="recompra",
            nullable=False,
        ),
    )
    op.create_foreign_key(
        "fk_lembretes_protocolo_recorrencia",
        "lembretes",
        "produto_protocolos_recorrencia",
        ["protocolo_recorrencia_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index(
        "ix_lembretes_protocolo_recorrencia_id",
        "lembretes",
        ["protocolo_recorrencia_id"],
    )

    op.add_column(
        "venda_itens",
        sa.Column("protocolo_recorrencia_id", sa.Integer(), nullable=True),
    )
    op.add_column(
        "venda_itens",
        sa.Column(
            "ignorar_recorrencia",
            sa.Boolean(),
            server_default=sa.false(),
            nullable=False,
        ),
    )
    op.create_foreign_key(
        "fk_venda_itens_protocolo_recorrencia",
        "venda_itens",
        "produto_protocolos_recorrencia",
        ["protocolo_recorrencia_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index(
        "ix_venda_itens_protocolo_recorrencia_id",
        "venda_itens",
        ["protocolo_recorrencia_id"],
    )

    if op.get_bind().dialect.name == "postgresql":
        op.execute(sa.text("""
                INSERT INTO produto_protocolos_recorrencia (
                    produto_id, nome, tipo, especie_compativel, fase_vida,
                    intervalo_recompra_dias, ajustar_ao_historico,
                    reiniciar_apos_dias, observacoes, ativo, tenant_id
                )
                SELECT
                    id,
                    CASE WHEN COALESCE(numero_doses, 0) > 1
                         THEN 'Protocolo existente'
                         ELSE 'Recompra contínua' END,
                    CASE WHEN COALESCE(numero_doses, 0) > 1
                         THEN 'protocolo_doses'
                         ELSE 'recompra_continua' END,
                    COALESCE(NULLIF(especie_compativel, ''), 'both'),
                    'all',
                    CASE WHEN COALESCE(numero_doses, 0) <= 1
                         THEN intervalo_dias ELSE NULL END,
                    CASE WHEN COALESCE(numero_doses, 0) <= 1
                         THEN TRUE ELSE FALSE END,
                    NULL,
                    observacoes_recorrencia,
                    TRUE,
                    tenant_id
                FROM produtos
                WHERE tem_recorrencia IS TRUE
                  AND intervalo_dias BETWEEN 1 AND 3650
                """))
        op.execute(sa.text("""
                INSERT INTO produto_protocolo_doses (
                    protocolo_id, numero_dose, dias_desde_inicio, tenant_id
                )
                SELECT
                    protocolo.id,
                    serie.numero_dose,
                    (serie.numero_dose - 1) * produto.intervalo_dias,
                    protocolo.tenant_id
                FROM produto_protocolos_recorrencia protocolo
                JOIN produtos produto ON produto.id = protocolo.produto_id
                CROSS JOIN LATERAL generate_series(1, produto.numero_doses)
                    AS serie(numero_dose)
                WHERE protocolo.tipo = 'protocolo_doses'
                """))

        op.execute(sa.text("""
                UPDATE lembretes lembrete
                SET protocolo_recorrencia_id = protocolo.id,
                    tipo_lembrete = CASE
                        WHEN COALESCE(lembrete.dose_total, 0) > 1
                            THEN 'proxima_dose'
                        ELSE 'recompra'
                    END,
                    data_inicio_protocolo = CASE
                        WHEN COALESCE(lembrete.dose_total, 0) > 1
                            THEN lembrete.data_compra
                                - (
                                    GREATEST(COALESCE(lembrete.dose_atual, 2) - 2, 0)
                                    * COALESCE(produto.intervalo_dias, 0)
                                  ) * INTERVAL '1 day'
                        ELSE NULL
                    END
                FROM produto_protocolos_recorrencia protocolo,
                     produtos produto
                WHERE protocolo.produto_id = lembrete.produto_id
                  AND protocolo.tenant_id = lembrete.tenant_id
                  AND produto.id = protocolo.produto_id
                  AND produto.tenant_id = protocolo.tenant_id
                """))

    _criar_politica_rls("produto_protocolos_recorrencia")
    _criar_politica_rls("produto_protocolo_doses")


def downgrade() -> None:
    op.drop_index("ix_venda_itens_protocolo_recorrencia_id", table_name="venda_itens")
    op.drop_constraint(
        "fk_venda_itens_protocolo_recorrencia", "venda_itens", type_="foreignkey"
    )
    op.drop_column("venda_itens", "protocolo_recorrencia_id")
    op.drop_column("venda_itens", "ignorar_recorrencia")

    op.drop_index("ix_lembretes_protocolo_recorrencia_id", table_name="lembretes")
    op.drop_constraint(
        "fk_lembretes_protocolo_recorrencia", "lembretes", type_="foreignkey"
    )
    op.drop_column("lembretes", "tipo_lembrete")
    op.drop_column("lembretes", "data_inicio_protocolo")
    op.drop_column("lembretes", "protocolo_recorrencia_id")

    op.drop_table("produto_protocolo_doses")
    op.drop_table("produto_protocolos_recorrencia")
