"""
Script para corrigir os testes de idempotência
"""
import re
from pathlib import Path

file_path = Path(__file__).parent / "tests" / "test_handlers_idempotencia_fase53.py"
content = file_path.read_text(encoding='utf-8')

# Adicionar imports
if "from app.core.side_effects_guard import suppress_in_replay" not in content:
    content = content.replace(
        "from app.read_models.handlers_v53_idempotente import VendaReadModelHandler",
        "from app.read_models.handlers_v53_idempotente import VendaReadModelHandler\n" +
        "from app.core.side_effects_guard import suppress_in_replay\n" +
        "from app.core.replay_context import enable_replay_mode, disable_replay_mode"
    )

# Corrigir VendaCriada em test_venda_criada_idempotente
content = re.sub(
    r'evento = VendaCriada\(\s*venda_id="venda_test_1",\s*numero_venda=1,\s*user_id=1,\s*total=100\.00,\s*quantidade_itens=2,\s*cliente_id=42,\s*tem_entrega=False\s*\)',
    '''evento = VendaCriada(
        venda_id=100,
        numero_venda='202601230001',
        user_id=1,
        cliente_id=42,
        funcionario_id=None,
        total=100.0,
        quantidade_itens=2,
        tem_entrega=False
    )''',
    content
)

# Corrigir VendaFinalizada
content = re.sub(
    r'evento = VendaFinalizada\(\s*venda_id="venda_test_2",\s*numero_venda=2,\s*user_id=1,\s*user_nome="Test User",\s*total=500\.00,\s*total_pago=500\.00,\s*status="finalizada",\s*funcionario_id=10,\s*formas_pagamento=\["dinheiro"\]\s*\)',
    '''evento = VendaFinalizada(
        venda_id=200,
        numero_venda='202601230002',
        user_id=1,
        user_nome='Test User',
        cliente_id=None,
        funcionario_id=10,
        total=500.0,
        total_pago=500.0,
        status='finalizada',
        formas_pagamento=['dinheiro'],
        estoque_baixado=True,
        caixa_movimentado=True,
        contas_baixadas=1
    )''',
    content
)

# Corrigir VendaCancelada
content = re.sub(
    r'evento = VendaCancelada\(\s*venda_id="venda_test_3",\s*numero_venda=3,\s*user_id=1,\s*total=300\.00,\s*funcionario_id=10,\s*motivo="Teste cancelamento",\s*status_anterior="aberta"\s*\)',
    '''evento = VendaCancelada(
        venda_id=300,
        numero_venda='202601230003',
        user_id=1,
        cliente_id=None,
        funcionario_id=10,
        motivo='Teste cancelamento',
        status_anterior='aberta',
        total=300.0,
        itens_estornados=2,
        contas_canceladas=1,
        comissoes_estornadas=False
    )''',
    content
)

# Corrigir VendaCriada em test_upsert_performance
content = re.sub(
    r'evento = VendaCriada\(\s*venda_id=f"venda_\{i\}",\s*numero_venda=i,\s*user_id=1,\s*total=100\.00,\s*quantidade_itens=1,\s*cliente_id=None,\s*tem_entrega=False\s*\)',
    '''evento = VendaCriada(
            venda_id=i,
            numero_venda=f'202601230{i:03d}',
            user_id=1,
            cliente_id=None,
            funcionario_id=None,
            total=100.0,
            quantidade_itens=1,
            tem_entrega=False
        )''',
    content,
    flags=re.MULTILINE | re.DOTALL
)

file_path.write_text(content, encoding='utf-8')
print(f"✅ Arquivo corrigido: {file_path}")
