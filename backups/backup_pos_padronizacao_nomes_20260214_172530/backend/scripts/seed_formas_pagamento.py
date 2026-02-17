"""
Script para popular formas de pagamento com taxas e vínculos
Vincula: Cartões → Stone, PIX → Santander, Dinheiro → Caixa
"""
import sys
from pathlib import Path
from decimal import Decimal

# Adicionar backend ao path
backend_path = Path(__file__).parent.parent
sys.path.insert(0, str(backend_path))

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
import os

# Configuração do banco
database_url = os.getenv(
    "DATABASE_URL",
    "postgresql://postgres:postgres@localhost:5433/petshop_dev"
)

engine = create_engine(database_url)
Session = sessionmaker(bind=engine)
session = Session()

print("🏦 SEED: Formas de Pagamento")
print("=" * 60)

# Obter IDs das contas e tenant
result = session.execute(text("""
    SELECT 
        (SELECT id FROM contas_bancarias WHERE nome = 'Caixa' LIMIT 1) as caixa_id,
        (SELECT id FROM contas_bancarias WHERE nome = 'Santander' LIMIT 1) as santander_id,
        (SELECT id FROM contas_bancarias WHERE nome = 'Stone' LIMIT 1) as stone_id,
        (SELECT id FROM users LIMIT 1) as user_id,
        (SELECT tenant_id FROM users LIMIT 1) as tenant_id
"""))
ids = result.first()

caixa_id = ids[0]
santander_id = ids[1]
stone_id = ids[2]
user_id = ids[3]
tenant_id = ids[4]

print(f"\n📋 Contas encontradas:")
print(f"   Caixa: {caixa_id}")
print(f"   Santander: {santander_id}")
print(f"   Stone: {stone_id}")
print(f"   User ID: {user_id}")
print(f"   Tenant ID: {tenant_id}")

if not all([caixa_id, santander_id, stone_id, user_id, tenant_id]):
    print("\n❌ ERRO: Contas bancárias ou usuário não encontrados!")
    print("Execute primeiro o seed de contas bancárias.")
    session.close()
    sys.exit(1)

# Limpar formas de pagamento existentes
print("\n🗑️  Limpando formas de pagamento antigas...")
session.execute(text("DELETE FROM formas_pagamento"))
session.commit()

# Formas de pagamento a criar
formas_pagamento = [
    # =====================================================
    # DINHEIRO - Caixa físico
    # =====================================================
    {
        "nome": "Dinheiro",
        "tipo": "dinheiro",
        "taxa_percentual": Decimal("0.00"),
        "taxa_fixa": Decimal("0.00"),
        "prazo_dias": 0,
        "operadora": None,
        "gera_contas_receber": False,
        "conta_bancaria_destino_id": caixa_id,
        "requer_nsu": False,
        "tipo_cartao": None,
        "bandeira": None,
        "permite_parcelamento": False,
        "max_parcelas": 1,
        "icone": "💵",
        "cor": "#22C55E",
        "permite_antecipacao": False,
        "dias_recebimento_antecipado": None,
        "taxa_antecipacao_percentual": None
    },
    
    # =====================================================
    # PIX - Santander (recebimento instantâneo)
    # =====================================================
    {
        "nome": "PIX",
        "tipo": "pix",
        "taxa_percentual": Decimal("0.00"),
        "taxa_fixa": Decimal("0.00"),
        "prazo_dias": 0,
        "operadora": "Santander",
        "gera_contas_receber": False,
        "conta_bancaria_destino_id": santander_id,
        "requer_nsu": False,
        "tipo_cartao": None,
        "bandeira": None,
        "permite_parcelamento": False,
        "max_parcelas": 1,
        "icone": "💳",
        "cor": "#0EA5E9",
        "permite_antecipacao": False,
        "dias_recebimento_antecipado": None,
        "taxa_antecipacao_percentual": None
    },
    
    # =====================================================
    # DÉBITO - Stone (taxa 2%, recebe em 1 dia)
    # =====================================================
    {
        "nome": "Débito",
        "tipo": "cartao_debito",
        "taxa_percentual": Decimal("2.00"),
        "taxa_fixa": Decimal("0.00"),
        "prazo_dias": 1,
        "operadora": "Stone",
        "gera_contas_receber": True,
        "conta_bancaria_destino_id": stone_id,
        "requer_nsu": True,
        "tipo_cartao": "debito",
        "bandeira": None,
        "permite_parcelamento": False,
        "max_parcelas": 1,
        "icone": "💳",
        "cor": "#3B82F6",
        "permite_antecipacao": True,
        "dias_recebimento_antecipado": 0,
        "taxa_antecipacao_percentual": Decimal("0.50")
    },
    
    # =====================================================
    # CRÉDITO À VISTA - Stone (taxa 3%, recebe em 30 dias)
    # =====================================================
    {
        "nome": "Crédito à Vista",
        "tipo": "cartao_credito",
        "taxa_percentual": Decimal("3.00"),
        "taxa_fixa": Decimal("0.00"),
        "prazo_dias": 30,
        "operadora": "Stone",
        "gera_contas_receber": True,
        "conta_bancaria_destino_id": stone_id,
        "requer_nsu": True,
        "tipo_cartao": "credito",
        "bandeira": None,
        "permite_parcelamento": False,
        "max_parcelas": 1,
        "icone": "💳",
        "cor": "#8B5CF6",
        "permite_antecipacao": True,
        "dias_recebimento_antecipado": 0,
        "taxa_antecipacao_percentual": Decimal("2.50")
    },
    
    # =====================================================
    # CRÉDITO PARCELADO - Stone
    # Taxa base 3% + 0.8% por parcela adicional
    # =====================================================
]

