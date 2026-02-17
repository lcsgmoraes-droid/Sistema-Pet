"""
Script para verificar dados já importados no banco DEV
"""
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

# Conexão direta ao banco DEV
DATABASE_URL = "postgresql://postgres:postgres@localhost:5433/petshop_dev"
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)

def verificar_dados():
    """Verifica quantidade de dados importados"""
    db = SessionLocal()
    
    try:
        print("\n" + "="*70)
        print("DADOS JÁ IMPORTADOS NO BANCO DEV".center(70))
        print("="*70)
        
        # Contagem de registros
        queries = {
            'Clientes': "SELECT COUNT(*) FROM clientes",
            'Produtos': "SELECT COUNT(*) FROM produtos",
            'Pets': "SELECT COUNT(*) FROM pets",
            'Vendas': "SELECT COUNT(*) FROM vendas",
            'Itens Venda': "SELECT COUNT(*) FROM vendas_itens",
            'Espécies': "SELECT COUNT(*) FROM especies",
            'Raças': "SELECT COUNT(*) FROM racas",
            'Marcas': "SELECT COUNT(*) FROM marcas",
        }
        
        for tabela, query in queries.items():
            result = db.execute(text(query))
            count = result.scalar()
            print(f"{tabela:15} : {count:6} registros")
        
        # Verificar clientes com código (importados)
        result = db.execute(text("SELECT COUNT(*) FROM clientes WHERE codigo IS NOT NULL AND codigo != ''"))
        clientes_codigo = result.scalar()
        print(f"\n{'Clientes c/ código':15} : {clientes_codigo:6} (importados do SimplesVet)")
        
        # Verificar produtos com código
        result = db.execute(text("SELECT COUNT(*) FROM produtos WHERE codigo IS NOT NULL AND codigo != ''"))
        produtos_codigo = result.scalar()
        print(f"{'Produtos c/ código':15} : {produtos_codigo:6} (importados do SimplesVet)")
        
        # Verificar vendas importadas (com prefixo IMP-)
        result = db.execute(text("SELECT COUNT(*) FROM vendas WHERE numero_venda LIKE 'IMP-%'"))
        vendas_imp = result.scalar()
        print(f"{'Vendas IMP-*':15} : {vendas_imp:6} (importadas do SimplesVet)")
        
        print("="*70)
        
        # Mostrar alguns exemplos de códigos já importados
        print("\nEXEMPLOS DE CÓDIGOS JÁ IMPORTADOS:")
        print("-"*70)
        
        result = db.execute(text("SELECT codigo, nome FROM clientes WHERE codigo IS NOT NULL ORDER BY id LIMIT 5"))
        clientes = result.fetchall()
        if clientes:
            print("\nClientes:")
            for codigo, nome in clientes:
                print(f"  - Código: {codigo:10} | {nome}")
        
        result = db.execute(text("SELECT codigo, nome FROM produtos WHERE codigo IS NOT NULL ORDER BY id LIMIT 5"))
        produtos = result.fetchall()
        if produtos:
            print("\nProdutos:")
            for codigo, nome in produtos:
                print(f"  - Código: {codigo:10} | {nome}")
        
        print("="*70 + "\n")
        
    except Exception as e:
        print(f"Erro: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    verificar_dados()
