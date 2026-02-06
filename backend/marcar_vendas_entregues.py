"""
Marca todas as vendas com entrega como ENTREGUE
Para limpar e testar novamente
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from sqlalchemy import text
from app.db import SessionLocal

def marcar_vendas_entregues():
    """Marca todas vendas com entrega como entregues"""
    db = SessionLocal()
    
    try:
        print("=" * 70)
        print("🚚 MARCAR VENDAS COMO ENTREGUES")
        print("=" * 70)
        
        # Contar vendas pendentes
        count_sql = """
        SELECT COUNT(*) 
        FROM vendas 
        WHERE tem_entrega = true 
        AND (status_entrega != 'entregue' OR status_entrega IS NULL);
        """
        count = db.execute(text(count_sql)).scalar()
        
        if count == 0:
            print("\n✅ Não há vendas pendentes de entrega!")
            return True
        
        print(f"\n📦 Encontradas {count} vendas com entrega pendente")
        
        # Verificar se tem argumento --sim
        auto_confirm = len(sys.argv) > 1 and sys.argv[1] == '--sim'
        
        if not auto_confirm:
            confirma = input(f"\n⚠️  Marcar TODAS as {count} vendas como ENTREGUE? (s/n): ").strip().lower()
            if confirma != 's':
                print("\n❌ Operação cancelada")
                return False
        else:
            print(f"\n✅ Modo automático ativado (--sim)")
        
        # Marcar como entregue
        update_sql = """
        UPDATE vendas 
        SET status_entrega = 'entregue',
            data_entrega = NOW()
        WHERE tem_entrega = true 
        AND (status_entrega != 'entregue' OR status_entrega IS NULL);
        """
        db.execute(text(update_sql))
        db.commit()
        
        print(f"\n✅ {count} vendas marcadas como ENTREGUE!")
        print("\n📌 Agora você pode:")
        print("   1. Criar novas vendas de teste")
        print("   2. Testar a otimização de rotas novamente")
        print()
        
        return True
        
    except Exception as e:
        print(f"\n❌ Erro: {e}")
        db.rollback()
        return False
    finally:
        db.close()

if __name__ == "__main__":
    success = marcar_vendas_entregues()
    sys.exit(0 if success else 1)
