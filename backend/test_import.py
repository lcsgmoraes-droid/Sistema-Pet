"""
Script de teste de import do FastAPI app
"""
import sys
import traceback

print("🔍 Testando import do app.main...")
print(f"Python version: {sys.version}")
print(f"Python path: {sys.path[:3]}")

try:
    from app.main import app
    print("\n✅ SUCCESS - App carregado com sucesso!")
    print(f"   App title: {app.title}")
    print(f"   App version: {app.version}")
except Exception as e:
    print(f"\n❌ ERRO ao importar app.main:")
    print(f"   {type(e).__name__}: {e}")
    print("\n📋 Traceback completo:")
    traceback.print_exc()
    sys.exit(1)
