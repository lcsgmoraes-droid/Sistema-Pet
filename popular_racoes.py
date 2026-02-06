"""
Popular banco com rações populares do Brasil
============================================
Cria produtos de ração com tabelas de consumo reais
"""
import sys
import json
from pathlib import Path

backend_dir = Path(__file__).parent / "backend"
sys.path.insert(0, str(backend_dir))

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from app.produtos_models import Produto

DATABASE_URL = "postgresql+psycopg2://postgres:postgres@localhost:5433/petshop_dev"
engine = create_engine(DATABASE_URL)
Session = sessionmaker(bind=engine)

# Definir produtos
produtos = [
    # ========== PREMIER (SUPER PREMIUM) ==========
    {
        "codigo": "RACAO-PREMIER-ADULTO-12KG",
        "nome": "Premier Cães Adultos Ambientes Internos Frango 12kg",
        "descricao_curta": "Ração Premier Super Premium para Cães Adultos de Ambientes Internos",
        "descricao_completa": "Premier Ambientes Internos Sabor Frango. Nutrição de excelência para cães adultos que vivem em apartamentos. Super Premium.",
        "preco_custo": 165.00,
        "preco_venda": 289.90,
        "codigo_barras": "7896181217640",
        "peso_liquido": 12.0,
        "classificacao_racao": "super_premium",
        "categoria_racao": "adulto",
        "especies_indicadas": "dog",
        "tabela_consumo": {
            "tipo": "peso_adulto",
            "dados": {
                "2kg": {"adulto": 45},
                "5kg": {"adulto": 90},
                "10kg": {"adulto": 150},
                "15kg": {"adulto": 200},
                "20kg": {"adulto": 250},
                "25kg": {"adulto": 290},
                "30kg": {"adulto": 330},
                "35kg": {"adulto": 370},
                "40kg": {"adulto": 405}
            }
        }
    },
    {
        "codigo": "RACAO-PREMIER-ADULTO-FRANGO-15KG",
        "nome": "Premier Cães Adultos Raças Médias e Grandes Frango 15kg",
        "descricao_curta": "Ração Premier Super Premium para Cães Adultos Médios e Grandes",
        "descricao_completa": "Premier Raças Médias e Grandes Sabor Frango. Fórmula completa e balanceada para cães adultos. Super Premium.",
        "preco_custo": 195.00,
        "preco_venda": 339.90,
        "codigo_barras": "7896181217701",
        "peso_liquido": 15.0,
        "classificacao_racao": "super_premium",
        "categoria_racao": "adulto",
        "especies_indicadas": "dog",
        "tabela_consumo": {
            "tipo": "peso_adulto",
            "dados": {
                "5kg": {"adulto": 85},
                "10kg": {"adulto": 145},
                "15kg": {"adulto": 195},
                "20kg": {"adulto": 245},
                "25kg": {"adulto": 285},
                "30kg": {"adulto": 325},
                "35kg": {"adulto": 360},
                "40kg": {"adulto": 395},
                "45kg": {"adulto": 425}
            }
        }
    },
    
    # ========== GOLDEN (PREMIUM SPECIAL) ==========
    {
        "codigo": "RACAO-GOLDEN-ADULTO-CARNE-15KG",
        "nome": "Golden Formula Cães Adultos Carne e Arroz 15kg",
        "descricao_curta": "Ração Golden Premium Special para Cães Adultos",
        "descricao_completa": "Golden Formula Sabor Carne e Arroz. Nutrição completa para cães adultos. Premium Special com extrato de Yucca.",
        "preco_custo": 135.00,
        "preco_venda": 239.90,
        "codigo_barras": "7896029003565",
        "peso_liquido": 15.0,
        "classificacao_racao": "premium",
        "categoria_racao": "adulto",
        "especies_indicadas": "dog",
        "tabela_consumo": {
            "tipo": "peso_adulto",
            "dados": {
                "5kg": {"adulto": 95},
                "10kg": {"adulto": 165},
                "15kg": {"adulto": 225},
                "20kg": {"adulto": 280},
                "25kg": {"adulto": 330},
                "30kg": {"adulto": 380},
                "35kg": {"adulto": 425},
                "40kg": {"adulto": 470},
                "45kg": {"adulto": 510}
            }
        }
    },
    {
        "codigo": "RACAO-GOLDEN-ADULTO-FRANGO-15KG",
        "nome": "Golden Formula Cães Adultos Frango e Arroz 15kg",
        "descricao_curta": "Ração Golden Premium Special para Cães Adultos",
        "descricao_completa": "Golden Formula Sabor Frango e Arroz. Nutrição completa para cães adultos. Premium Special com extrato de Yucca.",
        "preco_custo": 135.00,
        "preco_venda": 239.90,
        "codigo_barras": "7896029003541",
        "peso_liquido": 15.0,
        "classificacao_racao": "premium",
        "categoria_racao": "adulto",
        "especies_indicadas": "dog",
        "tabela_consumo": {
            "tipo": "peso_adulto",
            "dados": {
                "5kg": {"adulto": 95},
                "10kg": {"adulto": 165},
                "15kg": {"adulto": 225},
                "20kg": {"adulto": 280},
                "25kg": {"adulto": 330},
                "30kg": {"adulto": 380},
                "35kg": {"adulto": 425},
                "40kg": {"adulto": 470},
                "45kg": {"adulto": 510}
            }
        }
    },
    
    # ========== SPECIAL DOG VEGETAIS (PREMIUM) ==========
    {
        "codigo": "RACAO-SPECIALDOG-VEGETAIS-15KG",
        "nome": "Special Dog Vegetais 15kg",
        "descricao_curta": "Ração Special Dog Premium Vegetais para Cães Adultos",
        "descricao_completa": "Special Dog Vegetais com cenoura, ervilha e espinafre. Fórmula Premium para cães adultos. Rica em vitaminas.",
        "preco_custo": 95.00,
        "preco_venda": 169.90,
        "codigo_barras": "7896181208006",
        "peso_liquido": 15.0,
        "classificacao_racao": "premium",
        "categoria_racao": "adulto",
        "especies_indicadas": "dog",
        "tabela_consumo": {
            "tipo": "peso_adulto",
            "dados": {
                "5kg": {"adulto": 105},
                "10kg": {"adulto": 180},
                "15kg": {"adulto": 245},
                "20kg": {"adulto": 305},
                "25kg": {"adulto": 360},
                "30kg": {"adulto": 415},
                "35kg": {"adulto": 465},
                "40kg": {"adulto": 515},
                "45kg": {"adulto": 560}
            }
        }
    }
]

