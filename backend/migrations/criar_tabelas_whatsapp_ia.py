"""
Migration: Criar tabelas para WhatsApp + IA Integration

Tabelas:
1. tenant_whatsapp_config - Configuração por tenant
2. whatsapp_sessions - Sessões de conversa
3. whatsapp_messages - Histórico de mensagens
4. whatsapp_metrics - Métricas de uso

Data: 2026-02-01
Sprint: 1 - Fundação WhatsApp + IA
"""
import sys
import os
from pathlib import Path

# Adicionar o diretório backend ao path
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from sqlalchemy import text
from app.db import engine, get_session

print(f"🔌 Conectando ao banco: {engine.url}")
print(f"   Tipo: {engine.dialect.name}")
print()


def run_migration():
    """Executa a migration"""
    print("=" * 80)
    print("MIGRATION: Criar Tabelas WhatsApp + IA")
    print("=" * 80)
    
    try:
        # Criar session usando get_session
        db = next(get_session())
        
        # 1. Tabela de Configuração por Tenant
        print("\n[1/4] Criando tabela tenant_whatsapp_config...")
        db.execute(text("""
            CREATE TABLE IF NOT EXISTS tenant_whatsapp_config (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                tenant_id UUID NOT NULL,
                
                -- Provider Config
                provider VARCHAR(50) DEFAULT '360dialog',
                api_key TEXT,
                phone_number VARCHAR(20),
                webhook_url TEXT,
                webhook_secret TEXT,
                
                -- IA Config
                openai_api_key TEXT,
                model_preference VARCHAR(50) DEFAULT 'gpt-4o-mini',
                
                -- Business Rules
                auto_response_enabled BOOLEAN DEFAULT TRUE,
                human_handoff_keywords TEXT,
                working_hours_start TIME,
                working_hours_end TIME,
                
                -- Notificações
                notificacoes_entrega_enabled BOOLEAN DEFAULT FALSE,
                
                -- Style & Tone
                bot_name VARCHAR(100),
                greeting_message TEXT,
                tone VARCHAR(50) DEFAULT 'friendly',
                
                -- Timestamps
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                
                FOREIGN KEY (tenant_id) REFERENCES tenants(id)
            )
        """))
        print("✅ tenant_whatsapp_config criada")
        
        # Índices
        db.execute(text("CREATE INDEX IF NOT EXISTS idx_whatsapp_config_tenant ON tenant_whatsapp_config(tenant_id)"))
        
        # 2. Tabela de Sessões
        print("\n[2/4] Criando tabela whatsapp_ia_sessions...")
        db.execute(text("""
            CREATE TABLE IF NOT EXISTS whatsapp_ia_sessions (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                tenant_id UUID NOT NULL,
                cliente_id INTEGER,
                phone_number VARCHAR(20) NOT NULL,
                
                -- Status
                status VARCHAR(20) DEFAULT 'bot',
                assigned_to INTEGER,
                
                -- Context
                context TEXT,
                last_intent VARCHAR(100),
                message_count INTEGER DEFAULT 0,
                
                -- Timestamps
                started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_message_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                closed_at TIMESTAMP,
                
                FOREIGN KEY (tenant_id) REFERENCES tenants(id),
                FOREIGN KEY (cliente_id) REFERENCES clientes(id),
                FOREIGN KEY (assigned_to) REFERENCES users(id)
            )
        """))
        print("✅ whatsapp_ia_sessions criada")
        
        # Índices
        db.execute(text("CREATE INDEX IF NOT EXISTS idx_session_tenant_status ON whatsapp_ia_sessions(tenant_id, status, last_message_at)"))
        db.execute(text("CREATE INDEX IF NOT EXISTS idx_session_phone ON whatsapp_ia_sessions(phone_number, tenant_id)"))
        db.execute(text("CREATE INDEX IF NOT EXISTS idx_session_cliente ON whatsapp_ia_sessions(cliente_id, tenant_id)"))
        
        # 3. Tabela de Mensagens
        print("\n[3/4] Criando tabela whatsapp_ia_messages...")
        db.execute(text("""
            CREATE TABLE IF NOT EXISTS whatsapp_ia_messages (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                session_id UUID NOT NULL,
                tenant_id UUID NOT NULL,
                
                -- Message Info
                tipo VARCHAR(10) NOT NULL,
                conteudo TEXT NOT NULL,
                
                -- WhatsApp IDs
                whatsapp_message_id VARCHAR(255),
                
                -- IA Info
                intent_detected VARCHAR(100),
                model_used VARCHAR(50),
                tokens_input INTEGER,
                tokens_output INTEGER,
                processing_time_ms INTEGER,
                
                -- Metadata (renomeado para evitar conflito SQLAlchemy)
                message_metadata TEXT,
                
                -- User (se enviada por humano)
                sent_by_user_id INTEGER,
                
                -- Timestamps
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                
                FOREIGN KEY (session_id) REFERENCES whatsapp_ia_sessions(id),
                FOREIGN KEY (tenant_id) REFERENCES tenants(id),
                FOREIGN KEY (sent_by_user_id) REFERENCES users(id)
            )
        """))
        print("✅ whatsapp_ia_messages criada")
        
        # Índices
        db.execute(text("CREATE INDEX IF NOT EXISTS idx_message_session ON whatsapp_ia_messages(session_id, created_at)"))
        db.execute(text("CREATE INDEX IF NOT EXISTS idx_message_tenant ON whatsapp_ia_messages(tenant_id, created_at)"))
        db.execute(text("CREATE INDEX IF NOT EXISTS idx_message_whatsapp_id ON whatsapp_ia_messages(whatsapp_message_id)"))
        
        # 4. Tabela de Métricas
        print("\n[4/4] Criando tabela whatsapp_ia_metrics...")
        db.execute(text("""
            CREATE TABLE IF NOT EXISTS whatsapp_ia_metrics (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                tenant_id UUID NOT NULL,
                
                -- Metric Type
                metric_type VARCHAR(50) NOT NULL,
                
                -- Values
                value FLOAT NOT NULL,
                metric_metadata TEXT,
                
                -- Timestamp
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                
                FOREIGN KEY (tenant_id) REFERENCES tenants(id)
            )
        """))
        print("✅ whatsapp_ia_metrics criada")
        
        # Índice
        db.execute(text("CREATE INDEX IF NOT EXISTS idx_metric_tenant_time ON whatsapp_ia_metrics(tenant_id, timestamp)"))
        
        # Commit
        db.commit()
        
        print("\n" + "=" * 80)
        print("✅ MIGRATION CONCLUÍDA COM SUCESSO!")
        print("=" * 80)
        print("\nTabelas criadas:")
        print("  ✓ tenant_whatsapp_config")
        print("  ✓ whatsapp_ia_sessions")
        print("  ✓ whatsapp_ia_messages")
        print("  ✓ whatsapp_ia_metrics")
        print("\nÍndices criados: 8")
        print("\n🚀 Sistema pronto para receber configurações WhatsApp!")
        
    except Exception as e:
        print(f"\n❌ ERRO na migration: {e}")
        import traceback
        traceback.print_exc()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    run_migration()
