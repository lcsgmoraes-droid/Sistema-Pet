"""
Script para verificar e corrigir a estrutura da tabela cliente_segmentos
"""
import os
import sys
from pathlib import Path

# Adicionar o diretório backend ao path
backend_dir = Path(__file__).parent
sys.path.insert(0, str(backend_dir))

from sqlalchemy import text, inspect
from app.db import SessionLocal, engine

def verificar_e_corrigir_tabela():
    """Verifica e corrige a estrutura da tabela cliente_segmentos"""
    
    print("=" * 80)
    print("VERIFICAÇÃO E CORREÇÃO: Tabela cliente_segmentos")
    print("=" * 80)
    print()
    
    db = SessionLocal()
    
    try:
        # Verificar se tabela existe
        inspector = inspect(engine)
        tables = inspector.get_table_names()
        
        if 'cliente_segmentos' not in tables:
            print("❌ Tabela 'cliente_segmentos' não existe!")
            print("📝 Criando tabela...")
            
            # Criar tabela completa
            create_table_sql = text("""
                CREATE TABLE IF NOT EXISTS cliente_segmentos (
                    id SERIAL PRIMARY KEY,
                    cliente_id INTEGER NOT NULL,
                    user_id INTEGER NOT NULL,
                    tenant_id UUID NOT NULL,
                    segmento VARCHAR(50) NOT NULL,
                    metricas JSONB NOT NULL,
                    tags JSONB,
                    observacoes TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (cliente_id) REFERENCES clientes(id) ON DELETE CASCADE,
                    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
                    CONSTRAINT cliente_segmentos_tenant_cliente_unique UNIQUE (tenant_id, cliente_id)
                );
                
                CREATE INDEX IF NOT EXISTS idx_cliente_segmentos_cliente_id ON cliente_segmentos(cliente_id);
                CREATE INDEX IF NOT EXISTS idx_cliente_segmentos_user_id ON cliente_segmentos(user_id);
                CREATE INDEX IF NOT EXISTS idx_cliente_segmentos_segmento ON cliente_segmentos(segmento);
                CREATE INDEX IF NOT EXISTS idx_cliente_segmentos_updated_at ON cliente_segmentos(updated_at);
                CREATE INDEX IF NOT EXISTS idx_cliente_segmentos_tenant ON cliente_segmentos(tenant_id);
                CREATE INDEX IF NOT EXISTS idx_cliente_segmentos_tenant_cliente ON cliente_segmentos(tenant_id, cliente_id);
            """)
            
            db.execute(create_table_sql)
            db.commit()
            print("✅ Tabela criada com sucesso!")
        else:
            print("✅ Tabela 'cliente_segmentos' existe")
        
        # Verificar colunas
        columns = inspector.get_columns('cliente_segmentos')
        column_names = [col['name'] for col in columns]
        
        print("\n📋 Colunas atuais:")
        for col in columns:
            print(f"  - {col['name']:20s} {str(col['type']):20s} {'NOT NULL' if not col.get('nullable', True) else 'NULL'}")
        
        print("\n🔍 Verificando colunas obrigatórias...")
        
        colunas_necessarias = {
            'id': 'INTEGER',
            'cliente_id': 'INTEGER',
            'user_id': 'INTEGER',
            'tenant_id': 'UUID',
            'segmento': 'VARCHAR',
            'metricas': 'JSONB',
            'tags': 'JSONB',
            'observacoes': 'TEXT',
            'created_at': 'TIMESTAMP',
            'updated_at': 'TIMESTAMP'
        }
        
        colunas_faltantes = []
        for coluna, tipo in colunas_necessarias.items():
            if coluna not in column_names:
                colunas_faltantes.append((coluna, tipo))
        
        if colunas_faltantes:
            print(f"\n⚠️  Colunas faltantes detectadas: {len(colunas_faltantes)}")
            
            for coluna, tipo in colunas_faltantes:
                print(f"   Adicionando coluna: {coluna} ({tipo})")
                
                if coluna == 'tenant_id':
                    add_column_sql = text("""
                        ALTER TABLE cliente_segmentos 
                        ADD COLUMN IF NOT EXISTS tenant_id UUID;
                    """)
                elif coluna == 'metricas':
                    add_column_sql = text("""
                        ALTER TABLE cliente_segmentos 
                        ADD COLUMN IF NOT EXISTS metricas JSONB NOT NULL DEFAULT '{}'::jsonb;
                    """)
                elif coluna == 'tags':
                    add_column_sql = text("""
                        ALTER TABLE cliente_segmentos 
                        ADD COLUMN IF NOT EXISTS tags JSONB;
                    """)
                elif coluna == 'user_id':
                    add_column_sql = text("""
                        ALTER TABLE cliente_segmentos 
                        ADD COLUMN IF NOT EXISTS user_id INTEGER;
                    """)
                else:
                    continue
                
                db.execute(add_column_sql)
                db.commit()
                print(f"   ✅ Coluna '{coluna}' adicionada")
        else:
            print("✅ Todas as colunas necessárias estão presentes")
        
        # Verificar se tenant_id é NOT NULL
        tenant_col = next((col for col in columns if col['name'] == 'tenant_id'), None)
        if tenant_col and tenant_col.get('nullable', True):
            print("\n⚠️  Coluna tenant_id permite NULL, corrigindo...")
            
            # Atualizar registros NULL com tenant padrão (se houver)
            try:
                update_sql = text("""
                    UPDATE cliente_segmentos 
                    SET tenant_id = (SELECT tenant_id FROM clientes WHERE clientes.id = cliente_segmentos.cliente_id LIMIT 1)
                    WHERE tenant_id IS NULL
                """)
                db.execute(update_sql)
                db.commit()
                
                # Tornar NOT NULL
                alter_sql = text("""
                    ALTER TABLE cliente_segmentos 
                    ALTER COLUMN tenant_id SET NOT NULL;
                """)
                db.execute(alter_sql)
                db.commit()
                print("✅ Coluna tenant_id agora é NOT NULL")
            except Exception as e:
                print(f"⚠️  Aviso ao corrigir tenant_id: {e}")
        
        # Verificar índices
        indices = inspector.get_indexes('cliente_segmentos')
        print(f"\n🔍 Índices criados: {len(indices)}")
        for idx in indices:
            print(f"  - {idx['name']}")
        
        print("\n" + "=" * 80)
        print("✅ VERIFICAÇÃO CONCLUÍDA!")
        print("=" * 80)
        
        return True
        
    except Exception as e:
        print(f"\n❌ Erro: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        db.close()

if __name__ == "__main__":
    verificar_e_corrigir_tabela()
