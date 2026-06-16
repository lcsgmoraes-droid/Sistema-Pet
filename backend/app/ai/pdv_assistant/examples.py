"""
Exemplos de Uso do PDV Assistant

Demonstra como usar o sistema de IA contextual para PDV
em diferentes cenários reais.
"""

import asyncio
from datetime import datetime
from decimal import Decimal

from app.ai.pdv_assistant.models import (
    PDVContext,
    ItemVendaPDV,
)
from app.ai.pdv_assistant.service import PDVAIService
from app.utils.logger import logger


# ============================================================================
# EXEMPLO 1: Venda Simples - Apenas um produto
# ============================================================================


def criar_exemplo_venda_simples() -> PDVContext:
    """
    Venda simples com um produto de ração.

    Expectativa: IA pode sugerir produtos complementares.
    """
    return PDVContext(
        tenant_id=1,
        timestamp=datetime.now(),
        itens=[
            ItemVendaPDV(
                produto_id=101,
                nome_produto="Ração Premium 15kg",
                quantidade=1,
                valor_unitario=Decimal("159.90"),
                valor_total=Decimal("159.90"),
                categoria="Alimentação",
                fabricante="Royal Canin",
            )
        ],
        total_parcial=Decimal("159.90"),
        vendedor_id=1,
        vendedor_nome="João Silva",
    )


# ============================================================================
# EXEMPLO 2: Venda com Cliente Identificado
# ============================================================================


def criar_exemplo_cliente_recorrente() -> PDVContext:
    """
    Venda com cliente recorrente identificado.

    Expectativa: IA pode trazer informações sobre padrão de compra,
    última compra, produtos favoritos, etc.
    """
    return PDVContext(
        tenant_id=1,
        timestamp=datetime.now(),
        itens=[
            ItemVendaPDV(
                produto_id=101,
                nome_produto="Ração Premium 15kg",
                quantidade=1,
                valor_unitario=Decimal("159.90"),
                valor_total=Decimal("159.90"),
                categoria="Alimentação",
                fabricante="Royal Canin",
            )
        ],
        total_parcial=Decimal("159.90"),
        vendedor_id=1,
        vendedor_nome="João Silva",
        cliente_id=50,
        cliente_nome="Maria Oliveira",
        metadata={
            "cliente_ultima_compra": "2026-01-10",
            "cliente_total_compras": 12,
        },
    )


# ============================================================================
# EXEMPLO 3: Oportunidade de Kit
# ============================================================================


def criar_exemplo_oportunidade_kit() -> PDVContext:
    """
    Venda com produtos que fazem parte de um kit vantajoso.

    Expectativa: IA sugere que o kit é mais vantajoso.
    """
    return PDVContext(
        tenant_id=1,
        timestamp=datetime.now(),
        itens=[
            ItemVendaPDV(
                produto_id=101,
                nome_produto="Ração Premium 15kg",
                quantidade=1,
                valor_unitario=Decimal("159.90"),
                valor_total=Decimal("159.90"),
                categoria="Alimentação",
            ),
            ItemVendaPDV(
                produto_id=205,
                nome_produto="Shampoo Antipulgas",
                quantidade=1,
                valor_unitario=Decimal("45.00"),
                valor_total=Decimal("45.00"),
                categoria="Higiene",
            ),
        ],
        total_parcial=Decimal("204.90"),
        vendedor_id=1,
        vendedor_nome="João Silva",
        cliente_id=50,
        cliente_nome="Maria Oliveira",
    )


# ============================================================================
# EXEMPLO 4: Cross-sell
# ============================================================================


def criar_exemplo_cross_sell() -> PDVContext:
    """
    Venda com produto que frequentemente é comprado junto com outro.

    Expectativa: IA sugere produto complementar.
    """
    return PDVContext(
        tenant_id=1,
        timestamp=datetime.now(),
        itens=[
            ItemVendaPDV(
                produto_id=205,
                nome_produto="Shampoo Antipulgas",
                quantidade=1,
                valor_unitario=Decimal("45.00"),
                valor_total=Decimal("45.00"),
                categoria="Higiene",
            ),
        ],
        total_parcial=Decimal("45.00"),
        vendedor_id=1,
        vendedor_nome="João Silva",
        cliente_id=50,
        cliente_nome="Maria Oliveira",
    )


# ============================================================================
# EXEMPLO 5: Cliente VIP
# ============================================================================


def criar_exemplo_cliente_vip() -> PDVContext:
    """
    Venda com cliente de alto valor.

    Expectativa: IA destaca importância do cliente e sugere
    atendimento diferenciado.
    """
    return PDVContext(
        tenant_id=1,
        timestamp=datetime.now(),
        itens=[
            ItemVendaPDV(
                produto_id=301,
                nome_produto="Ração Super Premium 15kg",
                quantidade=2,
                valor_unitario=Decimal("299.90"),
                valor_total=Decimal("599.80"),
                categoria="Alimentação",
            ),
        ],
        total_parcial=Decimal("599.80"),
        vendedor_id=1,
        vendedor_nome="João Silva",
        cliente_id=99,
        cliente_nome="Roberto Santos",
        metadata={
            "cliente_categoria": "VIP",
            "cliente_total_gasto": "15000.00",
        },
    )


# ============================================================================
# EXEMPLO 6: Venda Vazia (Início)
# ============================================================================


