"""add missing features: recorrencia, comissoes, segmentacao

Revision ID: 20260215_add_missing_features
Revises: 20260215_add_racao_jsonb_fields, ed82d13a98a0
Create Date: 2026-02-15 18:15:00.000000

Adiciona features que faltavam no banco de produção:
1. Colunas de recorrência em contas_receber e contas_pagar
2. Colunas de comissão/cargo em clientes
3. Tabela cliente_segmentos para segmentação de clientes

SEGURO PARA PRODUÇÃO: Verifica existência antes de criar

⚠️ MERGE: Unifica duas branches paralelas (racao_jsonb + final_merge)
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect, text
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '20260215_add_missing_features'
down_revision = ('20260215_add_racao_jsonb_fields', 'ed82d13a98a0')
branch_labels = None
depends_on = None


def column_exists(table_name, column_name):
    """Verifica se uma coluna existe em uma tabela"""
    bind = op.get_bind()
    inspector = inspect(bind)
    columns = [col['name'] for col in inspector.get_columns(table_name)]
    return column_name in columns


def table_exists(table_name):
    """Verifica se uma tabela existe"""
    bind = op.get_bind()
    inspector = inspect(bind)
    return table_name in inspector.get_table_names()


def index_exists(index_name):
    """Verifica se um índice existe"""
    bind = op.get_bind()
    result = bind.execute(text("""
        SELECT 1 FROM pg_indexes 
        WHERE indexname = :index_name
    """), {"index_name": index_name})
    return result.fetchone() is not None


def upgrade():
    """Adiciona features faltantes com verificação de existência"""
    
    print("=" * 80)
    print("🚀 Iniciando migration: add_missing_features")
    print("=" * 80)
    
    # ============================================================================
    # 1. CONTAS_RECEBER - Adicionar colunas de recorrência
    # ============================================================================
    print("\n📝 [1/4] Processando contas_receber...")
    
    recorrencia_columns = [
        ('eh_recorrente', sa.Boolean(), {'server_default': 'false'}),
        ('tipo_recorrencia', sa.String(20), {}),
        ('intervalo_dias', sa.Integer(), {}),
        ('data_inicio_recorrencia', sa.Date(), {}),
        ('data_fim_recorrencia', sa.Date(), {}),
        ('numero_repeticoes', sa.Integer(), {}),
        ('proxima_recorrencia', sa.Date(), {}),
    ]
    
    for col_name, col_type, kwargs in recorrencia_columns:
        if not column_exists('contas_receber', col_name):
            print(f"   ✅ Adicionando coluna: contas_receber.{col_name}")
            op.add_column('contas_receber', sa.Column(col_name, col_type, **kwargs))
        else:
            print(f"   ⏭️  Coluna já existe: contas_receber.{col_name}")
    
    # FK para conta_recorrencia_origem_id
    if not column_exists('contas_receber', 'conta_recorrencia_origem_id'):
        print(f"   ✅ Adicionando coluna FK: contas_receber.conta_recorrencia_origem_id")
        op.add_column('contas_receber', 
            sa.Column('conta_recorrencia_origem_id', sa.Integer(), nullable=True))
        try:
            op.create_foreign_key(
                'fk_contas_receber_origem', 
                'contas_receber', 
                'contas_receber', 
                ['conta_recorrencia_origem_id'], 
                ['id']
            )
        except Exception as e:
            print(f"   ⚠️  FK já existe ou erro: {e}")
    else:
        print(f"   ⏭️  Coluna já existe: contas_receber.conta_recorrencia_origem_id")
    
    # ============================================================================
    # 2. CONTAS_PAGAR - Adicionar colunas de recorrência
    # ============================================================================
    print("\n📝 [2/4] Processando contas_pagar...")
    
    # Verificar se contas_pagar tem as mesmas colunas
    for col_name, col_type, kwargs in recorrencia_columns:
        if not column_exists('contas_pagar', col_name):
            print(f"   ✅ Adicionando coluna: contas_pagar.{col_name}")
            op.add_column('contas_pagar', sa.Column(col_name, col_type, **kwargs))
        else:
            print(f"   ⏭️  Coluna já existe: contas_pagar.{col_name}")
    
    # FK para conta_recorrencia_origem_id
    if not column_exists('contas_pagar', 'conta_recorrencia_origem_id'):
        print(f"   ✅ Adicionando coluna FK: contas_pagar.conta_recorrencia_origem_id")
        op.add_column('contas_pagar', 
            sa.Column('conta_recorrencia_origem_id', sa.Integer(), nullable=True))
        try:
            op.create_foreign_key(
                'fk_contas_pagar_origem', 
                'contas_pagar', 
                'contas_pagar', 
                ['conta_recorrencia_origem_id'], 
                ['id']
            )
        except Exception as e:
            print(f"   ⚠️  FK já existe ou erro: {e}")
    else:
        print(f"   ⏭️  Coluna já existe: contas_pagar.conta_recorrencia_origem_id")
    
    # ============================================================================
    # 3. CLIENTES - Adicionar colunas de comissão/cargo
    # ============================================================================
    print("\n📝 [3/4] Processando clientes...")
    
    # cargo_id - apenas se tabela cargos existir
    if table_exists('cargos'):
        if not column_exists('clientes', 'cargo_id'):
            print(f"   ✅ Adicionando coluna: clientes.cargo_id (FK para cargos)")
            op.add_column('clientes', sa.Column('cargo_id', sa.Integer(), nullable=True))
            try:
                op.create_foreign_key(
                    'fk_clientes_cargo',
                    'clientes',
                    'cargos',
                    ['cargo_id'],
                    ['id']
                )
            except Exception as e:
                print(f"   ⚠️  FK já existe ou erro: {e}")
        else:
            print(f"   ⏭️  Coluna já existe: clientes.cargo_id")
    else:
        print(f"   ⚠️  Tabela 'cargos' não existe, pulando cargo_id")
    
    # data_fechamento_comissao
    if not column_exists('clientes', 'data_fechamento_comissao'):
        print(f"   ✅ Adicionando coluna: clientes.data_fechamento_comissao")
        op.add_column('clientes', sa.Column('data_fechamento_comissao', sa.Date(), nullable=True))
    else:
        print(f"   ⏭️  Coluna já existe: clientes.data_fechamento_comissao")
    
    # ============================================================================
    # 4. CLIENTE_SEGMENTOS - Criar tabela de segmentação
    # ============================================================================
    print("\n📝 [4/4] Processando cliente_segmentos...")
    
    if not table_exists('cliente_segmentos'):
        print(f"   ✅ Criando tabela: cliente_segmentos")
        
        op.create_table(
            'cliente_segmentos',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('cliente_id', sa.Integer(), nullable=False),
            sa.Column('user_id', sa.Integer(), nullable=False),
            sa.Column('tenant_id', postgresql.UUID(), nullable=False),
            sa.Column('segmento', sa.String(length=50), nullable=False),
            sa.Column('metricas', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
            sa.Column('tags', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
            sa.Column('observacoes', sa.Text(), nullable=True),
            sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=True),
            sa.Column('updated_at', sa.DateTime(), server_default=sa.text('now()'), nullable=True),
            sa.PrimaryKeyConstraint('id')
        )
        
        # Foreign Keys
        print(f"   ✅ Criando foreign keys...")
        op.create_foreign_key(
            'fk_cliente_segmentos_cliente',
            'cliente_segmentos', 
            'clientes',
            ['cliente_id'], 
            ['id']
        )
        op.create_foreign_key(
            'fk_cliente_segmentos_user',
            'cliente_segmentos',
            'users',
            ['user_id'],
            ['id']
        )
        
        # Indexes
        print(f"   ✅ Criando índices...")
        indexes_to_create = [
            ('idx_cliente_segmentos_id', ['id']),
            ('idx_cliente_segmentos_cliente_id', ['cliente_id']),
            ('idx_cliente_segmentos_user_id', ['user_id']),
            ('idx_cliente_segmentos_segmento', ['segmento']),
            ('idx_cliente_segmentos_updated_at', ['updated_at']),
            ('idx_cliente_segmentos_tenant', ['tenant_id']),
            ('idx_cliente_segmentos_tenant_cliente', ['tenant_id', 'cliente_id']),
        ]
        
        for idx_name, columns in indexes_to_create:
            if not index_exists(idx_name):
                op.create_index(idx_name, 'cliente_segmentos', columns)
    else:
        print(f"   ⏭️  Tabela já existe: cliente_segmentos")
    
    print("\n" + "=" * 80)
    print("✅ Migration concluída com sucesso!")
    print("=" * 80)


def downgrade():
    """Remove features adicionadas (ordem inversa)"""
    
    print("=" * 80)
    print("⬇️  Iniciando downgrade: add_missing_features")
    print("=" * 80)
    
    # ============================================================================
    # 4. Remover tabela cliente_segmentos
    # ============================================================================
    print("\n📝 [1/4] Removendo cliente_segmentos...")
    if table_exists('cliente_segmentos'):
        # Drop indexes primeiro
        indexes_to_drop = [
            'idx_cliente_segmentos_id',
            'idx_cliente_segmentos_cliente_id',
            'idx_cliente_segmentos_user_id',
            'idx_cliente_segmentos_segmento',
            'idx_cliente_segmentos_updated_at',
            'idx_cliente_segmentos_tenant',
            'idx_cliente_segmentos_tenant_cliente',
        ]
        
        for idx_name in indexes_to_drop:
            if index_exists(idx_name):
                try:
                    op.drop_index(idx_name, table_name='cliente_segmentos')
                    print(f"   ✅ Índice removido: {idx_name}")
                except Exception as e:
                    print(f"   ⚠️  Erro ao remover índice {idx_name}: {e}")
        
        # Drop table
        op.drop_table('cliente_segmentos')
        print(f"   ✅ Tabela removida: cliente_segmentos")
    else:
        print(f"   ⏭️  Tabela não existe: cliente_segmentos")
    
    # ============================================================================
    # 3. Remover colunas de clientes
    # ============================================================================
    print("\n📝 [2/4] Removendo colunas de clientes...")
    
    if column_exists('clientes', 'data_fechamento_comissao'):
        op.drop_column('clientes', 'data_fechamento_comissao')
        print(f"   ✅ Coluna removida: clientes.data_fechamento_comissao")
    
    if column_exists('clientes', 'cargo_id'):
        # Drop FK first
        try:
            op.drop_constraint('fk_clientes_cargo', 'clientes', type_='foreignkey')
        except Exception:
            pass
        op.drop_column('clientes', 'cargo_id')
        print(f"   ✅ Coluna removida: clientes.cargo_id")
    
    # ============================================================================
    # 2. Remover colunas de contas_pagar
    # ============================================================================
    print("\n📝 [3/4] Removendo colunas de contas_pagar...")
    
    if column_exists('contas_pagar', 'conta_recorrencia_origem_id'):
        try:
            op.drop_constraint('fk_contas_pagar_origem', 'contas_pagar', type_='foreignkey')
        except Exception:
            pass
        op.drop_column('contas_pagar', 'conta_recorrencia_origem_id')
        print(f"   ✅ Coluna removida: contas_pagar.conta_recorrencia_origem_id")
    
    recorrencia_cols = [
        'proxima_recorrencia',
        'numero_repeticoes',
        'data_fim_recorrencia',
        'data_inicio_recorrencia',
        'intervalo_dias',
        'tipo_recorrencia',
        'eh_recorrente',
    ]
    
    for col_name in recorrencia_cols:
        if column_exists('contas_pagar', col_name):
            op.drop_column('contas_pagar', col_name)
            print(f"   ✅ Coluna removida: contas_pagar.{col_name}")
    
    # ============================================================================
    # 1. Remover colunas de contas_receber
    # ============================================================================
    print("\n📝 [4/4] Removendo colunas de contas_receber...")
    
    if column_exists('contas_receber', 'conta_recorrencia_origem_id'):
        try:
            op.drop_constraint('fk_contas_receber_origem', 'contas_receber', type_='foreignkey')
        except Exception:
            pass
        op.drop_column('contas_receber', 'conta_recorrencia_origem_id')
        print(f"   ✅ Coluna removida: contas_receber.conta_recorrencia_origem_id")
    
    for col_name in recorrencia_cols:
        if column_exists('contas_receber', col_name):
            op.drop_column('contas_receber', col_name)
            print(f"   ✅ Coluna removida: contas_receber.{col_name}")
    
    print("\n" + "=" * 80)
    print("✅ Downgrade concluído com sucesso!")
    print("=" * 80)
