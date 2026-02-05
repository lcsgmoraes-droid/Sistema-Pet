"""
Migração: Adicionar campos de estorno em comissoes_itens
Sprint 3 - Hardening Financeiro
"""
import sys
import os
sys.path.append(os.path.dirname(__file__))

from app.db import get_db_connection
from datetime import datetime

def adicionar_campos_estorno():
    """Adiciona campos necessários para estorno de comissões"""
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    print("🔄 Iniciando migração: Campos de estorno em comissoes_itens...")
    
    # Verificar se a tabela existe
    cursor.execute("""
        SELECT name FROM sqlite_master 
        WHERE type='table' AND name='comissoes_itens'
    """)
    
    if not cursor.fetchone():
        print("⚠️  Tabela comissoes_itens não encontrada!")
        print("ℹ️  Execute primeiro: python criar_tabela_comissoes_itens.py")
        conn.close()
        return False
    
    # Verificar campos existentes
    cursor.execute("PRAGMA table_info(comissoes_itens)")
    campos_existentes = [row[1] for row in cursor.fetchall()]
    
    print(f"✅ Campos atuais: {len(campos_existentes)}")
    
    campos_adicionar = []
    
    # 1. data_estorno
    if 'data_estorno' not in campos_existentes:
        campos_adicionar.append(('data_estorno', 'DATETIME'))
        print("  📝 Adicionará: data_estorno (DATETIME)")
    
    # 2. motivo_estorno
    if 'motivo_estorno' not in campos_existentes:
        campos_adicionar.append(('motivo_estorno', 'TEXT'))
        print("  📝 Adicionará: motivo_estorno (TEXT)")
    
    # 3. estornado_por
    if 'estornado_por' not in campos_existentes:
        campos_adicionar.append(('estornado_por', 'INTEGER'))
        print("  📝 Adicionará: estornado_por (INTEGER)")
    
    if not campos_adicionar:
        print("✅ Todos os campos já existem. Nenhuma alteração necessária.")
        conn.close()
        return True
    
    # Adicionar campos
    try:
        for campo, tipo in campos_adicionar:
            sql = f"ALTER TABLE comissoes_itens ADD COLUMN {campo} {tipo}"
            print(f"  🔧 Executando: {sql}")
            cursor.execute(sql)
        
        conn.commit()
        print(f"\n✅ Migração concluída com sucesso!")
        print(f"✅ {len(campos_adicionar)} campo(s) adicionado(s)")
        
        # Verificar campos finais
        cursor.execute("PRAGMA table_info(comissoes_itens)")
        campos_finais = [row[1] for row in cursor.fetchall()]
        print(f"✅ Total de campos agora: {len(campos_finais)}")
        
        return True
        
    except Exception as e:
        print(f"\n❌ Erro na migração: {str(e)}")
        conn.rollback()
        return False
        
    finally:
        conn.close()


if __name__ == '__main__':
    print("=" * 60)
    print("MIGRAÇÃO: Estorno de Comissões")
    print("=" * 60)
    print()
    
    sucesso = adicionar_campos_estorno()
    
    print()
    print("=" * 60)
    if sucesso:
        print("✅ MIGRAÇÃO FINALIZADA COM SUCESSO")
    else:
        print("❌ MIGRAÇÃO FALHOU")
    print("=" * 60)
