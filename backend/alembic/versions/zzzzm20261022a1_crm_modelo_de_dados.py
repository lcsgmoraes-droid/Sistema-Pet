"""CRM etapa 1.4: funil, colunas, leads, oportunidades, historico e agenda

Revision ID: zzzzm20261022a1
Revises: zzzzl20261022a1
Create Date: 2026-10-22

Tudo por loja (tenant) com isolamento por RLS. Veja docs/crm/CONTRATOS_CONCEITUAIS.md.
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from app.tenant_rls_migration import apply_tenant_rls


revision = "zzzzm20261022a1"
down_revision = "zzzzl20261022a1"
branch_labels = None
depends_on = None

TABLES = (
    "crm_funis",
    "crm_colunas",
    "crm_leads",
    "crm_oportunidades",
    "crm_movimentacoes",
    "crm_interacoes",
    "crm_acoes",
    "crm_proximos_passos",
)


def _base(table):
    return (
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
    )


def _ts(name, nullable=True, default_now=False):
    return sa.Column(
        name,
        sa.DateTime(timezone=True),
        nullable=nullable,
        server_default=sa.text("now()") if default_now else None,
    )


def _fk(name, target, nullable=True):
    return sa.Column(name, sa.Integer(), sa.ForeignKey(target), nullable=nullable)


def upgrade() -> None:
    op.create_table(
        "crm_funis",
        *_base("crm_funis"),
        sa.Column("nome", sa.String(80), nullable=False),
        sa.Column("padrao", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("ativo", sa.Boolean(), nullable=False, server_default="true"),
    )
    op.create_index(
        "uq_crm_funis_padrao",
        "crm_funis",
        ["tenant_id"],
        unique=True,
        postgresql_where=sa.text("padrao"),
    )

    op.create_table(
        "crm_colunas",
        *_base("crm_colunas"),
        _fk("funil_id", "crm_funis.id", nullable=False),
        sa.Column("nome", sa.String(60), nullable=False),
        sa.Column("ordem", sa.Integer(), nullable=False),
        sa.Column("tipo", sa.String(20), nullable=False),
        sa.Column("janela_dias", sa.Integer()),
        sa.Column("ativo", sa.Boolean(), nullable=False, server_default="true"),
    )
    op.create_index(
        "ix_crm_colunas_funil_ordem", "crm_colunas", ["tenant_id", "funil_id", "ordem"]
    )

    op.create_table(
        "crm_leads",
        *_base("crm_leads"),
        _fk("funil_id", "crm_funis.id", nullable=False),
        _fk("coluna_id", "crm_colunas.id", nullable=False),
        _fk("cliente_id", "clientes.id"),
        sa.Column("telefone", sa.String(40)),
        sa.Column("nome_exibicao", sa.String(200)),
        sa.Column("origem", sa.String(40), nullable=False, server_default="manual"),
        _fk("responsavel_user_id", "users.id"),
        sa.Column("valor_estimado", sa.Numeric(12, 2)),
        sa.Column("ciclo_atual", sa.Integer(), nullable=False, server_default="1"),
        _ts("coluna_desde"),
        _ts("ultimo_contato_em"),
        sa.Column("motivo_perda", sa.String(200)),
        _fk("separado_de_lead_id", "crm_leads.id"),
    )
    op.create_index("ix_crm_leads_cliente_id", "crm_leads", ["cliente_id"])
    op.create_index("ix_crm_leads_coluna", "crm_leads", ["tenant_id", "coluna_id"])
    op.create_index(
        "ix_crm_leads_responsavel", "crm_leads", ["tenant_id", "responsavel_user_id"]
    )
    op.create_index(
        "uq_crm_leads_cliente",
        "crm_leads",
        ["tenant_id", "cliente_id"],
        unique=True,
        postgresql_where=sa.text(
            "cliente_id IS NOT NULL AND separado_de_lead_id IS NULL"
        ),
    )
    op.create_index(
        "uq_crm_leads_telefone_sem_cadastro",
        "crm_leads",
        ["tenant_id", "telefone"],
        unique=True,
        postgresql_where=sa.text(
            "cliente_id IS NULL AND separado_de_lead_id IS NULL "
            "AND telefone IS NOT NULL"
        ),
    )

    op.create_table(
        "crm_oportunidades",
        *_base("crm_oportunidades"),
        _fk("lead_id", "crm_leads.id", nullable=False),
        sa.Column("ciclo", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("tipo", sa.String(40), nullable=False),
        sa.Column("detalhe", sa.String(300)),
        sa.Column("estado", sa.String(20), nullable=False, server_default="aberta"),
        sa.Column("motivo", sa.String(200)),
        sa.Column("generica", sa.Boolean(), nullable=False, server_default="false"),
        _ts("resolvida_em"),
    )
    op.create_index(
        "ix_crm_oportunidades_lead",
        "crm_oportunidades",
        ["tenant_id", "lead_id", "ciclo"],
    )

    op.create_table(
        "crm_movimentacoes",
        *_base("crm_movimentacoes"),
        _fk("lead_id", "crm_leads.id", nullable=False),
        sa.Column("ciclo", sa.Integer(), nullable=False, server_default="1"),
        _fk("coluna_origem_id", "crm_colunas.id"),
        _fk("coluna_destino_id", "crm_colunas.id", nullable=False),
        _fk("user_id", "users.id"),
        sa.Column("nota", sa.Text()),
    )
    op.create_index(
        "ix_crm_movimentacoes_lead",
        "crm_movimentacoes",
        ["tenant_id", "lead_id", "created_at"],
    )

    op.create_table(
        "crm_interacoes",
        *_base("crm_interacoes"),
        _fk("lead_id", "crm_leads.id"),
        _fk("cliente_id", "clientes.id"),
        sa.Column("tipo", sa.String(40), nullable=False),
        sa.Column("resumo", sa.String(500), nullable=False),
        sa.Column("origem", sa.String(40), nullable=False, server_default="sistema"),
        _ts("ocorrida_em", nullable=False, default_now=True),
    )
    op.create_index(
        "ix_crm_interacoes_lead", "crm_interacoes", ["tenant_id", "lead_id", "ocorrida_em"]
    )
    op.create_index(
        "ix_crm_interacoes_cliente",
        "crm_interacoes",
        ["tenant_id", "cliente_id", "ocorrida_em"],
    )

    op.create_table(
        "crm_acoes",
        *_base("crm_acoes"),
        _fk("lead_id", "crm_leads.id", nullable=False),
        sa.Column("tipo", sa.String(20), nullable=False),
        sa.Column("observacao", sa.Text()),
        _fk("user_id", "users.id"),
        _ts("ocorrida_em", nullable=False, default_now=True),
    )
    op.create_index(
        "ix_crm_acoes_lead", "crm_acoes", ["tenant_id", "lead_id", "ocorrida_em"]
    )

    op.create_table(
        "crm_proximos_passos",
        *_base("crm_proximos_passos"),
        _fk("lead_id", "crm_leads.id", nullable=False),
        sa.Column("tipo", sa.String(20), nullable=False),
        sa.Column("descricao", sa.String(300)),
        _ts("agendado_para", nullable=False),
        _fk("responsavel_user_id", "users.id"),
        _ts("concluido_em"),
    )
    op.create_index(
        "ix_crm_proximos_passos_lead",
        "crm_proximos_passos",
        ["tenant_id", "lead_id", "concluido_em"],
    )
    op.create_index(
        "ix_crm_proximos_passos_agenda",
        "crm_proximos_passos",
        ["tenant_id", "responsavel_user_id", "agendado_para"],
    )

    for table in TABLES:
        op.create_index(f"ix_{table}_tenant_id", table, ["tenant_id"])
    apply_tenant_rls(op_module=op, sa_module=sa, table_names=TABLES, enable=True)


def downgrade() -> None:
    for table in reversed(TABLES):
        op.drop_table(table)
