"""
Exemplos de uso do Chat do Operador

Este módulo contém exemplos funcionais que demonstram como usar
o OperatorChatService em diferentes cenários.

Execute com:
    python -m app.ai.operator_chat.examples
"""

from datetime import datetime
from typing import Dict, Any

from .models import (
    OperatorMessage,
    OperatorChatContext,
)
from .service import get_operator_chat_service
from app.utils.logger import logger


# ============================================================================
# DADOS DE EXEMPLO
# ============================================================================

EXEMPLO_CLIENTE_VIP = {
    "nome": "Roberto Santos",
    "total_compras": 50,
    "ticket_medio": 450.00,
    "ultima_compra": "2026-01-20",
    "status": "VIP",
    "categorias_preferidas": ["Ração Premium", "Higiene", "Acessórios"],
}

EXEMPLO_VENDA_EM_ANDAMENTO = {
    "venda_id": 12345,
    "cliente_nome": "Roberto Santos",
    "total_parcial": 599.80,
    "vendedor_nome": "João Silva",
    "itens": [
        {
            "produto_id": 301,
            "nome_produto": "Ração Super Premium 15kg",
            "quantidade": 2,
            "valor_unitario": 299.90,
            "valor_total": 599.80,
            "categoria": "Ração",
            "fabricante": "Royal Canin",
        }
    ],
}

EXEMPLO_PRODUTOS = [
    {
        "produto_id": 301,
        "nome": "Ração Super Premium 15kg",
        "categoria": "Ração",
        "fabricante": "Royal Canin",
        "valor_unitario": 299.90,
        "quantidade": 2,
    },
    {
        "produto_id": 205,
        "nome": "Shampoo Antipulgas",
        "categoria": "Higiene",
        "fabricante": "Pet Clean",
        "valor_unitario": 45.00,
        "quantidade": 1,
    },
]

EXEMPLO_INSIGHTS = [
    {
        "tipo": "cliente_vip",
        "titulo": "Cliente VIP",
        "mensagem_curta": "Cliente VIP - 50 compras realizadas.",
        "confianca": 0.90,
    },
    {
        "tipo": "kit_vantajoso",
        "titulo": "Kit Mais Vantajoso",
        "mensagem_curta": "Kit Higiene Completa sai 12% mais barato.",
        "confianca": 0.85,
    },
]


# ============================================================================
# FUNÇÕES AUXILIARES
# ============================================================================


def criar_mensagem(pergunta: str) -> OperatorMessage:
    """Cria uma mensagem do operador"""
    return OperatorMessage(
        pergunta=pergunta,
        operador_id=1,
        operador_nome="João Silva",
        timestamp=datetime.now(),
    )


def criar_contexto(
    pergunta: str,
    contexto_pdv: Dict[str, Any] = None,
    contexto_cliente: Dict[str, Any] = None,
    contexto_produto: list = None,
    contexto_insights: list = None,
) -> OperatorChatContext:
    """Cria um contexto completo para o chat"""
    mensagem = criar_mensagem(pergunta)

    return OperatorChatContext(
        tenant_id=1,
        message=mensagem,
        contexto_pdv=contexto_pdv,
        contexto_cliente=contexto_cliente,
        contexto_produto=contexto_produto,
        contexto_insights=contexto_insights,
    )


def exibir_resposta(resposta, numero_exemplo: int, titulo: str):
    """Exibe a resposta de forma formatada"""
    print("\n" + "=" * 80)
    logger.info(f"EXEMPLO {numero_exemplo}: {titulo}")
    print("=" * 80)
    logger.info("\n📝 RESPOSTA:")
    print(resposta.resposta)
    logger.info("\n📊 METADADOS:")
    logger.info(f"   - Intenção: {resposta.intencao_detectada}")
    logger.info(f"   - Confiança: {resposta.confianca:.2%}")
    logger.info(f"   - Fontes: {', '.join(resposta.fontes_utilizadas)}")
    logger.info(f"   - Tempo: {resposta.tempo_processamento_ms}ms")
    logger.info(f"   - Origem: {resposta.origem}")
    logger.info("\n💡 CONTEXTO USADO:")
    for chave, valor in resposta.contexto_usado.items():
        logger.info(f"   - {chave}: {'✓' if valor else '✗'}")


# ============================================================================
# EXEMPLOS FUNCIONAIS
# ============================================================================


def exemplo_1_cliente_vip():
    """Exemplo 1: Pergunta sobre cliente VIP"""
    logger.info("\n\n🎯 Iniciando Exemplo 1...")

    contexto = criar_contexto(
        pergunta="Esse cliente costuma comprar o quê?",
        contexto_cliente=EXEMPLO_CLIENTE_VIP,
        contexto_insights=EXEMPLO_INSIGHTS,
    )

    service = get_operator_chat_service()
    resposta = service.processar_pergunta(contexto)

    exibir_resposta(resposta, 1, "Pergunta sobre Cliente VIP")


def exemplo_2_kit_vantajoso():
    """Exemplo 2: Pergunta sobre kit melhor"""
    logger.info("\n\n🎯 Iniciando Exemplo 2...")

    contexto = criar_contexto(
        pergunta="Tem algum kit melhor pra essa venda?",
        contexto_pdv=EXEMPLO_VENDA_EM_ANDAMENTO,
        contexto_produto=EXEMPLO_PRODUTOS,
        contexto_insights=EXEMPLO_INSIGHTS,
    )

    service = get_operator_chat_service()
    resposta = service.processar_pergunta(contexto)

    exibir_resposta(resposta, 2, "Pergunta sobre Kit Vantajoso")


