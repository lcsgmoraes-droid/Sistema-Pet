"""
🔒 EXECUTAR TESTES DE CONTRATO MULTI-TENANT
============================================

Script helper para executar testes de segurança multi-tenant rapidamente.

USO:
    python executar_testes_multitenant.py

TESTES INCLUÍDOS:
    - Estrutura de tabelas (tenant_id obrigatório)
    - Isolamento entre tenants
    - Validação de constraints
    - Propagação de tenant_id
    - Relatório de segurança

SAÍDA:
    - ✅ SUCESSO: Todos os testes passaram
    - ❌ FALHA: Vazamento de segurança detectado
"""

import subprocess
import sys
from pathlib import Path

def main():
    print("=" * 70)
    print("🔒 TESTES DE CONTRATO MULTI-TENANT")
    print("=" * 70)
    print()
    
    # Validar que estamos no diretório correto
    backend_dir = Path(__file__).parent
    test_file = backend_dir / "tests" / "test_multitenant_contract.py"
    
    if not test_file.exists():
        print(f"❌ ERRO: Arquivo de teste não encontrado!")
        print(f"   Esperado em: {test_file}")
        sys.exit(1)
    
    print(f"📁 Diretório: {backend_dir}")
    print(f"📄 Arquivo de teste: {test_file.name}")
    print()
    
    # Executar pytest
    print("🚀 Executando testes...")
    print("-" * 70)
    print()
    
    try:
        result = subprocess.run(
            [
                sys.executable, "-m", "pytest",
                str(test_file),
                "-v",           # Verbose
                "-s",           # Mostrar prints
                "--tb=short",   # Traceback curto
                "--color=yes"   # Colorido
            ],
            cwd=backend_dir,
            check=False
        )
        
        print()
        print("=" * 70)
        
        if result.returncode == 0:
            print("✅ SUCESSO: Todos os testes de contrato passaram!")
            print()
            print("🎯 PRÓXIMOS PASSOS:")
            print("   1. Revisar relatório de segurança acima")
            print("   2. Validar que novas tabelas têm tenant_id")
            print("   3. Deploy pode prosseguir com segurança")
        else:
            print("❌ FALHA: Testes de contrato falharam!")
            print()
            print("🚨 AÇÃO OBRIGATÓRIA:")
            print("   1. Revisar erros acima")
            print("   2. Corrigir problemas de isolamento")
            print("   3. NÃO fazer deploy até todos passarem")
            print()
            print("📚 Consultar: backend/tests/README_MULTITENANT_TESTS.md")
        
        print("=" * 70)
        
        return result.returncode
    
    except FileNotFoundError:
        print("❌ ERRO: pytest não encontrado!")
        print("   Instale com: pip install pytest")
        return 1
    except Exception as e:
        print(f"❌ ERRO inesperado: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
