# ⚠️ ARQUIVO CRÍTICO DE PRODUÇÃO
# Este arquivo impacta diretamente operações reais (PDV / Financeiro / Estoque).
# NÃO alterar sem:
# 1. Entender o fluxo completo
# 2. Testar cenário real
# 3. Validar impacto financeiro

"""
ROTAS DE ESTOQUE - Sistema Pet Shop Pro
Gestão completa de estoque com sincronização Bling

Funcionalidades:
- Entrada manual de estoque
- Saída manual (perdas, avarias, ajustes)
- Transferências entre estoques
- Sincronização bidirecional com Bling
- Entrada por XML (NF-e fornecedor)
- Alertas e relatórios
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import Optional
from pydantic import BaseModel, Field
from datetime import date
from decimal import Decimal, ROUND_HALF_UP
import json

from .db import get_session
from .auth.dependencies import get_current_user_and_tenant
from .financeiro_models import ContaPagar
from .produtos_models import (
    Produto,
    ProdutoLote,
    EstoqueMovimentacao,
)
from .produtos.estoque_regras import mensagem_servico_sem_estoque, produto_eh_servico
from .bling_estoque_sync import sincronizar_bling_background
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/estoque", tags=["Estoque"])

# ============================================================================
# SCHEMAS
# ============================================================================


class SaidaEstoqueRequest(BaseModel):
    """Saída manual de estoque"""

    produto_id: int
    quantidade: float = Field(gt=0)
    motivo: str = Field(
        default="perda"
    )  # perda, avaria, roubo, amostra, uso_interno, devolucao_fornecedor, ajuste
    documento: Optional[str] = None
    observacao: Optional[str] = None
    # Para KIT FÍSICO: se True, desmontou o kit e volta os componentes ao estoque
    retornar_componentes: bool = False
    # Uso interno: reclassifica custo do estoque para despesa do mes, sem movimentar banco/caixa
    gerar_despesa_uso_interno: bool = False
    descricao_despesa: Optional[str] = None
    data_competencia: Optional[date] = None
    categoria_id: Optional[int] = None
    dre_subcategoria_id: Optional[int] = None
    tipo_despesa_id: Optional[int] = None


# ============================================================================
# SAÍDA DE ESTOQUE
# ============================================================================


@router.post("/saida", status_code=status.HTTP_201_CREATED)
def saida_estoque(
    saida: SaidaEstoqueRequest,
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    """
    Saída manual de estoque

    Motivos:
    - perda: Vencimento, deterioração
    - avaria: Produto danificado
    - roubo: Roubo/furto
    - amostra: Amostra grátis
    - uso_interno: Uso da loja
    - devolucao_fornecedor: Devolução ao fornecedor
    - ajuste: Ajuste negativo de inventário
    """
    current_user, tenant_id = user_and_tenant
    logger.info(
        f"📤 Saída de estoque - Produto {saida.produto_id}, Qtd: {saida.quantidade}"
    )

    # Buscar produto
    produto = (
        db.query(Produto)
        .filter(Produto.id == saida.produto_id, Produto.tenant_id == tenant_id)
        .first()
    )
    if not produto:
        raise HTTPException(status_code=404, detail="Produto não encontrado")

    # ========================================
    # 🔒 TRAVA 2 — VALIDAÇÃO: PRODUTO PAI NÃO TEM ESTOQUE
    # ========================================
    if produto_eh_servico(produto):
        raise HTTPException(status_code=400, detail=mensagem_servico_sem_estoque(produto))

    if produto.is_parent:
        raise HTTPException(
            status_code=400,
            detail=f"❌ Produto '{produto.nome}' possui variações. O estoque deve ser controlado nas variações individuais (cor, tamanho, etc.), não no produto pai.",
        )

    # ========== VALIDAÇÃO: KIT VIRTUAL não permite movimentação manual ==========
    if produto.tipo_produto == "KIT" and produto.tipo_kit == "VIRTUAL":
        raise HTTPException(
            status_code=400,
            detail=(
                f"❌ Não é possível movimentar estoque manualmente para KIT VIRTUAL. "
                f"O estoque deste kit ('{produto.nome}') é calculado automaticamente "
                f"com base nos componentes que o compõem. "
                f"Para reduzir o estoque, movimente os produtos componentes individualmente."
            ),
        )

    estoque_anterior = produto.estoque_atual or 0

    # Validar estoque disponível
    if estoque_anterior < saida.quantidade:
        raise HTTPException(
            status_code=400,
            detail=f"Estoque insuficiente. Disponível: {estoque_anterior}, Solicitado: {saida.quantidade}",
        )

    # Sistema FIFO: consumir lotes mais antigos (se existirem lotes ativos)
    lotes_consumidos = []
    lotes_ativos = (
        db.query(ProdutoLote)
        .filter(
            ProdutoLote.produto_id == produto.id,
            ProdutoLote.quantidade_disponivel > 0,
            ProdutoLote.status == "ativo",
        )
        .order_by(ProdutoLote.ordem_entrada)
        .all()
    )

    if lotes_ativos:
        # Se tem lotes, usar FIFO
        quantidade_restante = saida.quantidade

        for lote in lotes_ativos:
            if quantidade_restante <= 0:
                break

            saldo_anterior = (
                lote.quantidade_disponivel
            )  # Guardar saldo antes de consumir
            qtd_consumir = min(lote.quantidade_disponivel, quantidade_restante)
            lote.quantidade_disponivel -= qtd_consumir
            quantidade_restante -= qtd_consumir

            if lote.quantidade_disponivel == 0:
                lote.status = "esgotado"

            lotes_consumidos.append(
                {
                    "lote_id": lote.id,
                    "nome_lote": lote.nome_lote,
                    "quantidade": qtd_consumir,
                    "saldo_anterior": saldo_anterior,  # Para mostrar (X/Y)
                }
            )

            logger.info(f"📦 FIFO: Consumido lote {lote.nome_lote}: {qtd_consumir}")

        if quantidade_restante > 0:
            logger.warning(
                f"⚠️ Lotes insuficientes. Restante será deduzido do estoque geral: {quantidade_restante}"
            )

    # Atualizar estoque do produto
    produto.estoque_atual = estoque_anterior - saida.quantidade

    # Registrar movimentação
    movimentacao = EstoqueMovimentacao(
        produto_id=produto.id,
        tipo="saida",
        motivo=saida.motivo,
        quantidade=saida.quantidade,
        quantidade_anterior=estoque_anterior,
        quantidade_nova=produto.estoque_atual,
        custo_unitario=produto.preco_custo,
        valor_total=saida.quantidade * (produto.preco_custo or 0),
        lotes_consumidos=json.dumps(lotes_consumidos) if lotes_consumidos else None,
        documento=saida.documento,
        observacao=saida.observacao,
        user_id=current_user.id,
        tenant_id=tenant_id,
    )
    db.add(movimentacao)

    conta_pagar_uso_interno = None
    if saida.motivo == "uso_interno" and saida.gerar_despesa_uso_interno:
        db.flush()

        valor_total_despesa = Decimal(str(movimentacao.valor_total or 0)).quantize(
            Decimal("0.01"),
            rounding=ROUND_HALF_UP,
        )
        data_competencia = saida.data_competencia or date.today()
        descricao_despesa = (
            saida.descricao_despesa or f"Material de uso interno - {produto.nome}"
        ).strip()
        observacoes_uso_interno = (
            "Baixa de estoque para uso interno, sem desembolso financeiro. "
            f"Movimentacao de estoque #{movimentacao.id}."
        )
        if saida.observacao:
            observacoes_uso_interno = (
                f"{observacoes_uso_interno}\nObservacao: {saida.observacao}"
            )

        conta_pagar_uso_interno = ContaPagar(
            descricao=descricao_despesa,
            fornecedor_id=None,
            categoria_id=saida.categoria_id,
            dre_subcategoria_id=saida.dre_subcategoria_id,
            canal="loja_fisica",
            tipo_despesa_id=saida.tipo_despesa_id,
            valor_original=valor_total_despesa,
            valor_pago=valor_total_despesa,
            valor_final=valor_total_despesa,
            data_emissao=data_competencia,
            data_vencimento=data_competencia,
            data_pagamento=data_competencia,
            status="pago",
            documento=saida.documento or f"USO-EST-{movimentacao.id}",
            observacoes=observacoes_uso_interno,
            user_id=current_user.id,
            tenant_id=tenant_id,
        )
        db.add(conta_pagar_uso_interno)

    db.commit()
    db.refresh(movimentacao)
    if conta_pagar_uso_interno:
        db.refresh(conta_pagar_uso_interno)

    logger.info(
        f"✅ Saída registrada - Estoque: {estoque_anterior} → {produto.estoque_atual}"
    )

    # Alerta se estoque baixo
    if produto.estoque_atual <= (produto.estoque_minimo or 0):
        logger.warning(
            f"⚠️ Estoque abaixo do mínimo! {produto.nome}: {produto.estoque_atual}"
        )

    # ========== SENSIBILIZAÇÃO: KIT FÍSICO - SAÍDA pode retornar componentes ==========
    # LÓGICA: Saída no kit físico PODE retornar os componentes ao estoque (se desmontou o kit)
    # Exemplo:
    # - Desmontou o kit: retornar_componentes=True → componentes AUMENTAM (voltam ao estoque)
    # - Perdeu/vendeu o kit: retornar_componentes=False → componentes NÃO mexem
    componentes_sensibilizados = []
    if produto.tipo_produto == "KIT" and produto.tipo_kit == "FISICO":
        from .produtos_models import ProdutoKitComponente

        # Buscar componentes do kit
        componentes = (
            db.query(ProdutoKitComponente)
            .filter(ProdutoKitComponente.kit_id == produto.id)
            .all()
        )

        if saida.retornar_componentes:
            # CASO 1: Desmontou o kit - componentes VOLTAM ao estoque
            logger.info(
                f"🧩 KIT FÍSICO - DESMONTAGEM: Retornando {len(componentes)} componentes ao estoque (desmontando {saida.quantidade} kits)"
            )

            for comp in componentes:
                componente_produto = (
                    db.query(Produto)
                    .filter(Produto.id == comp.produto_componente_id)
                    .first()
                )

                if componente_produto:
                    quantidade_componente = saida.quantidade * comp.quantidade
                    estoque_ant_comp = componente_produto.estoque_atual or 0

                    # ⚠️ IMPORTANTE: AUMENTA os componentes (voltam ao estoque após desmontagem)
                    componente_produto.estoque_atual = (
                        estoque_ant_comp + quantidade_componente
                    )

                    # Registrar movimentação do componente como ENTRADA (devolução)
                    mov_componente = EstoqueMovimentacao(
                        produto_id=componente_produto.id,
                        tipo="entrada",
                        motivo="kit_fisico_desmontagem",
                        quantidade=quantidade_componente,
                        quantidade_anterior=estoque_ant_comp,
                        quantidade_nova=componente_produto.estoque_atual,
                        custo_unitario=componente_produto.preco_custo,
                        valor_total=quantidade_componente
                        * (componente_produto.preco_custo or 0),
                        observacao=f"Desmontagem: componente retornado ao estoque após desmontar KIT FÍSICO '{produto.nome}' (desmontados {saida.quantidade} kit(s))",
                        user_id=current_user.id,
                        tenant_id=tenant_id,
                    )
                    db.add(mov_componente)

                    componentes_sensibilizados.append(
                        {
                            "id": componente_produto.id,
                            "nome": componente_produto.nome,
                            "quantidade": quantidade_componente,
                            "estoque_anterior": estoque_ant_comp,
                            "estoque_novo": componente_produto.estoque_atual,
                            "acao": "retornado",
                        }
                    )

                    logger.info(
                        f"   ↳ {componente_produto.nome}: {estoque_ant_comp} → {componente_produto.estoque_atual} (+{quantidade_componente}) [retornado ao estoque]"
                    )

            db.commit()
            logger.info(
                f"✅ KIT FÍSICO: {len(componentes_sensibilizados)} componentes retornados ao estoque"
            )
        else:
            # CASO 2: NÃO desmontou - componentes NÃO mexem (perda, roubo, venda, etc)
            logger.info(
                f"🧩 KIT FÍSICO - SAÍDA SEM DESMONTAGEM: Componentes NÃO serão retornados ao estoque (perda/roubo/etc de {saida.quantidade} kits)"
            )
            # Não faz nada com os componentes

    # Retornar dict
    response_data = {
        "id": movimentacao.id,
        "produto_id": movimentacao.produto_id,
        "produto_nome": produto.nome,
        "tipo": movimentacao.tipo,
        "motivo": movimentacao.motivo,
        "quantidade": movimentacao.quantidade,
        "quantidade_anterior": movimentacao.quantidade_anterior,
        "quantidade_nova": movimentacao.quantidade_nova,
        "custo_unitario": movimentacao.custo_unitario,
        "valor_total": movimentacao.valor_total,
        "documento": movimentacao.documento,
        "observacao": movimentacao.observacao,
        "user_id": movimentacao.user_id,
        "user_nome": current_user.nome,
        "created_at": movimentacao.created_at,
        "despesa_uso_interno": {
            "conta_pagar_id": conta_pagar_uso_interno.id,
            "valor": float(conta_pagar_uso_interno.valor_original),
            "data_competencia": conta_pagar_uso_interno.data_emissao,
        }
        if conta_pagar_uso_interno
        else None,
        "componentes_sensibilizados": componentes_sensibilizados
        if componentes_sensibilizados
        else None,
    }

    # Sincronizar estoque com Bling automaticamente
    try:
        sincronizar_bling_background(produto.id, produto.estoque_atual, "saida_estoque")
    except Exception as e_sync:
        logger.warning(f"[BLING-SYNC] Erro ao agendar sync (saida): {e_sync}")

    return response_data
