"""Script para corrigir template Stone no banco"""
import psycopg2
import json

# Conectar ao banco
conn = psycopg2.connect(
    host="localhost",
    port=5433,
    database="petshop_dev",
    user="postgres",
    password="postgres"
)

cur = conn.cursor()

# Mapeamento correto
mapeamento_correto = {
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
    "parcelas": {
        "coluna": "N DE PARCELAS",
        "transformacao": "inteiro",
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
try:
    cur.execute(
        "UPDATE adquirentes_templates SET mapeamento = %s WHERE nome = 'STONE'",
        (json.dumps(mapeamento_correto),)
    )
    
    conn.commit()
    print(f"✅ Template Stone atualizado com sucesso!")
    print(f"   Campo 'parcela' → 'parcelas' (transformação: inteiro)")
    
    # Verificar
    cur.execute("SELECT mapeamento FROM adquirentes_templates WHERE nome = 'STONE'")
    result = cur.fetchone()
    if result:
        print(f"\n🔍 Mapeamento atual:")
        mapeamento_db = result[0]
        if 'parcelas' in mapeamento_db:
            print(f"   ✅ Campo 'parcelas': {mapeamento_db['parcelas']}")
        else:
            print(f"   ❌ Campo 'parcelas' não encontrado!")
            
except Exception as e:
    print(f"❌ Erro: {e}")
    conn.rollback()
finally:
    cur.close()
    conn.close()
