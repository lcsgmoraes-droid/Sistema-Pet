"""
Criar produto Special Dog pelo ORM - VERSÃO SIMPLES
"""
import sys
import json
from pathlib import Path

backend_dir = Path(__file__).parent / "backend"
sys.path.insert(0, str(backend_dir))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.produtos_models import Produto

DATABASE_URL = "postgresql+psycopg2://postgres:postgres@localhost:5433/petshop_dev"
engine = create_engine(DATABASE_URL)
Session = sessionmaker(bind=engine)

# Tabela de consumo
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

print("\n" + "="*60)
print("🐕 CRIAR PRODUTO: Special Dog Carne 15kg (ORM)")
print("="*60)

session = Session()

try:
    # Buscar tenant e usuário
    from sqlalchemy import text
    tenant = session.execute(text("SELECT id FROM tenants LIMIT 1")).fetchone()
    user = session.execute(text("SELECT id FROM users LIMIT 1")).fetchone()
    
    if not tenant or not user:
        print("❌ Tenant ou usuário não encontrado!")
        sys.exit(1)
    
    tenant_id = str(tenant[0])
    user_id = str(user[0])
    
    print(f"✅ Tenant: {tenant_id}")
    print(f"✅ User: {user_id}")
    
    # Verificar se já existe
    produto_existente = session.query(Produto).filter(
        Produto.codigo == "RACAO-SPECIALDOG-15KG"
    ).first()
    
    if produto_existente:
        print(f"\n⚠️  Produto já existe! ID: {produto_existente.id}")
        print("📝 Atualizando tabela de consumo...")
        produto_existente.tabela_consumo = json.dumps(tabela_consumo)
        produto_existente.peso_liquido = 15.0
        produto = produto_existente
    else:
        print("\n📦 Criando novo produto...")
        produto = Produto(
            codigo="RACAO-SPECIALDOG-15KG",
            nome="Special Dog Carne 15kg",
            tipo_produto="SIMPLES",
            descricao_curta="Ração Special Dog Sabor Carne para Cães Adultos",
            descricao_completa="Ração Special Dog Sabor Carne para Cães Adultos - Embalagem 15kg. Alimento completo e balanceado.",
            preco_custo=85.00,
            preco_venda=149.90,
            codigo_barras="7896181207931",
            estoque_atual=50,
            estoque_minimo=5,
            unidade="UN",
            situacao=True,
            peso_liquido=15.0,
            classificacao_racao="standard",
            categoria_racao="adulto",
            especies_indicadas="dog",
            tabela_consumo=json.dumps(tabela_consumo),
            tenant_id=tenant_id,
            user_id=user_id
        )
        session.add(produto)
    
    session.commit()
    session.refresh(produto)
    
    print(f"\n✅ Produto criado/atualizado! ID: {produto.id}")
    print("\n📊 Dados:")
    print(f"   Nome: {produto.nome}")
    print(f"   Preço: R$ {produto.preco_venda:.2f}")
    print(f"   Peso: {produto.peso_liquido}kg")
    print(f"   Estoque: {produto.estoque_atual} unidades")
    
    print("\n📋 Tabela de Consumo:")
    for peso, dados in tabela_consumo["dados"].items():
        print(f"   Cão de {peso.rjust(4)}: {dados['adulto']}g/dia")
    
    print("\n✅ Pronto para testar na calculadora!")
    
except Exception as e:
    print(f"\n❌ Erro: {e}")
    session.rollback()
    raise
finally:
    session.close()

print("\n" + "="*60 + "\n")
