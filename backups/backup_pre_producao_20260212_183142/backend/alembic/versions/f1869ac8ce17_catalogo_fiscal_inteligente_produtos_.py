from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'f1869ac8ce17'
down_revision = '658cbbfe90c6'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'fiscal_catalogo_produtos',
        sa.Column('id', sa.Integer, primary_key=True),
        sa.Column('palavras_chave', sa.Text, nullable=False),
        sa.Column('categoria_fiscal', sa.String(100), nullable=False),

        sa.Column('ncm', sa.String(10)),
        sa.Column('cest', sa.String(10)),
        sa.Column('cst_icms', sa.String(3)),
        sa.Column('icms_st', sa.Boolean),

        sa.Column('pis_cst', sa.String(3)),
        sa.Column('cofins_cst', sa.String(3)),

        sa.Column('observacao', sa.Text),
        sa.Column('ativo', sa.Boolean, server_default=sa.text('true')),
        sa.Column('created_at', sa.DateTime, server_default=sa.func.now())
    )

    # Seed inicial — PET SHOP
    dados = [
        (
            'ração,cachorro,cão,pet food',
            'Ração para cães',
            '2309.10.00',
            '17.018.00',
            '060',
            True,
            '01',
            '01',
            'Ração para cães, normalmente sujeita a ICMS ST em vários estados'
        ),
        (
            'ração,gato,felino,pet food',
            'Ração para gatos',
            '2309.10.00',
            '17.018.00',
            '060',
            True,
            '01',
            '01',
            'Ração para gatos, normalmente sujeita a ICMS ST'
        ),
        (
            'shampoo,pet,banho,higiene',
            'Higiene animal',
            '3305.90.00',
            '20.024.00',
            '060',
            True,
            '01',
            '01',
            'Produtos de higiene para animais'
        ),
        (
            'brinquedo,pet,osso,bola',
            'Brinquedos para animais',
            '9503.00.99',
            None,
            '060',
            False,
            '01',
            '01',
            'Brinquedos e acessórios para pets'
        ),
        (
            'medicamento,pet,antipulga,vermífugo',
            'Medicamentos veterinários',
            '3004.90.99',
            None,
            '040',
            False,
            '01',
            '01',
            'Medicamentos veterinários podem ter regras específicas por estado'
        )
    ]

    for d in dados:
        op.execute(
            f"""
                INSERT INTO fiscal_catalogo_produtos
                (palavras_chave, categoria_fiscal, ncm, cest, cst_icms,
                 icms_st, pis_cst, cofins_cst, observacao)
                VALUES
                ('{d[0]}', '{d[1]}', '{d[2]}', {'NULL' if d[3] is None else "'" + d[3] + "'"}, '{d[4]}', 
                 {d[5]}, '{d[6]}', '{d[7]}', '{d[8]}')
            """
        )


def downgrade():
    op.drop_table('fiscal_catalogo_produtos')