def exemplo_3_produto_vendendo_bem():
    """Exemplo 3: Pergunta sobre produto específico"""
    logger.info("\n\n🎯 Iniciando Exemplo 3...")

    contexto = criar_contexto(
        pergunta="Esse produto está vendendo bem?", contexto_produto=EXEMPLO_PRODUTOS
    )

    service = get_operator_chat_service()
    resposta = service.processar_pergunta(contexto)

    exibir_resposta(resposta, 3, "Pergunta sobre Produto")


def exemplo_4_sugestao_venda():
    """Exemplo 4: Pergunta sobre o que oferecer"""
    logger.info("\n\n🎯 Iniciando Exemplo 4...")

    contexto = criar_contexto(
        pergunta="Tem algo que eu deveria oferecer agora?",
        contexto_pdv=EXEMPLO_VENDA_EM_ANDAMENTO,
        contexto_insights=EXEMPLO_INSIGHTS,
    )

    service = get_operator_chat_service()
    resposta = service.processar_pergunta(contexto)

    exibir_resposta(resposta, 4, "Pergunta sobre Sugestões")


def exemplo_5_cliente_atrasado():
    """Exemplo 5: Pergunta sobre situação do cliente"""
    logger.info("\n\n🎯 Iniciando Exemplo 5...")

    cliente_com_atraso = {
        **EXEMPLO_CLIENTE_VIP,
        "status": "Atenção - Pagamento atrasado",
    }

    contexto = criar_contexto(
        pergunta="Esse cliente está atrasado?", contexto_cliente=cliente_com_atraso
    )

    service = get_operator_chat_service()
    resposta = service.processar_pergunta(contexto)

    exibir_resposta(resposta, 5, "Pergunta sobre Status do Cliente")


def exemplo_6_resumo_venda():
    """Exemplo 6: Pergunta sobre resumo da venda"""
    logger.info("\n\n🎯 Iniciando Exemplo 6...")

    contexto = criar_contexto(
        pergunta="Resumo rápido dessa venda",
        contexto_pdv=EXEMPLO_VENDA_EM_ANDAMENTO,
        contexto_cliente=EXEMPLO_CLIENTE_VIP,
        contexto_produto=EXEMPLO_PRODUTOS,
        contexto_insights=EXEMPLO_INSIGHTS,
    )

    service = get_operator_chat_service()
    resposta = service.processar_pergunta(contexto)

    exibir_resposta(resposta, 6, "Resumo da Venda")


def exemplo_7_pergunta_generica():
    """Exemplo 7: Pergunta genérica sem contexto"""
    logger.info("\n\n🎯 Iniciando Exemplo 7...")

    contexto = criar_contexto(pergunta="Como funciona o sistema de comissões?")

    service = get_operator_chat_service()
    resposta = service.processar_pergunta(contexto)

    exibir_resposta(resposta, 7, "Pergunta Genérica")


def exemplo_8_estoque():
    """Exemplo 8: Pergunta sobre estoque"""
    logger.info("\n\n🎯 Iniciando Exemplo 8...")

    contexto = criar_contexto(
        pergunta="Tem esse produto em estoque?", contexto_produto=EXEMPLO_PRODUTOS
    )

    service = get_operator_chat_service()
    resposta = service.processar_pergunta(contexto)

    exibir_resposta(resposta, 8, "Pergunta sobre Estoque")


# ============================================================================
# FUNÇÃO PRINCIPAL
# ============================================================================


def executar_todos_exemplos():
    """Executa todos os exemplos em sequência"""
    logger.info("\n")
    logger.info("╔" + "=" * 78 + "╗")
    logger.info("║" + " " * 20 + "CHAT DO OPERADOR - EXEMPLOS" + " " * 31 + "║")
    logger.info("║" + " " * 20 + "Sprint 6 - Passo 5" + " " * 39 + "║")
    logger.info("╚" + "=" * 78 + "╝")

    try:
        exemplo_1_cliente_vip()
        exemplo_2_kit_vantajoso()
        exemplo_3_produto_vendendo_bem()
        exemplo_4_sugestao_venda()
        exemplo_5_cliente_atrasado()
        exemplo_6_resumo_venda()
        exemplo_7_pergunta_generica()
        exemplo_8_estoque()

        print("\n\n" + "=" * 80)
        logger.info("✅ TODOS OS EXEMPLOS EXECUTADOS COM SUCESSO!")
        print("=" * 80)
        logger.info("\n📝 Observações:")
        logger.info("   - Todas as respostas são MOCK (IA simulada)")
        logger.info("   - Integração com IA real será no Passo 6")
        logger.info("   - Nenhuma ação foi executada (apenas consultas)")
        logger.info("   - Sistema está pronto para receber perguntas do operador")
        logger.info("\n")

    except Exception as e:
        logger.info(f"\n\n❌ ERRO AO EXECUTAR EXEMPLOS: {str(e)}")
        raise


if __name__ == "__main__":
    executar_todos_exemplos()