# Adicionar opções parceladas (2x a 12x)
for parcelas in range(2, 13):
    taxa = Decimal("3.00") + (Decimal("0.80") * (parcelas - 1))
    formas_pagamento.append({
        "nome": f"Crédito {parcelas}x",
        "tipo": "cartao_credito",
        "taxa_percentual": taxa,
        "taxa_fixa": Decimal("0.00"),
        "prazo_dias": 30,
        "operadora": "Stone",
        "gera_contas_receber": True,
        "split_parcelas": True,
        "conta_bancaria_destino_id": stone_id,
        "requer_nsu": True,
        "tipo_cartao": "credito",
        "bandeira": None,
        "permite_parcelamento": True,
        "max_parcelas": parcelas,
        "icone": "💳",
        "cor": "#A855F7",
        "permite_antecipacao": True,
        "dias_recebimento_antecipado": 0,
        "taxa_antecipacao_percentual": Decimal("2.50")
    })

print(f"\n📝 Criando {len(formas_pagamento)} formas de pagamento...")

for idx, forma in enumerate(formas_pagamento, 1):
    try:
        # Preparar dados
        insert_data = {
            **forma,
            "user_id": user_id,
            "tenant_id": str(tenant_id),
            "ativo": True,
            "prazo_recebimento": forma["prazo_dias"],
            "parcelas_maximas": forma["max_parcelas"],
            "split_parcelas": forma.get("split_parcelas", False),
            "permite_antecipacao": forma.get("permite_antecipacao", False),
            "dias_recebimento_antecipado": forma.get("dias_recebimento_antecipado"),
            "taxa_antecipacao_percentual": forma.get("taxa_antecipacao_percentual")
        }
        
        # SQL com RETURNING para pegar o ID
        sql = text("""
            INSERT INTO formas_pagamento (
                nome, tipo, taxa_percentual, taxa_fixa, prazo_dias, prazo_recebimento,
                operadora, gera_contas_receber, split_parcelas, conta_bancaria_destino_id,
                requer_nsu, tipo_cartao, bandeira, ativo, permite_parcelamento,
                max_parcelas, parcelas_maximas, icone, cor, user_id, tenant_id,
                permite_antecipacao, dias_recebimento_antecipado, taxa_antecipacao_percentual,
                created_at, updated_at
            ) VALUES (
                :nome, :tipo, :taxa_percentual, :taxa_fixa, :prazo_dias, :prazo_recebimento,
                :operadora, :gera_contas_receber, :split_parcelas, :conta_bancaria_destino_id,
                :requer_nsu, :tipo_cartao, :bandeira, :ativo, :permite_parcelamento,
                :max_parcelas, :parcelas_maximas, :icone, :cor, :user_id, CAST(:tenant_id AS UUID),
                :permite_antecipacao, :dias_recebimento_antecipado, :taxa_antecipacao_percentual,
                NOW(), NOW()
            ) RETURNING id
        """)
        
        result = session.execute(sql, insert_data)
        forma_id = result.scalar()
        session.commit()
        
        # Exibir resumo
        taxa_str = f"{forma['taxa_percentual']}%" if forma['taxa_percentual'] > 0 else "sem taxa"
        prazo_str = f"{forma['prazo_dias']}d" if forma['prazo_dias'] > 0 else "imediato"
        conta_nome = "Caixa" if forma["conta_bancaria_destino_id"] == caixa_id else ("Santander" if forma["conta_bancaria_destino_id"] == santander_id else "Stone")
        
        print(f"   ✅ {idx:2d}. {forma['nome']:<20} - {taxa_str:<10} - {prazo_str:<10} → {conta_nome} (ID: {forma_id})")
        
    except Exception as e:
        print(f"   ❌ Erro ao criar '{forma['nome']}': {e}")
        session.rollback()

# Resumo final
print("\n" + "=" * 60)
print("📊 RESUMO:")

result = session.execute(text("""
    SELECT 
        CASE 
            WHEN fp.tipo = 'dinheiro' THEN 'Dinheiro'
            WHEN fp.tipo = 'pix' THEN 'PIX'
            WHEN fp.tipo_cartao = 'debito' THEN 'Débito'
            WHEN fp.tipo_cartao = 'credito' AND fp.max_parcelas = 1 THEN 'Crédito à Vista'
            WHEN fp.tipo_cartao = 'credito' AND fp.max_parcelas > 1 THEN 'Crédito Parcelado'
            ELSE 'Outros'
        END as categoria,
        COUNT(*) as qtd,
        MIN(fp.taxa_percentual) as taxa_min,
        MAX(fp.taxa_percentual) as taxa_max,
        cb.nome as conta_destino
    FROM formas_pagamento fp
    LEFT JOIN contas_bancarias cb ON cb.id = fp.conta_bancaria_destino_id
    GROUP BY categoria, cb.nome
    ORDER BY categoria
"""))

for row in result:
    categoria, qtd, taxa_min, taxa_max, conta_destino = row
    if float(taxa_min) == float(taxa_max):
        taxa_str = f"{float(taxa_min):.2f}%"
    else:
        taxa_str = f"{float(taxa_min):.2f}% - {float(taxa_max):.2f}%"
    
    print(f"   {categoria:<20} - {int(qtd):2d} forma(s) - Taxa: {taxa_str:<12} → {conta_destino}")

print("\n✅ SEED COMPLETO!")
print("\n💡 Vínculos criados:")
print("   💵 Dinheiro        → Caixa")
print("   💳 PIX             → Santander")
print("   💳 Débito          → Stone")
print("   💳 Crédito (todos) → Stone")
print("\n🎯 Para testar no frontend:")
print("   1. Acesse a tela de Vendas/PDV")
print("   2. Selecione forma de pagamento")
print("   3. Valores serão creditados nas contas corretas!")

session.close()
