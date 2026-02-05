"""
Ativa todas as comissões que estão com ativo = 0 ou NULL
"""
import sys
import os
sys.path.append(os.path.dirname(__file__))

from app.db import get_db_connection

def ativar_comissoes():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Verificar quantos registros estão inativos
    cursor.execute("SELECT COUNT(*) FROM comissoes_configuracao WHERE ativo IS NULL OR ativo = 0")
    total = cursor.fetchone()[0]
    
    print(f"📊 Encontrados {total} registros inativos")
    
    if total > 0:
        # Ativar todos
        cursor.execute("UPDATE comissoes_configuracao SET ativo = 1 WHERE ativo IS NULL OR ativo = 0")
        conn.commit()
        print(f"✅ {total} registros ativados com sucesso!")
        
        # Mostrar funcionários afetados
        cursor.execute("""
            SELECT DISTINCT u.nome, COUNT(cc.id) as total
            FROM users u
            INNER JOIN comissoes_configuracao cc ON u.id = cc.funcionario_id
            WHERE cc.ativo = 1
            GROUP BY u.id, u.nome
            ORDER BY u.nome
        """)
        
        print("\n👥 Funcionários com comissões ativas:")
        for row in cursor.fetchall():
            print(f"   - {row['nome']}: {row['total']} configurações")
    else:
        print("✅ Todas as comissões já estão ativas!")
    
    conn.close()

if __name__ == "__main__":
    ativar_comissoes()
