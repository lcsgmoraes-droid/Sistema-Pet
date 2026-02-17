"""add_entregador_fields_and_cargos

Revision ID: 20260215_add_entregador_fields
Revises: 20260215_add_missing_features
Create Date: 2026-02-15 18:45:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.engine.reflection import Inspector


# revision identifiers, used by Alembic.
revision = '20260215_add_entregador_fields'
down_revision = '20260215_add_missing_features'
branch_labels = None
depends_on = None


def table_exists(table_name):
    """Verifica se uma tabela existe"""
    bind = op.get_bind()
    inspector = Inspector.from_engine(bind)
    return table_name in inspector.get_table_names()


def column_exists(table_name, column_name):
    """Verifica se uma coluna existe em uma tabela"""
    bind = op.get_bind()
    inspector = Inspector.from_engine(bind)
    columns = [col['name'] for col in inspector.get_columns(table_name)]
    return column_name in columns


def upgrade():
    """
    Adiciona:
    1. Tabela cargos (se não existir)
    2. Campo cargo_id em clientes
    3. Campos de entregador faltantes na tabela clientes
    """
    
    print("\n" + "="*80)
    print("🚀 Iniciando migration: add_entregador_fields_and_cargos")
    print("="*80)
    
    # 👔 ETAPA 1: Criar tabela cargos
    print("\n📝 [1/3] Processando tabela cargos...")
    if not table_exists('cargos'):
        print("   ✅ Criando tabela: cargos")
        op.create_table(
            'cargos',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('user_id', sa.Integer(), nullable=False),
            sa.Column('tenant_id', UUID(as_uuid=True), nullable=False),
            sa.Column('nome', sa.String(100), nullable=False),
            sa.Column('descricao', sa.Text(), nullable=True),
            sa.Column('salario_base', sa.Numeric(), nullable=False),
            sa.Column('inss_patronal_percentual', sa.Numeric(), nullable=False, server_default='20'),
            sa.Column('fgts_percentual', sa.Numeric(), nullable=False, server_default='8'),
            sa.Column('gera_ferias', sa.Boolean(), nullable=False, server_default='1'),
            sa.Column('gera_decimo_terceiro', sa.Boolean(), nullable=False, server_default='1'),
            sa.Column('ativo', sa.Boolean(), nullable=False, server_default='1'),
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
            sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
            sa.PrimaryKeyConstraint('id')
        )
        
        # Criar índices
        op.create_index('ix_cargos_id', 'cargos', ['id'])
        op.create_index('ix_cargos_tenant_id', 'cargos', ['tenant_id'])
        op.create_index('ix_cargos_user_id', 'cargos', ['user_id'])
        op.create_index('ix_cargos_nome', 'cargos', ['nome'])
        
        # Criar foreign keys
        op.create_foreign_key('cargos_user_id_fkey', 'cargos', 'users', ['user_id'], ['id'])
        op.create_foreign_key('fk_cargos_tenant', 'cargos', 'tenants', ['tenant_id'], ['id'], ondelete='RESTRICT')
        
        print("   ✅ Índices e foreign keys criados")
    else:
        print("   ⏭️  Tabela já existe: cargos")
    
    # 👔 ETAPA 2: Adicionar campo cargo_id em clientes
    print("\n📝 [2/3] Adicionando campo cargo_id em clientes...")
    if not column_exists('clientes', 'cargo_id'):
        print("   ✅ Adicionando coluna: clientes.cargo_id")
        op.add_column('clientes', 
            sa.Column('cargo_id', sa.Integer(), nullable=True)
        )
        # Adicionar índice
        op.create_index('ix_clientes_cargo_id', 'clientes', ['cargo_id'])
        # Adicionar FK
        op.create_foreign_key('clientes_cargo_id_fkey', 'clientes', 'cargos', ['cargo_id'], ['id'])
        print("   ✅ Índice e foreign key criados")
    else:
        print("   ⏭️  Coluna já existe: clientes.cargo_id")
    
    # 🚚 ETAPA 3: Adicionar campos de entregador faltantes
    print("\n📝 [3/3] Adicionando campos de entregador em clientes...")
    
    # entregador_padrao
    if not column_exists('clientes', 'entregador_padrao'):
        print("   ✅ Adicionando coluna: clientes.entregador_padrao")
        op.add_column('clientes', 
            sa.Column('entregador_padrao', sa.Boolean(), nullable=False, server_default='0')
        )
    else:
        print("   ⏭️  Coluna já existe: clientes.entregador_padrao")
    
    # gera_conta_pagar_custo_entrega
    if not column_exists('clientes', 'gera_conta_pagar_custo_entrega'):
        print("   ✅ Adicionando coluna: clientes.gera_conta_pagar_custo_entrega")
        op.add_column('clientes', 
            sa.Column('gera_conta_pagar_custo_entrega', sa.Boolean(), nullable=False, server_default='0')
        )
    else:
        print("   ⏭️  Coluna já existe: clientes.gera_conta_pagar_custo_entrega")
    
    print("\n" + "="*80)
    print("✅ Migration concluída com sucesso!")
    print("="*80 + "\n")


def downgrade():
    """
    Remove todas as alterações da migration em ordem reversa
    """
    
    print("\n" + "="*80)
    print("⏮️  Revertendo migration: add_entregador_fields_and_cargos")
    print("="*80)
    
    # ETAPA 3: Remover colunas de entregador
    print("\n📝 [3/3] Removendo campos de entregador...")
    if column_exists('clientes', 'gera_conta_pagar_custo_entrega'):
        print("   ❌ Removendo coluna: clientes.gera_conta_pagar_custo_entrega")
        op.drop_column('clientes', 'gera_conta_pagar_custo_entrega')
    
    if column_exists('clientes', 'entregador_padrao'):
        print("   ❌ Removendo coluna: clientes.entregador_padrao")
        op.drop_column('clientes', 'entregador_padrao')
    
    # ETAPA 2: Remover cargo_id de clientes
    print("\n📝 [2/3] Removendo campo cargo_id de clientes...")
    if column_exists('clientes', 'cargo_id'):
        print("   ❌ Removendo foreign key e coluna: clientes.cargo_id")
        try:
            op.drop_constraint('clientes_cargo_id_fkey', 'clientes', type_='foreignkey')
        except:
            pass
        try:
            op.drop_index('ix_clientes_cargo_id', table_name='clientes')
        except:
            pass
        op.drop_column('clientes', 'cargo_id')
    
    # ETAPA 1: Remover tabela cargos
    print("\n📝 [1/3] Removendo tabela cargos...")
    if table_exists('cargos'):
        print("   ❌ Removendo tabela: cargos")
        # Remover FKs primeiro
        try:
            op.drop_constraint('fk_cargos_tenant', 'cargos', type_='foreignkey')
        except:
            pass
        try:
            op.drop_constraint('cargos_user_id_fkey', 'cargos', type_='foreignkey')
        except:
            pass
        # Remover índices
        try:
            op.drop_index('ix_cargos_nome', table_name='cargos')
            op.drop_index('ix_cargos_user_id', table_name='cargos')
            op.drop_index('ix_cargos_tenant_id', table_name='cargos')
            op.drop_index('ix_cargos_id', table_name='cargos')
        except:
            pass
        # Remover tabela
        op.drop_table('cargos')
    
    print("\n" + "="*80)
    print("✅ Downgrade concluído com sucesso!")
    print("="*80 + "\n")
