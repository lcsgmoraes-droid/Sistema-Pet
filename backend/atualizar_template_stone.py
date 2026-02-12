"""
Script para atualizar template Stone com colunas corretas do CSV
"""
import os
import sys
import json
import psycopg2
from psycopg2.extras import Json

# Pegar DATABASE_URL do ambiente
DATABASE_URL = os.getenv('DATABASE_URL', 'postgresql://postgres:postgres@localhost:5432/petshop')

# Converter DATABASE_URL para formato psycopg2
# postgresql+psycopg2://user:pass@host:port/dbname
DATABASE_URL = DATABASE_URL.replace('postgresql+psycopg2://', 'postgresql://')
parts = DATABASE_URL.replace('postgresql://', '').split('@')
credentials = parts[0].split(':')
location = parts[1].split('/')
host_port = location[0].split(':')

conn_params = {
    'host': host_port[0],
    'port': host_port[1] if len(host_port) > 1 else '5432',
    'dbname': location[1],
    'user': credentials[0],
    'password': credentials[1]
}

def atualizar_template_stone():
    conn = None
    try:
        # Conectar ao banco
        conn = psycopg2.connect(**conn_params)
        cur = conn.cursor()
        
        # Buscar template Stone versão 1.0
        cur.execute("""
            SELECT id, nome_adquirente, mapeamento 
            FROM templates_adquirentes 
            WHERE nome_adquirente ILIKE '%stone%'
            LIMIT 1
        """)
        
        result = cur.fetchone()
        if not result:
            print("❌ Template Stone não encontrado!")
            return
        
        template_id, nome_adquirente, mapeamento_atual = result
        print(f"✅ Template encontrado: {template_id} - {nome_adquirente}")
        
        # Novo mapeamento correto
        novo_mapeamento = {
            "nsu": {
                "coluna": "STONE ID",
                "transformacao": "nsu",
                "obrigatorio": True
            },
            "data_venda": {
                "coluna": "DATA DA VENDA",
                "transformacao": "data_br",
                "obrigatorio": True
            },
            "data_pagamento": {
                "coluna": "DATA DO ULTIMO STATUS",
                "transformacao": "data_br",
                "obrigatorio": False
            },
            "valor_bruto": {
                "coluna": "VALOR BRUTO",
                "transformacao": "monetario_br",
                "obrigatorio": True
            },
            "taxa_mdr": {
                "coluna": "DESCONTO DE MDR",
                "transformacao": "monetario_br",
                "obrigatorio": False
            },
            "valor_taxa": {
                "coluna": "DESCONTO UNIFICADO",
                "transformacao": "monetario_br",
                "obrigatorio": False
            },
            "valor_liquido": {
                "coluna": "VALOR LIQUIDO",
                "transformacao": "monetario_br",
                "obrigatorio": True
            },
            "parcela": {
                "coluna": "N DE PARCELAS",
                "transformacao": "texto",
                "obrigatorio": False
            },
            "tipo_transacao": {
                "coluna": "PRODUTO",
                "transformacao": "texto",
                "obrigatorio": False
            },
            "bandeira": {
                "coluna": "BANDEIRA",
                "transformacao": "texto",
                "obrigatorio": False
            }
        }
        
        # Atualizar template
        cur.execute("""
            UPDATE templates_adquirentes 
            SET mapeamento = %s,
                updated_at = NOW()
            WHERE id = %s
        """, (
            Json(novo_mapeamento),
            template_id
        ))
        
        conn.commit()
        
        print("\n✅ Template Stone atualizado com sucesso!")
        print("\n📋 Mapeamento NSU atualizado:")
        print(f"   Coluna: NSU -> STONE ID")
        print(f"   Data Venda: Data Transação -> DATA DA VENDA")
        print(f"   Valor Líquido: Valor Líquido -> VALOR LIQUIDO")
        
        cur.close()
        
    except Exception as e:
        print(f"❌ Erro ao atualizar template: {e}")
        if conn:
            conn.rollback()
        import traceback
        traceback.print_exc()
    finally:
        if conn:
            conn.close()

if __name__ == '__main__':
    print("🔄 Atualizando template Stone...\n")
    atualizar_template_stone()
