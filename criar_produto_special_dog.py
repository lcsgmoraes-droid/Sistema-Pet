"""
Criar produto Special Dog Carne 15kg com tabela de consumo
============================================================
Script para inserir produto de ração com tabela de consumo
para testes da calculadora.
"""

import sys
import json
from pathlib import Path

# Adicionar o diretório backend ao path
backend_dir = Path(__file__).parent / "backend"
sys.path.insert(0, str(backend_dir))

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

# Configuração do banco
DATABASE_URL = "postgresql+psycopg2://postgres:postgres@localhost:5433/petshop_dev"

# Criar engine
engine = create_engine(DATABASE_URL)
Session = sessionmaker(bind=engine)

# Tabela de consumo baseada em dados reais da Special Dog
# Fonte: Embalagem original Special Dog Carne 15kg
tabela_consumo = {
    "tipo": "peso_adulto",
    "dados": {
        "5kg": {"adulto": 110},
        "10kg": {"adulto": 185},
        "15kg": {"adulto": 250},
        "20kg": {"adulto": 310},
        "25kg": {"adulto": 365},
        "30kg": {"adulto": 420},
        "35kg": {"adulto": 470},
        "40kg": {"adulto": 520},
        "45kg": {"adulto": 565}
    }
}

def criar_produto():
    """Cria o produto Special Dog no banco"""
    session = Session()
    
    try:
        print("\n🔍 Buscando tenant_id...")
        
        # Buscar tenant_id (UUID)
        result_tenant = session.execute(
            text("SELECT id FROM tenants LIMIT 1")
        ).fetchone()
        
        if not result_tenant:
            print("❌ Nenhum tenant encontrado! Execute a migração primeiro.")
            return
        
        tenant_id = str(result_tenant[0])
        print(f"✅ Tenant ID: {tenant_id}")
        
        print("\n🔍 Verificando se produto já existe...")
        
        # Verificar se já existe
        result = session.execute(
            text("SELECT id, nome FROM produtos WHERE nome LIKE '%Special Dog%' LIMIT 1")
        ).fetchone()
        
        if result:
            print(f"⚠️  Produto já existe: ID {result[0]} - {result[1]}")
            print("\n📝 Atualizando tabela de consumo...")
            
            # Atualizar tabela de consumo
            session.execute(
                text("""
                    UPDATE produtos 
                    SET tabela_consumo = :tabela,
                        peso_liquido = 15.0,
                        classificacao_racao = 'standard',
                        categoria_racao = 'adulto',
                        especies_indicadas = 'dog',
                        updated_at = CURRENT_TIMESTAMP
                    WHERE id = :id
                """),
                {"tabela": json.dumps(tabela_consumo), "id": result[0]}
            )
            session.commit()
            
            print(f"✅ Produto atualizado com sucesso!")
            produto_id = result[0]
            
        else:
            print("\n📦 Criando novo produto...")
            
            # Criar produto
            result = session.execute(
                text("""
                    INSERT INTO produtos (
                        codigo,
                        nome,
                        tipo_produto,
                        descricao_curta,
                        descricao_completa,
                        preco_custo,
                        preco_venda,
                        codigo_barras,
                        estoque_atual,
                        estoque_minimo,
                        unidade,
                        situacao,
                        peso_liquido,
                        classificacao_racao,
                        categoria_racao,
                        especies_indicadas,
                        tabela_consumo,
                        tenant_id,
                        created_at,
                        updated_at
                    ) VALUES (
                        :codigo,
                        :nome,
                        :tipo_produto,
                        :descricao_curta,
                        :descricao_completa,
                        :preco_custo,
                        :preco_venda,
                        :codigo_barras,
                        :estoque_atual,
                        :estoque_minimo,
                        :unidade,
                        :situacao,
                        :peso_liquido,
                        :classificacao_racao,
                        :categoria_racao,
                        :especies_indicadas,
                        :tabela_consumo,
                        :tenant_id,
                        CURRENT_TIMESTAMP,
                        CURRENT_TIMESTAMP
                    )
                    RETURNING id
                """),
                {
                    "codigo": "RACAO-SPECIALDOG-15KG",
                    "nome": "Special Dog Carne 15kg",
                    "tipo_produto": "SIMPLES",
                    "descricao_curta": "Ração Special Dog Sabor Carne para Cães Adultos",
                    "descricao_completa": "Ração Special Dog Sabor Carne para Cães Adultos - Embalagem 15kg. Alimento completo e balanceado.",
                    "preco_custo": 85.00,
                    "preco_venda": 149.90,
                    "codigo_barras": "7896181207931",
                    "estoque_atual": 50,
                    "estoque_minimo": 5,
                    "unidade": "UN",
                    "situacao": True,
                    "peso_liquido": 15.0,
                    "classificacao_racao": "standard",
                    "categoria_racao": "adulto",
                    "especies_indicadas": "dog",
                    "tabela_consumo": json.dumps(tabela_consumo),
                    "tenant_id": tenant_id
                }
            )
            
            produto_id = result.fetchone()[0]
            session.commit()
            
            print(f"✅ Produto criado com sucesso! ID: {produto_id}")
        
        # Mostrar dados do produto
        print("\n📊 Dados do Produto:")
        print("=" * 60)
        
        produto = session.execute(
            text("""
                SELECT 
                    id,
                    nome,
                    preco_venda,
                    peso_liquido,
                    classificacao_racao,
                    categoria_racao,
                    especies_indicadas,
                    estoque_atual
                FROM produtos
                WHERE id = :id
            """),
            {"id": produto_id}
        ).fetchone()
        
        print(f"ID: {produto[0]}")
        print(f"Nome: {produto[1]}")
        print(f"Preço: R$ {produto[2]:.2f}")
        print(f"Peso: {produto[3]}kg")
        print(f"Classificação: {produto[4]}")
        print(f"Categoria: {produto[5]}")
        print(f"Espécie: {produto[6]}")
        print(f"Estoque: {produto[7]} unidades")
        
        print("\n📋 Tabela de Consumo (gramas/dia):")
        print("=" * 60)
        for peso, dados in tabela_consumo["dados"].items():
            print(f"Cão de {peso.rjust(4)}: {dados['adulto']}g/dia")
        
        print("\n✅ Produto pronto para usar na calculadora!")
        print("\n💡 Exemplo de teste:")
        print(f"   - Cão de 10kg: {tabela_consumo['dados']['10kg']['adulto']}g/dia")
        print(f"   - Durabilidade: {(15000 / tabela_consumo['dados']['10kg']['adulto']):.1f} dias")
        print(f"   - Custo/dia: R$ {(149.90 / (15000 / tabela_consumo['dados']['10kg']['adulto'])):.2f}")
        
    except Exception as e:
        print(f"\n❌ Erro: {e}")
        session.rollback()
        raise
    finally:
        session.close()

if __name__ == "__main__":
    print("\n" + "="*60)
    print("🐕 CRIAR PRODUTO: Special Dog Carne 15kg")
    print("="*60)
    
    criar_produto()
    
    print("\n" + "="*60)
    print("✅ CONCLUÍDO!")
    print("="*60 + "\n")