def criar_exemplo_venda_vazia() -> PDVContext:
    """
    Venda ainda sem produtos (momento inicial).

    Expectativa: IA pode trazer informações sobre cliente,
    mas não sobre produtos.
    """
    return PDVContext(
        tenant_id=1,
        timestamp=datetime.now(),
        itens=[],
        total_parcial=Decimal("0.00"),
        vendedor_id=1,
        vendedor_nome="João Silva",
        cliente_id=50,
        cliente_nome="Maria Oliveira",
    )


# ============================================================================
# FUNÇÃO AUXILIAR: Executar Exemplo
# ============================================================================


async def executar_exemplo(
    nome: str,
    pdv_context: PDVContext,
    db_session,  # Passado como parâmetro
) -> None:
    """
    Executa um exemplo e exibe os resultados.

    Args:
        nome: Nome do exemplo
        pdv_context: Contexto do PDV
        db_session: Sessão do banco de dados
    """
    logger.info(f"\n{'=' * 80}")
    logger.info(f"EXEMPLO: {nome}")
    logger.info(f"{'=' * 80}")

    logger.info("\n📋 CONTEXTO:")
    logger.info(f"  Vendedor: {pdv_context.vendedor_nome}")
    if pdv_context.tem_cliente_identificado:
        logger.info(f"  Cliente: {pdv_context.cliente_nome}")
    logger.info(f"  Itens na venda: {pdv_context.quantidade_itens}")
    logger.info(f"  Total parcial: R$ {pdv_context.total_parcial:.2f}")

    if pdv_context.itens:
        logger.info("\n  Produtos:")
        for item in pdv_context.itens:
            logger.info(f"    • {item.nome_produto} - R$ {item.valor_total:.2f}")

    # Criar serviço
    service = PDVAIService(db=db_session, use_mock=True)

    # Gerar sugestões
    logger.info("\n🤖 GERANDO SUGESTÕES...")
    sugestoes = await service.sugerir_para_pdv(pdv_context)

    # Exibir sugestões
    logger.info(f"\n💡 SUGESTÕES GERADAS ({len(sugestoes)}):")
    if sugestoes:
        for i, sugestao in enumerate(sugestoes, 1):
            logger.info(
                f"\n  {i}. [{sugestao.prioridade.value.upper()}] {sugestao.titulo}"
            )
            logger.info(f"     {sugestao.mensagem}")
            if sugestao.acao_sugerida:
                logger.info(f"     ➜ Ação: {sugestao.acao_sugerida}")
            logger.info(f"     Confiança: {sugestao.confianca * 100:.0f}%")
    else:
        logger.info("  Nenhuma sugestão gerada.")

    logger.info(f"\n{'=' * 80}\n")


# ============================================================================
# FUNÇÃO PRINCIPAL: Executar Todos os Exemplos
# ============================================================================


async def executar_todos_exemplos(db_session) -> None:
    """
    Executa todos os exemplos em sequência.

    Args:
        db_session: Sessão do banco de dados
    """
    print("\n" + "=" * 80)
    logger.info("DEMONSTRAÇÃO: PDV ASSISTANT - IA CONTEXTUAL PARA PDV")
    print("=" * 80)

    exemplos = [
        ("Venda Simples", criar_exemplo_venda_simples()),
        ("Cliente Recorrente", criar_exemplo_cliente_recorrente()),
        ("Oportunidade de Kit", criar_exemplo_oportunidade_kit()),
        ("Cross-sell", criar_exemplo_cross_sell()),
        ("Cliente VIP", criar_exemplo_cliente_vip()),
        ("Venda Vazia", criar_exemplo_venda_vazia()),
    ]

    for nome, contexto in exemplos:
        await executar_exemplo(nome, contexto, db_session)
        await asyncio.sleep(0.5)  # Pausa entre exemplos

    print("\n" + "=" * 80)
    logger.info("DEMONSTRAÇÃO CONCLUÍDA")
    logger.info("=" * 80 + "\n")


# ============================================================================
# EXEMPLO DE USO DIRETO
# ============================================================================


async def exemplo_uso_direto() -> None:
    """
    Exemplo de uso direto do serviço (sem banco de dados real).

    Para testes rápidos sem dependências.
    """
    from unittest.mock import MagicMock

    logger.info("\n🚀 EXEMPLO DE USO DIRETO\n")

    # Mock da sessão do banco
    db_mock = MagicMock()
    db_mock.query.return_value.filter.return_value.all.return_value = []

    # Criar contexto
    contexto = criar_exemplo_venda_simples()

    # Criar serviço
    service = PDVAIService(db=db_mock, use_mock=True)

    # Gerar sugestões
    sugestoes = await service.sugerir_para_pdv(contexto)

    logger.info(f"✅ Geradas {len(sugestoes)} sugestões")

    for sugestao in sugestoes:
        logger.info(f"\n  • {sugestao.mensagem}")


# ============================================================================
# PONTO DE ENTRADA
# ============================================================================

if __name__ == "__main__":
    """
    Executa exemplos quando o arquivo é executado diretamente.
    
    Para executar:
        python -m app.ai.pdv_assistant.examples
    """
    logger.info("\n⚠️  NOTA: Para executar os exemplos completos, use:")
    logger.info("    python -m app.ai.pdv_assistant.examples")
    logger.info("\nExecutando exemplo direto...\n")

    asyncio.run(exemplo_uso_direto())
