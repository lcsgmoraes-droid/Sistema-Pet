"""
Teste Unitário de Rate Limiting - FASE 8.3
Testa a lógica do RateLimitStore sem necessidade de servidor rodando
"""

import sys
from pathlib import Path
import time

# Adiciona o diretório backend ao path
backend_dir = Path(__file__).parent
sys.path.insert(0, str(backend_dir))

from app.middlewares.rate_limit import RateLimitStore, RATE_LIMIT_MAX, RATE_LIMIT_WINDOW

def test_rate_limit_store():
    """Testa a lógica do rate limit store"""
    
    print("\n" + "="*60)
    print("🧪 TESTE UNITÁRIO: Rate Limit Store (FASE 8.3)")
    print("="*60)
    
    store = RateLimitStore()
    test_ip = "192.168.1.1"
    test_path = "/auth/login"
    
    # Teste 1: Primeira request deve ser permitida
    print(f"\n✅ Teste 1: Primeira request")
    is_allowed, remaining = store.check_limit(test_ip, test_path)
    assert is_allowed == True, "Primeira request deve ser permitida"
    assert remaining == RATE_LIMIT_MAX - 1, f"Remaining deve ser {RATE_LIMIT_MAX - 1}"
    print(f"   ✅ Permitida: {is_allowed}, Remaining: {remaining}")
    
    # Teste 2: Requests dentro do limite
    print(f"\n✅ Teste 2: Requests dentro do limite (até {RATE_LIMIT_MAX})")
    for i in range(2, RATE_LIMIT_MAX + 1):
        is_allowed, remaining = store.check_limit(test_ip, test_path)
        expected_remaining = RATE_LIMIT_MAX - i
        if i < RATE_LIMIT_MAX:
            assert is_allowed == True, f"Request {i} deve ser permitida"
            assert remaining == expected_remaining, f"Remaining deve ser {expected_remaining}, got {remaining}"
        else:
            # A décima request atinge o limite mas ainda é permitida
            assert is_allowed == True, f"Request {i} (última) deve ser permitida"
            assert remaining == 0, f"Remaining deve ser 0"
    print(f"   ✅ {RATE_LIMIT_MAX} requests totais permitidas")
    
    # Teste 3: Request excedendo limite
    print("\n✅ Teste 3: Request excedendo limite (11)")
    is_allowed, remaining = store.check_limit(test_ip, test_path)
    assert is_allowed == False, "Request além do limite deve ser bloqueada"
    assert remaining == 0, "Remaining deve ser 0"
    print(f"   ✅ Bloqueada: {not is_allowed}, Remaining: {remaining}")
    
    # Teste 4: Múltiplas tentativas após limite
    print(f"\n✅ Teste 4: Múltiplas tentativas após limite")
    for i in range(5):
        is_allowed, remaining = store.check_limit(test_ip, test_path)
        assert is_allowed == False, "Deve continuar bloqueada"
        assert remaining == 0, "Remaining deve continuar 0"
    print(f"   ✅ 5 tentativas adicionais bloqueadas")
    
    # Teste 5: IP diferente não afeta
    print(f"\n✅ Teste 5: IP diferente não é afetado")
    other_ip = "192.168.1.2"
    is_allowed, remaining = store.check_limit(other_ip, test_path)
    assert is_allowed == True, "Outro IP deve ser permitido"
    assert remaining == RATE_LIMIT_MAX - 1, "Contador separado para outro IP"
    print(f"   ✅ Outro IP permitido: {is_allowed}, Remaining: {remaining}")
    
    # Teste 6: Path diferente não afeta
    print(f"\n✅ Teste 6: Path diferente para mesmo IP")
    other_path = "/auth/refresh"
    is_allowed, remaining = store.check_limit(test_ip, other_path)
    assert is_allowed == True, "Outro path deve ser permitido"
    assert remaining == RATE_LIMIT_MAX - 1, "Contador separado para outro path"
    print(f"   ✅ Outro path permitido: {is_allowed}, Remaining: {remaining}")
    
    # Teste 7: Cleanup de entradas expiradas
    print(f"\n✅ Teste 7: Cleanup de entradas expiradas")
    initial_size = len(store.store)
    store.cleanup_expired()
    after_size = len(store.store)
    print(f"   Antes: {initial_size} entradas, Depois: {after_size} entradas")
    print(f"   ✅ Cleanup executado (sem expiração ainda)")
    
    print("\n" + "="*60)
    print("✅ Todos os testes unitários passaram")
    print("="*60)
    print("\n📌 Configuração atual:")
    print(f"   - Limite: {RATE_LIMIT_MAX} requests")
    print(f"   - Janela: {RATE_LIMIT_WINDOW}s")
    print(f"   - Storage: In-memory (dict)")
    print("\n💡 Para ajustar o limite:")
    print("   Edite RATE_LIMIT_MAX e RATE_LIMIT_WINDOW em:")
    print("   backend/app/middlewares/rate_limit.py")
    print("\n")

if __name__ == "__main__":
    test_rate_limit_store()
