"""create operadoras cartao

Revision ID: 20260211_create_operadoras
Revises: 20260211_stone_transactions
Create Date: 2026-02-11 16:00:00

FASE 2: Criar tabela operadoras_cartao + FKs + Seed automático
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import text
from sqlalchemy.dialects import postgresql
from datetime import datetime

# revision identifiers, used by Alembic.
revision = '20260211_create_operadoras'
down_revision = '20260211_stone_transactions'
branch_labels = None
depends_on = None


def upgrade():
    # ========================================
    # 1. CRIAR TABELA OPERADORAS_CARTAO
    # ========================================
    op.create_table(
        'operadoras_cartao',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False),
        
        # Dados básicos
        sa.Column('nome', sa.String(length=100), nullable=False),
        sa.Column('codigo', sa.String(length=50), nullable=True),
        
        # Configurações
        sa.Column('max_parcelas', sa.Integer(), nullable=False, server_default='12'),
        sa.Column('padrao', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('ativo', sa.Boolean(), nullable=False, server_default='true'),
        
        # Taxas padrão (opcional)
        sa.Column('taxa_debito', sa.Numeric(5, 2), nullable=True),
        sa.Column('taxa_credito_vista', sa.Numeric(5, 2), nullable=True),
        sa.Column('taxa_credito_parcelado', sa.Numeric(5, 2), nullable=True),
        
        # Integração API
        sa.Column('api_enabled', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('api_endpoint', sa.String(length=255), nullable=True),
        sa.Column('api_token_encrypted', sa.Text(), nullable=True),
        
        # UI
        sa.Column('cor', sa.String(length=7), nullable=True),
        sa.Column('icone', sa.String(length=50), nullable=True),
        
        # Auditoria
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('NOW()')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('NOW()')),
        
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='RESTRICT'),
    )
    
    # Índices
    op.create_index('idx_operadoras_tenant_id', 'operadoras_cartao', ['tenant_id'])
    op.create_index('idx_operadoras_codigo', 'operadoras_cartao', ['codigo'])
    op.create_index(
        'idx_operadoras_padrao', 
        'operadoras_cartao', 
        ['tenant_id', 'padrao'], 
        postgresql_where=sa.text('padrao = true')
    )
    
    # ========================================
    # 2. ADICIONAR FK EM FORMAS_PAGAMENTO
    # ========================================
    op.add_column(
        'formas_pagamento',
        sa.Column('operadora_id', sa.Integer(), nullable=True)
    )
    op.create_foreign_key(
        'fk_formas_pagamento_operadora',
        'formas_pagamento', 'operadoras_cartao',
        ['operadora_id'], ['id'],
        ondelete='SET NULL'
    )
    op.create_index('idx_formas_pagamento_operadora', 'formas_pagamento', ['operadora_id'])
    
    # ========================================
    # 3. ADICIONAR FK EM VENDA_PAGAMENTOS
    # ========================================
    op.add_column(
        'venda_pagamentos',
        sa.Column('operadora_id', sa.Integer(), nullable=True)
    )
    op.create_foreign_key(
        'fk_venda_pagamentos_operadora',
        'venda_pagamentos', 'operadoras_cartao',
        ['operadora_id'], ['id'],
        ondelete='SET NULL'
    )
    op.create_index('idx_venda_pagamentos_operadora', 'venda_pagamentos', ['operadora_id'])
    
    # Índice composto para buscar por NSU + Operadora (evita duplicatas entre operadoras)
    # ⚠️ DEFENSIVO: Criar apenas se coluna nsu_cartao existir
    connection = op.get_bind()
    coluna_nsu_existe = connection.execute(text("""
        SELECT 1
        FROM information_schema.columns
        WHERE table_name = 'venda_pagamentos'
          AND column_name = 'nsu_cartao'
    """)).fetchone()
    
    if coluna_nsu_existe:
        op.create_index(
            'idx_venda_pagamentos_nsu_operadora',
            'venda_pagamentos',
            ['nsu_cartao', 'operadora_id']
        )
    else:
        print("⚠️ Coluna nsu_cartao não existe. Pulando índice idx_venda_pagamentos_nsu_operadora.")
    
    # ========================================
    # 4. SEED AUTOMÁTICO DE OPERADORAS
    # ========================================
    # Importante: Executar apenas se não existir nenhuma operadora
    # Isso evita duplicação em ambientes que já foram migrados
    
    # connection já foi obtido acima para verificação da coluna
    
    # Buscar todos os tenants
    tenants_result = connection.execute(sa.text("SELECT id FROM tenants"))
    tenants = tenants_result.fetchall()
    
    if tenants:
        print(f"🌱 Seed: Criando operadoras padrão para {len(tenants)} tenant(s)...")
        
        # Buscar primeiro usuário de cada tenant para associar
        for tenant in tenants:
            tenant_id = tenant[0]
            
            # Buscar primeiro usuário do tenant
            user_result = connection.execute(
                sa.text("SELECT id FROM users WHERE tenant_id = :tenant_id LIMIT 1"),
                {"tenant_id": tenant_id}
            )
            user = user_result.fetchone()
            
            if not user:
                print(f"⚠️  Tenant {tenant_id}: Nenhum usuário encontrado, pulando seed...")
                continue
            
            user_id = user[0]
            
            # Verificar se já existe alguma operadora para este tenant
            check_result = connection.execute(
                sa.text("SELECT COUNT(*) FROM operadoras_cartao WHERE tenant_id = :tenant_id"),
                {"tenant_id": tenant_id}
            )
            count = check_result.fetchone()[0]
            
            if count > 0:
                print(f"ℹ️  Tenant {tenant_id}: Já possui {count} operadora(s), pulando seed...")
                continue
            
            # Operadoras padrão
            operadoras = [
                {
                    'nome': 'Stone',
                    'codigo': 'STONE',
                    'max_parcelas': 12,
                    'padrao': True,  # Stone como padrão
                    'taxa_debito': 1.49,
                    'taxa_credito_vista': 2.49,
                    'taxa_credito_parcelado': 3.79,
                    'cor': '#00A868',
                    'icone': '💳'
                },
                {
                    'nome': 'Cielo',
                    'codigo': 'CIELO',
                    'max_parcelas': 12,
                    'padrao': False,
                    'taxa_debito': 1.99,
                    'taxa_credito_vista': 2.75,
                    'taxa_credito_parcelado': 4.25,
                    'cor': '#00AEEF',
                    'icone': '🏦'
                },
                {
                    'nome': 'Rede',
                    'codigo': 'REDE',
                    'max_parcelas': 12,
                    'padrao': False,
                    'taxa_debito': 1.89,
                    'taxa_credito_vista': 2.69,
                    'taxa_credito_parcelado': 3.99,
                    'cor': '#E31E24',
                    'icone': '💰'
                },
                {
                    'nome': 'Getnet',
                    'codigo': 'GETNET',
                    'max_parcelas': 12,
                    'padrao': False,
                    'taxa_debito': 1.79,
                    'taxa_credito_vista': 2.59,
                    'taxa_credito_parcelado': 3.89,
                    'cor': '#FF6600',
                    'icone': '💵'
                },
                {
                    'nome': 'Sumup',
                    'codigo': 'SUMUP',
                    'max_parcelas': 12,
                    'padrao': False,
                    'taxa_debito': 1.39,
                    'taxa_credito_vista': 2.39,
                    'taxa_credito_parcelado': 3.59,
                    'cor': '#00D4FF',
                    'icone': '⚡'
                },
                {
                    'nome': 'Legacy (Histórico)',
                    'codigo': 'LEGACY',
                    'max_parcelas': 24,
                    'padrao': False,
                    'taxa_debito': None,
                    'taxa_credito_vista': None,
                    'taxa_credito_parcelado': None,
                    'cor': '#9CA3AF',
                    'icone': '📦'
                },
            ]
            
            for op_data in operadoras:
                connection.execute(
                    sa.text("""
                        INSERT INTO operadoras_cartao (
                            tenant_id, nome, codigo, max_parcelas, padrao, ativo,
                            taxa_debito, taxa_credito_vista, taxa_credito_parcelado,
                            cor, icone, user_id, created_at, updated_at
                        ) VALUES (
                            :tenant_id, :nome, :codigo, :max_parcelas, :padrao, true,
                            :taxa_debito, :taxa_credito_vista, :taxa_credito_parcelado,
                            :cor, :icone, :user_id, NOW(), NOW()
                        )
                    """),
                    {
                        'tenant_id': tenant_id,
                        'nome': op_data['nome'],
                        'codigo': op_data['codigo'],
                        'max_parcelas': op_data['max_parcelas'],
                        'padrao': op_data['padrao'],
                        'taxa_debito': op_data['taxa_debito'],
                        'taxa_credito_vista': op_data['taxa_credito_vista'],
                        'taxa_credito_parcelado': op_data['taxa_credito_parcelado'],
                        'cor': op_data['cor'],
                        'icone': op_data['icone'],
                        'user_id': user_id
                    }
                )
            
            print(f"✅ Tenant {tenant_id}: Seed de {len(operadoras)} operadoras concluído!")
            
            # ========================================
            # 5. MIGRAR DADOS HISTÓRICOS
            # ========================================
            # Vincular venda_pagamentos antigos à operadora Legacy
            legacy_result = connection.execute(
                sa.text("""
                    SELECT id FROM operadoras_cartao 
                    WHERE tenant_id = :tenant_id AND codigo = 'LEGACY'
                """),
                {"tenant_id": tenant_id}
            )
            legacy_op = legacy_result.fetchone()
            
            if legacy_op:
                legacy_id = legacy_op[0]
                
                # Atualizar pagamentos sem operadora
                result = connection.execute(
                    sa.text("""
                        UPDATE venda_pagamentos 
                        SET operadora_id = :legacy_id
                        WHERE tenant_id = :tenant_id 
                        AND operadora_id IS NULL
                        AND (forma_pagamento ILIKE '%cartão%' OR forma_pagamento ILIKE '%cartao%')
                    """),
                    {"legacy_id": legacy_id, "tenant_id": tenant_id}
                )
                
                rows_updated = result.rowcount
                if rows_updated > 0:
                    print(f"✅ Tenant {tenant_id}: {rows_updated} pagamento(s) histórico(s) vinculado(s) à operadora Legacy")


def downgrade():
    # Remover índices (defensivo: if_exists para evitar erro caso não exista)
    op.drop_index('idx_venda_pagamentos_nsu_operadora', 'venda_pagamentos', if_exists=True)
    op.drop_index('idx_venda_pagamentos_operadora', 'venda_pagamentos')
    op.drop_index('idx_formas_pagamento_operadora', 'formas_pagamento')
    op.drop_index('idx_operadoras_padrao', 'operadoras_cartao')
    op.drop_index('idx_operadoras_codigo', 'operadoras_cartao')
    op.drop_index('idx_operadoras_tenant_id', 'operadoras_cartao')
    
    # Remover FKs
    op.drop_constraint('fk_venda_pagamentos_operadora', 'venda_pagamentos', type_='foreignkey')
    op.drop_constraint('fk_formas_pagamento_operadora', 'formas_pagamento', type_='foreignkey')
    
    # Remover colunas
    op.drop_column('venda_pagamentos', 'operadora_id')
    op.drop_column('formas_pagamento', 'operadora_id')
    
    # Remover tabela
    op.drop_table('operadoras_cartao')
