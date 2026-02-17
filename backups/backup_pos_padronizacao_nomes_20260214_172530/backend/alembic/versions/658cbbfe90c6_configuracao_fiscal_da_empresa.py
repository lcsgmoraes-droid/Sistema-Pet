"""configuracao fiscal da empresa

Revision ID: 658cbbfe90c6
Revises: 8322a84ec114
Create Date: 2026-01-30 22:25:51.431247

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '658cbbfe90c6'
down_revision = '8322a84ec114'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'empresa_config_fiscal',
        sa.Column('id', sa.Integer, primary_key=True),

        # Multi-tenant
        sa.Column('tenant_id', sa.Integer, nullable=False, index=True),

        # Estado base (herança)
        sa.Column(
            'fiscal_estado_padrao_id',
            sa.Integer,
            sa.ForeignKey('fiscal_estado_padrao.id'),
            nullable=False
        ),

        # Identificação
        sa.Column('uf', sa.String(2), nullable=False),

        # Regime
        sa.Column('regime_tributario', sa.String(50), nullable=False),
        sa.Column('cnae_principal', sa.String(10)),
        sa.Column('contribuinte_icms', sa.Boolean, nullable=False, server_default=sa.text('true')),

        # ICMS
        sa.Column('icms_aliquota_interna', sa.Numeric(5, 2), nullable=False),
        sa.Column('icms_aliquota_interestadual', sa.Numeric(5, 2), nullable=False),
        sa.Column('aplica_difal', sa.Boolean, nullable=False),

        # CFOP padrão
        sa.Column('cfop_venda_interna', sa.String(4), nullable=False),
        sa.Column('cfop_venda_interestadual', sa.String(4), nullable=False),
        sa.Column('cfop_compra', sa.String(4), nullable=False),

        # PIS / COFINS
        sa.Column('pis_cst_padrao', sa.String(3)),
        sa.Column('pis_aliquota', sa.Numeric(5, 2)),
        sa.Column('cofins_cst_padrao', sa.String(3)),
        sa.Column('cofins_aliquota', sa.Numeric(5, 2)),

        # ISS (serviços)
        sa.Column('municipio_iss', sa.String(100)),
        sa.Column('iss_aliquota', sa.Numeric(5, 2)),
        sa.Column('iss_retido', sa.Boolean, server_default=sa.text('false')),

        # Controle
        sa.Column('herdado_do_estado', sa.Boolean, nullable=False, server_default=sa.text('true')),
        sa.Column('created_at', sa.DateTime, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime, onupdate=sa.func.now())
    )

    # Índice único por tenant
    op.create_unique_constraint(
        'uq_empresa_config_fiscal_tenant',
        'empresa_config_fiscal',
        ['tenant_id']
    )


def downgrade():
    op.drop_table('empresa_config_fiscal')