print("\n" + "="*70)
print("🐕 POPULAR BANCO COM RAÇÕES - MARCAS POPULARES")
print("="*70)

session = Session()

try:
    # Buscar tenant e usuário
    tenant = session.execute(text("SELECT id FROM tenants LIMIT 1")).fetchone()
    user = session.execute(text("SELECT id FROM users LIMIT 1")).fetchone()
    
    if not tenant or not user:
        print("❌ Tenant ou usuário não encontrado!")
        sys.exit(1)
    
    tenant_id = str(tenant[0])
    user_id = str(user[0])
    
    print(f"✅ Tenant: {tenant_id}")
    print(f"✅ User: {user_id}\n")
    
    criados = 0
    atualizados = 0
    
    for prod_data in produtos:
        # Verificar se já existe
        produto_existente = session.query(Produto).filter(
            Produto.codigo == prod_data["codigo"]
        ).first()
        
        if produto_existente:
            print(f"⚠️  {prod_data['nome'][:50]}... já existe (ID: {produto_existente.id})")
            # Atualizar tabela de consumo
            produto_existente.tabela_consumo = json.dumps(prod_data["tabela_consumo"])
            produto_existente.peso_liquido = prod_data["peso_liquido"]
            atualizados += 1
        else:
            produto = Produto(
                codigo=prod_data["codigo"],
                nome=prod_data["nome"],
                tipo_produto="SIMPLES",
                descricao_curta=prod_data["descricao_curta"],
                descricao_completa=prod_data["descricao_completa"],
                preco_custo=prod_data["preco_custo"],
                preco_venda=prod_data["preco_venda"],
                codigo_barras=prod_data["codigo_barras"],
                estoque_atual=30,
                estoque_minimo=5,
                unidade="UN",
                situacao=True,
                peso_liquido=prod_data["peso_liquido"],
                classificacao_racao=prod_data["classificacao_racao"],
                categoria_racao=prod_data["categoria_racao"],
                especies_indicadas=prod_data["especies_indicadas"],
                tabela_consumo=json.dumps(prod_data["tabela_consumo"]),
                tenant_id=tenant_id,
                user_id=user_id
            )
            session.add(produto)
            print(f"✅ {prod_data['nome'][:50]}... criado")
            criados += 1
    
    session.commit()
    
    print("\n" + "="*70)
    print("📊 RESUMO:")
    print(f"   ✅ Produtos criados: {criados}")
    print(f"   ♻️  Produtos atualizados: {atualizados}")
    print(f"   📦 Total: {criados + atualizados}")
    
    print("\n📋 PRODUTOS NO BANCO:")
    print("="*70)
    
    # Listar todos os produtos de ração
    racoes = session.query(Produto).filter(
        Produto.classificacao_racao.isnot(None)
    ).order_by(Produto.classificacao_racao, Produto.nome).all()
    
    classificacao_atual = None
    for racao in racoes:
        if racao.classificacao_racao != classificacao_atual:
            classificacao_atual = racao.classificacao_racao
            print(f"\n🏆 {classificacao_atual.upper()}")
            print("-" * 70)
        
        print(f"   • {racao.nome[:55]}")
        print(f"     R$ {racao.preco_venda:.2f} | {racao.peso_liquido}kg | Estoque: {racao.estoque_atual}")
    
    print("\n✅ Banco populado com sucesso!")
    print("🧪 Teste a calculadora de ração com estes produtos!")
    
except Exception as e:
    print(f"\n❌ Erro: {e}")
    session.rollback()
    raise
finally:
    session.close()

print("\n" + "="*70 + "\n")
