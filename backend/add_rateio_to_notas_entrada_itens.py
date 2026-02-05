"""
Script para adicionar campos de rateio nas tabelas de notas de entrada
Rateio é APENAS informativo/analítico - o estoque é UNIFICADO
"""

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from sqlalchemy import text
from app.db import SessionLocal

def main():
    db = SessionLocal()
    
    try:
        print("🔄 Adicionando campos de rateio...")
        
        # ============ NOTAS_ENTRADA ============
        print("\n📋 Atualizando tabela notas_entrada...")
        db.execute(text("""
            ALTER TABLE notas_entrada
            ADD COLUMN IF NOT EXISTS tipo_rateio VARCHAR(20) DEFAULT 'loja',
            ADD COLUMN IF NOT EXISTS percentual_online FLOAT DEFAULT 0,
            ADD COLUMN IF NOT EXISTS percentual_loja FLOAT DEFAULT 100,
            ADD COLUMN IF NOT EXISTS valor_online FLOAT DEFAULT 0,
            ADD COLUMN IF NOT EXISTS valor_loja FLOAT DEFAULT 0;
        """))
        
        # Atualizar registros existentes
        db.execute(text("""
            UPDATE notas_entrada
            SET valor_loja = valor_total,
                tipo_rateio = 'loja',
                percentual_loja = 100,
                percentual_online = 0,
                valor_online = 0
            WHERE valor_loja IS NULL OR valor_loja = 0;
        """))
        
        # ============ NOTAS_ENTRADA_ITENS ============
        print("📦 Atualizando tabela notas_entrada_itens...")
        db.execute(text("""
            ALTER TABLE notas_entrada_itens
            ADD COLUMN IF NOT EXISTS quantidade_online FLOAT DEFAULT 0,
            ADD COLUMN IF NOT EXISTS valor_online FLOAT DEFAULT 0;
        """))
        
        # Remover colunas antigas se existirem
        db.execute(text("""
            ALTER TABLE notas_entrada_itens
            DROP COLUMN IF EXISTS percentual_online,
            DROP COLUMN IF EXISTS percentual_loja,
            DROP COLUMN IF EXISTS quantidade_loja;
        """))
        
        # ============ CONTAS_PAGAR ============
        print("💰 Atualizando tabela contas_pagar...")
        db.execute(text("""
            ALTER TABLE contas_pagar
            ADD COLUMN IF NOT EXISTS percentual_online FLOAT DEFAULT 0,
            ADD COLUMN IF NOT EXISTS percentual_loja FLOAT DEFAULT 100;
        """))
        
        db.commit()
        
        print("\n✅ Campos de rateio adicionados com sucesso!")
        print("\n📊 Estrutura do Rateio:")
        print("   • Estoque: UNIFICADO (não separa físico)")
        print("   • Rateio: apenas informativo/analítico")
        print("   • NotaEntrada.tipo_rateio: 'online', 'loja', 'parcial'")
        print("   • NotaEntradaItem.quantidade_online: qtd que é do online")
        print("   • Sistema calcula % automaticamente")
        print("   • ContaPagar herda os % para filtros/relatórios")
        
    except Exception as e:
        print(f"❌ Erro: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    main()
