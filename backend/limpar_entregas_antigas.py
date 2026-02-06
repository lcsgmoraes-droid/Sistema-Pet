"""
Marca vendas antigas como entregues, mantendo apenas as recentes
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from sqlalchemy import text
from app.db import SessionLocal

def limpar_entregas():
    db = SessionLocal()
    
    try:
        # Marcar vendas antigas como entregue (manter apenas as últimas)
        update_sql = text("""
        UPDATE vendas 
        SET status_entrega = 'entregue',
            data_entrega = NOW()
        WHERE tem_entrega = true 
        AND status_entrega = 'pendente'
        AND numero_venda NOT LIKE '%0011'
        AND numero_venda NOT LIKE '%0010'
        """)
        
        result = db.execute(update_sql)
        count = result.rowcount
        db.commit()
        
        print(f"✅ {count} vendas antigas marcadas como entregue")
        print("📋 Vendas mantidas: #0010 e #0011")
        
        return True
        
    except Exception as e:
        print(f"❌ Erro: {e}")
        db.rollback()
        return False
    finally:
        db.close()

if __name__ == "__main__":
    limpar_entregas()
