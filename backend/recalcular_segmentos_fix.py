"""
Script para recalcular segmentos de todos os clientes
Resolve o problema de 404 ao consultar segmentos não calculados
"""

import sys
from sqlalchemy.orm import Session
from app.db import SessionLocal
from app.services.segmentacao_service import SegmentacaoService

def main():
    """Recalcula segmentos de todos os clientes"""
    db: Session = SessionLocal()
    
    try:
        print("🔄 Iniciando recálculo de segmentos...")
        print("=" * 60)
        
        service = SegmentacaoService()
        
        # Recalcular todos os segmentos (user_id=1 é o padrão)
        resultado = service.recalcular_todos_segmentos(
            user_id=1,
            db=db,
            limit=None  # Todos os clientes
        )
        
        print("\n✅ RECÁLCULO COMPLETO!")
        print("=" * 60)
        print(f"📊 Total processados: {resultado['total_processados']}")
        print(f"✅ Sucessos: {resultado['sucessos']}")
        print(f"❌ Erros: {resultado['erros']}")
        
        print("\n📊 DISTRIBUIÇÃO POR SEGMENTO:")
        print("-" * 60)
        for segmento, qtd in resultado['distribuicao_segmentos'].items():
            print(f"  {segmento}: {qtd} clientes")
        
        print("\n" + "=" * 60)
        print("✅ Agora os endpoints /segmentacao/clientes/{id} funcionarão!")
        print("=" * 60)
        
        return 0
        
    except Exception as e:
        print(f"\n❌ ERRO: {e}")
        import traceback
        traceback.print_exc()
        return 1
        
    finally:
        db.close()

if __name__ == "__main__":
    sys.exit(main())
