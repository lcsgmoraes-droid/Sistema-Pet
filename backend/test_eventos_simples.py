"""
Teste simples dos eventos de domínio - sem importar app completo
"""

import sys
from pathlib import Path

# Adicionar backend ao path
backend_dir = Path(__file__).parent
sys.path.insert(0, str(backend_dir))

print("=" * 80)
print("TESTE SIMPLES: EVENTOS DE DOMÍNIO")
print("=" * 80)

print("\n📋 TESTE 1: Importar domain_events diretamente")
print("-" * 80)
try:
    from app.events.domain_events import (
        DomainEvent,
        VendaRealizadaEvent,
        ProdutoVendidoEvent,
        KitVendidoEvent
    )
    print("✅ Importação bem-sucedida!")
except Exception as e:
    print(f"❌ ERRO ao importar: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print("\n📋 TESTE 2: Criar VendaRealizadaEvent")
print("-" * 80)
try:
    evento_venda = VendaRealizadaEvent(
        user_id=1,
        venda_id=123,
        numero_venda="VENDA-2024-001",
        total=250.50,
        forma_pagamento="DINHEIRO",
        quantidade_itens=3,
        cliente_id=456,
        tem_kit=True
    )
    print(f"✅ Evento criado: {evento_venda.event_id[:30]}...")
    print(f"   - venda_id: {evento_venda.venda_id}")
    print(f"   - numero_venda: {evento_venda.numero_venda}")
    print(f"   - total: R$ {evento_venda.total:.2f}")
    print(f"   - timestamp: {evento_venda.timestamp}")
except Exception as e:
    print(f"❌ ERRO ao criar evento: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print("\n📋 TESTE 3: Criar ProdutoVendidoEvent")
print("-" * 80)
try:
    evento_produto = ProdutoVendidoEvent(
        user_id=1,
        venda_id=123,
        produto_id=456,
        produto_nome="Shampoo Neutro 500ml",
        tipo_produto="SIMPLES",
        quantidade=2.0,
        preco_unitario=15.50,
        preco_total=31.00,
        estoque_anterior=10.0,
        estoque_novo=8.0
    )
    print(f"✅ Evento criado: {evento_produto.event_id[:30]}...")
    print(f"   - produto_id: {evento_produto.produto_id}")
    print(f"   - produto_nome: {evento_produto.produto_nome}")
    print(f"   - quantidade: {evento_produto.quantidade}")
    print(f"   - estoque: {evento_produto.estoque_anterior} → {evento_produto.estoque_novo}")
except Exception as e:
    print(f"❌ ERRO ao criar evento: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print("\n📋 TESTE 4: Criar KitVendidoEvent")
print("-" * 80)
try:
    evento_kit = KitVendidoEvent(
        user_id=1,
        venda_id=123,
        kit_id=789,
        kit_nome="Kit Banho Completo",
        tipo_kit="VIRTUAL",
        quantidade=2.0,
        preco_unitario=85.00,
        preco_total=170.00,
        componentes_baixados=[
            {"produto_id": 10, "nome": "Shampoo", "quantidade": 2.0},
            {"produto_id": 11, "nome": "Condicionador", "quantidade": 2.0}
        ]
    )
    print(f"✅ Evento criado: {evento_kit.event_id[:30]}...")
    print(f"   - kit_id: {evento_kit.kit_id}")
    print(f"   - kit_nome: {evento_kit.kit_nome}")
    print(f"   - tipo_kit: {evento_kit.tipo_kit}")
    print(f"   - componentes: {len(evento_kit.componentes_baixados)}")
except Exception as e:
    print(f"❌ ERRO ao criar evento: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print("\n📋 TESTE 5: Verificar imutabilidade")
print("-" * 80)
try:
    evento_venda.venda_id = 999  # Deve falhar
    print("❌ ERRO: Evento não é imutável!")
    sys.exit(1)
except Exception:
    print("✅ Eventos são imutáveis (frozen=True funcionando)")

print("\n📋 TESTE 6: Testar serialização")
print("-" * 80)
try:
    dict_evento = evento_venda.to_dict()
    print(f"✅ to_dict() OK - {len(dict_evento)} campos")
    
    json_evento = evento_venda.to_json()
    print(f"✅ to_json() OK - {len(json_evento)} caracteres")
    print(f"   Exemplo: {json_evento[:100]}...")
except Exception as e:
    print(f"❌ ERRO na serialização: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print("\n" + "=" * 80)
print("✅ TODOS OS TESTES PASSARAM!")
print("=" * 80)
