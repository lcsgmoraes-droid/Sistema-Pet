# -*- coding: utf-8 -*-
"""
Script para visualizar comissões geradas
"""
import sqlite3
from datetime import datetime

db_path = "petshop.db"

try:
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    print("\n" + "="*80)
    print("💰 COMISSÕES GERADAS - ÚLTIMAS VENDAS")
    print("="*80 + "\n")
    
    # Buscar comissões pendentes
    query = """
    SELECT 
        ci.id,
        v.numero_venda,
        c.nome as funcionario,
        p.nome as produto,
        ci.quantidade,
        ci.valor_venda,
        ci.tipo_calculo,
        ci.percentual_comissao,
        ci.valor_comissao_gerada,
        ci.status,
        ci.data_criacao
    FROM comissoes_itens ci
    JOIN vendas v ON ci.venda_id = v.id
    JOIN clientes c ON ci.funcionario_id = c.id
    JOIN produtos p ON ci.produto_id = p.id
    ORDER BY ci.data_criacao DESC
    LIMIT 10
    """
    
    cursor.execute(query)
    comissoes = cursor.fetchall()
    
    if not comissoes:
        print("❌ Nenhuma comissão encontrada.")
        print("\nPossíveis motivos:")
        print("1. Venda não teve funcionário selecionado")
        print("2. Não existe configuração de comissão para o produto/categoria")
        print("3. A geração automática não foi executada")
    else:
        print(f"✅ {len(comissoes)} comissões encontradas:\n")
        
        total_geral = 0
        for com in comissoes:
            print(f"🔹 ID: {com[0]}")
            print(f"   Venda: {com[1]}")
            print(f"   Funcionário: {com[2]}")
            print(f"   Produto: {com[3]}")
            print(f"   Qtd: {com[4]} | Valor Item: R$ {com[5]:.2f}")
            print(f"   Tipo: {com[6]} | Percentual: {com[7]}%")
            print(f"   💰 COMISSÃO: R$ {com[8]:.2f}")
            print(f"   Status: {com[9]} | Data: {com[10]}")
            print("-" * 80)
            total_geral += com[8] if com[8] else 0
        
        print(f"\n💵 TOTAL COMISSÕES: R$ {total_geral:.2f}\n")
    
    # Resumo por funcionário
    print("\n" + "="*80)
    print("📊 RESUMO POR FUNCIONÁRIO")
    print("="*80 + "\n")
    
    query_resumo = """
    SELECT 
        c.nome as funcionario,
        COUNT(*) as total_itens,
        SUM(ci.valor_comissao_gerada) as total_comissoes
    FROM comissoes_itens ci
    JOIN clientes c ON ci.funcionario_id = c.id
    WHERE ci.status = 'pendente'
    GROUP BY ci.funcionario_id, c.nome
    ORDER BY total_comissoes DESC
    """
    
    cursor.execute(query_resumo)
    resumo = cursor.fetchall()
    
    if resumo:
        for func in resumo:
            print(f"👤 {func[0]}")
            print(f"   Itens: {func[1]} | Total: R$ {func[2]:.2f}")
            print("-" * 40)
    
    conn.close()
    print("\n✅ Consulta concluída!\n")
    
except Exception as e:
    print(f"\n❌ Erro: {str(e)}\n")
