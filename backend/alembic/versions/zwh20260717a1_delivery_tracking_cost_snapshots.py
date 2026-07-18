"""secure public delivery tracking and persist cost per stop

Revision ID: zwh20260717a1
Revises: zwg20260716a1
Create Date: 2026-07-17
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "zwh20260717a1"
down_revision = "zwg20260716a1"
branch_labels = None
depends_on = None


def upgrade():
    # Formaliza colunas que antes eram criadas apenas em runtime por compatibilidade.
    op.execute(
        "ALTER TABLE rotas_entrega ADD COLUMN IF NOT EXISTS token_rastreio VARCHAR(64)"
    )
    op.execute(
        "ALTER TABLE rotas_entrega ADD COLUMN IF NOT EXISTS lat_atual NUMERIC(10,6)"
    )
    op.execute(
        "ALTER TABLE rotas_entrega ADD COLUMN IF NOT EXISTS lon_atual NUMERIC(10,6)"
    )
    op.execute(
        "ALTER TABLE rotas_entrega ADD COLUMN IF NOT EXISTS localizacao_atualizada_em TIMESTAMP"
    )
    op.execute(
        "ALTER TABLE rotas_entrega ADD COLUMN IF NOT EXISTS distancia_total_km_real NUMERIC(10,3)"
    )
    op.execute(
        "ALTER TABLE rotas_entrega ADD COLUMN IF NOT EXISTS distancia_retorno_km_real NUMERIC(10,3)"
    )
    op.execute(
        "ALTER TABLE rotas_entrega_paradas ADD COLUMN IF NOT EXISTS lat_entrega NUMERIC(10,6)"
    )
    op.execute(
        "ALTER TABLE rotas_entrega_paradas ADD COLUMN IF NOT EXISTS lon_entrega NUMERIC(10,6)"
    )
    op.execute(
        "ALTER TABLE rotas_entrega_paradas ADD COLUMN IF NOT EXISTS distancia_trecho_real_km NUMERIC(10,3)"
    )
    op.execute(
        "ALTER TABLE rotas_entrega_paradas ADD COLUMN IF NOT EXISTS distancia_acumulada_real_km NUMERIC(10,3)"
    )

    op.create_table(
        "rotas_entrega_rastreio_tokens",
        sa.Column("token", sa.String(length=64), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("rota_id", sa.Integer(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["rota_id"], ["rotas_entrega.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("token"),
        sa.UniqueConstraint("rota_id"),
    )
    op.create_index(
        "ix_rotas_entrega_rastreio_tokens_tenant_id",
        "rotas_entrega_rastreio_tokens",
        ["tenant_id"],
        unique=False,
    )

    op.add_column(
        "rotas_entrega_paradas",
        sa.Column("tentativas", sa.Integer(), server_default="1", nullable=False),
    )
    op.add_column(
        "rotas_entrega_paradas",
        sa.Column("modelo_custo_operacional", sa.String(length=24), nullable=True),
    )
    op.add_column(
        "rotas_entrega_paradas",
        sa.Column("valor_base_custo_operacional", sa.Numeric(12, 4), nullable=True),
    )
    op.add_column(
        "rotas_entrega_paradas",
        sa.Column("distancia_custo_km", sa.Numeric(10, 3), nullable=True),
    )
    op.add_column(
        "rotas_entrega_paradas",
        sa.Column("custo_operacional", sa.Numeric(12, 2), nullable=True),
    )
    op.add_column(
        "rotas_entrega_paradas",
        sa.Column(
            "custo_moto_rateado", sa.Numeric(12, 2), server_default="0", nullable=True
        ),
    )
    op.add_column(
        "rotas_entrega_paradas",
        sa.Column("custo_calculado_em", sa.DateTime(), nullable=True),
    )

    # O indice global contem apenas token aleatorio -> tenant/rota. Assim a API
    # publica resolve a empresa antes de tocar tabelas protegidas por RLS.
    op.execute(
        """
        INSERT INTO rotas_entrega_rastreio_tokens (token, tenant_id, rota_id)
        SELECT token_rastreio, tenant_id, id
        FROM rotas_entrega
        WHERE token_rastreio IS NOT NULL AND token_rastreio <> ''
        ON CONFLICT DO NOTHING
        """
    )

    # Corrige automaticamente o bug historico apenas quando a evidencia e
    # inequivoca: custo antigo da rota (sem moto) igual a uma unica taxa fixa.
    # Nesse caso cada parada recebe a taxa e o total da rota passa a ser taxa x entregas.
    op.execute(
        """
        WITH fixed_routes AS (
            SELECT
                r.id AS rota_id,
                r.tenant_id,
                c.taxa_fixa_entrega::numeric AS taxa,
                COALESCE(r.custo_moto, 0)::numeric AS custo_moto,
                COUNT(p.id)::integer AS total_paradas,
                MAX(p.id) AS ultima_parada_id
            FROM rotas_entrega r
            JOIN clientes c
              ON c.id = r.entregador_id AND c.tenant_id = r.tenant_id
            JOIN rotas_entrega_paradas p
              ON p.rota_id = r.id AND p.tenant_id = r.tenant_id
            WHERE r.status = 'concluida'
              AND COALESCE(c.controla_rh, false) = false
              AND c.modelo_custo_entrega = 'taxa_fixa'
              AND c.taxa_fixa_entrega IS NOT NULL
            GROUP BY r.id, r.tenant_id, c.taxa_fixa_entrega, r.custo_moto
            HAVING ABS(
                (COALESCE(r.custo_real, 0) - COALESCE(r.custo_moto, 0))
                - c.taxa_fixa_entrega
            ) <= 0.01
        )
        UPDATE rotas_entrega_paradas p
        SET modelo_custo_operacional = 'taxa_fixa',
            valor_base_custo_operacional = f.taxa,
            distancia_custo_km = 0,
            custo_operacional = ROUND(f.taxa, 2),
            custo_moto_rateado = CASE
                WHEN p.id = f.ultima_parada_id THEN
                    f.custo_moto - TRUNC(f.custo_moto / f.total_paradas, 2)
                        * (f.total_paradas - 1)
                ELSE TRUNC(f.custo_moto / f.total_paradas, 2)
            END,
            custo_calculado_em = COALESCE(r.data_conclusao, r.updated_at)
        FROM fixed_routes f
        JOIN rotas_entrega r
          ON r.id = f.rota_id AND r.tenant_id = f.tenant_id
        WHERE p.rota_id = f.rota_id AND p.tenant_id = f.tenant_id
        """
    )
    op.execute(
        """
        WITH fixed_routes AS (
            SELECT
                r.id AS rota_id,
                r.tenant_id,
                c.taxa_fixa_entrega::numeric AS taxa,
                COALESCE(r.custo_moto, 0)::numeric AS custo_moto,
                COUNT(p.id)::integer AS total_paradas
            FROM rotas_entrega r
            JOIN clientes c
              ON c.id = r.entregador_id AND c.tenant_id = r.tenant_id
            JOIN rotas_entrega_paradas p
              ON p.rota_id = r.id AND p.tenant_id = r.tenant_id
            WHERE r.status = 'concluida'
              AND COALESCE(c.controla_rh, false) = false
              AND c.modelo_custo_entrega = 'taxa_fixa'
              AND c.taxa_fixa_entrega IS NOT NULL
            GROUP BY r.id, r.tenant_id, c.taxa_fixa_entrega, r.custo_moto, r.custo_real
            HAVING ABS(
                (COALESCE(r.custo_real, 0) - COALESCE(r.custo_moto, 0))
                - c.taxa_fixa_entrega
            ) <= 0.01
        )
        UPDATE rotas_entrega r
        SET custo_real = ROUND(f.taxa * f.total_paradas + f.custo_moto, 2)
        FROM fixed_routes f
        WHERE r.id = f.rota_id AND r.tenant_id = f.tenant_id
        """
    )

    # Para os demais registros legados, preserva o total historico e o reparte
    # entre as entregas, deixando explicito que a origem nao tinha snapshot.
    op.execute(
        """
        WITH legacy_routes AS (
            SELECT
                r.id AS rota_id,
                r.tenant_id,
                GREATEST(COALESCE(r.custo_real, 0) - COALESCE(r.custo_moto, 0), 0)::numeric
                    AS custo_entregador,
                COALESCE(r.custo_moto, 0)::numeric AS custo_moto,
                COUNT(p.id)::integer AS total_paradas,
                MAX(p.id) AS ultima_parada_id
            FROM rotas_entrega r
            JOIN rotas_entrega_paradas p
              ON p.rota_id = r.id AND p.tenant_id = r.tenant_id
            WHERE r.status = 'concluida'
              AND p.custo_operacional IS NULL
            GROUP BY r.id, r.tenant_id, r.custo_real, r.custo_moto
        )
        UPDATE rotas_entrega_paradas p
        SET modelo_custo_operacional = 'legado_rateado',
            valor_base_custo_operacional = ROUND(
                l.custo_entregador / l.total_paradas, 4
            ),
            custo_operacional = CASE
                WHEN p.id = l.ultima_parada_id THEN
                    l.custo_entregador - TRUNC(l.custo_entregador / l.total_paradas, 2)
                        * (l.total_paradas - 1)
                ELSE TRUNC(l.custo_entregador / l.total_paradas, 2)
            END,
            custo_moto_rateado = CASE
                WHEN p.id = l.ultima_parada_id THEN
                    l.custo_moto - TRUNC(l.custo_moto / l.total_paradas, 2)
                        * (l.total_paradas - 1)
                ELSE TRUNC(l.custo_moto / l.total_paradas, 2)
            END,
            custo_calculado_em = COALESCE(r.data_conclusao, r.updated_at)
        FROM legacy_routes l
        JOIN rotas_entrega r
          ON r.id = l.rota_id AND r.tenant_id = l.tenant_id
        WHERE p.rota_id = l.rota_id AND p.tenant_id = l.tenant_id
          AND p.custo_operacional IS NULL
        """
    )


def downgrade():
    op.drop_column("rotas_entrega_paradas", "custo_calculado_em")
    op.drop_column("rotas_entrega_paradas", "custo_moto_rateado")
    op.drop_column("rotas_entrega_paradas", "custo_operacional")
    op.drop_column("rotas_entrega_paradas", "distancia_custo_km")
    op.drop_column("rotas_entrega_paradas", "valor_base_custo_operacional")
    op.drop_column("rotas_entrega_paradas", "modelo_custo_operacional")
    op.drop_column("rotas_entrega_paradas", "tentativas")
    op.drop_index(
        "ix_rotas_entrega_rastreio_tokens_tenant_id",
        table_name="rotas_entrega_rastreio_tokens",
    )
    op.drop_table("rotas_entrega_rastreio_tokens")
