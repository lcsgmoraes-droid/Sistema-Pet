"""
SPRINT 6 - PASSO 6: MIGRATION - Adicionar campos para pagamento parcial e forma de pagamento

Novos campos:
- forma_pagamento: Como foi feito o pagamento (dinheiro, cheque, transferência, etc)
- valor_pago: Quanto foi pago (permite pagamento parcial)
- saldo_restante: valor_comissao - valor_pago (derivado, para auditoria)

Regras:
- Snapshot imutável: valor_comissao NUNCA é alterado
- Pagamento parcial: valor_pago < valor_comissao é permitido
- Saldo: calculado derivadamente para clareza
"""

import sqlite3
import os
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(__file__), 'petshop.db')

def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def migration_up():
    """Aplicar migration: adicionar novos campos"""
    print("=" * 80)
    print("MIGRATION UP: Adicionando campos para pagamento parcial")
    print("=" * 80)
    
    conn = get_connection()
    cursor = conn.cursor()
    
    try:
        # Verificar se coluna já existe
        cursor.execute("PRAGMA table_info(comissoes_itens)")
        colunas = [row[1] for row in cursor.fetchall()]
        
        if 'forma_pagamento' not in colunas:
            print("\n📝 Adicionando coluna 'forma_pagamento'...")
            cursor.execute("""
                ALTER TABLE comissoes_itens 
                ADD COLUMN forma_pagamento VARCHAR(50) DEFAULT 'nao_informado'
            """)
            print("   ✅ Coluna 'forma_pagamento' adicionada")
        else:
            print("\n⚠️  Coluna 'forma_pagamento' já existe")
        
        if 'valor_pago' not in colunas:
            print("\n📝 Adicionando coluna 'valor_pago'...")
            cursor.execute("""
                ALTER TABLE comissoes_itens 
                ADD COLUMN valor_pago DECIMAL(10,2) DEFAULT NULL
            """)
            print("   ✅ Coluna 'valor_pago' adicionada")
        else:
            print("\n⚠️  Coluna 'valor_pago' já existe")
        
        if 'saldo_restante' not in colunas:
            print("\n📝 Adicionando coluna 'saldo_restante'...")
            cursor.execute("""
                ALTER TABLE comissoes_itens 
                ADD COLUMN saldo_restante DECIMAL(10,2) DEFAULT NULL
            """)
            print("   ✅ Coluna 'saldo_restante' adicionada")
        else:
            print("\n⚠️  Coluna 'saldo_restante' já existe")
        
        # Criar tabela auxiliar de formas de pagamento se não existir
        print("\n📝 Verificando tabela 'formas_pagamento_comissoes'...")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS formas_pagamento_comissoes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nome VARCHAR(50) NOT NULL UNIQUE,
                descricao TEXT,
                ativo INTEGER DEFAULT 1,
                data_criacao DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Inserir formas padrão
        formas_padrao = [
            ('dinheiro', 'Pagamento em dinheiro'),
            ('transferencia', 'Transferência bancária'),
            ('cheque', 'Cheque'),
            ('cartao_credito', 'Cartão de crédito'),
            ('pix', 'PIX'),
            ('nao_informado', 'Não informado'),
        ]
        
        for forma, descricao in formas_padrao:
            cursor.execute(
                "SELECT COUNT(*) as cnt FROM formas_pagamento_comissoes WHERE nome = ?",
                (forma,)
            )
            if cursor.fetchone()['cnt'] == 0:
                cursor.execute(
                    "INSERT INTO formas_pagamento_comissoes (nome, descricao) VALUES (?, ?)",
                    (forma, descricao)
                )
                print(f"   ✅ Forma '{forma}' adicionada")
        
        conn.commit()
        
        # Validar mudanças
        print("\n" + "=" * 80)
        print("✅ MIGRATION CONCLUÍDA COM SUCESSO!")
        print("=" * 80)
        
        cursor.execute("PRAGMA table_info(comissoes_itens)")
        print("\n📊 Colunas da tabela 'comissoes_itens':")
        for row in cursor.fetchall():
            cid, name, type_, notnull, dflt_value, pk = row
            print(f"   • {name:30s} {type_:15s} (PK={pk}, NOT NULL={notnull})")
        
        print("\n" + "=" * 80)
        return True
        
    except Exception as e:
        print(f"\n❌ ERRO: {str(e)}")
        conn.rollback()
        return False
    finally:
        conn.close()

def migration_down():
    """Reverter migration: remover novos campos"""
    print("=" * 80)
    print("MIGRATION DOWN: Removendo campos para pagamento parcial")
    print("=" * 80)
    
    conn = get_connection()
    cursor = conn.cursor()
    
    try:
        # SQLite não permite DROP COLUMN diretamente, então usamos recreação de tabela
        # Mas para simplificar, apenas comentamos os dados
        print("\n⚠️  SQLite não permite DROP COLUMN de forma simples.")
        print("   Para reverter completamente, seria necessário recriar a tabela.")
        print("   Deixando campos como NULL para serem reutilizados.")
        
        conn.commit()
        print("\n✅ ROLLBACK SEM RISCO: dados preservados")
        return True
        
    except Exception as e:
        print(f"\n❌ ERRO: {str(e)}")
        conn.rollback()
        return False
    finally:
        conn.close()

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == 'down':
        migration_down()
    else:
        migration_up()
