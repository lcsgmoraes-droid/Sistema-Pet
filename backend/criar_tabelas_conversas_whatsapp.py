"""
Script para criar tabelas de conversas WhatsApp (conversas_whatsapp e mensagens_whatsapp)

Essas tabelas são usadas pela rota /api/whatsapp/clientes/{id}/whatsapp/ultimas
"""
import sys
from pathlib import Path
from sqlalchemy import create_engine, text

# Adiciona o diretório backend ao path
backend_dir = Path(__file__).parent
sys.path.insert(0, str(backend_dir))

from app.config import get_database_url

def criar_tabelas():
    """Cria as tabelas de conversas WhatsApp"""
    
    print("=" * 70)
    print("🔧 CRIANDO TABELAS DE CONVERSAS WHATSAPP")
    print("=" * 70)
    
    engine = create_engine(get_database_url())
    
    with engine.connect() as conn:
        try:
            # 1. Criar tabela conversas_whatsapp
            print("\n[1/2] Criando tabela conversas_whatsapp...")
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS conversas_whatsapp (
                    id SERIAL PRIMARY KEY,
                    tenant_id UUID NOT NULL,
                    usuario_id INTEGER NOT NULL,
                    cliente_id INTEGER,
                    
                    -- Informações do contato
                    numero_whatsapp VARCHAR(20) NOT NULL,
                    nome_cliente VARCHAR(200),
                    
                    -- Estado da conversa
                    estado_atual VARCHAR,
                    
                    -- Venda associada
                    venda_id INTEGER,
                    venda_gerada_por_ia BOOLEAN DEFAULT TRUE,
                    confianca_ia FLOAT,
                    
                    -- Histórico (JSON)
                    historico_mensagens_json TEXT,
                    
                    -- Métricas
                    total_mensagens INTEGER DEFAULT 0,
                    duracao_minutos INTEGER,
                    
                    -- Feedback e aprendizado
                    resultado_venda VARCHAR,
                    motivo_rejeicao VARCHAR,
                    rating_cliente FLOAT,
                    
                    -- Timestamps
                    data_inicio TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    data_fim TIMESTAMP,
                    criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    
                    FOREIGN KEY (tenant_id) REFERENCES tenants(id),
                    FOREIGN KEY (usuario_id) REFERENCES users(id),
                    FOREIGN KEY (cliente_id) REFERENCES clientes(id),
                    FOREIGN KEY (venda_id) REFERENCES vendas(id)
                )
            """))
            conn.commit()
            print("   ✓ Tabela conversas_whatsapp criada")
            
            # Criar índices para conversas_whatsapp
            print("\n   Criando índices...")
            conn.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_conversa_whatsapp_tenant 
                ON conversas_whatsapp(tenant_id)
            """))
            conn.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_conversa_whatsapp_usuario 
                ON conversas_whatsapp(usuario_id)
            """))
            conn.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_conversa_whatsapp_numero 
                ON conversas_whatsapp(numero_whatsapp)
            """))
            conn.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_conversa_whatsapp_venda 
                ON conversas_whatsapp(venda_id)
            """))
            conn.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_conversa_whatsapp_cliente 
                ON conversas_whatsapp(cliente_id, tenant_id)
            """))
            conn.commit()
            print("   ✓ Índices criados")
            
            # 2. Criar tabela mensagens_whatsapp
            print("\n[2/2] Criando tabela mensagens_whatsapp...")
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS mensagens_whatsapp (
                    id SERIAL PRIMARY KEY,
                    tenant_id UUID NOT NULL,
                    conversa_id INTEGER NOT NULL,
                    
                    -- Quem enviou
                    remetente VARCHAR,
                    
                    -- Conteúdo
                    tipo VARCHAR DEFAULT 'texto',
                    mensagem TEXT,
                    
                    -- Intenção detectada
                    intencao_detectada VARCHAR,
                    confianca_intencao FLOAT,
                    
                    -- IA Processing
                    processada_por_ia BOOLEAN DEFAULT FALSE,
                    resposta_ia TEXT,
                    
                    -- Timestamps
                    data_hora TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    criada_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    
                    FOREIGN KEY (tenant_id) REFERENCES tenants(id),
                    FOREIGN KEY (conversa_id) REFERENCES conversas_whatsapp(id) ON DELETE CASCADE
                )
            """))
            conn.commit()
            print("   ✓ Tabela mensagens_whatsapp criada")
            
            # Criar índices para mensagens_whatsapp
            print("\n   Criando índices...")
            conn.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_mensagem_whatsapp_tenant 
                ON mensagens_whatsapp(tenant_id)
            """))
            conn.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_mensagem_whatsapp_conversa 
                ON mensagens_whatsapp(conversa_id, data_hora DESC)
            """))
            conn.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_mensagem_whatsapp_data 
                ON mensagens_whatsapp(data_hora)
            """))
            conn.commit()
            print("   ✓ Índices criados")
            
            print("\n" + "=" * 70)
            print("✅ TODAS AS TABELAS CRIADAS COM SUCESSO!")
            print("=" * 70)
            print("\nTabelas criadas:")
            print("  ✓ conversas_whatsapp (com 5 índices)")
            print("  ✓ mensagens_whatsapp (com 3 índices)")
            print("\n⚠️  IMPORTANTE: Reinicie o container backend:")
            print("   docker-compose -f docker-compose.development.yml restart backend")
            print()
            
            return True
            
        except Exception as e:
            print(f"\n❌ ERRO: {e}")
            conn.rollback()
            import traceback
            traceback.print_exc()
            return False

if __name__ == "__main__":
    success = criar_tabelas()
    if not success:
        sys.exit(1)
