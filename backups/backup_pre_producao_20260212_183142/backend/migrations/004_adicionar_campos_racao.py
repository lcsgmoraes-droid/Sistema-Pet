"""
Migração: Adicionar campos de ração nos produtos
FASE 2 - Calculadora de Ração
"""
import sqlite3
from datetime import datetime

def migrate():
    conn = sqlite3.connect('petshop.db')
    cursor = conn.cursor()
    
    print("=" * 60)
    print("MIGRACAO 004: Adicionar campos de racao")
    print("=" * 60)
    
    # Verificar se as colunas já existem
    cursor.execute("PRAGMA table_info(produtos)")
    colunas_existentes = [col[1] for col in cursor.fetchall()]
    
    campos_adicionar = {
        'classificacao_racao': 'VARCHAR(50)',  # super_premium, premium, especial, standard
        'peso_embalagem': 'FLOAT',  # peso em kg
        'tabela_nutricional': 'TEXT',  # JSON com proteina, gordura, fibra, etc
        'categoria_racao': 'VARCHAR(50)',  # filhote, adulto, senior, etc
        'especies_indicadas': 'VARCHAR(100)',  # dog, cat, both (redundante mas específico para ração)
    }
    
    for campo, tipo in campos_adicionar.items():
        if campo not in colunas_existentes:
            try:
                cursor.execute(f"ALTER TABLE produtos ADD COLUMN {campo} {tipo}")
                print(f"✓ Campo '{campo}' adicionado")
            except Exception as e:
                print(f"✗ Erro ao adicionar '{campo}': {e}")
        else:
            print(f"○ Campo '{campo}' já existe")
    
    conn.commit()
    conn.close()
    
    print("\n✅ Migração concluída!")
    print("\nCampos adicionados:")
    print("  • classificacao_racao - Classificação (super premium, premium, etc)")
    print("  • peso_embalagem - Peso da embalagem em kg")
    print("  • tabela_nutricional - JSON com valores nutricionais")
    print("  • categoria_racao - Categoria (filhote, adulto, senior)")
    print("  • especies_indicadas - Espécies compatíveis")

if __name__ == "__main__":
    migrate()
