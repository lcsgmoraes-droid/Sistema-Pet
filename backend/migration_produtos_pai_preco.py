"""
Migração Simples: Atualizar preco_venda para 0 em produtos PAI
Data: 2026-01-24

Como SQLite não suporta ALTER COLUMN facilmente, vamos apenas garantir
que produtos PAI tenham preco_venda = 0 e o código já aceita NULL.
"""
import sqlite3
import os
from datetime import datetime

def migrar_preco_venda_produtos_pai():
    """Atualiza preco_venda = 0 para produtos PAI existentes"""
    
    db_path = os.path.join(os.path.dirname(__file__), 'petshop.db')
    
    if not os.path.exists(db_path):
        print(f"❌ Banco de dados não encontrado: {db_path}")
        return False
    
    print("=" * 60)
    print("MIGRAÇÃO: Ajustar preço de produtos PAI")
    print("=" * 60)
    print()
    print(f"📂 Banco: {db_path}")
    print(f"🕐 Início: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Verificar produtos PAI
        print("🔍 Verificando produtos PAI...")
        cursor.execute("""
            SELECT COUNT(*) 
            FROM produtos 
            WHERE tipo_produto = 'PAI'
        """)
        total_pai = cursor.fetchone()[0]
        print(f"   Total de produtos PAI: {total_pai}")
        
        if total_pai > 0:
            cursor.execute("""
                SELECT COUNT(*) 
                FROM produtos 
                WHERE tipo_produto = 'PAI' AND (preco_venda IS NULL OR preco_venda > 0)
            """)
            para_atualizar = cursor.fetchone()[0]
            print(f"   Produtos PAI com preço a ajustar: {para_atualizar}")
            
            if para_atualizar > 0:
                print()
                print("🔄 Atualizando preços...")
                cursor.execute("""
                    UPDATE produtos 
                    SET preco_venda = 0,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE tipo_produto = 'PAI' AND (preco_venda IS NULL OR preco_venda > 0)
                """)
                conn.commit()
                print(f"   ✅ {para_atualizar} produto(s) atualizado(s)")
        else:
            print("   ℹ️  Nenhum produto PAI encontrado")
        
        print()
        print("📊 Resumo Final:")
        cursor.execute("SELECT COUNT(*) FROM produtos WHERE ativo = 1 OR ativo IS NULL")
        total = cursor.fetchone()[0]
        print(f"   Total de produtos ativos: {total}")
        
        cursor.execute("SELECT COUNT(*) FROM produtos WHERE tipo_produto = 'PAI'")
        total_pai = cursor.fetchone()[0]
        print(f"   Produtos PAI: {total_pai}")
        
        cursor.execute("""
            SELECT COUNT(*) FROM produtos 
            WHERE tipo_produto = 'PAI' AND preco_venda = 0
        """)
        pai_sem_preco = cursor.fetchone()[0]
        print(f"   Produtos PAI com preço = 0: {pai_sem_preco}")
        
        conn.close()
        
        print()
        print("✅ Migração concluída!")
        print(f"🕐 Fim: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print()
        
        return True
        
    except Exception as e:
        print(f"❌ Erro: {str(e)}")
        if conn:
            conn.rollback()
            conn.close()
        return False


if __name__ == "__main__":
    sucesso = migrar_preco_venda_produtos_pai()
    
    if not sucesso:
        print("⚠️  Migração falhou!")
        exit(1)
    
    print("🎉 Pronto! Sistema preparado para produtos PAI sem preço.")
