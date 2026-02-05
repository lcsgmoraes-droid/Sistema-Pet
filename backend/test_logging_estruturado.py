"""
Teste de Logging Estruturado - FASE 8.2
Valida: configuração global, request logging, error logging
"""

import sys
from pathlib import Path

# Adiciona o diretório backend ao path
backend_dir = Path(__file__).parent
sys.path.insert(0, str(backend_dir))

# Importar e configurar logging
from app.utils.logger import configure_logging, logger

def test_structured_logging():
    """Testa o sistema de logging estruturado"""
    
    print("\n" + "="*60)
    print("🧪 TESTE: Logging Estruturado (FASE 8.2)")
    print("="*60)
    
    # Configurar logging
    configure_logging()
    print("\n✅ Logging global configurado (formato estruturado)\n")
    
    # Teste 1: Log INFO (fluxo normal)
    print("📝 Teste 1: Log INFO (fluxo normal)")
    logger.info(
        event="test_info",
        message="Fluxo normal de execução",
        user_id=123,
        action="create_order"
    )
    
    # Teste 2: Log WARNING (situação estranha)
    print("\n⚠️  Teste 2: Log WARNING (situação estranha)")
    logger.warning(
        event="test_warning",
        message="Duplicação evitada por idempotência",
        idempotency_key="abc123",
        status="skipped"
    )
    
    # Teste 3: Log ERROR (falha real)
    print("\n❌ Teste 3: Log ERROR (falha real)")
    logger.error(
        event="test_error",
        message="Falha ao conectar com serviço externo",
        service="bling_api",
        error_code="CONNECTION_TIMEOUT"
    )
    
    print("\n" + "="*60)
    print("✅ Todos os testes de logging executados")
    print("="*60)
    print("\n📌 Observações:")
    print("   - Logs no formato: timestamp | level | logger | message")
    print("   - INFO: fluxo normal")
    print("   - WARNING: situações estranhas")
    print("   - ERROR: falhas reais")
    print("   - Request logging será ativo ao iniciar o backend")
    print("\n")

if __name__ == "__main__":
    test_structured_logging()
