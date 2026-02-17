"""base fiscal padrao por estado

Revision ID: 8322a84ec114
Revises: a3d7e5569b20
Create Date: 2026-01-30 22:21:35.872299

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '8322a84ec114'
down_revision = 'a3d7e5569b20'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'fiscal_estado_padrao',
        sa.Column('id', sa.Integer, primary_key=True),
        sa.Column('uf', sa.String(2), nullable=False, unique=True),

        sa.Column('icms_aliquota_interna', sa.Numeric(5, 2), nullable=False),
        sa.Column('icms_aliquota_interestadual', sa.Numeric(5, 2), nullable=False),

        sa.Column('aplica_difal', sa.Boolean, nullable=False, server_default=sa.text('false')),
        sa.Column('cfop_venda_interna', sa.String(4), nullable=False),
        sa.Column('cfop_venda_interestadual', sa.String(4), nullable=False),
        sa.Column('cfop_compra', sa.String(4), nullable=False),

        sa.Column('regime_mais_comum', sa.String(50)),
        sa.Column('observacoes_fiscais', sa.Text),

        sa.Column('created_at', sa.DateTime, server_default=sa.func.now())
    )

    # Seed inicial — valores seguros e ajustáveis
    estados = [
        # UF, ICMS interno, ICMS inter, DIFAL, CFOP int, CFOP inter, CFOP compra, regime, obs
        ('SP', 18.00, 12.00, True, '5102', '6102', '1102', 'Simples Nacional', 'Padrão SEFAZ SP'),
        ('RJ', 18.00, 12.00, True, '5102', '6102', '1102', 'Simples Nacional', None),
        ('MG', 18.00, 12.00, True, '5102', '6102', '1102', 'Simples Nacional', None),
        ('PR', 18.00, 12.00, True, '5102', '6102', '1102', 'Simples Nacional', None),
        ('SC', 17.00, 12.00, True, '5102', '6102', '1102', 'Simples Nacional', None),
        ('RS', 18.00, 12.00, True, '5102', '6102', '1102', 'Simples Nacional', None),

        ('BA', 18.00, 12.00, True, '5102', '6102', '1102', None, None),
        ('PE', 18.00, 12.00, True, '5102', '6102', '1102', None, None),
        ('CE', 18.00, 12.00, True, '5102', '6102', '1102', None, None),
        ('GO', 17.00, 12.00, True, '5102', '6102', '1102', None, None),
        ('DF', 18.00, 12.00, True, '5102', '6102', '1102', None, None),

        # Demais estados — padrão Brasil
        ('AC', 17.00, 12.00, True, '5102', '6102', '1102', None, None),
        ('AL', 18.00, 12.00, True, '5102', '6102', '1102', None, None),
        ('AM', 18.00, 12.00, True, '5102', '6102', '1102', None, None),
        ('AP', 18.00, 12.00, True, '5102', '6102', '1102', None, None),
        ('ES', 17.00, 12.00, True, '5102', '6102', '1102', None, None),
        ('MA', 18.00, 12.00, True, '5102', '6102', '1102', None, None),
        ('MT', 17.00, 12.00, True, '5102', '6102', '1102', None, None),
        ('MS', 17.00, 12.00, True, '5102', '6102', '1102', None, None),
        ('PA', 17.00, 12.00, True, '5102', '6102', '1102', None, None),
        ('PB', 18.00, 12.00, True, '5102', '6102', '1102', None, None),
        ('PI', 18.00, 12.00, True, '5102', '6102', '1102', None, None),
        ('RN', 18.00, 12.00, True, '5102', '6102', '1102', None, None),
        ('RO', 17.50, 12.00, True, '5102', '6102', '1102', None, None),
        ('RR', 17.00, 12.00, True, '5102', '6102', '1102', None, None),
        ('SE', 18.00, 12.00, True, '5102', '6102', '1102', None, None),
        ('TO', 18.00, 12.00, True, '5102', '6102', '1102', None, None),
    ]

    for e in estados:
        op.execute(
            f"""
                INSERT INTO fiscal_estado_padrao
                (uf, icms_aliquota_interna, icms_aliquota_interestadual,
                 aplica_difal, cfop_venda_interna, cfop_venda_interestadual,
                 cfop_compra, regime_mais_comum, observacoes_fiscais)
                VALUES
                ('{e[0]}', {e[1]}, {e[2]}, {e[3]}, '{e[4]}', '{e[5]}', '{e[6]}', 
                 {'NULL' if e[7] is None else "'" + e[7] + "'"}, 
                 {'NULL' if e[8] is None else "'" + e[8] + "'"})
            """
        )


def downgrade():
    op.drop_table('fiscal_estado_padrao')
