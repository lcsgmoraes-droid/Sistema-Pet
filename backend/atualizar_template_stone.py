"""
Script para atualizar template Stone com colunas corretas do CSV
"""

from psycopg2.extras import Json

from legacy_script_env import connect_database
from legacy_stone_template_mapping import stone_template_mapping


def atualizar_template_stone():
    conn = None
    try:
        # Conectar ao banco
        conn = connect_database("STONE_TEMPLATE_DATABASE_URL", "DATABASE_URL")
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
        novo_mapeamento = stone_template_mapping(
            parcela_key="parcela",
            parcela_transformacao="texto",
        )

        # Atualizar template
        cur.execute(
            """
            UPDATE templates_adquirentes 
            SET mapeamento = %s,
                updated_at = NOW()
            WHERE id = %s
        """,
            (Json(novo_mapeamento), template_id),
        )

        conn.commit()

        print("\n✅ Template Stone atualizado com sucesso!")
        print("\n📋 Mapeamento NSU atualizado:")
        print("   Coluna: NSU -> STONE ID")
        print("   Data Venda: Data Transação -> DATA DA VENDA")
        print("   Valor Líquido: Valor Líquido -> VALOR LIQUIDO")

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


if __name__ == "__main__":
    print("🔄 Atualizando template Stone...\n")
    atualizar_template_stone()
