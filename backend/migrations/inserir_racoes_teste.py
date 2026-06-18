"""
Script para inserir produtos de ração de teste na base
"""

import sqlite3
import json
from datetime import datetime


def inserir_produtos_teste():
    conn = sqlite3.connect("petshop.db")
    cursor = conn.cursor()

    # Buscar user_id
    cursor.execute("SELECT id FROM users LIMIT 1")
    user = cursor.fetchone()
    if not user:
        print("❌ Erro: Nenhum usuário encontrado no banco de dados!")
        return

    user_id = user[0]
    print(f"📝 Usando user_id: {user_id}")

    print("=" * 70)
    print("INSERÇÃO DE PRODUTOS DE RAÇÃO PARA TESTE DA CALCULADORA")
    print("=" * 70)

    produtos_teste = [
        {
            "codigo": "RAC001",
            "nome": "Royal Canin Mini Adult",
            "descricao": "Ração para cães adultos de porte pequeno",
            "codigo_barras": "7896181200012",
            "preco_custo": 145.90,
            "preco_venda": 189.90,
            "estoque_minimo": 5,
            "estoque_atual": 20,
            "ativo": 1,
            # Campos específicos de ração
            "classificacao_racao": "super_premium",
            "peso_embalagem": 7.5,
            "categoria_racao": "adulto",
            "especies_indicadas": "dog",
            "tabela_nutricional": json.dumps(
                {
                    "proteina_bruta": "27%",
                    "gordura": "16%",
                    "fibra_bruta": "3.5%",
                    "umidade": "10%",
                    "calcio": "1.2%",
                    "fosforo": "0.9%",
                }
            ),
        },
        {
            "codigo": "RAC002",
            "nome": "Golden Fórmula Filhotes",
            "descricao": "Ração para filhotes de todas as raças",
            "codigo_barras": "7896181200029",
            "preco_custo": 89.90,
            "preco_venda": 119.90,
            "estoque_minimo": 10,
            "estoque_atual": 25,
            "ativo": 1,
            "classificacao_racao": "premium",
            "peso_embalagem": 15.0,
            "categoria_racao": "filhote",
            "especies_indicadas": "dog",
            "tabela_nutricional": json.dumps(
                {
                    "proteina_bruta": "30%",
                    "gordura": "18%",
                    "fibra_bruta": "3%",
                    "umidade": "10%",
                    "calcio": "1.4%",
                    "fosforo": "1.1%",
                    "dha": "0.05%",
                }
            ),
        },
        {
            "codigo": "RAC003",
            "nome": "Premier Gatos Castrados",
            "descricao": "Ração para gatos castrados adultos",
            "codigo_barras": "7896181200036",
            "preco_custo": 67.90,
            "preco_venda": 89.90,
            "estoque_minimo": 8,
            "estoque_atual": 15,
            "ativo": 1,
            "classificacao_racao": "premium",
            "peso_embalagem": 10.0,
            "categoria_racao": "adulto",
            "especies_indicadas": "cat",
            "tabela_nutricional": json.dumps(
                {
                    "proteina_bruta": "33%",
                    "gordura": "9%",
                    "fibra_bruta": "3.8%",
                    "umidade": "10%",
                    "calcio": "1%",
                    "fosforo": "0.85%",
                    "magnesio": "0.08%",
                }
            ),
        },
        {
            "codigo": "RAC004",
            "nome": "N&D Ancestral Grain Adulto",
            "descricao": "Ração natural para cães adultos com grãos ancestrais",
            "codigo_barras": "7896181200043",
            "preco_custo": 178.90,
            "preco_venda": 229.90,
            "estoque_minimo": 3,
            "estoque_atual": 12,
            "ativo": 1,
            "classificacao_racao": "super_premium",
            "peso_embalagem": 10.0,
            "categoria_racao": "adulto",
            "especies_indicadas": "dog",
            "tabela_nutricional": json.dumps(
                {
                    "proteina_bruta": "28%",
                    "gordura": "18%",
                    "fibra_bruta": "2.9%",
                    "umidade": "9%",
                    "calcio": "1.1%",
                    "fosforo": "0.91%",
                    "omega_3": "0.4%",
                    "omega_6": "3.3%",
                }
            ),
        },
        {
            "codigo": "RAC005",
            "nome": "Pedigree Adulto Carne e Vegetais",
            "descricao": "Ração completa para cães adultos",
            "codigo_barras": "7896181200050",
            "preco_custo": 42.90,
            "preco_venda": 59.90,
            "estoque_minimo": 15,
            "estoque_atual": 40,
            "ativo": 1,
            "classificacao_racao": "standard",
            "peso_embalagem": 10.0,
            "categoria_racao": "adulto",
            "especies_indicadas": "dog",
            "tabela_nutricional": json.dumps(
                {
                    "proteina_bruta": "21%",
                    "gordura": "10%",
                    "fibra_bruta": "4%",
                    "umidade": "12%",
                    "calcio": "1.2%",
                    "fosforo": "1%",
                }
            ),
        },
        {
            "codigo": "RAC006",
            "nome": "Hills Senior 7+ Cães",
            "descricao": "Ração para cães idosos com mais de 7 anos",
            "codigo_barras": "7896181200067",
            "preco_custo": 156.90,
            "preco_venda": 199.90,
            "estoque_minimo": 5,
            "estoque_atual": 10,
            "ativo": 1,
            "classificacao_racao": "super_premium",
            "peso_embalagem": 12.0,
            "categoria_racao": "senior",
            "especies_indicadas": "dog",
            "tabela_nutricional": json.dumps(
                {
                    "proteina_bruta": "24%",
                    "gordura": "14%",
                    "fibra_bruta": "3%",
                    "umidade": "10%",
                    "calcio": "0.9%",
                    "fosforo": "0.7%",
                    "glucosamina": "250mg/kg",
                    "condroitina": "300mg/kg",
                }
            ),
        },
    ]

    produtos_inseridos = []

    for produto in produtos_teste:
        try:
            # Verificar se produto já existe
            cursor.execute(
                "SELECT id FROM produtos WHERE codigo_barras = ?",
                (produto["codigo_barras"],),
            )

            existe = cursor.fetchone()

            if existe:
                print(f"⚠ Produto '{produto['nome']}' já existe (ID: {existe[0]})")
                produtos_inseridos.append(existe[0])
                continue

            # Inserir produto
            now = datetime.now().isoformat()
            cursor.execute(
                """
                INSERT INTO produtos (
                    user_id, codigo, nome, descricao, codigo_barras, 
                    preco_custo, preco_venda, 
                    estoque_minimo, estoque_atual,
                    unidade, ativo,
                    classificacao_racao, peso_embalagem,
                    categoria_racao, especies_indicadas,
                    tabela_nutricional,
                    created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    user_id,
                    produto["codigo"],
                    produto["nome"],
                    produto["descricao"],
                    produto["codigo_barras"],
                    produto["preco_custo"],
                    produto["preco_venda"],
                    produto["estoque_minimo"],
                    produto["estoque_atual"],
                    "kg",
                    produto.get("ativo", 1),
                    produto["classificacao_racao"],
                    produto["peso_embalagem"],
                    produto["categoria_racao"],
                    produto["especies_indicadas"],
                    produto["tabela_nutricional"],
                    now,
                    now,
                ),
            )

            produto_id = cursor.lastrowid
            produtos_inseridos.append(produto_id)

            print(f"✓ Produto inserido: {produto['nome']}")
            print(f"  • ID: {produto_id}")
            print(f"  • Classificação: {produto['classificacao_racao']}")
            print(f"  • Peso: {produto['peso_embalagem']}kg")
            print(f"  • Preço: R$ {produto['preco_venda']:.2f}")
            print(f"  • Categoria: {produto['categoria_racao']}")
            print(f"  • Espécie: {produto['especies_indicadas']}")
            print()

        except Exception as e:
            print(f"✗ Erro ao inserir '{produto['nome']}': {e}")

    conn.commit()
    conn.close()

    print("=" * 70)
    print(
        f"✅ Processo concluído! {len(produtos_inseridos)} produtos prontos para teste"
    )
    print("\nProdutos inseridos (IDs):", produtos_inseridos)
    print("\n💡 Para testar a calculadora:")
    print("   1. Acesse a página 'Calculadora de Ração' no menu")
    print("   2. Selecione um produto da lista")
    print("   3. Informe dados do pet (peso, idade, atividade)")
    print("   4. Clique em 'Calcular' para ver duração e custos")
    print("   5. Clique em 'Comparar Rações' para ver todas as opções")
    print("\n📊 Exemplo de teste:")
    print("   • Pet: Cão adulto, 12kg, atividade moderada")
    print("   • Produto: Golden Fórmula Filhotes (15kg - R$ 119,90)")
    print("   • Resultado esperado: ~50 dias de duração, R$ 2,40/dia")


if __name__ == "__main__":
    inserir_produtos_teste()
