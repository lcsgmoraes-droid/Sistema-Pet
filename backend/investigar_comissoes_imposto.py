"""
Investigar comissões e config fiscal
"""

import sys
sys.path.insert(0, r"c:\Users\Lucas\OneDrive\Área de Trabalho\Programa\Sistema Pet\backend")

from app.db import SessionLocal
from sqlalchemy import text

db = SessionLocal()

numero_venda = "202602130001"

print("="*80)
print(f"INVESTIGAÇÃO DETALHADA - VENDA {numero_venda}".center(80))
print("="*80)

# Buscar ID da venda
venda = db.execute(text("SELECT id FROM vendas WHERE numero_venda = :numero"), 
                   {"numero": numero_venda}).fetchone()
venda_id = venda[0] if venda else None

if not venda_id:
    print("Venda não encontrada!")
    sys.exit(1)

print(f"\nVenda ID: {venda_id}")

# 1. Buscar em TODAS as tabelas que podem ter comissões
print("\n[1] BUSCANDO COMISSÕES EM DIFERENTES TABELAS:")

# Tentar comissoes_itens
print("\n   A) Tabela comissoes_itens:")
try:
    comissoes_itens = db.execute(text("""
        SELECT id, funcionario_id, valor_comissao, percentual_comissao, status
        FROM comissoes_itens
        WHERE venda_id = :venda_id
    """), {"venda_id": venda_id}).fetchall()
    
    if comissoes_itens:
        print(f"      ✓ Encontradas {len(comissoes_itens)} comissões:")
        for com in comissoes_itens:
            print(f"      - ID {com[0]}: Funcionário {com[1]}, Valor R$ {com[2]}, {com[3]}%, Status: {com[4]}")
    else:
        print("      Nenhuma comissão encontrada")
except Exception as e:
    print(f"      ⚠️ Erro: Tabela não existe ou erro na query")
    db.rollback()

# 2. Verificar TODAS as colunas da tabela empresa_config_fiscal
print("\n[2] ESTRUTURA DA TABELA empresa_config_fiscal:")
try:
    colunas = db.execute(text("""
        SELECT column_name, data_type, is_nullable, column_default
        FROM information_schema.columns
        WHERE table_name = 'empresa_config_fiscal'
        ORDER BY ordinal_position
    """)).fetchall()
    
    print(f"   Colunas encontradas: {len(colunas)}")
    for col in colunas:
        print(f"   - {col[0]} ({col[1]}) NULL={col[2]} DEFAULT={col[3]}")
except Exception as e:
    print(f"   ⚠️ Erro: {str(e)}")
    db.rollback()

# 3. Buscar dados COMPLETOS da config fiscal
print("\n[3] DADOS COMPLETOS DA CONFIG FISCAL:")
try:
    config = db.execute(text("""
        SELECT *
        FROM empresa_config_fiscal
        LIMIT 1
    """)).fetchone()
    
    if config:
        print(f"   Registro encontrado com {len(config)} campos:")
        # Pegar nomes das colunas
        result = db.execute(text("SELECT * FROM empresa_config_fiscal LIMIT 0"))
        col_names = result.keys()
        
        for i, col_name in enumerate(col_names):
            print(f"   {col_name}: {config[i]}")
    else:
        print("   ❌ Nenhum registro encontrado")
except Exception as e:
    print(f"   ⚠️ Erro: {str(e)}")
    db.rollback()

# 4. Verificar se existe regime_tributario em outra tabela
print("\n[4] PROCURANDO REGIME TRIBUTÁRIO:")
try:
    # Pode estar na tabela empresa ou configuracoes
    tables = db.execute(text("""
        SELECT table_name 
        FROM information_schema.tables 
        WHERE table_schema = 'public' 
        AND table_name LIKE '%empresa%' OR table_name LIKE '%config%'
    """)).fetchall()
    
    print(f"   Tabelas relacionadas: {[t[0] for t in tables]}")
except Exception as e:
    print(f"   ⚠️ Erro: {str(e)}")

print("\n" + "="*80)
print("FIM DA INVESTIGAÇÃO".center(80))
print("="*80)

db.close()
