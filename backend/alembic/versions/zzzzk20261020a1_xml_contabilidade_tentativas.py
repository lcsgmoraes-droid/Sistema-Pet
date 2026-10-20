"""Relatórios imutáveis das tentativas de entrega, com isolamento por empresa."""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from app.tenant_rls_migration import apply_tenant_rls

revision = "zzzzk20261020a1"
down_revision = "zzzzj20261019a1"
branch_labels = None
depends_on = None
TABLES = ("xml_contabilidade_tentativas",)


def upgrade():
    op.create_index(
        "uq_xml_contabilidade_envios_tenant_id_id",
        "xml_contabilidade_envios",
        ["tenant_id", "id"],
        unique=True,
    )
    op.create_table(
        TABLES[0],
        sa.Column("id", sa.Integer(), sa.Identity(always=True), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("envio_id", sa.Integer(), nullable=False),
        sa.Column("numero_tentativa", sa.Integer(), nullable=False),
        sa.Column("iniciado_em", sa.DateTime(timezone=True), nullable=False),
        sa.Column("concluido_em", sa.DateTime(timezone=True), nullable=False),
        sa.Column("resultado", sa.String(30), nullable=False),
        sa.Column("resumo", sa.JSON(), nullable=False),
        sa.Column("snapshot", sa.JSON(), nullable=False),
        sa.ForeignKeyConstraint(
            ["tenant_id", "envio_id"],
            ["xml_contabilidade_envios.tenant_id", "xml_contabilidade_envios.id"],
            ondelete="RESTRICT",
        ),
        sa.UniqueConstraint(
            "tenant_id",
            "envio_id",
            "numero_tentativa",
            name="uq_xml_contabilidade_tentativa_numero",
        ),
    )
    op.create_index(
        "ix_xml_contabilidade_tentativas_tenant_id", TABLES[0], ["tenant_id"]
    )
    op.create_index(
        "ix_xml_contabilidade_tentativas_envio",
        TABLES[0],
        ["tenant_id", "envio_id", "id"],
    )
    apply_tenant_rls(op_module=op, sa_module=sa, table_names=TABLES, enable=True)
    if op.get_bind().dialect.name == "postgresql":
        op.execute(
            """CREATE FUNCTION xml_contabilidade_tentativa_imutavel() RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN RAISE EXCEPTION 'Relatorios de tentativas sao imutaveis'; END; $$"""
        )
        op.execute(
            "CREATE TRIGGER xml_contabilidade_tentativa_imutavel BEFORE UPDATE OR DELETE ON xml_contabilidade_tentativas FOR EACH ROW EXECUTE FUNCTION xml_contabilidade_tentativa_imutavel()"
        )


def downgrade():
    op.drop_table(TABLES[0])
    if op.get_bind().dialect.name == "postgresql":
        op.execute("DROP FUNCTION xml_contabilidade_tentativa_imutavel()")
    op.drop_index(
        "uq_xml_contabilidade_envios_tenant_id_id",
        table_name="xml_contabilidade_envios",
    )
