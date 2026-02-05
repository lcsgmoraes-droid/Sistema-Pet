"""
Teste Simples - Google Maps API Key

Verifica se a chave está configurada corretamente
"""

import os
from dotenv import load_dotenv

# Carregar .env
load_dotenv()

# Pegar chave
GOOGLE_MAPS_API_KEY = os.getenv("GOOGLE_MAPS_API_KEY")

print("=" * 60)
print("🗺️  TESTE GOOGLE MAPS API")
print("=" * 60)
print()

if not GOOGLE_MAPS_API_KEY:
    print("❌ GOOGLE_MAPS_API_KEY não encontrada")
elif GOOGLE_MAPS_API_KEY == "your_google_maps_api_key_here":
    print("⚠️  GOOGLE_MAPS_API_KEY está com valor padrão")
else:
    print("✅ GOOGLE_MAPS_API_KEY configurada!")
    print(f"   Chave: {GOOGLE_MAPS_API_KEY[:10]}...{GOOGLE_MAPS_API_KEY[-4:]}")
    print(f"   Tamanho: {len(GOOGLE_MAPS_API_KEY)} caracteres")
    print()
    print("🎯 Próximos passos:")
    print("   1. Ative as 3 APIs no Google Cloud Console")
    print("   2. Configure restrições (domínio/IP)")
    print("   3. Ative conta de cobrança ($200 grátis/mês)")
    print()
    print("✅ Sistema pronto para usar Google Maps!")

print()
print("=" * 60)
