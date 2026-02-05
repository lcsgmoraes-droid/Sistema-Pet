"""
Script para verificar e recalcular segmentos de clientes
"""
import sys
from pathlib import Path
from sqlalchemy import text

# Adiciona o diretório backend ao path
backend_dir = Path(__file__).parent
sys.path.insert(0, str(backend_dir))

from app.db import get_session
from app.services.segmentacao_service import SegmentacaoService

def verificar_e_recalcular():
    """Verifica a situação e recalcula segmentos"""
    
    print("=" * 70)
    print("🔍 VERIFICANDO SEGMENTAÇÃO DE CLIENTES")
    print("=" * 70)
    
    db = next(get_session())
    
    try:
        # 1. Verificar se tabela existe
        print("\n[1/5] Verificando se tabela cliente_segmentos existe...")
        result = db.execute(text("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_name = 'cliente_segmentos'
            )
        """)).scalar()
        
        if not result:
            print("   ❌ Tabela cliente_segmentos NÃO existe!")
            print("   Criando tabela...")
            
            db.execute(text("""
                CREATE TABLE IF NOT EXISTS cliente_segmentos (
                    id SERIAL PRIMARY KEY,
                    tenant_id UUID NOT NULL,
                    cliente_id INTEGER NOT NULL,
                    segmento VARCHAR(50) NOT NULL,
                    
                    -- Métricas calculadas
                    total_compras_90d FLOAT DEFAULT 0,
                    compras_90d INTEGER DEFAULT 0,
                    ticket_medio FLOAT DEFAULT 0,
                    dias_desde_primeira_compra INTEGER DEFAULT 0,
                    dias_desde_ultima_compra INTEGER DEFAULT 0,
                    total_em_aberto FLOAT DEFAULT 0,
                    compras_90d_anteriores INTEGER DEFAULT 0,
                    
                    -- Timestamps
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    
                    FOREIGN KEY (tenant_id) REFERENCES tenants(id),
                    FOREIGN KEY (cliente_id) REFERENCES clientes(id),
                    UNIQUE(tenant_id, cliente_id)
                )
            """))
            
            db.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_cliente_segmentos_tenant 
                ON cliente_segmentos(tenant_id)
            """))
            db.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_cliente_segmentos_segmento 
                ON cliente_segmentos(segmento)
            """))
            db.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_cliente_segmentos_cliente 
                ON cliente_segmentos(cliente_id, tenant_id)
            """))
            
            db.commit()
            print("   ✅ Tabela cliente_segmentos criada com sucesso!")
        else:
            print("   ✅ Tabela existe")
        
        # 2. Verificar quantos registros existem
        print("\n[2/5] Verificando registros existentes...")
        count = db.execute(text('SELECT COUNT(*) FROM cliente_segmentos')).scalar()
        print(f"   📊 Registros na tabela: {count}")
        
        # 3. Verificar se cliente 1 existe
        print("\n[3/5] Verificando cliente ID=1...")
        cliente = db.execute(text("""
            SELECT id, nome, tenant_id 
            FROM clientes 
            WHERE id = 1
        """)).fetchone()
        
        if not cliente:
            print("   ❌ Cliente ID=1 NÃO existe na tabela clientes!")
            
            # Listar primeiros clientes disponíveis
            print("\n   Primeiros clientes disponíveis:")
            clientes = db.execute(text("""
                SELECT id, nome, tenant_id 
                FROM clientes 
                ORDER BY id 
                LIMIT 5
            """)).fetchall()
            
            for c in clientes:
                print(f"     - ID: {c[0]}, Nome: {c[1]}, Tenant: {c[2]}")
            
            return False
        else:
            print(f"   ✅ Cliente encontrado: ID={cliente[0]}, Nome={cliente[1]}, Tenant={cliente[2]}")
        
        # 4. Verificar se cliente 1 tem segmento calculado
        print("\n[4/5] Verificando se cliente 1 tem segmento...")
        segmento_existente = db.execute(text("""
            SELECT segmento, updated_at 
            FROM cliente_segmentos 
            WHERE cliente_id = 1
        """)).fetchone()
        
        if segmento_existente:
            print(f"   ✅ Segmento existente: {segmento_existente[0]} (atualizado em {segmento_existente[1]})")
        else:
            print("   ⚠️  Cliente não tem segmento calculado")
        
        # 5. Recalcular segmento do cliente 1
        print("\n[5/5] Recalculando segmento do cliente 1...")
        tenant_id = str(cliente[2])
        
        try:
            resultado = SegmentacaoService.recalcular_segmento_cliente(
                cliente_id=1,
                tenant_id=tenant_id,
                db=db
            )
            
            print(f"   ✅ Segmento recalculado com sucesso!")
            print(f"   📊 Cliente: {resultado['cliente_nome']}")
            print(f"   🏷️  Segmento: {resultado['segmento']}")
            print(f"   💰 Total compras 90d: R$ {resultado['metricas']['total_compras_90d']:.2f}")
            print(f"   🛒 Compras 90d: {resultado['metricas']['compras_90d']}")
            print(f"   🎯 Ticket médio: R$ {resultado['metricas']['ticket_medio']:.2f}")
            
        except Exception as e:
            print(f"   ❌ Erro ao recalcular: {e}")
            import traceback
            traceback.print_exc()
            return False
        
        print("\n" + "=" * 70)
        print("✅ VERIFICAÇÃO E RECÁLCULO CONCLUÍDOS!")
        print("=" * 70)
        print("\n💡 Agora a rota GET /segmentacao/clientes/1 deve funcionar!")
        print()
        
        return True
        
    except Exception as e:
        print(f"\n❌ ERRO: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        db.close()

if __name__ == "__main__":
    success = verificar_e_recalcular()
    if not success:
        sys.exit(1)
