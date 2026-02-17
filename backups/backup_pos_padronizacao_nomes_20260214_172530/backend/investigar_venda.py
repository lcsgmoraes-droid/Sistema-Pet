"""
Investigar campos da venda 202602130001
"""

import sys
sys.path.insert(0, r"c:\Users\Lucas\OneDrive\Área de Trabalho\Programa\Sistema Pet\backend")

from app.db import SessionLocal
from sqlalchemy import text
from decimal import Decimal

db = SessionLocal()

numero_venda = "202602130001"

print("="*80)
print(f"INVESTIGAÇÃO DA VENDA {numero_venda}".center(80))
print("="*80)

# 1. Buscar dados da venda
print("\n[1] DADOS DA VENDA:")
venda = db.execute(text("""
    SELECT 
        id, numero_venda, data_venda, cliente_id, vendedor_id, funcionario_id,
        subtotal, desconto_valor, desconto_percentual, total,
        tem_entrega, taxa_entrega, 
        percentual_taxa_entregador, percentual_taxa_loja,
        valor_taxa_entregador, valor_taxa_loja,
        entregador_id, status
    FROM vendas
    WHERE numero_venda = :numero
"""), {"numero": numero_venda}).fetchone()

if not venda:
    print(f"❌ Venda {numero_venda} não encontrada!")
    sys.exit(1)

print(f"   ID: {venda[0]}")
print(f"   Número: {venda[1]}")
print(f"   Data: {venda[2]}")
print(f"   Cliente ID: {venda[3]}")
print(f"   Vendedor ID: {venda[4]}")
print(f"   Funcionário ID: {venda[5]}")
print(f"   Subtotal: R$ {venda[6]}")
print(f"   Desconto: R$ {venda[7]}")
print(f"   Desconto %: {venda[8]}")
print(f"   Total: R$ {venda[9]}")
print(f"   Tem Entrega: {venda[10]}")
print(f"   Taxa Entrega: R$ {venda[11]}")
print(f"   % Taxa Entregador: {venda[12]}")
print(f"   % Taxa Loja: {venda[13]}")
print(f"   Valor Taxa Entregador: R$ {venda[14]}")
print(f"   Valor Taxa Loja: R$ {venda[15]}")
print(f"   Entregador ID: {venda[16]}")
print(f"   Status: {venda[17]}")

venda_id = venda[0]

# 2. Buscar itens da venda
print(f"\n[2] ITENS DA VENDA:")
itens = db.execute(text("""
    SELECT 
        vi.id, vi.produto_id, p.nome, vi.quantidade, 
        vi.preco_unitario, vi.subtotal, p.preco_custo
    FROM venda_itens vi
    LEFT JOIN produtos p ON p.id = vi.produto_id
    WHERE vi.venda_id = :venda_id
"""), {"venda_id": venda_id}).fetchall()

print(f"   Total de itens: {len(itens)}")
for item in itens:
    print(f"   - {item[2]}: {item[3]} x R$ {item[4]} = R$ {item[5]} (custo: R$ {item[6]})")

# 3. Buscar pagamentos
print(f"\n[3] FORMAS DE PAGAMENTO:")
pagamentos = db.execute(text("""
    SELECT 
        id, forma_pagamento, valor, numero_parcelas,
        operadora_id, nsu_cartao, bandeira
    FROM venda_pagamentos
    WHERE venda_id = :venda_id
"""), {"venda_id": venda_id}).fetchall()

print(f"   Total de pagamentos: {len(pagamentos)}")
for pag in pagamentos:
    print(f"   - Forma: {pag[1]}")
    print(f"     Valor: R$ {pag[2]}")
    print(f"     Parcelas: {pag[3]}")
    print(f"     Operadora ID: {pag[4]}")
    print(f"     NSU: {pag[5]}")
    print(f"     Bandeira: {pag[6]}")

# 4. Buscar comissões
print(f"\n[4] COMISSÕES DA VENDA:")
try:
    comissoes = db.execute(text("""
        SELECT 
            id, funcionario_id, valor_venda, valor_comissao, 
            percentual, status
        FROM comissoes_vendas
        WHERE venda_id = :venda_id
    """), {"venda_id": venda_id}).fetchall()

    print(f"   Total de comissões: {len(comissoes)}")
    for com in comissoes:
        print(f"   - Funcionário ID: {com[1]}")
        print(f"     Valor Venda: R$ {com[2]}")
        print(f"     Valor Comissão: R$ {com[3]}")
        print(f"     Percentual: {com[4]}%")
        print(f"     Status: {com[5]}")
except Exception as e:
    print(f"   ⚠️ Erro ao buscar comissões: Tabela não existe no banco")
    db.rollback()  # Rollback para continuar

# 5. Buscar dados do entregador (se houver)
if venda[16]:  # entregador_id
    print(f"\n[5] DADOS DO ENTREGADOR:")
    entregador = db.execute(text("""
        SELECT 
            id, nome, taxa_fixa_entrega
        FROM clientes
        WHERE id = :entregador_id
    """), {"entregador_id": venda[16]}).fetchone()
    
    if entregador:
        print(f"   ID: {entregador[0]}")
        print(f"   Nome: {entregador[1]}")
        print(f"   Taxa Fixa Entrega: R$ {entregador[2]}")
    else:
        print("   ❌ Entregador não encontrado")

# 6. Buscar configuração fiscal
print(f"\n[6] CONFIGURAÇÃO FISCAL:")
config_fiscal = db.execute(text("""
    SELECT 
        id, simples_ativo, simples_anexo, aliquota_simples_vigente
    FROM empresa_config_fiscal
    LIMIT 1
""")).fetchone()

if config_fiscal:
    print(f"   ID: {config_fiscal[0]}")
    print(f"   Simples Ativo: {config_fiscal[1]}")
    print(f"   Anexo: {config_fiscal[2]}")
    print(f"   Alíquota Vigente: {config_fiscal[3]}%")
else:
    print("   ❌ Configuração fiscal não encontrada")

# 7. Buscar operadoras de cartão (se houver taxa_percentual nos pagamentos)
print(f"\n[7] OPERADORAS DE CARTÃO:")
operadoras = db.execute(text("""
    SELECT 
        id, nome, taxa_debito, taxa_credito_vista, taxa_credito_parcelado
    FROM operadoras_cartao
""")).fetchall()

print(f"   Total de operadoras cadastradas: {len(operadoras)}")
for op in operadoras:
    print(f"   - {op[1]}: Débito {op[2]}% | Crédito à vista {op[3]}% | Crédito parcelado {op[4]}%")

print("\n" + "="*80)
print("FIM DA INVESTIGAÇÃO".center(80))
print("="*80)

db.close()
