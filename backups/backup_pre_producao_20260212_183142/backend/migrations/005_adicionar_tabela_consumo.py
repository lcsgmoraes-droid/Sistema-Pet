"""
Migração: Adicionar campo tabela_consumo nos produtos
Para armazenar as tabelas de consumo que vêm nas embalagens
"""
import sqlite3

def migrate():
    conn = sqlite3.connect('petshop.db')
    cursor = conn.cursor()
    
    print("=" * 60)
    print("MIGRACAO 005: Adicionar tabela_consumo")
    print("=" * 60)
    
    # Verificar se a coluna já existe
    cursor.execute("PRAGMA table_info(produtos)")
    colunas_existentes = [col[1] for col in cursor.fetchall()]
    
    if 'tabela_consumo' not in colunas_existentes:
        try:
            cursor.execute("ALTER TABLE produtos ADD COLUMN tabela_consumo TEXT")
            print("✓ Campo 'tabela_consumo' adicionado")
            print("\nEstrutura esperada do JSON:")
            print("""{
  "peso_adulto": {
    "5": 89,    // 5kg de peso adulto -> 89g/dia
    "10": 150,  // 10kg -> 150g/dia
    "15": 203
  },
  "filhote_2m": {
    "5": 89,    // Filhote 2 meses, estimativa adulto 5kg -> 89g/dia
    "10": 150
  },
  "filhote_4m": {...},
  "filhote_6m": {...}
}""")
        except Exception as e:
            print(f"✗ Erro ao adicionar 'tabela_consumo': {e}")
    else:
        print("○ Campo 'tabela_consumo' já existe")
    
    conn.commit()
    conn.close()
    
    print("\n✅ Migração concluída!")
    print("\nAgora você pode cadastrar a tabela de consumo de cada ração")
    print("e a calculadora usará os valores EXATOS da embalagem!")

if __name__ == "__main__":
    migrate()
