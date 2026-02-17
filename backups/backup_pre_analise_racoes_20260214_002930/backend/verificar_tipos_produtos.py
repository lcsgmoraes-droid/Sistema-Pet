#!/usr/bin/env python3
"""
Verificar distribuição de produtos por tipo_produto no banco
"""
from sqlalchemy import create_engine, func
from sqlalchemy.orm import sessionmaker
import os
import sys

# Adicionar diretório parent ao Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.produtos_models import Produto

# Database URL
DATABASE_URL = "postgresql://postgres:postgres@localhost:5433/petshop_dev"

def verificar_tipos_produtos():
    engine = create_engine(DATABASE_URL)
    Session = sessionmaker(bind=engine)
    session = Session()
    
    try:
        tenant_id = "9df51a66-72bb-495f-a4a6-8a4953b20eae"
        
        print("📊 DISTRIBUIÇÃO DE PRODUTOS POR TIPO\n")
        print("="*60)
        
        # Total geral
        total = session.query(func.count(Produto.id)).filter(
            Produto.tenant_id == tenant_id
        ).scalar()
        print(f"Total geral de produtos: {total}")
        
        # Por tipo
        print(f"\nPor tipo_produto:")
        tipos = session.query(
            Produto.tipo_produto,
            func.count(Produto.id)
        ).filter(
            Produto.tenant_id == tenant_id
        ).group_by(Produto.tipo_produto).all()
        
        for tipo, qtd in tipos:
            print(f"  - {tipo or '(NULL)'}: {qtd}")
        
        # Filtro do backend (apenas SIMPLES, PAI, KIT)
        print(f"\n" + "="*60)
        print(f"Produtos que o backend MOSTRA na listagem:")
        print(f"(tipo_produto in ['SIMPLES', 'PAI', 'KIT'])")
        
        mostrados = session.query(func.count(Produto.id)).filter(
            Produto.tenant_id == tenant_id,
            Produto.tipo_produto.in_(['SIMPLES', 'PAI', 'KIT'])
        ).scalar()
        
        print(f"  Total: {mostrados}")
        
        # Produtos OCULTOS (VARIACAO)
        print(f"\n" + "="*60)
        print(f"Produtos OCULTOS na listagem:")
        print(f"(tipo_produto = 'VARIACAO')")
        
        ocultos = session.query(func.count(Produto.id)).filter(
            Produto.tenant_id == tenant_id,
            Produto.tipo_produto == 'VARIACAO'
        ).scalar()
        
        print(f"  Total: {ocultos}")
        
        # Produtos SEM tipo
        print(f"\n" + "="*60)
        print(f"Produtos SEM tipo_produto (NULL ou vazio):")
        
        sem_tipo = session.query(func.count(Produto.id)).filter(
            Produto.tenant_id == tenant_id,
            (Produto.tipo_produto.is_(None)) | (Produto.tipo_produto == '')
        ).scalar()
        
        print(f"  Total: {sem_tipo}")
        
        # Mostrar alguns exemplos de produtos SIMPLES
        print(f"\n" + "="*60)
        print(f"Exemplos de produtos SIMPLES:")
        simples = session.query(Produto).filter(
            Produto.tenant_id == tenant_id,
            Produto.tipo_produto == 'SIMPLES'
        ).limit(5).all()
        
        for p in simples:
            print(f"  - ID {p.id}: {p.nome} (código: {p.codigo})")
        
    finally:
        session.close()

if __name__ == "__main__":
    verificar_tipos_produtos()
