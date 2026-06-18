"""
Rotas de edicao e exclusao de movimentacoes de estoque.
"""

import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user_and_tenant
from app.bling_estoque_sync import sincronizar_bling_background
from app.db import get_session
from app.produtos_models import (
    EstoqueMovimentacao,
    Produto,
    ProdutoKitComponente,
    ProdutoLote,
)


logger = logging.getLogger(__name__)

router = APIRouter(prefix="/estoque", tags=["Estoque"])


def _buscar_movimentacao(db: Session, movimentacao_id: int, tenant_id: int):
    movimentacao = (
        db.query(EstoqueMovimentacao)
        .filter(
            EstoqueMovimentacao.id == movimentacao_id,
            EstoqueMovimentacao.tenant_id == tenant_id,
        )
        .first()
    )
    if not movimentacao:
        raise HTTPException(status_code=404, detail="Movimentacao nao encontrada")
    return movimentacao


def _buscar_produto(db: Session, produto_id: int, tenant_id: int):
    return (
        db.query(Produto)
        .filter(
            Produto.id == produto_id,
            Produto.tenant_id == tenant_id,
        )
        .first()
    )


def _buscar_produto_obrigatorio(db: Session, produto_id: int, tenant_id: int):
    produto = _buscar_produto(db, produto_id, tenant_id)
    if not produto:
        raise HTTPException(status_code=404, detail="Produto nao encontrado")
    return produto


def _buscar_lote(db: Session, lote_id: int):
    return db.query(ProdutoLote).filter(ProdutoLote.id == lote_id).first()


def _movimentacao_retorna_componentes(movimentacao) -> bool:
    return (
        movimentacao.tipo == "saida"
        and movimentacao.observacao
        and "componentes retornados" in movimentacao.observacao.lower()
    )


def _registrar_componente_estornado(
    componentes_estornados,
    componente_produto,
    quantidade,
    estoque_anterior,
    acao: str,
):
    componentes_estornados.append(
        {
            "nome": componente_produto.nome,
            "quantidade": quantidade,
            "estoque_anterior": estoque_anterior,
            "estoque_novo": componente_produto.estoque_atual,
            "acao": acao,
        }
    )


def _ajustar_componente_kit(
    componentes_estornados,
    componente_produto,
    quantidade,
    delta,
    acao: str,
    log_acao: str,
):
    estoque_anterior = componente_produto.estoque_atual
    componente_produto.estoque_atual += delta
    sinal = "+" if delta >= 0 else "-"
    logger.info(
        "%s: %s -> %s (%s%s) [%s]",
        componente_produto.nome,
        estoque_anterior,
        componente_produto.estoque_atual,
        sinal,
        quantidade,
        log_acao,
    )
    _registrar_componente_estornado(
        componentes_estornados,
        componente_produto,
        quantidade,
        estoque_anterior,
        acao,
    )


def _estornar_componentes_kit_fisico(
    db: Session, produto, movimentacao, tenant_id: int
):
    componentes_estornados = []
    if produto.tipo_produto != "KIT" or produto.tipo_kit != "FISICO":
        return componentes_estornados

    componentes_kit = (
        db.query(ProdutoKitComponente)
        .filter(
            ProdutoKitComponente.kit_id == produto.id,
        )
        .all()
    )
    if not componentes_kit:
        return componentes_estornados

    logger.info("KIT FISICO detectado - Estornando componentes...")
    for comp in componentes_kit:
        componente_produto = _buscar_produto(
            db,
            comp.produto_componente_id,
            tenant_id,
        )
        if not componente_produto:
            continue

        quantidade_componente = comp.quantidade * movimentacao.quantidade
        if movimentacao.tipo == "entrada":
            _ajustar_componente_kit(
                componentes_estornados,
                componente_produto,
                quantidade_componente,
                quantidade_componente,
                "devolvido",
                "devolvido",
            )
        elif _movimentacao_retorna_componentes(movimentacao):
            _ajustar_componente_kit(
                componentes_estornados,
                componente_produto,
                quantidade_componente,
                -quantidade_componente,
                "estornado",
                "estornando retorno",
            )

    logger.info("KIT FISICO: %s componentes estornados", len(componentes_estornados))
    return componentes_estornados


def _reverter_estoque_produto(produto, movimentacao):
    estoque_anterior = produto.estoque_atual
    if movimentacao.tipo == "entrada":
        delta = -movimentacao.quantidade
    elif movimentacao.tipo == "saida":
        delta = movimentacao.quantidade
    else:
        return

    produto.estoque_atual += delta
    sinal = "+" if delta >= 0 else "-"
    logger.info(
        "Estoque %s: %s -> %s (%s%s)",
        produto.nome,
        estoque_anterior,
        produto.estoque_atual,
        sinal,
        movimentacao.quantidade,
    )


