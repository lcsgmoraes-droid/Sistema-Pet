"""
Migration: Adicionar pontos inicial/final configuráveis nas rotas

Adiciona campos para controlar ponto inicial e final da rota,
permitindo que o entregador retorne à origem ou finalize em outro local.
"""
import sys
import os

# Adicionar o diretório raiz ao path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.db import engine
from sqlalchemy import text

def run_migration():
    """
    Adiciona campos de ponto inicial e final na tabela rotas_entrega
    """
    print("=" * 70)
    print("MIGRATION: Adicionar pontos inicial/final configuráveis")
    print("=" * 70)
    
    with engine.connect() as conn:
        try:
            # 1. Adicionar campo ponto_inicial_rota
            print("\n1. Adicionando campo ponto_inicial_rota...")
            conn.execute(text("""
                ALTER TABLE rotas_entrega 
                ADD COLUMN IF NOT EXISTS ponto_inicial_rota TEXT;
            """))
            conn.commit()
            print("   ✅ Campo ponto_inicial_rota adicionado")
            
            # 2. Adicionar campo ponto_final_rota
            print("\n2. Adicionando campo ponto_final_rota...")
            conn.execute(text("""
                ALTER TABLE rotas_entrega 
                ADD COLUMN IF NOT EXISTS ponto_final_rota TEXT;
            """))
            conn.commit()
            print("   ✅ Campo ponto_final_rota adicionado")
            
            # 3. Adicionar campo retorna_origem
            print("\n3. Adicionando campo retorna_origem...")
            conn.execute(text("""
                ALTER TABLE rotas_entrega 
                ADD COLUMN IF NOT EXISTS retorna_origem BOOLEAN NOT NULL DEFAULT TRUE;
            """))
            conn.commit()
            print("   ✅ Campo retorna_origem adicionado")
            
            # 4. Adicionar comentários
            print("\n4. Adicionando comentários nos campos...")
            conn.execute(text("""
                COMMENT ON COLUMN rotas_entrega.ponto_inicial_rota IS 
                'Endereço de origem da rota (normalmente a loja)';
            """))
            conn.execute(text("""
                COMMENT ON COLUMN rotas_entrega.ponto_final_rota IS 
                'Endereço de destino final (por padrão igual ao inicial)';
            """))
            conn.execute(text("""
                COMMENT ON COLUMN rotas_entrega.retorna_origem IS 
                'Se TRUE, ponto final = ponto inicial (volta para origem)';
            """))
            conn.commit()
            print("   ✅ Comentários adicionados")
            
            print("\n" + "=" * 70)
            print("✅ MIGRATION CONCLUÍDA COM SUCESSO!")
            print("=" * 70)
            print("\nCampos adicionados:")
            print("  - ponto_inicial_rota (TEXT)")
            print("  - ponto_final_rota (TEXT)")
            print("  - retorna_origem (BOOLEAN, DEFAULT TRUE)")
            print("\n⚠️  IMPORTANTE:")
            print("  Por padrão, rotas retornam à origem (retorna_origem = TRUE)")
            print("  Configure ponto_final_rota diferente para não retornar")
            
        except Exception as e:
            print(f"\n❌ Erro na migration: {e}")
            conn.rollback()
            raise

if __name__ == "__main__":
    run_migration()
