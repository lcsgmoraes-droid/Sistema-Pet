"""add_auditoria_campos_dre_detalhe

Revision ID: add_auditoria_dre_001
Revises: 
Create Date: 2026-01-31 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'add_auditoria_dre_001'
down_revision = None  # Ajustar para a última migration existente
branch_labels = None
depends_on = None


def upgrade():
    """
    Adiciona campos de auditoria e rastreabilidade ao DRE Detalhe Canal
    """
    # Verificar se a tabela existe antes de adicionar colunas
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    
    if 'dre_detalhe_canais' not in inspector.get_table_names():
        print("⚠️  Tabela dre_detalhe_canais não existe, pulando migration de auditoria")
        return
    
    columns = [col['name'] for col in inspector.get_columns('dre_detalhe_canais')]
    
    # Adicionar campos de auditoria apenas se não existirem
    if 'origem' not in columns:
        op.add_column(
            "dre_detalhe_canais",
            sa.Column("origem", sa.String(50), nullable=True,
                     comment="Tipo de lançamento: PROVISAO, AJUSTE, REAL")
        )
    
    if 'origem_evento' not in columns:
        op.add_column(
            "dre_detalhe_canais",
            sa.Column("origem_evento", sa.String(50), nullable=True,
                     comment="Evento que gerou: NF, DAS, FGTS, FERIAS, 13, BOLETO")
        )
    
    if 'referencia_id' not in columns:
        op.add_column(
            "dre_detalhe_canais",
            sa.Column("referencia_id", sa.String(100), nullable=True,
                     comment="ID da NF, Conta a Pagar, etc")
        )
    
    if 'observacao' not in columns:
        op.add_column(
            "dre_detalhe_canais",
            sa.Column("observacao", sa.Text, nullable=True,
                     comment="Texto humano explicativo")
        )
    
    # Criar índices se não existirem
    indexes = [idx['name'] for idx in inspector.get_indexes('dre_detalhe_canais')]
    
    if 'ix_dre_detalhe_canais_origem' not in indexes:
        op.create_index(
            'ix_dre_detalhe_canais_origem',
            'dre_detalhe_canais',
            ['origem'],
            unique=False
        )
    
    if 'ix_dre_detalhe_canais_origem_evento' not in indexes:
        op.create_index(
            'ix_dre_detalhe_canais_origem_evento',
            'dre_detalhe_canais',
            ['origem_evento'],
            unique=False
        )
    
    op.create_index(
        'ix_dre_detalhe_canais_referencia_id',
        'dre_detalhe_canais',
        ['referencia_id'],
        unique=False
    )
    
    op.create_index(
        'ix_dre_detalhe_canais_criado_em',
        'dre_detalhe_canais',
        ['criado_em'],
        unique=False
    )


def downgrade():
    """
    Remove campos de auditoria
    """
    # Remover índices
    op.drop_index('ix_dre_detalhe_canais_criado_em', table_name='dre_detalhe_canais')
    op.drop_index('ix_dre_detalhe_canais_referencia_id', table_name='dre_detalhe_canais')
    op.drop_index('ix_dre_detalhe_canais_origem_evento', table_name='dre_detalhe_canais')
    op.drop_index('ix_dre_detalhe_canais_origem', table_name='dre_detalhe_canais')
    
    # Remover colunas
    op.drop_column("dre_detalhe_canais", "observacao")
    op.drop_column("dre_detalhe_canais", "referencia_id")
    op.drop_column("dre_detalhe_canais", "origem_evento")
    op.drop_column("dre_detalhe_canais", "origem")
