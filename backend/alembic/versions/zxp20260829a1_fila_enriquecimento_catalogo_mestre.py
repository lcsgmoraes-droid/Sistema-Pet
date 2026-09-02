"""adiciona reserva segura a fila do catalogo mestre

Revision ID: zxp20260829a1
Revises: zxo20260829a1
Create Date: 2026-08-29
"""

from alembic import op
import sqlalchemy as sa


revision = "zxp20260829a1"
down_revision = "zxo20260829a1"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "catalogo_mestre_pendencias",
        sa.Column("reservada_por", sa.String(length=120), nullable=True),
    )
    op.add_column(
        "catalogo_mestre_pendencias",
        sa.Column("reserva_expira_em", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "catalogo_mestre_pendencias",
        sa.Column("ultima_execucao_em", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index(
        "ix_catalogo_mestre_pendencias_reservada_por",
        "catalogo_mestre_pendencias",
        ["reservada_por"],
        unique=False,
    )
    op.create_index(
        "ix_catalogo_mestre_pendencias_reserva_expira_em",
        "catalogo_mestre_pendencias",
        ["reserva_expira_em"],
        unique=False,
    )
    op.create_index(
        "ix_catalogo_mestre_pendencias_ultima_execucao_em",
        "catalogo_mestre_pendencias",
        ["ultima_execucao_em"],
        unique=False,
    )
    op.create_table(
        "catalogo_mestre_enriquecimento_execucoes",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("pendencia_id", sa.Integer(), nullable=True),
        sa.Column("produto_id", sa.Integer(), nullable=True),
        sa.Column("tipo", sa.String(length=50), nullable=False),
        sa.Column("provedor", sa.String(length=50), nullable=False),
        sa.Column("modelo", sa.String(length=120), nullable=False),
        sa.Column("versao_prompt", sa.String(length=120), nullable=False),
        sa.Column("worker_id", sa.String(length=120), nullable=False),
        sa.Column(
            "status", sa.String(length=30), nullable=False, server_default="processando"
        ),
        sa.Column("erro", sa.Text(), nullable=True),
        sa.Column("metadados", sa.JSON(), nullable=True),
        sa.Column("iniciada_em", sa.DateTime(timezone=True), nullable=False),
        sa.Column("concluida_em", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["pendencia_id"],
            ["catalogo_mestre_pendencias.id"],
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["produto_id"],
            ["catalogo_mestre_produtos.id"],
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    for column_name in ("pendencia_id", "produto_id", "tipo", "worker_id"):
        op.create_index(
            f"ix_catalogo_mestre_enriquecimento_execucoes_{column_name}",
            "catalogo_mestre_enriquecimento_execucoes",
            [column_name],
            unique=False,
        )
    op.create_index(
        "ix_catalogo_mestre_enriquecimento_execucoes_dia",
        "catalogo_mestre_enriquecimento_execucoes",
        ["iniciada_em", "tipo"],
        unique=False,
    )
    op.create_index(
        "ix_catalogo_mestre_enriquecimento_execucoes_status",
        "catalogo_mestre_enriquecimento_execucoes",
        ["status", "iniciada_em"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_catalogo_mestre_enriquecimento_execucoes_status",
        table_name="catalogo_mestre_enriquecimento_execucoes",
    )
    op.drop_index(
        "ix_catalogo_mestre_enriquecimento_execucoes_dia",
        table_name="catalogo_mestre_enriquecimento_execucoes",
    )
    for column_name in ("worker_id", "tipo", "produto_id", "pendencia_id"):
        op.drop_index(
            f"ix_catalogo_mestre_enriquecimento_execucoes_{column_name}",
            table_name="catalogo_mestre_enriquecimento_execucoes",
        )
    op.drop_table("catalogo_mestre_enriquecimento_execucoes")
    op.drop_index(
        "ix_catalogo_mestre_pendencias_ultima_execucao_em",
        table_name="catalogo_mestre_pendencias",
    )
    op.drop_index(
        "ix_catalogo_mestre_pendencias_reserva_expira_em",
        table_name="catalogo_mestre_pendencias",
    )
    op.drop_index(
        "ix_catalogo_mestre_pendencias_reservada_por",
        table_name="catalogo_mestre_pendencias",
    )
    op.drop_column("catalogo_mestre_pendencias", "ultima_execucao_em")
    op.drop_column("catalogo_mestre_pendencias", "reserva_expira_em")
    op.drop_column("catalogo_mestre_pendencias", "reservada_por")