def _reverter_lote_por_exclusao(db: Session, movimentacao):
    if not movimentacao.lote_id:
        return

    lote = _buscar_lote(db, movimentacao.lote_id)
    if not lote:
        return

    if movimentacao.tipo == "entrada":
        lote.quantidade_disponivel -= movimentacao.quantidade
        if lote.quantidade_disponivel <= 0:
            lote.status = "esgotado"
    elif movimentacao.tipo == "saida":
        lote.quantidade_disponivel += movimentacao.quantidade
        lote.status = "ativo"


def _ajustar_lote_por_edicao(db: Session, movimentacao, diferenca):
    if not movimentacao.lote_id:
        return

    lote = _buscar_lote(db, movimentacao.lote_id)
    if not lote:
        return

    if movimentacao.tipo == "entrada":
        lote.quantidade_disponivel += diferenca
    elif movimentacao.tipo == "saida":
        lote.quantidade_disponivel -= diferenca


def _aplicar_edicao_quantidade(produto, movimentacao, quantidade_nova, db: Session):
    diferenca = quantidade_nova - movimentacao.quantidade
    if movimentacao.tipo == "entrada":
        produto.estoque_atual += diferenca
    elif movimentacao.tipo == "saida":
        produto.estoque_atual -= diferenca

    _ajustar_lote_por_edicao(db, movimentacao, diferenca)
    movimentacao.quantidade = quantidade_nova
    movimentacao.quantidade_nova = produto.estoque_atual


def _agendar_sync_bling(produto, origem: str, log_contexto: str):
    try:
        sincronizar_bling_background(produto.id, produto.estoque_atual, origem)
    except Exception as e_sync:
        logger.warning(
            "[BLING-SYNC] Erro ao agendar sync (%s): %s",
            log_contexto,
            e_sync,
        )


@router.delete("/movimentacoes/{movimentacao_id}")
def excluir_movimentacao(
    movimentacao_id: int,
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    """
    Exclui uma movimentacao de estoque e reverte o efeito no produto.
    """
    _current_user, tenant_id = user_and_tenant
    try:
        movimentacao = _buscar_movimentacao(db, movimentacao_id, tenant_id)
        produto = _buscar_produto_obrigatorio(db, movimentacao.produto_id, tenant_id)

        logger.info(
            "Excluindo movimentacao %s - Tipo: %s, Qtd: %s",
            movimentacao_id,
            movimentacao.tipo,
            movimentacao.quantidade,
        )

        componentes_estornados = _estornar_componentes_kit_fisico(
            db,
            produto,
            movimentacao,
            tenant_id,
        )
        _reverter_estoque_produto(produto, movimentacao)
        _reverter_lote_por_exclusao(db, movimentacao)

        db.delete(movimentacao)
        db.commit()

        logger.info("Movimentacao excluida")

        _agendar_sync_bling(produto, "exclusao_movimentacao", "exclusao_mov")

        return {
            "message": "Movimentacao excluida com sucesso",
            "componentes_estornados": componentes_estornados,
        }

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error("Erro ao excluir movimentacao: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


class UpdateMovimentacaoRequest(BaseModel):
    quantidade: Optional[float] = None
    custo_unitario: Optional[float] = None
    observacao: Optional[str] = None


@router.patch("/movimentacoes/{movimentacao_id}")
def editar_movimentacao(
    movimentacao_id: int,
    dados: UpdateMovimentacaoRequest,
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    """
    Edita uma movimentacao existente.
    """
    _current_user, tenant_id = user_and_tenant
    try:
        movimentacao = _buscar_movimentacao(db, movimentacao_id, tenant_id)
        produto = _buscar_produto_obrigatorio(db, movimentacao.produto_id, tenant_id)

        if dados.quantidade is not None and dados.quantidade != movimentacao.quantidade:
            _aplicar_edicao_quantidade(produto, movimentacao, dados.quantidade, db)

        if dados.custo_unitario is not None:
            movimentacao.custo_unitario = dados.custo_unitario
            movimentacao.valor_total = movimentacao.quantidade * dados.custo_unitario

        if dados.observacao is not None:
            movimentacao.observacao = dados.observacao

        db.commit()
        db.refresh(movimentacao)

        logger.info("Movimentacao editada")

        if dados.quantidade is not None:
            _agendar_sync_bling(produto, "edicao_movimentacao", "edicao_mov")

        return {
            "id": movimentacao.id,
            "quantidade": movimentacao.quantidade,
            "custo_unitario": movimentacao.custo_unitario,
            "observacao": movimentacao.observacao,
            "estoque_atual_produto": produto.estoque_atual,
        }

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error("Erro ao editar movimentacao: %s", e)
        raise HTTPException(status_code=500, detail=str(e))
