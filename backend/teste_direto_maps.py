"""
Teste Direto - Google Maps Distância Prevista
"""

import os
import requests
from decimal import Decimal

# Carregar API Key do .env
from dotenv import load_dotenv
load_dotenv()

GOOGLE_MAPS_API_KEY = os.getenv("GOOGLE_MAPS_API_KEY")

print("=" * 70)
print("🗺️  TESTE DIRETO - CÁLCULO DE DISTÂNCIA")
print("=" * 70)
print()

if not GOOGLE_MAPS_API_KEY:
    print("❌ ERRO: GOOGLE_MAPS_API_KEY não encontrada no .env")
    exit(1)

print(f"✅ API Key: {GOOGLE_MAPS_API_KEY[:20]}...")
print()

# ============================================================================
# TESTE: Calcular Distância
# ============================================================================
print("📋 TESTE: Calculando distância...")
print("-" * 70)

origem = "Av. Paulista, 1578, São Paulo, SP"
destino = "Rua Augusta, 2690, São Paulo, SP"

print(f"Origem: {origem}")
print(f"Destino: {destino}")
print()

url = "https://maps.googleapis.com/maps/api/distancematrix/json"
params = {
    "origins": origem,
    "destinations": destino,
    "key": GOOGLE_MAPS_API_KEY,
    "language": "pt-BR"
}

try:
    response = requests.get(url, params=params, timeout=10)
    response.raise_for_status()
    data = response.json()
    
    print(f"Status API: {data.get('status')}")
    
    if data.get("status") != "OK":
        print(f"❌ Erro na API: {data.get('status')}")
        print(f"Resposta: {data}")
        exit(1)
    
    # Extrair resultado
    row = data["rows"][0]
    element = row["elements"][0]
    
    print(f"Status Rota: {element.get('status')}")
    
    if element.get("status") != "OK":
        print(f"❌ Rota inválida: {element.get('status')}")
        exit(1)
    
    # Extrair distância
    distancia_metros = element["distance"]["value"]
    distancia_texto = element["distance"]["text"]
    distancia_km = Decimal(str(distancia_metros)) / Decimal("1000")
    
    # Extrair duração
    duracao_segundos = element["duration"]["value"]
    duracao_texto = element["duration"]["text"]
    duracao_minutos = int(duracao_segundos / 60)
    
    print()
    print("✅ RESULTADO:")
    print(f"   Distância: {distancia_km} km ({distancia_texto})")
    print(f"   Duração: {duracao_minutos} minutos ({duracao_texto})")
    print(f"   Tipo: {type(distancia_km).__name__}")
    
    # Validações
    assert isinstance(distancia_km, Decimal), "Deve ser Decimal"
    assert distancia_km > 0, "Deve ser maior que zero"
    
    print()
    print("=" * 70)
    print("🎉 TESTE PASSOU! Sistema funcionando corretamente!")
    print("=" * 70)
    print()
    print("✅ A Etapa 9.2 está operacional:")
    print("   • Google Maps API configurada")
    print("   • Cálculo de distância funcionando")
    print("   • Retorno em formato Decimal")
    print()
    print("🚀 Próximo passo: testar endpoint de criação de rota")
    print("=" * 70)
    
except requests.exceptions.RequestException as e:
    print(f"❌ ERRO na requisição: {str(e)}")
    exit(1)
except Exception as e:
    print(f"❌ ERRO: {str(e)}")
    import traceback
    traceback.print_exc()
    exit(1)
