"""
Teste rápido de validação dos imports do novo código
"""

import sys
sys.path.insert(0, '.')

try:
    print("Testando imports do backend...")
    
    print("  ✅ Importando models...")
    from app.comissoes_avancadas_models import (
        ConferenciaComFiltrosResponse,
        FecharComPagamentoResponse,
        ListaFormasPagamento
    )
    
    print("  ✅ Importando routes...")
    from app.comissoes_avancadas_routes import router as comissoes_avancadas_router
    
    print("  ✅ Verificando endpoints...")
    routes = [r.path for r in comissoes_avancadas_router.routes]
    print(f"     Endpoints registrados: {len(routes)}")
    for route in routes:
        print(f"       • {route}")
    
    print("\n✅ Tudo validado com sucesso!")
    print("   Sistema está pronto para inicialização.")
    
except Exception as e:
    print(f"\n❌ Erro: {str(e)}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
