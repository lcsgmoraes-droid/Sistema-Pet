"""
Migration: Sprint 4 - Human Handoff Tables

Cria tabelas para:
- whatsapp_agents: Atendentes humanos
- whatsapp_handoffs: Transferências de conversa
- whatsapp_internal_notes: Notas internas dos atendentes
"""
import sys
import os

# Adicionar pasta raiz ao path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from sqlalchemy import create_engine, text
from app.db import get_database_url, Base

# Importar todos os models para que Base.metadata os conheça
from app.whatsapp.models import TenantWhatsAppConfig, WhatsAppSession, WhatsAppMessage, WhatsAppMetric
from app.whatsapp.models_handoff import WhatsAppAgent, WhatsAppHandoff, WhatsAppInternalNote

print("=" * 60)
print("MIGRATION: Sprint 4 - Human Handoff Tables")
print("=" * 60)

# Criar engine
DATABASE_URL = get_database_url()
print(f"\nConectando ao banco: {DATABASE_URL.split('@')[1] if '@' in DATABASE_URL else 'local'}")

engine = create_engine(DATABASE_URL)

# Criar tabelas
print("\nCriando tabelas...")

try:
    # Criar tabelas dos models
    Base.metadata.create_all(
        engine,
        tables=[
            WhatsAppAgent.__table__,
            WhatsAppHandoff.__table__,
            WhatsAppInternalNote.__table__
        ]
    )
    
    print("✅ Tabelas criadas:")
    print("   - whatsapp_agents")
    print("   - whatsapp_handoffs")
    print("   - whatsapp_internal_notes")
    
    # Verificar se tabelas foram criadas
    with engine.connect() as conn:
        result = conn.execute(text("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public' 
            AND table_name LIKE 'whatsapp_%'
            ORDER BY table_name
        """))
        
        print("\nTabelas WhatsApp no banco:")
        for row in result:
            print(f"   ✓ {row[0]}")
    
    print("\n" + "=" * 60)
    print("✅ MIGRATION COMPLETA!")
    print("=" * 60)
    print("\nPróximos passos:")
    print("1. Criar atendentes: POST /api/agents")
    print("2. Testar sentiment analysis")
    print("3. Simular handoff automático")
    
except Exception as e:
    print(f"\n❌ Erro ao criar tabelas: {e}")
    print("\nDetalhes:")
    import traceback
    traceback.print_exc()
    sys.exit(1)
