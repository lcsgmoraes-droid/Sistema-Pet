"""Script de teste rápido para validar o módulo operator_chat"""

from app.ai.operator_chat import (
    OperatorMessage,
    OperatorChatContext,
    get_operator_chat_service
)

print("\n" + "="*80)
print("TESTE RÁPIDO - CHAT DO OPERADOR")
print("="*80)

# Teste 1: Criar mensagem
print("\n1. Criando mensagem...")
mensagem = OperatorMessage(
    pergunta="Esse cliente costuma comprar o quê?",
    operador_id=1,
    operador_nome="João Silva"
)
print(f"   ✓ Mensagem criada: '{mensagem.pergunta}'")

# Teste 2: Criar contexto
print("\n2. Criando contexto...")
contexto = OperatorChatContext(
    tenant_id=1,
    message=mensagem,
    contexto_cliente={
        "nome": "Roberto Santos",
        "total_compras": 50
    }
)
print(f"   ✓ Contexto criado para tenant_id={contexto.tenant_id}")

# Teste 3: Processar pergunta
print("\n3. Processando pergunta...")
service = get_operator_chat_service()
resposta = service.processar_pergunta(contexto)
print(f"   ✓ Resposta recebida (confiança: {resposta.confianca:.2%})")

# Teste 4: Exibir resultado
print("\n4. Resultado:")
print(f"\n   Pergunta: {mensagem.pergunta}")
print(f"   Intenção: {resposta.intencao_detectada}")
print(f"   Confiança: {resposta.confianca:.2%}")
print(f"   Tempo: {resposta.tempo_processamento_ms}ms")
print(f"   Fontes: {', '.join(resposta.fontes_utilizadas)}")
print(f"\n   Resposta:")
print(f"   {resposta.resposta[:200]}...")

print("\n" + "="*80)
print("✅ TESTE CONCLUÍDO COM SUCESSO!")
print("="*80 + "\n")
