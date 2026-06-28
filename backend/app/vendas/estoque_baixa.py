"""Baixa de estoque de itens de venda."""

import logging
from typing import Any, Dict, List, TYPE_CHECKING

from sqlalchemy.orm import Session

from app.estoque.service import EstoqueService

if TYPE_CHECKING:
    from app.produtos_models import Produto

logger = logging.getLogger(__name__)

__all__ = ["processar_baixa_estoque_item"]


def processar_baixa_estoque_item(
    produto: "Produto",
    quantidade_vendida: float,
    venda_id: int,
    user_id: int,
    tenant_id: str,
    db: Session,
    product_variation_id: int = None,
    venda_codigo: str = None,
) -> List[Dict[str, Any]]:
    """
    Processa a baixa de estoque de um item de venda.

    Comportamento por tipo de produto:
    - SIMPLES/VARIACAO: Baixa estoque do próprio produto (ou da variação se product_variation_id fornecido)
    - KIT FÍSICO: Baixa estoque do KIT (tratado como produto simples)
    - KIT VIRTUAL: Baixa estoque de cada componente em cascata

    Args:
        produto: Objeto Produto (com tipo_produto e tipo_kit)
        quantidade_vendida: Quantidade vendida do produto
        venda_id: ID da venda
        user_id: ID do usuário (tenant)
        db: Sessão do banco (NÃO faz commit)
        product_variation_id: ID da variação do produto (se aplicável)

    Returns:
        List[Dict] com resultados da baixa de estoque para cada produto afetado

    Raises:
        ValueError: Se estoque insuficiente ou componente inválido
    """
    resultados = []

    # Se tiver product_variation_id, usar o produto da variação
    if product_variation_id:
        from app.produtos_models import Produto

        variacao = (
            db.query(Produto)
            .filter(
                Produto.id == product_variation_id,
                Produto.tipo_produto == "VARIACAO",
            )
            .first()
        )

        if variacao:
            produto = (
                variacao  # A variação é o próprio produto a ser baixado do estoque
            )

    # ============================================================
    # CASO 1: PRODUTO SIMPLES OU VARIAÇÃO
    # ============================================================
    if produto.tipo_produto in ("SIMPLES", "VARIACAO"):
        resultado_estoque = EstoqueService.baixar_estoque(
            produto_id=produto.id,
            quantidade=quantidade_vendida,
            motivo="venda",
            referencia_id=venda_id,
            referencia_tipo="venda",
            user_id=user_id,
            tenant_id=tenant_id,
            db=db,
            documento=venda_codigo,
            observacao=None,
        )

        resultados.append(
            {
                "produto": resultado_estoque["produto_nome"],
                "produto_id": produto.id,
                "tipo_produto": produto.tipo_produto,
                "quantidade": quantidade_vendida,
                "estoque_anterior": resultado_estoque["estoque_anterior"],
                "estoque_novo": resultado_estoque["estoque_novo"],
            }
        )

        logger.info(
            f"📦 Estoque baixado: {resultado_estoque['produto_nome']} - "
            f"Qtd: {quantidade_vendida} ({resultado_estoque['estoque_anterior']} → {resultado_estoque['estoque_novo']})"
        )

        return resultados

    # ============================================================
    # CASO 2: PRODUTO KIT
    # ============================================================
    if produto.tipo_produto == "KIT":
        tipo_kit = produto.tipo_kit or "VIRTUAL"  # Default VIRTUAL se não definido

        # --------------------------------------------------------
        # CASO 2.1: KIT FÍSICO (tratado como produto simples)
        # LÓGICA: Venda de kit físico só baixa o estoque do KIT
        # Os componentes já foram baixados quando o kit foi montado (entrada)
        # Portanto, NÃO sensibiliza os componentes novamente
        # --------------------------------------------------------
        if tipo_kit == "FISICO":
            resultado_estoque = EstoqueService.baixar_estoque(
                produto_id=produto.id,
                quantidade=quantidade_vendida,
                motivo="venda",
                referencia_id=venda_id,
                referencia_tipo="venda",
                user_id=user_id,
                tenant_id=tenant_id,
                db=db,
                documento=venda_codigo,
                observacao="KIT FÍSICO - Estoque próprio (componentes já foram baixados na montagem)",
            )

            resultados.append(
                {
                    "produto": resultado_estoque["produto_nome"],
                    "produto_id": produto.id,
                    "tipo_produto": "KIT",
                    "tipo_kit": "FISICO",
                    "quantidade": quantidade_vendida,
                    "estoque_anterior": resultado_estoque["estoque_anterior"],
                    "estoque_novo": resultado_estoque["estoque_novo"],
                }
            )

            logger.info(
                f"📦 KIT FÍSICO vendido: {resultado_estoque['produto_nome']} - "
                f"Qtd: {quantidade_vendida} ({resultado_estoque['estoque_anterior']} → {resultado_estoque['estoque_novo']}) "
                f"[Componentes NÃO sensibilizados - já foram baixados na montagem]"
            )

            return resultados

        # --------------------------------------------------------
        # CASO 2.2: KIT VIRTUAL (baixa em cascata dos componentes)
        # --------------------------------------------------------
        if tipo_kit == "VIRTUAL":
            from app.produtos_models import ProdutoKitComponente, Produto

            # Buscar componentes do KIT
            componentes = (
                db.query(ProdutoKitComponente)
                .filter(ProdutoKitComponente.kit_id == produto.id)
                .all()
            )

            if not componentes:
                raise ValueError(
                    f"KIT VIRTUAL '{produto.nome}' não possui componentes cadastrados. "
                    f"Não é possível processar a venda."
                )

            logger.info(
                f"📦 KIT VIRTUAL: {produto.nome} - "
                f"Processando {len(componentes)} componentes (Qtd vendida: {quantidade_vendida})"
            )

            # Baixar estoque de cada componente
            for componente in componentes:
                # Calcular quantidade total do componente
                quantidade_componente = quantidade_vendida * componente.quantidade

                # Buscar dados do produto componente
                produto_componente = (
                    db.query(Produto)
                    .filter(
                        Produto.id == componente.produto_componente_id,
                        Produto.user_id == user_id,
                    )
                    .first()
                )

                if not produto_componente:
                    raise ValueError(
                        f"Componente ID {componente.produto_componente_id} não encontrado"
                    )

                # Validar tipo do componente (apenas SIMPLES ou VARIACAO)
                if produto_componente.tipo_produto not in ("SIMPLES", "VARIACAO"):
                    raise ValueError(
                        f"Componente '{produto_componente.nome}' possui tipo inválido: {produto_componente.tipo_produto}. "
                        f"KIT VIRTUAL aceita apenas componentes SIMPLES ou VARIACAO."
                    )

                # Validar se componente está ativo (apenas warning, não bloqueia venda)
                if not produto_componente.situacao:
                    logger.warning(
                        f"⚠️ Componente '{produto_componente.nome}' (ID: {produto_componente.id}) está INATIVO. "
                        f"Venda do KIT '{produto.nome}' será processada normalmente."
                    )

                # Baixar estoque do componente
                resultado_componente = EstoqueService.baixar_estoque(
                    produto_id=produto_componente.id,
                    quantidade=quantidade_componente,
                    motivo="venda",
                    referencia_id=venda_id,
                    referencia_tipo="venda",
                    user_id=user_id,
                    tenant_id=tenant_id,
                    db=db,
                    documento=venda_codigo,
                    observacao=f"Componente do KIT VIRTUAL '{produto.nome}' (vendido: {quantidade_vendida}x)",
                )

                resultados.append(
                    {
                        "produto": resultado_componente["produto_nome"],
                        "produto_id": produto_componente.id,
                        "tipo_produto": produto_componente.tipo_produto,
                        "quantidade": quantidade_componente,
                        "estoque_anterior": resultado_componente["estoque_anterior"],
                        "estoque_novo": resultado_componente["estoque_novo"],
                        "kit_origem": produto.nome,
                        "kit_id": produto.id,
                    }
                )

                logger.info(
                    f"   ↳ Componente: {resultado_componente['produto_nome']} - "
                    f"Qtd: {quantidade_componente} ({resultado_componente['estoque_anterior']} → {resultado_componente['estoque_novo']})"
                )

            logger.info(
                f"✅ KIT VIRTUAL '{produto.nome}' processado: {len(componentes)} componentes baixados"
            )

            return resultados

    # ============================================================
    # CASO 3: TIPO DE PRODUTO NÃO SUPORTADO
    # ============================================================
    raise ValueError(
        f"Tipo de produto '{produto.tipo_produto}' não suportado para baixa de estoque. "
        f"Tipos válidos: SIMPLES, VARIACAO, KIT"
    )
