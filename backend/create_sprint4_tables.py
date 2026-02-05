import sys
from app.db import SessionLocal, engine
from app.whatsapp.models_handoff import WhatsAppAgent, WhatsAppHandoff, WhatsAppInternalNote

print("Criando tabelas Sprint 4...")

try:
    from sqlalchemy import inspect
    inspector = inspect(engine)
    
    tables_before = set(inspector.get_table_names())
    print(f"\nTabelas antes: {len(tables_before)}")
    
    # Criar tabelas
    WhatsAppAgent.__table__.create(engine, checkfirst=True)
    WhatsAppHandoff.__table__.create(engine, checkfirst=True)
    WhatsAppInternalNote.__table__.create(engine, checkfirst=True)
    
    inspector = inspect(engine)
    tables_after = set(inspector.get_table_names())
    print(f"Tabelas depois: {len(tables_after)}")
    
    new_tables = tables_after - tables_before
    if new_tables:
        print(f"\n✅ Tabelas criadas: {new_tables}")
    else:
        print("\n✓ Tabelas já existiam")
    
    # Verificar tabelas Sprint 4
    sprint4 = ['whatsapp_agents', 'whatsapp_handoffs', 'whatsapp_internal_notes']
    print("\nStatus Sprint 4:")
    for table in sprint4:
        exists = table in tables_after
        print(f"  {'✅' if exists else '❌'} {table}")
    
    if all(t in tables_after for t in sprint4):
        print("\n🎉 SPRINT 4 DATABASE - COMPLETO!")
    
except Exception as e:
    print(f"\n❌ Erro: {e}")
    import traceback
    traceback.print_exc()
