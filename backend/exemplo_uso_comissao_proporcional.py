"""
EXEMPLO DE USO - Comissão Proporcional a Pagamentos Parciais

Este arquivo demonstra como usar a nova funcionalidade de comissão proporcional.
"""
from decimal import Decimal
from app.comissoes_service import gerar_comissoes_venda

# ============================================================================
# EXEMPLO 1: Venda com pagamento total à vista
# ============================================================================

print("EXEMPLO 1: Pagamento à vista (comportamento tradicional)")
print("-" * 60)

resultado = gerar_comissoes_venda(
    venda_id=100,
    funcionario_id=5
    # Sem valor_pago = gera comissão sobre o valor total
)

print(f"✅ Comissão gerada: R$ {resultado.get('total_comissao', 0):.2f}")
print(f"   Duplicado: {resultado.get('duplicated', False)}")
print()


# ============================================================================
# EXEMPLO 2: Venda com pagamentos parciais
# ============================================================================

print("EXEMPLO 2: Pagamentos parciais")
print("-" * 60)
print("Venda total: R$ 1.000,00 | Comissão: 10%")
print()

# Primeira parcela: R$ 300
print("1️⃣ Primeira parcela: R$ 300,00")
resultado1 = gerar_comissoes_venda(
    venda_id=101,
    funcionario_id=5,
    valor_pago=Decimal('300.00'),
    parcela_numero=1
)
print(f"   ✅ Comissão gerada: R$ {resultado1.get('total_comissao', 0):.2f} (30% do total)")
print()

# Segunda parcela: R$ 400
print("2️⃣ Segunda parcela: R$ 400,00")
resultado2 = gerar_comissoes_venda(
    venda_id=101,
    funcionario_id=5,
    valor_pago=Decimal('400.00'),
    parcela_numero=2
)
print(f"   ✅ Comissão gerada: R$ {resultado2.get('total_comissao', 0):.2f} (40% do total)")
print()

# Terceira parcela: R$ 300
print("3️⃣ Terceira parcela: R$ 300,00")
resultado3 = gerar_comissoes_venda(
    venda_id=101,
    funcionario_id=5,
    valor_pago=Decimal('300.00'),
    parcela_numero=3
)
print(f"   ✅ Comissão gerada: R$ {resultado3.get('total_comissao', 0):.2f} (30% do total)")
print()

total = (
    resultado1.get('total_comissao', 0) +
    resultado2.get('total_comissao', 0) +
    resultado3.get('total_comissao', 0)
)
print(f"📊 Total acumulado: R$ {total:.2f}")
print()


# ============================================================================
# EXEMPLO 3: Tentativa de duplicar parcela (idempotência)
# ============================================================================

print("EXEMPLO 3: Idempotência (tentativa de duplicar)")
print("-" * 60)

resultado_dup = gerar_comissoes_venda(
    venda_id=101,
    funcionario_id=5,
    valor_pago=Decimal('300.00'),
    parcela_numero=1  # Mesma parcela do Exemplo 2
)

print(f"✅ Duplicado detectado: {resultado_dup.get('duplicated', False)}")
print(f"   Mensagem: {resultado_dup.get('message', '')}")
print(f"   Comissão gerada: R$ {resultado_dup.get('total_comissao', 0):.2f} (zero pois já existe)")
print()


# ============================================================================
# EXEMPLO 4: Consultando comissões por parcela
# ============================================================================

print("EXEMPLO 4: Consultar comissões de uma venda")
print("-" * 60)

from app.db import get_db_connection

conn = get_db_connection()
cursor = conn.cursor()

cursor.execute("""
    SELECT 
        parcela_numero,
        valor_pago_referencia,
        percentual_aplicado,
        valor_base_original,
        valor_base_comissionada,
        valor_comissao
    FROM comissoes_itens
    WHERE venda_id = 101 AND funcionario_id = 5
    ORDER BY parcela_numero
""")

parcelas = cursor.fetchall()

print(f"Total de parcelas: {len(parcelas)}")
print()

for p in parcelas:
    print(f"Parcela {p['parcela_numero']}:")
    print(f"   Valor pago: R$ {p['valor_pago_referencia']:.2f}")
    print(f"   Percentual: {p['percentual_aplicado']:.2f}%")
    print(f"   Comissão original: R$ {p['valor_base_original']:.2f}")
    print(f"   Comissão proporcional: R$ {p['valor_base_comissionada']:.2f}")
    print(f"   Comissão final: R$ {p['valor_comissao']:.2f}")
    print()

conn.close()


# ============================================================================
# BOAS PRÁTICAS
# ============================================================================

print("=" * 60)
print("📚 BOAS PRÁTICAS")
print("=" * 60)
print()
print("1. SEMPRE informar parcela_numero quando usar valor_pago")
print("   - Garante idempotência correta")
print()
print("2. Incrementar parcela_numero sequencialmente")
print("   - parcela_numero=1, 2, 3, ...")
print()
print("3. Não recalcular comissões já geradas")
print("   - Use o retorno 'duplicated' para validar")
print()
print("4. Monitorar logs estruturados")
print("   - COMMISSION_PARTIAL_GENERATED")
print("   - COMMISSION_PARTIAL_DUPLICATED")
print()
print("5. Validar antes de gerar:")
print("   - Venda deve estar 'finalizada' ou 'baixa_parcial'")
print("   - Configuração de comissão deve existir")
print()
