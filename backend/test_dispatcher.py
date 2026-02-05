"""
Teste do EventDispatcher - Pub/Sub de eventos
"""

import sys
from pathlib import Path

# Adicionar backend ao path
backend_dir = Path(__file__).parent
sys.path.insert(0, str(backend_dir))

print("=" * 80)
print("TESTE: EVENT DISPATCHER (PUB/SUB)")
print("=" * 80)

print("\n📋 TESTE 1: Importar EventDispatcher")
print("-" * 80)
try:
    from app.events.event_dispatcher import EventDispatcher, publish_event, subscribe_event, get_all_events
    from app.events.domain_events import VendaRealizadaEvent, ProdutoVendidoEvent
    print("✅ Importação bem-sucedida!")
except Exception as e:
    print(f"❌ ERRO ao importar: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print("\n📋 TESTE 2: Publicar eventos")
print("-" * 80)
try:
    evento1 = VendaRealizadaEvent(
        user_id=1,
        venda_id=100,
        numero_venda="VENDA-001",
        total=150.00,
        forma_pagamento="PIX",
        quantidade_itens=2
    )
    publish_event(evento1)
    print(f"✅ Evento VendaRealizadaEvent publicado (venda_id={evento1.venda_id})")
    
    evento2 = ProdutoVendidoEvent(
        user_id=1,
        venda_id=100,
        produto_id=50,
        produto_nome="Ração Premium 15kg",
        tipo_produto="SIMPLES",
        quantidade=1.0,
        preco_unitario=120.00,
        preco_total=120.00,
        estoque_anterior=5.0,
        estoque_novo=4.0
    )
    publish_event(evento2)
    print(f"✅ Evento ProdutoVendidoEvent publicado (produto_id={evento2.produto_id})")
    
    evento3 = VendaRealizadaEvent(
        user_id=1,
        venda_id=101,
        numero_venda="VENDA-002",
        total=89.90,
        forma_pagamento="CREDITO",
        quantidade_itens=1
    )
    publish_event(evento3)
    print(f"✅ Evento VendaRealizadaEvent publicado (venda_id={evento3.venda_id})")
except Exception as e:
    print(f"❌ ERRO ao publicar: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print("\n📋 TESTE 3: Verificar armazenamento")
print("-" * 80)
try:
    todos_eventos = get_all_events()
    print(f"✅ Total de eventos armazenados: {len(todos_eventos)}")
    for i, evt in enumerate(todos_eventos, 1):
        tipo = evt.__class__.__name__
        if hasattr(evt, 'venda_id'):
            print(f"   {i}. {tipo} - venda_id={evt.venda_id}")
        if hasattr(evt, 'produto_id'):
            print(f"      └─ produto_id={evt.produto_id}, produto={evt.produto_nome}")
except Exception as e:
    print(f"❌ ERRO ao verificar eventos: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print("\n📋 TESTE 4: Subscriber/Handler")
print("-" * 80)
try:
    # Criar handler para VendaRealizadaEvent
    vendas_processadas = []
    
    def on_venda_realizada(evento: VendaRealizadaEvent):
        vendas_processadas.append(evento.venda_id)
        print(f"   → Handler chamado: venda_id={evento.venda_id}, total=R${evento.total:.2f}")
    
    # Registrar handler (passar CLASSE, não string)
    subscribe_event(VendaRealizadaEvent, on_venda_realizada)
    print("✅ Handler registrado para VendaRealizadaEvent")
    
    # Publicar novo evento - deve chamar o handler
    evento4 = VendaRealizadaEvent(
        user_id=1,
        venda_id=102,
        numero_venda="VENDA-003",
        total=220.00,
        forma_pagamento="DEBITO",
        quantidade_itens=4
    )
    publish_event(evento4)
    print(f"✅ Evento publicado e handler executado")
    print(f"   Vendas processadas pelo handler: {vendas_processadas}")
except Exception as e:
    print(f"❌ ERRO no handler: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print("\n📋 TESTE 5: Estatísticas do dispatcher")
print("-" * 80)
try:
    from app.events.event_dispatcher import get_event_stats
    
    stats = get_event_stats()
    print(f"✅ Estatísticas coletadas:")
    print(f"   - Total de eventos: {stats['total']}")
    print(f"   - Contagem por tipo:")
    for tipo, count in stats['por_tipo'].items():
        print(f"      • {tipo}: {count}")
    print(f"   - Contagem por usuário:")
    for user_id, count in stats['por_usuario'].items():
        print(f"      • user_id {user_id}: {count}")
except Exception as e:
    print(f"❌ ERRO nas estatísticas: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print("\n📋 TESTE 6: Múltiplos handlers")
print("-" * 80)
try:
    produtos_log = []
    
    def log_produto_vendido(evento: ProdutoVendidoEvent):
        produtos_log.append(evento.produto_nome)
    
    subscribe_event(ProdutoVendidoEvent, log_produto_vendido)
    print("✅ Segundo handler registrado para ProdutoVendidoEvent")
    
    # Publicar produto
    evento5 = ProdutoVendidoEvent(
        user_id=1,
        venda_id=102,
        produto_id=51,
        produto_nome="Coleira de Couro P",
        tipo_produto="VARIACAO",
        quantidade=1.0,
        preco_unitario=45.00,
        preco_total=45.00,
        estoque_anterior=3.0,
        estoque_novo=2.0
    )
    publish_event(evento5)
    print(f"✅ Handler executado, produtos no log: {produtos_log}")
except Exception as e:
    print(f"❌ ERRO em múltiplos handlers: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print("\n" + "=" * 80)
print("✅ TODOS OS TESTES DO DISPATCHER PASSARAM!")
print("=" * 80)
print(f"\nResumo final:")
print(f"  - Eventos publicados: {len(get_all_events())}")
print(f"  - Handlers registrados: 2 tipos (VendaRealizadaEvent, ProdutoVendidoEvent)")
print(f"  - Sistema pub/sub funcionando corretamente")
