# Testar import do router Sprint 4
import sys
sys.path.insert(0, r"c:\Users\Lucas\OneDrive\Área de Trabalho\Programa\Sistema Pet\backend")

print("\n" + "="*50)
print("TESTANDO IMPORTS SPRINT 4")
print("="*50)

try:
    print("\n1. Importando models...")
    from app.whatsapp.models_handoff import WhatsAppAgent, WhatsAppHandoff, WhatsAppInternalNote
    print("   ✓ Models OK")
except Exception as e:
    print(f"   ✗ ERRO: {e}")

try:
    print("\n2. Importando schemas...")
    from app.whatsapp.schemas_handoff import (
        WhatsAppAgentCreate,
        WhatsAppAgentResponse,
        WhatsAppHandoffResponse
    )
    print("   ✓ Schemas OK")
except Exception as e:
    print(f"   ✗ ERRO: {e}")

try:
    print("\n3. Importando router...")
    from app.routers.whatsapp_handoff import router
    print(f"   ✓ Router OK - Prefix: {router.prefix}")
    print(f"   ✓ Total de rotas: {len(router.routes)}")
    
    print("\n   Rotas registradas:")
    for route in router.routes:
        if hasattr(route, 'path') and hasattr(route, 'methods'):
            print(f"     - {list(route.methods)[0]} {route.path}")
            
except Exception as e:
    print(f"   ✗ ERRO: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "="*50)
