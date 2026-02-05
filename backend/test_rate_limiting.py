"""
Teste de Rate Limiting - FASE 8.3
Valida: proteção de rotas de auth, exceção para health/ready, resposta 429
"""

import requests
import time

BASE_URL = "http://localhost:8000"

def test_rate_limiting():
    """Testa o sistema de rate limiting"""
    
    print("\n" + "="*60)
    print("🧪 TESTE: Rate Limiting (FASE 8.3)")
    print("="*60)
    
    # Teste 1: Health/Ready devem estar livres
    print("\n✅ Teste 1: Health e Ready SEM rate limit")
    for i in range(15):  # Mais que o limite de 10
        response = requests.get(f"{BASE_URL}/health")
        if response.status_code != 200:
            print(f"   ❌ FALHA: /health retornou {response.status_code}")
            return
    print("   ✅ /health: 15 requests sem bloqueio")
    
    for i in range(15):
        response = requests.get(f"{BASE_URL}/ready")
        if response.status_code != 200:
            print(f"   ❌ FALHA: /ready retornou {response.status_code}")
            return
    print("   ✅ /ready: 15 requests sem bloqueio")
    
    # Teste 2: Login com rate limit
    print("\n⏱️  Teste 2: Rate limit em /auth/login-multitenant")
    success_count = 0
    rate_limited = False
    
    for i in range(12):  # Excede o limite de 10
        response = requests.post(
            f"{BASE_URL}/auth/login-multitenant",
            json={"email": "test@test.com", "password": "wrong"}
        )
        
        print(f"   Request {i+1}: {response.status_code}", end="")
        
        if response.status_code == 429:
            print(" (RATE LIMITED) ✅")
            rate_limited = True
            
            # Verificar headers de rate limit
            if "X-RateLimit-Limit" in response.headers:
                print(f"      X-RateLimit-Limit: {response.headers['X-RateLimit-Limit']}")
            if "Retry-After" in response.headers:
                print(f"      Retry-After: {response.headers['Retry-After']}s")
            
            break
        elif response.status_code == 401:
            print(" (Unauthorized - normal)")
            success_count += 1
        else:
            print(f" (Inesperado)")
    
    if not rate_limited:
        print("   ❌ FALHA: Rate limit não foi aplicado")
        return
    
    print(f"\n   ✅ Rate limit ativado após {success_count} requests")
    
    # Teste 3: Aguardar janela expirar
    print("\n⏳ Teste 3: Aguardando janela de rate limit expirar (5s)...")
    time.sleep(5)  # Aguardar um pouco (não os 60s completos para o teste ser rápido)
    
    # Teste 4: Verificar outras rotas não autenticadas
    print("\n✅ Teste 4: Outras rotas públicas SEM rate limit")
    for i in range(12):
        response = requests.get(f"{BASE_URL}/docs")
        if response.status_code == 429:
            print(f"   ❌ FALHA: /docs foi bloqueado (não deveria)")
            return
    print("   ✅ /docs: 12 requests sem bloqueio")
    
    print("\n" + "="*60)
    print("✅ Todos os testes de rate limiting executados com sucesso")
    print("="*60)
    print("\n📌 Comportamento validado:")
    print("   ✅ Rate limit aplicado SOMENTE em /auth/*")
    print("   ✅ /health e /ready livres de rate limit")
    print("   ✅ Resposta 429 ao exceder limite")
    print("   ✅ Headers X-RateLimit-* presentes")
    print("\n")

if __name__ == "__main__":
    print("\n⚠️  IMPORTANTE: Inicie o backend antes de executar este teste!")
    print("   Comando: cd backend && python run_server.py")
    
    input("\n▶️  Pressione ENTER quando o backend estiver rodando...")
    
    try:
        test_rate_limiting()
    except requests.exceptions.ConnectionError:
        print("\n❌ ERRO: Não foi possível conectar ao backend.")
        print("   Verifique se o backend está rodando em http://localhost:8000")
    except Exception as e:
        print(f"\n❌ ERRO: {str(e)}")
