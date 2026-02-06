"""
Adiciona campo ordem_entrega_otimizada na tabela vendas
Para economizar chamadas à API do Google Maps
"""
import os
import sys
from pathlib import Path

# Adicionar o diretório raiz ao path
sys.path.insert(0, str(Path(__file__).parent))

from sqlalchemy import text
from app.db import SessionLocal

def add_ordem_entrega_otimizada():
    """Adiciona campo ordem_entrega_otimizada"""
    db = SessionLocal()
    
    try:
        print("=" * 70)
        print("🔧 ADICIONAR CAMPO ordem_entrega_otimizada")
        print("=" * 70)
        
        # Verificar se coluna já existe
        check_sql = """
        SELECT column_name 
        FROM information_schema.columns 
        WHERE table_name='vendas' AND column_name='ordem_entrega_otimizada';
        """
        result = db.execute(text(check_sql)).fetchone()
        
        if result:
            print("✅ Campo ordem_entrega_otimizada já existe!")
            return True
        
        # Adicionar coluna
        print("\n📝 Adicionando coluna ordem_entrega_otimizada...")
        alter_sql = """
        ALTER TABLE vendas 
        ADD COLUMN ordem_entrega_otimizada INTEGER NULL;
        """
        db.execute(text(alter_sql))
        
        # Criar índice
        print("📝 Criando índice...")
        index_sql = """
        CREATE INDEX IF NOT EXISTS idx_vendas_ordem_entrega_otimizada 
        ON vendas(ordem_entrega_otimizada);
        """
        db.execute(text(index_sql))
        
        db.commit()
        
        print("\n" + "=" * 70)
        print("✅ SUCESSO! Campo adicionado")
        print("=" * 70)
        print()
        print("📌 Benefícios:")
        print("   - Economiza chamadas à API do Google Maps")
        print("   - Ordem otimizada persiste no banco")
        print("   - Novas vendas aparecem no final (cronológico)")
        print()
        
        return True
        
    except Exception as e:
        print(f"\n❌ Erro: {e}")
        db.rollback()
        return False
    finally:
        db.close()

if __name__ == "__main__":
    success = add_ordem_entrega_otimizada()
    sys.exit(0 if success else 1)
