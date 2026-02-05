"""
Script para corrigir movimentações de caixa faltantes
Adiciona MovimentacaoCaixa para vendas já finalizadas que não têm movimentação registrada
"""
import sqlite3
import os

# Caminho do banco
DB_PATH = os.path.join(os.path.dirname(__file__), 'petshop.db')

conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

print("🔧 Corrigindo movimentações de caixa...")

# Buscar vendas finalizadas/baixa_parcial que têm pagamentos mas não têm movimentação no caixa
cursor.execute("""
    SELECT 
        vp.id,
        vp.venda_id,
        vp.forma_pagamento,
        vp.valor,
        v.numero_venda,
        v.user_id,
        u.nome as user_nome,
        v.data_venda
    FROM venda_pagamentos vp
    JOIN vendas v ON v.id = vp.venda_id
    LEFT JOIN users u ON u.id = v.user_id
    LEFT JOIN movimentacoes_caixa mc ON mc.venda_id = v.id AND mc.tipo = 'venda'
    WHERE v.status IN ('finalizada', 'baixa_parcial')
        AND vp.forma_pagamento = 'Dinheiro'
        AND mc.id IS NULL
    ORDER BY v.data_venda
""")

pagamentos_sem_movimentacao = cursor.fetchall()

if not pagamentos_sem_movimentacao:
    print("✅ Nenhuma correção necessária - todas as vendas já têm movimentação no caixa!")
    conn.close()
    exit(0)

print(f"📊 Encontrados {len(pagamentos_sem_movimentacao)} pagamentos sem movimentação no caixa")

# Buscar caixas abertos dos usuários na data das vendas
for pag in pagamentos_sem_movimentacao:
    pag_id, venda_id, forma_pag, valor, numero_venda, user_id, user_nome, data_venda = pag
    
    # Tentar encontrar caixa aberto do usuário na data da venda
    cursor.execute("""
        SELECT id FROM caixas 
        WHERE usuario_id = ?
            AND DATE(data_abertura) = DATE(?)
            AND status = 'aberto'
        LIMIT 1
    """, (user_id, data_venda))
    
    caixa = cursor.fetchone()
    
    if caixa:
        caixa_id = caixa[0]
        
        # Inserir movimentação
        cursor.execute("""
            INSERT INTO movimentacoes_caixa 
            (caixa_id, tipo, valor, forma_pagamento, descricao, venda_id, usuario_id, usuario_nome, data_movimento)
            VALUES (?, 'venda', ?, ?, ?, ?, ?, ?, ?)
        """, (
            caixa_id,
            valor,
            forma_pag,
            f'Venda #{numero_venda} (corrigido)',
            venda_id,
            user_id,
            user_nome or 'Sistema',
            data_venda
        ))
        
        print(f"  ✅ Venda #{numero_venda} - {forma_pag} - R$ {valor:.2f} → Caixa #{caixa_id}")
    else:
        print(f"  ⚠️  Venda #{numero_venda} - SEM CAIXA ABERTO na data {data_venda}")

conn.commit()
conn.close()

print("\n✅ Correção concluída!")
print("🔄 Recarregue o modal de fechar caixa para ver as alterações")
