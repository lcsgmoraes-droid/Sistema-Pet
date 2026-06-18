"""Script para corrigir template Stone no banco"""

import json

from legacy_script_env import connect_database
from legacy_stone_template_mapping import stone_template_mapping

# Conectar ao banco
conn = connect_database("STONE_TEMPLATE_DATABASE_URL", "DATABASE_URL")

cur = conn.cursor()

# Mapeamento correto
mapeamento_correto = stone_template_mapping(
    parcela_key="parcelas",
    parcela_transformacao="inteiro",
)

# Atualizar template
try:
    cur.execute(
        "UPDATE adquirentes_templates SET mapeamento = %s WHERE nome = 'STONE'",
        (json.dumps(mapeamento_correto),),
    )

    conn.commit()
    print("✅ Template Stone atualizado com sucesso!")
    print("   Campo 'parcela' → 'parcelas' (transformação: inteiro)")

    # Verificar
    cur.execute("SELECT mapeamento FROM adquirentes_templates WHERE nome = 'STONE'")
    result = cur.fetchone()
    if result:
        print("\n🔍 Mapeamento atual:")
        mapeamento_db = result[0]
        if "parcelas" in mapeamento_db:
            print(f"   ✅ Campo 'parcelas': {mapeamento_db['parcelas']}")
        else:
            print("   ❌ Campo 'parcelas' não encontrado!")

except Exception as e:
    print(f"❌ Erro: {e}")
    conn.rollback()
finally:
    cur.close()
    conn.close()
